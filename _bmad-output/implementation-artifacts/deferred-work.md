# Deferred Work

Gesammelte Findings aus Reviews, die pre-existing sind oder außerhalb des Story-Scopes liegen. Aus dieser Liste speisen sich Kandidaten für Folge-Stories (Refactors, Tech-Debt-Epics, Security-Hardening).

## Deferred from: code review of story-1-1-add-on-skeleton-mit-custom-repository-multi-arch-build (2026-04-22)

- GHA-Actions nicht auf Commit-SHA gepinnt — Supply-Chain-Hardening-Kandidat für Epic 6/7.
- Keine cosign/Image-Attestation, kein SBOM, kein gitleaks/secret-scan in CI — Epic 6/7 Security-Gates.
- Kein `CODEOWNERS`-File — Repo-Admin-Task, nicht Story-1.1-Code.
- `LICENSE`-Text mischt MIT-Warranty-Boilerplate mit proprietären Klauseln — Legal-Review nötig.
- Kein Vitest/Playwright-Frontend-Test (Spec explizit "post-MVP") — später eigene Story im Frontend-Test-Epic.
- `configure_logging`-Unit-Test fehlt (aktuell nur Integration via `conftest.py`) — Test-Coverage-Nachzug.
- Kein SPA-Catch-All-Fallback-Route für Client-Routed Deep-Links — Territory Epic 2 Wizard-Routing.
- `docs_url=None / redoc_url=None / openapi_url=None` — intentional per CLAUDE.md "kein OpenAPI-Codegen".
- Release publiziert `:latest` auch für Prerelease-Tags — Release-Strategie klären nach Beta.
- Release-Tag-Filter `v*.*.*` matcht SemVer-Prerelease-Suffixe wie `v1.0.0-rc.1` nicht — Release-Strategie.
- `release.yml` bumps `repository.yaml` nicht automatisch — Spec erlaubt manuell; Automation ist Nice-to-have.
- `map: []` sperrt Zugriff auf `/share`, `/ssl` — öffnen sobald Feature es braucht.
- Ingress-Port 8099 statisch (Kollisions-Risiko auf Multi-Addon-HA-Instanz) — HA-Supervisor-Konvention akzeptiert.
- Dockerfile frontend-builder-Stage ohne `--platform=$BUILDPLATFORM` — CI-Performance-Optimierung.
- Dockerfile `curl | sh` für uv-Installer — Supply-Chain; Umstieg auf pinned uv-Image (`ghcr.io/astral-sh/uv:0.5.x`).
- Dockerfile baut Frontend neu obwohl CI `frontend/dist` als Artifact hochlädt — redundante Build-Zeit, aufräumen.
- `fastapi[standard]` + separates `uvicorn[standard]` + `websockets` = überlappende Extras — Dep-Hygiene.
- `frontend/tsconfig.json` überschreibt `@tsconfig/svelte`-Base-Keys — post-MVP-Cleanup nach Frontend-Feature-Freeze.
- `importlib.reload(main_mod)` in Test-Fixture ist Smell — auf `create_app()`-Factory refactoren, wenn mehr Tests dazukommen.
- `RotatingFileHandler` + Multi-Worker-Race — aktuell Single-Process-Uvicorn in HA; erst relevant bei Worker-Scale-Out.
- `.editorconfig max_line_length=120` vs Ruff `ignore=["E501"]` — Style-Config-Konsistenz.
- Ruff `per-file-ignores` für tests vs `mypy strict=true` auf tests — Strictness-Alignment.
- Spec-Source-Tree drift (`test_main.py` statt `test_health.py`; `svelte.config.js` fehlt im Source-Tree-Block) — Spec-Doc-Hygiene, beim nächsten Story-Edit mitziehen.
- `log_dir`-Feld in `config.py` nicht in Spec-Task-3 dokumentiert — Spec-Doc-Hygiene.
- Icon/Logo-Größen nicht verifiziert (Platzhalter per Spec) — Story 1.5 liefert finale Assets.
- `homeassistant:`-Min-Version in 1.1-Commit fehlte (in Story 1.2 uncommitted bereits nachgezogen) — beim 1.2-Merge erledigt.
- `repository.yaml` minimal (nur `name`/`url`/`maintainer`) — Doc-Enhancement, niedrige Prio.
- **Port 8099 Single-Source-Refactor** (from Patch P9) — echter DRY würde `addon/config.yaml` → HA-Supervisor-env → Python-Settings → Docker-Compose-Override-Channel bedingen. Für eigene Refactor-Story; vorerst bleibt 8099 als Fallback in Settings + Run-Scripts.
- **Docker `USER`-Directive / Drop-Privileges** (from Patch P18) — HA-Add-on-Konvention fordert root für s6-overlay (PID 1, /data-Mount-Permissions, hassio_api-Token). Drop-Privileges-Patch wäre nicht-trivial (s6 `user=`-Direktiven + /data-Chown + Test auf echter HA-Instanz). Hardening-Story post-Beta.

