# Story 2.5: Smart-Meter-Vorzeichen-Toggle mit Live-Preview im Config-Flow

Status: done

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

- [x] **Task 1: Backend `entity-state`-Endpoint** (AC 5, 6, 11)
  - [x] Neuer Endpoint `GET /api/v1/setup/entity-state` in `backend/src/solalex/api/routes/setup.py`. Pydantic-Response-Model `EntityStateResponse` in `backend/src/solalex/api/schemas/setup.py`.
  - [x] Whitelist-Logik: Endpoint ruft intern dieselbe Filter-Logik wie `get_entities()` auf (oder extrahiert die Filter-Funktion in einen Helper, damit beide Endpoints dieselbe Wahrheit haben). Bei Treffer in `wr_limit` oder `power` → Wert lesen; sonst 403.
  - [x] Wert-Lesen aus `state_cache.last_states`. Falls Entity noch nicht im Cache: HA-WS-Subscribe ausführen (über bestehenden `ha_client.subscribe_entity`), `value_w = None` zurückgeben — der Frontend-Poller fragt 1 s später erneut und bekommt dann den Wert.
  - [x] Wert-Konvertierung: Reuse `GenericMeterAdapter.parse_readback()` für die UoM-Konvertierung W↔kW. Adapter wird hier nur als Pure-Function genutzt, keine Adapter-Instanz im Endpoint.
  - [x] Tests: 200/403/noch-nicht-subscribed-Pfad.

- [x] **Task 2: Backend Schema + Save-Route** (AC 7, 9, 11)
  - [x] `HardwareConfigRequest` in `backend/src/solalex/api/schemas/devices.py`: Feld `invert_sign: bool = False` hinzufügen.
  - [x] `backend/src/solalex/api/routes/devices.py`: Beim Save den Wert in `config_json` des Grid-Meter-Records mergen (analog zu existierenden `min_limit_w`/`max_limit_w`-Overrides, aber für das **grid_meter-Device** — Achtung: aktuelle Override-Felder schreiben in den **wr_limit-Device**-Record).
  - [x] Tests: Save mit `invert_sign=true` → DB-Row `device.config_json` enthält `{"invert_sign": true}` für das grid_meter-Device.
  - [x] Tests: Save ohne `invert_sign` → DB-Row hat den Key NICHT (Pydantic-Default lässt ihn weg im JSON-Merge).

- [x] **Task 3: Backend Controller-Anwendung** (AC 8, 9, 11)
  - [x] Helper `_maybe_invert_sensor_value(self, device, value_w)` in `controller.py` ergänzen.
  - [x] In `on_sensor_update` direkt nach `sensor_value = _extract_sensor_w(event_msg)` aufrufen. Resultat wird durchgereicht in `_dispatch_by_mode`/`_evaluate_mode_switch`.
  - [x] Auch die Helper-Methode `_grid_in_feedin_band` (controller.py:844) muss den invertierten Wert berücksichtigen — sie nimmt aktuell aus dem Buffer; da der Buffer bereits den invertierten Wert enthält, ist hier KEIN zusätzlicher Flip nötig. Im Code-Kommentar dokumentieren.
  - [x] Tests: Ein Drossel-Test + ein Speicher-Test, jeweils mit `config_json={"invert_sign": True}` auf dem grid_meter-Device, der prüft, dass eine positive Sensor-Eingabe wie eine negative behandelt wird (Drossel: kein Drossel-Down bei +Wert; Speicher: Charge bei +Wert statt Discharge).

- [x] **Task 4: Frontend `Config.svelte` Toggle + Live-Preview** (AC 1, 2, 3, 4, 12)
  - [x] State `invertSign = $state(false)`. Conditional unter dem Smart-Meter-Block, nur wenn `useSmartMeter && gridMeterEntityId !== ''`.
  - [x] Live-Preview-Card als neue `<section class="config-section live-preview">` mit:
    - Großer Watt-Zahl (font-size analog zu existierenden Card-Headern, tabular-nums)
    - Konvention-Satz darunter
    - Bei `Math.abs(effectiveValue) < 50` der Zero-Hint statt Konvention-Satz
  - [x] Polling-Hook: `usePolling(client.getEntityState(gridMeterEntityId), 1000)`. Polling läuft nur bei gesetzter Entity.
  - [x] Toggle als Standard-Checkbox (analog `nightDischargeEnabled` in derselben Datei). Sub-Label genau wie in AC 1.
  - [x] `effectiveValue = invertSign ? -rawValue : rawValue` — keine Backend-Roundtrip-Abhängigkeit für Toggle-Wechsel.
  - [x] `handleSave` reicht `invert_sign: invertSign` an `client.saveDevices` durch.

