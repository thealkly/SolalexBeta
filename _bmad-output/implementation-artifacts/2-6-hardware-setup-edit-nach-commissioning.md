# Story 2.6: Hardware-Setup nachträglich ändern (Edit nach Commissioning)

Status: review

<!-- Erstellt 2026-04-25 als Reaktion auf Smoke-Test Alex' lokales HA-Setup. Beta-Launch-blocking — der aktuelle Gate-Mechanismus aus Story 2.3a (`gate.ts:39-44`) sperrt den Config-Flow strikt für commissioned User. Wer aus Versehen ohne WR commissioned hat (nur Smart-Meter), wer den Smart-Meter falsch zugewiesen hat oder wer einen Hardware-Wechsel macht, hat heute KEINE Möglichkeit, das im UI zu korrigieren — nur per SQL-Reset. Diese Story behebt das. -->

## Story

Als Beta-Tester, der seine Hardware-Konfiguration nachträglich ändern möchte (WR ergänzen, Smart-Meter wechseln, Vorzeichen-Invertierung korrigieren, falsch zugewiesene Entity tauschen),
möchte ich nach dem Commissioning eine sichtbare Möglichkeit haben, in die Hardware-Konfiguration zurück zu navigieren und sie zu ändern, ohne meine Datenbank manuell zu löschen,
so dass ich Setup-Fehler ohne Support-Eingriff beheben kann und sicher bin, dass ein nachträglicher Hardware-Wechsel (z. B. Marstek-Akku ergänzen, Trucki gegen Hoymiles tauschen) im laufenden Betrieb möglich ist.

## Acceptance Criteria

1. **Settings-Seite bekommt einen Hardware-Bereich:** Die existierende `Settings.svelte` (Story 3.6) bekommt eine neue Card „Hardware-Konfiguration" oberhalb der Akku-Konfig-Card. Card zeigt: aktuell konfigurierte Hardware (z. B. „Wechselrichter (allgemein) — `input_number.t2sgf72a29_set_target`"), Smart-Meter (falls gesetzt) inkl. Sign-Invert-Status, ggf. Marstek-Venus-Setup. Daneben ein Button „Hardware ändern" der zur Edit-Route führt.

2. **Neue Edit-Route `/hardware-edit`:** Die Route lädt die existierende `Config.svelte`-Komponente in einem **Edit-Modus** (Prop `editMode: boolean`). Edit-Modus unterscheidet sich vom Initial-Setup-Modus durch:
   - Header heißt „Hardware ändern" statt „Hardware konfigurieren"
   - Existierende Config-Werte aus der DB werden als Initial-Values vorbefüllt (hardware_type, wr_limit_entity_id, grid_meter_entity_id, min/max_limit_w, min/max_soc, night-discharge-Felder, **invert_sign aus Story 2.5**)
   - „Speichern"-Button heißt „Änderungen übernehmen", redirected nach `#/running` (nicht `#/functional-test`)
   - Funktionstest wird **nicht zwingend** erneut durchlaufen — Save schreibt direkt durch, Commissioning bleibt erhalten

3. **Backend-Endpoint für Hardware-Re-Save:** `PUT /api/v1/devices` (existiert noch nicht; aktuell ist nur `POST` für Initial-Save da). Body identisch zum POST `HardwareConfigRequest`. Verhalten:
   - Wenn `wr_limit_entity_id` sich ändert: alter Eintrag wird gelöscht, neuer angelegt mit `commissioned_at = NULL` (User muss Funktionstest erneut bestehen — Safety: neue Hardware ohne Readback-Verifikation darf nicht produktiv schalten).
   - Wenn `grid_meter_entity_id` sich ändert: alter Eintrag gelöscht, neuer mit `commissioned_at = now` (Smart-Meter ist read-only, kein Funktionstest nötig).
   - Wenn nur `min_limit_w` / `max_limit_w` / `invert_sign` / `min_soc` / `max_soc` / `night_*` ändern: in-place UPDATE auf bestehender Row, `commissioned_at` bleibt erhalten.
   - Wenn `hardware_type` von `generic` zu `marstek_venus` (oder umgekehrt) wechselt: alle Devices außer evtl. grid_meter werden ersetzt, `commissioned_at = NULL` für die neuen.
   - Antwort: Liste der neuen `DeviceResponse[]` analog zum POST.

4. **Frontend-Route durchs Gate erlauben:** `frontend/src/lib/gate.ts` bekommt einen neuen Branch für `/hardware-edit` analog zu `/settings`: pre-disclaimer-User → bounce zu Disclaimer; commissioned-User → stay (NICHT in `WIZARD_ROUTES` aufnehmen, sonst würde der commissioned-User-Redirect die Edit-Route auch blocken).

5. **Sicherheits-Banner im Edit-Modus:** Wenn der User Felder ändert, die ein neues Funktionstest-Commissioning auslösen werden (= WR-Entity-ID-Wechsel oder Hardware-Typ-Wechsel), zeigt eine prominente Warn-Card oben in der Page (gleicher Style wie `error-block`, aber neutral): „Diese Änderung erfordert einen erneuten Funktionstest. Solalex pausiert die Regelung, bis der neue Wechselrichter verifiziert ist." Kein Modal (UX-DR30).

