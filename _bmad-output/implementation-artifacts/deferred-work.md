# Deferred Work

Gesammelte Findings aus Reviews, die pre-existing sind oder außerhalb des Story-Scopes liegen. Aus dieser Liste speisen sich Kandidaten für Folge-Stories (Refactors, Tech-Debt-Epics, Security-Hardening).

## Deferred from: code review of 2-5-smart-meter-sign-invert-mit-live-preview (2026-04-25)

- **Vitest „saveDevices wird mit invert_sign aufgerufen" fehlt (AC 12, 4. Bullet)** — happy-dom propagiert `change`-Events auf `<select bind:value>` nicht zurück in Svelte-5-Runen-Setter; Begründung im Config.test.ts-Code-Comment dokumentiert. Abdeckung über Backend-Roundtrip-Test + LivePreviewCard-Isolation + Manual-SR-01. Patch wäre eine andere Test-Strategie (props-mocking statt DOM-driven), Aufwand > Nutzen für Beta. (Frontend `routes/Config.test.ts`.)
- **Vitest „Polling stoppt bei Entity-Wechsel auf leer" partiell** — Mount/Unmount in `LivePreviewCard.test.ts` getestet; der Branch `entityId === ''` → `stopPolling()` direkt nicht. In der Praxis durch `{#if}`-Guard in `Config.svelte` abgefangen, theoretisch aber eigene Pfad. Low-Risk.
- **`get_states`-Roundtrip auf Cache-Miss-Pfad weicht von AC 5 wörtlich ab** — Spec „kein neuer HA-WS-Call"; Cache-Miss zwingt aber zu einem Roundtrip, weil Whitelist-Verifikation sonst nicht möglich ist. Trade-off mit AC 6 bewusst, durch Whitelist-Cache-Patch deutlich entschärft. (Backend `api/routes/setup.py:698`.)
- **`adapter_key`-Wechsel bei gleicher (entity_id, role) wird als `override_only` klassifiziert** — Adapter-Wechsel bei gleicher Entity sollte `commissioned_at` zurücksetzen + Functional-Test erzwingen. Story-2.6-Scope (PUT-Endpoint), nicht 2.5. (Backend `api/routes/devices.py:133-142`.)
- **`override_only`-Branch DELETEt/INSERTet nichts — orphan-rows bei Multi-Row-Schema-Edge-Case** — Pre-existing Schema-Issue (kein UNIQUE-Constraint auf (entity_id, role) sichtbar in der Migration). Nicht Story-2.5-Scope. (Backend `api/routes/devices.py:230-237`.)
- **Mehrere `grid_meter`-Devices: nur das erste wird invertiert; Buffer-Mix möglich** — v1 erlaubt nur ein grid_meter; Multi-Meter ist v1.5+. Aktuell pre-existing Schema-Voraussetzung. (Backend `controller.py:367-396`.)
- **Concurrent PUT + battery-config PATCH: lost-update auf `wr_charge.config_json`** — Generelles Concurrency-Issue auf der DB-Schicht (PUT liest existing außerhalb seiner BEGIN-IMMEDIATE-Transaktion). Story-2.6/3.6-übergreifender Punkt; Mitigation wäre SELECT-FOR-UPDATE-Equivalent oder optimistic-locking-Token. Nicht Story-2.5-Scope. (Backend `api/routes/devices.py:271-303`.)

## Deferred from: code review of 3-6-user-config-min-max-soc-nacht-entlade-zeitfenster (2026-04-25)

- **MULTI-Max-SoC-Fallback nutzt Speicher-Deadband als Drossel-Gate** — `_is_feed_in_after_smoothing()` liest den Speicher-Deadband (`30 W`) als Vorfilter, bevor `_policy_drossel()` ueberhaupt entscheiden darf. Dadurch bleibt Einspeisung zwischen Drossel-Deadband (`10 W`) und Speicher-Deadband ungedrosselt. Deferred, weil dies aus dem gebuendelten Story-3.5-Control-Patch stammt und Story 3.6 laut Scope `_policy_multi` nicht anfassen sollte. Kandidat fuer Story-3.5/3.8-Follow-up.

## Deferred from: code review of story-4-0a-diagnose-schnellexport-db-dump-logs-zip (2026-04-25)

- **Streaming partial ZIP nicht von vollständigem unterscheidbar** — Wenn der Worker mid-stream raised (z. B. Logrotation-TOCTOU oder Disk-Full nach erstem Chunk), sieht der Browser einen erfolgreich abgeschlossenen Download mit korrupter ZIP. Mitigation wäre HTTP-Trailer mit Checksum, vollständige Vor-Bufferung, oder Pre-Flight-`HEAD`-Request mit `Content-Length` aus Pre-Computation — alle außerhalb des Schnellexport-Scopes. (Backend `routes/diagnostics.py` + `diagnostics/export.py`.)
- **Kein Size-Cap für Logs / Multi-GB-DB-Memory-Pressure** — `_write_file_entry` streamt unbegrenzt; bei fehlender Logger-Größenrotation oder Multi-GB-DB kann Export sehr groß / langlaufend werden. Operationelle Sorge, kein Bug. Mitigation wäre Max-Size-Header, frühes Abbrechen oder pre-flight Größenwarnung im Frontend. (Backend `diagnostics/export.py:_write_file_entry`.)

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

