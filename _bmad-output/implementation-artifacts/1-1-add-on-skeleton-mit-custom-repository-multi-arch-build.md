# Story 1.1: Add-on Skeleton mit Custom Repository & Multi-Arch-Build

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Entwickler,
I want ein lauffähiges HA Add-on-Gerüst im Custom Repository `alkly/solarbot` mit Multi-Arch-Docker-Build,
so that Solarbot über den HA Add-on Store installierbar ist und das Fundament für alle weiteren Features trägt.

## Acceptance Criteria

1. **GHA Multi-Arch Build:** `Given` das Repository `alkly/solarbot`, `When` Code gepusht und getaggt wird, `Then` GitHub Actions baut Docker-Images für `amd64` + `aarch64` und publisht sie in GitHub Container Registry. **And** Release-Builds werden bei Tag-Push (`vX.Y.Z`) automatisch getriggert.
2. **Custom-Repo-Installierbarkeit:** `Given` eine HA-Instanz mit HA OS oder Supervised, `When` der Nutzer das Custom Repository in den Add-on-Store einfügt, `Then` Solarbot erscheint im Store als installierbar.
3. **FastAPI + SQLite Bootstrap:** `Given` das Add-on ist installiert, `When` der Container startet, `Then` ein FastAPI-Prozess (Python 3.13) lauscht auf dem Ingress-Port **And** die SQLite-Datei `/data/solarbot.db` wird initialisiert (leer, produktive Tabellen kommen in späteren Stories dazu).
4. **Svelte-Minimal-Build:** `Given` der Container läuft, `When` die Svelte-Frontend-Route aufgerufen wird, `Then` ein minimaler Svelte + Tailwind-Build lädt ohne Fehler.
5. **Persistenz-Volume:** `Given` `/data/` als Persistenz-Volume, `When` das Add-on neu gestartet wird, `Then` `/data/`-Inhalt bleibt erhalten.
6. **Ressourcen-Budget (Pi 4):** `Given` Raspberry Pi 4 als Referenz-Hardware, `When` das Add-on im Idle läuft, `Then` RSS ≤ 150 MB und CPU ≤ 2 %.
7. **Keine externen Ports:** `Given` der Container, `When` er läuft, `Then` keine externen Port-Expositionen außer HA-Ingress.

## Tasks / Subtasks

