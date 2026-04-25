# Story 4.0: Debug-Logging-Toggle & Hot-Path-Debug-Trace

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Alex (Support) / Beta-Tester,
I want einen Add-on-Option-Schalter, mit dem ich das Solalex-Log-Level zur Laufzeit auf `debug` ziehen kann, und genug `_logger.debug(...)`-Punkte im Regel-Hot-Path, damit ein DEBUG-Log einen Vorfall vollständig nacherzählt,
so that ich Beta-Probleme über das HA-Add-on-Log-Tab live nachvollziehen kann ohne Container-Rebuild und der Diagnose-Export aussagekräftige Traces enthält.

**Scope-Pflock:** Diese Story ist die Voraussetzung für Epic 4 Diagnose. Sie baut **keine Diagnose-Route**, **keinen Diagnose-Export**, **keine UI** und **keine SQL-Migration**. Sie macht nur das bestehende JSON-Logging konfigurierbar und ergänzt Debug-Traces in den bereits vorhandenen Hot-Path-Modulen: `addon/config.yaml`, `addon/rootfs/etc/services.d/solalex/run`, `backend/src/solalex/config.py`, `backend/src/solalex/startup.py`, `backend/src/solalex/common/logging.py`, `backend/src/solalex/controller.py`, `backend/src/solalex/executor/dispatcher.py`, `backend/src/solalex/executor/readback.py`, `backend/src/solalex/battery_pool.py`, `backend/src/solalex/ha_client/client.py`.

**Architektur-Leitplanken:** Logging bleibt stdlib-basiert über `get_logger(__name__)` und `configure_logging(...)`. Kein `structlog`, keine Correlation-ID-Infrastruktur, kein neuer Logger-Wrapper, keine neue Dependency. DEBUG muss bei Default `info` vollständig durch den Root-Level-Filter wegfallen, damit Idle-Logvolumen und Performance unverändert bleiben.

**HA-Add-on-Semantik:** Home Assistant Add-on-Optionen werden im s6-Service-Entry über `bashio::config` gelesen und als Env-Variablen an den Python-Prozess gereicht. `Settings` liest anschließend `SOLALEX_LOG_LEVEL` wegen `env_prefix="SOLALEX_"` als `log_level`. Ein Nutzer muss nach Änderung der Add-on-Option neu starten; echtes Runtime-Hot-Reload ohne Neustart ist **nicht** Scope dieser Story, auch wenn die Formulierung "zur Laufzeit auf debug ziehen" produktsprachlich gemeint ist.

## Acceptance Criteria

1. **Add-on-Option sichtbar (Epic AC 4.0.1):** `Given` `addon/config.yaml`, `When` der Nutzer die Add-on-Konfiguration in Home Assistant öffnet, `Then` existiert ein Feld `log_level` mit Optionen `debug | info | warning | error`, **And** `options.log_level` ist `info`, **And** das Feld hat eine kurze deutsche Beschreibung: `Nur fuer Support-Anfragen auf debug stellen - produziert mehr Logs.`

2. **Option wird in Env exportiert:** `Given` `addon/rootfs/etc/services.d/solalex/run`, `When` der Service startet, `Then` liest das Script `bashio::config 'log_level'` und exportiert `SOLALEX_LOG_LEVEL`, **And** wenn die Option fehlt oder leer ist, fällt es auf `info` zurück, **And** `SOLALEX_DB_PATH`, `SOLALEX_PORT` und `PYTHONPATH` bleiben unverändert.

3. **Settings validiert Log-Level:** `Given` `backend/src/solalex/config.py`, `When` `Settings()` initialisiert wird, `Then` enthält es `log_level` mit erlaubten Werten `debug | info | warning | error` und Default `info`, **And** ungültige Werte failen beim Startup sichtbar über Pydantic statt still auf `info` zurückzufallen.