## Deferred from: code review of story-1-2-landing-page-voraussetzungs-hinweis-ha-versions-range (2026-04-23)

- `homeassistant:`-Pin wirkt nicht für HA Container/Core — DOCS-Formulierung könnte das präzisieren (Install-Warning-Mechanik ist Supervisor-only); low-prio, da Container/Core ohnehin keinen Add-on-Store-Flow hat.
- „Getestet bis 2026.4.3" in `addon/DOCS.md` wird mit jedem HA-Patch veralten — manuelle Bump-Disziplin notwendig. Spec-explicit als „zum Release-Zeitpunkt dokumentieren".
- Kein CI-Gate für Versions-Range-Konsistenz (`homeassistant:`-Pin ≤ Minimum-Doku ≤ „getestet bis") — strukturelles Gate-Thema, Kandidat für v1.5.
- Frontend-H1 (`frontend/src/App.svelte:31`) und FastAPI-`title` (`backend/src/solalex/main.py:88`) halten weiterhin kurzen „Solalex"-Titel, während `panel_title` auf „Solalex by ALKLY" aktualisiert wurde — Branding-Konsistenz-Thema für Story 1.5 (HA-Sidebar-Registrierung mit Alkly-Branding).
- Story-1-1-Patches (`panel_title: Solalex → Solalex by ALKLY`, `schema: {}`, `options: {}` in `addon/config.yaml`) landeten im Story-1-2-Arbeitsbaum statt separat in Story 1.1 committed zu werden. Reason: zu spät committed — Git-Historie auf `main` nicht mehr rückwirkend sauber zu splitten; als akzeptierter Scope-Bleed zu Story 1.1 dokumentiert.

## Deferred from: code review of story-1-3-ha-websocket-foundation-mit-reconnect-logik (2026-04-23)

- `_reconnect_attempt`-Counter wird im AuthError-Pfad nie erhöht (`reconnect.py:98-109`) — Diagnose-Accuracy für Story 4.2 (Fehler-Historie); Reconnect-Korrektheit unbeeinträchtigt.
- `/api/health` kann AttributeError werfen wenn Request vor Lifespan-Startup ankommt (`health.py:25-27`) — im HA-Add-on-Runtime unter uvicorn nicht erreichbar; defensive `getattr(..., default)` wäre Zero-Cost-Hardening.
- Stale `ha_ws_connected=true` wenn der Supervisor-Task silent stirbt (`health.py`, `main.py`) — nach Patch #1 (generic `except Exception` in `run_forever`) größtenteils moot; optionaler Belt-and-Suspenders-Check via `task.done() and task.exception()` für Regression-Schutz.
- Kein Integrationstest für `call_service`-Round-Trip (`tests/integration/test_ha_client_reconnect.py`) — AC5 fordert ihn nicht, aber Mock-Server-Handler existiert und Epic 3 wird `call_service` für Writes nutzen; Test-Coverage-Nachzug vor Epic 3 sinnvoll.
- Client-Swap beim Reconnect exponiert veraltete Referenzen an externe Caller (`reconnect.py:69-72`) — `ReconnectingHaClient.client` gibt die aktuelle Instanz bei Access-Zeit zurück; Epic-3-Controller wird diese Referenz cachen und bei Reconnect auf einen toten Socket schreiben. Braucht Epic-3-API-Design-Entscheidung (alles durch Wrapper routen vs. Lock um `client`-Zugriff).

## Deferred from: code review of story-1-7-i18n-foundation-mit-locales-de-json (2026-04-23)

- Kein CI-Gate sichert i18n-Prohibition dauerhaft ab — keine der 4 Hard-CI-Gates in CLAUDE.md fängt ein späteres `svelte-i18n`-Import oder `$t()`-Call ab; strukturelles Gate-Thema, Kandidat für Epic 6 oder eigene Guardrail-Story.
- Guardrail-Scan umfasst nur `frontend/src`, nicht Backend oder künftige Routen — historischer Scan gegen nahezu leeres `src/`; als Epic-2–5-Routen hinzukommen, bietet der Story-1.7-Scan-Claim keine Schutzwirkung mehr.
- Guardrail deckt nicht alle i18n-Einstiegspunkte ab — Verbot nennt `$t()` und `locales/*.json`, nicht `import { t } from '...'`-Muster, Python-`gettext`/`ngettext`, oder Library-Bootstrap-Calls in `main.ts`; Guardrail-Präzisierung bei v2-Planung nachholen.

## Deferred from: code review of story-1-5 and story-1-6 (2026-04-23)

- AC 3 Story 1.5 (Sidebar-Klick → Ingress-Frame): manuelle QA in echtem HA-Environment noch ausstehend; nicht automatisierbar.
- Cross-Frame-Theme-Limitation: MutationObserver im Ingress-iframe isoliert vom HA-Elterndokument; HA-eigener Theme-Toggle propagiert nicht in den iframe. OS-Level `matchMedia` greift als Fallback. Vertiefung bei konkretem User-Bug-Report oder HA-Ingress-API-Erweiterung.
- Doppeltes hashchange-Event auf initialem Load (ensureDefaultRoute + syncRoute) — harmlos, begrenzt.
- `color-mix()` ohne Browser-Fallback — HA Chromium-Engine, kein praktisches Problem.
- Dark-Mode-Token-Overrides außerhalb `@theme`-Block — funktioniert für `var()`-Nutzung im aktuellen Code; Tailwind-Utilities erst betroffen bei zukünftiger Verwendung, dann nachziehen.
- `subscribe()` in ha_client speichert Payload ohne Server-ACK-Bestätigung — Replay bei Reconnect könnte fehlschlagende Subscriptions persistieren; pre-existing. Epic-3-Controller-API-Design entscheidet ob das ein Problem wird.

## Deferred from: code review of story-1-4-alkly-design-system-foundation-tokens-lokale-dm-sans-pipeline (2026-04-23)

- Font-Pfad `../static/fonts/` weicht vom Spec-Beispiel `./fonts/` ab (`frontend/src/app.css:170-194`) — Dev Agent hat bewusst korrigiert, Vite bundlet korrekt (`dist/assets/DMSans-*.woff2` bestätigt), AC 6 Kern-Intent (keine externen Hosts) ist erfüllt; Spec-Beispielpfad ging von implicit `src/fonts/`-Struktur aus, die nicht existiert. Spec-Doc-Hygiene-Thema, beim nächsten Story-Edit mitziehen.
- Keine `<link rel="preload">`-Hints für kritische Fonts (`frontend/src/app.css:168-198`) — Performance-Optimierung post-MVP; DM Sans ist in `.text-hero` (700er-Weight) Headline-kritisch, Preload reduziert FOUT. Kandidat für Performance-Epic nach Beta.
- `font-display: swap` ohne `size-adjust`/`ascent-override`-Fallback (`frontend/src/app.css:169-174`) — FOUT-Layout-Shift-Optimierung post-MVP; nur relevant falls Layout-Shift-Metrics in HA-Ingress kritisch werden.
- Deep-Link `#/wizard` zeigt Empty-State statt Wizard-Route (`frontend/src/App.svelte:39-41`) — Wizard kommt in Epic 2; `svelte-spa-router` ist dep-seitig vorhanden, aber ungenutzt. Wird mit Epic-2-Wizard-Shell gewired.
- `document.body` theoretisch null bei `observer.observe` (`frontend/src/App.svelte:91-92`) — in HA-Ingress-Kontext nicht reproduzierbar (`onMount` läuft post-paint), SSR nicht genutzt; Defensive-Check wäre Zero-Cost-Hardening falls jemals SSR/JSDOM-Test-Context hinzukommt.

## Deferred from: code review of 1-6-ha-ingress-frame-mit-light-look-und-empty-state (2026-04-23)

- `pingAttempts`-Counter in `App.svelte` wird nach 3 Fehlversuchen nie zurueckgesetzt — Backend das spaet hochfaehrt zeigt nach Retry-Exhaustion dauerhaft "Fehler" bis zum naechsten Page-Reload. Kein Blocker fuer v1-Beta (HA Add-on startet synchron); Low-Prio-Fix oder silent Retry-Reset per Route-Change.
- `syncRoute` erlaubt `/wizard` als Route aber kein View vorhanden — pre-existing in Story-1.6-Code; VALID_ROUTES-Erweiterung und Conditional-Rendering wurde in nachfolgenden Epic-2-Commits nachgezogen. Kein Handlungsbedarf.
- Commission-Gate-Race-Conditions in `App.svelte` (async IIFE in `onMount`) — eingebracht durch Epic-2-Commits nach Story 1.6; mehrere Racing-Szenarien (hashchange vs. Gate-Resolve, `currentRoute`-Staleness, timed deep-link override). Edge-Case-Hunter-Details in Story 2.x; nachholen falls Routing-Bugs in Manual-QA aufschlagen.
- `BASE_URL` relative-URL-Verhalten bei HA Ingress ohne trailing slash — `import.meta.env.BASE_URL` nach `replace(/\/$/, '')` = `'.'`; `fetch('./api/health')` loest korrekt auf solange HA Ingress trailing slash liefert (Standard). Kein akuter Bug; Robustheit-Check wenn HA-Ingress-Pfade kuenftig ohne trailing slash kommen.
- `color-mix()` ohne Fallback fuer aeltere Browser — HA-Frontend-Target ist modernes Chromium (Supervisor-intern); kein praktisches Problem in v1. Re-evaluieren wenn Support-Matrix erweitert wird.

## Deferred from: code review of 1-4-alkly-design-system-foundation-tokens-lokale-dm-sans-pipeline (2026-04-23, Zweiter Review-Zyklus)

- `color-mix()` ohne `@supports`-Fallback (`frontend/src/app.css:127-128, 172-174, 238, 263`) — Redundant zum Story-1.6-Eintrag oben; bleibt Story-1.6-Scope. Fix erst, wenn HA-Companion-Webview-Kompatibilität ein reales Problem wird.
- `.setup-button`-Kontrast auf Gradient-Ende unter WCAG-AA (`frontend/src/app.css:163-180`) — Story-1.6-Scope; Button ist Teal-Gradient mit `--color-button-text: #00120f`. Kontrast-Messung im Browser noch ausstehend. Nicht-blockierend (Button ist CTA, nicht Fließtext).
- `ensureDefaultRoute()` → `hashchange`-Race (`frontend/src/App.svelte:28-32`) — `location.hash = '#/'` feuert vor Listener-Registrierung. In HA-Ingress-Praxis nicht reproduzierbar.
- In-iframe-Navigation via `<a href="#/...">` / `target="_blank"` unter HA-Ingress (`frontend/src/App.svelte:114, 129-131`) — Anchor-vs-Button-Refactor ist größerer Touch, gehört in Epic 2 Routing-Hardening.
- Working-Tree-App.svelte enthält Epic-2-Routing (uncommitted M) — Commission-Gate + 4 Route-Komponenten. Gehört in nächsten Epic-2-Review-Zyklus, sobald committed.

## Deferred from: code review of story-2-1-hardware-config-page-typ-auswahl-entity-dropdown (2026-04-23)

- **Shelly `_POWER_PATTERN` overmatched Hoymiles `ac_power`-Sensoren** (`backend/src/solalex/adapters/shelly_3em.py:344`) — `detect()` wird in v1 nicht aus UI aufgerufen (AC8-Sub-And); Fix in v1.5 zusammen mit Auto-Detection-Server-Pfad.
- **Marstek `_SOC_PATTERN` regex-Logik zweideutig** (`backend/src/solalex/adapters/marstek_venus.py:259`) — `_SOC_PATTERN = r"^sensor\..+(battery_)?soc$"` macht die optionale Group redundant wegen `.+`-Greedy. Identische Begründung wie Shelly; detect() v1-ungenutzt.
- **`entity_role_map` ist Startup-Snapshot ohne Refresh nach `POST /devices`** (`backend/src/solalex/main.py:1163-1172`) — Controller-/Event-Dispatch-Thema; gehört zu Story 3.1 Core-Controller. Für 2.1 (ohne Control-Pfad) folgenlos. Bei 3.1-Implementierung Map neu bauen nach jedem `POST /api/v1/devices`.
- **`upsert_device` gibt `0` auf UPDATE-Pfad zurück — Contract-Lüge** (`backend/src/solalex/persistence/repositories/devices.py:1407-1422`) — `ON CONFLICT DO UPDATE` liefert `lastrowid` unzuverlässig. Aktueller Caller ignoriert den Return; Cleanup wenn weitere Callers dazukommen (Rückgabetyp präzisieren oder zwei Funktionen `insert_device`/`update_device`).
- **`GET /setup/entities` ohne Pagination/Dedupe bei >500 HA-Entities** (`backend/src/solalex/api/routes/setup.py:692-704`) — Response kann auf grossen HA-Installationen zehntausende Zeilen umfassen. NFR nicht explizit; Beta-Nutzer unwahrscheinlich kritisch. Scale-Nachzug wenn Beta-Feedback oder Perf-Messung es verlangt.
- **Scope-Creep im Bundle-Commit: `POST /setup/test` + `POST /setup/commission` in Story-2.1-Diff** (`backend/src/solalex/api/routes/setup.py:713-851`) — Gehört zu Story 2.2 (Funktionstest) bzw. 2.3 (Commissioning). Offene Findings in diesem Bereich: Lock-TOCTOU-Race (`lock.locked()` vor `async with lock:`), `devices[0]`-Fallback trifft bei Devices-Order-Abweichung eine Non-WR-Row, `str(exc)` leakt in 500-`detail` (potenzielle Token-Exposure), `count if count > 0 else len(devices)` in Commissioning-Response verschleiert Idempotenz, `mark_all_commissioned` schreibt `+00:00`-Suffix während DEFAULT `Z`-Suffix schreibt. Abarbeitung in den jeweiligen Story-Reviews (2.2, 2.3).
- **Scope-Creep im Bundle-Commit: `App.svelte` enthält `/running`+`/disclaimer`-Routes + `getDevices`-Autoforward** (`frontend/src/App.svelte:30, 2299-2313`) — Gehört zu Story 2.3 (Disclaimer) und späterem Running-Screen. Offene Findings: stale `currentRoute`-Read im async-IIFE, Ping-Interval prüft `ac.signal.aborted` nicht. Abarbeitung im 2.3-Review.
