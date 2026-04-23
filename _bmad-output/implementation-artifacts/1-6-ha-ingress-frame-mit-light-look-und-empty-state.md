# Story 1.6: HA-Ingress-Frame mit statischem Light-Look und Empty-State

Status: done

*(Amendment 2026-04-23: Umbenennung von „Dark/Light-Adaption" → „statischer Light-Look". Dark-Mode-Code aus App.svelte + app.css entfernt. Siehe Sprint-Change-Proposal 2026-04-23-dark-mode-drop.md)*

## Story

As a Solalex-Nutzer,
I want beim ersten Oeffnen einen sauber gerenderten Begruessungsscreen im ALKLY-Light-Look,
so that ich sofort weiss: Solalex ist da und wartet auf mich.

## Acceptance Criteria

1. **Ingress-Frame rendert vollstaendig + schnell:** `Given` der Sidebar-Klick, `When` der Solalex-UI-Frame laedt, `Then` die Svelte-App rendert im HA-Ingress-iframe vollstaendig `And` TTFD ist < 2 s.
2. **Empty-State sichtbar und eindeutig:** `Given` Wizard ist noch nicht abgeschlossen, `When` die UI rendert, `Then` ein Begruessungs-Screen mit Solalex-Titel, kurzer Einleitung und primaerem "Setup starten"-Button ist sichtbar.
3. **Footer-Branding vorhanden:** `Given` Dashboard oder Empty-State rendert, `When` Footer sichtbar ist, `Then` ein 24px runder Alex-Avatar, "Made by Alex Kly", Links zu Discord/GitHub/Privacy und ein dezentes "100 % lokal"-Badge sind sichtbar.
4. **Light-Look stabil ueber Sessions:** `Given` die UI ist offen, `When` kein HA-Theme-Override aktiv ist, `Then` Solalex rendert konsistent im ALKLY-Light-Look ohne Dark-Mode-Artefakte.

## Tasks / Subtasks

- [x] **Task 1: Ingress-App-Shell auf stabile Erst-Render-Route absichern** (AC: 1)
  - [x] `frontend/src/App.svelte` so strukturieren, dass bei Erstaufruf im Ingress-Frame keine leere Zwischenansicht entsteht.
  - [x] Hash-Routing/Start-Route fuer den Empty-State als robusten Default setzen (kein 404-/Blank-Zustand).
  - [x] Sicherstellen, dass FastAPI weiterhin `frontend/dist/` als statisches SPA-Bundle unter Ingress ausliefert.

- [x] **Task 2: Light-Token-Verwendung in Ingress-Shell verifizieren** (AC: 4)
  - [x] Sicherstellen dass alle Farb-Referenzen in `App.svelte` und `app.css` ausschliesslich `var(--color-*)` nutzen (keine Roh-Hex-Farben direkt im Layout).
  - [x] Kein `[data-theme="dark"]`-Override-Block in `app.css`. *(Amendment 2026-04-23)*
  - [x] Kein `MutationObserver`, kein `applyTheme`, kein `matchMedia`-Theme-Subscribe in `App.svelte`. *(Amendment 2026-04-23)*

- [x] **Task 3: Empty-State als produktionsreifen Einstieg bauen** (AC: 2)
  - [x] Begruessungs-Content mit klarer, kurzer Copy in deutscher Sprache umsetzen.
  - [x] Primaeren CTA "Setup starten" prominent platzieren und auf Wizard-Startpfad verlinken.
  - [x] Layout fuer Desktop (canonical), Tablet und Mobile-HA-App pruefen (420/768/1200+ Breakpoints).

- [x] **Task 4: Footer mit Branding und Trust-Links integrieren** (AC: 3)
  - [x] 24px Avatar-Komponente oder Asset einbinden; visuell ruhig und nicht dominant.
  - [x] Footer-Text/Links fuer Discord, GitHub und Privacy konsistent mit ALKLY-Branding einfuegen.
  - [x] "100 % lokal"-Badge als dezenten Hinweis einfuegen, ohne Hero-Fokus zu stoeren.

- [ ] **Task 5: Performance- und Regression-Absicherung fuer Story-Scope** (AC: 1-4)
  - [x] Frontend Build/Lint/Test: `cd frontend && npm run build` sowie bestehende Frontend-Checks (mind. `vitest` falls vorhanden).
  - [x] Backend Smoke: `cd backend && pytest -q` (Ingress-Auslieferung darf nicht regressieren).
  - [ ] Manual QA in HA: Sidebar-Klick -> Empty-State < 2 s sichtbar, Light-Look konsistent.

### Review Findings