## Deferred from: code review of story-2-2-funktionstest-mit-readback-commissioning (2026-04-24)

- **Chart-Datenpunkte pro Tick dupliziert, State-Timestamp ignoriert** (`frontend/src/routes/FunctionalTest.svelte`) — Jeder Poll pusht einen Punkt für jede Entity unabhängig ob sich der State geändert hat → Memory-Wachstum + flache Horizontale. Erfordert Svelte-5-Refactor (`$effect`→`onMount`-Subscribe + Timestamp-basiertes Dedup). Als eigene Frontend-Polish-Story vor Epic 5.
- **`$effect` in FunctionalTest abonniert Polling-Store bei jeder `chartPoints`-Mutation neu** (`frontend/src/routes/FunctionalTest.svelte`) — Effect liest `chartPoints`, reagiert reaktiv, re-subscribet → doppelte Punkt-Inserts. Gehört zum obigen Chart-Refactor (gleicher Code-Bereich, selber Fix-Pass).
- **Fehlende Integration-Tests für POST /api/v1/setup/test** (`backend/tests/integration/test_setup_test.py`) — Happy-Path, Mismatch, Timeout und Concurrency-409 fehlen; Spec Testing-Requirements fordert die 4 Szenarien explizit. `push_state_changed`-Helper in `mock_ha_ws/server.py` ist bereits da. Als eigene Test-Coverage-Story (zusammen mit den zwei nachfolgenden Einträgen).
- **Kein Frontend-Test für Commission-Gate-Redirect** (`frontend/src/App.svelte`) — AC 8 ist der größte Regression-Risk-Punkt (User könnte dauerhaft im Config-Flow festhängen), Fetch-Mock-Test mit `all-commissioned` / `none-commissioned` / `backend-down`-Branches wäre trivial.
- **Kein Test für Subscription-Idempotenz** (`backend/src/solalex/setup/test_session.py`) — `ensure_entity_subscriptions` hat Dedup-Logik, ohne Test würde ein Regression-Re-Subscribe unbemerkt bleiben.

- **`upsert_device` commitet innerhalb Repo-Funktion** (`backend/src/solalex/persistence/repositories/devices.py:788-802`) — pre-existing aus 2.1; Repo-Pattern-Thema (transactional composition), betrifft auch `delete_all` und `mark_all_commissioned`. Cleanup wenn weitere mehrstufige Flows dazukommen.
- **`config_json` ohne JSON-Validierung vor Insert** (`backend/src/solalex/persistence/repositories/devices.py:787-802`) — pre-existing aus 2.1; `config_json` als `str` geht ungeprüft in die DB, fehlerhafter Repr-String korrumpiert die Row. `json.loads(...)` als Pre-Insert-Validation.
- **`/entities`-Endpoint ohne Adapter-spezifische Filterung** (`backend/src/solalex/api/routes/setup.py:133-155`) — pre-existing aus 2.1 (Detection/Filter-Polish v1.5); UoM-Filter allein ist zu breit, würde Auto-Detection-Pfad in v1.5 ergänzt.
- **Module-scope `_app_state_cache` wird im Lifespan neu zugewiesen** (`backend/src/solalex/main.py:47, 672`) — betrifft Test-Reload-Pfade; in Produktion (Single-Instance HA-Add-on) harmlos. Refactor zu `create_app()`-Factory post-Beta, bündelt mehrere Fixture-Smells.
- **Subscription-Leak bei Config-Change** (`backend/src/solalex/setup/test_session.py`) — orphaned `entity_id`-Subscriptions werden beim Reconnect repliziert, auch wenn Device gelöscht wurde. Reconcile-Logik gehört zu Story 3.1-Controller-API-Design (`ensure_controller_subscriptions`-Schwester-Funktion).
- **`ensure_entity_subscriptions` akzeptiert ungenutzten `state_cache`-Parameter** (`backend/src/solalex/setup/test_session.py:890`) — cosmetic, `# noqa: ARG001`. Bei 3.1-Controller-Integration wird die Signatur ohnehin überarbeitet.
- **`StateCache.mark_test_started/ended`/`set_last_command_at` nicht unter Lock** (`backend/src/solalex/state_cache.py:981-988`) — asyncio-single-thread macht das praktisch folgenlos; Konsistenz-Cleanup (alle Mutations async + locked) bei 3.1-StateCache-Erweiterung.
- **Test-Lock-Singleton an Event-Loop gebunden** (`backend/src/solalex/api/routes/setup.py:99-106`) — Test-Fixture-Thema (Workaround via `setup_mod._test_lock = None` bereits im Code). Refactor zusammen mit `create_app()`-Factory.
- **`importlib.reload(main_mod)`-Pattern in Test-Fixtures** (`backend/tests/integration/test_commission.py:1120, test_setup_test.py:1193, test_control_state.py:1250`) — bereits im 1-1-Review als Smell erfasst; `create_app()`-Factory-Refactor löst alle drei Stellen gleichzeitig.
- **Readback-Tolerance ohne Upper-Bound** (`backend/src/solalex/executor/readback.py:455`) — Spec hard-codiert `max(10.0, expected*0.05)` für 2.2; bei 10 kW-WR ergibt das 500 W Toleranz. Cap-Diskussion (`min(500.0, ...)`) für Story 3.2 (Drossel-Policy mit echten Watt-Werten).
- **Globales `_app_state_cache` geteilt zwischen FastAPI-Instanzen** (`backend/src/solalex/main.py:47`) — rein hypothetisch (HA-Add-on startet Single-Instance); wird beim `create_app()`-Factory-Refactor strukturell gelöst.

