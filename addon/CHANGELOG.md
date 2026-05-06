# Changelog — Solalex Add-on

Dieses Changelog betrifft nur das HA-Add-on-Artefakt (Container + Manifest).
Repo-weites Changelog: `/CHANGELOG.md`.

## 0.1.80 — 2026-05-06

- feat: Sticky Header/Footer für Settings- und Diagnose-Seiten

## 0.1.79 — 2026-05-06

- fix: Passive-Akku-Flow und Running-UI nachschärfen

## 0.1.78 — 2026-05-05

- fix: iOS-Nav-Fallbacks in Running/Setup-Routen absichern

## 0.1.77 — 2026-05-05

- fix: SettingsVerhalten-Review-Patches und Story-Status abschließen

## 0.1.76 — 2026-05-05

- feat: Settings-Verhalten auf eine Sammel-Page konsolidieren

## 0.1.75 — 2026-05-05

- feat: Narrative-, Settings- und Diagnose-Refinements bündeln

## 0.1.74 — 2026-05-05

- feat: Settings-IA-Refactor, Verbindungsdiagnose und Health-Status erweitern

## 0.1.73 — 2026-05-05

- feat: Topologie-Default für Akku-Cooldown absichern

## 0.1.72 — 2026-05-05

- feat: Sign-Flip-Cooldown, Helper-Slugs und Klartext-Mapping

## 0.1.71 — 2026-05-04

- fix: QA-Status-Helper über HA-WebSocket anlegen
- ci: Add-on-Changelog bei Auto-Release aus Git-Log ergänzen

## 0.1.1-beta.7 — 2026-04-25

- Manifest/Release-Stand auf `0.1.1-beta.7` aktualisiert.
- Runtime- und Debug-Logging-Verbesserungen aus Story-4.0-Zyklus integriert.
- Speicher-/Controller-Stabilisierung inklusive begleitender Test-Erweiterungen.

## 0.1.0-beta.1 — 2026-04-23

- Initiales Add-on-Skeleton (Multi-Arch, amd64 + aarch64).
- FastAPI-Backend unter Ingress-Port 8099.
- Health-Endpoint `/api/health`.
- SQLite-Init unter `/data/solalex.db` (WAL-Mode).
- Minimum HA Core: 2026.4.0 deklariert (via `addon/config.yaml`
  `homeassistant:`-Feld; niedrigere Versionen erhalten Install-Warning).
- Support-Matrix auf **Home Assistant OS** beschränkt. Home Assistant
  Supervised, Container und Core werden nicht unterstützt.
- Landing-Page-Voraussetzungen (`docs/landing/voraussetzungen.md`) und
  In-Store-Doku (`addon/DOCS.md` Abschnitt „Unterstützte HA-Versionen")
  ergänzt.
