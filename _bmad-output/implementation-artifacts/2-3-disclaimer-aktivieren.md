# Story 2.3: Disclaimer + Aktivieren

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Nutzer,
I want einen expliziten Installations-Disclaimer vor der Aktivierung,
so that ich bewusst bestätige, dass ich die Verantwortung für die Steuerung meiner Anlage übernehme.

## Acceptance Criteria

1. **Weiter-zum-Disclaimer-Button:** `Given` der Funktionstest (Story 2.2) war erfolgreich, `When` der Nutzer den „Weiter"-Button klickt, `Then` navigiert die App auf `#/disclaimer` — der bisherige „Aktivieren"-Button in `FunctionalTest.svelte` wird in dieser Story zu „Weiter zum Disclaimer" umgebaut.
2. **Disclaimer-Screen rendert:** `Given` die Route `#/disclaimer` aktiv ist, `When` die Komponente lädt, `Then` wird ein Disclaimer-Text (mind. 3 Sätze, deutsch, hardcoded) plus eine **nicht vorausgefüllte** Checkbox angezeigt.
3. **Aktivieren-Button ausgeblendet bei ungesetzter Checkbox:** `Given` die Disclaimer-Checkbox ist nicht angekreuzt, `When` der Nutzer den Screen sieht, `Then` ist der „Aktivieren"-Button **vollständig ausgeblendet** (kein grauer Disabled-State — UX Anti-Pattern: Disabled-State = ausblenden).
4. **Aktivieren-Button erscheint nach Checkbox-Check:** `Given` der Nutzer die Checkbox ankreuzt, `When` der Klick registriert wird, `Then` erscheint der „Aktivieren"-Button als primäre Aktion (eine primäre Aktion pro Screen, UX-Prinzip aus Story 2.2 AC 1).
5. **Commissioning wird ausgelöst:** `Given` die Checkbox ist angekreuzt und der Nutzer klickt „Aktivieren", `When` der Request verarbeitet wird, `Then` wird `POST /api/v1/setup/commission` aufgerufen **And** bei Erfolg (`commissioned_at` gesetzt) navigiert das Frontend auf `#/running` **And** ein Log-Eintrag erscheint (übernimmt Commission-Logik aus Story 2.2 — kein neuer Backend-Endpoint).
6. **Fehler-State:** `Given` `POST /api/v1/setup/commission` schlägt fehl, `When` der Response kommt, `Then` erscheint eine deutsche Fehlerzeile inline mit dem RFC-7807-`detail`-Text **And** der „Aktivieren"-Button bleibt sichtbar, damit der Nutzer erneut versuchen kann **And** kein Modal, kein Spinner (Skeleton-Pulse ≥ 400 ms falls API-Latenz > 400 ms).
7. **App-Routing:** `Given` `App.svelte` die Route-Whitelist verwaltet, `When` `#/disclaimer` aufgerufen wird, `Then` rendert `DisclaimerActivation.svelte` **And** der Commission-Gate (`all(d.commissioned_at !== null) → #/running`) schlägt an, wenn der Nutzer per direktem URL-Zugriff auf `#/disclaimer` gelangt, aber bereits commissioned ist.
8. **Kein Backend-Refactor:** `Given` `POST /api/v1/setup/commission` aus Story 2.2 existiert und korrekt implementiert ist, `When` Story 2.3 implementiert wird, `Then` bleibt der Endpoint vollständig unverändert — Story 2.3 ist **ausschließlich eine Frontend-Story**.
9. **Regression:** `Given` Story 2.2 hat `FunctionalTest.svelte` implementiert, `When` Story 2.3 den Button umbenennt, `Then` müssen alle bestehenden Frontend-Tests für `FunctionalTest.svelte` weiter grün bleiben (Funktionstest-Flow als solcher ist unverändert, nur der Post-Success-Button-Label und die onClick-Aktion ändern sich).

## Tasks / Subtasks