- [x] **Task 5: Frontend Client + Types** (AC 5, 7, 12)
  - [x] `frontend/src/lib/api/client.ts`: Neue Funktion `getEntityState(entityId: string): Promise<EntityState>`.
  - [x] `frontend/src/lib/api/types.ts`: Neuer Type `EntityState = { entity_id: string; value_w: number | null; ts: string }`. `HardwareConfigRequest`-Type um `invert_sign?: boolean` erweitern.
  - [x] Tests: `client.test.ts` deckt 200- und 403-Pfad ab.

- [x] **Task 6: Doku-Updates** (AC 13)
  - [x] `_bmad-output/qa/manual-tests/smoke-test.md`: Neuer Test SR-01 „Vorzeichen-Verifikation". Schritt: nach Smart-Meter-Wahl die Live-Preview-Card lesen, große Last anschalten, prüfen ob Wert in die erwartete Richtung wandert, ggf. Toggle setzen.
  - [x] `CLAUDE.md`: In der Pro-Device-Override-Schema-Liste (Regel 2 / Hardware-Day-1) den Key `invert_sign` ergänzen.

- [x] **Task 7: Validierung und Final-Gates** (AC 11, 12, 13)
  - [x] Backend: `cd backend && uv run ruff check . && uv run mypy . && uv run pytest`
  - [x] Frontend: `cd frontend && npm run lint && npm run check && npm test && npm run build`
  - [x] Manual: Alex testet auf seinem ESPHome-SML — Toggle-Zustand + Live-Preview-Wert vor dem Speichern stimmen mit Wasserkocher-Test überein.

### Review Findings

Code-Review 2026-04-25 (3-Layer adversarial: Blind Hunter + Edge Case Hunter + Acceptance Auditor; Diff `7d3bf25..HEAD` gefiltert auf 15 Story-2.5-Files).

#### Decision-needed

- [x] [Review][Decision] **Fail-Open vs. Skip-Cycle bei `invert_sign`-Config-Parse-Failure** — Entschieden: **Skip-Cycle** (Option a). `_maybe_invert_sensor_value` returnt jetzt `None` bei `JSONDecodeError` oder Non-Dict-Payload; die Policies kürzen die Cycle ab über ihre vorhandenen `sensor_value_w is None`-Early-Exits. Zusätzlich latched Once-per-Device-Log (P10) gegen Spam.

#### Patch (high)

- [x] [Review][Patch] **`id(pool)` als Key für `_speicher_pending_setpoints` ist nach `reload_devices_from_db` nicht stabil** [backend/src/solalex/controller.py:1135] — CPython recycled freigegebene IDs; Vergleich kann nach Reload (Story 2.6 PUT-Endpoint) entweder garantiert mismatchen oder versehentlich auf einen anderen Pool matchen. Vorher `pool_key`. Stabilen Identifier wiederherstellen.
- [x] [Review][Patch] **Audit-Cycle-Mode kennt `Mode.EXPORT` nicht und fällt auf "drossel" zurück** [backend/src/solalex/api/routes/devices.py:345-353] — Wenn der Controller im `Mode.EXPORT` läuft (Amendment 2026-04-25), wird der Audit-Eintrag fälschlich als `drossel` geloggt. CLAUDE.md: Audit-Trail-Klarheit ist non-verhandelbar. EXPORT-Branch ergänzen (idle-Default als sentinel statt drossel).
- [x] [Review][Patch] **`get_entity_state` ruft bei jedem Cache-Miss `get_states` auf — Polling-Hammer auf HA** [backend/src/solalex/api/routes/setup.py:684-737] — `LivePreviewCard` pollt im 1-s-Takt. Bei stillen Sensoren (kein `state_changed`) feuert jede Anfrage einen vollen `get_states`-Snapshot. Mitigation: Whitelist-Cache pro Entity einmal befüllen (z.B. `{entity_id: classification}` mit kurzer TTL), danach nur cached subscribe + `value_w=null` zurückgeben.
- [x] [Review][Patch] **Toggle-Off im editMode wird durch `_merge_config` verschluckt** [backend/src/solalex/api/routes/devices.py:132-144 + 170-190] — User mit gespeichertem `invert_sign=true` deaktiviert den Toggle und speichert. Frontend sendet `invert_sign=False` → omit-when-False schreibt `{}` ins Body. PUT mergt `existing={"invert_sign":true}` mit incoming `{}` → bleibt `{invert_sign:true}`. `_row_diff_kind` meldet `identical`, kein DB-Write. Der un-flip schlägt schweigend fehl → Control-Loop regelt weiter in falsche Richtung. AC 7 Merge-Semantik muss Key-Deletes unterstützen oder `invert_sign` explizit als `False` persistiert werden (nicht omit-when-False).
- [x] [Review][Patch] **Speicher-Policy-Test mit invertiertem Smart-Meter fehlt (AC 11 / Task 3)** [backend/tests/unit/test_controller_invert_sign.py] — Spec fordert explizit „Speicher: Charge bei +Wert statt Discharge". Aktuell nur Drossel-Buffer-Tests. Test ergänzen, der `Mode.SPEICHER` mit `invert_sign=True` + +Wert füttert und Charge-Decision verifiziert.

