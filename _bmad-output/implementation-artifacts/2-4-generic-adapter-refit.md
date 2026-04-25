# Story 2.4: Generic-Adapter-Refit (Hoymiles -> Generic, Shelly -> Generic-Meter)

Status: done

<!-- Erstellt nach Sprint Change Proposal 2026-04-25. Grund: sprint-status.yaml markierte Story 2.4 bereits ready-for-dev, aber die Story-Datei fehlte. -->

## Story

Als Beta-Tester mit nicht-Hoymiles-Wechselrichter (ESPHome, Trucki, MQTT) und nicht-Shelly-Smart-Meter (ESPHome SML, Tibber, MQTT),
moechte ich, dass das Add-on meine Hardware via Home-Assistant-Standardattribute auto-detected,
so dass ich nicht fuer jeden Hersteller einen eigenen Adapter im Image brauche und auch Nicht-Day-1-Hardware im Setup funktioniert.

## Acceptance Criteria

1. **Hoymiles -> Generic-Inverter:** `backend/src/solalex/adapters/hoymiles.py` ist durch `backend/src/solalex/adapters/generic.py` ersetzt; Klasse `HoymilesAdapter` heisst `GenericInverterAdapter`; das Modul exportiert `ADAPTER = GenericInverterAdapter()`.
2. **Shelly -> Generic-Meter:** `backend/src/solalex/adapters/shelly_3em.py` ist durch `backend/src/solalex/adapters/generic_meter.py` ersetzt; Klasse `Shelly3EmAdapter` heisst `GenericMeterAdapter`; das Modul exportiert `ADAPTER = GenericMeterAdapter()`.
3. **Generic-Inverter-Detection:** `GenericInverterAdapter.detect()` findet WR-Limit-Entities ueber Domain `number` oder `input_number` plus `unit_of_measurement` `W` oder `kW`. Vendor-Suffix-Patterns wie `_limit_nonpersistent_absolute` sind kein Filter mehr.
4. **Generic-Meter-Detection:** `GenericMeterAdapter.detect()` findet Smart-Meter-Entities ueber Domain `sensor` plus `unit_of_measurement` `W` oder `kW`. Suffix-Hints wie `_power`, `_current_load`, `_grid_power` duerfen hoechstens spaeter als Confidence-Boost dienen, sind aber in dieser Story kein Filter.
5. **Service-Domain passend zur Entity-Domain:** `GenericInverterAdapter.build_set_limit_command(device, watts)` nutzt die Domain der Entity (`number.set_value` fuer `number.*`, `input_number.set_value` fuer `input_number.*`) und bleibt beim Payload `{"entity_id": device.entity_id, "value": watts}`.
6. **Generic-Drossel-Overrides:** `GenericInverterAdapter.get_drossel_params(device)` nutzt Defaults `deadband_w=10`, `min_step_w=5`, `smoothing_window=5`, `limit_step_clamp_w=200` und liest optionale Overrides aus `device.config_json`. `DrosselParams.__post_init__` validiert das Ergebnis hart.
7. **Generic-Limit-Range-Overrides:** `GenericInverterAdapter.get_limit_range(device)` nutzt Defaults `(2, 3000)` W und liest optionale Overrides `min_limit_w` und `max_limit_w` aus `device.config_json`.
8. **Forward-only Migration:** Neue Migration `backend/src/solalex/persistence/sql/003_adapter_key_rename.sql` setzt in `devices.adapter_key` und `devices.type` die alten Keys `hoymiles -> generic` und `shelly_3em -> generic_meter`. Kein Downgrade-Pfad.
9. **API-Schema-Keywechsel:** `HardwareConfigRequest.hardware_type` akzeptiert `"generic" | "marstek_venus"`. Old-key `"hoymiles"` wird vom Pydantic-Schema mit 422 abgewiesen.
10. **Backend-Save- und Funktionstest-Flows:** `POST /api/v1/devices/` speichert WR als `type="generic", adapter_key="generic"` und optionale Grid-Meter als `type="generic_meter", adapter_key="generic_meter"`. `POST /api/v1/setup/test` sucht steuerbare WR ueber `adapter_key == "generic"` und verwendet generische deutsche Fehlermeldungen ohne Hoymiles-Only-Text.
11. **Frontend-Konfiguration:** `Config.svelte` zeigt die Tiles `Wechselrichter (allgemein)` mit Sub-Label `z. B. Hoymiles/OpenDTU, Trucki, ESPHome` und `Marstek Venus 3E/D`. Die Smart-Meter-Checkbox heisst `Smart Meter zuordnen` mit Sub-Label `z. B. Shelly 3EM, ESPHome SML, Tibber`. Frontend-Types nutzen `hardware_type: 'generic' | 'marstek_venus'`.
12. **Frontend-Labels:** `FunctionalTest.svelte` und `Running.svelte` mappen `generic -> "Wechselrichter"`, `marstek_venus -> "Marstek Venus"` und vermeiden neue Hoymiles-only Copy. Kommentare sprechen generisch von WR-Adapter-Rate-Limit.
13. **Test-Key-Sweep:** Alle Backend-Tests mit `adapter_key="hoymiles"` oder `"shelly_3em"` sind auf `generic` bzw. `generic_meter` umgestellt. Frontend-Tests (`client.test.ts`, `gate.test.ts`, `Running.test.ts` und betroffene Route-Tests) ebenfalls.
14. **Smoke-Test-Doku:** `_bmad-output/qa/manual-tests/smoke-test.md` ist aktualisiert: §1.2 Compat-Vor-Befund entfaellt; Variante A/B kollabieren zu einem direkten Pfad. Template-Helper-Anhang §5/§6 bleibt als optionale Edge-Case-Doku fuer Entities ohne `unit_of_measurement`.
15. **CI-Gates:** Backend-Gates `ruff`, `mypy --strict`, `pytest`; Frontend-Gates `eslint`, `svelte-check`, `prettier --check`, `vitest`; und SQL-Migration-Ordering laufen gruen. Smoke-Test gegen Alex' reales HA-Setup (Trucki ESPHome `input_number.t2sgf72a29_*` + ESPHome SML `sensor.00_smart_meter_sml_current_load`) ist als Manual-QA zu dokumentieren.

