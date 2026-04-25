# Story 2.5: Smart-Meter-Vorzeichen-Toggle mit Live-Preview im Config-Flow

Status: in-progress

<!-- Erstellt 2026-04-25 als Reaktion auf Smoke-Test Alex' lokales HA-Setup (ESPHome SML `sensor.00_smart_meter_sml_current_load`). Beta-Launch-blocking — Story 2.4 Code-Review hatte den fehlenden Sign-Convention-Check bereits als High-Severity-Defer markiert ("Generic-Meter `detect()` ohne Sign-Convention-Check — invertierte Vorzeichen-Konventionen führen zu positivem Feedback in der Speicher-Policy"). Diese Story löst den Defer auf. -->

## Story

Als Beta-Tester mit einem Smart-Meter, dessen Vorzeichen-Konvention von Solalex' Standard abweicht (positiv = Einspeisung statt Bezug — bei vielen ESPHome-SML-Readern und MQTT-Bridges Standard, je nach OBIS-Konfig),
möchte ich im Config-Flow einen Toggle „Vorzeichen invertieren" mit einer Live-Preview, die mir sofort zeigt, was Solalex aktuell aus meinem Smart-Meter liest und ob das die richtige Richtung hat,
so dass ich vor dem Speichern verifizieren kann, dass Drossel/Speicher in die richtige Richtung regeln werden, und nicht nach dem Commissioning feststelle, dass mein WR genau falsch herum reguliert wird.

## Acceptance Criteria

1. **Toggle im Config-Flow:** `Config.svelte` zeigt unter dem Smart-Meter-Block (`useSmartMeter == true && gridMeterEntityId !== ''`) einen Toggle „Vorzeichen invertieren" mit Sub-Label „Aktivieren, wenn der gewählte Sensor Bezug als negative und Einspeisung als positive Werte liefert (häufig bei ESPHome-SML)". Default: aus.

2. **Live-Preview-Card direkt unter dem Toggle:** Sobald `gridMeterEntityId` gesetzt ist, zeigt die Card den aktuellen Sensor-Wert mit Vorzeichen, einer großen Watt-Zahl und einem Konventions-Hinweis-Satz: bei positivem effektivem Wert (nach optionaler Invertierung) „Bezug aus dem Netz", bei negativem „Einspeisung ins Netz", bei `|wert| < 50 W` „Sensor zeigt nahezu 0 W — schalt eine große Last (Wasserkocher, Heizlüfter) ein und beobachte die Richtung". Die Watt-Zahl ist nackt (CLAUDE.md UX-DR30: keine emotionalen Adjektive, keine Trend-Icons).

3. **Toggle wirkt sofort in der Live-Preview:** Wechselt der User den Toggle-Zustand, ändert sich die angezeigte Watt-Zahl und der Konventions-Hinweis-Satz innerhalb des nächsten Polling-Ticks. Der Toggle-Zustand wird **nicht** automatisch persistiert — Persistenz passiert ausschließlich beim normalen „Speichern"-Button am Ende des Config-Flows.

4. **Polling über existierenden `usePolling`-Hook:** Live-Preview pollt `GET /api/v1/setup/entity-state?entity_id=<gewählte_entity>` mit 1 s Intervall. Polling läuft nur, solange `gridMeterEntityId !== ''` und der User auf der Config-Page ist (`onDestroy` in `Config.svelte` ruft `polling.stop()`). Kein zweiter Poller, wenn der User die Entity wechselt — der bestehende Poller wird auf neue Entity umgestellt.

5. **Backend-Endpoint:** `GET /api/v1/setup/entity-state?entity_id=<entity_id>` liest den State direkt aus `state_cache.last_states` (kein DB-Hit, kein neuer HA-WS-Call). Antwort: `{"entity_id": "...", "value_w": <float|null>, "ts": "<iso>"}`. Der Endpoint subscribed automatisch über den existierenden HA-Client auf die Entity, falls noch nicht subscribed (analog zur HA-WS-Subscription beim Commissioning, aber ohne Persistenz). Antwort `value_w == null`, wenn die Entity (noch) keinen Wert geliefert hat.

