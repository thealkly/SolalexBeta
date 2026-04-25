# Story 3.4: Speicher-Modus — Akku-Lade/-Entlade-Regelung innerhalb SoC-Grenzen

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Marstek-Micha / Beta-Björn mit Marstek-Venus-Akku,
I want dass Solalex bei PV-Überschuss den Akku-Pool lädt und bei Grundlast aus dem Pool entlädt — respektierend Min-SoC / Max-SoC,
so that mein Strom im Haus bleibt und die Akku-Gesundheit nicht durch Tiefentladung oder Überladung leidet.

**Scope-Pflock:** Diese Story ersetzt `_policy_speicher_stub` in [controller.py](../../backend/src/solalex/controller.py) durch eine **produktive reaktive Lade-/Entlade-Logik** für den `Mode.SPEICHER`-Branch, die den **bereits gebauten** [`BatteryPool`](../../backend/src/solalex/battery_pool.py) aus Story 3.3 konsumiert. Sie berührt weder Drossel- (3.2) noch Multi-Modus (3.5) noch den Mode-Selector (3.5) noch den Fail-Safe-Wrapper (3.7 ergänzt ihn). Alle Safety-Gates (Range → Rate-Limit → Readback) laufen **unverändert** durch den Executor aus Story 3.1, jetzt aber **parallel pro Pool-Member** (jeder Member ein eigener Dispatch-Task mit eigenem Per-Device-Lock).

**Amendment 2026-04-22 (verbindlich):** Speicher-Parameter (Deadband, Smoothing-Fenster, Min-Step, Step-Clamp, Toleranz ±30 W) leben als **Python-Konstanten im Adapter-Modul** (`adapters/marstek_venus.py`) — **keine JSON-Templates, kein `/data/templates/`-Verzeichnis, kein JSON-Schema-Validator** (CLAUDE.md Regel 2, [architecture.md Amendment-Log Cut 11/16](../planning-artifacts/architecture.md)). Die Epic-AC-Formulierung „aus Template" ist pre-Amendment und wird durch „aus Adapter-Modul-Konstanten" realisiert.

**Scope-Tension Modus-Wechsel-Flag (aufgelöst):** Epic-AC 3 verlangt, dass „Modus-Wechsel zu Drossel **geflaggt** wird" wenn der Pool Max-SoC erreicht — der **tatsächliche** Mode-Switch mit 97/93 %-Hysterese ist explizit Story 3.5 (Adaptive Strategie). 3.4 implementiert den **Hard-Cap** (Lade-Setpoint = 0 W) plus einen ein-Zeilen-Info-Log `speicher_mode_at_max_soc` als Audit-Spur — **keine** `controller.set_mode(Mode.DROSSEL)`-Aufrufe aus der Policy.

**Scope-Tension Multi-Member-Dispatch (aufgelöst):** Drossel produziert **eine** `PolicyDecision`; Pool produziert **N** Decisions (eine pro Online-Member). Die Signatur von `_dispatch_by_mode` ändert sich von `PolicyDecision | None` zu `list[PolicyDecision]` — Drossel wraps seinen Einzelfall (`[decision]` oder `[]`), Speicher ruft `pool.set_setpoint(...)` direkt durch. Jede Decision spawnt einen eigenen `_safe_dispatch`-Task — Per-Device-Lock aus 3.1 stellt Mutual-Exclusion pro `device_id` sicher; verschiedene Members laufen parallel, derselbe Member serialisiert.

## Acceptance Criteria

1. **Speicher-Lade-Reaktion auf Einspeisung (FR15, Epic-AC 1):** `Given` der Controller läuft im `Mode.SPEICHER` mit je einem kommissionierten Device in Rolle `grid_meter` (Shelly 3EM) und einem `wr_charge` + `battery_soc` Marstek-Venus-Paar, **And** `app.state.battery_pool` ist nicht `None` und enthält ≥ 1 Online-Member, `When` ein `state_changed`-Event auf der `grid_meter`-Entity einen geglätteten Wert < 0 W meldet (Einspeisung nach Shelly-Konvention `parse_readback`: positiv = Bezug, negativ = Einspeisung), `Then` berechnet `_policy_speicher` einen Pool-Lade-Setpoint `+watts > 0` (cancelt die Einspeisung in den Akku), delegiert an `pool.set_setpoint(+watts, state_cache)` und gibt **N `PolicyDecision`-Objekte** mit `command_kind='set_charge'`, `mode=Mode.SPEICHER`, `target_value_w > 0` zurück (eine pro Online-Member, gleichverteilt), **And** der Executor dispatched jeden via `marstek_venus.build_set_charge_command(...)` parallel (eigener `asyncio.Lock` pro `device_id` aus Story 3.1), **And** für jeden eine `control_cycles`-Zeile mit `mode='speicher'`, `source='solalex'`, `readback_status in ('passed','failed','timeout')`, `target_value_w=<share>`, `sensor_value_w=<smoothed>` wird via Executor geschrieben.

2. **Speicher-Entlade-Reaktion auf Grundlast (FR15, Epic-AC 2):** `Given` `Mode.SPEICHER` ist aktiv, der Pool-SoC liegt **strikt über Min-SoC** (Default 15 %), `When` der geglättete Smart-Meter-Wert > 0 W meldet (Bezug = Grundlast), `Then` berechnet `_policy_speicher` einen Pool-Entlade-Setpoint `-watts < 0` (Betrag = geglätteter Bezug, gecappt durch `limit_step_clamp_w` und Hardware-Range), delegiert an `pool.set_setpoint(-watts, state_cache)` und gibt **N `PolicyDecision`-Objekte** mit `target_value_w < 0` zurück (negative Werte = Entlade), **And** der Executor dispatched die Entlade-Befehle exakt wie Lade-Befehle — Range-Check passiert die negative Spanne **NUR**, wenn der Marstek-Venus-Adapter `get_limit_range = (-2500, 2500)` liefert (siehe AC 13).

3. **Hard-Cap bei Max-SoC (Epic-AC 3, FR15 Akku-Schutz):** `Given` Speicher-Modus ist aktiv und der **kapazitätsgewichtete Pool-SoC** (`pool.get_soc(state_cache).aggregated_pct`) **≥ Max-SoC** (Default 95 %, lesbar aus `wr_charge.config().get('max_soc')`), `When` ein Lade-Setpoint berechnet würde (Smoothed < 0, Einspeisung), `Then` liefert `_policy_speicher` `[]` zurück — **kein** Lade-Befehl, **kein** `pool.set_setpoint`-Call, **And** ein einmaliger Info-Log `speicher_mode_at_max_soc` mit `extra={'aggregated_pct': float, 'max_soc': int}` wird geschrieben (kein Spam: Log greift nur, wenn der vorherige Cycle nicht bereits gecappt war — Tracking via `controller._speicher_max_soc_capped: bool`-Flag, das beim Verlassen des Max-Bands resettet), **And** ein **Mode-Switch zu Drossel passiert NICHT** in 3.4 — das ist Story 3.5 mit 97/93 %-Hysterese; das Flag ist nur ein Audit-Trail.

4. **Hard-Cap bei Min-SoC (Epic-AC 4):** `Given` Speicher-Modus ist aktiv und der Pool-SoC **≤ Min-SoC** (Default 15 %, lesbar aus `wr_charge.config().get('min_soc')`), `When` ein Entlade-Setpoint berechnet würde (Smoothed > 0, Bezug), `Then` liefert `_policy_speicher` `[]` zurück — **kein** Entlade-Befehl, **And** Netz-Bezug wird zugelassen (Solalex tut nichts, der Bezug läuft über das Hausnetz), **And** ein einmaliger Info-Log `speicher_mode_at_min_soc` mit `extra={'aggregated_pct': float, 'min_soc': int}` wird geschrieben (analoges Flag-Tracking).

5. **Toleranz ±30 W Marstek-Venus (Epic-AC 5, PRD Zeile 392 Beta-Gate):** `Given` der geglättete Smart-Meter-Wert liegt im Bereich `[-SPEICHER_DEADBAND_W, +SPEICHER_DEADBAND_W]` (Marstek-Default: 30 W), **And** das berechnete Pool-Setpoint-Delta gegenüber dem zuletzt gesendeten Wert wäre kleiner als `SPEICHER_MIN_STEP_W` (Default 20 W), `When` ein Sensor-Event eintrifft, `Then` liefert `_policy_speicher` `[]` zurück — kein Dispatch — **And** der Unit-Test `test_speicher_marstek_tolerance` verifiziert das Verhalten für eine Sinus-Last-Simulation im ±25 W-Bereich.

6. **Rate-Limit-Respekt pro Member (Epic-AC 6, inherited aus 3.1 Executor):** `Given` der Marstek-Venus-Adapter definiert `RateLimitPolicy(min_interval_s=60.0)`, `When` `_policy_speicher` mehrere `PolicyDecision`s an mehreren Members in schneller Folge produziert, `Then` produziert sie **trotzdem** die `PolicyDecision`-Liste (Policy ist nicht für Rate-Limiting zuständig), **aber** der Executor schreibt **pro Member** eine `control_cycles`-Zeile mit `readback_status='vetoed'` und `reason` beginnt mit `'rate_limit: …'`, wenn der Member innerhalb seiner 60-s-Sperre erneut angefragt wird — exakt das Verhalten aus Story 3.1, hier nur als Multi-Member-Regression gesichert. `test_controller_speicher_policy.py::test_rate_limit_veto_per_member` verifiziert die End-to-End-Kette für einen 2-Member-Pool, bei dem nur **ein** Member innerhalb seiner Sperre ist.

7. **Pool-Konsum durch Controller-Konstruktor:** `Given` die `Controller(...)`-Konstruktion in [`main.py::lifespan`](../../backend/src/solalex/main.py), `When` der Pool gebaut und an `app.state.battery_pool` angehängt wurde (Story 3.3), `Then` wird `Controller(...)` **mit dem neuen Parameter** `battery_pool: BatteryPool | None = None` instanziiert (Default-`None` für Test-Backwards-Kompatibilität — bestehende 3.1/3.2-Tests, die ohne Pool laufen, bleiben grün), **And** `_policy_speicher` greift auf `self._battery_pool` zu — ohne Pool (`is None` ODER `members == ()`) liefert die Policy `[]` (Konfiguration unvollständig, Pool nicht commissioniert).

8. **Multi-Member-Dispatch in `_dispatch_by_mode`-Signatur (Multi-Decision-Refactor):** `Given` 3.4 muss N Decisions parallel dispatchen, `When` die Methoden-Signaturen angepasst werden, `Then` ändert sich `Controller._dispatch_by_mode(...) -> list[PolicyDecision]` (statt `PolicyDecision | None`), **And** der Drossel-Branch wraps seinen Einzelfall in `[decision]` (oder `[]` für `None`), **And** `on_sensor_update` iteriert über die Liste: für jede Decision spawnt es einen eigenen `asyncio.create_task(self._safe_dispatch(decision, pipeline_ms))`-Task mit `name=f"controller_dispatch_{device.id}"`, **And** wenn die Liste `[]` ist UND `source != 'solalex'`, wird der bestehende `_record_noop_cycle`-Pfad **unverändert** ausgeführt (genau **einmal**, nicht pro virtuellem Member), **And** `_dispatch_tasks` enthält bei einem 2-Member-Pool-Speicher-Zyklus 2 Tasks, die unabhängig completen.

9. **Per-Device-Lock pro Member (Story 3.1 AC 7-Pattern):** `Given` ein Pool mit N=2 Members und parallelen Decisions aus einem Sensor-Event, `When` `_safe_dispatch` für jede Decision aufgerufen wird, `Then` greift `self._lock_for(decision.device)` auf das **per-`device_id`-Lock-Dict** zu (`self._device_locks` aus 3.1) — verschiedene Members nutzen verschiedene Locks und laufen parallel, derselbe Member serialisiert über aufeinanderfolgende Sensor-Events, **And** der Test `test_speicher_dispatch_locks_per_member` baut zwei Decisions, mockt `executor.dispatcher.dispatch` mit einem `asyncio.Event`-Sync und asserted, dass beide Decisions ihre `dispatch`-Calls **gleichzeitig** in-flight haben (kein serielles Lock auf Pool-Ebene).