## Tasks / Subtasks

- [x] **Task 1: Adapter-Dateien refitten und Registry umstellen** (AC 1, 2, 3, 4, 5, 6, 7)
  - [x] `backend/src/solalex/adapters/generic.py` aus `hoymiles.py` ableiten; Klasse, Docstring, Detection, Service-Domain, `parse_readback`, Defaults und `config_json`-Overrides implementieren.
  - [x] `backend/src/solalex/adapters/generic_meter.py` aus `shelly_3em.py` ableiten; Klasse, Docstring, Detection und read-only Fehlertexte generisch halten.
  - [x] `backend/src/solalex/adapters/__init__.py` auf Registry-Keys `generic`, `generic_meter`, `marstek_venus` umstellen.
  - [x] Alte Module `hoymiles.py` und `shelly_3em.py` entfernen, sofern keine Imports mehr darauf zeigen.
  - [x] Tests zuerst anlegen/anpassen: Detection fuer `input_number.*` + `W`, `number.*` + `kW`, Sensor-Meter mit `_current_load`, kW-Readback-Konvertierung, Service-Domain `input_number.set_value`, Drossel-Override und Limit-Range-Override.

- [x] **Task 2: Backend API, Setup-Flow und Migration nachziehen** (AC 8, 9, 10)
  - [x] `backend/src/solalex/api/schemas/devices.py`: `HardwareConfigRequest.hardware_type` auf `Literal["generic", "marstek_venus"]` aendern.
  - [x] `backend/src/solalex/api/routes/devices.py`: gespeicherte WR- und Grid-Meter-Records auf `generic` / `generic_meter` umstellen.
  - [x] `backend/src/solalex/api/routes/setup.py`: Funktionstest sucht `generic`-WR, Variablennamen und Fehlermeldungen generisch.
  - [x] Neue SQL-Migration `backend/src/solalex/persistence/sql/003_adapter_key_rename.sql` mit vier `UPDATE`-Statements fuer `adapter_key` und `type`.
  - [x] Migrationstest erweitern: vor Version 3 vorhandene `hoymiles`/`shelly_3em` Rows werden nach Migration korrekt auf neue Keys umgeschrieben; `_migration_files()` bleibt lueckenlos.

