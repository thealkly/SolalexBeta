# Story 3.2: Drossel-Modus — WR-Limit-Regelung für Nulleinspeisung

Status: ready-for-dev

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

- [ ] **Task 1: `AdapterBase.get_drossel_params()` + `DrosselParams` Dataclass** (AC: 8)
  - [ ] `adapters/base.py` um `@dataclass(frozen=True) class DrosselParams` erweitern mit Feldern:
    - `deadband_w: int` — Breite des Null-Punkts, innerhalb derer nicht dispatched wird.
    - `min_step_w: int` — minimale Delta zwischen aktuellem und neuem Limit, sonst Noop (Glättungs-Schutz).
    - `smoothing_window: int` — Anzahl Sensor-Samples im Moving Average.
    - `limit_step_clamp_w: int` — maximal erlaubte Änderung pro Dispatch (gegen Überschwingen, Default 200 W).
  - [ ] `AdapterBase.get_drossel_params(self, device) -> DrosselParams` mit Default (z. B. `deadband_w=10`, `min_step_w=5`, `smoothing_window=5`, `limit_step_clamp_w=200`); Subclasses überschreiben.
  - [ ] `NotImplementedError` NICHT werfen im Default — die Policy fragt generisch; Nicht-WR-Adapter überschreiben mit `raise NotImplementedError` nicht nötig, weil der Aufrufer (Drossel-Policy) den Adapter nur für `wr_limit`-Role-Devices abfragt.

