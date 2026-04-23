# Sprint Change Proposal — 2026-04-23 (Dark-Mode-Drop)

**Workflow:** `/bmad-correct-course`
**Trigger:** User-Request 2026-04-23 („Dark Mode brauchen wir nicht, in Story 1.4 oder so anpassen.")
**Modus:** Batch
**Verfasser:** Dev (Amelia, via Claude Opus 4.7)
**Status:** Approved durch Alex am 2026-04-23

---

## 1. Issue Summary

### Problem-Statement

Solalex soll in v1 **keinen Dark-Mode** mehr anbieten. Die UI rendert nur im Light-Look — unabhängig vom HA-Theme-Signal. Kein `[data-theme="dark"]`-Override, kein MutationObserver, keine modus-spezifische Saturation, keine Dual-Token-Palette.

### Kontext zur Discovery

- **Wann:** 2026-04-23, während Story 1.4 und Story 1.6 in `review` stehen (Commit `9d31cd6` bündelt beide, Dark-Mode-Code bereits gemerged).
- **Wo:** User-Entscheidung ohne konkreten Bug-Trigger — Scope-Reduktion.
- **Motivation (aus Gespräch):** Dark-Mode ist ein Cost-Center ohne klaren MVP-Nutzen. v1-Beta-Launch in 9 Wochen, Solo-Dev-Support — jeder Dark-Mode-Fix (Kontrast-Verifikation, Theme-Sync mit HA, Dark-Token-Pflege über Wizard/Dashboard) kostet Zeit, die Epic 2/3/5 braucht.

### Kategorisierung

**Strategic Scope-Reduction** — im Geist des Amendments 2026-04-22, das bereits 15 „Was verwenden wir NICHT in v1"-Punkte gesetzt hat. Dark-Mode wird der 16. Punkt.

### Evidenz

| Datei | Zeile(n) | Dark-Mode-Bezug |
|---|---|---|
| `_bmad-output/planning-artifacts/prd.md` | 640 | FR43 „Dark/Light-Mode-Umschaltung ohne Bruch der ALKLY-Farbidentität" |
| `_bmad-output/planning-artifacts/prd.md` | 688 | NFR26 Designqualität-Bullet „HA-Dark-/Light-Mode-Unterstützung" |
| `_bmad-output/planning-artifacts/ux-design-specification.md` | 31, 56, 112, 147 | Executive-Summary-Satz, Key Challenge #2, Platform-Strategy-Zeile, Moment 6 |
| `_bmad-output/planning-artifacts/ux-design-specification.md` | — (UX-DR1, UX-DR7, UX-DR27) | Design-Rules zu modus-spezifischer Saturation, Theme-Adaption, beider-Modus-WCAG |
| `_bmad-output/planning-artifacts/architecture.md` | 161, 375, 391 | Styling-Bullet, `theme`-Store-Feld, Design-Token-Layer mit `[data-theme="dark"]` |
| `_bmad-output/planning-artifacts/epics.md` | 562, 610–643, 367 | Story 1.4 AC, Story 1.6 Titel + 3 ACs, FR43-Mapping |
| `_bmad-output/implementation-artifacts/1-4-….md` | AC 2, Task 2, Token-Tabelle Dark, Review-Findings „Dark-Akzent-Hex" | Dark-Varianten im Token-Layer |
| `_bmad-output/implementation-artifacts/1-6-….md` | Titel, ACs 2/3/6, Task 2, Completion Notes | Gesamte Theme-Live-Adaption |
| `frontend/src/App.svelte` | 6, 32–58, 69–90, 93 | `isDarkTheme`-State, `resolveThemeMode`, `applyTheme`, MutationObserver |
| `frontend/src/app.css` | 67–74 | `:root[data-theme='dark']` Override-Block |

**Fußnote:** `CLAUDE.md` enthält keine Dark-Mode-Regel — keine Änderung nötig.

---

## 2. Impact Analysis

### Epic-Impact

- **Epic 1** bleibt in-progress. Story 1.4 + 1.6 (beide `review`) bekommen Content-Updates. Kein Epic neu, kein Epic gestrichen.
- **Epic 5 (Dashboard)** entlastet: Dashboard-Stories müssen nicht mehr Dark-Token-Konsistenz gewährleisten.
- **Epic 2/7 (Wizard/Lizenz)** entlastet: keine Theme-Adaption im Wizard- und Kauf-Flow nötig.

### Story-Impact

| Story | Status | Änderung |
|---|---|---|
| **1.4** — Design-System-Foundation | review | AC 2 umformulieren („Token-Layer ist Light-Mode-Single-Source"); Task 2 Dark-Overrides streichen; Dark-Token-Tabelle + Dark-Hex-Change-Log-Zeile entfernen; Review-Findings „Dark-Mode-Akzent-Hex weicht ab" wird obsolet → als Defer/Dismissed markieren |
| **1.6** — bisher „Dark/Light-Adaption + Empty-State" | review | **Rename**: „HA-Ingress-Frame mit statischem Light-Look und Empty-State". ACs 2 + 3 + 6 streichen; Tasks 2 (Theme-Adaption-Subtasks) neu formulieren auf „Light-only Token-Referenzen"; Review-Finding „MutationObserver-Feedback-Loop" wird obsolet |
| **1.5, 1.7** | done | kein Impact |
| **Epic 2–7** | backlog | kein AC-Text enthält Dark-Mode-Forderung → no-op |

### Artifact-Konflikte

- **PRD FR43** wird umformuliert: „UI ist im HA-Ingress-Frame eingebettet und rendert konsistent im Light-Look (keine HA-Theme-Adaption in v1)."
- **PRD NFR26**-Bullet „HA-Dark-/Light-Mode-Unterstützung" entfernt.
- **UX-Spec** Key Challenge #2 ersetzt durch expliziten Cut-Hinweis; Moment 6 entfernt (wird zu „UI-Konsistenz über Sessions hinweg" oder gestrichen); UX-DR1/DR7/DR27 entsprechend gekürzt (WCAG-AA nur noch für Light-Mode).
- **Architecture §161 + §375 + §391** auf Light-only korrigiert; `theme`-Store-Eintrag gestrichen; `[data-theme="dark"]`-Selector-Referenz raus.
- **Epics.md** Story 1.4 AC-Bullet „Dark-Mode-Varianten … getrennt definiert" raus; Story 1.6 Titel + 3 Dark/Light-ACs raus.
- **Anti-Pattern-Liste in CLAUDE.md** bekommt eine zusätzliche Zeile: „Wenn Du `[data-theme='dark']`-Overrides oder einen Theme-Observer baust — STOP. Light-only in v1."

### Technical Impact (Code)

- `frontend/src/App.svelte`: MutationObserver, `applyTheme`, `resolveThemeMode`, `isDarkTheme`, `matchMedia`-Subscribe, `data-theme-mode`-Attribut raus. Verbleibende Funktionalität: Hash-Route-Sync + Backend-Ping.
- `frontend/src/app.css`: Block `:root[data-theme='dark']` (Zeilen 67–74) entfernen. Light-Token-Palette bleibt unverändert.
- Keine Template-Änderungen in der `<main>`-Markup-Struktur.

---

## 3. Recommended Approach

**Gewählter Pfad: Direct Adjustment + Partial Rollback.**

- **Direct Adjustment** in den Planning-Artefakten (PRD/UX/Architecture/Epics/CLAUDE.md) + den beiden `review`-Stories (1.4/1.6).
- **Partial Rollback** des Dark-Mode-Codes aus Commit `9d31cd6` (App.svelte + app.css). Kein `git revert` — gezielter, chirurgischer Patch, damit die restlichen 1.4-/1.6-Inhalte (Empty-State, Footer, Tokens, DM-Sans-Pipeline) unberührt bleiben.

### Begründung

- **Stories in `review`, nicht `done`** — günstigster Zeitpunkt, den Scope zu kürzen. Danach wird es teurer (Wizard/Dashboard-Stories bauen dann auf Dark-Token-Annahmen auf).
- **Review-Findings in Story 1.4 obsolet** — zwei der drei „Decision"-Einträge (Dark-Akzent-Hex, MutationObserver-Loop) verschwinden mit dem Rollback.
- **Timeless-Tokens-Prinzip** (UX-Spec §„Anti-Patina, Anti-Bling") bleibt gewahrt — Light-Mode-Tokens sind schon timeless, der Dark-Mode-Block war die eigentliche Variabilitätsquelle.
- **Konsistent mit Amendment 2026-04-22-Philosophie** — 15 „Kein X in v1"-Cuts sind bereits dokumentiert, Dark-Mode wird der 16.

### Effort + Risk

- **Effort:** ~90 min (Docs + Stories + Code-Rollback + Build-Verifikation).
- **Risk:** niedrig — Light-Mode-Tokens werden nicht angefasst, nur Dark-Mode-Overhead entfernt; Build/Test-Pipeline deckt Regression ab.
- **Timeline-Impact:** keine Verschiebung, eher Zeitgewinn (ein Review-Finding weniger in Story 1.4, keine Manual-QA für Theme-Wechsel in 1.6 nötig).

---

## 4. Detailed Change Proposals

Alle Änderungen werden in einem einzigen Durchgang umgesetzt (Batch-Mode). Diff-Highlights:

### 4.1 `_bmad-output/planning-artifacts/prd.md`

- **FR43** (Zeile 640): Formulierung auf „UI rendert im HA-Ingress-Frame in einem statischen Light-Look; keine Dark-Mode-Adaption in v1 (Amendment 2026-04-23)".
- **NFR26 Designqualität-Bullet** (Zeile 688): Zeile „HA-Dark-/Light-Mode-Unterstützung ohne Bruch der ALKLY-Farbidentität" ersatzlos streichen.

### 4.2 `_bmad-output/planning-artifacts/ux-design-specification.md`

- Executive Summary Zeile 31: „Sie muss sich in HA-Dark/Light-Mode einfügen, ohne die ALKLY-Identität zu verlieren." → „Sie rendert konsistent im ALKLY-Light-Look (Dark-Mode gestrichen, Amendment 2026-04-23)."
- Key Design Challenge #2 (Zeile 56) durch Cut-Hinweis ersetzen.
- Platform-Strategy-Tabelle Zeile 112: Zelle „HA-Dark/Light-Mode respektieren …" → „Statischer Light-Look, keine HA-Theme-Adaption (v1-Cut 2026-04-23)".
- Moment 6 (Zeile 147) ersatzlos streichen (Momente neu nummerieren? → nein, Liste bleibt stabil, Moment 6 entfällt; Moment 1–5 bleiben).
- UX-DR1/DR7/DR27: Dark-Referenzen entfernen oder Regel ins Backlog vertagen (explizit mit „v1-Cut 2026-04-23"-Vermerk).

### 4.3 `_bmad-output/planning-artifacts/architecture.md`

- Styling-Solution-Bullet Zeile 161: „Dark/Light-Mode via HA-Theme-Adaption + Token-Layer mit modus-spezifischer Saturation" ersetzen durch „Light-only Token-Layer (Dark-Mode gestrichen, Amendment 2026-04-23)".
- State-Management Zeile 375: Store-Eintrag `theme — HA-Dark/Light-Signal` ersatzlos streichen.
- Design-Token-Layer Zeile 391: Satz „ALKLY-Tokens … in `:root` + modus-spezifisch in `[data-theme="dark"]`. HA-Theme-Signal triggert Attribut-Setzen am `<html>`-Tag." ersetzen durch „ALKLY-Tokens in `:root`. Kein modus-spezifischer Override in v1 (Amendment 2026-04-23)."

### 4.4 `_bmad-output/planning-artifacts/epics.md`

- Story 1.4 AC-Block (Zeile 562): Bullet „Dark-Mode-Varianten (Teal mit Glow) und Light-Mode-Varianten (Rot mit Sättigung) sind getrennt definiert" streichen.
- Story 1.6 Titel (Zeile 610): „HA-Ingress-Frame mit Dark/Light-Adaption und Empty-State" → „HA-Ingress-Frame mit statischem Light-Look und Empty-State".
- Story 1.6 Story-Statement (Zeile 613): „in HA-Theme-konformem Dark- oder Light-Mode" → „im ALKLY-Light-Look".
- Story 1.6 ACs (Zeilen 623–631 + 641–643): 3 Dark/Light-AC-Blöcke ersatzlos streichen.
- FR43-Mapping-Zeile (Zeile 367): „HA-Ingress-Frame mit Dark/Light-Mode-Adaption" → „HA-Ingress-Frame mit statischem Light-Look".

### 4.5 `CLAUDE.md` — Stolpersteine

Zwei zusätzliche Einträge in der Stolperstein-Liste:

- „Wenn Du `[data-theme='dark']`-Overrides oder einen Theme-Observer in Frontend-Code einbaust — **STOP**. Dark-Mode gestrichen (Amendment 2026-04-23), Light-only in v1."
- „Wenn Du einen `theme`-Store oder HA-Theme-Subscriber planst — **STOP**. Siehe Amendment 2026-04-23."

Zusätzlich in „Was explizit NICHT verwendet wird"-Sektion: neuer Bullet „Kein Dark-Mode / kein `[data-theme='dark']`-Override in v1 (Amendment 2026-04-23)."

### 4.6 `_bmad-output/implementation-artifacts/1-4-…-design-system-foundation…`.md

- AC 2 umformulieren: „Light-Mode-Token-Set als einzige Single-Source; kein `[data-theme='dark']`-Block."
- Task 2 Subtasks: Dark-Override-Zeilen streichen, Kontrast-Verifikations-Hinweis auf Light-only begrenzen.
- Token-Tabelle Dark-Varianten: ersatzlos streichen (plus Hinweis: „Dark-Mode gestrichen, siehe Sprint-Change-Proposal 2026-04-23").
- Review-Findings: Decision-Eintrag „Dark-Mode-Akzent-Hex weicht vom Spec-Richtwert ab" → als **Defer** / **Dismissed (obsolet durch Sprint-Change 2026-04-23)** markieren.

### 4.7 `_bmad-output/implementation-artifacts/1-6-…ha-ingress-frame…`.md (Rename)

- Filename-Rename: `1-6-ha-ingress-frame-mit-dark-light-adaption-und-empty-state.md` → `1-6-ha-ingress-frame-mit-light-look-und-empty-state.md`.
- Story-Titel + User-Story-Statement auf Light-only.
- ACs 2, 3, 6 ersatzlos streichen; AC 1 / 4 / 5 behalten und neu nummerieren (1–4).
- Task 2 Subtasks: „Theme-Adaption über bestehende Token-Single-Source verankern" → „Light-Token-Verwendung in Ingress-Shell verifizieren".
- Task 5 Manual-QA: Theme-Wechsel-Check streichen.
- Review-Findings (MutationObserver-Loop, FOUC im Dark-Mode, `classHint.includes('dark')`, Dark-Tokens-nicht-auf-body) → als **Dismissed (obsolet durch Sprint-Change 2026-04-23)** markieren.
- Change-Log-Zeile für das Amendment ergänzen.

### 4.8 `_bmad-output/implementation-artifacts/sprint-status.yaml`

- Key `1-6-ha-ingress-frame-mit-dark-light-adaption-und-empty-state` → `1-6-ha-ingress-frame-mit-light-look-und-empty-state`. Status bleibt `review`.
- `last_updated`-Header-Kommentar-Zeile und `last_updated`-Feld aktualisieren.

### 4.9 Code-Rollback

**`frontend/src/App.svelte`:**

- `isDarkTheme`-State, `resolveThemeMode()`, `applyTheme()` entfernen.
- `onMount`: `applyTheme()`-Call, `matchMedia`-Subscribe, `MutationObserver` entfernen; Cleanup entsprechend reduziert.
- `<main>`-Attribut `data-theme-mode={isDarkTheme ? 'dark' : 'light'}` entfernen.
- Imports (`$state`) bleiben (`backendStatus`/`currentRoute` brauchen es noch).

**`frontend/src/app.css`:**

- Block `:root[data-theme='dark'] { … }` (Zeilen 67–74) ersatzlos entfernen.
- Kein weiterer Token-Umbau. Light-Palette bleibt.

---

## 5. Implementation Handoff

**Change-Scope: Moderate.**

- Planning-Artefakte (4 Dokumente) + Implementation-Stories (2) + CLAUDE.md + Frontend-Code (2 Files) + sprint-status.yaml.
- Kein Architektur-Replan nötig, kein neuer Epic, kein PM-/Architect-Involvement.

**Handoff-Empfänger:** Dev-Agent (Amelia) — direkt im Anschluss an Approval (Batch-Run im selben Turn).

**Success-Kriterien:**

1. `grep -riE "data-theme|dark-mode|HA-Dark|Dark/Light" _bmad-output/planning-artifacts/ _bmad-output/implementation-artifacts/` liefert nur noch Hinweise auf den Amendment-Cut (keine positiven Dark-Mode-Aussagen).
2. `grep -riE "data-theme|MutationObserver|applyTheme|resolveThemeMode" frontend/src/` → 0 Treffer.
3. `cd frontend && npm run build && npm run check && npm run lint` exit 0.
4. `cd backend && pytest -q` exit 0 (keine Regression).
5. Story 1.4 + 1.6 bleiben `review` (Code-Review-Commit folgt separat nach Alex' Freigabe).

**Nicht-Ziel:** Git-Commit wird in diesem Workflow NICHT gemacht. Alex entscheidet manuell, wann commited wird (CLAUDE.md Git-Regel).

---

## 6. Open Items / Nicht geklärt

- Soll das Amendment auch einen Eintrag in `architecture.md` „Revision-Log" bekommen? (architecture.md-Autorität-Prinzip legt es nahe.) → Wird umgesetzt, kurzer Eintrag unter den 2026-04-22-Amendment-Block.
- Soll der Moment-6-Shift in der UX-Spec die Nummerierung intakt halten (Moment 6 = leer/strike) oder Momente 1–5 belassen und Moment 6 einfach entfernen? → **Entscheidung**: Einfach entfernen, 5 Momente reichen.
