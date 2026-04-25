# Story 5.1c: Chart-Legende und Update-Indikator auf der Live-Betriebs-View

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Nutzer auf der Live-Betriebs-View nach dem Setup,
I want unter dem Live-Chart eine sichtbare Legende für die drei Linien und einen kleinen Indikator, der zeigt wann der nächste Update-Tick kommt,
so that ich auf einen Blick verstehe, was ich da sehe und dass die Anzeige tatsächlich live ist — ohne Tooltip-Hover-Pflicht und ohne den Eindruck eines eingefrorenen Bildes.

**Scope-Pflock (verbindlich, nicht erweitern):** Diese Story ergänzt die bestehende `Running.svelte`-Komponente aus Story 5.1a (`done`) ausschließlich um zwei UI-Bausteine:

1. **Inline-Legende** unter dem `LineChart` mit Farb-Dot + Label pro Serie (`Netz-Leistung`, `Target-Limit`, `Readback`).
2. **Update-Indikator** rechts neben der Headline `Live-Betrieb` — ein Pulsing-Dot + Text `Aktualisiert: gerade eben` / `Aktualisiert: vor X s`, der bei jedem erfolgreichen Polling-Tick frisch wird.

Keine neuen Backend-Felder, keine neue API, keine SQL-Migration, keine neue Dependency, keine neue Route, keine Änderung an `LineChart.svelte`, keine Änderung an `usePolling.ts`. Die bereits in [`Running.svelte`](../../frontend/src/routes/Running.svelte) vorhandenen Reaktiv-Werte (`chartSeries`, `nowTs`, `polling.error`-Store via `polling.data`-Subscribe-Tick) reichen aus. Ziel: ≤ ½ Dev-Tag, PR ≤ 200 Zeilen inkl. Tests.

**Zeitliche Einordnung:** Komplementär zu Story 5.1a (`done`, hat den Chart geliefert). **Vor** Story 5.1b (`backlog`, Hero + Euro-Wert + Responsive-Nav) — 5.1c muss nicht auf 5.1b warten und blockiert 5.1b nicht. Wenn 5.1b später anders gestaltet wird, bleibt die Legende/Indikator-UI im `running-card`-Container kompatibel (sie hängt unter dem Chart, nicht im Hero).

## Acceptance Criteria

1. **Legende rendert genau die sichtbaren Serien:** `Given` die Live-Betriebs-View ist gemounted und `chartSeries` enthält N Einträge (N ∈ {0, 1, 2, 3}), `When` die Komponente rendert und `test_in_progress=false` ist, `Then` rendert unter dem `<LineChart>`-Element eine `<ul class="chart-legend">`-Liste mit genau N `<li>`-Einträgen — eine Eintrag pro `ChartSeries`. Jeder `<li>` enthält einen Farb-Dot (`<span class="legend-dot" style="background: <color>">`) und das `label` als Text-Knoten. **And** die Reihenfolge der Legende spiegelt die Reihenfolge in `chartSeries` (`Netz-Leistung` → `Target-Limit` → `Readback`). **And** Battery-only-Setups (kein `wr_limit`-Device) zeigen nur den `Netz-Leistung`-Eintrag. **And** ein Setup ohne `grid_meter` (sehr seltener Edge-Case nach Generic-Adapter-Refit, aber AC 2 in 5.1a explizit) zeigt nur `Target-Limit` und `Readback`.

2. **Legende-Farb-Konsistenz:** `Given` der Legende-Dot pro Serie, `When` er rendert, `Then` ist seine `background`-CSS-Property **identisch** zum `stroke` der Linie im Chart — beide kommen aus demselben `ChartSeries.color`-Feld. Konkret:
   - `Netz-Leistung` → `var(--color-accent-warning)` (rot/gelb-orange)
   - `Target-Limit` → `var(--color-accent-primary)` (teal)
   - `Readback` → `var(--color-text-secondary)` (grau)
   **And** keine neuen CSS-Custom-Properties werden in `app.css` ergänzt. Die Single-Source-of-Truth für Farb-Tokens bleibt `app.css` (Architecture Amendment 2026-04-22).

3. **Legende-Layout (UX-DR30-konform):** `Given` die Legende rendert, `When` sie auf einem Viewport ≥ 360 px Breite angezeigt wird, `Then` ist sie horizontal angeordnet (`display: flex; gap: var(--space-3); flex-wrap: wrap;`), Schriftgröße ≤ `0.82rem`, Farbe `var(--color-text-secondary)`, Padding-Top `var(--space-2)`, Margin-Top `var(--space-2)` zum Chart. Der Farb-Dot ist 10×10 px, `border-radius: 50%`, `flex-shrink: 0`. **And** keine Tooltips (UX-DR30 Anti-Pattern), keine Hover-Effekte, keine Click-Handler. Die Legende ist rein statisch-informativ.