4. **Logging-Konfiguration respektiert Settings:** `Given` der Nutzer setzt `log_level: debug` und startet das Add-on neu, `When` `run_startup(settings)` läuft, `Then` wird `settings.log_level` an `configure_logging(settings.log_dir, level=...)` durchgereicht, **And** DEBUG-Records erscheinen in `/data/logs/solalex.log` und auf stdout (HA Add-on-Log-Tab).

5. **`configure_logging` kann Level ändern:** `Given` `configure_logging` wurde bereits für denselben `log_dir` mit `info` aufgerufen, `When` es anschließend mit `debug` aufgerufen wird, `Then` wird mindestens der Root-Level aktualisiert und DEBUG-Records werden sichtbar, **And** es entstehen keine doppelten Handler und keine offenen Handler-Leaks. Die heutige frühe Rückkehr bei gleichem `log_dir` darf den Level-Wechsel nicht blockieren.

6. **Level-Normalisierung bleibt zentral:** `Given` `configure_logging(log_dir, level=...)`, `When` `level` als String (`"debug"`) oder int (`logging.DEBUG`) übergeben wird, `Then` wird es deterministisch auf ein stdlib-Level gemappt, **And** nur `debug | info | warning | error` sind als öffentliche String-Werte erlaubt, **And** keine Call-Site außerhalb von `common/logging.py` parst `logging`-Level selbst.

7. **Controller pro Sensor-Zyklus genau eine Debug-Zeile:** `Given` `controller.on_sensor_update(...)` verarbeitet ein Sensor-Event, `When` Log-Level `debug` aktiv ist, `Then` wird pro Event genau ein DEBUG-Record `controller_cycle_decision` geschrieben mit `extra={device_id, entity_id, role, source, mode, sensor_value_w, derived_setpoint_w, decision_count, command_kinds, pipeline_ms}`, **And** `derived_setpoint_w` ist `None` bei Noop und bei mehreren Akku-Pool-Decisions der Pool-Setpoint-Summenwert, **And** diese Debug-Zeile entsteht nach `_dispatch_by_mode(...)`, damit sie die echte Policy-Entscheidung beschreibt.

8. **Executor-Veto-Kaskade debuggt jede Stufe:** `Given` `executor.dispatcher.dispatch(...)` prüft Adapter, Range, Rate-Limit, HA-WS-Recheck und Readback, `When` Log-Level `debug` aktiv ist, `Then` jede Stufe schreibt einen DEBUG-Record mit `stage`, `decision="pass" | "block"`, `device_id`, `adapter_key`, `target_w` und stufenspezifischer Begründung, **And** bestehende INFO/WARNING/ERROR-Records bleiben semantisch unverändert.

9. **HA-Service-Call vor Send sichtbar:** `Given` ein Adapter-Modul baut einen `HaServiceCall`, `When` der Executor direkt vor `ha_client.call_service(...)` steht, `Then` schreibt der Executor einen DEBUG-Record `dispatch_service_call_built` mit `extra={device_id, command_kind, service, target_entity, payload, expected_readback}`, **And** der Log enthält keine Secrets, keine Supervisor-Tokens und keine rohen WebSocket-Frames.

10. **Readback-Vergleich debuggt auch Success:** `Given` `verify_readback(...)` vergleicht erwarteten und beobachteten Wert, `When` Log-Level `debug` aktiv ist, `Then` ein DEBUG-Record `readback_compare` enthält `extra={entity_id, expected, observed, delta, tolerance_w, within_tolerance}`, **And** er wird auch bei erfolgreichem Match geschrieben, **And** bestehende WARN/ERROR-Pfade für Timeout, unavailable und Mismatch bleiben erhalten.

11. **Akku-Pool-Verteilung debuggt Setpoint und SoC:** `Given` `BatteryPool.set_setpoint(...)` verteilt einen Setpoint und/oder `BatteryPool.get_soc(...)` liefert einen SoC-Breakdown, `When` Log-Level `debug` aktiv ist, `Then` ein DEBUG-Record beschreibt `pool_setpoint`, `online_member_count`, `per_member_setpoints` und - sobald verfügbar - `soc_breakdown`, **And** Offline-Member werden als Anzahl oder Device-ID-Liste sichtbar, ohne dass der Pool IO oder HA-Client-Zugriffe bekommt.

