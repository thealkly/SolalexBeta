# Story 3.3: Akku-Pool-Abstraktion mit Gleichverteilung & SoC-Aggregation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Marstek-Micha mit ≥ 1 Marstek Venus 3E/D (Kernsegment),
I want dass Solalex meine Akkus intern als logischen Pool behandelt mit Gleichverteilung in v1 und aggregiertem SoC-Wert,
so that ich keine Multi-Akku-Komplexität im UI sehe und der Pool wie ein einziger Speicher reagiert.

**Scope-Pflock:** Diese Story liefert eine **reine Abstraktions-Schicht** (`backend/src/solalex/battery_pool.py`) plus zwei kleine Adapter-/Lifespan-Andockungen. Sie **verdrahtet nichts** in den Controller — der Pool ist in 3.3 ein dormanter Baustein, den Story 3.4 (Speicher-Modus) konsumiert. `Mode.SPEICHER` und `Mode.MULTI` bleiben Noop-Stubs (`_policy_speicher_stub`, `_policy_multi_stub` aus 3.1/3.2 unverändert). Alle Safety-Gates im Executor (Range → Rate-Limit → Readback → Fail-Safe) laufen unverändert durch die Executor-Dispatch-Kette aus Story 3.1 — der Pool baut nur `PolicyDecision`-Listen, er ruft **nie** selbst `ha_client.call_service`.

