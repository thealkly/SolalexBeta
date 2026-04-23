# Story 1.5: HA-Sidebar-Registrierung mit ALKLY-Branding

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Solalex-Nutzer,
I want nach der Installation einen sichtbaren „Solalex by ALKLY"-Eintrag im HA-Sidebar,
so that ich Solalex in meiner gewohnten HA-Navigation wiederfinde.

## Acceptance Criteria

1. **Sidebar-Eintrag sichtbar:** `Given` das Add-on ist installiert und gestartet, `When` der Nutzer Home Assistant oeffnet, `Then` der HA-Sidebar zeigt den Eintrag „Solalex by ALKLY" mit ALKLY-Icon.
2. **Ingress + Asset korrekt deklariert:** `Given` `addon/config.yaml`, `When` Ingress konfiguriert ist, `Then` die Ingress-URL ist deklariert und das Icon ist als Asset im Image eingebettet.
3. **Klickpfad funktioniert:** `Given` der Sidebar-Eintrag, `When` der Nutzer ihn klickt, `Then` der Solalex-UI-Frame oeffnet im HA-Panel.

## Tasks / Subtasks

- [x] **Task 1: Manifest fuer Sidebar/Ingress final validieren und harmonisieren** (AC: 1, 2, 3)
  - [x] `addon/config.yaml` pruefen/setzen: `name`, `panel_title` beide auf **Solalex by ALKLY**.
  - [x] `ingress: true` und `ingress_port: 8099` bestaetigen (Port muss zur FastAPI-Runtime passen).
  - [x] `panel_icon` auf finalen MDI-Wert validieren (`mdi:solar-power-variant` oder bewusst geaenderter finaler Icon-Key).
  - [x] Sicherstellen, dass `ports: {}` und `ports_description: {}` unveraendert bleiben (kein externer Port fuer diese Story).

- [x] **Task 2: Icon-Assets fuer HA Add-on Packaging validieren** (AC: 1, 2)
  - [x] `addon/icon.png` und `addon/logo.png` vorhanden, lesbar und im erwarteten PNG-Format.
  - [x] Aufloesung und Dateigroesse pruefen (HA-kompatibel, visuell klar im Sidebar-Kontext).
  - [x] Bei Asset-Update: Dateien ersetzen, aber Dateinamen stabil halten (`icon.png`, `logo.png`).

- [ ] **Task 3: Klickpfad Ingress-Ende-zu-Ende pruefen** (AC: 3)
  - [ ] Add-on in HA starten, Sidebar-Eintrag anklicken.
  - [ ] Verifizieren, dass der Ingress-Frame die bestehende App-Shell (`frontend/dist`) laedt und kein leeres/fehlerhaftes Panel zeigt.
  - [ ] Fail-Fall dokumentieren (z. B. 404, Proxy-Fehler, Asset-Fehler) und beheben.

- [x] **Task 4: Doku auf finales Sidebar-Branding abgleichen** (AC: 1, 2)
  - [x] `addon/DOCS.md` an relevanten Stellen auf „Solalex by ALKLY" konsistent halten.
  - [x] `README.md`/`addon/CHANGELOG.md` nur dann anfassen, wenn dort Name/Icon-Info veraltet ist.

- [ ] **Task 5: Verifikation und Regression-Schutz** (AC: 1, 2, 3)
  - [ ] Backend Smoke: `cd backend && pytest -q` (mind. Health/Add-on-nahe Tests).
  - [x] Frontend Smoke: `cd frontend && npm run build` (Ingress-UI-Bundle weiterhin intakt).
  - [ ] Add-on Build-Sanity: `docker build -f addon/Dockerfile ...` oder bestehende CI-Pipeline erfolgreich.

### Review Findings

- [x] [Review][Defer] AC 3 Klickpfad (Sidebar-Klick → Ingress-Frame öffnet) noch ungetestet — manuelle QA in echtem HA-Environment erforderlich; nicht automatisierbar [addon/config.yaml] — deferred, pre-existing

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektuere)

