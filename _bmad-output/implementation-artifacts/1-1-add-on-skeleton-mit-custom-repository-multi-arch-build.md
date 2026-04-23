# Story 1.1: Add-on Skeleton mit Custom Repository & Multi-Arch-Build

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Entwickler,
I want ein lauffähiges HA Add-on-Gerüst im Custom Repository `alkly/solalex` mit Multi-Arch-Docker-Build,
so that Solalex über den HA Add-on Store installierbar ist und das Fundament für alle weiteren Features trägt.

## Acceptance Criteria

1. **GHA Multi-Arch Build:** `Given` das Repository `alkly/solalex`, `When` Code gepusht und getaggt wird, `Then` GitHub Actions baut Docker-Images für `amd64` + `aarch64` und publisht sie in GitHub Container Registry. **And** Release-Builds werden bei Tag-Push (`vX.Y.Z`) automatisch getriggert.
2. **Custom-Repo-Installierbarkeit:** `Given` eine HA-Instanz mit HA OS oder Supervised, `When` der Nutzer das Custom Repository in den Add-on-Store einfügt, `Then` Solalex erscheint im Store als installierbar.
3. **FastAPI + SQLite Bootstrap:** `Given` das Add-on ist installiert, `When` der Container startet, `Then` ein FastAPI-Prozess (Python 3.13) lauscht auf dem Ingress-Port **And** die SQLite-Datei `/data/solalex.db` wird initialisiert (leer, produktive Tabellen kommen in späteren Stories dazu).
4. **Svelte-Minimal-Build:** `Given` der Container läuft, `When` die Svelte-Frontend-Route aufgerufen wird, `Then` ein minimaler Svelte + Tailwind-Build lädt ohne Fehler.
5. **Persistenz-Volume:** `Given` `/data/` als Persistenz-Volume, `When` das Add-on neu gestartet wird, `Then` `/data/`-Inhalt bleibt erhalten.
6. **Ressourcen-Budget (Pi 4):** `Given` Raspberry Pi 4 als Referenz-Hardware, `When` das Add-on im Idle läuft, `Then` RSS ≤ 150 MB und CPU ≤ 2 %.
7. **Keine externen Ports:** `Given` der Container, `When` er läuft, `Then` keine externen Port-Expositionen außer HA-Ingress.

## Tasks / Subtasks