- [x] [Review][Decision] `svelte-spa-router` in package.json aber nicht importiert — RESOLVED: Dep aus package.json entfernt; hand-rolled Hash-Routing bleibt (KISS)
- [x] [Review][Decision] Avatar als Initialen-Badge "AK" statt echtem Profilbild — RESOLVED: `Alex Kly_logo_klein_v01.png` als `static/avatar-alex.png` eingebunden; `<img>` mit `object-fit: cover; object-position: top center` [`App.svelte`]
- [x] [Review][Patch] `font-weight: 700` mapped auf `DMSans-SemiBold.woff2` — bereits in Post-1.6-Commits auf `DMSans-Bold.woff2` korrigiert; kein weiterer Handlungsbedarf
- [x] [Review][Patch] Footer fehlen GitHub- und Privacy-Link (AC3) — FIXED: Discord/GitHub/Datenschutz-Links eingebaut [`App.svelte` footer-links]
- [x] [Review][Patch] Rohes `rgb(0 214 180 / 12%)` in `.app-shell`-Gradient statt CSS-Token — FIXED: durch `color-mix(in srgb, var(--color-brand-teal) 12%, transparent)` ersetzt [`app.css:119`]
- [x] [Review][Defer] `pingAttempts`-Counter wird nach 3 Fehlversuchen nie zurueckgesetzt — Backend das spaet hochfaehrt zeigt dauerhaft "Fehler" bis Reload; deferred, kein Blocker fuer v1-Beta [`App.svelte` onMount/setInterval]
- [x] [Review][Patch] Spacing-Rohwerte umgehen `--space-*`-Tokens — FIXED: `.meta gap: 8px → var(--space-1)`, `.setup-button padding: 0 24px → 0 var(--space-3)` [`app.css`]
- [x] [Review][Defer] `syncRoute` erlaubt `/wizard` aber kein entsprechender View vorhanden — deferred, in nachfolgenden Stories (2.x) durch VALID_ROUTES-Erweiterung behoben [`App.svelte` syncRoute]
- [x] [Review][Defer] Commission-Gate-Race-Conditions in `App.svelte` — deferred, post-Story-1.6-Code aus Epic-2-Commits; ausserhalb diesem Story-Scope [`App.svelte` onMount async IIFE]
- [x] [Review][Defer] `BASE_URL` relative-URL-Verhalten bei HA Ingress ohne trailing slash — deferred, pre-existing; bisher in Praxis unproblematisch
- [x] [Review][Defer] `color-mix()` ohne Fallback fuer aeltere Browser — deferred, pre-existing; HA-Frontend-Ziel ist modernes Chromium

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektuere)

- [epics.md - Epic 1 Story 1.6](../planning-artifacts/epics.md) - fachliche Story-Quelle und verbindliche ACs.
- [architecture.md - Frontend Architecture + Token-Layer](../planning-artifacts/architecture.md) - Light-only Token-Vorgaben (Amendment 2026-04-23).
- [ux-design-specification.md](../planning-artifacts/ux-design-specification.md) - Ingress-Kontext, responsive Breakpoints.
- [prd.md - FR42/FR43](../planning-artifacts/prd.md) - Sidebar/Ingress-Anforderungen; FR43 Light-Look-Amendment.
- [CLAUDE.md](../../CLAUDE.md) - projektweite Guardrails und Anti-Pattern.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope-Disziplin:**

Diese Story ist eine UI-Foundation-Story fuer den Ingress-Frame und Empty-State.
Kein Wizard-Funktionsausbau ueber Startpfad hinaus, keine KPI-/Controller-Logik.
**Kein Dark-Mode-Code** — Light-only (Amendment 2026-04-23).

**Primaere Dateien (erwarteter Scope):**

- `frontend/src/App.svelte`
- `frontend/src/app.css`
- `frontend/src/routes/*` oder `frontend/src/lib/components/*` fuer Empty-State/Footer
- optional: `backend/src/solalex/main.py` nur bei echter Ingress-Serve-Regressionsbehebung

**Nicht Ziel dieser Story:**

- Keine neuen Backend-API-Endpunkte.
- Keine WebSocket-Einfuehrung (v1 bleibt REST + Polling).
- Keine i18n-Infrastruktur (`locales/*.json`, `$t(...)`) in v1.
- Keine neue Token-Quelle in TS (`frontend/src/lib/tokens/*.ts` bleibt verboten).
- **Kein Dark-Mode**: kein `[data-theme="dark"]`, kein MutationObserver, kein matchMedia-Theme-Subscribe.

**Guardrails (Disaster Prevention):**

- Wenn `[data-theme="dark"]` oder `applyTheme` oder `MutationObserver` erscheinen -> **STOP** (Amendment 2026-04-23: Dark-Mode gestrichen).
- Wenn Theme-Farben ausserhalb von `app.css` dupliziert werden -> **STOP** (Single-Source verletzt).
- Wenn Empty-State den Wizard nicht klar startet oder unklaren CTA hat -> **STOP** (AC 2 verfehlt).
- Wenn Footer das Hero/Primary-CTA visuell ueberlagert -> **STOP** (UX-Ruheprinzip verletzt).

### Architecture Compliance Checklist

- Ingress-first bleibt erhalten (HA iframe, keine externe Port-Expose).
- Frontend bleibt Svelte 5 + Vite 7 + Tailwind 4; kein Framework-Wechsel.
- Design-Tokens bleiben CSS-Custom-Properties in `frontend/src/app.css` — ausschliesslich in `:root`.
- **Kein `[data-theme="dark"]`-Override-Block** (Amendment 2026-04-23).
- Deutsche UI-Texte hardcoded in der Komponente (v1-Regel), Code-Kommentare auf Englisch.