10. **Pipeline-Latenz ≤ 1 s (3.1-Invariante, FR31/NFR2):** `Given` ein Speicher-Dispatch-Zyklus, `When` er läuft, `Then` bleibt `cycle_duration_ms` in **jeder** `control_cycles`-Zeile **unter 1000 ms** für den reinen Policy-Pfad (Pool-Builder ist synchron, `set_setpoint` < 1 ms, `get_soc` < 1 ms), **And** Readback-Wartezeit (bis 30 s für Marstek) ist vom Pipeline-Zeitmessungs-Fenster ausgeschlossen, weil `_safe_dispatch` per `asyncio.create_task` aus 3.1 fire-and-forget läuft. (Der Test misst die Policy-Berechnungs-Dauer isoliert.)

11. **Fail-Safe greift unverändert (FR18, Story 3.1 AC 9, Story 3.2 AC 11-Regression):** `Given` Speicher-Modus produziert N Decisions, `When` für **eine** der Decisions `ha_ws_connected_fn()` `False` liefert ODER `ha_client.call_service` eine Exception wirft, `Then` greift `_safe_dispatch` aus Story 3.1 unverändert: `control_cycles` mit `readback_status='vetoed'`, `reason` beginnt mit `'fail_safe: …'`, **keine** `devices.last_write_at`-Aktualisierung für den betroffenen Member, **keine** propagierte Exception — die anderen Member-Decisions in derselben Liste werden unabhängig dispatched (ein fehlgeschlagener Member bricht den Pool nicht), **And** der Test `test_speicher_failsafe_per_member` baut 2 Decisions, lässt eine `call_service` werfen und verifiziert: 1× vetoed-Cycle + 1× erfolgreicher-Cycle.

12. **Source-Attribution bleibt korrekt (Story 3.1 AC 5):** `Given` ein Solalex-getriebener Speicher-Zyklus schreibt N Decisions parallel, `When` die N Readback-Events auf den Charge-Entities ankommen, `Then` erkennt `_classify_source` jedes Event als `'solalex'` (innerhalb des 2-s-Solalex-Fensters aus 3.1) — der Cache-Schreib-Zeitpunkt `last_command_at` wird **nur einmal pro Sensor-Event** (im ersten erfolgreichen `dispatch`) gesetzt; folgende `set_last_command_at(now)`-Calls (selber `now` im selben Zyklus) sind idempotent, **And** es entsteht **kein** zusätzlicher Noop-Attribution-Zyklus für die eigenen Writes — 3.1-Invariante bleibt.

13. **Marstek-Venus-Range erweitert auf signed (Lade + Entlade):** `Given` die heutige `MarstekVenusAdapter.get_limit_range = (0, 2500)` (Lade-only), `When` Speicher-Modus auch entlädt, `Then` wird die Range auf **`(-2500, 2500)`** erweitert (negative = Entlade, positive = Lade), **And** der Adapter-Kommentar dokumentiert die Sign-Konvention: „negative watts = discharge, positive = charge — Marstek-Venus-Charge-Power-Entity akzeptiert beide Vorzeichen via `number.set_value`", **And** der Test `test_marstek_venus_range_signed` verifiziert `(-2500, 2500)`, **And** `Hoymiles.get_limit_range = (2, 1500)` bleibt unverändert (WR-only, keine Entlade-Semantik).

14. **Speicher-Parameter im Adapter-Modul (CLAUDE.md Regel 2):** `Given` die Speicher-Parameter (`SPEICHER_DEADBAND_W=30`, `SPEICHER_MIN_STEP_W=20`, `SPEICHER_SMOOTHING_WINDOW=5`, `SPEICHER_LIMIT_STEP_CLAMP_W=500`), `When` die Policy sie liest, `Then` stammen sie aus `adapters/base.py::SpeicherParams` (Dataclass, default-werte konservativ) plus `marstek_venus.get_speicher_params()`-Override (Marstek-Werte), **And** es existiert **keine** `/data/templates/`-Datei, **kein** JSON-Schema-Validator, **kein** dynamischer Template-Loader, **And** `marstek_venus.py` dokumentiert jeden Parameter mit einer Code-Kommentar-Zeile (Hardware-Spec bzw. empirisch).

15. **Min-SoC / Max-SoC aus `wr_charge.config_json` (FR22, Vorbereitung Story 3.6):** `Given` der Wizard 2.1 persistiert `min_soc` und `max_soc` (Defaults 15/95) im `config_json`-Blob des `wr_charge`-Devices (siehe [`api/routes/devices.py:78-95`](../../backend/src/solalex/api/routes/devices.py)), `When` `_policy_speicher` die SoC-Grenzen liest, `Then` liest sie aus dem **ersten** `wr_charge`-Device im Pool (`pool.members[0].charge_device.config()`) — **NICHT** aus jedem Member einzeln (in v1 sind alle Members vom selben Vendor mit gleicher Konfiguration; v1.5 wird per-Member-Konfiguration nachziehen, dann gilt der konservativste Wert: `max_soc = min(member_max)`, `min_soc = max(member_min)`), **And** Defaults bei fehlendem Key: `min_soc=15`, `max_soc=95` (PRD-Default-Spec, identisch zu `HardwareConfigRequest.Field`-Defaults), **And** Validation: `min_soc < max_soc` ist Wizard-garantiert (Pydantic `model_validator` in [`api/schemas/devices.py:24-29`](../../backend/src/solalex/api/schemas/devices.py)) — die Policy **vertraut** dem Wizard und macht **keinen** zusätzlichen Range-Check (dead-code defense würde nur log-spam produzieren).

16. **Mode-Gate (Story 3.5 Vorbereitung):** `Given` der Controller läuft in `Mode.DROSSEL` oder `Mode.MULTI`, `When` ein Sensor-Event eintrifft, `Then` wird `_policy_speicher` gar **nicht** aufgerufen (der `match`-Block in `_dispatch_by_mode` bleibt der Dispatch-Punkt; 3.4 befüllt nur den `Mode.SPEICHER`-Branch). `test_controller_speicher_policy.py::test_not_invoked_in_drossel_mode` verifiziert, dass keine Speicher-Logik greift, wenn `controller.set_mode(Mode.DROSSEL)` aktiv ist.

17. **Policy läuft nur auf `grid_meter`-Events, nicht auf `wr_charge`/`battery_soc`-Readback-Events:** `Given` ein `state_changed`-Event trifft auf einer `wr_charge`- oder `battery_soc`-Entity ein (z. B. weil HA den Marstek-State aktualisiert hat), `When` der Controller den Event verarbeitet, `Then` liefert `_policy_speicher` `[]` — die Source-Attribution aus Story 3.1 (AC 5) greift weiterhin und schreibt ggf. einen Noop-Zyklus mit `source='manual'` oder `source='ha_automation'`, **And** es wird **kein** `call_service` ausgelöst.

18. **Moving-Average pro `grid_meter` (kein Persist):** `Given` das Smoothing-Fenster (`SPEICHER_SMOOTHING_WINDOW=5`), `When` Solalex neu startet, `Then` beginnt die Policy mit einem leeren Fenster (kein Persistieren der letzten N Sensor-Samples in der DB), **And** der Speicher-Buffer ist **logisch separat** vom Drossel-Buffer (`self._speicher_buffers: dict[int, deque[float]]`) — ein Mode-Wechsel (Story 3.5) clearet den alten Buffer nicht, weil beide Buffer nebeneinander existieren und nur durch Mode-Dispatch aktiviert werden. `test_controller_speicher_policy.py::test_smoothing_buffer_in_memory_separate_from_drossel` sichert, dass keine DB-Writes für den Ring-Buffer entstehen UND dass Drossel- und Speicher-Buffer disjoint sind.

19. **Pipeline-Reference-Flow (Speicher-Pfad):**
    ```
    HA state_changed event (Shelly 3EM: sensor.<...>_total_power)
      ↓ _dispatch_event in main.py                                  [unverändert aus 3.1]
      ↓ state_cache.update(entity_id, ...)                          [unverändert]
      ↓ device = devices_by_entity.get(entity_id)  → grid_meter
      ↓ controller.on_sensor_update(msg, device)
      ↓   ├─ test_in_progress? → return
      ↓   ├─ source = _classify_source(msg)
      ↓   ├─ sensor_w = _extract_sensor_w(msg)
      ↓   ├─ mode = self._current_mode == SPEICHER
      ↓   ├─ decisions = self._dispatch_by_mode(SPEICHER, device, sensor_w)
      ↓   │   ↓ case SPEICHER: return _policy_speicher(device, sensor_w)  [3.4 NEW BODY]
      ↓   │   │   ├─ if device.role != 'grid_meter': return []
      ↓   │   │   ├─ if sensor_w is None or not finite: return []
      ↓   │   │   ├─ if self._battery_pool is None or not pool.members: return []
      ↓   │   │   ├─ params = adapter[charge.adapter_key].get_speicher_params(charge_device)
      ↓   │   │   ├─ buffer.append(sensor_w); smoothed = mean(buffer)
      ↓   │   │   ├─ if abs(smoothed) <= deadband_w: return []
      ↓   │   │   ├─ soc_breakdown = pool.get_soc(state_cache); soc = breakdown.aggregated_pct
      ↓   │   │   ├─ if smoothed < 0 (Einspeisung) and soc >= max_soc: log, return []
      ↓   │   │   ├─ if smoothed > 0 (Bezug) and soc <= min_soc: log, return []
      ↓   │   │   ├─ proposed = -int(round(smoothed))   # negate sign: charge on excess
      ↓   │   │   ├─ proposed = _clamp_step(0, proposed, params.limit_step_clamp_w)
      ↓   │   │   ├─ if abs(proposed - last_dispatched_w) < params.min_step_w: return []
      ↓   │   │   └─ return pool.set_setpoint(proposed, state_cache)   # list[PolicyDecision]
      ↓   ├─ if not decisions and source != 'solalex' → noop-attribution-cycle (1× pro Event)
      ↓   └─ for d in decisions: asyncio.create_task(self._safe_dispatch(d, t0))
      ↓        ↓ _safe_dispatch wraps exception + fail-safe (3.1)
      ↓        ↓ executor.dispatcher.dispatch(d, ctx)
      ↓            ├─ Range-Check Marstek (-2500, 2500) W              [3.4 widened]
      ↓            ├─ Rate-Limit per device (min_interval_s=60)         [3.1]
      ↓            ├─ build_set_charge_command                          [3.1, 2.2]
      ↓            ├─ ha_client.call_service('number','set_value',{...})
      ↓            ├─ verify_readback(...)                              [3.1]
      ↓            ├─ control_cycles.insert + devices.last_write_at     [3.1]
      ↓            └─ latency.insert (if passed)                        [3.1]
    ```
    **Einziger neuer Code lebt im Block `[3.4 NEW BODY]` plus die Refactors in AC 7 + 8 + 13 + 14.** Alles drumherum steht und ist in 3.1/3.2/3.3 getestet.

20. **Sign-Konvention Setpoint (verbindlich):** `Given` der Smart-Meter (Shelly 3EM) liefert `parse_readback`: positiv = **Bezug**, negativ = **Einspeisung**, **And** der Marstek-Venus-Charge-Entity akzeptiert positive = **Lade**, negative = **Entlade**, `When` `_policy_speicher` rechnet, `Then` ist die Konvention: `proposed_setpoint_w = -smoothed_grid_w` (Vorzeichen-Negation). **Beispiel:** Smart-Meter zeigt −500 W (Einspeisung 500 W) → `proposed = +500 W` (Akku lädt mit 500 W) → Bilanz: Einspeisung wird in Akku geleitet, Netz-Saldo → 0. **Beispiel 2:** Smart-Meter zeigt +200 W (Bezug 200 W) → `proposed = -200 W` (Akku entlädt 200 W) → Bilanz: Akku deckt Grundlast, Netz-Saldo → 0. Die Pool-Verteilung in `pool.set_setpoint(proposed, ...)` macht Integer-Division mit Rest-Rotation (Story 3.3 AC 2) — sign-symmetric (`divmod(-1001, 2) == (-501, 1)` ⇒ `[-501, -500]`).