- [epics.md - Epic 1 Story 1.5](../planning-artifacts/epics.md) - fachliche Story-Quelle + ACs.
- [architecture.md - Requirements to Structure Mapping (Epic 1)](../planning-artifacts/architecture.md) - erwartete Zielpfade fuer Epic-1-Aenderungen.
- [architecture.md - Frontend/Ingress Grundsatz](../planning-artifacts/architecture.md) - SPA laeuft im HA-Ingress, kein separater externer Port.
- [prd.md - FR42/FR43](../planning-artifacts/prd.md) - Sidebar-Branding + Ingress-Embedding als Produktanforderung.
- [CLAUDE.md](../../CLAUDE.md) - harte Regeln und Anti-Pattern (insb. kein externer Port, keine Architektur-Abweichungen).

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope-Disziplin:**

Diese Story ist eine **Branding- und Ingress-Integrationsstory** fuer das Add-on-Manifest und Assets.  
Kein Umbau von Wizard, Dashboard oder Domain-Logik.

**Primaere Dateien (erwarteter Scope):**

- `addon/config.yaml`
- `addon/icon.png`
- `addon/logo.png`
- optional: `addon/DOCS.md`, `addon/CHANGELOG.md` (nur falls textliche Konsistenz noetig)

**Nicht Ziel dieser Story:**

- Keine Backend-Architektur-Aenderung (`backend/src/solalex/**` nur bei klarer Ingress-Fehlfunktion).
- Keine neuen API-Endpunkte.
- Kein Theme-Wiring oder Empty-State-Ausbau (Story 1.6).
- Keine i18n-Infrastruktur.

**Guardrails (Disaster Prevention):**

- Wenn du `ports:` oeffnest oder neue externe Ports hinzufuegst -> **STOP** (verletzt Ingress-only Policy).
- Wenn du Add-on-Name/Panel-Title inkonsistent setzt -> **STOP** (Branding-Bruch in HA-UI).
- Wenn du Icon nur im Repo ersetzt, aber Packaging/Manifest nicht verifizierst -> **STOP** (AC 1/2 unvollstaendig).

### Architecture Compliance Checklist

- Ingress-only Access bleibt erhalten (`ingress: true`, keine externen Ports).
- Sidebar-Entry basiert auf Add-on-Manifest statt Custom-Panel-Hacks.
- Bestehende Repo-Struktur bleibt intakt (`addon/`, `backend/`, `frontend/` getrennt, kein Workspace-Umbau).

### Library/Framework Requirements

- Home Assistant Add-on Manifest-Konventionen in `addon/config.yaml` einhalten.
- Kein neues Framework, keine neuen Dependencies.
- Frontend bleibt bei Svelte 5 + Vite 7 Build-Artefakt, das ueber FastAPI/Ingress ausgeliefert wird.

### File Structure Requirements

- Icon/Logo-Dateinamen stabil halten: `addon/icon.png`, `addon/logo.png`.
- Keine neuen Verzeichnisse fuer Branding ohne Not.
- Manifest-Felder im bestehenden `addon/config.yaml` pflegen, nicht aufsplitten.

### Testing Requirements

- Sichtpruefung in HA: Sidebar zeigt „Solalex by ALKLY" + Icon.
- Klicktest: Sidebar oeffnet Ingress-UI ohne Fehler.
- Build-/Smoke-Gates:
  - `cd frontend && npm run build`
  - `cd backend && pytest -q`
  - optional `docker build` fuer Add-on-Packaging-Sanity.

### Previous Story Intelligence (Story 1.4)

- Story 1.4 hat das visuelle Fundament (Tokens + lokale DM Sans) vorbereitet; Story 1.5 nutzt dieses Fundament, veraendert es aber nicht grundlegend.
- In Story 1.4 wurde Scope-Disziplin streng gehalten (gezielte Dateien, kein Architektur-Creep). Dasselbe gilt hier fuer Manifest/Assets.
- Bereits etablierte Arbeitsweise: erst klare AC-Abdeckung, dann Build/Lint/Smoke-Verifikation.

### Git Intelligence Summary

