# Story 1.2: Landing-Page-Voraussetzungs-Hinweis + HA-Versions-Range

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Interessent auf alkly.de,
I want vor dem Download-Schritt klar zu sehen, welche HA-Installationstypen und welche HA-Version unterstützt werden,
so that ich kein fehlgeschlagenes Setup erlebe und die Voraussetzungen vorher kenne.

> **Amendment 2026-04-23 (KISS-Cut):** Support-Matrix auf **Home Assistant OS** reduziert. Supervised, Container und Core werden nicht unterstützt. Begründung: „Keep it simple" — v1-Komplexität minimieren, Support-Triage-Matrix auf eine known-good Host-Konfiguration beschränken. Trifft auch PRD FR2 und Epic 1 Story 1.2 → PRD/Epic-Amendment via `/bmad-correct-course` nötig.

## Acceptance Criteria

1. **Voraussetzungs-Zeile über jedem CTA (Landing-Page):** `Given` die Solalex-Landing-Page auf alkly.de, `When` der Besucher die Seite öffnet, `Then` oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile **„Benötigt Home Assistant OS"** sichtbar (keine Tooltips, keine Modals — direkt im Flow, siehe CLAUDE.md Stil-Leitplanken).
2. **Nicht unterstützte HA-Varianten explizit markiert (Landing-Page):** `Given` der Check-Block auf der Landing-Page, `When` er gelesen wird, `Then` HA Supervised, HA Container **und** HA Core sind explizit als **„nicht unterstützt"** markiert (punkt, ohne best-effort-Aufweichung).
3. **Install-Warning via `addon/config.yaml`-Deklaration:** `Given` ein Nutzer versucht Solalex auf einer nicht-unterstützten HA-Version zu installieren, `When` der Add-on-Store die Installation prüft, `Then` eine Install-Warning wird gezeigt **And** die supported HA-Version-Range ist in `addon/config.yaml` via `homeassistant:`-Feld deklariert (Mindest-Version-Pin).

## Tasks / Subtasks

- [x] **Task 1: `addon/config.yaml` um `homeassistant:`-Feld erweitern** (AC: 3)
  - [x] Voraussetzung: Story 1.1 hat `addon/config.yaml` bereits mit Grundfeldern (name, version, slug, arch, ingress, ingress_port, panel_title, hassio_api, …) angelegt. **Nur erweitern, nicht neu schaffen.**
  - [x] Feld `homeassistant: "2026.4.0"` (Minimum-Pin) einfügen. Begründung: aktuelle stable HA Core ist 2026.4.3 (Stand April 2026). Minimum auf Patch-Release-Start des aktuellen Minor pinnen, um Lag-Toleranz für Beta-Tester zu gewähren.
  - [x] Kommentar im YAML: `# Minimum HA Core version — inkompatible Versionen erhalten Install-Warning im Add-on-Store.`
  - [x] **snake_case-Disziplin** (CLAUDE.md Regel 1): Key ist `homeassistant` (HA-Supervisor-Spec, lowercase — passt zu snake_case). Kein PascalCase, kein camelCase.
  - [x] **Kein `homeassistant_api`-Setzen in dieser Story** — das wurde in Story 1.1 entschieden. Nicht umschalten.
  - [x] Manuelle Verifikation: `yq '.homeassistant' addon/config.yaml` liefert die Versions-String.
