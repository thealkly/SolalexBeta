# Story: Status-Sensor-Layer via HA Input-Helpers

**Erstellt:** 2026-04-26 · **Status:** Draft · **Beta-Launch-Blocking:** Nein (QA-Smoketest-Blocking: Ja)

> Dies ist eine **Skizze** als Vorlage für `bmad-create-story` oder direkte Implementierung. Architektur-Begründung im [Architecture Amendment 2026-04-26](architecture.md#2026-04-26-—-status-sensor-layer-via-ha-input-helpers).

## User-Story

Als **Solalex-QA-Agent** (und als Power-User mit eigenem HA-Dashboard) will ich den **internen Zustand von Solalex via HA-Entities lesen können**, damit ich **Add-on-Health, Mode, Last-Activity, Fail-Safe-State und Lizenz-Status ohne Zugriff auf die Solalex-REST-API** prüfen kann.

## Acceptance-Criteria

1. **6 Helper werden vom Wizard angelegt** (Step 4 Commission) — idempotent (existierende werden übersprungen, kein Fehler):
   - `input_text.solalex_active_mode`
   - `input_text.solalex_last_command_at`
   - `input_text.solalex_last_readback_status`
   - `input_number.solalex_recent_cycles_count`
   - `input_text.solalex_fail_safe_state`
   - `input_number.solalex_license_days_remaining`
2. **Solalex aktualisiert die Helper** nach jedem Controller-Cycle:
   - On-change-Events sofort (Mode-Wechsel, Fail-Safe-Übergang, Readback-Mismatch)
   - Sonst max. 1 Update/Helper/30 s (Throttle)
3. **Aufruf ist non-blocking:** `asyncio.create_task` aus dem Controller, niemals `await` im Hot-Path. Latenz-Budget des 1-s-Cycles wird **nicht** durch HA-WS-Latenz erhöht.
4. **Failure-Toleranz:** WS-API-Errors (HA-down, Helper gelöscht) werden via `logger.warning` geloggt und geswallowt. Controller läuft weiter.
5. **`solalex_active_mode`** liefert einen der Werte: `drossel`, `speicher`, `multi`, `export`, `idle`.
6. **`solalex_last_command_at`** ist ISO8601 UTC (z.B. `2026-04-26T08:42:13Z`).
7. **`solalex_last_readback_status`** ∈ {`ok`, `mismatch`, `timeout`}.
8. **`solalex_recent_cycles_count`** ist die Anzahl von `control_cycles`-Einträgen mit `ts > now() - 1h` (Rolling-Window).
9. **`solalex_fail_safe_state`** ∈ {`inactive`, `active_hold`, `active_release`}.
10. **`solalex_license_days_remaining`** ist die Restdauer der LemonSqueezy-Grace in vollen Tagen (kann negativ sein, wenn abgelaufen).
11. **CI-Tests:**
    - Unit-Test für Throttle-Logik (nicht > 1×/30 s, on-change-Override funktioniert)
    - Unit-Test für Failure-Swallowing (Mock-HA-Client wirft, Controller läuft weiter)
    - Integration-Test gegen Mock-HA-Client für Helper-Anlage-Idempotenz

## Out-of-Scope (für diese Story)

- MQTT-Discovery-Variante
- Auto-Helper-Heilung bei manuellem Helper-Löschen durch User
- Custom-Component-Variante (`sensor.solalex_*`-Domain)
- Frontend-Diagnose-Page mit Helper-Werten
- User-Migration: bestehende Add-on-Installationen ohne Helpers (Wizard muss neu durchlaufen werden — als bekannter Limit dokumentieren)

## Technische Aufgaben

### Backend

1. **Neues Modul `backend/src/solalex/status_publisher.py`:**
   - `class StatusSnapshot(NamedTuple)` mit den 6 Feldern
   - `async def publish_status(snapshot: StatusSnapshot, ha_client: HaClient) -> None`
   - Throttle-State: `_last_published_at: dict[str, float]` (Helper-Name → Unix-Timestamp)
   - Fire-and-forget-Wrapper im Controller via `asyncio.create_task`
2. **Erweiterung `backend/src/solalex/ha_client/client.py`:**
   - Neue Methode `async def call_service(self, domain: str, service: str, data: dict) -> None` falls noch nicht vorhanden
   - Reuse vorhandene WS-Connection
3. **Hook in `backend/src/solalex/controller.py`:**
   - Nach `_record_cycle()` → `asyncio.create_task(status_publisher.publish_status(snapshot, self.ha_client))`
   - Snapshot-Build aus aktuellem Controller-State (ein paar getter-Calls)
4. **Neue Setup-Route `backend/src/solalex/api/routes/setup.py`:**
   - `POST /api/v1/setup/create_status_helpers`
   - Body: leer
   - Response: `{"created": [...], "existing": [...]}`
   - Idempotent: prüft existierende Helper via `input_text.list_input_text` / `input_number.list_input_number`, ruft `*.create_*` nur für fehlende
5. **License-Day-Calculation:**
   - Reuse vorhandene `license/grace.py`-Logik
   - Falls noch nicht vorhanden: Funktion `days_remaining_until_expiry(license_state) -> int`

### Frontend

6. **Wizard `Step4Activation.svelte`:**
   - Im Commission-Submit-Handler: zusätzlich `POST /api/v1/setup/create_status_helpers`
   - Bei Fehler: nicht-blockierend (Toast/Inline-Hinweis: "Status-Helper konnten nicht angelegt werden, Solalex funktioniert trotzdem"), Commission läuft weiter
   - Reihenfolge: erst Helper anlegen, dann Commission — falls Commission fehlschlägt, sind die Helper schon da (kein Cleanup nötig, wird beim nächsten Re-Run wiederverwendet)

### Tests

7. **`backend/tests/unit/test_status_publisher.py`:**
   - `test_throttle_blocks_within_30s_window`
   - `test_throttle_allows_on_change_override`
   - `test_publish_swallows_ha_client_error`
   - `test_snapshot_building_from_controller_state`
8. **`backend/tests/unit/test_setup_create_status_helpers.py`:**
   - `test_creates_all_helpers_when_none_exist`
   - `test_skips_existing_helpers`
   - `test_returns_partial_failure_gracefully`
9. **`backend/tests/unit/test_controller_status_hook.py`:**
   - `test_controller_creates_publish_task_after_cycle`
   - `test_controller_does_not_await_publish` (latency-test)

### Doku

10. **CLAUDE.md:**
    - Stolperstein-Liste erweitern (siehe Architektur-Amendment, „Stolpersteine für AI-Agents")
    - „Was verwendet wird"-Liste ergänzen mit „Status-Sensoren via input_*-Helpers"
    - „Was explizit NICHT verwendet wird"-Liste ergänzen mit „Kein MQTT-Discovery, keine Custom-Component, keine HA-Notifications für Status"
11. **`addon/DOCS.md`:**
    - Neuer Abschnitt „Solalex Status in Home Assistant" mit Liste der 6 Helper, Erklärung der Werte, Hinweis dass Wizard sie anlegt
12. **`qa/agent-smoketest/AGENT.md`:**
    - Check 5 update auf 6 erwartete Helper mit Plausibilitätsprüfungen
    - Check 5 zum Critical-Check hochziehen

### DB-Migration

Keine. Helper sind reine HA-State, keine Solalex-DB-Schema-Änderung.

## Abhängigkeiten

- `ha_client.call_service()` muss WS-API-tauglich sein (vermutlich schon vorhanden für Hardware-Service-Calls — prüfen, sonst additiv erstellen)
- Wizard Step 4 muss bereits implementiert sein (sollte `done` sein)
- LemonSqueezy-License-Modul muss `days_remaining`-Funktion exposen (sonst Story-Vorbedingung)

## Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| HA-WS-Service-Call latenz spikes blockieren Controller-Cycle | Niedrig | Hoch | `asyncio.create_task` (fire-and-forget), CI-Test für Latenz-Garantie |
| Helper-Anlage scheitert auf älteren HA-Versionen ohne `input_*.create_*`-Service | Niedrig | Mittel | HA ≥ 2026.04 ist Min-Version (siehe addon/config.yaml) — Service existiert seit 2023.09 |
| User löscht Helper manuell → permanente Warnings im Log | Mittel | Niedrig | v1: Warnings, dokumentiert. v1.5: Auto-Heilung |
| Throttle-State geht bei Add-on-Restart verloren → kurzzeitig zu viele Updates | Niedrig | Niedrig | Akzeptabel, Throttle ist soft, kein Hardware-Schutz |
| Mode-Enum erweitert sich (z.B. zukünftig `Mode.NIGHT`) → `solalex_active_mode` ist veralteter String | Mittel | Niedrig | Helper-Update mit dem neuen Mode-String — kein Helper-Schema-Cleanup nötig |

## Definition of Done

- [ ] Alle 6 Helper werden vom Wizard angelegt und nach Cycles aktualisiert
- [ ] Smoketest Check 5 wechselt von `skipped` zu `pass` mit valider Plausibilitätsprüfung
- [ ] Controller-Latenz-Test zeigt: 99p Cycle-Zeit verändert sich um < 1 ms durch Hook
- [ ] Failure-Modes (HA-down, Helper-gelöscht) führen nicht zu Controller-Crash
- [ ] CLAUDE.md, addon/DOCS.md, qa/agent-smoketest/AGENT.md sind synchron
- [ ] PR-Reviewer findet keine NFR27-Verletzung („Pull nicht Push")
