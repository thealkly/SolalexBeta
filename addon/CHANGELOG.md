# Changelog — Solalex Add-on

Dieses Changelog betrifft nur das HA-Add-on-Artefakt (Container + Manifest).
Repo-weites Changelog: `/CHANGELOG.md`.

## 0.1.0-beta.0 — 2026-04-23

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