12. **HA-WS-Subscriptions debuggen Subscribe/Unsubscribe/Replay:** `Given` `HaWebSocketClient.subscribe(...)` oder Reconnect-Replay registriert Entities, `When` Log-Level `debug` aktiv ist, `Then` ein DEBUG-Record enthält `extra={entity_id, action, subscription_id}` soweit aus dem Payload ableitbar, **And** generische Payloads ohne Entity-ID loggen `payload_type` statt kompletten Payload, **And** keine Tokens werden geloggt. Falls kein explizites Unsubscribe im Client existiert, ist nur Subscribe/Re-Subscribe zu instrumentieren.

13. **Default `info` bleibt leise:** `Given` Log-Level `info` (Default), `When` das Add-on im Idle-Zustand läuft, `Then` das Log-Volumen pro Stunde übersteigt nicht das heutige Niveau, **And** alle neuen Hot-Path-Records sind `_logger.debug(...)` und werden komplett gefiltert, **And** keine teure Debug-Payload wird in Tight-Loops unnötig gebaut, wenn `logger.isEnabledFor(logging.DEBUG)` false ist.

14. **Diagnose-Export 4.5 kann Logs ungefiltert übernehmen:** `Given` Story 4.5 baut später den Diagnose-Export, `When` diese Story abgeschlossen ist, `Then` liegen DEBUG-Records bei aktivem Level bereits in den rotierten Dateien unter `/data/logs/`, **And** es gibt keine separate Sanitizing-/Export-Logik in 4.0.

15. **Keine funktionalen Nebenwirkungen im Regel-Hot-Path:** `Given` bestehende Controller-/Executor-/Readback-Tests aus Epic 3, `When` diese Story implementiert wird, `Then` keine Policy-Entscheidung, kein Dispatch, kein Rate-Limit, kein Readback-Timing, kein `control_cycles`-Write und kein `state_cache`-Update ändert sein Verhalten wegen Logging.

16. **Unit-Tests decken Level und Traces ab:** `Given` `pytest`, `ruff` und `mypy --strict`, `When` die Tests laufen, `Then` mindestens folgende neue/erweiterte Tests existieren: `tests/unit/test_common_logging.py`, `tests/unit/test_config.py` oder äquivalent, Erweiterungen in `test_startup.py`, `test_executor_dispatcher.py`, `test_readback.py`, `test_battery_pool.py`, `test_controller_dispatch.py`/`test_controller_speicher_policy.py` und HA-WS-Client-Tests, **And** alle bestehenden 219+ Backend-Tests bleiben grün.

## Tasks / Subtasks

- [ ] **Task 1: Add-on-Manifest um `log_level` erweitern** (AC: 1)
  - [ ] `addon/config.yaml`: `schema.log_level` als `list(debug|info|warning|error)` ergänzen.
  - [ ] `addon/config.yaml`: `options.log_level: info` setzen.
  - [ ] Beschreibung/Optionstext deutsch und kurz halten. Keine neue UI-Route, kein Frontend-Code.

- [ ] **Task 2: s6-Run-Datei exportiert `SOLALEX_LOG_LEVEL`** (AC: 2)
  - [ ] `addon/rootfs/etc/services.d/solalex/run`: per `bashio::config 'log_level'` lesen.
  - [ ] Leere oder fehlende Option auf `info` fallbacken.
  - [ ] `export SOLALEX_LOG_LEVEL="..."` vor dem `uvicorn`-Start setzen.
  - [ ] Nicht den Supervisor-Token, HA-Payloads oder sonstige Secrets loggen.