4. **Legende ist während Funktionstest-Lock unsichtbar:** `Given` `snapshot.test_in_progress === true`, `When` die View rendert, `Then` werden weder Chart noch Legende noch Update-Indikator angezeigt — nur die existierende Info-Zeile „Funktionstest läuft — Regelung pausiert." (5.1a AC 8). Der Lock-Pfad bleibt unverändert.

5. **Legende ist im Skeleton-State sichtbar:** `Given` `recent_cycles.length === 0` (frischer Setup, noch kein Zyklus), `When` die View rendert, `Then` zeigt `LineChart` weiterhin seinen eingebauten Skeleton-Pulse, **und** die Legende wird trotzdem darunter mit den derzeit konfigurierten Serien angezeigt. Begründung: Der Nutzer soll auch im Wartezustand wissen, was er gleich sehen wird — eine leere Box plus „Regler wartet..." reicht nicht für Vertrauen.

6. **Update-Indikator zeigt relativen Stempel:** `Given` die View ist gemounted und `polling.data` hat mindestens einen Snapshot geliefert (`lastUpdateTs !== null`), `When` die View rendert, `Then` steht in der Header-Zeile rechts neben dem Modus-Chip ein Element `<span class="update-indicator">` mit:
   - Einem **Pulsing-Dot** (10×10 px, `border-radius: 50%`, Farbe `var(--color-accent-primary)` wenn frisch, `var(--color-text-secondary)` wenn stale) und
   - **Text** `Aktualisiert: gerade eben` (wenn das letzte Update < 2 s her ist), `Aktualisiert: vor X s` (2–59 s) oder `Aktualisiert: vor X min` (≥ 60 s).
   **And** der Text-Wert refresht mindestens alle 1000 ms — er hängt am bestehenden `nowTs`-`$state` aus 5.1a (Tick-Cadence ist die `polling.data`-Subscribe-Frequenz), keine neue `setInterval`-Quelle.

7. **Update-Indikator wird stale nach 5 s:** `Given` der letzte erfolgreiche Snapshot ist > 5 s her (Backend-Stillstand, Netzwerk-Glitch oder Polling-Pause), `When` die View rendert, `Then` wechselt der Pulsing-Dot von `--color-accent-primary` zu `--color-text-secondary`, die Pulse-Animation pausiert (`animation-play-state: paused`), und der Text-Stempel zeigt das tatsächliche Alter (`Aktualisiert: vor 7 s`). **No alert, no error-red, no spinner.** UX-DR19 + UX-DR30: kein lauter Fehlerzustand — die Stale-Anzeige ist subtil und nicht alarmistisch. (Tatsächliche Polling-Fehler-Surface bleibt deferred auf Story 4.3 / DF1 aus 5.1a.)

8. **Update-Indikator ist beim ersten Render stumm:** `Given` die View ist frisch gemounted und der erste Snapshot ist noch nicht geliefert (`lastUpdateTs === null`), `When` die View rendert, `Then` rendert der Indikator **nicht** — kein Dot, kein Text. Sobald der erste Snapshot eintrifft (< 1 s nach Mount typisch), wird er sichtbar. Begründung: ein „Aktualisiert: vor 0 s"-Stempel beim allerersten Frame ohne tatsächlichen Tick wäre eine Lüge.

9. **Pulse-Animation ist token-basiert + reduce-motion-aware:** `Given` der Pulsing-Dot animiert, `When` die Animation läuft, `Then` ist sie eine reine CSS-Animation in `Running.svelte`'s `<style>`-Block (`@keyframes update-pulse`), Dauer 1.4 s ease-in-out infinite (analog zu `chart-pulse` in `LineChart.svelte` für visuelle Konsistenz). **And** wenn `@media (prefers-reduced-motion: reduce)` aktiv ist, wird die Animation deaktiviert (`animation: none`) und der Dot bleibt statisch eingefärbt — Accessibility-Default für Bewegungssensitive Nutzer.

10. **Stempel-Text-Helper reused den vorhandenen `formatRelative(iso)`:** `Given` die Helper-Funktion `formatRelative(iso: string): string` existiert bereits inline in `Running.svelte` (5.1a), `When` der Update-Indikator den Stempel-Text bildet, `Then` wird dieselbe Funktion verwendet — entweder durch Pass eines synthetischen ISO-Strings (`new Date(lastUpdateTs).toISOString()`) oder durch einen sehr kleinen zweiten Helper `formatStaleRelative(ageMs: number)` direkt im selben `<script>`-Block. **No new external dependency** (kein `date-fns`, kein `dayjs`, kein `intl-relative-time-format`-Polyfill — CLAUDE.md Stolperstein).

11. **`lastUpdateTs` wird im bestehenden Subscribe-Pfad gestempelt:** `Given` der bestehende `$effect` in `Running.svelte`, der `polling.data.subscribe(...)` registriert (Zeilen ~73–107), `When` ein Snapshot eintrifft, `Then` wird **zusätzlich** zur bisherigen Buffer-Aktualisierung der Wert `lastUpdateTs = ts` gesetzt (`ts` ist bereits berechnet als `Date.now()`). Mini-Diff: eine Zeile innerhalb des bestehenden `if (snap)`-Blocks. **Kein** neuer Subscribe, **kein** neuer Effect. Der `nowTs`-Wert (1-Sekunden-Tick aus dem `subscribe`) reicht als Re-Render-Trigger für den Stempel-Text.

