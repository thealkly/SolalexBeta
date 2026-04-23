# Sprint Change Proposal — 2026-04-23

**Workflow:** `/bmad-correct-course`
**Trigger-Story:** Story 1.2 (Landing-Page Voraussetzungs-Hinweis + HA-Versions-Range), Review-Patch 2026-04-23 (KISS-Cut)
**Modus:** Batch
**Verfasser:** Dev (Amelia, via Claude Opus 4.7)
**Status:** Draft — Approval ausstehend

---

## 1. Issue Summary

### Problem-Statement

Die Solalex-Doku beschreibt die unterstützten Home-Assistant-Plattformen **uneinheitlich und teilweise falsch**. Korrekt ist: **Solalex unterstützt ausschließlich Home Assistant OS (HAOS)**. Home Assistant Supervised, Home Assistant Container und Home Assistant Core sind nicht unterstützt.

In Story 1.2 wurde diese Beschränkung am 2026-04-23 als **KISS-Cut-Amendment** im Review beschlossen und in den umsetzungsnahen Artefakten (Story-AC, `addon/DOCS.md`, `addon/CHANGELOG.md`, `docs/landing/voraussetzungen.md`, `README.md`) sauber umgesetzt. **Aber:** PRD-FR2, mehrere PRD-Sektionen, Epic-1-FR2-Inventory, Epic-1-Story-1.1-AC, Epic-1-Story-1.2-AC und Story 1.1 selbst tragen weiterhin die alte Formulierung „HA OS oder Supervised" bzw. „best-effort ohne Support". Das produziert Drift zwischen Spec-Schicht und Implementierungs-Schicht.

### Kontext zur Discovery