- [ ] **Task 3: Settings + Startup verdrahten** (AC: 3, 4)
  - [ ] `backend/src/solalex/config.py`: `log_level` als Literal/Enum mit Default `info` aufnehmen.
  - [ ] `backend/src/solalex/startup.py`: `configure_logging(settings.log_dir, level=settings.log_level)` verwenden.
  - [ ] Startup-Info-Log darf `log_level` nennen, aber keine Secrets.

- [ ] **Task 4: `common/logging.py` level-switch-fähig machen** (AC: 5, 6)
  - [ ] `configure_logging` akzeptiert `int | str` und normalisiert zentral.
  - [ ] Frühe Rückkehr bei gleichem `log_dir` darf nur noch Handler-Rebuild überspringen, nicht Level-Update.
  - [ ] Root-Level und installierte Handler-Level konsistent setzen.
  - [ ] `reset_logging_for_tests()` unverändert als Test-Helfer behalten.
  - [ ] Neue Datei `backend/tests/unit/test_common_logging.py` anlegen.

- [ ] **Task 5: Controller-Zyklus-Debug ergänzen** (AC: 7, 13, 15)
  - [ ] `backend/src/solalex/controller.py`: nach `_dispatch_by_mode(...)` genau einen `controller_cycle_decision`-Debug-Record pro Event schreiben.
  - [ ] Für Drossel: `derived_setpoint_w` = Zielwert der einen Decision.
  - [ ] Für Speicher: `derived_setpoint_w` = Summe aller Decision-Zielwerte.
  - [ ] Für Noop: `derived_setpoint_w=None`, `decision_count=0`.
  - [ ] Nur Debug-Payload bauen, wenn DEBUG aktiv ist.

- [ ] **Task 6: Executor-Dispatch-Stufen debuggen** (AC: 8, 9, 13, 15)
  - [ ] `backend/src/solalex/executor/dispatcher.py`: DEBUG für unknown adapter, range pass/block, rate-limit pass/block, service-call-built, HA-WS-Recheck und dispatch completion.
  - [ ] Bestehende WARNING/INFO-Records nicht löschen oder zu DEBUG degradieren.
  - [ ] `dispatch_service_call_built` direkt vor `call_service(...)` schreiben.
  - [ ] Payload begrenzen auf `domain`, `service`, `service_data` und erwarteten Readback-Wert; keine Tokens/Frames.

- [ ] **Task 7: Readback-Vergleich debuggen** (AC: 10, 13, 15)
  - [ ] `backend/src/solalex/executor/readback.py`: `readback_compare` bei numeric compare schreiben.
  - [ ] `extra` enthält `expected`, `observed`, `delta`, `tolerance_w`, `within_tolerance`.
  - [ ] Timeout-/Unavailable-/Non-Numeric-Pfade behalten ihre heutigen WARN/Failure-Semantiken.

- [ ] **Task 8: Akku-Pool-Debug ergänzen** (AC: 11, 13, 15)
  - [ ] `backend/src/solalex/battery_pool.py`: bei `set_setpoint(...)` Debug mit `pool_setpoint`, `online_member_count`, `per_member_setpoints`.
  - [ ] Bei `get_soc(...)` Debug mit `aggregated_pct` und `per_member`, wenn ein Breakdown entsteht.
  - [ ] Keine Abhängigkeit von `controller.py` hinzufügen; Pool bleibt synchron und IO-frei.

- [ ] **Task 9: HA-WS-Client-Subscription-Debug ergänzen** (AC: 12, 13, 15)
  - [ ] `backend/src/solalex/ha_client/client.py`: `subscribe(...)` debuggt `action="subscribe"`, `subscription_id`, ableitbare `entity_id`.
  - [ ] Reconnect-Replay prüfen: falls Re-Subscribe in `ha_client/reconnect.py` passiert, dort ebenfalls `action="resubscribe"` debuggen.
  - [ ] Keine vollständigen Payloads loggen, wenn sie unnötig groß oder potenziell sensibel sind.

