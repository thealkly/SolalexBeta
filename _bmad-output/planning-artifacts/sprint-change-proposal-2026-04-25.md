# Sprint Change Proposal — 2026-04-25

**Trigger:** „Wir müssen uns überlegen, ich hätte gerne ein generisches Programm, das alle WR und Akkus aus Home Assistant unterstützt. Wie schaffen wir es, dass wir nicht für jeden Hersteller ein Python anlegen müssen, sondern irgendwie das generischer machen können — aber trotzdem Auto-Detection mal anbieten können? Könnten wir nicht aktuell den Hoymiles umbenennen zu Generic? Das ist einfacher für einen simplen Beta-Test."

**Mode:** Batch
**Autor:** Alex (Solo-Dev) + Claude Opus 4.7
**Scope-Klassifikation:** **Moderate** — Backlog-Erweiterung um eine Story in Epic 2, ein DB-Migrations-File, ein Architecture-Amendment, ein CLAUDE.md-Update. Kein PRD-Cut, kein fundamentaler Replan, keine Story-Rollbacks.

---

## 1. Issue Summary

Beim Vorbereiten des manuellen Smoke-Tests gegen Alex' eigenes HA-Setup (Trucki-ESPHome-Stick als Hoymiles-Wrapper, ESPHome-SML-Smart-Meter, Victron-Akku via ESPHome) ist aufgefallen, dass **keine** der drei Day-1-Adapter-Patterns matcht:

- Hoymiles-Pattern erwartet `^number\..+_limit_nonpersistent_absolute$` — Trucki nutzt aber Domain `input_number` und Suffix `_set_target`.
- Shelly-3EM-Pattern erwartet `^sensor\..+_(total_)?power$` — ESPHome-SML benutzt Suffix `_current_load`.
- Marstek-Venus-Pattern erwartet `^sensor\..+(battery_)?soc$` — Victron-SoC matcht zufällig (`state_of_charge` enthält `soc`), aber das ist Glück, kein Design.

Symptomatik: Der Smoke-Test (`_bmad-output/qa/manual-tests/smoke-test.md` §1.2) beschreibt einen erwarteten Block bei ST-02 mit zwei Workaround-Varianten — entweder ehrliche Block-Dokumentation (Variante A) oder Template-Helper-Frickelei in HA (Variante B). Beides ist Reibung, die der reale Beta-Tester nicht akzeptieren kann.

**Tieferes Problem:** Die drei Adapter-Module sind strukturell ~80 % Boilerplate. Nur die Drossel-/Speicher-Tuning-Parameter und die Hardware-Range sind tatsächlich vendor-spezifisch — der Rest (Service-Domain, Service-Name, Readback-Parsing, Detection-Logik) ist HA-Standard. Die in Architecture Amendment 2026-04-22 getroffene Entscheidung „ein Modul pro Vendor + hardcoded Patterns" hat den Re-Use unterschätzt.

**Kategorie:** Technische Limitation, im realen Smoke-Test entdeckt. Nicht: Misverständnis, kein Pivot, keine Strategieänderung — nur eine empirische Korrektur einer Architektur-Annahme.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Betroffen | Art der Änderung |
|------|-----------|------------------|
| Epic 1 | Nein | `done`, unverändert |
| **Epic 2** | **Ja** | Neue **Story 2.4 — Generic-Adapter-Refit** (Hoymiles + Shelly konsolidieren). Stories 2.1/2.2/2.3 bleiben `done`, werden technisch nachgezogen. |
| Epic 3 | Indirekt | Story 3.1/3.2/3.3 sind `done` und funktionieren mit dem umbenannten Adapter unverändert (Interface-stabil). Stories 3.4–3.7 ebenfalls — `wr_charge` bleibt Marstek-only. |
| Epic 4 | Nein | |
| Epic 5 | Indirekt | Story 5.1a (`done`) zeigt `adapter_key` im UI — Frontend-Strings + types.ts ziehen automatisch nach. |
| Epic 6 | Nein | |
| Epic 7 | Nein | |

### Story Impact

- **Neu: Story 2.4 — „Generic-Adapter-Refit (Hoymiles → Generic, Shelly → Generic-Meter)"** — Nachzieh-Story zu Epic 2. Vor Beta-Launch zwingend. Sprint-Status: `ready-for-dev` direkt, weil Architektur-Entscheidung in diesem Proposal getroffen wird.
- **Geändert: Story 1.5/2.1/2.2/2.3 (alle `done`)** — Werden im Rahmen von 2.4 mit umetikettierten `adapter_key`-Werten weiter funktionieren. Acceptance-Kriterien bleiben gültig (sie sprechen von „Wechselrichter" generisch, nicht von „Hoymiles").
- **Story 5.1a (`done`)** — Frontend-Type-Update zieht automatisch nach. Keine AC-Änderung nötig.

### Artefakt-Konflikte

