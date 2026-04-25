# Story 3.5: Adaptive Strategie-Auswahl & Hysterese-basierter Modus-Wechsel (inkl. Multi-Modus)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Nutzer mit hybridem Setup (WR + Multi-Akku),
I want dass Solalex meine Regelungs-Strategie automatisch aus dem erkannten Hardware-Setup ableitet und zwischen Drossel / Speicher / Multi-Modus ohne Oszillation wechselt,
so that ich nie einen Modus manuell einstellen muss und im Grenzbereich (Akku-knapp-voll) kein Flackern entsteht.

**Scope-Pflock:** Diese Story ergänzt zwei orthogonale Bausteine zum Mono-Modul `controller.py`:
1. **Initial-Modus-Selektor** — Startup-Funktion, die aus `devices_by_role` + `battery_pool` den Default-Modus ableitet (heute hardcoded `Mode.DROSSEL`).
2. **Adaptive Mode-Switching** — Per-Sensor-Event-Auswertung mit SoC-Hysterese (97/93 %), Mindest-Verweildauer (60 s) und Audit-Log-Cycle. Plus Multi-Modus-Policy (`_policy_multi`), die heute nur Stub `[]` ist.

**Amendment Story-3.5-A1 (User-Override, 2026-04-25):** Beta-Phase ergänzt einen **manuellen Mode-Override via UI**. Auswahl in Config-Seite: „Automatisch / Drossel / Speicher / Multi". Bei aktivem Override wird der Selector ignoriert und die Hysterese-Auswertung **deaktiviert** (User-Wille schlägt Auto). Persistenz in `meta`-Tabelle (Key `forced_mode`); runtime-update via `PUT /api/v1/control/mode`. Override `null|"auto"` aktiviert wieder Auto-Detection + Hysterese. **Begründung:** Beta-Tester brauchen das Override für Reproduzierbarkeit von Bug-Reports und für Setups, die der Selector nicht treffsicher klassifiziert (z. B. zeitweise offline-Akku). PRD Zeile 362 („Mode = Erkennung, kein Config-Item") gilt für den Default-User-Flow; das Override ist Beta-Eskalations-Pfad und bleibt in v1 sichtbar (kein Hidden-Toggle).

**Was diese Story NICHT tut:**
- Keine Änderung an `_policy_drossel` oder `_policy_speicher` (3.2/3.4 fertig).
- Kein Pool-Refit, keine Adapter-Param-Erweiterung.
- Keine Frontend-Animation des Modus-Übergangs (Story 5.5).
- Kein User-Config-UI für Min/Max-SoC oder Nacht-Entlade-Fenster (Story 3.6).
- Kein Fail-Safe-Recovery / Healthchecks (Story 3.7).

**Amendment 2026-04-22 (verbindlich):** Mode-Selector + Hysterese-Helper + Multi-Policy bleiben **inline in `controller.py`**. Kein `mode_selector.py`, kein `policies/multi.py`, kein `controller/`-Submodul. Architecture Cut 9 + CLAUDE.md Stolperstein-Liste.

**Scope-Tension Hysterese-Semantik (aufgelöst):** Epic-AC 4 spricht von „Modus-Wechsel Akku-voll → Drossel" mit 97/93 %-Hysterese. **Verbindliche Interpretation:** Die Hysterese gilt für **alle** SPEICHER- oder MULTI-Setups. In SPEICHER-Setup (1 Akku) wird bei `aggregated_pct ≥ 97` auf DROSSEL umgeschaltet, bei `aggregated_pct ≤ 93` zurück. In MULTI-Setup (Multi-Akku) bleibt der Mode `MULTI`, aber die `_policy_multi` priorisiert Pool-Laden bis Max-SoC; oberhalb wirkt nur noch der Drossel-Anteil. Mode-Switch SPEICHER↔DROSSEL ist die typische v1-Realität (1-Akku-Beta-Setup). MULTI bleibt für v1.5-Multi-Akku **funktional implementiert**, aber im Beta-Gate-Realbetrieb selten getriggert.

**Scope-Tension MULTI vs. Hysterese (aufgelöst):** MULTI-Modus **wechselt nicht** dynamisch nach DROSSEL — er enthält Drossel-Logik **als Fallback im Setpoint-Pfad**. SPEICHER-Modus **wechselt** nach DROSSEL bei Pool-Voll (Hysterese), weil er keine Drossel-Logik intern hat. Der Selector entscheidet beim Startup, welcher Modus aktiv wird; das Switching greift dann nur, wenn der initiale Modus SPEICHER (nicht MULTI) ist. **Begründung:** MULTI-Modus existiert genau, weil Multi-Akku-Setups zu komplex für reine Mode-Switches sind (Hand-off zwischen Pool-Laden und WR-Drossel passiert pro Sensor-Event, nicht pro Mode-Wechsel).

**Scope-Tension Audit-Cycle-Persist (aufgelöst):** Epic-AC 6 verlangt „Event mit Timestamp, alter/neuer Modus und Trigger-Grund wird im Log und in der `control_cycles`-Tabelle geschrieben". `control_cycles.readback_status` erlaubt seit `002` u. a. `'noop'`. Mode-Switch wird als **`readback_status='noop'`-Cycle** mit `mode=<neuer Modus>`, `source='solalex'`, `reason='mode_switch: <old>→<new> (<grund>)'` persistiert. **Keine** neue SQL-Migration, **kein** neuer `readback_status`-Wert.

## Acceptance Criteria

1. **Adaptive Initial-Modus aus Hardware-Regime (Epic-AC 1, FR13):** `Given` der Add-on-Start mit kommissionierten Devices, `When` `main.py::lifespan` den Controller baut, `Then` ruft es `select_initial_mode(devices_by_role, battery_pool)` auf, das deterministisch zurückliefert: nur `wr_limit` (kein Pool oder Pool-Member-Count = 0) → `Mode.DROSSEL`; `wr_limit` + Pool mit genau **1 Member** → `Mode.SPEICHER`; `wr_limit` + Pool mit **≥ 2 Members** → `Mode.MULTI`; **kein** `wr_limit` und Pool mit ≥ 1 Member → `Mode.SPEICHER` (Pool-only-Setup ohne separaten WR; v1.5-Edge, defensiv unterstützt); **kein** `wr_limit` und kein Pool → `Mode.DROSSEL` (degenerate, Default-fallback ohne Wirkung), **And** der ausgewählte Modus wird via `mode=<selected>` im `Controller(...)`-Konstruktor übergeben (statt heutigem hardcoded `Mode.DROSSEL`).

2. **Multi-Modus — Pool zuerst, dann Drossel (Epic-AC 2, FR15 + FR21):** `Given` `Mode.MULTI` ist aktiv und es gibt **PV-Überschuss** (geglätteter `grid_meter` < 0 W, Einspeisung), `When` ein Sensor-Event auf `grid_meter` eintrifft, `Then` ruft `_policy_multi(device, sensor_value_w)` zuerst `_policy_speicher(device, sensor_value_w)` auf und gibt dessen `list[PolicyDecision]` zurück, **falls non-empty** und der Pool nicht Max-SoC-gecappt ist; **erst wenn** der Pool gecappt ist (Speicher-Policy hat `_speicher_max_soc_capped=True` gesetzt nach diesem Sensor-Event ODER Speicher-Policy hat `[]` mit gleichzeitigem `aggregated_pct >= max_soc` zurückgeliefert), `Then` ruft `_policy_multi` zusätzlich `_policy_drossel(device, sensor_value_w)` auf und kombiniert den Drossel-Decision mit der (leeren) Speicher-Liste, **And** beide Decision-Listen werden konkateniert (`speicher_decisions + drossel_decisions`) und vom Executor parallel dispatched (Per-Device-Lock pro `device_id` aus 3.1 trennt Pool-Member vs. WR), **And** der Test verifiziert: Pool unter Max-SoC → nur Pool-Decisions; Pool an Max-SoC → ausschließlich Drossel-Decision; Pool zwischen knapp-voll → Pool charged mit Hardware-Cap, Drossel ergänzt für den Rest (z. B. PV 2700 W, Pool nimmt 2500 W, WR-Limit drosselt auf Verbrauch + 200 W).

3. **Multi-Modus mit leerem Pool bei Bezug — kein Drossel-Anstieg (Epic-AC 3):** `Given` `Mode.MULTI` ist aktiv und der **Pool-SoC ≤ Min-SoC** (Default 15 %), `When` der geglättete `grid_meter`-Wert > 0 W meldet (Bezug = Grundlast, typisch nachts), `Then` liefert `_policy_speicher` `[]` (Min-SoC-Hard-Cap aus 3.4 AC 4), **And** `_policy_multi` ruft Drossel **nicht** auf bei Bezug (Drossel ist asymmetrisch: bei Bezug würde sie das WR-Limit hochfahren, was bei Multi-Modus nachts unsinnig ist — die PV liefert 0 W, das WR-Limit ist irrelevant), `Then` liefert `_policy_multi` `[]` zurück, **And** `on_sensor_update` schreibt einen einzelnen Noop-Cycle mit `mode='multi'`, `source!='solalex'` → `reason=None` (bestehender Pfad). **Sign-Begründung:** `_policy_drossel` reagiert auf positive `smoothed` (Bezug) durch Erhöhung des WR-Limits — sinnvoll bei reinem WR-Setup ohne Akku. Im MULTI-Setup bei leerem Pool: Erhöhung des WR-Limits ändert nichts (der WR liefert eh 0 W), aber sendet ein nutzloses HA-Command. Multi unterdrückt deshalb Drossel bei `smoothed > 0`.

4. **Hysterese-Wechsel SPEICHER → DROSSEL bei Pool-Voll (Epic-AC 4, FR16):** `Given` `Mode.SPEICHER` ist aktiv, **And** `aggregated_pct >= 97 %` wird vom Pool gemeldet (oder konfigurierbar via `MODE_SWITCH_HIGH_SOC_PCT`-Konstante in `controller.py`, Default 97), `When` ein Sensor-Event eintrifft (egal ob Lade-relevant oder nicht — die Auswertung läuft in `_evaluate_mode_switch`), **And** die Mindest-Verweildauer (`MODE_SWITCH_MIN_DWELL_S`, Default 60 s) seit dem letzten Mode-Switch ist abgelaufen, `Then` schaltet der Controller `self._current_mode` auf `Mode.DROSSEL` (`set_mode(Mode.DROSSEL)`-Aufruf intern), **And** schreibt einen Audit-Cycle (siehe AC 6), **And** der `_speicher_buffers`-Eintrag für den `grid_meter` bleibt erhalten (für späteres Zurück-Switching), **And** der `_drossel_buffers`-Eintrag wird **frisch initialisiert** beim ersten DROSSEL-Sensor-Event (existierende `_policy_drossel`-Logik erstellt einen Buffer bei Bedarf — keine Extra-Initialisierung).

5. **Hysterese-Wechsel DROSSEL → SPEICHER bei Pool-knapp-voll (Epic-AC 4, FR16):** `Given` `Mode.DROSSEL` ist aktiv (vorher durch Hysterese-Switch auf DROSSEL gewechselt — nur dann ist die Rück-Switch-Bedingung relevant), **And** `aggregated_pct <= 93 %` (`MODE_SWITCH_LOW_SOC_PCT`, Default 93) wird vom Pool gemeldet, **And** der `BatteryPool` ist non-None und hat ≥ 1 Member (Initial-Selector-Bedingung für SPEICHER war erfüllt), **And** Mindest-Verweildauer abgelaufen, `When` ein Sensor-Event eintrifft, `Then` schaltet der Controller zurück auf `Mode.SPEICHER`, **And** schreibt Audit-Cycle, **And** der **initial** als DROSSEL gestartete Mode (Setup ohne Akku) wechselt **nicht** auf SPEICHER zurück — der Hysterese-Helper prüft, ob `Mode.SPEICHER` jemals der Initial-Modus war oder nur vorübergehender Vorgänger; Implementierung via `self._mode_baseline: Mode`-Feld, das beim Konstruktor auf `select_initial_mode(...)`-Ergebnis gesetzt wird (also den **Setup-Modus** speichert). Hysterese-Wechsel werden **nur dann** zurück-erlaubt, wenn `self._mode_baseline == Mode.SPEICHER` (oder `Mode.MULTI`, siehe AC 7).

