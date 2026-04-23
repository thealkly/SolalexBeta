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
3. URL eintragen: `https://github.com/alkly/solalex`
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

## Lizenz

Proprietär — siehe [LICENSE](LICENSE). Source ist zur Auditierbarkeit offen, aber
nicht freie Software.

## Kontakt

ALKLY — info@alkly.de
