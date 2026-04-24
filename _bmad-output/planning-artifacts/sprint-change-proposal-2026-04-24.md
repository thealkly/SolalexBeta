# Sprint Change Proposal — 2026-04-24

**Trigger:** „Wir brauchen früher die Möglichkeit zu sehen, was unsere Regelung macht. Aktuell aktiviert man es aber es passiert nichts — man sieht kein Diagramm, also kein Feedback, was genau die Regelung macht."

**Mode:** Incremental (Korrektur­schritt-für-Schritt-approved)
**Autor:** Alex (Solo-Dev) + Claude Opus 4.7
**Scope-Klassifikation:** **Moderate** — Backlog-Reorganisation (Story-Split in Epic 5), kein PRD-/Architecture-Cut.

---

## 1. Issue Summary

Nach dem „Aktivieren"-Klick in Story 2.3 fehlt dem Nutzer jeder Screen, auf dem er sehen könnte, **was Solalex gerade tut**. Die Regler-Pipeline ist technisch fertig (Story 3.1 ✅ review — Controller, Executor, `control_cycles`, Fail-Safe, persistenter Rate-Limiter), die Drossel-Policy ist in der Pipeline (Story 3.2 ready-for-dev). Aber:

- Während des Funktionstests (Story 2.2) gibt es bereits einen Live-Chart via `LineChart.svelte` — der verschwindet nach Commissioning.
- Das richtige Dashboard (Epic 5) liegt komplett im Backlog.
- Die Diagnose-Route (Epic 4) ebenfalls komplett im Backlog — und Story 4.1 würde nur eine Liste liefern, kein Diagramm.

**Ergebnis:** Schwarzer-Screen-Effekt nach Aktivierung. Der Nutzer verliert Vertrauen („das Ding tut nichts"), obwohl der Regler im Hintergrund arbeitet (sobald 3.2 produktiv ist).

**Kategorie:** Neue Anforderung aus Beta-Realität emergiert (nicht: Misunderstanding, nicht: failed approach). Die ursprüngliche Sequenz Epic 3 → Epic 4 → Epic 5 unterschätzt, wie früh Beta-Tester den Visibility-Hunger haben.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Betroffen | Art der Änderung |
|------|-----------|------------------|
| Epic 1 | Nein | `done`, keine Auswirkung |
| Epic 2 | Nein | Reuse von `LineChart.svelte` und Polling-Hook aus 2.2 — keine Story-Änderung |
| Epic 3 | Nein | **Nummerisch unverändert** (3.1–3.7 bleiben). Neue Story kommt in Epic 5, nicht in Epic 3 |
| Epic 4 | Indirekt | Nicht mehr die einzige Visibility-Quelle, bleibt aber inhaltlich unverändert |
| **Epic 5** | **Ja** | Story 5.1 wird **gesplittet** in 5.1a (vorgezogen) + 5.1b (Rest-Scope). 5.2–5.7 unverändert |
| Epic 6 | Nein | |
| Epic 7 | Nein | |

### Story Impact

- **Neu: Story 5.1a — „Live-Betriebs-View post-Commissioning (Mini-Shell, vorgezogen)"** — wird zwischen Story 3.2 (done) und Story 3.3 Akku-Pool eingeplant. Sprint-Status: `backlog` bis 3.2 done, dann `ready-for-dev`.
- **Umbenannt: Story 5.1 → Story 5.1b „Dashboard-Hero + Euro-Wert + Responsive Navigation (Rest-Scope nach 5.1a)"** — Preamble ergänzt, AC-Semantik leicht angepasst („baut auf 5.1a auf"). Bleibt `backlog`.

### Artefakt-Konflikte

