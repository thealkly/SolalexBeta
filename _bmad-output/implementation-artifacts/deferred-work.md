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
