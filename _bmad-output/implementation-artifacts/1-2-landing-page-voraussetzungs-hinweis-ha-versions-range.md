# Story 1.2: Landing-Page-Voraussetzungs-Hinweis + HA-Versions-Range

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Interessent auf alkly.de,
I want vor dem Download-Schritt klar zu sehen, welche HA-Installationstypen und welche HA-Version unterstützt werden,
so that ich kein fehlgeschlagenes Setup erlebe und die Voraussetzungen vorher kenne.

## Acceptance Criteria

1. **Voraussetzungs-Zeile über jedem CTA (Landing-Page):** `Given` die Solalex-Landing-Page auf alkly.de, `When` der Besucher die Seite öffnet, `Then` oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile **„Benötigt Home Assistant OS oder Supervised"** sichtbar (keine Tooltips, keine Modals — direkt im Flow, siehe CLAUDE.md Stil-Leitplanken).
2. **HA-Container/Core explizit als nicht supported markiert (Landing-Page):** `Given` der Check-Block auf der Landing-Page, `When` er gelesen wird, `Then` HA Container **und** HA Core sind explizit als **„nicht supported, best-effort ohne Support"** markiert. Formulierung wörtlich aus Epics/FR2.
3. **Install-Warning via `addon/config.yaml`-Deklaration:** `Given` ein Nutzer versucht Solalex auf einer nicht-unterstützten HA-Version zu installieren, `When` der Add-on-Store die Installation prüft, `Then` eine Install-Warning wird gezeigt **And** die supported HA-Version-Range ist in `addon/config.yaml` via `homeassistant:`-Feld deklariert (Mindest-Version-Pin).

## Tasks / Subtasks

- [ ] **Task 1: `addon/config.yaml` um `homeassistant:`-Feld erweitern** (AC: 3)
  - [ ] Voraussetzung: Story 1.1 hat `addon/config.yaml` bereits mit Grundfeldern (name, version, slug, arch, ingress, ingress_port, panel_title, hassio_api, …) angelegt. **Nur erweitern, nicht neu schaffen.**
  - [ ] Feld `homeassistant: "2026.4.0"` (Minimum-Pin) einfügen. Begründung: aktuelle stable HA Core ist 2026.4.3 (Stand April 2026). Minimum auf Patch-Release-Start des aktuellen Minor pinnen, um Lag-Toleranz für Beta-Tester zu gewähren.
  - [ ] Kommentar im YAML: `# Minimum HA Core version — inkompatible Versionen erhalten Install-Warning im Add-on-Store.`
  - [ ] **snake_case-Disziplin** (CLAUDE.md Regel 1): Key ist `homeassistant` (HA-Supervisor-Spec, lowercase — passt zu snake_case). Kein PascalCase, kein camelCase.
  - [ ] **Kein `homeassistant_api`-Setzen in dieser Story** — das wurde in Story 1.1 entschieden. Nicht umschalten.
  - [ ] Manuelle Verifikation: `yq '.homeassistant' addon/config.yaml` liefert die Versions-String.
- [ ] **Task 2: Install-Warning-Smoke-Test dokumentieren** (AC: 3)
  - [ ] **Kein CI-Gate** — HA-Supervisor validiert das Feld beim Install. Reproduktion nur manuell via HA-Test-Instanz möglich.
  - [ ] In `addon/DOCS.md` einen Abschnitt **„Unterstützte HA-Versionen"** ergänzen:
    - Minimum: 2026.4.0
    - Getestet bis: aktuelle stable (zum Release-Zeitpunkt dokumentieren)
    - Supported Installation-Types: **HA OS, HA Supervised**. HA Container und HA Core werden als **nicht supported, best-effort ohne Support** gekennzeichnet.
  - [ ] In `addon/CHANGELOG.md` Eintrag für die Version hinzufügen: `- Minimum HA Core: 2026.4.0 deklariert.`