| Artefakt | Änderung | Aufwand |
|----------|----------|---------|
| `epics.md` | Story 5.1 splitten in 5.1a + 5.1b | ~15 min Edit |
| `sprint-status.yaml` | Alter 5-1-Key entfernen, zwei neue Keys (5-1a + 5-1b) einfügen | ~5 min Edit |
| `architecture.md` | **Keine** Änderung nötig — alle Bausteine (Polling, state_cache, control_cycles-Repo, LineChart) sind architektur-konform |
| `prd.md` | **Keine** Änderung — MVP-Scope wächst nicht, nur Reihenfolge ändert sich |
| `ux-design-specification.md` | **Keine** Änderung der Kern-Spec — Anti-Pattern-Liste UX-DR30 bleibt gültig, Tokens in `app.css` unverändert |

### Technischer Impact

- **Backend:** `StateCache` um Feld `current_mode` erweitern + Setter-Method. `/api/v1/control/state` erweitern um `current_mode`, `recent_cycles[]` (max 10 aus `control_cycles.list_recent`), `rate_limit_status[]` (aus `devices.last_write_at`). ~1–2 h Arbeit. Keine Migration nötig.
- **Frontend:** Neue Route `/live` (oder `/` als Default-Route bei commissioned devices), wiederverwendet `LineChart.svelte` aus 2.2. Modus-Chip + Mini-Zyklen-Liste als neue kleine Svelte-Komponenten. ~1 Tag.
- **Tests:** Pytest für Backend-Erweiterung, Vitest für Frontend-Route. Coverage-Ziel ≥ 90 % auf neuen Pfaden.
- **CI-Gates:** alle 4 bleiben grün, keine neue Dependency, keine neue Migration.
- **Risk:** Niedrig. Pure Reuse + kleiner Backend-Additive-Change. Kein Scope-Overlap mit 3.2.

---

## 3. Recommended Approach

**Option gewählt: Direct Adjustment (Story-Split in Epic 5)**

**Alternativen bewertet und verworfen:**

- ❌ Story 4.1 (Diagnose-Route) vorziehen: 4.1 liefert Liste, nicht Chart — matched den Wunsch nicht.
- ❌ Scope von Story 3.2 aufblähen: 3.2 ist als produktive Drossel-Policy scharf geschnitten; UI-Kram würde das Scope-Pflock (AC 1–14) sprengen.
- ❌ Neue Story in Epic 3 (z. B. 3.3-neu, 3.3–3.7 verschieben): semantisch eher UI → Epic 5 passt besser, und Umnummerieren von 3.3–3.7 würde Referenzen im architecture.md und sprint-status.yaml brechen.
- ❌ Rollback von 2.3 oder MVP-Review: kein Rückbau nötig, MVP-Scope bleibt konstant.

**Begründung der Wahl:**

- Kleinster Schnitt, der den Trigger tatsächlich erfüllt (Live-Diagramm).
- Reuse von bereits produktivem Code (`LineChart.svelte`, `/api/v1/control/state`).
- Epic 3 bleibt **nummerisch unverändert** — keine Story-ID-Wanderung, kein Reference-Breakage.
- Nahtlos erweiterbar: 5.1b baut später iterativ auf die Shell auf (Hero + Nav + Tokens).
- Zeitpunkt **nach 3.2**: stellt sicher, dass der Chart beim ersten Launch echte Drossel-Dispatches zeigt, kein leerer Skeleton-State.

**Effort-Schätzung:** ~2 Dev-Tage (1 Tag Backend + Frontend-Shell, 1 Tag Tests + Polishing).
**Risk:** Niedrig.
**Timeline-Impact:** +2 Dev-Tage im Epic-3/5-Slot, Beta-Launch-Ziel (9-Wochen-Fenster) bleibt machbar.

---

## 4. Detailed Change Proposals

### 4.1 Neue Story 5.1a (Insertion in `epics.md` direkt vor aktueller Story 5.1)

