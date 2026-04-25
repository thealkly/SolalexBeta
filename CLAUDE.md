# CLAUDE.md — Solalex

Projekt-spezifische Instruktionen für AI-Agents (Claude Code und andere). Gilt für jede Implementierungs-Session in diesem Repo.

**Single-Source-of-Truth für Architektur-Entscheidungen:** `_bmad-output/planning-artifacts/architecture.md` (Amendments 2026-04-22, 2026-04-23, 2026-04-25). Dieses Dokument hier ist eine kondensierte Abfrage-schnelle Referenz; bei Widerspruch gewinnt `architecture.md`.

---

## Projekt in einem Absatz

Solalex ist ein kommerzielles Home-Assistant-Add-on (Python 3.13 + FastAPI + Svelte 5 + SQLite), das Wechselrichter und Akkus sekundengenau via HA-WebSocket-API steuert. Solo-Dev-Projekt, Beta-Launch in 9 Wochen geplant, v1 mit 3 Hardware-Adaptern (Generic-Wechselrichter, Marstek Venus, Generic-Smart-Meter; Detection via HA-Capabilities). 100 % lokal, monatlicher LemonSqueezy-Lizenz-Check, keine Telemetry.

---

## 5 harte Regeln (nie verletzen)

Diese 5 Regeln überleben jede Story. Verletzung = Blocker im Code-Review.

### 1. snake_case überall

Datenbank (Tabellen, Spalten, Indexes), Python (Files, Funktionen, Variablen, Konstanten via UPPER_SNAKE), API-JSON (Feldnamen), URL-Pfade, Query-Params. **Einziger Case im ganzen System.** Kein Boundary-Transform zwischen Layern.

Ausnahmen (dürfen, weil Sprach-Konvention):
- Python-Klassen: `PascalCase`
- Svelte-Komponenten-Dateien: `PascalCase.svelte`
- TypeScript-Typen: `PascalCase`
- TS-Variablen/Funktionen: `camelCase` (aber JSON bleibt snake_case)
- CSS-Klassen: `kebab-case` (Tailwind)

### 2. Ein Python-Modul pro Adapter

Jeder Adapter bekommt exakt ein Modul unter `backend/src/solalex/adapters/<key>.py`. Day-1-Adapter in v1: `generic.py` (Wechselrichter), `marstek_venus.py` (Akku), `generic_meter.py` (Smart-Meter).

`generic.py` und `generic_meter.py` nutzen **HA-Capabilities** (Domain + `unit_of_measurement`) statt vendor-Suffix-Patterns — Detection deckt Hoymiles/OpenDTU, Trucki, ESPHome, MQTT-bridged Geräte einheitlich ab. `marstek_venus.py` bleibt vendor-spezifisch wegen Akku-Charge-Service. **Kein JSON-Template-Loader, kein JSON-Schema-Validator, kein `/data/templates/`-Verzeichnis** — gestrichen im Amendment 2026-04-22, verstärkt im Amendment 2026-04-25. Vendor-spezifisches Tuning (z. B. Hoymiles ±5 W Drossel-Deadband) ist v1.5-Scope als Subklasse, die `GenericInverterAdapter` erbt.

Alle Adapter erfüllen das `adapters/base.py` Abstract-Interface:
- `detect(ha_states) -> list[DetectedDevice]`
- `build_set_limit_command(device, watts) -> HaServiceCall` (wenn zutreffend)
- `build_set_charge_command(device, watts) -> HaServiceCall` (wenn zutreffend)
- `parse_readback(state) -> int | None`
- `get_rate_limit_policy() -> RateLimitPolicy`
- `get_readback_timing() -> ReadbackTiming` (Timeout, sync/async-Modus)

Static-Registry: `ADAPTERS = {"generic": generic, "marstek_venus": marstek_venus, "generic_meter": generic_meter}`.

Pro-Device-Override-Schema in `device.config_json` (alle Keys optional, Generic-Adapter): `deadband_w`, `min_step_w`, `smoothing_window`, `limit_step_clamp_w`, `min_limit_w`, `max_limit_w`. UI-Exposure ist v1.5-Scope.