6. **Whitelist-Schutz auf dem Endpoint:** Der Endpoint akzeptiert nur Entities, die `GET /api/v1/setup/entities` aktuell als `wr_limit_entities` oder `power_entities` zurückgibt. Andere Entities werden mit `403 Forbidden` (`application/problem+json`) abgewiesen. Verhindert, dass die UI als beliebige HA-Entity-Reader missbraucht werden kann.

7. **Persistenz in `device.config_json`:** Beim „Speichern" wird `invert_sign: true|false` in `device.config_json` des Grid-Meter-Devices geschrieben (Merge-Semantik wie Story 3.6 — nicht den ganzen `config_json` ersetzen, sondern den Schlüssel mergen). `HardwareConfigRequest` bekommt ein neues Feld `invert_sign: bool = False`. Routes-Code in `devices.py` reicht den Wert in den DB-Insert/Update durch.

8. **Anwendung im Controller — vor dem Smoothing-Buffer:** `Controller.on_sensor_update` flippt das Vorzeichen, **bevor** der Wert in einen Drossel-/Speicher-Buffer geht und bevor irgendeine Policy ihn sieht. Implementierung als 4-Zeilen-Helper in `controller.py` (kein neues Modul):
   ```python
   def _maybe_invert_sensor_value(self, device: DeviceRecord, value_w: float) -> float:
       if device.role == "grid_meter" and device.config().get("invert_sign", False) is True:
           return -value_w
       return value_w
   ```
   Aufruf direkt nach `_extract_sensor_w(event_msg)` in `on_sensor_update`. **Adapter selbst werden NICHT geändert** — `parse_readback` bleibt unverändert (wir flippen nur den Pfad in den Controller, nicht die Adapter-Konvention).

9. **Default-Verhalten unverändert:** Bestehende DBs ohne `invert_sign`-Key in `device.config_json` verhalten sich exakt wie heute (positiv = Bezug). `device.config().get("invert_sign", False)` ist die einzige Default-Quelle. Keine Migration, kein Backfill, kein Schema-Update.

10. **Live-Preview im Backend reflektiert den UI-Toggle:** Der `entity-state`-Endpoint gibt den **rohen** Sensor-Wert zurück (nicht invertiert) — das Frontend wendet den Toggle-Zustand client-seitig an. So muss der Endpoint nicht den UI-State kennen, und der User sieht beim Wechsel des Toggles direkt die invertierte Zahl ohne Round-Trip zum Server.

11. **Tests Backend:**
    - Unit-Test: `_maybe_invert_sensor_value` flippt nur bei `role == "grid_meter"` UND `invert_sign == True`; ignoriert bei anderen Rollen, ignoriert bei `invert_sign == False`/missing.
    - Unit-Test: `on_sensor_update` wendet den Flip an, bevor `_drossel_buffers`/`_speicher_buffers` gefüllt werden — verify durch Test, der ein invertiertes Device + 5 W Bezug-Event füttert und prüft, dass `_drossel_buffers[grid_meter_id]` `-5.0` statt `+5.0` enthält.
    - Integrations-Test: `GET /api/v1/setup/entity-state?entity_id=...` mit (a) gültiger Power-Entity → 200 + Wert; (b) ungültiger Entity → 403; (c) noch nicht subscribed → automatische Subscribe + Wert nach erstem State-Push.
    - Schema-Test: `HardwareConfigRequest({invert_sign: true})` wird akzeptiert; Persistenz schreibt `config_json` mit dem Key.
    - Migrations-Test: Alte Rows ohne `invert_sign` → `device.config()` returned `{}` und `_maybe_invert_sensor_value` gibt den Wert unverändert zurück.

12. **Tests Frontend:**
    - Vitest: Toggle-State steuert die Anzeige der Watt-Zahl (positive Anzeige bei deaktiviertem Toggle und +2120-W-Mock; negative Anzeige bei aktiviertem Toggle und +2120-W-Mock).
    - Vitest: Konventions-Hinweis-Satz wechselt zwischen „Bezug aus dem Netz" / „Einspeisung ins Netz" / „nahezu 0 W"-Hint je nach effektivem Wert.
    - Vitest: `usePolling` startet bei Entity-Wahl und stoppt bei `onDestroy` und bei Entity-Wechsel auf leer.
    - Vitest: `saveDevices` wird mit `invert_sign: true|false` aufgerufen entsprechend des Toggle-Zustands.

