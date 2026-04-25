# Story 3.8: Surplus-Export-Modus bei Akku-Voll (opt-in pro WR)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Beta-Tester mit angemeldeter Anlage und Akku-Speicher,
I want dass Solalex bei vollem Akku das WR-Limit nicht eindrosselt (PV-Abregelung), sondern auf Hardware-Max öffnet (Einspeisung), wenn ich diesen Modus pro Wechselrichter explizit aktiviert habe,
so that ich keine PV-Energie verschenke, aber Mixed-Setups (ein angemeldeter WR + ein Balkonkraftwerk ohne Anmeldung) trotzdem unabhängig konfigurieren kann.

**Scope-Pflock:** Diese Story ergänzt **vier orthogonale Bausteine** zum bestehenden Mono-Modul-Controller:

1. **Mode-Enum-Erweiterung** — `Mode.EXPORT = "export"` als 4. Wert; SQL-Migration 004 erweitert CHECK-Constraints.
2. **Neue Policy `_policy_export`** — am Controller; setzt das WR-Limit auf `device.config_json.max_limit_w`.
3. **Hysterese-Erweiterung in 3.5-Helpern** — `_evaluate_mode_switch` lernt SPEICHER → EXPORT und EXPORT → baseline; `_policy_multi` Cap-Branch ruft `_policy_export` statt `_policy_drossel` bei Toggle ON.
4. **Toggle pro WR** — Persistenz in `device.config_json.allow_surplus_export` (Default `false`); neuer PATCH-Endpunkt `PATCH /api/v1/devices/{id}/config`; Frontend-Toggle in [Config.svelte](../../frontend/src/routes/Config.svelte) + Label-Mapping in [Running.svelte](../../frontend/src/routes/Running.svelte).

**Architektur-Bezug:** Sprint Change Proposal `sprint-change-proposal-2026-04-25-surplus-export.md` + Architecture-Amendment 2026-04-25 (Surplus-Export). Mode-Enum von 3-fach auf 4-fach erweitert; `_policy_export` als Methode am Mono-Modul-Controller (Architektur-Cut 9 bleibt — kein neues Modul). Toggle-Persistenz im bestehenden `device.config_json`-Override-Schema (additiv zum 2026-04-25-Generic-Adapter-Amendment).

**Was diese Story NICHT tut:**

- Keine Spotpreis-/Tibber-Integration (v2-Scope).
- Keine globale `meta.allow_surplus_export`-Variante (per-WR ist verbindlich für Mixed-Setups, siehe SCP).
- Keine Änderung an `_policy_drossel`, `_policy_speicher` (3.2/3.4 fertig).
- Kein Mode-Switch-Animation im Frontend (Story 5.5).
- Kein 5. Mode (`Mode.EXPORT_SCHEDULED` o. ä.) — Surplus-Export ist event-getriggert, nicht zeitfenster-basiert.
- Keine Erweiterung der bestehenden 97/93 %-Hysterese-Schwellen (werden 1:1 wiederverwendet).
- Kein User-Override per Wizard-Sektion „Erweiterte Einstellungen" für andere config_json-Keys (`deadband_w`, `min_step_w`, …) — bleibt v1.5-Scope (siehe Generic-Adapter-Amendment 2026-04-25).
- Keine Mode-Enum-Erweiterung im `state_cache.ModeValue`-Literal **als IDLE-Sentinel** — `'export'` wird ein realer Wert (kein Sentinel).

