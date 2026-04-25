# Story 2.6: Hardware-Setup nachträglich ändern (Edit nach Commissioning)

Status: in-progress

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

- [ ] **Task 1: Backend `PUT /api/v1/devices`-Endpoint** (AC 3, 7, 8, 10)
  - [ ] Route in `backend/src/solalex/api/routes/devices.py`: `@router.put("/")` mit demselben `HardwareConfigRequest`-Body.
  - [ ] Diff-Logik: Lade aktuelle Devices, vergleiche mit Body, kategorisiere Änderung in (a) Override-only-Update, (b) Smart-Meter-Wechsel, (c) WR-Wechsel, (d) Hardware-Typ-Wechsel.
  - [ ] In-place Updates für (a) via `update_device_config_json` (existiert).
  - [ ] Replace-Logik für (b)/(c)/(d): alte Row löschen oder `commissioned_at=NULL` setzen (Race-frei: SELECT-für-UPDATE → Diff → DELETE/INSERT/UPDATE in einer Transaktion).
  - [ ] Audit-Cycle schreiben (siehe AC 8).
  - [ ] `controller.reload_devices_from_db()` aufrufen.
  - [ ] Tests: alle 5 Backend-Test-Cases aus AC 10.

- [ ] **Task 2: Backend Schema-Konsolidierung** (AC 3)
  - [ ] `HardwareConfigRequest` ist bereits dafür ausgelegt — sicherstellen, dass alle in Story 2.5 / 3.6 hinzugefügten Felder (`invert_sign`, `min_soc`, `max_soc`, `night_*`) im PUT-Pfad ebenfalls validiert und gemerged werden.
  - [ ] DTO-Test: PUT-Body mit allen optionalen Feldern → korrekt deserialisiert.

- [ ] **Task 3: Frontend `Config.svelte` Edit-Modus** (AC 2, 5, 11)
  - [ ] Prop `editMode = $props.editMode ?? false` und `initialConfig = $props.initialConfig` (DeviceResponse[]).
  - [ ] `onMount`: wenn `editMode`, fülle State-Variablen aus `initialConfig` (hardwareType, wrLimitEntityId, …) statt aus Defaults.
  - [ ] Header-Text und Save-Button-Label conditional auf `editMode`.
  - [ ] Save-Funktion: `editMode ? client.updateDevices(...) : client.saveDevices(...)`. Redirect: `editMode ? '#/running' : '#/functional-test'`.
  - [ ] Warn-Banner-Komponente am Page-Top, conditional auf Edit-Modus + erkanntes WR-Wechsel-Diff (vergleiche aktuell-eingegebene Werte mit `initialConfig`).
  - [ ] Tests: Initial-Werte-Befüllung, Save-Button-Label, Redirect, Warn-Banner-Sichtbarkeit.

- [ ] **Task 4: Frontend Settings-Card** (AC 1, 11)
  - [ ] In `Settings.svelte` neue Card `<section class="settings-section">` für Hardware-Konfiguration. Liest Devices aus `client.getDevices()` (gleiche Quelle wie `Running.svelte`).
  - [ ] Anzeige: Hardware-Typ-Label (Mapping aus existierenden Files: generic → „Wechselrichter (allgemein)", marstek_venus → „Marstek Venus"), Entity-IDs, optional Smart-Meter mit Sign-Invert-Status.
  - [ ] Button „Hardware ändern" → `window.location.hash = '#/hardware-edit'`.
  - [ ] Tests: Card-Rendering und Navigation.

- [ ] **Task 5: Frontend Routing + Gate** (AC 4, 11)
  - [ ] `frontend/src/App.svelte`: neue Route `/hardware-edit` registrieren, `VALID_ROUTES`-Set ergänzen, dynamisch `Config.svelte` mit `editMode={true}` und `initialConfig` aus `getDevices()`-Cache instantiieren.
  - [ ] `frontend/src/lib/gate.ts`: neuer Branch `if (currentRoute === '/hardware-edit')` analog zum `/settings`-Branch (pre-accepted? sonst Disclaimer; commissioned? → stay; nicht commissioned? → bounce zu `#/`).
  - [ ] `gate.test.ts` ergänzen.

- [ ] **Task 6: Frontend Client + Types** (AC 3, 11)
  - [ ] `client.ts`: `updateDevices(req: HardwareConfigRequest): Promise<DeviceResponse[]>` (PUT statt POST).
  - [ ] Types: keine neuen Types nötig, beide Endpoints teilen `HardwareConfigRequest` und `DeviceResponse[]`.
  - [ ] Tests: `client.test.ts` PUT-Pfad.

- [ ] **Task 7: `/running`-Page Funktionstest-Hinweis** (AC 9)
  - [ ] `Running.svelte`: Wenn ein commissioned-Wert mit `wr_limit`-Role, aber `commissioned_at == null` existiert → Banner oben in der Page „Funktionstest erforderlich für neuen Wechselrichter" mit Link `#/functional-test`.
  - [ ] Tests: `Running.test.ts` Banner-Sichtbarkeit.

- [ ] **Task 8: Doku-Updates** (AC 12)
  - [ ] Smoke-Test SH-01.
  - [ ] CLAUDE.md Stop-Signal-Liste.

- [ ] **Task 9: Validierung und Final-Gates** (AC 10, 11, 12)
  - [ ] Backend: ruff, mypy, pytest.
  - [ ] Frontend: lint, check, vitest, build.
  - [ ] Manual: Alex testet Hardware-Wechsel im laufenden Betrieb (grid_meter only → WR ergänzen → Funktionstest → Drossel regelt).

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

(wird beim Dev-Story-Workflow gefüllt)

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Story 2.6 erstellt nach Smoke-Test Alex' Setup. Beta-Launch-blocking — Gate-Sperre für commissioned User wird durchbrochen, Hardware-Edit nach Commissioning ohne SQL-Reset möglich. Parallel zu Story 2.5. | Claude Opus 4.7 |