| Artefakt | Änderung | Aufwand |
|----------|----------|---------|
| `architecture.md` | **Amendment 2026-04-25** — Hardware-Adapter-Layer wird auf Generic-First umgestellt. Marstek bleibt Vendor-Adapter. JSON-Template-Verbot aus Amendment 2026-04-22 bleibt erhalten — keine neuen Templates. | ~30 min |
| `CLAUDE.md` | Hardware-Day-1-Liste umschreiben (Hoymiles + Shelly raus, Generic + Generic-Meter rein); Stolperstein-Liste anpassen (Hoymiles-Stop entfällt). | ~15 min |
| `epics.md` | Neue Story 2.4 unter Epic 2 einfügen mit AC. | ~30 min |
| `sprint-status.yaml` | Eintrag Story 2.4 als `ready-for-dev` hinzufügen. | ~5 min |
| `prd.md` | **Keine** Änderung — PRD spricht generisch von „Wechselrichter / Smart Meter", nicht von „Hoymiles / Shelly" (PRD-Linien 181, 392 referenzieren Hoymiles/Marstek nur als Tuning-Beispiele). | 0 min |
| `ux-design-specification.md` | **Keine** strukturelle Änderung. Wizard-Step-Bezeichnung bleibt „Hardware konfigurieren". | 0 min |
| `_bmad-output/qa/manual-tests/smoke-test.md` | §1.2 Compat-Vor-Befund + Variante A/B kollabieren zu einem direkten Pfad. ⚠ Achtung: Variante B (Template-Helper-Anhang §5/§6) bleibt als optionale Doku — wer auch ohne `device_class`-Attribute testen will, kann die Helper weiter nutzen. | ~30 min |

### Technischer Impact

#### Backend (15 Files)

- **`backend/src/solalex/adapters/hoymiles.py` → `backend/src/solalex/adapters/generic.py`** — Klasse `HoymilesAdapter` → `GenericInverterAdapter`. Patterns lockern auf HA-Capabilities (siehe §4 Detail).
- **`backend/src/solalex/adapters/shelly_3em.py` → `backend/src/solalex/adapters/generic_meter.py`** — Klasse `Shelly3EmAdapter` → `GenericMeterAdapter`. Pattern leicht lockern.
- **`backend/src/solalex/adapters/__init__.py`** — Registry: `"generic": generic.ADAPTER`, `"generic_meter": generic_meter.ADAPTER`, `"marstek_venus": …`.
- **`backend/src/solalex/api/routes/devices.py:67-115`** — `hardware_type == "hoymiles"` → `"generic"`; `adapter_key="hoymiles"` → `"generic"`; `adapter_key="shelly_3em"` → `"generic_meter"`.
- **`backend/src/solalex/api/routes/setup.py:170-179`** — Variablen-Rename `hoymiles_devices` → `generic_inverters`; Filter-String entsprechend; Fehlertext anpassen.
- **`backend/src/solalex/api/schemas/devices.py:14`** — `Literal["hoymiles", "marstek_venus"]` → `Literal["generic", "marstek_venus"]`.
- **`backend/src/solalex/persistence/sql/003_adapter_key_rename.sql`** — Forward-Only-Migration (siehe §4).
- **Tests (17 Files)** — Alle `adapter_key="hoymiles"` → `"generic"`, alle `adapter_key="shelly_3em"` → `"generic_meter"`. Pattern-Tests in `test_adapters.py` an gelockerte Detection anpassen.

#### Frontend (5 Files)