- [x] **Task 3: Backend-Test-Sweep und Regressionen** (AC 3, 4, 5, 6, 7, 8, 10, 13, 15)
  - [x] `backend/tests/unit/test_adapters.py`, `test_hoymiles_drossel_params.py`, `test_executor_dispatcher.py`, `test_setpoint_provider.py`, `test_readback.py`, `test_debug_traces.py`, `test_devices_repo.py`, `_controller_helpers.py` und Integrationstests nach neuen Keys aktualisieren.
  - [x] Test-Helper `seeded_device()` Default-Adapter auf `generic` setzen; Marstek-spezifische Tests unveraendert halten.
  - [x] Sicherstellen, dass Controller, Executor, BatteryPool und KPI-Code nicht wegen Vendor-Key-Annahmen angepasst werden muessen. Nur Adapter-Registry-Keys und Test-Fixtures sollen sich aendern.
  - [x] Backend-Gates ausfuehren: `cd backend && uv run ruff check . && uv run mypy . && uv run pytest`.

- [x] **Task 4: Frontend-Types, Config-UI und Labels aktualisieren** (AC 11, 12, 13)
  - [x] `frontend/src/lib/api/types.ts`: `hardware_type` auf `'generic' | 'marstek_venus'`.
  - [x] `frontend/src/routes/Config.svelte`: State-Typ, `selectType`, Tile-Key, Labels, Empty-State-Hinweis und Smart-Meter-Checkbox/Sub-Label aktualisieren.
  - [x] `frontend/src/routes/FunctionalTest.svelte`: `hardwareLabel()` auf `generic -> "Wechselrichter"`; keine Hoymiles-only Copy.
  - [x] `frontend/src/routes/Running.svelte` und Tests: Adapter-Key-Fixtures und Kommentare auf `generic` / `generic_meter`.
  - [x] Frontend-Gates ausfuehren: `cd frontend && npm run lint && npm run check && npm test && npm run build`; fuer Prettier, falls kein Check-Script existiert: `npx prettier --check .`.

- [x] **Task 5: Smoke-Test-Doku und Final Verification** (AC 14, 15)
  - [x] `_bmad-output/qa/manual-tests/smoke-test.md` aktualisieren, falls vorhanden; wenn Datei fehlt, im Dev Agent Record dokumentieren und nicht erfinden.
  - [x] `rg "hoymiles|shelly_3em|Shelly 3EM|Hoymiles"` pruefen und nur legitime historische Doku-/v1.5-Hinweise stehen lassen. Produktiver Code, Tests und UI duerfen keine alten Day-1-Keys mehr verwenden.
  - [x] Manual-QA-Ergebnis fuer Alex' reales HA-Setup dokumentieren: ST-00 bis ST-05 mit Trucki `input_number.t2sgf72a29_*` und ESPHome SML `sensor.00_smart_meter_sml_current_load`. Falls nicht lokal verifizierbar, explizit als Alex-Manual-QA offen lassen und Story trotzdem nicht als technisch vollstaendig behaupten.

## Dev Notes

### Architektur-Bezugspunkte