#### Patch (medium)

- [x] [Review][Patch] **Drossel-Policy-Test bleibt auf Buffer-Ebene statt Policy-Outcome (AC 11)** [backend/tests/unit/test_controller_invert_sign.py] — `test_drossel_buffer_contains_inverted_value` prüft `list(buf) == [-5.0]`, nicht „kein Drossel-Down bei +Wert". Buffer-Test ist Implementations-Detail-Aufnahme; Policy-Outcome-Test schützt vor Refactorings, die den Buffer umgehen.
- [x] [Review][Patch] **`_merge_config(existing, target) != existing.config_json` — Vergleich gegen unklarem Type** [backend/src/solalex/api/routes/devices.py:226] — Wenn `existing.config_json` als JSON-String aus der DB kommt und `_merge_config` ein dict zurückgibt, vergleicht der Code dict vs str → immer != → unnötige UPDATEs jeden PUT. Falls beides dicts sind (Repository deserializes), könnte trotzdem Key-Reihenfolge zu False-Negativen führen. Symmetric-Diff statt Inequality + cast verifizieren.
- [x] [Review][Patch] **`gridMeter`-Insert markiert ALLE NULL-`commissioned_at`-Meter als commissioned** [backend/src/solalex/api/routes/devices.py:262-268] — `UPDATE devices SET commissioned_at = ? WHERE role = 'grid_meter' AND commissioned_at IS NULL` filtert nicht nach der frisch eingefügten Row. Bei zukünftigen Multi-Meter-Szenarien oder Legacy-Daten werden alle als commissioned markiert. WHERE-Filter um `id = ?` ergänzen.
- [x] [Review][Patch] **`get_entity_state` Subscribe-Failure → 200 mit `value_w=null` statt 5xx** [backend/src/solalex/api/routes/setup.py:725-737] — Wenn `ensure_entity_subscriptions` raises, wird das suggestiv als „noch keine Werte" reportet. Frontend pollt weiter, jeder Tick re-subscribed (mit `get_states`-Roundtrip). Mindestens 503 (HA unreachable) oder Cached-Error-State.
- [x] [Review][Patch] **`invert_sign_config_parse_failed` läuft pro Sensor-Event, wenn `config_json` malformed** [backend/src/solalex/controller.py:384-390] — Bei 1–10 Hz Sensor-Rate spamt `logger.exception` `/data/logs/` und rotiert genuine Errors aus. Once-per-device-Flag analog zum Cap-Flag-Pattern (siehe `_speicher_night_gate_active`) oder einmal-pro-N-Cycles rate-limiten.

#### Patch (low)

- [x] [Review][Patch] **`LivePreviewCard.svelte` `subscribe`-Subscriptions werden nie cleant** [frontend/src/lib/components/LivePreviewCard.svelte:1700-1712] — `p.data.subscribe(...)` und `p.error.subscribe(...)` werfen den Unsubscriber weg. Bei Entity-Wechsel oder Component-Unmount bleiben Closures hängen. Unsubscriber sammeln und in `onDestroy` + bei Entity-Wechsel cleanen.
- [x] [Review][Patch] **Sub-Watt-Drift versteckt sich an der 50-W-Threshold-Grenze** [frontend/src/lib/components/LivePreviewCard.svelte:1768] — `Math.round(50.4)` zeigt „50 W", aber `Math.abs(effectiveValueW) < 50` ist false → „Bezug aus dem Netz" trotz „nahezu 0 W"-Optik. Threshold gegen rounded value oder konsistent rounden.
- [x] [Review][Patch] **`entity_id` wird ohne Regex-Validation in Cache-Lookup + Subscribe gereicht** [backend/src/solalex/api/routes/setup.py:684] — HA's entity_id-Constraint (`^[a-z][a-z0-9_]*\.[a-z0-9_]+$`) wird im Backend nicht enforced. Defensiver Regex-Check vor Cache-Lookup; fail-fast bei mismatch (422 statt subscribe-attempt + 403).