13. **Beta-Launch-Hinweis:** AC15 von Story 2.4 (Manual-QA gegen Trucki + ESPHome SML) wird durch diese Story um den Sign-Test ergänzt: Manual-Smoke-Test-Doku bekommt einen neuen Schritt „SR-01 Vorzeichen-Verifikation: aktivierter Wasserkocher → erwarte Wert-Steigerung (bei korrekter Konvention)".

## Tasks / Subtasks

- [ ] **Task 1: Backend `entity-state`-Endpoint** (AC 5, 6, 11)
  - [ ] Neuer Endpoint `GET /api/v1/setup/entity-state` in `backend/src/solalex/api/routes/setup.py`. Pydantic-Response-Model `EntityStateResponse` in `backend/src/solalex/api/schemas/setup.py`.
  - [ ] Whitelist-Logik: Endpoint ruft intern dieselbe Filter-Logik wie `get_entities()` auf (oder extrahiert die Filter-Funktion in einen Helper, damit beide Endpoints dieselbe Wahrheit haben). Bei Treffer in `wr_limit` oder `power` → Wert lesen; sonst 403.
  - [ ] Wert-Lesen aus `state_cache.last_states`. Falls Entity noch nicht im Cache: HA-WS-Subscribe ausführen (über bestehenden `ha_client.subscribe_entity`), `value_w = None` zurückgeben — der Frontend-Poller fragt 1 s später erneut und bekommt dann den Wert.
  - [ ] Wert-Konvertierung: Reuse `GenericMeterAdapter.parse_readback()` für die UoM-Konvertierung W↔kW. Adapter wird hier nur als Pure-Function genutzt, keine Adapter-Instanz im Endpoint.
  - [ ] Tests: 200/403/noch-nicht-subscribed-Pfad.

- [ ] **Task 2: Backend Schema + Save-Route** (AC 7, 9, 11)
  - [ ] `HardwareConfigRequest` in `backend/src/solalex/api/schemas/devices.py`: Feld `invert_sign: bool = False` hinzufügen.
  - [ ] `backend/src/solalex/api/routes/devices.py`: Beim Save den Wert in `config_json` des Grid-Meter-Records mergen (analog zu existierenden `min_limit_w`/`max_limit_w`-Overrides, aber für das **grid_meter-Device** — Achtung: aktuelle Override-Felder schreiben in den **wr_limit-Device**-Record).
  - [ ] Tests: Save mit `invert_sign=true` → DB-Row `device.config_json` enthält `{"invert_sign": true}` für das grid_meter-Device.
  - [ ] Tests: Save ohne `invert_sign` → DB-Row hat den Key NICHT (Pydantic-Default lässt ihn weg im JSON-Merge).

- [ ] **Task 3: Backend Controller-Anwendung** (AC 8, 9, 11)
  - [ ] Helper `_maybe_invert_sensor_value(self, device, value_w)` in `controller.py` ergänzen.
  - [ ] In `on_sensor_update` direkt nach `sensor_value = _extract_sensor_w(event_msg)` aufrufen. Resultat wird durchgereicht in `_dispatch_by_mode`/`_evaluate_mode_switch`.
  - [ ] Auch die Helper-Methode `_grid_in_feedin_band` (controller.py:844) muss den invertierten Wert berücksichtigen — sie nimmt aktuell aus dem Buffer; da der Buffer bereits den invertierten Wert enthält, ist hier KEIN zusätzlicher Flip nötig. Im Code-Kommentar dokumentieren.
  - [ ] Tests: Ein Drossel-Test + ein Speicher-Test, jeweils mit `config_json={"invert_sign": True}` auf dem grid_meter-Device, der prüft, dass eine positive Sensor-Eingabe wie eine negative behandelt wird (Drossel: kein Drossel-Down bei +Wert; Speicher: Charge bei +Wert statt Discharge).