## Deferred from: code review of story-2-1-hardware-config-page-typ-auswahl-entity-dropdown (2026-04-23)

- **Shelly `_POWER_PATTERN` overmatched Hoymiles `ac_power`-Sensoren** (`backend/src/solalex/adapters/shelly_3em.py:344`) — `detect()` wird in v1 nicht aus UI aufgerufen (AC8-Sub-And); Fix in v1.5 zusammen mit Auto-Detection-Server-Pfad.
- **Marstek `_SOC_PATTERN` regex-Logik zweideutig** (`backend/src/solalex/adapters/marstek_venus.py:259`) — `_SOC_PATTERN = r"^sensor\..+(battery_)?soc$"` macht die optionale Group redundant wegen `.+`-Greedy. Identische Begründung wie Shelly; detect() v1-ungenutzt.
- **`entity_role_map` ist Startup-Snapshot ohne Refresh nach `POST /devices`** (`backend/src/solalex/main.py:1163-1172`) — Controller-/Event-Dispatch-Thema; gehört zu Story 3.1 Core-Controller. Für 2.1 (ohne Control-Pfad) folgenlos. Bei 3.1-Implementierung Map neu bauen nach jedem `POST /api/v1/devices`.
- **`upsert_device` gibt `0` auf UPDATE-Pfad zurück — Contract-Lüge** (`backend/src/solalex/persistence/repositories/devices.py:1407-1422`) — `ON CONFLICT DO UPDATE` liefert `lastrowid` unzuverlässig. Aktueller Caller ignoriert den Return; Cleanup wenn weitere Callers dazukommen (Rückgabetyp präzisieren oder zwei Funktionen `insert_device`/`update_device`).
- **`GET /setup/entities` ohne Pagination/Dedupe bei >500 HA-Entities** (`backend/src/solalex/api/routes/setup.py:692-704`) — Response kann auf grossen HA-Installationen zehntausende Zeilen umfassen. NFR nicht explizit; Beta-Nutzer unwahrscheinlich kritisch. Scale-Nachzug wenn Beta-Feedback oder Perf-Messung es verlangt.
- **Scope-Creep im Bundle-Commit: `POST /setup/test` + `POST /setup/commission` in Story-2.1-Diff** (`backend/src/solalex/api/routes/setup.py:713-851`) — Gehört zu Story 2.2 (Funktionstest) bzw. 2.3 (Commissioning). Offene Findings in diesem Bereich: Lock-TOCTOU-Race (`lock.locked()` vor `async with lock:`), `devices[0]`-Fallback trifft bei Devices-Order-Abweichung eine Non-WR-Row, `str(exc)` leakt in 500-`detail` (potenzielle Token-Exposure), `count if count > 0 else len(devices)` in Commissioning-Response verschleiert Idempotenz, `mark_all_commissioned` schreibt `+00:00`-Suffix während DEFAULT `Z`-Suffix schreibt. Abarbeitung in den jeweiligen Story-Reviews (2.2, 2.3).
- **Scope-Creep im Bundle-Commit: `App.svelte` enthält `/running`+`/disclaimer`-Routes + `getDevices`-Autoforward** (`frontend/src/App.svelte:30, 2299-2313`) — Gehört zu Story 2.3 (Disclaimer) und späterem Running-Screen. Offene Findings: stale `currentRoute`-Read im async-IIFE, Ping-Interval prüft `ac.signal.aborted` nicht. Abarbeitung im 2.3-Review.

## Deferred from: code review of story-3-1-core-controller-mono-modul-sensor-policy-executor-event-source-readback-persistenter-rate-limit (2026-04-24)