- [ ] **Task 2: Hoymiles-Adapter — Drossel-Parameter + Kommentare** (AC: 4, 8)
  - [ ] `adapters/hoymiles.py`: Modul-Konstanten oder `DrosselParams`-Instanz mit:
    - `deadband_w=5` (Architecture Zeile 181, „Hoymiles/OpenDTU ±5 W")
    - `min_step_w=3` (empirisch: unter 3 W ist Signal im Sensor-Rauschen)
    - `smoothing_window=5` (Balance zwischen Reaktivität und Rausch-Unterdrückung; 5 × 1-s-Polling ≈ 5 s Glättung)
    - `limit_step_clamp_w=200` (verhindert WR-Schock-Transitionen bei Lastsprung)
  - [ ] `get_drossel_params` gibt diese Werte zurück. Pro Feld ein One-Liner-Kommentar mit Quelle.
  - [ ] **Keine** JSON-Datei, **kein** `load_from_template()`-Call, **kein** externes File-Laden.

- [ ] **Task 3: Marstek / Shelly — Drossel-Parameter (Smoke-Overrides)** (AC: 8)
  - [ ] `adapters/marstek_venus.py`: `get_drossel_params` erbt vom Default — Drossel-Modus schaltet in 3.2 nicht auf Akkus; wird in Story 3.4/3.5 relevant (Mode-Wechsel). Kein Code-Add nötig **außer** Test-Stub, der bestätigt, dass der Default greift.
  - [ ] `adapters/shelly_3em.py`: Smart-Meter ist kein Write-Target; `get_drossel_params` erbt Default — **nicht** `NotImplementedError` werfen (die Policy fragt den **WR**-Adapter, nicht den SM-Adapter).

- [ ] **Task 4: `controller.py` — Drossel-Policy produktiv** (AC: 1, 2, 3, 6, 7, 9, 10, 13)
  - [ ] Ersetze `_policy_drossel_stub` durch eine richtige Policy-Funktion/Methode `_policy_drossel(self, device, sensor_value_w) -> PolicyDecision | None`. Die Stubs für `_policy_speicher` / `_policy_multi` bleiben `return None` (Story 3.4/3.5).
  - [ ] Controller hält pro `device_id` (des `grid_meter`) einen **`collections.deque`** mit `maxlen=smoothing_window` als Moving-Average-Puffer. In-Memory, nicht persistent (AC 13).
  - [ ] **Early-Returns** in `_policy_drossel` (in dieser Reihenfolge):
    1. `device.role != 'grid_meter'` → `None` (AC 7, nur SM-Events triggern die Drossel-Berechnung).
    2. `sensor_value_w is None` → `None` (kein brauchbares Messsignal, z. B. `unavailable`).
    3. `self._wr_limit_device is None` → `None` (AC 6, Konfiguration unvollständig).
  - [ ] Shelly-Vorzeichen-Konvention: `shelly_3em.parse_readback` liefert **positive Werte = Bezug, negative Werte = Einspeisung** (siehe Adapter-Kommentar). Drossel reagiert auf **negative** Werte (Einspeisung → WR drosseln). Die Berechnung in 3.2:
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
  - [ ] `_read_current_wr_limit_w()` liest aus `state_cache.last_states.get(wr_device.entity_id)` und nutzt `hoymiles.parse_readback(state)` → `int | None`. Fallback: wenn kein State gecached, liefert die Policy `None` (besser keinen Befehl als einen mit falschem Ausgangs-Limit).
  - [ ] Der **Dispatch-Punkt** ist unverändert `_dispatch_by_mode(...)` aus 3.1 — nur der `Mode.DROSSEL`-Case ruft jetzt die echte Policy auf. Der `match`-Block bleibt strukturell gleich.
  - [ ] **Kein** neuer `subscribe`-Call für grid_meter — Story 1.3/2.2/3.1 stellen die Subscription bereits her (jedes kommissionierte Device wird subscribed). Die Policy konsumiert nur den Event-Strom, den der bestehende `_dispatch_event` in `main.py` liefert.

- [ ] **Task 5: `Controller`-Konstruktor — `devices_by_role`-Lookup** (AC: 1, 6, 7)
  - [ ] `Controller.__init__` bekommt einen zusätzlichen Parameter `devices_by_role: dict[str, DeviceRecord]`. Alternative (wenn du es flexibler magst): `devices_by_role_fn: Callable[[], dict[str, DeviceRecord]]` — **bevorzugt Direkt-Dict**, weil in v1 die Device-Konfiguration zur Startup-Zeit fix ist (Story 2.x).
  - [ ] `controller.py` leitet daraus `self._wr_limit_device: DeviceRecord | None = devices_by_role.get('wr_limit')` und `self._grid_meter_device = devices_by_role.get('grid_meter')` ab.
  - [ ] **Hot-Reload NICHT in 3.2.** Wenn der User die Device-Konfiguration ändert, ist ein Add-on-Neustart nötig — das ist Wizard-/Config-Page-Scope (Epic 2), nicht 3.2.
  - [ ] `main.py` Lifespan baut das `devices_by_role`-Dict parallel zu `devices_by_entity` (gleicher Durchlauf) und übergibt es an den `Controller(...)`.

- [ ] **Task 6: `main.py` Integration — devices_by_role bereitstellen** (AC: 1, 6)
  - [ ] In `lifespan(...)` das Dict `devices_by_role: dict[str, DeviceRecord] = {d.role: d for d in devices}` bauen (v1: max. 1 Device pro Rolle, siehe PRD Zeile 223).
  - [ ] An `Controller(...)` durchreichen. Keine weitere API-Änderung in `main.py`.
  - [ ] **Keine Änderung** an `_dispatch_event` — die Role-Filterung passiert **innerhalb** von `_policy_drossel` (AC 7).

- [ ] **Task 7: Unit-Tests — Drossel-Policy + Hoymiles-Params** (AC: 14)
  - [ ] `backend/tests/unit/test_controller_drossel_policy.py` — siehe AC 14, enthält **alle** dort aufgelisteten Test-Fälle.
  - [ ] `backend/tests/unit/test_hoymiles_drossel_params.py` — Adapter-Default + Toleranz-Sinus.
  - [ ] Reuse `backend/tests/unit/_controller_helpers.py` (aus 3.1) für `FakeHaClient`, `FakeClock`, In-Memory-DB-Fixture. **Keine** neuen Helper-Dateien ohne Notwendigkeit.
  - [ ] Tests verwenden `Controller(...)` direkt (nicht via `main.py`). `devices_by_role` wird per Fixture bereitgestellt (ein `wr_limit` + ein `grid_meter` Device).
  - [ ] Coverage-Messung via `pytest --cov=solalex.controller --cov=solalex.adapters.hoymiles` muss ≥ 90 % Line-Coverage auf den **in 3.2 geänderten** Abschnitten zeigen.

- [ ] **Task 8: Final Verification** (AC: 14)
  - [ ] `uv run ruff check .` → grün.
  - [ ] `uv run mypy --strict src/ tests/` → grün.
  - [ ] `uv run pytest -q` → grün (alle bestehenden 91 Tests + neue Drossel-Tests).
  - [ ] SQL-Ordering: unverändert (`001_initial.sql` + `002_control_cycles_latency.sql`) — **keine neue Migration in 3.2**.
  - [ ] Drift-Check: `grep -rE "/data/templates|load_json_template|json-schema" backend/src/solalex/` → 0 Treffer.
  - [ ] Drift-Check: `grep -rE "drossel\.py$|speicher\.py$|multi\.py$|mode_selector\.py$|pid\.py$|failsafe\.py$" backend/src/solalex/` → 0 Treffer (Controller bleibt Mono-Modul).
  - [ ] Manual-Smoke lokal im HA-Add-on mit einem Shelly 3EM + einem OpenDTU-WR offen — Ausführung durch Alex; kein Blocker für Review.

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.2 erstellt und auf `ready-for-dev` gesetzt. Drossel-Policy (Deadband + Moving Average + Min-Step + Step-Clamp) als produktive Implementierung von `_policy_drossel` in `controller.py`; Adapter-Modul-Konstanten für Hoymiles in `adapters/hoymiles.py`. Keine neue SQL-Migration, kein Executor-Change, keine Frontend-Änderung. | Claude Opus 4.7 |