### 3. Closed-Loop-Readback für jeden Write-Command (Safety, non-verhandelbar)

Jeder Write-Command (HA `call_service`) **muss** einen Readback-Check nach sich ziehen:

1. Kommando absetzen → Timestamp merken
2. Adapter-spezifisches Timeout-Fenster abwarten (`get_readback_timing()`)
3. State aus HA lesen → mit erwartetem Wert vergleichen
4. Mismatch → Event in `control_cycles` mit `readback_mismatch=true`, optional Fail-Safe triggern

**Keine Write-Commands ohne Readback. Keine Ausnahmen.** Wenn ein Hersteller asynchronen Readback hat (OpenDTU MQTT), modelliert das Adapter-Modul dieses Timing explizit.

Zusätzlich gelten im Executor immer:
- **Range-Check** (Limit-Wert in erlaubter Hardware-Spanne)
- **Rate-Limit** (max 1 Write/Device/Minute Default, persistent in `devices.last_write_at` — auch nach Restart)
- **Fail-Safe-Wrapper** (bei Kommunikations-Ausfall: letztes bekanntes Limit halten, nicht freigeben)

### 4. JSON-Responses ohne Wrapper

API-Antworten sind das direkte Objekt:

```json
{ "id": 42, "type": "generic", "entity": "input_number.trucki_set_target" }
```

**Nicht:**

```json
{ "data": { ... }, "success": true, "error": null }
```

Fehler folgen RFC 7807 (`application/problem+json`) — FastAPI-Middleware konvertiert Exceptions einheitlich. Direkt die Fehler-Struktur, keine äußere Hülle.

### 5. Logging via `get_logger(__name__)` aus `common/logging.py`

Kein `print()`. Kein `logging.getLogger()` direkt. Kein `logging.info()` ohne Wrapper.

`common/logging.py` exportiert einen `get_logger(name)`-Wrapper, der stdlib `logging` mit `JSONFormatter` + `RotatingFileHandler` (10 MB / 5 Files unter `/data/logs/`) initialisiert. Alle Exceptions mit Kontext (`logger.exception(...)` innerhalb `except`-Blöcken). Keine structlog-Dependency, keine Correlation-IDs in v1.

---

## Architektur-Kurzfassung (wichtigste Cuts 2026-04-22)

### Was verwendet wird

- **Backend:** FastAPI + uvicorn + raw aiosqlite (kein ORM) auf Python 3.13
- **Frontend:** Svelte 5 Runes + Vite 7 + Tailwind 4 + `svelte-spa-router`
- **Datenbank:** SQLite, WAL-Mode, `schema_version`-Row + `sql/NNN_*.sql` Forward-Only-Migrations
- **Live-Updates:** REST-Endpoint `/api/v1/control/state` + **Client-seitiges 1-s-Polling** (kein WebSocket in v1)
- **Interner Control-Flow:** **direkte Funktionsaufrufe** (`controller.on_sensor_update()` → `executor.dispatch()` → `kpi.record()` + `state_cache.update()`). Kein Pub/Sub, kein asyncio.Queue-Bus
- **Controller:** Ein Mono-Modul `controller.py` mit Enum-Dispatch (`Mode.DROSSEL | SPEICHER | MULTI`) + Hysterese-Helper + Fail-Safe-Wrapper
- **Scheduler:** `asyncio.create_task` + `sleep_until` (kein APScheduler)
- **Lizenz:** LemonSqueezy-Online-Check, Plain-JSON in `/data/license.json`, **keine kryptografische Signatur** in v1
- **Backup:** 1 Slot in `/data/.backup/solalex.db`, atomisch via `VACUUM INTO .tmp → fsync → rename → fsync(dir)`
- **Rollback:** Backup-File-Replace beim Start der vorherigen Add-on-Version (kein Alembic-Downgrade)
- **Frontend-Tokens:** CSS Custom Properties in `app.css` als Single-Source (kein `lib/tokens/*.ts`)
- **TS-Types:** handgeschrieben neben `client.ts` (kein `openapi-typescript`-Generator)

