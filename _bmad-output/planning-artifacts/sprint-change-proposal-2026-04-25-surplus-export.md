# Sprint Change Proposal — 2026-04-25 — Surplus-Export-Mode

**Trigger:** „Wenn ich einen Wechselrichter mit nachgeschaltetem Akku habe (PV → Akku → WR), passiert bei Akku-Voll: Solalex drosselt den WR runter (Nulleinspeisung), aber die PV wird intern abgeregelt — verlorene Energie. Solalex müsste erkennen ‚Akku voll' und das WR-Limit aufmachen, sodass eingespeist statt abgeregelt wird."

**Mode:** Batch
**Autor:** Alex (Solo-Dev) + Claude Opus 4.7
**Scope-Klassifikation:** **Moderate** — Backlog-Erweiterung um eine Story in Epic 3, ein neuer Mode-Enum-Wert, eine neue SQL-Migration (CHECK-Constraint-Erweiterung), ein Architecture-Amendment, ein CLAUDE.md-Update, kleines Frontend-Add (Toggle in Config-Page). Kein PRD-Cut, kein Re-Open bestehender Stories, keine Behavior-Change ohne expliziten User-Opt-In.

---

## 1. Issue Summary

Beim Durchsprechen des Beta-Verhaltens für DC-gekoppelte Hybrid-/Stack-Setups (PV-Module → Akku mit MPPT → Wechselrichter → Hausnetz) ist ein konzeptionelles Loch in der aktuellen Mode-Logik aufgefallen, das **auch AC-gekoppelte Setups** (Marstek Venus parallel zu Hoymiles am Hausnetz — Beta-Sweet-Spot!) betrifft:

- Wenn der Akku-Pool voll ist (`aggregated_pct ≥ 97 %`) **und** PV liefert weiter Leistung **und** Last < PV, dann switcht Solalex (Story 3.5) im SPEICHER-Mode automatisch zu **DROSSEL** und reduziert das WR-Limit auf Last-Niveau.
- Konsequenz: Die überschüssige PV wird **abgeregelt** (am MPPT, sei es WR-intern oder Akku-intern). Sie wird **nicht** ins Netz eingespeist.
- Wirtschaftlich: PV-Abregelung = 0 € Wert; Einspeisung = ~6–8 ct/kWh (EEG); Eigenverbrauch wäre ~30 ct/kWh, ist aber bei vollem Akku nicht möglich.
- Im DROSSEL-Mode erlaubt Solalex aktuell **keinen** Pfad, das WR-Limit nach oben zu öffnen, um die PV einspeisen zu lassen statt abzuregeln.

**Tieferes Problem:** Solalex's Mission war bisher binär „Nulleinspeisung". In der Realität gibt es **drei** Klassen von Beta-Testern:

1. **Strenge Nulleinspeisung** (Anlagen ohne Inbetriebnahme-Anmeldung beim Netzbetreiber, rechtlich grau bei Einspeisung): wollen niemals einspeisen, auch nicht bei vollem Akku → Status quo bleibt.
2. **Pragmatische Eigenverbrauchs-Maximierer** (angemeldete Anlagen mit EEG-Vergütung): wollen primär Eigenverbrauch + Akku-Laden, aber bei vollem Akku lieber einspeisen als abregeln.
3. **Reine Einspeise-Optimierer** (dynamische Tarife wie Tibber): wollen je nach Strompreis wechseln. Out-of-Scope für v1.

Klasse 2 ist im DACH-Raum die **Mehrheit**, vor allem bei Bestandsanlagen mit Akku-Nachrüstung. Solalex muss diesen Modus liefern, sonst „verbrennt" jeder Beta-Tester der Klasse 2 im Schnitt 1–3 kWh/Tag PV-Leistung in den Sommermonaten.

