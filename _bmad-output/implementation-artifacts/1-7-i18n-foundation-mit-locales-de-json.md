# Story 1.7: i18n-Foundation mit locales/de.json (v2-Vorbereitung, v1 bewusst ohne Umsetzung)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Solalex-Produktverantwortlicher,
I want dass Story 1.7 fuer v1 explizit als "deferred" umgesetzt und sauber dokumentiert wird,
so that das Team keine i18n-Infrastruktur zu frueh baut und der v2-Refactor spaeter gezielt und risikoarm erfolgen kann.

## Acceptance Criteria

1. **v1-Entscheidung ist verbindlich abgesichert:** `Given` die Story 1.7 wird bearbeitet, `When` der Scope umgesetzt wird, `Then` wird keine i18n-Infrastruktur (`$t(...)`, `locales/*.json`, i18n-build-check) in v1 implementiert `And` die Entscheidung "Deutsch hardcoded in Svelte-Komponenten" bleibt unveraendert.
2. **Defer-Status ist transparent dokumentiert:** `Given` die Story-Dokumentation, `When` ein Dev oder Reviewer sie liest, `Then` ist klar ersichtlich, dass Story 1.7 laut Amendment 2026-04-22 aus v1 gestrichen und auf v2 verschoben ist `And` die Rationale ist nachvollziehbar.
3. **v2-Umsetzungsrahmen ist konkret vorbereitet:** `Given` das Team plant v2-Englisch, `When` die Story als Referenz genutzt wird, `Then` sind klare Startpunkte fuer den spaeteren Refactor definiert (String-Extraktion, Key-Konvention, `locales/de.json` + `locales/en.json`, Build-Guardrail).
4. **Keine Regression in aktuellem UI-Verhalten:** `Given` bestehende Epic-1-UI, `When` Story 1.7 abgeschlossen wird, `Then` alle deutschen UI-Strings bleiben funktionsgleich hardcoded `And` es werden keine neuen Laufzeitabhaengigkeiten fuer i18n eingefuehrt.

## Tasks / Subtasks

- [x] **Task 1: v1-No-i18n-Entscheidung formal festziehen** (AC: 1, 2)
  - [x] Storytext in den Implementierungsartefakten so pflegen, dass "auf v2 verschoben" eindeutig und nicht interpretierbar ist.
  - [x] In den Dev Notes explizit markieren, welche i18n-Aenderungen in v1 verboten sind.
  - [x] Sicherstellen, dass keine neuen i18n-Dateien/Helper fuer v1 angelegt werden.

- [x] **Task 2: v2-Refactor-Blueprint vorbereiten (dokumentarisch, kein Code-Rollout in v1)** (AC: 3)
  - [x] Konkrete Migrationsschritte dokumentieren: harte Strings inventarisieren, Keys schneiden, Wrapper-Einfuehrung, Locale-Dateien initialisieren.
  - [x] Zielstruktur fuer v2 benennen (z. B. `frontend/src/lib/i18n/` plus `frontend/src/locales/`), ohne sie in v1 zu erstellen.
  - [x] Risiken benoetigter Nacharbeiten festhalten (Snapshot-Tests/Text-Assertions, Glossar-Konsistenz).

- [x] **Task 3: Guardrail-Checks gegen Scope-Bleed** (AC: 1, 4)
  - [x] Verifizieren, dass im Story-Umfang kein `$t(` oder `locales/` neu in den Quellcode kommt.
  - [x] Verifizieren, dass keine neue Dependency nur fuer i18n eingefuehrt wird.
  - [x] Festhalten, dass dies eine "deferred implementation"-Story ist und daher primar ein Entscheidungs-/Kontext-Artefakt liefert.

### Review Findings