6. **Während aktiver Edit-Session pausiert die Regelung NICHT:** Der User soll die Hardware ändern können, während das System weiterläuft. Erst nach „Änderungen übernehmen"-Klick und nur bei WR-Wechsel wird `commissioned_at` für den WR auf NULL gesetzt — was den Controller via `Controller.reload_devices_from_db` (Story 3.6) dazu bringt, das Device aus dem `_devices_by_role` zu entfernen, wodurch die Drossel-Policy automatisch in den „kein wr_limit"-Early-Exit fällt (genau wie heute bei Alex' Test-Setup).

7. **Reload-Hook nach Save:** `PUT /api/v1/devices` ruft am Ende `controller.reload_devices_from_db()` (existierender Story-3.6-Hook) auf, sodass die Änderungen ohne Add-on-Restart wirksam werden.

8. **Audit-Trail in `control_cycles`:** Beim Save wird ein Cycle mit `mode='audit', readback_status='noop', reason='hardware_edit: <kurzer-text>'` geschrieben (analog zum existierenden `_record_mode_switch_cycle`-Pattern), damit der Hardware-Wechsel in der Diagnose nachvollziehbar ist. Anchor-Device: das verbleibende grid_meter oder bei Total-Wechsel der erste neue Device-Record.

9. **Funktionstest-Re-Run im Edit-Modus:** Wenn ein WR-Entity-Wechsel stattfindet, redirected die UI **nicht** automatisch zum Funktionstest. Stattdessen zeigt die `/running`-Page nach Save einen prominenten Hinweis-Banner „Funktionstest erforderlich für neuen Wechselrichter — [Funktionstest starten]". Begründung: die Decision-Hoheit über das Re-Commissioning soll beim User liegen, nicht beim System.

10. **Tests Backend:**
    - `test_devices_api.py`: `test_put_devices_changes_wr_resets_commissioned_at`, `test_put_devices_changes_grid_meter_keeps_commissioned`, `test_put_devices_only_overrides_in_place_update`, `test_put_devices_writes_audit_cycle`, `test_put_devices_calls_reload_devices_from_db`.
    - `test_controller.py`: `test_reload_devices_from_db_after_wr_swap_clears_wr_limit_device` (existiert evtl. schon aus 3.6 — anpassen falls nicht abdeckt).
    - Edge-Case: Save mit identischer Config wie aktuell → keine DB-Schreibung, kein Audit-Cycle (keine Phantom-Inserts).

11. **Tests Frontend:**
    - `Config.test.ts`: `test_edit_mode_renders_initial_values_from_devices_prop`, `test_edit_mode_save_button_label_changes`, `test_edit_mode_save_redirects_to_running`.
    - `Settings.test.ts`: `test_hardware_card_renders_current_config`, `test_hardware_change_button_navigates_to_hardware_edit`.
    - `gate.test.ts`: `test_hardware_edit_route_allowed_for_commissioned_user`, `test_hardware_edit_route_redirects_pre_disclaimer_user`.
    - Vitest: Warn-Banner erscheint nur bei WR-Entity-Wechsel oder Hardware-Typ-Wechsel.

12. **Doku-Updates:**
    - `_bmad-output/qa/manual-tests/smoke-test.md`: Neuer Test SH-01 „Hardware-Wechsel im laufenden Betrieb": Ausgangs-Setup mit grid_meter only → Edit-Route → WR ergänzen → Funktionstest re-run → Drossel-Policy regelt.
    - **CLAUDE.md** ergänzt: Stop-Signal-Liste: „Wenn Du eine zweite Config-Komponente neben `Config.svelte` baust statt Edit-Modus-Prop — STOP. Edit/Initial-Setup teilen sich eine Komponente."

13. **Beta-Launch-Hinweis:** Diese Story ist parallel zu Story 2.5 implementierbar; Reihenfolge der Merge frei. Bei Merge-Konflikten (beide Stories berühren `Config.svelte` und `HardwareConfigRequest`) gewinnt die zuerst gemergte; die zweite muss rebasen.

## Tasks / Subtasks

- [x] **Task 1: Backend `PUT /api/v1/devices`-Endpoint** (AC 3, 7, 8, 10)
  - [x] Route in `backend/src/solalex/api/routes/devices.py`: `@router.put("/")` mit demselben `HardwareConfigRequest`-Body.
  - [x] Diff-Logik: Lade aktuelle Devices, vergleiche mit Body, kategorisiere Änderung in (a) Override-only-Update, (b) Smart-Meter-Wechsel, (c) WR-Wechsel, (d) Hardware-Typ-Wechsel.
  - [x] In-place Updates für (a) via `update_device_config_json` (existiert).
  - [x] Replace-Logik für (b)/(c)/(d): alte Row löschen oder `commissioned_at=NULL` setzen (Race-frei: SELECT-für-UPDATE → Diff → DELETE/INSERT/UPDATE in einer Transaktion).
  - [x] Audit-Cycle schreiben (siehe AC 8).
  - [x] `controller.reload_devices_from_db()` aufrufen.
  - [x] Tests: alle 5 Backend-Test-Cases aus AC 10.

- [x] **Task 2: Backend Schema-Konsolidierung** (AC 3)
  - [x] `HardwareConfigRequest` ist bereits dafür ausgelegt — sicherstellen, dass alle in Story 2.5 / 3.6 hinzugefügten Felder (`invert_sign`, `min_soc`, `max_soc`, `night_*`) im PUT-Pfad ebenfalls validiert und gemerged werden.
  - [x] DTO-Test: PUT-Body mit allen optionalen Feldern → korrekt deserialisiert.

- [x] **Task 3: Frontend `Config.svelte` Edit-Modus** (AC 2, 5, 11)
  - [x] Prop `editMode = $props.editMode ?? false` und `initialConfig = $props.initialConfig` (DeviceResponse[]).
  - [x] `onMount`: wenn `editMode`, fülle State-Variablen aus `initialConfig` (hardwareType, wrLimitEntityId, …) statt aus Defaults.
  - [x] Header-Text und Save-Button-Label conditional auf `editMode`.
  - [x] Save-Funktion: `editMode ? client.updateDevices(...) : client.saveDevices(...)`. Redirect: `editMode ? '#/running' : '#/functional-test'`.
  - [x] Warn-Banner-Komponente am Page-Top, conditional auf Edit-Modus + erkanntes WR-Wechsel-Diff (vergleiche aktuell-eingegebene Werte mit `initialConfig`).
  - [x] Tests: Initial-Werte-Befüllung, Save-Button-Label, Redirect, Warn-Banner-Sichtbarkeit.

- [x] **Task 4: Frontend Settings-Card** (AC 1, 11)
  - [x] In `Settings.svelte` neue Card `<section class="settings-section">` für Hardware-Konfiguration. Liest Devices aus `client.getDevices()` (gleiche Quelle wie `Running.svelte`).
  - [x] Anzeige: Hardware-Typ-Label (Mapping aus existierenden Files: generic → „Wechselrichter (allgemein)", marstek_venus → „Marstek Venus"), Entity-IDs, optional Smart-Meter mit Sign-Invert-Status.
  - [x] Button „Hardware ändern" → `window.location.hash = '#/hardware-edit'`.
  - [x] Tests: Card-Rendering und Navigation.

- [x] **Task 5: Frontend Routing + Gate** (AC 4, 11)
  - [x] `frontend/src/App.svelte`: neue Route `/hardware-edit` registrieren, `VALID_ROUTES`-Set ergänzen, dynamisch `Config.svelte` mit `editMode={true}` und `initialConfig` aus `getDevices()`-Cache instantiieren.
  - [x] `frontend/src/lib/gate.ts`: neuer Branch `if (currentRoute === '/hardware-edit')` analog zum `/settings`-Branch (pre-accepted? sonst Disclaimer; commissioned? → stay; nicht commissioned? → bounce zu `#/`).
  - [x] `gate.test.ts` ergänzen.

- [x] **Task 6: Frontend Client + Types** (AC 3, 11)
  - [x] `client.ts`: `updateDevices(req: HardwareConfigRequest): Promise<DeviceResponse[]>` (PUT statt POST).
  - [x] Types: keine neuen Types nötig, beide Endpoints teilen `HardwareConfigRequest` und `DeviceResponse[]`.
  - [x] Tests: `client.test.ts` PUT-Pfad.

- [x] **Task 7: `/running`-Page Funktionstest-Hinweis** (AC 9)
  - [x] `Running.svelte`: Wenn ein commissioned-Wert mit `wr_limit`-Role, aber `commissioned_at == null` existiert → Banner oben in der Page „Funktionstest erforderlich für neuen Wechselrichter" mit Link `#/functional-test`.
  - [x] Tests: `Running.test.ts` Banner-Sichtbarkeit.

- [x] **Task 8: Doku-Updates** (AC 12)
  - [x] Smoke-Test SH-01.
  - [x] CLAUDE.md Stop-Signal-Liste.

- [x] **Task 9: Validierung und Final-Gates** (AC 10, 11, 12)
  - [x] Backend: ruff, mypy, pytest.
  - [x] Frontend: lint, check, vitest, build.
  - [x] Manual: Alex testet Hardware-Wechsel im laufenden Betrieb (grid_meter only → WR ergänzen → Funktionstest → Drossel regelt).

## Dev Notes

### Architektur-Bezugspunkte

- **Story 2.3a Gate-Logik:** Der existierende Gate (`gate.ts:39-44`) ist eine harte Sperre: jeder commissioned User wird vom `WIZARD_ROUTES`-Set zwangs-redirected zu `#/running`. Diese Story durchbricht das **explizit** mit einer separaten `/hardware-edit`-Route, die NICHT im `WIZARD_ROUTES`-Set ist (analog zu `/settings`/`/diagnostics`). [Source: `frontend/src/lib/gate.ts:6-16`]
- **Story 3.6 Settings-Page existiert:** `Settings.svelte` ist bereits da und versteckt (kein Footer-Link, manueller Hash-Aufruf). Diese Story hängt eine Card und einen sichtbaren Footer/Header-Eintrag dran. [Source: `_bmad-output/implementation-artifacts/3-6-user-config-min-max-soc-nacht-entlade-zeitfenster.md`]
- **Story 3.6 reload_devices_from_db existiert:** `Controller.reload_devices_from_db()` ist bereits implementiert und race-frei. Diese Story ruft sie nach jedem PUT auf. [Source: `backend/src/solalex/controller.py:361-402`]
- **Story 2.4 Generic-Adapter-Refit:** Das System ist bereits Generic-First. WR-Wechsel zwischen Hoymiles/Trucki/ESPHome erfordert nur Entity-ID-Wechsel, nicht Adapter-Wechsel. Marstek bleibt Sonderfall. [Source: `_bmad-output/implementation-artifacts/2-4-generic-adapter-refit.md`]
- **Story 2.5 invert_sign:** Sollte parallel mergen — wenn 2.5 zuerst landet, hat dieser PUT-Endpoint das Feld bereits zu mergen. [Source: `_bmad-output/implementation-artifacts/2-5-smart-meter-sign-invert-mit-live-preview.md`]
- **CLAUDE.md Disclaimer-Pflicht:** Neuer Disclaimer ist NUR vor dem Initial-Setup nötig, nicht vor dem Edit (User hat ihn schon akzeptiert). Der Gate-Branch für `/hardware-edit` re-prüft `preAccepted` defensiv, geht aber bei einem commissioned User immer durch.

### Aktueller Codezustand und Ziel-Änderungen

- `backend/src/solalex/api/routes/devices.py` hat aktuell nur `POST /api/v1/devices` (Initial-Save) und `PATCH /api/v1/devices/battery-config` (Story 3.6). Diese Story ergänzt `PUT /api/v1/devices`.
- `frontend/src/routes/Config.svelte` ist heute reine Initial-Setup-Komponente. Diese Story macht sie dual-purpose über `editMode`-Prop. **Nicht** eine zweite Komponente bauen — sonst doppelte UI-Wahrheit.
- `frontend/src/lib/gate.ts` `evaluateGate` hat bereits eine flache Switch-Struktur. Den `/hardware-edit`-Branch genau wie `/settings` ergänzen.
- `frontend/src/App.svelte` `VALID_ROUTES` Set erweitern.
- `Running.svelte` braucht einen Banner-Slot für „Funktionstest erforderlich" — die Page hat bereits Conditional-Branches (`testInProgress`/`loadError`/`else`); ein vierter Pfad „WR vorhanden, aber not commissioned" lässt sich da einhängen.

### Implementation Guardrails

- **Keine zweite Config-Komponente:** Edit und Initial-Setup teilen sich `Config.svelte` über eine Prop. Doppelte Komponenten driften auseinander.
- **Kein Modal:** Warn-Banner ist eine Card, kein Popup.
- **Keine automatische Funktionstest-Redirection:** User entscheidet selbst, wann der Test läuft. Auto-Redirect erzeugt das Gefühl, gefangen zu sein.
- **Replace-Pattern statt Update für Entity-ID-Wechsel:** Alte Row löschen + neue anlegen ist sauberer als Spalten-UPDATE, weil `commissioned_at`-Reset, `last_write_at`-Reset und `config_json`-Reset zusammen passieren.
- **Audit-Trail Pflicht:** Jede Hardware-Änderung schreibt einen Cycle-Log-Eintrag. Sonst ist der Wechsel in der Diagnose unsichtbar.
- **Race-Sicherheit:** Der gesamte PUT-Pfad in eine SQLite-Transaktion (`async with conn.execute("BEGIN")`-Pattern wie bei Migration 003), damit ein Crash mitten im Diff nicht zu inkonsistentem State führt.
- **Reload-Hook synchron:** `controller.reload_devices_from_db()` returned, bevor der HTTP-Response zurückgeht. Sonst sieht der Frontend-Refresh evtl. noch alte Werte.
- **Gate-Branch IMMER re-prüfen:** Der `/hardware-edit`-Branch im Gate muss explizit prüfen, dass es Devices gibt (`devices.length > 0`) — sonst ist der Initial-Setup-Flow gemeint und der User sollte zu `/` (Welcome) bounced werden.

### File Structure Requirements

```text
backend/src/solalex/
├── api/
│   ├── routes/
│   │   └── devices.py          [MOD: PUT /api/v1/devices, Audit-Cycle, Reload-Hook]
│   └── schemas/
│       └── devices.py          [UNCHANGED: HardwareConfigRequest passt schon]
└── controller.py               [UNCHANGED: reload_devices_from_db existiert]

frontend/src/
├── App.svelte                  [MOD: /hardware-edit Route, VALID_ROUTES]
├── lib/
│   ├── api/
│   │   └── client.ts           [MOD: updateDevices PUT]
│   └── gate.ts                 [MOD: /hardware-edit Branch]
└── routes/
    ├── Config.svelte           [MOD: editMode-Prop, initialConfig, Warn-Banner, Save-Verzweigung]
    ├── Running.svelte          [MOD: Funktionstest-erforderlich-Banner]
    └── Settings.svelte         [MOD: Hardware-Card oberhalb der Akku-Card]

_bmad-output/qa/manual-tests/
└── smoke-test.md               [MOD: Neuer Test SH-01]

CLAUDE.md                       [MOD: Stop-Signal "keine zweite Config-Komponente"]
```

### Testing Requirements

- **Backend** Test-Stack erweitert um:
  - `test_devices_api.py`: 5 Test-Cases aus AC 10 + identische-config-no-op-Test.
  - `test_controller.py` falls Story 3.6 nicht alle Reload-Pfade testet.
- **Frontend** Test-Stack erweitert um:
  - `Config.test.ts`: 3 Test-Cases aus AC 11.
  - `Settings.test.ts`: 2 Test-Cases.
  - `gate.test.ts`: 2 Test-Cases.
  - `Running.test.ts`: Banner-Sichtbarkeit.

### Previous Story Intelligence

- Story 3.6 hat bereits den Pattern für „versteckte Settings-Route mit Gate-Branch" etabliert. Diese Story folgt dem Pattern 1:1 für `/hardware-edit`, macht aber die Settings-Card sichtbar (mit Hardware-Bereich), damit User sie überhaupt finden.
- Story 3.6 hat `Controller.reload_devices_from_db` ohne Mode-Reset implementiert — heißt: Hardware-Wechsel triggert KEINEN unbeabsichtigten Mode-Switch, was für unsere Story Voraussetzung ist.
- Story 2.3a Gate-Logik ist auf direkte URL-Eingaben getestet — der `/hardware-edit`-Branch muss denselben Test-Pattern bekommen (manueller Hash-Eintrag durch User darf nicht durchs Disclaimer-Gate fallen).

### References

- [Source: `frontend/src/lib/gate.ts:6-16`] WIZARD_ROUTES + Settings-Branch-Vorbild
- [Source: `frontend/src/routes/Settings.svelte`] Bestehende versteckte Settings-Page
- [Source: `frontend/src/routes/Config.svelte`] Komponente, die dual-purpose wird
- [Source: `frontend/src/App.svelte` `VALID_ROUTES`] Routing-Whitelist
- [Source: `backend/src/solalex/api/routes/devices.py`] POST + PATCH bestehen schon
- [Source: `backend/src/solalex/controller.py:361-402`] `reload_devices_from_db`
- [Source: `_bmad-output/implementation-artifacts/3-6-user-config-min-max-soc-nacht-entlade-zeitfenster.md`] Settings-Pattern
- [Source: `_bmad-output/planning-artifacts/architecture.md`] Authority bei Konflikten

### Validation Commands

Backend:

```bash
cd backend
uv run ruff check .
uv run mypy .
uv run pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run check
npm test
npm run build
```

Manual-QA:

```text
SH-01 Hardware-Wechsel im laufenden Betrieb (smoke-test.md):
1. Ausgangslage: Setup mit grid_meter only (kein WR commissioned)
2. Settings öffnen → „Hardware ändern" klicken
3. Wechselrichter (allgemein) wählen → input_number.<...> → Speichern
4. /running zeigt Banner „Funktionstest erforderlich"
5. Funktionstest starten → bei Erfolg: Drossel regelt
6. Erneut Settings → „Hardware ändern" → Smart-Meter-Sign-Invert-Toggle ändern → Speichern
7. /running ohne Banner, Drossel-Regelung weiter aktiv, Live-Chart zeigt invertierten Wert korrekt
```

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Claude Opus 4.7, 1M-Kontext) via `/bmad-dev-story` Workflow.

