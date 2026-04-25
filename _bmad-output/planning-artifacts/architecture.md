---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md
workflowType: 'architecture'
project_name: 'SolalexDevelopment'
user_name: 'Alex'
date: '2026-04-22'
lastStep: 8
status: 'complete'
completedAt: '2026-04-22'
amendments:
  - date: '2026-04-22'
    title: 'Komplexitäts-Reduktion — 16 Cuts'
    summary: 'Solo-Dev-orientiertes Vereinfachungspaket. Event-Bus → direkter Aufruf; SQLAlchemy+Alembic → aiosqlite + schema_version + Rollback via Backup-Replace; WS → REST-Polling; Ed25519-Signatur gestrichen; Controller-Split konsolidiert; Template-JSON-Layer gestrichen; Day-1-Adapter auf 3 (Marstek/Shelly/Hoymiles); Wizard 7→4; strukturelle Vereinfachungen in Frontend, Repo-Layout und CI. Multi-Arch-Build bleibt. Begründungen in den entsprechenden Sektionen.'
---

# Architecture Decision Document

_Amendment 2026-04-22: 16 Cuts zur Komplexitätsreduktion eingearbeitet. Historische Entscheidungen (SQLAlchemy+Alembic, In-Process-Event-Bus, WS-Live-Stream, Ed25519, Template-JSON-Layer, etc.) wurden ersetzt. Details im Abschnitt „Amendment-Log" am Ende._

## Project Context Analysis

### Requirements Overview

**Funktionale Requirements:** 43 FRs in 8 Kategorien. Architektonisch kondensieren sie sich auf ~6–8 Kernmodule mit einem hardware-agnostischen Controller als Rückgrat.

**Non-Functional Requirements — architekturprägend:**

- Performance-Budget: Regel-Zyklus ≤ 1 s, Dashboard TTFD ≤ 2 s, ≤ 150 MB idle RSS, ≤ 2 % CPU idle auf Raspberry Pi 4 → enge Framework-Auswahl, keine Overhead-Bibliotheken
- Reliability: 24-h-Dauertest, 0 kritische Bugs, Wiederanlauf < 2 min, 14 Tage Lizenz-Grace → deterministische Safe-States, Persistenz-Disziplin
- Security & Privacy: 100 % lokal, SUPERVISOR_TOKEN-only, keine Telemetry → einzige externe Grenze = LemonSqueezy (monatlicher Online-Check)
- Maintainability: Ein Modul pro Device-Adapter, Solo-Dev-Kriterium „jedes Modul in ≤ 30 min nachvollziehbar"
- Scalability: ≥ 10 weitere Hersteller in v2–v3 ohne Core-Refactor (Adapter-Modul-Pattern als Erweiterungspunkt)

**Scale & Complexity:**

- Primär-Domain: Edge Orchestrator / IoT Embedded (HA Add-on)
- Komplexität: MITTEL–HOCH (Echtzeit-Regelung, Multi-Hardware, kommerziell, Fail-Safe) — reduziert gegenüber Vor-Amendment durch Streichung mehrerer architektonischer Schichten
- Geschätzte Architektur-Komponenten: ~6–8 Kernmodule (vorher ~8–12)

### Technical Constraints & Dependencies

Aus dem PRD bereits fixiert:

- Tech-Stack: Python 3.13 + FastAPI, Svelte 5 + Tailwind 4, SQLite
- Runtime: HA Add-on Base Image (Alpine 3.19), HA-Ingress, Supervisor-Token
- Distribution: Custom Add-on Repository (GitHub `alkly/solalex`), Multi-Arch-Build (amd64 + aarch64)
- Alleiniger Integrations-Kanal: HA WebSocket API (`ws://supervisor/core/websocket`)
- Externe Services: ausschließlich LemonSqueezy (Aktivierung + monatliche Re-Validation)
- Persistenz: `/data/`-Volume (SQLite, Lizenz, Backup, rotierte Logs)
- **Hardware-Day-1 (reduziert auf 3): Hoymiles/OpenDTU, Marstek Venus 3E/D, Shelly 3EM**
- Anker Solix + Generic HA Entity verschoben auf Beta-Week-6 / v1.5

### Cross-Cutting Concerns

1. **Closed-Loop-Readback + Fail-Safe** als durchgängiges Pattern für jeden Steuerbefehl
2. **Event-Source-Attribution** (`solalex | manual | ha_automation`) als Basis aller KPIs
3. **E2E-Latenz-Messung pro Device** als Input für hardware-spezifische Regel-Parameter
4. **EEPROM-Rate-Limiting** (≤ 1 Schreibbefehl/Device/Minute Default)
5. **Stdlib-Logging mit JSON-Formatter** (rotiert 10 MB / 5 Dateien)
6. **Lizenz-Gated Startup** via LemonSqueezy-Online-Check (keine kryptografische Signatur)
7. **Backup-Slot vor jedem Update** als Rollback-Mechanismus
8. **ALKLY-Design-System** (CSS-Token-basiert, Dark/Light-konform)

### Architektonische Spannungsfelder (entschieden)

| Spannungsfeld | Entscheidung |
|---|---|
| Regelungs-Engine: monolithisch vs. Pipeline | **Monolith mit Modi-Dispatch** (ein `controller.py`-Modul mit Enum-Dispatch + Hysterese) |
| Adapter-Tiefe | **Hardware-spezifische Python-Module** mit hardcoded Entity-Mappings (kein JSON-Template-Layer) |
| Frontend-Datenkontrakt | **REST + 1-s-Polling** als First-Shot; WS als v1.5-Upgrade falls UX das zwingt |
| Internes Messaging | **Direkte Funktionsaufrufe** (kein Event-Bus, kein Pub/Sub in Single-Process-App) |
| SQL-Layer | **Raw aiosqlite + handgeschriebene Queries** in `repositories/` (kein ORM) |
| Schema-Migration | **`schema_version`-Row + `sql/NNN_*.sql`-Upgrade-Liste** (kein Alembic) |
| Rollback-Semantik | **Backup-File-Replace** (kein Forward/Backward-Migrations-Pfad) |

### PRD-Rückwirkungen aus Amendment 2026-04-22

- **NFR15 (Lizenz-Signatur kryptografisch):** entfällt. Ersetzt durch LemonSqueezy-Online-Check.
- **NFR44 (Device-Template-System als JSON-Schema):** Formulierung entfällt. Erweiterungspunkt ist das Adapter-Modul-Pattern (`adapters/<vendor>.py`).
- **FR8/Hardware-Day-1:** auf 3 Hersteller gekürzt. Anker Solix + Generic HA Entity nach Beta-Week-6 / v1.5.
- **NFR49 (i18n-ready ab v1):** aufgeschoben. Deutsche Strings hardcoded, i18n-Refactor in v2 bei englischer Ergänzung.

## Starter Template Evaluation

### Primary Technology Domain

Edge Orchestrator / IoT Embedded als Home-Assistant-Add-on. Stack: Python 3.13 + FastAPI + SQLite (Backend), Svelte 5 + Vite + Tailwind 4 (Frontend als SPA), Multi-Arch Docker (amd64/aarch64), 100 % lokal, HA-Ingress-embedded, Supervisor-Token-only, DM Sans lokal als WOFF2.

### Starter Options Considered

| Option | Bewertung |
|---|---|
| `tiangolo/full-stack-fastapi-template` | Verworfen — Postgres + Traefik + K8s sind Cloud-first und widersprechen „100 % lokal + SQLite". |
| `buhodev/sveltekit-tailwind-starter` | Verworfen — SvelteKit ist SSR-orientiert, passt nicht zu HA-Ingress. |
| `home-assistant/addons-example` | Als Referenz adoptiert für `config.yaml`, `Dockerfile`, s6-overlay, `run.sh` mit bashio. |
| **Komponierter Solalex-Skeleton** | **Gewählt.** Zwei separate `init`-Commands (Backend + Frontend), kein Monorepo-Workspace-Root. |

### Selected Starter: Komponierter Solalex-Skeleton

**Rationale:**

Der Stack ist zu spezifisch (HA-Ingress + Multi-Arch + 100-%-lokal + Svelte-SPA in FastAPI-Static-Serve + DM-Sans-WOFF2), als dass ein Fremd-Starter passt. Die reale Boilerplate-Last ist einmalig ~3 Stunden.

**Initialisierungs-Sequenz (zwei Layer, kein Workspace-Root):**

```bash
# Repository-Wurzel als HA Custom Add-on Repo
# Manuell: repository.yaml + README + icon.png
# Vorlage: github.com/home-assistant/addons-example

# Backend (Python 3.13 + FastAPI)
cd backend/
uv init --python 3.13
uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite httpx pydantic-settings
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy

# Frontend (Svelte 5 + Vite + Tailwind 4)
cd frontend/
npm create vite@latest . -- --template svelte-ts
npm i -D tailwindcss @tailwindcss/vite
npm i svelte-spa-router
# + DM Sans WOFF2 manuell unter frontend/static/fonts/
# + OFL.txt neben den Font-Files für Lizenz-Compliance
```

**Verifizierte Aktuelle Versionen (Stand April 2026):**

| Komponente | Version | Quelle |
|---|---|---|
| Python | 3.13 | FastAPI-empfohlen |
| FastAPI | aktuelle stable | PyPI (Version beim Bootstrap fixieren, im Readme dokumentieren) |
| uv | 0.5+ | Astral, Alpine/musl-arm64 stabil |
| Svelte | 5 (stabil) | aktuelle Major |
| Vite | 7.x | aktuelle Major |
| Tailwind CSS | 4 (stabil) | `@tailwindcss/vite` Plugin |
| HA Add-on Base Image | `ghcr.io/home-assistant/{arch}-base-python:3.13-alpine3.19` | Multi-Arch (amd64/arm64) |
| s6-overlay + bashio | im HA-Base enthalten | Nicht separat installieren |

**Hinweis:** Konkrete Versions-Hashes werden beim Bootstrap (Story 1.1) in `pyproject.toml`/`package.json` gepinnt und in der README dokumentiert. Node-Version via `.nvmrc`, Python-Version via `pyproject.toml#requires-python` + `.python-version`.

### Architectural Decisions Provided by Starter

**Language & Runtime:**

- Backend: Python 3.13, FastAPI, uvicorn (ASGI), aiosqlite (async SQLite, raw SQL)
- Frontend: TypeScript, Svelte 5 (Runes), Vite 7 (Build + HMR)
- Single-Source-of-Truth für Python-Deps: `backend/pyproject.toml` + `backend/uv.lock`
- Node-Lockfile: `frontend/package-lock.json` committed
- **Kein Monorepo-Workspace-Root.** Backend und Frontend haben eigenständige Package-Manager-Umgebungen.