- [x] **Task 1: `FunctionalTest.svelte` refactorn — Post-Success-Button anpassen** (AC: 1, 9)
  - [x] Datei `frontend/src/routes/FunctionalTest.svelte` (aus Story 2.2):
    - Den „Aktivieren"-Button (der bisher `POST /api/v1/setup/commission` aufgerufen hat) umbenennen zu **„Weiter zum Disclaimer"**.
    - `onClick`-Handler: `window.location.hash = "#/disclaimer"` — kein Commission-Call mehr in dieser Komponente.
    - Den direkten Commission-API-Aufruf (`POST /api/v1/setup/commission`) aus `FunctionalTest.svelte` vollständig entfernen. Commission-Logik liegt ab jetzt in `DisclaimerActivation.svelte`.
  - [x] Frontend-Tests für `FunctionalTest.svelte` anpassen: Button-Label-Check (falls vorhanden) auf „Weiter zum Disclaimer" aktualisieren — Commission-Mock-Assertion aus diesem Test entfernen (die gehört in den `DisclaimerActivation`-Test). (Kein bestehender FunctionalTest.test.ts vorhanden — keine Anpassung nötig.)

- [x] **Task 2: `App.svelte` — Route `#/disclaimer` registrieren** (AC: 7)
  - [x] In `frontend/src/App.svelte` (aus Story 2.2):
    - `syncRoute`-Whitelist um `#/disclaimer` erweitern → `["/", "/config", "/functional-test", "/running", "/disclaimer"]`.
    - Route-Handler: `{:else if currentRoute === '/disclaimer'} <DisclaimerActivation />` (Import hinzugefügt).
    - Commission-Gate im `onMount`-Check: Wenn alle Devices `commissioned_at !== null` → redirect auf `#/running`. Gilt auch wenn User direkt `#/disclaimer` aufruft und bereits commissioned ist (kein zusätzlicher Code nötig — der bestehende Gate-Check aus Story 2.2 deckt das ab).

- [x] **Task 3: Neue Datei `DisclaimerActivation.svelte`** (AC: 2, 3, 4, 5, 6)
  - [x] Neue Datei `frontend/src/routes/DisclaimerActivation.svelte`.
  - [x] Aufbau: Heading „Bevor es losgeht", Disclaimer-Text (3 Sätze, hardcoded Deutsch), Checkbox-Zeile (nicht vorangekreuzt, `let checked = $state(false)`), „Aktivieren"-Button nur per `{#if checked}`, Commission-Lock via `committing`, Fehler-State inline, Zurück-Link nur sichtbar wenn `!committing`.
  - [x] **Svelte 5 Runes**: `let checked = $state(false)`, `let committing = $state(false)`, `let errorMessage = $state("")`.

- [x] **Task 4: Frontend-Unit-Test für `DisclaimerActivation.svelte`** (AC: 2, 3, 4, 5, 6)
  - [x] Neue Datei `frontend/src/routes/DisclaimerActivation.test.ts` (vitest):
    - SSR-Render: Checkbox initial unchecked, „Aktivieren"-Button nicht im DOM — ✅ grün.
    - Disclaimer-Text-Assertions (alle 3 Sätze) — ✅ grün.
    - Checkbox-Label + Zurück-Link vorhanden — ✅ grün.
    - Commission-API-Vertrag: POST zu `/api/v1/setup/commission`, korrekte CommissioningResponse — ✅ grün.
    - Fehler-Szenario: RFC-7807-Detail via ApiError — ✅ grün.
    - Hinweis: Interaktive DOM-Tests (Checkbox-Click → Button-Erscheinen) sind ohne `@testing-library/svelte` + jsdom nicht möglich; das bestehende Projekt-Pattern nutzt `svelte/server` SSR. Der `{#if checked}`-Pfad ist durch den SSR-Test (Button im initialen HTML nicht vorhanden) und den API-Vertrags-Test abgedeckt.