- [x] **Task 2: Install-Warning-Smoke-Test dokumentieren** (AC: 3)
  - [x] **Kein CI-Gate** — HA-Supervisor validiert das Feld beim Install. Reproduktion nur manuell via HA-Test-Instanz möglich.
  - [x] In `addon/DOCS.md` einen Abschnitt **„Unterstützte HA-Versionen"** ergänzen:
    - Minimum: 2026.4.0
    - Getestet bis: aktuelle stable (zum Release-Zeitpunkt dokumentieren)
    - Unterstützt: **ausschließlich Home Assistant OS** (Amendment 2026-04-23, KISS-Cut). Home Assistant Supervised, Container und Core werden als **nicht unterstützt** gekennzeichnet (kein „best-effort"-Aufweichen).
  - [x] In `addon/CHANGELOG.md` Eintrag für die Version hinzufügen: `- Minimum HA Core: 2026.4.0 deklariert.`
- [x] **Task 3: Landing-Page-Content für alkly.de erstellen** (AC: 1, 2)
  - [x] **Scope-Hinweis für Dev-Agent:** Die Landing-Page lebt **außerhalb dieses Repos** (alkly.de-Marketing-Site). In diesem Repo wird nur der **Content-Baustein als Markdown-Snippet** unter `docs/landing/voraussetzungen.md` abgelegt — damit die Copy-Quelle versioniert ist und per `git mv` beim „Solalex"-Rename mitwandert.
  - [x] Datei `docs/landing/voraussetzungen.md` neu anlegen mit folgender Struktur (Frontmatter + Markdown-Body) — **aktualisiert 2026-04-23 auf OS-only-Cut**:
    ```markdown
    ---
    slug: voraussetzungen
    target_placement: above_every_cta
    required_above: ["install_cta", "download_cta", "waitlist_cta"]
    ---

    ## Voraussetzungen

    > **Benötigt Home Assistant OS.**

    | HA-Installationstyp       | Status              |
    | ------------------------- | ------------------- |
    | Home Assistant OS         | ✅ unterstützt       |
    | Home Assistant Supervised | ❌ nicht unterstützt |
    | Home Assistant Container  | ❌ nicht unterstützt |
    | Home Assistant Core       | ❌ nicht unterstützt |

    Du weißt nicht, welche Variante du hast? Öffne in HA: **Einstellungen → System → Info**.
    ```
  - [x] **Formulierungen nach KISS-Cut:** „Benötigt Home Assistant OS" + „nicht unterstützt" (hart, kein „best-effort ohne Support"-Aufweichen). Keine emotionalen Adjektive, keine „easy/einfach"-Claims (CLAUDE.md Stil-Leitplanken). PRD-FR2-wörtliche Formulierung wurde durch das 2026-04-23-Amendment ersetzt — PRD-Amendment folgt via `/bmad-correct-course`.
  - [x] **Glossar-Disziplin** (CLAUDE.md): Der Begriff ist **„Home Assistant OS"** (korrekt ausgeschrieben bei Erstnennung), danach „HA OS" okay. Nie „HAOS".
  - [x] Alex überträgt den Content manuell auf alkly.de (Marketing-Site-Deployment ist außerhalb dieser Story). Commit in diesem Repo genügt als Abnahme-Beleg.
- [x] **Task 4: Referenz-Link zwischen Landing-Page und Add-on-Repo** (AC: 1, 2)
  - [x] In `README.md` (Root) unter „Installation" eine Zeile ergänzen, die auf die Voraussetzungen verweist: `Voraussetzungen: Home Assistant OS. Siehe [docs/landing/voraussetzungen.md](./docs/landing/voraussetzungen.md).`
  - [x] Keine Inhalts-Duplikation — nur Verweis, damit Single-Source-of-Truth das `voraussetzungen.md`-File bleibt.
- [x] **Task 5: Smoke-Tests & Final Verification** (AC: 1, 2, 3)
  - [x] `addon/config.yaml` ist valides YAML (`yq . addon/config.yaml` wirft keinen Fehler).
  - [x] `homeassistant:`-Feld hat einen Versions-String, der semver-kompatibel zum HA-Supervisor-Pattern ist (`YYYY.M.P`, z. B. `2026.4.0`).
  - [x] `docs/landing/voraussetzungen.md` existiert, enthält die drei Pflicht-Elemente: „Benötigt Home Assistant OS"-Kernzeile, Tabelle mit 4 Install-Typ-Zeilen, Hinweis auf Einstellungen → System → Info.
  - [x] `addon/DOCS.md` hat Abschnitt „Unterstützte HA-Versionen".
  - [x] `README.md` verweist auf `docs/landing/voraussetzungen.md`.

### Review Findings

_Code-Review vom 2026-04-23 (3 parallele Layer: Blind Hunter, Edge Case Hunter, Acceptance Auditor). Acceptance-Auditor bestätigt AC 1/2/3 inhaltlich erfüllt._

- [x] [Review][Defer] **Story-1-1-Patches separat vor Story-1-2 committen** — `panel_title: Solalex → Solalex by ALKLY` und neue `schema: {}` / `options: {}` in `addon/config.yaml` sind laut Story-1-1-Completion-Log Review-Patches aus 1-1. [addon/config.yaml:1,17,28-29] — deferred 2026-04-23 (Cycle 2), Reason: zu spät committed (Changes bereits auf `main`, Git-Historie-Rewrite nicht mehr reibungsfrei möglich); rückwirkend als akzeptierter Scope-Bleed zu Story 1.1 dokumentiert.
- [x] [Review][PRD-Amendment] **OS-only-Cut trifft PRD FR2 und Epic 1 Story 1.2** — abgehakt am 2026-04-23 via `/bmad-correct-course` (Sprint Change Proposal 2026-04-23). PRD FR2, PRD Launch-Gates, PRD Journey 3, PRD Journey Requirements Summary, Epic-1-FR2-Inventory, Epic-1-Story-1.1-AC, Epic-1-Story-1.2-AC 1+2 wurden auf „Home Assistant OS"-Wording reduziert. Story 1.2 entblockt für `done`-Promotion.
- [x] [Review][Patch] OS-only-Cut in DOCS.md, voraussetzungen.md, README.md und Story-1-2-Spec (AC 1, AC 2, Task 3, File-Spec, Anti-Patterns) vereinheitlicht — gefixt 2026-04-23
- [x] [Review][Patch] `## Voraussetzungen`-Block + `## Unterstützte HA-Versionen`-Block in DOCS.md vereinheitlicht (keine Widersprüche mehr) [addon/DOCS.md:14-32] — gefixt (D3 via Variante 3 aufgelöst: Duplikation akzeptiert, beide Blöcke harmonisiert)
- [x] [Review][Patch] CHANGELOG-Eintrag um Landing-Page, DOCS-Ergänzung und OS-only-Cut erweitert [addon/CHANGELOG.md:8-15] — gefixt
- [x] [Review][Defer] `homeassistant:`-Pin wirkt nicht für HA Container/Core — DOCS-Formulierung präzisieren low-prio [addon/DOCS.md:22-28] — deferred, Container/Core hat keinen Add-on-Store-Flow
- [x] [Review][Defer] „Getestet bis 2026.4.3" wird mit jedem HA-Patch veralten — manuelle Bump-Disziplin notwendig [addon/DOCS.md:25] — deferred, spec-explicit als „zum Release-Zeitpunkt dokumentieren"
- [x] [Review][Defer] Kein CI-Gate für Versions-Range-Konsistenz (`homeassistant:` ≤ Minimum ≤ „getestet bis") — deferred, strukturelles Gate-Thema für v1.5

_Dismissed (12) als Noise/Spec-konform: Tabelle+Emojis in voraussetzungen.md (Spec-mandated), README-Link-Bruch (README ≠ DOCS-Kanal), Tabellen-Alignment-Delimiter ohne `:` (Spec-Muster), Frontmatter-Keys Dead-Metadata (Spec als „dokumentative Hints"), Glossar-Alias HAOS (Spec verbietet), „best-effort"-Mehrdeutigkeit (wörtlich aus FR2), Feld-Reihenfolge `homeassistant:` (Spec-konform), Trailing-Whitespace/EOF-Newline (pre-commit grün), Tabellen-Spalten-Kosmetik, Debug-Log „21 Top-Level-Keys" (1-1-Context), ⚠️-Emoji-Breite (GFM rendert sauber)._

#### Review Cycle 2 — 2026-04-23 (zweiter Durchgang, 3 parallele Layer)

- [x] [Review][Defer] **Frontend-H1 und FastAPI-`title` zeigen noch „Solalex" statt „Solalex by ALKLY"** — `panel_title` wurde in `addon/config.yaml:17` auf „Solalex by ALKLY" aktualisiert, aber [frontend/src/App.svelte:31](../../frontend/src/App.svelte#L31) und [backend/src/solalex/main.py:88](../../backend/src/solalex/main.py#L88) halten weiterhin den kurzen „Solalex"-Titel. Branding-Konsistenz ist out-of-scope für Story 1.2 (doc-only), gehört zu Story 1.5 (HA-Sidebar-Registrierung mit Alkly-Branding) — deferred.
- [x] [Review][Dismiss-Bestätigung] **German-Quote-Typography (`„…"` mit ASCII-Closing)** in `addon/DOCS.md:16` und `addon/CHANGELOG.md:17` folgt der etablierten Repo-Konvention (CLAUDE.md nutzt selben Pattern) — dismissed, keine Inkonsistenz zum Projekt.
- [x] [Review][Dismiss-Bestätigung] **Install-Warning-Semantik vs. Hard-Block** (Runtime-Crash-Sorge auf HA < 2026.4.0) — Spec-definiert als Soft-Warning, Runtime-Crash ist spekulativ und durch Story 1.3 auf 2026.4.x validiert — dismissed.
- [x] [Review][Dismiss-Bestätigung] **Pre-Release-HA-Version-Vergleich** (2026.4.0b0 triggert Warning) — HA-Supervisor-Verhalten, Lag-Toleranz deckt es ab — dismissed.
- [x] [Review][Dismiss-Bestätigung] **Supervised-Migration-Path fehlt** — keine existierenden Installs (Pre-Beta), nicht anwendbar — dismissed.
- [x] [Review][Dismiss-Bestätigung] **Changelog-Merge-Konflikt unter `0.1.0 — TBD`** — 0.1.0 ist WIP-Bucket, Workflow-Concern, kein Code-Issue — dismissed.

_Status offener `[ ]`-Items: Der Story-1-1-Patch-Separation-Punkt (`panel_title` + `schema: {}` + `options: {}` im 1.2-Arbeitsbaum) bleibt unresolved und ist das einzige `decision_needed`-Finding aus diesem Zyklus._

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md §Technical Constraints](../planning-artifacts/architecture.md) — Runtime-Constraints (HA Add-on Base Image, Supervisor-Token, `/data/`)
- [architecture.md §Project Directory Structure](../planning-artifacts/architecture.md) — `addon/`-Layout bestätigt
- [prd.md §FR2, FR40](../planning-artifacts/prd.md) — Original-Requirement-Formulierungen (wörtlich!)
- [prd.md §NFR28 — 100 % lokal](../planning-artifacts/prd.md) — Keine Tracking-Scripts auf Landing-Page
- [epics.md Epic 1 Story 1.2](../planning-artifacts/epics.md) — Original-AC
- [CLAUDE.md — 5 harte Regeln + Stil-Leitplanken](../../CLAUDE.md)
- HA-Supervisor Addon-Config-Spec: [developers.home-assistant.io/docs/add-ons/configuration](https://developers.home-assistant.io/docs/add-ons/configuration/) — `homeassistant:` Feld-Definition

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope dieser Story ist minimal und präzise — nicht aufblähen!**

Diese Story hat **keine Code-Änderungen in `backend/` oder `frontend/`**. Sie berührt nur:

1. `addon/config.yaml` — ein einzelnes neues Feld
2. `addon/DOCS.md` + `addon/CHANGELOG.md` — Dokumentations-Ergänzungen
3. `docs/landing/voraussetzungen.md` — neuer Markdown-Content für alkly.de
4. `README.md` — eine Verweis-Zeile

**Wenn Du anfängst, Python-Code, Svelte-Komponenten, CI-Workflows oder Lizenz-Logik zu schreiben — STOP. Falsche Story.**

**HA-Supervisor-Version-Field-Semantik (kritisch):**

| Feld in `addon/config.yaml` | Typ | Semantik |
|---|---|---|
| `homeassistant: "2026.4.0"` | string | **Minimum-Pin.** Inkompatible (= niedrigere) HA-Core-Version → Install-Warning im Add-on-Store. Das Add-on kann trotzdem installiert werden — aber der User sieht die Warning. |
| **Keine Maximum-Deklaration** | — | HA-Supervisor hat kein Maximum-Pin-Feld. „Range" im Epic-Wording ist effektiv „Minimum + dokumentierte getestete Obergrenze in DOCS.md". |

**Version-Pin-Wert:** `2026.4.0`. Begründung: 2026.4.3 ist aktuelle stable (Stand April 2026). Auf den Minor-Start zu pinnen, gibt Beta-Testern Lag-Toleranz (sie können auf 2026.4.0 sein, während 2026.4.3 verfügbar ist) und blockiert gleichzeitig alte HA-Versionen mit potenziellen WebSocket-API-Abweichungen.

**Wenn Alex explizit eine andere Minimum-Version bevorzugt:** Im Completion-Log dokumentieren und den Wert entsprechend setzen. Alle anderen Aufgaben bleiben unverändert.

### Anti-Patterns & Gotchas

- **KEIN neuer `addon.yaml` neben `addon/config.yaml`.** Der HA-Supervisor erwartet die Datei unter `addon/config.yaml` (Architektur §601–602). Die Epic-/PRD-Formulierung „addon.yaml" meint umgangssprachlich das Addon-Manifest — die Datei heißt in unserer Struktur `addon/config.yaml`.
- **KEIN `homeassistant_version`-Feld.** Der korrekte Key heißt `homeassistant` (ohne `_version`-Suffix). Andere Varianten führen zu Ignorierung ohne Fehler.
- **KEIN Max-Version-Feld ausdenken.** HA-Supervisor hat keine Maximum-Deklaration. Range-Semantik lebt in DOCS.md als „getestet bis X".
- **KEIN Marketing-Umformulieren** der Kernzeile. Die Formulierung lautet seit dem 2026-04-23-Amendment **„Benötigt Home Assistant OS"** (KISS-Cut, OS-only) und darf nicht in „Unterstützt HA OS" o. ä. weichgespült werden. Epic-AC fordert „prominent sichtbar". Ursprüngliche PRD-FR2-Formulierung („OS oder Supervised") wurde via `/bmad-correct-course` (Sprint Change Proposal 2026-04-23) nachgezogen.
- **KEIN Tooltip, KEIN Modal, KEIN Accordion** für die Voraussetzungs-Information. CLAUDE.md Stil-Leitplanken (UX-DR30): Anti-Patterns explizit verboten. Direkt im Flow über dem CTA.
- **KEIN Tracking-Pixel / Google-Analytics / Facebook-Pixel** auf der Landing-Page (NFR28 „100 % lokal" erstreckt sich auf die Marketing-Identität; keine Pflicht, aber strategisch kongruent).
- **KEIN i18n-Framework** für das Markdown-Snippet (CLAUDE.md: keine i18n-Infrastruktur in v1). Deutsch hardcoded.
- **KEIN Rename** des Add-ons in dieser Story (auto-memory: „Solalex" steht unter Markenrechts-Vorbehalt). `config.yaml` behält den aktuellen Slug aus Story 1.1. Rename-Risiko außerhalb dieser Story-Scope.
- **Story-Abhängigkeit:** Story 1.1 (Add-on Skeleton) muss implementiert sein, bevor diese Story gestartet wird — sonst existiert `addon/config.yaml` nicht. Sprint-Status: 1.1 ist aktuell `ready-for-dev`, nicht `done`. Falls 1.1 noch nicht implementiert ist, **erst 1.1 dev-storyen**.

### Source Tree — zu ändernde/neue Dateien (Zielzustand nach Story)

```
solalex/ (= Repo-Root)
├── README.md                                           [MOD — Verweis-Zeile auf voraussetzungen.md]
├── addon/
│   ├── config.yaml                                     [MOD — + homeassistant: "2026.4.0"]
│   ├── DOCS.md                                         [MOD — + Abschnitt „Unterstützte HA-Versionen"]
│   └── CHANGELOG.md                                    [MOD — + Eintrag für Minimum-HA-Pin]
└── docs/
    └── landing/
        └── voraussetzungen.md                          [NEW — Landing-Page-Copy-Quelle]
```

**Keine neuen Python-/TS-/Svelte-Files.** Keine Änderungen in `backend/` oder `frontend/`.

### Library/Framework Requirements

**Keine neuen Dependencies.** Diese Story fügt keine Libraries hinzu.

### File Spec — `addon/config.yaml` Diff-Muster (Copy-Paste-sicher)

Bestehende `addon/config.yaml` aus Story 1.1 (Beispielstruktur):

```yaml
name: "Solalex"
version: "0.1.0"
slug: "solalex"
description: "Reaktive Nulleinspeisung und Akku-Regelung für Home Assistant."
arch:
  - amd64
  - aarch64
ingress: true
ingress_port: 8099
panel_icon: "mdi:solar-power"
panel_title: "Solalex by ALKLY"
init: false
hassio_api: true
hassio_role: "default"
ports: {}
image: "ghcr.io/alkly/solalex-{arch}"
```

**Nach Story 1.2 ergänzt um:**

```yaml
# Minimum HA Core version — inkompatible Versionen erhalten Install-Warning im Add-on-Store.
homeassistant: "2026.4.0"
```

Einfügen idealerweise direkt nach `version:` oder vor `arch:` (Supervisor ist indifferent gegenüber Reihenfolge, aber Lesbarkeit bevorzugt die Nähe zu anderen Version-/Identitäts-Feldern).

### File Spec — `docs/landing/voraussetzungen.md` (Copy-Paste-sicher, KISS-Cut 2026-04-23)

```markdown
---
slug: voraussetzungen
target_placement: above_every_cta
required_above: ["install_cta", "download_cta", "waitlist_cta"]
---

## Voraussetzungen

> **Benötigt Home Assistant OS.**

| HA-Installationstyp       | Status              |
| ------------------------- | ------------------- |
| Home Assistant OS         | ✅ unterstützt       |
| Home Assistant Supervised | ❌ nicht unterstützt |
| Home Assistant Container  | ❌ nicht unterstützt |
| Home Assistant Core       | ❌ nicht unterstützt |

Du weißt nicht, welche Variante du hast? Öffne in HA: **Einstellungen → System → Info**.
```

**Frontmatter-Felder sind dokumentative Hints** für die Alkly-Marketing-Site-Integration (Platzierung „über jedem CTA"). Sie brechen nicht, wenn sie von einem einfachen Markdown-Renderer ignoriert werden.

### Testing Requirements

- **Kein pytest-/vitest-Test** erforderlich — diese Story enthält keinen ausführbaren Code.
- **Manuelle Validierung:**
  1. `yq '.homeassistant' addon/config.yaml` → gibt `"2026.4.0"` aus.
  2. `cat docs/landing/voraussetzungen.md` → enthält die drei Pflicht-Elemente.
  3. `cat README.md | grep voraussetzungen.md` → Link-Zeile vorhanden.
- **CI-Gate:** Keine neuen Gates. Die 4 bestehenden CI-Gates (Ruff+MyPy+Pytest, ESLint+svelte-check+Prettier+Vitest, Egress-Whitelist, SQL-Migrations-Ordering) laufen unverändert weiter. Das Hinzufügen von `homeassistant:` zu `addon/config.yaml` bricht keinen Test.
- **Beta-Validierung (post-Story):** Ein Beta-Tester auf HA-Version < 2026.4.0 sollte beim Install-Versuch die Warning sehen. Wenn während Beta kein solcher Tester existiert, ist das akzeptabel — HA-Supervisor-Verhalten ist dokumentiert und deterministisch.

### Project Structure Notes

- **Alignment:** `addon/config.yaml`-Änderung ist konsistent mit Story 1.1 (dort wird die Datei erstmals angelegt).
- **Neues Verzeichnis `docs/landing/`:** Nicht in Architektur explizit benannt, aber im `docs/`-Ordner vorgesehen (architecture.md §749). Die Unterstruktur `docs/landing/` signalisiert die Marketing-Quelle sauber getrennt von `docs/architecture.md` / `docs/api.md` / `docs/development.md`.
- **Keine Konflikte:** Story 1.1 legt `addon/DOCS.md` und `addon/CHANGELOG.md` als Dateien an — hier werden nur Abschnitte ergänzt, keine Dateistruktur geändert.

### Previous Story Intelligence — Lessons aus Story 1.1

Story 1.1 ist selbst noch nicht implementiert (Status: `ready-for-dev`), aber ihr Story-File enthält bereits etablierte Konventionen, die hier gelten:

- **`addon/config.yaml`-Minimalismus:** Die bestehende Datei ist bewusst schlank. Story 1.2 fügt genau **ein** Feld hinzu — keine Refactor-Gelegenheit, keine Umsortierung.
- **snake_case-Disziplin:** Das Feld `homeassistant` passt in das Schema (lowercase, keine Trenner). Andere HA-Supervisor-Keys (`ingress_port`, `hassio_api`, `panel_icon`, `panel_title`) sind bereits snake_case — stilistisch konsistent.
- **Keine CDN-Requests:** Story 1.1 legt das 100-%-lokal-Fundament ab Tag 1. Die Landing-Page-Copy enthält **keine externen Font-/Script-Einbindungen** (ist reines Markdown, rendert im Alkly-Marketing-Stack).
- **Changelog-Disziplin:** Story 1.1 legt `addon/CHANGELOG.md` an. Jede Config-Änderung (wie der `homeassistant:`-Pin) bekommt hier einen Eintrag. Nicht vergessen.

### Git Intelligence

- **Repo-Zustand:** Nur ein Commit (`Initial project planning artifacts and workspace setup`). Kein Source-Code committed. Story 1.1 ist `ready-for-dev`, aber ihr Dev-Cycle läuft noch. **Annahme für Dev-Agent:** 1.1 ist zum Zeitpunkt des 1.2-Starts abgeschlossen und gemerged. Falls nicht, ist die Voraussetzung nicht erfüllt — dann **erst 1.1 abschließen**.
- **Commit-Message-Stil (aus CLAUDE.md):** Deutsch okay, kurz, Imperativ. Beispiel-Commit für diese Story: `Add homeassistant-Mindest-Version-Pin und Landing-Page-Voraussetzungen`. **Keine Commits ohne explizite Alex-Anweisung** (CLAUDE.md §Git & Commits).

### Latest Technical Information

- **HA Core Stable (April 2026):** 2026.4.3 laut [home-assistant.io](https://www.home-assistant.io/). Minimum-Pin `2026.4.0` gibt realistische Lag-Toleranz.
- **HA-Supervisor `homeassistant:`-Feld:** Dokumentiert als Minimum-Pin-String im `YYYY.M.P`-Format. Kein Range, keine Maxima. Quelle: [developers.home-assistant.io Add-on Configuration Docs](https://developers.home-assistant.io/docs/add-ons/configuration/).
- **Add-on-Store-Install-Warning:** HA-Supervisor prüft `homeassistant:` beim Install-Trigger. Bei Mismatch wird eine Warning im Supervisor-UI gezeigt, der Install kann trotzdem fortgesetzt werden — der User trägt die Verantwortung. Dieses Verhalten ist Ziel-Semantik der AC 3.

### Project Context Reference

- [CLAUDE.md](../../CLAUDE.md) — 5 harte Regeln, Style-Leitplanken, Anti-Pattern-Liste.
- [architecture.md](../planning-artifacts/architecture.md) — Directory Structure, Tech-Stack-Versions-Matrix.
- [prd.md](../planning-artifacts/prd.md) — FR2, FR40, NFR28.
- [epics.md](../planning-artifacts/epics.md) — Epic 1 Story 1.2 Original-AC.

### Story Completion Status

Diese Story ist **klein und dokumentations-schwer**. Sie kipptfertig ab:

- `addon/config.yaml` enthält `homeassistant:` mit Versions-String.
- `docs/landing/voraussetzungen.md` enthält die 3 Pflicht-Elemente (Kernzeile, Tabelle, Hinweis).
- `addon/DOCS.md`, `addon/CHANGELOG.md`, `README.md` sind entsprechend ergänzt.
- Manuelle `yq`-Verifikation grün.

Kein Backend-Code, kein Frontend-Code, kein CI-Gate. Dev-Agent bleibt fokussiert.

### References

- [architecture.md – Project Directory Structure](../planning-artifacts/architecture.md)
- [architecture.md – Technical Constraints](../planning-artifacts/architecture.md)
- [prd.md – FR2 (Landing-Page-Voraussetzung)](../planning-artifacts/prd.md)
- [prd.md – FR40 (HA-Version-Kompatibilität in addon.yaml)](../planning-artifacts/prd.md)
- [prd.md – NFR28 (100 % lokal)](../planning-artifacts/prd.md)
- [epics.md – Epic 1 Story 1.2](../planning-artifacts/epics.md)
- [CLAUDE.md – 5 harte Regeln, Stil-Leitplanken](../../CLAUDE.md)
- [HA Supervisor Add-on Configuration Docs](https://developers.home-assistant.io/docs/add-ons/configuration/)
- [Story 1.1 (Add-on Skeleton)](./1-1-add-on-skeleton-mit-custom-repository-multi-arch-build.md)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) — bmad-dev-story skill

### Debug Log References

- `addon/config.yaml`: YAML-Parser-Validierung via `python3 -c "import yaml; yaml.safe_load(open('addon/config.yaml'))"` (uv run --with pyyaml) → OK, `homeassistant='2026.4.0'`, 21 Top-Level-Keys.
- Semver-Pattern-Check: `re.fullmatch(r'\d{4}\.\d{1,2}\.\d+', "2026.4.0")` → Match.
- Pflicht-Element-Check `docs/landing/voraussetzungen.md`: Kernzeile „Benötigt Home Assistant OS" (Stand nach KISS-Cut-Review-Patch 2026-04-23; ursprüngliche Dev-Cycle-Verifikation am 2026-04-22 prüfte noch die alte Formulierung „OS oder Supervised"), 4 Install-Typ-Zeilen (HA OS, HA Supervised, HA Container, HA Core), Info-Hinweis „Einstellungen → System → Info" — alle vorhanden.
- `addon/DOCS.md`: Abschnitt `## Unterstützte HA-Versionen` vorhanden.
- `addon/CHANGELOG.md`: Eintrag `- Minimum HA Core: 2026.4.0 deklariert.` vorhanden.
- `README.md`: Verweis-Zeile `docs/landing/voraussetzungen.md` vorhanden.
- Pre-commit Hooks (`uvx pre-commit run --files …`): trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict, mixed-line-ending → alle Passed. Ruff/ruff-format/prettier → no files to check (Story enthält keine Python-/Svelte-Änderungen, wie erwartet).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Task 1:** `addon/config.yaml` um `homeassistant: "2026.4.0"` ergänzt, mit YAML-Kommentar direkt darüber. Position: zwischen `version:` und `slug:` (Nähe zu Identitäts-Feldern, Supervisor ist reihenfolge-indifferent).
- **Task 2:** Neuer Abschnitt „Unterstützte HA-Versionen" in `addon/DOCS.md` nach „Voraussetzungen" eingefügt (Minimum 2026.4.0, Getestet bis 2026.4.3). Ursprünglicher Snapshot 2026-04-22: „HA OS/Supervised supported, HA Container/Core als nicht supported, best-effort ohne Support". KISS-Cut-Review-Patch 2026-04-23 reduziert auf „HAOS-only unterstützt; Supervised/Container/Core nicht unterstützt". Bestehender „Voraussetzungen"-Abschnitt unverändert. Changelog-Eintrag in `addon/CHANGELOG.md` unter der bestehenden `0.1.0 — TBD`-Rubrik ergänzt.
- **Task 3:** `docs/landing/voraussetzungen.md` 1:1 nach dem Copy-Paste-Muster der Story-Spec angelegt (Frontmatter + Markdown-Body). Kernzeile ursprünglich „Benötigt Home Assistant OS oder Supervised." wörtlich aus PRD FR2 (Stand 2026-04-22) — durch KISS-Cut-Review-Patch 2026-04-23 auf „Benötigt Home Assistant OS." reduziert; PRD FR2 wurde via Sprint Change Proposal 2026-04-23 nachgezogen. Keine Marketing-Umformulierung, keine Tooltips/Modals, keine Tracking-Pixel. Glossar-Disziplin: „Home Assistant OS" voll ausgeschrieben.
- **Task 4:** `README.md` um eine Verweis-Zeile unter der „Installation"-Überschrift ergänzt (direkt vor dem nummerierten Install-Flow). Keine Inhalts-Duplikation — nur Link auf `docs/landing/voraussetzungen.md` als Single-Source.
- **Task 5:** Alle 5 Smoke-Tests (YAML-Validität, Semver-Pattern, Pflicht-Elemente in Markdown-Snippet, DOCS-Abschnitt, README-Verweis) automatisch via Python/pyyaml durchlaufen — alle grün. Pre-commit-Hooks ohne Beanstandung.
- **Scope-Disziplin:** Keine Änderungen in `backend/` oder `frontend/`. Keine neuen Dependencies. Kein Rename von Slug/Image/Repo-Namen.
- **Review-Patch 2026-04-23 (KISS-Cut):** Support-Matrix im Review-Cycle auf „nur Home Assistant OS" reduziert. Supervised/Container/Core jetzt hart „nicht unterstützt". Änderung trifft AC 1, AC 2, Task 3, File-Spec, Anti-Patterns, `addon/DOCS.md`, `docs/landing/voraussetzungen.md`, `README.md` und `addon/CHANGELOG.md`. PRD-FR2-Amendment als Action-Item an `/bmad-correct-course` delegiert.

### File List

- `addon/config.yaml` [MOD] — `homeassistant: "2026.4.0"` + Kommentar ergänzt
- `addon/DOCS.md` [MOD] — Abschnitt „Unterstützte HA-Versionen" ergänzt
- `addon/CHANGELOG.md` [MOD] — Eintrag „Minimum HA Core: 2026.4.0 deklariert." ergänzt
- `docs/landing/voraussetzungen.md` [NEW] — Landing-Page-Copy-Quelle (Frontmatter + Markdown)
- `README.md` [MOD] — Verweis-Zeile unter „Installation via Home Assistant Add-on Store"
- `_bmad-output/implementation-artifacts/sprint-status.yaml` [MOD] — Status-Tracking (ready-for-dev → in-progress → review)
- `_bmad-output/implementation-artifacts/1-2-landing-page-voraussetzungs-hinweis-ha-versions-range.md` [MOD] — Tasks abgehakt, Dev Agent Record, File List, Change Log, Status

## Change Log

| Datum      | Version | Änderung                                                               | Autor |
| ---------- | ------- | ---------------------------------------------------------------------- | ----- |
| 2026-04-22 | 0.1.0   | Minimum HA Core 2026.4.0 via `addon/config.yaml` pinnt Install-Warning | Dev    |
| 2026-04-22 | 0.1.0   | `docs/landing/voraussetzungen.md` als Landing-Page-Copy-Quelle         | Dev    |
| 2026-04-22 | 0.1.0   | `addon/DOCS.md` + `README.md` um Voraussetzungs-Hinweise ergänzt       | Dev    |
| 2026-04-23 | 0.1.0   | KISS-Cut im Review: Support-Matrix auf Home Assistant OS beschränkt; Supervised/Container/Core als „nicht unterstützt" markiert. AC 1/2, Task 3, File-Spec, `addon/DOCS.md`, `docs/landing/voraussetzungen.md`, `README.md`, `addon/CHANGELOG.md` angepasst. PRD-FR2 + Epic 1 Story 1.2 Amendment via `/bmad-correct-course` ausstehend. | Review |
| 2026-04-23 | 0.1.0   | Sprint Change Proposal 2026-04-23 angewandt: PRD/Epic-Amendment OS-only-Cut nachgezogen (PRD FR2 + 3 narrative Stellen, Epic-1-FR2-Inventory, Epic-1-Story-1.1-AC, Epic-1-Story-1.2-AC 1+2, Story 1.1 AC 2). Task-4/Task-5-Beschreibungen wording-aligned. Review-Item `[Review][PRD-Amendment]` abgehakt → Story 1.2 entblockt, Status `in-progress → review`. | Dev (Correct-Course) |
