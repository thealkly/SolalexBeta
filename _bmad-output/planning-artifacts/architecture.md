---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md
workflowType: 'architecture'
project_name: 'SolarBotDevelopment'
user_name: 'Alex'
date: '2026-04-21'
lastStep: 8
status: 'complete'
completedAt: '2026-04-21'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Funktionale Requirements:** 43 FRs in 8 Kategorien (Installation/Lizenz, Setup/Onboarding, Regelung/Steuerung, Akku-Management, Monitoring/Dashboard, Diagnose/Support, Updates/Administration, Branding/UI). Architektonisch kondensieren sie sich auf ~8–12 Kernmodule mit einem hardware-agnostischen Core-Controller als Rückgrat.

**Non-Functional Requirements — architekturprägend:**

- Performance-Budget: Regel-Zyklus ≤ 1 s, Dashboard TTFD ≤ 2 s, ≤ 150 MB idle RSS, ≤ 2 % CPU idle auf Raspberry Pi 4 → enge Framework-Auswahl, keine Overhead-Bibliotheken
- Reliability: 24-h-Dauertest, 0 kritische Bugs, Wiederanlauf < 2 min, 14 Tage Lizenz-Grace → deterministische Safe-States, Persistenz-Disziplin
- Security & Privacy: 100 % lokal, SUPERVISOR_TOKEN-only, signierte Lizenz, keine Telemetry → einzige externe Grenze = LemonSqueezy (monatlich)
- Maintainability: Ein Modul pro Device-Template, ≥ 70 % Core-Coverage, Solo-Dev-Kriterium „jedes Modul in ≤ 30 min nachvollziehbar"
- Scalability: ≥ 10 weitere Hersteller in v2–v3 ohne Core-Refactor (Device-Template-System als Erweiterungspunkt)

**Scale & Complexity:**

- Primär-Domain: Edge Orchestrator / IoT Embedded (HA Add-on)
- Komplexität: HOCH (Echtzeit-Regelung, Multi-Hardware, kommerziell, Fail-Safe)
- Geschätzte Architektur-Komponenten: ~8–12 Kernmodule

### Technical Constraints & Dependencies

Aus dem PRD bereits fixiert und nicht offen:

- Tech-Stack: Python 3.13 + FastAPI, Svelte + Tailwind, SQLite
- Runtime: HA Add-on Base Image (Alpine 3.19), HA-Ingress, Supervisor-Token
- Distribution: Custom Add-on Repository (GitHub `alkly/solarbot`), Multi-Arch-Build
- Alleiniger Integrations-Kanal: HA WebSocket API (`ws://supervisor/core/websocket`)
- Externe Services: ausschließlich LemonSqueezy (Aktivierung + monatliche Re-Validation)
- Persistenz: `/data/`-Volume (SQLite, Lizenz, Templates, Backup, rotierte Logs)
- Hardware-Day-1: Hoymiles/OpenDTU, Anker Solix, Marstek Venus 3E/D, Shelly 3EM, Generic HA Entity

### Cross-Cutting Concerns Identified

1. **Closed-Loop-Readback + Fail-Safe** als durchgängiges Pattern für jeden Steuerbefehl
2. **Event-Source-Attribution** (`solarbot | manual | ha_automation`) als Basis aller KPIs
3. **E2E-Latenz-Messung pro Device** als Input für hardware-spezifische Regel-Parameter
4. **EEPROM-Rate-Limiting** (≤ 1 Schreibbefehl/Device/Minute Default)
5. **Device-Template-System** als einheitliches JSON-Schema und Erweiterungspunkt
6. **Strukturiertes JSON-Logging** (rotiert 10 MB / 5 Dateien)
7. **i18n-Ready ab v1** — alle UI-Strings in `locales/de.json`
8. **Lizenz-Gated Startup** mit Signatur-Verifikation
9. **Backup-Rotation** (letzte 5 Stände) vor jedem Update
10. **ALKLY-Design-System** (Token-basiert, Dark/Light-konform)

### Architektonische Spannungsfelder (früh zu entscheiden)

- Regelungs-Engine: monolithisch vs. Pipeline (Sensor → Policy → Executor)
- Adapter-Tiefe: reines Entity-Mapping vs. hardware-spezifische Policy-Funktionen
- Frontend-Datenkontrakt: REST vs. WebSocket-Live-Stream zum Svelte-UI
- SetpointProvider-Naht: reines Interface vs. Strategy-Pattern mit Default-Noop v1
- SQLite-Schema-Design (Zyklen, Latenz, KPI-Aggregate) unter Speicher-Budget

### PRD-Rückwirkungen / Scope-Fragen (aus ADR-Debatte)

Aus der Multi-Architect-Debatte entstandene Hinweise an spätere Workflow-Schritte und mögliche PRD-Rückwirkungen:

- **Kipp-Kandidat für die Scope-Liste:** WebSocket-Live-Stream zum Dashboard. Aktuell nicht als kippbar markiert. Fallback wäre REST-Polling (2 s). Empfehlung: zur PRD-Kipp-Liste hinzufügen — nicht-verhandelbar ist nur die Dashboard-TTFD ≤ 2 s, nicht der Transportkanal.
- **Bestätigt nicht kippbar:** SetpointProvider-Interface in v1. Gehört namentlich zur Innovation-Liste (PRD) und zur v2-Forecast-Naht. Debatte bestätigt: zero-cost in v1 wenn Default-Impl = aktuelles reaktives Verhalten.
- **Safety-Grenze präzisiert:** Policy/Provider liefern Vorschläge, Executor entscheidet mit Veto-Rechten (Range-Check, Rate-Limit, Readback). Gilt als architektonisches Prinzip ab Step 3+.

## Starter Template Evaluation

### Primary Technology Domain

Edge Orchestrator / IoT Embedded als Home-Assistant-Add-on. Stack: Python 3.13 + FastAPI + SQLite (Backend), Svelte 5 + Vite + Tailwind 4 (Frontend als SPA), Multi-Arch Docker (amd64/aarch64), 100 % lokal, HA-Ingress-embedded, Supervisor-Token-only, DM Sans lokal als WOFF2.

### Starter Options Considered

| Option | Bewertung |
|---|---|
| `tiangolo/full-stack-fastapi-template` | Verworfen — Postgres + Traefik + K8s sind Cloud-first und widersprechen „100 % lokal + SQLite". Dekonstruktion kostet ~40h über Projektverlauf. |
| `buhodev/sveltekit-tailwind-starter` | Verworfen — SvelteKit ist SSR-orientiert. HA-Ingress liefert keinen SSR-Endpoint, Ingress-URL ist zur Build-Zeit unbekannt (Supervisor injiziert runtime). 80 % der SvelteKit-Docs sind Load-Functions/Server-Endpoints ohne Relevanz. |
| `jpawlowski/hacs.integration_blueprint` | Verworfen — falscher Projekt-Typ (Custom Integration, nicht Add-on). |
| `home-assistant/addons-example` | Als Referenz adoptiert (nicht als Basis) für `config.yaml`, `Dockerfile`, s6-overlay, `run.sh` mit bashio. |
| `hassio-addons/addon-base-python` | Als Referenz adoptiert (nicht als Basis) — offizielles HA Base-Image ist neutraler für ein kommerzielles Produkt. |
| **Komponierter Solarbot-Skeleton** | **Gewählt.** Drei separate `init`-Commands + dokumentierte Integrationsschicht. Alle Decisions bleiben explizit in der Architektur statt in Boilerplate versteckt. |

### Selected Starter: Komponierter Solarbot-Skeleton

**Rationale for Selection:**

Der Stack ist zu spezifisch (HA-Ingress + Multi-Arch + 100-%-lokal + Svelte-SPA in FastAPI-Static-Serve + DM-Sans-WOFF2), als dass ein Fremd-Starter passt. Jeder generische Starter schleppt Annahmen mit, die dem PRD widersprechen (Cloud-DB, SSR, externe Fonts, Auth-Stubs). Die reale Boilerplate-Last für den komponierten Skeleton ist einmalig ~4 Stunden (`config.yaml` ~30 Zeilen, `run.sh` mit bashio ~20 Zeilen, `Dockerfile` ~40 Zeilen, Multi-Arch-Workflow ~60 Zeilen). Die Verstehens-Investition in diese Dateien ist unvermeidbar, weil HA-Add-ons eng mit Supervisor gekoppelt sind. Ein Starter, der das wegabstrahiert, rächt sich beim ersten Ingress-Bug.

Party-Mode-Validierung (Winston/Amelia/Sally) bestätigt alle vier Kern-Entscheidungen einhellig: Skeleton komponiert, Pure Svelte-SPA (kein SvelteKit), uv als Package-Manager, Monorepo-Struktur.

**Initialisierungs-Sequenz (drei Layer):**

```bash
# Layer 1 — Repository-Wurzel als HA Custom Add-on Repo
# Manuell: repository.yaml + README + icon.png
# Vorlage: github.com/home-assistant/addons-example

# Layer 2 — Backend (Python 3.13 + FastAPI)
cd backend/
uv init --python 3.13
uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite websockets \
       pydantic-settings httpx cryptography
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
# Build-Backend: hatchling fixieren (uv_build noch experimental)

# Layer 3 — Frontend (Svelte 5 + Vite + Tailwind 4)
cd frontend/
npm create vite@latest . -- --template svelte-ts
npm i -D tailwindcss @tailwindcss/vite
npm i svelte-spa-router
# + DM Sans WOFF2 manuell unter frontend/static/fonts/ ablegen
```

**Verifizierte Aktuelle Versionen (Stand April 2026):**