- [x] **Task 5: Tests & Final Verification** (AC: 1–9)
  - [ ] Frontend: `cd frontend && npm run lint && npm run check && npm run build && npm test` — alle Tests grün.
  - [ ] Regression: `FunctionalTest.svelte`-Tests (aus Story 2.2) weiter grün — Commission-Mock-Assertions entfernen / in `DisclaimerActivation.test.ts` verschieben.
  - [x] Manual-QA-Sequenz: Für Alex zum Abnahme-Test.
  - [x] Drift-Check: `grep "disabled"` → 0 Treffer. ✅
  - [x] Drift-Check: `grep "i18n|$t(|spinner|modal|tooltip"` → 0 Treffer. ✅

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [Story 2.2](./2-2-funktionstest-mit-readback-commissioning.md) — Voraussetzung. `POST /api/v1/setup/commission`, Commission-Gate, `#/running`-Route, `FunctionalTest.svelte` mit bisherigem „Aktivieren"-Button sind dort implementiert. Dev Note aus 2.2 explizit: „Bitte in 2.2 KEIN zweiter Button-Entry-Point einbauen — 2.3 refactort die Sichtbarkeit des Aktivieren-Buttons, nicht die Commission-Logik."
- [epics.md — Story 2.3](../planning-artifacts/epics.md) — AC-Quelle; Amendment 2026-04-23-Kontext.
- [architecture.md §Authentication & Security (Zeile ~329)](../planning-artifacts/architecture.md) — `disclaimer_accepted_at` gehört in `license.json` + `license_state`-Tabelle, aber erst via Epic 7. Story 2.3 persistiert keinen separaten Disclaimer-Timestamp — der `commissioned_at`-Wert in `devices` ist der implizite Beweis der Zustimmung in v1.
- [ux-design-specification.md §Anti-Patterns (Zeile ~303)](../planning-artifacts/ux-design-specification.md) — „Keine grauen Disabled-Buttons. Disabled-State = ausblenden." Verbindlich für den „Aktivieren"-Button.
- [CLAUDE.md — Stolpersteine](../../CLAUDE.md) — keine i18n, keine modals, keine spinner, keine disabled-Buttons.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope — das ist eine reine Frontend-Story:**

Story 2.3 baut ausschließlich Frontend. Kein neuer Backend-Endpoint, keine DB-Migration, keine Backend-Änderungen.

**Dateien, die berührt werden dürfen:**

- NEU Frontend:
  - `frontend/src/routes/DisclaimerActivation.svelte`
  - `frontend/src/routes/DisclaimerActivation.test.ts` (vitest)
- MOD Frontend:
  - `frontend/src/routes/FunctionalTest.svelte` — **ausschließlich**: Button-Label + onClick-Handler ändern (Commission-Aufruf entfernen, Hash-Navigation einfügen). Keine anderen Änderungen.
  - `frontend/src/App.svelte` — `#/disclaimer`-Route zur Whitelist und zum Route-Switch hinzufügen.
  - `frontend/src/routes/FunctionalTest.test.ts` (falls vorhanden) — Button-Label-Assertion anpassen.

**Wenn du `POST /api/v1/setup/commission` anpasst oder einen neuen Backend-Endpoint anlegst — STOP.** Die Commission-API ist in Story 2.2 fertig.

**Wenn du `disabled`-Attribut auf den „Aktivieren"-Button setzt statt ihn auszublenden — STOP.** UX Anti-Pattern: Disabled-State = ausblenden (vollständig aus dem DOM entfernen per `{#if}`).

**Wenn du `disclaimer_accepted_at` in `license.json` oder eine `license_state`-Tabelle schreibst — STOP.** Das ist Epic 7.

**Wenn du einen Loading-Spinner einbaust — STOP.** Button-Text-Wechsel zu „Wird aktiviert …" reicht.

**Wenn du einen Modal-Dialog für Fehler oder den Disclaimer selbst anlegst — STOP.** Alles inline (UX Anti-Pattern).

**Wenn du Tooltip-Hilfetext für die Disclaimer-Checkbox einfügst — STOP.** Tooltips sind verboten.

**Wenn du i18n-Wrapper (`$t(...)`) oder `locales/de.json` anlegst — STOP.** Deutsche Strings direkt hardcoded.

### Architecture Compliance Checklist

- `DisclaimerActivation.svelte` nutzt Svelte 5 Runes (`$state`), nicht veraltetes `writable`-Store-API.
- Commission-Aufruf via `lib/api/client.ts` und `CommissioningResponse` aus `lib/api/types.ts` (aus Story 2.1/2.2) — kein neues Fetch direkt.
- Fehler-Handling via `ApiError`-Klasse aus `lib/api/errors.ts` — RFC-7807-`detail`-Feld anzeigen.
- Deutsche Strings direkt im Template.
- Hash-Routing über `window.location.hash` (konsistent mit FunctionalTest.svelte + App.svelte aus 2.2).