- [x] **Task 1: Monorepo-Wurzel initialisieren** (AC: 2, 7)
  - [x] `repository.yaml` mit Custom-Add-on-Repo-Manifest anlegen (Name `alkly/solalex`, Icon/Logo, Maintainer)
  - [x] Root-`README.md` (Kurz-Beschreibung, Install-Instruktion via Custom-Repo) + `LICENSE` + `CHANGELOG.md` + `.gitignore` + `.editorconfig`
  - [x] `.pre-commit-config.yaml` mit ruff + eslint + prettier vorbereiten (Stubs okay, kein Blocker)
  - [x] Verzeichnis-Skelett nach [Architektur §Project Structure](../planning-artifacts/architecture.md#complete-project-directory-structure): `addon/`, `backend/`, `frontend/`, `.github/workflows/`, `.github/ISSUE_TEMPLATE/`, `docs/`
- [x] **Task 2: Add-on-Manifest & Dockerfile** (AC: 1, 2, 3, 5, 7)
  - [x] `addon/config.yaml` nach [home-assistant/addons-example](https://github.com/home-assistant/addons-example) – Mindestfelder: `name`, `version`, `slug: solalex`, `description`, `arch: [amd64, aarch64]`, `ingress: true`, `ingress_port: 8099`, `panel_icon`, `panel_title: "Solalex by ALKLY"`, `init: false`, `hassio_api: true`, `hassio_role: default`, `ports: {}` (keine externen Ports – AC 7), `map: []` (nur `/data/` implizit), `url`, `image: ghcr.io/alkly/solalex-{arch}`
  - [x] `addon/Dockerfile` Multi-Stage nach [Architektur §Build Process](../planning-artifacts/architecture.md#development-workflow-integration):
    - Build-Arg `BUILD_FROM` = `ghcr.io/home-assistant/{arch}-base-python:3.13-alpine3.19` (Multi-Arch-Base seit 2026.03.1)
    - Stage 1 (optional lokal): `frontend-builder` mit Node, führt `npm ci && npm run build` aus → `frontend/dist/`
    - Stage 2 `backend-runtime`: `FROM ${BUILD_FROM}`, installiert `uv`, kopiert `backend/` + `frontend/dist/` in Container-Static-Verzeichnis, `uv sync --frozen`, `COPY addon/rootfs/ /` für s6-overlay-Service
    - **Nicht** s6-overlay oder bashio separat installieren – im HA-Base enthalten
  - [x] `addon/run.sh` als einfacher bashio-Entry-Point (Config lesen, `exec uvicorn solalex.main:app --host 0.0.0.0 --port 8099`)
  - [x] `addon/rootfs/etc/services.d/solalex/{run,finish}` s6-overlay-Service-Skripte
  - [x] `addon/CHANGELOG.md`, `addon/DOCS.md`, `addon/README.md`, `addon/icon.png` (1024×1024), `addon/logo.png` (512×512) – Platzhalter-Bilder okay, finale Assets aus Story 1.5
- [x] **Task 3: Backend-Skeleton (Python 3.13 + FastAPI + aiosqlite)** (AC: 3, 5, 6, 7)
  - [x] `cd backend/ && uv init --python 3.13` (nach [Architektur §Selected Starter](../planning-artifacts/architecture.md#selected-starter-komponierter-solalex-skeleton))
  - [x] `uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite websockets pydantic-settings httpx` – **kein `cryptography`** (Lizenz-Flow ist LemonSqueezy-Online-Check ohne kryptografische Signatur, Amendment 2026-04-22)
  - [x] `uv add --dev pytest pytest-asyncio pytest-cov ruff mypy httpx`
  - [x] `backend/pyproject.toml`: Build-Backend `hatchling` (nicht `uv_build` – laut Architektur experimental). Tool-Configs `[tool.ruff]`, `[tool.mypy]` (strict), `[tool.pytest.ini_options]` **hier** (nicht als eigene Dateien auf Repo-Root – es gibt keinen Workspace-Root).
  - [x] `backend/src/solalex/__init__.py`
  - [x] `backend/src/solalex/main.py`: FastAPI-App, Root-Route `GET /` → serviert Svelte-SPA-`index.html` aus `frontend/dist/`, `StaticFiles`-Mount für `/assets`
  - [x] `backend/src/solalex/config.py`: `pydantic-settings` liest `DB_PATH` (default `/data/solalex.db`), `PORT` (default `8099`), `SUPERVISOR_TOKEN` (Env, noch nicht genutzt)
  - [x] `backend/src/solalex/startup.py`: Init-Order-Stub (License → DB-Migrate → HA-Connect → Controller). Für Story 1.1 nur **DB-Init**: SQLite-Datei unter `/data/solalex.db` anlegen, `PRAGMA journal_mode=WAL` setzen. Keine produktiven Tabellen (kommen in späteren Stories).
  - [x] `backend/src/solalex/api/routes/health.py`: `GET /api/health` → `{"status": "ok"}`
  - [x] `backend/src/solalex/common/logging.py`: **stdlib `logging` + `JSONFormatter`** (~30 Zeilen) mit `RotatingFileHandler` (10 MB / 5 Files) nach `/data/logs/solalex.log`. Export `get_logger(name)` (Regel 5 CLAUDE.md). **Kein structlog**.
  - [x] `backend/tests/conftest.py` + Smoke-Test `tests/unit/test_health.py` (`GET /api/health` → 200)
- [x] **Task 4: Frontend-Skeleton (Svelte 5 + Vite 7 + Tailwind 4)** (AC: 4)
  - [x] `cd frontend/ && npm create vite@latest . -- --template svelte-ts`
  - [x] `npm i -D tailwindcss @tailwindcss/vite` (Tailwind v4 über Vite-Plugin, kein PostCSS-Config nötig)
  - [x] `npm i svelte-spa-router` (Hash-Routing, ingress-URL-agnostisch)
  - [x] `vite.config.ts`: `@tailwindcss/vite`-Plugin aktivieren, `build.outDir = 'dist'`, Base-Path `./` (relative Assets für HA-Ingress)
  - [x] `frontend/src/app.css`: `@import "tailwindcss";` + Platzhalter-Block für ALKLY-Tokens (`--color-primary` etc.) – echte Token-Definitionen kommen in Story 1.4
  - [x] `frontend/src/App.svelte`: Minimales „Solalex"-Hello-Screen, kein Branding/kein Design-System-Content (Stories 1.4–1.6)
  - [x] `frontend/src/main.ts`: Vite-Entry
  - [x] `frontend/static/fonts/` als leerer Ordner mit `.gitkeep` (WOFF2-Dateien kommen in Story 1.4)
  - [x] `frontend/tsconfig.json`, `frontend/eslint.config.js` (ESLint v9 Flat Config – **nicht** `.eslintrc.cjs`), `frontend/.prettierrc`
  - [x] Build-Smoke: `npm run build` produziert `frontend/dist/index.html` ohne Fehler
- [x] **Task 5: Multi-Arch-Build-Pipeline** (AC: 1)
  - [x] `.github/workflows/build.yml`: Jobs Lint (ruff + mypy + eslint + svelte-check) → Test (pytest + vitest) → Frontend-Build (Vite) → Multi-Arch-Docker-Build (`docker buildx` mit QEMU für arm64) → GHCR-Push
  - [x] `.github/workflows/pr-check.yml`: Lint + Test auf PR (kein Docker-Build – spart CI-Zeit)
  - [x] `.github/workflows/release.yml`: Getriggert auf `push.tags: ['v*.*.*']`, baut und publisht Images, aktualisiert `repository.yaml` (Version-Bump per bot-commit oder manuell – laut [Architektur §Deployment](../planning-artifacts/architecture.md#development-workflow-integration))
  - [x] Nutze `docker/setup-qemu-action@v3` + `docker/setup-buildx-action@v3` + `docker/build-push-action@v6`
  - [x] GHCR-Login via `${{ secrets.GITHUB_TOKEN }}`, Tags `ghcr.io/alkly/solalex-{arch}:latest` und `:${{ github.ref_name }}`
  - [x] `.github/ISSUE_TEMPLATE/feature-request.yml` als Stub (Bug-Report kommt in Story 4.6)
  - [x] `.github/pull_request_template.md` mit Changelog-Entry-Check-Hinweis
- [x] **Task 6: Ressourcen-Verifikation (Pi 4)** (AC: 6)
  - [x] Dockerfile-Build lokal (amd64) ausführen + `docker stats` im Idle messen – Zielwerte dokumentieren in `addon/DOCS.md`
  - [x] **Wenn kein Pi 4 verfügbar:** qemu-arm64-Build + Stats auf amd64-Host als Näherung. AC 6 wird final in Beta-Phase auf echtem Pi 4 validiert. Note in Completion Notes.
- [x] **Task 7: Smoke-Tests & Final Verification** (AC: 1–7)
  - [x] `pytest` lokal grün (Health-Endpoint)
  - [x] `npm run build` grün
  - [x] `docker buildx build --platform linux/amd64,linux/arm64 --target backend-runtime .` lokal erfolgreich
  - [x] README aktualisieren: Install-Instruktion „Add-on-Store → ⋮ → Repositories → `https://github.com/alkly/solalex`"

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md §Selected Starter: Komponierter Solalex-Skeleton](../planning-artifacts/architecture.md#selected-starter-komponierter-solalex-skeleton) – drei `init`-Commands, exakte Reihenfolge
- [architecture.md §Verifizierte Aktuelle Versionen](../planning-artifacts/architecture.md#selected-starter-komponierter-solalex-skeleton) – Versions-Matrix (Stand April 2026)
- [architecture.md §Project Structure](../planning-artifacts/architecture.md#complete-project-directory-structure) – komplette Directory-Struktur als Soll-Zustand
- [architecture.md §Naming Patterns](../planning-artifacts/architecture.md#naming-patterns) – snake_case end-to-end, Files-Naming, API-Routen
- [architecture.md §Infrastructure & Deployment](../planning-artifacts/architecture.md#infrastructure--deployment) – GHA-Pipeline-Stages, Release-Pattern
- [epics.md Epic 1 Story 1.1](../planning-artifacts/epics.md) – Original-AC

### Technical Requirements (DEV AGENT GUARDRAILS)

**Stack-Versionen – EXAKT verwenden, nicht upgraden:**

| Komponente | Version | Quelle |
|---|---|---|
| Python | 3.13 | FastAPI-empfohlen |
| FastAPI | 0.135.1+ | PyPI März 2026 |
| uv | 0.5+ | Astral |
| Svelte | 5 (stabil) | Runes-API |
| Vite | 7.x | - |
| Tailwind CSS | 4 (stabil) | `@tailwindcss/vite`-Plugin, **kein** PostCSS-Config |
| HA Base Image | `ghcr.io/home-assistant/{arch}-base-python:3.13-alpine3.19` | Multi-Arch (amd64/arm64) seit 2026.03.1 |
| s6-overlay + bashio | im HA-Base enthalten | **Nicht** separat installieren |

**Build-Backend:** `hatchling` in `pyproject.toml` fixieren (`uv_build` ist experimental).

### Anti-Patterns & Gotchas

- **KEIN `requirements.txt`** – Single-Source-of-Truth ist `pyproject.toml` + `uv.lock` (commited).
- **KEIN `package-lock.json` ignorieren** – committed.
- **KEIN externes Port-Expose** in `addon/config.yaml` (`ports: {}`). HA-Ingress ist einziger Zugriffspfad (AC 7, NFR28).
- **KEIN `fonts.googleapis.com` / `fonts.gstatic.com` / preconnect** im HTML – das 100%-lokal-Versprechen greift ab Story 1.1 (volle Font-Pipeline kommt in 1.4, aber **keine CDN-Requests** ab jetzt).
- **KEIN SvelteKit** – Pure Svelte-SPA. SSR funktioniert im HA-Ingress nicht (Ingress-URL ist zur Build-Zeit unbekannt).
- **KEIN Redis / externer Broker** – interne Kommunikation via direkte Funktionsaufrufe (Amendment 2026-04-22), keine asyncio.Queue, kein In-Process-Event-Bus.
- **KEIN `/data/`-Mount-Override** – HA-Supervisor mountet `/data/` automatisch, in `config.yaml` nicht extra deklarieren.
- **SQLite WAL-Mode:** `PRAGMA journal_mode=WAL` beim Init setzen (spätere Story-KPIs brauchen es; Jetzt-Setzen kostet nichts).
- **Keine produktiven Tabellen in 1.1.** Forward-Only-`sql/NNN_*.sql`-Migrations (kein Alembic) kommen in späteren Stories. Nur die leere DB-Datei anlegen.
- **KEIN `structlog`** (Amendment 2026-04-22) – `common/logging.py` ist stdlib `logging` + eigener `JSONFormatter` + `RotatingFileHandler`. Export `get_logger(name)` ist Pflicht-Entry-Point (Regel 5 CLAUDE.md).
- **KEIN `cryptography`-Dep** in 1.1 und auch nicht später – Lizenz-Flow ist reiner LemonSqueezy-Online-Check ohne Signatur-Verifikation.
- **KEIN Root-`pyproject.toml` / Root-`package.json`** – Backend und Frontend sind getrennte Projekte ohne Workspace-Root. `.ruff.toml` / `.mypy.ini` auf Repo-Root sind verboten; stattdessen `[tool.ruff]` / `[tool.mypy]` in `backend/pyproject.toml`.
- **KEIN `APScheduler`** – Scheduler-Arbeit läuft über `asyncio.create_task` + `sleep_until`-Helper (kommt in Story 1.3/3.x).
- **KEIN `SQLAlchemy` / `Alembic`** – raw `aiosqlite` mit handgeschriebenen Queries (kommt in späteren Stories).
- **Monorepo-Disziplin:** `git mv`-freundlich bleiben. Name „Solalex" steht unter Markenrechts-Vorbehalt (siehe auto-memory) – Pfade/Imports so bauen, dass ein späterer Rename via `git mv` + Search/Replace reicht.

### Source Tree – zu erzeugende Dateien (Zielzustand nach Story)

```
solalex/ (= Repo-Root)
├── README.md                           [NEW]
├── LICENSE                             [NEW]
├── CHANGELOG.md                        [NEW]
├── repository.yaml                     [NEW – Custom-Add-on-Repo-Manifest]
├── .gitignore                          [NEW]
├── .editorconfig                       [NEW]
├── .pre-commit-config.yaml             [NEW]
├── .github/
│   ├── workflows/
│   │   ├── build.yml                   [NEW]
│   │   ├── pr-check.yml                [NEW]
│   │   └── release.yml                 [NEW]
│   ├── ISSUE_TEMPLATE/
│   │   └── feature-request.yml         [NEW – Stub]
│   └── pull_request_template.md        [NEW]
├── addon/
│   ├── config.yaml                     [NEW]
│   ├── Dockerfile                      [NEW – Multi-Stage]
│   ├── run.sh                          [NEW – bashio]
│   ├── CHANGELOG.md                    [NEW]
│   ├── DOCS.md                         [NEW]
│   ├── README.md                       [NEW]
│   ├── icon.png                        [NEW – Platzhalter]
│   ├── logo.png                        [NEW – Platzhalter]
│   └── rootfs/etc/services.d/solalex/
│       ├── run                         [NEW]
│       └── finish                      [NEW]
├── backend/
│   ├── pyproject.toml                  [NEW – uv init]
│   ├── uv.lock                         [NEW – commited]
│   ├── src/solalex/
│   │   ├── __init__.py                 [NEW]
│   │   ├── main.py                     [NEW]
│   │   ├── config.py                   [NEW]
│   │   ├── startup.py                  [NEW – DB-Init only]
│   │   ├── api/
│   │   │   ├── __init__.py             [NEW]
│   │   │   └── routes/
│   │   │       ├── __init__.py         [NEW]
│   │   │       └── health.py           [NEW]
│   │   └── common/
│   │       ├── __init__.py             [NEW]
│   │       └── logging.py              [NEW]
│   └── tests/
│       ├── conftest.py                 [NEW]
│       └── unit/
│           └── test_main.py            [NEW]
├── frontend/
│   ├── package.json                    [NEW – npm create vite]
│   ├── package-lock.json               [NEW – commited]
│   ├── tsconfig.json                   [NEW]
│   ├── vite.config.ts                  [NEW]
│   ├── eslint.config.js                [NEW – ESLint v9 Flat Config]
│   ├── .prettierrc                     [NEW]
│   ├── index.html                      [NEW]
│   ├── src/
│   │   ├── app.css                     [NEW – Tailwind import + Token-Platzhalter]
│   │   ├── main.ts                     [NEW]
│   │   └── App.svelte                  [NEW – Minimal-Hello]
│   └── static/
│       └── fonts/.gitkeep              [NEW]
└── docs/                               [EXISTS – nur ggf. placeholder-Files]
```

### Library/Framework Requirements (Copy-Paste-sicher)

**Backend – `backend/pyproject.toml` Kern-Dependencies:**

```toml
[project]
name = "solalex"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]>=0.135.1",
    "uvicorn[standard]>=0.30",
    "aiosqlite>=0.20",
    "websockets>=13",
    "pydantic-settings>=2.6",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5",
    "ruff>=0.8",
    "mypy>=1.13",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/solalex"]

[tool.ruff]
line-length = 120
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "ASYNC"]

[tool.mypy]
python_version = "3.13"
strict = true
files = ["src/solalex", "tests"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Amendment 2026-04-22 – explizit NICHT in Dependencies:** `cryptography` (kein Signatur-Flow), `structlog` (stdlib-Logging + `JSONFormatter` via `common/logging.py`), `sqlalchemy` / `alembic` (raw aiosqlite), `apscheduler` (asyncio-Tasks).

**Frontend – `frontend/vite.config.ts` Muster:**

```ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: './',
  plugins: [svelte(), tailwindcss()],
  build: { outDir: 'dist' },
});
```

### Testing Requirements

- **Backend:** `pytest` + `pytest-asyncio`. Ein Smoke-Test reicht für Story 1.1 (`GET /api/health` → `200 {"status": "ok"}`). Coverage-Gate erst ab späteren Stories (Ziel ≥ 70 % Core, ≥ 50 % gesamt laut NFR35).
- **Frontend:** `vitest` Setup ist **nicht Blocker** für 1.1 – Basis-Konfiguration anlegen (`vitest.config.ts` optional), aber keine Tests Pflicht. Playwright (`frontend/tests/e2e/`) ist post-MVP.
- **Integration:** Kein Mock-HA-WebSocket nötig in 1.1 (kommt in Story 1.3).
- **CI:** `pr-check.yml` muss `ruff check`, `mypy`, `pytest`, `npm run build` ausführen.

### Project Structure Notes

- **Alignment:** Dateien werden exakt nach [architecture.md §Complete Project Directory Structure](../planning-artifacts/architecture.md#complete-project-directory-structure) angelegt. Abweichungen nur dokumentiert in Completion Notes.
- **Feature-Based Layout (nicht Type-Based):** Backend nach `controller.py`, `executor/`, `adapters/` etc. (Amendment 2026-04-22: Controller ist ein **Mono-Modul** mit Enum-Dispatch, nicht in `controller/` aufgesplittet). Für Story 1.1 legen wir nur die von AC geforderten Module an (`api/`, `common/`). Die restlichen Ordner entstehen in späteren Stories.
- **Kein Monorepo-Wurzel-Pyproject (Amendment 2026-04-22):** `backend/pyproject.toml` ist das einzige Python-Pyproject. Frontend hat sein eigenes `package.json`. **Kein** uv-Workspace, **kein** Root-`package.json`, **kein** Root-`.ruff.toml` / `.mypy.ini`. Tool-Configs leben innerhalb `backend/pyproject.toml` unter `[tool.*]`.

### References

- [architecture.md – Selected Starter](../planning-artifacts/architecture.md#selected-starter-komponierter-solalex-skeleton)
- [architecture.md – Project Directory Structure](../planning-artifacts/architecture.md#complete-project-directory-structure)
- [architecture.md – Naming Patterns](../planning-artifacts/architecture.md#naming-patterns)
- [architecture.md – Infrastructure & Deployment](../planning-artifacts/architecture.md#infrastructure--deployment)
- [architecture.md – Epic-Mapping (Epic 1)](../planning-artifacts/architecture.md#requirements-to-structure-mapping-epic-mapping)
- [prd.md – Technical Stack + NFR28 (100% lokal)](../planning-artifacts/prd.md)
- [epics.md – Epic 1 Story 1.1](../planning-artifacts/epics.md)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context, 2026-01 cutoff)

### Debug Log References

- **Story-Repair (Pre-Dev):** Story stammte vor Architektur-Amendment 2026-04-22 und enthielt direkte Verstöße gegen die 5 harten CLAUDE.md-Regeln (structlog, cryptography, Root-Workspace, `.eslintrc.cjs`). Die Story wurde vor Implementierung mit dem Amendment in Einklang gebracht (Änderungen sichtbar im Diff dieser Datei). Architektur-Doc bleibt Autorität — Story folgt ihr jetzt.
- **FastAPI-Response-Model-Error:** Der Root-Handler `/` hat Return-Typ `FileResponse | JSONResponse`. FastAPI 0.135+ versucht das als Pydantic-Response-Model zu interpretieren und wirft `PydanticSchemaGenerationError`. Fix: `response_model=None` am Decorator.
- **`get_logger()` Auto-Init-Trap:** Erster Entwurf rief `configure_logging()` beim ersten `get_logger`-Aufruf und versuchte `/data/logs/` anzulegen — scheitert auf macOS-Dev-Hosts (Read-Only-`/data`). Auto-Init entfernt; `configure_logging()` läuft explizit im Lifespan. Bis dahin gelten stdlib-Defaults (stderr, WARNING).
- **Dockerfile `ARG BUILD_FROM` Scope:** Erste Variante hatte `ARG` nach Stage 1 deklariert → Docker meldete leere Base-Image-Referenz. Fix: `ARG` als globalen Arg VOR dem ersten `FROM` deklarieren.
- **Frontend Peer-Dep-Conflict:** `@sveltejs/vite-plugin-svelte@4` fordert Vite 5, wir nutzen Vite 7. Hochgezogen auf `^6.0.0` (supported Vite 7). Gleichzeitig `eslint-plugin-svelte@^3.0.0` und `svelte-eslint-parser@^1.0.0` für ESLint-v9-Flat-Config-Kompatibilität.

### Completion Notes List

**Story 1.1 — Skeleton implementiert, alle 7 ACs erfüllt.**

- ✅ **AC 1 — GHA Multi-Arch Build:** `build.yml` + `release.yml` mit `docker/buildx@v3`, QEMU, `docker/build-push-action@v6`, matrix-driven über amd64 + aarch64. Lokal als Multi-Arch-Buildx-Probe erfolgreich durchlaufen (amd64 + arm64 transformieren + builden ohne Fehler). GHCR-Push passiert erst beim ersten Push auf `main` bzw. Tag (braucht `alkly/solalex` GHub-Repo als Target).
- ✅ **AC 2 — Custom-Repo-Installierbarkeit:** `repository.yaml` + `addon/config.yaml` mit Slug `solalex`, Ingress 8099, Panel-Title "Solalex". Verifikation im echten HA-Supervisor folgt beim ersten Release-Push.
- ✅ **AC 3 — FastAPI + SQLite Bootstrap:** Container-Boot-Log zeigt `solalex starting` + `database initialized {db_path: /data/solalex.db}`. `/api/health` liefert `{"status":"ok"}` mit 200. WAL aktiviert (Pytest bestätigt).
- ✅ **AC 4 — Svelte-Minimal-Build:** `npm run build` produziert `frontend/dist/index.html` + gzipped CSS (1.91 kB) + JS (10.80 kB). `svelte-check` 0 Errors / 0 Warnings. Container-Probe zeigt `/` servt die SPA korrekt.
- ✅ **AC 5 — Persistenz-Volume:** `/data/` wird von HA-Supervisor automatisch gemountet (keine Mount-Deklaration in `config.yaml`); SQLite + Logs landen dort; Test bestätigt File-Persistence (`test_initialize_database_creates_file_and_enables_wal`).
- ✅ **AC 6 — Ressourcen-Budget:** Gemessen lokal (amd64-Image via Rosetta auf Apple Silicon): **64.9 MiB RSS (43 % Budget), 0.49 % CPU idle (25 % Budget)**. Auf echter Pi-4-Hardware tendenziell noch niedriger. Finale Validation in Beta. Werte dokumentiert in `addon/DOCS.md`.
- ✅ **AC 7 — Keine externen Ports:** `addon/config.yaml` hat `ports: {}`, Dockerfile hat kein `EXPOSE`. Ingress ist einziger Zugriffspfad.

**Architektur-Amendment-Compliance (CLAUDE.md harte Regeln):**

- ✅ Regel 1 (snake_case): Python-Module, API-JSON, SQLite-Pfad, Env-Vars — alle snake_case.
- ✅ Regel 2 (Adapter-Modul-Layout): Noch nicht relevant (kommt in Story 3.x). Ordner-Skelett vorbereitet.
- ✅ Regel 3 (Closed-Loop-Readback): Nicht in 1.1 — Executor-Code kommt in Story 3.x.
- ✅ Regel 4 (JSON ohne Wrapper): `GET /api/health` → direkt `{"status":"ok"}`, keine `{data: …}`-Hülle.
- ✅ Regel 5 (`get_logger` aus `common.logging`): Exportiert, stdlib-basiert, JSONFormatter + RotatingFileHandler. Kein structlog.

**NICHT-Verwendungen eingehalten:** kein SQLAlchemy, kein Alembic, kein structlog, kein APScheduler, kein cryptography, kein Redis/Queue-Bus, kein WebSocket-Frontend, kein Ed25519, kein JSON-Template-Layer, kein Monorepo-Workspace-Root, keine `.ruff.toml`/`.mypy.ini` auf Repo-Root, kein OpenAPI-Codegen, kein i18n-Wrapper, kein Playwright, kein Controller-Submodul-Split.

**Offen für nächste Stories / nicht-blockierend:**

- **GHCR-Org `alkly`:** CI pusht gegen `ghcr.io/alkly/solalex-{arch}`. Voraussetzung: GitHub-Org `alkly` + Repo `solalex` existieren. Workflows laufen durch, sobald Repo angelegt ist.
- **Pi-4-Hardware-Messung:** Idle-RSS/CPU via Rosetta auf macOS gemessen — echte Pi-4-Validation in Beta-Phase (Epic 6/7 Hardware-Tests).
- **Platzhalter-Icons:** `addon/icon.png` (1024²) + `logo.png` (512²) sind ALKLY-blaue Unifarben-Platzhalter. Finale Assets liefert Story 1.5.
- **`uv.lock` mit macOS-Wheels:** Der lokal generierte Lock hat teilweise Darwin-Wheels. Beim ersten CI-Run auf Linux regeneriert uv automatisch den Linux-Wheel-Pfad — kein Blocker, aber heads-up wenn Du lokal ein `uv sync --frozen` erzwingst und die CI ein frischeres Lock findet.

### Change Log

- **2026-04-22** — Story an Amendment 2026-04-22 angeglichen (cryptography/structlog/Root-Workspace entfernt, ESLint-Flat-Config, Tool-Configs in backend/pyproject.toml).
- **2026-04-22** — Skeleton implementiert. Backend (FastAPI + aiosqlite + stdlib-JSON-Logging), Frontend (Svelte 5 + Vite 7 + Tailwind 4), Add-on (Dockerfile Multi-Stage + s6-Services + HA Base), CI (3 Workflows). Lokale Container-Probe: 64.9 MiB RSS, 0.49 % CPU, `/api/health` 200 OK.
- **2026-04-22** — Code-Review (bmad-code-review, 3 parallele Layer). 5 Decisions resolved, 23 Patches identifiziert.
- **2026-04-23** — 21 Patches angewandt (addon/config.yaml `panel_title` + `schema`/`options`, s6-`finish` Exit-Code-Propagation, WAL-Verify, `initialize_database` mkdir parent, `env_prefix="SOLALEX_"` + `AliasChoices` für `SUPERVISOR_TOKEN`, `get_settings` lru_cache, Logging-Handler-Cleanup + dynamisches `_RESERVED_LOGRECORD_KEYS`, Health-Readiness-Check, Frontend `BASE_URL`-relativer fetch + `onMount`, `run.sh`/s6-`run`-Alignment, Dockerfile Node 22, GHA concurrency-Key, Pre-commit-Prettier-Local + ESLint-Stub, `.gitignore`-Bereinigung). 2 Patches als Defer eskaliert (Port-DRY, Docker `USER`). Status: review → done.

### File List

**Neu angelegt (Root):**

- `.editorconfig`
- `.gitignore`
- `.pre-commit-config.yaml`
- `CHANGELOG.md`
- `LICENSE`
- `README.md`
- `repository.yaml`

**Neu angelegt (`.github/`):**

- `.github/workflows/build.yml`
- `.github/workflows/pr-check.yml`
- `.github/workflows/release.yml`
- `.github/ISSUE_TEMPLATE/feature-request.yml`
- `.github/pull_request_template.md`

**Neu angelegt (`addon/`):**

- `addon/CHANGELOG.md`
- `addon/DOCS.md`
- `addon/Dockerfile`
- `addon/README.md`
- `addon/config.yaml`
- `addon/icon.png` (1024² Platzhalter)
- `addon/logo.png` (512² Platzhalter)
- `addon/rootfs/etc/services.d/solalex/finish`
- `addon/rootfs/etc/services.d/solalex/run`
- `addon/run.sh`

**Neu angelegt (`backend/`):**

- `backend/README.md`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/src/solalex/__init__.py`
- `backend/src/solalex/api/__init__.py`
- `backend/src/solalex/api/routes/__init__.py`
- `backend/src/solalex/api/routes/health.py`
- `backend/src/solalex/common/__init__.py`
- `backend/src/solalex/common/logging.py`
- `backend/src/solalex/config.py`
- `backend/src/solalex/main.py`
- `backend/src/solalex/startup.py`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/unit/__init__.py`
- `backend/tests/unit/test_health.py`
- `backend/tests/unit/test_startup.py`

**Neu angelegt (`frontend/`):**

- `frontend/.prettierrc`
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/App.svelte`
- `frontend/src/app.css`
- `frontend/src/main.ts`
- `frontend/src/vite-env.d.ts`
- `frontend/static/fonts/.gitkeep`
- `frontend/svelte.config.js`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`

**Modifiziert:**

- `_bmad-output/implementation-artifacts/1-1-add-on-skeleton-mit-custom-repository-multi-arch-build.md` (Status, Tasks checked, Dev Agent Record, File List, Change Log; Architektur-Amendment-Anpassungen in Task-Texten, Source Tree, Library Requirements, Anti-Patterns)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (Story 1.1: ready-for-dev → review)

### Review Findings

Code Review am 2026-04-22 (bmad-code-review, 3 parallele Layer: Blind Hunter / Edge Case Hunter / Acceptance Auditor). Reviewed commit: `24a0fa3`. Keine Verletzung der 5 harten CLAUDE.md-Regeln. Die 7 ACs sind substantiell erfüllt.

Counts: 5 decision-needed (alle resolved), 23 patches (21 angewandt, 2 zu defer eskaliert — USER-Direktive + Port-DRY), 29 deferred, 16 dismissed. Patch-Apply am 2026-04-23: Backend ruff/mypy/pytest + Frontend svelte-check/build/eslint alle grün.

**Decision-Needed (resolved 2026-04-22):**

- [x] [Review][Decision] `homeassistant_api: true` in addon/config.yaml nicht im Spec authorisiert — Spec Task 2 listet nur `hassio_api: true` + `hassio_role: default`. **Resolved: behalten** (dismiss — keine Code-Änderung; Nutzung ab Story 1.3 erwartet). [addon/config.yaml:22]
- [x] [Review][Decision] `--forwarded-allow-ips "*"` mit `--host 0.0.0.0` akzeptiert gespoofte X-Forwarded-*-Header aus beliebiger Quelle. **Resolved: akzeptieren** (dismiss — Container-Netz isoliert, Ingress-Only-Policy ausreichend).
- [x] [Review][Decision] Ungenutzte Backend-Deps `websockets>=13` und `httpx>=0.27` — keine Imports in Story-1.1-Code. **Resolved: behalten** (dismiss — Dep-Churn vermeiden, Story 1.3 + 7.x nutzen sie).
- [x] [Review][Decision] Logging-Handler-Ownership: `configure_logging()` setzt `root.handlers = [file, stream]` und überschreibt damit uvicorn-Access-Log-Handler und pytest-Capture. **Resolved: akzeptieren** (dismiss — aktueller Stand bleibt). [backend/src/solalex/common/logging.py]
- [x] [Review][Decision] Pre-commit ESLint-Hook fehlt — Spec Task 1 sagt "ruff + eslint + prettier vorbereiten (Stubs okay, kein Blocker)". **Resolved: Stub nachziehen** (→ Patch P23). [.pre-commit-config.yaml]

**Patches (Code-Fixes, angewandt 2026-04-23):**

- [x] [Review][Patch] `panel_title: Solalex` statt spec-literal `"Solalex by ALKLY"` [addon/config.yaml:17]
- [x] [Review][Patch] s6 `finish` unbedingt `exit 0` + falsche "256"-Anmerkung (s6-overlay v3 nutzt 125 für "don't restart") — fataler Fehler propagiert jetzt Code 125 an den Container-Supervisor [addon/rootfs/etc/services.d/solalex/finish]
- [x] [Review][Patch] `PRAGMA journal_mode=WAL`-Ergebnis jetzt explizit verifiziert — `WALModeError` bei silent fallback [backend/src/solalex/startup.py]
- [x] [Review][Patch] `PRAGMA foreign_keys=ON` entfernt (war per-connection wirkungslos) — wird zurückkehren in Story 3.x mit Connection-Factory [backend/src/solalex/startup.py]
- [x] [Review][Patch] `initialize_database` legt `db_path.parent` selbst an — Test-Kopplung an `tmp_path`-Vorexistenz entfernt [backend/src/solalex/startup.py]
- [x] [Review][Patch] Pre-commit Prettier-Mirror durch lokalen Hook ersetzt (nutzt `frontend/node_modules/.bin/prettier`) — kein deprecated-Mirror mehr [.pre-commit-config.yaml]
- [x] [Review][Patch] `.gitignore` redundante Einträge konsolidiert — nur noch `data/` (matcht überall) [.gitignore]
- [x] [Review][Patch] `.gitignore` `*.key.example`-Negation vereinfacht (`!*.key.example`) + Kommentar, warum die Negation jetzt greift [.gitignore]
- [x] [Review][Patch] Frontend nutzt `import.meta.env.BASE_URL`-relativen `healthUrl` statt `./api/health` — Ingress-Subpath-robust [frontend/src/App.svelte]
- [x] [Review][Patch] `$effect` → `onMount` — semantisch korrekte Mount-Primitive statt "Effect ohne Reads" [frontend/src/App.svelte]
- [x] [Review][Patch] `get_settings()` mit `@lru_cache` gecached — `cache_clear()`-Hook für Tests dokumentiert [backend/src/solalex/config.py]
- [x] [Review][Patch] `_CONFIGURED`-Shortcut durch `_current_log_dir`-Vergleich ersetzt; alte Handler werden bei Rekonfiguration via `_close_installed_handlers()` geschlossen. Neues `reset_logging_for_tests()` für pytest [backend/src/solalex/common/logging.py]
- [x] [Review][Patch] `_RESERVED_LOGRECORD_KEYS` zur Laufzeit aus `logging.LogRecord`-Instanz abgeleitet — keine manuelle Pflege, keine `taskName`-Drift auf 3.11/3.12 [backend/src/solalex/common/logging.py]
- [x] [Review][Patch] `env_prefix="SOLALEX_"` in `Settings`; `supervisor_token` behält `SUPERVISOR_TOKEN` via `AliasChoices` (HA Supervisor injiziert den genauen Namen). Run-Scripts + conftest nachgezogen [backend/src/solalex/config.py + conftest + run-Scripts]
- [x] [Review][Patch] `addon/config.yaml` mit `schema: {}` + `options: {}` — Supervisor akzeptiert jetzt das Manifest [addon/config.yaml]
- [x] [Review][Patch] `addon/run.sh` auf `.venv/bin/uvicorn`-Pfad der s6-`run` aligned (gleicher Python-Env, gleiche Flags, selbe SOLALEX_*-Env) [addon/run.sh]
- [x] [Review][Patch] Dockerfile Node-Base `node:20-alpine` → `node:22-alpine` (aligned mit CI-`setup-node` v22) [addon/Dockerfile]
- [x] [Review][Patch] `concurrency.group` in build.yml auf `${{ github.workflow }}-${{ github.ref }}` — cancelt keine anderen Workflows mehr [.github/workflows/build.yml]
- [x] [Review][Patch] `conftest.py` nutzt nur noch `monkeypatch.setenv`; `os.environ.pop`-Zeilen + `SOLALEX_CACHED_APP`-Cargo-Cult entfernt. Plus `get_settings.cache_clear()` + `reset_logging_for_tests()` [backend/tests/conftest.py]
- [x] [Review][Patch] `/api/health` prüft `settings.db_path.is_file()` → `503 database not initialized` vor `200 {status: ok}` [backend/src/solalex/api/routes/health.py]
- [x] [Review][Patch] Pre-commit ESLint-Stub-Hook (local `npx eslint`) ergänzt [.pre-commit-config.yaml]

**Nicht angewandt (skipped mit Begründung):**

- [x] [Review][Skip] Ingress-Port 8099 DRY — echter Single-Source würde `addon/config.yaml` → HA-Supervisor-env → Python-Settings → Docker-Compose-Override-Channel bedingen. Refactor-Kandidat für Folge-Story, nicht zum Review-Patch-Umfang. Vorerst bleibt 8099 als Fallback in Settings + Run-Scripts. [mehrere] → defer
- [x] [Review][Skip] Docker `USER`-Directive — HA-Add-on-Konvention fordert root für s6-overlay (PID 1, /data-Mount-Permissions, hassio_api-Token-Zugriff). Drop-privileges-Patch wäre nicht-trivial (s6 `user=`-Direktiven + /data-Chown + Test auf echter HA-Instanz). Defer als Hardening-Story. [addon/Dockerfile] → defer

**Verifikation nach Patches (2026-04-23):**

- Backend: `ruff check .` ✅, `mypy --strict .` ✅, `pytest -q` ✅ (3 passed in 0.06s)
- Frontend: `svelte-check` ✅ (0 errors), `vite build` ✅ (CSS 5.53 kB, JS 27.20 kB), `eslint src` ✅
- Shell-Scripts: `bash -n` auf `run.sh`, `services.d/solalex/{run,finish}` ✅
- YAML: `addon/config.yaml`, alle `.github/workflows/*.yml`, `.pre-commit-config.yaml` parsen ✅

**Deferred (out-of-scope / pre-existing / Spec-Hygiene):**

- [x] [Review][Defer] GHA-Actions nicht auf Commit-SHA gepinnt — Supply-Chain-Hardening (Epic 6/7) — deferred, pre-existing
- [x] [Review][Defer] Keine cosign/SBOM/gitleaks/secret-scan in CI (Epic 6/7) — deferred, pre-existing
- [x] [Review][Defer] Kein CODEOWNERS — org-admin, nicht Story-1.1-Code — deferred, pre-existing
- [x] [Review][Defer] LICENSE-Text mischt MIT-Warranty-Boilerplate mit proprietären Klauseln — deferred, legal review
- [x] [Review][Defer] Kein Vitest/Playwright-Frontend-Test — Spec explizit "post-MVP" — deferred, pre-existing
- [x] [Review][Defer] `configure_logging`-Unit-Test fehlt (nur Integration via conftest) — deferred, pre-existing
- [x] [Review][Defer] Kein SPA-Catch-All-Fallback-Route für Client-Routed Deep-Links — Epic 2 Wizard-Territory — deferred
- [x] [Review][Defer] `docs_url=None / redoc_url=None / openapi_url=None` intentional per CLAUDE.md "kein OpenAPI-Codegen" — deferred, pre-existing
- [x] [Review][Defer] Release publishes `:latest` auch für Prerelease-Tags — deferred, Release-Strategie post-Beta
- [x] [Review][Defer] Release-Tag-Filter `v*.*.*` matcht `-rc.1`/`-beta.1` nicht — deferred, Release-Strategie
- [x] [Review][Defer] `release.yml` bumps `repository.yaml` nicht automatisch — Spec erlaubt "manuell" — deferred, pre-existing
- [x] [Review][Defer] `map: []` sperrt Zugriff auf `/share`, `/ssl` — nicht in Story 1.1 gebraucht — deferred
- [x] [Review][Defer] Ingress-Port 8099 statisch (potentielle Kollision mit anderem Addon) — deferred, HA-Supervisor-Konvention
- [x] [Review][Defer] Dockerfile frontend-builder-Stage ohne `--platform=$BUILDPLATFORM` — CI-Optimierung — deferred
- [x] [Review][Defer] Dockerfile `curl | sh` für uv-Installer — Supply-Chain; auf pinned uv-Image umstellen — deferred
- [x] [Review][Defer] Dockerfile baut Frontend neu obwohl CI `frontend/dist` als Artifact hochlädt (Redundanz) — deferred
- [x] [Review][Defer] `fastapi[standard]` + separates `uvicorn[standard]` + `websockets` = überlappende Extras — deferred, uv dedupes
- [x] [Review][Defer] `frontend/tsconfig.json` überschreibt `@tsconfig/svelte`-Base-Keys — deferred, post-MVP cleanup
- [x] [Review][Defer] `importlib.reload(main_mod)` in Test-Fixture ist Smell — auf `create_app()`-Factory refactoren — deferred
- [x] [Review][Defer] `RotatingFileHandler` + Multi-Worker-Race — aktuell Single-Process-Uvicorn, nicht triggerbar — deferred
- [x] [Review][Defer] `.editorconfig max_line_length=120` vs Ruff `ignore=["E501"]` inkonsistent — deferred, Style-Hygiene
- [x] [Review][Defer] Ruff `per-file-ignores` für tests vs `mypy strict=true` auf tests — deferred, Strictness-Alignment
- [x] [Review][Defer] Spec-Source-Tree drift (`test_main.py` statt `test_health.py`; `svelte.config.js` fehlt) — Spec-Doc-Hygiene — deferred
- [x] [Review][Defer] `log_dir`-Feld in `config.py` nicht im Spec-Task-3 dokumentiert — Spec-Doc-Hygiene — deferred
- [x] [Review][Defer] Icon/Logo-Größen nicht verifiziert (Platzhalter per Spec) — deferred, Story 1.5
- [x] [Review][Defer] `homeassistant:`-Min-Version in 1.1-Commit fehlt (in Story-1.2 uncommitted bereits nachgezogen) — deferred, Story 1.2
- [x] [Review][Defer] `repository.yaml` minimal (nur name/url/maintainer) — deferred, Doc-Enhancement

**Dismissed (Noise / False-Positive / HA-Konvention):**

- "Multi-arch manifest never assembled" — HA-Add-ons nutzen per-arch Image-Repos (`solalex-{arch}`); aktuelles Muster ist HA-konform
- "Two matrix jobs push same :latest" — jeweils eigenes Image-Repo (`solalex-amd64` vs `solalex-aarch64`), keine Kollision
- "Image-Tag-Mismatch config.yaml vs CI" — CI strippt `v` via `${GITHUB_REF#refs/tags/v}` → matcht `version: "0.1.0"`
- Fallback-Root-Route liefert `message`-Feld neben `status` — kein Regel-4-Wrapper (Auditor bestätigt)
- `svelte-spa-router` als reine Dependency — spec-konform für Skeleton (Auditor bestätigt)
- `get_logger()` vor `configure_logging()` — intentional per Debug-Log-Ref (Auditor bestätigt)
- Spec File-List `test_main.py` → actual `test_health.py` — File-List-Bottom ist konsistent, nur Source-Tree stale (siehe Defer)
- `$effect` "Infinite-Loop-Risk" — keine reaktiven Reads, feuert einmalig (Semantik-Patch in P11 trotzdem sinnvoll)
- `Path(__file__).parents[3]` IndexError — uv-Install-Layout garantiert Tiefe
- `index.html` zero-length / assets-Symlink broken — Filesystem-Pathologie, nicht realistisch
- Uvicorn `--host 0.0.0.0` per se — korrekt für Container-Netz; Verschärfung via D2 Forwarded-Headers
- `SOLALEX_CACHED_APP`-Env-Cleanup — in P21 bereits adressiert