### Was explizit NICHT verwendet wird (wichtig zu wissen)

- **Kein SQLAlchemy, kein Alembic.** Raw aiosqlite mit handgeschriebenen Queries in `repositories/*.py`.
- **Kein asyncio.Queue-Event-Bus, kein Pub/Sub-Dispatch.** Direkte Funktionsaufrufe.
- **Kein WebSocket-Endpoint im Frontend** in v1. REST + Polling.
- **Kein structlog.** stdlib `logging` + `JSONFormatter`.
- **Kein APScheduler.** `asyncio.create_task`.
- **Kein Ed25519, keine `cryptography`-Dep** für Lizenzen.
- **Kein JSON-Template-Layer** für Hardware-Adapter.
- **Kein OpenAPI-Codegen.** Handgeschriebene TS-Types.
- **Kein Monorepo-Workspace-Root** (kein uv-Workspace, kein Root-`package.json`).
- **Kein `lib/tokens/*.ts`** im Frontend.
- **Kein Playwright in v1.**
- **Keine i18n-Infrastruktur in v1.** Deutsche Strings hardcoded in Svelte-Komponenten.
- **Kein `/data/templates/`-Verzeichnis.** Adapter sind Python-Module im Image.
- **Keine 5-Slot-Backup-Rotation.** Ein Slot reicht.
- **Kein Dark-Mode in v1.** Kein `[data-theme="dark"]`-Override, kein MutationObserver für HA-Theme, kein `matchMedia`-Theme-Subscribe. Light-only Token-Layer. (Amendment 2026-04-23)

---

## Hardware Day-1

- **Generischer Wechselrichter** (Hoymiles/OpenDTU, Trucki, ESPHome, MQTT, …) → `adapters/generic.py`
- **Marstek Venus 3E/D** (Akku, Kern-Segment 44 % Waitlist) → `adapters/marstek_venus.py`
- **Generischer Smart Meter** (Shelly 3EM, ESPHome SML, Tibber, MQTT, …) → `adapters/generic_meter.py`

Detection erfolgt über HA-Standardattribute (Domain + `unit_of_measurement`), nicht über vendor-spezifische Entity-ID-Patterns.

**Nicht Day-1 — auf v1.5 verschoben:**
- Anker Solix (Akku) → `adapters/anker_solix.py`
- Hoymiles-Tuning-Profile (Subklasse von Generic) → `adapters/hoymiles.py`
- Shelly-3EM-Tuning-Profile (Subklasse von GenericMeter) → `adapters/shelly_3em.py`

---

## Directory Layout (Ausschnitt)

```
solalex/
├── addon/                        # HA Add-on Definition
├── backend/                      # eigenständig, kein Workspace-Root
│   ├── pyproject.toml            # uv-managed
│   └── src/solalex/
│       ├── main.py               # FastAPI + Lifespan-Tasks
│       ├── controller.py         # Mono-Modul mit Enum-Dispatch
│       ├── executor/
│       │   ├── dispatcher.py
│       │   ├── readback.py
│       │   └── rate_limiter.py   # persistent via devices.last_write_at
│       ├── adapters/             # ein Modul pro Adapter
│       │   ├── base.py
│       │   ├── generic.py
│       │   ├── generic_meter.py
│       │   ├── marstek_venus.py
│       ├── persistence/
│       │   ├── db.py             # aiosqlite-Factory + WAL
│       │   ├── migrate.py        # schema_version + sql/-Apply
│       │   ├── sql/
│       │   │   └── 001_initial.sql
│       │   └── repositories/
│       ├── license/
│       │   ├── lemonsqueezy.py   # Online-Check
│       │   └── grace.py          # 14-Tage-Grace
│       ├── kpi/
│       │   ├── attribution.py
│       │   ├── rollup.py
│       │   └── scheduler.py      # asyncio-Task
│       ├── backup/
│       │   ├── snapshot.py       # VACUUM INTO → fsync → rename → fsync(dir)
│       │   └── restore.py        # Auto-Restore beim Start bei Schema-Mismatch
│       ├── state_cache.py        # In-Memory für Polling-Endpoint
│       └── common/
│           ├── logging.py        # stdlib + JSONFormatter (~30 Zeilen)
│           └── clock.py          # sleep_until, UTC-Wrapper
└── frontend/                     # eigenständig, kein Workspace-Root
    ├── package.json
    └── src/
        ├── app.css               # Tailwind + CSS Custom Properties (Tokens Single-Source)
        ├── lib/
        │   ├── api/              # client.ts + handgeschriebene types.ts
        │   ├── polling/          # usePolling-Hook
        │   └── stores/           # stateSnapshot, theme, license
        └── routes/
            ├── Dashboard.svelte
            └── Wizard/
                ├── Step1Hardware.svelte
                ├── Step2Detection.svelte       # Smart-Meter + Battery als Sub-Cards
                ├── Step3FunctionalTest.svelte
                └── Step4Activation.svelte
```