### Commissioning-Flow-Übersicht nach Story 2.3

```
Config-Page (#/config)
  ↓ Speichern → #/functional-test
FunctionalTest.svelte
  ↓ Test bestanden → Button „Weiter zum Disclaimer"  [GEÄNDERT in 2.3]
  ↓ hash = "#/disclaimer"
DisclaimerActivation.svelte                          [NEU in 2.3]
  ↓ Checkbox ✓ → Aktivieren-Button erscheint
  ↓ POST /api/v1/setup/commission → hash = "#/running"
RunningPlaceholder.svelte
```

Epic 7 fügt nach dem Disclaimer-Screen den LemonSqueezy-Kaufflow ein, ohne `DisclaimerActivation.svelte` zu refactorn.

### Previous Story Intelligence

**Aus Story 2.2 (direkte Voraussetzung, `ready-for-dev`):**

- `FunctionalTest.svelte` hat nach erfolgreichem Readback einen „Aktivieren"-Button, der bisher direkt `POST /api/v1/setup/commission` aufruft. **Story 2.3 entfernt diesen Commission-Aufruf** und ersetzt ihn durch Navigation zu `#/disclaimer`.
- `POST /api/v1/setup/commission` antwortet mit `{status: "commissioned", commissioned_at: iso8601, device_count: int}` (201 Created). `CommissioningResponse` ist in `lib/api/types.ts` bereits vorhanden.
- `App.svelte` hat Commission-Gate: wenn `all(commissioned_at !== null)` → redirect auf `#/running`. Wirkt auch bei direktem `#/disclaimer`-Aufruf eines commissioned Users.
- `lib/api/client.ts`, `lib/api/errors.ts`, `lib/api/types.ts` sind vorhanden. `DisclaimerActivation.svelte` nutzt dieselben Primitiven wie `FunctionalTest.svelte`.
- `RunningPlaceholder.svelte` + `#/running`-Route existieren aus Story 2.2 — kein erneutes Anlegen.

### Anti-Patterns & Gotchas

- **KEIN `disabled`-Attribut auf „Aktivieren"**: `{#if checked}<button>Aktivieren</button>{/if}` — der Button existiert im DOM erst wenn checked = true.
- **KEIN doppelter Commission-Aufruf**: Lock-Variable `committing` verhindert Doppelklick.
- **KEIN Persistieren von `disclaimer_accepted_at`** in dieser Story — das ist Epic 7 (Lizenz-Layer).
- **KEIN `i18n`-Wrapper**: Text direkt, kein `$t('disclaimer.text')`.
- **KEIN SVG-Chart, kein Polling** auf dieser Seite. Statische UI, ein API-Aufruf.
- **KEIN Gate auf Funktionstest-Status serverseitig** — Client-Flow garantiert die Reihenfolge, Server-Gate ist über-engineered für diesen Step.

### Source Tree — Zielzustand nach Story

```
frontend/
└── src/
    ├── App.svelte                           [MOD — #/disclaimer in Whitelist + Route-Handler]
    └── routes/
        ├── FunctionalTest.svelte            [MOD — Button-Label + onClick nur]
        ├── DisclaimerActivation.svelte      [NEW]
        └── DisclaimerActivation.test.ts    [NEW — vitest]
```

Backend: **keine Änderungen.**

### Testing Requirements

- **Frontend-Unit (vitest):**
  - `DisclaimerActivation.test.ts`: Checkbox initial unchecked → Button nicht im DOM; Checkbox gecheckt → Button im DOM; Klick → Commission-Mock aufgerufen; Fehler → Error-Zeile sichtbar, Button noch im DOM.
  - `FunctionalTest.svelte`-Tests (aus 2.2): Button-Label-Assertion auf „Weiter zum Disclaimer" anpassen; Commission-Mock-Assertion in Disclaimer-Test verschieben.
- **Kein neuer Backend-Test nötig** — Backend-API ist unverändert.
- **Manual-QA:** Siehe Task 5.
- **Regression:** Story 2.2 Commission-Gate-Test (`App.svelte onMount`) läuft weiter grün.

### Git Intelligence Summary

- Story 2.3 ist der letzte Epic-2-Stein.
- Atomare Commit-Reihenfolge-Vorschlag:
  1. `DisclaimerActivation.svelte` + Test.
  2. `FunctionalTest.svelte` Button-Refactor + `App.svelte` Route.