```markdown
### Story 5.1a: Live-Betriebs-View post-Commissioning (Mini-Shell, vorgezogen)

As a Nutzer direkt nach Klick auf „Aktivieren",
I want sofort sehen, was Solalex gerade regelt — ein Live-Diagramm, aktueller Modus, letzte Zyklen,
So that ich Vertrauen gewinne, dass die Regelung arbeitet, bevor Epic 4 (Diagnose) und Story 5.1b (Euro-Hero) fertig sind.

**Scope-Pflock:** Diese Story zieht aus Story 5.1 nur den Shell-Grundbestand vor: Route + Live-Chart + Modus-Chip + Mini-Zyklen-Liste. Kein Euro-Wert, kein Energy-Ring, keine Responsive-Nav, keine Charakter-Zeile, kein Bezugspreis-Stepper — das bleibt komplett in Story 5.1b. Ziel: ≤ 2 Dev-Tage. Zeitliche Einordnung: **nach Story 3.2 (Drossel produktiv)**, damit der Chart beim ersten Launch echte Dispatches zeigt.

**Acceptance Criteria:**

**Given** mindestens ein Device mit `commissioned_at IS NOT NULL`
**When** das Frontend die Ingress-Route öffnet
**Then** die Route `/live` (oder `/` als Default-Route für commissioned Setups) rendert — non-commissioned Setups bleiben im Wizard-Flow aus Epic 2

**Given** die Live-Betriebs-View
**When** sie rendert
**Then** die bereits existierende `LineChart.svelte`-Komponente (aus Story 2.2) rendert mit 5-s-Sliding-Window und drei Serien: Sensor-Wert (grid_meter via Shelly 3EM, Teal/Rot nach Vorzeichen), Target-Wert (letzter Dispatch `target_value_w` aus `control_cycles`, Blau), Readback-Wert (aktueller HW-State via `adapter.parse_readback`, Grau)

**Given** die View rendert
**When** sie den aktuellen Regel-Modus anzeigt
**Then** ein Modus-Chip oben zeigt einen von `Drossel | Speicher | Multi | Idle` mit semantischem Icon — Wert stammt aus dem erweiterten `/api/v1/control/state`-Feld `current_mode`

**Given** die View rendert
**When** sie die Mini-Zyklen-Liste zeigt
**Then** unter dem Chart werden die letzten 10 Zyklen aus `control_cycles` (via `list_recent(limit=10)`) in einer kompakten Liste dargestellt: Timestamp (relativ, z. B. „vor 3 s"), Source-Badge (`solalex` / `manual` / `ha_automation`), Target-Watts, Readback-Status-Badge (`passed` / `failed` / `vetoed`), Latenz

**Given** der Rate-Limiter blockiert einen Write
**When** die View den Status anzeigt
**Then** ein kleiner Hinweis „Nächster Write in X s" rendert — berechnet aus `devices.last_write_at + min_interval_s − now` (Datenfeld `rate_limit_status` im Polling-Payload)

**Given** das Polling
**When** es läuft
**Then** `/api/v1/control/state` wird im 1-s-Takt gepollt (bestehender Hook aus 2.2), kein WebSocket, keine externe Chart-Lib (CLAUDE.md-Stolpersteine)

**Given** noch keine `control_cycles`-Einträge (frischer Commissioning, Controller hat noch nicht dispatched)
**When** die View rendert
**Then** Chart zeigt Skeleton-Pulse (≥ 400 ms, UX-DR19) mit neutraler Zeile „Regler wartet auf erstes Sensor-Event." — kein Fehlerzustand, kein Spinner

**Given** das Backend
**When** `/api/v1/control/state` antwortet
**Then** der Payload enthält zusätzlich zu den bestehenden Feldern: `current_mode: "drossel" | "speicher" | "multi" | "idle"`, `recent_cycles: [...]` (max 10 Einträge, snake_case-JSON, keine Wrapper-Hülle — CLAUDE.md Regel 4), `rate_limit_status: [{ "device_id": int, "seconds_until_next_write": int | null }, ...]`

**Given** der Controller schließt einen Zyklus ab
**When** er `state_cache.update(...)` aufruft (Story 3.1 AC 11)
**Then** er ruft zusätzlich `state_cache.update_mode(self._current_mode)` — neues Feld `current_mode` in `StateCache` mit Setter-Methode

**Given** Unit-Tests
**When** sie laufen
**Then** neue Tests: `test_state_snapshot_exposes_current_mode` (Backend, pytest), `test_state_snapshot_includes_recent_cycles` (Backend, pytest), `test_live_view_renders_mode_chip_and_chart` (Frontend, vitest). Coverage ≥ 90 % auf neuen Backend-Code-Pfaden. Alle 4 Hard-CI-Gates grün (ruff, mypy --strict, pytest, SQL-Migrations-Ordering — keine neue Migration)

**Given** diese Story wird gekippt (Notfall-Fallback)
**When** der Fallback greift
**Then** nach Commissioning landet der User auf einem statischen Hinweis-Screen „Solalex regelt — detaillierte Ansicht folgt in v1.0" mit Link zur Diagnose-Route (Epic 4, sobald verfügbar)
```