21. **Keine SQL-Migration, keine API-Schema-Änderung, keine Frontend-Änderung:** `Given` der Scope-Pflock, `When` der Diff gemessen wird, `Then` existiert **keine** neue Datei unter `backend/src/solalex/persistence/sql/` (Ordering bleibt bei 2 Dateien: `001_initial.sql` + `002_control_cycles_latency.sql`), **keine** Änderung an `persistence/repositories/devices.py`, `api/routes/*.py` oder `api/schemas/*.py` (Min-/Max-SoC sind bereits aus 2.1 persistiert), **keine** Änderung unter `frontend/src/` (Pool-Anzeige + Modus-Animation sind Epic-5-Scope), **And** `pyproject.toml` bleibt unverändert (keine neue Dependency — Speicher nutzt stdlib `dataclasses`/`collections.deque` plus die bestehenden Domain-Typen).

22. **Unit-Tests (Pytest, MyPy strict, Ruff):** Neue Test-Dateien unter `backend/tests/unit/`:
    - `test_controller_speicher_policy.py`:
      - `test_speicher_charges_on_feed_in_pool_of_one` (AC 1)
      - `test_speicher_charges_on_feed_in_pool_of_two_split_evenly` (AC 1, AC 8 — Multi-Decision)
      - `test_speicher_discharges_on_load_above_grundlast` (AC 2)
      - `test_speicher_hard_cap_at_max_soc_no_charge` (AC 3)
      - `test_speicher_hard_cap_at_min_soc_no_discharge` (AC 4)
      - `test_speicher_max_soc_log_fires_only_once_until_band_exit` (AC 3 — Flag-Tracking)
      - `test_speicher_min_soc_log_fires_only_once_until_band_exit` (AC 4 — Flag-Tracking)
      - `test_speicher_deadband_suppresses_dispatch` (AC 5 — ±30 W)
      - `test_speicher_min_step_suppresses_dispatch_after_first_send` (AC 5 — Min-Step gegen letzten gesendeten Wert)
      - `test_speicher_returns_empty_when_pool_is_none` (AC 7 — keine Pool-Konfiguration)
      - `test_speicher_returns_empty_when_pool_has_no_online_members` (AC 7 — alle Members offline)
      - `test_dispatch_by_mode_returns_list_for_drossel_branch` (AC 8 — Drossel wraps in list)
      - `test_speicher_dispatch_locks_per_member` (AC 9 — parallele Dispatches)
      - `test_speicher_failsafe_per_member` (AC 11 — eine Decision wirft, andere completen)
      - `test_speicher_rate_limit_veto_per_member` (AC 6 — pro-Member-Rate-Limit-Veto)
      - `test_not_invoked_in_drossel_mode` (AC 16)
      - `test_speicher_noop_for_battery_soc_events` (AC 17)
      - `test_speicher_noop_for_wr_charge_events` (AC 17)
      - `test_smoothing_buffer_in_memory_separate_from_drossel` (AC 18)
      - `test_speicher_uses_min_max_soc_from_first_wr_charge_config_json` (AC 15)
      - `test_speicher_min_max_soc_defaults_when_config_json_empty` (AC 15)
      - `test_speicher_sign_convention_feed_in_yields_positive_setpoint` (AC 20)
      - `test_speicher_sign_convention_load_yields_negative_setpoint` (AC 20)
      - `test_speicher_only_one_noop_attribution_cycle_per_event` (AC 8 — Noop nicht pro virtuellem Member)
    - `test_marstek_venus_speicher_params.py`:
      - `test_marstek_adapter_exposes_speicher_params` — Marstek liefert via `get_speicher_params()` die Defaults `(30, 20, 5, 500)`.
      - `test_speicher_marstek_tolerance` (AC 5 — Sinus-Last im ±25 W-Bereich, kein Dispatch)
      - `test_marstek_venus_range_signed` (AC 13 — `(-2500, 2500)`)
      - `test_adapter_base_speicher_params_default` — Base-Default existiert (konservativ, gleiche Werte oder strenger).
      - `test_hoymiles_inherits_speicher_params_default` — Hoymiles erbt Default ohne Override (Hoymiles ist kein Speicher; defensive Reach-Test).
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf allen Änderungen in `controller.py` (Speicher-Policy + Multi-Decision-Dispatch + Flag-Tracking) und `adapters/marstek_venus.py` (Speicher-Params + Range-Erweiterung) plus `adapters/base.py` (`SpeicherParams`-Dataclass).
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (unverändert bei 2 Dateien — **keine neue Migration in 3.4**).

## Tasks / Subtasks

- [x] **Task 1: `AdapterBase.get_speicher_params()` + `SpeicherParams` Dataclass** (AC: 14)
  - [x] `adapters/base.py` um `@dataclass(frozen=True) class SpeicherParams` erweitern, analog zu `DrosselParams`:
    - `deadband_w: int` — Breite des Null-Bands, innerhalb dessen nicht dispatched wird (Marstek: 30 W).
    - `min_step_w: int` — minimale Delta zwischen letztem dispatched Setpoint und neuem (Marstek: 20 W). Gegen Akku-Schreibrauschen.
    - `smoothing_window: int` — Anzahl Sensor-Samples im Moving Average (Default 5).
    - `limit_step_clamp_w: int` — maximal erlaubte Änderung pro Dispatch (gegen Schock-Lade-Sprünge; Marstek: 500 W).
  - [x] `__post_init__`-Validation analog zu `DrosselParams` (Story 3.2 Review P6/P7-Pattern):
    - `deadband_w >= 0`, sonst `ValueError`.
    - `min_step_w >= 1`, `smoothing_window >= 1`, `limit_step_clamp_w >= 1`, sonst `ValueError`.
  - [x] `AdapterBase.get_speicher_params(self, device) -> SpeicherParams`-Default. Konservative Werte: `SpeicherParams(deadband_w=30, min_step_w=20, smoothing_window=5, limit_step_clamp_w=500)`.
  - [x] **Kein `NotImplementedError`** im Default (Lessons aus 3.2/3.3 — defensive Defaults verhindern Fail-Loud im falschen Moment). Hoymiles erbt Default ohne Override (Hoymiles ist kein Speicher-Target — Default ist toter-Code-Proof).