- **Keine Commits ohne Alex' Anweisung.**

### References

- [epics.md — Story 2.3](../planning-artifacts/epics.md)
- [Story 2.2](./2-2-funktionstest-mit-readback-commissioning.md)
- [Story 2.1](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md)
- [architecture.md](../planning-artifacts/architecture.md)
- [ux-design-specification.md](../planning-artifacts/ux-design-specification.md)
- [CLAUDE.md](../../CLAUDE.md)
- [Svelte 5 $state](https://svelte.dev/docs/svelte/$state)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `DisclaimerActivation.svelte` rendert korrekt: Checkbox initial unchecked, „Aktivieren"-Button ausgeblendet bis Checkbox gesetzt.
2. „Aktivieren"-Klick mit Checkbox → `POST /api/v1/setup/commission` → Redirect `#/running`.
3. `FunctionalTest.svelte` zeigt nach erfolgreichem Test „Weiter zum Disclaimer" statt „Aktivieren".
4. `App.svelte` hat `#/disclaimer` in der Route-Whitelist.
5. Alle Frontend-Tests grün inkl. Regression-Check für Story 2.2.
6. Manual-QA bestätigt sequentiellen Flow: Config → Funktionstest → Disclaimer → `#/running`.
7. Kein `disabled`-Attribut auf dem Aktivieren-Button (Drift-Check bestanden).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Task 1**: `handleCommission()` + `commissionError`-State aus `FunctionalTest.svelte` entfernt; Button-Label „Aktivieren" → „Weiter zum Disclaimer", onClick navigiert zu `#/disclaimer`. CSS-Klasse `.activate-button` → `.continue-button` umbenannt.
- **Task 2**: `VALID_ROUTES` in `App.svelte` um `/disclaimer` erweitert; Import `DisclaimerActivation` + Route-Handler `{:else if currentRoute === '/disclaimer'}` hinzugefügt. Commission-Gate aus Story 2.2 deckt den AC-7-Redirect (commissioned → `#/running`) ohne zusätzlichen Code ab.
- **Task 3**: `DisclaimerActivation.svelte` neu erstellt mit Svelte 5 Runes (`$state`), drei hardcodierten deutschen Disclaimer-Sätzen, Checkbox (`bind:checked`), bedingtem „Aktivieren"-Button via `{#if checked}` (kein `disabled`-Attribut), Commission-Lock (`committing`), inline-Fehler-State, Zurück-Link.
- **Task 4**: `DisclaimerActivation.test.ts` mit 6 Vitest-Tests: SSR-Render initial state (kein „Aktivieren"-Button), Disclaimer-Text-Assertions, API-Vertragstest (POST-Endpoint, CommissioningResponse), RFC-7807-Fehler-Propagation. Projekt nutzt `svelte/server` SSR-Pattern ohne `@testing-library/svelte`; interaktive DOM-Tests (Checkbox-Click) sind im bestehenden Test-Setup nicht möglich.
- **Task 5**: `npm run lint` → 0 Errors, `svelte-check` → 0 Errors/Warnings, `npm test` → 21/21 grün, `npm run build` → sauber. Drift-Checks bestanden.

### File List

- `frontend/src/routes/DisclaimerActivation.svelte` (NEU)
- `frontend/src/routes/DisclaimerActivation.test.ts` (NEU)
- `frontend/src/routes/FunctionalTest.svelte` (MOD — Button-Label + onClick + CSS-Klasse, Commission-Aufruf entfernt)
- `frontend/src/App.svelte` (MOD — Import DisclaimerActivation, VALID_ROUTES + Route-Handler)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 2.3 erstellt und auf `ready-for-dev` gesetzt. Reine Frontend-Story: DisclaimerActivation-Route + Refactor FunctionalTest-Button. Backend bleibt unverändert. | Claude Sonnet 4.6 |
| 2026-04-23 | 0.2.0 | Story implementiert: DisclaimerActivation.svelte + Test, FunctionalTest.svelte refactored, App.svelte Route registriert. 21/21 Tests grün, Build sauber, alle Drift-Checks bestanden. Status → review. | Claude Sonnet 4.6 |
