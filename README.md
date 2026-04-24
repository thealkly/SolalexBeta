# Solalex

**Sekundengenaue aktive Nulleinspeisung und Akku-Pool-Steuerung als Home-Assistant-Add-on.**

Solalex ist ein kommerzielles Home-Assistant-Add-on, das Wechselrichter und Akkus
sekundengenau via HA-WebSocket-API steuert. 100 % lokal, keine Telemetry, kein
Cloud-Zwang — nur der monatliche Lizenz-Check verlässt Dein Netz.

> **Status:** Pre-Beta. Beta-Launch ist für 9 Wochen nach dem initialen Skeleton
> geplant. Siehe `_bmad-output/planning-artifacts/prd.md` für den vollen PRD.

## Installation via Home Assistant Add-on Store

Voraussetzungen: Home Assistant OS. Siehe [docs/landing/voraussetzungen.md](./docs/landing/voraussetzungen.md).

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store**.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/thealkly/SolalexBeta`
4. Nach dem Refresh erscheint Solalex in der Liste. **Installieren**.
5. Nach dem Start öffnet sich der Wizard im HA-Ingress-Frame.

Unterstützte Architekturen: `amd64`, `aarch64`.

## Unterstützte Hardware (Day 1)

- **Hoymiles / OpenDTU** — Wechselrichter
- **Marstek Venus 3E/D** — Akku
- **Shelly 3EM** — Smart Meter

Weitere Adapter (Anker Solix, Generic HA Entity) sind für v1.5 geplant.

## Entwicklung

Das Repository ist ein pragmatisches Zwei-Projekt-Setup ohne Workspace-Root:

- `backend/` — Python 3.13 + FastAPI + raw aiosqlite (`pyproject.toml` via `uv`)
- `frontend/` — Svelte 5 + Vite 7 + Tailwind 4 (`package.json` via `npm`)
- `addon/` — Home-Assistant-Add-on-Manifest, Dockerfile, s6-Services
- `_bmad-output/` — Planungs- und Implementierungs-Artefakte (PRD, Architektur, Stories)

Siehe `CLAUDE.md` für projekt-spezifische Regeln und die harten Nicht-Verwendungen
(kein SQLAlchemy, kein structlog, kein Redis, kein APScheduler, kein WebSocket im
Frontend in v1).

## Manuelles Release (erster Test)

Wenn Du für einen ersten Test ein Release-Paket lokal bauen und selbst in ein
öffentliches GitHub-Repository hochladen willst:

1. Archiv bauen:
   - `scripts/create_manual_release.sh 0.1.0`
2. Ergebnis prüfen:
   - `dist/releases/solalex-v0.1.0.tar.gz`
   - `dist/releases/sha256sums.txt`
3. Im Ziel-Repository auf GitHub eine neue Release anlegen (z. B. Tag `v0.1.0`)
   und beide Dateien als Assets hochladen.

Hinweis: Das Skript packt den aktuellen Repo-Stand, aber ohne `.git`,
`frontend/node_modules`, `backend/.venv`, `dist/releases`, `__pycache__` und
`.DS_Store`.

### Manuell nach `SolalexBeta`-Branch publizieren

Wenn ein neues Release zuerst bewusst per Hand in das öffentliche Beta-Repo
gepusht werden soll:

1. Sicherstellen, dass der Arbeitsbaum sauber ist:
   - `git status`
2. Release-Tag lokal anlegen (falls noch nicht vorhanden):
   - `git tag v0.1.0`
3. Publish-Skript ausführen:
   - `scripts/publish_release_to_solalexbeta.sh 0.1.0 main`

Das Skript:
- baut zuerst das manuelle Release-Archiv (`create_manual_release.sh`)
- pusht danach `HEAD` in den Ziel-Branch im Repo `thealkly/SolalexBeta`
- pusht abschließend den Tag `v<version>` in dasselbe Repo

### One-Command-Beta-Release

Wenn Du kuenftig alles mit einem Befehl fahren willst (Version setzen,
alle aktuellen Aenderungen committen, taggen, publishen):

- `scripts/release_beta_one_command.sh 0.1.0-beta.3`

Optional:
- `scripts/release_beta_one_command.sh 0.1.0-beta.3 "feat: story 3.1 beta release" main`

Verhalten:
- setzt `addon/config.yaml` auf die uebergebene Version
- fuehrt `git add -A` + Commit aus
- erstellt den Tag `v<version>`
- ruft `publish_release_to_solalexbeta.sh` auf `main` auf
- faellt bei Non-Fast-Forward automatisch auf `sync/v<version>` zurueck

Wichtig fuer Home Assistant Pulls:
- Das Add-on nutzt GHCR-Images `ghcr.io/thealkly/solalexbeta-{arch}`.
- Stelle in GitHub sicher, dass die Packages `solalexbeta-amd64` und
  `solalexbeta-aarch64` auf **Public** stehen, sonst liefert GHCR beim
  anonymen Token-Request `401 Unauthorized`.

## Lizenz

Proprietär — siehe [LICENSE](LICENSE). Source ist zur Auditierbarkeit offen, aber
nicht freie Software.

## Kontakt

ALKLY — info@alkly.de
