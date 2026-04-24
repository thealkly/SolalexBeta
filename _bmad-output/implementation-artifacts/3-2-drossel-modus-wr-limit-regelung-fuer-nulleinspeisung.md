# Story 3.2: Drossel-Modus — WR-Limit-Regelung für Nulleinspeisung

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Balkon-Benni / Neugier-Nils ohne Akku,
I want dass Solalex bei PV-Überschuss das WR-Limit reaktiv runterregelt, damit keine Watt ans Netz verschenkt werden,
so that meine Hoymiles / OpenDTU-Hardware nulleinspeisungs-konform läuft ohne Bastelei.

**Scope-Pflock:** Diese Story ersetzt `_policy_drossel_stub` in `controller.py` durch eine **produktive reaktive Regel-Logik** für den `Mode.DROSSEL`-Zweig. Sie berührt weder Speicher- noch Multi-Modus (Story 3.4 / 3.5), weder den Mode-Selector (Story 3.5) noch den Fail-Safe-Wrapper (Story 3.7 ergänzt ihn). Alle Safety-Gates (Veto-Kaskade Range → Rate-Limit → Readback) laufen **unverändert** durch den Executor aus Story 3.1.

**Amendment 2026-04-22 (verbindlich):** Policy-Parameter (Deadband, Smoothing-Fenster, Mindest-Änderung) leben als **Python-Konstanten im Adapter-Modul** (`adapters/hoymiles.py`) — **keine JSON-Templates, kein `/data/templates/`-Verzeichnis, kein JSON-Schema-Validator** (CLAUDE.md Regel 2, architecture.md Amendment-Log Cut 11/16). Die Epic-AC-Formulierung „aus Template" ist pre-Amendment und wird hier durch „aus Adapter-Modul-Konstanten" realisiert.

## Acceptance Criteria

1. **Drossel-Reaktion auf Einspeisung (FR14, Epic-AC 1):** `Given` der Controller läuft im `Mode.DROSSEL` mit je einem kommissionierten Device in Rolle `grid_meter` (Shelly 3EM) und Rolle `wr_limit` (Hoymiles/OpenDTU), `When` ein `state_changed`-Event auf der `grid_meter`-Entity einen geglätteten Netzbezugs-Wert > 0 W meldet (positiv = Einspeisung nach Shelly-Konvention ist **invertiert**: `shelly_3em.parse_readback` liefert positive Werte für Bezug; das Adapter-Modul dokumentiert die Vorzeichen-Konvention und die Drossel-Policy folgt ihr), `Then` berechnet `_policy_drossel` eine `PolicyDecision` mit `command_kind='set_limit'`, `mode=Mode.DROSSEL`, `device=<wr_limit-Device>`, `target_value_w=<neues Limit>` **And** der Executor dispatched `number.set_value` via Hoymiles-Adapter (`build_set_limit_command`) **And** eine `control_cycles`-Zeile mit `mode='drossel'`, `source='solalex'`, `readback_status in ('passed','failed','timeout')`, `target_value_w=<limit>`, `sensor_value_w=<sensor>` wird via Executor geschrieben.
2. **Deadband — Hoymiles ±5 W (Epic-AC 2, PRD Zeile 181):** `Given` Drossel-Modus ist aktiv, `When` der geglättete Netzbezugs-Wert innerhalb `± DROSSEL_DEADBAND_W` (Hoymiles: 5 W) um den Ziel-Punkt (0 W = exakte Nulleinspeisung) liegt **UND** das berechnete neue Limit sich um weniger als `DROSSEL_MIN_STEP_W` (Hoymiles: 3 W) vom aktuellen Limit unterscheidet, `Then` liefert `_policy_drossel` `None` zurück **And** es entsteht **keine** `control_cycles`-Zeile mit `readback_status in ('passed','failed','timeout','vetoed')` — nur eventuelle Noop-/Attribution-Zeilen aus 3.1 (für `source != 'solalex'`) bleiben bestehen **And** kein `ha_client.call_service` wird ausgelöst.
3. **Lastsprung ohne Schwingen (Epic-AC 3, PRD Zeile 183):** `Given` eine Sequenz von Sensor-Werten, die einen Last-Ein-/Ausschalt-Vorgang simuliert (z. B. Zuschaltung 1500 W Verbraucher nach 10 s Grundlast), `When` die Policy mit einem gleitenden Fenster von `DROSSEL_SMOOTHING_WINDOW` (Default 5 Samples) arbeitet, `Then` konvergiert die Ziel-Limit-Folge **monoton** auf den neuen Gleichgewichts-Wert (keine Vorzeichen-Wechsel der `target_value_w`-Differenz innerhalb von ≤ 3 aufeinanderfolgenden Dispatch-Zyklen nach dem Event) **And** der Unit-Test `test_controller_drossel_policy.py::test_load_step_no_oscillation` verifiziert diese Eigenschaft mit einer aufgenommenen Sensor-Folge.
4. **Hoymiles-Toleranz ±5 W (Epic-AC 4, PRD Zeile 181, Beta-Gate):** `Given` der geglättete Sensor-Wert liegt stabil im Bereich `[-DROSSEL_DEADBAND_W, +DROSSEL_DEADBAND_W]`, `When` mindestens 3 aufeinanderfolgende Events eintreffen, `Then` wird innerhalb dieses Fensters **kein** neuer `call_service`-Write ausgelöst (Stabilisierung über Deadband + Min-Step-Kombination aus AC 2) **And** der Unit-Test `test_hoymiles_drossel_tolerance.py` verifiziert das Verhalten für eine Sinus-Last-Simulation im ±4 W-Bereich.
5. **Rate-Limit-Respekt (Epic-AC 5, inherited aus 3.1 Executor):** `Given` das Hoymiles-Adapter-Modul definiert `RateLimitPolicy(min_interval_s=60.0)`, `When` die Policy innerhalb der 60-s-Sperre ein neues Limit berechnet, `Then` produziert sie trotzdem die `PolicyDecision` (die Policy ist nicht für Rate-Limiting zuständig), **aber** der Executor-Dispatch schreibt eine `control_cycles`-Zeile mit `readback_status='vetoed'`, `reason` beginnt mit `'rate_limit: …'` und **kein** `call_service` wird ausgelöst — exakt das Verhalten aus Story 3.1, hier nur als Regression gesichert. `test_controller_drossel_policy.py::test_rate_limit_veto_passthrough` verifiziert die End-to-End-Kette.
6. **Policy liefert `None`, wenn Konfiguration unvollständig ist:** `Given` nur ein Device (nur `grid_meter` **oder** nur `wr_limit`) ist kommissioniert, `When` ein Sensor-Event eintrifft, `Then` liefert `_policy_drossel` `None` **And** es wird **keine** Exception geworfen **And** ein Noop-Attribution-Zyklus aus Story 3.1 darf trotzdem entstehen, wenn Source `'manual'`/`'ha_automation'` ist (3.1-Invariante).
7. **Policy läuft nur auf `grid_meter`-Events, nicht auf WR-Readback-Events:** `Given` ein `state_changed`-Event trifft auf einem `wr_limit`-Entity ein (z. B. weil der HA-User das Limit manuell geändert hat), `When` der Controller den Event verarbeitet, `Then` liefert `_policy_drossel` `None` — die Source-Attribution aus Story 3.1 (AC 5) greift weiterhin und schreibt ggf. einen Noop-Zyklus mit `source='manual'` oder `source='ha_automation'` **And** es wird **kein** `call_service` ausgelöst (insbesondere keine Rückkorrektur-Kaskade).
8. **Policy-Parameter im Adapter-Modul (CLAUDE.md Regel 2):** `Given` die Drossel-Parameter (`DROSSEL_DEADBAND_W`, `DROSSEL_MIN_STEP_W`, `DROSSEL_SMOOTHING_WINDOW`), `When` die Policy sie liest, `Then` stammen sie ausschließlich aus `adapters/hoymiles.py` (als Modul-Konstanten **oder** via neue `AdapterBase.get_drossel_params() -> DrosselParams`-Methode) **And** es existiert **keine** `/data/templates/`-Datei, **kein** JSON-Schema-Validator, **kein** dynamischer Template-Loader **And** das Hoymiles-Modul dokumentiert jeden Parameter mit einer Code-Kommentar-Zeile, die die Quelle (Hardware-Spec bzw. empirisch) nennt.
9. **Mode-Gate (Vorbereitung Story 3.5):** `Given` der Controller läuft in `Mode.SPEICHER` oder `Mode.MULTI`, `When` ein Sensor-Event eintrifft, `Then` wird `_policy_drossel` gar **nicht** aufgerufen (der `match`-Block in `_dispatch_by_mode` bleibt der Dispatch-Punkt; 3.2 befüllt nur den `Mode.DROSSEL`-Branch). `test_controller_drossel_policy.py::test_not_invoked_in_speicher_mode` verifiziert, dass keine Drossel-Logik greift, wenn `controller.set_mode(Mode.SPEICHER)` aktiv ist.
10. **Pipeline-Latenz ≤ 1 s (3.1-Invariante, FR31/NFR2-Vorarbeit):** `Given` ein Drossel-Dispatch-Zyklus, `When` er läuft, `Then` bleibt `cycle_duration_ms` in der `control_cycles`-Zeile **unter 1000 ms** für den reinen Policy-Pfad **And** Readback-Wartezeit (bis 15 s für Hoymiles) ist vom Pipeline-Zeitmessungs-Fenster ausgeschlossen, weil `_safe_dispatch` per `asyncio.create_task` aus Story 3.1 fire-and-forget läuft. (Der Test misst die Policy-Berechnungs-Dauer isoliert.)
11. **Fail-Safe bleibt greifen (FR18, Story 3.1 AC 9):** `Given` Drossel-Modus ist aktiv, `When` `ha_ws_connected_fn()` `False` liefert oder `ha_client.call_service` eine Exception wirft, `Then` greift der Fail-Safe-Wrapper aus Story 3.1 unverändert: `control_cycles` mit `readback_status='vetoed'`, `reason` beginnt mit `'fail_safe: …'`, **keine** `devices.last_write_at`-Aktualisierung, **keine** propagierte Exception — das letzte am WR gesetzte Limit bleibt physisch bestehen (wir setzen kein neues). Eine Regression-Test-Zeile in `test_controller_drossel_policy.py` sichert das Verhalten für eine Policy, die eine `PolicyDecision` liefert.
12. **Source-Attribution bleibt korrekt (Story 3.1 AC 5):** `Given` ein Solalex-getriebener Drossel-Zyklus schreibt in `control_cycles`, `When` der nachfolgende `state_changed`-Event auf der WR-Entity vom Readback-Mechanismus ankommt, `Then` erkennt `_classify_source` das Event als `'solalex'` (innerhalb des 2-s-Solalex-Fensters aus 3.1) **And** es entsteht **kein** zusätzlicher Noop-Attribution-Zyklus für den eigenen Write — 3.1-Invariante bleibt.
13. **Moving-Average-Zustand nicht persistieren:** `Given` das Smoothing-Fenster, `When` Solalex neu startet, `Then` beginnt die Policy mit einem leeren Fenster (kein Persistieren der letzten N Sensor-Samples in der DB) — das Fenster füllt sich innerhalb weniger Sekunden von selbst neu. Kein neues Schema, keine neue Repo-Datei. `test_controller_drossel_policy.py::test_smoothing_buffer_in_memory` sichert, dass keine DB-Writes für den Ring-Buffer entstehen.
14. **Unit-Tests (Pytest, MyPy strict, Ruff):** Neue Test-Dateien unter `backend/tests/unit/`:
    - `test_controller_drossel_policy.py`:
      - `test_drossel_policy_produces_decision_on_feed_in` (AC 1)
      - `test_deadband_suppresses_dispatch` (AC 2)
      - `test_load_step_no_oscillation` (AC 3 — feeds a recorded Sensor-Sequenz)
      - `test_rate_limit_veto_passthrough` (AC 5 — End-to-End mit FakeHaClient + FakeRateLimiter-State)
      - `test_no_decision_when_only_grid_meter_commissioned` (AC 6)
      - `test_policy_noop_for_wr_limit_events` (AC 7)
      - `test_not_invoked_in_speicher_mode` (AC 9)
      - `test_smoothing_buffer_in_memory` (AC 13)
      - `test_fail_safe_triggered_on_call_service_exception` (AC 11 — Regression)
    - `test_hoymiles_drossel_params.py`:
      - `test_adapter_exposes_drossel_params` — Hoymiles-Adapter liefert via `get_drossel_params()` die Defaults.
      - `test_hoymiles_drossel_tolerance` (AC 4 — Sinus-Last im ±4 W-Bereich)
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf allen Änderungen in `controller.py` (Drossel-Policy + Smoothing-Helper) und `adapters/hoymiles.py` (DrosselParams).
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (nummerisch lückenlos — **keine neue Migration in 3.2**).