- **Check/Reserve/Mark nicht atomic im Dispatcher — TOCTOU** (`backend/src/solalex/executor/rate_limiter.py` + `executor/dispatcher.py`) — Zwei Connection-Scopes (Read bei `check_and_reserve`, Write bei `mark_write` + `control_cycles.insert`). In v1 durch per-device-`asyncio.Lock` im Controller gemildert (Anti-Pattern-Note Z. 260 der Story-Spec akzeptiert das explizit als Pragma). Sauberer Refactor: ein Connection-Scope mit `BEGIN IMMEDIATE` oder SELECT-with-lock. Thema für DB-Hardening-Story post-Beta.
- **Zweite DB-Transaction schlägt fehl nachdem HA-Call erfolgreich war → Ghost-Write** (`backend/src/solalex/executor/dispatcher.py:712-727`) — HA-Hardware wurde beschrieben, `commit` (last_write_at + cycle + latency) schlägt fehl (Disk-Full, DB-Lock). Readback-Mismatch fängt das teilweise ab, aber Rate-Limit-Schutz + Audit-Trail sind weg. Vollständige Lösung: Outbox/Journal-Pattern, 2-Phase-Commit-Protokoll. v2-Reliability-Hardening.
- **Sync-Readback (Hoymiles 15 s) blockiert Per-Device-Lock** (`backend/src/solalex/executor/dispatcher.py:689-696`, adapter `hoymiles.get_readback_timing`) — Während der Readback-Wait schläft, hält der Dispatch-Task den Per-Device-Lock — weitere Events für dasselbe Device stauen sich. Story 3.2+ adressiert Async-Readback-Pfad für OpenDTU/MQTT mit echten State-Subscribes.
- **`NotImplementedError` als semantisches "read-only-adapter"-Signal** (`backend/src/solalex/executor/dispatcher.py` Range-Check-Gate) — Der Catch von `NotImplementedError` als "Adapter ist read-only" ist fragil: jede Typo in einem künftigen Adapter (vergessene Override) wird als read-only maskiert statt als Bug geworfen. Design-Diskussion — sauberer wäre `adapter.supports_write() -> bool` oder eine eigene `ReadOnlyAdapterError`-Klasse.
- **`kpi.record` außerhalb der DB-Transaction des Cycle-Rows → Dual-Write-Skew** (`backend/src/solalex/controller.py:273,321-322`) — Aktuell Noop-Stub, impact null. Sobald Epic 5 die reale KPI-Aggregation einzieht (separate KPI-Tabelle), entsteht ein Konsistenz-Fenster zwischen `control_cycles.insert` (committed) und `kpi.record` (möglicher Crash dazwischen). Adressieren beim Epic-5-Design.
- **`test_direct_calls_no_queue_imports` naive Docstring-Toggle** (`backend/tests/unit/test_controller_dispatch.py:1576-1590`) — Der Architektur-Guard gegen `asyncio.Queue`/`events/bus`/`structlog`/`APScheduler` hat Lücken: Docstring-Opening-auf-Mid-Line (`x = """foo"""`) schließt den Toggle nicht sauber, und Einzeiler-Docstrings mit `#` werden mitgescannt. AST-basierter Scan wäre robust. Test-Quality-Nit, blockiert niemanden.
- **Zwei `Mode`-Definitionen — Enum in `controller.py`, Literal in `persistence/repositories/control_cycles.py` + `latency.py`** — Kosmetische Duplikation; Enum hat 3 Werte, Literal hat 4 (`'idle'`-Extra, per SQL-CHECK erlaubt aber unerreichbar). Wird mit Decision-Item D3 des Reviews aufgelöst (Entweder `'idle'` überall streichen oder `Mode.IDLE` in das Enum aufnehmen und für `_record_noop_cycle` nutzen).
- **Scope-Bleed: Frontend- und Story-2.x-Artefakte im Working-Tree während 3.1-Reviews** (`frontend/src/App.svelte`, `frontend/src/lib/api/client.ts`, `frontend/src/routes/Config.svelte`, `_bmad-output/implementation-artifacts/2-1-*.md` u. a.) — Die uncommitted Änderungen vermischen Backend-3.1-Arbeit mit Frontend-Epic-2-Arbeit in einem Working-Tree. Für den Review explizit ausgeklammert; Commit-Splitting-Disziplin beim nächsten Commit.

## Deferred from: code review of story-2-3-disclaimer-aktivieren (2026-04-24)

- **Hardcoded Route-Strings verteilt** (`frontend/src/App.svelte`, `frontend/src/routes/FunctionalTest.svelte`, `frontend/src/routes/DisclaimerActivation.svelte`) — Route-Literale `"#/disclaimer"`, `"#/functional-test"`, `"#/running"` verstreut; Typo → stilles Routing-Fallback. Route-Const-Module (`lib/routes.ts`) wäre eigene Refactor-Story, unabhängig von 2.3.
- **Keine Idempotency-Key / CSRF auf `POST /api/v1/setup/commission`** (`frontend/src/routes/DisclaimerActivation.svelte` + Backend) — Commissioning ist State-Transition; Frontend-`committing`-Flag ist nur in-memory. Backend-Thema für Epic 7 (Lizenz); im HA-Ingress-Context (isolierter Panel-Iframe) aktuell niedrige Prio.
- **Gradient/Shadow-Tokens im Activate-Button dupliziert aus FunctionalTest.svelte** (`frontend/src/routes/DisclaimerActivation.svelte` — `.activate-button`-CSS) — Zwei Copies der „primären Aktion"-Optik; Epic 5 Dashboard-Shell braucht dieselbe primäre Button-Variante. Gemeinsame Button-Komponente als Design-System-Story.
- **Back-Link via `href="#/functional-test"` pollutet Browser-History-Stack** (`frontend/src/routes/DisclaimerActivation.svelte` — Back-Link) — Push statt Replace-State lässt `history.back()` durch eigene Wizard-Historie hampeln. `history.replaceState` oder `<button onclick={history.back}>` wäre sauberer. Pre-existing Muster auch in FunctionalTest.svelte.
- **`res.json()`-Rejection auf 2xx unbehandelt in `client.ts`** (`frontend/src/lib/api/client.ts`) — pre-existing aus Story 2.1; Malformed-JSON-Response auf 2xx wirft unhandled Promise-Rejection. Betrifft alle Endpoints, nicht spezifisch 2.3.
- **D5: Write-Amplification `_record_noop_cycle` bei jedem Event** (`backend/src/solalex/controller.py:162-172`) — Controller schreibt pro non-solalex-Event eine `control_cycles`-Row, auch bei Policy-Noop. Shelly 3EM @ 1-2 Hz → ~30-86k Rows/Tag/Device. Spec Z. 328 deferriert Deadband explizit auf Story 3.2/3.4, Retention auf 4.4. Alex hat gegen frühen Eingriff entschieden — Storage-Volumen für Beta nicht blocker-kritisch, 3.2/3.4 werden Deadband in die Policies einziehen, 4.4 die 30-Tage-Retention umsetzen.
- **Unbounded Dispatch-Task-Backlog im Controller** (`backend/src/solalex/controller.py:178-184`) — Bursty Sensor-Events + langer Readback können Tausende wartende Tasks hinter dem `asyncio.Lock` aufstauen. In v1 durch 1 Hz/Device Normal-Betrieb + <20 Tasks im Worst-Case akzeptabel. Saubere Lösung (bounded Queue oder Drop-if-pending-for-device) ist Design-Choice, gehört in eine v2-Scale-Story nach Beta-Feedback.
- **Test-Lücke: concurrent Dispatch pro Device (Stress-Test)** (`backend/tests/unit/test_controller_dispatch.py`) — Per-Device-`asyncio.Lock` ist die einzige Verteidigung gegen gleichzeitige Writes, aber kein expliziter Race-Test. Zwei parallele `on_sensor_update`-Calls → exakt ein `mark_write`, zweiter bekommt `rate_limit`-Veto. Realistisch eigene Test-Coverage-Story vor Epic 4.