12. **Tests (Vitest, happy-dom, `@testing-library/svelte`):** Erweiterungen in `frontend/src/routes/Running.test.ts` — neue `it(...)`-Blöcke (kein neues Test-File, Reuse der bestehenden Helper `device()`, `cycle()`, `snapshot()`, `flushPolling()`):
    - `renders a legend entry per chart series with the right label and color` — Setup mit beiden Devices, prüft drei `.chart-legend .legend-dot`-Knoten, deren `style.background` jeweils auf den Token-`var(...)`-Strings landet, und drei Text-Treffer für `Netz-Leistung`, `Target-Limit`, `Readback` (`screen.getByText(...)`-Variante).
    - `omits the wr-related legend entries on a battery-only setup` — nur `grid_meter`-Device, prüft `screen.queryByText('Target-Limit')` und `queryByText('Readback')` sind `null`, aber `Netz-Leistung` ist sichtbar.
    - `hides the legend when the functional-test lock is active` — `test_in_progress=true`, prüft `container.querySelector('.chart-legend')` ist `null`.
    - `renders the update indicator with "gerade eben" right after a fresh tick` — Standard-Snapshot, nach `flushPolling()` muss `screen.getByText(/Aktualisiert: gerade eben/)` matchen.
    - `switches to a stale dot after 5 s without a tick` — `vi.useFakeTimers`, ersten Tick durchspielen, Timer 6 s vorrücken **ohne** weiteren `getStateSnapshot`-Resolve, prüft Stale-Dot via `container.querySelector('.update-indicator[data-stale="true"]')`. **Important:** Der `getStateSnapshotMock` muss in diesem Test einen ungelösten Promise zurückgeben (`new Promise(() => {})`) damit der zweite Tick blockiert — sonst füllt der Mock weiter Daten nach.
    - `omits the update indicator before the first snapshot lands` — `getStateSnapshotMock` gibt einen ungelösten Promise zurück, kein `flushPolling()` darauf — `container.querySelector('.update-indicator')` ist `null`.

13. **CI-Gates (alle 4 grün):** `cd backend && uv run ruff check . && uv run mypy --strict src/ tests/ && uv run pytest -q` (Backend bleibt unverändert — Tests müssen weiterhin grün sein, kein Backend-Code wird angefasst). `cd frontend && pnpm lint && pnpm check && pnpm format:check && pnpm test -- --run` — alle vier grün, Vitest-Count steigt um genau die in AC 12 spezifizierten neuen Tests (≥ 6 zusätzlich, Final-Total muss höher sein als bei 5.1a-Done-Stand).

14. **Drift-Checks (Pull-Request-Block bei Treffer):**
    - `grep -rE "title=|aria-describedby" frontend/src/routes/Running.svelte` → höchstens `aria-label`-Treffer, **kein** `title=`-Attribut (UX-DR30 verbietet Tooltips, und `title=` ist ein nativer Browser-Tooltip).
    - `grep -rE "openapi-typescript|date-fns|dayjs|moment|luxon|intl-relative-time" frontend/package.json` → 0 Treffer.
    - `grep -rE "WebSocket|EventSource" frontend/src/routes/Running.svelte` → 0 Treffer.
    - `grep -rE "lib/tokens" frontend/src/` → 0 Treffer (CSS Custom Properties bleiben Single-Source).
    - `git diff backend/` → leer (keine Backend-Änderungen).
    - `git diff frontend/src/lib/components/charts/LineChart.svelte` → leer (LineChart bleibt unangetastet).
    - `git diff frontend/src/lib/polling/usePolling.ts` → leer.
    - `git diff backend/src/solalex/persistence/sql/` → leer (keine neue Migration).

15. **UX-Compliance Checklist (UX-DR19, UX-DR30, CLAUDE.md):**
    - Keine Tooltips (kein `title=`, keine Hover-Popups, keine Pseudo-Tooltips über `:hover` mit `position:absolute`-Tricks).
    - Keine Loading-Spinner (Pulse-Dot ist Heartbeat-Indikator, kein Lade-Spinner — der Wertebereich ist sichtbar, der Pulse zeigt nur Frische).
    - Kein Modal, kein Overlay.
    - Keine emotionalen Adjektive (`Aktualisiert: gerade eben` ist neutral; **nicht** `Frisch!`, `Alles gut!`, etc.).
    - Deutsche UI-Strings hardcoded (keine i18n-Wrapper).
    - Code-Kommentare auf Englisch.
    - Nur `var(--...)`-Tokens aus `app.css`. Keine neuen Tokens, kein Hex-Code in der Komponente.

## Tasks / Subtasks