#### Defer

- [x] [Review][Defer] **Vitest „saveDevices wird mit invert_sign aufgerufen" fehlt (AC 12, 4. Bullet)** [frontend/src/routes/Config.test.ts] — happy-dom propagiert `change`-Events auf `<select bind:value>` nicht zurück in Svelte-5-Runen-Setter; Begründung im Code-Comment dokumentiert. Abdeckung über Backend-Roundtrip-Test + LivePreviewCard-Isolation + Manual-SR-01. Patch wäre eine andere Test-Strategie (props-mocking statt DOM-driven), Aufwand > Nutzen für Beta.
- [x] [Review][Defer] **Vitest „Polling stoppt bei Entity-Wechsel auf leer" partiell** [frontend/src/lib/components/LivePreviewCard.test.ts] — Mount/Unmount getestet, der Branch `entityId === ''` → `stopPolling()` direkt nicht. In der Praxis durch `{#if}` in Config.svelte abgefangen, theoretisch aber eigene Pfad. Low-Risk.
- [x] [Review][Defer] **`get_states`-Roundtrip auf Cache-Miss-Pfad weicht von AC 5 wörtlich ab** [backend/src/solalex/api/routes/setup.py:698] — Spec sagt „kein neuer HA-WS-Call". Cache-Miss zwingt aber zu einem Roundtrip, weil Whitelist-Verifikation sonst nicht möglich ist. Trade-off mit AC 6 bewusst, durch Patch P3 (Whitelist-Cache) deutlich entschärft.
- [x] [Review][Defer] **`adapter_key`-Wechsel bei gleicher (entity_id, role) wird als `override_only` klassifiziert** [backend/src/solalex/api/routes/devices.py:133-142] — Adapter-Wechsel bei gleicher Entity sollte `commissioned_at` zurücksetzen + Functional-Test erzwingen. Story-2.6-Scope (PUT-Endpoint), nicht 2.5.
- [x] [Review][Defer] **`override_only`-Branch DELETEt nichts und INSERTet nichts — orphan-rows bei Multi-Row-Schema-Edge-Case** [backend/src/solalex/api/routes/devices.py:230-237] — Pre-existing Schema-Issue (kein UNIQUE-Constraint auf (entity_id, role) sichtbar). Nicht Story-2.5-Scope.
- [x] [Review][Defer] **Mehrere `grid_meter`-Devices: nur das erste wird invertiert; Buffer-Mix möglich** [backend/src/solalex/controller.py:367-396] — v1 erlaubt nur ein grid_meter; Multi-Meter ist v1.5+. Aktuell pre-existing Schema-Voraussetzung.
- [x] [Review][Defer] **Concurrent PUT + battery-config PATCH: lost-update auf `wr_charge.config_json`** [backend/src/solalex/api/routes/devices.py:271-303] — Generelles Concurrency-Issue auf der DB-Schicht (PUT liest existing außerhalb seiner BEGIN-IMMEDIATE-Transaktion). Story-2.6/3.6-übergreifender Punkt; Mitigation wäre SELECT-FOR-UPDATE-Equivalent oder optimistic-locking-Token. Nicht Story-2.5-Scope.

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

claude-opus-4-7[1m] (Claude Opus 4.7, 1M-Kontext) via `/bmad-dev-story` Workflow.

### Debug Log References

- Backend: `cd backend && uv run pytest` → 398 grün (vorher 377; +21 neu durch 2.5).
- Frontend: `npm test -- --run` → 96 grün (vorher 73; +23 neu durch 2.5).
- Lint/MyPy/svelte-check/build alle grün.

### Completion Notes List