## Deferred from: code review of story-3-2-drossel-modus-wr-limit-regelung-fuer-nulleinspeisung (2026-04-24)

- **`_drossel_buffers` wächst unbounded + `device.id`-Key bei SQLite-rowid-Recycling** (`backend/src/solalex/controller.py`) — v1 hat ein stabiles `grid_meter`, Device-Recommission verlangt Restart. Post-Beta Scale-Hardening-Thema (key per `(id, entity_id)`-Tuple oder Eviction beim Config-Change-Hook).
- **`_read_current_wr_limit_w` rebuildet `HaState` pro Event** (`backend/src/solalex/controller.py`) — Hot-Path-Overhead messbar, aber deutlich unter dem < 1 ms Policy-Budget. Cache/Memo erst wenn Perf-Messung es verlangt.
- **`buf.maxlen != params.smoothing_window` rebuild verwirft In-Memory-Samples ohne Log** (`backend/src/solalex/controller.py`) — params sind Code-Konstanten, in Praxis tritt der Pfad nie ein; bleibt Defensive-Code ohne Handlungsbedarf.
- **`min_step` wird nach `_clamp_step` geprüft** (`backend/src/solalex/controller.py`) — Bei pathologischer Config (`clamp < min_step`) werden alle Decisions silent dropped. Invariant-Validation in `DrosselParams.__post_init__` (siehe Patch-Finding) deckt das indirekt; ordering-Refactor ist Nice-to-have.
- **Tests rufen `_policy_drossel` direkt statt über `on_sensor_update`** (`backend/tests/unit/test_controller_drossel_policy.py`) — Dispatch-Kette nur durch AC 9 exerziert. Integration-Test-Pass in späterer Story (3.5 Mode-Selector oder eigene Integration-Story vor Beta).
- **`state_cache.last_states` Read ohne Lock** (`backend/src/solalex/controller.py`) — pre-existing aus 3.1, asyncio-single-thread mildert. StateCache-Lock-Refactor bei 3.1-StateCache-Erweiterung.
- **`_read_current_wr_limit_w` keine eigene Unavailable/Unknown-Filter** (`backend/src/solalex/controller.py`) — `parse_readback` handhabt Sentinels in `executor/readback.py`; doppelt-prüfen bei späterem Adapter-Refactor.
- **Observability-Minors: `grid_meter.device.id is None`, `device.role is None`, `wr_device.adapter_key unknown`** (`backend/src/solalex/controller.py`) — jeder liefert `None` korrekt, aber kein Warn-Log. Aufnehmen in späteren Observability-Pass (Story 4.1/4.2 Diagnose-Route).
- **`usePolling` `epoch++` in `stop()` UND in `start()`** (`frontend/src/lib/polling/usePolling.ts`) — Token-Bump um 2 pro `start()`, korrektheits-neutral; Kommentar-Drift „each `start()` increments".
- **`usePolling` kein `inFlight`-Guard bei langsamem Backend** (`frontend/src/lib/polling/usePolling.ts`) — wenn `fetchFn` länger als `intervalMs` braucht, stapeln sich parallele Requests. Frontend-Polish-Thema vor Epic 5.
- **`window.location.hash = '#/running'` ohne verifizierte Route-Registrierung** (`frontend/src/routes/DisclaimerActivation.svelte`) — frontend out-of-3.2-scope; Route-Hygiene in Epic 5 (wenn Running-Screen gebaut wird).
- **Mehrere `hoymiles wr_limit`-Devices kommissioniert → nur `[0]` getestet** (`backend/src/solalex/api/routes/setup.py`) — setup.py out-of-3.2-scope; v1 erlaubt max 1 pro Rolle laut PRD, SQLite erzwingt es aber nicht.
- **Readback `_CLOCK_DRIFT_TOLERANCE_S` einseitig angewendet** (`backend/src/solalex/executor/readback.py`) — readback.py out-of-3.2-scope; Tolerance in eine Richtung macht Drift in die andere Richtung stumm.
- **`routes/setup.py` TOCTOU `lock.locked()` + `async with lock`** (`backend/src/solalex/api/routes/setup.py`) — setup.py out-of-3.2-scope; asyncio-single-thread mildert, aber Refactor zu `lock.acquire(blocking=False)` wäre robuster gegen künftige `await`-Insertions.
- **`routes/setup.py` nested try/except log-Semantik** (`backend/src/solalex/api/routes/setup.py`) — `functional_test_complete` kann auch bei failed-readback feuern, weil der Info-Log außerhalb des Readback-Status-Zweigs liegt. Out-of-3.2-scope.
- **`devices_by_role` einmalig im Lifespan, kein Runtime-Refresh** (`backend/src/solalex/main.py`) — explizit per Story „Hot-Reload NICHT in 3.2". Bei Wizard-Re-Commission (Story 3.6+ oder 2.x-Update) nachziehen, sonst regelt der Controller gegen stale Device-Referenz.