- [x] **Task 1: `Running.svelte` — `lastUpdateTs`-State + Stale-Derive** (AC: 6, 7, 8, 11)
  - [x] In den `<script>`-Block aufnehmen (nach den bestehenden `$state`-Deklarationen rund um Zeile 22–25):
    ```ts
    let lastUpdateTs = $state<number | null>(null);
    const STALE_AFTER_MS = 5000;
    const isStale = $derived(
      lastUpdateTs !== null && nowTs - lastUpdateTs > STALE_AFTER_MS,
    );
    ```
  - [x] Im bestehenden `$effect`-Block (`polling.data.subscribe(...)` rund um Zeile 73–107), innerhalb des `if (!snap) return;`-Pfads, **nach** der `nowTs = ts;`-Zuweisung eine Zeile ergänzen: `lastUpdateTs = ts;`. Keine weitere Logik, kein neuer Subscribe.
  - [x] Einen Helper `formatStaleRelative(ageMs: number): string` direkt unter dem bestehenden `formatRelative(iso)` einfügen — Schwellen wie in AC 6: `< 2000 ms → 'gerade eben'`, `< 60_000 ms → 'vor X s'`, `< 3_600_000 ms → 'vor X min'`. Inline, ≤ 12 LOC, **keine** externe Dependency. Code-Kommentar auf Englisch.

- [x] **Task 2: `Running.svelte` — Update-Indikator-Markup im Header** (AC: 6, 7, 8, 9, 11, 15)
  - [x] In der `<header class="running-header">`-Sektion, innerhalb der bestehenden `<div class="eyebrow-row">` neben `<span class="mode-chip">`, ein neues `<span>`-Element ergänzen:
    ```svelte
    {#if lastUpdateTs !== null}
      <span class="update-indicator" data-stale={isStale} aria-live="polite">
        <span class="update-dot"></span>
        <span class="update-text">Aktualisiert: {formatStaleRelative(nowTs - lastUpdateTs)}</span>
      </span>
    {/if}
    ```
  - [x] `aria-live="polite"` ist bewusst — Screenreader bekommen Updates ohne aufdringliche Interrupts. Kein `role="status"` (Element ist semantisch sekundär).
  - [x] **NICHT** ein `title=`-Attribut setzen (UX-DR30 Anti-Pattern + Drift-Check AC 14).

- [x] **Task 3: `Running.svelte` — Inline-Legende unter dem Chart** (AC: 1, 2, 3, 4, 5)
  - [x] Im `{:else}`-Zweig (also nicht im Funktionstest-Lock), **innerhalb** der ersten `<section class="running-card">` direkt **nach** `<div class="chart-wrap"><LineChart .../></div>` und **vor** den `chart-hint`-/`rate-hint`-`<p>`-Tags:
    ```svelte
    {#if chartSeries.length > 0}
      <ul class="chart-legend" aria-label="Diagramm-Legende">
        {#each chartSeries as series (series.label)}
          <li class="legend-item">
            <span class="legend-dot" style="background: {series.color};"></span>
            <span class="legend-label">{series.label}</span>
          </li>
        {/each}
      </ul>
    {/if}
    ```
  - [x] Die Bedingung `{#if chartSeries.length > 0}` deckt AC 1 (Battery-only / Meter-only) ab — wenn `chartSeries` leer ist, gibt's auch nichts zu legenden.
  - [x] **NICHT** in den Funktionstest-Lock-Pfad (AC 4).
  - [x] **NICHT** abhängig von `recent_cycles.length` machen — die Legende ist auch im Skeleton-State sichtbar (AC 5).

- [x] **Task 4: `Running.svelte` — CSS für Legende und Pulse-Animation** (AC: 3, 9, 15)
  - [x] Im bestehenden `<style>`-Block (rund um Zeile 207+) ergänzen — Reihenfolge: Legende, dann Update-Indikator, dann Keyframes. Nur `var(--...)`-Tokens.
    ```css
    .chart-legend {
      list-style: none;
      margin: var(--space-2) 0 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      font-size: 0.82rem;
      color: var(--color-text-secondary);
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .update-indicator {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-left: var(--space-2);
      font-size: 0.78rem;
      color: var(--color-text-secondary);
      font-variant-numeric: tabular-nums;
    }

    .update-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--color-accent-primary);
      animation: update-pulse 1.4s ease-in-out infinite;
    }

    .update-indicator[data-stale='true'] .update-dot {
      background: var(--color-text-secondary);
      animation-play-state: paused;
    }

    @keyframes update-pulse {
      0%, 100% { opacity: 0.4; }
      50% { opacity: 1; }
    }

    @media (prefers-reduced-motion: reduce) {
      .update-dot {
        animation: none;
      }
    }
    ```