**Styling Solution:**

- Tailwind CSS v4 über `@tailwindcss/vite` Plugin
- ALKLY-Design-Tokens als **CSS Custom Properties (Single-Source)** in `frontend/src/app.css`
- DM Sans lokal als WOFF2 im Container unter `frontend/static/fonts/` (inkl. `OFL.txt`)
- **Light-only Token-Layer** in v1 — kein Dark-Mode-Override, keine HA-Theme-Adaption *(Amendment 2026-04-23: Dark-Mode gestrichen)*
- **Keine TypeScript-Token-Duplikate** (`frontend/src/lib/tokens/*.ts` entfällt)

**Build Tooling:**

- Vite 7 als Frontend-Bundler → `frontend/dist/` als statisches Bundle
- **2-Stage-Dockerfile:** Stage 1 `frontend-builder` (Node, baut `dist/` hermetisch aus Source), Stage 2 `backend-runtime` (HA Base-Python) kopiert das Bundle ins Static-Verzeichnis
- FastAPI serviert die SPA unter HA-Ingress-URL (keine separate Node-Runtime im Prozess)
- Multi-Arch-Build via `docker buildx` + GitHub Actions (amd64 + aarch64)
- **Multi-Arch bleibt drin** — Zielhardware deckt beide Architekturen ab

**Testing Framework:**

- Backend: `pytest` + `pytest-asyncio` + `pytest-cov`
- Frontend: `vitest` für Unit-Tests
- **Playwright / E2E-Folder erst post-MVP** — Manual-QA-Checklist + Beta-Tester als v1-E2E
- Mock-HA-WebSocket für Adapter-Integration-Tests

**Linting / Formatting:**

- Python: `ruff` (Lint + Format) + `mypy` (Type-Check)
- TS/Svelte: `eslint` + `prettier` + `svelte-check`

**Code Organization (ohne Monorepo-Workspace-Root):**

```
solalex/
├── addon/              # HA Add-on Definition
│   ├── config.yaml
│   ├── Dockerfile      # Multi-Stage: frontend-build + backend-assemble
│   ├── run.sh          # Entry-Point mit bashio
│   └── rootfs/
├── backend/            # Python 3.13 + FastAPI (eigenständig)
│   ├── pyproject.toml  # uv-managed
│   ├── uv.lock
│   ├── src/solalex/
│   └── tests/
├── frontend/           # Svelte 5 + Vite + Tailwind 4 (eigenständig)
│   ├── package.json
│   ├── src/
│   └── static/fonts/   # DM Sans WOFF2 + OFL.txt
├── repository.yaml
├── .github/workflows/
└── README.md
```

**Rationale Ein-Repo-ohne-Workspace-Root:** Ein Release-Artefakt (das Add-on-Image), ein Changelog, atomic commits bei API↔Frontend-Contract-Änderungen. CI-Pipeline macht `cd backend && …` bzw. `cd frontend && …`. Kein uv-Workspace, kein Root-`package.json` — halbiert die Dual-Package-Manager-Komplexität ohne Funktionalitätsverlust.

**Development Experience:**

- Vite HMR für Frontend (Svelte-Reaktivität sofort sichtbar)
- `uvicorn --reload` für Backend-Entwicklung
- Svelte-DevTools-Extension + Vite-Svelte-Inspector
- GitHub Actions CI: Ruff + Mypy + Pytest + Frontend-Build + Multi-Arch-Docker-Build
- uv ist 10–100× schneller als pip/poetry beim Resolve → spart bei Multi-Arch-Builds 2–4 Minuten pro Build

### Vertagte Entscheidungen (für spätere Versionen)

- **WebSocket-Upgrade-Pfad** (v1.5 wenn UX-Latenz des 1-s-Pollings beißt): Endpoint-Skelett vorbereiten, aber nicht in v1 implementieren
- **numpy/pandas:** nicht im MVP; Base bleibt Alpine. Bei späterer Forecast/Optimization-Integration → Wechsel zu `python:3.13-slim` als einfache Dockerfile-Änderung
- **Anker Solix + Generic Adapter:** Beta-Week-6 / v1.5
- **i18n-Infrastruktur + englische Lokalisierung:** v2

**Note:** Projekt-Initialisierung mittels der oben dokumentierten `init`-Commands ist die erste Implementation-Story (Epic 1 / Story 1.1 Bootstrap).

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- **Frontend-Datenkontrakt: REST + 1-s-Polling** (kein WS in v1). Dashboard-TTFD ≤ 2 s wird über initiales Bulk-GET + Client-Side-Cache erreicht; Live-Updates via 1-s-Polling auf `/api/v1/control/state` und `/api/v1/kpi/live`.
- **Data-Persistence-Stack: Raw `aiosqlite` + handgeschriebene Queries** in `repositories/`. WAL-Mode aktiv, `synchronous=NORMAL`.
- **Schema-Migration: `schema_version`-Row + `sql/NNN_*.sql`-Upgrade-Liste** (kein Alembic).
- **Rollback: Backup-File-Replace** via `VACUUM INTO .tmp → fsync → rename → fsync(dir)` vor jedem Update; bei Rollback manueller File-Replace durch alten Add-on-Build.
- **Lizenz-Validierung:** LemonSqueezy-Online-Check mit Key in `/data/license.json`. **Keine kryptografische Signatur** (Ed25519 gestrichen). 14-Tage-Grace, danach Funktions-Drossel.
- **Egress-Whitelist:** nur `*.lemonsqueezy.com` — httpx-Client mit Allowlist-Enforcement + CI-Mock-Test.

**Important Decisions (Shape Architecture):**

- **Interner Control-Flow:** direkter Funktionsaufruf (`controller.on_sensor_update(…)` → `kpi.record(…)` + `ws_state_cache.update(…)`). **Kein asyncio.Queue-Event-Bus**, **kein Pub/Sub-Dispatch**.
- **Controller-Monolith:** ein `controller.py`-Modul mit Enum-Dispatch (`Mode.DROSSEL | SPEICHER | MULTI`) + Hysterese-Helper + Fail-Safe-Wrapper. Kein 6-fach-Split in Submodule.
- **Adapter-Modul-Pattern:** ein Python-Modul pro Hersteller (`adapters/hoymiles.py`, `adapters/marstek_venus.py`, `adapters/shelly_3em.py`) mit hardcoded Entity-Mappings als Python-Dicts. **Kein JSON-Template-Loader, kein JSON-Schema-Validator.**
- **Rollup-Tabellen** für KPI-Aggregation (Dashboard-TTFD ≤ 2 s)
- **Svelte 5 Runes primär** + Svelte-Stores für Cross-View-Subscriptions (Theme, License-Status, gepollter State-Snapshot)
- **Hash-basiertes Routing** via `svelte-spa-router` (Ingress-URL-agnostisch)
- **TypeScript-Types handgeschrieben** neben `client.ts` (kein `openapi-typescript`-Generator-Pipeline, kein OpenAPI-Diff-CI-Gate)
- **Scheduling via asyncio-Task** (`while True: await sleep_until(next_0005); rollup()`), kein APScheduler
- **Logging via stdlib `logging` + JSON-Formatter** + `RotatingFileHandler`, kein structlog

**Deferred Decisions (Post-MVP):**

- WebSocket-Live-Stream-Upgrade (v1.5 wenn Polling-Latenz beißt)
- MQTT-Discovery (v1.5)
- SetpointProvider-Konkrete-Implementierung (v2 Forecast)
- Multi-WR / SoC-Balance (v2)
- Kaskaden-Modell (v2)
- i18n-Mechanik (v2 Englisch)
- Anker Solix + Generic-Adapter (Beta-Week-6 / v1.5)
- Kryptografische Lizenz-Signatur (v1.5 falls Anti-Tamper relevant)

### Data Architecture

**Driver:** Raw `aiosqlite` + handgeschriebene SQL-Queries in `backend/src/solalex/persistence/repositories/*.py`. Kein ORM, keine Mapped-Models. Für ~9 Tabellen mit je ≤10 Spalten ist ein ORM reine Overhead. AI-Tooling (Claude Code) schreibt korrektes SQL zuverlässiger als korrekte SQLAlchemy-Session-Lifecycles.

**Migration-Tool:** `schema_version`-Row in `meta`-Tabelle + sequentielle `sql/NNN_*.sql`-Upgrade-Blöcke. Beim Startup: aktuelle Version lesen, alle höher-nummerierten SQL-Dateien in Transaktion anwenden, `schema_version` hochzählen. ~30 Zeilen in `persistence/migrate.py`. **Kein Alembic**, keine Forward/Backward-Pflicht.

**Kern-Schema (Tabellen):**

| Tabelle | Zweck |
|---|---|
| `devices` | Konfigurierte HA-Entities + Adapter-Zuordnung |
| `control_cycles` | Ringpuffer Regelzyklen (FR31 — 100 Zeilen oder ~1 h, was größer ist) |
| `events` | Ringpuffer letzte 20 Fehler/Warnungen (FR32) |
| `latency_measurements` | Pro-Device E2E-Latenz-Rohdaten (FR34), 30-Tage-Retention |
| `kpi_daily` | Rollup pro Tag (kWh selbst verbraucht, selbst gesteuert, Euro-Wert) |
| `kpi_monthly` | Rollup pro Monat (Stats-Tab-Basis) |
| `license_state` | Lizenz-Key, letzte Validierung, Grace-Counter, Disclaimer-Accepted |
| `meta` | `schema_version` + andere Key-Value-Metadaten (Bezugspreis-Default, etc.) |

**KPI-Aggregation:** Rollup-Tabellen + materialisierte Tages-/Monatsaggregate via asyncio-Task (00:05 lokale Zeit). Rollup-Cost ca. 4 KB/Tag. Live-`SUM` über 30 Tage wäre am Pi-4-Budget.

**WAL-Mode + Backup:** `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`. Backup-Semantik:

```python
# in backup/snapshot.py
await conn.execute("VACUUM INTO '/data/.backup/solalex.db.tmp'")
os.fsync(tmp_fd)
os.rename('/data/.backup/solalex.db.tmp', '/data/.backup/solalex.db')
os.fsync(dir_fd)  # fsync auf das Verzeichnis, damit rename persistiert
```

**Nur ein Backup-Slot.** HA hat native System-Snapshots. Der Add-on braucht genau ein „letzter Backup vor Update"-File, keine Rotation-of-5.

**Rollback-Semantik:**