- [ ] **Task 3: Landing-Page-Content für alkly.de erstellen** (AC: 1, 2)
  - [ ] **Scope-Hinweis für Dev-Agent:** Die Landing-Page lebt **außerhalb dieses Repos** (alkly.de-Marketing-Site). In diesem Repo wird nur der **Content-Baustein als Markdown-Snippet** unter `docs/landing/voraussetzungen.md` abgelegt — damit die Copy-Quelle versioniert ist und per `git mv` beim „Solalex"-Rename mitwandert.
  - [ ] Datei `docs/landing/voraussetzungen.md` neu anlegen mit folgender Struktur (Frontmatter + Markdown-Body):
    ```markdown
    ---
    slug: voraussetzungen
    target_placement: above_every_cta
    required_above: ["install_cta", "download_cta", "waitlist_cta"]
    ---

    ## Voraussetzungen

    > **Benötigt Home Assistant OS oder Supervised.**

    | HA-Installationstyp   | Status                              |
    | --------------------- | ----------------------------------- |
    | Home Assistant OS     | ✅ supported                         |
    | Home Assistant Supervised | ✅ supported                     |
    | Home Assistant Container  | ⚠️ nicht supported, best-effort ohne Support |
    | Home Assistant Core       | ⚠️ nicht supported, best-effort ohne Support |

    Du weißt nicht, welche Variante du hast? Öffne in HA: **Einstellungen → System → Info**.
    ```
  - [ ] **Formulierungen wörtlich aus Epics/FR2 übernehmen** — kein Umformulieren in Marketing-Sprech. Keine emotionalen Adjektive, keine „easy/einfach"-Claims (CLAUDE.md Stil-Leitplanken).
  - [ ] **Glossar-Disziplin** (CLAUDE.md): Der Begriff ist **„Home Assistant OS"** (korrekt ausgeschrieben bei Erstnennung), danach „HA OS" okay. Nie „HAOS".
  - [ ] Alex überträgt den Content manuell auf alkly.de (Marketing-Site-Deployment ist außerhalb dieser Story). Commit in diesem Repo genügt als Abnahme-Beleg.
- [ ] **Task 4: Referenz-Link zwischen Landing-Page und Add-on-Repo** (AC: 1, 2)
  - [ ] In `README.md` (Root) unter „Installation" eine Zeile ergänzen, die auf die Voraussetzungen verweist: `Voraussetzungen: Home Assistant OS oder Supervised. Siehe [docs/landing/voraussetzungen.md](./docs/landing/voraussetzungen.md).`
  - [ ] Keine Inhalts-Duplikation — nur Verweis, damit Single-Source-of-Truth das `voraussetzungen.md`-File bleibt.
- [ ] **Task 5: Smoke-Tests & Final Verification** (AC: 1, 2, 3)
  - [ ] `addon/config.yaml` ist valides YAML (`yq . addon/config.yaml` wirft keinen Fehler).
  - [ ] `homeassistant:`-Feld hat einen Versions-String, der semver-kompatibel zum HA-Supervisor-Pattern ist (`YYYY.M.P`, z. B. `2026.4.0`).
  - [ ] `docs/landing/voraussetzungen.md` existiert, enthält die drei Pflicht-Elemente: „Benötigt HA OS oder Supervised"-Kernzeile, Tabelle mit 4 Install-Typ-Zeilen, Hinweis auf Einstellungen → System → Info.
  - [ ] `addon/DOCS.md` hat Abschnitt „Unterstützte HA-Versionen".
  - [ ] `README.md` verweist auf `docs/landing/voraussetzungen.md`.

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
- **KEIN Marketing-Umformulieren** der Kernzeile „Benötigt Home Assistant OS oder Supervised". Die Formulierung ist in PRD-FR2 **wörtlich gesetzt** und darf nicht in „Unterstützt HA OS / Supervised" o. ä. weichgespült werden. Epic-AC fordert „prominent sichtbar".
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

### File Spec — `docs/landing/voraussetzungen.md` (Copy-Paste-sicher)

```markdown
---
slug: voraussetzungen
target_placement: above_every_cta
required_above: ["install_cta", "download_cta", "waitlist_cta"]
---

## Voraussetzungen

> **Benötigt Home Assistant OS oder Supervised.**

| HA-Installationstyp       | Status                                         |
| ------------------------- | ---------------------------------------------- |
| Home Assistant OS         | ✅ supported                                    |
| Home Assistant Supervised | ✅ supported                                    |
| Home Assistant Container  | ⚠️ nicht supported, best-effort ohne Support |
| Home Assistant Core       | ⚠️ nicht supported, best-effort ohne Support |

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