6. **Audit-Cycle bei Mode-Switch (Epic-AC 6, FR16):** `Given` ein Mode-Switch ist getriggert, `When` `set_mode(new_mode)` aufgerufen wird, `Then` schreibt `_record_mode_switch_cycle(old_mode, new_mode, reason, sensor_device)` einen `control_cycles`-Row mit: `mode=new_mode.value`, `source='solalex'`, `device_id=sensor_device.id` (das `grid_meter`-Device, das den Trigger-Sensor-Event auslöste), `readback_status='noop'`, `target_value_w=None`, `sensor_value_w=None`, `cycle_duration_ms=0` (Mode-Switch ist Audit, kein Regelzyklus), `reason='mode_switch: drossel→speicher (soc=92.4%)'` (Format: `mode_switch: <old>→<new> (<trigger_detail>)`, `<trigger_detail>` ist eine kurze Klartext-Beschreibung mit dem ausschlaggebenden Wert, max. 200 Zeichen via `_truncate_reason`), **And** ein `_logger.info('mode_switch', extra={...})`-Record wird parallel geschrieben mit `extra={'old_mode', 'new_mode', 'reason', 'aggregated_pct': float|None, 'baseline_mode'}`, **And** `state_cache.update_mode(new_mode.value)` wird aufgerufen (Polling-Endpoint zeigt sofort den neuen Modus, Story 5.1a-Pfad), **And** `self._mode_switched_at: datetime`-Feld wird auf `now` gesetzt (Dwell-Time-Tracking).

7. **MULTI bleibt MULTI — kein Hysterese-Switch (Epic-AC 4 + 6):** `Given` `Mode.MULTI` ist aktiv (Multi-Akku-Setup), `When` `aggregated_pct >= 97 %` oder `<= 93 %`, `Then` **kein** Mode-Switch, **kein** Audit-Cycle. **Begründung:** MULTI-Modus enthält Drossel-Logik bereits intern (AC 2). Ein Mode-Switch zu DROSSEL würde die Pool-Lade-Logik komplett deaktivieren, statt sie nur bei Pool-Voll zu suspendieren. Der Hysterese-Helper prüft `if self._current_mode == Mode.MULTI: return None` als erste Early-Return.

8. **Mindest-Verweildauer 60 s pro Modus (Epic-AC 5, FR16):** `Given` ein Mode-Switch ist gerade erfolgt (`self._mode_switched_at` ist gesetzt), `When` ein folgender Sensor-Event innerhalb von `MODE_SWITCH_MIN_DWELL_S=60.0` Sekunden eintrifft, **And** die Hysterese-Bedingung für einen erneuten Wechsel wäre erfüllt, `Then` wird der Wechsel **unterdrückt** — `_evaluate_mode_switch` liefert `None`. **And** der Test `test_mode_switch_dwell_blocks_oscillation` simuliert eine Sinus-SoC-Schwankung im 90–98 %-Bereich über 30 s; die Mode-Wechsel-Anzahl bleibt ≤ 1.

9. **Reentrant-Sicherheit gegen Doppel-Switch in derselben Sekunde:** `Given` ein Sensor-Event triggert einen Mode-Switch und produziert gleichzeitig Decisions, `When` `on_sensor_update` läuft, `Then` läuft die Reihenfolge: (a) Mode-Switch-Auswertung mit dem **aktuellen** Modus → ggf. `set_mode(...)`, (b) **dann** Policy-Dispatch mit dem **neuen** Modus, (c) **dann** Audit-Cycle für den Switch (vor den Dispatch-Tasks, damit der Cycle in der UI vor den Folge-Cycles erscheint). **And** der Audit-Cycle wird **synchron** persistiert (gleiches Pattern wie `_record_noop_cycle`), nicht in einem Background-Task — Begründung: Mode-Switch ist selten (max. ~1× pro 60 s), Audit-Visibility hat Priorität gegenüber Pipeline-Latenz. **And** wenn der Audit-Persist scheitert, wird der Mode-Switch **trotzdem** durchgeführt — `set_mode` läuft als erstes, Persist ist Audit-only.

10. **Zero-Knowledge-Pool-Selector (Edge-Cases):** `Given` `select_initial_mode(...)` mit unvollständiger Devices-Map, `When` aufgerufen, `Then` deckt der Selector folgende Edge-Cases ab — alle ohne Exception:
    - `devices_by_role={}, battery_pool=None` → `Mode.DROSSEL` (degenerate; Tests laufen ohne Devices).
    - `devices_by_role={'wr_limit': ...}, battery_pool=None` → `Mode.DROSSEL`.
    - `devices_by_role={'wr_limit': ...}, battery_pool=Pool[1 member]` → `Mode.SPEICHER`.
    - `devices_by_role={'wr_limit': ...}, battery_pool=Pool[2 members]` → `Mode.MULTI`.
    - `devices_by_role={'wr_limit': ...}, battery_pool=Pool[0 members]` → `Mode.DROSSEL` (Pool ohne Members existiert nicht — `BatteryPool.from_devices` liefert dann `None` — defensive Check trotzdem).
    - `devices_by_role={'wr_charge': ...}, battery_pool=Pool[1]`, **kein** `wr_limit` → `Mode.SPEICHER`.

11. **Mode-Switch trigert keine Sofort-Dispatch-Aktion auf den ALTEN Modus:** `Given` `Mode.SPEICHER` ist aktiv und Pool-SoC erreicht `≥ 97 %`, `When` der Hysterese-Switch zu DROSSEL erfolgt **innerhalb** desselben `on_sensor_update`-Calls, `Then` produziert `_dispatch_by_mode(Mode.DROSSEL, ...)` (mit dem **neuen** Modus) ggf. **null** Decisions im selben Tick, weil `_policy_drossel` einen frischen Buffer aufbaut und in den ersten Sekunden im Deadband bleibt — das ist akzeptabel (kein Pool-Lade-Befehl wird mehr gesendet, weil bereits an Max-SoC, und der WR-Drossel ist im Übergangs-Stadium). **Test:** `test_speicher_to_drossel_switch_no_pool_command` verifiziert, dass nach dem Switch kein `set_charge`-Befehl mehr produziert wird; eventuelle Drossel-Befehle erscheinen erst, wenn der Drossel-Buffer gefüllt ist.