**Amendment 2026-04-25 (Surplus-Export, verbindlich):** `Mode.EXPORT` ist der 4. Mode-Enum-Wert (CLAUDE.md aktualisiert: „Mode-Enum bleibt 4-fach"). Toggle-Persistenz **pro WR** in `device.config_json.allow_surplus_export` (kein globaler Schalter). Validierung: `allow_surplus_export = true` ist nur akzeptabel, wenn `max_limit_w` ebenfalls gesetzt ist (sonst kennt `_policy_export` den Ziel-Wert nicht). Default `allow_surplus_export = false` preserve das ursprüngliche Nulleinspeisungs-Verhalten — strenge Klasse-1-User (Anlagen ohne Inbetriebnahme-Anmeldung) bemerken keine Verhaltensänderung ohne explizite Toggle-Aktivierung.

**Scope-Tension EXPORT-Hysterese-Schwellen (aufgelöst):** Es wäre denkbar, separate Schwellen für EXPORT (`MODE_SWITCH_EXPORT_HIGH_SOC_PCT`, `MODE_SWITCH_EXPORT_LOW_SOC_PCT`) einzuführen — etwa 95/90 % für EXPORT statt 97/93 % für DROSSEL. **Verbindliche Interpretation:** 3.8 verwendet die **gleichen** Konstanten 97/93 % aus 3.5 (`MODE_SWITCH_HIGH_SOC_PCT`, `MODE_SWITCH_LOW_SOC_PCT`). Keine neuen Konstanten. **Begründung:** Der Schwellenwert beschreibt „Akku ist effektiv voll und nimmt nichts mehr nennenswert auf" — diese physische Grenze ist mode-unabhängig. Wenn EXPORT mit niedrigeren Schwellen früher trigger soll (z. B. 95 %), ist das v1.5-Scope per `device.config_json`-Override; v1 bleibt bei 97/93 %.

**Scope-Tension EXPORT vs. DROSSEL-Migration-Pfad (aufgelöst):** Wenn ein User den Toggle **nach** einem bereits erfolgten DROSSEL-Switch aktiviert (Pool ist gerade ≥ 97 %, Mode ist DROSSEL, dann Toggle ON), passiert **nicht** sofort ein Switch zu EXPORT — der Toggle wirkt erst beim **nächsten** Hysterese-Event. Genauer: `_evaluate_mode_switch` läuft pro Sensor-Event; beim nächsten Event mit `aggregated_pct ≥ 97 %` wird der Toggle gelesen und (a) wenn DROSSEL aktiv und Toggle ON → kein Switch (DROSSEL ist „falscher" Mode, aber das Eintrittskriterium SPEICHER → EXPORT trifft nicht zu), (b) wenn der Pool-SoC ≤ 93 % sinkt, switcht DROSSEL → SPEICHER (3.5-Logik), und beim **nächsten** ≥ 97 %-Event SPEICHER → EXPORT. **Begründung:** Toggle-Aktivierung ist kein Trigger-Event, sondern eine Konfigurations-Änderung. Sofortiger Mode-Switch wäre konzeptionell sauber, aber zwingt den Controller zu einer asynchronen Re-Evaluierung außerhalb des Sensor-Event-Pfads — das verletzt das „Trigger sind Sensor-Events"-Prinzip aus 3.5 AC 26. **Akzeptable Latenz:** maximal eine Hysterese-Periode (Pool runter zu 93 %, dann hoch zu 97 %), in der Praxis Sekunden bis Minuten. **Test:** `test_toggle_activation_does_not_force_immediate_switch`.

**Scope-Tension EXPORT vs. Force-Mode-Override aus 3.5 A1 (aufgelöst):** Story 3.5 Amendment A1 erlaubt einen User-Override (`forced_mode`) per `meta.forced_mode`-Persistenz. Wenn `forced_mode == 'drossel'` aktiv ist, ignoriert `_evaluate_mode_switch` jede Hysterese-Auswertung (returniert `None`) — das gilt **auch** für EXPORT-Switches. Konsequenz: bei aktivem Force-Override hat das Surplus-Export-Toggle **keine** Wirkung. **Begründung:** User-Wille (Force-Mode) schlägt Auto-Detection (Hysterese + Toggle). Das ist konsistent mit der A1-Semantik. **Force-Override `forced_mode = 'export'`:** ist akzeptiert (Mode-Enum-Erweiterung wirkt überall), aber dann ist der Toggle irrelevant — der User hat den Mode hart fixiert. **Test:** `test_forced_mode_disables_surplus_export_switch`.

## Acceptance Criteria

1. **Mode-Enum-Erweiterung (Architektur-Amendment 2026-04-25 Surplus-Export):** `Given` der bestehende `Mode`-Enum mit drei Werten (`DROSSEL`, `SPEICHER`, `MULTI`), `When` Story 3.8 implementiert wird, `Then` wird ein vierter Wert `EXPORT = "export"` ergänzt (lowercase Value, matcht den CHECK-Constraint nach Migration 004). **And** der Enum-Decorator `StrEnum` bleibt unverändert; **and** alle bestehenden Switch-Cases auf `Mode.MULTI` etc. bleiben unverändert; **and** `_dispatch_by_mode` ergänzt einen Branch `case Mode.EXPORT: return self._policy_export(device, sensor_value_w)`.

2. **`_policy_export` Methode am Controller (Mono-Modul-Prinzip):** `Given` ein Sensor-Event auf einem `grid_meter`-Device im `Mode.EXPORT`, `When` `_dispatch_by_mode(Mode.EXPORT, ...)` aufgerufen wird, `Then` ruft es `self._policy_export(device, sensor_value_w)` auf. Signatur: `def _policy_export(self, device: DeviceRecord, sensor_value_w: float | None) -> list[PolicyDecision]`. **Pflicht-Eigenschaften:** Methode lebt am `Controller` (kein Modul-Top-Level, kein Submodul `policies/export.py`); ist **synchron** (kein `async`); macht **keinen** DB-Write, **keinen** State-Cache-Mutation, **keinen** Hardware-Call — produziert nur ein `PolicyDecision`-Objekt, das vom Executor dispatcht wird.

3. **`_policy_export` Decision-Logik:** `Given` `_policy_export(device, sensor_value_w)` läuft, `When` `device.role == 'grid_meter'` und `wr_limit_device != None` und `device.config_json.max_limit_w` ist gesetzt (int), `Then` produziert die Methode genau eine Decision: `PolicyDecision(device=wr_limit_device, target_value_w=int(max_limit_w), mode=Mode.EXPORT.value, command_kind='set_limit', sensor_value_w=sensor_value_w)`. **And** wenn `current_wr_limit_w == max_limit_w` (Limit ist bereits am Hardware-Max) → returniert `[]` (no-op, kein redundanter Schreibbefehl). **And** wenn `device.role != 'grid_meter'` → `[]` (Role-Filter analog Drossel/Speicher).

4. **`_policy_export` Defensive-Handling bei fehlendem `max_limit_w`:** `Given` `Mode.EXPORT` ist aktiv, **And** `wr_limit_device.config_json` enthält **kein** `max_limit_w`, `When` `_policy_export` aufgerufen wird, `Then` schreibt es einen `_logger.warning('policy_export_max_limit_missing', extra={'device_id': wr_limit_device.id})` und returniert `[]`. **And** dies sollte praktisch nie passieren, weil der PATCH-Endpunkt (AC 19) `allow_surplus_export = true` ohne `max_limit_w` ablehnt — die Defensive-Behandlung schützt vor manuell editierter DB oder DB-Migration aus älterer Version. **Test:** `test_export_no_decision_when_max_limit_missing_in_config`.

5. **`_policy_export` Defensive-Handling bei `wr_limit_device == None`:** `Given` `Mode.EXPORT` ist aktiv (irrtümlicherweise — sollte nie ohne WR initial gewählt werden), **And** `self._wr_limit_device is None`, `When` `_policy_export` aufgerufen wird, `Then` returniert es `[]` ohne Log (defensive — kein Crash, kein redundanter Warn-Spam).

6. **Hysterese-Erweiterung in `_evaluate_mode_switch` (additiv zu Story 3.5):** `Given` der bestehende `_evaluate_mode_switch`-Helper (Story 3.5 AC 17 — Pure Function, keine I/O), `When` Story 3.8 ihn erweitert, `Then` wird die Methode um zwei Branches ergänzt:
    - **SPEICHER + Toggle ON → EXPORT:** `if self._current_mode == Mode.SPEICHER and aggregated >= MODE_SWITCH_HIGH_SOC_PCT and self._wr_allow_surplus_export(): return (Mode.EXPORT, f'pool_full_export (soc={aggregated:.1f}%)')`. Dieser Branch hat **Priorität** über den existierenden SPEICHER → DROSSEL-Branch (siehe AC 7).
    - **EXPORT → baseline:** `if self._current_mode == Mode.EXPORT and aggregated <= MODE_SWITCH_LOW_SOC_PCT: return (self._mode_baseline, f'pool_below_low_threshold_export_exit (soc={aggregated:.1f}%)')`. Rückkehr ist immer zum Baseline-Mode (üblicherweise SPEICHER bei 1-Akku-Setup, MULTI bei Multi-Akku-Setup) — **nicht** zu DROSSEL.
    Pure-Function-Disziplin bleibt: Helper macht **keinen** DB-Write, **keinen** Mode-Set, **keinen** Toggle-Read über `meta` (Toggle wird via `device.config_json` gelesen, also auch Pure).

7. **Hysterese-Erweiterung — SPEICHER + Toggle OFF preserve DROSSEL (Regression):** `Given` `Mode.SPEICHER` ist aktiv, **And** `aggregated >= 97 %`, **And** `wr_limit.config_json.allow_surplus_export == False` (Default), `When` `_evaluate_mode_switch` läuft, `Then` returniert es **wie bisher** `(Mode.DROSSEL, f'pool_full (soc={aggregated:.1f}%)')` (Story-3.5-Verhalten unverändert). **Begründung:** Default-Verhalten = Nulleinspeisung. Toggle-OFF-User dürfen keine Verhaltensänderung sehen. **Test:** `test_speicher_to_drossel_when_toggle_off_at_high_soc`.

8. **Hysterese-Helper `_wr_allow_surplus_export` Toggle-Read:** `Given` der Hysterese-Helper braucht den Toggle-Wert, `When` Story 3.8 implementiert wird, `Then` wird eine private Pure-Method `Controller._wr_allow_surplus_export(self) -> bool` ergänzt:
    1. `if self._wr_limit_device is None: return False`.
    2. `try: config = self._wr_limit_device.config()` (ruft `json.loads(config_json)`, kann `JSONDecodeError` werfen).
    3. `except (json.JSONDecodeError, TypeError, ValueError): return False` (defensive — kaputte JSON soll nicht den Controller crashen, sondern stillschweigend Toggle als OFF betrachten).
    4. `value = config.get('allow_surplus_export', False); return bool(value)`.
    Methode ist Pure (kein DB-Read, kein State-Cache-Read — nur Field-Access auf `_wr_limit_device`). **Test:** `test_wr_allow_surplus_export_returns_false_on_corrupt_json`, `test_wr_allow_surplus_export_returns_false_when_no_wr_device`.

9. **`_policy_multi` Cap-Branch-Erweiterung (additiv zu Story 3.5 AC 2):** `Given` der bestehende `_policy_multi` mit Cap-Branch (Speicher empty wegen Max-SoC + Einspeisung → ruft `_policy_drossel` als Fallback), `When` Story 3.8 ihn erweitert, `Then` wird die Cap-Branch-Logik geändert auf:
    ```python
    if self._speicher_max_soc_capped and self._is_feed_in_after_smoothing(device, sensor_value_w):
        if self._wr_allow_surplus_export():
            export_decisions = self._policy_export(device, sensor_value_w)
            return export_decisions  # MULTI mit Surplus-Export — Pool voll, einspeisen
        drossel_decision = self._policy_drossel(device, sensor_value_w)
        return [drossel_decision] if drossel_decision is not None else []
    ```
    **And** MULTI bleibt MULTI (kein Mode-Switch — `_evaluate_mode_switch` returniert weiterhin `None` für aktiven MULTI, AC 7 aus 3.5). **Begründung:** MULTI hat seine Drossel-/Export-Logik intern; ein Mode-Switch wäre destruktiv für die Pool-Lade-Logik. **Test:** `test_multi_cap_branch_calls_export_when_toggle_on`, `test_multi_cap_branch_calls_drossel_when_toggle_off` (Regression).

10. **MULTI-Cap-Branch ohne Einspeisung (Bezug-Symmetrie):** `Given` `Mode.MULTI` aktiv, **And** `_speicher_max_soc_capped == True` (Pool voll), **And** `_is_feed_in_after_smoothing == False` (Bezug, z. B. abendliche Last bei vollem Akku), `When` `_policy_multi` läuft, `Then` returniert es `[]` (weder Drossel noch Export — keine Einspeisung möglich, kein PV-Verlust zu verhindern). **Begründung:** Bezug bei vollem Akku ist kein Surplus-Export-Szenario; Pool entlädt sich (3.4-Logik) und füllt die Last; sobald `aggregated_pct < 97 %` eintritt, wechselt die Cap-Branch zu normaler Speicher-Logik. **Test:** `test_multi_cap_branch_no_decision_on_load_when_pool_full`.

11. **SQL-Migration 004 erweitert CHECK-Constraint:** `Given` die existierende Migration `002_control_cycles_latency.sql` mit `CHECK (mode IN ('drossel','speicher','multi'))`, `When` Story 3.8 die Migration 004 anlegt, `Then` erweitert sie die Constraint auf `CHECK (mode IN ('drossel','speicher','multi','export'))` für **beide** Tabellen (`control_cycles` + `latency_measurements`). **SQLite-Pattern (CREATE TABLE _new + INSERT … SELECT + DROP + RENAME):** SQLite kennt kein `ALTER TABLE … ALTER CONSTRAINT`. Forward-only, kein Downgrade-Pfad (Architecture-Vorgabe). **Indexe** werden nach `RENAME` neu angelegt: `idx_control_cycles_ts`, `idx_control_cycles_device`, `idx_latency_device_ts`. **Test:** `test_migration_004_preserves_existing_rows`, `test_migration_004_allows_export_mode_insert`, `test_migration_004_rejects_invalid_mode`.

12. **`state_cache.ModeValue` + `update_mode`-Whitelist erweitern:** `Given` der bestehende `state_cache.py` mit `ModeValue = Literal["drossel", "speicher", "multi", "idle"]` (Zeile 18) und Whitelist `if mode_value in {"drossel", "speicher", "multi", "idle"}:` (Zeile 75), `When` Story 3.8 ihn erweitert, `Then` wird `'export'` an **drei** Stellen ergänzt: (a) `ModeValue`-Literal in Zeile 18, (b) Whitelist-Set in Zeile 75, (c) `StatePayload.current_mode`-Literal in Zeile 98 (gleiche `ModeValue`-Type-Annotation). **And** `update_mode('export')` setzt `current_mode = 'export'`; unbekannte Werte fallen weiterhin auf `'idle'` (Status-quo-Verhalten). **Test:** `test_state_cache_accepts_export_mode_value`.

13. **Audit-Cycle bei EXPORT-Switch (Pattern aus 3.5 AC 6):** `Given` `_evaluate_mode_switch` returniert `(Mode.EXPORT, reason)`, `When` `_record_mode_switch_cycle(...)` läuft (existierende Methode aus 3.5), `Then` wird der Cycle mit `mode='export'`, `source='solalex'`, `readback_status='noop'`, `reason='mode_switch: speicher→export (pool_full_export (soc=97.5%))'` persistiert. **And** State-Cache wird via `state_cache.update_mode('export')` aktualisiert. **And** `_logger.info('mode_switch', extra={...})` mit `old_mode='speicher'`, `new_mode='export'`, `reason='pool_full_export (soc=97.5%)'`, `baseline_mode=<setup-baseline>`, `aggregated_pct=97.5`. **Test:** `test_export_switch_audit_cycle_persisted_with_export_mode`.

14. **Audit-Cycle bei EXPORT-Exit (Pattern aus 3.5 AC 6):** `Given` `_evaluate_mode_switch` returniert `(self._mode_baseline, reason)` (EXPORT → SPEICHER oder EXPORT → MULTI), `When` `_record_mode_switch_cycle` läuft, `Then` wird der Cycle mit `mode='speicher'` (oder `'multi'`), `reason='mode_switch: export→speicher (pool_below_low_threshold_export_exit (soc=92.4%))'` persistiert. **Test:** `test_export_to_speicher_audit_cycle_on_low_soc`.

15. **Mindest-Verweildauer 60 s gilt auch für EXPORT-Switch (Anti-Oszillation aus 3.5 AC 8):** `Given` ein EXPORT-Switch ist gerade erfolgt (`self._mode_switched_at` gesetzt durch `_record_mode_switch_cycle`), **And** ein folgender Sensor-Event innerhalb von 60 s simuliert eine SoC-Schwankung 92↔98 %, `When` `_evaluate_mode_switch` läuft, `Then` returniert es `None` (Dwell-Time-Block aus 3.5 unverändert wirksam). **Test:** `test_export_dwell_blocks_oscillation` (Sinus-SoC 30 s, max. 1 Wechsel).

16. **Force-Mode-Override (3.5 A1) deaktiviert EXPORT-Switch:** `Given` `forced_mode = 'drossel'` ist aktiv (`meta.forced_mode='drossel'`, Setter aus 3.5 A1 hat `self._forced_mode = Mode.DROSSEL` gesetzt), **And** Pool-SoC ≥ 97 %, **And** Toggle ON, `When` `_evaluate_mode_switch` läuft, `Then` returniert es `None` (Early-Return `if self._forced_mode is not None: return None` aus 3.5 A1 greift). **Begründung:** User-Override schlägt Auto-Detection. **Test:** `test_forced_mode_disables_surplus_export_switch`.

17. **Force-Mode-Override `forced_mode = 'export'` ist akzeptiert:** `Given` der API-Endpunkt `PUT /api/v1/control/mode` aus 3.5 A1, `When` ein Body `{"forced_mode": "export"}` gesendet wird, `Then` validiert die Pydantic-Schema `ForcedModeRequest` den Wert (Literal-Erweiterung um `"export"`); Backend persistiert in `meta.forced_mode='export'` und ruft `controller.set_forced_mode(Mode.EXPORT)` auf. **And** der Audit-Cycle aus 3.5 A1 wird mit `reason='mode_switch: <old>→export (manual_override)'` persistiert. **Test:** `test_forced_mode_export_accepted_and_audited`.

18. **`PATCH /api/v1/devices/{id}/config` Endpunkt (neu):** `Given` der Toggle muss persistierbar sein, `When` Story 3.8 den Endpunkt anlegt, `Then` ergänzt `backend/src/solalex/api/routes/devices.py` einen `@router.patch("/{device_id}/config", response_model=DeviceResponse)`-Handler. **Pflicht-Verhalten:**
    - **Body-Schema:** `DeviceConfigPatchRequest` (siehe AC 21).
    - **Lookup:** Device per `device_id` aus DB. Bei Nicht-Vorhanden → 404.
    - **Partial-Merge:** existierender `config_json` wird per `json.loads`-Parse + Dict-Update + `json.dumps`-Re-Serialize gemerged. Unbekannte Keys im existierenden config_json bleiben erhalten (forward-compat mit zukünftigen Override-Keys).
    - **Validierung:** wenn `body.allow_surplus_export == True`, **muss** der gemergte config_json einen `max_limit_w`-Schlüssel haben (entweder im Patch oder bereits gespeichert). Sonst → 422 mit Klartext „Surplus-Einspeisung erfordert ein konfiguriertes Hardware-Max-Limit (`max_limit_w`)".
    - **Persistenz:** `UPDATE devices SET config_json = ?, updated_at = ? WHERE id = ?` (kein Upsert — Device existiert per Lookup).
    - **Response:** aktualisierter `DeviceResponse` (200 OK).
    - **License/Disclaimer-Gate:** Endpunkt liegt **hinter** dem License-Gate (analog zu anderen Mutationen, gleiche `Depends`-Struktur).

19. **`PATCH`-Endpunkt-Validierung — Surplus ohne Max-Limit ergibt 422:** `Given` ein Device mit `config_json = '{}'` (leer), `When` `PATCH /api/v1/devices/123/config { "allow_surplus_export": true }` ohne `max_limit_w` im Patch, `Then` antwortet das Backend `422 Unprocessable Entity` mit Body `{ "detail": "Surplus-Einspeisung erfordert ein konfiguriertes Hardware-Max-Limit (max_limit_w). Setze zuerst max_limit_w in den Hardware-Einstellungen." }` (RFC 7807 `application/problem+json` Format aus CLAUDE.md Regel 4). **Test:** `test_patch_config_rejects_surplus_without_max_limit`.

20. **`PATCH`-Endpunkt — Surplus mit Max-Limit im Patch akzeptiert:** `Given` ein Device mit `config_json = '{}'`, `When` `PATCH /api/v1/devices/123/config { "allow_surplus_export": true, "max_limit_w": 600 }`, `Then` antwortet das Backend `200 OK`; der gemergte `config_json` enthält `{"allow_surplus_export": true, "max_limit_w": 600}`. **Test:** `test_patch_config_accepts_surplus_with_max_limit_in_patch`.

21. **`DeviceConfigPatchRequest`-Pydantic-Schema:** `Given` der PATCH-Body, `When` Story 3.8 das Schema definiert, `Then` lebt es in `backend/src/solalex/api/schemas/devices.py` als:
    ```python
    class DeviceConfigPatchRequest(BaseModel):
        allow_surplus_export: bool | None = None
        max_limit_w: int | None = Field(default=None, ge=1)
        min_limit_w: int | None = Field(default=None, ge=0)
        deadband_w: int | None = Field(default=None, ge=0)
        min_step_w: int | None = Field(default=None, ge=0)
        smoothing_window: int | None = Field(default=None, ge=1)
        limit_step_clamp_w: int | None = Field(default=None, ge=1)
        model_config = ConfigDict(extra="forbid")
    ```
    **Pflicht:** `extra="forbid"` (keine unbekannten Keys aus Frontend). Alle Felder optional (PATCH ist partial). **And** Werte werden nur in den `config_json`-Merge übernommen, wenn sie `non-None` sind (partial-merge-Semantik). **Test:** `test_patch_config_request_schema_rejects_unknown_keys`.

22. **`PATCH`-Endpunkt — partial-merge bewahrt unbekannte Keys:** `Given` ein Device mit `config_json = '{"deadband_w": 5, "future_key": "v2_value"}'` (manuelle DB-Edit oder zukünftiger Override-Key), `When` `PATCH /api/v1/devices/123/config { "allow_surplus_export": true, "max_limit_w": 600 }`, `Then` ist der gemergte config_json `{"deadband_w": 5, "future_key": "v2_value", "allow_surplus_export": true, "max_limit_w": 600}` (alle vorhandenen Keys bleiben erhalten). **Begründung:** Schutz vor Datenverlust durch Frontend-Schema-Drift; v1.5/v2 könnten zusätzliche Override-Keys einführen. **Test:** `test_patch_config_partial_merge_preserves_unknown_keys`.

23. **Frontend `Config.svelte` — Toggle pro WR-Tile:** `Given` die Hardware-Config-Page mit existierenden WR-Devices, `When` Story 3.8 die UI erweitert, `Then` wird **pro WR-Device** (Role `wr_limit`) ein Toggle-Block gerendert:
    - Label: „**Surplus-Einspeisung erlauben** (statt PV-Abregelung) bei vollem Akku"
    - Sub-Hint: „Bei vollem Akku öffnet Solalex das WR-Limit auf das Hardware-Maximum, statt die PV einzudrosseln. Geeignet für angemeldete Anlagen mit EEG-Vergütung. Nicht aktivieren bei Anlagen ohne Inbetriebnahme-Anmeldung beim Netzbetreiber."
    - Voraussetzungs-Hint (wenn `max_limit_w` nicht gesetzt): Toggle ist **disabled** mit zusätzlichem Klartext „Voraussetzung: Hardware-Max-Limit (W) muss zuerst gesetzt werden."
    - On-Change: Optimistisches UI-Update + `setSurplusExport(deviceId, value)` PATCH-Call. Bei Fehler: Revert + Inline-Hint-Text mit der Backend-Fehlermeldung (kein Toast — UX-DR30).
    - Kein „Speichern"-Button (Auto-PUT-Pattern aus Story 2.1).
    - Strings deutsch hardcoded (CLAUDE.md — keine i18n).

24. **Frontend `client.ts` — neue API-Methode `setSurplusExport`:** `Given` der PATCH-Endpunkt aus AC 18, `When` Story 3.8 die Frontend-Schnittstelle ergänzt, `Then` wird in [client.ts](../../frontend/src/lib/api/client.ts) ergänzt:
    ```ts
    export async function setSurplusExport(
      deviceId: number,
      enabled: boolean,
    ): Promise<DeviceResponse> {
      return apiPatch<DeviceResponse>(`/api/v1/devices/${deviceId}/config`, {
        allow_surplus_export: enabled,
      });
    }
    ```
    **And** TS-Type-Erweiterung in [types.ts](../../frontend/src/lib/api/types.ts): `DeviceConfigPatchBody` als optionales Sub-Interface (analog zu existierenden Patch-Bodies, falls vorhanden — sonst inline `Record<string, boolean | number>`).

25. **Frontend `Running.svelte` — Mode-Label-Mapping `'export'` → „Einspeisung":** `Given` die Running-View rendert `current_mode` aus `state_cache`, `When` Story 3.8 die UI erweitert, `Then` wird das Mode-Label-Mapping um `'export' → 'Einspeisung'` ergänzt (deutsche Strings, keine i18n). Mapping liegt typischerweise in einer Inline-Funktion oder einem `const`-Objekt; existierende Mode-Werte (`'drossel' → 'Drossel'`, `'speicher' → 'Speicher'`, `'multi' → 'Multi'`, `'idle' → 'Inaktiv'` oder ähnlich) bleiben unverändert.

26. **Polling-Endpoint `/api/v1/control/state` enthält `current_mode = 'export'` automatisch:** `Given` `state_cache.current_mode = 'export'` (aus AC 12), `When` der Polling-Endpoint die `StatePayload` zurückgibt, `Then` enthält das JSON `{"current_mode": "export", ...}` ohne weitere Code-Änderung — die `state_cache.ModeValue`-Erweiterung deckt das ab. **Test:** `test_polling_endpoint_returns_export_mode_when_cache_set`.

27. **Toggle-Aktivierung triggert KEINEN sofortigen Mode-Switch (Aktualisierungs-Latenz):** `Given` `Mode.DROSSEL` ist aktiv (vorher von SPEICHER gewechselt wegen Pool-Voll), **And** der User aktiviert jetzt den Toggle (`PATCH config { allow_surplus_export: true }`), `When` der PATCH-Handler den Toggle persistiert, `Then` triggert er **keinen** sofortigen Mode-Switch (kein expliziter `controller.evaluate_mode_switch_now()`-Call). **Begründung:** Mode-Switches sind sensor-event-getriggert (3.5 AC 26); Toggle-Änderung ist Konfiguration. Beim nächsten Sensor-Event mit Pool-SoC ≤ 93 % switcht DROSSEL → SPEICHER (3.5-Logik), und beim folgenden ≥ 97 %-Event SPEICHER → EXPORT (3.8-Logik). **Akzeptable Latenz:** Sekunden bis Minuten. **Test:** `test_toggle_activation_does_not_force_immediate_switch`.

28. **`_record_mode_switch_cycle` Cap-Flag-Reset gilt auch für EXPORT-Switch:** `Given` ein Mode-Switch zu EXPORT erfolgt (von SPEICHER), `When` `_record_mode_switch_cycle` läuft (aus 3.5 AC 12), `Then` werden `self._speicher_max_soc_capped = False` und `self._speicher_min_soc_capped = False` zurückgesetzt — Pattern unverändert. **Begründung:** Beim späteren Rück-Switch zu SPEICHER soll der erste Cap-Eintritt wieder einen `info`-Log produzieren. **Kein Code-Change** in 3.8 nötig — 3.5-Logik greift unverändert für jeden Switch. Test wird in 3.5-Test-Suite gespiegelt: `test_mode_switch_resets_speicher_cap_flags_for_export`.

29. **Initial-Selector `select_initial_mode` wählt **NICHT** EXPORT initial:** `Given` `select_initial_mode(devices_by_role, battery_pool, forced_mode=None)` aus Story 3.5, `When` Story 3.8 die Logik berührt (oder sie unverändert lässt), `Then` returniert der Selector **nie** `Mode.EXPORT` als Initial-Mode bei `forced_mode=None`. **Begründung:** EXPORT ist ein Hysterese-State, kein Setup-Mode. Der Initial-Mode kommt aus `wr/pool/member-count`-Topologie (3.5 AC 1); EXPORT wird nur per Hysterese-Switch erreicht. **Force-Override:** `forced_mode='export'` ist erlaubt (AC 17), und in dem Fall returniert der Selector `(Mode.EXPORT, baseline=<auto>)` — das ist ein expliziter User-Wille, kein Auto-Detect. **Code-Change in `select_initial_mode`:** **keiner** für Auto-Detect-Fall; die `forced_mode`-Pass-Through-Logik aus 3.5 A1 wirkt automatisch (nur Pydantic-Schema-Erweiterung um `"export"` nötig — siehe AC 17). **Test:** `test_select_initial_mode_never_returns_export_without_forced`.

30. **Tests (Pytest, MyPy strict, Ruff):** Neue Test-Dateien unter `backend/tests/unit/`:
    - `test_controller_policy_export.py`:
      - `test_export_sets_limit_to_max_when_below` (AC 3)
      - `test_export_no_decision_when_already_at_max` (AC 3)
      - `test_export_no_decision_when_max_limit_missing_in_config` (AC 4)
      - `test_export_warns_logger_when_max_limit_missing` (AC 4)
      - `test_export_no_decision_on_non_grid_meter_event` (AC 3)
      - `test_export_no_decision_when_no_wr_limit_device` (AC 5)
      - `test_export_dispatch_by_mode_routes_to_policy_export` (AC 1)
    - `test_controller_mode_switch_export.py`:
      - `test_speicher_to_export_when_toggle_on_and_pool_full` (AC 6)
      - `test_speicher_to_drossel_when_toggle_off_and_pool_full` (AC 7 — Regression)
      - `test_export_to_speicher_at_low_soc_when_baseline_was_speicher` (AC 6)
      - `test_export_to_multi_at_low_soc_when_baseline_was_multi` (AC 6)
      - `test_export_dwell_blocks_oscillation` (AC 15)
      - `test_export_switch_audit_cycle_persisted_with_export_mode` (AC 13)
      - `test_export_to_speicher_audit_cycle_on_low_soc` (AC 14)
      - `test_forced_mode_disables_surplus_export_switch` (AC 16)
      - `test_forced_mode_export_accepted_and_audited` (AC 17)
      - `test_toggle_activation_does_not_force_immediate_switch` (AC 27)
      - `test_select_initial_mode_never_returns_export_without_forced` (AC 29)
    - `test_controller_multi_export.py`:
      - `test_multi_cap_branch_calls_export_when_toggle_on` (AC 9)
      - `test_multi_cap_branch_calls_drossel_when_toggle_off` (AC 9 — Regression)
      - `test_multi_cap_branch_no_decision_on_load_when_pool_full` (AC 10)
    - `test_controller_wr_allow_surplus_export.py`:
      - `test_wr_allow_surplus_export_returns_true_when_set` (AC 8)
      - `test_wr_allow_surplus_export_returns_false_default` (AC 8)
      - `test_wr_allow_surplus_export_returns_false_on_corrupt_json` (AC 8)
      - `test_wr_allow_surplus_export_returns_false_when_no_wr_device` (AC 8)
    - `test_state_cache_export_mode.py`:
      - `test_state_cache_accepts_export_mode_value` (AC 12)
      - `test_polling_endpoint_returns_export_mode_when_cache_set` (AC 26)
    - `test_migration_004_export_mode.py`:
      - `test_migration_004_preserves_existing_rows` (AC 11)
      - `test_migration_004_allows_export_mode_insert` (AC 11)
      - `test_migration_004_rejects_invalid_mode` (AC 11)
      - `test_migration_004_indexes_recreated` (AC 11)
    - `test_api_devices_patch_config.py`:
      - `test_patch_config_rejects_surplus_without_max_limit` (AC 19)
      - `test_patch_config_accepts_surplus_with_max_limit_in_patch` (AC 20)
      - `test_patch_config_accepts_surplus_with_existing_max_limit` (AC 20)
      - `test_patch_config_partial_merge_preserves_unknown_keys` (AC 22)
      - `test_patch_config_request_schema_rejects_unknown_keys` (AC 21)
      - `test_patch_config_404_for_unknown_device` (AC 18)
      - `test_patch_config_requires_active_license_gate` (AC 18 — License/Disclaimer-Gate)
    - **Coverage-Ziel:** ≥ 90 % Line-Coverage auf allen Änderungen in `controller.py` (`_policy_export`, `_evaluate_mode_switch`-Erweiterung, `_policy_multi`-Cap-Branch-Erweiterung, `_wr_allow_surplus_export`).
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (`004_mode_export.sql` lückenlos nach `003`).

31. **Frontend-Tests (Vitest + @testing-library):** Erweiterung bestehender Test-Dateien:
    - `frontend/src/routes/Config.test.ts` (existierend, erweitern):
      - `test_renders_surplus_toggle_for_wr_devices` (AC 23)
      - `test_toggle_disabled_without_max_limit` (AC 23)
      - `test_patch_called_on_toggle_change` (AC 24)
      - `test_toggle_reverts_on_api_error` (AC 24)
      - `test_inline_hint_shown_on_validation_error` (AC 24)
    - `frontend/src/routes/Running.test.ts` (existierend, erweitern):
      - `test_displays_einspeisung_label_when_mode_is_export` (AC 25)
    - `frontend/src/lib/api/client.test.ts` (existierend, erweitern):
      - `test_set_surplus_export_calls_patch_endpoint` (AC 24)
      - `test_set_surplus_export_returns_device_response` (AC 24)

32. **Drift-Checks (CI-Gate-relevant):**
    - `grep -rE "policy_export\.py$|export_policy\.py$|policies/export\.py$" backend/src/solalex/` → **0 Treffer** (Mono-Modul-Prinzip — `_policy_export` lebt am Controller, kein separates Modul).
    - `grep -rE "Mode\.EXPORT" backend/src/solalex/controller.py` → ≥ 4 Treffer (Enum-Definition, `_dispatch_by_mode`-Branch, `_evaluate_mode_switch`-Branch, `_policy_export`-Returnwert).
    - `grep -rE "allow_surplus_export" backend/src/solalex/` → mehrere Treffer in `controller.py`, `api/routes/devices.py`, `api/schemas/devices.py`.
    - `grep -rE "MODE_SWITCH_EXPORT_HIGH_SOC_PCT|MODE_SWITCH_EXPORT_LOW_SOC_PCT" backend/src/solalex/` → **0 Treffer** (keine separaten EXPORT-Schwellen; siehe Scope-Tension oben).
    - `grep -rE "structlog|APScheduler|cryptography|numpy|pandas|SQLAlchemy" backend/src/solalex/` → **0 Treffer** (CLAUDE.md harte Regeln unverändert).
    - SQL-Ordering: `001` + `002` + `003` + `004` (lückenlos nach 2.4-Refit + 3.8-Surplus).

33. **Frontend-Drift-Check:** `grep -rE "Mode\.EXPORT|'export'" frontend/src/` → Treffer in `lib/api/types.ts` (Mode-Type-Erweiterung), `routes/Running.svelte` (Label-Mapping), `routes/Config.svelte` (Toggle-Logik), Tests. Keine Treffer in `app.css`, `lib/stores/`, anderen Routes.

34. **Manueller Smoke-Test (im Story-File dokumentiert, kein separater Smoke-Test-Doku-Update nötig):**
    1. Setup-Wizard durchlaufen mit angemeldetem WR (`max_limit_w=600` z. B. setzen). Smoke-Test-Dokument bleibt unverändert.
    2. In Config-Page nach Setup: Toggle „Surplus-Einspeisung erlauben" für WR aktivieren. Inline-Hint sollte verschwinden. Toggle-State persistiert (Page-Reload zeigt weiterhin aktiv).
    3. Pool-SoC manuell auf 98 % setzen (HA-Sensor-Override im Test-HA oder echter Setup).
    4. Beobachten in Running-View: Mode-Label wechselt von „Speicher" zu „Einspeisung". WR-Limit (in HA-Entity sichtbar) springt auf 600 W.
    5. Im SQLite-Diagnose-Export: `control_cycles` enthält Row mit `mode='export'`, `reason='mode_switch: speicher→export (pool_full_export (soc=98.0%))'`, `target_value_w=600`.
    6. Pool-SoC manuell auf 92 % setzen.
    7. Beobachten: nach 60 s Dwell-Time switcht Mode zurück zu „Speicher". WR-Limit reagiert wieder reaktiv (Drossel-Pfad).
    8. **Regression:** Toggle deaktivieren. Pool-SoC auf 98 %. Beobachten: Mode wechselt zu „Drossel" (nicht „Einspeisung"). Status-quo aus 3.5 unverändert.

35. **Scope-Eingrenzung Diff:** Die Story bringt **Backend + Frontend + SQL-Migration**, aber:
    - **Keine** neue Python-Dependency (`pyproject.toml` unverändert).
    - **Keine** neue Frontend-Dependency (`package.json` unverändert).
    - **Keine** neue Konstante in `controller.py` außerhalb der Mode-Enum-Erweiterung (97/93 % aus 3.5 wiederverwendet).
    - **Keine** Änderung am `AdapterBase`-Interface (Adapter sind 3.8-blind).
    - **Keine** Änderung am Executor / Veto-Kaskade / Readback / Rate-Limiter (nutzen unverändert die `PolicyDecision`-Struktur, `mode='export'` ist neuer Wert im `mode`-Field).

## Tasks / Subtasks

- [ ] **Task 1: Mode-Enum + SQL-Migration 004** (AC: 1, 11)
  - [ ] In [controller.py](../../backend/src/solalex/controller.py) Zeile ~72: `Mode`-Enum erweitern um `EXPORT = "export"`.
  - [ ] Neue SQL-Datei [backend/src/solalex/persistence/sql/004_mode_export.sql](../../backend/src/solalex/persistence/sql/004_mode_export.sql) anlegen mit Recreate-Pattern für `control_cycles` und `latency_measurements`. Forward-only.
  - [ ] **STOP:** Bei der Erweiterung der CHECK-Constraint **nicht** vergessen, `latency_measurements.mode` ebenfalls zu aktualisieren — sonst inkonsistente Constraints, und Story 4.4-Latenz-Auswertung mit `mode='export'` schlägt fehl.

- [ ] **Task 2: `state_cache.ModeValue` + `update_mode`-Whitelist** (AC: 12, 26)
  - [ ] In [state_cache.py](../../backend/src/solalex/state_cache.py) Zeile 18: `ModeValue = Literal["drossel", "speicher", "multi", "idle", "export"]`.
  - [ ] Zeile 75: `if mode_value in {"drossel", "speicher", "multi", "idle", "export"}:`.
  - [ ] Zeile 98 (StatePayload-Dataclass): `current_mode: ModeValue = "idle"` — Type-Annotation passt automatisch durch ModeValue-Update.
  - [ ] **Stop:** **Kein** neuer Sentinel — `'export'` ist ein realer Mode-Wert, nicht IDLE-äquivalent.

- [ ] **Task 3: `_wr_allow_surplus_export` Helper** (AC: 8)
  - [ ] Neue Methode `Controller._wr_allow_surplus_export(self) -> bool`. Signatur ohne Parameter. Pure (kein DB-Read).
  - [ ] Defensive `try/except (json.JSONDecodeError, TypeError, ValueError)` um `device.config()`.
  - [ ] **Stop:** **Kein** Caching — Toggle wird live gelesen, damit der nächste PATCH sofort wirkt.

- [ ] **Task 4: `_policy_export` Methode** (AC: 2, 3, 4, 5)
  - [ ] Neue Methode `Controller._policy_export(self, device: DeviceRecord, sensor_value_w: float | None) -> list[PolicyDecision]`.
  - [ ] Pflicht-Filter: `device.role != 'grid_meter'` → `[]`.
  - [ ] Hardware-Max lesen aus `wr_limit_device.config().get('max_limit_w')`. Bei `None` → warning-log + `[]`.
  - [ ] Aktuellen Limit-Wert lesen via `_read_current_wr_limit_w(wr_limit_device)`. Bei `None` (state-cache miss) → `[]`.
  - [ ] Bei `current_w >= max_limit_w` → `[]` (no-op).
  - [ ] Sonst: `PolicyDecision(device=wr_limit_device, target_value_w=int(max_limit_w), mode=Mode.EXPORT.value, command_kind='set_limit', sensor_value_w=sensor_value_w)`.
  - [ ] **Stop:** **Keine** `_speicher_*`-Flags lesen oder mutieren — `_policy_export` ist unabhängig von der Speicher-Logik.

- [ ] **Task 5: `_dispatch_by_mode`-Erweiterung** (AC: 1)
  - [ ] In `_dispatch_by_mode` ergänzen: `case Mode.EXPORT: return self._policy_export(device, sensor_value_w)`.
  - [ ] `assert_never(mode)`-Branch bleibt am Ende — er sieht jetzt auch EXPORT als gehandhabt.

- [ ] **Task 6: `_evaluate_mode_switch`-Erweiterung** (AC: 6, 7, 15, 16)
  - [ ] **Reihenfolge der neuen Branches in der Methode (kritisch):**
    1. Force-Mode-Override-Check (3.5 A1, unverändert) → return None.
    2. MULTI-Early-Return (3.5 AC 7, unverändert) → return None.
    3. Pool-Existenz-Check (3.5, unverändert) → return None.
    4. Soc-Read (3.5, unverändert) → bei None return None.
    5. Dwell-Check (3.5 AC 8, unverändert) → return None.
    6. **NEU:** SPEICHER + 97% + Toggle ON → `(Mode.EXPORT, f'pool_full_export (soc={aggregated:.1f}%)')`. **Vor** dem existierenden SPEICHER → DROSSEL-Branch.
    7. SPEICHER + 97% (Toggle OFF) → `(Mode.DROSSEL, f'pool_full (soc={aggregated:.1f}%)')` (3.5-Branch, unverändert — wirkt nur wenn Toggle OFF).
    8. **NEU:** EXPORT + 93% → `(self._mode_baseline, f'pool_below_low_threshold_export_exit (soc={aggregated:.1f}%)')`.
    9. DROSSEL → SPEICHER (3.5 AC 5, unverändert).
    10. Sonst return None.
  - [ ] **Pure-Function-Disziplin** (3.5 AC 17): keine Side-Effects, keine I/O. Toggle-Read via `self._wr_allow_surplus_export()` (Pure).

- [ ] **Task 7: `_policy_multi` Cap-Branch-Erweiterung** (AC: 9, 10)
  - [ ] In `_policy_multi`-Methode (Story 3.5 AC 13 Promotion vom Stub): den Cap-Branch ergänzen:
    ```python
    if self._speicher_max_soc_capped and self._is_feed_in_after_smoothing(device, sensor_value_w):
        if self._wr_allow_surplus_export():
            return self._policy_export(device, sensor_value_w)
        drossel_decision = self._policy_drossel(device, sensor_value_w)
        return [drossel_decision] if drossel_decision is not None else []
    ```
  - [ ] **Keine Änderung** am Bezugs-Pfad (Min-SoC-Cap ohne Drossel-Anstieg, AC 3 aus 3.5) — Bezug-Symmetrie aus AC 10 stellt sicher, dass `_policy_export` bei Bezug nicht aufgerufen wird (kein Surplus zu exportieren).

- [ ] **Task 8: PATCH-Endpunkt + Pydantic-Schema** (AC: 18, 19, 20, 21, 22)
  - [ ] Neuer Handler `@router.patch("/{device_id}/config", response_model=DeviceResponse)` in [api/routes/devices.py](../../backend/src/solalex/api/routes/devices.py).
  - [ ] Body-Schema `DeviceConfigPatchRequest` in [api/schemas/devices.py](../../backend/src/solalex/api/schemas/devices.py): siehe AC 21. `extra="forbid"`. `model_config = ConfigDict(extra="forbid")`.
  - [ ] Lookup-Path: `device = await get_device_by_id(conn, device_id)`. Bei `None` → `HTTPException(404, ...)`.
  - [ ] Partial-Merge-Logik:
    ```python
    existing = json.loads(device.config_json) if device.config_json else {}
    patch = body.model_dump(exclude_none=True)
    merged = {**existing, **patch}
    ```
  - [ ] Validierung: `if merged.get('allow_surplus_export') and 'max_limit_w' not in merged: raise HTTPException(422, ...)`.
  - [ ] Persistenz: `UPDATE devices SET config_json=?, updated_at=? WHERE id=?` via Repository-Layer (folgt 2.4-Refit-Pattern).
  - [ ] License/Disclaimer-Gate: `Depends(require_active_license)` o. ä. (analog zu existierenden Mutationen).
  - [ ] **Stop:** **Kein** vollständiges Replace von `config_json` — partial-merge ist non-verhandelbar (AC 22).

- [ ] **Task 9: `set_forced_mode` Schema-Erweiterung um `'export'`** (AC: 17)
  - [ ] In [api/schemas/control.py](../../backend/src/solalex/api/schemas/control.py): `ForcedModeRequest.forced_mode`-Literal um `"export"` erweitern.
  - [ ] **Keine** Änderung an `set_forced_mode`-Methode am Controller — die nimmt bereits `Mode | None` an.

- [ ] **Task 10: Frontend `Config.svelte` Toggle** (AC: 23, 24)
  - [ ] In [Config.svelte](../../frontend/src/routes/Config.svelte): pro WR-Device-Tile (Role `wr_limit`) einen Block einfügen mit Checkbox + Label + Sub-Hint + Voraussetzungs-Hint.
  - [ ] State: `let surplusExport = $state(...)` initialisiert aus `device.config_json`-Parse.
  - [ ] Helper: `let hasMaxLimit = $derived(...)` — true wenn `max_limit_w` in config_json gesetzt.
  - [ ] On-Change: `setSurplusExport(device.id, surplusExport)` mit optimistischem UI-Update + Revert-bei-Fehler.
  - [ ] Strings deutsch hardcoded.
  - [ ] **Stop:** Kein Toast, kein Modal, kein Spinner (UX-DR30). Skeleton-Pulse während des PATCH-Calls erlaubt, ≥ 400 ms.

- [ ] **Task 11: Frontend `client.ts` API-Methode** (AC: 24)
  - [ ] In [client.ts](../../frontend/src/lib/api/client.ts): `setSurplusExport(deviceId, enabled)` ergänzen, Pattern wie existierende Funktionen.
  - [ ] **Stop:** Falls Generic `apiPatch<T>`-Helper noch nicht existiert, kleine Erweiterung des HTTP-Wrappers nötig (analog zu `apiPost`/`apiGet`).

- [ ] **Task 12: Frontend `Running.svelte` Mode-Label** (AC: 25)
  - [ ] In [Running.svelte](../../frontend/src/routes/Running.svelte): Mode-Label-Mapping ergänzen — `'export' → 'Einspeisung'`. Genaue Stelle im Mapping-`const` oder Inline-`switch`-Block.

- [ ] **Task 13: Backend Tests** (AC: 30)
  - [ ] 6 neue Test-Files mit ~30 Tests (siehe AC-Liste oben).
  - [ ] Reuse von `_controller_helpers.py` (FakeHaClient, In-Memory-DB, `build_marstek_pool`) aus 3.x-Stories.
  - [ ] `test_export_dwell_blocks_oscillation` simuliert Sinus-SoC-Schwankung 92↔98 % über 30 s, asserted max. 1 Wechsel.

- [ ] **Task 14: Frontend Tests** (AC: 31)
  - [ ] Erweiterung von `Config.test.ts`, `Running.test.ts`, `client.test.ts`. Pattern wie 2.4-Test-Sweep.

- [ ] **Task 15: Final Verification** (AC: 30, 32, 33)
  - [ ] `cd backend && uv run ruff check .` → grün.
  - [ ] `cd backend && uv run mypy --strict src/ tests/` → grün.
  - [ ] `cd backend && uv run pytest -q` → grün (alle bisherigen + ~30 neue Tests).
  - [ ] `cd frontend && npm run lint && npm run check && npm run test` → grün.
  - [ ] Drift-Check 1: `grep -rE "policy_export\.py$" backend/src/solalex/` → 0 Treffer.
  - [ ] Drift-Check 2: `grep -rE "MODE_SWITCH_EXPORT_HIGH_SOC_PCT" backend/src/solalex/` → 0 Treffer.
  - [ ] SQL-Ordering: 001 + 002 + 003 + 004 (lückenlos).
  - [ ] **Manueller Smoke-Test:** Schritte 1–8 aus AC 34 durchführen.

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [Sprint Change Proposal 2026-04-25 Surplus-Export](../planning-artifacts/sprint-change-proposal-2026-04-25-surplus-export.md) — **Pflichtlektüre.** Vollständige Begründung, Verworfene Alternativen, Detail-Spezifikation.
- [architecture.md — Amendment 2026-04-25 Surplus-Export](../planning-artifacts/architecture.md) — Mode-Enum-Erweiterung, `_policy_export`-Vertrag, Toggle-Persistenz.
- [architecture.md — Amendment 2026-04-25 Generic-Adapter](../planning-artifacts/architecture.md) — `device.config_json`-Override-Schema, das in 3.8 um `allow_surplus_export` erweitert wird.
- [architecture.md — Core Architectural Decisions Zeile 230–262](../planning-artifacts/architecture.md) — Controller-Monolith, Cut 9.
- [prd.md — FR16 + FR16a (Amendment 2026-04-25 Surplus-Export)](../planning-artifacts/prd.md) — Hysterese-Erweiterung um EXPORT-Branch, Default-Verhalten preserve.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine (aktualisiert)](../../CLAUDE.md) — Mode-Enum bleibt 4-fach, kein `_policy_drossel`-Patch für Surplus.
- [Story 3.1](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — `Mode`-Enum, `set_mode`-API, `_dispatch_by_mode`, Per-Device-Lock, `_safe_dispatch`, `_record_noop_cycle`-Pattern.
- [Story 3.2](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — `_policy_drossel`-Logik, Smoothing-Buffer (für 3.8-`_is_feed_in_after_smoothing`-Reuse).
- [Story 3.4](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md) — `_policy_speicher`, `_speicher_max_soc_capped`-Flag-Pattern (Brücke zu MULTI-Cap-Branch).
- [Story 3.5](./3-5-adaptive-strategie-auswahl-hysterese-basierter-modus-wechsel-inkl-multi-modus.md) — **Pflichtlektüre.** Hysterese-Helper `_evaluate_mode_switch`, Audit-Cycle-Pattern `_record_mode_switch_cycle`, `_policy_multi` mit Cap-Branch, Force-Mode-Override (A1), `_mode_baseline`-Field.
- [Story 5.1a — Live-Betriebs-View](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md) — `state_cache.update_mode`-Heartbeat-Pattern; EXPORT-Mirror passt nahtlos ein.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Backend (Mode-Enum + Policy + Migration + PATCH-Endpunkt + Hysterese-Erweiterungen) **plus** Frontend (Config-Toggle + Label-Mapping). Keine Animationen — die kommen in Story 5.5.

**Mini-Diff-Prinzip:** Erwarteter Diff-Umfang:

- **MOD Backend:**
  - `backend/src/solalex/controller.py` (+~120 LOC: Mode-Enum +1 Wert, `_wr_allow_surplus_export` ~10 LOC, `_policy_export` ~30 LOC, `_evaluate_mode_switch`-Erweiterung ~15 LOC, `_policy_multi`-Cap-Erweiterung ~10 LOC, `_dispatch_by_mode`-Branch +2 LOC, plus Defensive-Comments).
  - `backend/src/solalex/state_cache.py` (~3 LOC — Whitelist-Erweiterung).
  - `backend/src/solalex/api/routes/devices.py` (+~50 LOC — PATCH-Handler).
  - `backend/src/solalex/api/schemas/devices.py` (+~15 LOC — `DeviceConfigPatchRequest`).
  - `backend/src/solalex/api/schemas/control.py` (~1 LOC — Literal-Erweiterung um `"export"`).

- **NEU Backend:**
  - `backend/src/solalex/persistence/sql/004_mode_export.sql` (~50 LOC — Recreate-Pattern).
  - 6 NEU Test-Files: `test_controller_policy_export.py` (~250 LOC), `test_controller_mode_switch_export.py` (~600 LOC), `test_controller_multi_export.py` (~300 LOC), `test_controller_wr_allow_surplus_export.py` (~150 LOC), `test_state_cache_export_mode.py` (~80 LOC), `test_migration_004_export_mode.py` (~150 LOC), `test_api_devices_patch_config.py` (~250 LOC).

- **MOD Frontend:**
  - `frontend/src/routes/Config.svelte` (+~30 LOC — Toggle-Block + Logic).
  - `frontend/src/routes/Running.svelte` (~2 LOC — Label-Mapping).
  - `frontend/src/lib/api/client.ts` (+~10 LOC — `setSurplusExport`-Funktion).
  - `frontend/src/lib/api/types.ts` (~2 LOC — Mode-Type-Erweiterung um `'export'`).

- **MOD Frontend Tests:**
  - `frontend/src/routes/Config.test.ts` (+~80 LOC — 5 neue Tests).
  - `frontend/src/routes/Running.test.ts` (+~20 LOC — 1 neuer Test).
  - `frontend/src/lib/api/client.test.ts` (+~30 LOC — 2 neue Tests).

**Dateien, die berührt werden dürfen — und sonst NIEMAND:**

- **MOD Backend:** `controller.py`, `state_cache.py`, `api/routes/devices.py`, `api/schemas/devices.py`, `api/schemas/control.py`.
- **NEU Backend:** `persistence/sql/004_mode_export.sql`, 6 Test-Files.
- **MOD Frontend:** `routes/Config.svelte`, `routes/Running.svelte`, `lib/api/client.ts`, `lib/api/types.ts`, 3 Test-Files.

- **NICHT anfassen:**
  - `backend/src/solalex/battery_pool.py` — Pool fertig in 3.3; 3.8 konsumiert nur indirekt via `_policy_speicher`-Cap-Flag-Brücke.
  - `backend/src/solalex/executor/*.py` — Veto-Kaskade greift unverändert für `mode='export'`.
  - `backend/src/solalex/adapters/*` — Adapter sind 3.8-blind; `_policy_export` setzt nur den Limit-Wert via existierender `build_set_limit_command`-API.
  - `backend/src/solalex/persistence/repositories/control_cycles.py` — Insertion akzeptiert `mode='export'` automatisch nach Migration 004.
  - `backend/src/solalex/persistence/sql/{001,002,003}_*.sql` — bestehende Migrations sind forward-only und werden **nicht** modifiziert.
  - `backend/src/solalex/main.py` — kein Lifespan-Change (Force-Mode-Override aus 3.5 lädt bereits per `meta.forced_mode`; 3.8 ändert nichts an Lifespan).
  - `backend/src/solalex/kpi/*` — KPI-Aggregation nimmt `mode='export'`-Cycles automatisch auf.
  - `backend/src/solalex/common/*` — Logging-Wrapper unverändert.
  - `pyproject.toml`, `package.json` — keine neue Dependency.
  - `frontend/src/app.css` — keine neuen Tokens (Toggle ist Standard-Checkbox-Style).
  - `frontend/src/lib/stores/*` — keine neuen Stores (Toggle-State lokal in Config.svelte).

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du `_policy_export` in ein eigenes Modul `policies/export.py` auslagerst — **STOP**. Mono-Modul-Prinzip (Architecture Cut 9, Amendment 2026-04-22 + 2026-04-25 Surplus-Export).
- Wenn du `Mode.EXPORT` als Patch in `_policy_drossel` umsetzt statt eigener Methode `_policy_export` — **STOP**. Audit-Trail-Klarheit (`mode='export'` im Log) ist non-verhandelbar (CLAUDE.md aktualisiert).
- Wenn du eine neue SQL-Migration **anders** als 004 nummerierst (z. B. 004a, 005, …) — **STOP**. Lückenlose Nummerierung ist CI-Gate 4.
- Wenn du die SQL-Migration **ohne Recreate-Pattern** versuchst (`ALTER TABLE ... ALTER CONSTRAINT`) — **STOP**. SQLite kennt das nicht; Migration scheitert.
- Wenn du den Toggle global in `meta`-Tabelle ablegst statt pro WR in `device.config_json.allow_surplus_export` — **STOP**. Mixed-Setups müssen unabhängig schaltbar sein.
- Wenn du `allow_surplus_export = true` ohne `max_limit_w`-Validierung akzeptierst — **STOP**. `_policy_export` kennt sonst den Ziel-Wert nicht (AC 4 + 19).
- Wenn du `_evaluate_mode_switch` zur async-Function machst, weil du Toggle aus DB lesen willst — **STOP**. Toggle wird aus `wr_limit_device.config_json` gelesen (Pure, kein DB-Read). 3.5 AC 17 Pure-Function-Disziplin.
- Wenn du den PATCH-Endpunkt **ohne** License-Gate exposed — **STOP**. Konfigurations-Mutationen sind hinter dem Gate (analog zu `/api/v1/devices` POST).
- Wenn du PATCH **vollständig replace** (`config_json = body.json()`) statt partial-merge — **STOP**. AC 22 Datenverlust-Schutz.
- Wenn du separate EXPORT-Hysterese-Konstanten (`MODE_SWITCH_EXPORT_HIGH_SOC_PCT` etc.) einführst — **STOP**. 97/93 % aus 3.5 wiederverwenden (Scope-Tension oben).
- Wenn du den Initial-Selector `select_initial_mode` so erweitest, dass er EXPORT als Auto-Detect zurückgeben kann — **STOP**. EXPORT ist Hysterese-State, kein Setup-Mode (AC 29).
- Wenn du im EXPORT-Mode den Pool weiter lädst (z. B. `_policy_speicher`-Decisions zusätzlich produzierst) — **STOP**. EXPORT setzt nur das WR-Limit; Pool-Logik ist suspendiert. MULTI ist ein anderer Mode.
- Wenn du `_policy_export` async machst — **STOP**. Synchron, gleiches Pattern wie `_policy_drossel` / `_policy_speicher`.
- Wenn du den `_mode_baseline`-Wert beim EXPORT-Switch änderst — **STOP**. Baseline ist Setup-immutable (3.5 AC 5); EXPORT verändert ihn nicht. Bei EXPORT → SPEICHER kehrt der Mode auf den Baseline-Wert zurück, der weiterhin auf den Setup-Mode zeigt.
- Wenn du das Toggle-Read im Hot-Path aufwendig cacht (z. B. Redis-Layer) — **STOP**. `device.config().get('allow_surplus_export')` ist sub-µs (Dict-Lookup nach JSON-Parse, einmal pro Sensor-Event). Kein Caching nötig.
- Wenn du `print(...)` statt `_logger` verwendest — **STOP**. CLAUDE.md Regel 5.

### Architecture Compliance (5 harte Regeln aus CLAUDE.md)

1. **snake_case überall:** Alle neuen Symbole (`_policy_export`, `_wr_allow_surplus_export`, `Mode.EXPORT.value == "export"`, `allow_surplus_export`-Key in JSON, `004_mode_export.sql`) sind `snake_case` / `lower_snake_case`. API-JSON-Felder: `allow_surplus_export`, `max_limit_w` — alle snake_case.
2. **Ein Python-Modul pro Adapter:** Nicht direkt anwendbar — 3.8 berührt keinen Adapter. Mono-Modul-Prinzip zieht analog: `_policy_export` lebt am Controller in [controller.py](../../backend/src/solalex/controller.py), kein Submodul.
3. **Closed-Loop-Readback:** EXPORT-Decisions durchlaufen die normale Veto-Kaskade + Readback im Executor (`set_limit`-Command-Kind, gleiche Behandlung wie Drossel-Decisions). Kein Bypass.
4. **JSON-Responses ohne Wrapper:** PATCH-Endpunkt liefert direkt `DeviceResponse`-Objekt (kein `{data: ..., success: true}`-Wrapper). Fehler folgen RFC 7807 (`application/problem+json`) — FastAPI-Middleware konvertiert automatisch.
5. **Logging via `get_logger(__name__)`:** Alle neuen Logs nutzen `_logger`. `_logger.warning('policy_export_max_limit_missing', ...)` (AC 4), `_logger.info('mode_switch', extra={...})` (Audit-Pattern aus 3.5, unverändert). Kein `print`, kein `logging.getLogger`.

### Library & Framework Requirements

- **Keine neuen Dependencies.** Alle Bausteine aus stdlib (`json` für config_json-Parse, `enum.StrEnum` für Mode-Erweiterung, `typing.Literal` für Whitelist-Type).
- **Python 3.13** (`pyproject.toml` unverändert).
- **Pydantic v2** (`model_config = ConfigDict(extra="forbid")`) — bereits Projekt-Standard.
- **FastAPI** für PATCH-Endpunkt — Standard-Pattern (`@router.patch(...)`, `Depends(...)`).
- **SQLite** Recreate-Pattern für Migration 004 — kein neues Tool.
- **Svelte 5 Runes** (`$state`, `$derived`) für Frontend-Toggle — bereits Projekt-Standard (Story 2.1).
- **Vitest** + **@testing-library** für Frontend-Tests — bereits Projekt-Standard (Story 2.3a Test-Stack-Ausbau).

### File Structure Requirements

- **Mode-Logik im Controller-Modul** (Mono-Modul, Cut 9). Kein `controller/export.py`, kein `policies/`-Verzeichnis.
- **`_policy_export` als Methode am Controller** — analog zu `_policy_drossel`, `_policy_speicher`, `_policy_multi`.
- **`_wr_allow_surplus_export` als private Methode am Controller** — Pure, ohne Parameter (außer `self`).
- **PATCH-Endpunkt in `api/routes/devices.py`** — kein neuer Router-File; das Routing-Pattern aus existierendem `GET /` und `POST /` wird wiederverwendet.
- **Pydantic-Schema in `api/schemas/devices.py`** — analog zu existierendem `HardwareConfigRequest`.
- **SQL-Migration in `persistence/sql/004_mode_export.sql`** — lückenlose Nummerierung nach `003_adapter_key_rename.sql`.
- **Test-Files spiegeln Source-Pfade:** alle 6 neuen Test-Files unter `backend/tests/unit/`.
- **Frontend-Toggle in `routes/Config.svelte`** — kein neuer Route, keine Sub-Komponente. Toggle ist ein Block innerhalb des bestehenden WR-Device-Tile-Renders.
- **Mode-Label-Mapping in `routes/Running.svelte`** — kein neuer Mapping-Helper, Inline-Erweiterung des existierenden.

### Testing Requirements

- **Pytest + pytest-asyncio + MyPy strict + Ruff** — alle 4 CI-Gates grün.
- **Coverage ≥ 90 %** auf allen Änderungen in `controller.py`.
- **Vitest + @testing-library** für Frontend — bereits eingerichtet (Story 2.3a Test-Stack-Ausbau).
- **Deterministische Hysterese-Tests:** `now_fn`-Injection (aus 3.1) bestimmt den Zeitstempel. Sinus-SoC-Test (`test_export_dwell_blocks_oscillation`) iteriert über injizierte SoC-Werte am Pool-Mock und einen `now_fn`, der pro Tick um 1 s avanciert. Pattern aus 3.5 wiederverwendet.
- **Migration-Tests:** In-Memory-DB (`aiosqlite.connect(":memory:")`) mit Migrations 001+002+003+004 sequentiell anwenden, dann Insert mit `mode='export'` testen + Insert mit `mode='invalid'` testen (CHECK-Constraint-Violation erwartet).
- **PATCH-Endpunkt-Tests:** FastAPI `TestClient` (`httpx.AsyncClient`) mit In-Memory-DB. Reuse von `_api_helpers.py` (License-Gate-Mock, Disclaimer-Gate-Mock) aus 2.x-Stories.
- **Toggle-State-Tests im Frontend:** `@testing-library/svelte` `render` + `fireEvent.click` auf Checkbox; `vi.mocked(setSurplusExport).mockResolvedValue(...)` für API-Mock; assertions auf optimistisches UI + Revert.

### Previous Story Intelligence (3.5, 3.4, 3.3, 3.2, 3.1)

**Aus Story 3.5 (jüngste, höchste Relevanz — alle Hysterese-Helper aus 3.5 werden in 3.8 erweitert):**

- **`_evaluate_mode_switch` ist Pure-Function** (3.5 AC 17). 3.8 erweitert sie additiv um zwei Branches; Pure-Function-Disziplin **muss** erhalten bleiben. Toggle-Read über `_wr_allow_surplus_export` ist Pure (Field-Access auf `_wr_limit_device.config()`).
- **`_record_mode_switch_cycle` schreibt synchron Audit-Cycle** (3.5 AC 6 + 9). 3.8 nutzt diesen Pfad für EXPORT-Switch und EXPORT-Exit unverändert.
- **`_speicher_max_soc_capped`-Flag** (aus 3.4) ist die Brücke zu MULTI-Cap-Branch. 3.8 erweitert die Cap-Branch-Logik in `_policy_multi`, das Flag-Pattern bleibt identisch.
- **Mindest-Verweildauer 60 s** (3.5 AC 8) gilt **automatisch** auch für EXPORT-Switches — `_evaluate_mode_switch` prüft Dwell-Time vor jedem Branch, kein Extra-Code in 3.8.
- **`_mode_baseline`-Field** (3.5 AC 5) bleibt Setup-immutable. EXPORT-Exit returniert zum Baseline-Wert (üblicherweise SPEICHER oder MULTI). Wichtig: `_mode_baseline` wird beim EXPORT-Switch **nicht** verändert.
- **Force-Mode-Override (3.5 A1)** deaktiviert `_evaluate_mode_switch` per Early-Return. EXPORT-Switch ist davon **automatisch** betroffen (AC 16). `forced_mode='export'` ist neuer akzeptierter Wert (AC 17).
- **`select_initial_mode` mit `forced_mode`-Parameter** (3.5 AC 29) — 3.8 nutzt diesen Pfad für `forced_mode='export'` unverändert; **keine** Erweiterung am Auto-Detect-Fall.
- **`reason='mode_switch: <old>→<new> (<detail>)'`** Format aus 3.5 wird beibehalten. EXPORT-Switch-Reason: `'mode_switch: speicher→export (pool_full_export (soc=97.5%))'`.

**Aus Story 3.4 (Speicher-Logik wird in MULTI gerufen, indirekt 3.8-relevant):**

- **`_speicher_max_soc_capped`-Flag** wird beim Cap-Eintritt auf `True` gesetzt. 3.8-`_policy_multi` liest das Flag, um zu entscheiden, ob `_policy_export` (Toggle ON) oder `_policy_drossel` (Toggle OFF) als Cap-Fallback gerufen wird.
- **`_policy_speicher` ist Methode am Controller, ruft `pool.get_soc(state_cache)`** — nicht direkt von 3.8 modifiziert, aber Cap-Flag-Setzung ist Voraussetzung für 3.8-MULTI-Cap-Branch.

**Aus Story 3.3 (Pool-Konsum):**

- **`pool.get_soc(state_cache).aggregated_pct`** liefert den SoC-Wert für Hysterese-Schwelle. 3.8 nutzt das in `_evaluate_mode_switch`-Erweiterung; bei `None` (alle Pool-Members offline) → kein Mode-Switch (3.5-Defensive).

**Aus Story 3.2 (Drossel-Logik im MULTI):**

- **`_is_feed_in_after_smoothing(device, sensor_value_w)`** (Helper aus 3.5 für MULTI-Cap-Branch) wird in 3.8 unverändert genutzt — entscheidet, ob Pool-Voll + Einspeisung zutrifft.
- **`_drossel_buffers`-Lazy-Init** — bleibt unberührt; 3.8-`_policy_export` nutzt den Buffer **nicht** (es liest direkt `max_limit_w` aus config_json).

**Aus Story 3.1 (Foundation):**

- **`Mode`-Enum + `set_mode`-API + `current_mode`-Property** — fertig. 3.8 erweitert nur um EXPORT-Wert.
- **`_dispatch_by_mode`-`match`-Block** — 3.8 ergänzt einen `case Mode.EXPORT:`-Branch.
- **`_safe_dispatch` + Per-Device-Lock** — multiplexieren sich automatisch über die EXPORT-Decisions; `device_id` ist `wr_limit_device.id`, also gleicher Lock wie für DROSSEL-Decisions.
- **`now_fn`-Injection** — der Hysterese-Helper nutzt `now=self._now_fn()` weiterhin für Dwell-Time-Tracking.
- **`_record_noop_cycle`-Pattern** — Audit-Cycles aus 3.5 folgen demselben Pattern; 3.8 nutzt den Pfad unverändert.

**Aus Story 2.4 (Generic-Adapter-Refit, 2026-04-25):**

- **`device.config_json`-Override-Schema** ist die Grundlage für `allow_surplus_export`. Schema bleibt forward-compatible (zusätzliche Keys sind erlaubt).
- **`config()`-Method auf `DeviceRecord`** (Zeile 150 in `adapters/base.py`): `json.loads(self.config_json)`. 3.8 nutzt diese unverändert.
- **`max_limit_w` ist bereits im 2.4-Schema** vorgesehen (Default `3000`); 3.8 nutzt es als Ziel-Wert für `_policy_export`.
- **Kein UI-Override für config_json-Keys in v1** (außer min_soc/max_soc in Wizard) — 3.8 bricht das Pattern minimal: der `allow_surplus_export`-Toggle ist der **erste** UI-exposable Override-Key. Begründung: Beta-Launch-Block (siehe SCP).

**Aus Story 5.1a (Live-Betriebs-View, Heartbeat-Pattern):**

- **`state_cache.update_mode(...)` Heartbeat** wird beim Mode-Switch automatisch aufgerufen (durch `_record_mode_switch_cycle`). 3.8 erweitert `state_cache.ModeValue`-Whitelist um `'export'`; Polling-Endpoint zeigt EXPORT-Mode automatisch.
- **`/api/v1/control/state`-Polling-Payload** enthält `current_mode`-Field; Frontend liest und rendert. Label-Mapping in `Running.svelte` ergänzt 'export' → 'Einspeisung'.

### Git Intelligence Summary

**Letzte 5 Commits (chronologisch, neueste zuerst):**

- `59aba38 chore(release): beta 0.1.1-beta.8` — Sync-Release.
- `65d675e feat(4.0a): Diagnose-Schnellexport (DB-Dump + Logs als ZIP) + Code-Review-Patches` — Story 4.0a abgeschlossen.
- `21b0306 fix(4.0): code-review patches` — Logging-Pattern verschärft (sanitize, isEnabledFor-Guards). 3.8 nutzt `_logger.warning` und `_logger.info` analog.
- `1a22d8f fix(2.4): code-review patches — config_json validation, kW/input_number setup endpoint, UI limit-range overrides` — **direkt relevant für 3.8**: PATCH-Endpunkt-Validierung folgt dem 2.4-Pattern (Pydantic `Field(ge=...)`-Validierung, `extra="forbid"`).
- `91c7f6f feat(2.4): Generic-Adapter-Refit` — `device.config_json`-Override-Schema etabliert; 3.8 baut darauf auf.

**Relevante Code-Patterns aus den Commits:**

- **`device.config_json`-Validation aus 2.4-Patches:** `DrosselParams.__post_init__` validiert hart bei Override-Lesen (fail loud). 3.8-PATCH-Validierung folgt: `allow_surplus_export = true` ohne `max_limit_w` → 422.
- **`controller_cycle_decision`-DEBUG-Record (4.0)** — 3.8 sollte `controller_policy_export_decision`-DEBUG-Record analog hinzufügen, ist **nicht verpflichtend** (Audit-Info-Log + Cycle reichen).
- **`_record_mode_switch_cycle` synchroner Audit-Pattern (3.5)** — 3.8 nutzt unverändert für EXPORT-Switches.

### Latest Tech Information

- **Python 3.13 `match`-Statement** in `_dispatch_by_mode` ist bereits idiomatic. 3.8 ergänzt einen `case Mode.EXPORT:`-Branch — `assert_never(mode)` am Ende prüft Exhaustiveness automatisch.
- **`StrEnum` (Python 3.11+)** unterstützt `Mode.EXPORT.value == "export"` direkt (lowercase Value).
- **SQLite Recreate-Pattern** ist die kanonische Methode für CHECK-Constraint-Updates seit SQLite 3.x. Indexe müssen nach `RENAME` neu erstellt werden (gehen nicht mit der Tabelle automatisch mit).
- **Pydantic v2 `model_config = ConfigDict(extra="forbid")`** ist die Projekt-Standard für strikte Schemas.
- **Svelte 5 Runes (`$state`, `$derived`, `$effect`)** sind Projekt-Standard seit Story 2.1; 3.8 nutzt `$state` für Toggle-State und `$derived` für `hasMaxLimit`-Bedingung.
- **FastAPI `@router.patch`** ist Standard-Pattern; partial-merge-Semantik wird im Handler-Body implementiert (Pydantic kann's nicht automatisch).

### Project Context Reference

Kein `project-context.md` in diesem Repo. Referenz-Dokumente sind die oben verlinkten `prd.md`, `architecture.md` (mit Amendment 2026-04-25 Surplus-Export), `epics.md` (mit Story 3.8), `CLAUDE.md` (mit aktualisierten Stop-Signalen), `sprint-change-proposal-2026-04-25-surplus-export.md`, sowie Vor-Stories 3.1 / 3.2 / 3.3 / 3.4 / 3.5 / 2.4 / 5.1a.

### Hysterese-Verhaltens-Matrix mit Surplus-Export-Toggle

| Aktiver Modus | Baseline | aggregated_pct | Toggle | Dwell ok? | Aktion |
|---|---|---|---|---|---|
| `MULTI`     | `MULTI`     | beliebig | beliebig | – | Kein Switch (3.5 AC 7); MULTI internalisiert Cap-Logik via `_policy_multi` |
| `SPEICHER`  | `SPEICHER`  | `≥ 97 %` | **OFF**  | ja | Switch → `DROSSEL` (3.5 unverändert) |
| `SPEICHER`  | `SPEICHER`  | `≥ 97 %` | **ON**   | ja | **Switch → `EXPORT`** (3.8 NEU), Audit-Cycle |
| `SPEICHER`  | `SPEICHER`  | `≥ 97 %` | beliebig | nein | Kein Switch (3.5 Dwell-Block) |
| `EXPORT`    | `SPEICHER`  | `≤ 93 %` | beliebig | ja | **Switch → `SPEICHER`** (3.8 NEU; Toggle-Wert irrelevant beim Exit) |
| `EXPORT`    | `MULTI`     | `≤ 93 %` | beliebig | ja | **Switch → `MULTI`** (3.8 NEU; theoretischer Fall — siehe MULTI-Matrix unten) |
| `EXPORT`    | beliebig    | `> 93 %` und `< 97 %` | – | – | Kein Switch (Hysterese-Mitte) |
| `DROSSEL`   | `SPEICHER`  | `≤ 93 %` | beliebig | ja | Switch → `SPEICHER` (3.5 unverändert) |
| `DROSSEL`   | `DROSSEL`   | `≤ 93 %` | – | – | Kein Switch (3.5 AC 5 — Baseline blockt) |

**Wichtig:** Toggle-Wert wird **nur** beim SPEICHER → EXPORT-Eintritt geprüft. EXPORT-Exit prüft nur SoC; Toggle-Änderung während aktivem EXPORT bewirkt **keinen** sofortigen Exit (Mode bleibt EXPORT bis Pool-SoC ≤ 93 %).

### MULTI-Cap-Branch-Entscheidungs-Tabelle mit Surplus-Export-Toggle

| `aggregated_pct` | Smart-Meter `smoothed` | `_speicher_max_soc_capped` | Toggle | MULTI-Output |
|---|---|---|---|---|
| `< max_soc`, `> min_soc` | `< -deadband` (Einspeisung) | – | beliebig | `[N Pool-Decisions]` (Speicher-only) |
| `< max_soc`, `> min_soc` | `> deadband` (Bezug) | – | beliebig | `[N Pool-Decisions]` (Entlade) |
| `>= max_soc` | `< -deadband` (Einspeisung) | `True` | **OFF** | `[Drossel-Decision]` (3.5 unverändert) |
| `>= max_soc` | `< -deadband` (Einspeisung) | `True` | **ON**  | **`[Export-Decision]`** (3.8 NEU — Pool voll + einspeisen) |
| `>= max_soc` | `> deadband` (Bezug) | `True` | beliebig | `[]` (3.8 AC 10 — Bezug-Symmetrie, kein Surplus zu exportieren) |
| `<= min_soc` | `> deadband` (Bezug) | – | beliebig | `[]` (3.5 AC 3 — Min-SoC-Cap) |

**MULTI bleibt MULTI** — kein Mode-Switch, nur Cap-Branch-Routing-Änderung.

### Anti-Patterns & Gotchas

- **KEIN Mode-Switch zu DROSSEL bei EXPORT-Exit.** EXPORT exit immer zum Baseline-Mode (üblicherweise SPEICHER). Würde EXPORT → DROSSEL wechseln, gäbe es einen Mehrfach-Switch DROSSEL → SPEICHER → EXPORT bei nächster Pool-Ladung — vermeidbarer Audit-Spam.
- **KEIN Toggle-Read im `_policy_export` selbst.** Der Toggle-Check geschieht in `_evaluate_mode_switch` und `_policy_multi`-Cap-Branch. `_policy_export` wird nur aufgerufen, wenn der Toggle ON war (oder Mode bereits EXPORT) — Doppel-Check wäre redundant.
- **KEIN sofortiger Mode-Switch bei Toggle-Änderung.** PATCH-Handler darf `controller.evaluate_mode_switch_now()` o. ä. **nicht** rufen. Nächster Sensor-Event triggert die Re-Evaluierung (AC 27).
- **KEIN Schreibbefehl bei `current == max_limit_w`.** `_policy_export` muss no-op sein, wenn das Limit bereits am Hardware-Max ist (AC 3). Sonst schreibt der Executor jede Sekunde redundant — verstößt gegen Rate-Limit (3.1) und EEPROM-Schutz (FR19).
- **KEINE neue Migration ohne Recreate-Pattern.** SQLite kennt kein `ALTER TABLE … ALTER CONSTRAINT`; CHECK-Constraint-Update zwingt zur Recreate-Sequenz.
- **KEIN Cap-Flag-Reset im EXPORT-Branch von `_evaluate_mode_switch`.** Der Reset passiert in `_record_mode_switch_cycle` (3.5 AC 12) bei jedem Switch — unverändert. EXPORT-Switch löst denselben Reset aus.
- **KEIN Auto-Detect von EXPORT in `select_initial_mode`.** EXPORT ist Hysterese-State, nicht Setup-Mode (AC 29). `forced_mode='export'` ist die einzige Ausnahme (User-Override).
- **KEIN Logging des Toggle-State auf `info` jedes Sensor-Events.** Nur beim tatsächlichen Mode-Switch (`_logger.info('mode_switch', ...)` aus 3.5).
- **KEIN Replace des kompletten `config_json` im PATCH-Handler.** Partial-merge ist non-verhandelbar (AC 22 — Schutz vor Datenverlust durch Frontend-Schema-Drift).
- **KEINE Frontend-Cache-Invalidierung der Polling-Daten nach PATCH.** Polling-Endpoint zeigt eh keinen `forced_mode`-/Toggle-State (siehe 3.5 AC 32-Begründung); der nächste Polling-Cycle reflektiert ggf. einen Mode-Switch automatisch.

### Source Tree — Zielzustand nach Story

```
backend/src/solalex/
├── controller.py                                 [MOD — Mode.EXPORT, _policy_export, _wr_allow_surplus_export, _evaluate_mode_switch-Branches, _policy_multi-Cap-Erweiterung, _dispatch_by_mode-Branch]
├── state_cache.py                                [MOD — ModeValue + Whitelist um 'export']
├── battery_pool.py                               [unverändert]
├── adapters/                                     [unverändert]
├── executor/                                     [unverändert — Veto-Kaskade akzeptiert mode='export']
├── persistence/
│   ├── sql/
│   │   ├── 001_initial.sql                       [unverändert]
│   │   ├── 002_control_cycles_latency.sql        [unverändert]
│   │   ├── 003_adapter_key_rename.sql            [unverändert]
│   │   └── 004_mode_export.sql                   [NEW — CHECK-Constraint Recreate]
│   └── repositories/
│       └── control_cycles.py                     [unverändert — accept mode='export']
├── api/
│   ├── routes/
│   │   ├── devices.py                            [MOD — PATCH /{id}/config Endpunkt]
│   │   └── control.py                            [unverändert]
│   └── schemas/
│       ├── devices.py                            [MOD — DeviceConfigPatchRequest]
│       └── control.py                            [MOD — ForcedModeRequest Literal um "export"]
├── kpi/                                          [unverändert]
├── main.py                                       [unverändert]
└── common/                                       [unverändert]

backend/tests/unit/
├── test_controller_policy_export.py              [NEW — 7 Tests]
├── test_controller_mode_switch_export.py         [NEW — 11 Tests]
├── test_controller_multi_export.py               [NEW — 3 Tests]
├── test_controller_wr_allow_surplus_export.py    [NEW — 4 Tests]
├── test_state_cache_export_mode.py               [NEW — 2 Tests]
├── test_migration_004_export_mode.py             [NEW — 4 Tests]
└── test_api_devices_patch_config.py              [NEW — 7 Tests]

frontend/src/
├── routes/
│   ├── Config.svelte                             [MOD — Surplus-Toggle pro WR-Tile]
│   ├── Running.svelte                            [MOD — Label-Mapping 'export' → 'Einspeisung']
│   └── ...                                       [unverändert]
├── lib/
│   ├── api/
│   │   ├── client.ts                             [MOD — setSurplusExport-Funktion]
│   │   └── types.ts                              [MOD — Mode-Type um 'export']
│   └── ...                                       [unverändert]

frontend/src/routes/
├── Config.test.ts                                [MOD — 5 neue Tests]
└── Running.test.ts                               [MOD — 1 neuer Test]

frontend/src/lib/api/
└── client.test.ts                                [MOD — 2 neue Tests]
```

### Beta-Gate-Bezug

**Aus Sprint Change Proposal 2026-04-25 Surplus-Export §1:** Klasse-2-User („Eigenverbrauchs-Maximierer mit angemeldeter Anlage") ist die DACH-Mehrheit. Ohne Surplus-Export verlieren sie im Sommer signifikante PV-Energie (1–3 kWh/Tag) durch Abregelung am MPPT. Das Add-on bekommt unweigerlich „regelt mir die Sonne weg"-Wahrnehmung — Beta-Launch-blocking.

**Empirie-Verifikation (analog zu 3.5):** Der 24-h-Dauertest (Story 3.7) sollte einen Test-Zyklus mit aktiviertem Surplus-Export enthalten, um zu verifizieren, dass `mode='export'`-Cycles korrekt persistiert werden und keine Schwingungen auftreten.

### Performance & Sicherheit

- **NFR2 (Cycle-Latenz ≤ 1 s):** `_policy_export` ist sub-µs (Dict-Lookup + int-Konvertierung). `_evaluate_mode_switch`-Erweiterung addiert einen Toggle-Read (sub-µs). Audit-Cycle-Persist (~5 ms) fällt nur beim tatsächlichen Mode-Switch an, nicht bei jedem Sensor-Event.
- **Safety:** EXPORT-Decision wird vom Executor wie jede andere Decision behandelt — Range-Check (max_limit_w muss in `[min_limit_w, hardware_max]` liegen, AdapterBase-Logik aus 2.4), Rate-Limit (60 s pro Device), Readback (Closed-Loop mit Timeout). Bei Range-Verletzung (z. B. `max_limit_w` ist über `adapter.get_limit_range(device).max`) → Veto, kein Hardware-Schreibbefehl.
- **Concurrency:** Per-Device-Locks aus 3.1 sind unbeeinflusst. `_policy_export` produziert eine Decision auf dem `wr_limit_device.id` — gleicher Lock wie Drossel, also keine Race-Condition.
- **Audit-Trail:** Jeder EXPORT-Switch produziert genau einen `control_cycles`-Row mit `readback_status='noop'` + `reason='mode_switch: …'`. Story 4.5 (Diagnose-Export) sieht den neuen Mode-Wert ohne Adapter-Änderung.
- **Backward-Compatibility:** Vor-Migrations (001+002+003) bleiben unverändert. Nach Migration 004 sind alle bisherigen Rows preserved (INSERT…SELECT). Default-Verhalten ohne Toggle-Aktivierung = Status-quo (DROSSEL bei Pool-Voll).

### Scope-Grenzen zur Folge-Story (3.6, 3.7, 5.5)

- **Story 3.6 (User-Config — Min/Max-SoC + Nacht-Entlade):** unverändert. Der Surplus-Export-Toggle ist **nicht** Teil von 3.6's User-Config-UI — er sitzt **pro WR** (in 3.8) und nicht im allgemeinen User-Settings-Tab. Begründung: Toggle ist hardware-spezifisch (an einem WR sinnvoll, am anderen nicht — Mixed-Setups).
- **Story 3.7 (Fail-Safe + 24-h-Dauertest):** Recovery + Health-Marker. EXPORT-Mode im Fail-Safe-Zustand (`ha_ws_disconnected`) verhält sich wie alle anderen Modi — keine neuen Decisions, letzte WR-Limit-Wert (Hardware-Max) bleibt gehalten. Bei Recovery läuft der nächste Sensor-Event normal mit EXPORT-Mode durch.
- **Story 5.5 (Mode-Chip + Energy-Ring-Animation):** Frontend-Animation. 3.8 schreibt `state_cache.current_mode='export'` und Audit-Cycle; 5.5 verdrahtet das UI mit einer EXPORT-spezifischen Animation (vermutlich „Sonne strahlt nach außen"-Gestik). Story 5.5-Scope erweitert sich um den 4. Mode.

### Deferred (out-of-scope for 3.8, documented for v1.5+/v2)

- **Per-WR Hysterese-Schwellen für EXPORT** (`device.config_json.export_high_soc_pct`, `export_low_soc_pct`): v1.5. v1 nutzt globale 97/93 %.
- **Spotpreis-gesteuerter Export** (Tibber-Integration): v2. Externe Daten, neue Dependency, neue Failure-Modes.
- **EXPORT-Mode-Latenz-Messung** (im `latency_measurements`-Sinne): v2. 3.8 misst nichts spezifisch für EXPORT — die Standard-Latenz-Messung greift unverändert.
- **UI-Override für Hardware-Max-Limit** (Wizard-Sektion „Erweiterte Einstellungen" für `max_limit_w`-Editierung): v1.5. v1 setzt `max_limit_w` per Wizard-Step (Story 2.4-Refit) oder direktem PATCH-Call.
- **Mode-Switch-Visualisierung im Diagnose-Tab** (4.1): v1 zeigt `mode='export'`-Cycles im Standard-Cycles-Tab; spezifische EXPORT-Visualisierung kommt in 4.1.
- **Multi-Pool-Surplus-Routing** (mehrere Pools nebeneinander, z. B. Marstek + Anker mit unterschiedlichen Toggle-Settings): v1.5. v1 betrachtet einen Pool.
- **Auto-Recommendation für Toggle-Aktivierung** („Solalex hat 5 Tage in Folge bei Pool-Voll abgeregelt — möchtest du Surplus-Einspeisung aktivieren?"): v2. UX-Idee, kein Tech-Block.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

### Completion Notes List

### File List

### References

- [Sprint Change Proposal 2026-04-25 Surplus-Export](../planning-artifacts/sprint-change-proposal-2026-04-25-surplus-export.md) — **Pflichtlektüre**
- [architecture.md — Amendment 2026-04-25 Surplus-Export](../planning-artifacts/architecture.md)
- [architecture.md — Amendment 2026-04-25 Generic-Adapter (config_json-Schema-Basis)](../planning-artifacts/architecture.md)
- [architecture.md — Core Architectural Decisions Zeile 230–262 + Project Structure + Amendment-Log](../planning-artifacts/architecture.md)
- [prd.md — FR16 + FR16a (Amendment 2026-04-25 Surplus-Export)](../planning-artifacts/prd.md)
- [epics.md — Story 3.8](../planning-artifacts/epics.md)
- [CLAUDE.md — 5 harte Regeln + Stolpersteine (mit aktualisierten Stop-Signalen für EXPORT)](../../CLAUDE.md)
- [Story 3.1 — Core Controller (Mode-Enum, set_mode, _dispatch_by_mode)](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md)
- [Story 3.2 — Drossel-Policy (`_policy_drossel` referenziert in MULTI-Cap-Branch ohne Toggle)](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md)
- [Story 3.3 — BatteryPool API (`get_soc`, `aggregated_pct`)](./3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation.md)
- [Story 3.4 — Speicher-Policy + Cap-Flag-Pattern (Brücke zu MULTI-Cap-Branch)](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md)
- [Story 3.5 — Adaptive Strategie + Hysterese + MULTI + Force-Mode-Override (A1)](./3-5-adaptive-strategie-auswahl-hysterese-basierter-modus-wechsel-inkl-multi-modus.md) — **Pflichtlektüre**
- [Story 2.4 — Generic-Adapter-Refit + `device.config_json`-Override-Schema](./2-4-generic-adapter-refit.md)
- [Story 5.1a — `state_cache.update_mode`-Heartbeat](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md)
- [controller.py — Mode-Enum, `_dispatch_by_mode`, `_policy_drossel`, `_policy_speicher`, `_policy_multi`](../../backend/src/solalex/controller.py)
- [state_cache.py — ModeValue, update_mode-Whitelist](../../backend/src/solalex/state_cache.py)
- [adapters/base.py — DeviceRecord.config()-Method](../../backend/src/solalex/adapters/base.py)
- [api/routes/devices.py — existing GET/POST routes (Pattern für PATCH)](../../backend/src/solalex/api/routes/devices.py)
- [persistence/sql/002_control_cycles_latency.sql — CHECK-Constraint-Vorbild für Migration 004](../../backend/src/solalex/persistence/sql/002_control_cycles_latency.sql)
- [persistence/sql/003_adapter_key_rename.sql — Migration-Vorbild für Forward-only-Pattern](../../backend/src/solalex/persistence/sql/003_adapter_key_rename.sql)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.8 erstellt und auf `ready-for-dev` gesetzt. Surplus-Export-Mode bei Akku-Voll als opt-in pro WR via `device.config_json.allow_surplus_export`. Mode-Enum von 3-fach auf 4-fach erweitert (`Mode.EXPORT = "export"`); SQL-Migration 004 erweitert CHECK-Constraint auf `control_cycles.mode` + `latency_measurements.mode` um `'export'` (SQLite-Recreate-Pattern); neuer `_policy_export` als Methode am Mono-Modul-Controller (setzt WR-Limit auf `device.config_json.max_limit_w`); `_evaluate_mode_switch` (3.5) erweitert um SPEICHER → EXPORT-Branch mit Toggle-ON-Check und EXPORT → baseline-Branch bei SoC ≤ 93 %; `_policy_multi` Cap-Branch ruft `_policy_export` statt `_policy_drossel` mit Toggle ON; PATCH-Endpunkt `PATCH /api/v1/devices/{id}/config` mit Pydantic `DeviceConfigPatchRequest`-Schema (`extra="forbid"`, partial-merge auf config_json, Validierung `allow_surplus_export → max_limit_w required`); Frontend-Toggle pro WR-Tile in Config.svelte mit Inline-Hint bei fehlendem max_limit_w + Auto-PUT-Pattern; Running.svelte Label-Mapping `'export'` → „Einspeisung"; `state_cache.ModeValue`-Whitelist erweitert. Default-Verhalten preserve (Toggle OFF = Status-quo aus 3.5). 28+ Backend-Tests in 7 neuen Files + 8 Frontend-Tests in 3 erweiterten Files. Pattern-Reuse aus Story 3.5 (Hysterese-Helper, Audit-Cycle, Force-Mode-Override-Integration), Story 3.4 (Cap-Flag-Brücke), Story 2.4 (config_json-Override-Schema, Pydantic-Validation), Story 3.1 (`_record_noop_cycle`-Pattern). Beta-Launch-blocking. Architektur-Bezug: Sprint Change Proposal 2026-04-25-surplus-export + Architecture-Amendment 2026-04-25 (Surplus-Export). | Claude Opus 4.7 |
