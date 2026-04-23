# Story 3.1: Core Controller (Mono-Modul, Sensor → Policy → Executor) + Event-Source + Readback + persistenter Rate-Limit

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Solalex-Backend,
I want einen hardware-agnostischen Controller (`controller.py` Mono-Modul) mit Enum-Dispatch über `Mode.DROSSEL | SPEICHER | MULTI`, der Sensor-Events zu Steuerbefehlen verarbeitet, Source-Attribution schreibt, Readback prüft und EEPROM-Rate-Limits persistent durchsetzt,
so that alle Modi und Adapter-Module denselben Safety-Layer und dieselbe Event-Basis nutzen.

**Amendment 2026-04-22 (verbindlich):** Controller als **Mono-Modul** statt 6-fach-Split. Interner Control-Flow = **direkte Funktionsaufrufe** (`controller.on_sensor_update` → `executor.dispatch` → `state_cache.update` + `kpi.record`). Kein Event-Bus, kein `asyncio.Queue`. Rate-Limiter persistiert letzten Write-Timestamp in `devices.last_write_at` — nach Restart wartet der Executor mindestens `last_write_at + min_interval_s` pro Device.

## Acceptance Criteria

1. **Pipeline-Kette & Latenz-Budget (FR31/NFR2-Vorarbeit):** `Given` ein HA-Sensor-Event kommt über die bestehende WS-Subscription, `When` `controller.on_sensor_update(event)` es verarbeitet, `Then` läuft die Pipeline `Sensor → Mode-Dispatch (Enum) → Policy → Executor → Readback → control_cycles.insert → state_cache.update + kpi.record` als **direkte Funktionsaufrufe** innerhalb eines async-Contexts **And** die Gesamtdauer ≤ 1 s (gemessen über `time.monotonic`, geloggt als `cycle_duration_ms` in jedem `control_cycles`-Row).
2. **Enum-Dispatch (ein Modul, kein Split):** `Given` `controller.py` als **Mono-Modul**, `When` der Dispatch einen Mode wählt, `Then` existiert **genau eine** `Mode`-Enum mit `DROSSEL | SPEICHER | MULTI` **And** der Dispatch ist ein `match mode:`-Block in `controller.py` (kein `drossel.py` / `speicher.py` / `multi.py`-Split) **And** jede Mode-Branch ruft eine mode-spezifische Policy-Funktion auf (Stub für 3.2/3.3/3.4 ausreichend — liefert `PolicyDecision | None` mit `decision=None` = „nichts tun").
3. **Veto-Kaskade im Executor (Safety-Pflicht, CLAUDE.md Regel 3):** `Given` ein `PolicyDecision` (Target-Watts + Device + erwarteter Readback), `When` `executor.dispatcher.dispatch(decision)` ihn verarbeitet, `Then` prüft der Executor in genau dieser Reihenfolge: **(a) Range-Check** (Watts innerhalb Hardware-Spanne aus Adapter), **(b) Rate-Limit** (`now - device.last_write_at >= adapter.get_rate_limit_policy().min_interval_s`), **(c) Readback-Erwartung vorhanden** (nicht-leer) **And** schlägt eine Stufe fehl, wird der Befehl unterdrückt, ein `control_cycles`-Row mit `status='vetoed'` + Grund geschrieben, **kein** `ha_client.call_service` ausgelöst.
4. **Persistenter Rate-Limiter (FR19, CLAUDE.md Regel 3, Architecture Zeile 434):** `Given` ein erfolgreicher Write, `When` er gesendet wurde, `Then` wird **im selben DB-Commit wie der `control_cycles`-Row** auch `devices.last_write_at` auf den Command-Timestamp gesetzt **And** nach **Add-on-Restart** liest der Executor beim ersten Write pro Device den persistierten `last_write_at` aus der DB **And** unterdrückt den Write, wenn `now - last_write_at < min_interval_s` (Default 60 s) **And** ein Unit-Test simuliert Restart (neuer Executor-Instance, alte DB-Row) und verifiziert Unterdrückung.
5. **Source-Attribution (FR27):** `Given` ein Steuerbefehl oder ein beobachtetes Sensor-Event, `When` der Zyklus geschrieben wird, `Then` wird ein `source`-Feld mit einem von `'solalex' | 'manual' | 'ha_automation'` gesetzt. Herleitung:
   - **`solalex`**: Der Schreibbefehl wurde vom eigenen Executor dispatched (Executor schreibt `source='solalex'` direkt in den `control_cycles`-Row).
   - **`manual`**: Ein State-Change an einem Device-Entity, dessen HA-`context.user_id` **nicht `None`** ist und dessen `context.parent_id` `None` ist — bedeutet, ein HA-User hat die Entity von Hand geändert.
   - **`ha_automation`**: Ein State-Change an einem Device-Entity mit `context.parent_id != None` ODER `context.user_id == None` bei non-Solalex-Origin (erkannt daran, dass innerhalb der letzten 2 Sekunden **kein** Solalex-Write auf dieser Entity lief).
   Die Implementierung der Erkennung lebt in `controller.on_sensor_update` und liest `event["event"]["data"]["new_state"]["context"]` (HA-Wire-Format).
6. **Readback-Verifikation nach Write (CLAUDE.md Regel 3):** `Given` ein erfolgreich abgesetzter Steuerbefehl, `When` er durch den Executor ging, `Then` wird `executor.readback.verify_readback(...)` mit dem adapter-spezifischen Timeout aus `adapter.get_readback_timing()` gerufen **And** das Ergebnis (`status`, `actual_value_w`, `latency_ms`, `reason`) wird in den `control_cycles`-Row übernommen (Spalten `readback_status`, `readback_actual_w`, `readback_mismatch`). Mismatch bei `status='failed'` oder `status='timeout'`.
7. **`control_cycles`-Tabelle + Ringpuffer-Retention (FR31):** `Given` die erste Migration nach `001_initial.sql`, `When` Migrate läuft, `Then` existiert `control_cycles` mit Spalten: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `ts TIMESTAMP NOT NULL`, `device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE`, `mode TEXT NOT NULL CHECK (mode IN ('drossel','speicher','multi','idle'))`, `source TEXT NOT NULL CHECK (source IN ('solalex','manual','ha_automation'))`, `sensor_value_w REAL`, `target_value_w INTEGER`, `readback_status TEXT CHECK (readback_status IN ('passed','failed','timeout','vetoed','noop'))`, `readback_actual_w REAL`, `readback_mismatch INTEGER NOT NULL DEFAULT 0`, `latency_ms INTEGER`, `cycle_duration_ms INTEGER NOT NULL`, `reason TEXT` **And** ein Index auf `ts DESC` **And** ein Index auf `device_id` **And** ein Repository `persistence/repositories/control_cycles.py` mit `insert(conn, row) -> int` und `list_recent(conn, limit=100) -> list[ControlCycleRow]`.
8. **`latency_measurements`-Tabelle & Erfassung (FR34):** `Given` ein erfolgreicher Schreibbefehl, `When` Readback `status='passed'`, `Then` wird zusätzlich ein Row in `latency_measurements` (Spalten: `id`, `device_id`, `command_at TIMESTAMP`, `effect_at TIMESTAMP`, `latency_ms INTEGER`, `mode TEXT`) geschrieben via `persistence/repositories/latency.py` **And** eine 30-Tage-Retention wird **nicht** in dieser Story implementiert (kommt in Story 4.4) — DB-Schema und Insert reichen.
9. **Fail-Safe-Wrapper bei Kommunikations-Ausfall (FR18, NFR11):** `Given` ein Write-Versuch, `When` `ha_client.call_service(...)` eine Exception wirft (Timeout, ConnectionClosed, RuntimeError) ODER `ha_client.ha_ws_connected == False`, `Then` greift der Fail-Safe-Wrapper in `controller.py`: **(a)** ein `control_cycles`-Row mit `mode=<current>`, `source='solalex'`, `readback_status='vetoed'`, `reason='fail_safe: ha_ws_disconnected'` (bzw. Exception-Message) wird geschrieben, **(b)** **keine** `devices.last_write_at`-Aktualisierung, **(c)** Exception wird **nicht** propagiert (Loop bleibt grün) **And** ein Log-Eintrag `fail_safe_triggered` via `get_logger(__name__).exception(...)` entsteht.
10. **SetpointProvider-Interface (v2-Naht, Architecture Zeile 254/979):** `Given` das v2-Forecast-Feature, `When` `controller.py` den Soll-Bezugspreis oder externe Setpoints braucht, `Then` existiert eine Klasse `SetpointProvider` **direkt in `controller.py`** mit Docstring „v2-Forecast-Naht" + einer `get_current_setpoint(mode: Mode) -> int | None`-Methode **And** eine Default-Noop-Implementation (`class _NoopSetpointProvider`) liefert `None` zurück („current reactive behavior") **And** der Controller-Konstruktor akzeptiert einen optionalen `setpoint_provider`-Parameter, defaulted auf `_NoopSetpointProvider()`. **Kein separates Modul** (`setpoints/`-Folder), **kein Plugin-Loader**.
11. **Direkter Aufruf, kein Event-Bus (Architecture Zeile 241/562/823, CLAUDE.md „Stolpersteine"):** `Given` der Controller einen Zyklus abgeschlossen hat, `When` KPI und State-Cache aufgerufen werden, `Then` sind beide Aufrufe **direkte `await`-Calls** im selben async-Context: `await kpi.record(cycle)` + `await state_cache.update(...)` (oder synchron, falls keine IO) — **keine `asyncio.Queue`**, **kein `events/bus.py`**, **kein Pub/Sub-Dispatch**. `kpi.record` darf als **Noop-Stub** implementiert sein (`kpi/__init__.py` + `async def record(cycle): return`) — die eigentliche KPI-Logik kommt in Epic 5. Der Noop-Stub muss aber existieren, damit `controller.py` ihn aufrufen kann, ohne dass 3.1 auf Epic 5 wartet.
12. **HA-Subscription für Devices (Event-Quelle):** `Given` der Controller beim App-Lifespan-Start, `When` er initialisiert wird, `Then` ruft er für **jedes kommissionierte Device** (alle `devices`-Zeilen mit `commissioned_at IS NOT NULL`) die bestehende `solalex.setup.test_session.ensure_entity_subscriptions(...)`-Funktion (oder ein Äquivalent, falls die bestehende nur für Test-Sessions gedacht ist) auf, damit Sensor-Events auf diesen Entities via `_dispatch_event` in `main.py` landen **And** `_dispatch_event` in `main.py` wird erweitert: nach dem bestehenden `state_cache.update(...)` wird **zusätzlich** `controller.on_sensor_update(event_msg, device_record)` aufgerufen, wenn die Entity in `app.state.entity_role_map` liegt. **Commissioning-Gate**: Controller pickt **nur commissioned Devices** — nicht-commissioned Devices (Funktionstest-Phase) bleiben aus dem Control-Loop raus, damit Story 2.2's Funktionstest nicht in den Regler-Zyklus fällt.
13. **Regression (Story 2.2 Funktionstest):** `Given` der Funktionstest aus Story 2.2 ist nur für nicht-commissioned Devices aktiv (der Config-Page-Flow), `When` Story 3.1 den Controller-Subscriber hinzufügt, `Then` bleibt `POST /api/v1/setup/test` unverändert funktional **And** `state_cache.mark_test_started()` / `mark_test_ended()` fungieren als **Exklusiv-Lock**: während `test_in_progress == True` unterdrückt der Controller den Dispatch (der Executor darf nicht schreiben, solange der Funktionstest läuft) **And** bestehende Tests für `POST /api/v1/setup/test` bleiben grün.
14. **Unit-Tests (Pytest, MyPy strict, Ruff):** Neue Test-Dateien unter `backend/tests/unit/`:
    - `test_controller_dispatch.py`: Enum-Dispatch, Pipeline-Reihenfolge via Spy/Fake-Executor, Fail-Safe-Pfad (ha_ws_connected=False → vetoed row + keine Exception).
    - `test_executor_dispatcher.py`: Veto-Kaskade Range-Check, Rate-Limit-Block, Happy-Path. Verwendet Fake-`HaWebSocketClient` + in-memory `aiosqlite:memory:`-DB.
    - `test_executor_rate_limiter.py`: Persistenz über Restart (zwei Executor-Instanzen, gemeinsame DB), `now - last_write_at < min_interval` → blockiert.
    - `test_source_attribution.py`: `context.user_id` gesetzt → `manual`, `context.parent_id` gesetzt → `ha_automation`, eigener-Write → `solalex`.
    - `test_control_cycles_repo.py`: Insert + `list_recent(limit=100)` + FK ON DELETE CASCADE.
    - `test_setpoint_provider.py`: Noop liefert `None`, Custom Provider wird im Konstruktor übernommen.
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf `controller.py`, `executor/dispatcher.py`, `executor/rate_limiter.py`, `persistence/repositories/control_cycles.py`, `persistence/repositories/latency.py`.
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (nummerisch lückenlos).

## Tasks / Subtasks

- [ ] **Task 1: SQL-Migration 002 (control_cycles + latency_measurements)** (AC: 7, 8)
  - [ ] Neue Datei `backend/src/solalex/persistence/sql/002_control_cycles_latency.sql`.
    - Tabellen `control_cycles` + `latency_measurements` mit exakt den Spalten aus AC 7 / AC 8.
    - Indexes: `CREATE INDEX idx_control_cycles_ts ON control_cycles(ts DESC)`, `CREATE INDEX idx_control_cycles_device ON control_cycles(device_id)`.
    - `CHECK`-Constraints für Enum-Spalten (SQLite erlaubt Check-Constraints — syntaktisch inline in `CREATE TABLE`).
    - Forward-only: keine `ALTER TABLE`, nur `CREATE TABLE IF NOT EXISTS`.
  - [ ] Smoke-Test: lokales `pytest -k migrate` verifiziert, dass `run(db_path)` die neue Migration problemlos auf einer DB anwendet, die bereits auf `001` steht.

- [ ] **Task 2: `persistence/repositories/control_cycles.py`** (AC: 3, 6, 7, 9)
  - [ ] Datenklasse `ControlCycleRow` (dataclass, snake_case-Felder exakt wie die Tabelle).
  - [ ] `async def insert(conn: aiosqlite.Connection, row: ControlCycleRow) -> int`.
  - [ ] `async def list_recent(conn: aiosqlite.Connection, limit: int = 100) -> list[ControlCycleRow]` → `ORDER BY id DESC LIMIT ?`.
  - [ ] `async def list_by_device(conn, device_id, limit=100) -> list[ControlCycleRow]` (Dashboard-/Diagnose-Support für Epic 4/5).
  - [ ] Kein ORM, nur raw `aiosqlite` mit handgeschriebenem SQL (CLAUDE.md Regel 1 + „Kein SQLAlchemy").

- [ ] **Task 3: `persistence/repositories/latency.py`** (AC: 8)
  - [ ] Datenklasse `LatencyMeasurementRow`.
  - [ ] `async def insert(conn, row) -> int`.
  - [ ] `async def list_for_device(conn, device_id, since_ts) -> list[...]` (für Epic 4.4 vorbereitet, keine 30-Tage-Retention in 3.1).

- [ ] **Task 4: `executor/rate_limiter.py`** (AC: 4)
  - [ ] Funktion `async def check_and_reserve(conn, device_id, min_interval_s, now) -> tuple[bool, datetime | None]` — `True` wenn erlaubt, sonst `False` + `last_write_at`.
  - [ ] Funktion `async def mark_write(conn, device_id, ts)` — UPDATE `devices SET last_write_at=?`.
  - [ ] Reine SQL-Logik, liest/schreibt **nur** `devices.last_write_at`.
  - [ ] **Nicht** `datetime.now()` intern benutzen — immer Parameter `now` akzeptieren (Testbarkeit).

- [ ] **Task 5: `executor/dispatcher.py`** (AC: 3, 6, 9)
  - [ ] Datenklasse `PolicyDecision`: `device: DeviceRecord`, `target_value_w: int`, `mode: Mode`, `command_kind: Literal["set_limit","set_charge"]`.
  - [ ] Datenklasse `DispatchResult` (Status + geschriebener `ControlCycleRow`).
  - [ ] Funktion `async def dispatch(decision, ctx: DispatchContext) -> DispatchResult`:
    1. Range-Check via Adapter-Hardware-Spanne (siehe Task 6 für die Spanne-API).
    2. Rate-Limit via `rate_limiter.check_and_reserve`.
    3. Build Command via `adapter.build_set_limit_command` oder `build_set_charge_command`.
    4. `ha_client.call_service(...)` im `try` — bei Exception: Fail-Safe (AC 9).
    5. `rate_limiter.mark_write(...)` + `readback.verify_readback(...)` im selben DB-Commit-Transaction.
    6. `control_cycles.insert(...)` mit vollständigem Row.
    7. Optional `latency.insert(...)` bei readback=passed.
  - [ ] `DispatchContext` bündelt `ha_client`, `state_cache`, `db_conn_factory` (async context manager), `adapter_registry` (Dict), `now_fn: Callable[[], datetime]`.

- [ ] **Task 6: Adapter-Hardware-Spanne** (AC: 3)
  - [ ] `AdapterBase` in `adapters/base.py` um Methode `get_limit_range(device) -> tuple[int, int]` erweitern (Default: `(0, 10_000)` für W — Subclasses überschreiben).
  - [ ] Hoymiles: `(2, 1500)` W (Hardware-Spec-Minimum 2 W laut OpenDTU, Max 1500 W = typischer HM-1500).
  - [ ] Marstek Venus: `(0, 2500)` W (Charge-Range für Venus 3E — siehe Datasheet).
  - [ ] Shelly 3EM: `NotImplementedError` (Smart-Meter schreibt nicht).
  - [ ] Falls unsicher, Default-Spanne und `# TODO(3.2/3.4): eng fassen`-Kommentar setzen — später verfeinert in 3.2/3.4 mit echten Hardware-Tests.

- [ ] **Task 7: `controller.py` Mono-Modul** (AC: 1, 2, 5, 9, 10, 11, 13)
  - [ ] `Mode` Enum: `DROSSEL`, `SPEICHER`, `MULTI` (lowercase Values wegen DB-CHECK-Constraint).
  - [ ] Klasse `SetpointProvider` (Abstract-ish) + `_NoopSetpointProvider`-Default.
  - [ ] Klasse `Controller` mit:
    - `__init__(self, ha_client, state_cache, db_conn_factory, adapter_registry, mode: Mode = Mode.DROSSEL, setpoint_provider: SetpointProvider | None = None, now_fn = lambda: datetime.now(tz=UTC))`
    - `async def on_sensor_update(self, event_msg: dict, device: DeviceRecord) -> None`
    - Interner `_classify_source(event_msg) -> Literal["solalex","manual","ha_automation"]` (Logik aus AC 5).
    - Interner `_dispatch_by_mode(mode) -> PolicyDecision | None` (match-Block mit **Noop-Policies für 3.2/3.3/3.4** — Stub liefert `None`).
    - Interner `_record_noop_cycle(...)` für Source=`manual`/`ha_automation` (keine Solalex-Write-Entscheidung, aber Zyklus wird attribuiert).
    - Interner `_safe_dispatch(decision)` mit Fail-Safe-Wrapper (try/except → vetoed Row, keine Propagation).
  - [ ] Skip-Condition: wenn `state_cache.test_in_progress == True` **oder** `device.commissioned_at is None` → Controller returnt sofort ohne Zyklus-Row (kein Spam während Funktionstest).

- [ ] **Task 8: `kpi/__init__.py` Noop-Stub** (AC: 11)
  - [ ] Neue Datei `backend/src/solalex/kpi/__init__.py` mit:
    ```python
    async def record(cycle):  # noqa: ARG001
        """v1-Noop — echte KPI-Aggregation ist Epic 5."""
        return None
    ```
  - Das ist explizit ein Stub — **keine** Attribution-Logik, keine DB-Operationen. Epic 5 ersetzt den Body, nicht die Signatur.

- [ ] **Task 9: Startup-Integration in `main.py`** (AC: 1, 12, 13)
  - [ ] In `lifespan()` nach DB-Migration + vor `ha_client_task`: Controller-Instanz bauen und an `app.state.controller` hängen.
  - [ ] `_dispatch_event` erweitern: nach `state_cache.update(...)` eine Lookup `entity_id → DeviceRecord` (aus neuem `app.state.devices_by_entity: dict[str, DeviceRecord]`) **und** — nur wenn Device existiert und `commissioned_at is not None` und `state_cache.test_in_progress is False` — `await app.state.controller.on_sensor_update(msg, device)`.
  - [ ] `devices_by_entity` wird im Lifespan aus `list_devices(conn)` aufgebaut (gleicher Durchlauf wie `entity_role_map`).
  - [ ] HA-Subscriptions für kommissionierte Devices: Nach HA-WS-Auth (oder lazy beim ersten Event) `ensure_entity_subscriptions(ha_client.client, commissioned_entity_ids, state_cache)` aufrufen. **Wenn `ensure_entity_subscriptions` zu Funktionstest-spezifisch ist**, eine Schwester-Funktion `ensure_controller_subscriptions(...)` neben ihr in `setup/test_session.py` oder einem neuen `ha_client/subscriptions.py` anlegen — aber Logik identisch (subscribe_trigger auf `state_changed` pro Entity).

- [ ] **Task 10: Unit-Tests** (AC: 14)
  - [ ] `backend/tests/unit/test_controller_dispatch.py` (Pipeline + Fail-Safe).
  - [ ] `backend/tests/unit/test_executor_dispatcher.py` (Veto-Kaskade).
  - [ ] `backend/tests/unit/test_executor_rate_limiter.py` (Persistenz über „Restart").
  - [ ] `backend/tests/unit/test_source_attribution.py` (HA-context-Parsing).
  - [ ] `backend/tests/unit/test_control_cycles_repo.py` (Insert + list_recent).
  - [ ] `backend/tests/unit/test_latency_repo.py` (Insert smoke).
  - [ ] `backend/tests/unit/test_setpoint_provider.py`.
  - [ ] Fakes statt Mocks wo möglich: `FakeHaClient` mit `call_service`-Spy, in-memory aiosqlite DB.

- [ ] **Task 11: Final Verification** (AC: 14)
  - [ ] `cd backend && uv run ruff check .` → grün.
  - [ ] `cd backend && uv run mypy --strict src/` → grün.
  - [ ] `cd backend && uv run pytest -q` → grün, Coverage-Target erreicht.
  - [ ] SQL-Ordering-Check: `ls backend/src/solalex/persistence/sql/` → `001_initial.sql`, `002_control_cycles_latency.sql` (lückenlose Nummerierung).
  - [ ] Drift-Check: `grep -rE "asyncio.Queue|events/bus|structlog|APScheduler" backend/src/solalex/` → 0 Treffer (Stolpersteine aus CLAUDE.md).
  - [ ] Drift-Check: `grep -rE "def record|def update" backend/src/solalex/controller.py` → bestätigt, dass `kpi.record` + `state_cache.update` als direkte Aufrufe im Controller-Code vorkommen.
  - [ ] Manual-Smoke (wenn möglich): Add-on lokal starten, 1 Device commissioned, Smart-Meter-Wert ändern in HA Entwicklerwerkzeuge → prüfen, ob `control_cycles`-Row mit `source='manual'` entsteht (echte Regel-Logik ist Stub, aber Source-Attribution + Zyklus-Row müssen funktionieren).

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Core Architectural Decisions, Zeile 229–260](../planning-artifacts/architecture.md) — Direct-Call-Entscheidung, Mono-Controller, keine Queue.
- [architecture.md — API & Communication Patterns, Zeile 354–366](../planning-artifacts/architecture.md) — `controller.on_sensor_update` Beispiel-Code.
- [architecture.md — Rate-Limiter-Persistenz, Zeile 434](../planning-artifacts/architecture.md) — EEPROM-Schutz über Restart.
- [architecture.md — Data Architecture, Zeile 262–306](../planning-artifacts/architecture.md) — `control_cycles` Ringpuffer + `latency_measurements` 30-Tage.
- [architecture.md — Integration Points / Flows, Zeile 838–845](../planning-artifacts/architecture.md) — volle Kette inkl. Sequenz der Aufrufe.
- [architecture.md — Amendment 2026-04-22, Zeile 1023+](../planning-artifacts/architecture.md) — 16 Cuts, u. a. Controller-6er-Split gestrichen.
- [prd.md — FR18/FR19/FR27/FR31/FR34, Zeile 600–625](../planning-artifacts/prd.md) — Fail-Safe, Rate-Limit, Source-Attribution, Regelzyklen-Log, Latenz-Messung.
- [CLAUDE.md — 5 harte Regeln](../../CLAUDE.md) — insbesondere Regel 3 (Closed-Loop + Rate-Limit + Fail-Safe) und Regel 5 (Logging via `get_logger(__name__)`).
- [CLAUDE.md — Stolpersteine](../../CLAUDE.md) — `asyncio.Queue`, `structlog`, `APScheduler`, Controller-Submodul-Split, `SetpointProvider`-Extern sind **verboten**.
- [Story 2.2](./2-2-funktionstest-mit-readback-commissioning.md) — Executor-Readback ist bereits implementiert (`executor/readback.py`), `state_cache.test_in_progress` existiert als Lock-Signal.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Reine Backend-Story. **Keine Frontend-Änderungen.** Das Dashboard (Epic 5) pollt `/api/v1/control/state`, das bleibt in 3.1 unverändert — nur `state_cache.update(...)` wird um Controller-Zyklus-Metadaten erweitert, falls der Zyklus sie liefert.

**Dateien, die berührt werden dürfen:**

- **NEU Backend:**
  - `backend/src/solalex/controller.py` (neues Mono-Modul — **keine Sub-Files** wie `drossel.py` anlegen).
  - `backend/src/solalex/executor/dispatcher.py`
  - `backend/src/solalex/executor/rate_limiter.py`
  - `backend/src/solalex/persistence/repositories/control_cycles.py`
  - `backend/src/solalex/persistence/repositories/latency.py`
  - `backend/src/solalex/persistence/sql/002_control_cycles_latency.sql`
  - `backend/src/solalex/kpi/__init__.py` (Noop-Stub, Signatur ist Epic-5-fest).
  - `backend/tests/unit/test_controller_*.py`, `test_executor_*.py`, `test_control_cycles_repo.py`, `test_latency_repo.py`, `test_source_attribution.py`, `test_setpoint_provider.py`.
- **MOD Backend:**
  - `backend/src/solalex/main.py` — Lifespan: Controller bauen + `devices_by_entity` Map; `_dispatch_event`: Controller-Hook nach `state_cache.update(...)`.
  - `backend/src/solalex/adapters/base.py` — `get_limit_range(device)` ergänzen.
  - `backend/src/solalex/adapters/hoymiles.py`, `marstek_venus.py`, `shelly_3em.py` — `get_limit_range`-Override.
  - `backend/src/solalex/executor/__init__.py` — Re-Exports (optional).
  - Optional `backend/src/solalex/setup/test_session.py` oder neuer `backend/src/solalex/ha_client/subscriptions.py` — `ensure_controller_subscriptions` extrahieren, **wenn** `ensure_entity_subscriptions` nur Test-Sessions bedient.

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du `asyncio.Queue`, `events/bus.py`, Pub/Sub-Dispatch oder Subscription-Registry für den internen Control-Flow einbaust — **STOP**. Direkte Funktionsaufrufe (Architecture Zeile 241).
- Wenn du `controller.py` splittest in `drossel.py` / `speicher.py` / `multi.py` / `mode_selector.py` / `pid.py` / `failsafe.py` — **STOP**. Mono-Modul mit `match mode:` (Architecture Zeile 242, Amendment 2026-04-22 Cut 9).
- Wenn du SQLAlchemy-Modelle, Alembic-Migrations oder `pyproject.toml`-Dependencies für ORM einbaust — **STOP**. Raw aiosqlite (CLAUDE.md Regel 1 + architecture.md Zeile 264).
- Wenn du `structlog` importierst — **STOP**. `from solalex.common.logging import get_logger`.
- Wenn du `APScheduler` für Scheduling einbaust — **STOP**. Für 3.1 kein Scheduling nötig; die nightly-KPI-Rollup-Task ist Epic 5, nicht 3.1.
- Wenn du `cryptography` oder `Ed25519` importierst — **STOP**. Kein Teil dieser Story.
- Wenn du ein JSON-Template-Verzeichnis `/data/templates/` oder einen JSON-Schema-Validator für Adapter-Configs anlegst — **STOP**. Adapter sind Python-Module mit Hardcoded-Dicts (CLAUDE.md Regel 2, Amendment 2026-04-22).
- Wenn du einen `SetpointProvider` in ein eigenes Modul `setpoints/` auslagerst — **STOP**. Klasse direkt in `controller.py` (AC 10, Architecture Zeile 794).
- Wenn du `logging.getLogger(...)` statt `get_logger(__name__)` nutzt — **STOP**. CLAUDE.md Regel 5.
- Wenn du einen JSON-Response-Wrapper `{data: ..., success: true}` um neue Endpoints legst (falls überhaupt welche in 3.1 entstehen, was nicht vorgesehen ist) — **STOP**. Direkt das Objekt (CLAUDE.md Regel 4).
- Wenn du `disclaimer_accepted_at`, `license`-Logik oder LemonSqueezy-Calls einbaust — **STOP**. Das ist Epic 7.
- Wenn du Drossel-/Speicher-/Multi-**Policies** produktiv ausformulierst (echte Watt-Berechnung mit Hysterese/Deadband/Moving-Average) — **STOP**. Diese sind Story 3.2 (Drossel), 3.3 (Pool), 3.4 (Speicher), 3.5 (Mode-Selector + Hysterese). In 3.1 reichen **Noop-Stubs**, die `None` liefern.
- Wenn du die `subscribe_trigger`-Logik per HA-WS umschreibst oder `_dispatch_event`-Shape brichst (siehe `main.py` Z. 55–94) — **STOP**. Das ist aus Story 1.3/2.2 stabil.

### Architecture Compliance Checklist

- **snake_case überall** (CLAUDE.md Regel 1): Tabellen (`control_cycles`, `latency_measurements`), Spalten (`sensor_value_w`, `readback_mismatch`, `cycle_duration_ms`), Python-Variablen, Enum-Values (`'drossel'`, `'speicher'`, `'multi'`, `'idle'`), JSON-API-Felder. Enum-Klassennamen (`Mode`) dürfen PascalCase bleiben (Sprach-Konvention).
- **Ein Python-Modul pro Adapter** (CLAUDE.md Regel 2): `adapters/base.py` um `get_limit_range` ergänzen — keine neue Subfolder-Struktur.
- **Closed-Loop-Readback für jeden Write** (CLAUDE.md Regel 3): in `dispatcher.dispatch(...)` nach jedem `call_service` **zwingend** `verify_readback(...)` aufrufen und ins `control_cycles`-Row übernehmen. Keine Write-Calls ohne Readback — nicht mal „nur kurz".
- **JSON ohne Wrapper** (CLAUDE.md Regel 4): 3.1 schreibt keine neuen API-Endpoints. Falls du Hilfsendpoints brauchst, direkt das Objekt.
- **Logging** (CLAUDE.md Regel 5): `_logger = get_logger(__name__)` am Modul-Top; `_logger.exception(...)` in allen `except`-Blöcken (insbesondere Fail-Safe-Wrapper).
- **MyPy strict**: alle neuen Funktionen haben Type-Hints; `from __future__ import annotations` am Modul-Top; keine `Any` ausserhalb der HA-Wire-Format-Boundaries.
- **Forward-only Migrations**: `002_*.sql` nie editieren nach Merge — jede weitere Änderung kommt als `003_*.sql`.

### Pipeline-Kette — Reference Flow

```
HA state_changed event
  ↓ _dispatch_event in main.py
  ↓ state_cache.update(entity_id, state, ...)                  [bestand]
  ↓ device = app.state.devices_by_entity.get(entity_id)        [NEU]
  ↓ wenn device & commissioned & !test_in_progress:            [NEU]
  ↓   controller.on_sensor_update(msg, device)                 [NEU]
  ↓   ├─ source = _classify_source(msg)
  ↓   ├─ mode = self._current_mode (statisch in 3.1)
  ↓   ├─ decision = self._dispatch_by_mode(mode, ...)          [Policy-Stub → None in 3.1]
  ↓   ├─ wenn decision:
  ↓   │   ├─ _safe_dispatch(decision)
  ↓   │   │   ├─ executor.dispatcher.dispatch(decision, ctx)
  ↓   │   │   │   ├─ range_check → vetoed oder weiter
  ↓   │   │   │   ├─ rate_limiter.check_and_reserve → vetoed oder weiter
  ↓   │   │   │   ├─ adapter.build_set_*_command
  ↓   │   │   │   ├─ ha_client.call_service(...)              [try: Fail-Safe bei Exception]
  ↓   │   │   │   ├─ rate_limiter.mark_write(last_write_at)
  ↓   │   │   │   ├─ readback.verify_readback(...)
  ↓   │   │   │   ├─ control_cycles.insert(row)
  ↓   │   │   │   └─ latency.insert(row) [nur wenn passed]
  ↓   │   └─ kpi.record(cycle)                                 [Noop-Stub]
  ↓   └─ wenn decision is None und source != 'solalex':
  ↓       _record_noop_cycle(source=source, mode=self._current_mode)  [AC 5]
```

### Source-Attribution — HA Context Logik

HA sendet in jedem `state_changed`-Event ein `context`-Objekt:

```json
{
  "event": {
    "data": {
      "new_state": {
        "context": {"id": "01HQZ...", "user_id": "abc...", "parent_id": null}
      }
    }
  }
}
```

Regeln:
- `user_id` gesetzt + `parent_id` == `None` → **manual** (User hat direkt geändert).
- `parent_id` gesetzt → **ha_automation** (Automation oder Script als Parent-Context).
- Beide `None` → default `ha_automation` (oft System-interne Events, z. B. Zustandsabfrage).
- **Wenn Solalex gerade geschrieben hat** (innerhalb 2 s: vergleiche mit `state_cache.last_command_at` und `entity_id == device.entity_id`) → **solalex** überschreibt die HA-Context-Heuristik. Der Executor-Pfad setzt ohnehin `source='solalex'` beim Insert — die HA-Context-Heuristik greift nur für Events, die **nicht** als direkte Folge eines Solalex-Writes kommen.

### Previous Story Intelligence

**Aus Story 1.3 (HA-WS-Foundation, `done`):** `ha_client.ReconnectingHaClient` + `HaWebSocketClient` sind stabil. `call_service` + `subscribe` + `get_states` sind vorhanden. Der Event-Handler-Hook-Point ist `_dispatch_event` in `main.py` — dort **additiv** Controller-Hook einfügen, bestehende State-Cache-Logik nicht umschreiben.

**Aus Story 2.2 (Funktionstest mit Readback, `review`):**
- `executor/readback.py` existiert bereits mit `verify_readback(...)` — **nicht neu schreiben, nur nutzen**.
- `setup/test_session.py::ensure_entity_subscriptions(...)` subscribed Entities für Readback. Prüfe, ob die Funktion generisch genug für Controller-Use ist; falls sie Test-spezifische Seiteneffekte hat, extrahiere eine schlanke Geschwister-Funktion `ensure_controller_subscriptions`.
- `state_cache.test_in_progress` + `state_cache.last_command_at` sind als Exklusiv-Lock-Felder vorhanden (AC 13).
- `POST /api/v1/setup/test` nutzt einen `asyncio.Lock`, das ist ein Funktionstest-Scope-Lock — der Controller darf parallel laufen, aber `test_in_progress` muss ihn blockieren.

**Aus Story 2.3 (Disclaimer + Aktivieren, `review`):**
- `POST /api/v1/setup/commission` setzt `devices.commissioned_at` für alle Devices auf einen Timestamp.
- `mark_all_commissioned(conn, ts)` ist in `persistence/repositories/devices.py` vorhanden.
- Der Controller-Startup-Hook braucht exakt dieses Feld, um commissioned vs. non-commissioned Devices zu trennen (AC 12).

**Aus Story 1.4 (Design System, `review`):** Keine direkte Auswirkung — 3.1 ist reines Backend.

### Anti-Patterns & Gotchas

- **KEIN Sleep im Controller-Hot-Pfad**: Readback-Wait-Zeit ist bereits in `readback.verify_readback(...)` eingekapselt. Nicht zusätzlich `asyncio.sleep` drum-herum.
- **KEIN blocking SQLite-Call** (sync `sqlite3` statt `aiosqlite`) — jeder DB-Call ist `await`-bar via `aiosqlite.Connection`.
- **KEIN Writer-Lock-Contention**: Mehrere Devices können parallel Events feuern; der Controller darf **pro Device** einen Lock halten, aber **nicht global**. Einfachste Umsetzung in 3.1: Lock pro `device_id` in einem `dict[int, asyncio.Lock]`. Alternativ: kein Lock und stattdessen die `UNIQUE`-Constraint der DB reicht (der Rate-Limiter serialisiert effektiv pro Device über `last_write_at`). Entscheide pragmatisch; bei Zweifel `dict[int, asyncio.Lock]`.
- **KEIN Abfangen von `asyncio.CancelledError`** im Fail-Safe-Wrapper — Cancellation muss propagiert werden (sonst bleibt der Lifespan beim Shutdown hängen).
- **KEIN `datetime.utcnow()`** — immer `datetime.now(tz=UTC)` (MyPy-strict mag `utcnow()` nicht; CLAUDE.md zwingt aware timestamps).
- **KEIN Try/Except around `kpi.record(cycle)`** — wenn der Noop-Stub wirft, ist das ein Bug, kein Fail-Safe-Case.
- **KEIN Logging des Supervisor-Tokens** oder anderer Secrets in `control_cycles.reason` oder Log-Meldungen (CLAUDE.md Security-Hygiene).
- **KEIN Referenz auf `devices.last_write_at` außerhalb von `executor/rate_limiter.py`** — zentralisiere den Rate-Limit-Lesezugriff, damit später ein Cache-Layer (v2) leicht dazukommt.
- **KEIN `subscribe_events` (broad)** für Controller-Events — nutze `subscribe_trigger` auf `state_changed` pro Entity (konsistent mit Story 2.2, Architecture-Test). Broadcast-Events erzeugen unnötigen Traffic für nicht-relevante Entities.

### Source Tree — Zielzustand nach Story

```
backend/src/solalex/
├── controller.py                              [NEW — Mono-Modul]
├── executor/
│   ├── __init__.py                            [MOD — optional re-exports]
│   ├── readback.py                            [unverändert, aus 2.2]
│   ├── dispatcher.py                          [NEW]
│   └── rate_limiter.py                        [NEW]
├── adapters/
│   ├── base.py                                [MOD — get_limit_range]
│   ├── hoymiles.py                            [MOD — get_limit_range]
│   ├── marstek_venus.py                       [MOD — get_limit_range]
│   └── shelly_3em.py                          [MOD — get_limit_range raises]
├── kpi/
│   └── __init__.py                            [NEW — async def record Noop-Stub]
├── persistence/
│   ├── sql/
│   │   ├── 001_initial.sql                    [unverändert]
│   │   └── 002_control_cycles_latency.sql     [NEW]
│   └── repositories/
│       ├── control_cycles.py                  [NEW]
│       └── latency.py                         [NEW]
├── ha_client/
│   └── subscriptions.py                       [OPTIONAL-NEW — falls Extraktion nötig]
└── main.py                                    [MOD — Lifespan + _dispatch_event Hook]

backend/tests/unit/
├── test_controller_dispatch.py                [NEW]
├── test_executor_dispatcher.py                [NEW]
├── test_executor_rate_limiter.py              [NEW]
├── test_source_attribution.py                 [NEW]
├── test_control_cycles_repo.py                [NEW]
├── test_latency_repo.py                       [NEW]
└── test_setpoint_provider.py                  [NEW]
```

Frontend: **keine Änderungen.**

### Testing Requirements

- **Framework:** `pytest` + `pytest-asyncio` (already in `backend/pyproject.toml` aus Story 1.1).
- **Fakes:** `FakeHaClient` mit `call_service`-Call-Recording + konfigurierbarer Exception. `FakeClock` via `now_fn` Parameter (nicht monkeypatch `datetime.now`).
- **DB-Fixture:** In-Memory aiosqlite DB + `run_migration(":memory:")` vor jedem Test.
- **Hard-CI-Gates (CLAUDE.md):** Ruff + MyPy strict + Pytest + SQL-Migrations-Ordering.
- **Coverage-Ziel:** ≥ 90 % line coverage auf neuen Files. Messung via `pytest --cov=solalex.controller --cov=solalex.executor.dispatcher --cov=solalex.executor.rate_limiter --cov=solalex.persistence.repositories.control_cycles --cov=solalex.persistence.repositories.latency`.

### Technology & Version Notes

- **Python 3.13**: Nutze `from __future__ import annotations`, moderne Union-Syntax `X | None`, `match`-Statement für Enum-Dispatch (sauberer als `if/elif` für `Mode`).
- **aiosqlite ≥ 0.19**: `Connection.execute(...)` liefert `Cursor` via async context manager; `fetchall()` / `fetchone()` sind `await`-bar.
- **FastAPI Lifespan API** (aus Story 1.1/1.3): `@asynccontextmanager async def lifespan(app: FastAPI) -> AsyncIterator[None]` — der bestehende `lifespan` in `main.py` ist der Hook-Point.
- **`websockets` (async)**: `ha_client/client.py` nutzt `websockets.asyncio.client.connect`. Call-Service-Return-Shape: `{"id": N, "type": "result", "success": true/false, "result": {...}}`.
- **HA Wire-Format `context`**: `context = {"id": str, "user_id": str | None, "parent_id": str | None}` — stabil seit HA 0.114, keine Breaking-Changes erwartet.

### Performance & Sicherheit

- **NFR2 (Dashboard-TTFD ≤ 2 s)**: 3.1 hat keinen direkten UI-Pfad, aber der Controller darf **nicht** den `state_cache.update(...)`-Pfad blockieren. Daher: Controller-Hook im `_dispatch_event` ist `await`-bar, aber eine lange-laufende Readback-Verifikation (bis 15 s) muss **außerhalb** des `_dispatch_event`-Handlers laufen — verwende `asyncio.create_task(controller.on_sensor_update(...))` für Fire-and-Forget, oder: der Controller selbst startet `_safe_dispatch` via `asyncio.create_task`. **Empfohlen**: `_dispatch_event` `await`t nur `_classify_source` + `_record_noop_cycle` (schnell); `_safe_dispatch` via `asyncio.create_task` (der Readback-Wait blockiert dann nicht den HA-Event-Loop).
- **CLAUDE.md Safety Rule 3**: Every write path has readback, rate-limit, range-check — **nicht optional**, selbst bei trivialen Test-Writes.
- **Event-Flood-Resilience**: HA kann bei Bulk-Updates (z. B. Neustart eines Integrations-Loads) viele `state_changed` auf einmal senden. Controller soll nicht für jeden eine Policy-Entscheidung treffen — die Deduplication/Deadband-Logik liegt in 3.2/3.4 (`min change threshold` in der Policy). Für 3.1 reicht: jeder Event wird klassifiziert + attribuiert, aber nur bei konkretem `PolicyDecision` ein Write.

### Git Intelligence Summary

- **Zuletzt gemergte Commits (Stand: `a94c0f8`):**
  - `a94c0f8 feat(wizard): Story 2.3 — Disclaimer-Screen mit Commissioning-Gate`
  - `2f7bc8a Fix GHCR release target and bump beta to 0.1.0-beta.1`
  - `848bad7 Ship initial 0.1.0-beta.0 release for Home Assistant testing`
  - `f1d6bd3 Remove dark mode theme overrides from frontend CSS`
  - `ad66eef Prepare Epic 2 baseline with updated planning artifacts and UI foundation changes`
- Epic 2 ist merge-weit „review" — Story 3.1 startet Epic 3 als **erste Backend-Schwergewichts-Story**.
- **Atomarer Commit-Vorschlag (erst nach Alex' Anweisung):**
  1. SQL 002 + repositories (control_cycles + latency).
  2. Executor (dispatcher + rate_limiter) + base-Adapter-Spanne.
  3. Controller Mono-Modul + kpi-Noop-Stub.
  4. `main.py`-Lifespan- und `_dispatch_event`-Integration.
  5. Tests (ein Commit, zusammenhängend).
- **Keine Commits ohne Alex' Anweisung.** Keine `Co-Authored-By` ohne Rücksprache.

### References

- [epics.md — Story 3.1, Zeile 757–802](../planning-artifacts/epics.md)
- [architecture.md — v. a. §Core Decisions + §Data Architecture + §Amendment-Log](../planning-artifacts/architecture.md)
- [prd.md — FR18/FR19/FR27/FR31/FR34, Zeile 600–625](../planning-artifacts/prd.md)
- [Story 1.3 — HA-WebSocket-Foundation](./1-3-ha-websocket-foundation-mit-reconnect-logik.md)
- [Story 2.2 — Funktionstest mit Readback](./2-2-funktionstest-mit-readback-commissioning.md)
- [Story 2.3 — Disclaimer + Aktivieren](./2-3-disclaimer-aktivieren.md)
- [CLAUDE.md — 5 Regeln + Stolpersteine](../../CLAUDE.md)
- [aiosqlite Docs](https://aiosqlite.omnilib.dev/en/stable/)
- [HA WebSocket API — subscribe_trigger + state_changed](https://developers.home-assistant.io/docs/api/websocket)
- [HA Context-Objekt — user_id / parent_id](https://developers.home-assistant.io/docs/core/context/)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `controller.py` Mono-Modul vorhanden, `Mode`-Enum + `match`-Dispatch + `SetpointProvider`-Interface + Fail-Safe-Wrapper drin.
2. `executor/dispatcher.py` Veto-Kaskade (Range → Rate-Limit → Readback) implementiert; jeder Write führt zu `control_cycles.insert` + `devices.last_write_at`-Update im selben DB-Scope.
3. `executor/rate_limiter.py` persistiert über Restart (Test mit zwei Executor-Instanzen verifiziert).
4. `control_cycles` + `latency_measurements` Tabellen via `002_*.sql` angelegt; Repositories mit `insert` + `list_recent` funktionieren.
5. `main.py` Lifespan ruft Controller-Setup + `_dispatch_event` ruft `controller.on_sensor_update` für commissionierte Devices außerhalb des Funktionstest-Locks.
6. `kpi/__init__.py` hat `async def record(cycle)`-Noop-Stub; Controller importiert und ruft ihn auf.
7. Source-Attribution liefert `solalex` / `manual` / `ha_automation` gemäß AC 5.
8. Alle 4 CI-Gates grün (Ruff + MyPy strict + Pytest + SQL-Ordering), Coverage ≥ 90 % auf den neuen Files.
9. Drift-Checks bestanden: kein `asyncio.Queue`, kein `events/bus`, kein `structlog`, kein `APScheduler`, kein Controller-Sub-Split, kein separates `SetpointProvider`-Modul.
10. Bestehende Tests (Story 1.3, 2.2, 2.3) bleiben grün — `POST /api/v1/setup/test` unverändert, Commission-Flow unverändert.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.1 erstellt und auf `ready-for-dev` gesetzt. Core-Controller-Mono-Modul + Executor-Veto-Kaskade + persistenter Rate-Limiter + Source-Attribution + control_cycles/latency_measurements. Backend-only. | Claude Opus 4.7 |