### 4.2 Story 5.1 → 5.1b (Header + Preamble ändern, AC-Liste bleibt inhaltlich gleich)

**OLD-Header:**
```
### Story 5.1: Dashboard-Shell mit Responsive Navigation + Hero-Zone (Euro-Wert als 2-s-Kernaussage)
```

**NEW-Header:**
```
### Story 5.1b: Dashboard-Hero + Euro-Wert + Responsive Navigation (Rest-Scope nach 5.1a)
```

**Preamble (vor den AC eingefügt):**
```
**Preamble:** Story 5.1a (Live-Betriebs-View, vorgezogen) hat bereits den Shell-Grundbestand geliefert (Route, LineChart, Modus-Chip, Mini-Zyklen-Liste, Skeleton-State). Diese Story ergänzt die Hero-Zone mit Euro-Wert (56–72 px DM Sans), Bezugspreis-Transparenz-Overlay, Responsive Bottom-/Left-Nav mit Glass-Effect, Tastatur-Shortcuts, Footer. AC-Semantik „Hero-Zone in < 2 s sichtbar" bezieht sich auf die bestehende 5.1a-Route.
```

Die AC-Liste selbst bleibt inhaltlich unverändert — nur der Wording-Bezug „Dashboard lädt" wird implizit auf die 5.1a-Route umgebogen, sprich: wir ergänzen **keine** neue AC, und wir **streichen** keine. Bewusst minimaler Rename-Edit.

### 4.3 `sprint-status.yaml` — Key-Austausch in Epic 5

**OLD:**
```yaml
  # Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung
  epic-5: backlog
  5-1-dashboard-shell-mit-responsive-navigation-hero-zone-euro-wert-als-2-s-kernaussage: backlog
  5-2-bezugspreis-anpassung-inline-per-stepper: backlog
```

**NEW:**
```yaml
  # Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung
  epic-5: backlog
  # Key geändert: Sprint Change Proposal 2026-04-24 — Story 5.1 in 5.1a (vorgezogen) + 5.1b (Rest) gesplittet
  5-1a-live-betriebs-view-post-commissioning-mini-shell: backlog
  5-1b-dashboard-hero-euro-wert-responsive-navigation: backlog
  5-2-bezugspreis-anpassung-inline-per-stepper: backlog
```

Außerdem: `last_updated`-Kommentar am Dateianfang auf `2026-04-24 (Story 5.1 → 5.1a + 5.1b gesplittet via Sprint Change Proposal)` aktualisieren.

---

## 5. Implementation Handoff

**Scope-Klassifikation:** **Moderate**

### Wer macht was