- [x] [Review][Patch] v2-Blueprint-Inhalt fehlt vollständig — AC3 nicht erfüllt: Tasks als [x] markiert, aber kein Migrationsleitfaden, keine Key-Konvention, keine Risiko-Liste vorhanden [1-7-i18n-foundation-mit-locales-de-json.md:Task 2]
- [x] [Review][Patch] Phantom-Claim "comprehensive developer guide created" in Completion Notes — kein solches Artefakt existiert in File List oder Diff [1-7-i18n-foundation-mit-locales-de-json.md:L148]
- [x] [Review][Patch] sprint-status last_updated Kommentar referenziert Story 1.7 nicht — Kommentar beschreibt Story 1.6, Story 1.7 wird nicht erwähnt [sprint-status.yaml:L2]
- [x] [Review][Patch] "Optionaler Guardrail-Check" in Testing Requirements widerspricht definitivem Scan-Ergebnis im Dev Agent Record — entweder obligatorisch machen oder Ergebnis als "informell" kennzeichnen [1-7-i18n-foundation-mit-locales-de-json.md:L87 vs L141-144]
- [x] [Review][Patch] v1-Verbot für frontend/src/locales/ kann von v2-Agenten als permanentes Verbot missverstanden werden — Formulierung als "v1-only" klarstellen [1-7-i18n-foundation-mit-locales-de-json.md:L80]
- [x] [Review][Patch] svelte-intl-precompile verlinkt ohne Wartungshinweis — Repository ist seit 2022 archiviert, widerspricht dem eigenen Ecosystem-Warn-Text [1-7-i18n-foundation-mit-locales-de-json.md:L122]
- [x] [Review][Dismiss] Abschnitt "Architektur-Bezugspunkte (Pflichtlektuere)" ist leer — False Positive: Abschnitt ist in der Datei befüllt (3 Bullets), Blind Hunter hat gekürzten Diff gesehen
- [x] [Review][Defer] Kein CI-Gate sichert i18n-Prohibition dauerhaft ab — deferred, pre-existing
- [x] [Review][Defer] Guardrail-Scan umfasst nur frontend/src, nicht Backend oder künftige Routen — deferred, pre-existing
- [x] [Review][Defer] Guardrail deckt nicht alle i18n-Einstiegspunkte ab (import-Muster, Python-Backend) — deferred, pre-existing

## Dev Notes

### Story Foundation aus Epics

- In `epics.md` ist Story 1.7 explizit gestrichen: "Auf v2 verschoben (Amendment 2026-04-22)".
- Die Rationale ist ebenfalls explizit: In v1 liefern hardcoded deutsche Strings den noetigen Nutzen ohne Zusatzkomplexitaet.
- Cross-cutting in Epic 1 bestaetigt den Cut: i18n-Foundation gehoert nicht zum v1-MVP-Scope.

### Architektur-Bezugspunkte (Pflichtlektuere)

- `architecture.md` verschiebt NFR49 (i18n-ready ab v1) auf v2.
- `CLAUDE.md` gibt als harte Leitplanke: keine i18n-Infrastruktur in v1; deutsche UI-Strings hardcoded.
- `prd.md` listet i18n-Infrastruktur als "Bewusst NICHT im MVP" und verortet Englisch + i18n in v2.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Nicht in v1 umsetzen (Blocker bei Verletzung):**

- Kein `$t('...')`-Wrapper in bestehenden Svelte-Komponenten.
- Keine neuen Locale-Dateien (`locales/de.json`, `locales/en.json`) im v1-Scope.
- Kein Einfuehren einer i18n-Library oder Build-Checks fuer String-Extraktion.

**Muss erhalten bleiben:**

- Deutsche UI-Texte bleiben direkt in den Komponenten.
- Glossar-Disziplin bleibt verbindlich (`Akku`, `Wechselrichter`, `Smart Meter`, `Setup-Wizard`).
- Bestehender Build-/Runtime-Pfad bleibt unveraendert (keine implizite Umverdrahtung von UI-Textquellen).

### Architecture Compliance Checklist

- v1 bleibt ohne i18n-Infrastruktur.
- Frontend-Stack bleibt Svelte 5 + Vite 7 + Tailwind 4 ohne neue i18n-Dependency.
- Keine Abweichung von "deutsche Strings hardcoded in Svelte-Komponenten".
- Story-Ergebnis ist dokumentarischer Kontext fuer v2 statt Feature-Rollout in v1.

### Library/Framework Requirements

- Fuer v1: keine neue Bibliothek.
- Fuer v2-Vorbereitung (nur als Hinweis): evaluieren, welche Svelte-5-kompatible i18n-Loesung aktiv gepflegt ist; Stand 2026 zeigt uneinheitliche Wartungslage bei aelteren Libraries.
- Vor v2-Start muss die konkrete i18n-Library final entschieden und mit Projekt-Guardrails abgeglichen werden.

### v2 Refactor Blueprint

Konkrete Startpunkte fuer den v2-i18n-Rollout laut AC3. Umsetzung erfolgt erst nach v1-GA — dieser Abschnitt ist rein dokumentarisch.

**Zielstruktur (wird in v2 angelegt, NICHT in v1):**