- [ ] **Task 10: Tests für Logging-Behavior ergänzen** (AC: 5, 6, 13, 16)
  - [ ] `test_common_logging.py`: DEBUG erscheint bei `level="debug"` und verschwindet bei `level="info"`.
  - [ ] `test_common_logging.py`: Reconfigure gleicher `log_dir` von `info` auf `debug` funktioniert ohne Handler-Duplikate.
  - [ ] `test_common_logging.py`: ungültiger String-Level wirft `ValueError` oder Pydantic-validiert upstream fail-loud.
  - [ ] `test_config.py` oder `test_startup.py`: `SOLALEX_LOG_LEVEL=debug` landet in `Settings.log_level`.

- [ ] **Task 11: Hot-Path-Trace-Tests erweitern** (AC: 7-12, 15, 16)
  - [ ] Controller-Test mit `caplog.at_level(logging.DEBUG)`: genau ein `controller_cycle_decision` pro Event.
  - [ ] Dispatcher-Test: Range-Veto und Rate-Limit-Veto erzeugen Debug-Pass/Block-Records, ohne Service-Call.
  - [ ] Dispatcher-Happy-Path-Test: `dispatch_service_call_built` enthält Service und Ziel-Entity.
  - [ ] Readback-Test: Successful compare erzeugt `readback_compare`.
  - [ ] BatteryPool-Test: `set_setpoint` und `get_soc` erzeugen Debug-Records bei DEBUG.
  - [ ] HA-WS-Test: `subscribe` erzeugt Debug-Record ohne Token/Payload-Dump.

- [ ] **Task 12: CI-Gates lokal ausführen** (AC: 16)
  - [ ] Backend: `ruff check`.
  - [ ] Backend: `mypy --strict`.
  - [ ] Backend: `pytest`.
  - [ ] SQL-Migrations-Ordering-Check bleibt unverändert; diese Story legt keine Migration an.

## Dev Notes

### Bestehende Implementierung, auf der aufgebaut wird

- `backend/src/solalex/common/logging.py` hat bereits `JSONFormatter`, `RotatingFileHandler` mit 10 MB / 5 Dateien, stdout-StreamHandler und `get_logger(__name__)`. Nicht ersetzen, sondern erweitern.
- `configure_logging(log_dir, level=logging.INFO)` hat aktuell eine frühe No-op-Rückkehr, wenn derselbe `log_dir` bereits installiert ist. Für Level-Wechsel in Tests muss diese Stelle angepasst werden.
- `backend/src/solalex/config.py` nutzt `pydantic-settings` mit `env_prefix="SOLALEX_"`; `log_level` kann direkt als `SOLALEX_LOG_LEVEL` aus dem Add-on-Run-Script kommen.
- `backend/src/solalex/startup.py::run_startup` ruft aktuell `configure_logging(settings.log_dir)` ohne Level auf.
- `addon/config.yaml` hat aktuell `schema: {}` und `options: {}`; das ist der zentrale Add-on-Manifest-Ort für die neue Option.
- `addon/rootfs/etc/services.d/solalex/run` exportiert bereits `SOLALEX_DB_PATH`, `SOLALEX_PORT` und `PYTHONPATH`; hier wird `SOLALEX_LOG_LEVEL` ergänzt.
- `controller.py` hat die relevante Stelle direkt nach `source = ...`, `sensor_value = ...`, `decisions = self._dispatch_by_mode(...)`. Dort ist der beste Ort für genau eine Zyklus-Debug-Zeile.
- `dispatcher.py` ist die Safety-Kaskade Range → Rate-Limit → Service-Call → Readback. Debug-Records gehören an die Gate-Entscheidungen, nicht in Adapter-Module.
- `readback.py` hat die numeric-compare-Stelle bei `diff = abs(actual_w - expected_value_w)`; dort gehört `readback_compare` hin.
- `battery_pool.py` ist synchron und IO-frei; Debug darf keine HA-/DB-Aufrufe verursachen.
- `ha_client/client.py` hat `subscribe(...)`, aber kein explizites Unsubscribe. Nur vorhandene Subscriptions debuggen.