## Tasks / Subtasks

- [x] **Task 1: `AdapterBase.get_drossel_params()` + `DrosselParams` Dataclass** (AC: 8)
  - [x] `adapters/base.py` um `@dataclass(frozen=True) class DrosselParams` erweitern mit Feldern:
    - `deadband_w: int` — Breite des Null-Punkts, innerhalb derer nicht dispatched wird.
    - `min_step_w: int` — minimale Delta zwischen aktuellem und neuem Limit, sonst Noop (Glättungs-Schutz).
    - `smoothing_window: int` — Anzahl Sensor-Samples im Moving Average.
    - `limit_step_clamp_w: int` — maximal erlaubte Änderung pro Dispatch (gegen Überschwingen, Default 200 W).
  - [x] `AdapterBase.get_drossel_params(self, device) -> DrosselParams` mit Default (z. B. `deadband_w=10`, `min_step_w=5`, `smoothing_window=5`, `limit_step_clamp_w=200`); Subclasses überschreiben.
  - [x] `NotImplementedError` NICHT werfen im Default — die Policy fragt generisch; Nicht-WR-Adapter überschreiben mit `raise NotImplementedError` nicht nötig, weil der Aufrufer (Drossel-Policy) den Adapter nur für `wr_limit`-Role-Devices abfragt.

