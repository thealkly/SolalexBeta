# Story 3.1: Core Controller (Mono-Modul, Sensor → Policy → Executor) + Event-Source + Readback + persistenter Rate-Limit

Status: done

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

- [x] **Task 1: SQL-Migration 002 (control_cycles + latency_measurements)** (AC: 7, 8)
  - [x] Neue Datei `backend/src/solalex/persistence/sql/002_control_cycles_latency.sql`.
    - Tabellen `control_cycles` + `latency_measurements` mit exakt den Spalten aus AC 7 / AC 8.
    - Indexes: `CREATE INDEX idx_control_cycles_ts ON control_cycles(ts DESC)`, `CREATE INDEX idx_control_cycles_device ON control_cycles(device_id)`.
    - `CHECK`-Constraints für Enum-Spalten (SQLite erlaubt Check-Constraints — syntaktisch inline in `CREATE TABLE`).
    - Forward-only: keine `ALTER TABLE`, nur `CREATE TABLE IF NOT EXISTS`.
  - [x] Smoke-Test: lokales `pytest -k migrate` verifiziert, dass `run(db_path)` die neue Migration problemlos auf einer DB anwendet, die bereits auf `001` steht.

- [x] **Task 2: `persistence/repositories/control_cycles.py`** (AC: 3, 6, 7, 9)
  - [x] Datenklasse `ControlCycleRow` (dataclass, snake_case-Felder exakt wie die Tabelle).
  - [x] `async def insert(conn: aiosqlite.Connection, row: ControlCycleRow) -> int`.
  - [x] `async def list_recent(conn: aiosqlite.Connection, limit: int = 100) -> list[ControlCycleRow]` → `ORDER BY id DESC LIMIT ?`.
  - [x] `async def list_by_device(conn, device_id, limit=100) -> list[ControlCycleRow]` (Dashboard-/Diagnose-Support für Epic 4/5).
  - [x] Kein ORM, nur raw `aiosqlite` mit handgeschriebenem SQL (CLAUDE.md Regel 1 + „Kein SQLAlchemy").

- [x] **Task 3: `persistence/repositories/latency.py`** (AC: 8)
  - [x] Datenklasse `LatencyMeasurementRow`.
  - [x] `async def insert(conn, row) -> int`.
  - [x] `async def list_for_device(conn, device_id, since_ts) -> list[...]` (für Epic 4.4 vorbereitet, keine 30-Tage-Retention in 3.1).

- [x] **Task 4: `executor/rate_limiter.py`** (AC: 4)
  - [x] Funktion `async def check_and_reserve(conn, device_id, min_interval_s, now) -> tuple[bool, datetime | None]` — `True` wenn erlaubt, sonst `False` + `last_write_at`.
  - [x] Funktion `async def mark_write(conn, device_id, ts)` — UPDATE `devices SET last_write_at=?`.
  - [x] Reine SQL-Logik, liest/schreibt **nur** `devices.last_write_at`.
  - [x] **Nicht** `datetime.now()` intern benutzen — immer Parameter `now` akzeptieren (Testbarkeit).

- [x] **Task 5: `executor/dispatcher.py`** (AC: 3, 6, 9)
  - [x] Datenklasse `PolicyDecision`: `device: DeviceRecord`, `target_value_w: int`, `mode: Mode`, `command_kind: Literal["set_limit","set_charge"]`.
  - [x] Datenklasse `DispatchResult` (Status + geschriebener `ControlCycleRow`).
  - [x] Funktion `async def dispatch(decision, ctx: DispatchContext) -> DispatchResult`:
    1. Range-Check via Adapter-Hardware-Spanne (siehe Task 6 für die Spanne-API).
    2. Rate-Limit via `rate_limiter.check_and_reserve`.
    3. Build Command via `adapter.build_set_limit_command` oder `build_set_charge_command`.
    4. `ha_client.call_service(...)` — bei Exception propagiert bis zum Fail-Safe-Wrapper im Controller (AC 9).
    5. `rate_limiter.mark_write(...)` + `control_cycles.insert(...)` + `latency.insert(...)` im selben DB-Commit.
    6. `readback.verify_readback(...)` zwischen Service-Call und DB-Commit.
    7. `latency.insert(...)` nur wenn readback `status='passed'`.
  - [x] `DispatchContext` bündelt `ha_client`, `state_cache`, `db_conn_factory` (async context manager), `adapter_registry` (Dict), `now_fn: Callable[[], datetime]`.

- [x] **Task 6: Adapter-Hardware-Spanne** (AC: 3)
  - [x] `AdapterBase` in `adapters/base.py` um Methode `get_limit_range(device) -> tuple[int, int]` erweitern (Default: `(0, 10_000)` für W — Subclasses überschreiben).
  - [x] Hoymiles: `(2, 1500)` W (OpenDTU Hardware-Spec-Minimum, HM-1500 Max).
  - [x] Marstek Venus: `(0, 2500)` W (Charge-Range für Venus 3E).
  - [x] Shelly 3EM: `NotImplementedError` (Smart-Meter schreibt nicht).
  - [x] `TODO(3.2/3.4)`-Kommentare für spätere Verfeinerung aus Device-Config gesetzt.

- [x] **Task 7: `controller.py` Mono-Modul** (AC: 1, 2, 5, 9, 10, 11, 13)
  - [x] `Mode` als `StrEnum`: `DROSSEL`, `SPEICHER`, `MULTI` (lowercase Values wegen DB-CHECK-Constraint).
  - [x] Klasse `SetpointProvider` + `_NoopSetpointProvider`-Default direkt im Modul.
  - [x] Klasse `Controller` mit vollständiger Signatur (inkl. `ha_ws_connected_fn` für Fail-Safe-Erkennung) und `on_sensor_update`, `_classify_source`, `_dispatch_by_mode` (match-Block), `_record_noop_cycle`, `_safe_dispatch`, `_write_failsafe_cycle`, Per-Device-`asyncio.Lock`-Map.
  - [x] Skip-Condition: `test_in_progress == True` **oder** `commissioned_at is None` → früher Return.

- [x] **Task 8: `kpi/__init__.py` Noop-Stub** (AC: 11)
  - [x] Neue Datei mit `async def record(cycle: ControlCycleRow) -> None`, Rückgabe `None`. Signatur ist Epic-5-fest.

- [x] **Task 9: Startup-Integration in `main.py`** (AC: 1, 12, 13)
  - [x] Lifespan baut `Controller`-Instanz nach DB-Migration, vor `ha_client_task`. Hängt an `app.state.controller`.
  - [x] `_dispatch_event` erweitert: nach `state_cache.update(...)` ruft es `controller.on_sensor_update(msg, device)` für commissioned Devices außerhalb des Funktionstest-Locks.
  - [x] `devices_by_entity` wird im Lifespan aus `list_devices(conn)` gebaut (gleicher Durchlauf wie `entity_role_map`).
  - [x] `_subscribe_controller_entities` ruft `ensure_entity_subscriptions(...)` für kommissionierte Devices nach erfolgreicher WS-Auth — eine Schwester-Funktion war nicht nötig, da `ensure_entity_subscriptions` reine Subscription-Verwaltung ist.

- [x] **Task 10: Unit-Tests** (AC: 14)
  - [x] `backend/tests/unit/test_controller_dispatch.py` (Pipeline + Fail-Safe + Event-Shape-Tolerance + Drift-Guard).
  - [x] `backend/tests/unit/test_executor_dispatcher.py` (Veto-Kaskade + Happy-Path + Latency-Row).
  - [x] `backend/tests/unit/test_executor_rate_limiter.py` (Persistenz über simulierten Restart).
  - [x] `backend/tests/unit/test_source_attribution.py` (HA-context-Parsing).
  - [x] `backend/tests/unit/test_control_cycles_repo.py` (Insert + list_recent + FK ON DELETE CASCADE).
  - [x] `backend/tests/unit/test_latency_repo.py` (Insert smoke + since_ts-Filter).
  - [x] `backend/tests/unit/test_setpoint_provider.py` (Noop + Custom Injection).
  - [x] `FakeHaClient` als Fake statt Mock; alle DB-Tests nutzen temporäre SQLite-Dateien via `tmp_path`.

- [x] **Task 11: Final Verification** (AC: 14)
  - [x] `uv run ruff check .` → grün.
  - [x] `uv run mypy --strict src/ tests/` → grün (73 Files).
  - [x] `uv run pytest -q` → 91 Tests grün, Coverage 95 % gesamt (Controller 92 %, Dispatcher 97 %, Rate-Limiter 92 %, Repos 100 %).
  - [x] SQL-Ordering: `001_initial.sql` + `002_control_cycles_latency.sql` — lückenlos.
  - [x] Drift-Check `asyncio.Queue|events/bus|structlog|APScheduler`: 0 Code-Treffer (nur dokumentarische Erwähnungen in Docstrings/Kommentaren, wie in CLAUDE.md vorgesehen).
  - [x] `kpi.record` als direkter `await`-Aufruf in `_safe_dispatch`, `_record_noop_cycle`, `_write_failsafe_cycle` bestätigt. `state_cache.update` läuft weiterhin in `main.py._dispatch_event` vor dem Controller-Hook (Reference-Flow in Dev Notes).
  - [ ] Manual-Smoke lokal im HA-Add-on offen (Backend-only, Ausführung durch Alex — kein Blocker für Review).

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

### Review Findings

**Code Review 2026-04-24** — Blind Hunter + Edge Case Hunter + Acceptance Auditor.

#### Decision-Needed — alle aufgelöst (Alex, 2026-04-24)

Die 5 Decision-Items wurden mit Alex diskutiert und als Patches bzw. Defer geführt (siehe unten bei Patch / Defer).

- [x] D1 **Rate-Limit-Slot asymmetrisch Exception vs. Readback-Failure** → **Status quo behalten + Kommentar klarstellen.** Patch P-D1 (Code-Kommentar am Dispatcher + Fail-Safe-Wrapper).
- [x] D2 **`set_last_command_at` vor vs. nach `call_service`** → **Nach erfolgreichem Call setzen.** Patch P-D2 (`dispatcher.py`).
- [x] D3 **`Mode`-Drift Enum vs. Literal (`'idle'`)** → **`'idle'` streichen (SQL 002 editieren, noch nicht deployed).** Patch P-D3 (3 Zeilen).
- [x] D4 **AC 1 ≤ 1 s vs. Readback-Wait** → **`cycle_duration_ms` misst nur synchrone Pipeline, nicht Readback.** Patch P-D4 + Kommentar.
- [x] D5 **Write-Amplification `_record_noop_cycle`** → **Akzeptiert als Defer.** Story 3.2/3.4 (Deadband) + 4.4 (Retention) fangen es. (Siehe Defer-Liste.)

#### Patch (direkt anzuwenden)

- [x] [Review][Patch] **P-D1: Asymmetrie der Rate-Limit-Slot-Buchung dokumentieren** — Status quo (Exception-Pfad verbraucht keinen Slot, Readback-Failure verbraucht einen) bleibt. Kommentar am Dispatcher vor `mark_write` + am `_safe_dispatch`-Wrapper ergänzen, der die Logik erklärt: "Exception = wir sind sicher, dass nichts gesendet wurde. Readback-Failure = wir haben gesendet, Hardware hat evtl. empfangen → Slot verbrauchen." [dispatcher.py:712-727, controller.py:283-319]
- [x] [Review][Patch] **P-D2: `set_last_command_at(now)` erst nach erfolgreichem `call_service`** — Aktuell vor dem Call, poisoned 2-s-Fenster bei Exception oder langsamem HA. Bewegen auf die Zeile direkt nach `await ctx.ha_client.call_service(...)`. Tests auf Source-Attribution-Pfad anpassen, falls sie die aktuelle Reihenfolge voraussetzen. [dispatcher.py:685-686]
- [x] [Review][Patch] **P-D3: `'idle'` aus Schema + Literals streichen** — SQL-Migration 002 editieren (noch nicht deployt): `CHECK (mode IN ('drossel','speicher','multi'))`. `Mode`-Literal in `control_cycles.py` auf 3 Werte. Dito in `latency.py`, falls dort auch. Keine neue Migration nötig. [sql/002:1079, control_cycles.py:880, latency.py]
- [x] [Review][Patch] **P-D4: `cycle_duration_ms` misst nur die synchrone Pipeline, nicht den Readback** — Im Controller beim `on_sensor_update`-Pfad Timer stoppen bevor `asyncio.create_task(_safe_dispatch)` gefeuert wird (für den Write-Pfad). Für Noop/Vetoed-Pfade bleibt die bestehende Messung gültig. Kommentar am Timer: "Pipeline bis Dispatch-Task-Spawn; Readback-Wait zählt separat in `latency_measurements.latency_ms`." AC 1 wird damit erfüllbar; Test `cycle_duration_ms <= 1000` ergänzen. [controller.py:155-178, dispatcher.py:197,237]
- [x] [Review][Patch] **Fail-closed auf malformed ISO in Rate-Limiter** — `except ValueError: return True, None` bypasst Rate-Limit bei korrupter Spalte. Stattdessen: Log + fail-closed (treat as "just wrote"). [rate_limiter.py:50-53]
- [x] [Review][Patch] **Clock-Skew: negative `elapsed_s` sperrt perpetuierlich** — Wenn `now < last_write_at` (System-Clock-Rücksprung), blockt der Check für Ewigkeiten. Fix: `if elapsed_s < 0: behandeln als "just wrote now"` + Log. [rate_limiter.py:55-58]
- [x] [Review][Patch] **Naive/tz-aware-Mix in `check_and_reserve`** — `datetime.fromisoformat(str(raw))` liefert naive datetime, wenn die Spalte ohne Offset gespeichert wurde; `now` ist tz-aware → `TypeError` auf subtract. Normalisieren auf UTC. [rate_limiter.py:50-55]
- [x] [Review][Patch] **`_lock_for(device.id=None)` → fresh Lock pro Aufruf = null Serialisierung** — Jede Invocation erzeugt neuen `asyncio.Lock()`. Gleichzeitig wirft `_require_id` später sowieso für None → dead defense. Entweder früh rejecten oder global sentinel-Lock. [controller.py:362-370]
- [x] [Review][Patch] **`_dispatch_by_mode` ohne Exhaustiveness-Guard** — `case _: assert_never(mode)` anfügen; sonst Return-None-Silent bei zukünftiger Mode-Erweiterung. [controller.py:217-233]
- [x] [Review][Patch] **Nested Exception im Fail-Safe-Wrapper** — Wenn `_write_failsafe_cycle` intern wirft (DB-Lock, Disk-Full), geht die Original-Exception verloren. Inner-DB-Call in try/except wrappen. [controller.py:314-319]
- [x] [Review][Patch] **`reason` column: `str(exc)` kann Stack/PII/Newlines enthalten** — `reason=f"fail_safe: {type(exc).__name__}"` + vollständigen Trace via `_logger.exception` getrennt loggen. Spalte bleibt schlank, UI-Formatierung stabil. [controller.py:316]
- [x] [Review][Patch] **`datetime.fromtimestamp(0)` ohne `tz=UTC` → naive local-time Fallback** — Jeder andere Timestamp im Code ist tz-aware. Konflikt bei späterem `timedelta`. Fix: `fromtimestamp(0, tz=UTC)`. [control_cycles.py:906]
- [x] [Review][Patch] **`_extract_sensor_w` akzeptiert NaN/Inf + HA-`'unavailable'`/`'unknown'`** — `float("nan")`/`float("inf")` passen durch; `float("unavailable")` wirft zwar ValueError aber der Catch ist zu breit. Explizite Filterung für `{'unavailable','unknown','none'}` + `math.isfinite`-Check. [controller.py:439-447]
- [x] [Review][Patch] **`event_msg["event"]` non-dict → AttributeError** — Malformed HA-Payload (`event=None` oder Liste) crasht vor dem `.get()`. isinstance-Guard am Anfang. [controller.py:406-436]
- [x] [Review][Patch] **Dispatch-Tasks: kein Cancel/Await bei Controller-Shutdown** — `asyncio.create_task(_safe_dispatch)` ohne `aclose()`-Hook. Lifespan-Shutdown erzeugt "Task was destroyed but it is pending"-Warnings; halb-committete Zyklen möglich. `Controller.aclose()` + Wiring in `main.py`-Lifespan. [controller.py:178-184, main.py]
- [x] [Review][Patch] **Adapter-Registry Lookup ohne Guard** — `ctx.adapter_registry[decision.device.adapter_key]` crasht unbehandelt bei unbekanntem Key; Exception wandert in den Fail-Safe-Wrapper. Fix: `.get(...)` + Veto mit `reason='unknown_adapter'`. [dispatcher.py]
- [x] [Review][Patch] **`adapter.get_limit_range` mit `min > max` nicht gefangen** — Misconfiguriertes Adapter-Modul → jeder Write silent als `invalid_range` vetoed. Fix: Sanity-Check + distinct reason. [dispatcher.py]
- [x] [Review][Patch] **`min_interval_s ≤ 0` disabled Safety** — Null deaktiviert EEPROM-Schutz, negativ invertiert Logik. Fix: `max(<default>, min_interval_s)` + Warn-Log. [rate_limiter.py]
- [x] [Review][Patch] **`mark_write` silent-no-op bei unbekannter `device_id`** — Fehlende Row → `UPDATE` affectet 0 rows, kein Signal. `cur.rowcount == 0` → Warn-Log (Device wurde zwischen Check und Mark gelöscht). [rate_limiter.py:65-75]
- [x] [Review][Patch] **Clock-Source-Mix: `t0 = time.monotonic()` vs `effect_at = ctx.now_fn()`** — `latency_ms` und `effect_at - command_at` können divergieren (Clock-Skew während Readback). Einheitliche Ableitung: `effect_at = command_at + timedelta(milliseconds=latency_ms)`. [dispatcher.py:698-699]
- [x] [Review][Patch] **`ha_ws_connected`-TOCTOU** — Check in `_safe_dispatch` → Dispatcher → `call_service`. Trennung der WS zwischen Check und Call → unnützer Exception-Pfad + zusätzliche `vetoed`-Row. Re-Check kurz vor `call_service` in Dispatcher einbauen. [controller.py:283-289, dispatcher.py]
- [x] [Review][Patch] **`list_recent(limit=0)` → leere Liste, schweigend** — SQLite akzeptiert `LIMIT 0`. Caller die ≥1 Row erwarten brechen. Fix: `limit = max(1, limit)`. [control_cycles.py:961-969]
- [x] [Review][Patch] **Runtime-Validation von `row.mode` vor Insert** — Dynamic-String aus zukünftiger Code-Pfad schlägt erst an SQLite-CHECK mit nichts-sagender `IntegrityError` auf. Explicit `assert row.mode in _ALLOWED_MODES` mit klarer Meldung. [control_cycles.py:930-957]
- [x] [Review][Patch] **Tests: geteilte `/tmp/solalex_noop_test.db` zwischen Runs** — Stale-File aus Prior-Run → Schema-Mismatch. `tmp_path`-Fixture nutzen. [test_setpoint_provider.py:2115,2139]
- [x] [Review][Patch] **Tests: Module-level ADAPTERS-Mutation** — `hoymiles.get_readback_timing = ...` mit try/finally-Restore ist flaky bei KeyboardInterrupt. `monkeypatch`-Fixture nutzen. [test_executor_dispatcher.py:1833-1843]
- [x] [Review][Patch] **CI-Gate: `--cov-fail-under=90` für Backend-Pytest** — AC 14 fordert ≥ 90 % Coverage; kein durchsetzender Gate im Script. [Backend CI config]
- [x] [Review][Patch] **Test-Lücke AC 9b: `devices.last_write_at` bleibt unverändert auf Fail-Safe-Pfad** — Existierende Fail-Safe-Tests prüfen nur Cycle-Row + Status. Zusätzliche Assertion `SELECT last_write_at` → NULL (oder unverändert). [test_controller_dispatch.py]

#### Defer (pre-existing / außerhalb Story-Scope)

- [x] [Review][Defer] **Check/Reserve/Mark nicht atomic im Dispatcher — TOCTOU** [rate_limiter + dispatcher] — deferred, spec Anti-Patterns Z. 260 akzeptiert die per-device-`asyncio.Lock`-Absicherung als Pragma für v1. Refactor zu "einem Connection-Scope + BEGIN IMMEDIATE" gehört in eine DB-Hardening-Story.
- [x] [Review][Defer] **Zweite DB-Transaction schlägt fehl nachdem HA-Call erfolgreich war → Ghost-Write** [dispatcher.py:712-727] — deferred, fundamentale 2-Phasen-Grenze (HA vs. DB). Gemildert durch Readback-Erkennung; vollständige Lösung erfordert Outbox/Journal-Pattern — Thema für v2 Reliability-Hardening.
- [x] [Review][Defer] **Sync-Readback (Hoymiles 15 s) blockiert Per-Device-Lock** [dispatcher.py:689-696] — deferred, Story 3.2+ adressiert Async-Readback-Pfad für OpenDTU/MQTT.
- [x] [Review][Defer] **`NotImplementedError` als semantisches "read-only-adapter"-Signal** [dispatcher.py] — deferred, Design-Diskussion; sauberer wäre `adapter.supports_write()`-Flag. Aktuell pragmatisch akzeptabel.
- [x] [Review][Defer] **`kpi.record` außerhalb der DB-Transaction → Dual-Write-Skew** [controller.py:273,321-322] — deferred, heute Noop-Stub — Epic-5-Thema, wenn die reale KPI-Aggregation hinzukommt.
- [x] [Review][Defer] **`test_direct_calls_no_queue_imports` naive Docstring-Toggle** [test_controller_dispatch.py:1576-1590] — deferred, AST-basierter Scan ist robuster; Test-Quality-Nit, blockiert niemanden.
- [x] [Review][Defer] **Zwei `Mode`-Definitionen (Enum in Controller, Literal in Repo)** [controller.py + control_cycles.py + latency.py] — deferred, kosmetische Typ-Duplikation. Wird mit Decision D3 ("idle"-Drift) ggf. gemeinsam aufgelöst.
- [x] [Review][Defer] **Scope-Bleed: Frontend + Story-2.x-Artefakte im Working-Tree** — deferred, nicht 3.1-Scope; existierte schon vor diesem Review.
- [x] [Review][Defer] **D5: Write-Amplification `_record_noop_cycle` (Bursty-Event-Flood auf Ringpuffer)** [controller.py:162-172] — deferred (Alex, 2026-04-24). Grund: Spec Z. 328 deferriert Deadband explizit auf Story 3.2/3.4; Retention kommt in 4.4. Storage-Volumen für Beta nicht blocker-kritisch; User hat gegen frühen Eingriff entschieden.
- [x] [Review][Defer] **Unbounded Dispatch-Task-Backlog** [controller.py:178-184] — deferred (2026-04-24). Per-Device-`asyncio.Lock` serialisiert Execution, aber Tasks selbst können bei bursty Sensors wachsen. Kein Blocker für v1 (Events kommen ~1 Hz/Device, Readback 5-15 s → Backlog <20). Saubere Lösung (bounded Queue oder Drop-if-pending) ist Design-Choice, gehört in eine v2-Scale-Story wenn reale Event-Flood-Daten aus Beta vorliegen.
- [x] [Review][Defer] **Test-Lücke: concurrent Dispatch pro Device (Stress-Test)** [test_controller_dispatch.py] — deferred (2026-04-24). Per-Device-Lock ist wichtige Defense, aber Race-Stress-Test ist komplex und kann flaky sein. Realistisch eigene Test-Coverage-Story vor Epic 4.

#### Dismissed (Noise, handled elsewhere, false positive)

- `except Exception` fängt bereits korrekt keine `BaseException` (KeyboardInterrupt/SystemExit bubbeln) — Blind-Hunter-Claim war falsch.
- AC 5 Default-Branch-Wording (`user_id==None && parent_id==None → ha_automation`) stimmt mit Implementation überein; Auditor-Hinweis ist semantische Ambiguität, kein Code-Bug.
- AC 3(c) "Readback-Erwartung vorhanden" — Type-System erzwingt non-optional `target_value_w`; strukturell äquivalent.
- `_track_task(name=f"controller_dispatch_{device.id}")` — Debug-only-Label, kein Code-Bug.
- `_row_to_cycle` bool(int(...)) auf malformed strings — mit NOT-NULL-Constraint und Repo-only-Writes unerreichbar.
- `subscribe_trigger`-Context-Pfad — Code liest `to_state.context` über `_extract_new_state`, was korrekt ist (HA-Wire-Format).
- Boundary-Equality-Test-Coverage — implizit durch happy-path abgedeckt, Nit.
- `len(Mode)`-Assertion im Test — funktioniert für aktuelles Enum.
- Snapshot von `dispatch_tasks`-Set im Test — in der Praxis stabil.
- `event_msg` entity_id differs from device.entity_id innerhalb 2-s-Window — in v1 überwacht Controller nur Device-eigene Entities.
- Dispatcher `PolicyDecision.mode: Literal` statt `Mode`-Enum — reiner Typ-Split, mypy-strict-kompatibel.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — bmad-dev-story Workflow

### Debug Log References

- `uv run ruff check .` (grün)
- `uv run mypy --strict src/ tests/` (grün, 73 Files)
- `uv run pytest -q` (91 Tests grün, ~1.2 s)
- `uv run pytest tests/unit --cov=solalex.controller --cov=solalex.executor.dispatcher --cov=solalex.executor.rate_limiter --cov=solalex.persistence.repositories.control_cycles --cov=solalex.persistence.repositories.latency` → Gesamt 95 %, Controller 92 %, Dispatcher 97 %, Rate-Limiter 92 %, Repos 100 %.
- `grep -rE "asyncio\.Queue|events/bus|structlog|APScheduler" backend/src/solalex/` → 0 Code-Treffer (zwei Docstring-Nennungen in `controller.py` / `common/logging.py`, die die verbotenen Pattern explizit als *nicht verwendet* markieren — CLAUDE.md-konform).

### Completion Notes List

- Mono-Modul-Controller mit `match`-Dispatch über `Mode.DROSSEL | SPEICHER | MULTI` umgesetzt; Policies für 3.2/3.3/3.4 sind inline-Stubs und liefern `None` (keine `drossel.py`/`speicher.py`-Dateien angelegt).
- `SetpointProvider` liegt direkt in `controller.py` (v2-Naht, kein Folder).
- Executor-Veto-Kaskade in `executor/dispatcher.py`: Range → Rate-Limit → HA-Call → Readback. Bei Veto wird ein eigener `control_cycles`-Row geschrieben, **kein** `call_service` ausgeführt.
- Persistenter Rate-Limiter via `devices.last_write_at` — Unit-Test mit zwei Connections (simuliert Restart) verifiziert, dass der Lock über Container-Grenzen hinweg greift.
- Fail-Safe-Wrapper im Controller (`_safe_dispatch` + `_write_failsafe_cycle`) fängt Exceptions und `ha_ws_connected == False`; `asyncio.CancelledError` wird explizit re-raised.
- Dispatch läuft via `asyncio.create_task` (Fire-and-Forget), damit der 15–30 s Readback-Wait den HA-Event-Loop nicht blockiert (NFR2). Task-Refs werden getrackt, damit sie beim Shutdown nicht verwaisen.
- Source-Attribution in `_classify_source`: Solalex-Window (2 s nach `state_cache.last_command_at` auf derselben Entity) → `solalex`; `parent_id` gesetzt → `ha_automation`; nur `user_id` gesetzt → `manual`; beide `None` → Default `ha_automation`.
- `main.py`-Integration: `devices_by_entity`-Map + Controller-Hook im `_dispatch_event` (nach `state_cache.update`), HA-Subscriptions für kommissionierte Devices werden nach Auth via Hintergrund-Task `_subscribe_controller_entities` angelegt.
- SQL-Migration 002 mit forward-only `CREATE TABLE IF NOT EXISTS` + Indexes auf `ts DESC` und `device_id`. `ON DELETE CASCADE` auf `device_id` verifiziert via Repo-Test.
- `kpi/__init__.py` ist Noop-Stub mit stabiler Signatur `async def record(cycle: ControlCycleRow) -> None`.
- Bestehender `test_migrate`-Test wurde auf dynamische `_expected_head()` umgestellt, damit er mit jeder weiteren Migration grün bleibt — keine Logik-Änderung, nur Assertions.
- Frontend: keine Änderungen (Backend-only-Story, wie in Scope beschrieben).
- Task-11 Manual-Smoke bleibt offen für Alex' lokalen HA-Run; alle CI-relevanten Gates sind grün.

### File List

**Neu (Backend-Quellcode):**
- `backend/src/solalex/controller.py`
- `backend/src/solalex/executor/dispatcher.py`
- `backend/src/solalex/executor/rate_limiter.py`
- `backend/src/solalex/persistence/repositories/control_cycles.py`
- `backend/src/solalex/persistence/repositories/latency.py`
- `backend/src/solalex/persistence/sql/002_control_cycles_latency.sql`
- `backend/src/solalex/kpi/__init__.py`

**Neu (Backend-Tests):**
- `backend/tests/unit/_controller_helpers.py`
- `backend/tests/unit/test_controller_dispatch.py`
- `backend/tests/unit/test_executor_dispatcher.py`
- `backend/tests/unit/test_executor_rate_limiter.py`
- `backend/tests/unit/test_source_attribution.py`
- `backend/tests/unit/test_control_cycles_repo.py`
- `backend/tests/unit/test_latency_repo.py`
- `backend/tests/unit/test_setpoint_provider.py`

**Modifiziert (Backend):**
- `backend/src/solalex/adapters/base.py` (Default `get_limit_range`)
- `backend/src/solalex/adapters/hoymiles.py` (Override `get_limit_range = (2, 1500)`)
- `backend/src/solalex/adapters/marstek_venus.py` (Override `(0, 2500)`)
- `backend/src/solalex/adapters/shelly_3em.py` (Override → `NotImplementedError`)
- `backend/src/solalex/main.py` (Lifespan, `_dispatch_event`-Controller-Hook, `devices_by_entity`, `_subscribe_controller_entities`)
- `backend/tests/unit/test_migrate.py` (dynamische `_expected_head()`-Assertion)

**Modifiziert (Planning/Status):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (3-1 → in-progress → review)
- `_bmad-output/implementation-artifacts/3-1-…-persistenter-rate-limit.md` (Status + Dev Agent Record + File List)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.1 erstellt und auf `ready-for-dev` gesetzt. Core-Controller-Mono-Modul + Executor-Veto-Kaskade + persistenter Rate-Limiter + Source-Attribution + control_cycles/latency_measurements. Backend-only. | Claude Opus 4.7 |
| 2026-04-23 | 0.2.0 | Story 3.1 implementiert: Controller Mono-Modul mit Enum-Dispatch + SetpointProvider-Naht, Executor-Veto-Kaskade (Range → Rate-Limit → Readback), persistenter Rate-Limiter via `devices.last_write_at` mit Restart-Test, Source-Attribution (solalex/manual/ha_automation), SQL-Migration 002 für `control_cycles` (Ring-Buffer) + `latency_measurements`, KPI-Noop-Stub, main.py-Lifespan-Hook mit `devices_by_entity`-Map. 91 Tests grün, 95 % Coverage auf neuen Files, ruff + mypy strict grün. Status → review. | Claude Opus 4.7 |