- AC 5/6/10/11 (Backend Endpoint + Whitelist): `GET /api/v1/setup/entity-state` neu in `backend/src/solalex/api/routes/setup.py`. Whitelist-Logik in den Modul-Top-Helper `_classify_entity` extrahiert, den `get_entities` und `get_entity_state` teilen. Cache-Hit: kein HA-Roundtrip; Cache-Miss: einmaliges `get_states` für Whitelist-Verifikation, dann `ensure_entity_subscriptions` + `value_w=null`. `EntityStateResponse` in `backend/src/solalex/api/schemas/setup.py`.
- AC 7 (Schema + Save-Route): `HardwareConfigRequest.invert_sign: bool = False` neu in `backend/src/solalex/api/schemas/devices.py`. `routes/devices.py::save_devices` mergt den Wert in den `grid_meter`-Eintrag von `device.config_json` (omit-when-False, damit alte Rows minimal bleiben).
- AC 8/9 (Controller-Helper): `_maybe_invert_sensor_value` in `backend/src/solalex/controller.py` ergänzt; Aufruf direkt nach `_extract_sensor_w(...)` in `on_sensor_update`. Adapter unverändert (`parse_readback`-Vertrag bleibt). Buffer + Mode-Switch + Policies sehen den invertierten Wert.
- AC 1/2/3/4/12 (Frontend Toggle + Live-Preview): Live-Preview-UI als isolierte Sub-Komponente `frontend/src/lib/components/LivePreviewCard.svelte` extrahiert (testbar in Isolation; happy-dom propagiert `change`-Events auf `<select bind:value>` nicht zurück in Svelte 5's Runen-Setter). `Config.svelte` rendert die Card und reicht `invertSign`-State über `onInvertSignChange`-Callback nach oben durch. `usePolling`-Hook (Story 5.1a) für 1-s-Polling, `onDestroy` stoppt sauber.
- AC 13: Smoke-Test SR-01 in `_bmad-output/qa/manual-tests/smoke-test.md` ergänzt; CLAUDE.md hatte den `invert_sign`-Eintrag (Regel 2) bereits vorab aufgenommen.
- Tests: `tests/unit/test_controller_invert_sign.py` (5 Cases), `tests/integration/test_setup_entity_state.py` (7 Cases), `tests/integration/test_devices_api.py` um 3 Persistenz-Cases erweitert. Frontend: `lib/components/LivePreviewCard.test.ts` (6 Cases), `lib/api/client.test.ts` um 2 `getEntityState`-Cases erweitert.
- Bewusst KEINE Vitest-Tests für die volle Config.svelte-Integration (siehe Kommentar in `routes/Config.test.ts`); stattdessen Backend-Persistenz-Test + LivePreviewCard-Isolation + Smoke SR-01 auf realer Hardware.

### File List

Backend (modified):
- `backend/src/solalex/api/routes/setup.py`
- `backend/src/solalex/api/routes/devices.py`
- `backend/src/solalex/api/schemas/setup.py`
- `backend/src/solalex/api/schemas/devices.py`
- `backend/src/solalex/controller.py`

Backend (added):
- `backend/tests/unit/test_controller_invert_sign.py`
- `backend/tests/integration/test_setup_entity_state.py`

Backend (modified — tests):
- `backend/tests/integration/test_devices_api.py`

Frontend (added):
- `frontend/src/lib/components/LivePreviewCard.svelte`
- `frontend/src/lib/components/LivePreviewCard.test.ts`

Frontend (modified):
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/routes/Config.svelte`
- `frontend/src/routes/Config.test.ts`
- `frontend/src/lib/api/client.test.ts`

Docs (modified):
- `_bmad-output/qa/manual-tests/smoke-test.md`
- `_bmad-output/implementation-artifacts/2-5-smart-meter-sign-invert-mit-live-preview.md` (Status + Tasks + Dev Record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Story 2.5 erstellt nach Smoke-Test Alex' Setup. Schließt Story-2.4-Code-Review-Defer „Generic-Meter ohne Sign-Convention-Check" auf. Beta-Launch-blocking. | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Story 2.5 implementiert: Backend `GET /api/v1/setup/entity-state` + Whitelist-Helper, `HardwareConfigRequest.invert_sign`-Feld + Persistenz in `grid_meter.config_json`, Controller `_maybe_invert_sensor_value` vor Smoothing-Buffer; Frontend `LivePreviewCard.svelte` (isoliert) + `Config.svelte`-Wiring + `getEntityState`-Client; Smoke-Test SR-01. Backend 398 pytest grün (+21), Frontend 96 vitest grün (+23). | Claude Opus 4.7 |
| 2026-04-25 | 0.3.0 | Story 2.5 → done nach Code-Review: 14 Patches (1 Decision-Skip-Cycle + 13 Patches) angewendet — stabilen `_pool_key` statt `id(pool)`, Mode.EXPORT-forward-defensiver Audit-Cycle, Whitelist-Cache + 503-bei-Subscribe-Failure + Regex-Validation am `entity-state`-Endpoint, expliziter `invert_sign: false` im POST/PUT (Toggle-Off-Fix), strict-dict-equality im `_row_diff_kind`, gridMeter-INSERT auf `id IN (?)` statt role-wide, JSONDecodeError → Skip-Cycle + once-per-device-Log, LivePreviewCard subscribe-Cleanup + Threshold-against-rounded-value, plus Drossel-/Speicher-Policy-Outcome-Tests. Backend 432 pytest grün (+34), Frontend 144 vitest grün (+48). 7 Defers in deferred-work.md. | Claude Opus 4.7 |