- [ ] **Task 4: Frontend `Config.svelte` Toggle + Live-Preview** (AC 1, 2, 3, 4, 12)
  - [ ] State `invertSign = $state(false)`. Conditional unter dem Smart-Meter-Block, nur wenn `useSmartMeter && gridMeterEntityId !== ''`.
  - [ ] Live-Preview-Card als neue `<section class="config-section live-preview">` mit:
    - Großer Watt-Zahl (font-size analog zu existierenden Card-Headern, tabular-nums)
    - Konvention-Satz darunter
    - Bei `Math.abs(effectiveValue) < 50` der Zero-Hint statt Konvention-Satz
  - [ ] Polling-Hook: `usePolling(client.getEntityState(gridMeterEntityId), 1000)`. Polling läuft nur bei gesetzter Entity.
  - [ ] Toggle als Standard-Checkbox (analog `nightDischargeEnabled` in derselben Datei). Sub-Label genau wie in AC 1.
  - [ ] `effectiveValue = invertSign ? -rawValue : rawValue` — keine Backend-Roundtrip-Abhängigkeit für Toggle-Wechsel.
  - [ ] `handleSave` reicht `invert_sign: invertSign` an `client.saveDevices` durch.

- [ ] **Task 5: Frontend Client + Types** (AC 5, 7, 12)
  - [ ] `frontend/src/lib/api/client.ts`: Neue Funktion `getEntityState(entityId: string): Promise<EntityState>`.
  - [ ] `frontend/src/lib/api/types.ts`: Neuer Type `EntityState = { entity_id: string; value_w: number | null; ts: string }`. `HardwareConfigRequest`-Type um `invert_sign?: boolean` erweitern.
  - [ ] Tests: `client.test.ts` deckt 200- und 403-Pfad ab.

- [ ] **Task 6: Doku-Updates** (AC 13)
  - [ ] `_bmad-output/qa/manual-tests/smoke-test.md`: Neuer Test SR-01 „Vorzeichen-Verifikation". Schritt: nach Smart-Meter-Wahl die Live-Preview-Card lesen, große Last anschalten, prüfen ob Wert in die erwartete Richtung wandert, ggf. Toggle setzen.
  - [ ] `CLAUDE.md`: In der Pro-Device-Override-Schema-Liste (Regel 2 / Hardware-Day-1) den Key `invert_sign` ergänzen.

- [ ] **Task 7: Validierung und Final-Gates** (AC 11, 12, 13)
  - [ ] Backend: `cd backend && uv run ruff check . && uv run mypy . && uv run pytest`
  - [ ] Frontend: `cd frontend && npm run lint && npm run check && npm test && npm run build`
  - [ ] Manual: Alex testet auf seinem ESPHome-SML — Toggle-Zustand + Live-Preview-Wert vor dem Speichern stimmen mit Wasserkocher-Test überein.

## Dev Notes

### Architektur-Bezugspunkte

- **Story 2.4 Code-Review-Defer (2026-04-25):** „Generic-Meter `detect()` ohne Sign-Convention-Check — invertierte Vorzeichen-Konventionen führen zu positivem Feedback in der Speicher-Policy. **High** — deferred, Beta-Scope." [Source: `_bmad-output/implementation-artifacts/2-4-generic-adapter-refit.md` Review Findings]
- **Generic-Meter-Adapter explizite Konvention:** „Sign convention: positive value = grid import, negative = export. The source entity must conform; **the adapter does not flip signs**." [Source: `backend/src/solalex/adapters/generic_meter.py:7-8`]
- **Drossel-Policy hartkodiert:** „Shelly-3EM sign convention: positive = grid import (Bezug), negative = grid export (Einspeisung). Since the new WR limit is `current + smoothed`, a negative smoothed value drives the limit *down*…" [Source: `backend/src/solalex/controller.py:494-498`]
- **Speicher-Policy hartkodiert:** „Sign convention (Story 3.4 AC 20): Smart-meter — positive = grid import (Bezug), negative = grid export (Einspeisung). … Setpoint = `-smoothed` (sign-flip)…" [Source: `backend/src/solalex/controller.py:928-935`]
- **CLAUDE.md Pro-Device-Override-Schema:** Regel 2 listet `deadband_w`, `min_step_w`, `smoothing_window`, `limit_step_clamp_w`, `min_limit_w`, `max_limit_w`. Diese Story erweitert die Liste um `invert_sign` (Bool).
- **UX-DR30:** „Zahlen im UI sind nackt (keine emotionalen Adjektive, keine Trend-Icons ohne Anlass). Charakter-Zeilen beschreiben nur das Tun, nicht die Zahl." Live-Preview-Card folgt dem.
- **Architecture Single-Source-of-Truth:** Bei Konflikt mit dieser Story gewinnt `_bmad-output/planning-artifacts/architecture.md`.