## Deferred from: code review of story-2-3a-pre-setup-disclaimer-gate (2026-04-24)

- **Flash-of-wrong-content bei direktem URL-Hit auf `#/config`** (`frontend/src/App.svelte` onMount IIFE) — Gate-Redirect läuft erst nach `getDevices()`-Resolve; User sieht kurz Config-Internals, bevor umgeleitet wird. UX-Polish, kein Verhaltensbug; synchroner Pre-Gate in einer Service-Shell vor dem `await` würde das fixen, ist aber Architektur-Change.
- **Layout-Shift + fehlendes Focus-Management beim Einblenden des „Weiter"-Buttons** (`frontend/src/routes/PreSetupDisclaimer.svelte:44-46`) — Keyboard-User bleiben nach Checkbox-Space auf der Checkbox, Screenreader bekommen keinen `aria-live`-Announce für den neu eingeblendeten Button. a11y-Polish; AC 4 erzwingt das „Disabled-State = ausblenden"-Pattern explizit.
- **Test-`normalize` dekodiert keine HTML-Entities** (`frontend/src/routes/PreSetupDisclaimer.test.ts:6-8`) — `html.replace(/\s+/g, ' ')` macht die Verbatim-Assertions brüchig, sobald Svelte SSR einen Umlaut als `&auml;` escaped. Aktuell nicht getriggert.
- **localStorage-Key `solalex_pre_disclaimer_accepted` ohne Versions-Schema** (`frontend/src/App.svelte`, `frontend/src/routes/PreSetupDisclaimer.svelte`) — Zukünftige Disclaimer-Text-Änderung kann Accept nicht invalidieren. Epic 7 (Lizenz) migriert ohnehin nach `/data/license.json`; bis dahin bleibt das v1-Verhalten akzeptiert.
- **`backendStatus`-Race: `ping()`-Resolve vs. getDevices-Catch** (`frontend/src/App.svelte:68,118`) — Wenn getDevices fehlschlägt und gleichzeitig ein laufender `ping()` `'ok'` zurückmeldet, kann der Status-Chip fälschlich „verbunden" zeigen. Pre-existing Pattern, minor UX-Inkonsistenz.
- **Dichte Early-Return-Folge im `allCommissioned`-Block** (`frontend/src/App.svelte:76-105`) — Drei Returns in Reihe sind lesbar, aber eng. Refactor-Kandidat (z. B. Extraktion der Gate-Logik in benannte Funktion), nicht-buggy.
- **Story-File-List nennt die drei out-of-scope-Edits (FunctionalTest-Chart-Guard, Spinner-Removal, App.svelte-Catch-Rewrite) nicht** (`_bmad-output/implementation-artifacts/2-3a-pre-setup-disclaimer-gate.md:82-90, 128`) — Doc-Hygiene; wird mit Decision D2 (Scope-Expansion legitimieren vs. extrahieren) nachgezogen.
- **Manual-QA (AC 1/7/10) ungeprüft, Sprint-Status vorab auf `review`** — Task-5-Checkbox in der Story bleibt bewusst `[ ]`; von Alex auf echter HA-Instanz zu verifizieren, kein automatisierter E2E-Stack in v1.
- **Kein Test für `App.svelte`-Gate-Logik** (`frontend/src/App.svelte:63-140`) — Die sicherheitsrelevanteste Neulogik (Commissioned-Redirect + Pre-Disclaimer-Gate + Route-Fallback) hat Null-Coverage. Wenn v1.5 jsdom + @testing-library/svelte einführt, wäre der Gate der Top-Kandidat für die erste interaktive Testsuite — Teilmenge von Decision D1.

## Deferred from: hotfix RunningPlaceholder „Konfiguration ändern"-Link entfernt (2026-04-24)

- **Post-Commissioning Hardware-Re-Config-Flow fehlt** (`frontend/src/routes/RunningPlaceholder.svelte`, `frontend/src/lib/gate.ts`) — Der „Konfiguration ändern"-Link aus Story 2.2 wurde entfernt, weil der Gate aus Story 2.3a (P1+P2) commissionierte User von `/config` zurück auf `/running` redirected (`/config` ist Teil von `WIZARD_ROUTES`). Konsequenz: User können nach Commissioning ihre Hardware-Auswahl, Entity-Mappings, Min/Max-SoC und Nacht-Fenster nicht mehr ändern, ohne `localStorage` und Devices manuell zu löschen. Story 5.1b plant nur Settings-Tab-Platzhalter (AC: „Folgt in v1.5"), kein echter Edit-Flow. Folge-Story für v1.5 oder Epic 5+: dedizierter „Settings → Hardware ändern"-Flow inkl. Controller-Pause während Edit + Re-Test-Auslösung. Bis dahin ist Re-Setup nur via Add-on-Reinstall / DB-Reset möglich.