1. Vor jedem Update wird `.backup/solalex.db` geschrieben (Sequenz oben).
2. Bei fehlgeschlagenem Update → User installiert über HA Add-on Store die vorherige Version.
3. Beim Start der alten Version prüft `run.sh`: Wenn `schema_version` in `/data/solalex.db` > der alten Version erwartet → automatisches Überschreiben aus `.backup/solalex.db`.
4. Das Backup-Schema matcht die zugehörige Add-on-Version automatisch. **Kein Forward/Backward-Migrations-Pfad nötig.**

**Retention:** 
- `control_cycles`: Ringpuffer mit `ORDER BY id DESC LIMIT N` + Nightly `DELETE`. N = größer von {100 Zyklen, 3600 Einträge der letzten Stunde}, damit Diagnose-Analyse nach Incident aussagekräftig bleibt.
- `latency_measurements`: 30 Tage.
- `kpi_daily`/`kpi_monthly`: unbegrenzt (Speicher vernachlässigbar).
- `events`: letzte 20 Einträge.

### Authentication & Security

**Lizenz-Validierung:** Lizenz-Key in `/data/license.json` als Plain-JSON:

```json
{
  "license_key": "ABCDEF-12345678-...",
  "customer_email": "user@example.com",
  "activated_at": "2026-04-22T10:00:00Z",
  "last_validated_at": "2026-05-22T10:00:00Z",
  "grace_counter_days": 0,
  "disclaimer_accepted_at": "2026-04-22T09:55:00Z"
}
```

**Keine kryptografische Signatur** (Amendment 2026-04-22). Die 14-Tage-Grace macht Offline-Crack ohnehin trivial; Ed25519 + Baked-in-Public-Key hätte diesen Angriffsvektor nicht wirksam geschlossen und kostete Dependency (`cryptography`), Key-Rotation-Gap und Build-Pipeline-Komplexität.

**LemonSqueezy-Integration:** HTTPS-only. Monatliche `POST /v1/licenses/validate` (aktuelle LemonSqueezy-API-Form) mit `license_key`. Re-Validation-Failures → `grace_counter_days` hochzählen; bei 14 Tagen Funktions-Drossel aktivieren mit sichtbarem Banner, Regelung pausiert, Dashboard bleibt Read-only lesbar.

**Egress-Whitelist:** Harter Code-Audit + CI-Test. Einziger ausgehender HTTP-Endpunkt = `*.lemonsqueezy.com`. Der httpx-Client wird mit einem Transport-Hook versehen, der alle anderen Hosts blockt. CI-Test schickt Request zu `example.com` und erwartet `BlockedHostError`.

**Disclaimer-Checkbox:** Vor Lizenz-Aktivierung im Wizard. Persistenz in `license_state.disclaimer_accepted_at`. Zusätzlich optional in LemonSqueezy-Order-Custom-Field als Audit-Trail-Spiegel (v1.5).

**CSRF / CORS:** FastAPI default `same-origin`. HA-Ingress-Proxy liefert `X-Ingress-Path`-Header. Kein CORS-Middleware nötig, kein CSRF-Token-Layer.

