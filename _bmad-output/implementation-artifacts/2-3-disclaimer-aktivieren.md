# Story 2.3: Disclaimer + Aktivieren

Status: done

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
  - [x] Drift-Check: `grep "disabled"` → 0 Treffer. ✅ (Nach Review-Patch 2026-04-24: 1 Treffer auf Checkbox-Input `disabled={committing}` — **kein UX-Anti-Pattern-Verstoß**, da die Regel „Disabled-State = ausblenden" nur den primären Aktivieren-Button betrifft; Checkbox während in-flight POST ist semantisch korrektes `disabled`, keine UX-Aussage.)
  - [x] Drift-Check: `grep "i18n|$t(|spinner|modal|tooltip"` → 0 Treffer. ✅

### Review Findings (Code-Review 2026-04-24)

Triagiert aus 3-Layer-Review (Blind Hunter / Edge Case Hunter / Acceptance Auditor). Reihenfolge: **decision-needed** → **patch** → **defer/dismiss**.

#### Decision-Needed (Blocker — User-Call vor Patches)

- [x] [Review][Decision] **Disclaimer-First Flow Re-Architecture** — User-Input 2026-04-24: Der Disclaimer muss als allererstes kommen, nicht am Ende. **RESOLVED 2026-04-24: Option 3 (Story-Split) gewählt.** Neue Story [2-3a-pre-setup-disclaimer-gate.md](./2-3a-pre-setup-disclaimer-gate.md) ist angelegt und auf `ready-for-dev` gesetzt mit dem vom User vorgegebenen Disclaimer-Wortlaut. Story 2.3 (diese Story, Activation-Screen) bleibt wie committed in `a94c0f8`. Open Question in 2.3a: „Solarbot" vs. „Solalex" Branding-Konsistenz.
- [x] [Review][Decision] **Interaktive Komponenten-Tests — @testing-library/svelte + jsdom hinzufügen?** — **RESOLVED 2026-04-24: Option (b) gewählt — SSR-only akzeptiert.** Gap ist bekannt und in Change Log dokumentiert. Patches P11–P13 (Test-Qualität) bleiben in Scope, werden aber innerhalb der SSR-Grenzen umgesetzt: präziserer String-Check statt Substring (P11), `expect.assertions`-Guard (P13), Component-level Mock-Verify via `vi.mock('$lib/api/client')` + Direkt-Invokation der Component-Helpers (P12, soweit ohne DOM-Interaktion möglich). AC 4 (Button erscheint nach Check) bleibt nicht automatisiert testbar.

#### Patch (fixbar ohne weitere User-Entscheidung)

- [x] [Review][Patch] **P1 — Commission-Gate schützt `#/disclaimer` nicht vor commissioned-User** [frontend/src/App.svelte:71–76] — FIXED: `allCommissioned`-Redirect triggert jetzt für alle Wizard-Routes (`/`, `/disclaimer`, `/functional-test`, `/config`).
- [x] [Review][Patch] **P2 — `committing`-Flag bleibt auf `true` nach Success-Pfad hängen** [DisclaimerActivation.svelte] — FIXED: `committing = false` über `finally`-Block auf allen Pfaden (mit `mounted`-Guard).
- [x] [Review][Patch] **P3 — Back-Link versteckt → User trapped bei hängendem POST** [DisclaimerActivation.svelte] — FIXED: `{#if !committing}`-Wrapper um Back-Link entfernt; Back-Link immer sichtbar als Escape. Timer-basierter Timeout (`AbortSignal.timeout`) skipped: würde `client.commission()`-Signatur erweitern (API-Touch), geringer Mehrwert bei vorhandenem Escape-Pfad.
- [x] [Review][Patch] **P4 — Race: Component wird während `await client.commission()` unmounted** [DisclaimerActivation.svelte] — FIXED: `let mounted = true; onDestroy(() => mounted = false)` + Guards nach `await` in try/catch/finally.
- [x] [Review][Patch] **P5 — Checkbox bleibt während `committing` interagierbar** [DisclaimerActivation.svelte] — FIXED: Button-Guard erweitert auf `{#if checked || committing}` (Button bleibt während committing sichtbar) + Checkbox `disabled={committing}` (semantisches Disabled während In-Flight, keine UX-Anti-Pattern-Verletzung — Rule gilt nur für primary Action-Buttons).
- [x] [Review][Patch] **P6 — Leere RFC-7807-`detail` versteckt Fehler komplett** [DisclaimerActivation.svelte] — FIXED: `formatApiError()`-Helper liefert Fallback-String wenn sowohl `title` als auch `detail` leer sind.
- [x] [Review][Patch] **P7 — RFC-7807-`err.title` wird verworfen, nur `detail` angezeigt** [DisclaimerActivation.svelte] — FIXED: `formatApiError()` komponiert `title: detail` wenn beide gesetzt; Einzelwert wenn nur einer gesetzt.
- [x] [Review][Patch] **P8 — Netzwerk-Fehler (status 0) ist ununterscheidbar von 5xx** [DisclaimerActivation.svelte] — FIXED: `err.status === 0`-Branch in `formatApiError()` mit expliziter „Keine Verbindung zum Add-on …"-Meldung.
- [x] [Review][Patch] **P9 — Hash-Wechsel auf `#/running` ohne Response-Verifikation** [DisclaimerActivation.svelte] — FIXED: `if (response.status !== 'commissioned')` prüft vor Navigation; setzt sonst errorMessage = „Unerwartete Antwort vom Backend".
- [x] [Review][Patch] **P10 — Stale `errorMessage` nach Checkbox-Uncheck/Recheck** [DisclaimerActivation.svelte] — FIXED: `$effect(() => { if (!checked) errorMessage = ''; })`.
- [x] [Review][Patch] **P11 — Test-Assertion `.not.toContain('Aktivieren')` kollidiert mit „Aktivierung …"** [DisclaimerActivation.test.ts] — FIXED: Regex-Assertion `.not.toMatch(/<button[^>]*class="[^"]*activate-button/)` statt Substring-Check.
- [x] [Review][Patch] **P12 — Tests validieren nur `client.commission()` direkt, nicht den Component-getriggerten Call** [DisclaimerActivation.test.ts] — PARTIAL FIX (SSR-Limit, D2-Decision): describe-Block umbenannt auf „client-level, used by DisclaimerActivation" + Kommentar der die SSR-Beschränkung dokumentiert. Interaktive Component-Trigger-Verifikation bleibt explizite Gap (D2 = SSR-only akzeptiert).
- [x] [Review][Patch] **P13 — Test-`try/catch` ohne Fail-on-no-throw** [DisclaimerActivation.test.ts] — FIXED: `expect(caught).toBeDefined()` vor `isApiError(caught)`-Check; nicht-werfende `commission()` würde jetzt explizit fehlschlagen.
- [x] [Review][Patch] **P14 — CSS: `.back-link` doppelte `width`-Deklaration** [DisclaimerActivation.svelte] — FIXED: erste `width: min(100%, 640px)` entfernt; `width: fit-content` + `margin: 0 auto` (in Flex-Column-Parent) bleibt zum Zentrieren.
- [x] [Review][Patch] **P15 — Aktivieren-Button ohne `type="button"`** [DisclaimerActivation.svelte] — FIXED: `type="button"` explizit gesetzt.
- [x] [Review][Patch] **P16 — Accessibility** [DisclaimerActivation.svelte] — FIXED: `<p id="disclaimer-text">` + `<input aria-describedby="disclaimer-text">` + `<p class="error-line" role="alert" aria-live="polite">`. Neuer SSR-Test sichert die aria-Verknüpfung ab.
- [~] [Review][Patch] **P17 — Potenziell ungenutzter `isApiError`-Import in `FunctionalTest.svelte`** [FunctionalTest.svelte] — DISMISSED als False Positive: `grep isApiError FunctionalTest.svelte` → noch in Zeile 73 (`loadError` für `getDevices()`) und Zeile 94 (`testError` für `runFunctionalTest()`) genutzt. Kein Dead-Code, kein Lint-Error.

#### Defer (pre-existing / out-of-scope)

- [x] [Review][Defer] **Hardcoded Route-Strings verteilt** [App.svelte, FunctionalTest.svelte, DisclaimerActivation.svelte] — deferred, Route-Const-Module (`lib/routes.ts`) wäre eigene Refactor-Story, unabhängig von 2.3.
- [x] [Review][Defer] **Keine Idempotency-Key / CSRF auf Commission-POST** [DisclaimerActivation.svelte / Backend] — deferred, Backend-Thema (Epic 7 Lizenz / HA-Ingress-Isolation-Kontext); Frontend-Side würde nur symptomatisch helfen.
- [x] [Review][Defer] **Gradient/Shadow-Tokens im Activate-Button dupliziert aus FunctionalTest.svelte** [DisclaimerActivation.svelte — Button-CSS] — deferred, gemeinsame Button-Komponente wäre Design-System-Story (Epic 5 Dashboard hat sie nötig).
- [x] [Review][Defer] **Back-Link via `href="#/functional-test"` pollutet Browser-History-Stack** [DisclaimerActivation.svelte — Back-Link] — deferred, `history.back()` statt Hash-Push wäre ideal; pre-existing Pattern in FunctionalTest.svelte auch.
- [x] [Review][Defer] **`res.json()`-Rejection auf 2xx unbehandelt im `client.ts`** [frontend/src/lib/api/client.ts — pre-existing] — deferred, pre-existing aus Story 2.1; betrifft alle Endpoints, nicht spezifisch 2.3.

#### Dismissed (Noise / False Positive)

- `color-mix(..., white 8%)` defeat von Theming [DisclaimerActivation.svelte — Button-CSS] — Dark Mode ist in v1 explizit gestrichen (CLAUDE.md Amendment 2026-04-23).
- Rapid Double-Click auf „Weiter zum Disclaimer" [FunctionalTest.svelte:360] — `window.location.hash = '#/disclaimer'` ist idempotent; `hashchange`-Re-Trigger ist harmlos.
- `testPhase` flash während Transition Race [FunctionalTest.svelte:360-Umgebung] — pre-existing aus Story 2.2, nicht durch 2.3 eingeführt.
- Inline Arrow-Handler in Template [FunctionalTest.svelte:360] — konsistent mit bestehendem Muster im Repo; stilistische Präferenz.

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
| 2026-04-24 | 0.3.0 | Code-Review 3-Layer (Blind/Edge/Auditor): 2 Decisions resolved (D1 → Story 2.3a gespawnt; D2 → SSR-only akzeptiert), 16 Patches applied + 1 dismissed (P17 False Positive), 5 Findings ins deferred-work.md verschoben. Tests 22/22 grün, Build sauber, Lint 0, svelte-check 0. Status → done. | Claude Opus 4.7 (Code-Review) |