| Agent / Rolle | Verantwortung |
|---------------|---------------|
| **Claude + Alex (in dieser Session)** | epics.md + sprint-status.yaml Edits durchführen. Sprint Change Proposal-Dokument committen (nach Alex-Freigabe). |
| **Alex (PM + Dev)** | Finale Approval dieser Proposal. Entscheidung über Zeitpunkt: Story 5.1a direkt nach 3.2-Merge `ready-for-dev`? |
| **Developer-Agent (`bmad-create-story`)** | Sobald 3.2 `done` ist: Story-File `5-1a-live-betriebs-view-post-commissioning-mini-shell.md` scaffolden mit vollständigem Task/Subtask-Breakdown. |
| **Developer-Agent (`bmad-dev-story`)** | Implementierung der Story nach dem Story-File. Reuse-Punkte: `LineChart.svelte` (2.2), `/api/v1/control/state` (2.2), `control_cycles.list_recent` (3.1), `StateCache` (bereits vorhanden, wird erweitert). |

### Success-Kriterien

- [ ] `epics.md` enthält Story 5.1a (neu) + Story 5.1b (umbenannt, mit Preamble).
- [ ] `sprint-status.yaml` zeigt `5-1a-...: backlog` und `5-1b-...: backlog`, alter 5-1-Key entfernt.
- [ ] Dieses Sprint Change Proposal liegt als `sprint-change-proposal-2026-04-24.md` unter `_bmad-output/planning-artifacts/`.
- [ ] Nach Merge von Story 3.2: Story 5.1a wird gescaffoldet und durchläuft den normalen `ready-for-dev → review → done`-Flow.
- [ ] Nach Merge von Story 5.1a: Beta-Tester öffnet Ingress nach Aktivieren und sieht binnen 2 s Live-Chart + Modus-Chip + letzte Zyklen.

### Was bleibt NICHT in Scope dieses Change-Proposals

- Weder `architecture.md` noch `prd.md` noch `ux-design-specification.md` werden angefasst.
- Keine Änderung an Story 2.2, 2.3, 3.1, 3.2 — alle bleiben unverändert.
- Epic 3 bleibt numerisch unverändert (3.1–3.7).
- Die Entwicklung von Story 5.1a **blockiert nicht** Story 3.2 (die kann parallel laufen, muss aber vor 5.1a gemergt sein).

---

## 6. Open Questions (für spätere Review)

- Soll die Live-Betriebs-View als Default-Route (`/`) nach Commissioning einziehen, oder als dedizierter `/live`-Pfad mit Button „Live sehen" auf einer Post-Aktivierung-Landing? → **Default-Route `/` bei commissioned, `/setup` nur wenn kein Device commissioned** (Entscheidung in Story-Scaffold).
- Braucht die Mini-Zyklen-Liste einen expand-Indikator auf 100 Zyklen (überlappt mit 4.1)? → **Nein**, bewusst klein; 4.1 liefert die vollständige Diagnose-Route später.
- Wie verhält sich die View bei `test_in_progress=true` (Story 2.2 Lock)? → **View soll `test_in_progress=true` erkennen und eine Infoline zeigen „Funktionstest läuft — Regelung pausiert"** (Subtask-Detail für Story-Scaffold).

---

## 7. Approval-Log

| Datum | Entscheider | Entscheidung |
|-------|-------------|--------------|
| 2026-04-24 | Alex | Trigger bestätigt: UI-Visibility-Lücke (kein Diagramm) |
| 2026-04-24 | Alex | Mode: Incremental |
| 2026-04-24 | Alex | Platzierung: Story 5.1 reduziert vorziehen (Split 5.1a + 5.1b) |
| 2026-04-24 | Alex | Zeitpunkt: nach Story 3.2 |
| 2026-04-24 | Alex | Proposals #1–#3 approved, direkt ready-for-dev (ohne separate Story-Validierung) |

---

**Status nach diesem Dokument:** approved in-principle, wartet auf finale Artefakt-Commits (`epics.md` + `sprint-status.yaml`) durch Alex.
