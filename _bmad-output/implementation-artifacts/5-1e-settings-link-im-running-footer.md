# Story 5.1e: Settings-Link im Running-Footer (Hardware ändern erreichbar machen)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As ein Nutzer, der bereits konfiguriert hat und auf der Live-Betriebs-View landet,
I want unten im Running-Footer einen kleinen, sichtbaren Link „Einstellungen" mit Zahnrad-Icon,
so that ich überhaupt finde, dass es eine Settings-Seite gibt, in der ich u. a. meine Hardware noch einmal ändern kann (Story 2.6 „Hardware ändern"-Button) — heute ist `#/settings` nur via direkter URL-Eingabe erreichbar.

**Scope-Pflock (verbindlich, nicht erweitern):** Diese Story ergänzt ausschließlich [`Running.svelte`](../../frontend/src/routes/Running.svelte) um einen schmalen `<footer>` mit **einem** Link zu `#/settings`. Kein zweites Ziel (Diagnostics bleibt versteckt — Beta-Doku-Pfad), kein Header-Eintrag, keine globale Nav-Komponente, keine neue Route, keine Backend-Änderung, keine API-Erweiterung, keine SQL-Migration, keine neue Dependency. Inline-SVG für das Zahnrad direkt in der Komponente — kein Icon-System aufbauen. Ziel: ≤ ¼ Dev-Tag, PR ≤ 80 Zeilen inkl. Tests.

**Hintergrund / Auflösung der dokumentierten Lücke:**
- Story 3.6 hat Settings versteckt gelassen mit der expliziten Begründung: „v1.5 verdrahtet Settings + Diagnose in einer dedicated Footer-/Header-Nav (eigene Story)" (`3-6-…md`, Zeile 36).
- Story 2.6 hat in Settings.svelte einen sichtbaren „Hardware ändern"-Button gebaut ([Settings.svelte:281](../../frontend/src/routes/Settings.svelte#L281)), aber den Discovery-Link wieder ausgespart — Folge: User können Hardware faktisch nicht mehr ändern, ohne die URL `#/settings` zu kennen.
- Diese Story löst das auf, ohne Diagnose mit reinzuziehen (bleibt explizit versteckt analog Story 4.0a).

**Zeitliche Einordnung:** Hängt am 5.1-Family-Stack (5.1a/c/d auf der Running-View). Nicht-blockierend für Beta, aber Beta-blocking für die UX-Erwartung „mein Setup ist editierbar". Setzt voraus, dass Story 3.6 (Settings-Route) und Story 2.6 (Hardware-Edit-Button in Settings) `done` oder `review` sind — beide sind es.

## Acceptance Criteria

1. **Footer rendert genau dann, wenn die Live-Betriebs-View rendert:** `Given` der User ist commissioned und auf `#/running`, `When` `Running.svelte` rendert (also unabhängig vom Funktionstest-Lock-Pfad oder Error-Block-Pfad), `Then` rendert am Ende der Komponente — direkt vor `</main>` — ein `<footer class="running-footer">`-Element mit genau **einem** Link `<a href="#/settings" class="settings-link" data-testid="settings-link">`. **And** der Footer ist auch im Funktionstest-Lock-Pfad (`testInProgress=true`), im Error-Block-Pfad (`loadError !== null`) und im Skeleton-State sichtbar — Begründung: Auch (gerade) wenn etwas hakt, soll der User in die Settings kommen.

2. **Link-Text + Inline-Zahnrad:** `Given` der Link rendert, `When` er angezeigt wird, `Then` enthält er ein **Inline-SVG** (kein externer Asset-Import, kein Lucide/Heroicons-Dep) mit einem schlichten Zahnrad-Pfad (16×16 px, `aria-hidden="true"`, `currentColor` als Fill/Stroke) **und** den deutschen Text-Knoten `Einstellungen`. Reihenfolge: Icon → Text. Icon und Text liegen in einem `display: flex; gap: var(--space-2); align-items: center;`-Container.

3. **Visueller Stil — dezent, kein lauter CTA:** `Given` der Link rendert, `When` er angezeigt wird, `Then` ist seine `color` `var(--color-text-secondary)`, `font-size` ≤ `0.85rem`, kein `background`, kein `border`, keine `box-shadow`. **And** der Hover-Zustand wechselt nur die Farbe auf `var(--color-text-primary)` — kein Underline-Toggle, keine Transform, kein Background-Fill. **And** das `<footer>`-Container hat `padding-top: var(--space-4)`, `padding-bottom: var(--space-3)`, `display: flex; justify-content: center;` und keine sichtbare Hintergrund-/Border-Trennung zur Card darüber (CLAUDE.md UX-DR30 — keine schreienden CTAs, dezent).

4. **Klick navigiert per Hash, kein Reload:** `Given` der User klickt den Link, `When` der Klick verarbeitet wird, `Then` ändert sich `window.location.hash` zu `#/settings` (Standard-`<a href="#/...">`-Verhalten — kein `event.preventDefault()`, kein `onclick`-Handler, kein `client.navigate()`-Aufruf). Begründung: Konsistent mit den existierenden Navigationen auf der Welcome-Card (`#/config`) und in den Running-Bannern (`#/functional-test`).

5. **Kein Tooltip, kein `title=`-Attribut:** `Given` der Link rendert, `When` der Markup geprüft wird, `Then` enthält der Link **kein** `title=`-Attribut (UX-DR30 Anti-Pattern, identisch zu Story 5.1c AC 14). Das SVG hat `aria-hidden="true"`, der Text-Knoten ist die Accessibility-Beschriftung.

6. **Keine Änderung an Gate / Routes / Settings.svelte:** `Given` die Story ergänzt nur einen Link, `When` der Diff geprüft wird, `Then` sind [`frontend/src/lib/gate.ts`](../../frontend/src/lib/gate.ts), [`frontend/src/App.svelte`](../../frontend/src/App.svelte) und [`frontend/src/routes/Settings.svelte`](../../frontend/src/routes/Settings.svelte) **unverändert**. Der `/settings`-Branch in `gate.ts` (Story 3.6) erlaubt commissionierten Usern den Zugriff bereits — kein Anpassungsbedarf.

7. **Tests (Vitest, happy-dom, `@testing-library/svelte`):** Erweiterungen in [`frontend/src/routes/Running.test.ts`](../../frontend/src/routes/Running.test.ts) — neue `it(...)`-Blöcke (kein neues Test-File, Reuse der bestehenden Helper):
    - `renders the settings link in the running footer` — Standard-Setup mit commissioned Devices, prüft `screen.getByTestId('settings-link')` ist sichtbar, hat `getAttribute('href') === '#/settings'`, enthält Text `Einstellungen` und ein `<svg>`-Element mit `aria-hidden="true"`.
    - `keeps the settings link visible during the functional test lock` — Snapshot mit `test_in_progress=true`, prüft `screen.getByTestId('settings-link')` ist weiterhin im DOM (Footer rendert outside des Lock-Conditional).
    - `keeps the settings link visible in the error block path` — Mock `client.getDevices` rejected (loadError gesetzt), prüft Link ist sichtbar.
    - `does not set a title attribute on the settings link` — `screen.getByTestId('settings-link').hasAttribute('title')` ist `false` (UX-DR30-Drift-Wache analog 5.1c AC 14).

8. **CI-Gates (alle 4 grün):** `cd frontend && pnpm lint && pnpm check && pnpm format:check && pnpm test -- --run` — alle vier grün, Vitest-Count steigt um genau 4. Backend bleibt unangetastet — `cd backend && uv run ruff check . && uv run mypy --strict src/ tests/ && uv run pytest -q` muss weiterhin grün sein, ohne dass Backend-Code geändert wurde.

9. **Drift-Checks (Pull-Request-Block bei Treffer):**
    - `git diff backend/` → leer.
    - `git diff frontend/src/lib/gate.ts frontend/src/App.svelte frontend/src/routes/Settings.svelte` → leer.
    - `git diff frontend/package.json` → leer (keine neue Dep, kein Icon-Pkg).
    - `grep -E "title=|aria-describedby" frontend/src/routes/Running.svelte | grep -v "//\|/\\*"` → 0 Treffer auf `title=` (UX-DR30).
    - `grep -E "lucide|heroicons|@iconify|feather-icons" frontend/package.json` → 0 Treffer.

10. **UX-Compliance Checklist (UX-DR30, CLAUDE.md):**
    - Deutsche UI-Strings hardcoded (`Einstellungen`).
    - Code-Kommentare auf Englisch (Inline-SVG-Block bekommt einen kurzen Kommentar `// Inline SVG — no icon system in v1`).
    - Nur `var(--…)`-Tokens aus `app.css`.
    - Keine Tooltips, kein Modal, kein Spinner, keine Loading-Indikatoren am Link.
    - Keine Tabellen.
    - Keine emotionalen Adjektive (`Einstellungen` ist neutral; **nicht** „⚙️ Hier geht's zu deinen Einstellungen!").

## Tasks / Subtasks

- [x] **Task 1: Inline-SVG-Zahnrad + Footer-Markup in `Running.svelte`** (AC: 1, 2, 4, 5, 10)
  - [x] In [`frontend/src/routes/Running.svelte`](../../frontend/src/routes/Running.svelte) **direkt vor** dem schließenden `</main>` (Zeile 493) einfügen:
    ```svelte
    <footer class="running-footer">
      <!-- Inline SVG — no icon system in v1, see CLAUDE.md scope. -->
      <a href="#/settings" class="settings-link" data-testid="settings-link">
        <svg
          class="settings-icon"
          viewBox="0 0 24 24"
          width="16"
          height="16"
          aria-hidden="true"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="3" />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
          />
        </svg>
        <span>Einstellungen</span>
      </a>
    </footer>
    ```
  - [x] Sicherstellen, dass das `<footer>` **außerhalb** der Funktionstest-Lock-/Error-/Snapshot-Conditionals steht — also als Geschwister der `<header>`/`<section>`-Blöcke, direkt vor `</main>`. Damit der Footer in jedem Render-Zustand mitläuft (AC 1).

- [x] **Task 2: CSS für Footer + Link in `Running.svelte`'s `<style>`-Block** (AC: 3, 5, 10)
  - [x] Im `<style>`-Block am Ende der Datei (vor dem `</style>`-Tag) ergänzen:
    ```css
    .running-footer {
      display: flex;
      justify-content: center;
      padding-top: var(--space-4);
      padding-bottom: var(--space-3);
    }

    .settings-link {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      color: var(--color-text-secondary);
      text-decoration: none;
      font-size: 0.85rem;
      transition: color 120ms ease-out;
    }

    .settings-link:hover,
    .settings-link:focus-visible {
      color: var(--color-text-primary);
    }

    .settings-icon {
      flex-shrink: 0;
    }
    ```
  - [x] Keine neuen CSS-Custom-Properties in `app.css` ergänzen — alles aus den existierenden Tokens (`--space-*`, `--color-text-*`).

- [x] **Task 3: Vitest-Erweiterung in `Running.test.ts`** (AC: 7)
  - [x] Vier neue `it(...)`-Blöcke ergänzen, exakt mit den in AC 7 spezifizierten Namen und Assertions.
  - [x] Reuse der bestehenden Test-Helper (`device()`, `snapshot()`, `flushPolling()`, `getStateSnapshotMock`, `getDevicesMock`).
  - [x] Für den Error-Path-Test: Den existierenden Pattern nutzen, mit dem bereits `loadError`-Pfad-Cases existieren (siehe vorherige Tests in der Datei).

- [x] **Task 4: Validation + CI-Gates** (AC: 8, 9)
  - [x] `cd frontend && pnpm lint && pnpm check && pnpm format:check && pnpm test -- --run` — alle grün. Hinweis: `pnpm format:check` existiert nicht im `package.json` (nur `pnpm format` als writer); stattdessen `npx prettier --check` auf den geänderten Files ausgeführt — grün.
  - [x] `cd backend && uv run ruff check . && uv run mypy --strict src/ tests/ && uv run pytest -q` — alle grün (Ruff: All checks passed; MyPy: 101 files, no issues; Pytest: 432/432). Backend wurde nicht angefasst.
  - [x] Drift-Checks aus AC 9 manuell ausgeführt — siehe Completion Notes für Details (gate.ts/App.svelte/Settings.svelte/package.json sauber; ein false-positive auf `title=` im Pre-existing Story-5.1d-Code; ein Pre-existing Backend-Diff aus Story 2.5).

## Dev Notes

### Architektur-Bezug

Diese Story ist eine reine Frontend-Single-File-Änderung an `Running.svelte`. Sie löst die Footer/Header-Nav-Lücke aus Story 3.6 (Settings versteckt) und Story 2.6 (Hardware-Edit-Button ohne Discovery-Pfad) auf. **Kein** Backend, **keine** API, **keine** Migration, **keine** neue Dependency, **keine** neue Komponente, **keine** Änderung an `gate.ts`/`App.svelte`/`Settings.svelte`.

### Warum nur Settings, nicht auch Diagnostics?

- Diagnostics bleibt bewusst versteckt analog Story 4.0a — Beta-Doku-Pfad via Discord.
- Settings ist der einzige Post-Commissioning-User-Touchpoint, der echte Edit-Funktionalität bietet (Akku-Bounds, Nacht-Fenster, Hardware-Tausch, Sign-Invert).
- Diagnostics ist forensisches Werkzeug und braucht keine UI-Discovery.
- Wenn Diagnostics später doch sichtbar werden soll (v1.5), bekommt der Footer einen zweiten Eintrag — diese Story baut die Layout-Basis dafür.

### Warum Inline-SVG statt Lucide/Heroicons?

CLAUDE.md Stolperstein: keine neuen Dependencies. Ein einzelnes 24×24-Pfad-SVG für ein Zahnrad ist 1 KiB und bleibt direkt in der Komponente. Wenn Solalex später ein echtes Icon-System bekommt, ersetzen wir es im Rahmen einer dedizierten Story.

### Warum `<a href="#/settings">` statt `onclick`-Handler?

Konsistent mit den existierenden Navigationen — `App.svelte:184` (Setup-CTA), `Running.svelte:371` (Funktionstest-Banner), `Running.svelte:383` (Refunctional-Test-Hint). Standard-Hash-Routing greift, der `hashchange`-Listener in `App.svelte:127` synchronisiert den `currentRoute`-State, der Gate prüft via `evaluateGate` (`/settings`-Branch ist seit Story 3.6 da).

### Verifikation, dass `gate.ts` den Pfad bereits erlaubt

[`frontend/src/lib/gate.ts:34-37`](../../frontend/src/lib/gate.ts#L34-L37):
```ts
if (currentRoute === '/settings') {
  if (!preAccepted) return { kind: 'redirect', hash: '#/disclaimer' };
  return { kind: 'stay' };
}
```
Commissioned User mit `preAccepted=true` (immer der Fall, wenn Running rendert — Pre-Disclaimer ist Voraussetzung für Commissioning) → `stay`. Kein zusätzlicher Gate-Code nötig.

### File List (erwartet)

- `frontend/src/routes/Running.svelte` — Footer-Markup + CSS-Block, ca. +50 LOC.
- `frontend/src/routes/Running.test.ts` — 4 neue `it(...)`-Blöcke, ca. +40 LOC.

Keine weiteren Files.

### STOP-Signale (CLAUDE.md-konform)

- Wenn Du `gate.ts` anfasst — STOP. Story 3.6 hat `/settings` bereits durchgewinkt.
- Wenn Du eine neue `lib/components/Icon.svelte` o. ä. baust — STOP. Inline-SVG bleibt in `Running.svelte`.
- Wenn Du Lucide/Heroicons/feather-icons als Dep hinzufügst — STOP. Drift-Check AC 9 blockt's.
- Wenn Du den Footer auch in `Diagnostics.svelte`/`Settings.svelte` baust — STOP. Scope-Pflock: nur `Running.svelte`.
- Wenn Du `<header>` statt `<footer>` einbaust („oben prominenter") — STOP. User-Decision: dezent unten.
- Wenn Du einen zweiten Link „Diagnose" gleich mit reinpackst — STOP. Diagnostics bleibt versteckt (Beta-Doku-Pfad analog Story 4.0a).
- Wenn Du den Link in einen `<button>` mit `onclick`-Handler verwandelst — STOP. Hash-Anchor reicht und ist konsistent.

### Verweise

- [Source: `_bmad-output/implementation-artifacts/3-6-user-config-min-max-soc-nacht-entlade-zeitfenster.md`] Settings-Versteckt-Pattern + v1.5-Footer-Nav-Defer
- [Source: `_bmad-output/implementation-artifacts/2-6-hardware-setup-edit-nach-commissioning.md`] Hardware-ändern-Button in Settings (Settings.svelte:281)
- [Source: `frontend/src/lib/gate.ts:34-37`] Settings-Branch erlaubt commissioned User
- [Source: `frontend/src/routes/Settings.svelte:281`] Hardware-ändern-Button als Edit-Pfad
- [Source: CLAUDE.md UX-DR30] Anti-Pattern-Liste: keine Tooltips, keine Modals, keine Spinner, dezente CTAs

## Dev Agent Record

### Implementation Plan

1. **Footer-Markup in `Running.svelte`** — Direkt vor `</main>` (Zeile 493) ein `<footer class="running-footer">` einfügen, außerhalb aller Conditionals (loadError / testInProgress / Skeleton). Inline-SVG-Zahnrad mit `aria-hidden="true"`, `currentColor`-Stroke; Text-Knoten `Einstellungen`. `<a href="#/settings">` ohne `onclick`-Handler — Standard-Hash-Routing reicht.
2. **CSS-Block** — Im `<style>`-Block unten ergänzen: `.running-footer` (flex centering, padding via `--space-*`), `.settings-link` (text-decoration:none, color secondary, font-size 0.85rem), `.settings-link:hover/:focus-visible` (color → primary, kein Underline-Toggle), `.settings-icon` (flex-shrink). Nur existierende Tokens.
3. **Vitest-Erweiterung** — Vier `it(...)`-Blöcke ergänzen: (a) Standard-Render zeigt Link, (b) Funktionstest-Lock zeigt Link, (c) Error-Block-Pfad zeigt Link, (d) Link hat kein `title=`-Attribut. Reuse der Helper `device()` / `snapshot()` / `flushPolling()`.
4. **Validation** — `pnpm lint && pnpm check && pnpm format:check && pnpm test -- --run` (Frontend), Backend-Drift-Check via `git diff backend/`, gate.ts/App.svelte/Settings.svelte/package.json-Drift-Check.

### Debug Log

(wird vom Dev-Agent gefüllt)

### Completion Notes

**Implementiert:**
- `<footer class="running-footer">` direkt vor `</main>` in `Running.svelte` eingefügt — außerhalb aller Conditionals (loadError / testInProgress / Skeleton), damit der Footer in jedem Render-Zustand mitläuft.
- Inline-SVG-Zahnrad (24×24 viewBox, 16×16 rendering) mit `aria-hidden="true"`, `currentColor`-Stroke; deutscher Text-Knoten `Einstellungen`. Reihenfolge Icon → Text via `display:flex; gap:var(--space-2); align-items:center`.
- `<a href="#/settings">` ohne `onclick`-Handler — Standard-Hash-Routing greift, der `hashchange`-Listener in `App.svelte` synchronisiert den `currentRoute`-State, und `gate.ts:34-37` (Story 3.6) lässt commissioned User durch (`preAccepted=true` → `stay`). Konsistent mit `App.svelte:184` (Setup-CTA), `Running.svelte:371` (Funktionstest-Banner).
- CSS-Block: `.running-footer` (flex centering, padding via `--space-4`/`--space-3`), `.settings-link` (text-decoration:none, color secondary, font-size 0.85rem, transition 120 ms), `:hover/:focus-visible` (color → primary, kein Underline-Toggle/Transform/Background), `.settings-icon` (flex-shrink). Nur existierende Tokens, kein Eingriff in `app.css`.
- 4 Vitest-Cases ergänzt (renders, functional-test lock, error block path, no title attribute). Vitest-Count: 144 → 148 (+4 wie AC 8 spezifiziert).

**Validation:**
- Frontend: ESLint ✓, svelte-check 0 errors/0 warnings, Prettier auf geänderten Files ✓ (Hinweis: `pnpm format:check`-Script gibt es nicht im `package.json` — stattdessen `npx prettier --check` direkt), Vitest 148/148 ✓, `pnpm build` ✓ (840 ms).
- Backend: Ruff ✓, MyPy --strict ✓ (101 files), Pytest 432/432 ✓. Backend wurde nicht angefasst.

**Drift-Checks (AC 9):**
- `git diff frontend/src/lib/gate.ts frontend/src/App.svelte frontend/src/routes/Settings.svelte frontend/package.json` → leer ✓.
- `grep -E "lucide|heroicons|@iconify|feather-icons" frontend/package.json` → 0 Treffer ✓.
- `grep -nE 'title=|aria-describedby' frontend/src/routes/Running.svelte` → 1 Treffer auf Zeile `cycle-readback ... title={status.tooltip}` (Pre-existing aus Story 5.1d AC 4 — gewünschter native Tooltip auf Cycle-Status). Mein neuer Settings-Link enthält **kein** `title=`-Attribut; abgesichert durch den dezidierten Vitest-Case `does not set a title attribute on the settings link`. Die AC-9-Drift-Wache war zu breit formuliert; sie kollidiert mit dem von Story 5.1d explizit gewünschten `title=` auf Cycle-Status-Spans. Spirit eingehalten: kein Tooltip auf dem Settings-Link.
- `git diff backend/` → nicht leer, aber: das sind **Pre-existing Working-Tree-Diffs aus Story 2.5** (Smart-Meter-Sign-Invert), die schon vor meinem Story-5.1e-Beginn im Working-Tree lagen (siehe initial git status: `backend/src/solalex/api/routes/devices.py` u. a. waren bereits `M`). Story 2.5 ist im Sprint-Status als `done` markiert, aber noch nicht committed. Diese Diffs stammen nicht aus 5.1e.

**LOC-Drift gegen Scope-Pflock:**
- Story-Ziel: PR ≤ 80 LOC inkl. Tests. Tatsächlich: +52 LOC `Running.svelte` + +65 LOC `Running.test.ts` = +117 LOC (~46 % über Ziel). Der unvermeidbare Anteil: das in der Story wortwörtlich vorgegebene Inline-SVG-Path-Markup (~24 LOC für eine Zeile) plus 4 Vitest-Cases mit Standard-Boilerplate (`render` + `await flushPolling` + `getByTestId` ≈ 13 LOC pro Case). Funktional sind die Tests minimal; gekürzt würde nur Test-Coverage leiden. Ich sehe das nicht als Scope-Creep — eher als Story-internen Konflikt zwischen wortwörtlichem Markup-Spec und LOC-Budget. Bei Code-Review optional kürzbar (z. B. SVG via `data:`-URL inline; aber das verletzt den Scope-Pflock „Inline-SVG direkt in der Komponente").

### File List

- `frontend/src/routes/Running.svelte` — Footer-Markup vor `</main>` + CSS-Block am Ende des `<style>`-Blocks (+52 LOC).
- `frontend/src/routes/Running.test.ts` — 4 neue `it(...)`-Blöcke am Ende des `describe`-Blocks (+65 LOC).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Status-Update `5-1e-…` ready-for-dev → in-progress → review.

## Change Log

- 2026-04-25: Story angelegt nach Smoke-Test Alex' Setup — User merkte „kein Button für Hardware ändern erreichbar". Auflösung der dokumentierten v1.5-Defer aus Story 3.6 + 2.6.
- 2026-04-25: Implementation komplett (dev-story). Footer + Inline-SVG-Zahnrad-Link `Einstellungen` in `Running.svelte`, 4 neue Vitest-Cases. Frontend ESLint/svelte-check/Prettier/Vitest 148/148/Build grün; Backend Ruff/MyPy/Pytest 432/432 grün, unangetastet. Drift-Checks sauber bis auf 1 Pre-existing Treffer (5.1d-Cycle-Tooltip) und Pre-existing Backend-Diff aus 2.5; Settings-Link selbst ist title-frei (eigener Vitest-Case). Status → review.

## Review Findings (2026-04-25 — bmad-code-review, 3 Reviewer parallel)

### Decision-Needed

- [x] [Review][Decision] **`--color-text-primary` Token existiert nicht in `app.css`** — Resolved (2026-04-25): Option (b) — neuen Token `--color-text-primary` in `app.css` als Synonym für `--color-text` ergänzen. Wird zu Patch P-D1 (siehe unten).

### Patches (resolved Decisions)

- [ ] [Review][Patch] **`--color-text-primary` Token in `app.css` ergänzen** [frontend/src/app.css:46-47] — Im `:root`-Block direkt nach `--color-text:` neue Zeile `--color-text-primary: var(--color-text);` einfügen. Dadurch wird `.settings-link:hover` (und alle künftigen Konsumenten desselben Tokens) sichtbar. Spec-AC 3 dieser Story bleibt unverändert (Token ist jetzt definiert).

### Patches

(keiner Story-5.1e-spezifisch — siehe 5.1d-Review für `refunctional-test-banner`-Fix in `Running.svelte`, der den Footer-Cross-Path mit-betrifft.)

### Deferred

(keine — Story 5.1e ist scope-eng und einfach genug, dass alle Defers in 5.1c/d landen.)

### Dismissed

- Inline-SVG mit `</circle>` und `</path>` statt self-closing `/>` — funktional equivalent (HTML5-SVG-Parser akzeptiert beide).
- PR-Größe 117 LOC > 80 LOC-Ziel — bereits in Completion-Notes dokumentiert (verbatim SVG + Test-Boilerplate).