- **Architecture Amendment 2026-04-25:** Generic-First Adapter-Layer ersetzt Day-1 Hoymiles/Shelly durch `generic.py` und `generic_meter.py`; Marstek bleibt vendor-spezifisch. `AdapterBase` bleibt unveraendert; Controller/Executor/KPI/BatteryPool sprechen ueber Interface, nicht Vendor-Identitaet. [Source: `_bmad-output/planning-artifacts/architecture.md` Amendment 2026-04-25]
- **Sprint Change Proposal 2026-04-25:** Beta-Launch-blocking Refit wegen realer Smoke-Test-Hardware: Trucki nutzt `input_number.*_set_target`, ESPHome SML nutzt `sensor.*_current_load`. [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-25.md`]
- **CLAUDE.md Hardware Day-1:** Day-1 v1 ist jetzt generischer Wechselrichter, Marstek Venus 3E/D, generischer Smart Meter. Kein JSON-Template-Loader, kein `/data/templates/`, kein JSON-Schema-Validator. [Source: `CLAUDE.md` Hardware Day-1 und Stop-Signal-Liste]
- **Epic 2 Story 2.4:** Die Story ist in `epics.md` bereits eingefuegt; diese Datei ist die implementierungsfaehige Story-Fassung. [Source: `_bmad-output/planning-artifacts/epics.md` Story 2.4]

### Aktueller Codezustand und Zielaenderungen

- `backend/src/solalex/adapters/base.py` definiert die stabile Schnittstelle: `detect`, `build_set_limit_command`, `build_set_charge_command`, `parse_readback`, `get_rate_limit_policy`, `get_readback_timing`, optionale `get_limit_range`, `get_drossel_params`, `get_speicher_params`. Nicht erweitern.
- `hoymiles.py` ist aktuell regex-basiert (`^number\..+_limit_nonpersistent_absolute$`), `adapter_key="hoymiles"`, Range `(2, 1500)`, Drossel-Params `5/3/5/200`. Ziel: `generic.py`, capability-basiert ueber Domain + UoM, `adapter_key="generic"`, Range `(2, 3000)`, Drossel-Defaults `10/5/5/200` plus `config_json`-Overrides.
- `shelly_3em.py` ist aktuell regex-basiert (`^sensor\..+_(total_)?power$`), `adapter_key="shelly_3em"`. Ziel: `generic_meter.py`, Sensor + UoM `W|kW`, `adapter_key="generic_meter"`, weiterhin read-only.
- `backend/src/solalex/api/routes/setup.py` waehlt aktuell das steuerbare Testgeraet ueber `adapter_key == "hoymiles"`; diese Vendor-Annahme muss auf `generic` wechseln. Die Rolle `wr_limit` bleibt der wichtigere Sicherheitsfilter.
- `backend/src/solalex/api/routes/devices.py` speichert aktuell WR als Hoymiles und Grid-Meter als Shelly; diese Save-Route muss neue Keys schreiben, weil neue Installationen sonst direkt alte Keys in die DB bringen.
- `frontend/src/routes/Config.svelte` ist noch Hoymiles/Shelly-getextet; der Flow bleibt gleich, nur Typ-Key und Copy aendern sich.

### Implementation Guardrails

- **Kein Capability-Framework:** Kein Confidence-Score-System, keine neue Detection-Schicht, keine neue Dependency. Diese Story ist ein direkter Refit, kein Architektur-Neubau.
- **Keine JSON-Templates:** `device.config_json` darf nur die expliziten optionalen Override-Keys tragen. Keine Dateien in `/data/templates/`, keine JSON-Schema-Validierung.
- **Keine UI fuer Overrides:** `deadband_w`, `min_step_w`, `smoothing_window`, `limit_step_clamp_w`, `min_limit_w`, `max_limit_w` werden nur backendseitig gelesen. UI-Exposure ist v1.5-Scope.
- **Marstek nicht anfassen ausser Tests/Imports:** Marstek bleibt vendor-spezifisch und muss weiter funktionieren.
- **Closed-loop Readback bleibt Pflicht:** Readback-Parsing bleibt im Adapter, Verifikation im Executor/Setup-Flow. Nicht umgehen, nicht abschwaechen.
- **Key-Migration ist Forward-only:** Kein Alembic, kein Downgrade. Backup-File-Replace ist der Rollback-Mechanismus.
- **Historische Docs duerfen alte Namen behalten:** Alte abgeschlossene Story-Dateien, PRD-Altstellen oder v1.5-Hinweise koennen weiter Hoymiles/Shelly nennen. Produktiver Code, aktive Tests, API-Types und aktuelle Smoke-Test-Doku muessen auf neue Day-1-Keys umgestellt sein.

### File Structure Requirements

Zielzustand der relevanten Adapterstruktur:

```text
backend/src/solalex/adapters/
├── __init__.py          [MOD: Registry generic/generic_meter/marstek_venus]
├── base.py              [UNCHANGED]
├── generic.py           [NEW: GenericInverterAdapter]
├── generic_meter.py     [NEW: GenericMeterAdapter]
└── marstek_venus.py     [UNCHANGED]
```

Zu erwartende weitere Aenderungen:

- `backend/src/solalex/api/schemas/devices.py`
- `backend/src/solalex/api/routes/devices.py`
- `backend/src/solalex/api/routes/setup.py`
- `backend/src/solalex/persistence/sql/003_adapter_key_rename.sql`
- Backend-Tests unter `backend/tests/unit/` und `backend/tests/integration/`
- `frontend/src/lib/api/types.ts`
- `frontend/src/routes/Config.svelte`
- `frontend/src/routes/FunctionalTest.svelte`
- `frontend/src/routes/Running.svelte`
- Frontend-Tests unter `frontend/src/**/*.test.ts`
- `_bmad-output/qa/manual-tests/smoke-test.md`, falls vorhanden

### Testing Requirements

- Adapter-Unit-Tests muessen die neuen Detection-Regeln beweisen:
  - `input_number.t2sgf72a29_t2sgf72a29_set_target` + `unit_of_measurement="W"` wird als `wr_limit`/`generic` erkannt.
  - `number.opendtu_limit_nonpersistent_absolute` + `unit_of_measurement="W"` bleibt erkannt.
  - `number.some_limit` + `unit_of_measurement="kW"` wird erkannt; `parse_readback` konvertiert kW zu W.
  - `sensor.00_smart_meter_sml_current_load` + `unit_of_measurement="W"` wird als `grid_meter`/`generic_meter` erkannt.
  - Sensoren ohne `W|kW` werden nicht als Meter erkannt.
- Override-Tests:
  - `DeviceRecord(config_json='{"deadband_w": 12, "min_step_w": 7, "smoothing_window": 3, "limit_step_clamp_w": 150}')` liefert genau diese DrosselParams.
  - Ungueltige Overrides muessen ueber `DrosselParams.__post_init__` `ValueError` ausloesen.
  - `min_limit_w`/`max_limit_w` werden aus `config_json` gelesen.
- Migration-Test:
  - Eine DB mit alten Keys wird nach Migration 003 auf neue `type` und `adapter_key` umgeschrieben.
  - Migration bleibt idempotent und die Nummerierung bleibt contiguous.
- API/Frontend-Tests:
  - `saveDevices({ hardware_type: 'generic', ... })` postet neue Keys.
  - Old-key `'hoymiles'` ist TypeScript- und Pydantic-seitig nicht mehr gueltig.
  - Gate-/Running-Fixtures verwenden `generic`, `generic_meter`.

### Previous Story Intelligence

- Story 2.3a hat den Frontend-Teststack erweitert: `happy-dom`, `@testing-library/svelte`, `@testing-library/jest-dom`, `vitest.config.ts` und pure Gate-Tests sind vorhanden. Wiederverwenden statt neue Test-Infrastruktur aufzubauen. [Source: `_bmad-output/implementation-artifacts/2-3a-pre-setup-disclaimer-gate.md`]
- Story 4.0 verweist auf wiederverwendbare Backend-Testhelfer: `FakeHaClient`, `make_db_factory`, `seeded_device` aus `backend/tests/unit/_controller_helpers.py`. Diese Helper anpassen statt parallel neue Fakes zu bauen. [Source: `_bmad-output/implementation-artifacts/4-0-debug-logging-toggle-und-hot-path-debug-trace.md`]
- Mehrere alte Tests nutzen Default `adapter_key="hoymiles"`; ein globaler Search/Replace braucht danach gezielte fachliche Nacharbeit, weil historische Doku und v1.5-Hinweise nicht alle geaendert werden sollen.

### Git Intelligence

- Letzter relevanter Commit: `c2c2343 docs: Sprint Change Proposal 2026-04-25 + Generic-First Adapter-Layer`. Die Planungsartefakte sind bereits aktualisiert; nur die Story-Datei und spaeter die Implementierung fehlten.
- Release-Commits davor (`0.1.1-beta.7`, `0.1.1-beta.6`) zeigen: keine neue Runtime-Dependency fuer diesen Refit einfuehren; bestehende FastAPI/Svelte/aiosqlite-Struktur beibehalten.

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
npx prettier --check .
```

Repository-/Drift-Checks:

```bash
rg "hoymiles|shelly_3em|Shelly 3EM|Hoymiles" backend frontend _bmad-output/qa/manual-tests CLAUDE.md
```

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Backend: `uv run ruff check .` -> gruen; `uv run mypy .` -> gruen; `uv run pytest` -> 258 passed.
- Frontend: `npm run lint` -> gruen; `npm run check` -> 0 errors/warnings; `npm test` -> 53 passed; `npm run build` -> erfolgreich mit Node-Warnung (lokal 20.17.0, Vite empfiehlt 20.19+); scoped Prettier-Check auf Story-Dateien -> gruen.
- Drift-Check: `rg "hoymiles|shelly_3em|Shelly 3EM|Hoymiles" backend frontend _bmad-output/qa/manual-tests CLAUDE.md` zeigt nur noch Migration-Altwerte, Beispiele, v1.5-Hinweise und Hardware-Beispiele.

### Completion Notes List

- 2026-04-25: Story-Datei aus Sprint-Status, Sprint Change Proposal 2026-04-25, `epics.md`, Architecture Amendment 2026-04-25, CLAUDE.md und aktuellem Codezustand rekonstruiert. Keine Produktivcode-Implementierung in diesem Schritt.
- 2026-04-25: Generic-Inverter-Adapter und Generic-Meter-Adapter implementiert; alte Vendor-Adapter `hoymiles.py` und `shelly_3em.py` entfernt; Registry auf `generic`, `generic_meter`, `marstek_venus` umgestellt.
- 2026-04-25: API-Schema, Save-Route, Funktionstest-Zielsuche und Migration 003 auf neue Keys umgestellt.
- 2026-04-25: Backend- und Frontend-Tests auf neue Keys aktualisiert; neue Adapter-/Migrationstests fuer Generic-Detection, `input_number`-Service-Domain, kW-Konvertierung, `config_json`-Overrides und alte-Key-Migration ergaenzt.
- 2026-04-25: Config-UI, Functional-Test-Label, Running-Kommentar und Smoke-Test-Doku auf Generic-First-Normalpfad aktualisiert.
- 2026-04-25: Manual-QA gegen echtes HA-Setup bleibt als Smoke-Test-Ausfuehrung durch Alex offen; die Doku beschreibt jetzt den erwarteten direkten Trucki/ESPHome-SML-Pfad.

### File List

- `CLAUDE.md`
- `_bmad-output/implementation-artifacts/2-4-generic-adapter-refit.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/qa/manual-tests/smoke-test.md`
- `backend/src/solalex/adapters/__init__.py`
- `backend/src/solalex/adapters/base.py`
- `backend/src/solalex/adapters/generic.py`
- `backend/src/solalex/adapters/generic_meter.py`
- `backend/src/solalex/adapters/hoymiles.py` (deleted)
- `backend/src/solalex/adapters/marstek_venus.py`
- `backend/src/solalex/adapters/shelly_3em.py` (deleted)
- `backend/src/solalex/api/routes/devices.py`
- `backend/src/solalex/api/routes/setup.py`
- `backend/src/solalex/api/schemas/devices.py`
- `backend/src/solalex/controller.py`
- `backend/src/solalex/persistence/sql/003_adapter_key_rename.sql`
- `backend/tests/integration/test_commission.py`
- `backend/tests/integration/test_devices_api.py`
- `backend/tests/integration/test_setup_entities.py`
- `backend/tests/integration/test_setup_test.py`
- `backend/tests/unit/_controller_helpers.py`
- `backend/tests/unit/test_adapters.py`
- `backend/tests/unit/test_battery_pool.py`
- `backend/tests/unit/test_control_cycles_repo.py`
- `backend/tests/unit/test_control_state.py`
- `backend/tests/unit/test_controller_drossel_policy.py`
- `backend/tests/unit/test_controller_speicher_policy.py`
- `backend/tests/unit/test_debug_traces.py`
- `backend/tests/unit/test_devices_repo.py`
- `backend/tests/unit/test_executor_dispatcher.py`
- `backend/tests/unit/test_executor_rate_limiter.py`
- `backend/tests/unit/test_generic_drossel_params.py`
- `backend/tests/unit/test_hoymiles_drossel_params.py` (renamed)
- `backend/tests/unit/test_latency_repo.py`
- `backend/tests/unit/test_marstek_venus_speicher_params.py`
- `backend/tests/unit/test_middleware.py`
- `backend/tests/unit/test_migrate.py`
- `backend/tests/unit/test_readback.py`
- `frontend/src/lib/api/client.test.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/gate.test.ts`
- `frontend/src/routes/Config.svelte`
- `frontend/src/routes/FunctionalTest.svelte`
- `frontend/src/routes/Running.svelte`
- `frontend/src/routes/Running.test.ts`

### Review Findings

Aus Code-Review 2026-04-25 (3-Layer adversarial: Blind Hunter / Edge Case Hunter / Acceptance Auditor).

- [x] [Review][Patch] Setup-Endpoint Entity-Listing diverged von Adapter-Capability — `generic.detect()` akzeptiert `kW` und `input_number.*`, aber `setup.py` Endpoint filtert nur `eid.startswith("number.")` und `uom == "W"`. Trucki-/kW-User sehen leere WR-Liste obwohl Adapter funktioniert. **High** [`backend/src/solalex/api/routes/setup.py:96`]
- [x] [Review][Patch] `Running.svelte` und `FunctionalTest.svelte` ohne Mapping für `generic_meter` → fällt auf "Unbekannte Hardware" zurück. **Medium** [`frontend/src/routes/Running.svelte`, `frontend/src/routes/FunctionalTest.svelte`]
- [x] [Review][Patch] `config_json`-Overrides ungeprüft — `int(None)`, `int("abc")`, negative Werte, `min_limit_w > max_limit_w` crashen Executor oder vetoen alle Writes silent. Validierung in `get_limit_range`/`get_drossel_params` mit klarer Fehlermeldung. **Medium** [`backend/src/solalex/adapters/generic.py:75-90`]
- [x] [Review][Patch] Migration 003 nicht in Transaktion — bei Crash zwischen den 4 UPDATEs Mismatch `type='generic'` aber `adapter_key='hoymiles'` möglich. `BEGIN/COMMIT` ergänzen. **Medium** [`backend/src/solalex/persistence/sql/003_adapter_key_rename.sql`]
- [x] [Review][Patch] `test_battery_pool.py` Vendor-Leak-Guard sucht Substring `"generic"` — false-positive- und false-negative-Risiko. Set auf strikte Vendor-Namen reduzieren. **Medium** [`backend/tests/unit/test_battery_pool.py:467`]
- [x] [Review][Patch] UI Config-Step für `min_limit_w` / `max_limit_w` Override — Default-Range `(2, 3000)` vetoed >3 kW Inverter und blockiert `0 W`-Aus. Frontend-Felder ergänzen, die ins `device.config_json` schreiben. **High** (D3-Decision) [`frontend/src/routes/Config.svelte`]
- [x] [Review][Patch] `generic_meter.parse_readback` von `int(raw)` auf `round(raw)` umstellen — Konsistenz mit `generic.py`. **Low** (D4-Decision) [`backend/src/solalex/adapters/generic_meter.py:56`]
- [x] [Review][Patch] `parse_readback` UoM case-/whitespace-sensitive (`"kw"`, `"W "` werden falsch interpretiert). `.strip().casefold()` vor Vergleich. **Low** [`backend/src/solalex/adapters/generic.py:62`, `generic_meter.py:53`]
- [x] [Review][Patch] `parse_readback` NaN/Inf — `round(inf)` raises `OverflowError`, escapt aktuellen `(ValueError, TypeError)` catch. `math.isfinite`-Guard. **Low** [`backend/src/solalex/adapters/generic.py:64`]
- [x] [Review][Patch] `test_controller_drossel_policy.py:184` Docstring sagt „min_step_w=3 und deadband_w=5" — neue Defaults sind `min_step_w=5, deadband_w=10`. **Low** [`backend/tests/unit/test_controller_drossel_policy.py:184`]
- [x] [Review][Patch] Stale Kommentar `# generic → (2, 1500)` — Range ist `(2, 3000)`. **Nit** [`backend/tests/unit/test_executor_dispatcher.py:36`]
- [x] [Review][Patch] Negativ-Test fehlt: `HardwareConfigRequest` mit `hardware_type="hoymiles"` muss 422 returnen. 1-Liner-Test. **Low** [`backend/tests/unit/test_middleware.py`]
- [x] [Review][Patch] `Config.svelte` `allEntitiesEmpty` zeigt Globalbanner nur wenn alle drei Listen leer — WR-Liste leer + Meter-Liste voll = Dead-End-UX nicht signalisiert. **Low** [`frontend/src/routes/Config.svelte:35-41`]
- [x] [Review][Patch] `friendly_name`-Fallback zeigt Entity-ID doppelt („`number.x (number.x)`"). Fallback nur Label oder leeren String. **Nit** [`frontend/src/routes/Config.svelte`]
- [x] [Review][Defer] Generic-Inverter `detect()` zu permissiv — akzeptiert jedes `number`/`input_number` mit W/kW als `wr_limit` ohne `device_class`-Filter. **High** — deferred, Beta-Scope, User wählt Entity bewusst.
- [x] [Review][Defer] Generic-Meter `detect()` ohne Sign-Convention-Check — invertierte Vorzeichen-Konventionen führen zu positivem Feedback in der Speicher-Policy. **High** — deferred, Beta-Scope.
- [x] [Review][Defer] AC15 Manual-QA gegen Alex' echte Hardware (Trucki ESPHome + ESPHome SML) noch offen — kein Code-Issue, Alex testet manuell.
- [x] [Review][Defer] AC14 Smoke-Test-Doku nur oberflächlich verifiziert — User-Cross-Check empfohlen.
- [x] [Review][Defer] Duplicate `entity_id` Detection nicht dedupliziert — pre-existing, UNIQUE-Constraint im Save-Layer fängt es.
- [x] [Review][Defer] `HardwareConfigRequest` akzeptiert Marstek-Felder mit `hardware_type='generic'` und droppt sie silent — pre-existing.
- [x] [Review][Defer] 422-Fehlertext bei legacy `"hoymiles"`-Request ohne Cache-Clear-Hint — UX-Polish, nicht blockierend.
- [x] [Review][Defer] Marstek-Tile nicht disabled wenn `socEntities.length === 0` — UX-Polish.
- [x] [Review][Defer] Functional-Test Target-Priorität generic > marstek (hybrid-Setup edge case).
- [x] [Review][Defer] `parse_readback` "unavailable"/"unknown" nicht distinkt von Junk-Werten — pre-existing, beide → `None`.

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-25 | 0.1.0 | Fehlende Implementierungsstory fuer Story 2.4 erstellt. Enthält ACs, Tasks, Dev Notes, Architektur-Guardrails, Codezustand, Testanforderungen und Validation Commands fuer den Generic-First Adapter-Refit. | GPT-5 Codex |
| 2026-04-25 | 0.2.0 | Story 2.4 implementiert: Generic-Inverter/Generic-Meter-Adapter, DB-Migration 003, Backend/API/Setup-Keywechsel, Frontend-Labels/Types, Smoke-Test-Doku und Test-Sweep. Backend 258 Tests gruen, Ruff/MyPy gruen; Frontend Lint/Svelte-Check/Vitest/Build gruen, scoped Prettier gruen. Status -> review. | GPT-5 Codex |
