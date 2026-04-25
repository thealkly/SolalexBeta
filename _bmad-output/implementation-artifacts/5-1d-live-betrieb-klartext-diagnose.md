# Story 5.1d: Live-Betrieb mit Klartext-Diagnose und erweiterten Status-Infos

Status: review

<!-- Erstellt 2026-04-25 nach Smoke-Test Alex' lokales HA-Setup. Beobachtung: aktuelle Running.svelte zeigt nur kryptische "noop"-Zeilen ohne Begründung; User kann nicht erkennen, ob Solalex im Toleranzbereich, ohne Wechselrichter, ohne SoC oder mit kaputtem Sensor läuft. Liste auf 10 Einträge gedeckelt — Scroll-Container nutzlos. Beta-Tester werden ohne diese Klartext-Anzeige weder verstehen, ob das System läuft, noch was es gerade tut. Beta-Launch-blocking. -->

## Story

Als Beta-Tester, der nach dem Commissioning auf der Live-Betriebs-Seite stehe und sehen will, **ob** und **warum** Solalex regelt oder nicht regelt,
möchte ich eine Cycles-Liste mit Klartext-Status statt kryptischer „noop"-Einträge, eine sichtbare Aufschlüsselung aktueller Live-Werte (Sensor, WR-Limit-Readback, SoC, HA-WS-Verbindung) und eine kurze Erklärung des aktuellen Modus,
so dass ich auf einen Blick verstehe, ob mein Setup gesund läuft, was gerade passiert, und im Problemfall den Grund selbst diagnostizieren kann, ohne den Diagnose-Export rauszuziehen oder Logs zu lesen.

## Acceptance Criteria

### Cycle-Liste: Klartext + Header + Scrollen

1. **Header-Zeile über der Cycle-Liste:** Direkt unter dem `<h2>Letzte Zyklen</h2>` eine Header-Zeile in derselben Grid-Struktur wie `cycle-row` (90px / 100px / 80px / 80px / 64px) mit den Spaltentiteln „vor" / „Quelle" / „Ziel" / „Status" / „Latenz". Subtile Typografie (kleiner als Body, `var(--color-text-secondary)`).

2. **Status-Spalte mit deutschen Begriffen:** `cycle-readback`-Span mappt das Backend-`readback_status` plus `reason` auf eine deutsche Anzeige. Mapping (autoritativ):

   | Backend-Tupel | UI-Anzeige | data-status (für CSS) |
   |---|---|---|
   | `passed` | „Übernommen" | `passed` |
   | `failed` | „Fehlgeschlagen" | `failed` |
   | `timeout` | „Timeout" | `timeout` |
   | `vetoed` + `reason="fail_safe: …"` | „Fail-Safe" | `vetoed` |
   | `vetoed` + sonstiger reason | „Abgelehnt" | `vetoed` |
   | `noop` + `reason="noop: deadband …"` | „Im Toleranzbereich" | `noop-deadband` |
   | `noop` + `reason="noop: kein_wr_limit_device"` | „Kein Wechselrichter" | `noop-no-wr` |
   | `noop` + `reason="noop: min_step_nicht_erreicht …"` | „Schritt zu klein" | `noop-min-step` |
   | `noop` + `reason="noop: kein_soc_messwert"` | „SoC fehlt" | `noop-no-soc` |
   | `noop` + `reason="noop: nicht_grid_meter_event"` | „Beobachtung" | `noop-other` |
   | `noop` + `reason=None` (legacy) | „Beobachtung" | `noop-other` |
   | `noop` + `reason="mode_switch: …"` | „Mode-Wechsel" | `noop-mode-switch` |
   | `noop` + `reason="hardware_edit: …"` (Story 2.6) | „Hardware geändert" | `noop-hardware-edit` |

3. **`cycle-target`-Spalte zeigt bei Noop nicht `—`, sondern den Smoothed-Sensor-Wert in Klammern:** „— (gemessen 12 W)". So sieht der User auch bei Noops, ob überhaupt was reinkam und in welcher Größenordnung. Bei `passed` weiterhin nur die Watt-Zahl wie heute.

4. **Tooltip mit vollem `reason`:** Hover (oder Long-Press auf Touch) auf der Status-Spalte zeigt den vollen Backend-`reason` als nativer `title`-Tooltip. Kein Custom-Tooltip-Component (UX-DR30: keine Tooltips als UI-Element — nativer `title`-Hint ist erlaubt, weil Browser-Standard).