Beim Review am 2026-04-23 bewusst aus dem Patch-Batch ausgelassen (siehe Story-2.1-Review-Findings, Abschnitt „Patch"). Damals auf Folge-Stories punted, heute beim Status-Cleanup formal nach deferred-work.md verschoben, weil die Ziel-Stories (3.1) inzwischen `done` sind und die Items sonst durchrutschen würden.

- **`_dispatch_event` schluckt alle Exceptions** (`backend/src/solalex/main.py:1135-1136`) — Review-Verdict: Narrow-Scope braucht Wissen um die konkreten Exception-Klassen, die HA-Wire-Format-Parsing werfen kann. War als Action-Item für Story 3.1 geplant (Controller-Hook-Erweiterung), wurde dort aber nicht adressiert. Konkrete Exception-Klassen identifizieren, `except Exception` einengen, `logger.exception(...)` behalten. Observability-Thema; hängt funktional nicht.
- **Hoymiles-POST-Pfad schluckt Marstek-Felder still** (`backend/src/solalex/api/schemas/devices.py`, `backend/src/solalex/api/routes/devices.py`) — Review-Verdict: saubere Lösung erfordert Pydantic-Sentinel-Pattern (`Annotated[int | _Unset]`) oder eine discriminated union auf `type`. Aktuell schreibt ein Hoymiles-Payload mit versehentlich mitgegebenen `min_soc`/`max_soc`-Feldern keine Warnung, Defaults bleiben korrekt. Low-Risk, aber bleibt als sauberer Refactor offen.
- **Test `test_get_entities_returns_three_categories` testet NICHT den Happy-Path** (`backend/tests/integration/test_setup_entities.py:1777-1810`) — Review-Verdict: substantieller Test-Refactor mit Dependency-Injection-Fixture. Test-Debt für `/api/v1/setup/entities`-Happy-Path; kein Produktionsrisiko, aber eine Regression im Buckets-Filter (WR-Limit/Power/SoC) würde stumm durchrutschen.
- **`_app_state_cache` Double-Init im Module-Scope + Lifespan** — bereits in der 2-2-Deferred-Section (`backend/src/solalex/main.py:47, 672`) erfasst; dort als „Refactor zu `create_app()`-Factory post-Beta" bewertet. Kein eigener Eintrag nötig.

## Deferred from: code review of story-5-1a-live-betriebs-view-post-commissioning-mini-shell (2026-04-24)

- **Polling-Fehler werden im UI nicht sichtbar** (`frontend/src/routes/Running.svelte`) — Review-Verdict: `usePolling.error`-Store wird nicht subscribed → bei Backend-Ausfall/500/Timeout bleibt der letzte Snapshot stehen; Modus-Chip, Cycles, Rate-Limit-Hint zeigen stale Daten ohne sichtbaren Hinweis. Story 5.1a ist bewusst eine Mini-Shell; der system-weite Verbindungs-Status ist Scope von Story 4.3 (Verbindungs-Status-Panel) in Epic 4. Beim Implementieren von 4.3 muss Running.svelte auf die globale Connection-State-Surface umgehängt werden, damit alle Views konsistent reagieren.

## Deferred from: code review of story-3-3-akku-pool-abstraktion-mit-gleichverteilung-soc-aggregation (2026-04-25)

- **`entry.state` non-string defensiver Guard fehlt** (`backend/src/solalex/battery_pool.py:60-64`) — `_is_offline` ruft `entry.state.strip().lower()`. Wenn HA-State irgendwann via Regression als `None`/`int` ankommt, crasht `.strip()` mit `AttributeError`. Aktuell garantiert `HaStateEntry.state: str` den String-Typ, aber kein `isinstance`-Guard im Pool. Defer → ggf. global in `_HA_SENSOR_SENTINELS`-Pattern härten (Pattern-Konsistenz mit Controller).
- **Wall-Clock-Performance-Test flaky-prone** (`backend/tests/unit/test_battery_pool.py:529-543`) — `time.perf_counter_ns()` < 5 ms auf N=8 ist generös, aber CI-Runner-Jitter (free-threaded Py 3.13, GIL-Contention) kann gelegentlich rauschen. Markieren mit `@pytest.mark.benchmark` oder ganz entfernen, wenn rot. Kein Produktionsrisiko, nur Test-Quality-Concern.
- **`SocBreakdown.per_member: dict` veränderbar trotz `frozen=True`** (`backend/src/solalex/battery_pool.py:85-90`) — Konsumenten könnten den Dict mutieren, was die „frozen"-Garantie aushebelt. `types.MappingProxyType(per_member)` oder `tuple[tuple[int, float], ...]` wäre echt-immutable. Niedrige Priorität, da Konsumenten heute nur lesen; relevant ab Story 3.4 (Speicher-Modus konsumiert den Pool).
- **`_object_prefix` kollabiert auf leeren String wenn `object_id == suffix`** (`backend/src/solalex/battery_pool.py:43-57`) — pathologisch (HA-Entity-IDs sind immer länger als Suffix), aber zwei Devices mit `object_id == "_charge_power"` bzw. `"_battery_soc"` würden auf Prefix `""` pairen. Zusätzlicher Guard (`if object_id.endswith(suffix) and len(object_id) > len(suffix)`) wäre 1-Zeilen-Hardening. Sehr niedriges Risiko in der Realität.
- **`config_json` mit `null`/`[]`/Non-Object crasht Lifespan** (`backend/src/solalex/battery_pool.py:155`) — `charge.config()` ruft `json.loads(config_json)`; bei `"null"` returnt `None` und `.get("capacity_wh")` wirft `AttributeError`. `config_json` ist heute interner Upsert-Pfad (kein User-Input), aber v1.5-Wizard kann das ändern. `try/except + isinstance(cfg, dict)`-Guard wäre defensives Hardening; teilweise Überschneidung mit D1 (wenn D1 strict gewählt wird, propagiert dieser Crash auch).

## Deferred from: code review of story-2.4 (2026-04-25)

- **Generic-Inverter `detect()` zu permissiv** (`backend/src/solalex/adapters/generic.py:32-46`) — akzeptiert jedes `number`/`input_number` mit `unit_of_measurement in ("W","kW")` als `wr_limit`-Kandidat. Battery-Setpoint-Sliders, Heizungs-Dimmer, andere W-Helfer werden so als WR-Kandidaten angeboten; mit Closed-Loop-Write auf falsches Entity = Footgun. **Deferred — Beta-Scope. Alex' Entscheidung 2026-04-25: User wählt Entity bewusst, nur Beta.**
- **Generic-Meter `detect()` ohne Sign-Convention-Check** (`backend/src/solalex/adapters/generic_meter.py:29-45`) — akzeptiert jeden `sensor.* W|kW`. WR-AC-Power-Sensoren oder Tibber-Pulse mit umgekehrtem Vorzeichen (positiv=Export) lassen Speicher-Policy ins Gegenteil laufen — positives Feedback statt Regelung. **Deferred — Beta-Scope. Alex' Entscheidung 2026-04-25: nur Beta.**
- **AC15 Manual-QA gegen Alex' echte Hardware noch offen** — Trucki ESPHome `input_number.t2sgf72a29_*` + ESPHome SML `sensor.00_smart_meter_sml_current_load`. Kein Code-Issue, Alex testet manuell vor Beta-Launch.
- **AC14 Smoke-Test-Doku nur oberflächlich verifiziert** (`_bmad-output/qa/manual-tests/smoke-test.md`) — Acceptance Auditor hat Diff-Hunk gesehen aber Inhalt nicht voll ausgelesen. User-Cross-Check empfohlen.
- **Duplicate `entity_id` Detection nicht dedupliziert** (`backend/src/solalex/adapters/generic.py`, `generic_meter.py`) — pre-existing. UNIQUE-Constraint im Save-Layer fängt's, aber Wizard-Dropdown zeigt Dubletten.
- **`HardwareConfigRequest` akzeptiert Marstek-Felder mit `hardware_type='generic'`** (`backend/src/solalex/api/schemas/devices.py`) — `battery_soc_entity_id`, `min_soc`, `max_soc`, `night_*` werden silent geschluckt und gedroppt. Kein Validation-Error. Pre-existing.
- **422-Fehlertext bei legacy `"hoymiles"`-Request ohne Cache-Clear-Hint** — Outdated SPA aus Browser-Cache nach Upgrade bekommt generic Pydantic-422 ohne UX-Hinweis "bitte Browser-Cache leeren". UX-Polish.
- **Marstek-Tile nicht disabled wenn `socEntities.length === 0`** (`frontend/src/routes/Config.svelte:133-141`) — User kann Marstek wählen obwohl Save sowieso disabled bleibt. UX-Polish.
- **Functional-Test Target-Priorität generic > marstek** (`backend/src/solalex/api/routes/setup.py:170-187`) — hybrider Setup (Hoymiles + Marstek) testet nur Inverter, kein UI-Pfad für Marstek-only-Test. Pre-existing edge.
- **`parse_readback` "unavailable"/"unknown" nicht distinkt von Junk-Werten** (`backend/src/solalex/adapters/generic.py:60-66`, `generic_meter.py:53-60`) — beide → `None`. Readback-Layer kann transient (HA temporarily down) nicht von permanent (config-Bug) unterscheiden.

## Deferred from: code review of 4-0-debug-logging-toggle (2026-04-25)

- Kein Test misst tatsächliches Idle-Volumen für AC13 — quantitativ schwer Unit-zu-testen, semantisch durch isEnabledFor-Patches mitgedeckt; in QA-Phase mit echtem Add-on-Run validieren.
- JSONFormatter `repr()`-Fallback verlustbehaftet bei nicht-serialisierbaren Werten [backend/src/solalex/common/logging.py:73-80] — pre-existing pattern, nicht durch diese Story eingeführt.
- `configure_logging` Idempotenz mit ersetzten `root.handlers` [backend/src/solalex/common/logging.py:507-515] — hypothetisch (Uvicorn könnte handlers ersetzen), in HA-Add-on-Kontext kein realistischer Pfad.
- `dispatch_service_call_built` ohne korrespondierenden `dispatch_complete` bei `call_service`-Exception [backend/src/solalex/executor/dispatcher.py:817-823] — orphan-event im Failure-Pfad; Story 4.5 muss korrelieren können.