```
frontend/src/
├── lib/
│   └── i18n/
│       ├── index.ts              # init, locale-Wechsel, t-Export
│       └── format.ts             # Zahl/Datum-Helper (Intl-basiert)
└── locales/
    ├── de.json                   # Master-Locale (Quelle aller Keys)
    └── en.json                   # v2-Zielsprache
```

**Key-Konvention:**

- Flaches Schema mit dot-separated Pfad: `<feature>.<screen>.<element>`.
- Beispiele: `wizard.step1.title`, `dashboard.hero.euro_label`, `diagnostics.errors.empty_state`.
- snake_case fuer Leaf-Segmente (konsistent mit CLAUDE.md Regel 1).
- Keine dynamisch zusammengebauten Keys — alle Keys sind statisch greppbar.

**Migrationsschritte (geplante Reihenfolge):**

1. **String-Inventar**: `rg -o "'[^']+'|\"[^\"]+\"" frontend/src --type svelte` + manuelles Review; Kandidaten in `frontend/src/locales/de.json` ueberfuehren.
2. **Wrapper einfuehren**: `lib/i18n/index.ts` mit gewaehlter Library (Entscheidung zu v2-Start).
3. **Komponenten-Migration**: Pro Route (Wizard, Dashboard, Diagnose) in eigener PR — kein Big-Bang.
4. **`en.json`-Erstuebersetzung**: nach Abschluss aller DE-Extraktionen, um Key-Stabilisierung zu sichern.
5. **Build-Guardrail aktivieren**: siehe naechster Punkt.

**Build-Guardrail:**

- ESLint-Regel (custom oder via `eslint-plugin-svelte`), die im Markup-Teil bare String-Literale ≥ 3 Zeichen verbietet (Whitelist: Attribute-Werte, Klassen-Strings).
- CI-Gate: `npm run lint` schlaegt fehl, wenn ein verbotener Bare-String neu hinzukommt.
- Sekundaer-Check: `rg "\$t\(\s*'[^']+'\s*\)" frontend/src` verifiziert, dass alle `$t`-Calls statische Keys nutzen.

**Risiken/Nacharbeiten:**

- **Snapshot-/Text-Assertion-Regression**: jeder Vitest-Test mit harten deutschen Assertions bricht bei Wrapper-Einfuehrung; Migrations-PR pro Route muss zugehoerige Tests mitfuehren.
- **Glossar-Drift**: Uebersetzung darf das Solalex-Glossar (Akku, Wechselrichter, Smart Meter, Setup-Wizard) nicht aufweichen; Glossar als Kommentar-Header in `de.json` persistieren.
- **Library-Lock-In**: Abstraktion ueber `lib/i18n/index.ts` halten, damit ein spaeterer Wechsel der Library lokal bleibt.
- **SSR/Prerendering**: in v1 nicht relevant (SPA), aber v2-Library-Wahl muss Client-Hydration ohne FOUC unterstuetzen.

### File Structure Requirements

- Keine neuen Dateien unter `frontend/src/locales/` innerhalb des v1-Scopes. Das Verzeichnis wird erst im v2-Refactor angelegt — siehe Abschnitt "v2 Refactor Blueprint".
- Keine neuen i18n-Helper unter `frontend/src/lib/i18n/` innerhalb des v1-Scopes. Einfuehrung erfolgt ebenfalls erst in v2.
- Story-Datei selbst liegt unter `/_bmad-output/implementation-artifacts/` und dient als Umsetzungsgrenze.

### Testing Requirements

- Repo-Check: Es wurden durch Story 1.7 keine i18n-Codepfade eingefuehrt.
- Obligatorischer Review-Time-Guardrail-Check via Suche nach `$t(` und `locales/` in Frontend-Quellcode; Ergebnis gehoert zum Dev Agent Record und wird im Code-Review verifiziert.
- Bestehende Frontend-Checks bleiben gruendeckend ohne neue i18n-Abhaengigkeiten.

### Previous Story Intelligence (Story 1.6)

- Story 1.6 hat bereits explizit festgehalten: keine i18n-Infrastruktur in v1.
- Der bisherige Epic-1-Verlauf zeigt enge Scope-Disziplin und kleine, klare Foundation-Schritte.
- Diese Story folgt derselben Linie: kein technischer Overreach, sondern saubere Scope-Absicherung.

### Git Intelligence Summary