### Aktueller Codezustand und Ziel-Änderungen

- `backend/src/solalex/api/routes/setup.py` hat bereits `GET /api/v1/setup/entities`, das aus `ha_client.client.get_states()` die drei gefilterten Listen baut. Diese Story ergänzt einen zweiten GET-Endpoint, der den State **einer einzelnen** Entity aus dem `state_cache` liest. Die Filter-Logik aus `get_entities()` muss in einen Helper extrahiert werden, der von beiden Endpoints genutzt wird, damit Whitelist und Listing immer konsistent sind.
- `backend/src/solalex/controller.py` `on_sensor_update` (Zeilen 273-359) extrahiert `sensor_value` aus dem Event und reicht es an `_dispatch_by_mode` durch. Genau hier (zwischen `sensor_value = _extract_sensor_w(...)` und `switch = self._evaluate_mode_switch(...)`) kommt der Helper-Aufruf.
- `backend/src/solalex/persistence/repositories/devices.py` hat bereits `update_device_config_json` (Story 3.6) — Merge-Semantik ist da. `HardwareConfigRequest`-Save-Route muss diese Funktion oder denselben Merge-Pattern für das **grid_meter-Device** anwenden (heute schreibt sie `min_limit_w`/`max_limit_w` nur ins **wr_limit**-Device).
- `frontend/src/lib/polling/usePolling.ts` ist der existierende Polling-Hook von Story 5.1a — wiederverwenden, nicht neu bauen.
- `frontend/src/routes/Config.svelte` hat bereits Skeleton-Pulse, error-block, hint, field-row, checkbox-row Styles — wiederverwenden.

### Implementation Guardrails