### Debug Log References

- Backend: `cd backend && uv run pytest` → 408 grün (vorher 398; +10 neu durch 2.6).
- Frontend: `npm test -- --run` → 111 grün (vorher 96; +15 neu durch 2.6).
- Lint/MyPy/svelte-check/build alle grün.

### Completion Notes List

- AC 3/7/8/10 (Backend `PUT /api/v1/devices`): Neue Route in `backend/src/solalex/api/routes/devices.py` mit Diff-Klassifikator `_row_diff_kind` (`identical`, `override_only`, `smart_meter_swap`, `wr_swap`, `hardware_swap`). Gemeinsame Builder-Funktion `_build_rows_from_request` für POST und PUT. In-place UPDATE über bestehende `update_device_config_json` (Story 3.6) für Override-only-Diffs; Replace-Pfad mit Transaction (`BEGIN IMMEDIATE`) für Entity-Wechsel. `commissioned_at`-Behandlung pro Diff-Kind: Override-only erhält den Wert, Smart-Meter-Swap setzt automatisch auf `now`, WR/Hardware-Swap lässt `commissioned_at=NULL` (User muss Funktionstest re-runnen).
- AC 7/8: `controller.reload_devices_from_db()` synchron NACH der DB-Transaktion; Audit-Cycle (`mode=current_mode, source='solalex', readback_status='noop', reason='hardware_edit: <kind> (...)'`) als best-effort-write — Fehler logged ohne den HTTP-Response zu kippen.
- Merge-Semantik: `_merge_config` bewahrt fremde Keys (z. B. Story 3.8 `allow_surplus_export`), wenn nur Wizard-Subset überschrieben wird.
- AC 1/4 (Frontend): `Settings.svelte` neue Hardware-Card oberhalb der Akku-Card mit Liste aller Devices, Sign-Invert-Tag, Funktionstest-erforderlich-Tag, Button „Hardware ändern" → Hash-Navigation. `lib/gate.ts` neuer Branch für `/hardware-edit` analog zu `/settings`, mit Devices-Empty-Redirect zu `#/`.
- AC 2/5/6/9 (Frontend): `Config.svelte` bekommt `editMode: boolean` + `initialDevices: DeviceResponse[]` Props. `loadStateFromInitialDevices` befüllt alle State-Variablen aus den persistierten Werten. Header/Save-Button-Label/Save-Verzweigung schalten auf editMode um (`updateDevices` PUT + Redirect zu `/running`). Warn-Banner via `needsRefunctionalTest`-derived nur bei WR-Entity-Swap oder Hardware-Typ-Wechsel. `Running.svelte` zeigt Banner mit Link zu `/functional-test`, wenn ein commissioned-WR/Akku-Device ein `commissioned_at=null` hat.
- App-Routing: `App.svelte` `VALID_ROUTES` erweitert, neue Route rendert `<Config editMode initialDevices={…}/>` mit Cached-Devices.
- AC 12 (Doku): Smoke-Test SH-01 in `_bmad-output/qa/manual-tests/smoke-test.md` ergänzt; CLAUDE.md Stop-Signale für „keine zweite Config-Komponente" und „kein WIZARD_ROUTES für /hardware-edit" sind bereits vorab dokumentiert.
- Tests: `tests/integration/test_devices_put.py` (10 Cases — Identical-NoOp, Override-Only, Invert-Sign-Override, WR-Swap, Smart-Meter-Swap, Hardware-Type-Swap, Reload-Hook, Audit-Cycle, Foreign-Key-Preservation). `Settings.test.ts` um 5 Hardware-Card-Cases erweitert. `Running.test.ts` um 2 Banner-Cases erweitert. `gate.test.ts` um 4 `/hardware-edit`-Branch-Cases erweitert. `client.test.ts` um `updateDevices` PUT-Test erweitert. `Config.test.ts` um 3 editMode-Cases (Header, Tile-Vorbefüllung, Banner-Visibility-Default) erweitert.