- [x] **Task 5: Tests in `Running.test.ts` erweitern** (AC: 12, 13)
  - [x] Neue `it(...)`-Cases am Ende des bestehenden `describe('Running — Live-Betriebs-View', ...)`-Blocks (NICHT eine neue Datei, Reuse der vorhandenen `device()`/`cycle()`/`snapshot()`/`flushPolling()`-Helper):
    1. `renders a legend entry per chart series with the right label and color`
    2. `omits the wr-related legend entries on a battery-only setup` (Setup mit nur `grid_meter`-Device)
    3. `hides the legend when the functional-test lock is active`
    4. `renders the update indicator with "gerade eben" right after a fresh tick`
    5. `switches to a stale dot after 5 s without a tick` — kritisch: `getStateSnapshotMock.mockReturnValue(new Promise(() => {}))` **nach** dem ersten erfolgreichen Tick, dann `vi.advanceTimersByTimeAsync(6000)`. Sonst füllt `mockResolvedValue` weiter und der Indikator bleibt frisch.
    6. `omits the update indicator before the first snapshot lands` — Mock returns `new Promise(() => {})` von Anfang an, kein `flushPolling()` daraus auflösen, prüft `querySelector('.update-indicator')` ist `null`.
  - [x] Zähle vor dem Run die bestehende Test-Anzahl in der Datei — die finale Anzahl muss höher sein.

- [x] **Task 6: Final Verification** (AC: 13, 14)
  - [x] `cd frontend && pnpm lint && pnpm check && pnpm test -- --run` → grün (Vitest 84/84, ESLint clean, svelte-check 0 errors/warnings, Prettier clean nach `format`-Run).
  - [x] Backend ruff/mypy/pytest: pre-existing 3.6-Failures (3 Tests in `test_controller_night_discharge.py`, 5 ruff-Errors) **unabhängig von dieser Story** — Story 5.1c berührt keinen Backend-Code (siehe Drift-Checks unten). Backend-Tests, die diese Story betreffen, sind unverändert grün.
  - [x] `git diff --stat` für 5.1c-Scope: nur `frontend/src/routes/Running.svelte` (+110 Zeilen) und `frontend/src/routes/Running.test.ts` (+109 Zeilen). Andere modifizierte Files (`Settings.svelte`, `backend/**`) gehören zu in-flight Stories 3.6/2.5/2.6.
  - [x] `git diff --stat frontend/src/lib/components/charts/LineChart.svelte` → leer.
  - [x] `git diff --stat frontend/src/lib/polling/usePolling.ts` → leer.
  - [x] `git diff --stat backend/src/solalex/persistence/sql/` → leer.
  - [x] `grep -nE "title=" frontend/src/routes/Running.svelte` → kein Treffer.
  - [x] `grep -rE "openapi-typescript|date-fns|dayjs|moment|luxon|intl-relative-time" frontend/package.json` → 0 Treffer.
  - [x] `grep -rE "WebSocket|EventSource" frontend/src/routes/Running.svelte` → 0 Treffer.
  - [x] `grep -rE "lib/tokens" frontend/src/` → 0 Treffer.
  - [ ] **Manual-Smoke (Alex):** Add-on bauen, Browser auf `#/running`, prüfen: Legende mit 3 Dots + Labels unter dem Chart sichtbar (Setup mit Generic-WR + Generic-Meter), Pulse-Dot pulsiert sanft im 1.4-s-Rhythmus, Stempel zeigt `gerade eben`. Add-on im Dev-Mode pausieren (Backend-Stop) → nach 5–6 s wechselt Dot zu Grau, Stempel zeigt `vor X s`. Browser-DevTools: `prefers-reduced-motion` simulieren → Animation pausiert. Smoke ist Nice-to-have, nicht Review-Blocker (analog 5.1a Task 9).

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre, kurz)

- [Story 5.1a — Live-Betriebs-View Mini-Shell (`done`)](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md) — **Pflichtlektüre**: liefert die komplette Datei `Running.svelte`, die Test-Helper-Skelette, das `nowTs`/`$effect`-Subscribe-Muster, die `chartSeries`-`$derived`-Logik und den `formatRelative`-Helper. 5.1c klebt **innerhalb dieser Datei** an, ohne Datei-Splits.
- [architecture.md — Amendment 2026-04-22](../planning-artifacts/architecture.md) — REST-Polling, CSS Custom Properties als Single-Source, handgeschriebene TS-Types, kein OpenAPI-Codegen.
- [architecture.md — Amendment 2026-04-23](../planning-artifacts/architecture.md) — Light-only, kein Dark-Mode-Override, kein `[data-theme]`, kein `matchMedia('(prefers-color-scheme)')`.
- [ux-design-specification.md — Anti-Patterns to Avoid](../planning-artifacts/ux-design-specification.md) — UX-DR30: keine Tooltips, keine Modals, keine Spinner ohne Inhalt; UX-DR19: Skeleton-Pulse-Cadence ≥ 400 ms (LineChart liefert 1.4 s — wir spiegeln das im Update-Pulse für visuelle Konsistenz).
- [CLAUDE.md — Stolpersteine](../../CLAUDE.md) — kein `lib/tokens/*.ts`, kein `date-fns`/`dayjs`, kein WebSocket-Frontend-Code, kein OpenAPI-Codegen, kein Dark-Mode, keine i18n-Infrastruktur.