- [x] **Task 2: Marstek-Venus-Adapter — `get_speicher_params` + Range-Erweiterung** (AC: 13, 14)
  - [x] `adapters/marstek_venus.py`: `get_speicher_params(device) -> SpeicherParams` überschreiben mit:
    - `deadband_w=30` (Architecture/PRD Zeile 392 + 392, „Marstek Venus ±30 W lokale-API-Latenz-abhängig")
    - `min_step_w=20` (empirisch — unter 20 W ist Marstek-Charge-Power-Schreibrauschen, BMS-Mikro-Adjustments)
    - `smoothing_window=5` (Balance zwischen Reaktivität und Rausch-Unterdrückung; 5 × 1-s-Polling ≈ 5 s Glättung — gleich wie Hoymiles, weil Smart-Meter-Stream identisch ist)
    - `limit_step_clamp_w=500` (verhindert Schock-Lade-Übergänge bei Lastsprung; Akku-Charge-Power kann technisch bis 2500 W springen, aber 500 W/Zyklus ist hardware-schonend)
  - [x] Pro Feld ein One-Liner-Kommentar mit Quelle.
  - [x] **Range-Erweiterung:** `get_limit_range(device) -> tuple[int, int]` ändern von `(0, 2500)` auf `(-2500, 2500)`.
  - [x] Code-Kommentar oben am `get_limit_range`: „negative watts = discharge, positive = charge — Marstek Venus charge-power entity accepts both signs via `number.set_value`. Range from datasheet (3E variant: 2500 W charge / 2500 W discharge)."
  - [x] **TODO-Kommentar entfernen** in `get_limit_range` (`TODO(3.4): pull the actual cap from device.config once the Speicher story exposes it.`) — die Story passiert hier, Cap-Override per `device.config_json.charge_power_cap_w` ist v1.5-Scope (nicht 3.4).
  - [x] **Keine** JSON-Datei, **kein** `load_from_template()`-Call, **kein** externes File-Laden.

- [x] **Task 3: Hoymiles + Shelly — keine Overrides** (AC: 14)
  - [x] `adapters/hoymiles.py`: `get_speicher_params` **nicht** überschreiben — erbt Default. Hoymiles-Adapter wird nie als `wr_charge`-Role angefragt; Default ist toter-Code-Proof.
  - [x] `adapters/shelly_3em.py`: `get_speicher_params` **nicht** überschreiben — Default. Smart-Meter ist kein Schreib-Target; Policy fragt den `wr_charge`-Adapter, nicht den `grid_meter`.

- [x] **Task 4: `controller.py` — `_dispatch_by_mode`-Signatur ändern + `on_sensor_update`-Iteration** (AC: 8, 12)
  - [x] `_dispatch_by_mode(...)` Signatur: `(self, mode, device, sensor_value_w) -> list[PolicyDecision]` (statt `PolicyDecision | None`).
    ```python
    match mode:
        case Mode.DROSSEL:
            decision = self._policy_drossel(device, sensor_value_w)
            return [decision] if decision is not None else []
        case Mode.SPEICHER:
            return self._policy_speicher(device, sensor_value_w)  # already list
        case Mode.MULTI:
            return _policy_multi_stub(device, sensor_value_w)  # noop returns []
        case _:
            assert_never(mode)
    ```
  - [x] `_policy_multi_stub` muss in der Signatur `list[PolicyDecision]` zurückgeben — pass-through-Update von `return None` auf `return []` (1-Zeilen-Diff). Story 3.5 ersetzt das.
  - [x] `on_sensor_update`:
    ```python
    decisions = self._dispatch_by_mode(self._current_mode, device, sensor_value)
    pipeline_ms = int((time.monotonic() - t0) * 1000)
    if not decisions:
        if source != "solalex":
            await self._record_noop_cycle(...)  # exactly once per event
        return
    for decision in decisions:
        task = asyncio.create_task(
            self._safe_dispatch(decision, pipeline_ms),
            name=f"controller_dispatch_{decision.device.id}",
        )
        self._track_task(task)
    ```
    Wichtig: `pipeline_ms` wird **einmal** berechnet (das ist die synchrone Pipeline-Dauer Sensor → Decision-List); jede Dispatch-Task übernimmt denselben Wert für ihr `cycle_duration_ms`-Feld. (Begründung: Pipeline-Dauer ist die Sensor → Policy-Berechnungs-Strecke, nicht die Per-Member-Dispatch-Strecke; letztere wird vom Executor selbst gemessen, siehe `dispatcher.dispatch` `time.monotonic()`-Reset bei der Cycle-Insertion.)
  - [x] **Update `_classify_source`-Pfad** unverändert. `last_command_at`-Set passiert im Executor `dispatch` (Story 3.1) per Decision; mehrere parallele Decisions setzen denselben `now`-Wert idempotent (AC 12).

- [x] **Task 5: `controller.py` — `_policy_speicher` produktiv + Buffer + Flags** (AC: 1–5, 15, 17, 18, 20)
  - [x] Ersetze `_policy_speicher_stub` durch `Controller._policy_speicher(self, device, sensor_value_w) -> list[PolicyDecision]`.
  - [x] **Konstruktor-Erweiterung:** `Controller.__init__(...)` nimmt `battery_pool: BatteryPool | None = None`. Speichere als `self._battery_pool`. **Default `None`** für Test-Backwards-Kompatibilität (3.1/3.2-Tests, die ohne Pool laufen).
  - [x] Neue Felder am Controller (analog zu `_drossel_buffers` aus 3.2):
    ```python
    self._speicher_buffers: dict[int, deque[float]] = {}
    self._speicher_last_setpoint_w: dict[int, int] = {}  # per-pool (key: pool-id surrogate via id(pool); v1: only one pool)
    self._speicher_max_soc_capped: bool = False
    self._speicher_min_soc_capped: bool = False
    ```
    Begründung `_speicher_last_setpoint_w` als per-pool Dict: in v1 lebt **ein** Pool im Controller; das Dict erlaubt v1.5-Erweiterung auf mehrere Pools (z. B. Marstek + Anker parallel) ohne Refactor. Schlüssel: `id(self._battery_pool)` — `id()` ist stabil über Object-Lifetime.
  - [x] **Early-Returns** in `_policy_speicher` (in dieser Reihenfolge):
    1. `device.role != 'grid_meter'` → `[]` (AC 17).
    2. `sensor_value_w is None or not math.isfinite(sensor_value_w)` → `[]` (defensive; identisch zu Drossel-Pattern).
    3. `self._battery_pool is None or not self._battery_pool.members` → `[]` (AC 7).
    4. `self._battery_pool` hat keinen Online-Member (`pool._online_members(state_cache)` ist leer ODER `pool.set_setpoint(...)` würde `[]` liefern) → `[]`. **Aber:** Wir prüfen den Online-Status nicht doppelt — wir bauen den Setpoint und übergeben an `pool.set_setpoint`; der Pool filtert intern. Wenn der Pool `[]` liefert, geben wir `[]` zurück (AC 7).
  - [x] **Smoothing + Buffer:**
    ```python
    grid_meter_id = device.id
    if grid_meter_id is None:
        return []
    params = self._get_speicher_params_for_pool()
    buf = self._speicher_buffers.get(grid_meter_id)
    if buf is None or buf.maxlen != params.smoothing_window:
        buf = deque(maxlen=params.smoothing_window)
        self._speicher_buffers[grid_meter_id] = buf
    buf.append(sensor_value_w)
    smoothed = sum(buf) / len(buf)
    if abs(smoothed) <= params.deadband_w:
        return []
    ```
    `_get_speicher_params_for_pool()` ruft `self._adapter_registry[charge.adapter_key].get_speicher_params(charge)` für den **ersten** Member-`charge_device` (v1: alle Members vom selben Vendor; AC 15).
  - [x] **SoC-Read + Hard-Cap-Logik:**
    ```python
    soc_breakdown = self._battery_pool.get_soc(state_cache)
    if soc_breakdown is None:
        return []  # No SoC reading available — refuse to charge/discharge blindly.
    aggregated = soc_breakdown.aggregated_pct
    config = self._battery_pool.members[0].charge_device.config()
    max_soc = int(config.get("max_soc", 95))
    min_soc = int(config.get("min_soc", 15))
    
    if smoothed < 0:  # Einspeisung — would charge
        if aggregated >= max_soc:
            if not self._speicher_max_soc_capped:
                _logger.info("speicher_mode_at_max_soc",
                             extra={"aggregated_pct": aggregated, "max_soc": max_soc})
                self._speicher_max_soc_capped = True
            return []
        else:
            self._speicher_max_soc_capped = False  # exit max-band
    
    if smoothed > 0:  # Bezug — would discharge
        if aggregated <= min_soc:
            if not self._speicher_min_soc_capped:
                _logger.info("speicher_mode_at_min_soc",
                             extra={"aggregated_pct": aggregated, "min_soc": min_soc})
                self._speicher_min_soc_capped = True
            return []
        else:
            self._speicher_min_soc_capped = False  # exit min-band
    ```
  - [x] **Setpoint-Berechnung (Sign-Konvention AC 20):**
    ```python
    proposed = -int(round(smoothed))   # Sign-flip: feed-in (negative) → charge (positive)
    proposed = _clamp_step(0, proposed, params.limit_step_clamp_w)
    pool_key = id(self._battery_pool)
    last = self._speicher_last_setpoint_w.get(pool_key, 0)
    if abs(proposed - last) < params.min_step_w:
        return []
    decisions = self._battery_pool.set_setpoint(proposed, self._state_cache)
    if decisions:
        self._speicher_last_setpoint_w[pool_key] = proposed
        # Inject smoothed sensor reading per-decision so the cycle row carries it.
        decisions = [
            PolicyDecision(
                device=d.device,
                target_value_w=d.target_value_w,
                mode=d.mode,
                command_kind=d.command_kind,
                sensor_value_w=smoothed,
            )
            for d in decisions
        ]
    return decisions
    ```
    **Hinweis zum re-build:** `pool.set_setpoint` setzt `sensor_value_w=None` per Default (Pool-Code aus 3.3). Die Speicher-Policy ergänzt den geglätteten Wert pro Decision, damit `control_cycles.sensor_value_w` ausgefüllt ist (NFR-konsistent zu Drossel). Da `PolicyDecision` ein `@dataclass` (mutable) ist, könnten wir auch in-place setzen; wir bauen sie aber neu, damit der Pool-Pfad ein vollständig immutables Pattern bleibt. **Nicht** zu `frozen=True` ändern — der Test in 3.3 erwartet aktuell mutable.
  - [x] **Kein** Hot-Reload des Pools, **kein** Mode-Switch in der Policy, **kein** Logging des Sensor-Werts auf `info`-Level (HA-Event-Rate ist hoch — `debug` für verworfene, `info` nur beim Dispatch).

- [x] **Task 6: `main.py` Integration — `battery_pool` an Controller durchreichen** (AC: 7)
  - [x] [`main.py::lifespan`](../../backend/src/solalex/main.py): nach `battery_pool = BatteryPool.from_devices(...)` (Story 3.3, bereits da) den Pool an `Controller(...)` übergeben:
    ```python
    controller = Controller(
        ha_client=app.state.ha_client.client,
        state_cache=_app_state_cache,
        db_conn_factory=_db_conn_factory,
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: app.state.ha_client.ha_ws_connected,
        devices_by_role=devices_by_role,
        battery_pool=battery_pool,        # 3.4 NEW
        mode=Mode.DROSSEL,
    )
    ```
  - [x] **Keine Default-Mode-Änderung.** `Mode.DROSSEL` bleibt der Startup-Default; Story 3.5 baut die adaptive Auswahl basierend auf erkannter Hardware. Manueller Mode-Switch zur Speicher-Validierung läuft via `controller.set_mode(Mode.SPEICHER)` (heute schon existent in 3.1).
  - [x] **Keine Änderung** an `_dispatch_event` — die Multi-Decision-Iteration passiert **innerhalb** `controller.on_sensor_update`.

- [x] **Task 7: Unit-Tests — Speicher-Policy + Marstek-Speicher-Params** (AC: 22)
  - [x] `backend/tests/unit/test_controller_speicher_policy.py` mit allen 24 Test-Fällen aus AC 22.
  - [x] `backend/tests/unit/test_marstek_venus_speicher_params.py` mit 5 Test-Fällen aus AC 22.
  - [x] Reuse `backend/tests/unit/_controller_helpers.py` (FakeHaClient, In-Memory-DB-Fixture). **Keine** neuen Helper-Dateien ohne Notwendigkeit — falls ein Pool-Builder-Helper hilft, in `_controller_helpers.py` ergänzen (z. B. `build_marstek_pool(member_count: int) -> BatteryPool`).
  - [x] Reuse `_make_state_cache(entries)` aus `test_battery_pool.py` — copy-paste in den neuen Test-File **oder** in `_controller_helpers.py` extrahieren (bevorzugt: extrahieren, um Duplikation zu vermeiden).
  - [x] Tests verwenden `Controller(...)` direkt mit `battery_pool=BatteryPool.from_devices([...], ADAPTERS)` und `devices_by_role={'grid_meter': ..., 'wr_charge': ..., 'battery_soc': ...}`.
  - [x] Coverage-Messung via `pytest --cov=solalex.controller --cov=solalex.adapters.marstek_venus --cov=solalex.adapters.base` muss ≥ 90 % Line-Coverage auf den **in 3.4 geänderten** Abschnitten zeigen.

- [x] **Task 8: Final Verification** (AC: 21, 22)
  - [x] `uv run ruff check .` → grün.
  - [x] `uv run mypy --strict src/ tests/` → grün.
  - [x] `uv run pytest -q` → grün (alle bisherigen Tests + neue Speicher-Tests + 3.3-Pool-Tests).
  - [x] SQL-Ordering: unverändert (`001_initial.sql` + `002_control_cycles_latency.sql`) — **keine neue Migration in 3.4**.
  - [x] Drift-Check 1: `grep -rE "/data/templates|load_json_template|json-schema" backend/src/solalex/` → **0 Treffer** (Amendment 2026-04-22 Cut 11).
  - [x] Drift-Check 2: `grep -rE "drossel\.py$|speicher\.py$|multi\.py$|mode_selector\.py$|pid\.py$|failsafe\.py$" backend/src/solalex/` → **0 Treffer** (Mono-Modul bleibt).
  - [x] Drift-Check 3: `grep -rE "marstek_venus|hoymiles|shelly" backend/src/solalex/controller.py` → **0 Treffer** (Controller bleibt hardware-agnostisch — Adapter-Lookups via `self._adapter_registry`).
  - [x] Drift-Check 4: `grep -rE "marstek_venus|hoymiles|shelly" backend/src/solalex/battery_pool.py` → **0 Treffer** (3.3 AC 5 bleibt gewahrt).
  - [x] Drift-Check 5: `grep -rE "set_mode\(Mode\.\w+\)" backend/src/solalex/controller.py | grep -v test` → **0 Treffer in `_policy_speicher`** (Mode-Switching ist Story 3.5).
  - [x] Manual-Smoke lokal im HA-Add-on (optional, kein Blocker für Review): `controller.set_mode(Mode.SPEICHER)` per Diagnose-Hook (nicht UI), ein Real-Marstek-Setup, beobachten dass Charge bei Einspeisung > 30 W reagiert und Discharge bei Bezug > 30 W. Beta-Gate-Empirie ±30 W läuft empirisch durch Alex; Unit-Tests sichern Policy-Charakteristik.

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Core Architectural Decisions Zeile 229–260](../planning-artifacts/architecture.md) — Controller-Monolith, Direct-Call, Adapter-Modul-Pattern.
- [architecture.md — Amendment 2026-04-22 Cut 9 + 11](../planning-artifacts/architecture.md) — kein Controller-Submodul-Split, kein JSON-Template-Layer.
- [prd.md — FR15 + FR21 + FR22 + FR23](../planning-artifacts/prd.md) — Speicher-Lade/-Entlade, Pool-Gleichverteilung, Min/Max-SoC-Konfiguration, SoC-Aggregat.
- [prd.md — Zeile 348](../planning-artifacts/prd.md) — „Akku-Pool als Architektur-Abstraktion" (USP).
- [prd.md — Zeile 363–367](../planning-artifacts/prd.md) — **Modus-Abgrenzung verbindlich:** „Speicher-Modus: WR-Limit bleibt auf Max, nur bei Akku-Voll → Übergang zu Drossel" — der Mode-Wechsel ist Story 3.5; 3.4 implementiert nur die Speicher-Logik mit Hard-Caps.
- [prd.md — Zeile 392 (Beta-Gate)](../planning-artifacts/prd.md) — „Speicher-Modus stabil ±30 W bei Marstek Venus" — die Empirie-Hälfte des Beta-Gates läuft via Manual-Smoke; 3.4 sichert die Policy-Charakteristik.
- [prd.md — Zeile 396](../planning-artifacts/prd.md) — „Akku-Pool-Fehlverteilung: Fallback-Modus = 1 Hauptspeicher aktiv, andere statisch" — durch Pool-Offline-Filter in 3.3 abgedeckt.
- [prd.md — Zeile 223](../planning-artifacts/prd.md) — v1-Scope „1 WR + 1 SM + 1 Akku pro Instanz" — Multi-Akku ist via Pool-Abstraktion ready, Wizard-Erweiterung v1.5.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — insbesondere Regel 2 (ein Python-Modul pro Adapter, keine JSON-Templates) und Regel 3 (Closed-Loop + Rate-Limit + Fail-Safe).
- [Story 3.1](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — **Pflichtlektüre**: `PolicyDecision`-Dataclass, Per-Device-`asyncio.Lock`, `_safe_dispatch`-Wrapper, `_classify_source`-Window. Die Veto-Kaskade läuft pro Decision unverändert.
- [Story 3.2](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — **Pflichtlektüre**: `DrosselParams.__post_init__`-Invariant-Pattern (Patches P6/P7), `state_cache.last_states`-`isinstance`-Guard (P10), Defensive-Parse-Fehler-Handling (P9), Smoothing-Buffer-Pattern, `_clamp_step`. Speicher übernimmt das Pattern 1:1.
- [Story 3.3](./3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation.md) — **Pflichtlektüre**: `BatteryPool.set_setpoint(watts, state_cache)`, `pool.get_soc(state_cache) -> SocBreakdown | None`, Sign-symmetric-divmod-Verteilung, Offline-Filter. 3.4 konsumiert den Pool unverändert.
- [Story 2.1](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md) — `min_soc`/`max_soc`-Persistenz im `wr_charge.config_json`.
- [Story 2.2](./2-2-funktionstest-mit-readback-commissioning.md) — `commissioned_at`-Filter, Marstek-Charge-Command (`build_set_charge_command`).

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Reine Backend-Story. **Keine Frontend-Änderungen.** Pool-/Modus-Anzeige im Dashboard ist Epic 5 (Story 5.4 Energy-Ring + Story 5.5 Modus-Badge). 3.4 schreibt Daten in `control_cycles` mit `mode='speicher'`; das Frontend liest sie via `/api/v1/control/state` (Story 5.1a Polling-Endpoint, bereits live).

**Mini-Diff-Prinzip:** Der Pull-Request für 3.4 ist **mittlerer Größe** — die Policy ist komplexer als Drossel (zwei Richtungen, SoC-Hard-Caps, Multi-Member-Dispatch), aber alle Foundation-Bausteine (Pool, Executor, Per-Device-Lock, Fail-Safe) sind aus 3.1/3.2/3.3 fertig.

**Erwarteter Diff-Umfang:**
- 1 MOD-Datei: `backend/src/solalex/controller.py` (+ ~120 LOC: `_policy_speicher` ~80 LOC, `_dispatch_by_mode`-Refactor ~10 LOC, `on_sensor_update`-Iteration ~10 LOC, neue Felder + Konstruktor-Parameter ~10 LOC, `_get_speicher_params_for_pool` ~5 LOC).
- 3 MOD-Adapter-Dateien: `adapters/base.py` (+ ~30 LOC für `SpeicherParams` + Default), `adapters/marstek_venus.py` (+ ~20 LOC für Override + Range-Erweiterung), `adapters/hoymiles.py`/`adapters/shelly_3em.py` (unverändert — nur Test-Coverage erbt Default).
- 1 MOD: `main.py` (+ 1 LOC `battery_pool=battery_pool`).
- 2 NEU Test-Dateien: `test_controller_speicher_policy.py` (~600 LOC, 24 Tests), `test_marstek_venus_speicher_params.py` (~80 LOC, 5 Tests).
- Keine SQL-Migration, keine neue Route, keine neue Dependency, keine Frontend-Änderung.

**Dateien, die berührt werden dürfen:**

- **MOD Backend:**
  - `backend/src/solalex/controller.py`
    - `_policy_speicher` echt implementieren (ersetzt `_policy_speicher_stub`).
    - `_policy_speicher_stub` und `_policy_multi_stub` aus dem Modul-Top entfernen ODER beide auf `return []` umstellen (für `_policy_multi_stub` Pflicht; siehe Task 4).
    - `Controller.__init__` nimmt zusätzlich `battery_pool: BatteryPool | None = None`.
    - Neue Felder: `self._battery_pool`, `self._speicher_buffers`, `self._speicher_last_setpoint_w`, `self._speicher_max_soc_capped`, `self._speicher_min_soc_capped`.
    - `_dispatch_by_mode` Signatur auf `list[PolicyDecision]`.
    - `on_sensor_update` iteriert über die Liste.
    - `_get_speicher_params_for_pool()` als private Helper-Methode.
    - Drossel-Branch wraps in `[decision]`/`[]`.
  - `backend/src/solalex/adapters/base.py`
    - `SpeicherParams` Dataclass + `AdapterBase.get_speicher_params(device)` Default.
  - `backend/src/solalex/adapters/marstek_venus.py`
    - `get_speicher_params` Override (Marstek-Defaults).
    - `get_limit_range` von `(0, 2500)` auf `(-2500, 2500)` widen + Sign-Convention-Kommentar.
  - `backend/src/solalex/main.py`
    - 1-Zeilen-Erweiterung `battery_pool=battery_pool` im `Controller(...)`-Call.

- **NEU Backend (Tests):**
  - `backend/tests/unit/test_controller_speicher_policy.py` (~24 Tests)
  - `backend/tests/unit/test_marstek_venus_speicher_params.py` (~5 Tests)

- **NICHT anfassen:**
  - `backend/src/solalex/battery_pool.py` — Pool ist in 3.3 fertig; 3.4 konsumiert nur. Wenn du eine Methode am Pool ergänzen möchtest, **STOP** — die Logik gehört in den Controller.
  - `backend/src/solalex/executor/dispatcher.py` — Veto-Kaskade unverändert. Range-Check funktioniert mit signed range automatisch.
  - `backend/src/solalex/executor/rate_limiter.py` — unverändert. Per-Device-Persistent-Rate-Limit greift pro Member automatisch.
  - `backend/src/solalex/executor/readback.py` — unverändert. Marstek-Readback (sync, 30 s timeout) ist seit 2.2 funktional.
  - `backend/src/solalex/persistence/sql/*.sql` — **keine neue Migration**. `control_cycles`-Schema unterstützt `mode='speicher'` seit 002.
  - `backend/src/solalex/persistence/repositories/control_cycles.py` — unverändert. Insertion akzeptiert `mode='speicher'`.
  - `backend/src/solalex/api/routes/devices.py`, `api/schemas/devices.py` — Min/Max-SoC sind seit 2.1 persistiert.
  - `backend/src/solalex/state_cache.py` — `update_mode('speicher')` greift seit 5.1a.
  - `backend/src/solalex/adapters/hoymiles.py`, `adapters/shelly_3em.py` — erben `SpeicherParams`-Default; **kein** Override notwendig.
  - `frontend/src/**/*` — **nichts**. Pool-/Speicher-Anzeige ist Epic 5.
  - `pyproject.toml` — keine neue Dependency.

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du `controller.py` in `drossel.py` / `speicher.py` / `multi.py` splittest — **STOP**. Mono-Modul mit `match`-Block (Architecture Cut 9, Amendment 2026-04-22).
- Wenn du ein `/data/templates/marstek_speicher.json` oder einen `json-schema`-Validator anlegst — **STOP**. Python-Konstanten im Adapter-Modul (CLAUDE.md Regel 2, Cut 11).
- Wenn du eine neue SQL-Migration anlegst — **STOP**. Speicher-Policy braucht kein neues Schema (Smoothing in-memory, SoC-Caps aus `config_json`, `mode='speicher'` ist seit 002 erlaubt).
- Wenn du `structlog`, `APScheduler`, `cryptography`, `numpy`, `pandas` oder `SQLAlchemy` importierst — **STOP**. Stdlib reicht; CLAUDE.md Stolpersteine.
- Wenn du `asyncio.Queue`, `events/bus.py` oder einen Pub/Sub-Dispatch einbaust — **STOP**. Direct-Call (Architecture Zeile 241).
- Wenn du `executor/dispatcher.py` oder `executor/rate_limiter.py` editierst — **STOP**. 3.1 hat sie fertig; 3.4 ist reine Policy + Multi-Decision-Dispatch.
- Wenn du `battery_pool.py` editierst — **STOP**. Pool ist in 3.3 fertig; ergänze die Logik im Controller.
- Wenn du im Marstek-Adapter eine PID-Regelung, einen Kalman-Filter oder eine Feed-Forward-SoC-Schätzung einbaust — **STOP**. 3.4 ist eine **reaktive** Regelung mit Moving Average — nicht mehr. Forecast-Komponenten sind v2 (via `SetpointProvider`-Naht).
- Wenn du die Speicher-Logik in `adapters/marstek_venus.py` anstatt in `controller.py` einbaust — **STOP**. Die Policy ist Controller-Concern; das Adapter-Modul liefert nur **Parameter** (Deadband, Smoothing, Range) und **Commands** (`build_set_charge_command`), keine Regel-Logik.
- Wenn du `logging.getLogger(...)` statt `get_logger(__name__)` nutzt — **STOP**. CLAUDE.md Regel 5.
- Wenn du den Hysterese-basierten Mode-Wechsel `Mode.SPEICHER ↔ Mode.DROSSEL` (97/93 % Hysterese) einbaust — **STOP**. Das ist Story 3.5 (Adaptive Strategie-Auswahl). 3.4 setzt nur den Hard-Cap (Lade/Entlade = 0) plus ein Audit-Flag-Log.
- Wenn du einen Multi-Modus-Branch (`Mode.MULTI`) befüllst — **STOP**. Das ist Story 3.5. In 3.4 wird `_policy_multi_stub` nur auf `return []` umgestellt (Signatur-Fit).
- Wenn du `_dispatch_event` in `main.py` umbaust — **STOP**. Stabil seit 1.3/2.2/3.1. Multi-Decision-Iteration passiert **innerhalb** `controller.on_sensor_update`.
- Wenn du Min/Max-SoC-User-Config-UI / Nacht-Entlade-Zeitfenster baust — **STOP**. Das ist Story 3.6. 3.4 liest die bereits aus 2.1 persistierten Defaults aus `config_json`.
- Wenn du Anker-Solix-Adapter oder Generic-HA-Adapter-Pfad in 3.4 implementierst — **STOP**. Beide v1.5 (Amendment 2026-04-22).
- Wenn du Policy-Parameter persistierst (z. B. in `meta`-Tabelle) — **STOP**. Parameter sind Code-Konstanten; User-Config kommt erst in Story 3.6.
- Wenn du `battery_pool.set_setpoint` mit `state_cache=None` aufrufst — **STOP**. Pool benötigt den State-Cache für Online-Filter (3.3 AC 4).
- Wenn du `pool.set_setpoint` synchron mit positiven Werten für Entlade aufrufst — **STOP**. Sign-Konvention AC 20: positive = Lade, negative = Entlade.
- Wenn du einen direkten `ha_client.call_service`-Aufruf aus `_policy_speicher` einbaust — **STOP**. Pure-Function-Pattern; immer via `executor.dispatcher.dispatch`.
- Wenn du den Speicher-Buffer mit Drossel-Buffer teilst (gleicher `dict`-Key-Space) — **STOP**. Logisch separat (`self._speicher_buffers` vs. `self._drossel_buffers`); Mode-Wechsel (3.5) clearet den Wechsel-Buffer ggf. — beide existieren parallel ohne Interferenz.
- Wenn du im Controller `marstek_venus`-spezifische Konstanten oder Imports einbaust — **STOP**. Adapter-agnostisch via `self._adapter_registry`-Lookup.

### Architecture Compliance (5 harte Regeln aus CLAUDE.md)

1. **snake_case überall:** Alle neuen Python-Symbole (`_policy_speicher`, `_speicher_buffers`, `_speicher_last_setpoint_w`, `_speicher_max_soc_capped`, `_speicher_min_soc_capped`, `_get_speicher_params_for_pool`, `get_speicher_params`, `speicher_params`) sind `snake_case`. Klassennamen (`SpeicherParams`) sind `PascalCase` (Python-Klassen-Konvention).
2. **Ein Python-Modul pro Adapter:** Marstek-Speicher-Konstanten leben ausschließlich in `adapters/marstek_venus.py`; Range-Erweiterung dort. Controller bleibt hardware-agnostisch (Drift-Check 3 in Task 8).
3. **Closed-Loop-Readback:** Pool produziert `PolicyDecision`-Objekte; Executor enforced Readback für jeden `set_charge`-Call unverändert. Policy umgeht den Executor **nie**.
4. **JSON-Responses ohne Wrapper:** In 3.4 nicht relevant — keine neue Route.
5. **Logging via `get_logger(__name__)`:** Speicher-Policy nutzt `_logger` aus `controller.py` (bereits da). `_logger.info('speicher_mode_at_max_soc', extra=...)` und `_logger.info('speicher_mode_at_min_soc', extra=...)` sind die einzigen produktiven Info-Logs (Flag-getrackt gegen Spam). `debug`-Level für verworfene Decisions (Deadband, Min-Step). Kein `print`, kein `logging.info` direkt.

### Library & Framework Requirements

- **Keine neuen Dependencies.** Speicher nutzt ausschließlich stdlib (`dataclasses`, `collections.deque`, `math`, `typing`).
- **Python 3.13** (aus `pyproject.toml`). `from __future__ import annotations` bleibt Pflicht in jedem neuen File (Projekt-Konvention).
- **Kein numpy/pandas** für Smoothing — `sum(buf)/len(buf)` reicht für N=5.
- **Kein Pydantic-Model** für `SpeicherParams` — `@dataclass(frozen=True)` reicht (Backend-intern, wird nie via API serialisiert).
- **`collections.deque(maxlen=N)`** für Smoothing-Buffer (analog Drossel; thread-safe append/popleft im asyncio-Single-Thread-Modell).

### File Structure Requirements

- **Speicher-Logik im Controller-Modul:** Mono-Modul (Amendment 2026-04-22). **Kein** `controller/speicher.py`-Submodul, **kein** separates `policies/`-Verzeichnis.
- **`SpeicherParams` in `adapters/base.py`:** Analog zu `DrosselParams` — Dataclass + Default in der Adapter-Base, Override im Vendor-Modul.
- **Test-Files spiegeln Source-Pfade:** `tests/unit/test_controller_speicher_policy.py` für die Policy, `tests/unit/test_marstek_venus_speicher_params.py` für den Adapter-Override.

### Testing Requirements

- **Pytest + pytest-asyncio + MyPy strict + Ruff** — alle 4 CI-Gates grün.
- **Coverage ≥ 90 %** auf `_policy_speicher` + Buffer-Logik + Hard-Cap-Branches + `SpeicherParams` + Marstek-Range-Erweiterung. Messung via `pytest --cov=solalex.controller --cov=solalex.adapters.marstek_venus --cov=solalex.adapters.base`.
- **Keine Playwright, kein Vitest** — Speicher ist reines Backend-Python, Frontend-Tests unberührt (AC 21).
- **FakeStateCache + FakeHaClient** statt realer DB/HA-Connection für die Policy-Tests. Für die Multi-Decision-Tests (AC 8, AC 9) wird die vorhandene In-Memory-DB-Fixture aus `_controller_helpers.py` reused — keine neuen Fixtures.
- **Property-Style-Tests gibt es im Pool aus 3.3 schon.** 3.4 fokussiert auf **Branching-Coverage** der Policy: Deadband, Min-Step, Hard-Cap-Max, Hard-Cap-Min, Multi-Member, Pool-None, Pool-Empty, Sign-Konvention.
- **Deterministische Lock-Tests (AC 9):** `test_speicher_dispatch_locks_per_member` mockt `executor.dispatcher.dispatch` mit `asyncio.Event`-Hold + Release-Pattern. Beide Members blocken am Event; nach Release laufen beide simultan complete. Asserted: beide Decisions hatten den `dispatch`-Call concurrent (nicht sequenziell).

### Previous Story Intelligence (3.3, 3.2, 3.1, 2.1, 2.2)

**Aus Story 3.3 (jüngste, höchste Relevanz — Pool ist hier konsumiert):**

- **Pool-API-Vertrag fix:** `pool.set_setpoint(watts: int, state_cache: StateCache) -> list[PolicyDecision]` — synchron, IO-frei, gibt `[]` bei All-Offline. **Übertrag:** 3.4 ruft direkt durch; kein State-Cache-Doppellesen, kein Online-Member-Pre-Filter.
- **Pool-`get_soc(state_cache) -> SocBreakdown | None`:** Kapazitätsgewichtet, mit `per_member`-Map. **Übertrag:** 3.4 nutzt `aggregated_pct`; Per-Member-SoC ist nicht für die Policy relevant (v1: gleichverteilt; v2: SoC-Balance).
- **`get_soc` liefert `None` bei All-Offline:** **Übertrag:** AC 7 — wenn der Pool kein SoC liefert, refuse zu charge/discharge (return `[]`).
- **Pool-Konstruktion in `main.py::lifespan`:** `BatteryPool.from_devices(devices, ADAPTERS)` produziert `BatteryPool | None`. **Übertrag:** Controller-Konstruktor nimmt `BatteryPool | None` (Default `None` für Tests).
- **PoolMember-Invariant:** `capacity_wh >= 1` via `__post_init__`. **Übertrag:** 3.4 vertraut dem Pool — keine Extra-Validation in Policy.
- **`_speicher_max_soc_capped`-Flag-Pattern (NEU in 3.4):** Analog zu `state_cache.test_in_progress` aus 2.2 — Boolean-Flag mit Set/Reset-Logik, vermeidet Log-Spam bei oszillierender Cap-Bedingung.

**Aus Story 3.2 (Drossel-Policy-Pattern — 1:1-Übertrag):**

- **`DrosselParams.__post_init__`-Invariant-Pattern:** `SpeicherParams.__post_init__` validiert dieselben vier Invariants (deadband_w >= 0, min_step_w >= 1, smoothing_window >= 1, limit_step_clamp_w >= 1).
- **`state_cache.last_states`-`isinstance`-Guard:** P10 in 3.2 — `isinstance(entry.attributes, dict)`. **Übertrag:** Im Pool aus 3.3 schon abgedeckt; Speicher-Policy liest nur `state.state` (numerische Sensor-Werte), kein Extra-Guard nötig.
- **NaN/Inf-Guard auf `sensor_value_w`:** P4 in 3.2 — `math.isfinite()`. **Übertrag:** AC 18-Pflicht-Early-Return.
- **Defensive `try/except` für Adapter-Calls (P9):** Speicher-Policy ruft `adapter.get_speicher_params(device)` — der Default kann nicht werfen (kein `NotImplementedError`); Override ebenfalls nicht (Marstek liefert konstante Defaults). **Kein** `try/except` an dieser Stelle.
- **`int(round(smoothed))` statt `int(smoothed)`:** P5 in 3.2 — symmetrische Rundung. **Übertrag:** 3.4 nutzt `int(round(smoothed))` für `proposed`-Berechnung.
- **`_clamp_step(current, proposed, max_step)`:** Existiert als Modul-Helper in `controller.py`. **Übertrag:** Wiederverwenden — kein neuer Helper.
- **Smoothing-Buffer als `dict[device.id, deque]`:** Drossel macht das schon. **Übertrag:** `_speicher_buffers` mit identischer Struktur, getrennt vom Drossel-Buffer.
- **Role-Filterung in der Policy (AC 7 Drossel = AC 17 Speicher):** Beide Policies filtern auf `device.role == 'grid_meter'`.

**Aus Story 3.1 (Controller-Foundation — fundamentaler Ankerpunkt):**

- **`Mode.SPEICHER`-Enum-Value `'speicher'`:** Existiert; `state_cache.update_mode('speicher')` und `control_cycles.mode='speicher'`-CHECK sind seit 5.1a/3.1 abgedeckt.
- **`PolicyDecision.command_kind='set_charge'`:** Existiert seit 3.1; Executor routet auf `adapter.build_set_charge_command`.
- **`Marstek-Venus.build_set_charge_command`:** Existiert seit 2.2 — `HaServiceCall(domain='number', service='set_value', service_data={...})`.
- **Per-Device-Lock (`self._device_locks`):** Existiert; greift automatisch pro `device_id`. **Übertrag:** Multi-Member-Dispatch nutzt das ohne Code-Änderung.
- **`_safe_dispatch`-Wrapper:** Existiert; Fail-Safe-Branch ist fertig. **Übertrag:** Multi-Decision-Iteration ruft pro Decision; jede Task hat ihren eigenen Fail-Safe-Pfad.
- **`asyncio.create_task(...)` + `_track_task(task)`:** Existiert. **Übertrag:** Iteration in `on_sensor_update` spawnt N Tasks; alle werden via `_dispatch_tasks` getrackt; `aclose()` cancelt alle pending Tasks beim Shutdown.
- **`_classify_source`-2-s-Solalex-Window:** Greift pro Sensor-Event einmal. **Übertrag:** Multi-Decision-Dispatch innerhalb desselben Sensor-Events nutzt denselben Source-Wert (wird vor dem `_dispatch_by_mode`-Call berechnet).
- **`state_cache.set_last_command_at(now)`:** Wird im Executor `dispatch` aufgerufen, nachdem `call_service` erfolgreich war. Bei N parallelen Decisions setzen alle den **gleichen** `now`-Wert (idempotent — AC 12).

**Aus Story 2.2 (Funktionstest + Commissioning):**

- **`commissioned_at IS NOT NULL`-Filter:** In `main.py::lifespan::devices_by_role` und `BatteryPool.from_devices` schon abgedeckt. 3.4 vertraut den Filtern.
- **Marstek-Charge-Subscription:** `ensure_entity_subscriptions` subscribed alle commissionierten Entity-IDs. Speicher-Readback greift automatisch.

**Aus Story 2.1 (Hardware Config Page):**

- **`config_json`-Schema für Marstek-Venus:** `{min_soc, max_soc, night_discharge_enabled, night_start, night_end}` — persistiert vom Wizard, lebt am `wr_charge`-Device-Row. **Übertrag:** Speicher-Policy liest `min_soc`/`max_soc` direkt; `night_*`-Felder werden in 3.6 von der Policy konsumiert (Nacht-Entlade), in 3.4 **noch nicht**.
- **Pydantic-Wizard-Validation:** `min_soc < max_soc - 10` (Range-Check), `night_start != night_end`. 3.4 vertraut den Wizard-Garantien — keine Doppel-Validation.

### Git Intelligence Summary

**Letzte 10 Commits (chronologisch, neueste zuerst):**

- `af0559f fix(api): tighten control state mode typing for idle override` — `state_cache.update_mode` jetzt narrowed auf 4 ModeValues; Speicher-Mode-Mirror funktioniert seit 5.1a.
- `c41a87b fix(tests): seed control cycle for control/state mode assertions` — Test-Pattern für Mode-Assertion etabliert; Speicher-Tests können direkt gegen `state_cache.current_mode == 'speicher'` asserten.
- `1aabf22 chore(release): beta 0.1.1-beta.4` — Sync-Release.
- `0650862 feat(5.1a)`: Live-Running-View + Polling-Endpoint live; Mode-Mirror in `state_cache` greift.
- `4053a83 fix(3.2)`: Code-Review-Fixes Story 3.2 — Pattern-Transfer: Invariant-Validation, NaN-Guards, `isinstance`-Checks, `int(round())`-statt-`int()`-Trunkierung. **Direkt für 3.4 relevant.**
- `f3b4a68 fix(3.1)`: Harden Controller/Executor — Fail-Safe-Wrapper, Async-Task-Management. Per-Device-Lock-Pattern.

**Relevante Code-Patterns aus den Commits:**
- `controller.py` Enum-Dispatch + `match`-Block bleibt das Vorbild.
- `DrosselParams.__post_init__`-Invariant-Pattern → 1:1 für `SpeicherParams`.
- `_drossel_buffers` als `dict[int, deque[float]]` → 1:1 für `_speicher_buffers`.
- `_clamp_step`-Helper bleibt wiederverwendbar.
- Code-Review-Pattern aus 3.2 (Patches P1–P16, Decisions D1–D5): Defensive-Checks (Invariant-Validation, NaN-Filter, `isinstance`-Guards) sind Teil der initialen Implementation, nicht „später nachziehen".

### Latest Tech Information

- **Python 3.13 `divmod` behaviour:** `divmod(-1001, 2) == (-501, 1)` — sign-symmetric. Pool-`set_setpoint` aus 3.3 nutzt das; 3.4 muss nichts dazu wissen.
- **`@dataclass(frozen=True)`** für `SpeicherParams`: identisch zu `DrosselParams`. Frozen → hashbar, immutable, `__post_init__` läuft vor dem Freeze.
- **`asyncio.create_task(...)` mit `name=...`** für deterministische Task-Identifikation in Stack-Traces. Multi-Decision-Iteration: `name=f"controller_dispatch_{device.id}"` pro Member.
- **FastAPI `app.state.battery_pool`** wird in der Lifespan vor `Controller(...)` gebaut (3.3). 3.4 nutzt das Setup unverändert; `app.state.battery_pool` bleibt der Wahrheits-Ort.

### Project Context Reference

Kein `project-context.md` in diesem Repo. Referenz-Dokumente sind die oben verlinkten `prd.md`, `architecture.md`, `epics.md`, `CLAUDE.md` sowie die Vor-Stories 3.1 / 3.2 / 3.3 / 2.1 / 2.2.

### Pipeline-Kette — Reference Flow (Speicher-Pfad)

Siehe AC 19 für das vollständige ASCII-Flow-Diagramm. Kurz-Zusammenfassung der **dreistufigen** Veto-/Filter-Kette:

1. **Policy-Stufe (`_policy_speicher`):** Role-Filter, NaN/Inf-Filter, Pool-Existenz-Filter, SoC-Existenz-Filter, Deadband-Filter, Hard-Cap-Filter (Max/Min-SoC), Min-Step-Filter. Output: `list[PolicyDecision]` (kann `[]` sein, keine Exceptions, keine IO).
2. **Pool-Stufe (`pool.set_setpoint`):** Online-Member-Filter, Gleichverteilung mit Rest-Rotation. Output: `list[PolicyDecision]` (kann `[]` sein, keine Exceptions, keine IO).
3. **Executor-Stufe (`executor.dispatcher.dispatch`):** Range-Check, Rate-Limit, `call_service`, Readback, Cycle-Insert + Latency-Insert. Output: `DispatchResult` mit `status in {passed, failed, timeout, vetoed}`.

**Jede Stufe darf `[]` (kein Decision) liefern; das ist kein Fehler.** Cycle-Rows entstehen nur in der Executor-Stufe — Policy-/Pool-Filter produzieren keinen Audit-Trail in `control_cycles` (nur Logs).

### Vorzeichen-Konvention (Single-Source-of-Truth)

Siehe AC 20 für die verbindliche Definition. **Verständnishilfe:**

| Smart-Meter-Wert | Bedeutung | Speicher-Setpoint | Pool-Verhalten |
|---|---|---|---|
| `+200 W` | Bezug 200 W aus Netz | `-200 W` (negativ) | Pool entlädt 200 W → deckt Grundlast |
| `0 W ± 30 W` | Deadband | — | Kein Dispatch |
| `-500 W` | Einspeisung 500 W ins Netz | `+500 W` (positiv) | Pool lädt 500 W → cancelt Einspeisung |
| `-2700 W` | Einspeisung 2700 W (PV-Peak) | `+2500 W` (gecappt) | Pool lädt mit Marstek-Max 2500 W; 200 W bleiben Einspeisung (Drossel-Hand-off in 3.5) |

**Mathematisch:** `proposed_setpoint_w = -int(round(smoothed_grid_w))`, dann `_clamp_step` auf `±limit_step_clamp_w` (Marstek: 500 W/Zyklus), dann `pool.set_setpoint` → `[PolicyDecision]` mit Pool-Verteilung, dann Executor-Range-Clamp auf `[-2500, +2500]`.

### Anti-Patterns & Gotchas

- **KEIN `time.sleep` oder `asyncio.sleep` in `_policy_speicher`.** Die Policy ist synchron (reine Berechnung); alle I/O liegt im Executor.
- **KEIN Lesen von `devices.last_write_at` aus der Policy** — das ist Rate-Limiter-Zuständigkeit (greift im Executor automatisch).
- **KEIN direktes `ha_client.call_service` aus der Policy** — immer via `executor.dispatcher.dispatch(...)`.
- **KEIN Persistieren des Smoothing-Puffers, des Last-Setpoints oder der Cap-Flags** — alles in-memory. State geht beim Add-on-Restart verloren; Buffer füllt sich in ~5 s neu (AC 18).
- **KEIN `numpy`, `pandas`, `scipy`** — reine stdlib.
- **KEIN Property-Getter für `_current_mode`-Setzung aus der Policy.** Mode-Switch ist Story 3.5 — die Policy darf den Mode **nicht** umschalten.
- **KEIN `datetime.utcnow()`** — immer `self._now_fn()` (Test-Injektions-Schiene aus 3.1).
- **KEIN Logging des Sensor-Werts auf `info` im Hot-Path** — `debug` für verworfene Decisions, `info` nur für Hard-Cap-Übergänge (AC 3, 4) und beim tatsächlichen Dispatch (im Executor; bereits da).
- **KEIN Mode-Wechsel auf Basis der Policy-Entscheidung** — Story 3.5.
- **KEIN Überschreiben von `AdapterBase.get_speicher_params` mit `NotImplementedError`** in Non-Speicher-Adaptern — Default greift; Hoymiles/Shelly sind nie `wr_charge`.
- **KEIN Per-Member-`min_soc`/`max_soc`-Read in v1** — der erste Member ist die Single-Source-of-Truth (AC 15). v1.5 wird per-Member-Konfiguration nachziehen.
- **KEIN `pool.set_setpoint(0, ...)`-Befehl bei Hard-Cap** — die Policy gibt `[]` zurück, nicht eine Lade-Decision mit Wert 0. Begründung: Ein `set_charge=0`-Befehl würde den Akku auf „nichts tun" zwingen, aber bei Marstek bedeutet `set_value=0` ggf. einen aktiven Stop-Befehl, der die Marstek-Logik überschreibt. **Hard-Cap = nichts senden** ist sicherer (Akku bleibt im letzten Zustand).
- **KEIN doppelter SoC-Read pro Sensor-Event** — `pool.get_soc(state_cache)` einmal pro `_policy_speicher`-Call. SoC-Updates in `state_cache.last_states` sind eventual consistent; nächste Policy-Iteration sieht den neuen Wert.

### Source Tree — Zielzustand nach Story

```
backend/src/solalex/
├── controller.py                              [MOD — _policy_speicher echt, _speicher_buffers, _speicher_last_setpoint_w, _speicher_max_soc_capped, _speicher_min_soc_capped, battery_pool im Konstruktor, _dispatch_by_mode list-signature, on_sensor_update iteration]
├── battery_pool.py                            [unverändert — Pool aus 3.3]
├── adapters/
│   ├── base.py                                [MOD — SpeicherParams Dataclass + get_speicher_params Default]
│   ├── hoymiles.py                            [unverändert — erbt Default]
│   ├── marstek_venus.py                       [MOD — get_speicher_params Override + get_limit_range (-2500,2500)]
│   └── shelly_3em.py                          [unverändert — erbt Default]
├── executor/                                  [unverändert aus 3.1]
├── persistence/                               [unverändert — keine neue Migration]
├── kpi/                                       [unverändert]
└── main.py                                    [MOD — battery_pool=battery_pool im Controller-Call]

backend/tests/unit/
├── test_controller_speicher_policy.py         [NEW]
└── test_marstek_venus_speicher_params.py      [NEW]
```

Frontend: **keine Änderungen.**

### Beta-Gate-Bezug

Aus PRD Zeile 392: **„Speicher-Modus stabil ±30 W bei Marstek Venus (Micha-Setup) plus expliziter sauberer Modus-Wechsel ‚Akku-voll → Drossel' ohne Oszillation."** 3.4 liefert die **Policy-Hälfte** des Beta-Gates: ±30 W-Deadband, Hard-Cap bei Max-SoC, Pool-Multi-Member-Dispatch. Den eigentlichen **Modus-Wechsel** mit 97/93 %-Hysterese liefert Story 3.5. Die **Empirie** (tatsächliches ±30 W-Verhalten am echten Marstek-Setup) verifiziert Alex im lokalen Manual-Smoke nach Merge (Beta-Gate-Empirie, kein PR-Block).

### Performance & Sicherheit

- **NFR2 (Dashboard-TTFD ≤ 2 s):** Policy läuft synchron in `on_sensor_update`, vor dem Fire-and-Forget-Dispatch. Performance-Budget der Policy: < 1 ms (Smoothing-Mittelwert + Pool-Methoden + Dict-Lookup). `pool.set_setpoint(N=8)` < 1 ms; `pool.get_soc(N=8)` < 1 ms (3.3 AC 14).
- **Safety (CLAUDE.md Regel 3):** Policy darf **niemals** direkt auf HA schreiben. Sie erzeugt nur `PolicyDecision`-Objekte; Executor verifiziert Range, Rate-Limit, Readback. Multi-Member-Dispatch behält die Garantie pro Decision.
- **EEPROM-Schutz:** Marstek-Charge-Power-Entity hat `min_interval_s=60.0`. Bei Pool mit N=2 Members heißt das: pro Member **separate** 60-s-Sperre (separate `device_id` → separate `last_write_at`). Pool-Setpoint-Berechnungen können bei jedem Sensor-Event laufen; tatsächliche Writes werden vom Executor pro Member getaktet.
- **Keine persistente State-Änderung ohne Dispatch:** Policy ändert weder `devices.last_write_at` noch `control_cycles` — das macht ausschließlich der Executor.

### Scope-Grenzen zur Folge-Story (3.5, 3.6, 3.7)

- **Story 3.5 (Adaptive + Hysterese):** Baut den Mode-Selector, der zur Laufzeit zwischen DROSSEL / SPEICHER / MULTI wechselt mit 97/93 %-Hysterese und 60-s-Mindest-Verweildauer. 3.4 setzt den Hard-Cap (Lade/Entlade = 0) plus Audit-Flag-Log; **kein** automatischer Mode-Switch.
- **Story 3.6 (User-Config — Min/Max-SoC + Nacht-Entlade):** Frontend-Settings für `min_soc`/`max_soc` + Nacht-Entlade-Zeitfenster. 3.4 liest die in 2.1 persistierten Werte direkt aus `wr_charge.config_json`; 3.6 baut das UI dafür plus Hot-Reload (Config-Change ohne Add-on-Neustart).
- **Story 3.7 (Fail-Safe bei Kommunikations-Ausfall):** 24-h-Dauertest + Health-Marker-Persistenz + Recovery-Logik. 3.4 nutzt den Fail-Safe-Wrapper aus 3.1 unverändert.

### Deferred (out-of-scope for 3.4, documented for v1.5+)

- **Per-Member-`min_soc`/`max_soc`** (v1.5): Heute liest die Policy `config_json` des **ersten** Members (v1: 1 Member). v1.5 mit echter Multi-Akku-Wizard-Erweiterung wird konservativ-aggregieren (`max_soc = min(member_max)`, `min_soc = max(member_min)`).
- **SoC-Balance statt Gleichverteilung** (v2): PRD Zeile 348 + Architektur Zeile 256/980. 3.4 bleibt auf Gleichverteilung — Pool aus 3.3 macht das.
- **Anker-Solix + Generic-HA-Adapter** (v1.5): Pool-Code und Speicher-Policy sind adapter-agnostisch. Bei Einzug der neuen Adapter werden nur `get_speicher_params` und `get_limit_range` überschrieben.
- **Async-Readback-Pfad für Marstek-Venus** (Story 3.4-Follow-up / v1.5): Marstek-Venus hat `ReadbackTiming(timeout_s=30.0, mode='sync')` — bei 2× Venus im Pool und je 30 s Readback kann sich der Per-Device-Lock aufstauen. Heute akzeptabel (Pool-of-1 in v1); v1.5 evaluiert async-Readback (analog zu OpenDTU-MQTT-Plan in `deferred-work.md`).
- **Hot-Reload des Pools bei Runtime-Config-Change:** Story 3.6 oder Epic 2 v1.5 nimmt das auf — analog zu `devices_by_role`-Reload (heute auch Static-Snapshot).
- **Charge-Power-Cap pro Device via `config_json.charge_power_cap_w`:** v1.5 — heute nutzt der Adapter den Datenblatt-Wert (2500 W), Override per `device.config_json` ist v1.5-Scope mit Wizard-Erweiterung.
- **Mode-Switch-Animation im Dashboard** (Story 5.5): Frontend-Anzeige der Modus-Übergänge (Drossel ↔ Speicher) — v1; 3.4 liefert die Daten in `control_cycles`, Story 5.5 baut das UI.
- **Pool-Display im Energy-Ring** (Story 5.4): Aggregierter SoC + Per-Member-Breakdown im Frontend — v1; `pool.get_soc()` liefert beides bereit, Story 5.4 verdrahtet.
- **Multi-Modus** (Story 3.5): Drossel + Speicher gleichzeitig (z. B. Pool laden UND WR drosseln, wenn Pool fast voll). 3.4 implementiert nur den `Mode.SPEICHER`-Branch; `Mode.MULTI` bleibt Stub.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- `uv run pytest -q` → 219 passed.
- `uv run ruff check .` → All checks passed.
- `uv run mypy --strict src/ tests/` → Success: no issues found in 83 source files.
- Drift-Checks 1–5 (templates, per-mode submodules, vendor-name leaks, set_mode in Speicher-Policy) → 0 Treffer.
- SQL-Migrations-Ordering unverändert: `001_initial.sql` + `002_control_cycles_latency.sql`.

### Completion Notes List

- **AC 1, 2, 20 (Lade/Entlade + Sign-Konvention):** `_policy_speicher` produziert `+watts` bei Einspeisung und `-watts` bei Bezug; sign-flip via `proposed = -int(round(smoothed))`.
- **AC 3, 4 (Hard-Caps + Flag-Tracking):** Bei `aggregated >= max_soc` (Lade) bzw. `aggregated <= min_soc` (Entlade) liefert die Policy `[]` und logt einmalig `speicher_mode_at_max_soc` / `speicher_mode_at_min_soc`. Boolean-Flags (`_speicher_max_soc_capped`, `_speicher_min_soc_capped`) deduplizieren den Log; Reset beim Verlassen des Caps.
- **AC 5 (Deadband + Min-Step):** Marstek-Defaults `deadband_w=30`, `min_step_w=20` — Smoothing über 5-Sample-`deque`. `min_step` greift gegen den letzten dispatched Pool-Setpoint (per `id(pool)`-Key in `_speicher_last_setpoint_w`).
- **AC 6, 11 (per-Member Rate-Limit / Fail-Safe):** Multi-Member-Dispatch via `asyncio.create_task` pro Decision; Per-Device-Lock (`self._device_locks`) erlaubt Member-Parallelität, serialisiert pro `device_id`. Eine fehlgeschlagene Member-Decision blockt die anderen nicht.
- **AC 7 (Pool-Existenz):** Frühe Returns bei `pool is None`, `pool.members` empty, `pool.set_setpoint(...) == []` (alle Members offline).
- **AC 8 (Multi-Decision-Refactor):** `_dispatch_by_mode` Signatur jetzt `list[PolicyDecision]`. Drossel wraps in `[decision]`/`[]`, MULTI bleibt Stub (`return []`). `on_sensor_update` iteriert über die Liste, spawnt einen `asyncio.create_task` pro Decision; Noop-Cycle wird **genau einmal** pro Sensor-Event geschrieben (nicht pro Member).
- **AC 13 (Marstek-Range signed):** `MarstekVenusAdapter.get_limit_range = (-2500, 2500)` mit Sign-Convention-Kommentar; TODO entfernt.
- **AC 14 (`SpeicherParams` im Adapter-Modul):** `@dataclass(frozen=True)` in `adapters/base.py` mit `__post_init__`-Invariants (P6/P7-Pattern). `MarstekVenusAdapter.get_speicher_params` overridet mit `(30, 20, 5, 500)`; Hoymiles + Shelly erben den Default. **Keine** JSON-Templates.
- **AC 15 (Min/Max-SoC aus `config_json`):** Helper `_read_soc_bounds(charge_device)` liest aus dem ersten Member; Defaults 95/15 bei fehlendem Key oder Parse-Fehler.
- **AC 16 (Mode-Gate):** Der `match`-Block in `_dispatch_by_mode` ruft `_policy_speicher` ausschließlich im `Mode.SPEICHER`-Branch.
- **AC 17 (Role-Filter):** Frühes `[]` bei `device.role != 'grid_meter'`.
- **AC 18 (Smoothing-Buffer in-memory + separat):** `self._speicher_buffers` ist getrennt von `self._drossel_buffers` und überlebt keinen Restart (kein DB-Persist).
- **AC 21 (No-Drift-Check):** Keine SQL-Migration, keine API-Schema-Änderung, keine Frontend-Änderung, keine neue Dependency.
- **Pattern-Transfer aus Story 3.2 Review:** `int(round(smoothed))` statt `int(...)` für symmetrische Rundung; defensive `try/except` in `_read_soc_bounds` analog zu `_read_current_wr_limit_w` (P9).
- **Bestehende Tests aktualisiert:** `test_controller_dispatch.py` — die zwei `_fake_dispatch`-Monkey-Patches geben jetzt `list[PolicyDecision]` zurück (Signatur-Änderung an `_dispatch_by_mode`).

### File List

**Modified Backend Source:**
- `backend/src/solalex/adapters/base.py` — `SpeicherParams` Dataclass + `AdapterBase.get_speicher_params()` Default.
- `backend/src/solalex/adapters/marstek_venus.py` — `get_speicher_params` Override (Marstek-Defaults), `get_limit_range` von `(0, 2500)` auf `(-2500, 2500)` widen, TODO entfernt.
- `backend/src/solalex/controller.py` — `_policy_speicher` produktiv (ersetzt Stub), `_dispatch_by_mode` Signatur auf `list[PolicyDecision]`, `on_sensor_update` iteriert über N Decisions, neue Felder `_battery_pool`, `_speicher_buffers`, `_speicher_last_setpoint_w`, `_speicher_max_soc_capped`, `_speicher_min_soc_capped`, neuer Helper `_read_soc_bounds`, `_policy_multi_stub` returniert jetzt `[]`, alter `_policy_speicher_stub` gelöscht.
- `backend/src/solalex/main.py` — `battery_pool=battery_pool` an `Controller(...)` durchgereicht.

**Modified Backend Tests:**
- `backend/tests/unit/test_controller_dispatch.py` — `_fake_dispatch`-Monkey-Patches in zwei Tests auf `list[PolicyDecision]` umgestellt (Signatur-Fit).

**New Backend Tests:**
- `backend/tests/unit/test_controller_speicher_policy.py` — 24 Test-Fälle (Lade/Entlade, Hard-Caps, Flag-Tracking, Deadband, Min-Step, Rate-Limit-Veto pro Member, Pool-None/Empty/Offline, Multi-Member-Dispatch + Per-Device-Lock, Per-Member-Fail-Safe, Min/Max-SoC aus `config_json`, Mode-Gate, Role-Filter, Buffer-Separation, Sign-Konvention).
- `backend/tests/unit/test_marstek_venus_speicher_params.py` — 7 Test-Fälle (Marstek-Override, Sinus-Last-Toleranz, Range-signed, Base-Default, Hoymiles-Inheritance, Registry-Resolution, Invariants).

### References

- [epics.md — Story 3.4, Zeile 860–894](../planning-artifacts/epics.md)
- [architecture.md — Project Structure Zeile 576–752 + Epic-3-Zeile 803](../planning-artifacts/architecture.md)
- [architecture.md — Amendment 2026-04-22 Cuts 9 + 11 + 16](../planning-artifacts/architecture.md)
- [prd.md — FR15 (Lade/Entlade), FR21 (Pool-Gleichverteilung), FR22 (Min/Max-SoC), FR23 (SoC-Aggregat) — Zeile 595–608](../planning-artifacts/prd.md)
- [prd.md — Modus-Abgrenzung Zeile 363–367](../planning-artifacts/prd.md)
- [prd.md — Beta-Gate Zeile 392 (Speicher ±30 W)](../planning-artifacts/prd.md)
- [prd.md — v1-Scope Zeile 223 (1 Akku pro Instanz)](../planning-artifacts/prd.md)
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md)
- [Story 3.1 — Core Controller (Mono-Modul, Sensor → Policy → Executor)](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md)
- [Story 3.2 — Drossel-Modus + Review-Findings](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — Pattern-Transfer (Invariants, Defensive-Checks, `isinstance`-Guards, `int(round())`-Symmetrische-Rundung)
- [Story 3.3 — Akku-Pool-Abstraktion](./3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation.md) — Pool-API-Vertrag (Pflichtlektüre)
- [Story 2.1 — Hardware Config Page](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md) — `config_json`-Persistenz für `min_soc`/`max_soc`
- [Story 2.2 — Funktionstest mit Readback & Commissioning](./2-2-funktionstest-mit-readback-commissioning.md) — `commissioned_at`-Filter, Marstek-Charge-Command
- [adapters/marstek_venus.py — Charge-Command + heute Range (0, 2500)](../../backend/src/solalex/adapters/marstek_venus.py)
- [adapters/base.py — AdapterBase-Interface + DrosselParams-Pattern](../../backend/src/solalex/adapters/base.py)
- [controller.py — Mode-Enum + PolicyDecision + Drossel-Policy](../../backend/src/solalex/controller.py)
- [battery_pool.py — Pool-API (3.3)](../../backend/src/solalex/battery_pool.py)
- [main.py — Lifespan-Verdrahtung + Pool-Bau](../../backend/src/solalex/main.py)
- [api/routes/devices.py — wr_charge.config_json mit min_soc/max_soc](../../backend/src/solalex/api/routes/devices.py)
- [api/schemas/devices.py — Wizard-Validation für SoC-Range](../../backend/src/solalex/api/schemas/devices.py)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.4 erstellt und auf `ready-for-dev` gesetzt. Speicher-Modus als produktive Lade-/Entlade-Regelung (`_policy_speicher` ersetzt Stub) mit Pool-Konsum aus Story 3.3, Hard-Cap bei Min/Max-SoC, Marstek-Range-Erweiterung auf `(-2500, 2500)`, `SpeicherParams` als Adapter-Modul-Konstanten (Marstek: ±30 W Deadband, ±20 W Min-Step, 5 Samples Smoothing, 500 W/Zyklus Step-Clamp). Multi-Member-Dispatch via `_dispatch_by_mode`-Signatur-Änderung auf `list[PolicyDecision]`. Kein Mode-Switch (Story 3.5), kein User-Config-UI (Story 3.6), keine SQL-Migration, keine Frontend-Änderung, keine neue Dependency. Tests decken Lade/Entlade-Beide-Richtungen, Hard-Caps mit Flag-Tracking, Multi-Member-Parallelität, Per-Member-Fail-Safe + Rate-Limit, Sign-Konvention, Marstek-Range-Erweiterung. Pattern-Transfer aus Story 3.2 Review (Invariant-Validation, NaN-Filter, `isinstance`-Guards, `int(round())`) und Story 3.3 (Pool-API-Vertrag). | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Implementation abgeschlossen — Status auf `review`. `SpeicherParams` + `AdapterBase.get_speicher_params()` Default in `adapters/base.py`, Marstek-Override mit Sign-Convention-Range (-2500, 2500). `Controller._policy_speicher` produktiv mit Smoothing-Buffer, Hard-Cap-Logik (Flag-getrackter Log-Spam-Schutz), Sign-Flip-Setpoint, Min-Step-Suppression. `_dispatch_by_mode` jetzt `list[PolicyDecision]`; `on_sensor_update` iteriert über N Decisions mit `asyncio.create_task` pro Member. `main.py::lifespan` reicht `battery_pool` an Controller durch. Bestehende `test_controller_dispatch.py`-Monkey-Patches an neue Signatur angepasst. 31 neue Tests (24 Policy + 7 Adapter), 219 Tests total grün. Ruff + MyPy strict + alle 5 Drift-Checks (templates, per-mode submodules, vendor leaks, set_mode in Speicher, SQL-Ordering) → grün. | Claude Opus 4.7 |