- **Kein Modal:** UX-DR30. Live-Preview ist eine Card, kein Popup.
- **Kein Loading-Spinner:** Skeleton-Pulse ≥ 400 ms wie überall sonst (Config.svelte hat das bereits).
- **Keine emotionalen Adjektive in Hint-Texten:** „Bezug aus dem Netz" / „Einspeisung ins Netz" — nicht „Du beziehst gerade!" / „Super, du speist ein!". Nüchtern bleiben.
- **Adapter NICHT ändern:** `GenericMeterAdapter.parse_readback` bleibt unverändert. Sign-Flip passiert ausschließlich im Controller-Pfad. Begründung: Adapter-Konvention ist Vertrag mit der Hardware (parse_readback wird auch von Readback-Verifikation des `wr_limit`-Adapters genutzt; den Vertrag nicht für Smart-Meter-Spezialfall aufbohren).
- **Kein neues Polling-Pattern:** `lib/polling/usePolling.ts` reuse, nicht neue `setInterval`-Konstrukte in `Config.svelte` einführen.
- **Whitelist NICHT umgehen:** Der Endpoint darf NIE eine beliebige HA-Entity ohne Whitelist-Check zurückgeben, sonst wird er zum Reflektor-Risiko (jeder Frontend-Bug oder XSS-Vektor könnte beliebige HA-Sensor-Werte exfiltrieren).
- **Kein Auto-Detect der Konvention:** User-Klick bleibt Pflicht. Auto-Detect (z. B. „der Wert war 30 s lang positiv → wahrscheinlich Bezug") ist trügerisch (Solar-Mittag mit Einspeisung würde Auto-Detect verfälschen). Die Live-Preview ist die ehrliche Lösung: User entscheidet selbst nach visueller Verifikation.
- **Kein OpenAPI-Codegen:** Handgeschriebene TS-Types (CLAUDE.md).
- **snake_case in API-JSON:** `value_w`, `entity_id`, `invert_sign` — kein camelCase im JSON-Vertrag (CLAUDE.md Regel 1).

### File Structure Requirements

```text
backend/src/solalex/
├── api/
│   ├── routes/
│   │   ├── setup.py             [MOD: neuer GET /entity-state Endpoint + Filter-Helper extrahiert]
│   │   └── devices.py           [MOD: HardwareConfigRequest.invert_sign in grid_meter-config_json mergen]
│   └── schemas/
│       ├── setup.py             [MOD: EntityStateResponse]
│       └── devices.py           [MOD: HardwareConfigRequest.invert_sign Feld]
├── controller.py                [MOD: _maybe_invert_sensor_value Helper + Aufruf in on_sensor_update]
└── persistence/repositories/
    └── devices.py               [UNCHANGED: update_device_config_json existiert bereits]

frontend/src/
├── lib/
│   └── api/
│       ├── client.ts            [MOD: getEntityState]
│       └── types.ts             [MOD: EntityState type, HardwareConfigRequest.invert_sign]
└── routes/
    └── Config.svelte            [MOD: invertSign-State, Live-Preview-Card, usePolling-Aufruf, Save-Param]

_bmad-output/qa/manual-tests/
└── smoke-test.md                [MOD: Neuer Test SR-01]

CLAUDE.md                        [MOD: invert_sign zur config_json-Override-Liste in Regel 2]
```

### Testing Requirements

- **Backend**: pytest-Sweep ergänzt um:
  - `test_setup_routes.py`: `test_entity_state_returns_cached_value`, `test_entity_state_403_for_non_whitelisted_entity`, `test_entity_state_subscribes_on_first_request`.
  - `test_devices_repo.py` / `test_devices_api.py`: `test_save_invert_sign_persists_to_grid_meter_config_json`, `test_save_without_invert_sign_omits_key`.
  - `test_controller.py` o. ä.: `test_maybe_invert_sensor_value_only_for_grid_meter_with_flag`, `test_on_sensor_update_buffer_contains_inverted_value`.
  - `test_controller_drossel_policy.py`: `test_drossel_with_inverted_grid_meter_treats_positive_as_export`.
  - `test_controller_speicher_policy.py`: `test_speicher_with_inverted_grid_meter_charges_on_positive_input`.
- **Frontend**: vitest-Sweep ergänzt um:
  - `Config.test.ts`: `test_toggle_invert_inverts_displayed_value`, `test_zero_hint_shown_below_50w_threshold`, `test_save_includes_invert_sign_flag`, `test_polling_starts_on_entity_select_and_stops_on_clear`.
  - `client.test.ts`: `test_get_entity_state_handles_200_and_403`.

### References

- [Source: `backend/src/solalex/adapters/generic_meter.py:7-8`] Sign-Konvention dokumentiert
- [Source: `backend/src/solalex/controller.py:494-498`] Drossel-Policy Sign-Annahme
- [Source: `backend/src/solalex/controller.py:928-935`] Speicher-Policy Sign-Annahme
- [Source: `backend/src/solalex/controller.py:273-359`] `on_sensor_update` Einfügepunkt
- [Source: `backend/src/solalex/api/routes/setup.py`] `get_entities` Filter-Logik (Whitelist-Quelle)
- [Source: `backend/src/solalex/persistence/repositories/devices.py:130-147`] `update_device_config_json` Merge-Helper
- [Source: `frontend/src/lib/polling/usePolling.ts`] Polling-Hook
- [Source: `frontend/src/routes/Config.svelte`] Bestehender Config-Flow
- [Source: `_bmad-output/implementation-artifacts/2-4-generic-adapter-refit.md` Review Findings] Defer-Begründung
- [Source: `CLAUDE.md` Regel 2] Pro-Device-Override-Schema
- [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` UX-DR30] Anti-Pattern-Liste

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
SR-01 Vorzeichen-Verifikation (smoke-test.md):
1. Config-Flow: Smart-Meter wählen → Live-Preview-Card lesen
2. Wasserkocher anschalten (~2000 W Last)
3. Erwartung bei korrektem Toggle: angezeigter Wert steigt deutlich an + Konvention-Hinweis lautet „Bezug aus dem Netz"
4. Wenn Wert FÄLLT statt zu steigen → Toggle „Vorzeichen invertieren" aktivieren
5. Speichern, Funktionstest durchführen
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
| 2026-04-25 | 0.1.0 | Story 2.5 erstellt nach Smoke-Test Alex' Setup. Schließt Story-2.4-Code-Review-Defer „Generic-Meter ohne Sign-Convention-Check" auf. Beta-Launch-blocking. | Claude Opus 4.7 |