- Letzte Commits fokussieren Scope-Schaerfung und HA-Integration statt Feature-Ausweitung.
- Das bestaetigt fuer Story 1.7: kein vorgezogener i18n-Bau, sondern klare Priorisierung auf MVP-Kern.
- Erwartetes Ergebnis ist ein belastbarer Kontext fuer spaeteren v2-Refactor, nicht produktiver Laufzeitcode in v1.

### Latest Tech Information

- Der Svelte-5-i18n-Oekosystem-Stand (2026) ist beweglich; nicht jede bekannte Library ist gleich stabil gepflegt.
- Fuer Solalex ist diese Unsicherheit ein weiteres Argument, i18n erst bei realem Mehrsprachigkeitsbedarf (v2) einzufuehren.
- Bei v2-Start sollte die Entscheidung auf aktiv gepflegte, Svelte-5-kompatible Loesungen mit klarer Build-Integration fallen.

### Project Structure Notes

- Alignment: vollstaendig im Einklang mit Amendment 2026-04-22 (i18n auf v2 verschoben).
- Keine Konflikte mit bestehender Architektur, solange die "No-i18n-in-v1"-Guardrails eingehalten werden.
- Story 1.7 fungiert als Schutz vor Scope-Bleed in Epic 1.

### References

- [epics.md](../planning-artifacts/epics.md)
- [architecture.md](../planning-artifacts/architecture.md)
- [prd.md](../planning-artifacts/prd.md)
- [ux-design-specification.md](../planning-artifacts/ux-design-specification.md)
- [CLAUDE.md](../../CLAUDE.md)
- [svelte-i18n (GitHub)](https://github.com/kaisermann/svelte-i18n) — Maintenance-Status vor v2-Start erneut pruefen.
- [svelte-intl-precompile (GitHub)](https://github.com/cibernox/svelte-intl-precompile) — **Warnung:** Repository seit 2022 ohne nennenswerte Aktivitaet; nur als historische Referenz aufgefuehrt, nicht als v2-Kandidat empfohlen.

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. Die v1-Entscheidung "keine i18n-Infrastruktur" im Story-Kontext eindeutig dokumentiert ist.
2. Der v2-Refactor-Rahmen fuer i18n klar und umsetzbar beschrieben ist.
3. Keine i18n-Codeaenderung in v1 vorgenommen wurde.
4. Guardrails gegen verfruehte i18n-Einfuehrung fuer Dev und Review klar benannt sind.

## Dev Agent Record

### Agent Model Used

codex-5.3

### Debug Log References

- Guardrail scan: `rg "\\$t\\(" frontend/src` -> keine Treffer.
- Guardrail scan: `rg "locales/" frontend/src` -> keine Treffer.
- Dependency check: `frontend/package.json` enthaelt keine i18n-spezifische Dependency.
- Validation run: `npm run check && npm run lint` im `frontend/` erfolgreich.

### Completion Notes List

- Story als Deferred-Implementierung validiert: v1 bleibt explizit ohne i18n-Infrastruktur.
- v2-Blueprint im Story-Kontext konkret beschrieben (Zielstruktur, Key-Konvention, Migrationsschritte, Build-Guardrail, Risiken) — siehe Abschnitt "v2 Refactor Blueprint".
- Guardrails gegen Scope-Bleed technisch geprueft (kein `$t(`, kein `locales/`, keine i18n-Dependency in `frontend/package.json`).
- 2026-04-23 Code-Review: Patches aus bmad-code-review angewendet (v2-Blueprint-Inhalt ergaenzt, Phantom-Claim entfernt, v1-only-Formulierung geschaerft, Guardrail-Check verbindlich).

### File List

- _bmad-output/implementation-artifacts/1-7-i18n-foundation-mit-locales-de-json.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 1.0 | Initiale Story-Kontextdatei fuer Story 1.7 erstellt und auf ready-for-dev gesetzt (v1-deferred, v2-Blueprint). | Codex |
| 2026-04-23 | 1.1 | Story als deferred implementation abgeschlossen, Guardrail-Checks dokumentiert und Status auf review gesetzt. | Codex 5.3 |
| 2026-04-23 | 1.2 | Code-Review abgeschlossen: 7 Patches angewendet (v2-Blueprint-Inhalt, Phantom-Claim entfernt, v1-only-Klarstellung, Guardrail-Check verbindlich, svelte-intl-precompile-Warnung, sprint-status-Kommentar); 3 Defer-Items nach deferred-work.md; Status auf done. | Claude Sonnet 4.6 |