- **`frontend/src/lib/api/types.ts:13`** — `hardware_type: 'hoymiles' | 'marstek_venus'` → `'generic' | 'marstek_venus'`.
- **`frontend/src/routes/Config.svelte`** — Type-Annotation, `selectType`-Argument, Tile-Klasse, Tile-Label, Sektions-Label-Text-Bedingung, Smart-Meter-Checkbox-Label.
- **`frontend/src/routes/FunctionalTest.svelte:107`** — Label-Lookup `'hoymiles'` → `'generic'` mit Anzeige-Text „Wechselrichter".
- **`frontend/src/routes/Running.svelte:97`** — Nur Kommentar-Update („Hoymiles' 60 s rate-limit" → „WR-Adapter-typisch 60 s rate-limit").
- **Tests (3 Files)** — `gate.test.ts`, `Running.test.ts`, `client.test.ts` mit den neuen Adapter-Keys.

#### Migration-Risiko

- **Beta noch nicht released** — keine Production-User mit `adapter_key='hoymiles'` in der DB. Migration kann ohne Restore-Pfad nach vorn.
- **Alex' eigenes Test-HA** — falls dort schon Devices commissioned wurden, fängt das Migrations-`UPDATE` sie auf. Kein manuelles Eingreifen nötig.
- **Forward-Only**, kein Downgrade-Pfad — entspricht Architecture-Vorgabe (Backup-File-Replace beim Restart der Vorgängerversion, kein Alembic).

#### CI-Gates

- **Ruff + MyPy strict + Pytest** — alle Test-Renames notwendig, sonst Fail.
- **ESLint + svelte-check + Prettier + Vitest** — Type-Update + Tests notwendig.
- **Egress-Whitelist** — unverändert.
- **SQL-Migrations-Ordering** — `003_adapter_key_rename.sql` ist nächste freie Nummer, lückenlos.

---

## 3. Recommended Approach

**Direct Adjustment (Option 1 aus Change-Checklist).** Der Refit erfolgt als eigenständige Story 2.4 *innerhalb* der bestehenden Epic-Struktur, ohne Rollback bestehender Stories. Stories 2.1/2.2/2.3 werden nicht „re-opened" — ihre Acceptance-Kriterien bleiben erfüllt, weil sie generisch von „Wechselrichter" sprechen. Story 2.4 ist ein Refactoring-Layer obendrauf.

### Rationale

| Kriterium | Bewertung |
|---|---|
| Implementierungs-Aufwand | **niedrig–mittel** — ~1 Tag Backend + Migration, ~½ Tag Frontend, ~½ Tag Test-Sweep + Smoke-Test-Doku-Cleanup. Keine neue Library, keine neue Architektur-Schicht. |
| Technisches Risiko | **niedrig** — `AdapterBase`-Interface bleibt stabil, Controller/Executor unverändert. Migration ist 2 simple `UPDATE`-Statements. |
| Beta-Launch-Impact | **enabling** — entfernt den ST-02-Block für 100 % der Nicht-Day-1-Hardware. Macht Beta-Tester mit ESPHome/Trucki/MQTT-Setups erst möglich. |
| Architektur-Konformität | **konform** — `generic` ist im Sinne von Regel 2 ein „Vendor", nur eben der Vendor „HA-konforme Geräte". JSON-Template-Verbot bleibt. Capability-Framework wurde *nicht* eingeführt (Option B aus der Vorab-Analyse — bewusst gespart). |
| Long-Term-Sustainability | **gut** — falls v1.5 echte Hoymiles-/Shelly-Vendor-Profile mit Spezial-Tuning braucht, kann ein `hoymiles.py` reanimiert werden, das von `GenericInverterAdapter` erbt und nur `get_drossel_params` overridet. Kein Rückbau nötig. |

### Verworfene Alternativen

- **Option B (Capability-Framework mit Confidence-Scores):** elegant, aber 5–7 Tage Aufwand und neue Detection-Schicht. Beta-Overkill.
- **Option C (JSON-Manifest pro Device):** verletzt Amendment 2026-04-22 frontal.
- **Option D (Adapter-Layer durch Capability-Profile ersetzen):** 9 Wochen vor Beta zu radikal.
- **Status-quo + Nur-Story 7 (Generic v1.5):** würde den Smoke-Test-Block für Alex' eigene Hardware bis Beta-Week-6 zementieren — nicht akzeptabel.

---

## 4. Detailed Change Proposals

### 4.1 Architecture Amendment 2026-04-25

**Datei:** `_bmad-output/planning-artifacts/architecture.md` — neuen Amendment-Block am Ende einfügen, gleicher Stil wie Amendment 2026-04-22 / 2026-04-23.

**Inhalt:**

```markdown
## Amendment 2026-04-25 — Generic-First Adapter-Layer

**Trigger:** Smoke-Test gegen reale Tester-Hardware (ESPHome/Trucki/SML) zeigt,
dass vendor-spezifische Regex-Patterns für Day-1 zu eng sind. ~80 % jedes
Vendor-Adapters ist HA-Standard-Boilerplate.

**Cut:** Hoymiles-Adapter wird zu `adapters/generic.py` (Klasse
`GenericInverterAdapter`), Shelly-3EM-Adapter wird zu `adapters/generic_meter.py`
(Klasse `GenericMeterAdapter`). Marstek-Venus bleibt vendor-spezifisch (Akku-
spezifische SoC-Patterns rechtfertigen ein eigenes Modul).

**Detection-Logik:**
- WR-Limit-Detection: Domain ∈ {`number`, `input_number`}, `unit_of_measurement`
  ∈ {`W`, `kW`}. `device_class == "power"` ist Bonus, nicht Pflicht (ESPHome
  setzt das nicht zuverlässig).
- WR-Output-Detection: Domain `sensor`, `unit_of_measurement` ∈ {`W`, `kW`}.
- Smart-Meter-Detection: Domain `sensor`, `unit_of_measurement` ∈ {`W`, `kW`},
  optional Suffix-Hint (`_power`, `_current_load`, `_grid_power`) für
  Confidence-Boost.

**Was NICHT geändert wird:**
- `AdapterBase`-Interface bleibt unverändert (gleiche Methoden, gleiche
  Signaturen).
- Service-Call-Generierung: Service-Domain folgt jetzt der Entity-Domain
  (`number.set_value` vs. `input_number.set_value`) — beide HA-Standard.
- Closed-Loop-Readback-Pflicht (Regel 3) — unverändert.
- Range-Check, Rate-Limit, Fail-Safe — unverändert.
- JSON-Template-Verbot aus Amendment 2026-04-22 — unverändert. Generic-Adapter
  liest **keine** Templates aus Files; vendor-Spezifika werden, falls überhaupt,
  per `device.config_json` (z. B. `max_limit_w`-Override) hinterlegt.

**Konsequenz für CLAUDE.md Regel 2:** Lautete „Ein Python-Modul pro Adapter".
Bleibt gültig. „Generic" ist im neuen Modell der Vendor „HA-konforme Geräte" —
ein Adapter, der per Definition keine Hersteller-Spezifik kennt. Echte
Hersteller-Tuning-Profile (z. B. Hoymiles ±5 W Deadband) können in v1.5+ als
Subklassen wiederkommen, die `GenericInverterAdapter` erben und nur die Tuning-
Params overriden.

**Konsequenz für Day-1-Hardware-Liste:**
- alt: Hoymiles/OpenDTU + Marstek Venus 3E/D + Shelly 3EM
- neu: Generischer Wechselrichter + Marstek Venus 3E/D + Generischer Smart Meter
- v1.5: optionale Vendor-Tuning-Profile als Subklassen + Anker Solix als eigener
  Vendor-Adapter (Akku-Spezifik)

**Konservative Defaults für Generic:**
- `get_drossel_params`: `deadband_w=10, min_step_w=5, smoothing_window=5,
  limit_step_clamp_w=200`. Toleranter als Hoymiles-Tuning, weil unbekannte WR
  größere Latenz/Hysterese haben können. **Pro-Device-Override** über
  `device.config_json` möglich (Keys: `deadband_w`, `min_step_w`,
  `smoothing_window`, `limit_step_clamp_w`). Validation in
  `DrosselParams.__post_init__` greift bei jedem Override (fail loud).
- `get_limit_range`: `(2, 3000)` W als Default — passend für Mikro-WR,
  Balkonkraftwerke und größere String-WR bis 3 kW. Per
  `device.config_json.max_limit_w` und `device.config_json.min_limit_w`
  override-bar.
- `get_rate_limit_policy`: `60 s` (Hoymiles-konservativ, sicher für unbekannte
  WR mit DTU-Protokoll-Limits).
- `get_readback_timing`: `15 s sync` (Hoymiles-konservativ).

**`device.config_json`-Override-Schema (v1):**
```json
{
  "deadband_w": 10,
  "min_step_w": 5,
  "smoothing_window": 5,
  "limit_step_clamp_w": 200,
  "min_limit_w": 2,
  "max_limit_w": 3000
}
```
Alle Keys optional. Editierbar in v1 nur per direktem DB-Update oder zukünftiger
PATCH-Route. UI-Exposure (Wizard-Sektion „Erweiterte Einstellungen" oder
Diagnose-Tab-Override) ist v1.5-Scope (eigene Story).
```

### 4.2 CLAUDE.md Updates

**Datei:** `/Users/alexander/Documents/Local-Projekte/Dev/Alkly/SolarBot/SolalexDevelopment/CLAUDE.md`

**Edit 1:** Sektion „Hardware Day-1 (3 Hersteller)" umschreiben:

```markdown
## Hardware Day-1

- **Generischer Wechselrichter** (Hoymiles/OpenDTU, Trucki, ESPHome, MQTT, …) → `adapters/generic.py`
- **Marstek Venus 3E/D** (Akku, Kern-Segment 44 % Waitlist) → `adapters/marstek_venus.py`
- **Generischer Smart Meter** (Shelly 3EM, ESPHome SML, Tibber, MQTT, …) → `adapters/generic_meter.py`

Detection erfolgt über HA-Standardattribute (Domain + `unit_of_measurement`),
nicht über vendor-spezifische Entity-ID-Patterns. Vendor-spezifisches Tuning
(z. B. Hoymiles ±5 W Drossel-Deadband) ist v1.5-Scope als Subklassen, die
`GenericInverterAdapter` erben.

**Nicht Day-1 — auf v1.5 verschoben:**
- Anker Solix (Akku) → `adapters/anker_solix.py`
- Hoymiles-Tuning-Profile (Subklasse von Generic) → `adapters/hoymiles.py`
- Shelly-3EM-Tuning-Profile (Subklasse von GenericMeter) → `adapters/shelly_3em.py`
```

**Edit 2:** Sektion „Häufige Stolpersteine für AI-Agents" — Stop-Signal-Listen-Eintrag aktualisieren:

```markdown
- Wenn Du JSON-Templates für Hardware-Adapter planst — **STOP**. Generic-Adapter
  liest keine Templates; vendor-Tuning-Profile sind Python-Subklassen.
- Wenn Du einen weiteren Hersteller-spezifischen Adapter für Day-1 anlegen willst
  — **STOP**. Generic-Detection deckt fast alle HA-konformen WR/Meter ab.
  Vendor-Adapter nur für Akkus oder bei nachgewiesenen Tuning-Anforderungen.
```

### 4.3 Neue Story in `epics.md`

**Datei:** `_bmad-output/planning-artifacts/epics.md` — am Ende von Epic 2 einfügen (nach Story 2.3):

```markdown
### Story 2.4: Generic-Adapter-Refit (Hoymiles → Generic, Shelly → Generic-Meter)

**Status:** `ready-for-dev` (Architecture-Decision in Sprint Change Proposal 2026-04-25 getroffen)

**Story:**
Als Beta-Tester mit nicht-Hoymiles-Wechselrichter (ESPHome, Trucki, MQTT) und
nicht-Shelly-Smart-Meter (ESPHome SML, Tibber, MQTT) möchte ich, dass das
Add-on meine Hardware via HA-Standardattribute auto-detected, ohne dass für
jeden Hersteller ein eigener Adapter im Image liegen muss.

**Acceptance Criteria:**

- **AC1:** `adapters/hoymiles.py` ist umbenannt zu `adapters/generic.py`, Klasse
  `HoymilesAdapter` → `GenericInverterAdapter`. `ADAPTER`-Singleton heißt jetzt
  `GenericInverterAdapter()`.
- **AC2:** `adapters/shelly_3em.py` ist umbenannt zu `adapters/generic_meter.py`,
  Klasse `Shelly3EmAdapter` → `GenericMeterAdapter`.
- **AC3:** Generic-Adapter detect WR-Limit-Entities mit Domain ∈ {`number`,
  `input_number`} und `unit_of_measurement` ∈ {`W`, `kW`}. Kein vendor-Suffix-
  Pattern mehr.
- **AC4:** Generic-Meter-Adapter detect Smart-Meter-Entities mit Domain `sensor`
  und `unit_of_measurement` ∈ {`W`, `kW`}. Suffix-Hints (`_power`,
  `_current_load`, `_grid_power`) sind weiche Confidence-Boosts (kein Filter).
- **AC5:** `build_set_limit_command` benutzt die Service-Domain passend zur
  Entity-Domain (`number.set_value` für `number.*`, `input_number.set_value` für
  `input_number.*`).
- **AC5b:** `GenericInverterAdapter.get_drossel_params(device)` liest die Keys
  `deadband_w`, `min_step_w`, `smoothing_window`, `limit_step_clamp_w` aus
  `device.config_json` und nutzt sie als Override; sonst die konservativen
  Defaults (`10/5/5/200`). `DrosselParams.__post_init__` validiert das Resultat
  hart.
- **AC5c:** `GenericInverterAdapter.get_limit_range(device)` liest die Keys
  `min_limit_w` (Default `2`) und `max_limit_w` (Default `3000`) aus
  `device.config_json`. Range gilt für den Range-Check im Executor.
- **AC6:** Forward-Only-Migration `003_adapter_key_rename.sql` setzt
  `UPDATE devices SET adapter_key='generic' WHERE adapter_key='hoymiles'` und
  `UPDATE devices SET adapter_key='generic_meter' WHERE adapter_key='shelly_3em'`.
  Genauso `type`-Spalte.
- **AC7:** API-Schema `DeviceCommissionRequest.hardware_type` akzeptiert
  `"generic" | "marstek_venus"`. Old-key `"hoymiles"` wird abgewiesen mit 422.
- **AC8:** Frontend Config.svelte zeigt Tiles „Wechselrichter (allgemein)" und
  „Marstek Venus 3E/D" — kein vendor-spezifischer Tile mehr für WR.
  Smart-Meter-Checkbox heißt „Smart Meter zuordnen" (ohne Vendor-Klammer).
- **AC9:** Functional-Test- und Running-Views nutzen den Label-Mapping
  `generic → "Wechselrichter"`, `marstek_venus → "Marstek Venus"`.
- **AC10:** Smoke-Test gegen Alex' Test-HA (Trucki ESPHome `input_number.t2sgf72a29_*`
  + ESPHome SML `sensor.00_smart_meter_sml_current_load`) durchläuft ST-00 bis
  ST-05 grün ohne Template-Helper.
- **AC11:** Alle Backend-Tests, die `adapter_key="hoymiles"` oder
  `adapter_key="shelly_3em"` verwenden, sind auf die neuen Keys umgestellt.
  Frontend-Tests (`gate.test.ts`, `Running.test.ts`, `client.test.ts`) ebenso.
- **AC12:** Smoke-Test-Dokument `_bmad-output/qa/manual-tests/smoke-test.md`
  ist aktualisiert: §1.2 Compat-Vor-Befund entfällt, Variante A/B kollabieren
  zu einem Pfad. Anhang §5/§6 (Template-Helper) bleibt als optionale Doku für
  Edge-Cases ohne `unit_of_measurement`-Attribute.
- **AC13:** CI-Gates 1+2 (Ruff/MyPy/Pytest, ESLint/svelte-check/Prettier/Vitest)
  laufen grün. CI-Gate 4 (SQL-Migrations-Ordering) ebenfalls.

**Notiz:** `AdapterBase`-Interface bleibt unverändert. Controller, Executor,
KPI, Battery-Pool werden **nicht** angefasst — sie sprechen mit dem Adapter
über das Interface, nicht über Vendor-Identität.
```

### 4.4 sprint-status.yaml

**Datei:** `_bmad-output/planning-artifacts/sprint-status.yaml` (oder analog) — neuen Eintrag:

```yaml
- epic: 2
  story: "2.4"
  title: "Generic-Adapter-Refit"
  status: ready-for-dev
  blocked_by: []
  blocks:
    - "beta-launch"
  added_via: "Sprint Change Proposal 2026-04-25"
```

### 4.5 Backend-Edits — konkrete Code-Änderungen

#### 4.5.1 `backend/src/solalex/adapters/generic.py` (war: `hoymiles.py`)

**Aktion:** `hoymiles.py` als Basis übernehmen, dann editieren. Nicht mit `git mv` umbenennen — `git rm hoymiles.py` + `git add generic.py` damit die Diff-Sicht klar bleibt (anders als ein vendor-Tuning-Profile-Override später).

**Inhalt:**

```python
"""Generic HA-conforming inverter adapter.

Detects any HA entity that exposes a writable power-limit value via the
``number`` or ``input_number`` domain with unit-of-measurement W or kW.
Covers Hoymiles/OpenDTU, Trucki, ESPHome, MQTT-bridged inverters and
similar HA-standard exposures without vendor-specific suffix matching.

Rate limit: 60 s (conservative — covers OpenDTU DTU protocol limit and
typical local inverter integrations).
Readback: synchronous, 15 s timeout.
"""

from __future__ import annotations

from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    DrosselParams,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)

_LIMIT_DOMAINS = ("number", "input_number")
_POWER_UOMS = ("W", "kW")


class GenericInverterAdapter(AdapterBase):
    """Generic adapter for HA-standard inverter entities."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            domain = state.entity_id.split(".", 1)[0]
            uom = state.attributes.get("unit_of_measurement", "")
            if domain in _LIMIT_DOMAINS and uom in _POWER_UOMS:
                devices.append(
                    DetectedDevice(
                        entity_id=state.entity_id,
                        friendly_name=state.attributes.get(
                            "friendly_name", state.entity_id
                        ),
                        suggested_role="wr_limit",
                        adapter_key="generic",
                    )
                )
        return devices

    def build_set_limit_command(
        self, device: DeviceRecord, watts: int
    ) -> HaServiceCall:
        # Service-domain matches entity-domain — both `number.set_value` and
        # `input_number.set_value` are HA standard services with identical
        # payload shape.
        domain = device.entity_id.split(".", 1)[0]
        return HaServiceCall(
            domain=domain,
            service="set_value",
            service_data={"entity_id": device.entity_id, "value": watts},
        )

    def build_set_charge_command(
        self, device: DeviceRecord, watts: int
    ) -> HaServiceCall:
        raise NotImplementedError(
            "Generic inverter adapter does not support battery charge commands"
        )

    def parse_readback(self, state: HaState) -> int | None:
        try:
            raw = float(state.state)
            uom = state.attributes.get("unit_of_measurement", "W")
            if uom == "kW":
                raw *= 1000.0
            return round(raw)
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=15.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        # Defaults cover micro-inverters, balcony solar and string
        # inverters up to 3 kW. Per-device override via
        # device.config_json.{min,max}_limit_w. UI exposure is v1.5
        # (Diagnose-Tab "advanced settings").
        config = device.config()
        min_w = int(config.get("min_limit_w", 2))
        max_w = int(config.get("max_limit_w", 3000))
        return (min_w, max_w)

    def get_drossel_params(self, device: DeviceRecord) -> DrosselParams:
        # Conservative defaults — unknown vendor inverters can have
        # higher latency/hysteresis than Hoymiles. Vendor-specific
        # tuning lives in v1.5 subclasses (e.g. HoymilesAdapter would
        # override deadband_w=5, min_step_w=3). Per-device override via
        # device.config_json so Beta testers can tune without an Add-on
        # rebuild; DrosselParams.__post_init__ validates the result.
        config = device.config()
        return DrosselParams(
            deadband_w=int(config.get("deadband_w", 10)),
            min_step_w=int(config.get("min_step_w", 5)),
            smoothing_window=int(config.get("smoothing_window", 5)),
            limit_step_clamp_w=int(config.get("limit_step_clamp_w", 200)),
        )


ADAPTER = GenericInverterAdapter()
```

#### 4.5.2 `backend/src/solalex/adapters/generic_meter.py` (war: `shelly_3em.py`)

**Inhalt:**

```python
"""Generic HA-conforming smart-meter adapter (read-only).

Detects any HA sensor entity exposing real-time grid power in W or kW.
Covers Shelly 3EM, ESPHome SML readers, Tibber pulse, MQTT-bridged
meters and similar HA-standard exposures.

Sign convention: positive value = grid import (Bezug), negative = export
(Einspeisung). Source entity must conform; the adapter does not flip
signs.
"""

from __future__ import annotations

from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)

_POWER_UOMS = ("W", "kW")


class GenericMeterAdapter(AdapterBase):
    """Read-only adapter for HA-standard smart-meter entities."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            if not state.entity_id.startswith("sensor."):
                continue
            uom = state.attributes.get("unit_of_measurement", "")
            if uom not in _POWER_UOMS:
                continue
            devices.append(
                DetectedDevice(
                    entity_id=state.entity_id,
                    friendly_name=state.attributes.get(
                        "friendly_name", state.entity_id
                    ),
                    suggested_role="grid_meter",
                    adapter_key="generic_meter",
                )
            )
        return devices

    def build_set_limit_command(
        self, device: DeviceRecord, watts: int
    ) -> HaServiceCall:
        raise NotImplementedError(
            "Generic meter adapter is read-only — no limit command available"
        )

    def build_set_charge_command(
        self, device: DeviceRecord, watts: int
    ) -> HaServiceCall:
        raise NotImplementedError(
            "Generic meter adapter is read-only — no charge command available"
        )

    def parse_readback(self, state: HaState) -> int | None:
        try:
            raw = float(state.state)
            uom = state.attributes.get("unit_of_measurement", "W")
            if uom == "kW":
                raw *= 1000.0
            return int(raw)
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=10.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        raise NotImplementedError(
            "Generic meter adapter is read-only — no write range"
        )


ADAPTER = GenericMeterAdapter()
```

#### 4.5.3 `backend/src/solalex/adapters/__init__.py`

**Inhalt:**

```python
"""Hardware adapter registry.

Importing this package makes ADAPTERS available — a dict from adapter_key
to the corresponding adapter singleton. Every adapter implements the
interface defined in :mod:`solalex.adapters.base`.
"""

from __future__ import annotations

from solalex.adapters import generic, generic_meter, marstek_venus
from solalex.adapters.base import AdapterBase

ADAPTERS: dict[str, AdapterBase] = {
    "generic": generic.ADAPTER,
    "generic_meter": generic_meter.ADAPTER,
    "marstek_venus": marstek_venus.ADAPTER,
}

__all__ = ["ADAPTERS", "AdapterBase"]
```

#### 4.5.4 `backend/src/solalex/api/schemas/devices.py:14`

**Edit:** `Literal["hoymiles", "marstek_venus"]` → `Literal["generic", "marstek_venus"]`.

#### 4.5.5 `backend/src/solalex/api/routes/devices.py:67-115`

**Edits:**

- Zeile 67: `if body.hardware_type == "hoymiles":` → `if body.hardware_type == "generic":`
- Zeile 71: `type="hoymiles"` → `type="generic"`
- Zeile 74: `adapter_key="hoymiles"` → `adapter_key="generic"`
- Zeile 112: `type="shelly_3em"` → `type="generic_meter"`
- Zeile 115: `adapter_key="shelly_3em"` → `adapter_key="generic_meter"`

#### 4.5.6 `backend/src/solalex/api/routes/setup.py:170-179`

**Edits:**

- Zeile 170: `hoymiles_devices = [` → `generic_inverters = [`
- Zeile 171: `d.adapter_key == "hoymiles"` → `d.adapter_key == "generic"`
- Zeile 178: `if hoymiles_devices:` → `if generic_inverters:`
- Zeile 179: `target_device = hoymiles_devices[0]` → `target_device = generic_inverters[0]`
- Fehlertext im 412-Branch: „Hoymiles-Wechselrichter (Rolle: wr_limit)" → „Wechselrichter (Rolle: wr_limit)".

#### 4.5.7 `backend/src/solalex/persistence/sql/003_adapter_key_rename.sql` (neu)

**Inhalt:**

```sql
-- Migration 003 — rename adapter_key/type from vendor-specific to generic.
-- Forward-only. No downgrade path (Architecture: backup-file-replace on
-- previous-version restart).

UPDATE devices SET adapter_key = 'generic'        WHERE adapter_key = 'hoymiles';
UPDATE devices SET adapter_key = 'generic_meter'  WHERE adapter_key = 'shelly_3em';
UPDATE devices SET type        = 'generic'        WHERE type        = 'hoymiles';
UPDATE devices SET type        = 'generic_meter'  WHERE type        = 'shelly_3em';
```

### 4.6 Frontend-Edits — konkrete Code-Änderungen

#### 4.6.1 `frontend/src/lib/api/types.ts:13`

```ts
hardware_type: 'generic' | 'marstek_venus';
```

#### 4.6.2 `frontend/src/routes/Config.svelte`

**Edits:**

- Zeile 14: `let hardwareType = $state<'hoymiles' | 'marstek_venus' | null>(null);`
  → `let hardwareType = $state<'generic' | 'marstek_venus' | null>(null);`
- Zeile 63: `function selectType(type: 'hoymiles' | 'marstek_venus'): void {`
  → `function selectType(type: 'generic' | 'marstek_venus'): void {`
- Zeile 119: Empty-State-Hinweis — „Prüfe, ob Hoymiles/Marstek/Shelly …"
  → „Prüfe, ob deine Wechselrichter-/Akku-/Smart-Meter-Integration aktiv ist und passende Power-Sensoren bereitstellt."
- Zeile 129–131: `class:active={hardwareType === 'hoymiles'}` etc.
  → `class:active={hardwareType === 'generic'}`, `aria-pressed={hardwareType === 'generic'}`, `onclick={() => selectType('generic')}`
- Zeile 133: `<span class="tile-title">Hoymiles / OpenDTU</span>`
  → `<span class="tile-title">Wechselrichter (allgemein)</span>` + Sub-Label „z. B. Hoymiles/OpenDTU, Trucki, ESPHome"
- Zeile 152: `{hardwareType === 'hoymiles' ? 'Wechselrichter-Limit-Entity' : 'Ladeleistungs-Entity'}`
  → `{hardwareType === 'generic' ? 'Wechselrichter-Limit-Entity' : 'Ladeleistungs-Entity'}`
- Zeile 238: `<span>Smart Meter (Shelly 3EM) zuordnen</span>`
  → `<span>Smart Meter zuordnen</span>` + Sub-Label „z. B. Shelly 3EM, ESPHome SML, Tibber"

#### 4.6.3 `frontend/src/routes/FunctionalTest.svelte:107`

```svelte
if (devices.some((d) => d.adapter_key === 'generic')) return 'Wechselrichter';
```

#### 4.6.4 `frontend/src/routes/Running.svelte:97`

Nur Kommentar:

```ts
// WINDOW_MS (typical 60 s rate-limit for HA-managed inverters) and suffers
```

### 4.7 Test-Sweep

**Backend (17 Files):** Mechanischer `sed`-Sweep (manuell verifizieren):

```
adapter_key="hoymiles"    → adapter_key="generic"
adapter_key='hoymiles'    → adapter_key='generic'
adapter_key="shelly_3em"  → adapter_key="generic_meter"
adapter_key='shelly_3em'  → adapter_key='generic_meter'
type="hoymiles"           → type="generic"
type="shelly_3em"         → type="generic_meter"
"hoymiles":               → "generic":      (Registry-Lookups in Tests)
"shelly_3em":             → "generic_meter":
```

**Sonderfälle:**

- `tests/unit/test_hoymiles_drossel_params.py` → renamen zu `test_generic_drossel_params.py`. Test-Werte aktualisieren auf neue konservative Defaults (`deadband_w=10` statt `5`).
- `tests/unit/test_adapters.py` → Pattern-Tests komplett ersetzen durch Capability-Tests (Domain + uom).

**Frontend (3 Files):**

- `lib/gate.test.ts` — alle `adapter_key`-Referenzen.
- `routes/Running.test.ts` — Mock-Devices.
- `lib/api/client.test.ts` — Mock-Responses.

### 4.8 Smoke-Test-Dokument-Update

**Datei:** `_bmad-output/qa/manual-tests/smoke-test.md`

**Edits:**

- §1.2 „Compat-Vor-Befund": komplett entfernen oder durch grünen Block ersetzen („Test-HW erwartet auto-detected via HA-Capabilities. Falls Entities trotz korrektem `unit_of_measurement` nicht erscheinen, siehe §5/§6 Template-Helper als Edge-Case-Lösung").
- §1.3 „Vorbedingungen": Variante-A/B-Auswahl-Checkbox entfernen.
- §2 ST-02-Tabelle: Variante-A-Spalte streichen, nur ein Pfad (analog zu „Variante B mit Helpers" — aber mit echter Trucki-Entity, nicht Helper).
- §4 Pass-Kriterien: Variante-A/B-Sektionen kollabieren zu einem End-zu-End-Pfad.
- §5/§6 Anhang: bleibt als optionale Doku für Edge-Cases (HA-Setups, in denen `unit_of_measurement` fehlt — z. B. Custom-Component ohne Attribute).

---

## 5. Implementation Handoff

**Scope-Klassifikation:** Moderate (siehe oben).

**Routing:** Developer-Agent (direkte Umsetzung) — die Architecture-Entscheidung ist in §4.1 dokumentiert, der Refit selbst ist mechanisch.

**Empfohlene Reihenfolge (für saubere Diffs + grüne CI auf jedem Schritt):**

1. **Architecture-Amendment + CLAUDE.md-Update + epics.md-Story-2.4** committen (reines Doku-Pre-Commit, keine Code-Änderung — gibt Audit-Trail).
2. **Backend Adapter-Files + `__init__.py`-Registry + DB-Migration 003** in einem Commit (`hoymiles.py` weg, `generic.py` rein; `shelly_3em.py` weg, `generic_meter.py` rein).
3. **Backend API-Routes + Schemas** in einem Commit (`devices.py`, `setup.py`, `schemas/devices.py`).
4. **Backend Tests** in einem Commit — Pytest muss danach grün sein.
5. **Frontend Types + Routes + Tests** in einem Commit — Vitest muss danach grün sein.
6. **Smoke-Test-Dokument** in einem Commit (reines QA-Doku-Update).
7. **Manueller Smoke-Test** gegen Alex' Test-HA durchführen (ST-00 bis ST-05 grün ohne Helper) — falls Befund: Patch-Commit.

**Success-Kriterien:**

- [ ] CI-Gate 1 (Ruff/MyPy strict/Pytest) grün
- [ ] CI-Gate 2 (ESLint/svelte-check/Prettier/Vitest) grün
- [ ] CI-Gate 4 (SQL-Migrations-Ordering) grün
- [ ] Smoke-Test ST-00–ST-05 gegen Trucki + ESPHome-SML grün ohne Template-Helper
- [ ] `git grep -E '(adapter_key|hardware_type|type)\s*[:=]\s*["\x27](hoymiles|shelly_3em)["\x27]'` liefert null Treffer im Source-Tree
- [ ] DB-Migration 003 läuft auf bestehender Test-DB durch (UPDATE-Counts > 0 falls vorher commissioned, sonst 0)

**Beta-Launch-Block:** Story 2.4 ist Beta-Launch-blocking. Beta darf nicht released werden, solange Generic-Detection nicht greifbar ist — sonst scheitern Beta-Tester mit Nicht-Day-1-Hardware bereits am Wizard-Step 2.

**Aufwand-Schätzung:** ~2 Tage Solo-Dev, inklusive Smoke-Test-Verifikation.

---

**Dieser Sprint Change Proposal ersetzt KEINE bestehenden Architecture-Decisions außer der in §4.1 dokumentierten. Amendment 2026-04-22 (kein JSON-Template-Layer) bleibt vollständig erhalten und wird durch §4.1 explizit verstärkt.**