- [ ] **Task 1: Monorepo-Wurzel initialisieren** (AC: 2, 7)
  - [ ] `repository.yaml` mit Custom-Add-on-Repo-Manifest anlegen (Name `alkly/solarbot`, Icon/Logo, Maintainer)
  - [ ] Root-`README.md` (Kurz-Beschreibung, Install-Instruktion via Custom-Repo) + `LICENSE` + `CHANGELOG.md` + `.gitignore` + `.editorconfig`
  - [ ] `.pre-commit-config.yaml` mit ruff + eslint + prettier vorbereiten (Stubs okay, kein Blocker)
  - [ ] Verzeichnis-Skelett nach [Architektur §Project Structure](../planning-artifacts/architecture.md#complete-project-directory-structure): `addon/`, `backend/`, `frontend/`, `.github/workflows/`, `.github/ISSUE_TEMPLATE/`, `docs/`
- [ ] **Task 2: Add-on-Manifest & Dockerfile** (AC: 1, 2, 3, 5, 7)
  - [ ] `addon/config.yaml` nach [home-assistant/addons-example](https://github.com/home-assistant/addons-example) – Mindestfelder: `name`, `version`, `slug: solarbot`, `description`, `arch: [amd64, aarch64]`, `ingress: true`, `ingress_port: 8099`, `panel_icon`, `panel_title: "Solarbot by ALKLY"`, `init: false`, `hassio_api: true`, `hassio_role: default`, `ports: {}` (keine externen Ports – AC 7), `map: []` (nur `/data/` implizit), `url`, `image: ghcr.io/alkly/solarbot-{arch}`
  - [ ] `addon/Dockerfile` Multi-Stage nach [Architektur §Build Process](../planning-artifacts/architecture.md#development-workflow-integration):
    - Build-Arg `BUILD_FROM` = `ghcr.io/home-assistant/{arch}-base-python:3.13-alpine3.19` (Multi-Arch-Base seit 2026.03.1)
    - Stage 1 (optional lokal): `frontend-builder` mit Node, führt `npm ci && npm run build` aus → `frontend/dist/`
    - Stage 2 `backend-runtime`: `FROM ${BUILD_FROM}`, installiert `uv`, kopiert `backend/` + `frontend/dist/` in Container-Static-Verzeichnis, `uv sync --frozen`, `COPY addon/rootfs/ /` für s6-overlay-Service
    - **Nicht** s6-overlay oder bashio separat installieren – im HA-Base enthalten
  - [ ] `addon/run.sh` als einfacher bashio-Entry-Point (Config lesen, `exec uvicorn solarbot.main:app --host 0.0.0.0 --port 8099`)
  - [ ] `addon/rootfs/etc/services.d/solarbot/{run,finish}` s6-overlay-Service-Skripte
  - [ ] `addon/CHANGELOG.md`, `addon/DOCS.md`, `addon/README.md`, `addon/icon.png` (1024×1024), `addon/logo.png` (512×512) – Platzhalter-Bilder okay, finale Assets aus Story 1.5
- [ ] **Task 3: Backend-Skeleton (Python 3.13 + FastAPI + aiosqlite)** (AC: 3, 5, 6, 7)
  - [ ] `cd backend/ && uv init --python 3.13` (nach [Architektur §Selected Starter](../planning-artifacts/architecture.md#selected-starter-komponierter-solarbot-skeleton))
  - [ ] `uv add "fastapi[standard]" "uvicorn[standard]" aiosqlite websockets pydantic-settings httpx cryptography`
  - [ ] `uv add --dev pytest pytest-asyncio pytest-cov ruff mypy`
  - [ ] `pyproject.toml`: Build-Backend `hatchling` (nicht `uv_build` – laut Architektur experimental)
  - [ ] `backend/src/solarbot/__init__.py`
  - [ ] `backend/src/solarbot/main.py`: FastAPI-App, Root-Route `GET /` → serviert Svelte-SPA-`index.html` aus `frontend/dist/`, `StaticFiles`-Mount für `/assets`
  - [ ] `backend/src/solarbot/config.py`: `pydantic-settings` liest `DB_PATH` (default `/data/solarbot.db`), `PORT` (default `8099`), `SUPERVISOR_TOKEN` (Env, noch nicht genutzt)
  - [ ] `backend/src/solarbot/startup.py`: Init-Order-Stub (License → DB-Migrate → HA-Connect → Controller). Für Story 1.1 nur **DB-Init**: SQLite-Datei unter `/data/solarbot.db` anlegen, `PRAGMA journal_mode=WAL` setzen. Keine produktiven Tabellen (kommen in späteren Stories).
  - [ ] `backend/src/solarbot/api/routes/health.py`: `GET /api/health` → `{"status": "ok"}`
  - [ ] `backend/src/solarbot/common/logging.py`: `structlog`-Setup mit JSON-Renderer + RotatingFileHandler (10 MB / 5 Files) nach `/data/logs/`
  - [ ] `.ruff.toml`, `.mypy.ini` auf Repo-Root
  - [ ] `backend/tests/conftest.py` + ein Smoke-Test `tests/unit/test_main.py` (`GET /api/health` → 200)
- [ ] **Task 4: Frontend-Skeleton (Svelte 5 + Vite 7 + Tailwind 4)** (AC: 4)
  - [ ] `cd frontend/ && npm create vite@latest . -- --template svelte-ts`
  - [ ] `npm i -D tailwindcss @tailwindcss/vite` (Tailwind v4 über Vite-Plugin, kein PostCSS-Config nötig)
  - [ ] `npm i svelte-spa-router` (Hash-Routing, ingress-URL-agnostisch)
  - [ ] `vite.config.ts`: `@tailwindcss/vite`-Plugin aktivieren, `build.outDir = 'dist'`, Base-Path `./` (relative Assets für HA-Ingress)
  - [ ] `frontend/src/app.css`: `@import "tailwindcss";` + Platzhalter-Block für ALKLY-Tokens (`--color-primary` etc.) – echte Token-Definitionen kommen in Story 1.4
  - [ ] `frontend/src/App.svelte`: Minimales „Solarbot"-Hello-Screen, kein Branding/kein Design-System-Content (Stories 1.4–1.6)
  - [ ] `frontend/src/main.ts`: Vite-Entry
  - [ ] `frontend/static/fonts/` als leerer Ordner mit `.gitkeep` (WOFF2-Dateien kommen in Story 1.4)
  - [ ] `frontend/tsconfig.json`, `frontend/.eslintrc.cjs`, `frontend/.prettierrc`
  - [ ] Build-Smoke: `npm run build` produziert `frontend/dist/index.html` ohne Fehler
- [ ] **Task 5: Multi-Arch-Build-Pipeline** (AC: 1)
  - [ ] `.github/workflows/build.yml`: Jobs Lint (ruff + mypy + eslint + svelte-check) → Test (pytest + vitest) → Frontend-Build (Vite) → Multi-Arch-Docker-Build (`docker buildx` mit QEMU für arm64) → GHCR-Push
  - [ ] `.github/workflows/pr-check.yml`: Lint + Test auf PR (kein Docker-Build – spart CI-Zeit)
  - [ ] `.github/workflows/release.yml`: Getriggert auf `push.tags: ['v*.*.*']`, baut und publisht Images, aktualisiert `repository.yaml` (Version-Bump per bot-commit oder manuell – laut [Architektur §Deployment](../planning-artifacts/architecture.md#development-workflow-integration))
  - [ ] Nutze `docker/setup-qemu-action@v3` + `docker/setup-buildx-action@v3` + `docker/build-push-action@v6`
  - [ ] GHCR-Login via `${{ secrets.GITHUB_TOKEN }}`, Tags `ghcr.io/alkly/solarbot-{arch}:latest` und `:${{ github.ref_name }}`
  - [ ] `.github/ISSUE_TEMPLATE/feature-request.yml` als Stub (Bug-Report kommt in Story 4.6)
  - [ ] `.github/pull_request_template.md` mit Changelog-Entry-Check-Hinweis
- [ ] **Task 6: Ressourcen-Verifikation (Pi 4)** (AC: 6)
  - [ ] Dockerfile-Build lokal (amd64) ausführen + `docker stats` im Idle messen – Zielwerte dokumentieren in `addon/DOCS.md`
  - [ ] **Wenn kein Pi 4 verfügbar:** qemu-arm64-Build + Stats auf amd64-Host als Näherung. AC 6 wird final in Beta-Phase auf echtem Pi 4 validiert. Note in Completion Notes.
- [ ] **Task 7: Smoke-Tests & Final Verification** (AC: 1–7)
  - [ ] `pytest` lokal grün (Health-Endpoint)
  - [ ] `npm run build` grün
  - [ ] `docker buildx build --platform linux/amd64,linux/arm64 --target backend-runtime .` lokal erfolgreich
  - [ ] README aktualisieren: Install-Instruktion „Add-on-Store → ⋮ → Repositories → `https://github.com/alkly/solarbot`"

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md §Selected Starter: Komponierter Solarbot-Skeleton](../planning-artifacts/architecture.md#selected-starter-komponierter-solarbot-skeleton) – drei `init`-Commands, exakte Reihenfolge
- [architecture.md §Verifizierte Aktuelle Versionen](../planning-artifacts/architecture.md#selected-starter-komponierter-solarbot-skeleton) – Versions-Matrix (Stand April 2026)
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
- **KEIN Redis / externer Broker** – In-Process-Event-Bus kommt später (`events/bus.py`), nicht in 1.1 nötig.
- **KEIN `/data/`-Mount-Override** – HA-Supervisor mountet `/data/` automatisch, in `config.yaml` nicht extra deklarieren.
- **SQLite WAL-Mode:** `PRAGMA journal_mode=WAL` beim Init setzen (spätere Story-KPIs brauchen es; Jetzt-Setzen kostet nichts).
- **Keine produktiven Tabellen in 1.1.** Alembic und Schema-Migration kommen in späteren Stories. Nur die leere DB-Datei anlegen.
- **Monorepo-Disziplin:** `git mv`-freundlich bleiben. Name „Solarbot" steht unter Markenrechts-Vorbehalt (siehe auto-memory) – Pfade/Imports so bauen, dass ein späterer Rename via `git mv` + Search/Replace reicht.

### Source Tree – zu erzeugende Dateien (Zielzustand nach Story)

```
solarbot/ (= Repo-Root)
├── README.md                           [NEW]
├── LICENSE                             [NEW]
├── CHANGELOG.md                        [NEW]
├── repository.yaml                     [NEW – Custom-Add-on-Repo-Manifest]
├── .gitignore                          [NEW]
├── .editorconfig                       [NEW]
├── .pre-commit-config.yaml             [NEW]
├── pyproject.toml                      [NEW – uv-workspace-Wurzel optional]
├── package.json                        [NEW – workspace-scripts optional]
├── .ruff.toml                          [NEW]
├── .mypy.ini                           [NEW]
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
│   └── rootfs/etc/services.d/solarbot/
│       ├── run                         [NEW]
│       └── finish                      [NEW]
├── backend/
│   ├── pyproject.toml                  [NEW – uv init]
│   ├── uv.lock                         [NEW – commited]
│   ├── src/solarbot/
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
│   ├── .eslintrc.cjs                   [NEW]
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
name = "solarbot"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]>=0.135.1",
    "uvicorn[standard]>=0.30",
    "aiosqlite>=0.20",
    "websockets>=13",
    "pydantic-settings>=2.6",
    "httpx>=0.27",
    "cryptography>=43",
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
```

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
- **Feature-Based Layout (nicht Type-Based):** Backend nach `controller/`, `executor/`, `adapters/` etc. Für Story 1.1 legen wir nur die von AC geforderten Module an (`api/`, `common/`). Die restlichen Ordner entstehen in späteren Stories.
- **Monorepo-Wurzel vs. Backend-Pyproject:** Architektur erwähnt beides. Pragmatik: `backend/pyproject.toml` ist Pflicht (`uv init` im backend/). Root-`pyproject.toml` als uv-workspace-Manifest ist **optional** – kann in Story 1.3+ dazukommen, wenn cross-package-Deps notwendig werden. Für 1.1 reicht Backend-isoliert.

### References

- [architecture.md – Selected Starter](../planning-artifacts/architecture.md#selected-starter-komponierter-solarbot-skeleton)
- [architecture.md – Project Directory Structure](../planning-artifacts/architecture.md#complete-project-directory-structure)
- [architecture.md – Naming Patterns](../planning-artifacts/architecture.md#naming-patterns)
- [architecture.md – Infrastructure & Deployment](../planning-artifacts/architecture.md#infrastructure--deployment)
- [architecture.md – Epic-Mapping (Epic 1)](../planning-artifacts/architecture.md#requirements-to-structure-mapping-epic-mapping)
- [prd.md – Technical Stack + NFR28 (100% lokal)](../planning-artifacts/prd.md)
- [epics.md – Epic 1 Story 1.1](../planning-artifacts/epics.md)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
