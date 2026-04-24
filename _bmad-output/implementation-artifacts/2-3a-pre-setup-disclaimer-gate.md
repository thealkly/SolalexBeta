# Story 2.3a: Pre-Setup-Disclaimer-Gate (vor Config + Funktionstest)

Status: review

<!-- Spawned aus Story 2.3 Code-Review 2026-04-24, Decision D1. User-Intent: Disclaimer muss als allererstes kommen, nicht am Ende des Setup-Flows. -->

## Story

Als Nutzer,
möchte ich beim allerersten Start des Add-ons einen Disclaimer sehen und explizit bestätigen,
so dass ich verstehe, wofür Solarbot zuständig ist und in welchem Rahmen ich es einsetze, **bevor** ich Entitäten konfiguriere oder einen Funktionstest auslöse.

## Acceptance Criteria

1. **Gate-Route beim First-Launch:** `Given` der User startet das Add-on zum ersten Mal (kein Device commissioned, Pre-Disclaimer noch nicht bestätigt), `When` er die Sidebar öffnet, `Then` zeigt die App **nicht** `#/config` oder `#/functional-test`, sondern `#/disclaimer` als allererste Ansicht.
2. **Disclaimer-Text verbindlich, 3 Absätze, hardcoded deutsch:** Exakter Wortlaut (siehe Task 2). Kein i18n-Wrapper.
3. **Checkbox nicht vorausgefüllt, exakter Label-Text (siehe Task 2).**
4. **„Weiter"-Button ausgeblendet bei ungesetzter Checkbox:** UX-Anti-Pattern „Disabled-State = ausblenden" — kein grauer disabled-Button, Button existiert erst im DOM wenn Checkbox gecheckt.
5. **„Weiter"-Button erscheint nach Checkbox-Check und routet auf `#/config`:** Primäre Aktion, ein Klick → `window.location.hash = '#/config'`.
6. **Acceptance-Persistence clientseitig:** Nach „Weiter"-Klick wird `localStorage.setItem('solalex_pre_disclaimer_accepted', '1')` gesetzt. Kein Backend-Call, keine DB-Migration, kein neuer API-Endpoint in v1. (Epic 7 kann das später nach `/data/license.json` migrieren.)
7. **Route-Gate auf `#/config` und `#/functional-test`:** `App.svelte` onMount — wenn `!localStorage.getItem('solalex_pre_disclaimer_accepted')` UND `!allCommissioned`, dann forced redirect auf `#/disclaimer`. Gilt auch bei direktem URL-Zugriff.
8. **Kein Backend-Refactor:** Rein Frontend-Story, kein Commission-POST, kein neuer API-Endpunkt, keine Schema-Migration.
9. **Abgrenzung zu Story 2.3 (Activation-Screen):** Die bereits existierende Komponente `DisclaimerActivation.svelte` aus Story 2.3 bleibt als Activation-Gate am Ende des Setup-Flows **unberührt**. Story 2.3a führt nur den Pre-Setup-Disclaimer ein. Eine eventuelle Refactor-Konsolidierung (doppelte Disclaimer-Wall vs. ein gemeinsamer Screen) ist **nicht** Scope dieser Story und wird erst entschieden, wenn 2.3a produktiv ist.
10. **Reload-Resilienz:** Browser-Reload auf `#/disclaimer` (User hat noch nicht „Weiter" geklickt) → bleibt auf `#/disclaimer`. Browser-Reload auf `#/config` nach Accept → bleibt auf `#/config`. LocalStorage überlebt Add-on-Restart (Iframe-Origin ist stabil).

## Tasks / Subtasks

- [x] **Task 1: Neue Komponente `PreSetupDisclaimer.svelte`** (AC 2, 3, 4, 5, 6)
  - [x] Neue Datei `frontend/src/routes/PreSetupDisclaimer.svelte`.
  - [x] Svelte 5 Runes: `let checked = $state(false)`.
  - [x] Layout: Heading „Bevor es losgeht", 3-Absatz-Disclaimer, Checkbox-Zeile (nicht vorangekreuzt), „Weiter"-Button via `{#if checked}`.
  - [x] OnClick „Weiter": `localStorage.setItem('solalex_pre_disclaimer_accepted', '1'); window.location.hash = '#/config';`.
  - [x] Styling: konsistent mit `DisclaimerActivation.svelte` (Primary-Button-Look), kein Modal, kein Tooltip, kein Spinner.

- [x] **Task 2: Disclaimer-Text + Checkbox-Label einbauen (verbindlicher Wortlaut)** (AC 2, 3)

  **Absatz 1:**
  > Solarbot steuert deine PV-/Akku-/Verbraucherlogik über Home Assistant. Bitte aktiviere Solarbot nur, wenn deine Anlage fachgerecht installiert ist und du sicher bist, dass die gewählten Entitäten, Grenzwerte und Geräte korrekt sind.

  **Absatz 2:**
  > Solarbot ersetzt keine Elektrofachkraft, keine Anlagenprüfung und keinen Netzschutz. Die App darf nicht für sicherheitskritische Funktionen verwendet werden. Falsche Einstellungen, fehlerhafte Sensorwerte, instabile Verbindungen oder parallele Automationen können zu unerwünschtem Verhalten führen.

  **Absatz 3:**
  > Ich bestätige, dass ich für Installation, Konfiguration und Betrieb meiner Anlage selbst verantwortlich bin und Solarbot nur innerhalb der zulässigen technischen und rechtlichen Grenzen verwende.

  **Checkbox-Label (exakt):**
  > Ich habe die Sicherheitshinweise gelesen und verstanden. Ich bin für die korrekte Installation, Konfiguration und den sicheren Betrieb meiner Anlage selbst verantwortlich.

  **✅ Open Question entschieden (2026-04-24, Alex):** Text auf „Solalex" angepasst (Repo-Codename-Konsistenz mit CLAUDE.md, FastAPI-Title, Frontend-H1). Wortlaut sonst verbindlich wie oben.

- [x] **Task 3: `App.svelte` — Route-Gate einbauen** (AC 1, 7, 10)
  - [x] `VALID_ROUTES`-Set um `/activate` erweitert (Neu für verschobene Activation-Route). `/disclaimer` bleibt und zeigt nun `<PreSetupDisclaimer />`. Route-Handler für `/activate` zeigt `<DisclaimerActivation />`.
  - [x] **Task 3a: Routen-Disambiguation entschieden (2026-04-24, Alex):** Pre-Setup = `#/disclaimer`, Activation = `#/activate`. Patch in `FunctionalTest.svelte` (L156: `#/disclaimer` → `#/activate`) + `App.svelte` (Route-Handler + `wizardRoutes`-Set).
  - [x] OnMount-Gate: Nach dem bestehenden Commission-Gate (allCommissioned → `#/running`), zusätzlich geprüft: wenn `!localStorage.getItem('solalex_pre_disclaimer_accepted')` und `currentRoute !== '/disclaimer'` → `window.location.hash = '#/disclaimer'`. Zusätzlich wurde der `allCommissioned`-Check gehärtet (gilt nur wenn `devices.length > 0` — sonst fällt ein leeres Device-Array in den Pre-Disclaimer-Gate und nicht in den „bereits commissioned"-Pfad).

- [x] **Task 4: Unit-Tests `PreSetupDisclaimer.test.ts`** (AC 2, 3, 4, 5, 6)
  - [x] SSR-Render: Checkbox unchecked → Button nicht im DOM; Disclaimer-Text (alle 3 Absätze wörtlich) im HTML vorhanden; Checkbox-Label wörtlich vorhanden; `aria-describedby` korrekt gesetzt; kein `disabled`-Attribut am Button (Anti-Pattern „Disabled-State = ausblenden").
  - [x] Whitespace-Normalisierung (`html.replace(/\s+/g, ' ')`) für die wörtlichen Absatz-Assertions — SSR rendert Template-Einrückung mit in den Output.

- [x] **Task 5: Regression + Final Verification**
  - [x] `FunctionalTest.svelte`-Flow (Story 2.2) und `DisclaimerActivation.svelte` (Story 2.3) unverändert grün (27/27 Tests).
  - [x] `npm run lint && npm run check && npm test && npm run build` — alle grün. (`localStorage` zu ESLint-Globals ergänzt.)
  - [x] Drift-Checks: `grep "disabled"` in neuer Komponente → 0 (nur im Test-Fall, der explizit `disabled` verhindert). `grep -E "i18n|\$t\(|spinner|modal|tooltip"` in neuen Dateien → 0.
  - [ ] Manual-QA: Frischer Add-on-Install (localStorage leer) → sieht `#/disclaimer`; Direkt auf `#/config` ohne Accept → redirected auf `#/disclaimer`; Nach Accept → `#/config` bleibt. *(Von Alex auf echter HA-Instanz zu verifizieren — kein automatisierter E2E-Stack in v1.)*

## Dev Notes

### Architektur-Bezugspunkte

- [Story 2.3 (Activation-Gate)](./2-3-disclaimer-aktivieren.md) — Vorgänger im Flow (am Ende), bleibt unverändert. 2.3a ist die Ergänzung am Anfang.
- [CLAUDE.md — Stolpersteine](../../CLAUDE.md) — keine i18n, keine Modals, keine Spinner, keine Disabled-Buttons.
- [ux-design-specification.md §Anti-Patterns](../planning-artifacts/ux-design-specification.md) — „Disabled-State = ausblenden".

### Technical Requirements

- **Reine Frontend-Story:** Keine Backend-Änderung, keine DB-Migration, kein neuer Endpoint.
- **Persistence:** `localStorage` (nicht sessionStorage — überlebt Tab-Close und Add-on-Restart). Key: `solalex_pre_disclaimer_accepted`, Value: `'1'`.
- **Route-Konflikt `#/disclaimer`:** Task 3a muss vor Implementierung entschieden werden. Default-Vorschlag: Pre-Setup bekommt `#/disclaimer`, Activation wird auf `#/activate` umgezogen (kleiner Patch in Story 2.3 `FunctionalTest.svelte:360` + `App.svelte`).
- **Kein `disclaimer_accepted_at` in DB:** Epic 7 (Lizenz) macht das später serverseitig. v1 bleibt bei `localStorage`.

### Dateien, die berührt werden

- NEU: `frontend/src/routes/PreSetupDisclaimer.svelte`, `frontend/src/routes/PreSetupDisclaimer.test.ts`
- MOD: `frontend/src/App.svelte` (Gate-Logik + Route-Handler), `frontend/src/routes/FunctionalTest.svelte` (Route-Ziel falls Umnennung `#/disclaimer` → `#/activate`)

### Source Tree — Zielzustand nach Story

```
frontend/src/
├── App.svelte                           [MOD — PreDisclaimer-Gate onMount + Route-Handler]
└── routes/
    ├── PreSetupDisclaimer.svelte        [NEW]
    ├── PreSetupDisclaimer.test.ts       [NEW]
    ├── DisclaimerActivation.svelte      [unverändert — 2.3]
    ├── FunctionalTest.svelte            [evtl. MOD — Route-Ziel umstellen falls Task-3a so entschieden]
    └── ...
```

### Testing Requirements

- SSR-Unit-Tests (analog zu `DisclaimerActivation.test.ts`).
- Falls D2 (Review Story 2.3) → @testing-library/svelte + jsdom kommt: interaktive Tests nachziehen.
- Manual-QA auf echter HA-Instanz.

## Dev Agent Record

### Implementierungs-Entscheidungen

- **Task 3a Routen-Disambiguation:** Pre-Setup-Disclaimer bekommt `#/disclaimer` (prominent, kommt im Flow zuerst), DisclaimerActivation wurde auf `#/activate` umgezogen. Umfang: 1 Zeile in `FunctionalTest.svelte` (Button-Onclick-Ziel) + `App.svelte` (Route-Handler, `VALID_ROUTES`, `wizardRoutes`-Set).
- **Branding-Konsistenz (Open Question):** Text auf „Solalex" angepasst (Alex-Entscheidung, 2026-04-24). Sonst wortwörtlich wie in der Story vorgegeben.
- **`allCommissioned`-Härtung:** Bisher flaggte `devices.every(...)` bei `devices.length === 0` als `true` (vacuous truth), weil der alte Code das per `if (devices.length === 0) return` vor dem Check abfing. Die neue Gate-Logik muss den Device-leeren Fall aber im selben Block behandeln, damit der Pre-Disclaimer-Gate greifen kann. Daher `allCommissioned = devices.length > 0 && devices.every(...)` — leere Device-Liste fällt nun in den Pre-Disclaimer-Gate.
- **ESLint-Global `localStorage`:** Zu `eslint.config.js` globals hinzugefügt. Legitimer Browser-API, bisher nicht im Code verwendet, daher nicht im bestehenden Whitelist.
- **Test-Whitespace-Normalisierung:** `svelte/server` SSR rendert Template-Einrückung mit, deshalb `html.replace(/\s+/g, ' ')` vor den Verbatim-Assertions der Disclaimer-Absätze.

### Completion Notes

- Alle 10 Acceptance Criteria erfüllt (AC 1–10).
- `DisclaimerActivation.svelte` (Story 2.3) bleibt **unverändert** (AC 9 erfüllt) — nur die Route-Einbindung in `App.svelte` + der Button-Link in `FunctionalTest.svelte` wurden umgezogen.
- Frontend-only Story: keine Backend-Änderung, keine DB-Migration, kein API-Endpoint (AC 8 erfüllt).
- Test-Stack: 5 neue SSR-Tests in `PreSetupDisclaimer.test.ts`. Gesamt 27/27 Tests grün. Interaktive Tests (Checkbox-Klick → Button → Redirect) sind bewusste Lücke (analog Story 2.3 Decision D2, kein jsdom-Stack in v1).
- Manual-QA (AC 1 + 7 + 10) verbleibt offen bis Alex auf echter HA-Instanz verifiziert — kein automatisierter E2E-Stack in v1.

### File List

- **NEU:** `frontend/src/routes/PreSetupDisclaimer.svelte` (Pre-Setup-Disclaimer-Komponente)
- **NEU:** `frontend/src/routes/PreSetupDisclaimer.test.ts` (SSR-Unit-Tests)
- **MOD:** `frontend/src/App.svelte` (Import, `VALID_ROUTES` um `/activate` erweitert, Route-Handler `/disclaimer` → PreSetupDisclaimer + neuer `/activate` → DisclaimerActivation, `wizardRoutes`-Set erweitert, Pre-Disclaimer-Gate in onMount, `allCommissioned`-Härtung)
- **MOD:** `frontend/src/routes/FunctionalTest.svelte` (Button-Onclick `#/disclaimer` → `#/activate` nach Funktionstest-Erfolg)
- **MOD:** `frontend/eslint.config.js` (`localStorage` zu Browser-Globals ergänzt)
- **MOD:** `_bmad-output/implementation-artifacts/sprint-status.yaml` (2-3a → in-progress → review)

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-24 | 0.1.0 | Story aus 2.3-Review Decision D1 (Story-Split) gespawnt. User-vorgegebener Disclaimer-Text + Checkbox-Label verbindlich. Open Question: Solarbot vs. Solalex Branding-Konsistenz. | Claude Opus 4.7 (Code-Review) |
| 2026-04-24 | 0.2.0 | Implementierung. Route-Disambiguation (Pre-Setup=/disclaimer, Activation=/activate). Branding auf „Solalex" (Alex-Entscheidung). Pre-Disclaimer-Gate + `allCommissioned`-Härtung in `App.svelte`. 5 SSR-Tests, 27/27 grün, lint + check + build grün. Status → review. | Claude Opus 4.7 (Dev) |