- **Wann:** Review-Cycle Story 1.2 am 2026-04-23 (Acceptance-Auditor-Layer hat den Konflikt zwischen Story-Spec und PRD-FR2 als „[Review][PRD-Amendment]" markiert).
- **Wo:** `_bmad-output/implementation-artifacts/1-2-landing-page-voraussetzungs-hinweis-ha-versions-range.md` Zeile 78 (Action-Item an `/bmad-correct-course` delegiert).
- **Aktueller Auslöser:** User-Request, den Drift jetzt nachzuziehen.

### Kategorisierung

**Misunderstanding of original requirements** (kombiniert mit **strategic scope reduction**):

- Originaler PRD-Wortlaut (FR2, Journey 3, Launch-Gates) zielte auf „HA OS oder Supervised" — angelehnt an die Reichweiten-Argumentation aus `docs/Solalex-Deep-Research.md` (~85 % aller HA-Nutzer).
- Im Story-1.2-Review wurde entschieden, die Support-Matrix zu vereinfachen („KISS-Cut"): nur HAOS, weil Solo-Dev-Support für vier Plattform-Permutationen unrealistisch ist und HAOS die einzige Konfiguration ist, die Solalex überhaupt verlässlich automatisiert testen kann (Add-on-Store-Install-Warning via `homeassistant:`-Pin wirkt nur für Supervisor-basierte Hosts; HA Container/Core haben strukturell keinen Add-on-Flow).
- Diese Entscheidung wurde nur in den Story-1.2-Artefakten und in den Add-on-Manifest-/Doku-Dateien nachgezogen, nicht in der PRD/Epic-Schicht.

### Evidenz

| Datei | Zeile | Veraltete Formulierung | Inhalts-Kontext |
|-------|-------|------------------------|------------------|
| `_bmad-output/planning-artifacts/prd.md` | 214 | `Landing-Hinweis „Benötigt HA OS oder Supervised" prominent` | Launch-Gates |
| `_bmad-output/planning-artifacts/prd.md` | 268 | `„Benötigt Home Assistant OS oder Supervised."` | Journey 3 (Nils) Opening Scene |
| `_bmad-output/planning-artifacts/prd.md` | 294 | `Landing-Page-Check für HA-OS/Supervised` | Journey Requirements Summary |
| `_bmad-output/planning-artifacts/prd.md` | 578 | `„HA OS oder Supervised"` | **FR2** |
| `_bmad-output/planning-artifacts/epics.md` | 40 | `„HA OS oder Supervised"` | **FR2** Inventory |
| `_bmad-output/planning-artifacts/epics.md` | 460 | `eine HA-Instanz mit HA OS oder Supervised` | Story 1.1 AC |
| `_bmad-output/planning-artifacts/epics.md` | 501 | `„Benötigt Home Assistant OS oder Supervised"` | Story 1.2 AC 1 |
| `_bmad-output/planning-artifacts/epics.md` | 505 | `HA Container und HA Core … „nicht supported, best-effort ohne Support"` | Story 1.2 AC 2 (Supervised fehlt + zu weich) |
| `_bmad-output/implementation-artifacts/1-1-add-on-skeleton-...md` | 16 | `eine HA-Instanz mit HA OS oder Supervised` | AC 2 (Story-Status: done) |
| `_bmad-output/implementation-artifacts/1-2-landing-page-...md` | 64 | `Voraussetzungen: Home Assistant OS oder Supervised. Siehe …` | Task 4 Beschreibung |
| `_bmad-output/implementation-artifacts/1-2-landing-page-...md` | 69 | `„Benötigt HA OS oder Supervised"-Kernzeile` | Task 5 Smoke-Test-Beschreibung |

**Korrekt umgesetzt** (kein Edit nötig):
- `README.md` (Root, Z. 14)
- `addon/config.yaml` (Z. 3–4, `homeassistant:`-Pin)
- `addon/DOCS.md` (Z. 16–17, 23–28)
- `addon/CHANGELOG.md` (Z. 12–15)
- `docs/landing/voraussetzungen.md` (Z. 9, 11–16)
- `_bmad-output/planning-artifacts/architecture.md` (keine Plattform-Erwähnungen — plattform-neutral)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (keine Plattform-Erwähnungen)

---

## 2. Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 1 (Add-on Foundation & Branding) | in-progress | **Doku-Update**: FR2-Inventory, Story 1.1 AC, Story 1.2 AC 1+2. Kein funktionaler Scope-Change. |
| Epic 2–7 | backlog | **Kein Impact**. Keine Plattform-Erwähnungen in nachgelagerten Epics. |

**Keine** Epics werden hinzugefügt, entfernt, neu-nummeriert oder reordered. **Keine** Stories werden hinzugefügt oder entfernt. Story-Reihenfolge unverändert.

### Story Impact

| Story | Status | Impact | Aktion |
|-------|--------|--------|--------|
| 1.1 Add-on Skeleton | done | AC-2-Wording veraltet | Doku-Nachzug am AC + Change-Log-Eintrag. **Code unverändert** (HA-Add-ons laufen strukturell nur unter Supervisor; Story 1.1 hat keinen Plattform-Check implementiert, weil das Solalex-Add-on durch das HA-Add-on-Konzept selbst auf HAOS/Supervised beschränkt ist und Story 1.2 die Restriktion auf HAOS-only via `homeassistant:`-Pin + DOCS hart deklariert). |
| 1.2 Landing-Page + HA-Versions-Range | in-progress | Bereits größtenteils auf KISS-Cut umgesetzt; zwei Resttext-Stellen (Task 4, Task 5) noch veraltet | Wording-Edits + nach Apply: Status `in-progress → review → done`. Review-Item „[Review][PRD-Amendment]" wird abgehakt. |
| 1.3 HA WebSocket Foundation | done | **Kein Impact** (nur ha_version-JSON, keine Plattform-Erwähnung) | — |
| 1.4–1.7, Epic 2–7 Stories | backlog | **Kein Impact** | — |

### Artifact Conflicts

| Artefakt | Konflikt | Update-Typ |
|----------|----------|------------|
| **PRD** (`prd.md`) | FR2 + 3 narrative Stellen (Launch-Gates, Journey 3, Journey-Summary) | Wording-Edit (4 Stellen) |
| **Epics** (`epics.md`) | FR2 + Story 1.1 AC + Story 1.2 AC 1+2 | Wording-Edit (4 Stellen) |
| **Story 1.1** (impl-artifact) | AC 2 + Change-Log-Eintrag | Wording-Edit (1 Stelle) + neuer Change-Log-Eintrag |
| **Story 1.2** (impl-artifact) | Task 4 + Task 5 Beschreibungstexte | Wording-Edit (2 Stellen) |
| **Architecture** (`architecture.md`) | **Kein Konflikt** | — |
| **UX-Spec** (`ux-design-specification.md`) | **Kein Konflikt** | — |
| **Sprint-Status** (`sprint-status.yaml`) | Kein struktureller Konflikt; nach Apply: Story-1.2-Status auf `review` bzw. `done` setzen | Status-Update (nicht Re-Plan) |
| **`docs/Solalex-Deep-Research.md`** | Z. 21, 41, 296–299 nennen „OS + Supervised ~85 %" als Marktargument | **Defer** — Research-Snapshot (kein Spec-Doc), kann mit Stamp „vor 2026-04-23 KISS-Cut" markiert werden, ist aber nicht load-bearing |
| **`docs/Archiv …`** | Veraltete Bezüge | **Defer** — Archiv-Material, keine Aktion |

### Technical Impact

- **Code-Impact: Null.** Solalex-Code (Backend, Frontend, Add-on-Manifest) ist bereits HAOS-konform. Der `homeassistant: "2026.4.0"`-Pin in `addon/config.yaml` (aus Story 1.2) deklariert die einzige technische Restriktion, die der HA-Supervisor durchsetzt.
- **CI-Impact: Null.** Die 4 CI-Gates (Ruff+MyPy+Pytest, ESLint+svelte-check+Prettier+Vitest, Egress-Whitelist, SQL-Migration-Ordering) sind unabhängig von der Plattform-Frage.
- **Deployment-/Infrastruktur-Impact: Null.** Kein Manifest-Bump nötig. CHANGELOG-Eintrag in `addon/CHANGELOG.md` für die OS-only-Restriktion ist bereits vorhanden (aus Story 1.2).
- **Tester-Impact: Minimal.** Beta-Tester-Akquise muss explizit nur HAOS-Hosts adressieren — das ist ohnehin unsere primäre Zielgruppe (Marstek-Micha, Neugier-Nils u. a. laufen alle auf RPi-4-HAOS gemäß User-Journeys).

### Risiko-/Stakeholder-Impact

- **Reichweite-Argument** aus `docs/Solalex-Deep-Research.md` (~85 % aller HA-Nutzer) reduziert sich strukturell auf den HAOS-Anteil. Schätzwert (laut Research-Doc): **~70–85 % aller HA-Nutzer auf HAOS** — die Kernzielgruppe Solalex (DACH-Consumer-PV mit RPi-4-HA-Setups) ist davon disproportional betroffen → praktisch keine Marktverengung.
- **Beta-Tester (20 Stk geplant):** Pre-Auswahl muss ein Filter-Item „läuft auf HAOS" haben. Kein neues Risiko, nur expliziter Filter.
- **Future v3+ „Solalex Lite (Custom Integration für HA Container/Core)"** in `prd.md` Z. 238 bleibt **unverändert** als langfristige Vision für die ausgeschlossenen Plattformen — diese Zeile wird **nicht** angefasst.

---

## 3. Recommended Approach

### Gewählter Pfad: **Option 1 — Direct Adjustment**

Alle 11 identifizierten Edits sind **reine Wording-Korrekturen in der Spec-/Doku-Schicht**. Der Code ist bereits konform, kein Rollback erforderlich, kein MVP-Cut nötig. Direct Adjustment ist die einzige rationale Option.

### Path-Forward-Evaluation (vollständig)

| Option | Bewertung | Entscheidung |
|--------|-----------|--------------|
| **Option 1: Direct Adjustment** (Wording-Edits in PRD/Epics/Stories) | Effort: **Low** (ca. 11 String-Edits, kein Code). Risk: **Low** (Doku-Drift wird abgebaut, keine Verhaltensänderung). Timeline-Impact: **0** (Sprint läuft weiter). | ✅ **Gewählt** |
| Option 2: Potential Rollback (z. B. Story 1.2 zurück auf „OS oder Supervised") | Würde den bewussten KISS-Cut zurücknehmen und vier Plattform-Permutationen für Solo-Dev-Support reaktivieren. Effort: hoch (DOCS, Landing-Page, Tester-Hinweise alle revertieren). Risk: hoch (überfordert Solo-Dev-Support; Tester-Triage explodiert). | ❌ Verworfen |
| Option 3: PRD MVP Review (Scope-Reduktion über HAOS-only hinaus) | Es gibt keinen Trigger für weitere MVP-Cuts. Die KISS-Reduktion wirkt bereits scope-reduzierend in die richtige Richtung. | ❌ Verworfen — kein Anlass |

### Justification

- **Implementierungsaufwand:** ~30 Minuten konzentriertes Editieren (11 Wording-Stellen + Change-Log-Eintrag in Story 1.1 + Status-Update in `sprint-status.yaml`).
- **Technisches Risiko:** Null. Code unverändert, CI unverändert, Deployment unverändert.
- **Team-Momentum:** Story 1.2 kann nach Apply von `in-progress` auf `done` gesetzt werden — Sprint-Velocity profitiert. Story 1.1 bleibt `done` (Doku-Patch ändert keinen Code).
- **Long-Term-Sustainability:** Drift zwischen PRD/Epics/Story-Specs wird **eliminiert**. Künftige Reviewer und Dev-Agents lesen einheitliche Anforderungen.
- **Stakeholder-Erwartungen:** KISS-Cut entspricht der Solo-Dev-Realität. Die Reichweiten-Frage ist im Worst Case eine Frage des User-Funnels, nicht der Spec-Korrektheit — und die Spec ist nun realistisch.

### Effort/Risk Estimate

- **Effort:** Low (≤ 30 min Doku-Editing + Status-Update + optional Change-Log-Schreiben in Story 1.1).
- **Risk:** Low (Doku-only, kein Code, kein Deploy).
- **Timeline-Impact:** Keiner. Sprint läuft normal weiter; Story 1.2 entblockt sofort.

---

## 4. Detailed Change Proposals

### 4.A — PRD (`_bmad-output/planning-artifacts/prd.md`)

#### Edit A1 — Launch-Gates (Zeile 214)

**Section:** Measurable Outcomes → Launch-Gates

**OLD:**
```
- Landing-Hinweis „Benötigt HA OS oder Supervised" prominent
```

**NEW:**
```
- Landing-Hinweis „Benötigt Home Assistant OS" prominent
```

**Rationale:** Launch-Gate spiegelt die wörtliche Landing-Page-Kernzeile wider. Die wurde im KISS-Cut auf HAOS-only reduziert; Launch-Gate folgt nach.

---

#### Edit A2 — Journey 3 Neugier-Nils, Opening Scene (Zeile 268)

**Section:** User Journeys → Journey 3: Neugier-Nils

**OLD:**
```
Oben steht gleich: „Benötigt Home Assistant OS oder Supervised." Er prüft HA → Einstellungen → „Raspberry Pi 4, HA OS". Passt.
```

**NEW:**
```
Oben steht gleich: „Benötigt Home Assistant OS." Er prüft HA → Einstellungen → „Raspberry Pi 4, HA OS". Passt.
```

**Rationale:** Narrative Konsistenz mit der echten Landing-Page-Kopie. Nils-Journey funktioniert weiterhin (er läuft ohnehin auf HAOS).

---

#### Edit A3 — Journey Requirements Summary (Zeile 294)

**Section:** Journey Requirements Summary → Setup & Onboarding

**OLD:**
```
- **Setup & Onboarding:** Zwei-Pfade-Wizard (Hoymiles/OpenDTU · Marstek Venus) · Auto-Detection für OpenDTU, Shelly 3EM, Marstek Venus · Live-Werte neben jedem Sensor · Funktionstest als Lern-Moment und Readback-Validierung · Landing-Page-Check für HA-OS/Supervised. Anker + Generic-Pfad + Blueprint-Import folgen v1.5.
```

**NEW:**
```
- **Setup & Onboarding:** Zwei-Pfade-Wizard (Hoymiles/OpenDTU · Marstek Venus) · Auto-Detection für OpenDTU, Shelly 3EM, Marstek Venus · Live-Werte neben jedem Sensor · Funktionstest als Lern-Moment und Readback-Validierung · Landing-Page-Check für Home Assistant OS. Anker + Generic-Pfad + Blueprint-Import folgen v1.5.
```

**Rationale:** Capability-Summary spiegelt die KISS-Cut-Restriktion wider.

---

#### Edit A4 — FR2 (Zeile 578)

**Section:** Functional Requirements → Installation & Lizenz → FR2

**OLD:**
```
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „HA OS oder Supervised" vor dem Download-Schritt.
```

**NEW:**
```
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „Home Assistant OS" vor dem Download-Schritt. Home Assistant Supervised, Home Assistant Container und Home Assistant Core sind ausdrücklich nicht unterstützt (Amendment 2026-04-23, KISS-Cut: Support-Matrix auf eine known-good Host-Konfiguration beschränkt).
```

**Rationale:** Kern-Requirement der gesamten Plattform-Frage. Zusätzlich expliziter Verweis auf das Amendment-Datum für künftige Audit-Spuren.

---

### 4.B — Epics (`_bmad-output/planning-artifacts/epics.md`)

#### Edit B1 — FR2 Requirements Inventory (Zeile 40)

**Section:** Requirements Inventory → Functional Requirements → Installation & Lizenz

**OLD:**
```
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „HA OS oder Supervised" vor dem Download-Schritt.
```

**NEW:**
```
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „Home Assistant OS" vor dem Download-Schritt. Home Assistant Supervised, Container und Core sind ausdrücklich nicht unterstützt (Amendment 2026-04-23, KISS-Cut).
```

**Rationale:** Epic-Inventory muss exakt zu PRD-FR2 passen.

---

#### Edit B2 — Story 1.1 AC (Zeile 460)

**Section:** Epic 1 → Story 1.1 → AC „Custom-Repo-Installierbarkeit"

**OLD:**
```
**Given** eine HA-Instanz mit HA OS oder Supervised
**When** der Nutzer das Custom Repository in den Add-on-Store einfügt
**Then** Solalex erscheint im Store als installierbar
```

**NEW:**
```
**Given** eine HA-Instanz mit Home Assistant OS
**When** der Nutzer das Custom Repository in den Add-on-Store einfügt
**Then** Solalex erscheint im Store als installierbar
```

**Rationale:** AC-Wording aligniert mit KISS-Cut. Funktional unverändert (Add-on installiert sich strukturell nur auf Supervisor-basierten Hosts; HAOS ist die einzige supportete davon).

---

#### Edit B3 — Story 1.2 AC 1 (Zeile 501)

**Section:** Epic 1 → Story 1.2 → Acceptance Criteria

**OLD:**
```
**Then** oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile „Benötigt Home Assistant OS oder Supervised" sichtbar
```

**NEW:**
```
**Then** oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile „Benötigt Home Assistant OS" sichtbar
```

**Rationale:** Spiegelt die Story-1.2-AC-1 (bereits KISS-Cut-konform in der Story-Spec) zurück in den Epic-Source-of-Truth.

---

#### Edit B4 — Story 1.2 AC 2 (Zeile 505)

**Section:** Epic 1 → Story 1.2 → Acceptance Criteria

**OLD:**
```
**Then** HA Container und HA Core sind explizit als „nicht supported, best-effort ohne Support" markiert
```

**NEW:**
```
**Then** Home Assistant Supervised, Home Assistant Container und Home Assistant Core sind explizit als „nicht unterstützt" markiert (kein „best-effort"-Aufweichen)
```

**Rationale:** (a) Supervised aufnehmen (im Original fehlend, weil Supervised vorher noch unter „supported" lief). (b) Hartes „nicht unterstützt" statt weicher „best-effort"-Formulierung — KISS-Cut entfernt jede Aufweichung.

---

### 4.C — Story 1.1 (`_bmad-output/implementation-artifacts/1-1-add-on-skeleton-mit-custom-repository-multi-arch-build.md`)

> **Hinweis:** Story 1.1 ist `done`. AC-Update an einer abgeschlossenen Story ist Doku-Nachzug (kein Code-Change, kein Re-Review).

#### Edit C1 — AC 2 (Zeile 16)

**Section:** Acceptance Criteria → 2. Custom-Repo-Installierbarkeit

**OLD:**
```
2. **Custom-Repo-Installierbarkeit:** `Given` eine HA-Instanz mit HA OS oder Supervised, `When` der Nutzer das Custom Repository in den Add-on-Store einfügt, `Then` Solalex erscheint im Store als installierbar.
```

**NEW:**
```
2. **Custom-Repo-Installierbarkeit:** `Given` eine HA-Instanz mit Home Assistant OS, `When` der Nutzer das Custom Repository in den Add-on-Store einfügt, `Then` Solalex erscheint im Store als installierbar.
```

**Rationale:** AC-Wording an Epic-Source-of-Truth (Edit B2) angeglichen.

---

#### Edit C2 — Change Log Eintrag ergänzen (am Ende der Story-Datei)

**Section:** Change Log (Story 1.1)

**Ergänzung (anhängen):**
```
- **2026-04-23** — AC 2 Wording auf „Home Assistant OS" reduziert. Doku-Nachzug zum KISS-Cut-Amendment 2026-04-23 (siehe Sprint Change Proposal 2026-04-23). Code/Implementierung/Tests unverändert: Solalex-Add-on installiert sich strukturell ausschließlich auf Supervisor-basierten Hosts, und Story 1.2 schränkt die Support-Matrix per `homeassistant:`-Pin + `addon/DOCS.md` auf HAOS-only hart ein. Story-Status bleibt `done`.
```

**Rationale:** Audit-Trail erhalten; Reviewer/Dev-Agents sehen, warum die AC-Zeile heute anders lautet als beim ursprünglichen Dev-Cycle.

---

### 4.D — Story 1.2 (`_bmad-output/implementation-artifacts/1-2-landing-page-voraussetzungs-hinweis-ha-versions-range.md`)

#### Edit D1 — Task 4 Beschreibung (Zeile 64)

**Section:** Tasks / Subtasks → Task 4: Referenz-Link zwischen Landing-Page und Add-on-Repo

**OLD:**
```
- [x] In `README.md` (Root) unter „Installation" eine Zeile ergänzen, die auf die Voraussetzungen verweist: `Voraussetzungen: Home Assistant OS oder Supervised. Siehe [docs/landing/voraussetzungen.md](./docs/landing/voraussetzungen.md).`
```

**NEW:**
```
- [x] In `README.md` (Root) unter „Installation" eine Zeile ergänzen, die auf die Voraussetzungen verweist: `Voraussetzungen: Home Assistant OS. Siehe [docs/landing/voraussetzungen.md](./docs/landing/voraussetzungen.md).`
```

**Rationale:** Task-Beschreibung muss zum tatsächlichen `README.md`-Inhalt (Z. 14) passen, der bereits HAOS-only ist.

---

#### Edit D2 — Task 5 Smoke-Test-Beschreibung (Zeile 69)

**Section:** Tasks / Subtasks → Task 5: Smoke-Tests & Final Verification

**OLD:**
```
- [x] `docs/landing/voraussetzungen.md` existiert, enthält die drei Pflicht-Elemente: „Benötigt HA OS oder Supervised"-Kernzeile, Tabelle mit 4 Install-Typ-Zeilen, Hinweis auf Einstellungen → System → Info.
```

**NEW:**
```
- [x] `docs/landing/voraussetzungen.md` existiert, enthält die drei Pflicht-Elemente: „Benötigt Home Assistant OS"-Kernzeile, Tabelle mit 4 Install-Typ-Zeilen, Hinweis auf Einstellungen → System → Info.
```

**Rationale:** Smoke-Test-Spec aligniert mit der tatsächlichen Datei (`docs/landing/voraussetzungen.md` Z. 9, bereits KISS-Cut-konform).

---

#### Edit D3 — Review-Item abhaken + Change Log Eintrag (am Ende der Story-Datei)

**Section:** Review Findings → Review-Patch-PRD-Amendment-Item (Zeile 78)

**OLD:**
```
- [ ] [Review][PRD-Amendment] **OS-only-Cut trifft PRD FR2 und Epic 1 Story 1.2** — die „HA OS oder Supervised"-Formulierung lebt wörtlich in PRD FR2 (Landing-Page-Voraussetzung) und `epics.md` Epic 1 Story 1.2 AC 1/2. Beide müssen via `/bmad-correct-course` nachgezogen werden. Story 1.2 darf erst `done` werden, wenn das Amendment durch ist — sonst driftet die Story-Spec vom PRD ab. [_bmad-output/planning-artifacts/prd.md §FR2, _bmad-output/planning-artifacts/epics.md Epic 1 Story 1.2]
```

**NEW:**
```
- [x] [Review][PRD-Amendment] **OS-only-Cut trifft PRD FR2 und Epic 1 Story 1.2** — abgehakt am 2026-04-23 via `/bmad-correct-course` (Sprint Change Proposal 2026-04-23). PRD FR2, PRD Launch-Gates, PRD Journey 3, PRD Journey Requirements Summary, Epic-1-FR2-Inventory, Epic-1-Story-1.1-AC, Epic-1-Story-1.2-AC 1+2 wurden auf „Home Assistant OS"-Wording reduziert. Story 1.2 entblockt für `done`-Promotion.
```

**Rationale:** Schließt das blockierende Review-Item; entblockt Story-1.2-Done-Promotion.

**Section:** Change Log (Story 1.2) — Ergänzung anhängen:
```
| 2026-04-23 | 0.1.0   | Sprint Change Proposal 2026-04-23 angewandt: PRD/Epic-Amendment OS-only-Cut nachgezogen. Review-Item entblockt. Task-4/Task-5-Beschreibungen wording-aligned. Status-Bewegung in-progress → review (bzw. direkt → done, falls Alex zustimmt). | Dev (Correct-Course) |
```

---

### 4.E — Sprint-Status (`_bmad-output/implementation-artifacts/sprint-status.yaml`)

#### Edit E1 — Story-1.2-Status

**Section:** development_status → epic-1

**OLD:**
```
1-2-landing-page-voraussetzungs-hinweis-ha-versions-range: in-progress
```

**NEW (nach Apply aller Edits 4.A–4.D):**
```
1-2-landing-page-voraussetzungs-hinweis-ha-versions-range: review
```

**Rationale:** Review-Item entblockt → Story kann in Review-Phase. Wenn Alex direkt approved (z. B. weil der Inhalt bereits review-zyklisch validiert wurde und nur das ausstehende Review-Item blockiert war), Status sofort auf `done`.

**Optional (Alex' Entscheidung):**
```
1-2-landing-page-voraussetzungs-hinweis-ha-versions-range: done
```

---

### 4.F — Optional / Defer

#### `docs/Solalex-Deep-Research.md` — DEFER

Z. 21, 41, 296–299 nennen „OS + Supervised ~85 %" als Marktargument. Das ist Research-Snapshot von vor der Scope-Reduktion und nicht load-bearing. **Vorschlag:** ein einzeiliger Header-Stamp am Anfang des Dokuments:
```
> ⚠️ Research-Snapshot vor 2026-04-23 (KISS-Cut auf Home Assistant OS only). Plattform-Reichweite-Argumente in diesem Dokument sind historischer Kontext, nicht aktuelle Spec.
```

**Defer-Begründung:** Research-Doc, nicht Spec-Doc. Markt-Argument bleibt strukturell richtig (HAOS ist mit ~70–85 % der größte HA-Plattform-Anteil, also kein Reichweite-Bruch). Nicht-blocker für Sprint. Kann bei Gelegenheit in einer Doku-Hygiene-PR nachgezogen werden.

#### `docs/Archiv …` — KEINE AKTION

Archiv-Material; bewusst eingefroren.

---

## 5. Implementation Handoff

### Scope-Klassifikation: **Minor**

- ✅ Doku-only (PRD, Epics, 2 Story-Files, Sprint-Status)
- ✅ Kein Code-Change (Backend, Frontend, Add-on-Manifest, CI-Workflows)
- ✅ Keine neuen oder gelöschten Stories
- ✅ Keine Re-Sequenzierung von Epics/Stories
- ✅ Kein neues Story-Sharding
- ✅ Kein Deployment-Bump

→ Kann **direkt durch Dev-Agent** (oder Alex selbst) ausgeführt werden. Keine PM-/Architect-Eskalation nötig.

### Handoff Recipient

**Dev (Amelia / `bmad-dev-story` oder direkter Edit)**

### Deliverables

1. **9 Wording-Edits** (4× PRD, 4× Epics, 1× Story 1.1) per `Edit`-Tool
2. **2 Wording-Edits + 1 Review-Checkbox + 1 Change-Log-Eintrag** in Story 1.2
3. **1 Change-Log-Eintrag** in Story 1.1
4. **Status-Update** in `sprint-status.yaml` (Story 1.2: `in-progress` → `review` oder direkt `done`)
5. **Optional:** Header-Stamp in `docs/Solalex-Deep-Research.md` (Defer-fähig)
6. **Kein Commit ohne Alex' explizite Anweisung** (CLAUDE.md §Git & Commits)

### Success Criteria

- `grep -r -i "OS oder Supervised\|HA OS oder\|HA-OS/Supervised\|HA Container und HA Core sind explizit als" _bmad-output/planning-artifacts/ _bmad-output/implementation-artifacts/` liefert **keine Treffer mehr** in PRD/Epics/Story-1.1/Story-1.2
- `_bmad-output/implementation-artifacts/sprint-status.yaml` zeigt Story-1.2-Status auf `review` oder `done`
- Story-1.2-Review-Findings-Liste zeigt das `[Review][PRD-Amendment]`-Item als abgehakt (`[x]`)
- Architecture/UX-Spec/Sprint-Status sind weiterhin frei von Plattform-Erwähnungen (war ohnehin so)

### Verification Steps (für Dev-Agent nach Apply)

```bash
# Drift-Check (sollte 0 Treffer haben)
grep -rn "OS oder Supervised" _bmad-output/planning-artifacts/ _bmad-output/implementation-artifacts/

# Konsistenz-Check zwischen PRD-FR2 und Epic-FR2
grep -A1 "FR2" _bmad-output/planning-artifacts/prd.md | grep "Home Assistant OS"
grep -A1 "FR2" _bmad-output/planning-artifacts/epics.md | grep "Home Assistant OS"

# Story-1.2-Review-Item ist abgehakt
grep "Review.*PRD-Amendment" _bmad-output/implementation-artifacts/1-2-landing-page-*.md
```

### Timeline

- **Apply:** ≤ 30 Minuten
- **Review:** keiner nötig (Doku-Edit, kein Code)
- **Promotion:** Story 1.2 sofort entblockt nach Apply

---

## Approval Block

**Status:** Draft, awaiting Alex' approval.

**Approval-Frage:** Ist dieses Sprint Change Proposal vollständig und akkurat? Sollen alle 4.A–4.E-Edits angewandt werden? Optionaler 4.F-Header-Stamp gewünscht oder defer?

**Antwort-Format:** `yes` / `no` / `revise` (mit Hinweis auf konkrete Edits, die anders/weggelassen/zusätzlich sein sollen).
