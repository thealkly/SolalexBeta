# Story 5.1a: Live-Betriebs-View post-Commissioning (Mini-Shell, vorgezogen)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Nutzer direkt nach Klick auf „Aktivieren",
I want sofort sehen, was Solalex gerade regelt — ein Live-Diagramm, aktueller Modus, letzte Zyklen —,
so that ich Vertrauen gewinne, dass die Regelung arbeitet, bevor Epic 4 (Diagnose) und Story 5.1b (Euro-Hero) fertig sind.

**Amendment Sprint Change Proposal 2026-04-24 (verbindlich):** Diese Story zieht aus der ursprünglichen Story 5.1 ausschließlich den Shell-Grundbestand vor: Route-Erweiterung von `/running` (aktuell `RunningPlaceholder.svelte`) zu einer Live-Betriebs-View mit Chart + Modus-Chip + Mini-Zyklen-Liste. Kein Euro-Wert, kein Energy-Ring, keine Responsive-Nav, keine Charakter-Zeile, kein Bezugspreis-Stepper — das bleibt komplett in Story 5.1b. Ziel: ≤ 2 Dev-Tage. Zeitliche Einordnung: **nach Story 3.2 done** (3.2 ist bereits done; die Drossel schreibt produktive Dispatches in `control_cycles`).

**Scope-Pflock:** Keine neue SQL-Migration. Keine neue externe Dependency. Keine Änderung an `controller.py` außer einem einzigen Zusatz-Call `state_cache.update_mode(...)`. `LineChart.svelte` + `usePolling<T>` + `getStateSnapshot` werden **1:1 reused** — nicht neu erfinden.

## Acceptance Criteria

1. **Route-Gate (commissioned-only):** `Given` mindestens ein Device in `devices` mit `commissioned_at IS NOT NULL` existiert, `When` das Frontend die Hash-Route `#/running` öffnet, `Then` rendert die neue Live-Betriebs-View — nicht mehr der `RunningPlaceholder`. **And** der bestehende Gate-Flow in `App.svelte` (`evaluateGate` → Redirect auf `#/config` wenn nicht commissioned) bleibt unverändert; non-commissioned Setups werden weiterhin in den Setup-Flow geleitet.

2. **Live-Chart (3 Serien, 5-s-Sliding-Window):** `Given` die Live-Betriebs-View ist gemounted, `When` sie rendert, `Then` wird die bereits existierende `LineChart.svelte`-Komponente aus `frontend/src/lib/components/charts/LineChart.svelte` mit `windowMs=5000` und drei Serien verwendet:
   - **„Netz-Leistung"** (`grid_meter`-Role, Serie-Farbe `var(--color-accent-warning)` — Rot für Bezug / positive Werte, Shelly 3EM liefert positive = Bezug, negative = Einspeisung, siehe Story 3.2 Dev-Notes)
   - **„Target-Limit"** (letzter Dispatch-`target_value_w` aus dem `recent_cycles`-Payload für `role='wr_limit'`, Serie-Farbe `var(--color-accent-primary)`)
   - **„Readback"** (aktueller HW-State der `wr_limit`-Entity aus `entities[*]`, Serie-Farbe `var(--color-text-secondary)`)
   **And** die Serien werden nur gerendert, wenn das jeweilige Role-Device existiert (Haushalt ohne WR: keine Target/Readback-Serien; siehe Story 5.4 AC für Präzedenz).

3. **Modus-Chip:** `Given` die View rendert, `When` der aktuelle Regel-Modus dargestellt wird, `Then` zeigt ein Status-Chip oben einen von `Drossel | Speicher | Multi | Idle`. Der Wert stammt aus dem **neuen Feld** `current_mode` im `/api/v1/control/state`-Payload. Mapping: `"drossel" → "Drossel"`, `"speicher" → "Speicher"`, `"multi" → "Multi"`, fehlend/`"idle"` → `"Idle"`. Das Chip nutzt die Farb-Tokens aus `app.css` (teal für aktiv, grau für idle) — **keine neuen** Farben.