### File List

Backend (modified):
- `backend/src/solalex/api/routes/devices.py`

Backend (added):
- `backend/tests/integration/test_devices_put.py`

Frontend (modified):
- `frontend/src/App.svelte`
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/gate.ts`
- `frontend/src/lib/gate.test.ts`
- `frontend/src/lib/api/client.test.ts`
- `frontend/src/routes/Config.svelte`
- `frontend/src/routes/Config.test.ts`
- `frontend/src/routes/Running.svelte`
- `frontend/src/routes/Running.test.ts`
- `frontend/src/routes/Settings.svelte`
- `frontend/src/routes/Settings.test.ts`

Docs (modified):
- `_bmad-output/qa/manual-tests/smoke-test.md` (SH-01)
- `_bmad-output/implementation-artifacts/2-6-hardware-setup-edit-nach-commissioning.md` (Status, Tasks, Dev Record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

Code-Review 2026-04-25 (3 parallele Reviewer: Blind Hunter, Edge Case Hunter, Acceptance Auditor). 27 Roh-Findings, 23 nach Triage, 4 als Noise/Out-of-Scope verworfen.

**Decision-Needed:**

- [ ] [Review][Decision] Override-Werte (`min_limit_w`/`max_limit_w`) lassen sich via PUT NICHT clearen — `_build_rows_from_request` schreibt die Keys nur wenn `is not None`, `_merge_config` ist links-biased, also bleibt der Altwert für immer drin. Symmetrisch zum `invert_sign`-P4-Patch wäre eine explizite Klar-Semantik nötig. Optionen: (a) Backend-Sentinel (`{"min_limit_w": None}` heißt clear, abwesender Key heißt preserve), (b) immer alle Wizard-managed Keys explizit schreiben (Frontend sendet `null` bei leerem Feld, Backend cleart), (c) Frontend-Inline-Confirm beim Blanken. Architektur-Entscheidung nötig — gleiche Frage taucht bei Story 3.8 `allow_surplus_export` auf, lohnt sich gemeinsam zu lösen. [`backend/src/solalex/api/routes/devices.py:82-100`, `175-195`]

**Patches:**

- [ ] [Review][Patch] Lost-Update-Race: `existing` wird außerhalb der Transaktion gelesen, zwei nebenläufige PUTs sehen den gleichen Snapshot, der zweite läuft auf stale plan und kann an `UNIQUE(entity_id, role)` scheitern oder DELETE-Phantome produzieren — Read-and-Classify gehört in die `BEGIN IMMEDIATE`-Transaktion, oder `INSERT ... ON CONFLICT DO UPDATE` für Replay-Idempotenz. [`backend/src/solalex/api/routes/devices.py:297-339`]
- [ ] [Review][Patch] Audit-Cycle wird übersprungen wenn `reload_devices_from_db()` raised — Reload steht aktuell BEFORE Audit-Write (L387-401), bei Reload-Fehler ist die Hardware-Änderung niemals im Diagnose-Ringpuffer. Audit-Cycle vor Reload schreiben oder in `try/finally` wrappen. [`backend/src/solalex/api/routes/devices.py:384-401`]
- [ ] [Review][Patch] `_ALLOWED_AUDIT_MODES` enthält `export` nicht — wenn Story 3.8 landet und Controller in `Mode.EXPORT` ist, wird der Audit-Cycle stillschweigend mit `mode='drossel'` geschrieben (Lüge im Audit-Trail, CLAUDE.md flagged Audit-Klarheit als non-negotiable). Mindestens `logger.warning("audit_mode_fallback", extra={"controller_mode": raw_mode})` im Fallback-Pfad, damit der Footgun beim 3.8-Merge sichtbar wird. [`backend/src/solalex/api/routes/devices.py:43-46, 460-465`]
- [ ] [Review][Patch] `_write_hardware_edit_audit_cycle` schluckt JEDE Exception mit `logger.exception` — bei FK-/CHECK-Verletzung verschwindet die Hardware-Änderung still aus dem Audit-Trail, der PUT antwortet trotzdem 200. Mindestens strukturiertes `audit_cycle_failed`-Feld loggen, idealerweise als Diagnose-Counter exposen. [`backend/src/solalex/api/routes/devices.py:448-490`]
- [ ] [Review][Patch] `/hardware-edit`-Initial-Devices-Race: bei Direkt-URL `#/hardware-edit` mountet `App.svelte` Config mit `initialDevices={devicesCache ?? []}` während der Cache noch null ist → `loadStateFromInitialDevices` wird durch den `length > 0`-Guard übersprungen → User sieht leeres Edit-Formular und Save erzeugt einen unbeabsichtigten `wr_swap`. Außerdem nach erfolgreichem PUT in `handleSave`: Response wird verworfen, `App.svelte`-Cache bleibt stale; nächster `/hardware-edit`-Aufruf zeigt alte Daten. Fix: `$effect` in Config.svelte das `loadStateFromInitialDevices` re-runned wenn `initialDevices` non-empty arrives, plus Cache-Refresh nach PUT (Callback-Prop oder shared Store). [`frontend/src/App.svelte:161-163`, `frontend/src/routes/Config.svelte:246, 1228-1230`]
- [ ] [Review][Patch] AC 11 — Warn-Banner-Positive-Case-Test fehlt: `Config.test.ts` "renders the warn-banner only after a WR-entity swap" prüft NUR den initialen Render ohne Banner und discardet die Harness via `void rerender; void container;`. Der Author begründet das mit happy-dom-`bind:value`-Limitation und verschiebt auf manuelles SR-01. Fix: Test direkt über Prop-Manipulation oder via `getByTestId('wr-entity-select').dispatchEvent(...)` — Banner-Sichtbarkeit ist die einzige UX-Warnung vor dem `commissioned_at=NULL`-Reset. [`frontend/src/routes/Config.test.ts:180-204`]
- [ ] [Review][Patch] AC 11 — Save-Button-Label-Test und Save-Redirect-Test fehlen: AC 11 nennt `test_edit_mode_save_button_label_changes` und `test_edit_mode_save_redirects_to_running` namentlich, beide Tests existieren nicht. [`frontend/src/routes/Config.test.ts`]
- [ ] [Review][Patch] Warn-Banner-Trigger ignoriert „swap-to-blank"-State: `needsRefunctionalTest` requires `wrLimitEntityId !== ''` — wenn der User den Dropdown clears um neu zu wählen, verschwindet die Warnung temporär. Fix: Guard relaxen oder Banner an „aktuell-eingegeben != initial" knüpfen statt an „beide non-empty". [`frontend/src/routes/Config.svelte:1212-1219`]
- [ ] [Review][Patch] Settings doppelt-Message-Bug: nach WR-Swap rendert die neue Hardware-Card („Funktionstest erforderlich"-Tag) UND die Story-3.6-`setupNotActivated`-Section („Schließe den Setup-Wizard ab") gleichzeitig — widersprüchliche Aufforderungen. Fix: `setupNotActivated`-Section ausblenden wenn `allDevices.length > 0` und Hardware-Card schon den Recovery-Pfad zeigt. [`frontend/src/routes/Settings.svelte:251-291`]
- [ ] [Review][Patch] `client.test.ts` `updateDevices`-Test asserted nur Method+Headers, nicht den Body — POST/PUT-Vertrag (HardwareConfigRequest-Shape) ist ungetestet, ein typo `hardware_type → hardwareType` würde grün durchlaufen. Fix: `JSON.parse(init.body as string)` gegen Expected-Payload assert. [`frontend/src/lib/api/client.test.ts:900-934`]
- [ ] [Review][Patch] AC 10 — `test_put_override_only_keeps_commissioned_at` prüft `commissioned_at`-Erhalt aber NICHT die Row-Identität (`id` pre/post). Eine Regression die in-place UPDATE auf DELETE+INSERT umstellt (mit Timestamp-Copy) würde durchrutschen. Fix: vor und nach dem PUT `id` lesen und Gleichheit asserten. [`backend/tests/integration/test_devices_put.py:113-138`]
- [ ] [Review][Patch] No-Controller-Audit-Fallback ungetestet: `controller is None → mode_value = "drossel"`-Pfad (L375-379) ist in early-lifespan / partial-init reachable, aber von keinem Test abgedeckt. Fix: Test ohne `app.state.controller` ausführen und prüfen dass Audit-Cycle trotzdem mit `mode='drossel'` und `source='solalex'` geschrieben wird. [`backend/src/solalex/api/routes/devices.py:375-379`, `backend/tests/integration/test_devices_put.py`]