---

## Wizard-Struktur (4 Schritte)

1. **Step1Hardware** — Wechselrichter (allgemein) oder Marstek Venus
2. **Step2Detection** — Auto-Detection mit Live-Werten, Smart-Meter + Battery als aufklappbare Sub-Cards (Min/Max-SoC, Nacht-Entlade-Fenster hier)
3. **Step3FunctionalTest** — Live-Chart + Closed-Loop-Readback
4. **Step4Activation** — Disclaimer-Checkbox + LemonSqueezy-Kauf + Aktivieren

---

## Häufige Stolpersteine für AI-Agents

- Wenn Du SQLAlchemy-Code schreibst — **STOP**. Raw aiosqlite. Queries in `repositories/*.py`.
- Wenn Du `asyncio.Queue` für internen Pub/Sub einbaust — **STOP**. Direkter Aufruf.
- Wenn Du `structlog` importierst — **STOP**. stdlib `logging` via `get_logger(__name__)`.
- Wenn Du WebSocket-Frontend-Code schreibst — **STOP**. Polling via `lib/polling/usePolling.ts`.
- Wenn Du `cryptography` für Lizenz-Signatur importierst — **STOP**. Nur LemonSqueezy-Online-Check.
- Wenn Du JSON-Templates für Hardware-Adapter planst — **STOP**. Generic-Adapter liest keine Templates; vendor-Tuning-Profile sind Python-Subklassen (v1.5+).
- Wenn Du einen weiteren Hersteller-spezifischen WR/Smart-Meter-Adapter für Day-1 anlegen willst — **STOP**. Generic-Detection (Domain + `unit_of_measurement`) deckt fast alle HA-konformen Geräte ab. Vendor-Adapter nur für Akkus oder bei nachgewiesenen Tuning-Anforderungen (dann als Subklasse von `GenericInverterAdapter`).
- Wenn Du OpenAPI-Codegen-Setup schreibst — **STOP**. Handgeschriebene TS-Types.
- Wenn Du `APScheduler` konfigurierst — **STOP**. `asyncio.create_task` mit `sleep_until`.
- Wenn Du Wrapper-Hülle `{data: ..., success: true}` um JSON legst — **STOP**. Direkt das Objekt.
- Wenn Du Anker Solix- oder Generic-HA-Entity-Code für v1 schreibst — **STOP**. Diese kommen in v1.5.
- Wenn Du `i18n`-Wrapper (`$t('key')`) oder `locales/*.json` für v1 anlegst — **STOP**. Deutsche Strings direkt.
- Wenn Du Controller in Submodule splittest (`drossel.py`, `speicher.py`, …) — **STOP**. Ein `controller.py` mit Enum-Dispatch.
- Wenn Du ein Monorepo-Workspace-`pyproject.toml` auf Root anlegst — **STOP**. Nur `backend/pyproject.toml` + `frontend/package.json`.
- Wenn Du `lib/tokens/colors.ts` (o. ä.) im Frontend anlegst — **STOP**. CSS Custom Properties in `app.css`.
- Wenn Du `[data-theme='dark']`-Overrides oder einen HA-Theme-Observer/Subscriber baust — **STOP**. Dark-Mode gestrichen (Amendment 2026-04-23), Light-only in v1.
- Wenn Du einen `theme`-Store (`lib/stores/theme.ts`) oder `applyTheme`/`resolveThemeMode`-Funktion schreibst — **STOP**. Kein Theme-Switching in v1.