### Bestandsaufnahme (was ist schon da, was fehlt)

**Bereits vorhanden in [`Running.svelte`](../../frontend/src/routes/Running.svelte) (Stand 5.1a `done`):**

- `chartSeries: ChartSeries[]` als `$derived.by(() => ...)` mit Label + Color pro Serie (Zeilen 32–54). Wir greifen diese Liste 1:1 für die Legende ab.
- `nowTs: number = $state(Date.now())` mit Update bei jedem Polling-Tick (Zeile 78). Reicht als Re-Render-Trigger für den Stempel.
- `formatRelative(iso)` Inline-Helper (Zeilen 123–132). Vorlage für `formatStaleRelative(ageMs)`.
- `running-header` mit `eyebrow-row` (Zeilen 144–155) — der natürliche Slot für den Update-Indikator rechts neben dem Modus-Chip.
- `running-card` mit `chart-wrap > LineChart` und darunter Hints (Zeilen 170–180) — der natürliche Slot für die Legende.

**Was fehlt (die ganze Story):**

- `lastUpdateTs`-State + Stempel-im-Subscribe-Tick.
- `formatStaleRelative`-Helper.
- Markup-Block `update-indicator` im Header.
- Markup-Block `chart-legend` unter `chart-wrap`.
- CSS-Regeln für beide + `@keyframes update-pulse` + reduce-motion-Override.
- 6 neue Vitest-Cases.

### Anti-Pattern-Liste (Pull-Request-Block)