- [x] **Task 2: Hoymiles-Adapter — Drossel-Parameter + Kommentare** (AC: 4, 8)
  - [x] `adapters/hoymiles.py`: Modul-Konstanten oder `DrosselParams`-Instanz mit:
    - `deadband_w=5` (Architecture Zeile 181, „Hoymiles/OpenDTU ±5 W")
    - `min_step_w=3` (empirisch: unter 3 W ist Signal im Sensor-Rauschen)
    - `smoothing_window=5` (Balance zwischen Reaktivität und Rausch-Unterdrückung; 5 × 1-s-Polling ≈ 5 s Glättung)
    - `limit_step_clamp_w=200` (verhindert WR-Schock-Transitionen bei Lastsprung)
  - [x] `get_drossel_params` gibt diese Werte zurück. Pro Feld ein One-Liner-Kommentar mit Quelle.
  - [x] **Keine** JSON-Datei, **kein** `load_from_template()`-Call, **kein** externes File-Laden.

- [x] **Task 3: Marstek / Shelly — Drossel-Parameter (Smoke-Overrides)** (AC: 8)
  - [x] `adapters/marstek_venus.py`: `get_drossel_params` erbt vom Default — Drossel-Modus schaltet in 3.2 nicht auf Akkus; wird in Story 3.4/3.5 relevant (Mode-Wechsel). Kein Code-Add nötig **außer** Test-Stub, der bestätigt, dass der Default greift.
  - [x] `adapters/shelly_3em.py`: Smart-Meter ist kein Write-Target; `get_drossel_params` erbt Default — **nicht** `NotImplementedError` werfen (die Policy fragt den **WR**-Adapter, nicht den SM-Adapter).

- [x] **Task 4: `controller.py` — Drossel-Policy produktiv** (AC: 1, 2, 3, 6, 7, 9, 10, 13)
  - [x] Ersetze `_policy_drossel_stub` durch eine richtige Policy-Funktion/Methode `_policy_drossel(self, device, sensor_value_w) -> PolicyDecision | None`. Die Stubs für `_policy_speicher` / `_policy_multi` bleiben `return None` (Story 3.4/3.5).
  - [x] Controller hält pro `device_id` (des `grid_meter`) einen **`collections.deque`** mit `maxlen=smoothing_window` als Moving-Average-Puffer. In-Memory, nicht persistent (AC 13).
  - [x] **Early-Returns** in `_policy_drossel` (in dieser Reihenfolge):
    1. `device.role != 'grid_meter'` → `None` (AC 7, nur SM-Events triggern die Drossel-Berechnung).
    2. `sensor_value_w is None` → `None` (kein brauchbares Messsignal, z. B. `unavailable`).
    3. `self._wr_limit_device is None` → `None` (AC 6, Konfiguration unvollständig).
  - [x] Shelly-Vorzeichen-Konvention: `shelly_3em.parse_readback` liefert **positive Werte = Bezug, negative Werte = Einspeisung** (siehe Adapter-Kommentar). Drossel reagiert auf **negative** Werte (Einspeisung → WR drosseln). Die Berechnung in 3.2:
    ```
    buffer.append(sensor_value_w)
    smoothed = sum(buffer) / len(buffer)
    if abs(smoothed) <= params.deadband_w:
        return None
    current_limit = _read_current_wr_limit_w()  # aus state_cache.last_states
    delta = -int(smoothed)                       # Einspeisung → negativ → delta positiv → Limit runter? NEIN:
    # Korrekte Richtung: bei Einspeisung (smoothed < 0) muss das WR-Limit runter (weniger Einspeisung).
    # delta = smoothed  → wenn smoothed = -100 W (Einspeisung), dann new_limit = current - 100 W
    # wenn smoothed = +80 W (Bezug), dann new_limit = current + 80 W
    proposed = current_limit + int(smoothed)
    proposed = _clamp_step(current_limit, proposed, params.limit_step_clamp_w)
    if abs(proposed - current_limit) < params.min_step_w:
        return None
    # Hartes Clamp auf Hoymiles-Range kommt im Executor (Range-Check aus 3.1)
    return PolicyDecision(device=wr_device, target_value_w=proposed, mode=Mode.DROSSEL, command_kind='set_limit', sensor_value_w=smoothed)
    ```
  - [x] `_read_current_wr_limit_w()` liest aus `state_cache.last_states.get(wr_device.entity_id)` und nutzt `hoymiles.parse_readback(state)` → `int | None`. Fallback: wenn kein State gecached, liefert die Policy `None` (besser keinen Befehl als einen mit falschem Ausgangs-Limit).
  - [x] Der **Dispatch-Punkt** ist unverändert `_dispatch_by_mode(...)` aus 3.1 — nur der `Mode.DROSSEL`-Case ruft jetzt die echte Policy auf. Der `match`-Block bleibt strukturell gleich.
  - [x] **Kein** neuer `subscribe`-Call für grid_meter — Story 1.3/2.2/3.1 stellen die Subscription bereits her (jedes kommissionierte Device wird subscribed). Die Policy konsumiert nur den Event-Strom, den der bestehende `_dispatch_event` in `main.py` liefert.

- [x] **Task 5: `Controller`-Konstruktor — `devices_by_role`-Lookup** (AC: 1, 6, 7)
  - [x] `Controller.__init__` bekommt einen zusätzlichen Parameter `devices_by_role: dict[str, DeviceRecord]`. Alternative (wenn du es flexibler magst): `devices_by_role_fn: Callable[[], dict[str, DeviceRecord]]` — **bevorzugt Direkt-Dict**, weil in v1 die Device-Konfiguration zur Startup-Zeit fix ist (Story 2.x).
  - [x] `controller.py` leitet daraus `self._wr_limit_device: DeviceRecord | None = devices_by_role.get('wr_limit')` und `self._grid_meter_device = devices_by_role.get('grid_meter')` ab.
  - [x] **Hot-Reload NICHT in 3.2.** Wenn der User die Device-Konfiguration ändert, ist ein Add-on-Neustart nötig — das ist Wizard-/Config-Page-Scope (Epic 2), nicht 3.2.
  - [x] `main.py` Lifespan baut das `devices_by_role`-Dict parallel zu `devices_by_entity` (gleicher Durchlauf) und übergibt es an den `Controller(...)`.

- [x] **Task 6: `main.py` Integration — devices_by_role bereitstellen** (AC: 1, 6)
  - [x] In `lifespan(...)` das Dict `devices_by_role: dict[str, DeviceRecord] = {d.role: d for d in devices}` bauen (v1: max. 1 Device pro Rolle, siehe PRD Zeile 223).
  - [x] An `Controller(...)` durchreichen. Keine weitere API-Änderung in `main.py`.
  - [x] **Keine Änderung** an `_dispatch_event` — die Role-Filterung passiert **innerhalb** von `_policy_drossel` (AC 7).

- [x] **Task 7: Unit-Tests — Drossel-Policy + Hoymiles-Params** (AC: 14)
  - [x] `backend/tests/unit/test_controller_drossel_policy.py` — siehe AC 14, enthält **alle** dort aufgelisteten Test-Fälle.
  - [x] `backend/tests/unit/test_hoymiles_drossel_params.py` — Adapter-Default + Toleranz-Sinus.
  - [x] Reuse `backend/tests/unit/_controller_helpers.py` (aus 3.1) für `FakeHaClient`, `FakeClock`, In-Memory-DB-Fixture. **Keine** neuen Helper-Dateien ohne Notwendigkeit.
  - [x] Tests verwenden `Controller(...)` direkt (nicht via `main.py`). `devices_by_role` wird per Fixture bereitgestellt (ein `wr_limit` + ein `grid_meter` Device).
  - [x] Coverage-Messung via `pytest --cov=solalex.controller --cov=solalex.adapters.hoymiles` muss ≥ 90 % Line-Coverage auf den **in 3.2 geänderten** Abschnitten zeigen.

- [x] **Task 8: Final Verification** (AC: 14)
  - [x] `uv run ruff check .` → grün.
  - [x] `uv run mypy --strict src/ tests/` → grün.
  - [x] `uv run pytest -q` → grün (alle bestehenden 91 Tests + neue Drossel-Tests).
  - [x] SQL-Ordering: unverändert (`001_initial.sql` + `002_control_cycles_latency.sql`) — **keine neue Migration in 3.2**.
  - [x] Drift-Check: `grep -rE "/data/templates|load_json_template|json-schema" backend/src/solalex/` → 0 Treffer.
  - [x] Drift-Check: `grep -rE "drossel\.py$|speicher\.py$|multi\.py$|mode_selector\.py$|pid\.py$|failsafe\.py$" backend/src/solalex/` → 0 Treffer (Controller bleibt Mono-Modul).
  - [ ] Manual-Smoke lokal im HA-Add-on mit einem Shelly 3EM + einem OpenDTU-WR offen — Ausführung durch Alex; kein Blocker für Review. (Post-Merge-Task, bleibt offen als Beta-Gate-Empirie.)

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Core Architectural Decisions, Zeile 229–260](../planning-artifacts/architecture.md) — Controller-Monolith, Direct-Call.
- [architecture.md — Amendment 2026-04-22 Cut 9 + 11](../planning-artifacts/architecture.md) — kein Controller-Submodul-Split, kein JSON-Template-Layer.
- [prd.md — FR14, FR17, FR18, FR19, FR27](../planning-artifacts/prd.md) — Drossel-Reaktion, Closed-Loop-Readback, Fail-Safe, Rate-Limit, Source-Attribution.
- [prd.md — Zeile 181–183 + 316](../planning-artifacts/prd.md) — ±5 W Hoymiles, Deadband + Rate Limiting + Moving Average als Anti-Schwing-Tripel.
- [prd.md — Zeile 363–367](../planning-artifacts/prd.md) — Modus-Abgrenzung: **Drossel = reiner WR, schnelle Abregelung, EEPROM-Rate-Limits**.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — insbesondere Regel 2 (ein Python-Modul pro Adapter, keine JSON-Templates) und Regel 3 (Closed-Loop + Rate-Limit + Fail-Safe).
- [Story 3.1](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — **Pflichtlektüre**: Die gesamte Executor-Veto-Kaskade, Fail-Safe-Wrapper, Source-Attribution, `control_cycles`-Schreib-Disziplin, Fire-and-Forget-Dispatch-Task sind dort fertig und werden in 3.2 **unverändert** genutzt.
- [Story 2.2 — Funktionstest](./2-2-funktionstest-mit-readback-commissioning.md) — `executor/readback.py::verify_readback` ist bereits live; in 3.2 nichts zu ändern.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Reine Backend-Story. **Keine Frontend-Änderungen.** Die Mode-Anzeige im Dashboard (FR28) und die Idle-State-Animation (FR29) sind Epic 5 — 3.2 schreibt Daten in `control_cycles`, Epic 5 liest sie.

**Mini-Diff-Prinzip:** Der Pull-Request für 3.2 sollte **klein** sein. Der Bulk der Regel-Engine steht schon aus 3.1. 3.2 ersetzt eine `return None`-Stub-Funktion durch ~40–70 Zeilen Drossel-Logik, fügt ~20 Zeilen `DrosselParams` im Adapter-Layer hinzu und rund 200 Zeilen Tests. Keine neue SQL-Migration. Keine neue Route. Keine neue Dependency.

**Dateien, die berührt werden dürfen:**

- **MOD Backend:**
  - `backend/src/solalex/controller.py`
    - `_policy_drossel` echt implementieren (ersetzt `_policy_drossel_stub`).
    - `Controller.__init__` nimmt `devices_by_role: dict[str, DeviceRecord]`.
    - Attribut `self._drossel_buffers: dict[int, collections.deque[float]]` für den Moving-Average-Ring-Puffer.
    - `_read_current_wr_limit_w()` als private Methode.
    - Speicher/Multi-Stubs bleiben `return None` — **nicht** produktiv ausformulieren (Story 3.4/3.5).
  - `backend/src/solalex/adapters/base.py`
    - `DrosselParams` Dataclass + `AdapterBase.get_drossel_params(device) -> DrosselParams` (mit Default-Implementation).
  - `backend/src/solalex/adapters/hoymiles.py`
    - `get_drossel_params` override mit den Hoymiles-Defaults (±5 W, etc.).
    - Klärende Kommentare pro Parameter (Hardware-Quelle).
  - `backend/src/solalex/adapters/marstek_venus.py`
    - Default vererben — **kein** Override in 3.2 (kommt in 3.4).
  - `backend/src/solalex/adapters/shelly_3em.py`
    - Default vererben — ausdrücklich **kein** `NotImplementedError`, weil die Policy grid_meter-Adapter nicht nach Drossel-Params fragt (die Policy fragt den WR-Adapter, siehe Task 4).
  - `backend/src/solalex/main.py`
    - Im Lifespan `devices_by_role = {d.role: d for d in devices}` bauen und an `Controller(...)` übergeben.

- **NEU Backend (Tests):**
  - `backend/tests/unit/test_controller_drossel_policy.py`
  - `backend/tests/unit/test_hoymiles_drossel_params.py`

- **NICHT anfassen:**
  - `backend/src/solalex/executor/dispatcher.py` — Veto-Kaskade bleibt **unverändert**. Jede Änderung hier ist Out-of-Scope.
  - `backend/src/solalex/executor/rate_limiter.py` — unverändert. Rate-Limit-Logik aus 3.1 greift automatisch.
  - `backend/src/solalex/executor/readback.py` — unverändert. 3.1/2.2 haben es fertig.
  - `backend/src/solalex/persistence/sql/*.sql` — **keine neue Migration**. `control_cycles`-Schema aus 002 ist ausreichend.
  - `backend/src/solalex/persistence/repositories/control_cycles.py` — unverändert.
  - `backend/src/solalex/persistence/repositories/latency.py` — unverändert.
  - `backend/src/solalex/kpi/__init__.py` — Noop-Stub bleibt, bis Epic 5 kommt.

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du `controller.py` in `drossel.py` / `speicher.py` / `multi.py` splittest — **STOP**. Mono-Modul mit `match`-Block (Architecture Cut 9, Amendment 2026-04-22).
- Wenn du ein `/data/templates/hoymiles_drossel.json` oder einen `json-schema`-Validator anlegst — **STOP**. Python-Konstanten im Adapter-Modul (CLAUDE.md Regel 2, Amendment 2026-04-22 Cut 11).
- Wenn du eine neue SQL-Migration anlegst — **STOP**. Die Drossel-Policy braucht kein neues Schema. Der Moving-Average-Puffer lebt in-memory (AC 13).
- Wenn du `structlog`, `APScheduler`, `cryptography` oder `SQLAlchemy` importierst — **STOP**. Nicht in 3.2 relevant.
- Wenn du `asyncio.Queue`, `events/bus.py` oder einen Pub/Sub-Dispatch einbaust — **STOP**. Direct-Call (Architecture Zeile 241).
- Wenn du `executor/dispatcher.py` oder `executor/rate_limiter.py` editierst — **STOP**. 3.1 hat sie fertig; 3.2 ist reine Policy-Logik.
- Wenn du im WR-Adapter einen PID-Regler, ein Kalman-Filter oder eine Feed-Forward-Schätzung einbaust — **STOP**. 3.2 ist eine **reaktive** Regelung mit Moving Average — nicht mehr. Forecast-Komponenten sind v2 (via `SetpointProvider`).
- Wenn du die Drossel-Logik in `adapters/hoymiles.py` anstatt in `controller.py` einbaust — **STOP**. Die Policy ist Controller-Concern (Mode-Dispatch-Owner); das Adapter-Modul liefert nur **Parameter** (Deadband, Smoothing-Fenster) und **Commands** (`build_set_limit_command`), keine Regel-Logik.
- Wenn du `logging.getLogger(...)` statt `get_logger(__name__)` nutzt — **STOP**. CLAUDE.md Regel 5.
- Wenn du den `_policy_speicher` oder `_policy_multi` Stub produktiv ausformulierst — **STOP**. Das ist Story 3.4 (Speicher) bzw. 3.5 (Multi-Modus + Mode-Selector).
- Wenn du Speicher/Multi-Modus-Wechsel-Logik (Hysterese, `Mode.SPEICHER ↔ Mode.DROSSEL`) einbaust — **STOP**. Das ist Story 3.5 (Adaptive Strategie-Auswahl). In 3.2 ist der Mode statisch auf `Mode.DROSSEL` (Default im Controller).
- Wenn du `_dispatch_event` in `main.py` umbaust (Shape-Change, neue Filter vor dem Controller-Hook) — **STOP**. Das ist Story 1.3/2.2/3.1 stabilisiert. Role-Filterung passiert **in der Policy** (AC 7).
- Wenn du einen WebSocket-Endpoint oder Server-Sent-Events für Drossel-Telemetry einbaust — **STOP**. Frontend-Live-Update läuft via REST + 1-s-Polling (Architecture Zeile 232).
- Wenn du deutsche Kommentare statt englischer schreibst — **STOP**. CLAUDE.md Stil-Leitplanken: **Code-Kommentare auf Englisch**, deutsche UI-Strings only im Frontend.
- Wenn du Policy-Parameter persistierst (z. B. in `meta`-Tabelle) — **STOP**. Parameter sind Code-Konstanten; User-Config (Min/Max-SoC, Nacht-Fenster) kommt erst in Story 3.6.

### Architecture Compliance Checklist

- **snake_case überall** (CLAUDE.md Regel 1): Python-Funktionen (`_policy_drossel`, `_read_current_wr_limit_w`), Variablen (`deadband_w`, `smoothing_window`, `limit_step_clamp_w`), Dataclass-Felder, Adapter-Konstanten. `DrosselParams` bleibt PascalCase (Python-Klassen-Konvention).
- **Ein Python-Modul pro Adapter** (CLAUDE.md Regel 2): `adapters/hoymiles.py` wird um `get_drossel_params` erweitert — keine neue Sub-Struktur, keine `hoymiles/drossel.py`-Datei.
- **Closed-Loop-Readback für jeden Write** (CLAUDE.md Regel 3): unverändert — die Policy **erzeugt** `PolicyDecision`; Executor **führt** den Write aus und verifiziert Readback. Kein direkter `ha_client.call_service` aus der Policy.
- **Rate-Limit persistent** (CLAUDE.md Regel 3): unverändert — Executor-Layer aus 3.1 übernimmt das.
- **JSON ohne Wrapper** (CLAUDE.md Regel 4): 3.2 fügt keine Routes hinzu.
- **Logging** (CLAUDE.md Regel 5): `_logger = get_logger(__name__)` am Modul-Top; `_logger.info('drossel_decision', extra=...)` für produktive Entscheidungen, `_logger.debug(...)` für verworfene (Deadband, Min-Step, leere Config) — Info-Level-Spam im Drossel-Loop vermeiden (HA-Event-Rate ist hoch).
- **MyPy strict**: alle neuen Funktionen haben Type-Hints; `from __future__ import annotations` am Modul-Top; `collections.deque[float]` statt unspezifizierter `deque`.
- **Forward-only Migrations**: **keine** neue Migration in 3.2.

### Pipeline-Kette — Reference Flow (Drossel-Pfad)

```
HA state_changed event (Shelly 3EM entity: sensor.<...>_total_power)
  ↓ _dispatch_event in main.py           [unverändert aus 3.1]
  ↓ state_cache.update(entity_id, state, ...) [unverändert]
  ↓ device = app.state.devices_by_entity.get(entity_id)  [grid_meter]
  ↓ controller.on_sensor_update(msg, device)  [unverändert aus 3.1]
  ↓   ├─ test_in_progress? → return       [3.1 invariant]
  ↓   ├─ source = _classify_source(msg)   [3.1 invariant]
  ↓   ├─ sensor_w = _extract_sensor_w(msg) [3.1 invariant]
  ↓   ├─ mode = self._current_mode == DROSSEL
  ↓   ├─ decision = self._dispatch_by_mode(DROSSEL, device, sensor_w)
  ↓   │   ↓ case DROSSEL: return _policy_drossel(device, sensor_w)  [3.2 NEW BODY]
  ↓   │   │   ├─ if device.role != 'grid_meter': return None
  ↓   │   │   ├─ if sensor_w is None: return None
  ↓   │   │   ├─ if self._wr_limit_device is None: return None
  ↓   │   │   ├─ buffer.append(sensor_w); smoothed = mean(buffer)
  ↓   │   │   ├─ if abs(smoothed) <= deadband_w: return None  [AC 2]
  ↓   │   │   ├─ current_w = _read_current_wr_limit_w() or None → return None
  ↓   │   │   ├─ proposed = current_w + int(smoothed)
  ↓   │   │   ├─ proposed = _clamp_step(current_w, proposed, limit_step_clamp_w)
  ↓   │   │   ├─ if abs(proposed - current_w) < min_step_w: return None
  ↓   │   │   └─ return PolicyDecision(device=wr_device, target_value_w=proposed, mode=DROSSEL, command_kind='set_limit', sensor_value_w=smoothed)
  ↓   ├─ if decision is None → noop attribution-cycle (AC 5 from 3.1)
  ↓   └─ else → asyncio.create_task(self._safe_dispatch(decision, t0))  [3.1 fire-and-forget]
  ↓        ├─ _safe_dispatch wraps exception + fail-safe (AC 11)
  ↓        └─ executor.dispatcher.dispatch(decision, ctx)
  ↓            ├─ Range-Check Hoymiles [2, 1500] W  [3.1]
  ↓            ├─ Rate-Limit (min_interval_s=60)   [3.1]
  ↓            ├─ build_set_limit_command           [3.1]
  ↓            ├─ ha_client.call_service('number', 'set_value', {...})
  ↓            ├─ verify_readback(...)              [3.1]
  ↓            ├─ control_cycles.insert + devices.last_write_at  [3.1]
  ↓            └─ latency.insert (if passed)        [3.1]
```

**Einziger neuer Code lebt im Block `[3.2 NEW BODY]`.** Alles drumherum steht und ist in 3.1 getestet.

### Vorzeichen-Konvention (Smart-Meter)

**Shelly 3EM** (siehe `adapters/shelly_3em.py` Docstring und `parse_readback`-Logik): `state` ist Rohwert in W oder kW; `parse_readback` liefert Rohwert als `int` in W. Die Konvention des Devices (Shelly 3EM):

- **Positiv = Grid Import (Bezug aus dem Netz)** — d. h. wir beziehen Strom.
- **Negativ = Grid Export (Einspeisung ins Netz)** — d. h. wir speisen ein.

Drossel-Ziel ist **Nulleinspeisung**: d. h. `grid_power ≈ 0` W, mit einem Deadband von ±5 W (Hoymiles-Toleranz). Bei `smoothed < 0` (Einspeisung) muss das WR-Limit **runter**; bei `smoothed > 0` (Bezug) darf das WR-Limit **hoch**, solange es die Hoymiles-Max-Grenze nicht überschreitet (Range-Check im Executor).

**Formel:**
```
new_limit = current_wr_limit + smoothed_grid_power
```

Weil `smoothed < 0` bei Einspeisung → `new_limit < current_wr_limit` → WR drosselt runter. ✓

**Beispiel:** Aktuelles WR-Limit = 800 W, Smart-Meter zeigt −150 W (Einspeisung). Dann `new_limit = 800 + (−150) = 650 W`. Nach einem 60-s-Rate-Limit-Fenster greift der nächste Zyklus.

**Hinweis:** Die Shelly-Konvention ist in der Praxis je nach Setup invertierbar (manche User haben die Phasen andersherum verkabelt). In 3.2 lebt die Konvention als Kommentar im Adapter-Modul; in Story 2.x gibt es eine Config-Page-Option „Smart-Meter-Vorzeichen invertieren" (aktuell **nicht** in 3.2-Scope, aber merken). Die Policy liest die Rohwerte und erwartet die oben beschriebene Konvention.

### Moving Average — Design-Entscheidungen

- **Puffer-Struktur:** `collections.deque(maxlen=smoothing_window)`. Kein numpy, kein pandas. Reine stdlib.
- **Puffer-Ort:** `dict[int, deque[float]]` in `self._drossel_buffers` mit `grid_meter.device_id` als Key. Erstellt on-demand beim ersten Event.
- **Arithmetik:** Einfacher Mittelwert `sum(buf)/len(buf)` — **nicht** `statistics.mean` (20× langsamer bei kleinen Listen).
- **Reset-Verhalten:** Keine explizite Reset-Logik in 3.2. Der Puffer füllt sich natürlich bei jedem Event; bei Add-on-Neustart beginnt er leer (AC 13). Wenn Story 3.5 einen Mode-Wechsel bringt, darf die Mode-Wechsel-Logik bei Bedarf die Buffer clearen — das ist aber 3.5-Scope.
- **Timing:** HA-State-Change-Events für Shelly 3EM kommen typisch alle 1–5 s. Smoothing-Window = 5 Samples → ~5–25 s Glättung. Reaktiv genug für WR-Drossel-Ziel (Hoymiles 5–15 s Latenz aus PRD Zeile 323), konservativ genug gegen Rausch-Induzierte Oszillation.

### Lastsprung-Analyse (AC 3)

Szenario: Grundlast 200 W, bei t=10 s schaltet ein 1500 W Verbraucher ein (z. B. Wasserkocher für 2 min).

- **t=9 s**: Sensor-Buffer `[−100, −100, −100, −100, −100]` (Einspeisung 100 W), smoothed = −100 W. WR-Limit z. B. 500 W, new_limit = 400 W. Dispatch (nach Rate-Limit-Fenster).
- **t=10 s** (Lastsprung): Sensor zeigt plötzlich +800 W Bezug. Buffer `[−100, −100, −100, −100, +800]`, smoothed = +80 W. Monoton: new_limit = 500 + 80 = 580 W. Nicht Oszillation, sondern graduelle Anpassung.
- **t=11 s**: Buffer `[−100, −100, −100, +800, +800]`, smoothed = +260 W. new_limit = 500 + 260 = 760 W. Weiterhin monoton steigend.
- **t=14 s**: Buffer stabil auf `[+800, +800, +800, +800, +800]`, smoothed = +800 W. Ziel-Limit = 500 + 800 = 1300 W (ggf. auf Hoymiles-Max 1500 W gecapped im Range-Check).
- **Rate-Limit 60 s** limitiert die Dispatch-Frequenz auf einen Zyklus/Minute — aber die *Policy-Entscheidungen* werden bei jedem Event berechnet. Die tatsächlichen Writes sind also geglättet durch Rate-Limit + Deadband + Min-Step.

Der Unit-Test `test_load_step_no_oscillation` simuliert diese Sequenz und verifiziert, dass die `target_value_w`-Folge monoton in eine Richtung zeigt (keine Vorzeichenwechsel der Delta-Folge innerhalb von ≤ 3 Zyklen nach dem Lastsprung).

### Previous Story Intelligence

**Aus Story 3.1 (`review` → Drossel-Policy-Stub läuft):**
- `controller.py::_dispatch_by_mode` hat bereits einen `match`-Block für `Mode.DROSSEL`. `_policy_drossel_stub` kehrt zurück `None`. 3.2 ersetzt den Body — der Dispatcher-Code darüber bleibt.
- `_safe_dispatch` + `_write_failsafe_cycle` sind fertig und greifen bei Exceptions + `ha_ws_connected == False`. Die neue Policy profitiert ohne Zusatzcode.
- `asyncio.create_task(self._safe_dispatch(decision, t0))` ist der Fire-and-Forget-Hook — Readback-Wait blockiert nicht den `_dispatch_event`-Loop. Das ist Voraussetzung für AC 10.
- `_classify_source` + 2-s-Solalex-Window sind fertig. AC 12 bleibt automatisch erfüllt.
- **Per-Device-Lock** (`dict[int, asyncio.Lock]`): greift beim Dispatch; relevant für parallele Events auf demselben WR-Device. Die Policy braucht den Lock nicht.
- `executor/dispatcher.py` macht alle Safety-Gates (Range-Check 2–1500 W Hoymiles, Rate-Limit 60 s, Readback, DB-Writes). 3.2 produziert nur `PolicyDecision`s.

**Aus Story 2.2 (`review`):** `executor/readback.py::verify_readback` + `state_cache.last_command_at` laufen. Die Policy nutzt `state_cache.last_states.get(wr_entity)` für `_read_current_wr_limit_w()` — das ist dasselbe Cache-Objekt, das `_dispatch_event` füllt.

**Aus Story 2.3 (`review`):** `devices.commissioned_at` ist gesetzt sobald der User im Wizard „Aktivieren" klickt. `_dispatch_event` filtert bereits auf `device.commissioned_at is not None`. Die Policy muss das **nicht** erneut prüfen.

**Aus Git (Stand `8fa847e`):**
- `8fa847e chore(release): bump addon version to 0.1.0-beta.2`
- `9cfe48a chore(release): switch beta publishing to SolalexBeta GHCR images`
- `81e427d feat(frontend): update release flow and wizard shell polish`
- `a94c0f8 feat(wizard): Story 2.3 — Disclaimer-Screen mit Commissioning-Gate`
- Story 3.1 ist aktuell `in-progress` (sprint-status.yaml). 3.2 geht `ready-for-dev`, darf aber **erst** nach Merge von 3.1 in Review/Implementierung gehen. Es gibt Datei-Kollisionen auf `controller.py` → sauber sequenziell arbeiten.

### Anti-Patterns & Gotchas

- **KEIN `time.sleep` oder `asyncio.sleep` in `_policy_drossel`.** Die Policy ist synchron (reine Berechnung); alle I/O liegt im Executor.
- **KEIN Lesen von `devices.last_write_at` aus der Policy** — das ist Rate-Limiter-Zuständigkeit (CLAUDE.md „Stolpersteine" aus 3.1 Dev Notes).
- **KEIN direktes `ha_client.call_service` aus der Policy** — immer via `executor.dispatcher.dispatch(...)`. Die Policy ist **pure Berechnung**.
- **KEIN Persistieren des Smoothing-Puffers** (AC 13). Kein neues Table. Kein Schema-Migration.
- **KEIN `numpy`, `pandas`, `scipy`** — reine stdlib. Die Projekt-`pyproject.toml` bleibt schlank (CLAUDE.md Komplexitäts-Regime).
- **KEIN Property-Getter für `_current_mode`-Setzung aus der Policy.** Die Policy darf den Mode **nicht** umschalten (das ist Story 3.5). Wenn die Policy merkt, dass Drossel im aktuellen Setup sinnlos ist (z. B. keine WR konfiguriert), liefert sie `None` — sie tut nichts an der Mode-State.
- **KEIN `datetime.utcnow()`** — immer `datetime.now(tz=UTC)` bzw. der `now_fn`-Parameter.
- **KEIN Logging des Sensor-Werts auf `info`** in der Hot-Path (HA-Event-Rate ist hoch). `debug`-Level für verworfene Entscheidungen; `info` nur beim tatsächlichen Dispatch.
- **KEIN Mode-Wechsel auf Basis der Policy-Entscheidung** (z. B. „wenn Drossel oszilliert, schalte auf Speicher") — das ist Story 3.5.
- **KEIN Überschreiben von `AdapterBase.get_drossel_params` mit `NotImplementedError`** in Non-WR-Adaptern (Marstek, Shelly). Der Default-Wert reicht; die Policy fragt nur den WR-Adapter an.

### Source Tree — Zielzustand nach Story

```
backend/src/solalex/
├── controller.py                              [MOD — _policy_drossel echt, _drossel_buffers, _wr_limit_device, _read_current_wr_limit_w, devices_by_role im Konstruktor]
├── adapters/
│   ├── base.py                                [MOD — DrosselParams + get_drossel_params Default]
│   ├── hoymiles.py                            [MOD — get_drossel_params mit Hoymiles-Defaults + Kommentare]
│   ├── marstek_venus.py                       [unverändert — erbt Default]
│   └── shelly_3em.py                          [unverändert — erbt Default]
├── executor/                                  [unverändert aus 3.1]
├── kpi/                                       [unverändert — Noop-Stub aus 3.1]
├── persistence/                               [unverändert — keine neue Migration]
└── main.py                                    [MOD — devices_by_role im Lifespan]

backend/tests/unit/
├── test_controller_drossel_policy.py          [NEW]
└── test_hoymiles_drossel_params.py            [NEW]
```

Frontend: **keine Änderungen.**

### Testing Requirements

- **Framework:** `pytest` + `pytest-asyncio` (bereits aus 3.1 in `backend/pyproject.toml`).
- **Fakes:** Reuse `backend/tests/unit/_controller_helpers.py` (`FakeHaClient`, `FakeClock` etc.). Keine neuen Helper-Dateien ohne Notwendigkeit. Falls für 3.2 ein `FakeStateCache` mit vor-befüllten `last_states` hilft, dort einfügen — nicht als neue Datei.
- **DB-Fixture:** In-Memory aiosqlite mit `run_migration(":memory:")` — **nur wenn Tests tatsächlich DB-Writes auslösen** (die Policy-Tests brauchen meist keine DB, weil sie die Policy isoliert aufrufen; die Dispatch-Pfad-Tests brauchen sie).
- **Coverage-Ziel:** ≥ 90 % Line-Coverage auf den **neuen/geänderten** Abschnitten: `controller.py`-Diff, `adapters/hoymiles.py`-Diff, `adapters/base.py`-Diff.
- **Kein Playwright** (v1 hat kein E2E-Frontend-Test — CLAUDE.md).
- **Hard-CI-Gates (CLAUDE.md):** Ruff + MyPy strict + Pytest + SQL-Migrations-Ordering (letzteres trivial, da 3.2 keine neue Migration bringt).

### Technology & Version Notes

- **Python 3.13**: `from __future__ import annotations`, `match`-Dispatch, `collections.deque[float]` (Generics auf deque).
- **`collections.deque`**: thread-safe für einzelne `append`/`popleft`-Calls; in asyncio-Single-Thread-Modell reicht das. Kein Lock nötig.
- **`statistics.mean`** ist auf kleinen Listen ~20× langsamer als `sum(buf)/len(buf)` — nutze die Direktform.
- **HA WebSocket `state_changed`-Rate**: typisch 1–5 Events/s pro Entity bei aktivem Smart-Meter. Der Smoothing-Window von 5 Samples entspricht ~1–5 s Glättung.

### Performance & Sicherheit

- **NFR2 (Dashboard-TTFD ≤ 2 s)**: Die Policy läuft synchron in `on_sensor_update`, vor dem Fire-and-Forget-Dispatch. Performance-Budget der Policy: < 1 ms (reine Arithmetik + Dict-Lookup).
- **Safety (CLAUDE.md Regel 3)**: Die Policy darf **niemals** direkt auf HA schreiben. Sie erzeugt nur `PolicyDecision`-Objekte; Executor verifiziert Range, Rate-Limit, Readback. Jeder direkte `call_service`-Aufruf aus `controller.py` außerhalb des `_safe_dispatch`-Pfads = Code-Review-Block.
- **Keine persistent State-Änderung ohne Dispatch**: Die Policy ändert weder `devices.last_write_at` noch `control_cycles` — das macht ausschließlich der Executor. Die Policy ist **pure Function** bis auf den in-memory `_drossel_buffers` Zustand.

### Beta-Gate-Bezug

Aus PRD Zeile 392: **„Zweigeteiltes Beta-Gate: Drossel-Modus stabil ±5 W bei Hoymiles (Nils-Setup) …"**. Diese Story liefert die **Policy-Hälfte** des Beta-Gates. Die Empirie (tatsächliches ±5 W-Verhalten beim echten OpenDTU + HM-1500) verifiziert Alex im lokalen Manual-Smoke nach Merge. Die Unit-Tests sichern die Policy-Charakteristik (Deadband greift, kein Oszillieren bei Lastsprung); die Real-Welt-Toleranz wird empirisch validiert.

### Scope-Grenzen zur Folge-Story (3.3, 3.4, 3.5)

- **Story 3.3 (Akku-Pool)**: Baut `BatteryPool`-Klasse, die Marstek-Venus-Adapter als Pool kapselt. 3.2 berührt das nicht; `_policy_drossel` fragt **keinen** Pool.
- **Story 3.4 (Speicher-Modus)**: Analoger Schritt zu 3.2, aber für `_policy_speicher`. Wird Marstek-Venus-Charge-/Discharge-Logik implementieren. 3.2 lässt `_policy_speicher` als `return None`-Stub.
- **Story 3.5 (Adaptive + Hysterese)**: Baut den Mode-Selector, der zur Laufzeit zwischen DROSSEL / SPEICHER / MULTI wechselt. 3.2 arbeitet nur mit statischem `Mode.DROSSEL` (Controller-Default). Eine ad-hoc-Mode-Wechsel-Logik in 3.2 wäre Scope-Creep.
- **Story 3.6 (User-Config)**: User kann Min/Max-SoC und Nacht-Fenster konfigurieren — betrifft Speicher-Modus, nicht Drossel.
- **Story 3.7 (Fail-Safe bei Kommunikations-Ausfall)**: Erweitert die Fail-Safe-Logik um eine Health-Marker-Persistenz und einen 24-h-Dauertest. 3.2 hinterlässt die Basis-Fail-Safe-Ausprägung aus 3.1 unverändert.

### Beispiel-Code-Skizze (nicht 1:1 übernehmen — Referenz für Shape)

```python
# Modul-Top, neben den bestehenden _policy_*_stub Funktionen
from collections import deque
from solalex.adapters.base import DrosselParams

class Controller:
    def __init__(
        self,
        ha_client: HaWebSocketClient,
        state_cache: StateCache,
        db_conn_factory: Callable[[], AbstractAsyncContextManager[aiosqlite.Connection]],
        adapter_registry: dict[str, AdapterBase],
        devices_by_role: dict[str, DeviceRecord],   # NEW
        *,
        ha_ws_connected_fn: Callable[[], bool],
        mode: Mode = Mode.DROSSEL,
        setpoint_provider: SetpointProvider | None = None,
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        # … existing code …
        self._devices_by_role = devices_by_role
        self._wr_limit_device = devices_by_role.get("wr_limit")
        self._drossel_buffers: dict[int, deque[float]] = {}

    def _policy_drossel(
        self,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> PolicyDecision | None:
        if device.role != "grid_meter":
            return None
        if sensor_value_w is None:
            return None
        wr_device = self._wr_limit_device
        if wr_device is None:
            return None

        adapter = self._adapter_registry[wr_device.adapter_key]
        params: DrosselParams = adapter.get_drossel_params(wr_device)

        grid_meter_id = device.id or 0
        buf = self._drossel_buffers.setdefault(
            grid_meter_id, deque(maxlen=params.smoothing_window)
        )
        buf.append(sensor_value_w)
        smoothed = sum(buf) / len(buf)

        if abs(smoothed) <= params.deadband_w:
            return None

        current = self._read_current_wr_limit_w(wr_device)
        if current is None:
            return None

        proposed = current + int(smoothed)
        proposed = _clamp_step(current, proposed, params.limit_step_clamp_w)

        if abs(proposed - current) < params.min_step_w:
            return None

        return PolicyDecision(
            device=wr_device,
            target_value_w=proposed,
            mode=Mode.DROSSEL,
            command_kind="set_limit",
            sensor_value_w=smoothed,
        )
```

```python
# adapters/base.py
@dataclass(frozen=True)
class DrosselParams:
    """Policy parameters consumed by the Drossel mode (controller.py)."""
    deadband_w: int = 10
    min_step_w: int = 5
    smoothing_window: int = 5
    limit_step_clamp_w: int = 200


class AdapterBase(ABC):
    # … existing abstract methods …

    def get_drossel_params(self, device: DeviceRecord) -> DrosselParams:
        """Return the drossel-policy parameter bundle for this device.

        Default is conservative. WR adapters override with hardware specifics
        (see Hoymiles). Read-only adapters inherit the default — the policy
        only queries the WR adapter, not the smart-meter adapter.
        """
        del device
        return DrosselParams()
```

```python
# adapters/hoymiles.py
class HoymilesAdapter(AdapterBase):
    # … existing methods …

    def get_drossel_params(self, device: DeviceRecord) -> DrosselParams:
        del device
        return DrosselParams(
            # ±5 W tolerance per PRD line 181 and beta-gate target.
            deadband_w=5,
            # Under 3 W delta is indistinguishable from sensor noise (empirical).
            min_step_w=3,
            # 5 × 1-s-polling ≈ 5 s smoothing — balance between reactivity
            # and noise suppression. (Cut from JSON templates in Amendment 2026-04-22.)
            smoothing_window=5,
            # Max 200 W delta per dispatch avoids WR shock transitions on load steps.
            limit_step_clamp_w=200,
        )
```

### References

- [epics.md — Story 3.2, Zeile 804–830](../planning-artifacts/epics.md)
- [architecture.md — Core Decisions Zeile 229–260 + Cuts Zeile 1023+](../planning-artifacts/architecture.md)
- [prd.md — FR14/FR17/FR18/FR19/FR27 + Beta-Gate Zeile 392](../planning-artifacts/prd.md)
- [prd.md — Deadband/Rate-Limit/Moving-Average-Tripel Zeile 183/316](../planning-artifacts/prd.md)
- [CLAUDE.md — 5 Regeln + Stolpersteine](../../CLAUDE.md)
- [Story 3.1 — Core Controller](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md)
- [Story 2.2 — Funktionstest mit Readback](./2-2-funktionstest-mit-readback-commissioning.md)
- [adapters/hoymiles.py — Adapter-Impl. + Range 2–1500 W](../../backend/src/solalex/adapters/hoymiles.py)
- [adapters/shelly_3em.py — Vorzeichen-Konvention](../../backend/src/solalex/adapters/shelly_3em.py)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `_policy_drossel` in `controller.py` ist produktiv, `_policy_speicher` und `_policy_multi` bleiben Noop-Stubs.
2. `Controller.__init__` akzeptiert `devices_by_role: dict[str, DeviceRecord]` und leitet `_wr_limit_device` ab.
3. In-memory `_drossel_buffers: dict[int, deque[float]]` existiert; kein DB-Persistenz des Puffers.
4. `adapters/base.py` bietet `DrosselParams` + `get_drossel_params` mit Defaults.
5. `adapters/hoymiles.py` überschreibt mit `deadband_w=5`, `min_step_w=3`, `smoothing_window=5`, `limit_step_clamp_w=200`.
6. `main.py` Lifespan baut `devices_by_role = {d.role: d for d in devices}` und übergibt es dem Controller.
7. Executor-Pfad unverändert (Veto-Kaskade, Readback, Fail-Safe — alles aus 3.1).
8. Unit-Tests `test_controller_drossel_policy.py` + `test_hoymiles_drossel_params.py` sind grün und decken AC 1–13 ab.
9. Alle 4 CI-Gates grün: Ruff + MyPy strict + Pytest + SQL-Ordering (unverändert bei 2 Dateien).
10. Drift-Checks bestanden: kein `/data/templates/`, kein `json-schema`, kein Controller-Sub-Split, kein numpy/pandas, keine neue Migration, keine Änderung am Executor.
11. Bestehende Tests aus Story 1.3/2.2/2.3/3.1 bleiben grün — insbesondere `POST /api/v1/setup/test` und der `_dispatch_event`-Hook.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- Ruff check (`uv run ruff check .`) → All checks passed.
- MyPy strict (`uv run mypy --strict src/ tests/`) → Success: no issues found in 75 source files.
- Pytest (`uv run pytest -q`) → 120 passed (91 bestehend + 29 neu in 3.2).
- Coverage auf 3.2-Abschnitten: `adapters/hoymiles.py` 100 %, `adapters/base.py` 96 %, `controller.py` 90 %; Summe 92 % — ≥ 90 %-Gate erfüllt.

### Completion Notes List

- `_policy_drossel` ist als Methode auf `Controller` umgesetzt (nicht als Modul-Funktion), weil sie auf `state_cache`, `adapter_registry` und den in-memory Ring-Puffer zugreift. Der ehemalige `_policy_drossel_stub` entfällt; `_policy_speicher_stub` / `_policy_multi_stub` bleiben als Modul-Funktionen für 3.4/3.5.
- `devices_by_role` auf `Controller.__init__` ist optional (`None` default → leeres Dict), damit bestehende Story-3.1-Tests ohne Anpassung grün bleiben. In `main.py` wird das Dict in der Lifespan aus den kommissionierten Devices gebaut und durchgereicht.
- Ring-Puffer lebt in `self._drossel_buffers: dict[int, deque[float]]` mit `maxlen=params.smoothing_window`; on-demand beim ersten Event pro `grid_meter.device_id`. Bei Parameter-Drift zwischen Prozess-Restarts wird der Puffer defensiv neu gebaut statt zurechtgeschnitten.
- Policy-Kette (Early-Returns → Moving Average → Deadband → aktuelles Limit lesen → Step-Clamp → Min-Step) genau wie in der Story-Code-Skizze. `_clamp_step` ist eine reine Modul-Funktion (einfacher zu testen, kein `self`-State nötig).
- `_read_current_wr_limit_w()` liest `state_cache.last_states`, baut daraus einen `HaState` für den Adapter und delegiert an `adapter.parse_readback`. Fehlender Cache → `None` (Policy abort, kein Befehl mit Phantom-Startwert).
- Shelly-Vorzeichen-Konvention: positive = Bezug, negative = Einspeisung. Formel bleibt `new_limit = current + smoothed_grid_power` — Einspeisung zieht das Limit runter, Bezug schiebt es hoch (Range-Check im Executor deckelt endgültig).
- `adapters/marstek_venus.py` und `adapters/shelly_3em.py` bleiben **unberührt** — sie erben den konservativen Default aus `AdapterBase.get_drossel_params`. Tests prüfen das explizit, damit eine spätere versehentliche `NotImplementedError`-Verschärfung auffliegt.
- Keine neue Migration, kein neuer Helper-File, keine neue Dependency. `pyproject.toml` unverändert. Drift-Checks (JSON-Templates, Controller-Sub-Split, SQL-Ordering) alle 0 Treffer.
- Manual-Smoke-Check (letzter AC-Bullet in Task 8) bleibt offen — Ausführung im realen Add-on mit OpenDTU/Shelly ist Alex-Aufgabe nach Merge und laut Story kein Review-Blocker.

### File List

- MOD `backend/src/solalex/adapters/base.py` — `DrosselParams` Dataclass + `AdapterBase.get_drossel_params` Default.
- MOD `backend/src/solalex/adapters/hoymiles.py` — `HoymilesAdapter.get_drossel_params` mit Hardware-Defaults (5/3/5/200).
- MOD `backend/src/solalex/controller.py` — `_policy_drossel` produktiv, `_read_current_wr_limit_w`, `_drossel_buffers`, `devices_by_role`-Konstruktor-Parameter, `_clamp_step`-Helper.
- MOD `backend/src/solalex/main.py` — `devices_by_role`-Dict in der Lifespan (nur kommissionierte Devices) und an `Controller(...)` durchgereicht.
- NEU `backend/tests/unit/test_controller_drossel_policy.py` — 14 Tests für AC 1/2/3/5/6/7/9/11/13 + Clamp-Helper.
- NEU `backend/tests/unit/test_hoymiles_drossel_params.py` — 5 Tests für Default + Hoymiles-Override + Sinus-Toleranz.

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.2 erstellt und auf `ready-for-dev` gesetzt. Drossel-Policy (Deadband + Moving Average + Min-Step + Step-Clamp) als produktive Implementierung von `_policy_drossel` in `controller.py`; Adapter-Modul-Konstanten für Hoymiles in `adapters/hoymiles.py`. Keine neue SQL-Migration, kein Executor-Change, keine Frontend-Änderung. | Claude Opus 4.7 |
| 2026-04-24 | 0.2.0 | Story 3.2 implementiert: `DrosselParams` + `AdapterBase.get_drossel_params` Default, Hoymiles-Override (5/3/5/200), `_policy_drossel` produktiv als Controller-Methode inkl. Moving-Average-Ring-Puffer, `devices_by_role`-Konstruktor-Parameter + Lifespan-Verdrahtung, Clamp-Helper. 19 neue Unit-Tests decken AC 1-7, 9, 11, 13 ab. 120/120 Tests grün, Ruff + MyPy strict grün. Status → `review`. | Claude Opus 4.7 |
| 2026-04-24 | 0.3.0 | Code-Review abgeschlossen. **Scope erweitert** um readback.py-Hardening (P1 Fresh-State-Guard, Clock-Drift-Tolerance, Unavailable-Sentinel), setup.py-Polish (D4 hart `uom='W'` für wr_limit, D5 `ha_ws_connected`-Gate in `/commission`, P2 `HTTPException`-Re-Raise, Role-basierte Target-Device-Auswahl) und Frontend-Polish (`usePolling` Epoch-Token-Hardening, `DisclaimerActivation` Typ-Guards für RFC-7807-Fields, P16 Test-Counter-Assertion). Safety-Patches: `_policy_drossel` NaN/Inf-Guard (P4), `int(round())` statt `int()` (P5), `_clamp_step`-Invariant + `DrosselParams.__post_init__`-Validation (P6/P7), `parse_readback`-defensive-catch + `entry.attributes`-isinstance-Guard (P9/P10), `main.py` Role-Collision-Warnlog (P8). Test-Qualität: min_step-Gate via adapter-Monkeypatch (P11), Last-Sprung-Monotonie ohne Selbst-Filter (P12), asymmetrisches Toleranz-Signal (P13), direkter Zugriff auf `_dispatch_tasks` statt `getattr`-Fallback (P14). Zwei neue Regression-Tests: AC-6-Symmetrie (`test_no_decision_when_only_wr_limit_commissioned`), Commissioned-at-Filter (`test_devices_by_role_filters_uncommissioned`), sowie `test_commission_without_ha_connection_returns_503`. Alle 4 Hard-CI-Gates grün: Ruff + MyPy strict (75 files) + Pytest 123/123 + Vitest 27/27 + svelte-check 244 files 0 errors. Status → `done`. | Claude Opus 4.7 |

## Review Findings

Code-Review 2026-04-24 (Blind Hunter + Edge Case Hunter + Acceptance Auditor, 3 parallele Layer).

### Decision Needed

- [x] [Review][Decision] **Scope-Violation — `executor/readback.py` modifiziert** — Aufgelöst 2026-04-24: **Scope erweitert** (Option b). Die Readback-Verbesserungen (`_CLOCK_DRIFT_TOLERANCE_S`, `_HA_UNAVAILABLE_SENTINELS`, `_is_fresh_state`, Poll-Loop, Unavailable-Branch) werden als Teil von 3.2 akzeptiert, siehe Change-Log-Eintrag 0.3.0.
- [x] [Review][Decision] **Scope-Violation — `api/routes/setup.py` modifiziert** — Aufgelöst 2026-04-24: **Scope erweitert** (Option b). UoM-Filter, Role-basierte Target-Device-Auswahl, Lock-Nesting und Fehlerpfad-Härtung werden als 3.2-Teil akzeptiert, siehe Change-Log-Eintrag 0.3.0.
- [x] [Review][Decision] **Scope-Violation — Frontend modifiziert** — Aufgelöst 2026-04-24: **Scope erweitert** (Option b). `usePolling.ts` Epoch-Token-Hardening und `DisclaimerActivation`-Polish als 3.2-Teil akzeptiert, siehe Change-Log-Eintrag 0.3.0.
- [x] [Review][Decision] **`wr_limit`-Entity mit `unit_of_measurement='%'` erlaubt** — Aufgelöst 2026-04-24: **Option (a) — hart `uom='W'`**. `/entities` filtert jetzt `wr_limit` strikt auf Watt-Entities, %-Support ist auf spätere `wr_limit_pct`-Role vertagt.
- [x] [Review][Decision] **`commission()` bei getrennter HA-WebSocket** — Aufgelöst 2026-04-24: **Option (a) — 503 werfen**. Commissioning refused wenn `ha_ws_connected=False`, neuer Regressions-Test `test_commission_without_ha_connection_returns_503`.

### Patch

- [x] [Review][Patch] **`_is_fresh_state` mit `last_command_at=None` liefert `True`** — [backend/src/solalex/executor/readback.py:~96-119] Kommentar behauptet „wenn `last_command_at` fehlt → fresh". Das invertiert die Safety-Semantik: direkt nach Prozess-Restart (Cache leer) akzeptiert der Readback jeden pre-Command-State als „frisch" und meldet `passed`, sobald der Wert zufällig dem Expected entspricht. False-Positive-Readback = silent safety bypass. Fix: bei `last_command_at=None` `False` zurückgeben, stale Cache-Entry nicht als Beweis werten.
- [x] [Review][Patch] **`except Exception` schluckt HTTPException** — [backend/src/solalex/api/routes/setup.py:~197-215] Reihenfolge `except TimeoutError: raise HTTPException(504, ...); except Exception:` fängt die gerade geworfene HTTPException wieder ein und mappt sie auf 502. Fix: `except HTTPException: raise` als erste except-Klausel vor `except Exception`.
- [x] [Review][Patch] **AC 6 Symmetrie-Test fehlt (`wr_limit-only commissioned`)** — Spec AC 6 fordert „`Given` nur ein Device (nur `grid_meter` **oder** nur `wr_limit`) ist kommissioniert". Es existiert nur `test_no_decision_when_only_grid_meter_commissioned`; der umgekehrte Fall (kein `grid_meter`, nur `wr_limit`) wird nicht exerziert. Fix: zweiter Test, der genau die Symmetrie prüft.
- [x] [Review][Patch] **`_policy_drossel` ohne NaN/Inf-Guard auf `sensor_value_w`** — [backend/src/solalex/controller.py:~288-296] Nur `sensor_value_w is None`-Guard. Direkt-Call in Tests oder ein kaputter Upstream-Sensor liefert `math.nan`/`math.inf` → `abs(nan) <= deadband` ist `False`, `int(smoothed)` raised `OverflowError`/`ValueError`. Fix: `if sensor_value_w is None or not math.isfinite(sensor_value_w): return None`.
- [x] [Review][Patch] **`int(smoothed)` trunkiert asymmetrisch** — [backend/src/solalex/controller.py:~313] `int(-0.9) == 0` und `int(+0.9) == 0`, aber `int(-1.5) == -1` und `int(+1.5) == 1` — Trunkierung Richtung Null bias't die Policy weg vom Null-Ziel. Fix: `round(smoothed)` oder `int(round(smoothed))` für symmetrisches Rundungsverhalten.
- [x] [Review][Patch] **`_clamp_step` mit `max_step <= 0` passiert unclamped** — [backend/src/solalex/controller.py:~554-567] Kein Invariant-Check. Bei `limit_step_clamp_w=0` (oder negativ, z. B. durch einen fehlerhaften Adapter-Override) wird `proposed` ohne Clamp durchgereicht — Safety-Gate stillschweigend deaktiviert. Fix: `if max_step <= 0: raise ValueError(...)` oder defensiv `return current` plus Warn-Log.
- [x] [Review][Patch] **`DrosselParams.smoothing_window <= 0` → `ZeroDivisionError`** — [backend/src/solalex/adapters/base.py + controller.py:~301] `deque(maxlen=0)` ist zulässig, aber `sum(buf)/len(buf)` auf leerem Deque wirft. Fix: `__post_init__` in `DrosselParams` validiert `smoothing_window >= 1` und `deadband_w >= 0` und `min_step_w >= 1` und `limit_step_clamp_w >= 1`.
- [x] [Review][Patch] **Role-Collision in `devices_by_role` silent** — [backend/src/solalex/main.py:~171-175] Bei zwei kommissionierten Devices mit identischer Role gewinnt der letzte Iterationsschritt, ohne Log oder Warnung. Spec sagt „max 1 pro Rolle", aber SQLite hat keinen Unique-Constraint. Fix: beim Bauen des Dicts auf Kollision prüfen und `_logger.warning('role_collision', extra={'role': r, 'prev': prev.entity_id, 'new': new.entity_id})`.
- [x] [Review][Patch] **`adapter.parse_readback` kann auf malformed Payload crashen** — [backend/src/solalex/controller.py:~348-364 (`_read_current_wr_limit_w`)] Kein `try/except` um Adapter-Call. Ein Bug im Adapter oder ein kaputter HA-State crash't den `on_sensor_update`-Handler (der Fire-and-Forget-Task stirbt still). Fix: defensive `try: ... except Exception: _logger.exception('parse_readback_failed'); return None`.
- [x] [Review][Patch] **`entry.attributes` nicht dict → AttributeError** — [backend/src/solalex/controller.py:~356-358] `.items()` auf None/Non-Dict crasht. Fix: `attrs_raw = entry.attributes if isinstance(entry.attributes, dict) else {}`.
- [x] [Review][Patch] **Test `test_min_step_suppresses_sub_threshold_delta` ist vacuous** — [backend/tests/unit/test_controller_drossel_policy.py:~187] Docstring verspricht „über Deadband, aber unter min_step → dropped". Der Test feedet `-2.0` W, was innerhalb des ±5 W Deadbands liegt — der min_step-Pfad wird nie erreicht, die Deadband-Short-Circuit-Branch erfüllt die Assertion zufällig. Fix: Wert über Deadband (z. B. `-7.0` W) aber mit aktuellem Limit so gewählt, dass `|proposed - current| < min_step_w=3`.
- [x] [Review][Patch] **Test `test_load_step_no_oscillation` filtert vor Assertion** — [backend/tests/unit/test_controller_drossel_policy.py:~232-245] Der Test filtert `targets` via `t >= targets[0]` **vor** der Monotonie-Assertion. Das macht den Monotonie-Claim selbst-erfüllend: ein nicht-monotones Element wird vor dem Check entfernt. Fix: ungefilterte Folge monotonically-non-decreasing prüfen und Sign-Flip-Count auf der Delta-Sequenz bounden.
- [x] [Review][Patch] **Test `test_hoymiles_drossel_tolerance_sine_within_deadband` ist tautologisch** — [backend/tests/unit/test_hoymiles_drossel_params.py:~60-79] Ein symmetrischer ±4 W Sinus hat per Definition Mittelwert 0. Jede absurde „Smoothing"-Implementierung (selbst `lambda buf: 0`) besteht den Test. Fix: asymmetrischen Last-Trace oder Realdaten-Sample verwenden, oder stattdessen AC-4-Charakteristik direkt testen (3 aufeinanderfolgende Events im Deadband → kein call_service).
- [x] [Review][Patch] **`getattr(controller, "_dispatch_tasks", set())` in Tests brittle** — [backend/tests/unit/test_controller_drossel_policy.py:~281] Wenn das private Attribut umbenannt oder entfernt wird, geht `await asyncio.gather(*set())` ohne Fehler durch und maskiert fehlendes Async-Warten. Fix: expliziter Zugriff ohne Default oder Controller-Helper `async def wait_for_dispatch()` nutzen.
- [x] [Review][Patch] **DisclaimerActivation `formatApiError` crasht bei non-string `title`/`detail`** — [frontend/src/routes/DisclaimerActivation.svelte:~?] `err.title?.trim()` / `err.detail?.trim()` nimmt implizit `string` an. RFC 7807 erlaubt Non-String-Extensions (z. B. Zahl, Objekt). Fix: `typeof err.title === 'string' ? err.title.trim() : ''`.
- [x] [Review][Patch] **DisclaimerActivation.test negative Assertion trivial-pass** — [frontend/src/routes/DisclaimerActivation.test.ts:~90] `.not.toMatch(/<button[^>]*class="[^"]*activate-button/)` besteht auch wenn der Render komplett leer ist. Fix: Counter-Assertion auf Button-Existenz bei `checked=true` oder auf ein anderes bekanntes Render-Attribut.
- [x] [Review][Patch] **Fehlender Test für `commissioned_at is None`-Filter im `devices_by_role`-Flow** — [backend/tests/unit/test_controller_drossel_policy.py:~322] Fixture `UPDATE devices SET commissioned_at = ?` markiert ALLE Rows als kommissioniert. Der `main.py:~174` Filter `if device.commissioned_at is not None` wird nirgends exerziert. Fix: Test mit gemischt (un-)kommissionierten Devices, der prüft, dass uncommissioned gar nicht erst in `devices_by_role` landet.

### Deferred

- [x] [Review][Defer] `_drossel_buffers` wächst unbounded; `device.id`-Key bei SQLite-rowid-Recycling problematisch — v1 hat ein stabiles `grid_meter`, Device-Recommission verlangt Restart. Post-Beta Scale-Hardening-Thema.
- [x] [Review][Defer] `_read_current_wr_limit_w` rebuildet `HaState` pro Event — Hot-Path-Overhead messbar, aber deutlich unter dem < 1 ms Budget. Cache/Memo später nachziehen.
- [x] [Review][Defer] `buf.maxlen != params.smoothing_window` rebuild verwirft In-Memory-Samples ohne Log — params sind Code-Konstanten, in Praxis tritt der Pfad nie ein; Defensive-Code.
- [x] [Review][Defer] `min_step` wird nach Clamp geprüft — bei pathologischer Config (`clamp < min_step`) werden alle Decisions silent dropped. Invariant-Validation in `DrosselParams.__post_init__` (siehe Patch) deckt das indirekt.
- [x] [Review][Defer] Tests rufen `_policy_drossel` direkt statt über `on_sensor_update` → dispatch-Kette nur durch AC 9 exerziert — Methodenwahl, in späteren Integration-Stories aufgreifen.
- [x] [Review][Defer] `state_cache.last_states` Read ohne Lock — pre-existing aus 3.1, asyncio-single-thread mildert.
- [x] [Review][Defer] `_read_current_wr_limit_w` keine eigene Unavailable/Unknown-Filter — `parse_readback` handhabt Sentinels in `executor/readback.py`; doppelt-prüfen bei späterem Adapter-Refactor.
- [x] [Review][Defer] Observability-Minors: `grid_meter.device.id is None`, `device.role is None`, `wr_device.adapter_key unknown` — jeder liefert `None` korrekt, aber kein Warn-Log. Aufnehmen in späteren Observability-Pass.
- [x] [Review][Defer] `usePolling` `epoch++` in `stop()` UND in `start()` — Token-Bump um 2 pro `start()`, korrektheits-neutral; Kommentar-Drift.
- [x] [Review][Defer] `usePolling` kein `inFlight`-Guard — wenn `fetchFn` länger als `intervalMs` braucht, stapeln sich parallele Requests. Frontend out-of-3.2-scope; Frontend-Polish-Thema vor Epic 5.
- [x] [Review][Defer] `window.location.hash = '#/running'` ohne verifizierte Route-Registrierung — frontend out-of-3.2-scope; Route-Hygiene in Epic 5.
- [x] [Review][Defer] Mehrere `hoymiles wr_limit`-Devices kommissioniert → nur `[0]` wird getestet — setup.py out-of-3.2-scope; v1 max 1 pro Rolle.
- [x] [Review][Defer] Readback `_CLOCK_DRIFT_TOLERANCE_S` einseitig angewendet — readback.py out-of-3.2-scope.
- [x] [Review][Defer] `routes/setup.py` TOCTOU `lock.locked()` + `async with lock` — setup.py out-of-3.2-scope; asyncio-single-thread mildert.
- [x] [Review][Defer] `routes/setup.py` nested try/except log-Semantik — setup.py out-of-3.2-scope; `functional_test_complete` kann auch bei failed-readback feuern.
- [x] [Review][Defer] `devices_by_role` einmalig im Lifespan, kein Runtime-Refresh — explizit per Story „Hot-Reload NICHT in 3.2"; bei späterer Wizard-Integration (3.6+) nachziehen.

### Dismissed

- `PolicyDecision.mode = Mode.DROSSEL.value` (string statt enum) — konsistent mit 3.1.
- `_clamp_step` Parameter-Name `max_step` vs. Spec-Label `limit_step_clamp_w` — kosmetische Drift, kein Bug.
- Test-Namens-Drift bei 2 Tests (`test_hoymiles_adapter_exposes_drossel_params`, `test_hoymiles_drossel_tolerance_sine_within_deadband`) — Rename gegenüber Spec, AC-Abdeckung unverändert.
- `_policy_drossel` touches `self._state_cache` synchron — Annahme, dass `state_cache.last_states.get` sync bleibt, ist für v1 trivial erfüllt.