**Kategorie:** Konzept-Lücke, in der Diskussion über Hardware-Topologien (DC- vs. AC-gekoppelt) entdeckt. Nicht: Misverständnis, kein Pivot, keine Strategieänderung — eine pragmatische Erweiterung des Mode-Modells um einen vierten, opt-in-basierten Modus.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Betroffen | Art der Änderung |
|------|-----------|------------------|
| Epic 1 | Nein | `done`, unverändert |
| Epic 2 | **Indirekt** | Story 2.1 (Hardware-Config-Page) wird in Story 3.8 frontend-seitig erweitert um den Surplus-Export-Toggle pro WR. **Kein Re-Open** — die UI-Erweiterung ist additiv und wird in 3.8 dokumentiert. |
| **Epic 3** | **Ja** | Neue **Story 3.8 — Surplus-Export-Mode bei Akku-Voll**. Stories 3.1–3.5 bleiben unverändert. Story 3.6 (User-Config Min/Max-SoC) und Story 3.7 (Fail-Safe) werden nicht angefasst — Reihenfolge bleibt. |
| Epic 4 | **Indirekt** | Diagnose-Tab (4.1) zeigt Mode-Wechsel-Cycles automatisch — `mode='export'` erscheint dann ohne Code-Change. Story 4.5 (Bug-Report-Export) sieht den neuen Mode in `control_cycles` ohne Anpassung. |
| Epic 5 | **Indirekt** | Story 5.1a (Live-Betriebs-View) zeigt `current_mode` aus `state_cache`. Mit `Mode.EXPORT` als neuem Wert braucht das Frontend eine Label-Erweiterung (`'export'` → „Einspeisung" o. ä.). Wird in Story 3.8 mitgemacht (kein 5.1a-Re-Open). Story 5.5 (Mode-Chip-Animation) bekommt einen vierten Zustand — wird in 5.5 selbst beachtet, **nicht** in 3.8. |
| Epic 6 | Nein | |
| Epic 7 | Nein | |

### Story Impact

- **Neu: Story 3.8 — „Surplus-Export-Mode bei Akku-Voll (opt-in pro WR)"** — Backend (Mode-Enum, `_policy_export`, Hysterese-Erweiterung in 3.5-Helpern) + DB-Migration 004 (CHECK-Constraint-Erweiterung) + Frontend (Toggle in Config-Page + Label-Mapping in Running-View). Status: `ready-for-dev` direkt, weil Architektur-Entscheidung in diesem Proposal getroffen wird.
- **Geändert: Story 3.5 (`done`)** — Wird **nicht** re-opened. Die in 3.8 hinzugefügten Erweiterungen (`_evaluate_mode_switch` lernt EXPORT-Branch, `_policy_multi` lernt EXPORT-Cap-Branch) sind additiv und werden im 3.8-Story-File explizit dokumentiert als Touch-Points zu 3.5.
- **Geändert: Story 2.1 (`done`)** — Frontend-Erweiterung in Config.svelte: ein neues Toggle pro WR-Device. Wird in 3.8-Frontend-Tasks abgehandelt, **nicht** als 2.1-Re-Open.
- **Story 5.1a (`done`)** — Label-Mapping `'export'` → „Einspeisung" wird in 3.8 mitgenommen (Mini-Diff in Running.svelte).

### Artefakt-Konflikte

| Artefakt | Änderung | Aufwand |
|----------|----------|---------|
| `architecture.md` | **Amendment 2026-04-25 (Surplus-Export)** — Mode-Enum von 3-fach auf 4-fach erweitert; neue Policy `_policy_export` als Methode am Mono-Modul-Controller (kein neues Modul); SQL-Migration 004 erweitert CHECK-Constraints; Toggle-Persistenz im bestehenden `device.config_json`-Override-Schema (additiv zum 2026-04-25-Generic-Adapter-Amendment). | ~30 min |
| `CLAUDE.md` | Stolperstein-Liste: Eintrag „Mode-Enum bleibt 3-fach" entfernen oder umformulieren („Mode-Enum bleibt 4-fach: DROSSEL, SPEICHER, MULTI, EXPORT — kein 5. Mode in v1"). Neuer Stop-Eintrag: „Surplus-Export ist `Mode.EXPORT` mit eigener Policy `_policy_export`, kein Patch in `_policy_drossel`." Hardware-Day-1-Liste bleibt. | ~10 min |
| `epics.md` | Neue Story 3.8 unter Epic 3 einfügen (nach Story 3.7) mit AC. Hinweis am Anfang von Story 3.5: „Erweiterung in Story 3.8 (Surplus-Export-Mode)". | ~30 min |
| `sprint-status.yaml` | Eintrag Story 3.8 als `ready-for-dev` hinzufügen. `last_updated` auf 2026-04-25 aktualisieren. | ~5 min |
| `prd.md` | **Mini-Patch** — FR16/FR21-Sektion ergänzen um Hinweis: „Bei aktivem Surplus-Export-Toggle wird der Modus-Switch SPEICHER → DROSSEL bei Pool-Voll durch SPEICHER → EXPORT ersetzt; das WR-Limit wird auf Hardware-Max gesetzt, statt eingedrosselt." Status-quo bleibt: Default ist Nulleinspeisung. | ~15 min |
| `ux-design-specification.md` | **Keine** strukturelle Änderung. Toggle in Config-Page wird im 3.8-Story-File spezifiziert (Pattern „kein Toast, Auto-PUT auf Toggle-Change", analog zu 2.1). | 0 min |
| `_bmad-output/qa/manual-tests/smoke-test.md` | Optional: ein neuer Smoke-Test-Step für Surplus-Export hinzufügen (aktivieren, simuliertes Pool-Voll, beobachten dass Limit auf Max gesetzt wird). Kann auch in Story 3.8 selbst als manueller Verifikations-Step dokumentiert sein. | ~15 min |

### Technischer Impact

#### Backend (~6 Files)

- **`backend/src/solalex/controller.py`** (UPDATE):
  - `Mode`-Enum: vierter Wert `EXPORT = "export"`.
  - Neue Methode `Controller._policy_export(self, device, sensor_value_w) -> list[PolicyDecision]` (~30 LOC) — liest `wr_limit_device.config_json.max_limit_w` und produziert Decision.
  - `_dispatch_by_mode`: `case Mode.EXPORT: return self._policy_export(...)`.
  - `_evaluate_mode_switch` (aus 3.5): erweitert um EXPORT-Branch — Bedingung `SPEICHER + aggregated ≥ 97 % + wr_limit.config_json.allow_surplus_export == True` → return `(Mode.EXPORT, reason)`. Rückkehr-Branch: `EXPORT + aggregated ≤ 93 %` → return `(self._mode_baseline, reason)`.
  - `_policy_multi` (aus 3.5): Cap-Branch erweitert — bei `_speicher_max_soc_capped == True` und Toggle ON → ruft `_policy_export` statt `_policy_drossel`.
  - Neue Konstante `MODE_SWITCH_EXPORT_SOC_PCT` ist **nicht** nötig — wir reusen `MODE_SWITCH_HIGH_SOC_PCT=97.0` und `MODE_SWITCH_LOW_SOC_PCT=93.0` aus 3.5.
- **`backend/src/solalex/persistence/sql/004_mode_export.sql`** (NEU): CHECK-Constraint-Erweiterung für `control_cycles.mode` und `latency_measurements.mode` — SQLite-Pattern `CREATE TABLE _new` + `INSERT ... SELECT` + `DROP` + `RENAME` + `CREATE INDEX`.
- **`backend/src/solalex/state_cache.py`** (UPDATE, ~2 LOC): falls dort eine Whitelist für `current_mode`-Werte existiert, `'export'` ergänzen.
- **`backend/src/solalex/api/schemas/devices.py`** (UPDATE, optional): falls `config_json` typisiert ist, ein optionales Feld `allow_surplus_export: bool | None` ergänzen — sonst keine Änderung, weil `config_json` als opaker JSON-String persistiert wird.
- **Tests:** ~3 NEU Test-Files: `test_controller_policy_export.py`, `test_controller_mode_switch_export.py`, `test_migration_004_export_mode.py`.

#### Frontend (~3 Files)

- **`frontend/src/routes/Config.svelte`** (UPDATE): pro WR-Device-Tile (oder bei aktivem WR-Device) ein Checkbox-Toggle „Surplus-Einspeisung erlauben (statt PV-Abregelung) bei vollem Akku" mit Inline-Hint zur Voraussetzung (`max_limit_w` muss gesetzt sein, sonst Toggle disabled mit erklärendem Text).
- **`frontend/src/lib/api/client.ts`** (UPDATE): neue Funktion `setSurplusExport(deviceId: number, enabled: boolean)` → schreibt `device.config_json.allow_surplus_export` per `PATCH /api/v1/devices/{id}/config`.
- **`frontend/src/lib/api/types.ts`** (UPDATE): erweitere `Mode`-Type-Union um `'export'`.
- **`frontend/src/routes/Running.svelte`** (UPDATE, ~2 LOC): Mode-Label-Mapping ergänzen — `'export' → 'Einspeisung'`.
- **Tests:** Erweiterung von `Config.test.ts` (Toggle-Tests) und `Running.test.ts` (Label-Mapping).

#### API (~2 Files)

- **`backend/src/solalex/api/routes/devices.py`** (UPDATE, ~30 LOC): neuer Endpunkt `PATCH /api/v1/devices/{id}/config` (oder Erweiterung eines existierenden), der `device.config_json` partial-merged. Bei `allow_surplus_export=True` muss `max_limit_w` im config_json gesetzt sein, sonst 422.
- **`backend/src/solalex/api/schemas/devices.py`** (UPDATE): Pydantic-Schema `DeviceConfigPatchRequest` mit Feldern `allow_surplus_export: bool | None`, `max_limit_w: int | None`, etc. (alle Override-Keys aus dem 2.4-Schema).

#### Migration-Risiko

- **Beta noch nicht released** — keine Production-User mit `mode='export'` in der DB. Migration 004 läuft auf jeder bestehenden DB durch (neue Tabelle hat dieselben Columns; INSERT...SELECT kopiert alle Rows mit `mode IN ('drossel','speicher','multi')` — für die neue Constraint trivial gültig).
- **Per-WR-Toggle Default `false`** — ohne explizite Aktivierung bleibt Solalex bei Status-quo-Verhalten (DROSSEL bei Pool-Voll). Beta-Tester der Klasse 1 (strenge Nulleinspeisung) bemerken nichts.
- **Forward-Only**, kein Downgrade-Pfad — entspricht Architecture-Vorgabe (Backup-File-Replace beim Restart der Vorgängerversion, kein Alembic).

#### CI-Gates

- **Ruff + MyPy strict + Pytest** — neue Tests notwendig, sonst Coverage-Cliff bei `_policy_export`.
- **ESLint + svelte-check + Prettier + Vitest** — Type-Update + Toggle-Tests notwendig.
- **Egress-Whitelist** — unverändert.
- **SQL-Migrations-Ordering** — `004_mode_export.sql` ist nächste freie Nummer nach `003_adapter_key_rename.sql`, lückenlos.

---

## 3. Recommended Approach

**Direct Adjustment (Option 1 aus Change-Checklist).** Surplus-Export erfolgt als eigenständige Story 3.8 **innerhalb** von Epic 3, ohne Rollback bestehender Stories. Story 3.5 bleibt `done`; ihre Mode-Switch-Logik wird in 3.8 erweitert (additiv, kein Re-Open). Default-Verhalten bleibt unverändert — Surplus-Export ist explizit opt-in pro WR.

### Rationale

| Kriterium | Bewertung |
|---|---|
| Implementierungs-Aufwand | **mittel** — ~1 Tag Backend + Migration + Tests, ~½ Tag Frontend (Config-Toggle + Label-Mapping). Keine neue Library, keine neue Architektur-Schicht. |
| Technisches Risiko | **niedrig–mittel** — Mode-Enum-Erweiterung ist trivial, SQL-Migration über Recreate-Pattern ist Standard-SQLite-Manöver, `_policy_export` ist die einfachste Policy (single Decision, keine Glättung, keine Hysterese intern). Risiko: Frontend-Tests + State-Cache-Whitelist nicht vergessen. |
| Beta-Launch-Impact | **enabling** — schließt eine Real-Welt-Lücke für die Mehrheit der DACH-Beta-Tester (Klasse 2). Ohne Surplus-Export werden Beta-Tester mit angemeldeten Anlagen + Akku im Sommer signifikante PV-Energie verlieren — schlecht für Wahrnehmung („das Add-on regelt mir die Sonne weg"). |
| Architektur-Konformität | **konform** — Mono-Modul-Prinzip bleibt (`_policy_export` als Methode am Controller, **kein** `policies/export.py`). Cap-Flag-Brücke aus 3.4/3.5 wird wiederverwendet. JSON-Template-Verbot bleibt. Toggle-Persistenz nutzt das bestehende `device.config_json`-Override-Schema aus dem 2026-04-25-Generic-Adapter-Amendment. |
| Long-Term-Sustainability | **gut** — falls v1.5 dynamische Tarife (Tibber-Spotpreise) integriert, kann `_policy_export` um eine Spotpreis-Bedingung erweitert werden („nur einspeisen wenn Preis > X ct/kWh"). Mode-Enum bleibt stabil. |

### Verworfene Alternativen

- **Option β (DROSSEL-Patch ohne neuen Mode):** `_policy_drossel` lernt einen zweiten Branch (Limit nach oben statt nach unten). Vorteil: keine SQL-Migration, kein Mode-Enum-Cut. Nachteil: Audit-Trail wird unsauber (`mode='drossel'` im Log obwohl gerade eingespeist wird). Fundamental missverständlich für Diagnose. **Verworfen.**
- **Option γ (Toggle in Story 3.6 einbauen, Backend-Logik separat in 3.8):** Toggle in 3.6's User-Config-UI, Backend-Mode in 3.8. Vorteil: 3.6's UI bringt den Toggle gleich mit. Nachteil: 3.8 muss dann ohne UI-Toggle arbeiten (= immer aktiv), bis 3.6 fertig ist — bricht Opt-In-Default. **Verworfen** zugunsten Pfad α (alles in 3.8 inklusive Toggle).
- **Globaler Toggle in `meta`-Tabelle statt per-WR:** simpler, aber zwingt User mit gemischten Setups (z. B. ein angemeldeter WR + ein nicht-angemeldeter), entweder beide einzuspeisen oder gar nicht. Verletzt Klasse-1-/Klasse-2-Trennung. **Verworfen.**
- **Spotpreis-gesteuerter Export (Tibber-Integration):** elegant, aber out-of-scope für v1. Externe Daten, neue Dependency, neue Failure-Modes. **Auf v2 verschoben.**

---

## 4. Detailed Change Proposals

### 4.1 Architecture Amendment 2026-04-25 (Surplus-Export)

**Datei:** `_bmad-output/planning-artifacts/architecture.md` — neuen Amendment-Block am Ende einfügen, gleicher Stil wie Amendment 2026-04-22 / 2026-04-23 / 2026-04-25 (Generic-Adapter).

**Inhalt:**

```markdown
## Amendment 2026-04-25 — Surplus-Export-Mode (`Mode.EXPORT`)

**Trigger:** Konzeptionelle Lücke entdeckt beim Durchsprechen DC-gekoppelter
Hybrid-Setups (PV → Akku → WR), die auch AC-gekoppelte Beta-Sweet-Spot-Setups
(Marstek Venus + Hoymiles parallel am Hausnetz) trifft: Bei Pool-Voll switcht
Story 3.5 zu DROSSEL und reduziert das WR-Limit — die überschüssige PV wird
dadurch abgeregelt, statt eingespeist. Wirtschaftlich verschenkt das im
Sommer 1–3 kWh/Tag pro Beta-Tester der Klasse „Eigenverbrauchs-Maximierer
mit angemeldeter Anlage" (DACH-Mehrheit).

**Cut:** Mode-Enum wird von 3-fach (DROSSEL, SPEICHER, MULTI) auf 4-fach
erweitert. Neuer Wert `Mode.EXPORT = "export"`. Neue Policy
`Controller._policy_export(self, device, sensor_value_w) -> list[PolicyDecision]`
am Mono-Modul-Controller (kein neues Modul, Architektur-Cut 9 bleibt). Die
Policy setzt das WR-Limit auf den Hardware-Max-Wert aus
`wr_limit_device.config_json.max_limit_w` (Schema aus dem Generic-Adapter-
Amendment 2026-04-25 wiederverwendet).

**Trigger-Logik:**
- Hysterese-Erweiterung in `_evaluate_mode_switch` (Story 3.5):
  - SPEICHER + `aggregated_pct ≥ 97 %` + `wr_limit.config_json.allow_surplus_export == True`
    → Switch zu EXPORT (statt DROSSEL).
  - EXPORT + `aggregated_pct ≤ 93 %` → Switch zurück zu `_mode_baseline`
    (üblicherweise SPEICHER oder MULTI).
- MULTI-Cap-Branch in `_policy_multi` (Story 3.5):
  - `_speicher_max_soc_capped == True` + Toggle ON → ruft `_policy_export`
    statt `_policy_drossel` auf. MULTI bleibt MULTI (kein Mode-Switch),
    die Decision wird einfach mit Hardware-Max-Limit produziert.

**Toggle-Persistenz:**
- Pro WR im bestehenden `device.config_json`-Override-Schema (Amendment
  2026-04-25 Generic-Adapter):
  ```json
  {
    "max_limit_w": 600,
    "allow_surplus_export": true
  }
  ```
- Default `allow_surplus_export = false` (Status-quo-Verhalten).
- Validierung: `allow_surplus_export = true` ist nur akzeptabel, wenn
  `max_limit_w` ebenfalls gesetzt ist (sonst kennt die Policy den Wert nicht,
  auf den sie das Limit setzen soll). API-Validierung im PATCH-Handler.

**Was NICHT geändert wird:**
- `AdapterBase`-Interface bleibt unverändert.
- Closed-Loop-Readback-Pflicht (Regel 3) — unverändert. EXPORT-Decisions
  durchlaufen die normale Veto-Kaskade + Readback im Executor.
- Range-Check, Rate-Limit, Fail-Safe — unverändert.
- `_mode_baseline`-Field aus 3.5 — bleibt; EXPORT setzt es nicht.
- Hysterese-Konstanten 97/93 % aus 3.5 — werden wiederverwendet, kein
  separater EXPORT-Schwellenwert.
- Mindest-Verweildauer 60 s aus 3.5 — gilt auch für EXPORT-Switch.
- JSON-Template-Verbot — unverändert.

**SQL-Migration 004:**
- Forward-only: erweitert CHECK-Constraint auf `control_cycles.mode` und
  `latency_measurements.mode` um Wert `'export'`.
- SQLite-Pattern: `CREATE TABLE _new` + `INSERT ... SELECT` + `DROP` +
  `RENAME` + `CREATE INDEX` (Standard-Recreate, weil SQLite kein
  `ALTER TABLE ... ALTER CONSTRAINT` kennt).
- Forward-Only-Konsistenz mit Architecture-Vorgabe (Backup-File-Replace
  beim Restart der Vorgängerversion).

**Konsequenz für CLAUDE.md:**
- Stolperstein-Eintrag „Mode-Enum bleibt 3-fach" wird entfernt bzw. ersetzt
  durch „Mode-Enum bleibt 4-fach: DROSSEL, SPEICHER, MULTI, EXPORT — kein
  5. Mode in v1".
- Neuer Stop-Eintrag: „Wenn du Surplus-Export als Patch in `_policy_drossel`
  einbauen willst statt eigenem `Mode.EXPORT` + `_policy_export` — STOP.
  Audit-Trail-Klarheit (mode='export' im Log) ist non-verhandelbar."

**Konsequenz für Default-User-Verhalten:**
- Status-quo bleibt erhalten. Beta-Tester der Klasse „strenge Nulleinspeisung"
  (z. B. Anlagen ohne Inbetriebnahme-Anmeldung beim Netzbetreiber) bemerken
  ohne Toggle-Aktivierung keinerlei Verhaltensänderung.
- Beta-Tester der Klasse „Eigenverbrauchs-Maximierer" können den Toggle pro
  WR aktivieren und vermeiden damit PV-Abregelung bei vollem Akku.

**Aufwand-Schätzung:** ~1 Tag Backend (Mode + Policy + Migration + Tests),
~½ Tag Frontend (Config-Toggle + Label + Tests).
```

### 4.2 CLAUDE.md Updates

**Datei:** `/Users/alexander/Documents/Local-Projekte/Dev/Alkly/SolarBot/SolalexDevelopment/CLAUDE.md`

**Edit 1:** Sektion „Häufige Stolpersteine für AI-Agents" — Eintrag mit `Mode.IDLE` aktualisieren von 3-fach auf 4-fach:

```markdown
- Wenn Du `Mode.IDLE` einführst — **STOP**. `state_cache.current_mode` hat
  `'idle'` als String-Sentinel für Polling-Endpoint, aber `Mode`-Enum bleibt
  4-fach (DROSSEL/SPEICHER/MULTI/EXPORT — Amendment 2026-04-25).
```

**Edit 2:** Sektion „Häufige Stolpersteine für AI-Agents" — neuen Eintrag ergänzen:

```markdown
- Wenn Du Surplus-Export als Patch in `_policy_drossel` einbauen willst
  statt eigener Policy `_policy_export` + Mode-Enum-Wert `Mode.EXPORT` —
  **STOP**. Audit-Trail-Klarheit (mode='export' im Log) ist
  non-verhandelbar (Amendment 2026-04-25 Surplus-Export).
- Wenn Du `_policy_export` in ein eigenes Modul auslagerst (`policies/export.py`
  o. ä.) — **STOP**. Mono-Modul-Controller bleibt (Architektur-Cut 9).
- Wenn Du den Surplus-Export-Toggle global in der `meta`-Tabelle ablegst
  statt pro WR in `device.config_json` — **STOP**. Mixed-Setups (ein
  angemeldeter WR + ein nicht-angemeldeter) müssen unabhängig schaltbar
  sein.
```

### 4.3 Neue Story in `epics.md`

**Datei:** `_bmad-output/planning-artifacts/epics.md` — am Ende von Epic 3 einfügen (nach Story 3.7):

```markdown
### Story 3.8: Surplus-Export-Mode bei Akku-Voll (opt-in pro WR)

**Status:** `ready-for-dev` (Architecture-Decision in Sprint Change Proposal
2026-04-25-Surplus-Export getroffen)

**Story:**
Als Beta-Tester mit angemeldeter Anlage und Akku-Speicher möchte ich, dass
Solalex bei vollem Akku das WR-Limit nicht eindrosselt (PV-Abregelung),
sondern auf Hardware-Max öffnet (Einspeisung), damit ich keine PV-Energie
verschenke. Der Modus muss explizit pro Wechselrichter aktivierbar sein,
weil ich Mixed-Setups habe (ein angemeldeter WR, ein Balkonkraftwerk
ohne Anmeldung — beide müssen unabhängig konfigurierbar sein).

**Acceptance Criteria:** (vollständig im Story-File 3-8-...md spezifiziert)

- **AC1–AC3:** `Mode.EXPORT` als 4. Enum-Wert; SQL-Migration 004 für
  CHECK-Constraint-Erweiterung; `_policy_export` als Methode am Controller.
- **AC4–AC6:** Hysterese-Erweiterung in `_evaluate_mode_switch` (3.5);
  MULTI-Cap-Branch-Erweiterung in `_policy_multi`; State-Cache-Whitelist
  ergänzt um `'export'`.
- **AC7–AC9:** PATCH-Endpunkt `PATCH /api/v1/devices/{id}/config` mit
  partial-merge auf `device.config_json`; Validierung `allow_surplus_export
  → max_limit_w required`; Auto-PUT-Pattern.
- **AC10–AC12:** Frontend Config.svelte Toggle pro WR; Inline-Hint bei
  fehlendem `max_limit_w`; Running.svelte Label-Mapping.
- **AC13–AC15:** Tests (Backend + Frontend), Migration-Test, Smoke-Test.

**Notiz:** `Mode.SPEICHER` und `Mode.MULTI` bleiben Default-Verhalten ohne
Toggle. Wenn Toggle ON, ändert sich nur das Verhalten *bei Pool-Voll*: statt
DROSSEL (Limit runter) → EXPORT (Limit auf Hardware-Max).

**Beta-Launch-Block:** **Ja**. Ohne Surplus-Export wird die Klasse
„Eigenverbrauchs-Maximierer" (DACH-Mehrheit) im Sommer signifikante
PV-Energie verlieren — schlecht für Beta-Wahrnehmung.
```

### 4.4 sprint-status.yaml

**Datei:** `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Edit:** Neuen Eintrag unter Epic 3 nach `3-7-fail-safe-bei-kommunikations-ausfall`:

```yaml
  # Neu 2026-04-25: Surplus-Export-Mode (Mode.EXPORT) — opt-in pro WR;
  # Beta-Launch-blocking weil Eigenverbrauchs-Maximierer-Klasse (DACH-Mehrheit)
  # ohne diesen Mode im Sommer PV-Energie abregelt statt einspeist.
  3-8-surplus-export-modus-bei-akku-voll: ready-for-dev
```

`last_updated`-Header aktualisieren auf 2026-04-25 mit Hinweis auf SCP.

### 4.5 PRD-Mini-Patch

**Datei:** `_bmad-output/planning-artifacts/prd.md`

**Edit:** Im FR16-Block (Anti-Oszillation / Mode-Switch) einen Hinweis ergänzen:

```markdown
**FR16 Erweiterung (Amendment 2026-04-25 Surplus-Export):** Wenn am
betreffenden Wechselrichter `device.config_json.allow_surplus_export = true`
gesetzt ist, ersetzt der Mode-Switch SPEICHER → DROSSEL bei Pool-Voll durch
SPEICHER → EXPORT. EXPORT setzt das WR-Limit auf den Hardware-Max-Wert
(`device.config_json.max_limit_w`), wodurch die PV-Erzeugung eingespeist
wird, statt am MPPT abgeregelt. Default `allow_surplus_export = false`
preserve das ursprüngliche Nulleinspeisungs-Verhalten.
```

### 4.6 Code-Änderungs-Skizze (im Detail im Story 3.8 File)

#### 4.6.1 `controller.py` — Mode-Enum + `_policy_export`

```python
class Mode(StrEnum):
    DROSSEL = "drossel"
    SPEICHER = "speicher"
    MULTI = "multi"
    EXPORT = "export"  # Amendment 2026-04-25 — Surplus-Export-Mode


def _dispatch_by_mode(self, mode, device, sensor_value_w):
    match mode:
        case Mode.DROSSEL:
            decision = self._policy_drossel(device, sensor_value_w)
            return [decision] if decision is not None else []
        case Mode.SPEICHER:
            return self._policy_speicher(device, sensor_value_w)
        case Mode.MULTI:
            return self._policy_multi(device, sensor_value_w)
        case Mode.EXPORT:
            return self._policy_export(device, sensor_value_w)


def _policy_export(self, device, sensor_value_w):
    """Surplus-Export — open WR limit to hardware max so PV can feed into
    grid instead of being curtailed at the MPPT.

    Triggered only when:
      - Mode.EXPORT is active (set by hysteresis in _evaluate_mode_switch
        when SPEICHER + pool >= 97 % + wr_limit.config_json.allow_surplus_export).
      - Sensor event arrives.
    """
    if device.role != "grid_meter":
        return []
    wr_device = self._wr_limit_device
    if wr_device is None:
        return []
    config = wr_device.config()
    max_limit_w = config.get("max_limit_w")
    if max_limit_w is None:
        # Defensive — should be impossible because the toggle PATCH
        # validates max_limit_w is set. Log + fail-safe-noop.
        _logger.warning(
            "policy_export_max_limit_missing",
            extra={"device_id": wr_device.id},
        )
        return []
    current = self._read_current_wr_limit_w(wr_device)
    if current is None or current >= int(max_limit_w):
        return []  # already at max — nothing to do
    return [
        PolicyDecision(
            device=wr_device,
            target_value_w=int(max_limit_w),
            mode=Mode.EXPORT.value,
            command_kind="set_limit",
            sensor_value_w=sensor_value_w,
        )
    ]
```

#### 4.6.2 `_evaluate_mode_switch` Erweiterung

```python
def _evaluate_mode_switch(self, *, sensor_device, now):
    if self._forced_mode is not None:
        return None
    if self._current_mode == Mode.MULTI:
        return None
    if self._battery_pool is None or not self._battery_pool.members:
        return None
    soc_breakdown = self._battery_pool.get_soc(self._state_cache)
    if soc_breakdown is None:
        return None
    if self._mode_switched_at is not None:
        if (now - self._mode_switched_at).total_seconds() < MODE_SWITCH_MIN_DWELL_S:
            return None
    aggregated = soc_breakdown.aggregated_pct

    # Read toggle from wr_limit device config.
    surplus_enabled = False
    if self._wr_limit_device is not None:
        try:
            surplus_enabled = bool(
                self._wr_limit_device.config().get("allow_surplus_export", False)
            )
        except (json.JSONDecodeError, TypeError):
            surplus_enabled = False

    # SPEICHER → EXPORT (with toggle) or DROSSEL (without)
    if self._current_mode == Mode.SPEICHER and aggregated >= MODE_SWITCH_HIGH_SOC_PCT:
        if surplus_enabled:
            return (Mode.EXPORT, f"pool_full_export (soc={aggregated:.1f}%)")
        return (Mode.DROSSEL, f"pool_full (soc={aggregated:.1f}%)")

    # EXPORT → baseline (SPEICHER or MULTI)
    if self._current_mode == Mode.EXPORT and aggregated <= MODE_SWITCH_LOW_SOC_PCT:
        return (
            self._mode_baseline,
            f"pool_below_low_threshold_export_exit (soc={aggregated:.1f}%)",
        )

    # DROSSEL → SPEICHER (existing 3.5 logic, unchanged)
    if self._current_mode == Mode.DROSSEL and self._mode_baseline in (Mode.SPEICHER, Mode.MULTI):
        if aggregated <= MODE_SWITCH_LOW_SOC_PCT:
            return (Mode.SPEICHER, f"pool_below_low_threshold (soc={aggregated:.1f}%)")

    return None
```

#### 4.6.3 SQL-Migration 004

```sql
-- Migration 004 — extend mode CHECK constraint to allow 'export'.
-- Forward-only. SQLite recreate-pattern (no ALTER for CHECK constraints).

CREATE TABLE control_cycles_new (
    id                INTEGER   PRIMARY KEY AUTOINCREMENT,
    ts                TIMESTAMP NOT NULL,
    device_id         INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    mode              TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi','export')),
    source            TEXT      NOT NULL CHECK (source IN ('solalex','manual','ha_automation')),
    sensor_value_w    REAL,
    target_value_w    INTEGER,
    readback_status   TEXT      CHECK (readback_status IN ('passed','failed','timeout','vetoed','noop')),
    readback_actual_w REAL,
    readback_mismatch INTEGER   NOT NULL DEFAULT 0,
    latency_ms        INTEGER,
    cycle_duration_ms INTEGER   NOT NULL,
    reason            TEXT
);

INSERT INTO control_cycles_new SELECT * FROM control_cycles;
DROP TABLE control_cycles;
ALTER TABLE control_cycles_new RENAME TO control_cycles;
CREATE INDEX IF NOT EXISTS idx_control_cycles_ts ON control_cycles(ts DESC);
CREATE INDEX IF NOT EXISTS idx_control_cycles_device ON control_cycles(device_id);

CREATE TABLE latency_measurements_new (
    id         INTEGER   PRIMARY KEY AUTOINCREMENT,
    device_id  INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    command_at TIMESTAMP NOT NULL,
    effect_at  TIMESTAMP NOT NULL,
    latency_ms INTEGER   NOT NULL,
    mode       TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi','export'))
);

INSERT INTO latency_measurements_new SELECT * FROM latency_measurements;
DROP TABLE latency_measurements;
ALTER TABLE latency_measurements_new RENAME TO latency_measurements;
CREATE INDEX IF NOT EXISTS idx_latency_device_ts
    ON latency_measurements(device_id, command_at DESC);
```

### 4.7 PATCH-Endpunkt für Toggle

**Datei:** `backend/src/solalex/api/routes/devices.py`

**Neuer Endpunkt:**

```python
@router.patch("/{device_id}/config", response_model=DeviceResponse)
async def patch_device_config(
    device_id: int,
    body: DeviceConfigPatchRequest,
    request: Request,
):
    """Partial-merge update of device.config_json.

    Validation:
      - allow_surplus_export = true requires max_limit_w to be set
        (either in this patch or already in config_json).
    """
    # ... fetch existing device, merge config, validate, persist ...
```

`DeviceConfigPatchRequest`-Schema:

```python
class DeviceConfigPatchRequest(BaseModel):
    allow_surplus_export: bool | None = None
    max_limit_w: int | None = None
    min_limit_w: int | None = None
    deadband_w: int | None = None
    min_step_w: int | None = None
    smoothing_window: int | None = None
    limit_step_clamp_w: int | None = None
```

### 4.8 Frontend — Config.svelte Toggle

Pro WR-Tile (oder im Device-Detail-Drawer der Hardware-Config-Page) ein zusätzlicher Block:

```svelte
{#if device.role === 'wr_limit'}
  <label class="toggle-row">
    <input
      type="checkbox"
      bind:checked={surplusExport}
      disabled={!hasMaxLimit}
      onchange={() => saveSurplusExport(device.id, surplusExport)}
    />
    <span>Surplus-Einspeisung erlauben (statt PV-Abregelung) bei vollem Akku</span>
  </label>
  {#if !hasMaxLimit}
    <p class="hint">
      Voraussetzung: Hardware-Max-Limit (W) muss konfiguriert sein.
      Setze zuerst „Max-Leistung" in den erweiterten Einstellungen.
    </p>
  {/if}
{/if}
```

### 4.9 Test-Sweep

**Backend (3 NEU Test-Files):**

- `test_controller_policy_export.py`:
  - `test_export_sets_limit_to_max_when_below`
  - `test_export_no_decision_when_already_at_max`
  - `test_export_no_decision_when_max_limit_missing_in_config`
  - `test_export_no_decision_on_non_grid_meter_event`
  - `test_export_no_decision_when_no_wr_limit_device`
- `test_controller_mode_switch_export.py`:
  - `test_speicher_to_export_when_toggle_on_and_pool_full`
  - `test_speicher_to_drossel_when_toggle_off_and_pool_full` (regression)
  - `test_export_to_baseline_speicher_at_low_soc`
  - `test_export_to_baseline_multi_at_low_soc`
  - `test_export_dwell_blocks_oscillation`
  - `test_export_audit_cycle_persisted_with_export_mode`
  - `test_multi_cap_branch_calls_export_when_toggle_on`
  - `test_multi_cap_branch_calls_drossel_when_toggle_off` (regression)
- `test_migration_004_export_mode.py`:
  - `test_migration_004_preserves_existing_rows`
  - `test_migration_004_allows_export_mode_insert`
  - `test_migration_004_rejects_invalid_mode`

**Frontend:**

- `Config.test.ts`: `test_renders_surplus_toggle_for_wr_devices`,
  `test_toggle_disabled_without_max_limit`,
  `test_patch_called_on_toggle_change`,
  `test_label_for_export_mode_in_running`.
- `Running.test.ts`: `test_displays_einspeisung_label_when_mode_is_export`.

### 4.10 Smoke-Test-Doku-Update (optional)

Ein neuer manueller Verifikations-Step im Story-File 3.8 selbst (kein eigener Smoke-Test-Doku-Update nötig):

```
1. Toggle in Config-Page für WR aktivieren.
2. Pool-SoC manuell auf 98 % setzen (HA-Sensor-Override oder echter Setup).
3. Beobachten: WR-Limit wird auf max_limit_w gesetzt; control_cycles
   enthält Row mit mode='export', reason='pool_full_export (soc=98.0%)'.
4. Pool-SoC manuell auf 92 % setzen.
5. Beobachten: nach 60 s Dwell-Time switcht zurück zu SPEICHER; WR-Limit
   wird wieder reaktiv geregelt.
```

---

## 5. Implementation Handoff

**Scope-Klassifikation:** Moderate (siehe oben).

**Routing:** Developer-Agent (direkte Umsetzung) — die Architecture-Entscheidung ist in §4.1 dokumentiert, die Code-Änderungen sind im Story 3.8 File detailliert.

**Empfohlene Reihenfolge (für saubere Diffs + grüne CI auf jedem Schritt):**

1. **SCP + Architecture-Amendment + CLAUDE.md-Update + epics.md-Story-3.8 + sprint-status-Eintrag + PRD-Mini-Patch** committen (reines Doku-Pre-Commit, keine Code-Änderung — gibt Audit-Trail).
2. **Backend: SQL-Migration 004 + Mode-Enum-Erweiterung + `_policy_export` + `_evaluate_mode_switch`-Erweiterung + `_policy_multi`-Erweiterung** in einem Commit (alles in `controller.py` + neuer SQL-File).
3. **Backend Tests** in einem Commit — Pytest muss danach grün sein (3 neue Test-Files + Update bestehender 3.5-Tests, falls Mock-Mode-Whitelist betroffen).
4. **Backend API: PATCH-Endpunkt + Schema** in einem Commit.
5. **Frontend: Types + Config.svelte Toggle + Running.svelte Label + Tests** in einem Commit.
6. **State-Cache-Whitelist + manueller Smoke-Test** als Final-Patch-Commit.

**Success-Kriterien:**

- [ ] CI-Gate 1 (Ruff/MyPy strict/Pytest) grün — inkl. ~14 neue Tests
- [ ] CI-Gate 2 (ESLint/svelte-check/Prettier/Vitest) grün
- [ ] CI-Gate 4 (SQL-Migrations-Ordering) grün — `004_mode_export.sql` lückenlos nach `003`
- [ ] Manueller Smoke-Test: Toggle aktivieren → Pool-Voll-Simulation → `mode='export'`-Cycle in DB → Toggle deaktivieren → Pool-Voll → `mode='drossel'`-Cycle (Regression-Verify)
- [ ] `git grep -E "Mode\.EXPORT"` zeigt Treffer in `controller.py`, `state_cache.py` (Whitelist), Tests — sonst nirgends

**Beta-Launch-Block:** Story 3.8 ist Beta-Launch-blocking. Ohne diesen Mode verliert die Mehrheit der DACH-Beta-Tester (Klasse „Eigenverbrauchs-Maximierer mit angemeldeter Anlage") signifikante PV-Energie im Sommer.

**Aufwand-Schätzung:** ~1.5 Tage Solo-Dev, inklusive Smoke-Test-Verifikation und Frontend-Toggle.

---

**Dieser Sprint Change Proposal ergänzt — ersetzt nicht — die bestehenden Architecture-Decisions.** Amendment 2026-04-22 (Mono-Modul-Controller, Cut 9), Amendment 2026-04-23 (Light-only), Amendment 2026-04-25 (Generic-Adapter-Refit) bleiben vollständig erhalten. Die Mode-Enum-Erweiterung von 3-fach auf 4-fach ist die einzige strukturelle Änderung am Mono-Modul-Vertrag und wird durch §4.1 explizit dokumentiert.