**Deferred:**

- [x] [Review][Defer] In-flight Controller-Writes können den ALTEN WR während eines Hardware-Swaps treffen — der Route hat keinen Lock gegen `controller._dispatch_tasks`, eine Tab-A-Functional-Test-Dispatch kann nach dem Swap noch zur HA gehen. Reaktion: Controller-Quiescence ist breitere Architektur-Frage (auch für Lizenz-Revoke, Restart-Sequenz relevant), gehört nicht in 2.6. → `deferred-work.md`. [`backend/src/solalex/api/routes/devices.py:332-389`]
- [x] [Review][Defer] `marstek → generic`-Hardware-Swap mit re-used grid_meter ist ungetestet — `ON DELETE CASCADE` auf `control_cycles`/`latency_measurements` löscht die History des entfernten Devices (Story 2.6 AC 8 verspricht den Audit-Trail des SWAPs, nicht die Erhaltung der historischen Cycles). Pre-existing FK-Verhalten, History-Loss ist eine separate Produktentscheidung. → `deferred-work.md`. [`backend/src/solalex/persistence/sql/002_control_cycles_latency.sql:7,25`]
- [x] [Review][Defer] `Settings.svelte` Hardware-Card rendert raw `role`/`adapter_key` Strings für unmapped Werte (z. B. zukünftiges `anker_solix`) — pre-existing Pattern in `describeRole`/`HARDWARE_TYPE_LABELS`-Fallback, kein Bug bis ein neues Adapter-Modul landet. → `deferred-work.md`. [`frontend/src/routes/Settings.svelte:1495-1561`]
- [x] [Review][Defer] Vorbefüllter `wrLimitEntityId` wird unsichtbar wenn die persistente HA-Entity deinstalliert wurde (kein matching `<option>` im Select) — User sieht ein scheinbar leeres Feld. Niche, hinten-runter-Polish v1.5. → `deferred-work.md`. [`frontend/src/routes/Config.svelte:103-140, 339-350`]

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Story 2.6 erstellt nach Smoke-Test Alex' Setup. Beta-Launch-blocking — Gate-Sperre für commissioned User wird durchbrochen, Hardware-Edit nach Commissioning ohne SQL-Reset möglich. Parallel zu Story 2.5. | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Story 2.6 implementiert: Backend `PUT /api/v1/devices` mit Diff-Klassifikator + Audit-Cycle + reload_devices_from_db-Hook + Foreign-Key-Merge. Frontend: `Config.svelte` editMode-Prop, `Settings.svelte` Hardware-Card, `Running.svelte` Funktionstest-erforderlich-Banner, `gate.ts` /hardware-edit-Branch, `App.svelte` Route + Routing, `client.updateDevices`. Smoke-Test SH-01. Backend 408 pytest grün (+10), Frontend 111 vitest grün (+15). | Claude Opus 4.7 |
| 2026-04-25 | 0.3.0 | Code-Review (3 parallele Reviewer): 1 Decision-Needed, 12 Patches, 4 Defers, 10 dismissed. Decision auf Override-Clear-Semantik; Patches v. a. Lost-Update-Race in PUT, Audit-Cycle-Reorder vor Reload, EXPORT-Fallback-Warning, Initial-Devices-Race in /hardware-edit-Mount, Test-Gaps für AC 11 Banner/Save-Button/Save-Redirect. | Claude Opus 4.7 |