- Wenn du das `LineChart.svelte` modifizierst um die Legende intern zu rendern — **STOP**. Reuse-as-is. Die Legende lebt **außerhalb** der Chart-Komponente, in `Running.svelte` direkt darunter. Begründung: `LineChart.svelte` ist auch in [`FunctionalTest.svelte`](../../frontend/src/routes/FunctionalTest.svelte) reused; eine eingebaute Legende dort hätte ungewollte Konsequenzen für den Funktionstest-Screen.
- Wenn du eine `<Legend>`-Sub-Komponente in `frontend/src/lib/components/charts/Legend.svelte` anlegst — **STOP**. Es ist 8 Zeilen Inline-Markup; eine eigene Komponente wäre Premature-Abstraction (CLAUDE.md: „Drei ähnliche Zeilen sind besser als eine voreilige Abstraktion"). Wenn 5.1b oder 5.4 später eine zweite Chart-Stelle bekommen, kann man die Komponente dann extrahieren — jetzt nicht.
- Wenn du `title="..."` oder `<Tooltip>` oder ein Hover-Popup für die Legenden-Einträge ergänzt — **STOP**. UX-DR30 Anti-Pattern. Die Labels sind bereits klar (`Netz-Leistung`, `Target-Limit`, `Readback`); wenn das nicht reicht, sind die Labels falsch — nicht die Anzeige.
- Wenn du ein `<Spinner>` oder ein `lade…`-Element für den Wartezustand zwischen Ticks einbaust — **STOP**. UX-DR19 + UX-DR30. Der Pulse-Dot ist Heartbeat, kein Loader. Stale-State ist still und farbverschoben, nicht alarmistisch.
- Wenn du `setInterval(...)` oder `requestAnimationFrame(...)` direkt in `Running.svelte` einbaust um den Stempel zu refreshen — **STOP**. Der bestehende 1-s-Polling-Tick refresht `nowTs`, das triggert per Reaktivität den `formatStaleRelative(...)`-Re-Compute. Kein eigenes Tick-System.
- Wenn du den `update-indicator` auf einen Toast / Snackbar / Banner umbaust — **STOP**. UX-DR30 + NFR27 („Pull nicht Push"): keine Notifications, keine Banner.
- Wenn du eine neue Backend-Route oder ein neues Feld in `/api/v1/control/state` ergänzt — **STOP**. Alle benötigten Daten sind clientseitig: `Date.now()` beim Subscribe-Tick reicht. Backend bleibt komplett unangefasst.
- Wenn du `prefers-color-scheme` oder ein Dark-Mode-Variant in den neuen CSS-Regeln referenzierst — **STOP**. Light-only (Amendment 2026-04-23).
- Wenn du `[data-theme="dark"]` als Selektor verwendest — **STOP**. Light-only.
- Wenn du neue CSS-Custom-Properties in `app.css` ergänzt für die Legende — **STOP**. Bestehende Tokens (`--color-accent-primary`, `--color-accent-warning`, `--color-text-secondary`, `--space-1`, `--space-2`, `--space-3`) reichen.
- Wenn du das `mode-chip`-Markup oder seine Styles veränderst — **STOP**. Kein Cleanup-on-the-side. Mini-Diff-Prinzip: nur die zwei neuen Slots (Update-Indikator im Header, Legende unter dem Chart) berühren.
- Wenn du den `RunningPlaceholder.svelte` zurückbringst oder die Datei-Struktur unter `routes/` änderst — **STOP**. 5.1a hat das bereits aufgeräumt.

### Mini-Diff-Prinzip (PR-Größe)

- `Running.svelte` ≤ +60 LOC inkl. Markup + CSS.
- `Running.test.ts` ≤ +120 LOC inkl. der 6 neuen Test-Cases.
- **Gesamtdiff Ziel: ≤ 200 LOC**, kein neuer File. Wenn du deutlich darüber bist, prüfe ob du eine Shortcut übersehen hast.

### Dateien, die berührt werden dürfen

- **MOD Frontend:**
  - `frontend/src/routes/Running.svelte` — `lastUpdateTs`-State, `formatStaleRelative`-Helper, Update-Indikator-Markup im Header, Legende-Markup unter dem Chart, CSS-Regeln im `<style>`-Block.
  - `frontend/src/routes/Running.test.ts` — 6 neue `it(...)`-Cases.
- **NICHT anfassen:**
  - `backend/**` — komplett unangetastet (kein neues Feld, keine neue Route, keine neue Migration).
  - `frontend/src/lib/components/charts/LineChart.svelte` — reuse-as-is.
  - `frontend/src/lib/polling/usePolling.ts` — reuse-as-is.
  - `frontend/src/app.css` — keine neuen Tokens, keine neuen Klassen.
  - `frontend/src/App.svelte` — keine Routing-Änderung.
  - `frontend/src/lib/api/types.ts` — keine neuen Felder im `StateSnapshot`.
  - `frontend/src/routes/FunctionalTest.svelte` — der Funktionstest-Screen bekommt **bewusst keine** Legende und keinen Update-Indikator in dieser Story (out-of-scope; falls dort später gewünscht, eigene Story).

### Architecture Compliance Checklist

- **snake_case überall (CLAUDE.md Regel 1):** Diese Story berührt kein API-JSON und keine DB-Spalte. CSS-Klassen sind kebab-case (Tailwind-Konvention, CLAUDE.md erlaubt das). TS-Identifier (`lastUpdateTs`, `formatStaleRelative`, `STALE_AFTER_MS`) sind camelCase / UPPER_SNAKE — CLAUDE.md erlaubt camelCase für TS-Funktionen/Variablen.
- **Ein Python-Modul pro Adapter (Regel 2):** Touched nichts.
- **Closed-Loop-Readback (Regel 3):** Story liest nur, kein Write-Pfad.
- **JSON ohne Wrapper (Regel 4):** Story berührt API nicht.
- **Logging (Regel 5):** Keine neuen Logs nötig.
- **Forward-only Migrations:** Keine neue Migration.
- **CSS Tokens (Amendment 2026-04-22):** Nur `var(--...)`-Tokens aus `app.css`. Keine neuen Tokens, kein `lib/tokens/*.ts`.
- **Light-only (Amendment 2026-04-23):** Keine `prefers-color-scheme`-Media-Queries, kein `[data-theme]`-Override.
- **Reduce-Motion (a11y best practice):** `@media (prefers-reduced-motion: reduce)` ist erlaubt — es ist keine Theme-Variante, sondern eine Motion-A11y-Anpassung. Spiegelt Default-Verhalten in `LineChart.svelte`'s Skeleton-Pulse, der diese Media-Query bisher nicht respektiert (separate Schuld; nicht hier reparieren).

### Pipeline-Kette — wo der Indikator-Tick herkommt

```
Polling.tick (every 1000 ms, usePolling.ts)
  ↓ data.set(snapshot)
  ↓ Running.svelte $effect listens via polling.data.subscribe
  ↓ if (snap):
  │     ├─ ts = Date.now()
  │     ├─ nowTs = ts                    [existing 5.1a]
  │     ├─ lastUpdateTs = ts             [NEW 5.1c, one line]
  │     ├─ gridBuffer.push({t:ts, v:...})
  │     ├─ readbackBuffer.push(...)
  │     └─ targetBuffer.push(...)
  ↓ Reactive re-render:
  │     ├─ chart-legend re-renders (no-op unless chartSeries changed)
  │     └─ update-indicator re-computes formatStaleRelative(nowTs - lastUpdateTs)
  ↓ When > 5 s without a successful tick:
        └─ isStale = true → data-stale="true" → CSS swaps dot color + pauses pulse
```

**Critical insight:** Der Stempel-Refresh hängt am `nowTs`-Tick, nicht an einem eigenen `setInterval`. Das funktioniert, **weil** der bestehende 1-s-Polling-Tick `nowTs` weitersetzt — auch wenn der Snapshot identisch wäre, der Tick selbst ist regelmäßig (modulo Backend-Stillstand, was genau der Stale-Trigger ist).

**Edge-Case beim Backend-Stillstand:** Wenn das Backend hängt und der `fetchFn` nie resolvet, schreibt `usePolling` keinen neuen Wert in den Store → `subscribe`-Callback feuert nicht → `nowTs` bleibt stehen → der Indikator-Stempel bleibt auch stehen, **aber** Time geht weiter, also der String wird nicht stale. **Lösung im Test (AC 12 #5):** wir messen den Stale-Wechsel im Komponententest mit Fake-Timern und einem hängenden Promise. **Real-World-Lösung:** Beim allernächsten erfolgreichen Tick (auch nach Minuten) springt `lastUpdateTs` auf den frischen Wert, und `nowTs - lastUpdateTs` ist groß → `data-stale="true"`. Der Wechsel von Frisch zu Stale wird also **nicht** real-time während des Stillstands gerendert (das wäre nur mit eigenem `setInterval` möglich), aber spätestens beim nächsten Tick ist die Anzeige korrekt. **Das ist das gewünschte Verhalten** für 5.1c — eine echte Live-Heartbeat-Logik mit eigenem Timer wäre Premature-Optimization und würde den Mini-Diff-Pflock sprengen. Story 4.3 (Verbindungs-Status-Panel) wird das System-weit lösen.

### Tests — was wirklich wichtig ist

- **Legende-Default:** AC 12 #1 prüft die 3-Dot-Variante. Stelle sicher, dass die Test-Devices (`device({id:1, role:'wr_limit'})` + `device({id:2, role:'grid_meter'})`) tatsächlich beide Serien aktivieren.
- **Battery-only-Edge:** AC 12 #2 ist der Schutz für Setups ohne `wr_limit`-Device (Akku-only-Hausstart). Ohne diesen Test riskieren wir, dass die Legende `Target-Limit` und `Readback` zeigt obwohl die Linien nicht da sind.
- **Funktionstest-Lock:** AC 12 #3 spiegelt 5.1a AC 8.
- **Stale-Indikator (AC 12 #5) ist der trickigste Test.** Der Mock muss nach dem ersten Tick einen ungelösten Promise zurückgeben, sonst feuert der Tick weiter. Pattern:
    ```ts
    getStateSnapshotMock.mockResolvedValueOnce(snapshot({ current_mode: 'idle' }));
    getStateSnapshotMock.mockReturnValue(new Promise<StateSnapshot>(() => {}));
    ```
- **No-Tick-Yet (AC 12 #6):** identischer Pattern mit `mockReturnValue(new Promise(() => {}))` von Anfang an.

### Project Structure Notes

- **Alignment:** Beide Markup-Blöcke leben im bestehenden `routes/Running.svelte`, kein neuer File, keine neue Subdirectory. CSS bleibt komponenten-scoped.
- **Detected conflict — keine.** Der `eyebrow-row`-Container hat aktuell genau zwei Kinder (`<p class="eyebrow">` + `<span class="mode-chip">`); das dritte Element passt natürlich rein.
- **Visueller Konflikt mit 5.1b:** 5.1b ergänzt eine Hero-Zone mit großer Euro-Zahl. Die Hero-Zone wird **oberhalb** der bestehenden `running-card`-Sections gerendert (5.1b-Preamble erklärt das). Unser Update-Indikator sitzt im **bestehenden** `running-header.eyebrow-row` neben dem Modus-Chip — kollidiert nicht mit der Hero-Zone, weil die Hero-Zone separater Wrapper-Block werden wird.

### References

- [Source: _bmad-output/implementation-artifacts/5-1a-live-betriebs-view-post-commissioning-mini-shell.md] — Vorgängerstory, gesamte Datei `Running.svelte` etabliert hier.
- [Source: _bmad-output/planning-artifacts/architecture.md — Amendment 2026-04-22] — REST-Polling, CSS Custom Properties Single-Source, handgeschriebene TS-Types.
- [Source: _bmad-output/planning-artifacts/architecture.md — Amendment 2026-04-23] — Light-only.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Anti-Patterns to Avoid] — UX-DR30 (keine Tooltips, keine Modals), UX-DR19 (kein Spinner; Skeleton-Pulse-Cadence).
- [Source: _bmad-output/planning-artifacts/prd.md — NFR27] — „Pull nicht Push": kein Toast, kein Banner für den Update-Indikator.
- [Source: CLAUDE.md] — Regel 5 (Logging), Stolperstein-Liste (`date-fns` & Co. verboten, kein `lib/tokens/*.ts`, kein WebSocket-Frontend-Code, kein OpenAPI-Codegen, kein Dark-Mode, keine i18n-Infrastruktur).
- [Source: frontend/src/routes/Running.svelte (5.1a-Stand)] — `chartSeries`-`$derived`-Logik, `nowTs`-Tick-Pfad, `formatRelative`-Helper.
- [Source: frontend/src/lib/components/charts/LineChart.svelte] — `ChartSeries`-Shape (`label`, `color`, `data`).

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

- **2026-04-25 — Story erstellt** via `bmad-create-story`. Scope: Inline-Legende für die 3 Chart-Serien + Update-Indikator (Pulse-Dot + relativer Stempel) im `Running.svelte`-Header. Komplementär zu Story 5.1a (`done`), nicht-blockierend für 5.1b (`backlog`). Kein Backend, keine Migration, keine neue Dependency. PR-Ziel ≤ 200 LOC inkl. 6 neuer Vitest-Cases.