| Komponente | Version | Quelle |
|---|---|---|
| Python | 3.13 | FastAPI-empfohlen für Performance |
| FastAPI | 0.135.1 | PyPI März 2026 |
| uv | 0.5+ | Astral, Alpine/musl-arm64 stabil seit Q3 2024 |
| Svelte | 5 (stabil) | aktuelle Major |
| Vite | 7.x | aktuelle Major |
| Tailwind CSS | 4 (stabil) | `@tailwindcss/vite` Plugin |
| HA Add-on Base Image | `ghcr.io/home-assistant/{arch}-base-python:3.13-alpine3.19` | Seit 2026.03.1 Multi-Arch (amd64/arm64) |
| s6-overlay + bashio | im HA-Base enthalten | Nicht separat installieren |

### Architectural Decisions Provided by Starter

**Language & Runtime:**

- Backend: Python 3.13, FastAPI 0.135+, uvicorn (ASGI), aiosqlite (async SQLite)
- Frontend: TypeScript, Svelte 5 (Runes), Vite 7 (Build + HMR)
- Single-Source-of-Truth für Python-Deps: `pyproject.toml` + `uv.lock` (kein `requirements.txt`)
- Node-Lockfile: `package-lock.json` committed

**Styling Solution:**

- Tailwind CSS v4 über `@tailwindcss/vite` Plugin
- ALKLY-Design-Tokens als CSS Custom Properties (`--color-primary`, `--color-accent`, etc.)
- DM Sans lokal als WOFF2 im Container unter `frontend/static/fonts/` (keine externe CDN, kein preconnect)
- Dark/Light-Mode via HA-Theme-Adaption + Token-Layer mit modus-spezifischer Saturation

**Build Tooling:**

- Vite 7 als Frontend-Bundler → `frontend/dist/` als statisches Bundle
- Dockerfile kopiert `frontend/dist/` in Backend-Static-Verzeichnis
- FastAPI serviert die SPA unter HA-Ingress-URL (keine separate Node-Runtime im Prozess)
- Multi-Arch-Build via `docker buildx` + GitHub Actions (amd64 + aarch64 via QEMU), dominiert von QEMU-Zeit (~8 min)

**Testing Framework:**

- Backend: `pytest` + `pytest-asyncio` + `pytest-cov` (Ziel ≥ 70 % Core-Coverage, ≥ 50 % gesamt laut NFR35)
- Frontend: `vitest` für Unit + `playwright` für E2E (später, nicht Launch-Gate)
- Mock-HA-WebSocket für Adapter-Integration-Tests

**Linting / Formatting:**

- Python: `ruff` (Lint + Format) + `mypy` (Type-Check)
- TS/Svelte: `eslint` + `prettier` + `svelte-check`

**Code Organization (Monorepo):**

```
solarbot/
├── addon/              # HA Add-on Definition
│   ├── config.yaml     # Add-on-Manifest (Supervisor-konform)
│   ├── Dockerfile      # Multi-Stage: frontend-build + backend-assemble
│   ├── run.sh          # Entry-Point mit bashio-Config-Read
│   └── rootfs/         # s6-overlay Services + Static-Files-Overlay
├── backend/            # Python 3.13 + FastAPI
│   ├── pyproject.toml  # uv-managed
│   ├── uv.lock         # reproduzierbar, committed
│   ├── src/solarbot/   # Package
│   └── tests/
├── frontend/           # Svelte 5 + Vite + Tailwind 4
│   ├── package.json
│   ├── src/
│   └── static/fonts/   # DM Sans WOFF2 lokal
├── repository.yaml     # Custom-Add-on-Repo-Manifest
├── .github/workflows/  # Multi-Arch-Build, Release-Tag-Trigger
└── README.md
```

**Rationale Monorepo:** Ein Release-Artefakt (das Add-on-Image), ein Changelog, atomic commits bei API↔Frontend-Contract-Änderungen, ein `git mv` bei späterem Rename (Markenrechts-Vorbehalt). Contract-Sync (OpenAPI-Schema → TS-Typen, WebSocket-Payload-Typen, Design-Tokens) passiert in-tree ohne Cross-Repo-PRs.

**Development Experience:**

- Vite HMR für Frontend (Svelte-Reaktivität sofort sichtbar)
- `uvicorn --reload` für Backend-Entwicklung (ausschließlich lokal)
- Svelte-DevTools-Extension + Vite-Svelte-Inspector
- GitHub Actions CI: Ruff + Mypy + Pytest + Frontend-Build + Multi-Arch-Docker-Build + SBOM
- uv ist 10–100× schneller als pip/poetry beim Resolve → spart bei Multi-Arch-Builds 2–4 Minuten pro Build

### Vertagte Entscheidungen (für spätere Steps)