**Response-Security-Header:** Middleware setzt `Content-Security-Policy` (kein external fetch, nur `self`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`. Stützt NFR19 („100 % lokal") auf Runtime-Ebene.

**Supervisor-Token-Handling:** Aus Env-Var `SUPERVISOR_TOKEN` beim Container-Start, in Memory halten, nicht persistieren. Bei Ablauf (Supervisor-Rotation) → Reconnect-Flow neu triggern.

### API & Communication Patterns

**REST + 1-s-Polling (First-Shot, v1):**

| Kanal | Use-Case |
|---|---|
| **REST** (FastAPI-HTTP-Endpunkte) | Alles: Wizard, Device-CRUD, Bezugspreis, Funktionstest, KPI-Read, Diagnose-Export, Lizenz, Backup/Restore-Actions, Live-State-Read |
| **Client-seitiges Polling** | Dashboard pollt `/api/v1/control/state` und `/api/v1/kpi/live` im 1-s-Takt für Energy-Ring, Flow-Animation-Daten-Basis, Modus-Chip, Idle-State |

**Begründung:** Flow-Animation läuft clientseitig aus dem letzten Frame (Partikel-Interpolation zwischen Sensor-Ticks). 1-s-Polling deckt NFR2 (Dashboard-TTFD ≤ 2 s) und erfüllt NFR26 (Design-Quality) ohne WS-Infrastruktur. **Upgrade auf WebSocket ist ein sauberer v1.5-Pfad**, wenn Beta-Feedback zeigt, dass Polling-Latenz die Wahrnehmung beschädigt. Bis dahin entfallen: `ws/endpoint.py`, Dispatcher, Subscription-Registry, Reconnect-Client, WS-Event-Versionierung, Transition-Windows.

**API-Design:** REST nach RFC 7807 (Problem Details für Fehler), OpenAPI 3.1 via FastAPI-Autogenerierung (nur für Debugging/Swagger-UI, keine Generator-Pipeline).

**TS-Client:** Handgeschriebene TS-Types in `frontend/src/lib/api/types.ts` + dünner `fetch`-Wrapper in `frontend/src/lib/api/client.ts` (~40 Zeilen). Pydantic bleibt Backend-Source-of-Truth; Drift fängt Alex im selben PR. **Kein `openapi-typescript`-Generator, kein CI-Drift-Check.**

**Error-Format:** RFC 7807 `application/problem+json`. FastAPI-Middleware konvertiert Exceptions einheitlich.

**Interner Control-Flow (Backend):** Direkter Funktionsaufruf statt Pub/Sub.

```python
# controller/core.py
async def on_sensor_update(self, event: SensorEvent) -> None:
    cycle = await self._compute_cycle(event)
    await self._executor.dispatch(cycle)
    await kpi.record(cycle)          # direkter Aufruf
    state_cache.update(cycle)         # direkter Aufruf (für Polling-Endpoint)
```

**Kein asyncio.Queue-Event-Bus**, **kein Subscription-Dispatch**, **kein `events/bus.py`**. Ein Publisher + zwei Consumer = Funktionsaufruf mit zwei Callees.

**HA-WebSocket-Reconnect:** Exponential Backoff 1 s → 2 s → 4 s → max 30 s, persistente Subscription-Liste, Re-Subscribe nach Reconnect (PRD-fixiert, bleibt zum HA-Upstream).

### Frontend Architecture

**State-Management:** 
- Svelte 5 Runes (`$state`, `$derived`, `$effect`) primär innerhalb Komponenten
- Svelte-Stores (`writable`) nur für Cross-View-Subscriptions:
  - `stateSnapshot` — gepollter `/api/v1/control/state`-Snapshot (1-s-Takt)
  - `license` — aktives Feature-Gating (grace/valid/drosseled)
- **Kein WebSocket-Stream-Store** (WS ist nicht in v1).

**Routing:** `svelte-spa-router` (Hash-basiert). Falls Integration mit Svelte 5 Runes Probleme macht, Fallback auf manuelles Conditional-Rendering auf Basis von `window.location.hash` — ~30 Zeilen.

**API-Layer:** `frontend/src/lib/api/` = handgeschriebene Types + `fetch`-Wrapper mit einheitlichem Error-Handling (RFC 7807 → Svelte-Toast-Message).

**Polling-Layer:** `frontend/src/lib/polling/` mit generischem Hook:

```ts
function usePolling<T>(url: string, intervalMs: number): Readable<T | null> { ... }
```

Der `stateSnapshot`-Store nutzt diesen Hook im Dashboard-Scope; Wizard und Diagnose-Views benutzen normale One-Shot-Fetches.

**Design-Token-Layer:** Tailwind 4 Config + **CSS Custom Properties als Single-Source** in `frontend/src/app.css`. ALKLY-Tokens (`--color-accent-primary`, `--font-sans`, `--radius-card`, …) ausschließlich in `:root`. **Kein `[data-theme="dark"]`-Override in v1, kein HA-Theme-Signal-Subscriber** *(Amendment 2026-04-23: Dark-Mode gestrichen)*.

**Kein `lib/tokens/*.ts`.** Keine TypeScript-Duplikation der Tokens. Komponenten referenzieren Tokens über Tailwind-Klassen oder `var(--...)` direkt.

**Font-Pipeline:** DM Sans WOFF2 (Regular/Medium/Semibold/Bold, Latin + Latin-Extended, ~120 kB) unter `frontend/static/fonts/`. `frontend/static/fonts/OFL.txt` als Lizenz-Notice-Compliance.

### Infrastructure & Deployment

**CI/CD:** GitHub Actions. Pipeline:
1. Lint (ruff + mypy + eslint + svelte-check)
2. Tests (pytest + vitest)
3. Egress-Whitelist-Test (Mock-HTTP, erwartet `BlockedHostError` für Nicht-LemonSqueezy-Hosts)
4. Frontend-Build (Vite → `frontend/dist/`)
5. **Multi-Arch-Docker-Build** (`docker buildx` für amd64 + aarch64, QEMU für arm64)
6. GHCR-Push
7. Release-Tag triggert Add-on-Store-Publish

**Release-Pattern:** Semver-Tags (`vX.Y.Z`). Pre-Release-Tags (`v1.0.0-beta.1`) für Beta-Tester. `CHANGELOG.md`-Check im CI (PR ohne Changelog-Eintrag → fail).

**Logging:** stdlib `logging` + `JSONFormatter` (~30 Zeilen in `common/logging.py`) + `RotatingFileHandler` (10 MB / 5 Files) unter `/data/logs/` (NFR36). Alle Exceptions mit Kontext. Add-on-Log-Panel zeigt stdout zusätzlich.

**Kein `structlog`, keine Correlation-IDs.** Ein Prozess, ein Kontext. Bei späterer Notwendigkeit (v2 Multi-Instance?) ist der Wechsel zu structlog ein mechanisches Refactor.

**Observability:** Add-on-Log-Panel (Standard) + Diagnose-Export als JSON (`solalex-diag_<timestamp>.json`, FR35) + optional Health-Endpoint `/api/health` für HA-Binary-Sensor-Integration. Zero Telemetry (NFR17).

**Rollback:** Siehe Data Architecture — Backup-File-Replace beim Start der vorherigen Version. Add-on-Store-Manual-Downgrade als User-Action.

**Scheduler:** asyncio-Task im FastAPI-Lifespan:

```python
# kpi/scheduler.py
async def nightly_loop(app: FastAPI):
    while True:
        await sleep_until_next("00:05")
        await rollup.run()

async def monthly_license_loop(app: FastAPI):
    while True:
        await sleep_until_monthly(day=1, hour=3)
        await license.revalidate()
```

Beide in `main.py` als `asyncio.create_task` im `lifespan`-Context. Uvicorn-Worker-Count: **genau 1** (im `run.sh` dokumentiert und gepinnt). Kein APScheduler.

**Rate-Limiter-Persistenz:** `executor/rate_limiter.py` persistiert letzten Write-Timestamp pro Device in SQLite (`devices.last_write_at`). Startup-Policy: beim Boot ersten Write pro Device erst nach `last_write_at + 60s` freigeben, um EEPROM-Schutz über Restart hinweg einzuhalten.

### Decision Impact Analysis

**Implementation Sequence (Dependency-optimiert):**

1. **Bootstrap** (Story 1.1) — `backend/` + `frontend/` Init, `addon/config.yaml`, Dockerfile, Multi-Arch-GHA-Workflow
2. **Schema v0 + WAL-Mode + Backup-Slot** — erste `sql/001_initial.sql`, `schema_version`-Logik
3. **HA-WebSocket-Adapter** (`backend/src/solalex/ha_client.py`) — Subscribe + Exponential-Backoff-Reconnect zum HA-Upstream
4. **Adapter-Module für 3 Day-1-Hersteller** — `adapters/hoymiles.py`, `adapters/marstek_venus.py`, `adapters/shelly_3em.py` mit hardcoded Entity-Mappings
5. **Controller + Executor + Rate-Limiter** — ein Controller-Modul mit Enum-Dispatch; Executor mit Readback + Rate-Limit + Fail-Safe
6. **Setup-Wizard-REST-API + Frontend-Wizard-Views (4 Schritte)**
7. **Dashboard-REST + 1-s-Polling + Energy-Ring + Euro-Hero + Flow-Animation**
8. **LemonSqueezy-Integration + Disclaimer-Checkbox + Grace-Counter**
9. **Diagnose-Tab + Latency-Measurement-Visualisierung + Export**
10. **Update/Backup/Rollback** (Epic 6) — `VACUUM INTO`-Backup + Add-on-Store-Downgrade + Auto-Restore on Start

**Cross-Component Dependencies:**

- **DB-Schema ↔ Alle Epics:** Jede persistierende Story braucht `sql/NNN_*.sql`-Migration. Forward-only. Bei Breaking-Change = Backup-File aus vorheriger Version beim Rollback.
- **Adapter-Module ↔ Core-Controller:** Adapter exportieren reine Funktionen (`build_set_limit_command(device, watts) -> HaServiceCall`, `parse_readback(state) -> int | None`). Core kennt nur die Abstract-Schnittstelle aus `adapters/base.py`.
- **Egress-Whitelist ↔ CI-Test:** Jeder neue Outbound-HTTP-Call ohne Whitelist-Eintrag → CI-Fail.
- **Polling-Endpoint ↔ Frontend-Store:** `/api/v1/control/state` liefert ein einziges konsolidiertes JSON (aktueller Modus, letzte Zyklus-Metriken, Live-Sensor-Werte). Frontend pollt im 1-s-Takt. Response-Shape ist dokumentiert in `api/schemas/state.py` (Pydantic) — Änderungen erfordern Parallel-Update der handgeschriebenen TS-Types.

## Implementation Patterns & Consistency Rules

### 5 harte Regeln (reduziert von 10 MUST + 14 Kategorien)

Jede Implementierung (AI-Agent oder manuell) MUSS:

1. **snake_case überall** (DB, Python, API-JSON, URLs) — einziger Case im System
2. **Ein Modul pro Adapter** in `adapters/` (NFR34/NFR44 — architektonischer Extension-Point)
3. **Closed-Loop-Readback für jeden Write-Command** im Executor (non-verhandelbar, Safety)
4. **JSON-Responses ohne Wrapper** — direktes Objekt, kein `{data: ..., error: ...}`-Hüllenformat. Fehler via RFC 7807.
5. **Logging via `get_logger(__name__)`-Wrapper** aus `common/logging.py`, nie `print()`, nie direct `logging.info()` ohne Wrapper-Binding

Der Rest wird durch Code-Beispiele und Reviews etabliert, nicht durch zusätzliche Lint-Regeln oder CI-Gates.

### CI-Enforcement (reduziert)

- Ruff + MyPy strict + pytest (Backend)
- ESLint + svelte-check + prettier + vitest (Frontend)
- Egress-Whitelist-Test: httpx-Mock blockt alles außer `*.lemonsqueezy.com`
- `sql/NNN_*.sql`-Ordnungs-Check: alle Files nummerisch sortiert, keine Lücken

**Entfallen gegenüber altem Stand:** OpenAPI-Schema-Diff-Check (keine Generator-Pipeline), Alembic-Head-Check (kein Alembic), 14 Pattern-Kategorien, 10 MUST-Regeln.

### Naming & Format

**Database:**
- Tabellen: `snake_case`, plural (`devices`, `control_cycles`)
- Spalten: `snake_case`
- Primary Keys: `id` (INTEGER AUTOINCREMENT)
- Timestamps: `created_at`, `updated_at` als UTC TIMESTAMP

**Python:**
- Files: `snake_case.py` singular
- Functions/Variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

**Svelte / TypeScript:**
- Components: `PascalCase.svelte`
- Non-Component-Files: `camelCase.ts`
- Functions/Variables: `camelCase`
- Types: `PascalCase`
- Stores: `camelCase` mit `$`-Convention

**API Endpoints:**
- Plural, kebab-case: `/api/v1/devices`, `/api/v1/control-cycles`
- Versionierung: `/api/v1/...`
- Route-Params: `{device_id}` (FastAPI-Style)
- Query-Params: `snake_case`

**JSON-Field-Case:** `snake_case` end-to-end. Kein Boundary-Transform.

**Date/Time:**
- Storage/API: ISO-8601 UTC mit `Z`-Suffix
- Intern (Python): `datetime` mit `tzinfo=UTC`
- UI: lokale Zeit nur in der Render-Schicht via `Intl.DateTimeFormat('de-DE')`

**Null-Handling:** Expliziter `null`-Value statt fehlendes Feld. Pydantic `Optional[...]` · TS `T | null`.

### Pattern Examples

**Gut (DB):**

```python
# persistence/repositories/control_cycles.py
async def insert_cycle(conn: aiosqlite.Connection, cycle: ControlCycle) -> int:
    cursor = await conn.execute(
        """
        INSERT INTO control_cycles
          (device_id, created_at, limit_set_w, readback_w, latency_ms, event_source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (cycle.device_id, cycle.created_at, cycle.limit_set_w,
         cycle.readback_w, cycle.latency_ms, cycle.event_source),
    )
    await conn.commit()
    return cursor.lastrowid
```

**Anti (DB):**

```python
# ORM-Overhead für 9-Tabellen-Schema
class ControlCycle(Base):  # KEIN ORM in v1
    __tablename__ = "control_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    ...
```

**Gut (API-Response auf `/api/v1/devices/42`):**

```json
{ "id": 42, "type": "hoymiles", "entity": "number.opendtu_limit_nonpersistent_absolute" }
```

**Anti (API-Response):**

```json
{ "data": { "deviceId": 42, "deviceType": "hoymiles" }, "success": true }
```

**Gut (Interner Control-Flow):**

```python
async def on_sensor_update(self, event: SensorEvent) -> None:
    cycle = await self._compute_cycle(event)
    await self._executor.dispatch(cycle)
    await kpi.record(cycle)         # direkt
    state_cache.update(cycle)        # direkt
```

**Anti (Event-Bus für Single-Process):**

```python
# KEIN Event-Bus in v1
bus.publish(CycleComplete(...))   # Overengineered
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
solalex/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CLAUDE.md                         # 5-Regel-Kanon für AI-Agents (siehe Amendment)
├── repository.yaml                   # Custom Add-on Repo Manifest
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml           # ruff + eslint + prettier
├── .github/
│   ├── workflows/
│   │   ├── build.yml                 # Multi-Arch Docker, Lint, Test, Publish
│   │   ├── pr-check.yml              # Lint + Test on PR
│   │   └── release.yml               # Tag → Add-on-Store-Publish
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug-report.yml
│   │   └── feature-request.yml
│   └── pull_request_template.md
│
├── addon/                            # HA Add-on Definition
│   ├── config.yaml
│   ├── Dockerfile                    # Multi-Stage: frontend-build + backend-assemble
│   ├── run.sh                        # Entry-Point mit bashio (auto-restore on start)
│   ├── CHANGELOG.md
│   ├── DOCS.md
│   ├── README.md
│   ├── icon.png
│   ├── logo.png
│   └── rootfs/
│       └── etc/services.d/solalex/
│           ├── run
│           └── finish
│
├── backend/                          # Eigenständiges uv-Projekt
│   ├── pyproject.toml                # uv-managed, requires-python = "3.13"
│   ├── .python-version
│   ├── uv.lock
│   ├── src/solalex/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI-Entry + Lifespan-Tasks
│   │   ├── config.py                 # pydantic-settings
│   │   ├── startup.py                # Init-Order: DB-Migrate → HA-Connect → Controller
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py         # /api/health
│   │   │   │   ├── setup.py          # Epic 2 — 4-Schritt-Wizard
│   │   │   │   ├── devices.py
│   │   │   │   ├── control.py        # /api/v1/control/state — Polling-Endpoint
│   │   │   │   ├── pricing.py
│   │   │   │   ├── kpi.py
│   │   │   │   ├── diagnose.py
│   │   │   │   ├── license.py
│   │   │   │   └── backup.py
│   │   │   ├── schemas/              # pydantic request/response models
│   │   │   └── middleware.py         # Exception-Handler, License-Gate, Security-Headers
│   │   ├── ha_client/
│   │   │   ├── client.py             # HA-WS-Client (auth, subscribe, call_service)
│   │   │   ├── reconnect.py
│   │   │   └── types.py
│   │   ├── controller.py             # EIN Modul: Enum-Dispatch + Hysterese + Fail-Safe
│   │   ├── executor/
│   │   │   ├── dispatcher.py         # Command-Dispatch
│   │   │   ├── readback.py           # Closed-Loop-Verifikation
│   │   │   └── rate_limiter.py       # EEPROM-Schutz (FR19), persistent
│   │   ├── adapters/                 # NFR34 — ein Modul pro Hersteller
│   │   │   ├── base.py               # Abstract Adapter-Interface (Signaturen, Timing-Semantik)
│   │   │   ├── hoymiles.py
│   │   │   ├── marstek_venus.py
│   │   │   └── shelly_3em.py
│   │   │   # anker_solix.py + generic.py: Beta-Week-6 / v1.5
│   │   ├── persistence/
│   │   │   ├── db.py                 # aiosqlite-Connection-Factory, WAL-Mode
│   │   │   ├── migrate.py            # schema_version + sql/-Apply-Loop
│   │   │   ├── sql/
│   │   │   │   └── 001_initial.sql
│   │   │   └── repositories/
│   │   │       ├── devices.py
│   │   │       ├── control_cycles.py
│   │   │       ├── events.py
│   │   │       ├── latency.py
│   │   │       ├── kpi.py
│   │   │       ├── license.py
│   │   │       └── meta.py
│   │   ├── license/
│   │   │   ├── lemonsqueezy.py       # Validate + Re-Validate
│   │   │   └── grace.py              # 14-Tage-Grace-Counter
│   │   ├── kpi/
│   │   │   ├── attribution.py        # FR27 — Event-Source-Regel
│   │   │   ├── rollup.py             # Nightly-Aggregation
│   │   │   ├── calculator.py         # Euro-Wert-Berechnung
│   │   │   └── scheduler.py          # asyncio-Task (Nightly + Monthly)
│   │   ├── diagnose/
│   │   │   ├── export.py             # Story 4.5 — unversioniertes JSON
│   │   │   └── analysis.py           # Story 4.4 — Latency-Stats
│   │   ├── backup/
│   │   │   ├── snapshot.py           # VACUUM INTO → fsync → rename → fsync(dir)
│   │   │   └── restore.py            # Auto-Restore beim Start, wenn schema_version-Mismatch
│   │   ├── state_cache.py            # In-Memory-Cache für Polling-Endpoint
│   │   └── common/
│   │       ├── logging.py            # stdlib logging + JSONFormatter (~30 Zeilen)
│   │       ├── clock.py              # UTC-Wrapper, monotonic, sleep_until
│   │       ├── ids.py                # UUID, IDs
│   │       └── types.py              # Shared Type Aliases
│   └── tests/
│       ├── unit/                     # Mirror of src/
│       ├── integration/
│       │   ├── mock_ha_ws/
│       │   └── test_e2e_flow.py
│       └── conftest.py
│
├── frontend/                         # Eigenständiges npm-Projekt
│   ├── package.json
│   ├── package-lock.json
│   ├── .nvmrc                        # Node-Version pinning
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── index.html
│   ├── src/
│   │   ├── app.css                   # Tailwind + ALKLY-Tokens (CSS Custom Properties, Single-Source)
│   │   ├── main.ts
│   │   ├── App.svelte                # Root + svelte-spa-router
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── client.ts         # fetch-Wrapper
│   │   │   │   ├── types.ts          # handgeschriebene TS-Types
│   │   │   │   └── errors.ts         # RFC 7807 handling
│   │   │   ├── polling/
│   │   │   │   └── usePolling.ts     # Generic 1-s-Polling-Hook
│   │   │   ├── stores/
│   │   │   │   ├── stateSnapshot.ts  # Gepollter Control-State
│   │   │   │   ├── theme.ts
│   │   │   │   └── license.ts
│   │   │   ├── components/
│   │   │   │   ├── primitives/       # Button, Card, Input, Stepper
│   │   │   │   ├── layout/           # Shell, Nav, Footer
│   │   │   │   ├── charts/           # EnergyRing, FlowAnimation, LineChart
│   │   │   │   ├── dashboard/        # EuroHero, ModeBadge, IdleState, CharacterLine
│   │   │   │   ├── wizard/           # WizardStep, SensorLiveValue, FunctionalTestDramatik
│   │   │   │   └── diagnose/        # CycleTable, ErrorList, ConnectionStatus
│   │   │   └── utils/
│   │   │       ├── format.ts
│   │   │       ├── time.ts
│   │   │       └── a11y.ts
│   │   └── routes/
│   │       ├── Dashboard.svelte
│   │       ├── Wizard/
│   │       │   ├── index.svelte
│   │       │   ├── Step1Hardware.svelte       # Hardware-Auswahl
│   │       │   ├── Step2Detection.svelte      # Auto-Detection + Smart-Meter + Battery (Sub-Cards)
│   │       │   ├── Step3FunctionalTest.svelte # Funktionstest mit Live-Chart
│   │       │   └── Step4Activation.svelte     # Disclaimer + LemonSqueezy + Aktivieren
│   │       ├── Diagnose.svelte
│   │       ├── Stats.svelte
│   │       └── Settings.svelte
│   ├── static/
│   │   ├── fonts/                    # DM Sans WOFF2 + OFL.txt
│   │   │   ├── DMSans-Regular.woff2
│   │   │   ├── DMSans-Medium.woff2
│   │   │   ├── DMSans-SemiBold.woff2
│   │   │   ├── DMSans-Bold.woff2
│   │   │   └── OFL.txt
│   │   └── icons/                    # Custom PV-Ikonographie
│   └── dist/                         # Build-Output (gitignored)
│
└── docs/
    ├── architecture.md               # Copy/Symlink aus _bmad-output/
    ├── api.md
    └── development.md
```

### Architectural Boundaries

**API Boundaries (einziger externer Backend-Service-Layer):**

| Endpoint | Zweck | Epic |
|---|---|---|
| `GET /api/health` | Health-Check für HA-Binary-Sensor | Epic 1 |
| `POST /api/v1/setup/detect` | Auto-Detection (3 Adapter) | Story 2.2 |
| `POST /api/v1/setup/test` | Funktionstest (Readback) | Story 2.3 |
| `GET/POST /api/v1/devices` | Device-CRUD | Epic 1/2 |
| `GET /api/v1/control/state` | **Polling-Endpoint** (1-s-Takt, Live-Werte + Modus + letzter Zyklus) | Epic 3/5 |
| `GET/PUT /api/v1/pricing` | Bezugspreis | Story 5.2 |
| `GET /api/v1/kpi/{daily,monthly,live}` | KPI-Read | Story 5.3 |
| `GET /api/v1/diagnose/{cycles,errors,status,latency}` | Diagnose-Read | Epic 4 |
| `POST /api/v1/diagnose/export` | Diagnose-Export (unversioniert, Timestamp im Filename) | Story 4.5 |
| `GET/POST /api/v1/license/{status,activate}` | Lizenz-Flow | Epic 7 |
| `POST /api/v1/backup/{create,restore}` | Backup-Ops | Epic 6 |

**Kein `/ws`-Endpoint in v1.** WebSocket-Upgrade-Pfad als v1.5-Option dokumentiert.

**Component Boundaries (Frontend):**

- **Routes** kommunizieren niemals direkt mit API — immer via `lib/api/` oder `lib/stores/`
- **Primitives** sind stateless und domain-neutral
- **Feature-Components** dürfen Stores lesen
- **Charts** sind stateless-reactive auf Prop-Input
- **Stores** sind die einzige Cross-Component-Kommunikation

**Service Boundaries (Backend, In-Process):**

- **Controller ↔ Executor:** nur über typisierte Command-Objekte (nicht direct-state-mutation)
- **Controller ↔ HA-Client:** nur lesend (Sensor-Subscribe). Schreiben ausschließlich via Executor.
- **Controller ↔ KPI / State-Cache:** direkte Funktionsaufrufe (kein Bus).
- **Adapters ↔ alles:** statische Registry (`ADAPTERS = {...}`), pure Functions oder stateless Classes.
- **License ↔ API-Middleware:** License-State-Middleware blockt Writes bei `grace_expired`, Reads bleiben offen.

**Data Boundaries:**

- **Schema-Single-Source-of-Truth:** `persistence/sql/*.sql` — rohe SQL-Dateien
- **Zugriff:** ausschließlich über `repositories/*.py` — keine direkten Query-Builds außerhalb
- **Migration:** forward-only via `schema_version` + `sql/NNN_*.sql`
- **Externe Datenquelle:** HA-WS für Sensoren + LemonSqueezy für Lizenz; sonst keine

### Requirements to Structure Mapping (Epic-Mapping)

| Epic | Betroffene Verzeichnisse | Key-Files |
|---|---|---|
| **Epic 1 — Foundation** | `addon/`, `backend/src/solalex/{main,config,startup,ha_client}/`, `frontend/src/{app.css,App.svelte,lib/{api,polling,stores/theme}}`, `.github/workflows/` | `addon/config.yaml`, `addon/Dockerfile`, `addon/run.sh`, `ha_client/client.py`, `app.css` (Tokens) |
| **Epic 2 — Wizard (4 Schritte)** | `backend/src/solalex/{api/routes/setup,adapters,executor}/`, `frontend/src/routes/Wizard/*`, `frontend/src/lib/components/wizard/*` | `setup.py`, `adapters/hoymiles.py`, `adapters/marstek_venus.py`, `adapters/shelly_3em.py`, `Step1Hardware.svelte` … `Step4Activation.svelte` |
| **Epic 3 — Controller & Akku-Pool** | `backend/src/solalex/{controller.py,executor,adapters,persistence/repositories/control_cycles}/` | `controller.py` (Mono-Modul mit Enum-Dispatch), `executor/readback.py`, `rate_limiter.py` |
| **Epic 4 — Diagnose** | `backend/src/solalex/{diagnose,api/routes/diagnose}/`, `frontend/src/{routes/Diagnose.svelte,lib/components/diagnose}/`, `.github/ISSUE_TEMPLATE/bug-report.yml` | `diagnose/export.py` (unversioniert), `analysis.py`, `Diagnose.svelte` |
| **Epic 5 — Dashboard** | `backend/src/solalex/{kpi,api/routes/{kpi,pricing,control},state_cache.py}/`, `frontend/src/{routes/{Dashboard,Stats}.svelte,lib/{components/{dashboard,charts},stores/stateSnapshot}}/` | `state_cache.py` (Polling-Backing), `kpi/attribution.py`, `rollup.py`, `EuroHero.svelte`, `EnergyRing.svelte`, `FlowAnimation.svelte` |
| **Epic 6 — Update/Backup** | `backend/src/solalex/{backup,api/routes/backup}/`, `addon/run.sh` (auto-restore), `persistence/sql/` | `backup/snapshot.py` (VACUUM INTO → fsync → rename), `backup/restore.py` |
| **Epic 7 — License** | `backend/src/solalex/{license,api/routes/license,api/middleware}/`, `frontend/src/{lib/stores/license,routes/Wizard/Step4Activation}` | `license/lemonsqueezy.py`, `grace.py`, `api/middleware.py`, `license.ts` (Store), `Step4Activation.svelte` |

**Cross-Cutting Concerns:**

| Concern | Location |
|---|---|
| stdlib-Logging | `backend/.../common/logging.py` (~30 Zeilen Wrapper) + `api/middleware.py` |
| Design-Tokens | `frontend/src/app.css` (CSS Custom Properties, Single-Source) |
| Internal Control-Flow | Direkte Funktionsaufrufe (kein Bus-Modul) |
| Error-Handling | Backend: `api/middleware.py` (RFC 7807); Frontend: `lib/api/errors.ts` + Root-ErrorBoundary |
| Auth / License-Gate | Backend-Middleware: `api/middleware.py`; Frontend-Store: `lib/stores/license.ts` |

### Integration Points

**Internal Communication:**

- **Backend In-Process:** Controller ruft `kpi.record()` und `state_cache.update()` direkt auf. Kein Message-Broker.
- **Backend → Frontend (live):** REST-Polling auf `/api/v1/control/state` im 1-s-Takt → Svelte `lib/stores/stateSnapshot.ts` → Routen reagieren über Store-Subscriptions
- **Backend → Frontend (request/response):** REST `/api/v1/*` → handgeschriebene TS-Types → `lib/api/client.ts` Wrapper

**External Integrations:**

| Integration | Endpoint | Zweck |
|---|---|---|
| HA WebSocket | `ws://supervisor/core/websocket` | Sensor-Subscribe + `call_service` |
| LemonSqueezy | `https://api.lemonsqueezy.com/v1/licenses/validate` | Kauf + monatliche Re-Validation |
| GitHub Container Registry | `ghcr.io/alkly/solalex-{amd64,aarch64}` | Docker-Image-Hosting |
| HA Add-on Store | HA Supervisor via Custom-Repo | Update-Distribution |

**Data Flow (Haupt-Szenarien):**

1. **Regel-Zyklus (≤ 1 s, NFR1):**
   `HA Sensor Δ → ha_client.on_state_change` → `controller.on_sensor_update` → `mode_dispatch + policy` → `executor.dispatch` → `adapters/<vendor>.build_command` → `ha_client.call_service` → `executor.verify_readback` → `repositories.control_cycles.insert` → `state_cache.update(cycle)` + `kpi.record(cycle)` → Polling-Endpoint liefert beim nächsten Client-Tick den aktualisierten Snapshot

2. **Wizard-Pfad (Epic 2, 4 Schritte):**
   `User` → `Wizard/StepN.svelte` → `lib/api/client POST /api/v1/setup/detect` → `backend/api/routes/setup` → `adapters/<vendor>.detect(get_states_response)` → Response → Frontend zeigt Live-Werte via `GET /api/v1/control/state`-Polling → User bestätigt → `POST /api/v1/setup/test` → Funktionstest (Executor) → Readback-Ergebnis → `Step4Activation` → Disclaimer + `POST /api/v1/license/activate` → LemonSqueezy → Controller-Start (via `startup.py`)

3. **KPI-Rollup (täglich 00:05):**
   `asyncio.create_task(nightly_loop)` → `sleep_until("00:05")` → `kpi.rollup.run()` → aggregiert `control_cycles` → schreibt `kpi_daily` → Dashboard zieht über REST im nächsten Request

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** Alle verbleibenden Entscheidungen sind offiziell kompatibel: raw aiosqlite mit WAL-Mode; FastAPI + uvicorn + Pydantic v2 auf Python 3.13; Svelte 5 Runes + Vite 7 + Tailwind 4; Alpine 3.19 + uv; LemonSqueezy HTTPS; Multi-Arch Docker Buildx.

**Pattern Consistency:** snake_case end-to-end (DB → API → JSON). Direkte Funktionsaufrufe im internen Control-Flow. Closed-Loop-Readback im Executor nie umgangen. RFC 7807 einheitliches Error-Format. Ein-Modul-pro-Adapter spiegelt sich in `adapters/`.

**Structure Alignment:** Reduzierte Modul-Anzahl (`controller.py` statt 6 Files, keine `events/`, keine `templates/`, keine `lib/tokens/`) unterstützt Solo-Dev-30-Min-Kriterium. Ein Repository mit `addon/ + backend/ + frontend/` erlaubt Single-Release-Artefakt, ohne Workspace-Root-Komplexität.

### Requirements Coverage Validation

**Epic-Coverage (7/7):**

| Epic | Architektur-Support |
|---|---|
| Epic 1 Foundation | ✓ `addon/`, `ha_client/`, Tokens, Branding, Multi-Arch-CI |
| Epic 2 Wizard (4 Schritte) | ✓ `api/routes/setup.py`, 3 Adapter-Module, Wizard-Views |
| Epic 3 Controller & Akku-Pool | ✓ `controller.py` mit Enum-Dispatch + `executor/` + Fail-Safe + persistent rate-limit |
| Epic 4 Diagnose | ✓ `diagnose/`, unversioniertes Export |
| Epic 5 Dashboard | ✓ `kpi/`, `state_cache.py`, 1-s-Polling |
| Epic 6 Updates/Backup | ✓ `backup/` mit snapshot+restore, `sql/`-Migrate |
| Epic 7 License | ✓ `license/` mit lemonsqueezy+grace + Middleware (ohne Ed25519) |

**FR-Coverage:** FR8 reduziert auf 3 Hersteller Day-1 (Anker/Generic nach v1.5). Sonst unverändert.

**NFR-Coverage (angepasst):**

| NFR | Architektur-Antwort |
|---|---|
| NFR1 (≤ 1 s Regel-Zyklus) | Async-Direct-Calls, raw aiosqlite, PID in-Process |
| NFR2 (≤ 2 s TTFD) | Initial-Bulk-GET + Rollup-Tabellen + 1-s-Polling |
| NFR5/6 (RSS/CPU-Budget) | Alpine Base + FastAPI lean + SQLite embedded, keine ORM-Overhead |
| NFR8 (Wiederanlauf < 2 min) | `startup.py` Init-Order deterministisch |
| NFR9 (24h-Dauertest) | Integration-Tests + Load-Profile-Fixture |
| NFR11 (Fail-Safe) | `controller.py` Fail-Safe-Wrapper + Executor-Veto-Recht |
| NFR12 (14-Tage-Grace) | `license/grace.py` Counter |
| NFR13 (Container-Isolation) | HA-Add-on-Sandbox |
| NFR15 (License-Sig) | **Gestrichen** (Amendment 2026-04-22) — ersetzt durch LemonSqueezy-Online-Check |
| NFR17 (Zero-Telemetry) | Egress-Whitelist + CI-Test |
| NFR19 (100 % lokal) | Alpine + DM Sans WOFF2 + keine CDN + CSP-Header |
| NFR26 (Design-Quality) | Token-Layer (CSS-only) + 1-s-Polling + CSS-getriebene Atmen/Flow-Animation |
| NFR34 (ein Modul pro Adapter) | `adapters/*.py` 1:1 pro Hersteller |
| NFR44 (≥ 10 weitere Hersteller in v2–v3) | Adapter-Modul-Pattern als Erweiterungspunkt |
| NFR49 (i18n-ready ab v1) | **Aufgeschoben** auf v2 — hardcoded deutsche Strings in Svelte-Komponenten |

### Implementation Readiness Validation

**Decision Completeness:** Alle Major-Decisions dokumentiert. Konkrete Versionen werden im Bootstrap (Story 1.1) gepinnt.

**Structure Completeness:** Vollständiger Projekt-Tree von Root bis Leaf-Files.

**Pattern Completeness:** 5 harte Regeln als Hard-Enforcement. 4 CI-Checks. Gut-/Anti-Beispiele.

### Gap Analysis Results

**Critical Gaps:** Keine. Alle Readiness-Report-Findings vom 2026-04-21 wurden entweder adressiert oder durch die Vereinfachungen obsolet.

| Finding (Readiness 2026-04-21) | Auflösung |
|---|---|
| W-1 Architecture-Lücke | Amendment 2026-04-22 vollständig |
| W-4 WebSocket-vs-REST | REST + 1-s-Polling als First-Shot; WS als v1.5-Upgrade |
| Gap Schema-Migration-Konzept | `schema_version` + `sql/NNN_*.sql` Forward-Only |
| Gap Backup-Transaktions-Semantik | `VACUUM INTO .tmp → fsync → rename → fsync(dir)` |
| Gap Rollback-DB-Kompatibilität | Backup-File-Replace beim Start der vorherigen Add-on-Version |
| F-6 / NFR17 Egress-Audit | Whitelist + CI-Test |
| Gap Device-Template-JSON-Schema | Obsolet — Adapter-Module statt JSON-Templates |
| Gap Adapter-Interface-Signatur | `adapters/base.py` Abstract Adapter mit Timing-Semantik |
| Gap DM-Sans-Pipeline | `frontend/static/fonts/` + `OFL.txt` |

**Important Gaps (vor erstem Sprint zu klären):**

1. **Geschäftsmodell-Toggle (Trial vs. Freemium):** `config.py` Setting `license_mode: "trial" | "freemium"` + Branch-Logic in `license/grace.py`. In Story 7.2/7.3 ACs aufnehmen.
2. **Adapter-Abstract-Interface:** `adapters/base.py` mit Methoden `detect()`, `build_set_limit_command()`, `build_set_charge_command()`, `parse_readback()`, `get_rate_limit_policy()`, **plus Readback-Timing-Semantik** (Timeout-Fenster, Async-Readback-Support für OpenDTU) — in Story 2.2 als Teil der DoD.
3. **Polling-Shape-Dokumentation:** `/api/v1/control/state` muss ein konsolidiertes JSON mit allen für das Dashboard benötigten Feldern liefern. Shape in `api/schemas/state.py` (Pydantic) ist Source-of-Truth; TS-Types werden manuell synchron gehalten.

**Nice-to-Have Gaps (keine Launch-Relevanz):**

- SBOM-Generierung via `anchore/sbom-action` (CRA-Future-Vorarbeit)
- OpenAPI `Field(examples=[...])` für besseres Swagger-UI
- `dev/ha.yml` Compose für lokale HA-Dev-Instance
- MQTT-Discovery-Stub-Directory mit README (v1.5-Vorbereitung)
- WebSocket-Endpoint-Skelett (vorbereitet für v1.5-Upgrade ohne Breaking-Change)

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project-Context analysiert
- [x] Scale und Complexity assessed (MITTEL–HOCH nach Amendment)
- [x] Technical Constraints identifiziert
- [x] Cross-Cutting-Concerns gemappt (8 Punkte, reduziert von 10)

**✅ Architectural Decisions**
- [x] Critical Decisions dokumentiert
- [x] Tech-Stack spezifiziert (mit Bootstrap-Pinning-Policy)
- [x] Integration-Patterns definiert (REST + Polling)
- [x] Performance-Considerations adressiert (Rollup-Tabellen, WAL, Direct-Calls)

**✅ Implementation Patterns**
- [x] 5 harte Regeln als Kanon
- [x] Naming-Conventions (snake_case durchgängig)
- [x] Structure-Patterns (Feature-based, kein Workspace-Root)
- [x] Communication-Patterns (Direct-Calls, RFC 7807)

**✅ Project Structure**
- [x] Complete Directory-Structure
- [x] Component-Boundaries etabliert
- [x] Integration-Points gemappt
- [x] Requirements-to-Structure-Mapping pro Epic

### Architecture Readiness Assessment

**Overall Status:** **READY FOR IMPLEMENTATION** ✅

**Confidence Level:** **HIGH**

**Begründung:** Nach Amendment 2026-04-22 ist die Architektur signifikant schlanker und Solo-Dev-geeignet. 16 Cuts reduzieren Modul-Anzahl, Dependencies und CI-Komplexität um grob 40 %. Keine inneren Widersprüche, keine technologischen Inkompatibilitäten. Alle Day-1-Entscheidungen reversibel oder forward-migrierbar.

**Key Strengths:**
- Hardware-agnostischer Monolith-Controller mit statischer Adapter-Registry
- Direkte Funktionsaufrufe statt Event-Bus → debuggbar, profilebar
- Raw aiosqlite → AI-Tools produzieren korrekten Code zuverlässig
- REST + 1-s-Polling → Minimal-Infrastruktur mit sauberem WS-Upgrade-Pfad
- Backup-File-Replace → Rollback ohne Alembic-Downgrade-Komplexität
- Multi-Arch-Build bleibt → Zielhardware voll abgedeckt
- 5-Regel-Kanon in `CLAUDE.md` → AI-Agent-Governance ohne CI-Gate-Reibung

**Areas for Future Enhancement (v1.5/v2):**
- WebSocket-Live-Stream-Upgrade (bei UX-Beschwerden über Polling-Latenz)
- Anker Solix + Generic Adapter (Beta-Week-6)
- MQTT-Discovery-Integration (v1.5)
- Kryptografische Lizenz-Signatur (v1.5 wenn Anti-Tamper relevant)
- SetpointProvider-Konkretisierung mit Forecast-Quelle (v2)
- Multi-WR + Multi-Akku mit SoC-Balance (v2)
- i18n-Infrastruktur + englische UI (v2)

### Implementation Handoff

**AI-Agent + Dev-Guidelines:**

1. **Autorität:** Diese Architektur-Sektion + `CLAUDE.md` sind Single-Source-of-Truth. Änderungen via explizitem Architecture-Amendment (Datum + Begründung, siehe Amendment-Log unten).
2. **Pattern-Enforcement:** Die 5 harten Regeln gelten für jede Story. Die 4 CI-Checks (Ruff+MyPy+Pytest, ESLint+svelte-check+Prettier+Vitest, Egress-Whitelist-Mock, SQL-Migrations-Ordering) sind Hard-Gates.
3. **Feature-Modul-Respekt:** Direkte Funktionsaufrufe zwischen Modulen sind erlaubt und erwünscht. Kein Pub/Sub-Zwischenschicht in v1.
4. **Safety non-negotiable:** Closed-Loop-Readback + Rate-Limit + Fail-Safe ist in jeder Write-Operation Pflicht.

**First Implementation Priority (Story 1.1 Bootstrap):**

```bash
mkdir solalex && cd solalex
git init

# Repo-Wurzel (repository.yaml, README, LICENSE, .gitignore, CLAUDE.md)

# Backend (eigenständig, kein Workspace-Root)
mkdir backend && cd backend
uv init --python 3.13
uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite httpx pydantic-settings
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
cd ..

# Frontend (eigenständig)
mkdir frontend && cd frontend
npm create vite@latest . -- --template svelte-ts
npm i -D tailwindcss @tailwindcss/vite eslint prettier svelte-check vitest
npm i svelte-spa-router
# DM Sans WOFF2 + OFL.txt unter frontend/static/fonts/
# .nvmrc mit Node-Version (aktuelle LTS)
cd ..

# Add-on-Skelett
mkdir -p addon/rootfs/etc/services.d/solalex
# addon/config.yaml nach home-assistant/addons-example
# addon/Dockerfile Multi-Stage
# addon/run.sh mit bashio
```

## Amendment-Log

### 2026-04-22 — Komplexitäts-Reduktion (16 Cuts)

**Kontext:** Solo-Dev-Review mit zwei unabhängigen Parallelanalysen. Identifiziert: Architektur war auf Team-/Scale-Szenarien dimensioniert, nicht auf Solo-Dev + Beta-Launch.

**Angewandte Cuts:**

| # | Cut | Vorher | Nachher |
|---|---|---|---|
| 1 | Event-Bus → direkter Aufruf | `asyncio.Queue`-Pub/Sub + `events/bus.py` + Subscription-Dict | Direkte Funktionsaufrufe `kpi.record()` + `state_cache.update()` |
| 2 | ORM → aiosqlite + `schema_version`, Rollback via Backup-Replace | SQLAlchemy 2.0 async + Alembic + Forward/Backward-Migrations | Raw aiosqlite + handgeschriebene Queries + `sql/NNN_*.sql` Forward-Only + `VACUUM INTO`-Backup + File-Replace on Downgrade |
| 3 | WS → REST + 1-s-Polling | WebSocket-Live-Stream + Dispatcher + Subscription-Registry | REST-Polling im Dashboard, WS als v1.5-Upgrade-Pfad |
| 4 | WS-Event-Versionierung streichen (falls WS kommt) | `{event, v: 1, ts, data}` + Transition-Windows für Breaking-Changes | Unversionierte Events beim späteren WS-Upgrade |
| 5 | `openapi-typescript`-Pipeline streichen | Generator + OpenAPI-Diff-CI-Gate | Handgeschriebene TS-Types neben `client.ts` |
| 6 | `structlog` → stdlib logging | structlog + JSON-Renderer + Correlation-IDs | `logging` + `JSONFormatter` (~30 Zeilen) |
| 7 | APScheduler → asyncio-Task | APScheduler mit DB-JobStore | `asyncio.create_task` + `sleep_until` |
| 8 | Ed25519-Signatur streichen | `cryptography`-Dep + `public_key.pem` + Ed25519-Verify | Nur LemonSqueezy-Online-Check (14-Tage-Grace unverändert) |
| 9 | Controller-6er-Split konsolidieren | `drossel/speicher/multi/mode_selector/pid/failsafe` als 6 Module | Ein `controller.py` mit Enum-Dispatch + Hysterese-Helper + Fail-Safe-Wrapper |
| 10 | Template-System-JSON-Layer streichen | `templates/loader.py` + `templates/data/*.json` + JSON-Schema-Validator | Hardcoded Entity-Mappings als Python-Dicts in `adapters/<vendor>.py`; `detector.py` pattern-matcht auf Entity-Prefixe |
| 11 | Day-1-Adapter auf 3 | 5 Adapter (Hoymiles + Anker + Marstek + Shelly + Generic) | 3 Adapter (Hoymiles + Marstek + Shelly), Anker + Generic auf Beta-Week-6 / v1.5 |
| 12 | Wizard 7→4 | 7 Schritte | 4 Schritte: Hardware → Detection+Config (Smart-Meter/Battery als Sub-Cards) → Funktionstest → Disclaimer+Activation |
| 13 | `lib/tokens/*.ts` streichen | TS-Duplikat der Tokens | CSS Custom Properties in `app.css` als Single-Source |
| 14 | Playwright erst post-MVP | E2E-Folder + Playwright-Dep | Manual-QA + Beta-Tester als v1-E2E; Vitest bleibt |
| 15 | Monorepo-Workspace-Root auflösen | Root-`pyproject.toml` + uv-Workspace + Root-`package.json` | Nur `backend/` (uv) + `frontend/` (npm), CI macht `cd <dir>` |
| 16 | Pattern-/CI-Gate-Overhead reduzieren | 14 Pattern-Kategorien + 10 MUST-Regeln + 5 CI-Checks | 5 harte Regeln in `CLAUDE.md` + 4 CI-Checks |

**Explizit beibehalten:** Multi-Arch-Build (amd64 + aarch64) — Zielhardware deckt beide ab.

**PRD-Rückwirkungen (für PRD-Update):**
- NFR15 (Lizenz-Signatur) entfällt
- FR8 / Hardware-Day-1-Liste auf 3 Hersteller kürzen
- NFR44 (Device-Template-System als JSON-Schema) umformulieren zu „Adapter-Modul-Pattern"
- NFR49 (i18n-ready ab v1) auf v2 verschieben

**Epics-Rückwirkungen (für Epic-Update):**
- Epic 2 Story 2.1: 4 Schritte statt 7
- Epic 2 Story 2.2: 3 Adapter statt 5
- Epic 2 Story 2.2: Hardcoded Entity-Mappings statt JSON-Template-Loader
- Epic 3 Stories 3.x: Ein Controller-Modul statt 6
- Epic 5 Story 5.1+: Polling-basiert statt WS
- Epic 6 Story 6.2: Ein Backup-Slot statt Rotation-of-5
- Epic 6 Story 6.3: Backup-Replace statt Alembic-Downgrade
- Epic 7 Story 7.3: Ersatzlos gestrichen (keine Signatur-Verifikation)

---

### 2026-04-25 — Generic-First Adapter-Layer

**Kontext:** Smoke-Test gegen reale Tester-Hardware (ESPHome/Trucki/SML) zeigt, dass vendor-spezifische Regex-Patterns aus Cut #10/#11 (Amendment 2026-04-22) für Day-1 zu eng sind. Trucki-Stick (`input_number.t2sgf72a29_t2sgf72a29_set_target`) und ESPHome-SML (`sensor.00_smart_meter_sml_current_load`) matchen weder Hoymiles- noch Shelly-Patterns. Code-Analyse zeigt: ~80 % jedes Vendor-Adapters ist HA-Standard-Boilerplate (Service-Domain, Service-Name, Readback-Parsing, Detection-Logik). Echte Vendor-Spezifik sind nur die Tuning-Werte (Drossel-Deadband, Range, Rate-Limit, Readback-Timeout).

**Cut:** Hoymiles-Adapter wird zu `adapters/generic.py` (Klasse `GenericInverterAdapter`), Shelly-3EM-Adapter wird zu `adapters/generic_meter.py` (Klasse `GenericMeterAdapter`). Marstek-Venus bleibt vendor-spezifisch (Akku-spezifische SoC-Patterns + Charge-Power-Service rechtfertigen ein eigenes Modul).

**Detection-Logik (HA-Capabilities statt vendor-Suffix):**

- WR-Limit-Detection: Domain ∈ {`number`, `input_number`}, `unit_of_measurement` ∈ {`W`, `kW`}. `device_class == "power"` ist Bonus, nicht Pflicht (ESPHome setzt das nicht zuverlässig).
- WR-Output-Detection: Domain `sensor`, `unit_of_measurement` ∈ {`W`, `kW`}.
- Smart-Meter-Detection: Domain `sensor`, `unit_of_measurement` ∈ {`W`, `kW`}, optional Suffix-Hint (`_power`, `_current_load`, `_grid_power`) für Confidence-Boost.

**Was NICHT geändert wird:**

- `AdapterBase`-Interface bleibt unverändert (gleiche Methoden, gleiche Signaturen).
- Service-Call-Generierung: Service-Domain folgt jetzt der Entity-Domain (`number.set_value` vs. `input_number.set_value`) — beide HA-Standard.
- Closed-Loop-Readback-Pflicht (CLAUDE.md Regel 3) — unverändert.
- Range-Check, Rate-Limit, Fail-Safe — unverändert.
- JSON-Template-Verbot aus Amendment 2026-04-22 (Cut #10) — unverändert. Generic-Adapter liest **keine** Templates aus Files; vendor-Spezifika werden, falls überhaupt, per `device.config_json`-Override-Keys hinterlegt.
- CLAUDE.md Regel 2 („Ein Python-Modul pro Adapter") — bleibt gültig. „Generic" ist im neuen Modell der Vendor „HA-konforme Geräte" — ein Adapter, der per Definition keine Hersteller-Spezifik kennt. Echte Hersteller-Tuning-Profile (z. B. Hoymiles ±5 W Deadband) können in v1.5+ als Subklassen wiederkommen, die `GenericInverterAdapter` erben und nur die Tuning-Params overriden.

**Konsequenz für Day-1-Hardware-Liste (revidiert Cut #11 aus Amendment 2026-04-22):**

- alt: Hoymiles/OpenDTU + Marstek Venus 3E/D + Shelly 3EM
- neu: Generischer Wechselrichter + Marstek Venus 3E/D + Generischer Smart Meter
- v1.5: optionale Vendor-Tuning-Profile als Subklassen + Anker Solix als eigener Vendor-Adapter (Akku-Spezifik)

**Konservative Defaults für Generic:**

- `get_drossel_params`: `deadband_w=10, min_step_w=5, smoothing_window=5, limit_step_clamp_w=200`. Toleranter als Hoymiles-Tuning, weil unbekannte WR größere Latenz/Hysterese haben können. Pro-Device-Override über `device.config_json` möglich (Keys: `deadband_w`, `min_step_w`, `smoothing_window`, `limit_step_clamp_w`). Validation in `DrosselParams.__post_init__` greift bei jedem Override (fail loud).
- `get_limit_range`: `(2, 3000)` W als Default — passend für Mikro-WR, Balkonkraftwerke und String-WR bis 3 kW. Per `device.config_json.min_limit_w` und `device.config_json.max_limit_w` override-bar.
- `get_rate_limit_policy`: `60 s` (Hoymiles-konservativ, sicher für unbekannte WR mit DTU-Protokoll-Limits).
- `get_readback_timing`: `15 s sync` (Hoymiles-konservativ).

**`device.config_json`-Override-Schema (v1):**

```json
{
  "deadband_w": 10,
  "min_step_w": 5,
  "smoothing_window": 5,
  "limit_step_clamp_w": 200,
  "min_limit_w": 2,
  "max_limit_w": 3000
}
```

Alle Keys optional. Editierbar in v1 nur per direktem DB-Update oder zukünftiger PATCH-Route. UI-Exposure (Wizard-Sektion „Erweiterte Einstellungen" oder Diagnose-Tab-Override) ist v1.5-Scope (eigene Story).

**Epics-Rückwirkungen (für Epic-Update):**

- Epic 2 Story 2.4 (neu): Generic-Adapter-Refit — `hoymiles.py` → `generic.py`, `shelly_3em.py` → `generic_meter.py`, DB-Migration `003_adapter_key_rename.sql`. Beta-Launch-blocking.
- Epic 2 Stories 2.1–2.3 (`done`): Acceptance-Kriterien bleiben gültig (sprechen generisch von „Wechselrichter"); Frontend-Strings/Types werden als Teil von 2.4 nachgezogen.
- Epic 5 Story 5.1a (`done`): Frontend-Type-Update zieht automatisch nach.

**Detail-Spezifikation:** siehe Sprint Change Proposal `sprint-change-proposal-2026-04-25.md`.

---

### Amendment 2026-04-25 (Surplus-Export) — `Mode.EXPORT` als 4. Mode

**Trigger:** Konzeptionelle Lücke entdeckt beim Durchsprechen DC-gekoppelter Hybrid-Setups (PV → Akku → WR), die auch AC-gekoppelte Beta-Sweet-Spot-Setups (Marstek Venus + Hoymiles parallel am Hausnetz) trifft: Bei Pool-Voll switcht Story 3.5 zu DROSSEL und reduziert das WR-Limit — die überschüssige PV wird dadurch abgeregelt, statt eingespeist. Wirtschaftlich verschenkt das im Sommer 1–3 kWh/Tag pro Beta-Tester der Klasse „Eigenverbrauchs-Maximierer mit angemeldeter Anlage" (DACH-Mehrheit).

**Cut:** Mode-Enum wird von 3-fach (DROSSEL, SPEICHER, MULTI) auf 4-fach erweitert. Neuer Wert `Mode.EXPORT = "export"`. Neue Policy `Controller._policy_export(self, device, sensor_value_w) -> list[PolicyDecision]` am Mono-Modul-Controller (kein neues Modul, Architektur-Cut 9 bleibt). Die Policy setzt das WR-Limit auf den Hardware-Max-Wert aus `wr_limit_device.config_json.max_limit_w` (Schema aus dem Generic-Adapter-Amendment 2026-04-25 wiederverwendet — additiver Schlüssel `allow_surplus_export` ergänzt).

**Trigger-Logik:**

- Hysterese-Erweiterung in `_evaluate_mode_switch` (Story 3.5 Helper):
  - SPEICHER + `aggregated_pct ≥ 97 %` + `wr_limit.config_json.allow_surplus_export == True` → Switch zu EXPORT (statt DROSSEL).
  - EXPORT + `aggregated_pct ≤ 93 %` → Switch zurück zu `_mode_baseline` (üblicherweise SPEICHER oder MULTI).
- MULTI-Cap-Branch in `_policy_multi` (Story 3.5):
  - `_speicher_max_soc_capped == True` + Toggle ON → ruft `_policy_export` statt `_policy_drossel` auf. MULTI bleibt MULTI (kein Mode-Switch), die Decision wird einfach mit Hardware-Max-Limit produziert.

**Toggle-Persistenz:** Pro WR im bestehenden `device.config_json`-Override-Schema:

```json
{
  "max_limit_w": 600,
  "allow_surplus_export": true
}
```

- Default `allow_surplus_export = false` (Status-quo-Verhalten preserve).
- Validierung: `allow_surplus_export = true` ist nur akzeptabel, wenn `max_limit_w` ebenfalls gesetzt ist (sonst kennt die Policy den Wert nicht). API-Validierung im neuen `PATCH /api/v1/devices/{id}/config`-Endpunkt.
- Editierbar in v1 über Frontend Config-Page (Toggle pro WR-Tile).

**Was NICHT geändert wird:**

- `AdapterBase`-Interface bleibt unverändert.
- Closed-Loop-Readback-Pflicht (Regel 3) — unverändert. EXPORT-Decisions durchlaufen die normale Veto-Kaskade + Readback im Executor.
- Range-Check, Rate-Limit, Fail-Safe — unverändert.
- `_mode_baseline`-Field aus 3.5 — bleibt; EXPORT setzt es nicht.
- Hysterese-Konstanten 97/93 % aus 3.5 — werden wiederverwendet, kein separater EXPORT-Schwellenwert.
- Mindest-Verweildauer 60 s aus 3.5 — gilt auch für EXPORT-Switch.
- JSON-Template-Verbot — unverändert.

**SQL-Migration 004:** Forward-only Recreate-Pattern — erweitert CHECK-Constraint auf `control_cycles.mode` und `latency_measurements.mode` um Wert `'export'`. SQLite kennt kein `ALTER TABLE ... ALTER CONSTRAINT`, daher Standard-Pattern `CREATE TABLE _new` + `INSERT ... SELECT` + `DROP` + `RENAME` + `CREATE INDEX`.

**Konsequenz für CLAUDE.md:**

- Stolperstein-Eintrag „Mode-Enum bleibt 3-fach" wird ersetzt durch „Mode-Enum bleibt 4-fach: DROSSEL, SPEICHER, MULTI, EXPORT — kein 5. Mode in v1".
- Neuer Stop-Eintrag: „Wenn du Surplus-Export als Patch in `_policy_drossel` einbauen willst statt eigenem `Mode.EXPORT` + `_policy_export` — STOP. Audit-Trail-Klarheit (mode='export' im Log) ist non-verhandelbar."

**Konsequenz für Default-User-Verhalten:**

- Status-quo bleibt erhalten. Beta-Tester der Klasse „strenge Nulleinspeisung" (z. B. Anlagen ohne Inbetriebnahme-Anmeldung) bemerken ohne Toggle-Aktivierung keinerlei Verhaltensänderung.
- Beta-Tester der Klasse „Eigenverbrauchs-Maximierer" können den Toggle pro WR aktivieren und vermeiden damit PV-Abregelung bei vollem Akku.

**Erweitertes `device.config_json`-Schema (additiv zum 2026-04-25-Generic-Adapter):**

```json
{
  "deadband_w": 10,
  "min_step_w": 5,
  "smoothing_window": 5,
  "limit_step_clamp_w": 200,
  "min_limit_w": 2,
  "max_limit_w": 600,
  "allow_surplus_export": false
}
```

**Epics-Rückwirkungen:**

- Epic 3 Story 3.8 (neu): Surplus-Export-Mode bei Akku-Voll — `Mode.EXPORT` + `_policy_export` + DB-Migration 004 + Frontend-Toggle. Beta-Launch-blocking.
- Epic 3 Story 3.5 (`done`): `_evaluate_mode_switch` und `_policy_multi` werden in 3.8 additiv erweitert; Story 3.5 wird **nicht** re-opened.
- Epic 2 Story 2.1 (`done`): Frontend-Erweiterung Config.svelte (Toggle) wird in 3.8 mitgenommen.
- Epic 5 Story 5.1a (`done`): Mode-Label-Mapping `'export'` → „Einspeisung" wird in 3.8 mitgenommen.

**Detail-Spezifikation:** siehe Sprint Change Proposal `sprint-change-proposal-2026-04-25-surplus-export.md`.