### Anti-Patterns, die diese Story verhindern muss

- Kein `print()`, kein direktes `logging.getLogger()` in neuen Call-Sites, kein `logging.basicConfig`.
- Kein `structlog`, keine neue Logging-Dependency, keine OpenTelemetry-/Correlation-ID-Infrastruktur.
- Keine Secrets in Logs: kein `SUPERVISOR_TOKEN`, kein Access Token, keine kompletten HA-WebSocket-Frames.
- Keine Diagnose-Export-Implementierung in 4.0. Story 4.5 liest später nur die rotierten Log-Dateien.
- Keine UI-/Frontend-Arbeit. Die Option lebt in HA Add-on-Konfiguration, nicht in Solalex-Svelte.
- Keine neue SQL-Migration und keine Änderung an `control_cycles`/`latency_measurements`.
- Keine funktionalen Änderungen an Policy, Rate-Limit, Readback oder Akku-Pool-Verteilung.

### Test- und Entwicklungs-Hinweise

- Für Log-Assertions `caplog` oder temporäre `log_dir` nutzen und nach Tests `reset_logging_for_tests()` aufrufen, damit Handler nicht zwischen Tests leaken.
- Für Tests, die gleiche `tmp_path / "logs"` mehrfach konfigurieren, explizit prüfen, dass `len(logging.getLogger().handlers) == 2` bleibt.
- Wenn Debug-Payloads Listen/Dicts enthalten, müssen sie JSON-serialisierbar sein; `JSONFormatter` repräsentiert nicht serialisierbare Werte zwar defensiv, aber Tests sollten einfache Strukturen erwarten.
- Hot-Path-Debug sollte mit `if _logger.isEnabledFor(logging.DEBUG):` geschützt werden, sobald die Payload mehr als ein paar primitive Felder zusammensetzt.

### Project Structure Notes

- Backend bleibt eigenständiges uv-Projekt unter `backend/`; keine Root-`pyproject.toml`.
- Python-Kommentare auf Englisch, UI-/User-facing Texte Deutsch.
- snake_case überall in Python, JSON, Env-nahen Namen und Add-on-Options.
- Logging-Regel aus `CLAUDE.md`: immer `get_logger(__name__)` aus `common/logging.py`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.0: Debug-Logging-Toggle & Hot-Path-Debug-Trace]
- [Source: _bmad-output/planning-artifacts/epics.md#Diagnose & Support]
- [Source: _bmad-output/planning-artifacts/architecture.md#Logging]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- [Source: _bmad-output/planning-artifacts/prd.md#Diagnose]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Diagnose-Tab fuer Nerds]
- [Source: CLAUDE.md#5 harte Regeln]

## Previous Story Intelligence

Story 4.0 ist die erste Story in Epic 4, daher gibt es keine vorherige Epic-4-Story. Relevante Learnings stammen aus Epic 3:

- Story 3.1-3.4 haben den Regel-Hot-Path etabliert: `main._dispatch_event` → `StateCache.update` → `Controller.on_sensor_update` → Policy → `executor.dispatcher.dispatch` → `verify_readback` → `control_cycles`/`latency`.
- Tests nutzen `FakeHaClient`, `make_db_factory`, `seeded_device` aus `backend/tests/unit/_controller_helpers.py`; diese Helfer wiederverwenden statt neue Fakes zu erfinden.
- Story 3.4 hat den Akku-Pool in den Controller eingefädelt und viele Hot-Path-Tests ergänzt. Logging darf diese Tests nicht durch zusätzliche Await-Punkte, IO oder geänderte Dispatch-Reihenfolge destabilisieren.
- Bestehende Review-Learnings aus 3.2/3.4: Fail-loud bei falscher Konfiguration, aber keine defensive Doppelvalidierung im Policy-Hot-Path; für diese Story heißt das: `Settings.log_level` validiert früh, der Hot-Path vertraut auf konfigurierte Logger.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