- **View-Routing & State-Management** (Sally's offene Frage): svelte-spa-router vs. conditional rendering, Runes + Stores-Mix, Wizard-Multi-Step-State → **Step 5 (Patterns) / Step 6 (Structure)**
- **API-Contract-Layer**: OpenAPI-Schema → TS-Client-Generator (openapi-ts o. Ä.), WebSocket-Event-Typisierung → **Step 5**
- **SQLite-Schema + Migration-Konzept** (Readiness-Report-Finding): `yoyo-migrations` vs. handgebautes Version-Counter-Pattern → **Step 4**
- **numpy/pandas**: nicht im MVP; Base bleibt Alpine. Bei späterer Forecast/Optimization-Integration → Wechsel zu `python:3.13-slim` als einfache Dockerfile-Änderung.

**Note:** Projekt-Initialisierung mittels der drei oben dokumentierten `init`-Commands ist die erste Implementation-Story (Epic 1 / Story 1.1 Bootstrap).

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- W-4 aus Readiness-Report aufgelöst: **Hybrid WebSocket + REST** (WS nicht kippbar wegen NFR26/Flow-Animation/2-s-TTFD)
- Data-Persistence-Stack: **SQLAlchemy 2.0 async + aiosqlite + Alembic**, WAL-Mode aktiv, `VACUUM INTO` als Backup-Semantik
- Lizenz-Signatur: **Ed25519** via `cryptography` (Private-Key bei Alex, Public-Key im Image)
- Egress-Whitelist: nur `*.lemonsqueezy.com` — harter Code-Audit (NFR17)
- Schema-Migration-Konzept: Alembic `alembic_version`-Tabelle (schließt Readiness-Gap)

**Important Decisions (Shape Architecture):**

- Rollup-Tabellen für KPI-Aggregation (Dashboard-TTFD ≤ 2 s)
- In-Process Event-Bus (`asyncio.Queue`) für Backend-Pub/Sub — kein Redis
- Svelte 5 Runes primär + Stores für Cross-View-Subscriptions
- Hash-basiertes Routing via `svelte-spa-router` (Ingress-URL-agnostisch)
- `openapi-typescript` nur für Types + dünner `fetch`-Wrapper (kein Runtime-Client)

**Deferred Decisions (Post-MVP):**

- MQTT-Discovery (v1.5) — Mosquitto-Add-on-Dependency
- SetpointProvider-Konkrete-Implementierung (v2 Forecast)
- Multi-WR / SoC-Balance (v2)
- Kaskaden-Modell (v2)
- Character-Template-Engine (v1.5 falls in MVP gekippt)
- i18n-Mechanik (v2 Englisch) — Infra ab v1, aber nur Deutsch befüllt

### Data Architecture

**ORM + Driver:** SQLAlchemy 2.0 async + aiosqlite. Async-nativ, Connection-Pool, TypedModels via `sqlalchemy.orm.Mapped`. Overhead im normalen Request-Path vernachlässigbar. Für den Regel-Zyklus (Hot-Path, NFR1 ≤ 1 s) kann pro Abschnitt zu Raw-aiosqlite gewechselt werden, falls Profiling das nahelegt (Konservativer Default: SQLAlchemy überall, nur messbar optimieren).

**Migration-Tool:** Alembic (natürlich mit SQLAlchemy gepaart). Batch-Mode aktivieren für SQLite-ALTER-Limits. `alembic_version`-Tabelle ist Schema-Migration-Versions-Counter (schließt Readiness-Gap).

**Kern-Schema (Tabellen):**

| Tabelle | Zweck |
|---|---|
| `devices` | Konfigurierte HA-Entities + Device-Template-Zuordnung |
| `control_cycles` | Ringpuffer letzte 100 Regelzyklen (FR31) |
| `events` | Ringpuffer letzte 20 Fehler/Warnungen (FR32) |
| `latency_measurements` | Pro-Device E2E-Latenz-Rohdaten (FR34), 30-Tage-Retention |
| `kpi_daily` | Rollup pro Tag (kWh selbst verbraucht, selbst gesteuert, Euro-Wert) |
| `kpi_monthly` | Rollup pro Monat (Stats-Tab-Basis) |
| `templates_meta` | Installierte Device-Templates + Version |
| `license_state` | Lizenz-Token, letzte Validierung, Grace-Counter, Disclaimer-Accepted |
| `schema_migrations` (via `alembic_version`) | Aktueller Schema-Stand |

**KPI-Aggregation:** Rollup-Tabellen + materialisierte Tages-/Monatsaggregate via Nightly-Job (00:05 lokale Zeit). Rollup-Cost ca. 4 KB/Tag. Live-`SUM` über 30 Tage wäre am Pi-4-Budget.

**WAL-Mode + Backup:** `PRAGMA journal_mode=WAL` aktivieren. Backup-Semantik = `VACUUM INTO '/data/.backup/vX.Y.Z/solarbot.db'` — atomisch, transaktional-konsistent, blockiert kurz aber garantiert ein lesbares Snapshot-File ohne File-Copy-Race.

**Retention:** Ringpuffer via `ORDER BY id DESC LIMIT 100` + Nightly `DELETE WHERE id NOT IN (SELECT id FROM … LIMIT 100)`. Latency-Messungen 30 Tage. KPIs ewig (Speicher vernachlässigbar).

### Authentication & Security

**Lizenz-Signatur:** Ed25519 (Curve25519 EdDSA) via `cryptography`-Library. Kleine Keys (32 B), schnelle Verifikation auf Pi 4. Private-Key bleibt bei Alex (lokal/offline), `public_key.pem` wird ins Add-on-Image gebacken.

**Lizenz-Payload:**
```json
{
  "license_id": "uuid",
  "customer_email": "user@example.com",
  "valid_until": "2027-04-21T00:00:00Z",
  "features": ["core", "multi-device"],
  "issued_at": "2026-04-21T10:00:00Z"
}
```
Datei `/data/license.json`: Payload + `signature` (Base64 Ed25519-Signatur über den canonical-JSON-Payload).

**LemonSqueezy-Integration:** HTTPS-only. Monatliche GET `/licenses/validate` mit Token. Re-Validation-Failures → `license_state.grace_counter_days` hochzählen; bei Erreichen von 14 Tagen (NFR12) Funktions-Drossel aktivieren mit sichtbarem Banner und weiter Betrieb.

**Egress-Whitelist:** Harter Code-Audit und CI-Test verifiziert: einziger ausgehender HTTP-Endpunkt = `*.lemonsqueezy.com`. Erfüllt NFR17 (Readiness-Finding F-6).

**Disclaimer-Checkbox:** Vor Lizenz-Aktivierung im Wizard. Persistenz in `license_state.disclaimer_accepted_at` (nullable Timestamp).

**CSRF / CORS:** FastAPI default `same-origin`. HA-Ingress-Proxy liefert `X-Ingress-Path`-Header, iframe-Origin = HA-Host-Origin. Kein CORS-Middleware nötig, kein CSRF-Token-Layer.

**Supervisor-Token-Handling:** Aus Env-Var `SUPERVISOR_TOKEN` beim Container-Start, in Memory halten, nicht persistieren. Bei Ablauf (Supervisor-Rotation) → Reconnect-Flow neu triggern.

### API & Communication Patterns

**W-4 Resolution — Hybrid WebSocket + REST:**

| Kanal | Use-Case |
|---|---|
| **REST** (FastAPI-HTTP-Endpunkte) | Setup-Wizard-Schritte, Device-Config-CRUD, Bezugspreis-Update, Funktionstest-Trigger, Diagnose-Export, Lizenz-Aktivierung, Backup/Restore-Actions |
| **WebSocket** (`/ws` Endpoint) | Live-Sensor-Deltas, Regelungs-Modus-Updates, KPI-Live-Ticker, Funktionstest-Live-Chart (5-s-Fenster), Energy-Ring-Atmen, Flow-Animation-Partikel-Takt, Idle-State-Signale |

**Begründung:** Ohne WS reißt die Design-Quality (NFR26), Flow-Animation-60fps, Idle-State-Atmen, Funktionstest-Dramatik. REST-Only wäre 2-s-Polling und würde das 2-s-TTFD schlucken. „WS-Live-Stream ist nicht kippbar, wenn Design-Quality-Ziele erreicht werden sollen" (W-4 Readiness-Empfehlung).

**API-Design:** REST nach RFC 7807 (Problem Details für Fehler), OpenAPI 3.1 via FastAPI-Autogenerierung.

**TS-Client:** `openapi-typescript` erzeugt reine TS-Types. Dünner `fetch`-Wrapper in `frontend/src/lib/api/` (ca. 20–30 Zeilen). Kein SvelteKit-spezifischer Generator (Apity etc.), weil die bringen Annahmen mit, die wir nicht haben.

**WebSocket-Event-Format:** JSON, versioniert. Struktur:
```json
{ "event": "sensor.update", "v": 1, "ts": "...", "data": { ... } }
```
Clientseitig Discriminated Union via TS (`type Event = SensorUpdate | ModeChange | KpiTick | …`). MessagePack wäre 30 % kleiner, aber Debugging-Last für Solo-Dev nicht verhältnismäßig.

**Error-Format:** RFC 7807 `application/problem+json`. FastAPI-Middleware konvertiert Exceptions einheitlich.

**Internal Pub/Sub (Backend):** In-Process Event-Bus via `asyncio.Queue` + Subscription-Dict (`Dict[event_type, List[asyncio.Queue]]`). Kein Redis, kein externer Broker. Das WebSocket-Endpoint subskribiert sich an diesem Bus, der Regel-Controller publiziert.

**HA-WebSocket-Reconnect:** Exponential Backoff 1 s → 2 s → 4 s → max 30 s, persistente Subscription-Liste, Re-Subscribe nach Reconnect (bereits im PRD fixiert).

### Frontend Architecture

_Details zu Komponenten-Struktur, View-Organisation und Design-Tokens folgen in Step 5 (Patterns) und Step 6 (Structure). Hier nur High-Level-Rahmen._

**State-Management:** Svelte 5 Runes primär (`$state`, `$derived`, `$effect`). Svelte-Stores (`writable` / `readable`) nur für Cross-View-Subscriptions:

- WebSocket-Live-Stream-Store (alle Views hören)
- Theme-Store (HA-Dark/Light-Mode-Signal)
- i18n-Store (v1: Deutsch fest, v2-ready)
- License-State-Store (aktives Feature-Gating)

**Routing:** `svelte-spa-router` (Hash-basiert, `#/dashboard`, `#/wizard/1`, `#/diagnose`, `#/stats`). Ingress-URL-agnostisch, weil der Supervisor die Base-URL runtime injiziert.

**API-Layer:** `frontend/src/lib/api/` = generierte OpenAPI-Types + Custom `fetch`-Wrapper mit einheitlichem Error-Handling (RFC 7807 → Svelte-Toast-Message).

**WebSocket-Client:** `frontend/src/lib/ws/` — Reconnect-Logik, Exponential Backoff, Subscription-Registry, typisierte Event-Dispatcher. Muss HA-Reload robust überleben.

**Design-Token-Layer:** Tailwind 4 Config + CSS Custom Properties. ALKLY-Tokens (`--color-accent-primary`, `--font-sans`, `--radius-card`, …) in `:root` + modus-spezifisch in `[data-theme="dark"]`. HA-Theme-Signal triggert Attribut-Setzen am `<html>`-Tag.

### Infrastructure & Deployment

**CI/CD:** GitHub Actions. Pipeline:
1. Lint (ruff + mypy + eslint + svelte-check)
2. Tests (pytest + vitest)
3. Frontend-Build (Vite → `frontend/dist/`)
4. Multi-Arch-Docker-Build (`docker buildx` für amd64 + aarch64, QEMU für arm64)
5. GHCR-Push
6. Release-Tag triggert Add-on-Store-Publish

**Release-Pattern:** Semver-Tags (`vX.Y.Z`). Pre-Release-Tags (`v1.0.0-beta.1`) für Beta-Tester. `CHANGELOG.md`-Check im CI (PR ohne Changelog-Eintrag → fail). 

**Logging:** `structlog` mit JSON-Renderer + `logging.handlers.RotatingFileHandler` (10 MB / 5 Files) unter `/data/logs/` (NFR36). Alle Exceptions mit Kontext. Add-on-Log-Panel zeigt stdout zusätzlich.

**Observability:** Add-on-Log-Panel (Standard) + Diagnose-Export als versioniertes JSON (`solarbot-diag-v1.json`, FR35) + optional Health-Endpoint `/api/health` für HA-Binary-Sensor-Integration. Zero Telemetry (NFR17).

**Rollback:** Manueller Pfad via Add-on-Store + `.backup/`-Auto-Restore beim Start. WAL-Mode-Backup ist versions-tolerant (`VACUUM INTO` = Standard-SQLite-Format, jede Version liest). Alembic-Version im Restored-File ist Autorität für das Schema, das der alte Add-on-Build erwartet.

**Schema-Migration-Versions-Counter:** Alembic `alembic_version`-Tabelle. Bei Rollback auf ältere Add-on-Version → Alembic-Downgrade-Pfad explizit in jeder Migration pflegen (Forward + Backward).

### Decision Impact Analysis

**Implementation Sequence (Dependency-optimiert):**

1. **Bootstrap** (Story 1.1) — Monorepo, `uv init`, `npm create vite`, `addon/config.yaml`, Dockerfile, Multi-Arch-GHA-Workflow
2. **Schema v0 + Alembic + WAL-Mode** (Story 1.2/1.3) — erste Migration, `schema_migrations`-Tabelle, Init-Logik
3. **HA-WebSocket-Adapter** (`backend/src/solarbot/ha_client.py`) — Subscribe + Exponential-Backoff-Reconnect
4. **Device-Template-Schema + Hoymiles-Referenz-Template** — Template-Loader + erstes konkretes Template
5. **Controller-Core + Executor** (Readback-Loop + Fail-Safe + Rate-Limit) — jetzt erst die Regelung, alle Voraussetzungen sind da
6. **Setup-Wizard-REST-API** + Frontend-Wizard-Views (inkl. Live-Werte-Subscription)
7. **Dashboard-WebSocket-Stream** + Energy-Ring + Euro-Hero + Flow-Animation
8. **LemonSqueezy-Integration** + Disclaimer-Checkbox + Grace-Counter
9. **Diagnose-Tab** + Latency-Measurement-Visualisierung + Export
10. **Update/Backup/Rollback** (Epic 6) — `VACUUM INTO` + Alembic-Downgrade-Pfad

**Cross-Component Dependencies:**

- **DB-Schema ↔ Alle Epics:** Jede persistierende Story braucht Alembic-Migration-Eintrag (Forward + Backward)
- **WS-Event-Protokoll ↔ Frontend-Types:** Breaking-Change → Versioned-Event-Type-Bump (`v: 2`), Client toleriert beide Versionen während Transition
- **Device-Template-Schema ↔ Adapter-Modules:** Template-Schema-Change erfordert Review aller `adapters/*.py`
- **Ed25519-Public-Key ↔ Build-Pipeline:** Public-Key-Rotation wäre v2-Breaking-Change, muss versioned-and-fallback-fähig gebaut werden
- **Alembic-Migration ↔ `VACUUM INTO`-Backup:** Vor jedem Update-Apply = Backup; bei Rollback liest alte Add-on-Version das neue Schema-Level nicht, daher Alembic-Downgrade vor Restore
- **Egress-Whitelist ↔ CI-Test:** Jeder neue Outbound-HTTP-Call ohne Whitelist-Eintrag → CI-Fail

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

14 identifizierte Konflikt-Zonen zwischen AI-Agents / Dev-Sessions: DB-Naming, API-Routen, JSON-Case, Event-Schema, Component-Organisation, Error-Format, Log-Level, Retry-Logik, Test-Location, Date-Format, Null-Handling, WS-Subscribe-Pattern, Config-Files, Svelte-Store-vs-Rune-Regel.

### Naming Patterns

**Database (SQLite via SQLAlchemy):**
- Tabellen: `snake_case`, **plural** (`devices`, `control_cycles`, `latency_measurements`)
- Spalten: `snake_case` (`device_id`, `created_at`)
- Foreign Keys: `<parent_singular>_id` (`device_id`, nicht `fk_device`)
- Indexes: `idx_<table>_<columns>` (`idx_control_cycles_device_id_ts`)
- Primary Keys: immer `id` (INTEGER AUTOINCREMENT)
- Timestamps: `created_at`, `updated_at` als UTC TIMESTAMP

**Python Code (PEP 8 strict):**
- Files: `snake_case.py`, **singular** für Module (`device.py`, `controller.py`); `__init__.py` für Packages
- Functions/Variables: `snake_case` (`get_device_state`, `active_mode`)
- Classes: `PascalCase` (`DeviceController`, `HaClient`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_RATE_LIMIT_PER_MIN = 1`)
- Private: `_leading_underscore`
- Type aliases: `PascalCase` (`type DeviceId = str`)

**Svelte / TypeScript:**
- Components: `PascalCase.svelte` (`EuroHero.svelte`, `WizardStep.svelte`)
- Non-Component-Files: `camelCase.ts` (`wsClient.ts`, `apiClient.ts`)
- Functions/Variables: `camelCase` (`subscribeToSensor`, `activeMode`)
- Types/Interfaces: `PascalCase` (`type SensorUpdate`, `interface DeviceConfig`)
- CSS-Classes: `kebab-case` (Tailwind + custom), Data-Attrs `data-kebab-case`
- Stores: `camelCase` mit `$`-Convention in Usage (`$wsStream`, `$theme`)

**API Endpoints (REST, FastAPI):**
- Plural, kebab-case-fähige Path-Segmente: `/api/v1/devices`, `/api/v1/control-cycles`
- Versionierung: `/api/v1/...` im Pfad
- Route-Params: `{device_id}` (FastAPI-Style, snake_case matching Python)
- Query-Params: `snake_case` (`?from_date=...&to_date=...`)
- Custom Headers: `X-Solarbot-Version`, `X-Event-Source`

**WebSocket Events:**
- Event-Name: `dot.notation`, singular Verb (`sensor.update`, `mode.change`, `cycle.complete`, `kpi.tick`, `error.occurred`)
- Struktur (immer): `{event: string, v: number, ts: ISO8601, data: object}`
- Versioniert via `v` — bei Breaking-Change `v: 2`, Server emittiert beide Varianten während Transition-Window
- Subscribe-Message: `{type: "subscribe", topics: ["sensor.*", "mode.*"]}`

### Structure Patterns

**Backend-Organisation (by feature, nicht by type):**

```
backend/src/solarbot/
├── __init__.py
├── main.py              # FastAPI-App-Entry
├── config.py            # pydantic-settings
├── api/                 # REST-Endpunkte
│   ├── routes/
│   └── schemas/         # pydantic request/response models
├── ws/                  # WebSocket-Endpoint + Event-Dispatcher
├── ha_client/           # HA-WebSocket-Adapter
├── controller/          # Core-Regelung (hardware-agnostisch)
├── executor/            # Command-Dispatch + Readback + Rate-Limit
├── adapters/            # Ein Modul pro Hersteller (NFR35)
│   ├── base.py          # Abstract Adapter
│   ├── hoymiles.py
│   ├── anker_solix.py
│   ├── marstek_venus.py
│   ├── shelly_3em.py
│   └── generic.py
├── persistence/         # SQLAlchemy-Models + Repositories
│   ├── models.py
│   └── repositories/
├── license/             # Ed25519-Verify, LemonSqueezy-Client, Grace-Counter
├── events/              # In-Process Pub/Sub Bus
├── templates/           # Device-Template-Loader + JSON-Schema-Validation
├── kpi/                 # Attribution, Rollup-Jobs
├── diagnose/            # Export-Builder, Latency-Analysis
└── common/              # Logging, Clock, IDs, Types (shared)

backend/tests/
├── unit/                # Mirror of src structure
└── integration/         # Mock-HA-WS, DB-Fixtures
```

**Frontend-Organisation:**

```
frontend/src/
├── app.css              # Tailwind + ALKLY-Tokens + CSS Custom Properties
├── main.ts              # App-Entry
├── App.svelte           # Root mit Router
├── lib/
│   ├── api/             # openapi-ts Types + fetch-Wrapper
│   ├── ws/              # WebSocket-Client mit Reconnect
│   ├── stores/          # Cross-View Svelte-Stores (ws, theme, i18n, license)
│   ├── components/      # Reusable (Button, Card, EnergyRing, EuroHero, ModeBadge)
│   ├── utils/           # format.ts, time.ts, hysteresis.ts
│   └── tokens/          # ALKLY-Token-Definition (TS-typsicher)
├── routes/              # Top-Level-Views (nicht file-routing)
│   ├── Dashboard.svelte
│   ├── Wizard/
│   ├── Diagnose.svelte
│   └── Stats.svelte
└── static/
    └── fonts/           # DM Sans WOFF2 (Latin + Latin-Extended, 4 Weights)
```

**Test-Location:** Backend `backend/tests/` (nicht co-located); Frontend `src/**/*.test.ts` co-located + `e2e/` für Playwright.

**Config-Files (Root):** `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `alembic.ini`, `tsconfig.json`, `vite.config.ts`, `tailwind.config.ts`, `.ruff.toml`, `.mypy.ini`.

### Format Patterns

**API Response (Success):** direktes Objekt, kein Wrapper:

```json
{ "id": 1, "type": "hoymiles", "entity": "number.opendtu_limit" }
```

Kein `{data: ..., error: ...}`-Hüllenformat.

**API Response (Error, RFC 7807):**

```json
{
  "type": "https://solarbot.alkly.de/errors/device-not-found",
  "title": "Device not found",
  "status": 404,
  "detail": "No device configured with id=42",
  "instance": "/api/v1/devices/42"
}
```

**JSON-Field-Case:** **`snake_case` end-to-end.** Kein Boundary-Transform. Python-nativ, TS toleriert snake_case ohne Friktion, `openapi-typescript` erzeugt exakt matchende Types. Vermeidet Übersetzungs-Layer-Bugs bei Solo-Dev.

**Date/Time-Format:**
- Storage/API: ISO-8601 UTC mit `Z`-Suffix (`2026-04-21T10:00:00Z`)
- Intern (Python): `datetime` mit `tzinfo=UTC`, nie naiv
- UI: lokale Zeit nur in der Render-Schicht via `Intl.DateTimeFormat('de-DE')`

**Boolean:** JSON `true`/`false` · DB INTEGER `0`/`1` (SQLite-Konvention) · SQLAlchemy-Bool-Type macht das transparent.

**Null-Handling:** Expliziter `null`-Value statt fehlendes Feld. Pydantic `Optional[...]` · TS `T | null` (nicht `T | undefined`).

### Communication Patterns

**WebSocket Server-to-Client:**
- Event-Schema fix: `{event, v, ts, data}`
- Keine Raw-Payloads, keine unversioned Nachrichten
- Fehler-Signalisierung im WS-Kanal: `{event: "error.occurred", v: 1, data: {code, message}}`, bricht Connection nicht ab

**WebSocket Client-to-Server:**
- Nur Subscribe/Unsubscribe, keine Actions (alle Actions = REST-Calls)
- `{type: "subscribe", topics: [...]}`, `{type: "unsubscribe", topics: [...]}`

**Internal Pub/Sub (Backend):**
- `asyncio.Queue` pro Subscription, event-type-keyed Dictionary
- Publisher: `await bus.publish(SensorUpdate(device_id=..., value=...))`
- Events als Pydantic-BaseModel (typ-sicher, deserialisierbar)
- Kein direct-import zwischen Feature-Modulen für Cross-Module-Events — immer über Bus

**State Management (Svelte):**
- Runes: **immutable reassignment** statt Mutation (`$state.items = [...$state.items, x]`, nicht `$state.items.push(x)`)
- Stores: immer via `update()` oder `set()`, nie direct-mutation
- Komponenten-State: Rune. Cross-Komponenten-State: Store. Klarer Cut.

### Process Patterns

**Error Handling:**
- Backend: Global Exception-Middleware → RFC 7807 JSON. `HTTPException` für bekannte 4xx, generische Exception-Catcher für 5xx mit `logger.exception()`
- Frontend: API-Client wirft typed `ApiError` (Discriminated Union) → Top-Level-ErrorBoundary zeigt Toast + Fallback-View. Unerwartete Errors loggen in `console.error` + melden an internen Error-Store (Diagnose-Tab sichtbar)
- **User-facing-Regel:** Jede Fehlermeldung enthält Handlungsempfehlung (PRD „Keine roten Fehler ohne Kontext"-Anti-Pattern)

**Retry-Policies:**
- **HA-WebSocket-Reconnect:** Exponential Backoff 1→2→4→max 30 s, persistente Sub-List (PRD-fixiert)
- **LemonSqueezy-Lizenz-Check:** Ein Retry nach 5 s bei Netz-Fehler, dann Grace-Counter inkrementieren (kein Dauer-Retry)
- **HA-Service-Call (Write):** Kein Retry in v1. Failure → Event loggen, Fail-Safe triggern (letztes Limit halten). Retry wäre EEPROM-Risiko.
- **Alle anderen Internals:** Kein Retry. Fail-fast.

**Loading States:**
- Komponenten-lokal via `{#await}` oder `$state: loading = true/false`
- Global nur für full-screen-Transitions (Wizard-Step-Change)
- Skeleton-States mit grauem Pulse, nie Spinner-Only (PRD-Anti-Pattern)
- Skeleton-Display erst ab 400 ms Delay (kurze Loads blitzen nicht auf)

**Logging (strukturiert, JSON):**
- Framework: `structlog` mit JSON-Renderer
- Pflicht-Felder: `timestamp`, `level`, `module`, `message`, `correlation_id` (per-request/-cycle)
- Kontext-Felder (wenn anwendbar): `device_id`, `cycle_id`, `event_source` (`solarbot|manual|ha_automation`)
- Level-Regeln:
  - `DEBUG` — Inner-Loop-Details (nicht im Default-Log)
  - `INFO` — State-Transitions, Modus-Wechsel, Cycle-Summary, Reconnect-Success
  - `WARNING` — Readback-Mismatch, Rate-Limit-Treffer, Reconnect-Versuch
  - `ERROR` — Unerwartete Exceptions, Failed Control-Commands
  - `CRITICAL` — Fail-Safe entered, Datenkorruption-Risiko
- Default-Level: `INFO` (Prod), `DEBUG` via ENV `SOLARBOT_LOG_LEVEL`

**Validation:**
- Pydantic am Boundary (Request-Deserialisierung) — fail-early
- Database-Layer vertraut Pydantic-validierten Input (kein Double-Validation)
- Svelte: `zod` optional für Form-Validation; OpenAPI-Types als Primär-Source-of-Truth

**Authentication-Flow:**
- HA-Ingress-Request → Supervisor injects `X-Ingress-Token` + authentifizierten User-Context
- Backend-Middleware: `SUPERVISOR_TOKEN` bei HA-WS-Calls (einmalig beim Connect)
- License-State-Middleware: Blockiert API-Schreib-Endpunkte, wenn `license_state.grace_expired = true`; Read-Endpoints bleiben zugänglich (Read-only-Fallback)

### Enforcement Guidelines

**Jede Implementierung (AI-Agent oder manuell) MUSS:**

1. **snake_case überall** (DB, Python, API-JSON, WS-Events) — einziger Case im System
2. **Ein Modul pro Device-Template** in `adapters/` (NFR35)
3. **Alembic-Migration** für jede Schema-Änderung (Forward + Backward)
4. **Versioned WS-Events** — niemals unversioniert, niemals in-place-Schema-Change
5. **RFC 7807** für alle API-Errors
6. **structlog** für alle Logs, nie `print()`, nie plain `logging.info()` ohne structlog-Binding
7. **Closed-Loop-Readback** für jeden Write-Command im Executor (non-verhandelbar, Safety)
8. **Events via In-Process-Bus** publizieren, nie direct-import zwischen Feature-Modulen
9. **openapi-typescript** regenerieren bei API-Schema-Change — CI prüft Drift
10. **Egress-Whitelist halten** — kein neuer Outbound-HTTP ohne Review

**CI-Enforcement:**
- Ruff + MyPy strict + pytest (Backend)
- ESLint + svelte-check + prettier + vitest (Frontend)
- OpenAPI-Schema-Diff-Check (`openapi.yaml` committed, CI regeneriert + diff)
- Egress-Whitelist-Test: Mock-HTTP-Client blockt alles außer `*.lemonsqueezy.com` und `supervisor`-local
- Alembic-Head-Check: DB-Änderung ohne Migration → CI-Fail

**Pattern-Violation-Dokumentation:**
- Single-Source: diese Architektur-Sektion bleibt Autorität
- Änderungen nur via expliziten Architecture-Amendment-Block (Datum + Begründung)
- Ausnahmen im Code mit `# pattern-exception: <reason>`-Kommentar

### Pattern Examples

**Gut (DB):**

```python
class ControlCycle(Base):
    __tablename__ = "control_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    limit_set_w: Mapped[int]
    readback_w: Mapped[int | None]
    latency_ms: Mapped[int | None]
    event_source: Mapped[str]  # solarbot | manual | ha_automation
```

**Anti (DB):**

```python
class controlCycle:                     # camelCase-Class falsch
    __tablename__ = "ControlCycle"      # PascalCase-Table falsch
    cycleId = Column(Integer)           # camelCase-Column falsch, nicht-Mapped
```

**Gut (API-Response auf `/api/v1/devices/42`):**

```json
{ "id": 42, "type": "hoymiles", "entity": "number.opendtu_limit_nonpersistent_absolute" }
```

**Anti (API-Response):**

```json
{ "data": { "deviceId": 42, "deviceType": "hoymiles" }, "success": true }
```

**Gut (WS-Event):**

```json
{ "event": "mode.change", "v": 1, "ts": "2026-04-21T10:00:00Z", "data": { "from": "speicher", "to": "drossel", "reason": "akku_voll" } }
```

**Anti (WS-Event):**

```json
{ "modeChanged": { "previousMode": "speicher", "newMode": "drossel" } }
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
solarbot/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── repository.yaml                  # Custom Add-on Repo Manifest
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml          # ruff + eslint + prettier
├── pyproject.toml                   # uv workspace (Monorepo-Wurzel)
├── uv.lock
├── package.json                     # workspace-level scripts
├── .github/
│   ├── workflows/
│   │   ├── build.yml                # Multi-Arch Docker, Lint, Test, Publish
│   │   ├── pr-check.yml             # Lint + Test on PR
│   │   └── release.yml              # Tag → Add-on-Store-Publish
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug-report.yml           # Story 4.6 — HW/Firmware-Felder + Log-/Diag-Placeholder
│   │   └── feature-request.yml
│   └── pull_request_template.md
│
├── addon/                           # HA Add-on Definition
│   ├── config.yaml                  # Add-on Manifest (Supervisor-konform)
│   ├── Dockerfile                   # Multi-Stage: frontend-build + backend-assemble
│   ├── run.sh                       # Entry-Point mit bashio (auto-restore on start)
│   ├── CHANGELOG.md                 # Add-on-Version-History
│   ├── DOCS.md                      # User-facing Add-on Documentation
│   ├── README.md
│   ├── icon.png                     # 1024×1024
│   ├── logo.png                     # 512×512
│   └── rootfs/
│       └── etc/services.d/solarbot/
│           ├── run
│           └── finish
│
├── backend/
│   ├── pyproject.toml               # uv-managed Package
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                # Migration-Dateien (Forward + Backward)
│   ├── src/solarbot/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI-Entry, uvicorn-Startup
│   │   ├── config.py                # pydantic-settings
│   │   ├── startup.py               # Init-Order: License → DB-Migrate → HA-Connect → Controller
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py        # /api/health
│   │   │   │   ├── setup.py         # Epic 2
│   │   │   │   ├── devices.py       # Epic 1/2
│   │   │   │   ├── control.py       # Epic 3/5 Runtime-State-Read, Mode-Overrides
│   │   │   │   ├── pricing.py       # Story 5.2
│   │   │   │   ├── kpi.py           # Story 5.3, Stats
│   │   │   │   ├── diagnose.py      # Epic 4
│   │   │   │   ├── license.py       # Epic 7
│   │   │   │   └── backup.py        # Epic 6
│   │   │   ├── schemas/             # pydantic request/response models
│   │   │   └── middleware.py        # Exception-Handler, License-Gate, Logging
│   │   ├── ws/
│   │   │   ├── endpoint.py          # /ws Endpoint
│   │   │   ├── dispatcher.py        # Subscription-Management
│   │   │   └── events.py            # Event-Schema-Definitions
│   │   ├── ha_client/
│   │   │   ├── client.py            # HA-WS-Client (auth, subscribe, call_service)
│   │   │   ├── reconnect.py         # Exponential-Backoff-Logic
│   │   │   └── types.py             # HA-Event-Types
│   │   ├── controller/
│   │   │   ├── core.py              # Story 3.1 — hardware-agnostisch
│   │   │   ├── drossel_mode.py      # Story 3.2
│   │   │   ├── speicher_mode.py     # Story 3.4
│   │   │   ├── multi_mode.py        # Story 3.5
│   │   │   ├── mode_selector.py     # Hysterese-Logic
│   │   │   ├── pid.py               # PID-Regler + Deadband
│   │   │   └── failsafe.py          # Story 3.7
│   │   ├── executor/
│   │   │   ├── dispatcher.py        # Command-Dispatch
│   │   │   ├── readback.py          # Closed-Loop-Verifikation
│   │   │   └── rate_limiter.py      # EEPROM-Schutz (FR19)
│   │   ├── adapters/                # NFR35 — ein Modul pro Hersteller
│   │   │   ├── base.py              # Abstract Adapter
│   │   │   ├── hoymiles.py          # OpenDTU
│   │   │   ├── anker_solix.py       # Solix E1600
│   │   │   ├── marstek_venus.py     # Venus 3E/D
│   │   │   ├── shelly_3em.py        # Smart Meter
│   │   │   └── generic.py           # Manueller Pfad
│   │   ├── templates/
│   │   │   ├── loader.py            # JSON-Schema-Validation
│   │   │   ├── detector.py          # Story 2.2 — Auto-Detection
│   │   │   └── data/
│   │   │       ├── hoymiles.json
│   │   │       ├── anker_solix.json
│   │   │       ├── marstek_venus.json
│   │   │       ├── shelly_3em.json
│   │   │       └── generic.json
│   │   ├── persistence/
│   │   │   ├── engine.py            # SQLAlchemy async engine, WAL-Mode
│   │   │   ├── models.py            # Mapped Models
│   │   │   ├── session.py           # AsyncSession Factory
│   │   │   └── repositories/
│   │   │       ├── devices.py
│   │   │       ├── control_cycles.py
│   │   │       ├── events.py
│   │   │       ├── latency.py
│   │   │       ├── kpi.py
│   │   │       └── license.py
│   │   ├── license/
│   │   │   ├── verifier.py          # Story 7.3 — Ed25519-Verify
│   │   │   ├── lemonsqueezy.py      # Story 7.4 — Re-Validation
│   │   │   ├── grace.py             # 14-Tage-Grace-Counter
│   │   │   └── public_key.pem       # Embedded
│   │   ├── events/
│   │   │   ├── bus.py               # In-Process Pub/Sub (asyncio.Queue)
│   │   │   └── schemas.py           # Event-Pydantic-Models (typ-sicher)
│   │   ├── kpi/
│   │   │   ├── attribution.py       # FR27 — Event-Source-Regel
│   │   │   ├── rollup.py            # Nightly-Aggregation
│   │   │   └── calculator.py        # Euro-Wert-Berechnung
│   │   ├── diagnose/
│   │   │   ├── export.py            # Story 4.5
│   │   │   └── analysis.py          # Story 4.4 — Latency-Stats
│   │   ├── backup/
│   │   │   ├── snapshot.py          # Story 6.2 — VACUUM INTO
│   │   │   ├── rotation.py          # letzte 5 Stände
│   │   │   └── restore.py           # Story 6.3 — Auto-Restore
│   │   └── common/
│   │       ├── logging.py           # structlog-Setup
│   │       ├── clock.py             # UTC-Wrapper, monotonic
│   │       ├── ids.py               # UUID, Correlation-IDs
│   │       └── types.py             # Shared Type Aliases
│   └── tests/
│       ├── unit/                    # Mirror of src/
│       ├── integration/
│       │   ├── mock_ha_ws/          # Mock-HA-WS Fixture
│       │   └── test_e2e_flow.py
│       └── conftest.py
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── index.html
│   ├── src/
│   │   ├── app.css                  # Tailwind + ALKLY-Tokens + CSS Custom Properties
│   │   ├── main.ts                  # Vite-Entry
│   │   ├── App.svelte               # Root + svelte-spa-router
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── client.ts        # fetch-Wrapper
│   │   │   │   ├── types.ts         # openapi-typescript generated
│   │   │   │   └── errors.ts        # RFC 7807 handling
│   │   │   ├── ws/
│   │   │   │   ├── client.ts        # WS-Client + Reconnect
│   │   │   │   ├── subscriptions.ts # Topic-Registry
│   │   │   │   └── types.ts         # Event-Discriminated-Union
│   │   │   ├── stores/
│   │   │   │   ├── wsStream.ts      # Live-Stream-Store
│   │   │   │   ├── theme.ts         # HA-Dark/Light-Signal
│   │   │   │   ├── i18n.ts          # Story 1.7
│   │   │   │   └── license.ts       # License-State-Store
│   │   │   ├── components/
│   │   │   │   ├── primitives/      # Button, Card, Input, Stepper
│   │   │   │   ├── layout/          # Shell, Nav, Footer
│   │   │   │   ├── charts/          # EnergyRing, FlowAnimation, LineChart
│   │   │   │   ├── dashboard/       # EuroHero, ModeBadge, IdleState, CharacterLine
│   │   │   │   ├── wizard/          # WizardStep, SensorLiveValue, FunctionalTestDramatik
│   │   │   │   └── diagnose/        # CycleTable, ErrorList, ConnectionStatus
│   │   │   ├── utils/
│   │   │   │   ├── format.ts        # Euro, kWh, SoC
│   │   │   │   ├── time.ts          # Intl.DateTimeFormat-Wrapper
│   │   │   │   └── a11y.ts
│   │   │   └── tokens/
│   │   │       ├── colors.ts
│   │   │       ├── spacing.ts
│   │   │       └── typography.ts
│   │   ├── routes/
│   │   │   ├── Dashboard.svelte
│   │   │   ├── Wizard/
│   │   │   │   ├── index.svelte
│   │   │   │   ├── Step1Hardware.svelte
│   │   │   │   ├── Step2Detection.svelte
│   │   │   │   ├── Step3Battery.svelte
│   │   │   │   ├── Step4SmartMeter.svelte
│   │   │   │   ├── Step5FunctionalTest.svelte
│   │   │   │   ├── Step6Disclaimer.svelte
│   │   │   │   └── Step7Activation.svelte
│   │   │   ├── Diagnose.svelte
│   │   │   ├── Stats.svelte
│   │   │   └── Settings.svelte
│   │   └── locales/
│   │       └── de.json              # i18n (Story 1.7)
│   ├── static/
│   │   ├── fonts/                   # DM Sans WOFF2, Latin + Latin-Extended, 4 Weights
│   │   │   ├── DMSans-Regular.woff2
│   │   │   ├── DMSans-Medium.woff2
│   │   │   ├── DMSans-SemiBold.woff2
│   │   │   └── DMSans-Bold.woff2
│   │   └── icons/                   # Custom PV-Ikonographie
│   ├── tests/e2e/                   # Playwright (post-MVP Launch-Gate)
│   └── dist/                        # Build-Output (gitignored)
│
└── docs/                            # Legacy + Developer-Docs
    ├── architecture.md              # Copy/Symlink aus _bmad-output/
    ├── api.md                       # OpenAPI-Referenz
    └── development.md
```

### Architectural Boundaries

**API Boundaries (einziger externer Backend-Service-Layer):**

| Endpoint | Zweck | Epic |
|---|---|---|
| `GET /api/health` | Health-Check für HA-Binary-Sensor | Epic 1 |
| `POST /api/v1/setup/detect` | Auto-Detection via Templates | Story 2.2 |
| `POST /api/v1/setup/test` | Funktionstest (Readback) | Story 2.3 |
| `GET/POST /api/v1/devices` | Device-CRUD | Epic 1/2 |
| `GET /api/v1/control/state` | Runtime-Status (Modus, Zyklus) | Epic 3/5 |
| `GET/PUT /api/v1/pricing` | Bezugspreis | Story 5.2 |
| `GET /api/v1/kpi/{daily,monthly,live}` | KPI-Read | Story 5.3 |
| `GET /api/v1/diagnose/{cycles,errors,status,latency}` | Diagnose-Read | Epic 4 |
| `POST /api/v1/diagnose/export` | Strukturierter Export | Story 4.5 |
| `GET/POST /api/v1/license/{status,activate}` | Lizenz-Flow | Epic 7 |
| `POST /api/v1/backup/{create,restore}` | Backup-Ops | Epic 6 |
| `WS /ws` | Live-Stream (Subscribe) | Epic 3/5 |

**Component Boundaries (Frontend):**

- **Routes** kommunizieren niemals direkt mit API/WS — immer via `lib/api/` oder `lib/stores/`
- **Primitives** (Button, Card, …) sind stateless und domain-neutral
- **Feature-Components** (`dashboard/`, `wizard/`, `diagnose/`) sind stateful und dürfen Stores lesen
- **Charts** sind stateless-reactive auf Prop-Input
- **Stores** sind die einzige Cross-Component-Kommunikation (Runes intern in Components)

**Service Boundaries (Backend, In-Process):**

- **Controller ↔ Executor:** nur über typisierte Command-Objekte (nicht direct-state-mutation)
- **Controller ↔ HA-Client:** nur lesend (Sensor-Subscribe). Schreiben ausschließlich via Executor.
- **Controller ↔ WS-Dispatcher:** nur via Event-Bus. Controller kennt den Dispatcher nicht.
- **Adapters ↔ alles:** statische Registry (`ADAPTERS = {...}`), pure Functions oder stateless Classes.
- **License ↔ API-Middleware:** License-State-Middleware blockt Writes bei `grace_expired`, Reads bleiben offen.

**Data Boundaries:**

- **Schema-Single-Source-of-Truth:** `persistence/models.py` — SQLAlchemy Mapped Models
- **Zugriff:** ausschließlich über `repositories/*.py` — keine direkten Query-Builds außerhalb
- **Migration:** ausschließlich Alembic, Forward + Backward in derselben Datei
- **Externe Datenquelle:** HA-WS für Sensoren + LemonSqueezy für Lizenz; sonst keine

### Requirements to Structure Mapping (Epic-Mapping)

| Epic | Betroffene Verzeichnisse | Key-Files |
|---|---|---|
| **Epic 1 — Foundation** | `addon/`, `backend/src/solarbot/{main,config,startup,ha_client}/`, `frontend/src/{app.css,App.svelte,lib/{api,ws,stores/{theme,i18n}}}`, `.github/workflows/` | `addon/config.yaml`, `addon/Dockerfile`, `addon/run.sh`, `backend/.../ha_client/client.py`, `frontend/src/app.css` (Tokens), `frontend/src/locales/de.json` |
| **Epic 2 — Wizard** | `backend/src/solarbot/{api/routes/setup,templates,adapters,executor}/`, `frontend/src/routes/Wizard/*`, `frontend/src/lib/components/wizard/*` | `setup.py`, `detector.py`, `adapters/*.py`, `Step1Hardware.svelte` … `Step7Activation.svelte` |
| **Epic 3 — Controller & Akku-Pool** | `backend/src/solarbot/{controller,executor,adapters,events,persistence/repositories/control_cycles}/` | `controller/core.py`, `drossel_mode.py`, `speicher_mode.py`, `multi_mode.py`, `mode_selector.py`, `failsafe.py`, `executor/readback.py`, `rate_limiter.py` |
| **Epic 4 — Diagnose** | `backend/src/solarbot/{diagnose,api/routes/diagnose}/`, `frontend/src/{routes/Diagnose.svelte,lib/components/diagnose}/`, `.github/ISSUE_TEMPLATE/bug-report.yml` | `diagnose/export.py`, `analysis.py`, `api/routes/diagnose.py`, `Diagnose.svelte`, `CycleTable.svelte` |
| **Epic 5 — Dashboard** | `backend/src/solarbot/{kpi,api/routes/{kpi,pricing,control},ws}/`, `frontend/src/{routes/{Dashboard,Stats}.svelte,lib/{components/{dashboard,charts},stores/wsStream}}/` | `kpi/attribution.py`, `rollup.py`, `calculator.py`, `ws/endpoint.py`, `EuroHero.svelte`, `EnergyRing.svelte`, `FlowAnimation.svelte`, `ModeBadge.svelte`, `IdleState.svelte`, `CharacterLine.svelte` |
| **Epic 6 — Update/Backup** | `backend/src/solarbot/{backup,api/routes/backup}/`, `alembic/versions/`, `addon/run.sh` (auto-restore) | `backup/snapshot.py`, `rotation.py`, `restore.py`, `alembic/env.py` |
| **Epic 7 — License** | `backend/src/solarbot/{license,api/routes/license,api/middleware}/`, `frontend/src/{lib/stores/license,routes/Wizard/{Step6Disclaimer,Step7Activation}}` | `license/verifier.py`, `lemonsqueezy.py`, `grace.py`, `public_key.pem`, `api/middleware.py`, `license.ts` (Store), `Step6Disclaimer.svelte` |

**Cross-Cutting Concerns:**

| Concern | Location |
|---|---|
| Structured Logging | `backend/.../common/logging.py` + `api/middleware.py` + `controller/core.py` (Pflicht-Binding) |
| i18n | `frontend/src/lib/stores/i18n.ts` + `locales/de.json`; Backend produziert `i18n_key` bei User-facing-Strings, nie fertige Texte |
| Design-Tokens | `frontend/src/app.css` (CSS Custom Properties) + `lib/tokens/*.ts` (TS-typsicher für Component-Props) |
| Event-Bus | `backend/.../events/bus.py` (Single-Instance, von `main.py` injected) |
| Error-Handling | Backend: `api/middleware.py` (RFC 7807); Frontend: `lib/api/errors.ts` + Root-ErrorBoundary in `App.svelte` |
| Auth / License-Gate | Backend-Middleware: `api/middleware.py`; Frontend-Store: `lib/stores/license.ts` |

### Integration Points

**Internal Communication:**

- **Backend In-Process:** Controller publiziert auf `events/bus`, WS-Dispatcher + KPI-Rollup subskribieren. Kein Redis, kein externer Broker.
- **Backend → Frontend (live):** WebSocket `/ws` → versionierte Events → Svelte `lib/stores/wsStream.ts` → Routen reagieren über Store-Subscriptions
- **Backend → Frontend (request/response):** REST `/api/v1/*` → OpenAPI-Schema → generierte TS-Types → `lib/api/client.ts` Wrapper

**External Integrations:**

| Integration | Endpoint | Zweck |
|---|---|---|
| HA WebSocket | `ws://supervisor/core/websocket` | Sensor-Subscribe + `call_service` |
| LemonSqueezy | `https://api.lemonsqueezy.com/v1/licenses/*` | Kauf + monatliche Re-Validation |
| GitHub Container Registry | `ghcr.io/alkly/solarbot-{amd64,aarch64}` | Docker-Image-Hosting |
| HA Add-on Store | HA Supervisor via Custom-Repo | Update-Distribution |

**Data Flow (Haupt-Szenarien):**

1. **Regel-Zyklus (≤ 1 s, NFR1):**
   `HA Sensor Δ → ha_client` → `events/bus publish SensorUpdate` → `controller/core consumes` → `mode_selector + policy` → `executor/dispatcher` → `adapters/<vendor> build_command` → `ha_client.call_service` → `executor/readback.verify` → `persistence.control_cycles.insert` → `events/bus publish CycleComplete` → `ws/dispatcher broadcast` → `frontend/lib/stores/wsStream` → UI update

2. **Wizard-Pfad (Epic 2):**
   `User` → `Wizard/StepX.svelte` → `lib/api/client POST /api/v1/setup/detect` → `backend/api/routes/setup` → `templates/detector` (scan `get_states`) → `adapters/*` match → Response → Frontend Live-Werte-Subscription (WS) → User bestätigt → `POST /api/v1/setup/test` → Funktionstest (Executor) → Readback-Event via WS → `Step7Activation` → `POST /api/v1/license/activate` → LemonSqueezy → Controller-Start (via `startup.py` state transition)

3. **KPI-Rollup (täglich 00:05):**
   `Scheduler (APScheduler)` → `kpi/rollup.run()` → aggregiert `control_cycles` → schreibt `kpi_daily` → `events/bus publish KpiRollupComplete` → Dashboard zieht über REST im nächsten Request

### File Organization Patterns

**Configuration Files (Root):** `pyproject.toml` (uv), `uv.lock`, `package.json`, `package-lock.json`, `alembic.ini`, `tsconfig.json`, `vite.config.ts`, `tailwind.config.ts`, `.ruff.toml`, `.mypy.ini`, `.eslintrc.cjs`, `.prettierrc`. Alle auf Root (keine verschachtelten Configs außer Tool-spezifisch).

**Source Organization:** `src/solarbot/` (Python) und `frontend/src/` beide nach **Feature**, nicht nach **Type**. Gemeinsame Utilities in `common/` (Python) bzw. `lib/utils/` (TS).

**Test Organization:**
- Backend: `backend/tests/unit/` spiegelt `src/solarbot/` 1:1, `tests/integration/` für WS-Mocks + DB-Fixtures
- Frontend: Unit co-located (`*.test.ts` neben Source), E2E in `frontend/tests/e2e/`

**Asset Organization:**
- Frontend-Assets: `frontend/static/` für Fonts + Icons (gebaut in `dist/`)
- Build-Pipeline kopiert `frontend/dist/` in Backend-Static-Serve-Dir zur Dockerfile-Build-Zeit
- Keine Laufzeit-Uploads, keine CDN

### Development Workflow Integration

**Development Server:**
- Backend: `uv run uvicorn solarbot.main:app --reload --port 8099` (außerhalb Add-on)
- Frontend: `npm run dev` (Vite auf Port 5173, Proxy zu Backend)
- Lokales HA: optional via separate HA-Dev-Instance (`docker compose -f dev/ha.yml`) — nicht Teil der Release-Pipeline

**Build Process:**
1. `npm run build` erzeugt `frontend/dist/`
2. `docker buildx build` (Multi-Arch) mit 2-Stage-Dockerfile:
   - Stage 1 `frontend-builder` (Node, optional nur lokal; in Prod-Build wird `dist/` direkt kopiert)
   - Stage 2 `backend-runtime` (HA Base-Python) kopiert `backend/` + `frontend/dist/` + installiert uv-Deps
3. `docker push ghcr.io/alkly/solarbot-{amd64,aarch64}:vX.Y.Z`
4. Release-Tag aktualisiert `repository.yaml` im Custom-Add-on-Repo

**Deployment:**
- User fügt `alkly/solarbot` als HA Custom-Repo hinzu
- HA Supervisor erkennt neue Version → User klickt Install/Update
- Add-on-Container startet `run.sh` → bashio liest `config.yaml` → `uvicorn` startet FastAPI → FastAPI servt Svelte-SPA via HA-Ingress

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
Alle Technologie-Entscheidungen sind offiziell kompatibel: SQLAlchemy 2.0 async + aiosqlite + Alembic mit WAL-Mode; FastAPI + uvicorn + Pydantic v2 auf Python 3.13; Svelte 5 Runes + Vite 7 + Tailwind 4 + `svelte-spa-router`; Alpine 3.19 + uv (Party-Mode-Validierung in Step 3); Ed25519 via `cryptography` + LemonSqueezy HTTPS; Monorepo + Multi-Arch Docker Buildx. Keine inneren Widersprüche zwischen Entscheidungen.

**Pattern Consistency:**
snake_case end-to-end trägt durch DB → API → JSON → WS-Events. Event-Bus-Pattern durchgängig (Controller publiziert, Dispatcher + KPI subscriben). Closed-Loop-Readback im Executor nie umgangen. RFC 7807 einheitliches Error-Format. Ein-Modul-pro-Device-Template (NFR35) spiegelt sich in `adapters/` + `templates/data/`.

**Structure Alignment:**
Backend-Feature-Struktur (`controller/`, `executor/`, `adapters/`) unterstützt NFR35 + Solo-Dev-30-Min-Kriterium. Monorepo mit `addon/ + backend/ + frontend/` erlaubt Single-Release-Artefakt. Event-Bus in `events/bus.py` sitzt in-Process → null Latenz-Overhead für NFR1.

### Requirements Coverage Validation ✅

**Epic-Coverage (7/7):**

| Epic | Architektur-Support |
|---|---|
| Epic 1 Foundation | ✓ `addon/`, `ha_client/`, Tokens, Branding |
| Epic 2 Wizard | ✓ `api/routes/setup.py`, `templates/detector.py`, `adapters/*`, Wizard-Views |
| Epic 3 Controller & Akku-Pool | ✓ `controller/` mit 3 Modi + `executor/` + `failsafe` + `rate_limiter` |
| Epic 4 Diagnose | ✓ `diagnose/`, `api/routes/diagnose.py`, Diagnose-Views |
| Epic 5 Dashboard | ✓ `kpi/`, `ws/`, Hero/Ring/Flow/Mode/Idle/Character-Components |
| Epic 6 Updates/Backup | ✓ `backup/` mit snapshot/rotation/restore, Alembic-Downgrade |
| Epic 7 License | ✓ `license/` mit verifier/lemonsqueezy/grace + Middleware |

**FR-Coverage (43/43):** Stichprobe-Mapping FR11/17/19/27/34/35/38/43 sauber auf konkrete Module. Kein FR ohne Arch-Location.

**NFR-Coverage:**

| NFR | Architektur-Antwort |
|---|---|
| NFR1 (≤ 1 s Regel-Zyklus) | Async-Event-Bus, Raw-aiosqlite-Option für Hot-Path, PID in-Process |
| NFR2 (≤ 2 s TTFD) | WS-Live-Stream + Rollup-Tabellen |
| NFR5/6 (RSS/CPU-Budget) | Alpine Base + FastAPI lean + SQLite embedded |
| NFR8 (Wiederanlauf < 2 min) | `startup.py` Init-Order deterministisch |
| NFR9 (24h-Dauertest) | Integration-Tests + Load-Profile-Fixture |
| NFR11 (Fail-Safe) | `controller/failsafe.py` + Executor-Veto-Recht |
| NFR12 (14-Tage-Grace) | `license/grace.py` Counter |
| NFR13 (Container-Isolation) | HA-Add-on-Sandbox |
| NFR15 (License-Sig) | Ed25519 via `cryptography` |
| NFR17 (Zero-Telemetry) | Egress-Whitelist + CI-Test |
| NFR19 (100 % lokal) | Alpine + DM Sans WOFF2 + keine CDN |
| NFR26 (Design-Quality) | Token-Layer + WS-Live + Atmen/Flow-Animation |
| NFR35 (ein Modul pro Template) | `adapters/*.py` 1:1 pro Hersteller |

### Implementation Readiness Validation ✅

**Decision Completeness:** Alle Major-Decisions mit konkreten Versionen verankert (FastAPI 0.135, SQLAlchemy 2, Alembic, Svelte 5, Vite 7, Tailwind 4, Alpine 3.19, Ed25519). Versionen durch Web-Recherche im April 2026 verifiziert.

**Structure Completeness:** Vollständiger Projekt-Tree von Root bis Leaf-Files. Alle Epic-Dateien namentlich zugeordnet. Integration-Points + externe Endpunkte dokumentiert.

**Pattern Completeness:** 14 Konflikt-Zonen identifiziert + adressiert. 10 MUST-Regeln als Hard-Enforcement. CI-Enforcement-Checks explizit benannt (OpenAPI-Diff, Egress-Whitelist-Test, Alembic-Head-Check). Konkrete Gut-/Anti-Beispiele.

### Gap Analysis Results

**Critical Gaps:** **Keine.** Alle Readiness-Report-Findings vom 2026-04-21 adressiert.

| Finding (Readiness 2026-04-21) | Auflösung in diesem Dokument |
|---|---|
| W-1 Architecture-Lücke | Steps 1–6 jetzt vollständig |
| W-4 WebSocket-vs-REST | Step 4 — Hybrid REST + WS, WS nicht kippbar |
| Gap Schema-Migration-Konzept | Step 4 — Alembic + Forward/Backward-Migrations |
| Gap Backup-Transaktions-Semantik | Step 4 — `VACUUM INTO` atomisch |
| Gap Rollback-DB-Kompatibilität | Step 4 — Alembic-Downgrade-Pfad + versions-tolerante SQLite-Files |
| F-6 / NFR17 Egress-Audit | Step 4+5 — Whitelist + CI-Test |
| Gap Device-Template-JSON-Schema | Step 6 — `templates/loader.py` + `data/*.json` pro Hersteller |
| Gap Adapter-Interface-Signatur | Step 6 — `adapters/base.py` Abstract Adapter |
| Gap DM-Sans-Pipeline | Step 6 — `frontend/static/fonts/` + Story 1.4 |

**Important Gaps (nicht blockierend, vor erstem Sprint zu klären):**

1. **Geschäftsmodell-Toggle (Trial vs. Freemium, Readiness F-5):** `config.py` Setting `license_mode: "trial" | "freemium"` + Branch-Logic in `license/grace.py` und `license/lemonsqueezy.py`. In Story 7.2/7.3 ACs aufnehmen oder als Architecture-Amendment nach Beta-Entscheidung.
2. **Scheduler:** `APScheduler` für KPI-Rollup (Nightly) + LemonSqueezy-Re-Validation (Monthly). Im `main.py`-Lifespan integriert. `backend/pyproject.toml` ergänzen.
3. **Event-Type-Registry-Konsolidierung:** WS-Events (`ws/events.py`) und Pub/Sub-Events (`events/schemas.py`) gemeinsame Source-of-Truth in `events/schemas.py` mit `to_ws_event()`-Mapper.
4. **Adapter-Abstract-Interface:** `adapters/base.py` mit Methoden `detect()`, `build_set_limit_command()`, `build_set_charge_command()`, `parse_readback()`, `get_rate_limit_policy()` — in Story 2.2 als Teil der DoD.
5. **i18n-Key-Namespacing:** Flache Dot-Notation (`"wizard.step1.title"`) — in Story 1.7 explizit festlegen.

**Nice-to-Have Gaps (keine Launch-Relevanz):**

- SBOM-Generierung via `anchore/sbom-action` (CRA-Future-Vorarbeit)
- OpenAPI `Field(examples=[...])` für besseres Swagger-UI
- `frontend/static/icons/ICONS.md` als Visual-Inventar
- `dev/ha.yml` Compose für lokale HA-Dev-Instance
- MQTT-Discovery-Stub-Directory mit README (v1.5-Vorbereitung)

### Validation Issues Addressed

Während dieser Validation wurden **keine kritischen Issues** gefunden. Die 5 Important-Gaps werden als **Story-Additions** (Story 2.2, 1.7, 7.2/7.3) oder **Architecture-Amendments** (Beta-Entscheidung) adressiert.

### Architecture Completeness Checklist

**✅ Requirements Analysis (Step 2)**
- [x] Project-Context thoroughly analyzed
- [x] Scale und Complexity assessed (HIGH)
- [x] Technical Constraints identifiziert
- [x] Cross-Cutting-Concerns gemappt (10 Punkte)

**✅ Architectural Decisions (Step 3 + 4)**
- [x] Critical Decisions dokumentiert mit Versionen
- [x] Tech-Stack vollständig spezifiziert
- [x] Integration-Patterns definiert (REST + WS Hybrid)
- [x] Performance-Considerations adressiert (Rollup-Tabellen, WAL, Event-Bus)

**✅ Implementation Patterns (Step 5)**
- [x] Naming-Conventions etabliert (snake_case durchgängig)
- [x] Structure-Patterns definiert (Feature-based)
- [x] Communication-Patterns spezifiziert (Event-Bus, versioned WS, RFC 7807)
- [x] Process-Patterns dokumentiert (Error, Retry, Loading, Logging, Auth)

**✅ Project Structure (Step 6)**
- [x] Complete Directory-Structure (bis Leaf-Files)
- [x] Component-Boundaries etabliert
- [x] Integration-Points gemappt
- [x] Requirements-to-Structure-Mapping pro Epic

### Architecture Readiness Assessment

**Overall Status:** **READY FOR IMPLEMENTATION** ✅

**Confidence Level:** **HIGH**

**Begründung:** Alle Readiness-Report-Findings adressiert (W-1 war größter Blocker). Party-Mode-Validierung der Starter-Wahl bestätigt. Epic-Mapping ist vollständig und kollisionsfrei. 10 enforceable MUST-Regeln + 5 CI-Checks für Konsistenz. Keine inneren Widersprüche, keine technologischen Inkompatibilitäten.

**Key Strengths:**
- Hardware-agnostischer Core-Controller mit statischer Adapter-Registry (skaliert auf ≥ 10 weitere Hersteller — NFR35)
- Event-Bus-Architektur entkoppelt Controller/KPI/WS → jedes Feature isoliert testbar
- `VACUUM INTO` + Alembic-Downgrade löst Rollback-DB-Problem sauber
- WAL-Mode + Rollup-Tabellen halten NFR1 + NFR2 in erreichbaren Budgets
- HA-Add-on-Base + uv-Workflow ist schnell im CI und resource-effizient im Betrieb
- snake_case end-to-end eliminiert Case-Translation-Bug-Klasse

**Areas for Future Enhancement (v1.5/v2):**
- MQTT-Discovery-Integration (v1.5)
- SetpointProvider-Konkretisierung mit realer Forecast-Quelle (v2)
- Multi-WR + Multi-Akku mit SoC-Balance (v2)
- SBOM-Generierung + CRA-Vulnerability-Process (ab 2027)
- i18n-Englisch (v2) — Infra ist ready

### Implementation Handoff

**AI-Agent + Dev-Guidelines:**

1. **Autorität:** Diese Architektur-Sektion ist Single-Source-of-Truth. Änderungen nur via explizitem Architecture-Amendment (Datum + Begründung).
2. **Pattern-Enforcement:** Die 10 MUST-Regeln aus Step 5 gelten für jede Story. CI-Checks (Egress-Whitelist, OpenAPI-Diff, Alembic-Head) sind Hard-Gates.
3. **Feature-Modul-Respekt:** Keine Cross-Module-Direct-Imports außer via Event-Bus oder via public API aus `api/`.
4. **Safety non-negotiable:** Closed-Loop-Readback + Rate-Limit + Fail-Safe ist in jeder Write-Operation Pflicht. Nie umgehen.

**First Implementation Priority (Story 1.1 Bootstrap):**

```bash
mkdir solarbot && cd solarbot
git init

# Layer 1: Repo-Wurzel (repository.yaml, README, LICENSE, .gitignore, pyproject.toml-workspace)

# Layer 2: Backend
mkdir backend && cd backend
uv init --python 3.13
uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite websockets \
       sqlalchemy alembic pydantic-settings httpx cryptography \
       structlog apscheduler
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
alembic init alembic
cd ..

# Layer 3: Frontend
mkdir frontend && cd frontend
npm create vite@latest . -- --template svelte-ts
npm i -D tailwindcss @tailwindcss/vite eslint prettier svelte-check vitest
npm i svelte-spa-router
# DM Sans WOFF2 unter frontend/static/fonts/
cd ..

# Layer 4: Add-on-Skelett
mkdir -p addon/rootfs/etc/services.d/solarbot
# addon/config.yaml nach home-assistant/addons-example
# addon/Dockerfile Multi-Stage
# addon/run.sh mit bashio
```