- Letzte Commits zeigen Fokus auf Foundation/HA-Integration und Dokumentationskonsistenz; Story 1.5 soll denselben Stil fortfuehren (kleine, atomare Add-on-Verbesserung).
- Relevante zuletzt beruehrte Dateien: `addon/config.yaml`, `addon/DOCS.md`, `frontend/src/App.svelte`, Health/Ingress-nahe Infrastruktur.
- Commit-Stil im Repo: kurze, klare Imperativ-/Action-Titel.

### Latest Tech Information

- Home Assistant Ingress bleibt der korrekte Integrationsweg fuer Add-ons (`ingress: true` + `ingress_port` im Manifest).
- Sidebar-Icon wird ueber Manifest-Panel-Icon gesteuert; konsistente `name`/`panel_title`-Konfiguration vermeidet UI-Inkonsistenzen.
- Tailwind/Svelte-Versionstrends sind fuer diese Story nachrangig, weil primar Add-on-Manifest + Asset-Auslieferung betroffen sind.

### Project Structure Notes

- Alignment: Story 1.5 bleibt innerhalb `addon/` plus minimaler Doku-Anpassung.
- Keine Konflikte mit der Architektur-Single-Source (`architecture.md`) erwartet.
- Story 1.6 baut direkt auf dieser Story auf (Ingress-Frame-Qualitaet + Dark/Light-Adaption).

### References

- [epics.md](../planning-artifacts/epics.md)
- [architecture.md](../planning-artifacts/architecture.md)
- [prd.md](../planning-artifacts/prd.md)
- [CLAUDE.md](../../CLAUDE.md)
- [Home Assistant Ingress Blog](https://www.home-assistant.io/blog/2019/04/15/hassio-ingress/)
- [Home Assistant Developer Docs - Presenting your app](https://developers.home-assistant.io/docs/apps/presentation/)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `addon/config.yaml` Sidebar-/Ingress-Felder konsistent und korrekt sind.
2. `addon/icon.png` (und ggf. `logo.png`) im Add-on korrekt eingebettet und im HA-Kontext sichtbar sind.
3. Der Sidebar-Klick den Solalex-Ingress-Frame stabil oeffnet.
4. Build-/Smoke-Checks ohne neue Regression laufen.

## Dev Agent Record

### Agent Model Used

codex-5.3

### Debug Log References

- 2026-04-23: `cd backend && pytest -q` -> 4 passed, 3 errors (`PytestRemovedIn9Warning` in `backend/tests/integration/test_ha_client_reconnect.py` async fixture setup).
- 2026-04-23: `cd frontend && npm run build` -> erfolgreich (Vite Build grün), Hinweis auf empfohlene Node-Version >= 20.19.
- 2026-04-23: `docker build -f addon/Dockerfile -t solalex-addon-sanity:local .` -> lokal nicht ausfuehrbar (keine Berechtigung auf Docker-Socket im aktuellen Environment).
- 2026-04-23: Asset-Pruefung via `sips`/`ls -lh`: `addon/icon.png` 1024x1024 (5.6 KB), `addon/logo.png` 512x512 (1.8 KB).
### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Manifest für Sidebar/Ingress validiert: `name`/`panel_title`, `panel_icon`, `ingress`, `ingress_port`, `ports`/`ports_description` sind AC-konform.
- Branding-Text in `addon/DOCS.md` auf "Solalex by ALKLY" konsistent nachgezogen.
- Story bleibt in-progress: AC 3 (HA-Klickpfad im echten HA-Panel) sowie zwei Verifikationspunkte aus Task 5 sind noch offen.

### File List

- addon/DOCS.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/implementation-artifacts/1-5-ha-sidebar-registrierung-mit-alkly-branding.md
## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 1.0 | Initiale Story-Kontextdatei fuer Story 1.5 erstellt und auf ready-for-dev gesetzt. | Codex |
| 2026-04-23 | 1.1 | Story gestartet, Manifest/Assets validiert, Branding-Doku angepasst; offene Punkte für HA-Klicktest und vollstaendige Smoke-Gates dokumentiert. | Codex |