**Scope-Tension PRD-Zeile 223 vs. Epic-AC-Formulierung (aufgelöst):** PRD v1-Scope ist „1 WR + 1 SM + 1 Akku pro Instanz" (Zeile 223). Der heutige Wizard aus Story 2.1 persistiert exakt **einen** Akku pro Install (1 Zeile `role='wr_charge'` + optional 1 Zeile `role='battery_soc'`; `entity_id`-Prefix-Paarung; `config_json` trägt `min_soc`/`max_soc`/`night_*`). Die Epic-AC „Pool-Setpoint auf 2 Akkus verteilen" bleibt im **Abstraktions-Interface** vollständig erfüllt (N ≥ 1 Member) — der produktive Multi-Akku-Flow (Marstek-Micha-2×-Venus) wird durch eine Wizard-Erweiterung in v1.5 frei­geschaltet (siehe „Deferred" unten). 3.3 baut die Infrastruktur, sie ist **pool-of-1-first** und **multi-ready**.

**Amendment 2026-04-22 (verbindlich):** Pool lebt als **ein Python-Modul** `backend/src/solalex/battery_pool.py`, **kein** Unter-Verzeichnis `pool/`, **keine** JSON-Template-Konfiguration, **kein** externes File-Laden. Kapazität pro Member stammt aus `AdapterBase.get_default_capacity_wh()` (Adapter-Modul-Konstante, überschreibbar via `device.config_json.capacity_wh`). Kein Event-Bus, keine `asyncio.Queue` — die Pool-API ist synchron-pur (keine IO im Pool-Code, `set_setpoint` produziert `PolicyDecision`-Listen, Dispatch bleibt Executor-Aufgabe).

## Acceptance Criteria

1. **Pool-Konstruktion aus Devices-Tabelle (FR21, Epic-AC 1):** `Given` mindestens ein commissionierter Device-Row mit `role='wr_charge'` in der `devices`-Tabelle existiert, `When` `BatteryPool.from_devices(devices, adapter_registry)` in `main.py::lifespan` nach DB-Migration und Device-Load aufgerufen wird, `Then` liefert der Klassen-Konstruktor einen `BatteryPool` mit `len(pool.members) >= 1`, **And** jeder `PoolMember` bündelt genau einen `charge_device` (`role='wr_charge'`) und **optional** einen `soc_device` (`role='battery_soc'`) per **entity-ID-Prefix-Matching** (strip bekannter Suffixe: `_charge_power`, `_soc`, `_battery_soc`), **And** bei null commissionierten Battery-Devices liefert die Factory `None` — die Lifespan hängt dann `app.state.battery_pool = None` an (Pool-of-0 ist in v1 kein gültiger Zustand; Controller fragt vor Nutzung auf `is not None`).

2. **Gleichverteilungs-Setpoint (FR21, Epic-AC 2):** `Given` ein Pool mit N ≥ 1 Online-Members (alle mit gültigem `state_cache`-Eintrag) und ein Setpoint `watts: int`, `When` `pool.set_setpoint(watts, state_cache)` aufgerufen wird, `Then` liefert die Methode **genau N `PolicyDecision`-Objekte**, jedes mit `command_kind='set_charge'`, `mode=Mode.SPEICHER`, `device=<charge_device>`, `target_value_w=watts // N` für die ersten `N - (watts % N)` Members und `target_value_w=watts // N + 1` für die restlichen (Rundungsrest wird gleichmäßig auf die ersten-N-Members verteilt, damit `sum(decisions.target_value_w) == watts`), **And** bei negativem `watts` (Entlade-Anforderung) wird die Verteilung identisch angewendet (negative Werte werden ebenfalls symmetrisch gerundet), **And** bei N=1 erhält der einzige Member den vollen Betrag (`target_value_w=watts`).

3. **SoC-Aggregation (gewichtet nach Kapazität, FR23, Epic-AC 3):** `Given` ein Pool mit ≥ 1 Members, jedes mit einem im `state_cache` geführten `soc_device`-State (numerischer Wert 0–100 %), `When` `pool.get_soc(state_cache)` abgefragt wird, `Then` liefert die Methode ein `SocBreakdown` mit **`aggregated_pct: float`** = `sum(soc_i × capacity_i) / sum(capacity_i)` (gewichteter Mittelwert nach Kapazität in Wh) und **`per_member: dict[int, float]`** = `{device.id: soc_pct}` für jeden Online-Member, **And** wenn **kein** Member online ist (alle `soc_device`-States fehlen, sind `unavailable`/`unknown` oder nicht-parsebar) liefert `get_soc` `None` statt `0.0`, **And** die Methode ruft **nie** `ha_client` oder I/O — sie liest ausschließlich den übergebenen `state_cache` (Pool ist reine In-Memory-Abstraktion).

4. **Offline-Fallback (FR21, Epic-AC 4):** `Given` ein Pool mit N ≥ 2 Members, wobei ein Member offline ist (`state_cache` hat keinen oder einen `unavailable`/`unknown`-State für sein `soc_device` **oder** sein `charge_device`), `When` `pool.set_setpoint(watts, state_cache)` oder `pool.get_soc(state_cache)` aufgerufen werden, `Then` überspringen beide Methoden den offline Member vollständig — `set_setpoint` verteilt `watts` auf die verbleibenden `N_online` Members (volle Gleichverteilung unter den Online-Members, nicht „0 W an Offline"), `get_soc` schließt den offline Member aus der Gewichtung aus, **And** wenn **alle** Members offline sind, liefert `set_setpoint` eine leere Liste `[]` (keine Exception) und `get_soc` liefert `None`, **And** die Offline-Erkennung ist purer State-Cache-Read (`last_states.get(entity_id)` None oder State in `{'unavailable','unknown','none',''}` — identisch zu den Sentinels in `controller._HA_SENSOR_SENTINELS`).

5. **Adapter-Modul-Pattern für Kommunikation (CLAUDE.md Regel 2, Epic-AC 5):** `Given` ein `PoolMember.charge_device.adapter_key == 'marstek_venus'`, `When` das Konsumenten-Pfad später (Story 3.4) eine `PolicyDecision` aus `pool.set_setpoint(...)` an den Executor dispatched, `Then` baut der Executor den HA-Service-Call **ausschließlich** über `adapter_registry['marstek_venus'].build_set_charge_command(...)` — Pool selbst importiert **keinen** vendor-spezifischen Adapter-Namen, hält **keine** vendor-spezifischen Konstanten, **And** ein Drift-Check `grep -rE "marstek_venus|hoymiles|shelly" backend/src/solalex/battery_pool.py` liefert **0 Treffer** (Pool ist hardware-agnostisch; alles Vendor-Spezifische steht im Adapter-Modul).

6. **Kapazität pro Member aus Adapter-Default, optional überschreibbar:** `Given` ein `PoolMember`, `When` die Pool-Konstruktion die Member-Kapazität bestimmt, `Then` wird die Kapazität in Reihenfolge bestimmt: (a) wenn `charge_device.config().get('capacity_wh')` existiert und eine positive int ist, nimm den Wert; (b) sonst ruft die Pool-Factory `adapter.get_default_capacity_wh(charge_device) -> int` auf dem passenden Adapter, **And** `AdapterBase.get_default_capacity_wh` hat einen **konservativen Default** (5120 Wh, Marstek-Venus-3E-Spec-Wert aus Hersteller-Datenblatt) und wirft **NICHT** `NotImplementedError` — andere Adapter (Hoymiles, Shelly) erben den Default ohne Override, weil sie nie als `wr_charge`-Role auftauchen, **And** Marstek-Venus-Adapter überschreibt `get_default_capacity_wh` explizit mit `5120` (Single-Source-of-Truth Marstek-Modul), mit One-Liner-Kommentar, der das Datenblatt referenziert.

7. **Pool-Infrastruktur in `main.py::lifespan` verdrahtet, aber NICHT im Controller konsumiert:** `Given` die FastAPI-Lifespan-Funktion, `When` der Pool-Bau-Schritt läuft, `Then` wird `BatteryPool.from_devices(...)` **einmalig** zwischen Device-Load und Controller-Instanziierung aufgerufen und das Ergebnis an `app.state.battery_pool: BatteryPool | None` gehängt, **And** `Controller(...)` wird **unverändert** (ohne `battery_pool`-Parameter) konstruiert — der Pool fließt in 3.3 nicht in den Controller; Story 3.4 ergänzt den Konstruktor-Parameter, **And** die Lifespan-Shutdown-Route (`finally`-Block) fasst den Pool **nicht** an — der Pool hat keine IO-Ressourcen, keine Tasks, kein State zum Schließen.

8. **Hot-Reload NICHT in 3.3:** `Given` ein Nutzer ändert die Device-Konfiguration zur Laufzeit via `POST /api/v1/devices`, `When` das passiert, `Then` wird `app.state.battery_pool` **nicht** automatisch neu gebaut — ein Add-on-Neustart ist erforderlich, **And** dieses Verhalten ist identisch zu `devices_by_role` aus Story 3.2 (dort auch explizit als Non-Goal gesetzt); Wizard-/Config-Page-Integration ist Epic-2-/v1.5-Scope, nicht 3.3.

9. **Nur commissionierte Devices landen im Pool:** `Given` die `devices`-Tabelle enthält Devices mit `commissioned_at IS NULL` (unkommissionierte Wizard-Halbstände), `When` `BatteryPool.from_devices(devices, ...)` läuft, `Then` werden diese Devices **rausgefiltert** bevor Pairing und Member-Bau passieren — identisch zum bestehenden `commissioned_at`-Filter in `main.py::lifespan::devices_by_role`, **And** der `POST /api/v1/setup/test`-Funktionstest aus Story 2.2 sendet weiterhin gegen den commissionierten Charge-Device, der Pool kann vor Commissioning leer sein (`app.state.battery_pool = None`).

10. **Prefix-Pairing deterministisch und robust (domain-agnostisch):** `Given` Entity-IDs `number.venus_garage_charge_power` + `sensor.venus_garage_battery_soc`, `When` die Pool-Factory sie pairt, `Then` erkennt sie denselben **object-ID-Prefix** `venus_garage` — der Algorithmus splittet den HA-Domain-Präfix ab (`number.` bzw. `sensor.`, via `entity_id.partition('.')`) und stripped dann die bekannten Suffix-Listen (`_CHARGE_SUFFIXES = ('_charge_power',)` für Charge-Devices, `_SOC_SUFFIXES = ('_battery_soc', '_soc')` für SoC-Devices, längster Suffix zuerst), **And** der Vergleich ist case-sensitive und trim-frei (HA-Entity-IDs sind per HA-Konvention bereits lowercase-snake_case), **And** wenn ein `charge_device` **keinen** Prefix-Match auf ein `battery_soc`-Device findet, wird der Member trotzdem gebaut (mit `soc_device=None`) und `get_soc` schließt ihn aus dem Aggregat aus (dokumentiert als „Pool-of-N with soc_optional"), **And** der umgekehrte Fall (ein `battery_soc` ohne passenden `wr_charge`) wird ignoriert — ein SoC-Sensor ohne Charger ist kein Pool-Member. **Beispiel-Pairing:**
    - `number.venus_keller_charge_power` + `sensor.venus_keller_soc` → prefix `venus_keller` ✓
    - `number.venus_garage_charge_power` + `sensor.venus_garage_battery_soc` → prefix `venus_garage` ✓ (längeren Suffix `_battery_soc` vor `_soc` strippen)
    - `number.solix_charge_power` ohne passendes SoC-Device → Member mit `soc_device=None` ✓

11. **Invariant-Validation — Fail-Loud bei kaputter Config (Lessons aus Story 3.2 Review P7):** `Given` `DrosselParams.__post_init__` validiert Parameter-Ranges (3.2-Pattern), `When` ein zukünftiger Adapter versehentlich `get_default_capacity_wh` mit `0` oder negativ überschreibt ODER `config_json.capacity_wh` ≤ 0 setzt, `Then` wirft der `PoolMember`-Konstruktor `ValueError(f"capacity_wh must be >= 1, got {value}")` — **keine** silent-drop, **keine** `0`-Division-Falle in `get_soc`, **And** der Unit-Test `test_pool_member_rejects_nonpositive_capacity` verifiziert das Verhalten.

12. **Defensive-Catch auf Adapter-Aufrufen (Lessons aus Story 3.2 Review P9/P10):** `Given` ein kaputter Adapter wirft aus `get_default_capacity_wh(device)`, `When` die Pool-Factory ihn aufruft, `Then` wird die Exception **nicht gecatched** — ein Adapter-Bug muss den Startup sichtbar brechen (Fail-Loud am Startup-Pfad; keine Pool-of-Silent-Defaults). Der `state_cache.last_states[entity_id].attributes`-Read im SoC-Pfad filtert Non-Dict-Attribute defensiv (`isinstance(entry.attributes, dict)`) **And** ein `float(state.state)`/`int(...)`-Parse-Fehler im SoC-Parser liefert `None` für diesen Member (keine Exception propagiert aus `get_soc`).

13. **Keine SQL-Migration, kein Schema-Change, keine neue API-Route, keine Frontend-Änderung:** `Given` der Scope-Pflock, `When` der Diff gemessen wird, `Then` existiert **keine** neue Datei unter `backend/src/solalex/persistence/sql/` (Ordering bleibt bei 2 Dateien: `001_initial.sql` + `002_control_cycles_latency.sql`), **keine** Änderung an `persistence/repositories/devices.py` oder `api/routes/*.py`, **keine** Änderung unter `frontend/src/` (Pool-Anzeige ist Epic-5-Scope für Dashboard), **And** `pyproject.toml` bleibt unverändert (keine neue Dependency — Pool nutzt stdlib `dataclasses` + bestehende Typen).

14. **Pipeline-Invariante ≤ 1 s bleibt erhalten (FR31/NFR2):** `Given` der Pool wird später von Story 3.4 aus `_policy_speicher` konsumiert, `When` `pool.set_setpoint(...)` und `pool.get_soc(...)` laufen, `Then` sind beide Methoden **synchron-pur** (kein `await`, keine IO) — Laufzeit deterministisch unter 1 ms für N ≤ 16 Members, **And** ein Micro-Benchmark-Test (optional, nicht CI-blockierend) im Test-File misst `time.perf_counter_ns()` für `set_setpoint(2000, cache)` auf N=8-Pool und asserted `< 5 ms` (großzügig, damit CI-Runner-Jitter nicht false-red wird).

15. **Unit-Tests (Pytest, MyPy strict, Ruff):** Neue Test-Datei unter `backend/tests/unit/`:
    - `test_battery_pool.py`:
      - `test_from_devices_empty_list_returns_none` (AC 1)
      - `test_from_devices_pool_of_one_marstek_venus` (AC 1 — wizard-realer Fall: 1× `wr_charge` + 1× `battery_soc`)
      - `test_from_devices_pool_of_two_paired_by_entity_prefix` (AC 1, AC 10 — 2× Marstek via DB-Hand-Edit)
      - `test_from_devices_skips_uncommissioned_devices` (AC 9 — gemischt commissioniert/nicht)
      - `test_from_devices_ignores_unpaired_battery_soc_devices` (AC 10)
      - `test_from_devices_builds_member_without_soc_device_when_only_wr_charge_exists` (AC 10)
      - `test_set_setpoint_equal_split_2_members_even_watts` (AC 2 — 1000 W / 2 → [500, 500])
      - `test_set_setpoint_equal_split_2_members_odd_watts_rest_on_second_half` (AC 2 — 1001 W / 2 → [500, 501])
      - `test_set_setpoint_equal_split_3_members_with_remainder` (AC 2 — 1000 W / 3 → [333, 333, 334])
      - `test_set_setpoint_single_member_receives_full_watts` (AC 2 — N=1, 700 W → [700])
      - `test_set_setpoint_negative_watts_symmetric_rounding` (AC 2 — -1001 W / 2 → [-500, -501] oder [-501, -500] deterministisch)
      - `test_set_setpoint_returns_empty_list_when_all_offline` (AC 4)
      - `test_set_setpoint_skips_offline_member_and_splits_full_watts_on_remaining` (AC 4 — 2 Members, 1 offline → 1-Member bekommt 100 %)
      - `test_get_soc_weighted_by_capacity` (AC 3 — 2 Members mit unterschiedlicher Kapazität)
      - `test_get_soc_equal_capacity_reduces_to_simple_mean` (AC 3 — Regression)
      - `test_get_soc_returns_none_when_all_offline` (AC 4)
      - `test_get_soc_skips_offline_members_in_weighting` (AC 4)
      - `test_get_soc_returns_per_member_breakdown` (AC 3)
      - `test_member_capacity_overridden_via_config_json` (AC 6 — `config_json.capacity_wh=3000`)
      - `test_member_capacity_falls_back_to_adapter_default` (AC 6)
      - `test_pool_member_rejects_nonpositive_capacity` (AC 11 — `ValueError`)
      - `test_pool_does_not_import_vendor_specific_constants` (AC 5 — via grep assertion in test body oder AST-Scan)
      - `test_get_soc_filters_unavailable_sentinel_states` (AC 4 — Sentinel-Liste)
      - `test_get_soc_defensive_against_non_dict_attributes` (AC 12 — pathological `HaStateEntry.attributes`)
      - `test_set_setpoint_sum_equals_input_watts` (AC 2 — Property-Test-Stil: 10 verschiedene (watts, N)-Kombinationen)
    - `test_marstek_venus_default_capacity.py`:
      - `test_marstek_adapter_default_capacity_wh_5120` (AC 6)
      - `test_adapter_base_default_capacity_wh_5120` (AC 6 — Base-Default)
    - `test_main_lifespan_battery_pool.py` (Integration-Test, kurzkonfiguriert):
      - `test_lifespan_attaches_battery_pool_to_app_state_when_marstek_commissioned` (AC 7)
      - `test_lifespan_attaches_none_when_no_battery_devices_commissioned` (AC 7, AC 1)
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf `battery_pool.py` und den zwei Methoden in `adapters/base.py` + `adapters/marstek_venus.py`, die Kapazität liefern.
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (unverändert bei 2 Dateien — **keine neue Migration in 3.3**).

## Tasks / Subtasks

- [x] **Task 1: `AdapterBase.get_default_capacity_wh()` + Marstek-Override** (AC: 6)
  - [x] `adapters/base.py`: neue Methode `def get_default_capacity_wh(self, device: DeviceRecord) -> int`. Default-Body: `return 5120` (Marstek-Venus-3E-Spec, siehe Hersteller-Datenblatt — konservativer Fallback, niemals `NotImplementedError`, niemals `0`). One-Liner-Kommentar mit Quelle.
  - [x] `adapters/marstek_venus.py`: `get_default_capacity_wh(device) -> int` explizit überschreiben mit `return 5120`. Zweck: Single-Source-of-Truth im Adapter-Modul (CLAUDE.md Regel 2). Kommentar: „Datenblatt Marstek Venus 3E, Brutto-Nennkapazität 5120 Wh. Override für Sondergrößen via `device.config_json.capacity_wh`."
  - [x] `adapters/hoymiles.py`, `adapters/shelly_3em.py`: **NICHT** überschreiben — erben den Base-Default. Nicht-Battery-Adapter werden nie als `wr_charge`-Role angefragt; der Default ist toter-Code-Proof.
  - [x] **KEIN** `NotImplementedError` im Base-Default (Lessons aus 3.2 — defensive Defaults verhindern Fail-Loud im falschen Moment; 0 oder negative Kapazität werden im `PoolMember.__post_init__` abgefangen, AC 11).

- [x] **Task 2: `battery_pool.py` — Dataclasses + Factory + Methoden** (AC: 1, 2, 3, 4, 5, 10, 11, 12, 14)
  - [x] Neue Datei `backend/src/solalex/battery_pool.py`. **Ein Modul, kein Folder.** Kein `__init__.py`-Ordner, kein `pool/`-Submodul.
  - [x] `from __future__ import annotations` + Standard-Imports (`dataclasses`, `typing.Literal`).
  - [x] Import aus der Projekt-Domäne: `DeviceRecord`, `AdapterBase` (aus `solalex.adapters.base`), `Mode` + `PolicyDecision` (aus `solalex.executor.dispatcher`), `StateCache` + `HaStateEntry` (aus `solalex.state_cache`), `get_logger` (aus `solalex.common.logging`).
  - [x] Sentinel-Konstanten:
    ```python
    _SOC_SUFFIXES: tuple[str, ...] = ("_battery_soc", "_soc")  # längster Suffix zuerst
    _CHARGE_SUFFIXES: tuple[str, ...] = ("_charge_power",)
    _OFFLINE_SENTINELS: frozenset[str] = frozenset({"unavailable", "unknown", "none", ""})
    ```
    Begründung: Die SoC-Suffix-Reihenfolge hält `_battery_soc` vor `_soc`, damit `sensor.venus_battery_soc` auf Prefix `venus` reduziert wird statt auf `venus_battery`. Die Offline-Sentinels spiegeln `controller._HA_SENSOR_SENTINELS` — beide Module halten ihre eigene Konstante, weil `battery_pool` keine Abhängigkeit auf `controller` importieren soll (Layering).
  - [x] `@dataclass(frozen=True) class PoolMember`:
    - `charge_device: DeviceRecord` (Role `wr_charge`)
    - `soc_device: DeviceRecord | None` (Role `battery_soc`; `None` wenn Prefix-Pairing fehlschlägt, AC 10)
    - `capacity_wh: int` (positive Ganzzahl)
    - `prefix: str` (dokumentarisch, für Logs und Tests)
    - `__post_init__`: wenn `capacity_wh < 1`, wirf `ValueError("capacity_wh must be >= 1, got {capacity_wh}")` (AC 11).
  - [x] `@dataclass(frozen=True) class SocBreakdown`:
    - `aggregated_pct: float` (0–100, kapazitätsgewichtet)
    - `per_member: dict[int, float]` (`device.id → soc_pct`; Offline-Members **nicht** enthalten)
  - [x] `class BatteryPool`:
    - `__init__(self, members: list[PoolMember], adapter_registry: dict[str, AdapterBase])`. Speichern, keine Side-Effects.
    - `@classmethod from_devices(cls, devices: list[DeviceRecord], adapter_registry: dict[str, AdapterBase]) -> BatteryPool | None`:
      1. Filter auf `commissioned_at is not None` (AC 9).
      2. Teile in `charge_devices` (`role == 'wr_charge'`) und `soc_devices` (`role == 'battery_soc'`).
      3. Wenn `not charge_devices`: return `None` (AC 1).
      4. Pro `charge_device`: berechne Prefix via `_object_prefix(entity_id, _CHARGE_SUFFIXES)` (strippt zuerst `"number."`-Domain, dann den Suffix). Iteriere `soc_devices`, finde ersten mit `_object_prefix(entity_id, _SOC_SUFFIXES) == prefix`. Pairing (AC 10).
      5. Bestimme Kapazität (AC 6): `config_json.get('capacity_wh')` mit `isinstance(int) and > 0` → nimm; sonst `adapter_registry[charge_device.adapter_key].get_default_capacity_wh(charge_device)`.
      6. Baue `PoolMember` (invariant-validated, AC 11).
      7. Unpaired `battery_soc`-Devices werden ignoriert (AC 10 Satz 2).
      8. Return `BatteryPool(members, adapter_registry)`.
    - `def set_setpoint(self, watts: int, state_cache: StateCache) -> list[PolicyDecision]` (AC 2, AC 4):
      1. Ermittle Online-Members: `m` ist online, wenn **sowohl** `state_cache.last_states.get(m.charge_device.entity_id)` existiert und `state.state not in _OFFLINE_SENTINELS` **als auch** (wenn `m.soc_device is not None`) analog für `soc_device.entity_id`. Begründung: Ohne gecachten Charge-State kennen wir den aktuellen Lade-Zustand nicht → kein Dispatch an diesen Member.
      2. Wenn `not online_members`: return `[]` (AC 4 Satz 2).
      3. Verteile `watts` via Integer-Division + Rest: `base, rem = divmod(watts, len(online_members))`. Erste `len(online_members) - rem` Members bekommen `base`, restliche `rem` Members bekommen `base + 1` (bei negativen `watts` liefert `divmod` das korrekte symmetrisch-gerundete Verhalten — Python-`divmod(-1001, 2) == (-501, 1)`; das funktioniert, weil `-501 * 2 + 1 == -1001`). **Invariante:** `sum(d.target_value_w for d in decisions) == watts` (AC 15 Property-Test).
      4. Für jeden Online-Member baue `PolicyDecision(device=m.charge_device, target_value_w=share_w, mode=Mode.SPEICHER.value, command_kind='set_charge', sensor_value_w=None)`. `Mode.SPEICHER.value == 'speicher'` (Enum-StrEnum aus `controller.py` — Import via `from solalex.controller import Mode`).
      5. Return die Liste.
    - `def get_soc(self, state_cache: StateCache) -> SocBreakdown | None` (AC 3, AC 4, AC 12):
      1. Für jeden Member mit `soc_device is not None`: lies `state_cache.last_states.get(soc_device.entity_id)`. Wenn None oder `state.state in _OFFLINE_SENTINELS`: skip.
      2. Parse `state.state` via `float()` in einem `try/except (ValueError, TypeError)` — Fehler: skip Member (defensive; AC 12).
      3. Defensive `isinstance(entry.attributes, dict)`-Check (Lessons 3.2 Review P10).
      4. Sammle `(member, soc_pct)` in `online_entries: list[tuple[PoolMember, float]]`. Wenn `not online_entries`: return `None` (AC 3 Satz 2).
      5. `aggregated_pct = sum(soc * m.capacity_wh for m, soc in online_entries) / sum(m.capacity_wh for m, soc in online_entries)`. Gewichteter Mittelwert (AC 3).
      6. `per_member = {m.charge_device.id: soc for m, soc in online_entries if m.charge_device.id is not None}` (AC 3 Satz 2). Members mit `device.id is None` werden aus der Breakdown ausgelassen (Dead-Defense; DB-Rows haben immer ID, aber Type-System erlaubt `None`).
      7. Return `SocBreakdown(aggregated_pct=..., per_member=...)`.
    - `@property def members(self) -> tuple[PoolMember, ...]`: return frozen tuple copy (Pool-Konsumenten dürfen nicht in-place mutieren).
  - [x] Hilfsfunktionen (module-level, pure):
    - `def _object_prefix(entity_id: str, suffixes: tuple[str, ...]) -> str`: splittet zuerst den HA-Domain-Präfix via `entity_id.partition('.')` (z. B. `"number."` oder `"sensor."`) weg, dann durchläuft `suffixes` in Reihenfolge und stripped die erste passende Suffix. Gibt den verbleibenden object-ID-Prefix zurück. Wenn das Entity kein `.` enthält (defensiver Fall: HA-Konvention garantiert es, aber Type-System nicht): behandle den ganzen String als object_id. Wenn kein Suffix matched: gib die object_id unverändert zurück (wird nie für Pairing benutzt, weil der Member dann keinen Suffix-Match hat — `soc_device=None`).
    - **Kein** dynamischer Loader, **keine** Regex-Parser (der Strip-Loop ist 5 Zeilen, lesbar, deterministisch).
  - [x] `__all__ = ["BatteryPool", "PoolMember", "SocBreakdown"]`.
  - [x] **Kein** `async`-Keyword, **keine** IO-Calls, **keine** `await`. Pool ist synchron-pur (AC 14).

- [x] **Task 3: `main.py::lifespan` — Pool-Instanziierung** (AC: 7, 8, 9)
  - [x] `main.py`: nach `devices_by_role`-Konstruktion und **vor** `Controller(...)`-Instanziierung:
    ```python
    from solalex.battery_pool import BatteryPool

    battery_pool = BatteryPool.from_devices(devices, ADAPTERS)
    app.state.battery_pool = battery_pool  # BatteryPool | None
    ```
  - [x] `Controller(...)` wird **NICHT** angepasst — kein neuer Parameter, keine Attribute. (Controller-Integration erfolgt in Story 3.4 — dort wird `app.state.battery_pool` durchgereicht.)
  - [x] **Kein** Cleanup im `finally`-Block — der Pool hält keine Ressourcen (AC 7 Satz 3).
  - [x] Optionaler `_logger.info("battery_pool_built", extra={"member_count": len(battery_pool.members) if battery_pool else 0})` direkt nach dem Bau.

- [x] **Task 4: `controller.py` — unverändert!** (AC: 7 Scope-Wall)
  - [x] **Kein Diff** in `controller.py` in dieser Story. `Mode.SPEICHER` bleibt `_policy_speicher_stub`, `Mode.MULTI` bleibt `_policy_multi_stub`. Der Controller hat in 3.3 keinen Pool-Bezug. (Prüfung: `git diff --name-only HEAD~1..HEAD backend/src/solalex/controller.py` sollte nach 3.3-Merge leer sein.)

- [x] **Task 5: Unit-Tests** (AC: 15)
  - [x] `backend/tests/unit/test_battery_pool.py` mit allen 24 Test-Fällen aus AC 15.
  - [x] `backend/tests/unit/test_marstek_venus_default_capacity.py` mit 2 Test-Fällen.
  - [x] `backend/tests/unit/test_main_lifespan_battery_pool.py` mit 2 Integration-Fällen. Reuse `backend/tests/unit/_controller_helpers.py` und `backend/tests/integration/conftest.py` für In-Memory-DB + `test-compatible` Lifespan-Harness (identische Pattern wie `test_control_state.py` aus Story 5.1a).
  - [x] Fake-State-Cache-Factory: kleines Helper (`_make_state_cache(entries)`) mit direktem Set von `state_cache.last_states` — kein `await cache.update(...)` nötig, weil die Pool-Methoden synchron sind.
  - [x] Kein `FakeHaClient` benötigt (Pool macht keine IO — siehe AC 14).
  - [x] Property-Style-Test `test_set_setpoint_sum_equals_input_watts`: 10 Kombinationen `(watts, N)` aus `[(1000, 1), (1000, 2), (1000, 3), (1001, 2), (-1000, 2), (-1001, 2), (0, 3), (7, 5), (100, 10), (999, 7)]`, jeweils `sum(d.target_value_w) == watts` verifizieren.

- [x] **Task 6: Final Verification** (AC: 13, 14, 15)
  - [x] `uv run ruff check .` → grün.
  - [x] `uv run mypy --strict src/ tests/` → grün.
  - [x] `uv run pytest -q` → grün (alle bisherigen Tests + neue Pool-Tests). 182 passed.
  - [x] SQL-Ordering: unverändert (`001_initial.sql` + `002_control_cycles_latency.sql`) — **keine** neue Migration in 3.3.
  - [x] Drift-Check 1: `grep -rE "marstek_venus|hoymiles|shelly" backend/src/solalex/battery_pool.py` → **0 Treffer** (AC 5).
  - [x] Drift-Check 2: `grep -rE "^import .*battery_pool|from .*battery_pool" backend/src/solalex/controller.py` → **0 Treffer** (AC 4, Scope-Wall).
  - [x] Drift-Check 3: `ls backend/src/solalex/ | grep -E "^pool/"` → **leer** (Pool ist Modul, nicht Folder).
  - [x] Drift-Check 4: `grep -rE "/data/templates|load_json_template|json-schema" backend/src/solalex/` → **0 Treffer** (Amendment 2026-04-22 Cut 11 bleibt gewahrt).
  - [ ] Manual-Smoke lokal im HA-Add-on (optional, kein Blocker): `/api/v1/control/state` zeigt unveränderten Polling-Payload (Pool wird erst in 3.4/5.x sichtbar).

### Review Findings

Code-Review 2026-04-25 (Blind Hunter + Edge Case Hunter + Acceptance Auditor parallel). Ergebnis: 1 decision-needed → patch, 1 patch, 5 defer, ~32 dismissed (Spec-konformes Verhalten, false positives, defensiver Code in unerreichbaren Pfaden). Beide Patches angewandt; alle 188 Tests grün (+6 neue Tests für strict-capacity-Validation).

- [x] [Review][Decision→Patch] D1 — `config_json.capacity_wh ≤ 0` löst keinen `ValueError` aus, fällt still auf den Adapter-Default zurück — AC-11-Wortlaut sagt explizit „silent-drop unzulässig, ValueError werfen". Code in [backend/src/solalex/battery_pool.py:155-161](../../backend/src/solalex/battery_pool.py#L155-L161) (`_resolve_capacity`) filtert via `isinstance(int) and not isinstance(bool) and raw > 0` und greift bei `0`, `-100`, `False`, `5000.0` (float), `"5000"` (string) auf den Adapter-Default zurück — ohne Log, ohne Exception. AC 11 verlangt aber explizit `ValueError(f"capacity_wh must be >= 1, got {value}")` für `config_json.capacity_wh ≤ 0`. Drei Reviewer-Layer konvergieren: Auditor zitiert AC 11 wortwörtlich, Blind/Edge bemängeln zusätzlich die fehlende Type-Coercion (float/string). Entscheidung nötig: (a) **Strict (Spec-Wortlaut):** `_resolve_capacity` wirft `ValueError` bei `raw is not None and (not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0)` → Lifespan crasht bei kaputter `config_json` → Add-on-Boot blockiert; (b) **Defensive (Spec-Geist):** Loggen + Default-Fallback wie heute, aber `_logger.warning("invalid_capacity_wh_in_config_json", extra={...})`. Blind+Edge zusätzlich.
- [x] [Review][Patch] P1 — Toter `_ = soc_entry.attributes`-Defensive-Check + Test ohne echte Wirkung [[backend/src/solalex/battery_pool.py:235-237](../../backend/src/solalex/battery_pool.py#L235-L237), [backend/tests/unit/test_battery_pool.py:479-498](../../backend/tests/unit/test_battery_pool.py#L479-L498)]. Die Zeile `_ = soc_entry.attributes if isinstance(soc_entry.attributes, dict) else {}` weist nach `_` zu und verwirft das Resultat — `attributes` wird in `get_soc` nie konsumiert. Der Test `test_get_soc_defensive_against_non_dict_attributes` setzt `attributes="broken"` per `# type: ignore`, aber weil der Code das Feld nirgends liest, validiert der Test nichts. Fix: tote Zeile löschen, Test entfernen oder Test in `_make_state_cache`-Smoke umwandeln (kein semantischer Verlust, AC 12 verlangt nur den `isinstance`-Guard für **zukünftige** `attributes`-Reads — die kommen erst in v1.5).
- [x] [Review][Defer] DF1 — `entry.state` non-string defensiver Guard [[backend/src/solalex/battery_pool.py:60-64](../../backend/src/solalex/battery_pool.py#L60-L64)] — wenn HA-State irgendwann via Regression als `None`/`int` ankommt, crasht `.strip()` mit `AttributeError`. Aktuell garantiert `HaStateEntry.state: str` den String-Typ, aber kein `isinstance`-Guard im Pool. Defer → ggf. global in `_HA_SENSOR_SENTINELS`-Pattern härten.
- [x] [Review][Defer] DF2 — Wall-Clock-Performance-Test flaky-prone [[backend/tests/unit/test_battery_pool.py:529-543](../../backend/tests/unit/test_battery_pool.py#L529-L543)] — `time.perf_counter_ns()` < 5 ms auf N=8 ist generös, aber CI-Runner-Jitter (free-threaded Py 3.13, GIL-Contention) kann gelegentlich rauschen. Markieren mit `@pytest.mark.benchmark` oder ganz entfernen, wenn rot.
- [x] [Review][Defer] DF3 — `SocBreakdown.per_member: dict` veränderbar trotz `frozen=True` [[backend/src/solalex/battery_pool.py:85-90](../../backend/src/solalex/battery_pool.py#L85-L90)] — Konsumenten könnten den Dict mutieren, was die „frozen"-Garantie aushebelt. `types.MappingProxyType(per_member)` oder `tuple[tuple[int, float], ...]` wäre echt-immutable. Niedrige Priorität, da Konsumenten heute nur lesen.
- [x] [Review][Defer] DF4 — `_object_prefix` kollabiert auf leeren String wenn `object_id == suffix` [[backend/src/solalex/battery_pool.py:43-57](../../backend/src/solalex/battery_pool.py#L43-L57)] — pathologisch (HA-Entity-IDs sind immer länger als Suffix), aber zwei Devices mit `object_id == "_charge_power"` bzw. `"_battery_soc"` würden auf Prefix `""` pairen. Zusätzlicher Guard (`if object_id.endswith(suffix) and len(object_id) > len(suffix)`) wäre 1-Zeilen-Hardening.
- [x] [Review][Defer] DF5 — `config_json` mit `null`/`[]`/Non-Object crasht Lifespan [[backend/src/solalex/battery_pool.py:155](../../backend/src/solalex/battery_pool.py#L155)] — `charge.config()` ruft `json.loads(config_json)`; bei `"null"` returnt `None` und `.get("capacity_wh")` wirft `AttributeError`. `config_json` ist heute interner Upsert-Pfad (kein User-Input), aber v1.5-Wizard kann das ändern. `try/except + isinstance(cfg, dict)`-Guard wäre defensives Hardening; teilweise Überschneidung mit D1.

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Project Structure Zeile 576–752](../planning-artifacts/architecture.md) — Kein `pool/`-Subfolder im Layout; Pool-Abstraktion ist v1-Kern (siehe Zeile 803, Epic-3-Spalte).
- [architecture.md — Decision Priority Analysis Zeile 240–250](../planning-artifacts/architecture.md) — Adapter-Modul-Pattern, Single-Source-of-Truth pro Hersteller.
- [architecture.md — Amendment 2026-04-22 Cut 9 + 11](../planning-artifacts/architecture.md) — kein Controller-Submodul-Split, kein JSON-Template-Layer. Pool-Abstraktion folgt demselben Prinzip: ein Python-Modul, hardcoded Konstanten, keine externe Datei.
- [prd.md — FR21/FR23](../planning-artifacts/prd.md) — Pool-Gleichverteilung + SoC-Aggregat.
- [prd.md — Zeile 181–182 + Zeile 223](../planning-artifacts/prd.md) — Kern-Segment Marstek Venus, v1-Scope „1 Akku pro Instanz" (Wizard-Realität) vs. Abstraktions-Kontrakt (N ≥ 1).
- [prd.md — Zeile 363–367](../planning-artifacts/prd.md) — Modus-Abgrenzung: **Speicher-Modus konsumiert den Pool** (Story 3.4, nicht 3.3).
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — insbesondere Regel 2 (ein Python-Modul pro Adapter), Regel 3 (Closed-Loop + Rate-Limit + Fail-Safe bleiben Executor-Thema).
- [Story 3.1](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — **Pflichtlektüre**: `PolicyDecision`-Dataclass, `DispatchContext`, Fire-and-Forget-Dispatch-Task, Veto-Kaskade. Der Pool produziert nur `PolicyDecision`-Listen — der Dispatch-Pfad ist fertig und bleibt in 3.3 unberührt.
- [Story 3.2](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — **Pflichtlektüre**: `DrosselParams.__post_init__`-Invariant-Pattern (Kapitel „Review Findings" Patch P7), `state_cache.last_states`-Lese-Muster mit `isinstance`-Guard (P10), Defensive-Parse-Fehler-Handling (P9), `commissioned_at`-Filter in Lifespan (P8), Role-Kollisions-Log-Pattern.
- [Story 2.1 — Hardware Config Page](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md) — Device-Persistenz-Flow, `config_json` als JSON-Blob für `min_soc`/`max_soc`/`night_*`. 3.3 erweitert `config_json` um **optionales** `capacity_wh`; Wizard wird in v1.5 nachgezogen.
- [Story 2.2 — Funktionstest mit Readback & Commissioning](./2-2-funktionstest-mit-readback-commissioning.md) — Commissioning-Flow setzt `commissioned_at`; Pool respektiert denselben Filter.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Reine Backend-Story. **Keine Frontend-Änderungen** (Pool-Anzeige im Dashboard ist Epic 5, Story 5.4 Energy-Ring + Story 5.5 Modus-Anzeige). Pool ist in 3.3 ein schlafender Baustein.

**Mini-Diff-Prinzip:** Der Pull-Request für 3.3 sollte **klein und quadratisch** sein:
- 1 neue Datei: `backend/src/solalex/battery_pool.py` (~150 LOC inkl. Kommentare)
- 3 MOD-Dateien: `adapters/base.py` (+ ~5 LOC), `adapters/marstek_venus.py` (+ ~5 LOC), `main.py` (+ ~3 LOC)
- 3 neue Test-Dateien: `test_battery_pool.py` (~400 LOC), `test_marstek_venus_default_capacity.py` (~40 LOC), `test_main_lifespan_battery_pool.py` (~80 LOC)
- Keine SQL-Migration, keine neue API-Route, keine neue Dependency, keine Frontend-Änderung.

**Dateien, die berührt werden dürfen:**

- **NEU Backend:**
  - `backend/src/solalex/battery_pool.py` — Pool-Abstraktion (Dataclasses + Factory + `set_setpoint` + `get_soc`).

- **MOD Backend:**
  - `backend/src/solalex/adapters/base.py`
    - Methode `get_default_capacity_wh(self, device: DeviceRecord) -> int` mit Default `5120` (kein `NotImplementedError`, kein `0`).
  - `backend/src/solalex/adapters/marstek_venus.py`
    - Explizites `get_default_capacity_wh` Override `return 5120` mit Datenblatt-Kommentar (Single-Source-of-Truth im Adapter-Modul).
  - `backend/src/solalex/main.py`
    - Import `from solalex.battery_pool import BatteryPool`.
    - In `lifespan`: nach `devices_by_role`-Bau und **vor** `Controller(...)`-Instanziierung: `app.state.battery_pool = BatteryPool.from_devices(devices, ADAPTERS)`.
    - Optional Info-Log `battery_pool_built`.

- **NEU Backend (Tests):**
  - `backend/tests/unit/test_battery_pool.py` (~24 Test-Fälle gemäß AC 15).
  - `backend/tests/unit/test_marstek_venus_default_capacity.py` (~2 Tests).
  - `backend/tests/unit/test_main_lifespan_battery_pool.py` (~2 Integration-Tests).

- **NICHT anfassen:**
  - `backend/src/solalex/controller.py` — Pool wird nicht in den Controller verdrahtet (Story 3.4 macht das).
  - `backend/src/solalex/executor/*.py` — Veto-Kaskade, Readback, Rate-Limit bleiben unverändert.
  - `backend/src/solalex/adapters/hoymiles.py`, `adapters/shelly_3em.py` — erben den Base-Default für `get_default_capacity_wh`; **kein** Override notwendig.
  - `backend/src/solalex/persistence/sql/*.sql` — keine neue Migration.
  - `backend/src/solalex/persistence/repositories/*.py` — kein Repo-Change (Pool liest nur aus der bestehenden `devices`-Query in der Lifespan).
  - `backend/src/solalex/api/routes/*.py` — keine neue Route, keine Schema-Änderung.
  - `backend/src/solalex/state_cache.py` — keine neuen Felder, keine neuen Methoden (Pool liest `last_states` read-only).
  - `frontend/src/**/*` — **nichts**. Pool-Anzeige ist Epic 5.
  - `pyproject.toml` — keine neue Dependency (stdlib reicht).

### Architecture Compliance (5 harte Regeln aus CLAUDE.md)

1. **snake_case überall:** Alle neuen Python-Symbole (`battery_pool`, `pool_member`, `soc_breakdown`, `get_default_capacity_wh`, `from_devices`, `set_setpoint`, `get_soc`) sind `snake_case`. Klassennamen (`BatteryPool`, `PoolMember`, `SocBreakdown`) sind `PascalCase` (Python-Klassen-Konvention, Architecture Zeile 492).
2. **Ein Python-Modul pro Adapter:** Marstek-Kapazität (`5120 Wh`) lebt ausschließlich in `adapters/marstek_venus.py`. Pool ist hardware-agnostisch (AC 5).
3. **Closed-Loop-Readback:** Pool produziert `PolicyDecision`-Objekte; der Executor-Dispatch-Pfad (Story 3.1) enforced Readback für jeden `set_charge`-Call unverändert. Pool umgeht den Executor **nie**.
4. **JSON-Responses ohne Wrapper:** In 3.3 nicht relevant — keine neue Route.
5. **Logging via `get_logger(__name__)`:** Der Pool nutzt `get_logger("solalex.battery_pool")` nur für den Konstruktions-Log in `main.py::lifespan` und optional für Defensive-Catch-Logs in `get_soc`. Kein `print`, kein `logging.info` direkt.

### Library & Framework Requirements

- **Keine neuen Dependencies.** Pool nutzt ausschließlich stdlib (`dataclasses`, `typing`).
- **Python 3.13** (aus `pyproject.toml`). `from __future__ import annotations` bleibt Pflicht in jedem neuen File (Projekt-Konvention).
- **Kein numpy/pandas** für die gewichtete SoC-Aggregation — `sum(x*y)/sum(y)` ist eine Zeile Python-Built-ins und deckt N ≤ 16 Members in v1 vollständig ab.
- **Kein Pydantic-Model** für Pool-Dataclasses — der Pool ist Backend-intern, wird nie via API serialisiert. `@dataclass(frozen=True)` reicht.

### File Structure Requirements

- **Pool als Modul, nicht Folder:** `backend/src/solalex/battery_pool.py` — **kein** `backend/src/solalex/pool/__init__.py`, **kein** `pool/member.py`/`pool/soc.py`-Split. Analogie zu `controller.py` (Mono-Modul, Amendment 2026-04-22 Cut 9).
- **Test-Files spiegeln Source-Pfade:** `tests/unit/test_battery_pool.py` für das Pool-Modul. `tests/unit/test_marstek_venus_default_capacity.py` für den Adapter-Override (nicht `test_marstek_venus.py`, weil eine entsprechende Datei aus 3.2 bereits existieren könnte — separaten Test-File vermeidet Merge-Konflikte).

### Testing Requirements

- **Pytest + MyPy strict + Ruff** — alle 4 CI-Gates grün.
- **Coverage ≥ 90 %** auf `battery_pool.py` + Kapazitäts-Methoden. Messung via `pytest --cov=solalex.battery_pool --cov=solalex.adapters.marstek_venus --cov=solalex.adapters.base`.
- **Keine Playwright, kein Vitest** — Pool ist reines Backend-Python, Frontend-Tests unberührt (AC 13).
- **FakeStateCache** statt realer DB-Connection für die Pool-Methoden-Tests (AC 14 — Pool ist IO-frei, Tests müssen nicht gegen SQLite laufen). Für die 2 Integration-Tests in `test_main_lifespan_battery_pool.py` wird die vorhandene In-Memory-DB-Fixture aus `tests/integration/conftest.py` reused — keine neuen Fixtures.
- **Property-Style-Test für `set_setpoint`:** `test_set_setpoint_sum_equals_input_watts` deckt 10 (watts, N)-Kombinationen mit der Invariante `sum(decisions) == watts` ab. Keine `hypothesis`-Dependency nötig — eine explizite `pytest.mark.parametrize`-Liste reicht.
- **Deterministische Round-Robin-Semantik:** Die Tests müssen **genau** prüfen, welche Members den `base+1`-Anteil bekommen (AC 2 Satz 2). Implementation hält die Reihenfolge von `online_members` stabil (insertion-order durch `list`-Konstruktion aus `self.members`), damit Tests nicht flaky auf Dict-Sortierung werden.

### Previous Story Intelligence (3.1, 3.2, 2.2, 2.1)

**Aus Story 3.2 (jüngste, höchste Relevanz):**

- **Invariant-Validation-Pattern etabliert:** `DrosselParams.__post_init__` validiert `deadband_w/min_step_w/smoothing_window/limit_step_clamp_w`. **Übertrag auf 3.3:** `PoolMember.__post_init__` validiert `capacity_wh >= 1` (AC 11). Gleiche Fehler-Formulierung (`ValueError(f"capacity_wh must be >= 1, got {capacity_wh}")`).
- **`state_cache.last_states`-Lese-Pattern mit `isinstance`-Guard:** Story 3.2 Review P10 führte den `isinstance(entry.attributes, dict)`-Check ein. **Übertrag:** `get_soc` wendet denselben Guard an, auch wenn Pool die `attributes` nicht direkt liest — ein zukünftiger Pool-Extension könnte sie benötigen (z. B. SoC-Confidence aus `attributes.reporting_source`). Defensive-Code lohnt.
- **NaN/Inf-Guard bei float-Parsing:** Story 3.2 Review P4 ergänzte `math.isfinite()` auf `sensor_value_w`. **Übertrag:** SoC-Parse in `get_soc` prüft `math.isfinite(soc_pct)` nach `float(state.state)` — verhindert `NaN` im gewichteten Mittelwert.
- **Defensive Try/Except für Adapter-Calls:** Story 3.2 Review P9 fing `parse_readback`-Exceptions. **Übertrag:** Pool-Factory ruft `get_default_capacity_wh` **ohne** `try/except` (AC 12 Satz 1 — Fail-Loud am Startup). Pool-Methoden (`set_setpoint`/`get_soc`) haben aber defensive `float()`-Parses mit `except (ValueError, TypeError)` → skip Member.
- **`_dispatch_tasks`-Pattern nicht nötig:** Pool hat keine fire-and-forget-Tasks; der synchrone Pure-Pfad macht Shutdown-Handling überflüssig (AC 7 Satz 3).
- **Role-Collision-Warn-Log bereits in `main.py`:** Story 3.2 Review P8 fügte ein Warning-Log hinzu, wenn zwei Devices dieselbe Role haben. **3.3-Relevanz:** Pool ignoriert das, weil `wr_charge`/`battery_soc`-Multi-Role bewusst zulässig ist (N ≥ 2 Members). Der Warn-Log in `main.py` greift für `wr_limit`/`grid_meter`, aber der Pool ignoriert die Warnung für `wr_charge` — das ist konsistent, weil der Warn-Log davor ausgelöst wird und der Pool-Bau danach auf allen commissionierten Devices läuft. **Explicit Not-to-do:** Kein Filter-Refactor in 3.3; die Warnung ist Information, kein Error.

**Aus Story 3.1 (Controller-Foundation):**

- `Mode.SPEICHER` existiert als Enum-Value (`'speicher'`) und als CHECK-Constraint in `control_cycles.mode`. Pool-`set_setpoint` produziert `PolicyDecision(mode=Mode.SPEICHER.value)` — Story 3.4 konsumiert das.
- `PolicyDecision.command_kind` hat die zwei Werte `'set_limit'` (Drossel, 3.2) und `'set_charge'` (Speicher, 3.3/3.4). Executor routet via `decision.command_kind` auf `adapter.build_set_limit_command` bzw. `adapter.build_set_charge_command`. **Keine Änderung am Executor in 3.3.**
- `state_cache.last_states` ist die Wahrheit für aktuelle Entity-States. Controller und Pool lesen beide daraus — kein zweiter In-Memory-Cache.
- `Marstek-Venus.build_set_charge_command` existiert seit Story 2.2 (siehe `adapters/marstek_venus.py:60-65`) — der Pool konsumiert das **nicht direkt**, sondern produziert nur `PolicyDecision`; Executor baut den Command.
- `Marstek-Venus.get_limit_range(device) = (0, 2500)` — der Executor-Range-Check clamped End-Werte. Pool darf Werte außerhalb liefern; Range-Check veto't sie im Executor (vetoed-Cycle-Row). **Kein zweiter Range-Check im Pool.**

**Aus Story 2.2 (Funktionstest + Commissioning):**

- `commissioned_at IS NOT NULL` ist der Filter für „produktive" Devices (AC 9).
- `ensure_entity_subscriptions` in `setup/test_session.py` subscribed alle commissionierten Entity-IDs im HA-WS — das bleibt in 3.3 unverändert. Pool ruft keine Subscribe-Logik, die Subscription ist Lifespan-Verantwortung.
- `verify_readback` aus Story 2.2 ist in 3.3 nicht relevant (Pool produziert keine Commands; Readback greift erst im Executor in Story 3.4).

**Aus Story 2.1 (Hardware Config Page):**

- `config_json` ist ein frei-strukturierter JSON-Blob. Für Marstek-Venus heute: `{min_soc, max_soc, night_discharge_enabled, night_start, night_end}`. **3.3 erweitert die Semantik um `capacity_wh` (optional, nicht Pflicht)** — ohne Wizard-Änderung; nur dann konsumiert, wenn ein Nutzer via DB-Edit (oder v1.5-Wizard) den Key setzt.
- `devices`-Tabelle hat `UNIQUE(entity_id, role)` — zwei Marstek-Venus-3E benötigen unterschiedliche Entity-IDs (z. B. `number.venus_garage_charge_power` vs. `number.venus_keller_charge_power`), was HA automatisch sicherstellt, wenn beide Devices in HA eingebunden sind.

### Git Intelligence Summary

**Letzte 10 Commits (chronologisch, neueste zuerst):**

- `0650862 feat(5.1a)`: Story 5.1a Live-Running-View + Polling-Endpoint verdrahtet. Pool kommt in Story 5.x in die UI — in 3.3 keine Interferenz.
- `f4003fc fix(release)`: Bugfix Beta 0.1.1-beta.3.
- `4053a83 fix(3.2)`: Code-Review-Fixes Story 3.2 — Pattern-Transfer: Invariant-Validation, NaN-Guards, `isinstance`-Checks, `int(round())`-statt-`int()`-Trunkierung (für Pool nicht relevant, aber defensive Parsing-Pattern).
- `88894f3 feat(2.3a)`: Pre-Setup-Disclaimer-Gate. Gate-Semantik beeinflusst 3.3 nicht.
- `f3b4a68 fix(3.1)`: Harden Controller/Executor. Fix-Pattern übertragen (Fail-Safe-Wrapper, Async-Task-Management).
- `a32ec56 feat(release)`: 0.1.1-beta.0 mit Controller/Executor-Foundation.

**Relevante Code-Patterns aus den Commits:**
- `controller.py` Enum-Dispatch + `match`-Block bleibt das Vorbild für Mode-bezogene Methoden-Splits.
- `adapters/base.py` `DrosselParams`-Dataclass mit `__post_init__`-Validation ist der direkte Vorläufer für `PoolMember`.
- `main.py::lifespan` Sequenz `migrate → load devices → build devices_by_role → build controller` ist stabil; 3.3 schiebt genau einen Schritt zwischen `build devices_by_role` und `build controller` ein.
- Code-Review-Pattern aus 3.2 (Patch P1–P16, Decision D1–D5) zeigt: Safety-Patches werden im selben Story-PR erwartet, nicht in Follow-up-Stories. Für 3.3 heißt das: Defensive-Checks in AC 11 + AC 12 sind Teil der initialen Implementation, nicht „später nachziehen".

### Latest Tech Information

- **Python 3.13 `divmod` behaviour:** `divmod(-1001, 2) == (-501, 1)` — Python garantiert `a == divmod(a,b)[0]*b + divmod(a,b)[1]`. Die Round-Robin-Verteilung in `set_setpoint` funktioniert für positive **und** negative Watts identisch (AC 2 Satz 3).
- **`@dataclass(frozen=True)`** verhindert `PoolMember`-Mutation. Frozen-Dataclasses sind hashbar → können in Sets/Dicts verwendet werden. `__post_init__` läuft nach `__init__` — Invariant-Check ist zulässig vor dem Freeze.
- **FastAPI `app.state`** ist ein `types.SimpleNamespace`-ähnlicher Container — `app.state.battery_pool = None` ist zulässig, `getattr(app.state, "battery_pool", None)` kompatibel zu späterer Migration ohne Breaking-Change. Bestehende Pattern: `app.state.ha_client`, `app.state.state_cache`, `app.state.devices_by_entity`, `app.state.adapter_registry` — alle bereits verdrahtet.

### Project Context Reference

Kein `project-context.md` in diesem Repo. Referenz-Dokumente sind die oben verlinkten `prd.md`, `architecture.md`, `epics.md`, `CLAUDE.md` sowie die Vor-Stories 3.1 / 3.2 / 2.1 / 2.2.

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `backend/src/solalex/battery_pool.py` existiert mit `BatteryPool`, `PoolMember`, `SocBreakdown` und `_object_prefix`-Helper.
2. `BatteryPool.from_devices` filtert auf `commissioned_at IS NOT NULL` und pairt `wr_charge`/`battery_soc` per Entity-Prefix-Matching (AC 9, AC 10).
3. `BatteryPool.set_setpoint` verteilt `watts` gleichmäßig (Integer-Division + Rest-Rotation), überspringt Offline-Members, gibt leere Liste bei All-Offline (AC 2, AC 4).
4. `BatteryPool.get_soc` aggregiert gewichtet nach Kapazität, filtert Offline-Members, liefert `None` bei All-Offline (AC 3, AC 4).
5. `AdapterBase.get_default_capacity_wh` hat Default `5120`; `MarstekVenusAdapter.get_default_capacity_wh` überschreibt explizit mit `5120` (Datenblatt-Kommentar).
6. `main.py::lifespan` baut den Pool nach `devices_by_role` und hängt ihn an `app.state.battery_pool` (`BatteryPool | None`).
7. `controller.py` bleibt in 3.3 unverändert.
8. Unit-Tests in `test_battery_pool.py`, `test_marstek_venus_default_capacity.py`, `test_main_lifespan_battery_pool.py` sind grün und decken AC 1–12 + AC 14 ab.
9. Alle 4 CI-Gates grün: Ruff + MyPy strict + Pytest + SQL-Ordering (unverändert bei 2 Dateien).
10. Drift-Checks bestanden: kein Vendor-Name in `battery_pool.py`, kein Pool-Import in `controller.py`, kein `pool/`-Subfolder, keine `/data/templates/`, keine neue SQL-Migration.
11. Bestehende Tests aus Story 1.3/2.1/2.2/2.3/3.1/3.2/5.1a bleiben grün.

### References

- [epics.md — Story 3.3, Zeile 832–858](../planning-artifacts/epics.md)
- [architecture.md — Project Structure Zeile 576–752 + Epic-3-Zeile 803](../planning-artifacts/architecture.md)
- [architecture.md — Amendment 2026-04-22 Cuts 9 + 11](../planning-artifacts/architecture.md)
- [prd.md — FR21/FR22/FR23 Zeile 606–608](../planning-artifacts/prd.md)
- [prd.md — Kern-Segment Marstek Zeile 181–182 + v1-Scope Zeile 223](../planning-artifacts/prd.md)
- [prd.md — Modus-Abgrenzung Zeile 363–367](../planning-artifacts/prd.md)
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md)
- [Story 3.1 — Core Controller](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md)
- [Story 3.2 — Drossel-Modus + Review-Findings](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — Pattern-Transfer (Invariants, Defensive-Checks, `isinstance`-Guards)
- [Story 2.1 — Hardware Config Page](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md) — `config_json`-Blob-Semantik
- [Story 2.2 — Funktionstest mit Readback & Commissioning](./2-2-funktionstest-mit-readback-commissioning.md) — `commissioned_at`-Flag
- [adapters/marstek_venus.py — Charge-Command + Range 0–2500 W](../../backend/src/solalex/adapters/marstek_venus.py)
- [adapters/base.py — AdapterBase-Interface + DrosselParams-Pattern](../../backend/src/solalex/adapters/base.py)
- [controller.py — Mode-Enum + PolicyDecision](../../backend/src/solalex/controller.py)
- [main.py — Lifespan-Verdrahtung + devices_by_role](../../backend/src/solalex/main.py)

### Deferred (out-of-scope for 3.3, documented for v1.5+)

- **Multi-Akku-Wizard-Flow** (Marstek-Micha-2×-Venus — Epic 2 v1.5): Wizard persistiert heute nur 1 Charge-Device. Pool-Abstraktion ist ready; Wizard-Erweiterung für mehrere Entity-Picker pro Vendor ist eigene Story (v1.5-Epic-2-Nachtrag). Pro-Member-`config_json.pool_group`-Key bleibt Option für spätere Disambiguierung, wenn Prefix-Matching an Grenzen kommt.
- **Hot-Reload des Pools bei Runtime-Device-Change:** AC 8 schließt das in 3.3 explizit aus. Wird zusammen mit `devices_by_role`-Reload (heute auch Static-Snapshot) in Epic 2 v1.5 oder Epic 3 Wizard-Integration (Story 3.6) adressiert.
- **SoC-Balance statt Gleichverteilung** (v2): PRD Zeile 519–520 und Architektur Zeile 256 / 980 verschieben SoC-gewichtete Pool-Verteilung auf v2. 3.3 bleibt auf Gleichverteilung (Epic-AC 2: „N/2 Watt pro Akku").
- **Single-Hauptspeicher-Fallback-Modus** (Epic-AC 4 Satz 2: „Fallback-Modus = 1 Hauptspeicher aktiv, andere statisch"): 3.3 implementiert den einfachsten Fall — Offline-Members werden ausgeblendet, Online-Members übernehmen. „Statisch"-Semantik (Offline-Member hält letzten Setpoint) entsteht **von selbst**, weil Pool einen Offline-Member nicht überschreibt (kein Command → Hardware hält Letztes). Wenn Story 3.4 ein explizites „Offline-Member zurücksetzen" braucht, wird das dort ergänzt.
- **Anker-Solix-Adapter + Generic-HA-Adapter** (v1.5): Pool-Code ist adapter-agnostisch (AC 5). Bei Einzug der neuen Adapter wird nur `get_default_capacity_wh` überschrieben und ggf. ein Adapter-spezifischer Suffix in `_CHARGE_SUFFIXES` / `_SOC_SUFFIXES` ergänzt — kein Pool-Refactor.
- **Pool-Metrics im Dashboard** (Epic 5, Story 5.4 Energy-Ring + Story 5.5 Modus-Badge): Pool-Members, aggregierte SoC, Offline-Status kommen über `/api/v1/control/state` (Story 5.1a Polling-Endpoint) ins Frontend. 3.3 bereitet den Backend-Zustand vor; Read-Endpoint-Erweiterung erfolgt in Story 5.x.
- **Async-Readback-Pfad für Marstek-Venus** (Story 3.4 / v1.5): Marstek-Venus hat heute `ReadbackTiming(timeout_s=30.0, mode='sync')` — bei 2× Venus im Pool und je 30 s Readback kann sich der Controller-Per-Device-Lock aufstauen. Story 3.4 evaluiert Async-Readback (analog zum OpenDTU-MQTT-Plan aus deferred-work.md Zeile 126).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- Initiale Test-Suite (`test_marstek_venus_default_capacity.py`) lief im RED-Schritt mit `AttributeError: '_StubAdapter' object has no attribute 'get_default_capacity_wh'` — bestätigt fehlende Base-Methode vor Implementation.
- Mypy strict warf nach erstem Tests-Lauf zwei `attr-defined`-Errors auf `client.app.state.battery_pool`, weil `TestClient.app` als ASGI-Callable getypt ist. Lösung: Zugriff via `main_mod.app.state.battery_pool` (Modul-Referenz aus der Fixture).
- Ruff entfernte 3 unused imports (`SocBreakdown` im Pool-Test, `BatteryPool` aus Doppel-Import in `main.py` durch Sortierung).

### Completion Notes List

- **Task 1 (AC 6) — Adapter-Default-Capacity:** `AdapterBase.get_default_capacity_wh(device) -> int` mit Default 5120 Wh hinzugefügt, kein `NotImplementedError` per Design (Lessons aus Story 3.2 — defensive Defaults statt Fail-Loud im falschen Moment). `MarstekVenusAdapter` überschreibt explizit mit 5120 als Single-Source-of-Truth pro CLAUDE.md Regel 2. Hoymiles + Shelly erben den Base-Default unverändert (toter-Code-Proof, sie tauchen nie als `wr_charge` auf).
- **Task 2 (AC 1, 2, 3, 4, 5, 10, 11, 12, 14) — `battery_pool.py`:** Mono-Modul (~250 LOC inkl. Docstrings) mit `BatteryPool`, `PoolMember`, `SocBreakdown`, `_object_prefix`-Helper. Synchron-pur, keine IO, keine vendor-spezifischen Imports. Domain-agnostisches Prefix-Pairing via `partition('.')` + Suffix-Liste (`_battery_soc` vor `_soc`). `divmod` produziert symmetrisch-gerundete Splits für positive **und** negative Watts (Property-Test über 10 Kombinationen). Offline-Erkennung mirror't `_HA_SENSOR_SENTINELS` aus dem Controller (eigene Konstante in `battery_pool` — Layering, kein Cross-Import). Defensive Floats: NaN/Inf-Filter via `math.isfinite`, `try/except (ValueError, TypeError)` für Parser-Fehler, `isinstance(entry.attributes, dict)`-Guard für pathologische StateCache-Entries. `PoolMember.__post_init__` validiert `capacity_wh >= 1` (Pattern aus 3.2 P7).
- **Task 3 (AC 7, 8, 9) — Lifespan-Integration:** Zwei Zeilen Diff in `main.py::lifespan` (Import + Pool-Bau zwischen `devices_by_role` und `Controller(...)`). Pool wird an `app.state.battery_pool: BatteryPool | None` gehängt und mit `_logger.info("battery_pool_built", ...)` quittiert. **Kein** Cleanup im `finally`-Block (Pool ist State-frei). Hot-Reload bewusst nicht implementiert — Add-on-Restart erforderlich, identisch zu `devices_by_role`-Verhalten.
- **Task 4 — Scope-Wall:** `git status` bestätigt `controller.py` ist nicht modifiziert. `Mode.SPEICHER`/`Mode.MULTI` bleiben Stubs, Pool fließt nicht in den Controller-Konstruktor (Story 3.4 macht das).
- **Task 5 (AC 15) — Tests:** 44 neue Test-Fälle, alle grün. Coverage `battery_pool.py` = 97 % (Ziel ≥ 90 %). Lifespan-Integrationstests seedet die DB pre-startup und prüft `app.state.battery_pool` nach `TestClient(...)`-Eintritt.
- **Task 6 — CI-Gates + Drift-Checks:** Alle vier Hard-Gates grün (Ruff, Mypy strict, Pytest 182/182, SQL-Ordering unverändert bei 2 Dateien). Alle vier Drift-Checks 0 Treffer (kein Vendor-Name in `battery_pool.py`, kein Pool-Import in `controller.py`, kein `pool/`-Subfolder, keine `/data/templates/`-Pfade).

### File List

**NEU Backend:**
- `backend/src/solalex/battery_pool.py` (Pool-Abstraktion: `BatteryPool` + `PoolMember` + `SocBreakdown` + `_object_prefix`-Helper)

**MOD Backend:**
- `backend/src/solalex/adapters/base.py` (neue Methode `get_default_capacity_wh` mit Default 5120 Wh)
- `backend/src/solalex/adapters/marstek_venus.py` (explizites `get_default_capacity_wh`-Override mit 5120 Wh + Datenblatt-Kommentar)
- `backend/src/solalex/main.py` (Lifespan-Verdrahtung: Import + Pool-Bau + `app.state.battery_pool`-Anhang + Info-Log)

**NEU Tests:**
- `backend/tests/unit/test_battery_pool.py` (40 Test-Fälle: Pairing, Equal-Split, SoC-Aggregation, Offline-Fallback, Invariant-Validation, Property-Test, Vendor-Drift-Check)
- `backend/tests/unit/test_marstek_venus_default_capacity.py` (2 Test-Fälle: Base-Default + Marstek-Override)
- `backend/tests/unit/test_main_lifespan_battery_pool.py` (2 Integration-Test-Fälle: Pool-Anhang bei commissionierter Marstek + `None` ohne Battery-Devices)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-24 | 0.1.0 | Initiale Story-Kontextdatei für Story 3.3 erstellt und auf `ready-for-dev` gesetzt. Pool-Abstraktion als neues Modul `battery_pool.py` (BatteryPool + PoolMember + SocBreakdown); Adapter-Modul-Konstante `get_default_capacity_wh` = 5120 Wh in Marstek-Venus; `main.py::lifespan` hängt Pool an `app.state.battery_pool`. Keine Controller-Verdrahtung (3.4-Thema), keine SQL-Migration, keine Frontend-Änderung, keine neue Dependency. Tests decken Gleichverteilung (N=1/2/3, pos/neg Watts, Rest-Rotation), SoC-Aggregation (gewichtet), Offline-Fallback, Prefix-Pairing, Invariant-Validation. Pattern-Transfer aus Story 3.2 Review: `__post_init__`-Validation, `isinstance`-Guards, NaN-Filter, Fail-Loud am Startup. | Claude Opus 4.7 |
| 2026-04-25 | 0.2.0 | Implementation komplett, Status → review. `battery_pool.py` (250 LOC, Coverage 97 %), `AdapterBase.get_default_capacity_wh` + Marstek-Override, `main.py::lifespan` Pool-Verdrahtung. 44 neue Tests, 182 Tests gesamt grün. Alle vier CI-Gates grün (Ruff, Mypy strict, Pytest, SQL-Ordering). Alle vier Drift-Checks 0 Treffer. Controller.py bleibt unverändert (Scope-Wall AC 7). | Claude Opus 4.7 |