---

## CI-Gates

Solalex hat 4 Hard-CI-Gates, mehr nicht:

1. **Ruff + MyPy strict + Pytest** (Backend)
2. **ESLint + svelte-check + Prettier + Vitest** (Frontend)
3. **Egress-Whitelist-Test** (httpx-Mock blockt alles außer `*.lemonsqueezy.com`)
4. **SQL-Migrations-Ordering-Check** (`sql/NNN_*.sql` nummerisch lückenlos)

Kein OpenAPI-Diff-Check (keine Generator-Pipeline). Kein Alembic-Head-Check (kein Alembic). Kein i18n-Missing-Key-Check (kein i18n in v1).

---

## Referenzdokumente

- **Architecture (Autorität):** `_bmad-output/planning-artifacts/architecture.md` — Amendment 2026-04-22, Amendment 2026-04-23 (Dark-Mode-Cut), Amendment 2026-04-25 (Generic-First Adapter-Layer)
- **PRD:** `_bmad-output/planning-artifacts/prd.md`
- **Epics:** `_bmad-output/planning-artifacts/epics.md`
- **UX-Spec:** `_bmad-output/planning-artifacts/ux-design-specification.md`

Bei Widerspruch zwischen Dokumenten gewinnt die Architecture. Bei Widerspruch zwischen dieser CLAUDE.md und der Architecture gewinnt die Architecture.

---

## Git & Commits

- **Keine Commits ohne explizite User-Anweisung.** Alex commitet selbst oder weist explizit dazu an.
- **Proaktiver Commit-Hinweis:** Wenn ein logischer Commit-Zeitpunkt erreicht ist (Story/Task abgeschlossen, atomare Änderung fertig, Review-Patches angewendet, grüne Tests nach Refactor etc.), sag Alex in **einer Zeile** Bescheid: Scope der Änderung + Vorschlag der Commit-Message. Erst nach Alex' Bestätigung (z. B. „ja", „commit", „push") wird tatsächlich committed. Kein Commit bei unvollständigem/kaputtem Zustand vorschlagen.
- **Push folgt demselben Muster:** nie ungefragt pushen. Auf Ansage pushen; bei fehlendem Upstream kurz Branch-Namen bestätigen.
- Commit-Message-Stil: kurz, Imperativ, eine Zeile wenn möglich, ausführlicher Body bei nicht-trivialen Änderungen. Deutsche Commit-Messages sind erlaubt und üblich in diesem Repo.
- Keine sekundären Commit-Attribute wie „Co-Authored-By" ohne Rücksprache.

---

## Stil-Leitplanken für Code

- **Deutsche UI-Strings hardcoded** in Svelte-Komponenten; **Code-Kommentare auf Englisch**.
- **Zahlen im UI sind nackt** (keine emotionalen Adjektive, keine Trend-Icons ohne Anlass). Charakter-Zeilen beschreiben nur das Tun, nicht die Zahl.
- **Keine Tabellen**, **keine Modal-Dialoge**, **keine Tooltips**, **keine Loading-Spinner** (Skeleton-Pulse ≥ 400 ms). Anti-Pattern-Liste in `_bmad-output/planning-artifacts/ux-design-specification.md` (UX-DR30).
- **Keine Push-Notifications**, keine E-Mails, keine HA-Notifications — „Pull nicht Push" (NFR27).
- **Glossar verbindlich:** Akku (nicht Batterie/Speicher), Wechselrichter/WR, Smart Meter, Setup-Wizard.