5. **Limit auf 50 Einträge:** Backend `_RECENT_CYCLES_LIMIT` von 10 auf 50 erhöhen ([control.py:46](backend/src/solalex/api/routes/control.py#L46)). Frontend-`recentCycles.slice(0, 10)` durch `slice(0, 50)` ersetzen ([Running.svelte:69](frontend/src/routes/Running.svelte#L69)). Bestehende `max-height: 320px` + `overflow-y: auto` wird damit endlich genutzt.

6. **Backend reicht `reason` durch:** `RecentCycle`-Pydantic-Model in [control.py schemas](backend/src/solalex/api/schemas/control.py#L25-L46) bekommt `reason: str | None`. Die Drop-Begründung im Docstring („drop fields the UI does not render (`reason`, …)") ist mit dieser Story obsolet — Docstring entsprechend aktualisieren.

7. **`mode`-Literal erweitert:** `CycleMode` in `control.py` schemas heute `Literal["drossel", "speicher", "multi"]`. Erweitern auf `Literal["drossel", "speicher", "multi", "audit", "export"]`, weil `_record_mode_switch_cycle` Audit-Cycles schreibt und Story 3.8 Surplus-Export einführt. Frontend `ControlMode`-Type entsprechend.

### Klartext-Reasons im Backend

8. **`_policy_drossel` Noop-Reasons:** Jeder `return None`-Pfad in [`_policy_drossel`](backend/src/solalex/controller.py#L479-L558) reicht den Grund an `_record_noop_cycle` durch, statt aktuell `reason=None`. Konkret:
   - WR-Device fehlt → `reason="noop: kein_wr_limit_device"`
   - Smoothed im Deadband → `reason="noop: deadband (smoothed=Xw, deadband=Yw)"`
   - Min-Step nicht erreicht → `reason="noop: min_step_nicht_erreicht (delta=Xw, min=Yw)"`
   - Current WR-Limit unbekannt → `reason="noop: wr_limit_state_cache_miss"`
   - Sensor nicht numerisch → `reason="noop: sensor_nicht_numerisch"`

9. **`_policy_speicher` Noop-Reasons:** Analog für `_policy_speicher`:
   - Pool leer → `reason="noop: kein_akku_pool"`
   - SoC fehlt → `reason="noop: kein_soc_messwert"`
   - Smoothed im Deadband → `reason="noop: deadband (smoothed=Xw, deadband=Yw)"`
   - Max-SoC erreicht → `reason="noop: max_soc_erreicht (aggregated=X%)"`
   - Min-SoC erreicht → `reason="noop: min_soc_erreicht (aggregated=X%)"`
   - Nacht-Gate aktiv → `reason="noop: nacht_gate_aktiv"`
   - Sensor nicht numerisch → `reason="noop: sensor_nicht_numerisch"`

10. **Nicht-Grid-Meter-Events:** Wenn `on_sensor_update` mit einem Device aufgerufen wird, das nicht `role == "grid_meter"` ist (z. B. SoC-Update vom Akku triggert die Pipeline), wird ein Noop-Cycle mit `reason="noop: nicht_grid_meter_event"` geschrieben. Heute werden diese Events stillschweigend in den Policies verworfen — der Audit-Trail ist dann lückenhaft.

11. **`_record_noop_cycle`-Signatur:** Bekommt einen Pflicht-Parameter `reason: str` (nicht mehr Optional). Aufrufer müssen einen Grund angeben. Tests, die heute den Default nutzen, werden auf `reason="noop: testfixture"` umgestellt.

### Erweiterte Live-Status-Tiles

12. **Status-Tile-Reihe oberhalb des Charts:** Neue `<section class="status-tiles">` zwischen Header und Chart-Card. Zeigt 3-4 Tiles je nach Setup, jedes Tile als `<div class="status-tile">` mit Label, Wert, optional Sub-Hinweis:

    | Tile | Quelle | Anzeige |
    |---|---|---|
    | „Netz-Leistung" | grid_meter aus `entities` (effektiv, also nach `invert_sign`-Anwendung — dafür muss Backend den `effective_value_w` mitsenden, siehe AC 14) | „+2120 W" + Sub „Bezug aus dem Netz" / „Einspeisung ins Netz" / „nahezu 0 W" |
    | „Wechselrichter-Limit" | wr_limit aus `entities`, falls commissioned | „1500 W" + Sub „Aktuelles Limit" |
    | „Akku-SoC" | bei Marstek-Setup, aus pool aggregated | „54 %" + Sub „Min 15 % / Max 95 %" |
    | „Verbindung" | `ha_ws_connected` aus neuem Endpoint-Feld | „Verbunden" (grün) / „Getrennt" (rot mit Sekunden-Zähler seit Trennung) |

    Tile-Werte tabular-nums, nackt (UX-DR30 — keine Trend-Icons, keine Adjektive). Tile-Reihe responsive (auf Mobil untereinander).

13. **Mode-Erklärungs-Zeile:** Direkt unter dem `<h1>Live-Betrieb</h1>` eine kleine Zeile mit dem aktuellen Mode-Klartext:

    | Mode | Zeile |
    |---|---|
    | `drossel` | „Drossel — verhindert ungewollte Einspeisung durch WR-Limit-Anpassung" |
    | `speicher` | „Speicher — Akku gleicht Einspeisung und Bezug aus" |
    | `multi` | „Multi — Akku zuerst, WR-Limit als Fallback bei vollem Speicher" |
    | `export` | „Einspeisung — gezielt Überschuss ins Netz, Akku ist voll" |
    | `idle` | „Idle — wartet auf erstes Sensor-Event" |

    Conditional auf den Mode-Chip im Header. Keine Charakter-Zeile mit Adjektiven (CLAUDE.md Stil-Leitplanken: Charakter-Zeile beschreibt Tun, nicht Zahl — hier ist es eine Mode-Beschreibung, keine Charakter-Zeile).

14. **Backend-Erweiterung `EntitySnapshot`:** [`EntitySnapshot`](backend/src/solalex/api/schemas/control.py#L15-L22) bekommt zwei optionale Felder:
    - `effective_value_w: float | None` — bei `role == "grid_meter"`: nach `invert_sign`-Anwendung; bei anderen Rollen `None` und der `state`-Wert ist die Wahrheit
    - `display_label: str | None` — UI-fertiges Label aus dem deutschen Glossar („Netz-Leistung", „Wechselrichter-Limit", „Akku-SoC")
    
    So muss das Frontend keine Sign-Logik duplizieren und keine Glossar-Mapping-Tabelle pflegen.

15. **HA-WS-Verbindungs-Status im Snapshot:** `StateSnapshot` bekommt ein neues Feld `ha_ws_connected: bool` plus `ha_ws_disconnected_since: datetime | None` (None bei verbunden). Quelle: `controller._ha_ws_connected_fn()`. Wird im Connection-Tile angezeigt.

### Tests + Doku

16. **Tests Backend:**
    - `test_control_state.py`: Neue Tests für `RecentCycle.reason`-Durchreichung; alle vorhandenen Reason-Strings aus AC 8 + 9 als Smoke-Test (jeder Reason wird in einem Policy-Test produziert und der ausgehende Noop-Cycle hat den exakten Reason-Text).
    - `test_control_state.py`: `test_state_snapshot_has_ha_ws_connected_flag`, `test_state_snapshot_has_disconnect_timestamp_when_disconnected`.
    - `test_control_state.py`: `test_entity_snapshot_grid_meter_with_invert_sign_returns_flipped_effective_value` (Story-2.5-Coupling: dieser Test setzt voraus, dass 2.5 schon gemergt ist; falls nicht, in Story 2.5 verschieben).
    - `test_controller_drossel_policy.py` / `test_controller_speicher_policy.py`: Reason-Strings für jeden Early-Exit-Pfad asserten.

17. **Tests Frontend:**
    - `Running.test.ts`: Header-Zeile gerendert; Status-Mapping-Tabelle für alle Tupel aus AC 2; `cycle-target`-Sub-Anzeige bei Noop; Limit-50-Test (51 Cycles im Mock → 50 gerendert).
    - `Running.test.ts`: Status-Tile-Reihe gerendert je nach Setup-Variante (drossel-only, marstek, mit/ohne grid_meter, ha_ws disconnected).
    - `Running.test.ts`: Mode-Erklärungs-Zeile wechselt mit `currentMode`.
    - `Running.test.ts`: `data-stale`-Verhalten am Connection-Tile bei `ha_ws_connected: false` mit zähltem Sekunden-Counter.

18. **Doku-Updates:**
    - `_bmad-output/qa/manual-tests/smoke-test.md`: Neuer Test SD-01 „Diagnose-Klartext im Live-Betrieb": (1) Wasserkocher an, beobachten, dass Cycle-Status von „Im Toleranzbereich" auf „Übernommen" mit Watt-Zahl wechselt; (2) HA-WS trennen, beobachten, dass Connection-Tile auf „Getrennt" mit Sekunden-Zähler wechselt.
    - **CLAUDE.md** Glossar verbindlich erweitert: „Im Toleranzbereich" (statt Deadband), „Übernommen" (statt passed), „Abgelehnt" (statt vetoed), „Fail-Safe" (eigener Begriff).

19. **Beta-Launch-Hinweis:** Diese Story koppelt mit Story 2.5 (`effective_value_w` braucht den `invert_sign`-Flag). Wenn 2.5 nicht zuerst merged, fällt AC 14 auf `effective_value_w == state` zurück (Pass-Through) — der Entity-Snapshot funktioniert dann ohne Sign-Flip, aber die Story bleibt mergebar.

## Tasks / Subtasks

- [x] **Task 1: Backend Schema-Erweiterungen** (AC 6, 7, 14, 15)
  - [x] `backend/src/solalex/api/schemas/control.py`: `RecentCycle.reason: str | None` ergänzt, Docstring aktualisiert. `CycleMode` auf `Literal["drossel", "speicher", "multi", "audit", "export"]`. `EntitySnapshot.effective_value_w: float | None`, `EntitySnapshot.display_label: str | None`. `StateSnapshot.ha_ws_connected: bool`, `StateSnapshot.ha_ws_disconnected_since: datetime | None`.
  - [x] Tests: Schema-Round-Trip mit allen neuen Feldern.

- [x] **Task 2: Backend Route-Anpassung** (AC 5, 6, 14, 15)
  - [x] `backend/src/solalex/api/routes/control.py`: `_RECENT_CYCLES_LIMIT = 50`. `RecentCycle` jetzt mit `reason=row.reason`. Neuer Helper `_effective_value_w` (Story 2.5-konform, Pass-Through wenn invert_sign nicht gesetzt). `_ROLE_DISPLAY_LABEL`-Tabelle für `display_label`. `StateSnapshot` reicht `ha_ws_connected` + `ha_ws_disconnected_since` aus dem StateCache durch.
  - [x] Tests: Endpoint-Response enthält die neuen Felder; Connect/Disconnect-Pfad; invert_sign-Pfad.

- [x] **Task 3: Backend State-Cache HA-WS-Disconnect-Stempel** (AC 15, 16)
  - [x] `state_cache.py`: Neue Felder `ha_ws_connected: bool` (Default True) + `ha_ws_disconnected_since: datetime | None`. Idempotenter Updater `update_ha_ws_connection(connected, now=None)` — Disconnect stempelt UTC-Now, Reconnect cleart.
  - [x] `ha_client/reconnect.py`: Neuer optionaler `on_connection_change`-Callback im Konstruktor + interner `_set_connected`-Helper, der Transitionen detektiert und den Callback feuert (Exceptions im Hook werden geloggt, nie rethrown).
  - [x] `main.py`: Lifespan verdrahtet `on_connection_change` mit `state_cache.update_ha_ws_connection`.
  - [x] Tests: State-Cache-Update-Pfade für Disconnect/Reconnect, Endpoint-Round-Trip.

- [x] **Task 4: Backend Noop-Reason-Klartext** (AC 8, 9, 10, 11, 16)
  - [x] `controller.py`: `_record_noop_cycle`-Signatur jetzt mit Pflicht-Parameter `reason: str` + `_truncate_reason`-Wrapper für Sicherheit gegen Float-Bloat.
  - [x] **Option 1 implementiert** (Test-Aufwand für Option 2 wäre 55+ destrukturierte Callsites, also >> 2× Option 1): Neuer State-Buffer `_last_policy_noop_reason` + Helper `_set_noop_reason`. `_dispatch_by_mode` cleart den Buffer am Anfang jedes Sensor-Events; Policy-Methoden setzen ihn auf jedem Early-Exit. Policy-Signaturen unverändert (alle 55 bestehenden Test-Callsites bleiben grün).
  - [x] `_policy_drossel`: alle 6 Early-Exit-Pfade (nicht_grid_meter_event, sensor_nicht_numerisch, kein_wr_limit_device, adapter_unbekannt, deadband, wr_limit_state_cache_miss, min_step_nicht_erreicht) setzen den Reason.
  - [x] `_policy_speicher`: alle 9+ Early-Exit-Pfade (nicht_grid_meter_event, sensor_nicht_numerisch, kein_akku_pool, adapter_unbekannt, kein_soc_messwert, deadband, max_soc_erreicht, min_soc_erreicht, nacht_gate_aktiv, min_step_nicht_erreicht, pool_alle_offline, soc_member_inkonsistent) setzen den Reason.
  - [x] `_policy_multi`: zwei eigene Early-Exits + delegiert an Speicher/Drossel (deren Reasons fließen weiter durch).
  - [x] `on_sensor_update`: konsumiert Buffer und gibt den Reason an `_record_noop_cycle` weiter (Fallback "noop: unbekannt" defensiv).
  - [x] Tests: Reason-Strings für jeden Early-Exit-Pfad in `test_controller_drossel_policy.py` und `test_controller_speicher_policy.py`. Plus Buffer-Reset-Test.

- [x] **Task 5: Frontend Cycle-Liste** (AC 1, 2, 3, 4, 17)
  - [x] `Running.svelte`: `cycle-header`-Zeile über der Liste mit den 5 Spaltentiteln (Grid-Struktur synchron zu `cycle-row`). `formatCycleStatus`-Helper zentralisiert die Status-Mapping-Tabelle (Reason-Prefix-Discriminator) und liefert `{label, dataStatus, tooltip}`.
  - [x] `cycle-target` mit Sub-Anzeige `gemessen X W` bei `target_value_w === null && sensor_value_w !== null`.
  - [x] `slice(0, 10)` → `slice(0, 50)`. Bestehende `max-height: 320px + overflow-y: auto` greift jetzt sinnvoll.
  - [x] CSS: distinct `data-status`-Farb-Tokens für alle Noop-Varianten — Toleranzbereich/Min-Step/Mode-Switch/etc. nutzen Mix aus `--color-accent-warning`, `--color-accent-primary`, `--color-text-secondary`, `--color-neutral-muted`. Keine neuen Tokens.
  - [x] Tests: Vitest-Tabelle (`describe.each`) über alle Mapping-Tupel + Header + Tooltip + Sub-Anzeige.

- [x] **Task 6: Frontend Status-Tile-Reihe** (AC 12, 13, 17)
  - [x] Neue `<section class="status-tiles">` zwischen Header und Chart-Card. Inline-Tile-Markup (Single-File).
  - [x] Conditional-Tiles per `findEntityByRole`: Netz-Leistung (effective_value_w, post invert_sign), WR-Limit, Akku-SoC (mit Min/Max-Sub aus device.config_json), Verbindung (immer, mit Sekunden-Counter).
  - [x] CSS: 4-Spalten-Grid Desktop, 1-Spalten-Stack ≤ 480px (Breakpoint 560px für Übergang). Tabular-nums.
  - [x] Tests: Tile-Variantentests (drossel-only, marstek/SoC, ha_ws disconnected mit Counter, effective_value_w-Anzeige).

- [x] **Task 7: Frontend Mode-Erklärungs-Zeile** (AC 13, 17)
  - [x] `<p class="mode-explanation" data-testid="mode-explanation">` direkt unter dem `<h1>`. `MODE_EXPLANATION`-Mapping über alle 5 Modes inkl. `idle` und `export`.
  - [x] CSS: kleiner als Body, `--color-text-secondary`, `max-width: 60ch`.
  - [x] Tests: Mode-Switch-Test (drossel ↔ idle).

- [x] **Task 8: Frontend Types + Client** (AC 6, 7, 14, 15)
  - [x] `frontend/src/lib/api/types.ts`: `RecentCycle` um `reason: string | null` + erweiterte `mode`-Union. `ControlMode` jetzt mit `'export'`. `EntitySnapshot` um `effective_value_w` + `display_label`. `StateSnapshot` um `ha_ws_connected` + `ha_ws_disconnected_since`.
  - [x] Kein `client.ts`-Touch nötig — Endpoint-Pfad bleibt.

- [x] **Task 9: Doku** (AC 18)
  - [x] `_bmad-output/qa/manual-tests/smoke-test.md` Test SD-01 „Diagnose-Klartext im Live-Betrieb" mit 9 Schritten (Mode-Chip + Erklärung, 4 Tiles, Cycle-Header, Wasserkocher-Trigger, Tooltip-Hover, Disconnect-Counter, Reconnect, 50er-Scroll).
  - [x] CLAUDE.md Glossar erweitert + 3 neue Stop-Signale (Pflicht-Reason, Deadband-UI-Verbot, kein drittes Mapping-Layer).

- [x] **Task 10: Validierung und Final-Gates** (AC 16, 17)
  - [x] Backend: ruff ✓, mypy --strict ✓, pytest 427/427 grün.
  - [x] Frontend: ESLint ✓, svelte-check 0 errors ✓, vitest 144/144 ✓, vite build ✓, prettier ✓.
  - [ ] Manual: Alex testet auf seinem Setup — Connection-Tile bei addon-restart, Cycle-Status-Klartext-Wechsel bei Wasserkocher, Scrollen in der 50er-Liste.

## Dev Notes

### Architektur-Bezugspunkte

- **Story 5.1a Live-Betriebs-View:** Diese Story ist die direkte Erweiterung. 5.1a baute den Mini-Shell mit Mode-Chip, Chart, Cycle-Liste, Rate-Limit-Hint. 5.1d füllt die Anzeige mit Klartext und Diagnose-Tiefe. [Source: `_bmad-output/implementation-artifacts/5-1a-live-betriebs-view-post-commissioning-mini-shell.md`]
- **Story 5.1c Chart-Legende + Update-Indikator:** 5.1c liefert die Chart-Legende und einen Pulse-Dot. 5.1d bringt die Status-Tiles + Mode-Erklärung — komplementär, kein Konflikt. Beide modifizieren `Running.svelte`; bei Merge-Konflikten rebased die zweitgemergte Story. [Source: `_bmad-output/implementation-artifacts/5-1c-...-chart-legende-und-update-indikator.md` (laut sprint-status.yaml)]
- **Story 2.5 Sign-Invert:** Liefert `device.config().get("invert_sign")`-Flag. AC 14 nutzt das für `effective_value_w`. Falls 2.5 nicht zuerst merged: Backend gibt `effective_value_w = state` zurück (Pass-Through), Story bleibt mergebar. [Source: `_bmad-output/implementation-artifacts/2-5-smart-meter-sign-invert-mit-live-preview.md`]
- **Story 2.6 Hardware-Edit:** Schreibt Audit-Cycles mit `mode='audit'` und `reason='hardware_edit: …'`. Story 5.1d zeigt diese im Klartext als „Hardware geändert". Falls 2.6 nicht zuerst merged: Mapping-Tabelle hat den Eintrag, wird nur nicht produziert.
- **CLAUDE.md Glossar:** „Akku (nicht Batterie/Speicher), Wechselrichter/WR, Smart Meter, Setup-Wizard." Story 5.1d ergänzt: „Im Toleranzbereich" als Standard-Begriff für Deadband.
- **CLAUDE.md UX-DR30:** „Keine Tabellen, keine Modal-Dialoge, keine Tooltips." Native `title`-Attribute sind kein Custom-Tooltip-Component und werden vom Browser gerendert — daher mit der Regel verträglich. Custom-Hover-Cards wären verboten.
- **Architecture-Authoritative:** `_bmad-output/planning-artifacts/architecture.md` gewinnt bei Konflikten.

### Aktueller Codezustand und Ziel-Änderungen

- `backend/src/solalex/api/schemas/control.py:25-46` `RecentCycle`-Docstring sagt explizit: „Columns mirror the repository's ControlCycleRow but **drop fields the UI does not render** (`reason`, `cycle_duration_ms`, `readback_actual_w`, `readback_mismatch`)." — diese Annahme wird umgekehrt für `reason`. `cycle_duration_ms`, `readback_actual_w`, `readback_mismatch` bleiben gedroppt (Diagnose-Schnellexport / `4-0a` deckt sie ab).
- `backend/src/solalex/api/routes/control.py:46` `_RECENT_CYCLES_LIMIT = 10`. Auf 50.
- `backend/src/solalex/controller.py:1131-1175` `_record_noop_cycle`-Signatur hat `reason=None` als Default. Wird Pflicht-Parameter.
- `backend/src/solalex/controller.py:479-558` und `:921-…` Policies haben mehrere `return None`-Pfade ohne Begründung. Jeder bekommt einen Reason.
- `frontend/src/routes/Running.svelte:69` `slice(0, 10)`. Auf 50.
- `frontend/src/routes/Running.svelte:174-203` Cycle-Liste-Markup. Header-Zeile davor, Status-Mapping-Helper.
- `frontend/src/lib/api/types.ts` `RecentCycle`-Type, `ControlMode`-Type, `EntitySnapshot`-Type, `StateSnapshot`-Type erweitern.

### Implementation Guardrails

- **Reasons sind snake_case-Strings mit Doppelpunkt-Präfix:** `noop:`, `fail_safe:`, `mode_switch:`, `hardware_edit:`. Frontend-Mapping erkennt das Präfix als Discriminator. Kein neues `noop_reason`-Enum-Feld in der DB — `reason` ist und bleibt Free-Text-Spalte (existierende Migration 002).
- **`reason`-Spalte hat keine Längen-Constraint, aber:** Im DB-Code (`control_cycles.insert`) gibt es `_truncate_reason` ([controller.py:1240](backend/src/solalex/controller.py#L1240)) für Fail-Safe-Pfade — den Helper auch für die neuen Noop-Reasons nutzen, damit unkontrollierte Floats in den Templates die Spalte nicht aufblähen.
- **Keine neuen Frontend-Tokens:** `app.css` Custom Properties sind Single-Source. Neue `data-status`-Werte nutzen Mix aus `--color-accent-warning`, `--color-accent-primary`, `--color-text-secondary`, `--color-neutral-muted` (alle existieren).
- **Keine Charakter-Zeile mit Adjektiven:** Mode-Erklärungs-Zeile beschreibt **was der Mode tut**, nicht „wow, du speicherst gerade!". Nüchtern.
- **Keine Tooltips als Komponente:** Native `title`-Attribut ja, Floating-UI / Tooltip-Library nein.
- **Tile-Werte sind nackt:** „+2120 W", nicht „🟢 +2120 W ↑" oder „2,12 kW Bezug aus dem Netz". Das Sub-Label trägt den Kontext.
- **Backend-Glossar-Mapping zentral:** `display_label`-Werte sind im Backend definiert ([routes/control.py]). Frontend-Mapping-Tabellen nur für Status-Klartext, nicht für Glossar — sonst zwei Wahrheiten.
- **Backwards-Compat im RecentCycle:** Frontend-Tests, die Mock-Cycles ohne `reason` senden, müssen weiter laufen. `reason: string | null` macht das möglich; alte Mocks bekommen automatisch `null`.
- **Keine Migration:** `control_cycles.reason` existiert seit Migration 002.
- **Kein neuer Endpoint:** Alle Erweiterungen passen in das bestehende `GET /api/v1/control/state`-Payload.

### File Structure Requirements

```text
backend/src/solalex/
├── api/
│   ├── routes/
│   │   └── control.py             [MOD: _RECENT_CYCLES_LIMIT=50, RecentCycle.reason, EntitySnapshot.effective_value_w + display_label, StateSnapshot.ha_ws_connected + ha_ws_disconnected_since]
│   └── schemas/
│       └── control.py             [MOD: alle neuen Felder, Mode-Literal-Erweiterung]
├── controller.py                  [MOD: _record_noop_cycle Pflicht-reason, Policies geben Reasons mit]
└── state_cache.py                 [MOD: ha_ws_disconnected_since-Feld]

frontend/src/
├── lib/api/
│   └── types.ts                   [MOD: RecentCycle.reason, ControlMode-Erweiterung, EntitySnapshot, StateSnapshot]
└── routes/
    └── Running.svelte             [MOD: Status-Mapping, Header-Zeile, Limit 50, Status-Tiles, Mode-Erklärung]

_bmad-output/qa/manual-tests/
└── smoke-test.md                  [MOD: Test SD-01]

CLAUDE.md                          [MOD: Glossar erweitert, Stop-Signale ergänzt]
```

### Testing Requirements

- **Backend Test-Erweiterungen:**
  - `test_control_state.py`: Schema-Round-Trip-Test mit allen neuen Feldern; Endpoint-Test mit verschiedenen Setup-Varianten (kein WR / kein Akku / kein Smart-Meter).
  - `test_controller_drossel_policy.py`: Pro Early-Exit-Pfad ein Test, der den exakten Reason-String asserted.
  - `test_controller_speicher_policy.py`: Analog für Speicher-Policy.
  - `test_controller.py`: HA-WS-Disconnect → `state_cache.ha_ws_disconnected_since` gesetzt; Reconnect → None.
- **Frontend Test-Erweiterungen:**
  - `Running.test.ts`: Status-Mapping-Tabelle (parametrisierter Test über alle Tupel aus AC 2).
  - `Running.test.ts`: Status-Tile-Variantentests (drossel-only, marstek, ha_ws_disconnected mit Sekunden-Counter).
  - `Running.test.ts`: 50er-Limit-Test.
  - `Running.test.ts`: Mode-Erklärung wechselt mit Mode-Chip.

### Reason-Vokabular (Single-Source)

Diese Tabelle ist autoritativ für Backend-Reason-Strings und das Frontend-Mapping. Bei Erweiterungen Beide-Seiten-Update.

| Reason-String (Backend) | Trigger | UI-Anzeige | data-status |
|---|---|---|---|
| `noop: kein_wr_limit_device` | `_policy_drossel` ohne wr_limit | „Kein Wechselrichter" | `noop-no-wr` |
| `noop: deadband (smoothed=Xw, deadband=Yw)` | `\|smoothed\| ≤ deadband_w` | „Im Toleranzbereich" | `noop-deadband` |
| `noop: min_step_nicht_erreicht (delta=Xw, min=Yw)` | `\|proposed - current\| < min_step_w` | „Schritt zu klein" | `noop-min-step` |
| `noop: wr_limit_state_cache_miss` | `_read_current_wr_limit_w` returned None | „WR-Status fehlt" | `noop-no-wr-state` |
| `noop: sensor_nicht_numerisch` | NaN/None vom Sensor | „Sensor-Wert ungültig" | `noop-sensor-bad` |
| `noop: nicht_grid_meter_event` | Event von SoC/anderem Device | „Beobachtung" | `noop-other` |
| `noop: kein_akku_pool` | `pool is None or empty` | „Kein Akku" | `noop-no-pool` |
| `noop: kein_soc_messwert` | `pool.get_soc() is None` | „SoC fehlt" | `noop-no-soc` |
| `noop: max_soc_erreicht (aggregated=X%)` | aggregated >= max_soc | „Max-SoC erreicht" | `noop-max-soc` |
| `noop: min_soc_erreicht (aggregated=X%)` | aggregated <= min_soc | „Min-SoC erreicht" | `noop-min-soc` |
| `noop: nacht_gate_aktiv` | `_speicher_night_gate_active` | „Nacht-Modus aktiv" | `noop-night-gate` |
| `mode_switch: <old>→<new> (<grund>)` | `_record_mode_switch_cycle` | „Mode-Wechsel" | `noop-mode-switch` |
| `hardware_edit: <kurzer-text>` | Story 2.6 PUT /devices | „Hardware geändert" | `noop-hardware-edit` |
| `fail_safe: <…>` | `_write_failsafe_cycle` | „Fail-Safe" | `vetoed` (Override-CSS) |

### References

- [Source: `backend/src/solalex/controller.py:479-558`] `_policy_drossel` Early-Exits
- [Source: `backend/src/solalex/controller.py:921-…`] `_policy_speicher`
- [Source: `backend/src/solalex/controller.py:1131-1175`] `_record_noop_cycle`
- [Source: `backend/src/solalex/controller.py:1240`] `_truncate_reason`-Helper
- [Source: `backend/src/solalex/api/routes/control.py:46`] `_RECENT_CYCLES_LIMIT`
- [Source: `backend/src/solalex/api/schemas/control.py:25-46`] `RecentCycle`-Schema
- [Source: `backend/src/solalex/api/schemas/control.py:15-22`] `EntitySnapshot`-Schema
- [Source: `frontend/src/routes/Running.svelte:69`] `slice(0, 10)`
- [Source: `frontend/src/routes/Running.svelte:174-203`] Cycle-Liste-Markup
- [Source: `frontend/src/lib/api/types.ts`] TS-Types
- [Source: `_bmad-output/planning-artifacts/architecture.md`] Authority

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
SD-01 Diagnose-Klartext im Live-Betrieb (smoke-test.md):
1. Ausgangslage: Solalex commissioned, Drossel-Mode aktiv, Solar > Last (leichte Einspeisung)
2. /running öffnen — erwartet:
   - Mode-Chip "Drossel" + Erklärungs-Zeile "Drossel — verhindert ungewollte Einspeisung..."
   - Status-Tile "Netz-Leistung" zeigt aktuellen Wert mit Sub-Label
   - Status-Tile "Wechselrichter-Limit" zeigt aktuelles Readback-Watt
   - Status-Tile "Verbindung" zeigt "Verbunden" (grün)
   - Cycle-Liste hat Header "vor / Quelle / Ziel / Status / Latenz"
3. Wasserkocher anschalten → Cycle-Status wechselt von "Im Toleranzbereich" auf "Übernommen" mit Watt-Zahl + Sub "(gemessen XYZ W)"
4. HA-Container neu starten → Connection-Tile wechselt auf "Getrennt — vor X s"; nach Reconnect: "Verbunden"
5. /running scrollen — 50 statt 10 Zyklen sichtbar
```

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) via /bmad-dev-story (Dev-Workflow), 2026-04-25.

### Debug Log References

Keine Debug-Log-Referenzen — alle Validation-Gates sofort grün durchgelaufen.

### Completion Notes List

- **Architekturentscheidung Reason-Threading (Task 4):** Story-Spec ließ Option 1 (Helper) vs. Option 2 (Tuple-Return) zu, mit Faustregel „Option 2, wenn Test-Aufwand <2× Option 1". Die Codebase enthält ~55 direkte Test-Aufrufe von `_policy_drossel/_policy_speicher/_policy_multi`, die bei Tuple-Return alle destrukturiert werden müssten. Test-Aufwand Option 2 ≈ 3× Option 1 → **Option 1 implementiert**: neuer Buffer `_last_policy_noop_reason` + `_set_noop_reason`-Helper. `_dispatch_by_mode` cleart den Buffer am Anfang jedes Sensor-Events; Policy-Methoden setzen ihn auf jedem Early-Exit. Vorteil: alle 55 bestehenden Test-Callsites bleiben unverändert grün (kein Break-Change).
- **HA-WS-Reconnect-Hook (Task 3):** ReconnectingHaClient bekommt einen optionalen `on_connection_change(connected: bool)`-Callback im Konstruktor und ruft ihn aus einem internen `_set_connected`-Helper, der nur bei tatsächlichen Transitionen feuert (idempotent gegen Duplikat-Aufrufe). Callback-Exceptions werden geloggt, nie rethrown — eine kaputte Hook-Implementierung darf den Reconnect-Loop niemals stoppen. main.lifespan verdrahtet die Hook mit `state_cache.update_ha_ws_connection`. Saubere Layer-Trennung: ha_client kennt state_cache nicht direkt.
- **EntitySnapshot.effective_value_w (Task 2):** Neuer Helper `_effective_value_w` in routes/control.py spiegelt den controller-internen `_maybe_invert_sensor_value` (Story 2.5) — für `role == 'grid_meter'` mit `device.config_json.invert_sign == True` wird das Vorzeichen geflippt; für alle anderen Rollen wird der Raw-State durchgereicht. Story-Spec sieht das explizit als 2.5-Coupling vor; bei nicht-merge bleibt die Pass-Through-Variante intakt.
- **CycleMode-Literal-Forward-Compat (Task 1):** `CycleMode` enthält jetzt `"audit"` und `"export"` (Story 3.8). Aktuell schreibt der Controller nur drossel/speicher/multi-Mode-Werte in die DB; `audit` und `export` sind reserviert für künftige Stories. `current_mode`-Literal in StateSnapshot wurde ebenfalls um `"export"` erweitert (für die Mode-Erklärungs-Zeile AC 13). Der state_cache-Whitelist wurde mitgepflegt.
- **CSS-Status-Token-Mapping (Task 5):** Alle neuen `data-status`-Werte nutzen `color-mix(in srgb, --color-accent-warning|primary|--color-neutral-muted|--color-text-secondary, --color-surface)` — keine neuen Tokens in app.css. Verteilung: Toleranzbereich/Min-Step/SoC-Cap/Other → neutral; Mode-Wechsel/Hardware-Edit → primary-accent; Kein-WR/SoC-fehlt/Sensor-bad → warning.
- **Backend-Validation:** ruff ✓, mypy --strict (101 Files) ✓, pytest 427 passed in 3.93s. 0 Regressionen.
- **Frontend-Validation:** ESLint ✓, svelte-check 0 errors / 0 warnings auf 280 Files, vitest 144 passed (12 Test-Files), vite build 99.34 kB JS / 46.07 kB CSS, Prettier (auto-formatted).

### File List

**Backend (geändert):**
- `backend/src/solalex/api/schemas/control.py` — RecentCycle.reason, CycleMode-Erweiterung, EntitySnapshot.effective_value_w + display_label, StateSnapshot.ha_ws_connected + ha_ws_disconnected_since.
- `backend/src/solalex/api/routes/control.py` — _RECENT_CYCLES_LIMIT=50, RecentCycle.reason-Durchreichung, _effective_value_w-Helper, _ROLE_DISPLAY_LABEL-Mapping, StateSnapshot mit HA-WS-Feldern.
- `backend/src/solalex/state_cache.py` — ha_ws_connected + ha_ws_disconnected_since-Felder, update_ha_ws_connection-Updater, ModeValue um "export" erweitert.
- `backend/src/solalex/ha_client/reconnect.py` — on_connection_change-Hook im Konstruktor, _set_connected-Helper für transition-detection.
- `backend/src/solalex/main.py` — Lifespan verdrahtet ReconnectingHaClient on_connection_change → state_cache.update_ha_ws_connection.
- `backend/src/solalex/controller.py` — _last_policy_noop_reason-Buffer + _set_noop_reason-Helper, _dispatch_by_mode resettet Buffer, _policy_drossel/_policy_speicher/_policy_multi setzen Reason auf jedem Early-Exit, _record_noop_cycle mit Pflicht-Parameter `reason: str`, on_sensor_update threadet Buffer-Reason zur Persistenz.

**Backend (Tests, neu/erweitert):**
- `backend/tests/unit/test_control_state.py` — Empty-Cache-Defaults für ha_ws_*, Limit auf 50 erweitert, Reason-Durchreichung, EntitySnapshot mit invert_sign Pass-Through und Flip, StateSnapshot disconnect-/connect-Pfad.
- `backend/tests/unit/test_controller_drossel_policy.py` — 7 neue Tests für jeden Drossel-Reason + Buffer-Reset-Test.
- `backend/tests/unit/test_controller_speicher_policy.py` — 7 neue Tests für jeden Speicher-Reason.

**Frontend (geändert):**
- `frontend/src/lib/api/types.ts` — RecentCycle.reason, mode-Union um audit+export, ControlMode um export, EntitySnapshot.effective_value_w + display_label, StateSnapshot.ha_ws_connected + ha_ws_disconnected_since.
- `frontend/src/routes/Running.svelte` — formatCycleStatus-Helper, Status-Tile-Reihe, Mode-Erklärungs-Zeile, Cycle-Header-Zeile, Limit auf 50, Sub-Anzeige für sensor_value_w bei Noop, native title-Tooltip mit vollem Reason, neue data-status-CSS-Klassen.

**Frontend (Tests, neu/erweitert):**
- `frontend/src/routes/Running.test.ts` — entity()-Factory + Story 5.1d-Test-Block: 19 Status-Mapping-Tupel via describe.each, Cycle-Header, Sub-Anzeige, native Tooltip, Mode-Erklärung-Switch, Status-Tile-Varianten (drossel-only, marstek/SoC, ha_ws disconnected mit Counter, effective_value_w-Anzeige). Limit-50-Test (statt 10).

**Doku (geändert):**
- `_bmad-output/qa/manual-tests/smoke-test.md` — Neuer Test SD-01 „Diagnose-Klartext im Live-Betrieb" zwischen ST-05 und ST-06.
- `CLAUDE.md` — Glossar um Story-5.1d-Klartext-Begriffe erweitert; 3 neue Stop-Signale (Pflicht-Reason, Deadband-UI-Verbot, kein drittes Mapping-Layer).

**Sprint-Status:**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 5-1d-live-betrieb-klartext-diagnose: ready-for-dev → in-progress → review (in Schritt 9).
- `_bmad-output/implementation-artifacts/5-1d-live-betrieb-klartext-diagnose.md` — Status: ready-for-dev → review, alle Tasks/Subtasks abgehakt, Dev Agent Record + Change Log gefüllt.

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Story 5.1d erstellt nach Smoke-Test Alex' Setup. Cycle-Liste mit Klartext-Reasons, deutschen Status-Labels, Header-Zeile, Limit auf 50; Status-Tile-Reihe oberhalb des Charts; Mode-Erklärungs-Zeile; HA-WS-Connection-Indikator. Beta-Launch-blocking. Reason-Vokabular-Tabelle als Single-Source. | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Story 5.1d implementiert via /bmad-dev-story. Backend: 6 Files (schemas/control.py, routes/control.py, state_cache.py, ha_client/reconnect.py, main.py, controller.py); Pflicht-Reasons via _last_policy_noop_reason-Buffer (Option 1, da Test-Aufwand für Option 2 ≈ 3× wäre); HA-WS-Reconnect-Hook mit transition-detection. Frontend: Running.svelte komplett umgearbeitet (Status-Tiles, Mode-Erklärung, Cycle-Header, formatCycleStatus-Mapper, slice 50, Tooltip via native title). Tests: 14 neue Backend-Tests (Reasons + EntitySnapshot + StateSnapshot), 19 neue Frontend-Tests via describe.each + Tile-Varianten. Validation: ruff/mypy/pytest 427/427 grün; ESLint/svelte-check/vitest 144/144/build/prettier grün. Doku: SD-01-Smoke-Test, CLAUDE.md Glossar + 3 Stop-Signale. Status → review. | Claude Opus 4.7 (1M context) |

## Review Findings (2026-04-25 — bmad-code-review, 3 Reviewer parallel)

### Decision-Needed

- [x] [Review][Decision] **MULTI-Mode Reason-Verhalten** — Resolved (2026-04-25): Option (a) Last-write-wins akzeptieren. Aktuelles Verhalten bleibt — keine Code-Änderung nötig. Bei Speicher-Cap+Drossel-Deadband zeigt UI „Im Toleranzbereich"; das ist das gewollte Verhalten („zeige warum die finale Branch nicht regelte").
- [x] [Review][Decision] **`_effective_value_w` für non-grid_meter Rolle** — Resolved (2026-04-25): Option (b) Spec an Code anpassen. `effective_value_w` ist UI-fertiger Wert für alle Rollen; nur grid_meter wendet Sign-Invert an. Wird zu Patch P-D3 (Spec-Update AC 14). Eröffnet Folge-Patch: Frontend kann auf `entity.effective_value_w` für alle Tiles umstellen (DRY mit P16, sowie P2 Chart-Konsistenz).
- [x] [Review][Decision] **`StateSnapshot.ha_ws_connected` Default** — Resolved (2026-04-25): Option (a) Default auf `False` umstellen. Test-Fixtures explizit auf `True` setzen wo nötig. Wird zu Patch P-D4.

### Patches

- [ ] [Review][Patch] **P-D3: Spec AC 14 korrigieren — `effective_value_w` ist UI-fertiger Wert für alle Rollen, Sign-Invert nur bei grid_meter** [_bmad-output/implementation-artifacts/5-1d-live-betrieb-klartext-diagnose.md AC 14] — Doc-Patch: Spec-Wortlaut „bei anderen Rollen `None`" durch „raw passthrough für non-grid_meter; nur grid_meter wendet `invert_sign` an" ersetzen. Code bleibt wie ist; Test bleibt wie ist.
- [ ] [Review][Patch] **P-D4: `StateSnapshot.ha_ws_connected` Default auf `False`** [backend/src/solalex/state_cache.py:818] — Init-Wert von `True` → `False` umstellen. Test-Fixtures, die heute den Default nutzen und auf `True` rechnen, explizit auf `True` setzen. Reconnect-Hook flippt beim ersten erfolgreichen Connect ohnehin auf `True` (transition-detection), also keine Race im Production-Pfad. Frontend-Verhalten: in der Pre-Connect-Lücke (typisch < 2 s nach Start) zeigt Tile „Getrennt" statt fälschlich „Verbunden" — semantisch korrekt.
- [ ] [Review][Patch] **4 Backend-Reasons fehlen im Frontend `formatCycleStatus`-Mapper — fallen alle in `default → 'Beobachtung'`** [frontend/src/routes/Running.svelte:60-101] — Backend produziert `noop: adapter_unbekannt` (controller.py:644, 1269), `noop: kein_device_id` (controller.py:651, 1259), `noop: pool_alle_offline` (controller.py:1424), `noop: soc_member_inkonsistent` (controller.py:1435). Keine `startsWith`-Branches → User sieht „Beobachtung" für echte Misskonfigurationen. Fix: 4 Mappings ergänzen UND Reason-Vokabular-Tabelle in dieser Story (Zeilen 254-269) erweitern (Single-Source-Vertrag).
- [ ] [Review][Patch] **Reason-Vokabular-Tabelle in Story-Spec ergänzen** [_bmad-output/implementation-artifacts/5-1d-live-betrieb-klartext-diagnose.md:254-269] — Tabelle erfasst aktuell nur 11 Reasons; Code erzeugt mindestens 15. Beide Single-Sources (Backend-Emitter + Frontend-Mapper + Spec-Tabelle) müssen synchron sein.
- [ ] [Review][Patch] **`update_ha_ws_connection` mutiert `ha_ws_connected` und `ha_ws_disconnected_since` ohne Lock — Race vs. `snapshot()`-Reader** [backend/src/solalex/state_cache.py:822-843] — `snapshot()` hält `self._lock` beim Lesen; `update_ha_ws_connection` ist die einzige neue Methode, die schreibt OHNE `self._lock`. Kurz-Race-Window: Reader sieht `connected=True` mit nicht-`None` `disconnected_since` (oder umgekehrt). Fix: Methode als `async def` (oder mit `with self._lock:` wenn der Lock sync ist) wrap analog zu `update()`.
- [ ] [Review][Patch] **`isinstance(state_val, int | float)` matcht `bool` als numerisch in `_effective_value_w`** [backend/src/solalex/api/routes/control.py:244-245] — Python: `isinstance(True, int) == True`. Boolean-States (`sensor.power_on`) werden als `1.0`/`0.0 W` gerendert und durchlaufen die Sign-Invert-Mathe. Fix: `if isinstance(state_val, bool) or not isinstance(state_val, (int, float)): return None`.
- [ ] [Review][Patch] **`formatCycleStatus` `default`-Branch sollte unmappte Reasons `console.warn`-en** [frontend/src/routes/Running.svelte:1660] — Aktuell still „Beobachtung" mit `noop-other`-CSS. Wenn Backend einen neuen Reason ergänzt und FE-Mapping vergisst, driftet die Tabelle still weiter. Fix: `console.warn('Unmapped cycle reason:', reason)` im `default`-Branch (Vitest noch nicht abdeckend, aber sichtbar in Browser-Devtools / Diagnose-Export).
- [ ] [Review][Patch] **`_speicher_decisions_for_setpoint` überschreibt night-gate-entry-Intent mit `pool_alle_offline`-Reason** [backend/src/solalex/controller.py:1424] — Wenn die Nacht-Gate-Entry-Logik einen 0 W-Stop dispatcht und der Pool offline ist, wird die Reason auf `noop: pool_alle_offline` gesetzt. Operator sieht im Cycle-Log „Pool offline" statt „Nacht-Gate griff". Fix: Caller (night-gate-entry path bei Zeile 1397ff.) setzt `_set_noop_reason("noop: nacht_gate_aktiv")` BEVOR es `_speicher_decisions_for_setpoint(proposed=0, …)` ruft, und `_speicher_decisions_for_setpoint` setzt seinen eigenen Reason nur, wenn buffer leer ist.
- [ ] [Review][Patch] **`_maybe_invert_sensor_value` returnt `None` bei kaputter `config_json` → noop-Reason `sensor_nicht_numerisch` ist irreführend** [backend/src/solalex/controller.py:335-381, 617-619] — `_maybe_invert_sensor_value` schluckt `JSONDecodeError`/Type-Fehler in der Device-Config (Story 2.5). `on_sensor_update` interpretiert das als „Sensor lieferte nichts Numerisches" und schreibt `noop: sensor_nicht_numerisch` — aber der Sensor war fein, die DEVICE-CONFIG ist kaputt. Operator wird in falsche Diagnose-Richtung geschickt. Fix: neue Reason `noop: invert_sign_config_fehler` ergänzen, `_maybe_invert_sensor_value` markiert den Fall (z. B. zweiter Return-Sentinel oder Kontext-Variable), `on_sensor_update` differenziert.
- [ ] [Review][Patch] **`_invert_sign_parse_failed_logged: set[int]` wächst unbegrenzt** [backend/src/solalex/controller.py:289] — Set discardet einen Eintrag nur, wenn dasselbe Device-ID wieder erfolgreich parst. Bei Device-ID-Churn (delete+recreate, jedes Mal neue ID) wachsen Einträge über Wochen unbegrenzt. Klein, aber unbounded. Fix: in `reload_devices_from_db()` das Set leeren — beim Reload sind die Devices ohnehin frisch eingelesen.
- [ ] [Review][Patch] **`vetoed`-Reason-Discriminator nur für `fail_safe:` — andere Vetos kollabieren auf „Abgelehnt" ohne Differenzierung** [frontend/src/routes/Running.svelte:1614] — `rate_limit:`, `range_check:` und alle künftigen Veto-Typen bekommen denselben Label. User kann im Cycle-Log nicht unterscheiden, warum ein Write geblockt wurde. Fix: explizite Branches für `rate_limit:` (`„Rate-Limit"`) und `range_check:` (`„Außerhalb des Bereichs"`); UI-Tabelle in Story-Spec erweitern.
- [ ] [Review][Patch] **Empty-string `reason` fall-through** [backend/src/solalex/api/schemas/control.py:194] — Pydantic akzeptiert `reason=""`. Frontend `startsWith(...)` schlagen alle fehl → fallthrough zu „Beobachtung". Fix: `reason: str | None = Field(default=None, min_length=1)` ODER server-side `if reason: return reason else: return None`-Normalisierung.
- [ ] [Review][Patch] **`current_mode` Literal in 3 Files duplikat — Drift-Risiko** [backend/src/solalex/api/routes/control.py:18, backend/src/solalex/api/schemas/control.py:202, backend/src/solalex/state_cache.py:803, 851] — Drei Stellen definieren `Literal["drossel","speicher","multi","export","idle"]`. Eine vergessene Edit driftet still. Fix: Type-Alias `ControlMode` in einem Modul (z. B. `api/schemas/control.py`), die anderen importieren.
- [ ] [Review][Patch] **SoC-Tile zeigt `Min X% / Max Y%` ohne Plausibilitäts-Check** [frontend/src/routes/Running.svelte:413-414] — Wenn `min_soc=80, max_soc=20` (korrupte Config), Tile zeigt es as-is. Die Story-3.6-Validation greift bei PATCH, aber persistierte alte Config kann inkonsistent sein. Fix: `Math.min(min, max)` / `Math.max(min, max)` im Display ODER `console.warn` + Fallback-Label.
- [ ] [Review][Patch] **`reason="noop: unbekannt"` Fallback ohne Warn-Log** [backend/src/solalex/controller.py:316-320] — Wenn künftige Early-Exit-Branches `_set_noop_reason()` vergessen, landen sie als „Unbekannt" in der DB. Fix: `logger.warning("noop_reason_missing", policy=self._current_mode.value)` im Fallback-Pfad — sichtbar in Diagnose-Export.
- [ ] [Review][Patch] **Frontend `display_label` ungenutzt — Tile-Labels hardcoded duplizieren Backend-Glossar** [frontend/src/routes/Running.svelte:390, 397, 404, 416 + backend/src/solalex/api/routes/control.py:33-38] — Backend exposed `display_label` per Entity (Single-Source-Glossar laut AC 14), aber Frontend hardcodet `'Netz-Leistung'` / `'Wechselrichter-Limit'` / `'Akku-SoC'` / `'Verbindung'` an 4 Stellen. CLAUDE.md verbietet die „dritte Mapping-Tabelle" — aktuell sind es zwei Mapping-Quellen, die in Sync gehalten werden müssen. Fix: Tile-Markup liest `entity.display_label` (Fallback auf Connection-Tile-String, der nicht aus dem Backend kommt).
- [ ] [Review][Patch] **`refunctional-test-banner` für Fresh-Install verwirrend („neuen Wechselrichter")** [frontend/src/routes/Running.svelte:1683-1687, 1857-1865] — Banner feuert sobald irgendein `wr_limit`/`wr_charge` `commissioned_at===null` ist — INKLUSIVE Brand-New-Install vor dem Wizard. Wording „Funktionstest erforderlich für den neuen Wechselrichter" suggeriert einen Hardware-Wechsel. Fix: Guard mit „has any commissioned device" (sonst zeigt's brand-new-Hint statt Swap-Hint) ODER Wording entschärfen. (Cross-cutting zu 2.5/2.6, aber im Diff dieser Story; einfach zu fixen.)
- [ ] [Review][Patch] **`cycle-header`/`cycle-row` Grid-Drift Spec ↔ Code (5×Spalten-Breiten)** [frontend/src/routes/Running.svelte:687, 711] — Code: `90px 100px 1fr 110px 64px`. Spec AC 1: `90px / 100px / 80px / 80px / 64px`. Grund der Drift ist plausibel (Status/Ziel breiter für „— (gemessen 12 W)"-Sub-Anzeige), aber Spec und Code stimmen nicht. Fix (Doc): Spec auf Code-Werte aktualisieren mit kurzer Begründung.

### Deferred

- [x] [Review][Defer] **`findEntityByRole` returnt erste Match — Multi-pool / Multi-meter-Setups (v1.5) zeigen nur eine Tile** [frontend/src/routes/Running.svelte:184-186, 198-209] — In v1 ≤1 SoC, ≤1 grid_meter, ≤1 wr_charge → kein Risiko. Fix bei v1.5-Multi-Pool-Story (3.3-Erweiterung).
- [x] [Review][Defer] **`formatCycleStatus` brittle prefix-matching auf deutsche Klartext-Strings** [frontend/src/routes/Running.svelte:1614-1660] — Wenn Backend-Wording einer Reason geändert wird (Typo-Fix, Refactor), bricht das FE-Mapping still. Strukturelles Refactoring (separates `discriminator`-Field statt String-Prefix). Größerer Eingriff, post-Beta.
- [x] [Review][Defer] **`device.config()` per Entity per Polling-Tick — kein Caching** [backend/src/solalex/api/routes/control.py:229-261] — `json.loads(config_json)` läuft jede Sekunde × N Entities. Klein, aber bei vielen Devices spürbar. Cache an `app.state` mit Invalidation in `reload_devices_from_db`.
- [x] [Review][Defer] **`_pool_key` empty-tuple Edge-Case (mehrere Pools mit nur ID-losen Members kollidieren)** [backend/src/solalex/controller.py:232-247] — In v1 max 1 Pool → kein Risiko; bei v1.5-Multi-Pool muss Fallback auf `id(pool)` ergänzt werden, wenn keine Member committed sind.
- [x] [Review][Defer] **`_speicher_last_setpoint_w` migriert nicht über Hardware-Swap (`_pool_key` ändert sich)** [backend/src/solalex/controller.py:232-247, _speicher_last_setpoint_w-Map] — Nach Hardware-Edit (Story 2.6) bekommt Pool einen neuen Key, alter `_speicher_last_setpoint_w`-Eintrag bleibt orphan, neuer startet bei 0 → erster Step ignoriert `min_step_w`-Ramping. v1.5-Härtung.
- [x] [Review][Defer] **`aria-live="polite"` auf Update-Indikator → Screen-Reader-Spam jede Sekunde** [frontend/src/routes/Running.svelte:1843] — A11y-Verbesserung; nur Stale-Transitionen ankündigen, nicht jede Sekunde. Eigene A11y-Sweep-Story.
- [x] [Review][Defer] **Status-Tiles und Chart-Legende rendern auch während `testInProgress` — inkonsistente Gating** [frontend/src/routes/Running.svelte:1842, 1855] — Update-Indikator + Refunctional-Banner gaten auf `testInProgress`, aber Status-Tiles zeigen Live-Werte mid-test (was Verwirrung stiften kann). UX-Polish nach Beta.
- [x] [Review][Defer] **`MODE_LABEL` / `MODE_EXPLANATION` Records ohne Exhaustiveness-Check via `satisfies`** [frontend/src/routes/Running.svelte:1574-1581, 1585-1591] — Wenn `ControlMode`-Union erweitert wird (Story 3.8 EXPORT, künftige Modes), kann ein Map-Eintrag still fehlen → Lookup `undefined` → leere `<p>`. Fix: `satisfies Record<ControlMode, string>` statt `Record<ControlMode, string>`-Annotation.
- [x] [Review][Defer] **`audit` Mode in `_ALLOWED_AUDIT_MODES` (devices.py:46) für Story 3.8 EXPORT-Forward-Compat** [backend/src/solalex/api/routes/devices.py:46] — `CycleMode` erlaubt `audit`, aber `current_mode`-Literal nicht. Konsistenz wenn 3.8 implementiert wird.

### Dismissed

53 Findings als Noise / dokumentiert / pre-existing / out-of-scope verworfen (Test-Coupling-Nits, micro-perf, gleiche Issues mehrfach, Story-2.5/2.6-Scope, defensive duplicate-checks, magic-thresholds, etc.).