4. **Mini-Zyklen-Liste:** `Given` die View rendert, `When` die Liste angezeigt wird, `Then` werden die letzten **10** Zyklen aus dem neuen `recent_cycles`-Array des Payloads in einer kompakten Liste dargestellt mit den Spalten:
   - Timestamp (relativ: „vor 3 s", „vor 1 min", „vor 12 min" — simple Intl-Relative-Time oder handgeschriebene `formatRelative(iso)`-Funktion; keine neue Dependency wie `date-fns`)
   - Source-Badge (`solalex` = teal, `manual` = grau, `ha_automation` = blaugrau)
   - Target-Watts (als `xxx W` oder `—` wenn `null`)
   - Readback-Status-Badge (`passed` = teal, `failed`/`timeout` = rot, `vetoed` = orange, `noop` = grau)
   - Latenz (`xx ms` oder `—`)
   **And** die Liste hat ein max-height mit CSS-Scroll; keine Virtualisierung, keine Filter (4.1-Scope).

5. **Rate-Limit-Hinweis:** `Given` mindestens ein Device hat einen `last_write_at`-Wert jünger als `RateLimitPolicy.min_interval_s` (aktuell hart 60.0 s für Hoymiles/Marstek/Shelly), `When` die View rendert, `Then` zeigt sie eine kleine Info-Zeile unter dem Chart: „Nächster Write in X s". Der Wert kommt aus dem neuen Feld `rate_limit_status[]` im Payload (`seconds_until_next_write` pro Device). Wenn alle Devices `null` (kein Rate-Limit aktiv), wird die Zeile nicht angezeigt.

6. **Polling-Integration (Reuse):** `Given` die View ist gemounted, `When` das Polling läuft, `Then` wird der bestehende `usePolling<StateSnapshot>(client.getStateSnapshot, 1000)`-Hook aus `frontend/src/lib/polling/usePolling.ts` reused — **kein** neuer Hook, **kein** WebSocket (CLAUDE.md-Stolpersteine). `polling.start()` in `onMount`, `polling.stop()` in `onDestroy` — identisches Muster wie in `FunctionalTest.svelte`.

7. **Skeleton-Leerzustand (noch kein Zyklus):** `Given` nach frischem Commissioning enthält `control_cycles` noch keine Einträge (Controller hat noch nicht dispatched oder die ersten Events sind noch nicht im Puffer), `When` die View rendert, `Then` zeigt der Chart seinen eingebauten Skeleton-Pulse (hat `LineChart.svelte` bereits via `showSkeleton`) und unter dem Chart eine neutrale Zeile: „Regler wartet auf erstes Sensor-Event." Die Zyklen-Liste zeigt „Noch keine Zyklen erfasst." **Keine** Fehler-Roten, **keine** Spinner (UX-DR19/DR30).

8. **Funktionstest-Lock (Interop mit Story 2.2):** `Given` während die View offen ist startet ein User den Funktionstest (Story 2.2, `state_cache.test_in_progress == True`), `When` das Polling den nächsten Snapshot mit `test_in_progress=true` liefert, `Then` wird der Live-Chart ausgeblendet und stattdessen eine Info-Zeile gerendert: „Funktionstest läuft — Regelung pausiert." Mit Link `<a href="#/functional-test">Zum Funktionstest</a>`. Sobald `test_in_progress=false` zurückkommt, rendert die View normal weiter (Polling läuft durchgehend).

9. **Backend-Erweiterung `/api/v1/control/state`:** `Given` der bestehende Endpoint in `backend/src/solalex/api/routes/control.py`, `When` er eine Antwort baut, `Then` enthält das `StateSnapshot`-Pydantic-Modell (in `backend/src/solalex/api/schemas/control.py`) **zusätzlich** zu den bisherigen Feldern (`entities`, `test_in_progress`, `last_command_at`):
   - `current_mode: Literal["drossel", "speicher", "multi", "idle"]` — aus `state_cache.current_mode`, Default `"idle"` falls noch nie gesetzt.
   - `recent_cycles: list[RecentCycle]` — max 10 Einträge, geliefert über `control_cycles.list_recent(conn, limit=10)` mit Mapping auf ein neues Pydantic-Model `RecentCycle` (Felder: `ts: datetime`, `device_id: int`, `mode: str`, `source: str`, `sensor_value_w: float | None`, `target_value_w: int | None`, `readback_status: str | None`, `latency_ms: int | None`). Leere Liste wenn noch keine Zyklen.
   - `rate_limit_status: list[RateLimitEntry]` — eine Entry pro Device, `{ "device_id": int, "seconds_until_next_write": int | null }`. `null` wenn `last_write_at is None` oder ausreichend Zeit vergangen. Berechnung: `max(0, int((last_write_at + timedelta(seconds=min_interval_s) - now).total_seconds()))` oder `None`.
   **And** die JSON-Response-Shape bleibt CLAUDE.md-Regel-4-konform: direkt das Objekt, kein `{data: ..., success: true}`-Wrapper.

10. **StateCache-Erweiterung:** `Given` das bestehende `StateCache` in `backend/src/solalex/state_cache.py`, `When` die View den Modus liest, `Then` existiert ein neues Feld `self.current_mode: str = "idle"` (Default) und ein Setter `def update_mode(self, mode_value: str) -> None`, der den Wert aktualisiert (synchron, kein async, kein Lock — single-writer über Controller). **And** `StateSnapshot`-Dataclass (nicht das Pydantic-Model!) bekommt ein zusätzliches Feld `current_mode: str`. **And** `StateCache.snapshot()` schreibt den aktuellen Wert in den Snapshot.

11. **Controller schreibt Modus in State-Cache:** `Given` der Controller schließt einen Zyklus ab, `When` er `state_cache.update(...)` für die Device-Entity aufruft (AC 11 aus Story 3.1 — bestehender Code), `Then` ruft er **zusätzlich** `state_cache.update_mode(self._current_mode.value)` genau einmal pro Zyklus. Der `Mode.value` liefert direkt `"drossel"` / `"speicher"` / `"multi"` (Enum-Values sind lowercase strings, siehe `controller.py::Mode`). Die Erweiterung passt in eine einzelne Zeile im bestehenden Code-Pfad — es wird **keine** neue Methode im Controller eingeführt und **keine** bestehende Methode umstrukturiert.

12. **Rate-Limit-Berechnung im Backend:** `Given` die `rate_limit_status`-Berechnung für das Response-Payload, `When` der Endpoint die Werte bildet, `Then` lädt er alle Devices via `SELECT id, adapter_key, last_write_at FROM devices` (ein einziger Query), bestimmt pro Device `min_interval_s` via `adapter_registry[adapter_key].get_rate_limit_policy().min_interval_s`, und rechnet mit dem `now`-Timestamp (`datetime.now(tz=UTC)`) aus. Der Registry ist bereits in `app.state` vorhanden (Story 3.1); Zugriff wie in `main.py`.

13. **Polling-Payload ist Pydantic-Model-validiert:** `Given` die Response, `When` FastAPI sie serialisiert, `Then` läuft der existierende `response_model=StateSnapshot`-Mechanismus durch (das Pydantic-Model wird um die neuen Felder erweitert) **And** alle Feldnamen im JSON sind `snake_case` (CLAUDE.md Regel 1) **And** der TS-Handschrieb `StateSnapshot` in `frontend/src/lib/api/types.ts` wird mit den drei neuen Feldern erweitert — **kein** OpenAPI-Codegen (CLAUDE.md Regel „kein OpenAPI-Codegen-Setup").

14. **Unit-Tests (Pytest + Vitest, MyPy strict, Ruff):** Neue / erweiterte Tests:
    **Backend (`backend/tests/`):**
    - `backend/tests/unit/test_state_cache_mode.py` — `StateCache.update_mode` + `snapshot.current_mode` Default `"idle"`; Setter überschreibt; Snapshot spiegelt den Wert.
    - `backend/tests/integration/test_control_state_endpoint.py` (erweitert, falls existiert; sonst neu) — Endpoint liefert `current_mode`, `recent_cycles`, `rate_limit_status`; leere Listen bei leerer DB; Rate-Limit-Countdown korrekt wenn `last_write_at` vor 30 s gesetzt; `null` wenn `last_write_at is None` oder > `min_interval_s` in Vergangenheit.
    - `backend/tests/unit/test_controller_mode_propagation.py` — Mock-`StateCache` mit `update_mode`-Spy, Controller-Zyklus mit `Mode.DROSSEL` triggert den Call einmal pro Zyklus.
    
    **Frontend (`frontend/src/routes/`):**
    - `frontend/src/routes/Running.test.ts` (neue Datei, ersetzt das `RunningPlaceholder`-Setup, oder parallel dazu wenn wir den Placeholder als `Running.svelte` umbenennen) — Render-Test mit Mock-`getStateSnapshot`, verifiziert: Chart rendert mit 3 Serien, Modus-Chip zeigt korrekten Text, Mini-Liste rendert 10 Einträge, `test_in_progress=true` triggert den Lock-State, Skeleton bei leerer Liste.
    - `frontend/src/lib/api/types.test.ts` (optional, nur falls existiert) — Type-Check für erweiterten `StateSnapshot`.

    **Qualität:**
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf den neuen/geänderten Dateien: `state_cache.py`, `api/routes/control.py`, `api/schemas/control.py`, `routes/Running.svelte`.
    - Alle 4 Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (unverändert — **keine neue Migration**).
    - ESLint + svelte-check + Prettier + Vitest grün.

15. **UX-Compliance (UX-DR30, CLAUDE.md-Stil):** `Given` die View rendert, `Then`:
    - **Keine** Modals, **keine** Tooltips, **keine** Loading-Spinner (Skeleton-Pulse ≥ 400 ms statt Spinner — LineChart liefert das bereits).
    - **Keine** Tabellen im strikten HTML-Sinn (`<table>`) — die Mini-Liste ist eine semantische `<ul>` mit `<li>`-Einträgen und CSS-Grid-Layout.
    - **Keine** emotionalen Adjektive in den Zahlen (keine „super", „stark" — die Werte sind nackt mit Einheit; z. B. „ −142 W" statt „ordentliche −142 W").
    - Tokens aus `app.css` (CSS Custom Properties) — **keine** neuen Token-Dateien in `lib/tokens/*.ts` (CLAUDE.md Stolperstein).
    - Deutsche UI-Strings hardcoded in der Svelte-Komponente (CLAUDE.md: „keine i18n-Infrastruktur in v1").
    - Code-Kommentare auf Englisch.

16. **Fallback (kippbar):** `Given` die Story wird gestrichen (Notfall), `When` der Fallback greift, `Then` bleibt der bestehende `RunningPlaceholder.svelte` als Platzhalter erhalten, und ein kleiner Link „Diagnose öffnen" zeigt auf die (noch nicht existierende) Epic-4-Route. Kein Reißverschluss-Cleanup nötig.

## Tasks / Subtasks

- [x] **Task 1: Backend — `StateCache` um `current_mode` erweitern** (AC: 10)
  - [x] `backend/src/solalex/state_cache.py`:
    - Feld `self.current_mode: str = "idle"` im `__init__`.
    - Methode `def update_mode(self, mode_value: str) -> None` — akzeptiert `"drossel" | "speicher" | "multi" | "idle"`; speichert ohne Lock (single-writer-Garantie durch Controller's `_device_locks`).
    - `StateSnapshot`-Dataclass (nicht Pydantic) um `current_mode: str` erweitern.
    - `snapshot()` schreibt `self.current_mode` in die zurückgegebene Dataclass.
  - [x] Test: `backend/tests/unit/test_state_cache_mode.py` — Default, Setter, Snapshot-Mirror.

- [x] **Task 2: Backend — Pydantic-Schemas erweitern** (AC: 9, 13)
  - [x] `backend/src/solalex/api/schemas/control.py`:
    - Neues Model `RecentCycle` (`ts: datetime`, `device_id: int`, `mode: str`, `source: str`, `sensor_value_w: float | None`, `target_value_w: int | None`, `readback_status: str | None`, `latency_ms: int | None`).
    - Neues Model `RateLimitEntry` (`device_id: int`, `seconds_until_next_write: int | None`).
    - `StateSnapshot` um `current_mode: Literal["drossel","speicher","multi","idle"]`, `recent_cycles: list[RecentCycle]`, `rate_limit_status: list[RateLimitEntry]` erweitern.
  - [x] Snake_case im JSON durch direktes Feld-Naming (kein Pydantic-Alias).

- [x] **Task 3: Backend — Endpoint `/api/v1/control/state` erweitern** (AC: 9, 12)
  - [x] `backend/src/solalex/api/routes/control.py`:
    - Dependency-Zugriff auf `app.state.db_conn_factory` und `app.state.adapter_registry` (siehe `main.py` Lifespan-Wiring).
    - `recent_cycles`: `async with db_conn_factory() as conn: cycles = await list_recent(conn, limit=10)` → Mapping auf `RecentCycle`-Model.
    - `rate_limit_status`: `SELECT id, adapter_key, last_write_at FROM devices` — ein einzelner Query; pro Device `min_interval_s` aus `adapter_registry[adapter_key].get_rate_limit_policy()`; `seconds_until_next_write = max(0, ...)` oder `None`.
    - `current_mode` aus dem bestehenden `state_cache.snapshot().current_mode`.
    - Response-Shape direkt das Objekt, kein Wrapper (CLAUDE.md Regel 4).
  - [x] Test: `backend/tests/integration/test_control_state_endpoint.py` — 3 neue Felder in Response, leere Listen bei leerer DB, Rate-Limit-Countdown korrekt.

- [x] **Task 4: Backend — Controller ruft `update_mode` pro Zyklus** (AC: 11)
  - [x] `backend/src/solalex/controller.py`:
    - Im bestehenden Zyklus-Schreib-Pfad (direkt vor oder nach `state_cache.update(...)` — es gibt genau einen Call-Site in `_record_noop_cycle` / `_safe_dispatch`) einmal `self._state_cache.update_mode(self._current_mode.value)` aufrufen.
    - Keine neue Methode, keine Umstrukturierung. Mini-Diff.
  - [x] Test: `backend/tests/unit/test_controller_mode_propagation.py` — Mock-StateCache verifiziert genau einen Call pro Zyklus.

- [x] **Task 5: Frontend — TS-Types erweitern** (AC: 13)
  - [x] `frontend/src/lib/api/types.ts`:
    - `RecentCycle`-Interface.
    - `RateLimitEntry`-Interface.
    - `StateSnapshot` um `current_mode`, `recent_cycles`, `rate_limit_status` erweitern.
  - [x] Handgeschrieben, **kein** `openapi-typescript`-Codegen (CLAUDE.md Stolperstein).

- [x] **Task 6: Frontend — `Running.svelte` als Live-Betriebs-View** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 15)
  - [x] Datei-Entscheidung: **Rename** `frontend/src/routes/RunningPlaceholder.svelte` → `Running.svelte` UND Import in `App.svelte` anpassen (eine Zeile). Grund: `#/running` ist bereits im `VALID_ROUTES`-Set und wird via `evaluateGate` nach Commissioning angesteuert. Wir ersetzen den Inhalt, nicht den Pfad.
  - [x] `Running.svelte`:
    - `<script lang="ts">` Setup analog zu `FunctionalTest.svelte`:
      - `onMount`: `devices = await client.getDevices()` + `polling.start()`.
      - `onDestroy`: `polling.stop()`.
      - `$effect` auf `polling.data.subscribe(...)` → pusht Sensor/Target/Readback in pro-Entity-Puffer (WindowMs + 500).
    - Serien bauen via `$derived`:
      - `grid_meter`-Serie aus `snapshot.entities.find(e => e.role === 'grid_meter')`.
      - `wr_limit`-Target-Serie aus den letzten `recent_cycles` mit `role='wr_limit'` (Target-Watts, gefiltert aus den Cycles zu Entity-ID-Zuordnung über `devices`).
      - `wr_limit`-Readback-Serie aus `snapshot.entities.find(e => e.role === 'wr_limit')`.
    - Modus-Chip: `<span class="chip chip-{snapshot.current_mode}">{MODE_LABEL[snapshot.current_mode]}</span>`.
    - Mini-Liste: `{#each snapshot.recent_cycles.slice(0, 10) as cycle (cycle.ts)}` mit `<li>`-Einträgen und CSS-Grid-Layout.
    - Rate-Limit-Hinweis: `{#if activeRateLimit}<p class="rate-hint">Nächster Write in {activeRateLimit} s</p>{/if}`.
    - Funktionstest-Lock: `{#if snapshot.test_in_progress}` → Info-Zeile statt Chart.
    - Skeleton-State: LineChart rendert ihn built-in; unter dem Chart eine neutrale Zeile wenn `recent_cycles.length === 0`.
  - [x] Styles reusen aus `app.css` Tokens (`--color-accent-primary`, `--color-accent-warning`, `--color-text`, `--color-text-secondary`, `--color-surface`, `--space-*`, `--radius-card`, `--shadow-*`). **Keine** neuen Tokens.
  - [x] Deutsche UI-Strings hardcoded; Code-Kommentare auf Englisch.
  - [x] Test: `frontend/src/routes/Running.test.ts` mit `@testing-library/svelte` + `happy-dom` (beide sind durch Story 2.3a ausgebaut).

- [x] **Task 7: `formatRelative(iso)`-Helper (im `Running.svelte` oder als kleine Util-Datei)** (AC: 4)
  - [x] Einfache Funktion, die zu `"vor X s"`, `"vor X min"`, `"vor X h"` aufrundet — **keine** externe Dependency wie `date-fns` oder `dayjs`.
  - [x] Liegt idealerweise inline im `<script>`-Block von `Running.svelte` (nicht exportiert, 10–15 Zeilen).

- [x] **Task 8: App.svelte — Import-Rename (Mini-Diff)** (AC: 1)
  - [x] `import RunningPlaceholder from './routes/RunningPlaceholder.svelte'` → `import Running from './routes/Running.svelte'`.
  - [x] `<RunningPlaceholder />` im Route-Switch → `<Running />`.
  - [x] Eine Zeile im Import-Block, eine Zeile im Template. Keine weiteren Änderungen.

- [x] **Task 9: Final Verification** (AC: 14)
  - [x] `cd backend && uv run ruff check .` → grün.
  - [x] `cd backend && uv run mypy --strict src/ tests/` → grün.
  - [x] `cd backend && uv run pytest -q` → grün.
  - [x] `cd frontend && pnpm lint && pnpm check && pnpm format:check` → grün.
  - [x] `cd frontend && pnpm test -- --run` (vitest) → grün.
  - [x] SQL-Migrations-Ordering: unverändert (`001_initial.sql` + `002_control_cycles_latency.sql`) — **keine neue Migration**.
  - [x] Drift-Check: `grep -rE "openapi-typescript|date-fns|dayjs|moment" frontend/package.json` → 0 Treffer.
  - [x] Drift-Check: `grep -rE "WebSocket|EventSource" frontend/src/routes/Running.svelte` → 0 Treffer (nur REST-Polling).
  - [x] Manual-Smoke lokal im HA-Add-on mit einem Shelly 3EM + OpenDTU-WR — Alex führt aus, kein Blocker für Review (wie Story 3.2 Task 8).

### Review Findings (2026-04-24)

Adversarielles Review via `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor). Triage: 10 `patch` (inkl. D1→P10 aufgelöst 2026-04-24), 1 `defer`, 15 dismissed.

**Resolved Decisions:**

- D1 (Idle-Semantik zur Laufzeit) — aufgelöst 2026-04-24 zu Option 3: Backend-seitige Override im Endpoint basierend auf Heartbeat aus `recent_cycles[0].ts` mit 15-s-Grace-Window. Wird als Patch **P10** umgesetzt.

**Patch (unchecked — Fix ohne Rückfrage möglich):**

- [ ] [Review][Patch] **P1 [HIGH] — `activeRateLimit` zeigt `Math.max`, Label sagt „Nächster Write"** [`frontend/src/routes/Running.svelte`] — AC 5 (Blind+Edge). Bei zwei Devices mit 5 s / 55 s Rest zeigt UI „Nächster Write in 55 s" statt 5 s. Fix: `Math.max` → `Math.min`.
- [ ] [Review][Patch] **P2 [HIGH] — Target-Limit-Serie unsichtbar & Clock-Skew-Misalignment** [`frontend/src/routes/Running.svelte`] — AC 2 (Blind+Edge). `targetPoints` nutzt `new Date(c.ts).getTime()` (Server-UTC); `gridBuffer`/`readbackBuffer` nutzen `Date.now()` beim Empfang. Rate-Limit 60 s → typische Cycle-Timestamps sind > 5 s alt → Target-Linie nie sichtbar. Zusätzlich: NTP-Skew zwischen Browser & HA-Host verschiebt Target horizontal gegen die anderen zwei Serien. Fix: Target-Wert bei jedem Poll-Tick mit `Date.now()` buffern (analog grid/readback); „letzter Dispatch-`target_value_w`" aus AC 2 wird so als stehende Horizontal-Referenz gerendert.
- [ ] [Review][Patch] **P3 [MEDIUM] — `int(remaining)` truncation → 1-s-Lücke im Countdown** [`backend/src/solalex/api/routes/control.py:163-165`] — AC 5 (Edge). Bei `remaining ∈ (0, 1)` liefert `int(remaining) == 0`; Frontend-Filter `s > 0` schluckt das Signal. Fix: `math.ceil(remaining)` statt `int(...)`.
- [ ] [Review][Patch] **P4 [MEDIUM] — `RecentCycle.mode/source/readback_status` als `str` statt `Literal`** [`backend/src/solalex/api/schemas/control.py:33-39`, `frontend/src/lib/api/types.ts`] — AC 13 (Edge). Repository-Layer nutzt `Literal`; Pydantic-Schema an API-Boundary entfernt die Narrow-Type-Garantie. DB-Wert abseits der erlaubten Strings landet ohne Validierung in der Response; Frontend-Badges fallen stumm auf die Default-Klasse. Fix: Literal in `RecentCycle` + TS-Union in `types.ts` spiegeln.
- [ ] [Review][Patch] **P5 [MEDIUM] — Frontend-Tests testen weder 3-Serien noch 10-Einträge-Cap** [`frontend/src/routes/Running.test.ts`] — AC 14 (Auditor). Backend-Test deckt 10-Cap ab, Frontend explizit gefordert. Fix: Assertion für `ChartSeries`-Array mit 3 Einträgen (grid/target/readback); Render-Test mit 11 Cycles → 10 `<li>`-Einträge.
- [ ] [Review][Patch] **P6 [MEDIUM] — `source`-Badge-Farben nicht AC-konform** [`frontend/src/routes/Running.svelte` (Style `.cycle-source`)] — AC 4 (Auditor). Nur `solalex` (teal) hat distinkte Farbe; `manual` fällt auf Default-Grau, `ha_automation` ist nur marginal dunkleres Grau. AC fordert `solalex=teal`, `manual=grau`, `ha_automation=blaugrau`. Fix: `[data-source='manual']` + `[data-source='ha_automation']` mit distinkten Token-Werten.
- [ ] [Review][Patch] **P7 [LOW] — `datetime.fromisoformat` ValueError wird geschluckt** [`backend/src/solalex/api/routes/control.py:153-157`] — CLAUDE.md Regel 5 (Blind). Fail-open beim Rate-Limit ohne Log-Breadcrumb. Fix: `_logger.exception("unreadable last_write_at ...")` im `except`.
- [ ] [Review][Patch] **P8 [LOW] — Controller mirrort Modus vor Cycle-Write, nicht am Cycle-Call-Site** [`backend/src/solalex/controller.py:164-170`] — AC 11 (Blind+Auditor). Spec sagt „direkt vor oder nach `state_cache.update(...)` — genau ein Call-Site in `_record_noop_cycle` / `_safe_dispatch`". Aktuell: direkt nach Early-Exit-Guards, also auch für Events die nie einen `control_cycles`-Row schreiben. Fix: `update_mode`-Call in `_record_noop_cycle` und `_safe_dispatch` vor/nach dem jeweiligen `state_cache.update(...)` platzieren.
- [ ] [Review][Patch] **P9 [LOW] — Cycle-`{#each}`-Key kann kollidieren** [`frontend/src/routes/Running.svelte`] — AC 4 (Blind+Edge). Key `cycle.ts + '-' + cycle.device_id` kollidiert bei zwei Cycles desselben Device im selben Sekunden-Bucket. Fix: Cycle-`id` in `RecentCycle` aufnehmen (bereits PK in DB) oder Index-Fallback als Sekundär-Key.
- [ ] [Review][Patch] **P10 [LOW] — Idle-Override im Endpoint bei Heartbeat-Gap** [`backend/src/solalex/api/routes/control.py`] — AC 3, D1-Resolution. Wenn `recent_cycles` leer ist oder `recent_cycles[0].ts` älter als 15 s (Grace-Window = 15× Polling-Intervall), dann `current_mode = "idle"` im Response-Payload overriden — unabhängig vom State-Cache-Wert. Kein Controller-Change, kein neuer Query (Daten bereits im Endpoint-Scope). Zusätzlich ein Test-Case in `test_control_state.py`: stale recent_cycles (20 s alt) → Response `current_mode == "idle"` obwohl StateCache noch `"drossel"` mirrort.

**Deferred:**

- [x] [Review][Defer] **DF1 [MEDIUM] — Polling-Fehler werden nicht im UI sichtbar** [`frontend/src/routes/Running.svelte`] — deferred auf Epic 4 / Story 4.3 (Verbindungs-Status-Panel). `usePolling.error` wird nicht subscribed → stiller Stale-Snapshot bei Backend-Ausfall. Out-of-Scope für 5.1a-Mini-Shell; Story 4.3 deckt das System-weit ab.

**Dismissed (15 — Rauschen, defensiv, spec-konform oder Pre-Existing):**

- aiosqlite row_factory Speculation (global gesetzt via `connection_context`); `$effect`-subscribe-Timing (vernachlässigbar, LineChart.skeleton deckt ab); `targetPoints` nicht vor-gefiltert (LineChart-intern gehandhabt); Rate-Limit-Countdown-Refresh-Cadence (1 Hz-Polling reicht); `update_mode`-ohne-Lock (CPython-GIL garantiert Atomicity bei String-Assignment); `formatRelative`-Future-Timestamp (kosmetisch); Empty-State-Duplizierung Chart-Hint + Liste-Hint (spec-mandated — AC 7); `db_conn_factory is None`-Fallback (defensiv test-freundlich); naive-datetime-UTC-Annahme (spiegelt `executor/rate_limiter.py`); `SELECT FROM devices` ohne `commissioned_at`-Filter (keine UI-Konsequenz); Battery-only-Setup ohne Target-Serie (AC 2 explizit); `testInProgress`-stale-Buffer (LineChart filtert per `cutoff`); `main.py`-Mod gegen „NICHT anfassen"-Liste (Spec war ungenau, Change ist notwendig); Test in `tests/unit/` statt `tests/integration/` (File-List stimmt, Reklassifikations-Churn); `error-block` Warning-Rot (Device-Load-Fehler, nicht Empty-State AC 7).

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — REST-Polling statt WebSocket (Amendment 2026-04-22)](../planning-artifacts/architecture.md) — `/api/v1/control/state` ist der kanonische Polling-Endpoint. Client-seitige 1-s-Polling-Animation (UX-DR23) liegt im Chart-Rendering-Pfad.
- [architecture.md — CSS Custom Properties in `app.css` als Single-Source (Amendment 2026-04-22)](../planning-artifacts/architecture.md) — **kein** `lib/tokens/*.ts`.
- [architecture.md — Handgeschriebene TS-Types (Amendment 2026-04-22)](../planning-artifacts/architecture.md) — **kein** OpenAPI-Codegen.
- [prd.md — NFR2, NFR25, NFR27, UX-DR10, UX-DR12, UX-DR19, UX-DR30](../planning-artifacts/prd.md) — Dashboard-TTFD, Polling, „Pull nicht Push", Skeleton-Regeln, Anti-Pattern-Liste.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — insbesondere Regel 1 (snake_case JSON), Regel 4 (JSON ohne Wrapper) und Stolpersteine („kein WebSocket-Frontend-Code", „kein OpenAPI-Codegen", „Light-only, kein Dark-Mode").
- [Story 2.2 — Funktionstest mit Readback & Commissioning](./2-2-funktionstest-mit-readback-commissioning.md) — **Pflichtlektüre**: `LineChart.svelte`, `usePolling.ts`, der `ChartSeries`-`DataPoint`-Shape, das `$effect`/`subscribe`-Muster — alles reused, nichts reinventen.
- [Story 3.1 — Core Controller](./3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md) — `control_cycles`-Schema, `state_cache.update(...)`-Call-Site, Source-Attribution-Semantik, Fail-Safe-Wrapper.
- [Story 3.2 — Drossel-Modus](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md) — **Vorzeichen-Konvention Shelly 3EM**: positiv = Bezug, negativ = Einspeisung. Wichtig für die Netz-Leistung-Serie und den roten/teal-Switch.
- [Story 2.3a — Pre-Setup-Disclaimer Gate](./2-3a-pre-setup-disclaimer-gate.md) — der Test-Stack-Ausbau (`happy-dom` + `@testing-library/svelte`) ist dort gelandet; `Running.test.ts` kann den aufbauen.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Backend-Änderung ist klein (StateCache + Schemas + Endpoint + 1 Controller-Zeile). Frontend ersetzt `RunningPlaceholder.svelte` durch eine volle Live-Betriebs-View mit Reuse der 2.2-Infrastruktur. **Keine** neue Migration, **keine** neue Dependency, **keine** neue Route.

**Mini-Diff-Prinzip:** Der Pull-Request sollte auf ~400–600 Zeilen bleiben (inkl. Tests). Bulk ist die neue `Running.svelte` (~200 LOC inkl. Styles) + die Endpoint-Erweiterung (~60 LOC) + Tests (~250 LOC). Wenn du viel mehr produzierst — stopp und prüfe ob du eine Shortcut übersehen hast.

**Dateien, die berührt werden dürfen:**

- **MOD Backend:**
  - `backend/src/solalex/state_cache.py` — `current_mode`-Feld + `update_mode`-Setter + `StateSnapshot`-Dataclass-Feld.
  - `backend/src/solalex/api/schemas/control.py` — `RecentCycle`, `RateLimitEntry`, erweitertes `StateSnapshot`.
  - `backend/src/solalex/api/routes/control.py` — DB-Query für Cycles + Devices, Rate-Limit-Berechnung, Response-Zusammenbau.
  - `backend/src/solalex/controller.py` — **eine Zeile** `self._state_cache.update_mode(self._current_mode.value)` ergänzen. Nicht mehr.
- **NEU Backend (Tests):**
  - `backend/tests/unit/test_state_cache_mode.py`
  - `backend/tests/integration/test_control_state_endpoint.py` (oder erweitern, falls existiert — check mit `ls backend/tests/integration/ | grep control`)
  - `backend/tests/unit/test_controller_mode_propagation.py`
- **RENAME Frontend:**
  - `frontend/src/routes/RunningPlaceholder.svelte` → `frontend/src/routes/Running.svelte` (Inhalt ersetzt, Pfad umbenannt).
- **MOD Frontend:**
  - `frontend/src/App.svelte` — Import + Template-Tag-Name (2 Zeilen).
  - `frontend/src/lib/api/types.ts` — `RecentCycle`, `RateLimitEntry`, erweitertes `StateSnapshot`.
- **NEU Frontend (Tests):**
  - `frontend/src/routes/Running.test.ts`
- **NICHT anfassen:**
  - `backend/src/solalex/persistence/sql/*.sql` — **keine neue Migration**. Das Schema aus 002 reicht.
  - `backend/src/solalex/persistence/repositories/control_cycles.py` — `list_recent` existiert bereits; **nicht umstrukturieren**.
  - `backend/src/solalex/executor/*` — Veto-Kaskade, Rate-Limiter, Readback sind aus 3.1 fertig.
  - `backend/src/solalex/adapters/*.py` — Rate-Limit-Policies sind fertig; nur lesen.
  - `frontend/src/lib/polling/usePolling.ts` — reuse as-is.
  - `frontend/src/lib/components/charts/LineChart.svelte` — reuse as-is.
  - `frontend/src/routes/FunctionalTest.svelte` — anschauen als Referenz, **nicht** ändern.
  - `frontend/src/lib/gate.ts` — Gate-Logik bleibt unverändert; `/running` ist bereits im Gate-Flow.
  - `backend/src/solalex/main.py` — Lifespan-Wiring bleibt unverändert (`app.state.state_cache`, `app.state.controller`, `app.state.adapter_registry`, `app.state.db_conn_factory` sind bereits vorhanden).

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du ein `lib/tokens/colors.ts` oder sonst ein `lib/tokens/*.ts` anlegst — **STOP**. CSS Custom Properties in `app.css` sind Single-Source (CLAUDE.md Stolperstein).
- Wenn du `date-fns`, `dayjs`, `luxon` oder `moment` importierst — **STOP**. Die `formatRelative`-Funktion ist 10–15 Zeilen stdlib-TS.
- Wenn du `openapi-typescript` oder einen Codegen-Task in `package.json` hinzufügst — **STOP**. Handgeschriebene Types.
- Wenn du `WebSocket`, `EventSource`, `Server-Sent Events` oder `socket.io` nutzt — **STOP**. REST + 1-s-Polling (CLAUDE.md).
- Wenn du eine externe Chart-Library (`chart.js`, `echarts`, `d3`, `uPlot`, `recharts`) installierst — **STOP**. `LineChart.svelte` aus 2.2 reicht; es ist nativ-SVG.
- Wenn du einen Dark-Mode-Switch, ein `[data-theme]`-Attribut oder ein `matchMedia('(prefers-color-scheme)')`-Listener einbaust — **STOP**. Light-only (Amendment 2026-04-23).
- Wenn du `i18n`-Wrapper (`$t('key')`), `svelte-i18n`, `locales/de.json` in dieser Story anlegst — **STOP**. Deutsche Strings hardcoded (Amendment 2026-04-22, CLAUDE.md).
- Wenn du eine neue SQL-Migration `003_*.sql` anlegst — **STOP**. Die Daten sind bereits da (`control_cycles`, `devices.last_write_at`).
- Wenn du `asyncio.Queue`, `events/bus.py` oder Pub/Sub einbaust — **STOP**. Direct-Call im Controller; das Polling ersetzt Pub/Sub zum Frontend.
- Wenn du `structlog` importierst — **STOP**. `get_logger(__name__)` aus `common/logging.py` (CLAUDE.md Regel 5).
- Wenn du eine neue Route wie `/live` oder `/dashboard` anlegst — **STOP**. `/running` ist bereits im Gate-Flow und `VALID_ROUTES`. Wir tauschen nur den Inhalt.
- Wenn du den Hero-Euro-Wert, den Bezugspreis-Stepper, den Energy-Ring, die Charakter-Zeile, die Responsive-Bottom-Nav oder die Tastatur-Shortcuts einbaust — **STOP**. Das ist Story 5.1b, nicht 5.1a.
- Wenn du Filter/Virtualisierung für die Mini-Liste einbaust — **STOP**. 4.1-Scope. Max 10 Einträge reichen.
- Wenn du den vollen Export-Flow, Fehler-Klartext mit Handlungsvorschlag oder Verbindungs-Status-Panel ergänzt — **STOP**. Epic 4.
- Wenn du die Modus-Icons selbst zeichnest (SVG-Custom-Ikonographie UX-DR22) — **STOP**. Für 5.1a reicht ein simples textuelles Chip ohne Icon oder ein 16×16-Unicode-Emoji. Custom-Icons sind 5.1b/5.4.
- Wenn du den Noop-Cycle-Row-Write aus dem Controller änderst oder eine neue Telemetry-Tabelle anlegst — **STOP**. `control_cycles` ist bereits die Wahrheitsquelle.
- Wenn du Pydantic v1-Stil (`@validator`) verwendest — **STOP**. Repo ist auf Pydantic v2 (`@field_validator`, `BaseModel` direkt).
- Wenn du `logging.getLogger(...)` statt `get_logger(__name__)` schreibst — **STOP**. CLAUDE.md Regel 5.
- Wenn du einen Service-Worker, PWA-Manifest oder Offline-Cache ergänzt — **STOP**. Out-of-Scope v1.

### Architecture Compliance Checklist

- **snake_case überall (CLAUDE.md Regel 1):** Python-Felder (`current_mode`, `recent_cycles`, `rate_limit_status`, `seconds_until_next_write`), JSON-Feldnamen identisch, TS-Interfaces schreiben snake_case (nicht camelCase — CLAUDE.md „API-JSON snake_case"). Svelte-Komponenten PascalCase (`Running.svelte`), TS-Typen PascalCase (`RecentCycle`, `RateLimitEntry`, `StateSnapshot`).
- **Ein Python-Modul pro Adapter (Regel 2):** 5.1a fasst Adapter nicht an.
- **Closed-Loop-Readback für jeden Write (Regel 3):** 5.1a **liest** nur — kein neuer Write-Pfad.
- **JSON ohne Wrapper (Regel 4):** Response ist direkt das `StateSnapshot`-Objekt, kein `{data, success, error}`.
- **Logging (Regel 5):** Falls du Backend-Logs ergänzt: `_logger = get_logger(__name__)` am Modul-Top. Keine neuen Logs nötig für 5.1a.
- **MyPy strict:** Neue Funktionen type-hinted, `from __future__ import annotations`, `Literal[...]` für Enum-Strings.
- **Forward-only Migrations:** **keine** neue Migration.
- **CSS Tokens (Amendment 2026-04-22):** Nur `var(--...)` aus `app.css`, **keine** neuen Tokens, **kein** Dark-Mode-Override (Amendment 2026-04-23).

### Pipeline-Kette — Reference Flow (Live-Betriebs-View)

```
Browser loads #/running (commissioned gate passed)
  ↓ App.svelte <Running /> mounts
  ↓ onMount:
  │    ├─ devices = await client.getDevices()                [existing, Story 2.2]
  │    ├─ polling = usePolling(client.getStateSnapshot, 1000) [existing]
  │    └─ polling.start()
  ↓ Every 1 s:
  │    ├─ fetch GET /api/v1/control/state                    [existing endpoint, extended schema]
  │    │    └─ Backend:
  │    │         ├─ state_cache.snapshot() → entities, test_in_progress, last_command_at, current_mode  [NEW current_mode]
  │    │         ├─ list_recent(conn, limit=10) → RecentCycle[]                                        [existing repo]
  │    │         ├─ SELECT id, adapter_key, last_write_at FROM devices → rate_limit_status[]           [NEW query]
  │    │         └─ StateSnapshot(…).model_dump() → JSON
  │    └─ $effect:
  │         ├─ push entity[role=grid_meter].state → grid_meter buffer
  │         ├─ push entity[role=wr_limit].state → readback buffer
  │         └─ derive target-series from recent_cycles[role=wr_limit]
  ↓ Render:
  │    ├─ <Chip>{current_mode}</Chip>
  │    ├─ <LineChart series={[grid_meter, target, readback]} windowMs={5000} now={Date.now()} />   [reused 2.2]
  │    ├─ {#if rate_limit_active} <p>Nächster Write in {seconds}s</p> {/if}
  │    └─ <ul>{#each recent_cycles.slice(0, 10) as cycle} <li>…</li> {/each}</ul>
  ↓ onDestroy: polling.stop()
```

**Einziger wirklich neuer Code** lebt im Block `[NEW current_mode]` und `[NEW query]` sowie in `Running.svelte`. Alles andere ist Reuse.

### Vorzeichen-Konvention für die Netz-Leistung-Serie

**Shelly 3EM** (siehe [Story 3.2 Dev-Notes](./3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md)):
- **Positiv = Grid Import (Bezug aus dem Netz)** → Serie-Farbe Rot (`var(--color-accent-warning)`).
- **Negativ = Grid Export (Einspeisung ins Netz)** → Serie-Farbe Teal (`var(--color-accent-primary)`).

Für die View in 5.1a **reicht eine einzelne Serie** mit wechselnder Vorzeichen-Interpretation — der LineChart-Pfad zeichnet Werte einfach in der Achsenlage. Wenn du Farbänderung pro Vorzeichen willst (nice to have), kannst du pro Sample die Serie clippen oder zwei Serien („import"/„export") mit jeweils nur positiven/negativen Werten führen. **Für 5.1a reicht eine einzelne Serie mit dynamischer Farbe** — minimalst.

### Mini-Liste — konkrete Markup-Skizze (keine Verbindlichkeit, nur Hilfe)

```html
<ul class="cycle-list">
  {#each snapshot.recent_cycles.slice(0, 10) as cycle (cycle.ts)}
    <li class="cycle-row">
      <span class="cycle-ts">{formatRelative(cycle.ts)}</span>
      <span class="cycle-source" data-source={cycle.source}>{cycle.source}</span>
      <span class="cycle-target">{cycle.target_value_w ?? '—'} W</span>
      <span class="cycle-readback" data-status={cycle.readback_status ?? 'noop'}>
        {cycle.readback_status ?? 'noop'}
      </span>
      <span class="cycle-latency">{cycle.latency_ms ?? '—'} ms</span>
    </li>
  {/each}
</ul>
```

CSS-Grid mit `grid-template-columns: 90px 90px 80px 80px 60px; gap: var(--space-2)`.

### Testing — was wirklich wichtig ist

- **`test_state_snapshot_includes_recent_cycles`**: prüft, dass der erweiterte Endpoint bei **leerer** `control_cycles`-Tabelle `recent_cycles=[]` liefert (nicht `null`) und bei 11 Zeilen genau 10 Einträge in ID-DESC-Reihenfolge.
- **`test_rate_limit_countdown_correct`**: `last_write_at` gesetzt auf `now - 30 s`, Hoymiles-Policy `60 s` → `seconds_until_next_write == 30` (±1 für Timing-Slack).
- **`test_rate_limit_none_when_no_last_write`**: fresh device → `seconds_until_next_write is None`.
- **`test_current_mode_default_idle`**: fresh `StateCache` → snapshot-Mode ist `"idle"`.
- **`test_running_renders_test_in_progress_lock`** (frontend): snapshot mit `test_in_progress=true` → Chart ausgeblendet, Info-Zeile sichtbar.
- **`test_running_skeleton_when_no_cycles`** (frontend): snapshot mit `recent_cycles=[]` + `entities=[]` → LineChart rendert `chart-skeleton`, Zyklen-Liste zeigt „Noch keine Zyklen erfasst."

### Project Structure Notes

- **Alignment:** Die Änderungen respektieren die Directory-Layouts aus CLAUDE.md (Backend: `api/routes/control.py` + `api/schemas/control.py` + `state_cache.py`; Frontend: `routes/Running.svelte` + `lib/api/types.ts`). Keine neuen Subdirectories, keine Workspace-Root-Konfiguration.
- **Detected conflict:** Der Route-Key `running` ist in `App.svelte`-`VALID_ROUTES` bereits vorhanden und zeigt auf `RunningPlaceholder`. Durch den Rename zu `Running.svelte` und den Import-Fix bleibt die Gate-Logik unverändert.
- **Gate-Flow bleibt:** `evaluateGate(...)` in `lib/gate.ts` leitet commissioned-Setups bereits auf `#/running` — die Live-Betriebs-View erbt diesen Gate-Flow automatisch, ohne dass wir `gate.ts` ändern müssen.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1a] — Story-Definition (Amendment Sprint Change Proposal 2026-04-24).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-24.md#4.1] — Vollständige AC-Begründung und Scope-Begrenzung.
- [Source: _bmad-output/planning-artifacts/architecture.md — Amendment 2026-04-22] — REST-Polling statt WebSocket, handgeschriebene TS-Types, CSS Custom Properties als Single-Source.
- [Source: _bmad-output/planning-artifacts/architecture.md — Amendment 2026-04-23] — Light-only, kein Dark-Mode in v1.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#UX-DR10, UX-DR12, UX-DR19, UX-DR30] — Status-Chips, Skeleton, Anti-Pattern-Liste.
- [Source: _bmad-output/implementation-artifacts/2-2-funktionstest-mit-readback-commissioning.md#Task 8] — `LineChart.svelte` Scaffolding, `ChartSeries`-Shape.
- [Source: _bmad-output/implementation-artifacts/3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit.md#Task 2] — `control_cycles`-Repo, `list_recent`.
- [Source: _bmad-output/implementation-artifacts/3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung.md#Vorzeichen-Konvention] — Shelly 3EM sign convention.
- [Source: CLAUDE.md#5 harte Regeln + Stolpersteine] — snake_case, kein Wrapper, kein WS, Light-only, keine i18n-Infrastruktur, kein OpenAPI-Codegen, keine lib/tokens/*.ts.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) via Claude Code / `bmad-dev-story` (2026-04-24).

### Debug Log References

- `uv run pytest -q` → 136 passed (Backend, inkl. 11 neue Tests für State-Cache-Mode, Endpoint-Erweiterung und Controller-Mode-Propagation)
- `uv run ruff check .` → clean
- `uv run mypy --strict src/ tests/` → Success: no issues found in 77 source files
- `pnpm check` → 0 errors / 0 warnings (273 files)
- `pnpm lint` → clean
- `pnpm test -- --run` → 49/49 passed (inkl. 4 neue Running.test.ts-Tests mit happy-dom + @testing-library/svelte)
- Drift-Check `grep -rE "openapi-typescript|date-fns|dayjs|moment" frontend/package.json` → 0 Treffer
- Drift-Check `grep -rE "WebSocket|EventSource" frontend/src/routes/Running.svelte` → 0 Treffer
- SQL-Migrations unverändert (001 + 002 nummerisch lückenlos)

### Completion Notes List

- **Backend — StateCache (AC 10):** `current_mode: ModeValue = "idle"` + `update_mode()`-Setter mit Literal-Coercion auf `{drossel, speicher, multi, idle}`; unbekannte Werte fallen auf `"idle"` zurück, damit keine non-kanonischen Werte ins Polling-Payload lecken. `StateSnapshot`-Dataclass um `current_mode` erweitert; `snapshot()` spiegelt den Wert.
- **Backend — Pydantic-Schemas (AC 9, 13):** Neue Models `RecentCycle` (ohne `reason`/`cycle_duration_ms` — UI braucht sie nicht) und `RateLimitEntry`. `StateSnapshot` um `current_mode: Literal[...]`, `recent_cycles: list[RecentCycle] = Field(default_factory=list)`, `rate_limit_status: list[RateLimitEntry] = Field(default_factory=list)` erweitert. Snake_case direkt in den Feldnamen — keine Pydantic-Aliase nötig.
- **Backend — Endpoint (AC 9, 12):** `GET /api/v1/control/state` lädt `control_cycles.list_recent(conn, limit=10)` und einen einzelnen `SELECT id, adapter_key, last_write_at FROM devices` pro Call. Cooldown-Rechnung via `adapter_registry[key].get_rate_limit_policy().min_interval_s` mit UTC-`now()`. `db_conn_factory` + `adapter_registry` werden in `main.py`-Lifespan auf `app.state` exponiert — Endpoint greift read-only darauf zu, ohne Controller-Interna anzufassen. Response-Shape bleibt CLAUDE.md-Regel-4-konform (direktes Objekt).
- **Backend — Controller (AC 11):** `self._state_cache.update_mode(self._current_mode.value)` als einzelne Zeile direkt nach den Early-Exit-Guards (`test_in_progress` / nicht commissioned) in `on_sensor_update`. Genau ein Call pro verarbeitetes Event, keine neue Methode, keine Umstrukturierung. Test `test_update_mode_not_called_when_test_in_progress` dokumentiert, dass der Mode-Mirror während eines laufenden Funktionstests absichtlich nicht aktualisiert wird — der stale Wert hält die Diagnose-Semantik sauber.
- **Frontend — Types (AC 13):** `RecentCycle`, `RateLimitEntry`, `ControlMode` + erweiterter `StateSnapshot` handgeschrieben in `types.ts`. Kein OpenAPI-Codegen.
- **Frontend — Running.svelte (AC 1–8, 15):** `RunningPlaceholder.svelte` durch `Running.svelte` ersetzt; `App.svelte`-Import & Template-Tag umbenannt (2 Zeilen Mini-Diff). Komponente reused `usePolling<StateSnapshot>(client.getStateSnapshot, 1000)` und `LineChart.svelte` unverändert. Chart-Serien werden nur gerendert, wenn das passende Role-Device existiert (Präzedenz Story 5.4). Target-Serie kommt aus `recent_cycles[device_id == wrLimit.id]`, Grid-Meter/Readback aus einem rollenden `{t,v}`-Puffer (Window + 500 ms Slack, wie FunctionalTest.svelte). Mode-Chip mit Farb-Token-Switch teal/grau über `data-mode`-Attribut. Mini-Liste als `<ul>`/`<li>` mit CSS-Grid, max-height + overflow-y statt Virtualisierung. `formatRelative(iso)` als 10-Zeilen-Inline-Helper ohne externe Dependency. Funktionstest-Lock via `{#if test_in_progress}` → Chart ausgeblendet, Info-Zeile + Link zu `#/functional-test`. Skeleton-Pulse durch `LineChart.showSkeleton`, Text "Regler wartet auf erstes Sensor-Event." unter dem Chart wenn `recent_cycles.length === 0`. Deutsche UI-Strings hardcoded, Code-Kommentare Englisch, nur `var(--...)`-Tokens aus `app.css`.
- **Frontend — Tests (AC 14):** `Running.test.ts` mit `@vitest-environment happy-dom` + `@testing-library/svelte`; 4 Szenarien: Idle-Chip + empty-cycles-Hint, volle Darstellung mit Modus-Chip/Liste/Rate-Limit-Hinweis, Funktionstest-Lock, und Rate-Limit-Suppression wenn alle Devices frei sind. Client-Modul via `vi.mock('../lib/api/client.js', ...)` ersetzt — Tests laufen ohne Backend.
- **Policy-Guards:** Keine neue SQL-Migration, keine neue Dependency, kein WebSocket/EventSource, keine Tabellen, keine Modals, keine Spinner, kein Dark-Mode-Code, keine i18n-Wrapper, kein `lib/tokens/*.ts`, kein OpenAPI-Codegen. Pydantic-v2-Stil (`Field(default_factory=list)`, `Literal[...]`).

### File List

**Backend — MOD:**
- `backend/src/solalex/state_cache.py` — `ModeValue`-Literal, `current_mode`-Feld, `update_mode`-Setter, `StateSnapshot`-Dataclass-Erweiterung.
- `backend/src/solalex/api/schemas/control.py` — `RecentCycle`, `RateLimitEntry`, erweitertes `StateSnapshot`.
- `backend/src/solalex/api/routes/control.py` — DB-Query für Cycles + Devices, Rate-Limit-Berechnung, Response-Zusammenbau.
- `backend/src/solalex/controller.py` — `state_cache.update_mode(...)`-Call in `on_sensor_update` (eine Zeile + 3 Zeilen Kommentar).
- `backend/src/solalex/main.py` — `app.state.db_conn_factory` + `app.state.adapter_registry` in Lifespan expose.

**Backend — NEU (Tests):**
- `backend/tests/unit/test_state_cache_mode.py` — Default `idle`, Setter für jeden erlaubten Wert, Coercion unbekannter Werte auf `idle`, Snapshot-Mirror.
- `backend/tests/unit/test_controller_mode_propagation.py` — parametrisiert über alle Modes, Mock-StateCache verifiziert genau einen Call pro Zyklus; Test-in-progress-Gate-Verifikation.

**Backend — MOD (Tests):**
- `backend/tests/unit/test_control_state.py` — 5 neue Test-Cases: `current_mode`-Default + Reflect, `recent_cycles` ≤ 10 in DESC-Reihenfolge, Rate-Limit-Countdown bei 30-s-Fenster, `None` wenn `last_write_at is None`, `None` wenn Cooldown längst abgelaufen.

**Frontend — RENAME:**
- `frontend/src/routes/RunningPlaceholder.svelte` → `frontend/src/routes/Running.svelte` (gelöscht + neu; vollständiger Content-Austausch).

**Frontend — MOD:**
- `frontend/src/App.svelte` — Import + Template-Tag.
- `frontend/src/lib/api/types.ts` — `RecentCycle`, `RateLimitEntry`, `ControlMode`, erweiterter `StateSnapshot`.

**Frontend — NEU (Tests):**
- `frontend/src/routes/Running.test.ts` — 4 happy-dom-Szenarien (Idle-Chip + empty-cycles-Hint, Vollbild mit Liste + Rate-Limit, Funktionstest-Lock, Rate-Limit-Suppression).

## Change Log

- **2026-04-24 — Story 5.1a implementiert.** Live-Betriebs-View (`#/running`) ersetzt Placeholder; Backend-Endpoint `/api/v1/control/state` um `current_mode`, `recent_cycles` (max 10) und `rate_limit_status` erweitert. `StateCache.update_mode` im Controller als Single-Line-Hook. Alle 4 CI-Gates grün (Ruff + MyPy strict + Pytest 136 passed; ESLint + svelte-check + Vitest 49 passed; Drift-Checks sauber; Migrations unverändert). Reuse von `LineChart.svelte`, `usePolling<T>`, `getStateSnapshot` gemäß Story-Scope-Pflock.