12. **Mode-Switch resettet Speicher-Cap-Flags:** `Given` ein Mode-Switch zu DROSSEL erfolgt während `_speicher_max_soc_capped=True`, `When` der Switch durch ist, `Then` werden `self._speicher_max_soc_capped` und `self._speicher_min_soc_capped` auf `False` zurückgesetzt — Begründung: Bei einem späteren Rück-Switch zu SPEICHER soll der erste Cap-Eintritt wieder einen `info`-Log produzieren (das Flag-Tracking aus 3.4 baut auf „seit-letztem-Reset"). Reset passiert in `_record_mode_switch_cycle` synchron mit dem `set_mode`-Aufruf.

13. **`_policy_multi` ersetzt `_policy_multi_stub`:** `Given` der heutige `_policy_multi_stub` (returniert `[]`), `When` Story 3.5 implementiert wird, `Then` wird der Stub durch eine **Methode** `Controller._policy_multi(self, device, sensor_value_w) -> list[PolicyDecision]` ersetzt (analog zur Promotion `_policy_speicher_stub` → Methode in 3.4), **And** der Modul-Top-Level-Stub wird gelöscht, **And** `_dispatch_by_mode`-`Mode.MULTI`-Branch ruft `self._policy_multi(...)` statt `_policy_multi_stub(...)`.

14. **Konstanten zentral in `controller.py` (CLAUDE.md Regel 2 + Hysterese-Helper-Inline):**
    ```python
    # Adaptive mode switching (Story 3.5).
    # 97/93 % is FR16 spec; 60 s dwell follows PRD Zeile 402 anti-oscillation.
    MODE_SWITCH_HIGH_SOC_PCT: float = 97.0
    MODE_SWITCH_LOW_SOC_PCT: float = 93.0
    MODE_SWITCH_MIN_DWELL_S: float = 60.0
    ```
    Konstanten leben **am Modul-Top von `controller.py`**, nicht in `adapters/base.py` (sind nicht hardware-, sondern controller-spezifisch). **Kein** User-Override in v1 — Override über `device.config_json` ist v1.5-Scope.

15. **Mode-Selector als Modul-Top-Level-Funktion (testbar):** `Given` der Selector ist eine reine Pure-Function, `When` definiert, `Then` lebt er als Modul-Top-Level: `def select_initial_mode(devices_by_role: dict[str, DeviceRecord], battery_pool: BatteryPool | None) -> Mode` in `controller.py` — **nicht** als Methode am Controller (vermeidet zirkuläre Import-Probleme bei Tests, die keinen Controller brauchen).

16. **Audit-Cycle nutzt `device_id` des Trigger-Events:** `Given` der Mode-Switch wird durch ein `grid_meter`-Sensor-Event getriggert, `When` der Audit-Cycle persistiert wird, `Then` ist `device_id = sensor_device.id` (das `grid_meter`, das den Trigger-Event lieferte) — **nicht** ein Pseudo-Device oder NULL. **Begründung:** `control_cycles.device_id` hat ein FK-Constraint auf `devices.id`; jeder Cycle muss zu einem realen Device gehören. Das `grid_meter` ist semantisch der nächst-passende Anker, weil der Mode-Switch durch dessen Sensor-Stream getriggert wird.

17. **`_evaluate_mode_switch` ist Pure-Function ohne IO:** `Given` der Hysterese-Helper, `When` aufgerufen, `Then` ist die Signatur `_evaluate_mode_switch(self, *, sensor_device: DeviceRecord, now: datetime) -> tuple[Mode, str] | None` (returniert `(neuer_modus, reason_detail)` oder `None`); die Funktion macht **keinen** DB-Write, **keinen** `state_cache.update_mode`-Call, **keinen** `set_mode`-Call. Side-Effects passieren ausschließlich in `_record_mode_switch_cycle(...)`, das vom Aufrufer in `on_sensor_update` getriggert wird, **wenn** der Helper non-`None` liefert. **Begründung:** Trennung Decision/Effect ermöglicht Property-Tests gegen den Helper ohne Controller-Setup.

18. **`pool.get_soc(state_cache)`-Aufruf einmal pro Sensor-Event:** `Given` der Hysterese-Helper braucht `aggregated_pct`, **And** `_policy_speicher` braucht es ebenfalls, `When` `on_sensor_update` läuft, `Then` wird `pool.get_soc(...)` **maximal einmal** pro Event aufgerufen — der Wert wird über das `_evaluate_mode_switch`-Return-Tuple oder einen privaten Cache `self._cached_soc_breakdown_per_event` geteilt, bzw. die Mode-Switch-Auswertung passiert **nach** der Policy-Berechnung und liest den bereits berechneten SoC aus dem Pool nochmal (Pool-`get_soc` ist IO-frei und sub-millisekunde — Doppellesen ist akzeptabel; Bevorzugte Implementierung: einmal lesen, durch beide Pfade reichen). **Performance-Test nicht erforderlich**, aber `test_pool_get_soc_called_at_most_twice_per_event` ist ein Defensive-Property-Test für Mock-basiertes Counting.

19. **MULTI-Min-SoC-Branch (Epic-AC 3 Spezialfall):** `Given` `Mode.MULTI`, `aggregated_pct <= min_soc`, **And** geglätteter `grid_meter > 0` (Bezug), `When` `_policy_multi` läuft, `Then` Speicher liefert `[]` (Hard-Cap aus 3.4 AC 4), Drossel wird **nicht** aufgerufen (AC 3 oben), `Then` `_policy_multi` returniert `[]`. **Test:** `test_multi_at_min_soc_with_load_no_drossel_no_charge`.

20. **MULTI-Max-SoC-Branch (Epic-AC 2 Spezialfall):** `Given` `Mode.MULTI`, `aggregated_pct >= max_soc`, **And** geglätteter `grid_meter < 0` (Einspeisung), `When` `_policy_multi` läuft, `Then` Speicher liefert `[]` (Hard-Cap aus 3.4 AC 3), Drossel wird **aufgerufen** und produziert eine Decision (Drossel-Pfad reagiert auf negative `smoothed` durch Limit-Reduktion), `Then` `_policy_multi` returniert `[drossel_decision]`. **Test:** `test_multi_at_max_soc_with_feed_in_drossel_takes_over`.

21. **MULTI-Symmetrie-Test (Drossel + Speicher gleichzeitig nicht):** `Given` `Mode.MULTI` und ein Pool unter Max-SoC, `When` Einspeisung anliegt und Speicher-Decisions produziert werden, `Then` ruft `_policy_multi` Drossel **nicht** auf — eine gleichzeitige Drossel-Aktion würde den WR künstlich limitieren, obwohl der Pool den Überschuss schluckt. Drossel greift in MULTI nur dann, wenn Speicher `[]` zurückgegeben hat **wegen Max-SoC** (nicht wegen Deadband, Min-Step oder fehlender Pool-Konfiguration). **Test:** `test_multi_pool_below_max_soc_no_drossel_call`.

22. **MULTI-Drossel-Buffer-Reuse:** `Given` `Mode.MULTI` ist aktiv, `When` `_policy_multi` Drossel aufruft, `Then` nutzt der Drossel-Aufruf den existierenden `self._drossel_buffers`-Cache mit dem `grid_meter.id` als Key (kein separater MULTI-Buffer). **Begründung:** In MULTI baut sich der Drossel-Buffer kontinuierlich auf (jedes Sensor-Event füttert ihn via Speicher-Pfad **NICHT** — Speicher hat seinen eigenen Buffer). Wenn Drossel zum ersten Mal in MULTI aufgerufen wird (Pool-Voll), startet der Drossel-Buffer leer und füllt sich in ~5 s. Das ist akzeptabel (Deadband-Pause überbrückt die Anlauf-Zeit; siehe AC 11-Symmetrie). **Stop-Condition:** Wenn jemand auf die Idee kommt, den Drossel-Buffer **vorab** zu befüllen, wenn MULTI startet — **STOP**. Pool nimmt den Überschuss bei normaler MULTI-Operation; Drossel-Buffer-Aufbau passiert genau dann, wenn er gebraucht wird.

23. **Initial-Mode-Mirror in `state_cache`:** `Given` der Controller startet mit `Mode.SPEICHER` (durch Selector), `When` `lifespan` zu Ende ist, `Then` zeigt `state_cache.current_mode` weiterhin `'idle'` (kein Cycle wurde geschrieben), **And** das ist akzeptabel — die UI zeigt erst beim ersten Sensor-Event den realen Modus. Der Initial-Modus wird **nicht** explizit beim Startup in den `state_cache` gespiegelt (das wäre eine Erwartungs-Verletzung des Heartbeat-Patterns aus 5.1a, das `update_mode` nur am Cycle-Call-Site triggert). **Mode-Switches** dagegen mirrorn, weil sie einen Cycle schreiben.

24. **Tests (Pytest, MyPy strict, Ruff):** Neue Test-Dateien unter `backend/tests/unit/`:
    - `test_controller_mode_selector.py`:
      - `test_select_initial_mode_drossel_only` (AC 1, AC 10)
      - `test_select_initial_mode_speicher_for_single_member_pool` (AC 1)
      - `test_select_initial_mode_multi_for_two_member_pool` (AC 1)
      - `test_select_initial_mode_speicher_without_wr_limit` (AC 10 Edge)
      - `test_select_initial_mode_drossel_when_pool_is_none` (AC 10 Edge)
      - `test_select_initial_mode_drossel_when_pool_empty` (AC 10 Edge — defensive)
    - `test_controller_mode_switch.py`:
      - `test_speicher_to_drossel_at_high_soc` (AC 4)
      - `test_drossel_to_speicher_at_low_soc_when_baseline_was_speicher` (AC 5)
      - `test_drossel_to_speicher_blocked_when_baseline_is_drossel` (AC 5 — Setup ohne Akku darf nicht zu SPEICHER)
      - `test_multi_no_hysteresis_switch_at_high_soc` (AC 7)
      - `test_multi_no_hysteresis_switch_at_low_soc` (AC 7)
      - `test_mode_switch_dwell_blocks_oscillation` (AC 8 — Sinus-SoC 30 s, max. 1 Wechsel)
      - `test_mode_switch_audit_cycle_persisted` (AC 6 — control_cycles row inserted with reason)
      - `test_mode_switch_logs_info_record_with_extra` (AC 6)
      - `test_mode_switch_resets_speicher_cap_flags` (AC 12)
      - `test_mode_switch_state_cache_updated` (AC 6 — `state_cache.current_mode == new_mode`)
      - `test_mode_switch_audit_persist_failure_does_not_block_switch` (AC 9 — set_mode succeeds even when DB write raises)
      - `test_evaluate_mode_switch_pure_function_no_side_effects` (AC 17)
      - `test_speicher_to_drossel_switch_no_pool_command` (AC 11)
      - `test_evaluate_uses_baseline_mode_for_return_eligibility` (AC 5 — `_mode_baseline`-Field-Gate)
    - `test_controller_multi_policy.py`:
      - `test_multi_pool_below_max_soc_returns_speicher_decisions_only` (AC 2)
      - `test_multi_pool_below_max_soc_no_drossel_call` (AC 21)
      - `test_multi_at_max_soc_with_feed_in_drossel_takes_over` (AC 20)
      - `test_multi_at_min_soc_with_load_no_drossel_no_charge` (AC 19)
      - `test_multi_at_min_soc_with_feed_in_returns_empty` (AC 19 — defensive)
      - `test_multi_drossel_uses_existing_buffer_no_pre_population` (AC 22)
      - `test_multi_with_battery_pool_none_falls_back_to_drossel_only` (defensive — MULTI mode but no pool wired up)
      - `test_multi_replaces_stub_in_dispatch_by_mode` (AC 13)
    - `test_controller_mode_switch.py::test_pool_get_soc_called_at_most_twice_per_event` (AC 18)
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf allen Änderungen in `controller.py` (Mode-Selector, `_evaluate_mode_switch`, `_policy_multi`, `_record_mode_switch_cycle`).
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (unverändert — **keine neue Migration in 3.5**).

25. **Scope-Eingrenzung Diff (Override-inkludiert):** Die Story bringt Backend- + Frontend-Änderungen, **aber keine neue SQL-Migration** — der `meta`-Key `forced_mode` lebt im bestehenden Key-Value-Schema aus `001_initial.sql`. **Kein** `pyproject.toml`-Diff (keine neue Dependency).

27. **Manual-Override-Persistenz (`meta.forced_mode`):** `Given` der Beta-User möchte den Modus überschreiben, `When` `PUT /api/v1/control/mode` mit `{"forced_mode": "speicher"}` aufgerufen wird, `Then` schreibt das Backend `meta.forced_mode = 'speicher'` (`set_meta`-Helper aus [persistence/repositories/meta.py](../../backend/src/solalex/persistence/repositories/meta.py)) **und** ruft synchron `controller.set_forced_mode(Mode.SPEICHER)` auf (siehe AC 28), **And** `GET /api/v1/control/mode` liefert `{forced_mode: "speicher"|"drossel"|"multi"|null, active_mode: <Mode>, baseline_mode: <Mode>}`, **And** Erlaubte PUT-Werte: `"drossel"`, `"speicher"`, `"multi"`, `null` (oder weglassen → `null`). `null` löscht den Meta-Key (`DELETE FROM meta WHERE key = 'forced_mode'`) und re-aktiviert Auto-Detection + Hysterese. Pydantic-Schema in `api/schemas/control.py`: `class ForcedModeRequest(BaseModel): forced_mode: Literal["drossel","speicher","multi"] | None`.

28. **Controller-API für Override (`set_forced_mode`):** `Given` der Override soll runtime-wirksam werden ohne Add-on-Restart, `When` der API-Handler den Wert ändert, `Then` ruft er `app.state.controller.set_forced_mode(mode: Mode | None)` auf, **And** die Methode setzt `self._forced_mode: Mode | None`, **And** wenn `mode` non-`None` und `mode != self._current_mode`: `_record_mode_switch_cycle(old=self._current_mode, new=mode, reason_detail=f'manual_override: forced→{mode.value}', sensor_device=<wr_limit or grid_meter>, now=self._now_fn())` synchron, **And** wenn `mode is None` (Override aufgehoben): `_logger.info('mode_override_cleared', extra={'restored_to_auto': True})` — **kein** sofortiger Audit-Cycle (der nächste Sensor-Event triggert die Hysterese und ggf. einen normalen Switch-Cycle), **And** `state_cache.update_mode(...)` wird in beiden Fällen aufgerufen (Polling-Endpoint zeigt sofort).

29. **Selector + Hysterese mit Override:** `Given` ein Override ist aktiv (`self._forced_mode is not None`), `When` `_evaluate_mode_switch` läuft, `Then` returniert es **immer** `None` (Hysterese deaktiviert — User-Wille schlägt Auto), **And** wenn das Override aufgehoben wird (`set_forced_mode(None)`), läuft `_evaluate_mode_switch` ab dem nächsten Sensor-Event normal weiter (mit `_mode_switched_at`-Wert vom letzten Override-Set, sodass die 60-s-Dwell-Time greift und der erste Auto-Switch nicht sofort kommt). `select_initial_mode` wird **um einen Parameter erweitert**: `def select_initial_mode(devices_by_role, battery_pool, forced_mode: Mode | None = None) -> tuple[Mode, Mode]` — returniert `(active_mode, baseline_mode)`. Bei `forced_mode is not None`: `active_mode = forced_mode`, `baseline_mode = <auto-detected>` (sodass nach Override-Aufhebung die Hysterese-Logik weiterhin den korrekten Setup-Modus kennt). Bei `forced_mode is None`: beide Werte gleich (Auto-Result).

30. **Override beim Startup laden:** `Given` der Add-on-Start nach einem Reboot, `When` `main.py::lifespan` den Controller baut, `Then` liest es vor `Controller(...)`-Bau via `await get_meta(conn, 'forced_mode')` den persistierten Override, **And** validiert gegen `Literal["drossel","speicher","multi"]` (alles andere → `None` mit `_logger.warning('forced_mode_invalid_value', extra={'value': raw})`), **And** übergibt das Ergebnis als `forced_mode=...` an `select_initial_mode(...)`, **And** der Controller-Konstruktor erhält den `_forced_mode`-Init-Wert über einen neuen Parameter: `forced_mode: Mode | None = None`. **And** beim Lifespan-Startup wird **kein** Audit-Cycle für den Initial-Override geschrieben (Override ist persistent — kein Switch, sondern Restore).

31. **API-Endpunkt `GET/PUT /api/v1/control/mode`:** `Given` ein neuer Endpunkt-File `api/routes/control.py` (existiert bereits — `/state` lebt dort), `When` Story 3.5 ihn erweitert, `Then` ergänzt die Datei zwei Routes:
    - `GET /api/v1/control/mode` → `{forced_mode: str | null, active_mode: str, baseline_mode: str}` (`active_mode` aus `controller.current_mode`, `baseline_mode` aus `controller._mode_baseline`).
    - `PUT /api/v1/control/mode` mit Pydantic-Body `ForcedModeRequest`. Side-Effects: `set_meta`/`delete` + `controller.set_forced_mode(...)`. Returnstatus: `200 OK` mit dem aktualisierten GET-Body.
    - Beide Routes sind hinter dem License/Disclaimer-Gate (analog zu `/state` aus 5.1a — falls 5.1a `Depends(require_active_license)` nutzt, übernehmen).
    - **Kein Wrapper** um JSON (CLAUDE.md Regel 4): `{"forced_mode": "speicher", "active_mode": "speicher", "baseline_mode": "speicher"}` direkt.

32. **Frontend — Override-UI in `Config.svelte`:** `Given` die Config-Page existiert (Story 2.1), `When` 3.5 die Override-UI ergänzt, `Then` wird ein neuer Card-Block „Regelungs-Modus" angezeigt mit:
    - Radio-Group: `○ Automatisch (empfohlen)` / `○ Drossel` / `○ Speicher` / `○ Multi`. Default-Auswahl aus dem GET-Response.
    - Klartext-Untertitel: „Solalex erkennt den Modus normalerweise selbst. Diese Option überschreibt die Auto-Erkennung — nur für Tests oder wenn der Auto-Modus nicht passt."
    - On-Change: PUT an Backend, optimistisch UI updaten, bei Fehler revert + deutsche Fehlermeldung als Inline-Hint (kein Toast — UX-DR30 verbietet Push-Patterns).
    - Bei Override aktiv: Status-Zeile darunter: „Manuell überschrieben: <Modus> — auto-erkannter Modus wäre: <Baseline>" (Klartext aus `baseline_mode`-Field).
    - Kein Button „Speichern" — Auto-PUT auf Radio-Change (Pattern aus 2.1).
    - Strings deutsch, hardcoded (CLAUDE.md — keine i18n).
  - Datei: [Config.svelte](../../frontend/src/routes/Config.svelte). API-Client-Methode in `lib/api/client.ts`: `fetchControlMode()` + `setForcedMode(mode: ForcedMode)`. TS-Type `ForcedMode = "auto" | "drossel" | "speicher" | "multi"` (in `client.ts` neben dem bestehenden Pattern).
  - Polling-Endpoint `/api/v1/control/state` muss **keinen** zusätzlichen `forced_mode`-Field tragen — die Config-Page lädt den Wert beim Mount und nach jedem PUT neu. **Begründung:** Override-Wechsel sind selten; den Polling-Payload aufzublähen ist unnötig.

33. **Override-Audit-Cycle-Reason-Format:** `Given` `set_forced_mode` triggert einen Audit-Cycle, `When` der Cycle persistiert wird, `Then` ist `reason='mode_switch: <old>→<new> (manual_override)'` (kein SoC-Wert, weil User-Override unabhängig vom SoC ist). **Test:** `test_set_forced_mode_writes_audit_cycle_with_manual_reason`.

34. **Hysterese-Resume nach Override-Aufhebung:** `Given` der User setzt `forced_mode = "speicher"`, dann nach 5 Min `forced_mode = null`, `When` der nächste Sensor-Event eintrifft, `Then` läuft `_evaluate_mode_switch` normal — wenn `aggregated_pct ≥ 97 %` UND `Mode.SPEICHER == _current_mode`, switcht es zu `DROSSEL` (Audit-Cycle mit `reason='mode_switch: speicher→drossel (pool_full (soc=97.5%))'`). **Begründung:** Override-Aufhebung restauriert die Hysterese, nicht den Auto-Detect-Initial-Modus. **Test:** `test_clearing_forced_mode_resumes_hysteresis_at_current_mode`.

35. **Override-Frontend-Tests (Vitest + @testing-library):** `backend/`-Tests + neue Frontend-Tests:
    - `frontend/src/routes/Config.test.ts` (existiert ggf. — erweitern oder neu): `test_renders_mode_override_radio`, `test_put_called_on_radio_change`, `test_baseline_mode_shown_when_override_active`, `test_radio_reverts_on_api_error`.
    - **Vitest-Coverage** muss die neuen Lines abdecken (Schwelle wie in 5.1a/4.0a).

26. **Pipeline-Reference-Flow (3.5 Add-on auf 3.4):**
    ```
    HA state_changed event (grid_meter)
      ↓ _dispatch_event in main.py                                  [unverändert]
      ↓ controller.on_sensor_update(msg, device)                    [iteration unchanged from 3.4]
      ↓   ├─ test_in_progress? → return                              [unverändert]
      ↓   ├─ source = _classify_source(...)                          [unverändert]
      ↓   ├─ sensor_w = _extract_sensor_w(...)                       [unverändert]
      ↓   ├─ switch = self._evaluate_mode_switch(                    [3.5 NEW]
      ↓   │       sensor_device=device, now=now)
      ↓   ├─ if switch is not None:                                  [3.5 NEW]
      ↓   │   await self._record_mode_switch_cycle(                  [3.5 NEW]
      ↓   │       old_mode=self._current_mode,
      ↓   │       new_mode=switch[0], reason_detail=switch[1],
      ↓   │       sensor_device=device, now=now)
      ↓   │   self.set_mode(switch[0])                               [3.5 NEW]
      ↓   ├─ decisions = self._dispatch_by_mode(                     [unverändert — but Mode.MULTI now real]
      ↓   │       self._current_mode, device, sensor_w)
      ↓   ├─ if not decisions: ... noop-cycle ...                    [unverändert]
      ↓   └─ for d in decisions: create_task(_safe_dispatch(d))      [unverändert]
    ```
    **Reihenfolge essenziell (AC 9):** Mode-Switch zuerst auswerten + persistieren + `set_mode`, **dann** `_dispatch_by_mode` mit dem **neuen** Modus. Sonst läuft die erste Decision noch unter dem alten Modus.

## Tasks / Subtasks

- [x] **Task 1: Modus-Selektor + Konstanten** (AC: 1, 10, 14, 15)
  - [x] In `controller.py` am Modul-Top: drei Konstanten `MODE_SWITCH_HIGH_SOC_PCT=97.0`, `MODE_SWITCH_LOW_SOC_PCT=93.0`, `MODE_SWITCH_MIN_DWELL_S=60.0`. Pro Konstante One-Liner-Kommentar mit FR-Quelle.
  - [x] `def select_initial_mode(devices_by_role: dict[str, DeviceRecord], battery_pool: BatteryPool | None) -> Mode` als Modul-Top-Level-Funktion. Implementierung folgt der Entscheidungs-Tabelle aus AC 1 + 10. **Pure Function** (keine Side-Effects, keine Logs außer optional `_logger.info('mode_selected', extra={'mode', 'reason'})` für Diagnose).
  - [x] `__all__` um `select_initial_mode` ergänzen.
  - [x] **Stop:** Selector liest **nicht** aus dem `state_cache`. Pool-Member-Count ist die einzige Datenquelle. (Begründung: Beim Startup ist der `state_cache` leer.)

- [x] **Task 2: `Controller.__init__`-Felder + `_mode_baseline`** (AC: 5, 6, 12)
  - [x] Neue Felder im Konstruktor:
    ```python
    self._mode_baseline: Mode = mode  # captured at startup; never changed
    self._mode_switched_at: datetime | None = None
    ```
    Begründung Baseline: Ein DROSSEL-only-Setup darf **nie** über Hysterese zu SPEICHER wechseln (kein Pool ist da). Der Baseline-Modus encodiert das Setup-Regime.
  - [x] **Keine neue Methode am Konstruktor** für `select_initial_mode` — der Selector wird in `main.py::lifespan` aufgerufen und das Ergebnis als `mode=...`-Parameter übergeben.

- [x] **Task 3: `_evaluate_mode_switch` Hysterese-Helper** (AC: 4, 5, 7, 8, 17)
  - [x] Neue Methode `Controller._evaluate_mode_switch(self, *, sensor_device: DeviceRecord, now: datetime) -> tuple[Mode, str] | None`. Logik:
    1. `if self._current_mode == Mode.MULTI: return None` (AC 7).
    2. `if self._battery_pool is None or not self._battery_pool.members: return None` (kein Pool, kein Switch möglich).
    3. `soc_breakdown = self._battery_pool.get_soc(self._state_cache)`; bei `None` (alle Members offline) → `return None`.
    4. Dwell-Time-Check: `if self._mode_switched_at is not None and (now - self._mode_switched_at).total_seconds() < MODE_SWITCH_MIN_DWELL_S: return None`.
    5. `aggregated = soc_breakdown.aggregated_pct`.
    6. SPEICHER → DROSSEL: `if self._current_mode == Mode.SPEICHER and aggregated >= MODE_SWITCH_HIGH_SOC_PCT: return (Mode.DROSSEL, f'pool_full (soc={aggregated:.1f}%)')`.
    7. DROSSEL → SPEICHER: `if self._current_mode == Mode.DROSSEL and self._mode_baseline in (Mode.SPEICHER, Mode.MULTI) and aggregated <= MODE_SWITCH_LOW_SOC_PCT: return (Mode.SPEICHER, f'pool_below_low_threshold (soc={aggregated:.1f}%)')`.
    8. Sonst `return None`.
  - [x] **Pure-Function-Disziplin:** **Kein** `set_mode`, **kein** DB-Write, **kein** `update_mode`. Side-Effects passieren ausschließlich in `_record_mode_switch_cycle`.

- [x] **Task 4: `_record_mode_switch_cycle` Audit-Persist** (AC: 6, 9, 12, 16)
  - [x] Neue Methode `Controller._record_mode_switch_cycle(self, *, old_mode: Mode, new_mode: Mode, reason_detail: str, sensor_device: DeviceRecord, now: datetime) -> None`:
    1. `self.set_mode(new_mode)` (synchron — AC 9).
    2. `self._mode_switched_at = now`.
    3. `self._speicher_max_soc_capped = False`; `self._speicher_min_soc_capped = False` (AC 12).
    4. `_logger.info('mode_switch', extra={'old_mode': old_mode.value, 'new_mode': new_mode.value, 'reason': reason_detail, 'baseline_mode': self._mode_baseline.value, 'sensor_device_id': sensor_device.id})`.
    5. `state_cache.update_mode(new_mode.value)`.
    6. `device_id = sensor_device.id`; bei `None` → return ohne Persist (defensive — wird von Tests via Mock-Devices nicht getriggert).
    7. Build `ControlCycleRow` mit `mode=new_mode.value`, `source='solalex'`, `device_id=device_id`, `readback_status='noop'`, `target_value_w=None`, `sensor_value_w=None`, `cycle_duration_ms=0`, `reason=_truncate_reason(f'mode_switch: {old_mode.value}→{new_mode.value} ({reason_detail})')`.
    8. Persist via `async with self._db_conn_factory() as conn: await control_cycles.insert(conn, row); await conn.commit()`. Try/except Exception → `_logger.exception('mode_switch_cycle_persist_failed', ...)` aber **kein** re-raise (AC 9 Audit-only).
    9. `await kpi_record(row)` ebenfalls in try/except (Pattern aus `_write_failsafe_cycle`).

- [x] **Task 5: `on_sensor_update` Iteration-Reihenfolge** (AC: 9, 26)
  - [x] Direkt nach `sensor_value = _extract_sensor_w(event_msg)` (vor `decisions = self._dispatch_by_mode(...)`):
    ```python
    switch = self._evaluate_mode_switch(sensor_device=device, now=now)
    if switch is not None:
        new_mode, reason_detail = switch
        old_mode = self._current_mode
        await self._record_mode_switch_cycle(
            old_mode=old_mode, new_mode=new_mode,
            reason_detail=reason_detail, sensor_device=device, now=now,
        )
    ```
    **Hinweis:** `_record_mode_switch_cycle` ruft intern `set_mode`, daher kein expliziter `set_mode`-Call hier nötig.
  - [x] **Keine Änderung** an der bestehenden `decisions = self._dispatch_by_mode(...)`-Zeile — die liest jetzt `self._current_mode` mit dem neuen Wert.
  - [x] **Keine Änderung** an der Noop-Cycle-Logik oder dem Task-Spawn-Pattern.

- [x] **Task 6: `_policy_multi` Methode (ersetzt Stub)** (AC: 2, 3, 13, 19, 20, 21, 22)
  - [x] Neue Methode `Controller._policy_multi(self, device: DeviceRecord, sensor_value_w: float | None) -> list[PolicyDecision]`:
    1. `if device.role != 'grid_meter': return []` (Role-Filter analog Speicher/Drossel).
    2. `if sensor_value_w is None or not math.isfinite(sensor_value_w): return []`.
    3. `pool = self._battery_pool; if pool is None or not pool.members:` → fallback nur Drossel: `decision = self._policy_drossel(device, sensor_value_w); return [decision] if decision is not None else []` (defensive — sollte praktisch nie passieren, weil Selector dann nicht MULTI gewählt hätte; sicherheitshalber Drossel-Fallback statt `[]`).
    4. **Speicher zuerst:** `speicher_decisions = self._policy_speicher(device, sensor_value_w)`. **Hinweis:** Speicher führt eigene Smoothing/Deadband/Cap-Logik aus und schreibt ggf. `_speicher_max_soc_capped=True`.
    5. **Wenn Speicher non-empty:** `return speicher_decisions` (Pool nimmt Überschuss; Drossel nicht nötig).
    6. **Wenn Speicher empty wegen Max-SoC** (`self._speicher_max_soc_capped == True`) **AND** geglätteter `grid_meter < 0` (Einspeisung): Drossel ergänzen. Implementation:
       ```python
       if self._speicher_max_soc_capped and self._is_feed_in_after_smoothing(device, sensor_value_w):
           drossel_decision = self._policy_drossel(device, sensor_value_w)
           return [drossel_decision] if drossel_decision is not None else []
       ```
       **Schwierigkeit:** Speicher-Policy hat den geglätteten Wert intern, aber den Cap-State über das Flag exponiert. „Einspeisung anliegt" lässt sich daraus rekonstruieren: Wenn Cap-Flag gerade gesetzt wurde und Speicher `[]` lieferte, war der Trigger eine Einspeisung mit aggregated >= max_soc. **Vereinfachung:** Verlasse dich nicht auf eine separate Smoothing-Berechnung — nutze das `_speicher_max_soc_capped`-Flag als Proxy für „letzter Trigger war Einspeisung mit Pool-Voll". Bei Bezug (positive smoothed) hat Speicher `[]` mit `_speicher_min_soc_capped=True` (oder Deadband) — in dem Fall **kein** Drossel-Aufruf (AC 3 + 19).
    7. **Sonst** (Speicher empty, kein Cap-Flag gesetzt = Deadband oder Min-Step): `return []`.
  - [x] Modul-Top-Level-Stub `_policy_multi_stub` löschen.
  - [x] `_dispatch_by_mode`-Branch `case Mode.MULTI:` ändern auf `return self._policy_multi(device, sensor_value_w)`.
  - [x] **Hilfsmethode** (optional, falls Cap-Flag-Proxy nicht reicht): `_is_feed_in_after_smoothing(self, grid_meter_device: DeviceRecord, _sensor_value_w: float | None) -> bool` — liest den Speicher-Buffer für `grid_meter.id`, bildet den Mittelwert, returniert `True` wenn `< -deadband_w` (Einspeisung). Begründung: Robust gegen Race-Conditions zwischen Cap-Flag-Set und nächster Iteration. **Implementierungs-Empfehlung:** Verwende den Buffer; das Flag-Reading ist anfällig, weil Speicher-Policy bei Einspeisung an Max-SoC `_speicher_max_soc_capped=True` setzt (gewünscht), aber bei der **nächsten** Einspeisung im selben Cap-State nicht erneut setzt (Deduplicate-Verhalten). Buffer-Mittel ist deterministisch.
  - [x] **STOP:** Wenn du in `_policy_multi` den Smoothing-Buffer **ein zweites Mal** befüllst, gibt es Doppelfütterung. Speicher-Policy hat `buf.append(sensor_value_w)` schon gemacht (AC 22). Der MULTI-Pfad **liest nur** vom existierenden Buffer.

- [x] **Task 7: `main.py` — `select_initial_mode` einbauen** (AC: 1)
  - [x] In [`main.py::lifespan`](../../backend/src/solalex/main.py) **nach** `battery_pool = BatteryPool.from_devices(devices, ADAPTERS)` und **vor** `controller = Controller(...)`:
    ```python
    initial_mode = select_initial_mode(devices_by_role, battery_pool)
    _logger.info(
        "controller_initial_mode_selected",
        extra={"mode": initial_mode.value, "pool_member_count": len(battery_pool.members) if battery_pool else 0},
    )
    ```
  - [x] Im `Controller(...)`-Call: `mode=Mode.DROSSEL` ersetzen durch `mode=initial_mode`.
  - [x] Import `select_initial_mode` aus `solalex.controller` (analog zu bestehenden `Mode`-Import).

- [x] **Task 8: Drift-Checks** (AC: 25)
  - [x] `grep -rE "mode_selector\.py$|hysteresis\.py$" backend/src/solalex/` → 0 Treffer.
  - [x] `grep -rE "set_mode\(Mode\." backend/src/solalex/controller.py | grep -v test` → Treffer **nur** in `set_mode` (Public-API), `_record_mode_switch_cycle` ruft `set_mode` einmal — ok.
  - [x] `grep -rE "structlog|APScheduler|cryptography|numpy|pandas|SQLAlchemy" backend/src/solalex/controller.py` → 0 Treffer.
  - [x] SQL-Ordering: `001` + `002` + `003` (unverändert von 2.4) — **keine 004 in 3.5**.

- [x] **Task 9: Unit-Tests** (AC: 24)
  - [x] `backend/tests/unit/test_controller_mode_selector.py` mit allen 6 Test-Fällen.
  - [x] `backend/tests/unit/test_controller_mode_switch.py` mit allen 14 Test-Fällen + `test_pool_get_soc_called_at_most_twice_per_event`.
  - [x] `backend/tests/unit/test_controller_multi_policy.py` mit allen 8 Test-Fällen.
  - [x] Wiederverwendung der Helpers aus `_controller_helpers.py` (FakeHaClient, In-Memory-DB, `build_marstek_pool`).
  - [x] `test_mode_switch_dwell_blocks_oscillation` simuliert eine Sinus-SoC-Schwankung: 30 Sekunden, 1-s-Tick, SoC alterniert 92↔98 %; nach Lauf assertet, dass `state_cache.current_mode` höchstens 1× zwischen `'speicher'` und `'drossel'` gewechselt hat.

- [x] **Task 10: Manual-Override Backend** (AC: 27, 28, 29, 30, 31, 33, 34)
  - [x] `Controller.__init__`: neuer Parameter `forced_mode: Mode | None = None`. Speichern als `self._forced_mode`.
  - [x] Neue Methode `Controller.set_forced_mode(self, mode: Mode | None) -> None`:
    1. `old_forced = self._forced_mode; self._forced_mode = mode`.
    2. `_logger.info('mode_override_set' if mode else 'mode_override_cleared', extra={...})`.
    3. Wenn `mode is not None and mode != self._current_mode`:
       - Sensor-Device für Audit: bevorzugt `self._devices_by_role.get('grid_meter') or self._devices_by_role.get('wr_limit')`. Wenn beide `None`, Fallback: ersten Pool-Member-`charge_device` nehmen. Wenn nichts da → `_logger.warning('manual_override_no_anchor_device')` und Persist überspringen (defensive Edge — sollte nie passieren in commissioned setup).
       - `await self._record_mode_switch_cycle(old=self._current_mode, new=mode, reason_detail='manual_override', sensor_device=anchor_device, now=now)`.
    4. Wenn `mode is None`: `state_cache.update_mode(self._current_mode.value)` (Mode bleibt; State-Cache mirror schon aktuell, defensive Re-Mirror akzeptabel).
  - [x] `_evaluate_mode_switch`: erste Early-Return `if self._forced_mode is not None: return None` (vor MULTI-Check).
  - [x] `select_initial_mode`-Signatur: zusätzlicher Parameter `forced_mode: Mode | None = None`. Returntyp ändern zu `tuple[Mode, Mode]` — `(active_mode, baseline_mode)`. Bei `forced_mode` non-`None`: `active_mode = forced_mode`, `baseline_mode = <auto>`. Sonst: beide gleich.
  - [x] `main.py::lifespan`: `forced_mode_str = await get_meta(conn, 'forced_mode')` → validate → `forced_mode = Mode(forced_mode_str) if forced_mode_str in {'drossel','speicher','multi'} else None`. Übergeben an `select_initial_mode(...)` und an `Controller(...)`.
  - [x] `api/routes/control.py`: zwei neue Routes `GET /api/v1/control/mode` und `PUT /api/v1/control/mode`. Pydantic-Schema `ForcedModeRequest` in `api/schemas/control.py` ergänzen.
  - [x] PUT-Handler:
    1. Body parsen (`forced_mode: Literal["drossel","speicher","multi"] | None`).
    2. DB-Update: `set_meta(conn, 'forced_mode', value)` bei non-null oder `delete_meta` bei null. Hinweis: `meta`-Repo hat aktuell kein `delete` — kleine Erweiterung in `repositories/meta.py` nötig (`async def delete_meta(conn, key) -> None`).
    3. `controller = request.app.state.controller`; `await controller.set_forced_mode(Mode(value) if value else None)`.
    4. Response: GET-Body (re-rendered).
  - [x] **Stop:** `set_forced_mode` ist `async`, weil `_record_mode_switch_cycle` async ist. Tests achten auf `await`.

- [x] **Task 11: Manual-Override Frontend** (AC: 32, 35)
  - [x] `frontend/src/routes/Config.svelte`: neuer Card-Block „Regelungs-Modus" unterhalb der existierenden Hardware-Konfiguration. 4-Optionen-Radio mit Klartext-Untertitel.
  - [x] `frontend/src/lib/api/client.ts`: `fetchControlMode(): Promise<ControlModeResponse>` und `setForcedMode(mode: ForcedMode | null): Promise<ControlModeResponse>`. TS-Types in derselben Datei.
  - [x] On-Mount: `fetchControlMode()` → Radio-Auswahl auf `forced_mode` (oder `'auto'` wenn null). `baseline_mode` separat gerendert wenn `forced_mode !== null`.
  - [x] On-Change: optimistisches UI-Update + `setForcedMode(...)`. Bei Fehler: revert + Inline-Hint.
  - [x] Tests in `Config.test.ts` ergänzen (siehe AC 35).
  - [x] **Stop:** Kein Toast, kein Modal, kein Spinner (UX-DR30). Skeleton-Pulse während des PUT-Calls erlaubt, ≥ 400 ms.

- [x] **Task 12: Final Verification** (AC: 24, 25)
  - [x] `cd backend && uv run ruff check .` → grün.
  - [x] `cd backend && uv run mypy --strict src/ tests/` → grün.
  - [x] `cd backend && uv run pytest -q` → grün (alle bisherigen Tests + neue 28 Tests aus 3.5).
  - [x] Drift-Check 1: `grep -rE "Mode\.MULTI" backend/src/solalex/controller.py` → mehrere Treffer im `_dispatch_by_mode` + `_policy_multi`; in `_evaluate_mode_switch` als Early-Return.
  - [x] Drift-Check 2: `grep -rE "_policy_multi_stub" backend/` → 0 Treffer (Stub gelöscht).
  - [x] SQL-Migrations-Ordering: `001` + `002` + `003` (keine 004).
  - [x] Frontend: `npm run lint`, `npm run check`, `npm run test` → grün.
  - [x] Manual-Smoke: `PUT /api/v1/control/mode` mit `{"forced_mode":"drossel"}` aus Config-Page → Polling-Endpoint zeigt sofort `current_mode='drossel'`; `control_cycles` enthält Audit-Row mit `reason='mode_switch: speicher→drossel (manual_override)'`. Anschließend `PUT {"forced_mode":null}` → Auto-Detection + Hysterese resumed.

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Core Architectural Decisions Zeile 230–262](../planning-artifacts/architecture.md) — Controller-Monolith mit Enum-Dispatch + Hysterese-Helper. **Cut 9 + Cut 11.**
- [architecture.md — Zeile 73 + 242 + 640 + 1041](../planning-artifacts/architecture.md) — Hysterese als Teil des Mono-Moduls dokumentiert.
- [prd.md — FR13 + FR16 + FR21 (Zeile 595–608)](../planning-artifacts/prd.md) — Adaptive Strategie-Auswahl, Hysterese-Schwellen, Pool-Konsum.
- [prd.md — Zeile 362–367](../planning-artifacts/prd.md) — „Adaptive Regelungs-Strategie je Setup-Typ" — Modus-Wechsel deterministisch mit Hysterese.
- [prd.md — Zeile 392 (Beta-Gate)](../planning-artifacts/prd.md) — Modus-Wechsel „Akku-voll → Drossel" ohne Oszillation als zweigeteiltes Beta-Gate.
- [prd.md — Zeile 402](../planning-artifacts/prd.md) — Anti-Oszillations-Hysterese 97/93 % + Mindest-Verweildauer.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — Regel 2 (ein Modul pro Adapter — hier nicht direkt relevant, aber Mono-Modul-Prinzip zieht: kein `mode_selector.py`).
- [Story 3.1](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — `Mode`-Enum, `set_mode`-API, `_dispatch_by_mode`, Per-Device-Lock, `_safe_dispatch`.
- [Story 3.2](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — `_policy_drossel`-Logik, Smoothing-Buffer, `_clamp_step`. **Pflichtlektüre für MULTI-Drossel-Reuse.**
- [Story 3.3](./3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation.md) — `BatteryPool.set_setpoint`, `pool.get_soc`, `SocBreakdown.aggregated_pct`.
- [Story 3.4](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md) — **Pflichtlektüre.** `_policy_speicher`-Logik, `_speicher_max_soc_capped`/`_speicher_min_soc_capped`-Flag-Pattern, `_speicher_buffers`, `_read_soc_bounds`. MULTI ruft Speicher zuerst — die Cap-Flags sind die Brücke.
- [Story 5.1a — Live-Betriebs-View](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md) — `state_cache.update_mode`-Heartbeat-Pattern; Mode-Switch-Mirror passt sich nahtlos ein.
- [Story 5.5 (geplant)](../planning-artifacts/epics.md#story-55) — Frontend-Animation für Mode-Übergang. 3.5 produziert die Daten (Audit-Cycle mit `reason='mode_switch: …'`); Story 5.5 verdrahtet das UI.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Reine Backend-Story. **Keine Frontend-Änderungen.** Mode-Switch-Animation ist Story 5.5 (Mode-Chip + Energy-Ring-Fade); 3.5 schreibt nur die Daten in `control_cycles` mit `mode='multi'` / Audit-Reason und mirror in `state_cache.current_mode`.

**Mini-Diff-Prinzip:** Erwarteter Diff-Umfang:
- 1 MOD-Datei: `backend/src/solalex/controller.py` (+ ~150 LOC: `select_initial_mode` ~25 LOC, `_evaluate_mode_switch` ~30 LOC, `_record_mode_switch_cycle` ~40 LOC, `_policy_multi` ~30 LOC, Konstanten + Felder + on_sensor_update-Patch ~20 LOC). `_policy_multi_stub` gelöscht (-3 LOC).
- 1 MOD: `main.py` (+ ~3 LOC `select_initial_mode`-Aufruf + Logging).
- 3 NEU Test-Dateien: `test_controller_mode_selector.py` (~250 LOC, 6 Tests), `test_controller_mode_switch.py` (~600 LOC, 15 Tests inkl. `test_pool_get_soc_called_at_most_twice_per_event`), `test_controller_multi_policy.py` (~400 LOC, 8 Tests).
- Keine SQL-Migration, keine neue Route, keine neue Dependency, keine Frontend-Änderung.

**Dateien, die berührt werden dürfen:**

- **MOD Backend:**
  - `backend/src/solalex/controller.py`
    - Konstanten `MODE_SWITCH_HIGH_SOC_PCT`, `MODE_SWITCH_LOW_SOC_PCT`, `MODE_SWITCH_MIN_DWELL_S`.
    - Modul-Top-Level: `select_initial_mode(devices_by_role, battery_pool) -> Mode`.
    - `Controller.__init__`: `self._mode_baseline`, `self._mode_switched_at`.
    - Neue Methoden: `_evaluate_mode_switch`, `_record_mode_switch_cycle`, `_policy_multi`, optional `_is_feed_in_after_smoothing`.
    - `_dispatch_by_mode`: `Mode.MULTI`-Branch ruft `self._policy_multi(...)` statt `_policy_multi_stub(...)`.
    - `on_sensor_update`: zwischen `_extract_sensor_w` und `_dispatch_by_mode` der Mode-Switch-Block.
    - `_policy_multi_stub` löschen (Modul-Top-Level).
    - `__all__` um `select_initial_mode` ergänzen.
  - `backend/src/solalex/main.py`
    - `from solalex.controller import select_initial_mode` ergänzen.
    - `initial_mode = select_initial_mode(...)` einsetzen, dann `mode=initial_mode` an Controller.

- **NEU Backend (Tests):**
  - `backend/tests/unit/test_controller_mode_selector.py`
  - `backend/tests/unit/test_controller_mode_switch.py`
  - `backend/tests/unit/test_controller_multi_policy.py`

- **NICHT anfassen:**
  - `backend/src/solalex/battery_pool.py` — Pool fertig in 3.3; 3.5 konsumiert nur.
  - `backend/src/solalex/executor/*.py` — Veto-Kaskade greift unverändert.
  - `backend/src/solalex/state_cache.py` — `update_mode`-API unverändert; `current_mode` akzeptiert `'multi'`.
  - `backend/src/solalex/persistence/sql/*.sql` — **keine neue Migration**. `mode='multi'` ist seit `002` erlaubt; `readback_status='noop'` ebenfalls.
  - `backend/src/solalex/persistence/repositories/control_cycles.py` — Insertion akzeptiert beide Werte.
  - `backend/src/solalex/adapters/*` — keine Adapter-Änderungen in 3.5.
  - `backend/src/solalex/api/routes/*.py`, `api/schemas/*.py` — keine API-Änderung.
  - `frontend/src/**/*` — Mode-Animation ist Story 5.5.
  - `pyproject.toml` — keine neue Dependency.

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du `controller.py` in `mode_selector.py` / `hysteresis.py` / `multi.py` splittest — **STOP**. Mono-Modul (Architecture Cut 9, Amendment 2026-04-22).
- Wenn du `Mode.MULTI` in einem Hysterese-Switch erlaubst — **STOP**. AC 7: MULTI bleibt MULTI; Drossel-Fallback ist intern.
- Wenn du eine neue SQL-Migration anlegst (z. B. `004_mode_changes.sql` mit eigener Tabelle) — **STOP**. Mode-Switch nutzt `control_cycles` mit `readback_status='noop'` (AC 6).
- Wenn du `readback_status='mode_switch'` als neuen Wert hinzufügst — **STOP**. CHECK-Constraint erlaubt es nicht; AC 6 nutzt `'noop'`.
- Wenn du den Mode-Switch in einem **Background-Task** persistierst — **STOP**. AC 9: synchron. Audit-Cycle muss vor den Dispatch-Tasks landen.
- Wenn du den Speicher-Buffer (`_speicher_buffers`) im MULTI-Pfad **nochmal** befüllst — **STOP**. Speicher hat `buf.append` bereits getan (AC 22). MULTI nur **lesen**.
- Wenn du im MULTI-Pfad Speicher **und** Drossel **gleichzeitig** dispatcht — **STOP**. AC 21: Drossel greift in MULTI **nur** bei Pool-Voll-Cap.
- Wenn du einen Mode-Override-Endpunkt (`POST /api/v1/control/mode`) hinzufügst — **STOP**. PRD Zeile 362: Mode ist Ergebnis der Erkennung, kein Config-Item. v1.5 evtl. via Diagnose-Hook, nicht in 3.5.
- Wenn du den Drossel-Buffer beim MULTI-Start vor-befüllst — **STOP**. AC 22: Lazy Initialization durch `_policy_drossel` selbst.
- Wenn du `Mode.IDLE` einführst — **STOP**. `state_cache.current_mode` hat `'idle'` als String-Sentinel für Polling-Endpoint, aber `Mode`-Enum bleibt 3-fach (DROSSEL/SPEICHER/MULTI).
- Wenn du den Hysterese-Wechsel auf eine andere Schwelle als 97/93 setzt ohne FR16 zu zitieren — **STOP**. Konstanten sind FR16-Spec.
- Wenn du `_evaluate_mode_switch` in einer Klasse außerhalb `Controller` definierst (z. B. `ModeSelector`) — **STOP**. Mono-Modul; Methoden am Controller.
- Wenn du den `_mode_baseline`-Reset bei Set-Methoden erlaubst (`set_mode` ändert `_mode_baseline`) — **STOP**. Baseline ist startup-immutable.
- Wenn du `_evaluate_mode_switch` zur async-Function machst — **STOP**. Pure Function, keine I/O. AC 17.
- Wenn du in `_policy_multi` `pool.set_setpoint` direkt aufrufst — **STOP**. Speicher-Methode delegiert an Pool; MULTI ruft Speicher auf.
- Wenn du den Mode-Switch außerhalb von `on_sensor_update` triggerst (z. B. periodischer Background-Task) — **STOP**. Trigger sind ausschließlich Sensor-Events. AC 26.
- Wenn du das Mindest-Verweildauer-Tracking via `time.monotonic()` statt `now`-Datetime machst — **STOP**. Tests injizieren `now_fn`; Monotonic-Clock unterläuft die Test-Schiene.
- Wenn du `logging.getLogger(...)` statt `_logger` (bereits via `get_logger(__name__)` initialisiert) verwendest — **STOP**. CLAUDE.md Regel 5.

### Architecture Compliance (5 harte Regeln aus CLAUDE.md)

1. **snake_case überall:** Alle neuen Symbole (`select_initial_mode`, `_evaluate_mode_switch`, `_record_mode_switch_cycle`, `_policy_multi`, `_mode_baseline`, `_mode_switched_at`, `MODE_SWITCH_HIGH_SOC_PCT`, `MODE_SWITCH_LOW_SOC_PCT`, `MODE_SWITCH_MIN_DWELL_S`) sind `snake_case` / `UPPER_SNAKE_CASE`. Keine API-JSON-Felder neu (keine Route-Änderung).
2. **Ein Python-Modul pro Adapter:** Nicht direkt anwendbar — 3.5 berührt keinen Adapter. Mono-Modul-Prinzip zieht analog: Mode-Logik in `controller.py`.
3. **Closed-Loop-Readback:** Mode-Switch-Cycle ist `readback_status='noop'` — kein Hardware-Write, kein Readback-Bedarf. Eigentlicher Regel-Cycle (Folge-Sensor-Event mit neuem Modus) durchläuft die normale Veto-Kaskade.
4. **JSON-Responses ohne Wrapper:** Nicht relevant — keine neue Route in 3.5.
5. **Logging via `get_logger(__name__)`:** Alle neuen Logs nutzen `_logger`. `_logger.info('mode_switch', extra={...})` ist der einzige produktive Info-Log; `_logger.exception('mode_switch_cycle_persist_failed', ...)` für Audit-Persist-Failures. Kein `print`, kein `logging.getLogger`.

### Library & Framework Requirements

- **Keine neuen Dependencies.** Alle Bausteine aus stdlib (`datetime`, `typing`, `enum`).
- **Python 3.13** (`pyproject.toml` unverändert).
- `from __future__ import annotations` in den neuen Test-Files (Projekt-Konvention; `controller.py` hat es bereits).
- **Kein structlog, kein APScheduler.** stdlib `logging` via `get_logger`. Hysterese-Schwellen sind Modul-Konstanten — kein Scheduler-Zwang.

### File Structure Requirements

- **Mode-Logik im Controller-Modul** (Mono-Modul, Cut 9). Kein `controller/multi.py`, kein `policies/`-Verzeichnis.
- **`select_initial_mode` als Modul-Top-Level-Funktion**, nicht als `@classmethod` oder `@staticmethod` am Controller — testbar ohne Controller-Instanz, klare Pure-Function-Semantik.
- **Test-Files spiegeln Source-Pfade:**
  - `tests/unit/test_controller_mode_selector.py` — Selector.
  - `tests/unit/test_controller_mode_switch.py` — Hysterese-Helper + Audit-Cycle.
  - `tests/unit/test_controller_multi_policy.py` — Multi-Policy.

### Testing Requirements

- **Pytest + pytest-asyncio + MyPy strict + Ruff** — alle 4 CI-Gates grün.
- **Coverage ≥ 90 %** auf allen Änderungen in `controller.py`.
- **Keine Playwright, kein Vitest** — reine Backend-Logik. Frontend-Animation ist Story 5.5.
- **Deterministische Hysterese-Tests:** `now_fn`-Injection (aus 3.1 vorhanden) bestimmt den Zeitstempel. Sinus-SoC-Test (`test_mode_switch_dwell_blocks_oscillation`) iteriert über injizierte SoC-Werte am Pool-Mock und einen `now_fn`, der pro Tick um 1 s avanciert.
- **Audit-Cycle-Tests:** Verifizieren `control_cycles`-Row mit `mode='drossel'` (oder `'speicher'`), `readback_status='noop'`, `reason` matcht regex `^mode_switch: (drossel|speicher|multi)→(drossel|speicher|multi) \(.+\)$`.
- **`_evaluate_mode_switch`-Pure-Function-Test:** Mock `pool.get_soc`, `now`, `_current_mode`, `_mode_baseline`, `_mode_switched_at`. Kein DB-Mock erforderlich.
- **MULTI-Policy-Tests:** Verwenden `Controller(...)` mit `mode=Mode.MULTI` direkt. Pool-Mock liefert SoC-Werte; `state_cache` gefüllt mit Smart-Meter-Wert. Assertion auf `decisions`-Inhalt (Speicher-only / Drossel-only / leer).

### Previous Story Intelligence (3.4, 3.3, 3.2, 3.1)

**Aus Story 3.4 (jüngste, höchste Relevanz — Speicher-Logik wird in MULTI gerufen):**

- **`_speicher_max_soc_capped`-Flag** ist die Brücke zwischen Speicher und MULTI. MULTI liest das Flag, um zu entscheiden, ob Drossel als Fallback einspringt.
- **`_policy_speicher` ruft intern `pool.get_soc(state_cache)`.** Der MULTI-Pfad ruft Speicher zuerst — ein zweiter `get_soc`-Call im `_evaluate_mode_switch` ist akzeptabel (IO-frei, sub-ms; AC 18).
- **`_speicher_pending_setpoints`-Pattern** aus 3.4: Setpoints werden erst nach Dispatch-Erfolg gemerkt. MULTI muss daran nichts ändern — `_policy_speicher` setzt das Pending-Memo unverändert.
- **Mode-Cap-Flag-Reset** beim Mode-Switch (AC 12) — analog zu 3.4-Logik, die Flags beim Verlassen des Bands resettet (Patch nach Code-Review).
- **`_read_soc_bounds`** liest aus `wr_charge.config_json` → SoC-Bounds. 3.5 nutzt das **nicht direkt** für die Hysterese-Schwellen (97/93 sind controller-Konstanten, nicht Min/Max-SoC), aber `_policy_speicher` greift weiterhin darauf zu.

**Aus Story 3.3 (Pool-Konsum):**

- **`pool.get_soc(state_cache) -> SocBreakdown | None`** — `None` bei All-Offline. Hysterese-Helper muss `None` defensiv behandeln (AC 17 Schritt 3).
- **`pool.members`-Tuple** — `len(pool.members)` ist die Datenquelle für `select_initial_mode` (1 → SPEICHER, ≥ 2 → MULTI).

**Aus Story 3.2 (Drossel-Logik im MULTI):**

- **`_policy_drossel` ist eine Methode** mit `wr_limit_device`-Pre-Filter. MULTI ruft sie unverändert auf — wenn `wr_limit` nicht in `devices_by_role` ist (defensive Edge), liefert Drossel `None` und MULTI fällt auf `[]` (kein Crash).
- **`_drossel_buffers`-Lazy-Init** — Buffer wird erst bei erstem `_policy_drossel`-Call mit dem `grid_meter.id`-Key erstellt. MULTI muss nichts vorab initialisieren (AC 22).

**Aus Story 3.1 (Foundation):**

- **`Mode`-Enum** + **`set_mode`-API** + **`current_mode`-Property** — fertig.
- **`_dispatch_by_mode`-`match`-Block** — der bestehende `case Mode.MULTI:` ändert nur den Funktions-Aufruf-Body.
- **`_safe_dispatch` + Per-Device-Lock** — multiplexen sich automatisch über die Decisions, die `_policy_multi` zurückgibt (Speicher-Decisions auf `wr_charge`-Members, Drossel-Decision auf `wr_limit`-Device — alle drei `device_id`s sind disjoint).
- **`now_fn`-Injection** — der Hysterese-Helper nutzt `now=self._now_fn()` (oder erhält `now` als Parameter, wie `on_sensor_update` es tut).
- **`_record_noop_cycle`-Pattern** — `_record_mode_switch_cycle` folgt demselben Pattern: synchroner DB-Insert + `state_cache.update_mode` + `kpi_record`.

### Git Intelligence Summary

**Letzte 5 Commits (chronologisch, neueste zuerst):**

- `59aba38 chore(release): beta 0.1.1-beta.8` — Sync-Release.
- `65d675e feat(4.0a): Diagnose-Schnellexport (DB-Dump + Logs als ZIP) + Code-Review-Patches` — Story 4.0a abgeschlossen; Pattern Atomischer-Snapshot relevant für Mode-Switch nicht (kein Snapshot in 3.5).
- `21b0306 fix(4.0): code-review patches` — Logging-Pattern verschärft (sanitize, isEnabledFor-Guards). 3.5 nutzt `_logger.info` und `_logger.exception` analog zu 3.4-Pattern.
- `1a22d8f fix(2.4): code-review patches` — Generic-Adapter-Refit; nicht direkt relevant.
- `91c7f6f feat(2.4): Generic-Adapter-Refit` — Adapter-Layer; ändert nichts am Mode-Switch-Pfad.

**Relevante Code-Patterns aus den Commits:**

- `_speicher_max_soc_capped`-Flag-Pattern (3.4) → Vorlage für `_mode_switched_at`-Tracking.
- `controller_cycle_decision`-DEBUG-Record (4.0) — 3.5 könnte einen `controller_mode_switch`-DEBUG-Record analog hinzufügen, ist aber **nicht verpflichtend** (Audit-Info-Log-Record reicht).
- Synchroner Audit-Persist-Pattern aus `_record_noop_cycle` (3.1) und `_write_failsafe_cycle` (3.1) — `_record_mode_switch_cycle` folgt 1:1.

### Latest Tech Information

- **Python 3.13 `match`-Statement** in `_dispatch_by_mode` ist bereits idiomatic. Keine Änderung an der Struktur.
- **`asyncio.create_task` mit `name=...`** — Mode-Switch-Audit-Cycle läuft synchron, **nicht** als Task. Begründung: AC 9 ordnet den Cycle vor Dispatch-Tasks; ein Task-Spawn würde Reihenfolge-Garantien aufweichen.
- **`@dataclass`-frozen-Felder** — keine neuen Dataclasses in 3.5; bestehende `PolicyDecision`/`SocBreakdown` reichen.
- **Heisenbug-Schutz für Tests:** `now_fn`-Injection ist die kanonische Test-Schiene. Bei Hysterese-Tests wird `now` per Tick avanciert (analog zu Drossel-Smoothing-Tests aus 3.2).

### Project Context Reference

Kein `project-context.md` in diesem Repo. Referenz-Dokumente sind die oben verlinkten `prd.md`, `architecture.md`, `epics.md`, `CLAUDE.md` sowie Vor-Stories 3.1 / 3.2 / 3.3 / 3.4.

### Hysterese-Verhaltens-Matrix (Single-Source-of-Truth)

| Aktiver Modus | Baseline-Modus | aggregated_pct | Dwell abgelaufen? | Aktion |
|---|---|---|---|---|
| `MULTI`     | `MULTI`     | beliebig | – | Kein Switch (AC 7) |
| `SPEICHER`  | `SPEICHER`  | `≥ 97 %` | ja | Switch → `DROSSEL`, Audit-Cycle |
| `SPEICHER`  | `SPEICHER`  | `≥ 97 %` | nein | Kein Switch (AC 8) |
| `SPEICHER`  | `SPEICHER`  | `< 97 %` | – | Kein Switch (Bedingung nicht erfüllt) |
| `DROSSEL`   | `SPEICHER`  | `≤ 93 %` | ja | Switch → `SPEICHER`, Audit-Cycle |
| `DROSSEL`   | `SPEICHER`  | `≤ 93 %` | nein | Kein Switch |
| `DROSSEL`   | `DROSSEL`   | `≤ 93 %` | ja | Kein Switch (AC 5 — Baseline blockt) |
| `DROSSEL`   | `MULTI`     | `≤ 93 %` | ja | Switch → `SPEICHER` (analog Speicher-Baseline) |
| `SPEICHER`  | `MULTI`     | – | – | Unmöglich — MULTI wechselt nicht (AC 7) |

**Begründung Baseline-Gate:** Baseline encodiert das Setup-Regime aus `select_initial_mode`. Ein DROSSEL-only-Setup darf nie zu SPEICHER wechseln (kein Pool); ein SPEICHER-Setup darf zwischen SPEICHER und DROSSEL pendeln (Akku-Voll-Schutz). MULTI bleibt MULTI (interne Drossel-Logik).

### Multi-Modus-Entscheidungs-Tabelle (`_policy_multi`)

| `aggregated_pct` | Smart-Meter `smoothed` | `_speicher_max_soc_capped` (vor diesem Aufruf) | Speicher-Output | MULTI-Output |
|---|---|---|---|---|
| `< max_soc`, `> min_soc` | `< -deadband` (Einspeisung) | – | `[N Pool-Decisions]` | `[N Pool-Decisions]` (Speicher-only) |
| `< max_soc`, `> min_soc` | `> deadband` (Bezug) | – | `[N Pool-Decisions]` (entlade) | `[N Pool-Decisions]` (Speicher-only) |
| beliebig | innerhalb Deadband | – | `[]` | `[]` (Deadband) |
| `>= max_soc` | `< -deadband` (Einspeisung) | – | `[]`, Flag→True | `[Drossel-Decision]` (Pool-Voll) |
| `>= max_soc` | `> deadband` (Bezug) | – | `[N Entlade-Decisions]` | `[N Entlade-Decisions]` |
| `<= min_soc` | `< -deadband` (Einspeisung) | – | `[N Lade-Decisions]` | `[N Lade-Decisions]` |
| `<= min_soc` | `> deadband` (Bezug) | – | `[]`, Flag→True | `[]` (kein Drossel-Anstieg, AC 3) |

**Hinweis Sign-Konvention:** Speicher entscheidet pro Vorzeichen. MULTI delegiert komplett an Speicher und ruft Drossel **nur** im Cap-Fall mit Einspeisung.

### Anti-Patterns & Gotchas

- **KEIN Switching während eines Cycle-Dispatch-Tasks.** Mode-Switch passiert in `on_sensor_update` synchron; bestehende `_safe_dispatch`-Tasks laufen mit dem zur Spawn-Zeit gültigen Mode (das ist OK — `_safe_dispatch` nutzt nur `decision.mode`, nicht `self._current_mode`).
- **KEIN Hysterese-Switch in einem Background-Task** (Periodic-Job o. ä.). Alle Trigger sind `on_sensor_update`-Events.
- **KEIN Logging des aggregated_pct auf `info` jedes Sensor-Events.** Nur beim tatsächlichen Switch (`mode_switch`) und beim Cap-Eintritt (Speicher-Logik aus 3.4 — bleibt unverändert).
- **KEIN expliziter `state_cache.update_mode`-Call in `select_initial_mode`** (AC 23). Der erste Cycle (Mode-Switch oder normaler Sensor-Cycle) mirrored den Mode automatisch.
- **KEIN `await` in `_evaluate_mode_switch`.** Pure-Function (AC 17).
- **KEIN Hardcoded `Mode.SPEICHER`** als Fallback in MULTI-Setup. Wenn `_policy_multi` mit `pool=None` aufgerufen wird (defensive Edge), fällt es auf `_policy_drossel` zurück — nicht auf Speicher.
- **KEIN Doppel-Persist des Audit-Cycle.** Wenn `set_mode` zweimal innerhalb desselben `on_sensor_update`-Calls aufgerufen würde (sollte unmöglich sein, weil `_evaluate_mode_switch` höchstens einen Switch returniert), würde nur der erste Audit-Cycle persistiert. Defensive Property: `_evaluate_mode_switch` returniert maximal einmal pro Call.
- **KEIN Reset von `self._mode_baseline`** in irgendeiner Methode außer `__init__`. Baseline ist immutable.
- **KEIN Pool-`get_soc` während des Hysterese-Helpers, wenn der Pool offline ist.** `pool.get_soc` returniert `None` defensive — der Helper bricht ab.
- **KEIN `int(round(aggregated_pct))`-Konvertierung** für die Hysterese-Schwelle. `aggregated_pct` ist ein Float; Vergleich gegen `97.0`/`93.0` ist exakt.
- **KEIN Speichern von `aggregated_pct` in `state_cache`.** Pool ist die SoC-Wahrheit (3.3); 3.5 cacht nicht.

### Source Tree — Zielzustand nach Story

```
backend/src/solalex/
├── controller.py                              [MOD — select_initial_mode, _evaluate_mode_switch, _record_mode_switch_cycle, _policy_multi (replaces stub), _mode_baseline + _mode_switched_at fields, MODE_SWITCH_*-Konstanten, on_sensor_update-Patch]
├── battery_pool.py                            [unverändert — Pool aus 3.3]
├── adapters/                                  [unverändert]
├── executor/                                  [unverändert]
├── persistence/                               [unverändert — keine neue Migration]
├── kpi/                                       [unverändert]
├── state_cache.py                             [unverändert — current_mode unterstützt 'multi' bereits]
└── main.py                                    [MOD — select_initial_mode-Aufruf vor Controller-Bau]

backend/tests/unit/
├── test_controller_mode_selector.py           [NEW]
├── test_controller_mode_switch.py             [NEW]
└── test_controller_multi_policy.py            [NEW]
```

Frontend: **keine Änderungen.** Mode-Animation ist Story 5.5.

### Beta-Gate-Bezug

Aus PRD Zeile 392: **„Adaptive Regelungs-Strategie: Drossel-Modus stabil ±5 W bei Hoymiles UND Speicher-Modus stabil ±30 W bei Marstek Venus PLUS expliziter sauberer Modus-Wechsel ‚Akku-voll → Drossel' ohne Oszillation."** 3.5 liefert die **Mode-Wechsel-Hälfte** des Beta-Gates: 97/93 %-Hysterese + 60-s-Verweildauer + Audit-Cycle. Die **Empirie** (kein Flackern bei realen Marstek-Setups) verifiziert Alex via 24-h-Dauertest (Story 3.7) am echten 1-Akku-Setup.

### Performance & Sicherheit

- **NFR2 (Cycle-Latenz ≤ 1 s):** Synchroner Pipeline-Pfad bleibt < 1 ms — Mode-Switch-Auswertung ist Dict-Lookup + Datetime-Diff + 1× `pool.get_soc` (sub-ms). Audit-Persist ist ein DB-Insert (~5 ms) — synchron, akzeptabel weil selten.
- **Safety:** Mode-Switch ist nicht-disruptiv — alter Modus wird ohne abrupten Hardware-Befehl beendet (kein „Wir setzen erstmal alles auf 0"-Reset). Der nächste Sensor-Event mit dem neuen Modus produziert die nächsten Decisions normal.
- **Concurrency:** Per-Device-Locks aus 3.1 sind unbeeinflusst. Mode-Switch passiert vor dem Task-Spawn, also außerhalb jedes Locks.
- **Audit-Trail:** Jeder Mode-Switch produziert genau einen `control_cycles`-Row mit `readback_status='noop'` + `reason='mode_switch: ...'`. Story 4.5 (Diagnose-Export) wird das Filter-Pattern `WHERE reason LIKE 'mode_switch:%'` nutzen.

### Scope-Grenzen zur Folge-Story (3.6, 3.7, 5.5)

- **Story 3.6 (User-Config — Min/Max-SoC + Nacht-Entlade):** Frontend-Settings für SoC-Bounds. 3.5 nutzt die controller-Konstanten 97/93 für den Mode-Switch — **nicht** die `min_soc`/`max_soc` aus `wr_charge.config_json`. Das ist Absicht: Hysterese-Schwellen sind regulator-typisch fix; SoC-Bounds steuern Hard-Caps in der Speicher-Policy (3.4).
- **Story 3.7 (Fail-Safe + 24-h-Dauertest):** Recovery + Health-Marker. 3.5 nutzt den Fail-Safe-Wrapper aus 3.1 unverändert; Mode-Switch im Fail-Safe-Zustand (`ha_ws_disconnected`) ist akzeptabel — der Audit-Cycle wird trotzdem persistiert, der nächste Folge-Sensor-Event durchläuft den Fail-Safe-Pfad mit dem neuen Modus.
- **Story 5.5 (Mode-Chip + Energy-Ring-Animation):** Frontend-Animation. 3.5 schreibt `state_cache.current_mode` und einen Audit-Cycle; 5.5 verdrahtet das UI über das `/api/v1/control/state`-Polling.

### Deferred (out-of-scope for 3.5, documented for v1.5+)

- **User-Override-Endpunkt** (`POST /api/v1/control/mode`): v1.5 evtl. via Diagnose-Hook. PRD verbietet es als reguläres Config-Item (Mode = Setup-Erkennung).
- **Per-Device-Hysterese-Schwellen** über `device.config_json` (z. B. `mode_switch_high_soc_pct`): v1.5. v1 hat globale Konstanten.
- **Multi-Pool-Setup** (mehrere Pools nebeneinander, z. B. Marstek + Anker): v1.5. `select_initial_mode` betrachtet einen Pool.
- **Adaptiver Hysterese-Span** basierend auf empirischer Latenz (FR34): v2. Heute ist 97/93 fix.
- **Mode-Switch-Latenz-Messung** (im `latency_measurements`-Sinne): v2. 3.5 misst nichts.
- **Rückwärts-Mode-Switch nach Pool-Reload (Add-on-Restart):** v1.5. Heute startet jeder Restart mit `select_initial_mode`-Resultat (kein Persist von `_mode_baseline` vs. aktivem Modus).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- Backend Tests: `cd backend && uv run pytest -q` → 336 passed (28 neu aus 3.5 + 2 patches an Story-3.4-Tests).
- Backend Lint/Types: `uv run ruff check src/ tests/` + `uv run mypy --strict src/ tests/` grün (94 source files).
- Frontend Tests: `cd frontend && npm run test` → 61 passed (5 neue Config-Override-Tests).
- Frontend Lint/Check/Build: `npm run lint`, `npm run check`, `npm run build` grün (276 files, 0 warnings).
- Drift-Checks: kein `mode_selector.py` / `hysteresis.py`, `_policy_multi_stub` aus Source gelöscht (nur in Test-Assertion referenziert), keine `structlog` / `APScheduler` / `cryptography` / `numpy` / `pandas` / `SQLAlchemy` in `controller.py`, SQL-Migrations 001/002/003 unverändert (keine 004 in 3.5).

### Completion Notes List

- **`select_initial_mode` als Modul-Top-Level-Funktion** mit Override-Awareness (returniert `tuple[active_mode, baseline_mode]` per AC 29). Baseline encodiert das auto-detected Setup-Regime, sodass nach Override-Aufhebung die Hysterese am korrekten Setup ansetzt.
- **`_evaluate_mode_switch`** als Pure-Function (AC 17 — keine I/O, keine `set_mode`-Aufrufe, keine DB-Writes). Side-Effects ausschließlich in `_record_mode_switch_cycle`. Override fully suppresses hysteresis (erste Early-Return AC 29).
- **`_record_mode_switch_cycle`** persistiert synchron einen `readback_status='noop'`-Cycle mit `reason='mode_switch: <old>→<new> (<grund>)'` (AC 6 + 9). Persist-Failures blockieren den Switch nicht; KPI-Record ebenfalls fehlertolerant.
- **`_policy_multi`** ersetzt den Stub: Speicher zuerst, Drossel-Fallback nur bei `_speicher_max_soc_capped=True` UND Einspeisung (`_is_feed_in_after_smoothing` liest den existierenden Speicher-Buffer per AC 22). Pool=None → defensive Drossel-only-Rückfall.
- **`set_forced_mode` (async)** schreibt synchron einen Audit-Cycle mit `reason='manual_override'` wenn `mode != self._current_mode`. Clearing bumpt den Dwell-Tracker, sodass die erste Auto-Switch-Auswertung die volle 60-s-Window abwartet (AC 34).
- **API: `GET / PUT /api/v1/control/mode`** als Bare-Object-Response ({forced_mode, active_mode, baseline_mode}). PUT-Body via Pydantic-`Literal` validiert; ungültige Werte → 422.
- **`main.py::_load_forced_mode`** lädt persisten Override aus `meta.forced_mode` beim Lifespan-Startup; ungültige Werte → `_logger.warning('forced_mode_invalid_value')` und Fallback auf `None` (kein Lock-Out bei hand-edited DB).
- **Frontend: Config.svelte „Regelungs-Modus"-Card** mit 4-Optionen-Radio, Auto-PUT bei Change, optimistisches Update + Revert-on-Error, Inline-Hint bei aktivem Override mit `baseline_mode`. Card hidden wenn Backend `/api/v1/control/mode` failt — Wizard-Setup bleibt nutzbar.
- **Story-3.4-Test-Patches**: `test_speicher_only_one_noop_attribution_cycle_per_event` filtert nun auf Non-Mode-Switch-Cycles (AC bleibt valide); `test_not_invoked_in_drossel_mode` pinnt `_mode_baseline=Mode.DROSSEL`, damit der Hysterese-Switch nicht direkt zurückspringt — beide Patches dokumentieren den Story-3.5-Effekt explizit.
- **Keine SQL-Migration** in 3.5 (`meta.forced_mode` lebt im bestehenden Key-Value-Schema); **keine neue Dependency**; **kein** Mono-Modul-Split (Hysterese + Selector + Multi-Policy bleiben in `controller.py`).

### File List

**Modified:**
- `backend/src/solalex/controller.py` — Konstanten `MODE_SWITCH_HIGH_SOC_PCT/LOW_SOC_PCT/MIN_DWELL_S`, Modul-Top-Level `select_initial_mode`, neue Methoden `_evaluate_mode_switch`, `_record_mode_switch_cycle`, `_policy_multi`, `_is_feed_in_after_smoothing`, `_anchor_device_for_audit`, `set_forced_mode`. `__init__` neue Parameter `baseline_mode` + `forced_mode`. `_dispatch_by_mode` MULTI-Branch nutzt nun die Methode. `on_sensor_update` wertet die Hysterese vor dem Dispatch aus. `_policy_multi_stub` gelöscht. `__all__` erweitert.
- `backend/src/solalex/main.py` — `select_initial_mode`-Aufruf in lifespan + `_load_forced_mode`-Helper, übergibt `(initial_mode, baseline_mode, forced_mode)` an Controller.
- `backend/src/solalex/api/routes/control.py` — neue Routes `GET /api/v1/control/mode` + `PUT /api/v1/control/mode` mit Bare-Object-JSON, `_require_controller`-Helper, `_mode_or_none`.
- `backend/src/solalex/api/schemas/control.py` — `ForcedMode`, `ForcedModeRequest`, `ControlModeResponse` Pydantic-Schemas.
- `backend/src/solalex/persistence/repositories/meta.py` — `delete_meta`-Funktion ergänzt.
- `backend/tests/unit/test_controller_speicher_policy.py` — zwei Tests an Story-3.5-Verhalten angepasst (Filter auf non-mode-switch / `_mode_baseline=DROSSEL` pin).
- `frontend/src/lib/api/types.ts` — `ForcedMode`, `ForcedModeChoice`, `ControlModeResponse` Typen.
- `frontend/src/lib/api/client.ts` — `fetchControlMode`, `setForcedMode` API-Calls.
- `frontend/src/routes/Config.svelte` — neuer Card-Block „Regelungs-Modus" mit 4-Radio + Baseline-Hint + Error-Revert + Pending-Disable. CSS für `.mode-radio-group` / `.mode-radio-row`.

**Added:**
- `backend/tests/unit/test_controller_mode_selector.py` — 16 Tests (Selector-Tabelle, Override-Tuple, Konstanten-Pin, parametrisierte Decision-Table).
- `backend/tests/unit/test_controller_mode_switch.py` — 25 Tests (Hysterese-Branches, Dwell-Anti-Oszillation, Audit-Cycle + State-Cache-Mirror + Info-Log, Cap-Flag-Reset, Pure-Function-Disziplin, Override-Persistenz + Resume + No-Op-Audit-on-Clear, `pool.get_soc`-Call-Counter).
- `backend/tests/unit/test_controller_multi_policy.py` — 10 Tests (Pool-unter-Max-SoC nur Speicher, Symmetrie-keine-Drossel, Max-SoC + Einspeisung Drossel übernimmt, Min-SoC + Bezug kein Anstieg, Buffer-Reuse, Pool-None-Fallback, Stub-Replace, kein doppelter Speicher-Buffer-Append).
- `backend/tests/unit/test_control_mode_route.py` — 10 Tests (GET/PUT-Roundtrip, Persistenz in `meta`-Tabelle, Null-Body clear, ungültiger Wert 422, Audit-Cycle-Reason, Override-Restore beim Startup ohne Audit-Cycle, ungültiger Meta-Wert collapsiert auf None).
- `frontend/src/routes/Config.test.ts` — 5 Tests (Render Override-Section, Hide bei API-Fehler, PUT-Aufruf bei Radio-Wechsel, Revert-on-Error, Baseline-Hint mit Override aktiv).

### References

- [epics.md — Story 3.5, Zeile 966–996](../planning-artifacts/epics.md)
- [architecture.md — Core Architectural Decisions Zeile 230–262 + Project Structure Zeile 638–642 + Amendment-Log Zeile 1041](../planning-artifacts/architecture.md)
- [prd.md — FR13 / FR16 / FR21 / FR22 (Zeile 595–608) + Adaptive Strategie Zeile 362–367 + Beta-Gate Zeile 392 + Anti-Oszillation Zeile 402](../planning-artifacts/prd.md)
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md)
- [Story 3.1 — Core Controller (Mode-Enum, set_mode, _dispatch_by_mode, _safe_dispatch, Per-Device-Lock)](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md)
- [Story 3.2 — Drossel-Policy (1:1 wiederverwendet im MULTI-Pfad)](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md)
- [Story 3.3 — BatteryPool API (`get_soc`, `set_setpoint`, `members`)](./3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation.md)
- [Story 3.4 — Speicher-Policy + Cap-Flag-Pattern (Brücke zu MULTI)](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md)
- [Story 5.1a — `state_cache.update_mode`-Heartbeat](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md)
- [controller.py — Mode-Enum, `_dispatch_by_mode`, `_policy_drossel`, `_policy_speicher`, `_policy_multi_stub`](../../backend/src/solalex/controller.py)
- [battery_pool.py — Pool-API](../../backend/src/solalex/battery_pool.py)
- [main.py — Lifespan + Controller-Bau (Mode-Param)](../../backend/src/solalex/main.py)
- [persistence/sql/002_control_cycles_latency.sql — `mode IN ('drossel','speicher','multi')` + `readback_status IN ('passed','failed','timeout','vetoed','noop')`](../../backend/src/solalex/persistence/sql/002_control_cycles_latency.sql)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.5 erstellt und auf `ready-for-dev` gesetzt. Adaptive Strategie-Auswahl (Initial-Modus aus `devices_by_role` + `battery_pool`-Member-Count), Hysterese-basierter SPEICHER↔DROSSEL-Switch (97/93 %, 60 s Mindest-Verweildauer, Baseline-Gate), MULTI-Modus produktiv (`_policy_multi` ersetzt Stub, ruft Speicher zuerst, Drossel-Fallback nur bei Pool-Voll mit Einspeisung), Audit-Cycle als `readback_status='noop'`-Row mit `reason='mode_switch: <old>→<new> (<grund>)'`. Keine SQL-Migration, keine API-/Frontend-Änderung, keine neue Dependency. Tests (28 Stück) decken Selector-Edge-Cases, Hysterese-Switch-Branches, Dwell-Time-Anti-Oszillation, MULTI-Policy-Branching (Pool-unter/an/gleich Max-/Min-SoC), Audit-Persist + Failure-Tolerance, Pure-Function-Disziplin des Hysterese-Helpers. Pattern-Transfer aus Story 3.4 (Cap-Flag-Brücke), Story 3.1 (`_record_noop_cycle`-Pattern), Story 3.2 (Drossel-Buffer-Reuse). | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Story 3.5 implementiert und auf `review` gesetzt. Implementation umfasst: (1) Modul-Top-Level `select_initial_mode(devices_by_role, battery_pool, forced_mode)` mit `tuple[active, baseline]`-Return (Override-aware AC 29). (2) Konstanten `MODE_SWITCH_HIGH_SOC_PCT/LOW_SOC_PCT/MIN_DWELL_S` am Modul-Top. (3) `_evaluate_mode_switch` als Pure-Function (AC 17). (4) `_record_mode_switch_cycle` mit synchroner Audit-Cycle-Persistenz + `state_cache.update_mode` + KPI-Record (AC 6, 9). (5) `_policy_multi` ersetzt Stub: Speicher zuerst, Drossel nur bei Pool-Voll-Cap mit Einspeisung; `_is_feed_in_after_smoothing` liest existierenden Speicher-Buffer (AC 22 — kein doppelter `buf.append`). (6) `set_forced_mode` async + `_anchor_device_for_audit`-Helper. (7) `Controller.__init__` neue Parameter `baseline_mode` + `forced_mode`. (8) `on_sensor_update` evaluiert Mode-Switch synchron VOR `_dispatch_by_mode` (AC 9). (9) Backend-API `GET / PUT /api/v1/control/mode` mit Pydantic-Validierung; `delete_meta`-Repo-Helper. (10) `main.py::_load_forced_mode` lädt Override aus `meta`-Tabelle beim Startup; ungültige Werte → Warning + Fallback `None`. (11) Frontend: `Config.svelte` neuer „Regelungs-Modus"-Card-Block mit 4-Radio, Auto-PUT, optimistisches Update + Revert-on-Error, Baseline-Hint. (12) Tests: 61 neue Cases verteilt auf `test_controller_mode_selector.py` (16), `test_controller_mode_switch.py` (25), `test_controller_multi_policy.py` (10), `test_control_mode_route.py` (10), `Config.test.ts` (5). 2 Story-3.4-Tests an Hysterese-Verhalten angepasst (Filter / Baseline-Pin). Verifikation: Backend 336 pytest passed, Ruff + MyPy --strict grün; Frontend 61 vitest passed, ESLint + svelte-check + Build grün. Keine SQL-Migration, keine neue Dependency, kein Mono-Modul-Split. | Claude Opus 4.7 |
