# Changelog

Alle nennenswerten Änderungen am Solalex-Add-on werden in dieser Datei dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/);
dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Added
- Initiales Add-on-Skeleton mit Custom-Repository-Manifest.
- Multi-Arch-Docker-Build-Pipeline (amd64, aarch64) via GitHub Actions.
- FastAPI-Backend (Python 3.13) mit `/api/health`-Endpoint.
- SQLite-Init (`/data/solalex.db`) mit WAL-Journal-Mode.
- Svelte 5 + Vite 7 + Tailwind 4 Frontend-Skeleton.
- stdlib-basiertes JSON-Logging mit `RotatingFileHandler` nach `/data/logs/`.

## [0.1.1-beta.7] — 2026-04-25

### Added
- Smoke-Test-Dokumentation unter `_bmad-output/qa/manual-tests/smoke-test.md`.
- Zusätzliche Unit-Tests für Logging-, Config- und Debug-Trace-Verhalten.

### Changed
- Speicher-/Controller-Logik rund um Akku-Pool und SoC-Policy weiter geschärft.
- Debug-Logging-Story 4.0 und Sprint-Status-Artefakte auf aktuellen Stand gebracht.
- Add-on-Startpfad und Runtime-Konfiguration im Backend weiter stabilisiert.

### Fixed
- Reconnect-/Dispatcher-/Readback-Pfade im HA-Client und Executor robuster gemacht.
- Logging-Initialisierung und Hot-Path-Trace-Ausgaben konsistenter umgesetzt.

## [0.1.0-beta.1] — 2026-04-23

Erste initiale Beta für Home-Assistant-Test im eigenen Setup.