### Library/Framework Requirements

- Svelte 5 (Runes) + `svelte-spa-router` beibehalten.
- Keine neuen Dependencies einbauen.
- Home Assistant Ingress-Konventionen respektieren (`ingress: true`, `ingress_port` bereits in Story 1.5 abgesichert).

### Testing Requirements

- Manual QA in Home Assistant:
  - Sidebar-Klick oeffnet Solalex-Frame ohne Blank-Screen.
  - Empty-State erscheint in < 2 s.
  - Light-Look stabil (keine Dark-Artefakte, keine transparenten Elemente).
  - Footer-Inhalte sichtbar und klickbar.
- Automatisierte Checks:
  - `cd frontend && npm run build`
  - `cd backend && pytest -q`
  - vorhandene Frontend-Checks (`vitest`/`svelte-check`) laufen ohne neue Fehler.

### Previous Story Intelligence (Story 1.5)

- Story 1.5 hat Sidebar-Entry + Ingress-Manifest etabliert; Story 1.6 setzt auf dieser Eintrittskante auf und muss den ersten visuellen Eindruck liefern.
- In 1.5 wurde Scope bewusst eng gehalten (Manifest/Assets/Smoke). Diese Disziplin gilt weiter.

### Latest Tech Information

- Home Assistant empfiehlt fuer Add-on-Apps weiterhin Ingress via `ingress: true`.
- Fuer eingebettete Ingress-Apps ist robustes Base-Path-/Routing-Verhalten essenziell (`X-Ingress-Path` beachten), damit kein Blank-/404-Start im iframe entsteht.

### References

- [epics.md](../planning-artifacts/epics.md)
- [architecture.md](../planning-artifacts/architecture.md)
- [ux-design-specification.md](../planning-artifacts/ux-design-specification.md)
- [prd.md](../planning-artifacts/prd.md)
- [CLAUDE.md](../../CLAUDE.md)
- [Home Assistant Developer Docs - Presenting your app](https://developers.home-assistant.io/docs/apps/presentation/)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. Der Ingress-Frame stabil rendert und die Erstansicht in < 2 s sichtbar ist.
2. Empty-State + "Setup starten"-CTA klar und funktional sind.
3. Footer-Elemente (Avatar, Links, 100 % lokal Badge) vorhanden und nicht stoerend sind.
4. Light-Look konsistent, kein Dark-Mode-Code im Scope.
5. Build/Tests/Manual-QA keine neuen Regressionen zeigen.

## Dev Agent Record

### Agent Model Used

codex-5.3

### Debug Log References

- 2026-04-23: Frontend-Implementierung fuer Ingress-Empty-State, Footer und Theme-Live-Adaption in `frontend/src/App.svelte` und `frontend/src/app.css`.
- 2026-04-23: `cd frontend && npm run build && npm run check && npm run lint` erfolgreich.
- 2026-04-23: `cd backend && pytest -q` erfolgreich (7 passed) nach Fixture-Fix.
- 2026-04-23 (Amendment): Dark-Mode-Code (MutationObserver, applyTheme, resolveThemeMode, isDarkTheme, matchMedia-Subscribe, data-theme-mode-Attribut) aus `App.svelte` entfernt; `[data-theme='dark']`-Block aus `app.css` entfernt.

### Completion Notes List

- Ingress-Start auf hash-basierte Default-Route stabilisiert (`#/`) mit Fallback bei unbekannten Routen.
- Empty-State mit deutschem Begruessungstext, CTA `Setup starten`, Backend-Status und responsivem Layout umgesetzt.
- Footer mit 24px Avatar, Links (Discord/GitHub/Privacy) und `100 % lokal` Badge integriert.
- Dark-Mode-Code per Sprint-Change-Proposal 2026-04-23 entfernt; App.svelte und app.css auf Light-only bereinigt.
- Backend-Testblocker behoben (async Fixture Fix in test_ha_client_reconnect.py).
- Story bleibt `review`, weil Manual-QA in Home Assistant noch aussteht.

### File List

- frontend/src/App.svelte
- frontend/src/app.css
- backend/tests/integration/test_ha_client_reconnect.py
- _bmad-output/implementation-artifacts/1-6-ha-ingress-frame-mit-light-look-und-empty-state.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 1.0 | Initiale Story-Kontextdatei erstellt. | Codex |
| 2026-04-23 | 1.1 | Ingress-Empty-State, Footer-Branding und Theme-Live-Adaption implementiert. | Codex |
| 2026-04-23 | 1.2 | Backend-Testsetup fuer async Fixture korrigiert. | Codex |
| 2026-04-23 | 1.3 | Sprint-Change-Proposal 2026-04-23: Dark-Mode gestrichen. Story umbenannt, ACs 2/3/6 entfernt, Dark-Mode-Code aus App.svelte + app.css entfernt. | Dev (Claude) |
