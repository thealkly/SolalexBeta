# Story 4.0a: Diagnose-Schnellexport (DB-Dump + Logs als ZIP)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Alex (Support) / Beta-Tester,
I want eine versteckte UI-Route mit einem einzigen Button, der mir einen rohen Diagnose-Schnellexport (atomischer SQLite-Dump + alle aktuellen und rotierten Logs als ZIP) herunterlädt,
so that ich bei einem Beta-Vorfall in einem Klick alle Forensik-Daten ziehe, ohne in den Add-on-Container per SSH einzusteigen, ohne `sqlite3` lokal aufzurufen und ohne auf den vollständigen Diagnose-Tab (Story 4.1) oder den kuratierten Bug-Report-Export (Story 4.5) zu warten.

**Scope-Pflock:** Diese Story ist eine **bewusste Forensik-Schnelltür** zwischen Story 4.0 (Debug-Logging-Toggle) und Story 4.1 (Diagnose-Route mit Letzte 100 Zyklen). Sie baut **keinen** Diagnose-Tab, **keine** Cycle-Liste, **keinen** Verbindungs-Status, **keine** kuratierten Felder, **keinen** Schema-Versions-Export, **keine** Latenz-Auswertung, **keinen** Klipboard-Copy, **keinen** Toast und **kein** GitHub-Issue-Template. Sie liefert genau drei Dinge in einer ZIP: `meta.json`, `solalex.db` (Snapshot), `logs/solalex.log*`. Story 4.5 bleibt unverändert geplant als _kuratierter_ JSON-Export auf Basis von 4.1-4.4 — die zwei Exports sind komplementär (Roh-Forensik vs. Bug-Report-Beilage).

**Architektur-Leitplanken:** Reine FastAPI-Route + Streaming-ZIP via stdlib `zipfile`/`zipstream` — **keine** neue Dependency, **kein** `aiofiles`, **kein** externer ZIP-Builder. DB-Snapshot via SQLite-natives `VACUUM INTO` in eine temporäre Datei unter `/data/.diag/`, danach in den ZIP-Stream gelesen, danach `unlink`. Identisches Atomic-Pattern wie für Story 6.2 vorgesehen, aber Tmp-Pfad und Lebensdauer auf den Request beschränkt — **keine** Vermischung mit dem Backup-Slot. Frontend bleibt im bestehenden hash-routing (`App.svelte`-VALID_ROUTES + If/Else-Render), **kein** `svelte-spa-router`-Refactor, **keine** zusätzliche Lazy-Load-Mechanik. Logging via `get_logger(__name__)` (CLAUDE.md Regel 5). Alle Schreibwege bestehen aus genau einer neuen Backend-Komponente (`diagnostics/export.py`) und einer neuen Svelte-Route (`routes/Diagnostics.svelte`).

**Privacy-Pflock:** Die SQLite-Datei enthält nach heutigem Schema (`001_initial.sql`, `002_control_cycles_latency.sql`) **keine** Auth-Tokens, **keine** Lizenz-Keys, **keine** Passwörter — nur Entity-IDs, Hardware-Config, Cycle-Telemetrie, Latenz-Messungen. Diese Annahme wird im Code als Review-Checkliste dokumentiert (Sanitizing-Test in Tasks). `meta.json` enthält bewusst nur Add-on-Version, Container-Arch, Log-Level, Schema-Version, Timestamp — **keine** Token, **keine** Lizenz-Daten, **keine** WS-Frames. Logs unter `/data/logs/` enthalten gemäß Story 4.0 keine Tokens — das wurde dort als AC dokumentiert; diese Story verlässt sich darauf, ohne separate Sanitizing-Schicht.

## Acceptance Criteria

1. **Versteckte Frontend-Route `/diagnostics`:** `Given` `App.svelte` und das bestehende Hash-Routing, `When` der Nutzer im Browser `#/diagnostics` aufruft, `Then` wird die neue `Diagnostics.svelte`-Route gerendert, **And** `/diagnostics` wurde in `VALID_ROUTES` aufgenommen, **And** es existiert **kein** sichtbarer Nav- oder Footer-Link auf diese Route, **And** kein Gate-Auto-Forward von oder nach `/diagnostics` (`evaluateGate` lässt die Route durch wie eine reguläre Setup-Folge-Route).

2. **Minimale UI ohne Bug-Report-Anspruch:** `Given` `/diagnostics`, `When` die Route gerendert ist, `Then` zeigt sie genau drei sichtbare Elemente: einen Header `Diagnose-Schnellexport`, eine Subline `Versteckte Forensik-Route. Lädt einen rohen Schnappschuss (DB + Logs) als ZIP herunter. Für vollständige Bug-Reports wartet bitte auf den Diagnose-Tab.`, einen einzigen Button `Diagnose exportieren`, **And** **keine** Cycle-Liste, **keine** Statusanzeige, **kein** Spinner, **kein** Toast, **kein** Klipboard-Copy, **keine** Tabellen.

3. **Button löst Download aus:** `Given` der Button auf `/diagnostics`, `When` der Nutzer ihn klickt, `Then` triggert das Frontend einen `GET`-Request gegen `${BASE_URL}/api/v1/diagnostics/export`, **And** der Browser zeigt den Standard-Download-Dialog für die zurückgelieferte ZIP, **And** der Frontend-Code nutzt **keinen** zusätzlichen State, kein `fetch`-Streaming-Hack, sondern den nativen `<a download>`-/`window.location.assign`-Pfad mit dem korrekten Ingress-Base-URL-Prefix.

4. **Backend-Route `GET /api/v1/diagnostics/export`:** `Given` ein laufendes Add-on, `When` die Route aufgerufen wird, `Then` antwortet sie mit HTTP 200, `Content-Type: application/zip`, `Content-Disposition: attachment; filename="solalex-diag_<ISO>.zip"`, `Cache-Control: no-store`, **And** der Response-Body ist eine valide ZIP-Datei, **And** die Route ist über `app.include_router(diagnostics_router)` im Lifespan-Setup von `main.py` registriert.

5. **ZIP-Inhalt = exakt drei Top-Level-Sektionen:** `Given` ein gültiger Export, `When` die ZIP geöffnet wird, `Then` enthält sie auf Top-Level: genau eine Datei `meta.json`, genau eine Datei `solalex.db`, genau ein Verzeichnis `logs/`, **And** **keine** weiteren Top-Level-Einträge, **And** `logs/` enthält nur Dateien matching `solalex.log*` aus `settings.log_dir`.

6. **Atomischer DB-Snapshot via `VACUUM INTO`:** `Given` `settings.db_path` zeigt auf eine WAL-DB mit aktiven Schreibern, `When` der Export läuft, `Then` öffnet er eine **separate** aiosqlite-Verbindung, ruft `VACUUM INTO '<tmp>'` auf einen Pfad unter `/data/.diag/solalex_diag_<ts>.db`, liest die fertige Datei in den ZIP-Stream, **And** löscht die Tmp-Datei sowohl im Erfolgsfall als auch in jedem Fehlerfall (try/finally), **And** **keine** Schemamigrations werden ausgelöst, **And** **keine** PRAGMAs auf der Original-DB werden verändert.

7. **`meta.json` enthält genau diese Felder:** `Given` der Export, `When` `meta.json` aus der ZIP gelesen wird, `Then` ist es ein flaches JSON-Objekt mit den Schlüsseln `ts` (ISO-8601 UTC mit `Z`-Suffix), `addon_version` (String), `container_arch` (String aus `platform.machine()` oder `unknown`), `log_level` (`debug|info|warning|error`), `db_schema_version` (Integer aus `meta`-Tabelle, `0` wenn nicht gesetzt), `db_size_bytes` (Integer), `log_files` (Array von `{name, size_bytes}`-Objekten), **And** **keine** weiteren Schlüssel, **And** **kein** `supervisor_token`, **kein** `license`, **kein** `password`, **kein** `secret`.

8. **Filename-Pattern Windows-kompatibel:** `Given` der `Content-Disposition`-Header, `When` der Dateiname erzeugt wird, `Then` folgt er dem Pattern `solalex-diag_YYYY-MM-DDTHH-MM-SSZ.zip`, **And** statt `:` wird `-` zwischen Stunde, Minute und Sekunde verwendet (Windows verbietet `:` in Dateinamen), **And** der Timestamp ist UTC, sekundengenau, ohne Subsekunden.

9. **Endpoint streamt, ohne den Prozess zu blockieren:** `Given` eine 50-MB-DB und 50 MB rotierter Logs, `When` der Export läuft, `Then` antwortet die Route mit `StreamingResponse` (FastAPI), **And** der Speicher-Footprint des Prozesses während des Exports übersteigt nicht den Gesamtgrößen-Footprint plus konstanten Overhead (kein vollständiges Vor-Buffering aller Bytes im Heap), **And** parallele `/api/v1/control/state`-Polls werden während des Exports weiter beantwortet (nicht-blockierend in der Event-Loop).

10. **Sauberes Failure-Handling:** `Given` `/data/.diag/` ist nicht beschreibbar **oder** `VACUUM INTO` schlägt fehl, `When` der Export-Endpoint diesen Fehler trifft, `Then` gibt er eine RFC 7807 Problem-Response (`application/problem+json`) mit Status 500 und `title="diagnostics_export_failed"` zurück, **And** in `/data/.diag/` bleibt **keine** zerlegbare Tmp-Datei zurück, **And** ein WARNING-Log-Record `diagnostics_export_failed` mit Begründung wird geschrieben (kein Stack-Dump im Response-Body).

11. **Erfolgs-Log mit Metriken:** `Given` ein erfolgreicher Export, `When` der Endpoint mit dem Schreiben fertig ist, `Then` schreibt er genau einen INFO-Record `diagnostics_export_built` mit `extra={zip_size_bytes, db_bytes, log_files_count, duration_ms}`, **And** **kein** Pfad, **kein** Token, **kein** User-Identifier landet im Log.

12. **Add-on-Version durchgereicht:** `Given` `addon/rootfs/etc/services.d/solalex/run`, `When` der Service startet, `Then` exportiert das Run-Script `SOLALEX_ADDON_VERSION` aus `bashio::addon.version`, **And** `Settings` exponiert `addon_version: str` mit Default `"unknown"`, **And** dieser Wert landet in `meta.json`, **And** lokales `uv run uvicorn ...` ohne s6 funktioniert weiter (Default greift).

13. **Privacy-Sanity-Test im Code:** `Given` `tests/unit/test_diagnostics_export.py`, `When` `meta.json` aus dem Export gelesen wird, `Then` assertet der Test, dass die geserialisierten Bytes **keinen** der Strings `supervisor_token`, `license_key`, `password`, `secret` (case-insensitive) enthalten, **And** **kein** Pfad ausserhalb der whitelisted Felder aus AC 7 vorkommt.

14. **Backend-Tests:** `Given` pytest, `When` die Suite läuft, `Then` existieren mindestens: `test_diagnostics_export_builds_zip` (Smoke: Status, Header, ZIP-Entries vorhanden), `test_diagnostics_export_meta_fields` (AC 7), `test_diagnostics_export_filename_windows_compatible` (AC 8), `test_diagnostics_export_cleans_up_on_vacuum_failure` (AC 10), `test_diagnostics_export_no_secrets` (AC 13), **And** alle bestehenden Backend-Tests (≥ 249 nach Story 4.0) bleiben grün.

15. **Frontend-Tests:** `Given` Vitest, `When` die Suite läuft, `Then` existiert `frontend/src/routes/Diagnostics.test.ts` mit mindestens zwei Cases: Route rendert Header + Button (AC 2), Button-Click navigiert zum korrekten Backend-URL inkl. Ingress-Prefix (AC 3), **And** alle bestehenden Frontend-Tests bleiben grün.

16. **CI-Gates grün:** `Given` Ruff, MyPy `--strict`, Pytest, ESLint, svelte-check, Vitest, `When` lokal ausgeführt, `Then` melden alle sechs Tools null Fehler, **And** SQL-Migrations-Ordering-Check bleibt unverändert (diese Story legt **keine** Migration an), **And** Egress-Whitelist-Test bleibt unverändert (diese Story macht **keine** externen Calls).

## Tasks / Subtasks

- [x] **Task 1: `Settings.addon_version` + s6-Run-Export** (AC: 12)
  - [x] `backend/src/solalex/config.py`: `addon_version: str = Field(default="unknown", ...)` ergänzen.
  - [x] `addon/rootfs/etc/services.d/solalex/run`: `bashio::addon.version` lesen und `export SOLALEX_ADDON_VERSION="..."` vor dem `uvicorn`-Start setzen, mit Fallback auf `unknown` bei leerem Wert.
  - [x] Bestehende `SOLALEX_LOG_LEVEL`/`SOLALEX_DB_PATH`/`SOLALEX_PORT`/`PYTHONPATH`-Exports nicht anfassen.
  - [x] `test_config.py` (oder Erweiterung): `SOLALEX_ADDON_VERSION` landet in `Settings.addon_version`.

- [x] **Task 2: `diagnostics/export.py` als reine Factory anlegen** (AC: 5, 6, 7, 9, 10, 11)
  - [x] Neues Verzeichnis `backend/src/solalex/diagnostics/__init__.py`.
  - [x] Neue Datei `backend/src/solalex/diagnostics/export.py` mit:
    - `DIAG_TMP_DIR = Path("/data/.diag")` Konstante.
    - `async def vacuum_into_temp(db_path: Path, tmp_dir: Path, ts: datetime) -> Path` mit aiosqlite-Connection auf der Original-DB, `VACUUM INTO`-Statement auf einen Pfad `tmp_dir / f"solalex_diag_{ts:%Y%m%dT%H%M%SZ}.db"`, return des Pfades.
    - `def build_meta_json(...) -> bytes` (synchron, deterministisch).
    - `async def stream_diagnostic_zip(settings, ts) -> AsyncIterator[bytes]` mit `zipfile.ZipFile` auf einem `io.BytesIO`-Window oder `zipstream-ng` aus stdlib (keine neue Dep — `zipfile` mit Generator-Pattern via `for chunk in ...`).
    - try/finally um den Tmp-DB-Pfad mit `unlink(missing_ok=True)`.
  - [x] **Keine** HA-Calls, **keine** Controller-Berührung, **keine** State-Cache-Reads.
  - [x] Logger via `get_logger(__name__)`, INFO-Record `diagnostics_export_built` am Ende, WARNING-Record `diagnostics_export_failed` im Fehlerpfad.
  - [x] `db_schema_version` aus `meta`-Tabelle lesen (Repository: bestehender `meta.py` falls geeignet, sonst inline-SELECT — keine neue Schema-Migration).

- [x] **Task 3: API-Route + Schema** (AC: 4, 8, 10)
  - [x] Neue Datei `backend/src/solalex/api/routes/diagnostics.py` mit `router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])`.
  - [x] `@router.get("/export")` liefert `StreamingResponse` von `stream_diagnostic_zip(...)` mit `media_type="application/zip"`, `headers={"Content-Disposition": ..., "Cache-Control": "no-store"}`.
  - [x] Filename via Helper `_build_export_filename(ts: datetime) -> str` — testbar isoliert, Windows-kompatibles `:` → `-`-Replace.
  - [x] Bei `OSError`/`sqlite3.Error` während `vacuum_into_temp` → `HTTPException(status_code=500, detail=...)`-Pfad, der durch das bestehende RFC-7807-Middleware in `api/middleware.py` zu `application/problem+json` konvertiert wird.
  - [x] Optional: thin Pydantic-Modell für die Schema-Doku in `api/schemas/diagnostics.py` — **kein** Response-Modell auf der Route (Stream-Response), nur fürs OpenAPI-Doc.

- [x] **Task 4: Router-Registrierung in `main.py`** (AC: 4)
  - [x] `from solalex.api.routes.diagnostics import router as diagnostics_router` ergänzen.
  - [x] `app.include_router(diagnostics_router)` in derselben Reihenfolge wie die übrigen Router (vor dem SPA-Catch-All).
  - [x] **Keine** Lifespan-State-Anhänge (`app.state.diagnostics = ...`) — die Route liest direkt aus `request.app.state.settings` bzw. `get_settings()`.

- [x] **Task 5: Frontend-Route `Diagnostics.svelte`** (AC: 1, 2, 3)
  - [x] Neue Datei `frontend/src/routes/Diagnostics.svelte` mit Header, Subline, einem Button.
  - [x] Button-Klick: `window.location.assign(${import.meta.env.BASE_URL.replace(/\/$/, '')}/api/v1/diagnostics/export)` — kein `fetch`, kein Blob, kein State.
  - [x] Strings deutsch hardcoded (CLAUDE.md — kein i18n in v1).
  - [x] Styling minimal, gleiche Token-Klassen wie `Running.svelte`.

- [x] **Task 6: `App.svelte`-Routing erweitern** (AC: 1)
  - [x] `VALID_ROUTES`-Set um `/diagnostics` ergänzen.
  - [x] Render-Branch im If/Else-Block ergänzen.
  - [x] **Keinen** Footer-Link, **keinen** Nav-Eintrag hinzufügen.
  - [x] `evaluateGate` lässt `/diagnostics` durch — falls `gate.ts` aktuell auf einer Whitelist arbeitet, dort den Pfad ergänzen, damit kein Auto-Forward zur Disclaimer-/Setup-Route stattfindet.

- [x] **Task 7: Backend-Tests** (AC: 13, 14)
  - [x] Neue Datei `backend/tests/unit/test_diagnostics_export.py`.
  - [x] Fixture: tmp `db_path` (mit `meta`+`devices`+`control_cycles`-Schema bereits angelegt), tmp `log_dir` mit `solalex.log` + `solalex.log.1`.
  - [x] `test_diagnostics_export_builds_zip`: Status 200, Content-Type `application/zip`, ZIP enthält `meta.json`, `solalex.db`, `logs/solalex.log`, `logs/solalex.log.1`.
  - [x] `test_diagnostics_export_meta_fields`: keys = exakt die in AC 7 gelisteten.
  - [x] `test_diagnostics_export_filename_windows_compatible`: Header-Pattern matcht `^solalex-diag_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\.zip$`, kein `:` enthalten.
  - [x] `test_diagnostics_export_cleans_up_on_vacuum_failure`: monkeypatch `vacuum_into_temp` → raise; nach Request ist `/data/.diag/` leer und Response ist 500 RFC 7807.
  - [x] `test_diagnostics_export_no_secrets`: ZIP-Bytes zu String dekodieren, `assert "supervisor_token" not in s.lower()` (etc.).

- [x] **Task 8: Frontend-Tests** (AC: 15)
  - [x] Neue Datei `frontend/src/routes/Diagnostics.test.ts`.
  - [x] `renders header and button`: querySelector findet Header und genau einen Button.
  - [x] `button click navigates to export endpoint`: `vi.spyOn(window.location, 'assign')` (oder Stub via `delete window.location` Pattern), Button-Klick, assertedURL endet auf `/api/v1/diagnostics/export`, beginnt mit `BASE_URL`-Prefix.

- [x] **Task 9: CI-Gates lokal grün ziehen** (AC: 16)
  - [x] Backend: `cd backend && uv run ruff check && uv run mypy --strict src && uv run pytest`.
  - [x] Frontend: `cd frontend && npm run lint && npm run check && npm run test`.
  - [x] Egress-Whitelist-Test bleibt unangetastet — diese Story macht keinen externen Call.

## Dev Notes

### Bestehende Implementierung, auf der aufgebaut wird

- `backend/src/solalex/persistence/db.py:18-34` öffnet aiosqlite-Connections mit den vier Standard-PRAGMAs. Für den Export wird **eine zweite, separate Connection** aufgemacht — der `VACUUM INTO`-Pfad muss garantiert auf einer eigenen Connection laufen, weil SQLite `VACUUM INTO` innerhalb einer offenen Transaktion verbietet.
- `backend/src/solalex/main.py:189-310` ist das Lifespan- und Router-Wiring. Settings werden via `get_settings()` aus `solalex.config` gezogen; die neue Route liest direkt von dort, **nicht** aus `app.state` (kein State-Singleton nötig — Settings sind via `lru_cache` Prozess-singleton).
- `backend/src/solalex/api/routes/control.py` ist das stilistische Vorbild: `APIRouter(prefix=...)`, kein Wrapper um die Response, RFC 7807 für Fehler.
- `backend/src/solalex/api/middleware.py` (registriert in `main.py`) konvertiert Exceptions zu `application/problem+json`. Diese Story muss diese Middleware **nicht** anfassen — sie greift automatisch.
- `backend/src/solalex/common/logging.py` exportiert `get_logger`. Story 4.0 hat den Hot-Path schon mit DEBUG-Traces dotiert; diese Story bleibt auf INFO/WARNING (Export ist kein Hot-Path).
- `frontend/src/App.svelte:39-53` hält `VALID_ROUTES` und das If/Else-Render. Bewusst kein `svelte-spa-router`-Refactor in v1 (CLAUDE.md, planning-artifacts/architecture.md).
- `frontend/src/lib/gate.ts` (`evaluateGate`) hat eine Whitelist-Logik für die Setup-Reihenfolge. `/diagnostics` muss **vor** der Disclaimer-/Setup-Reihenfolge auf einen No-Op-Pfad gemappt werden, sonst wirft die Pre-Disclaimer-Logik den User zurück auf `/disclaimer`. Implementierung: Frühe Rückkehr `if (currentRoute === "/diagnostics") return { kind: "stay" }` ganz oben in `evaluateGate`.
- `addon/rootfs/etc/services.d/solalex/run` wurde in Story 4.0 um `bashio::config 'log_level'` erweitert — derselbe Block bekommt jetzt `bashio::addon.version`.

### Anti-Patterns, die diese Story verhindern muss

- **Kein** `aiofiles`, **kein** `zipstream-ng`, **kein** `pyzipper` — stdlib `zipfile` mit `BytesIO`-Chunking reicht.
- **Kein** `tempfile.NamedTemporaryFile` mit `delete=True` für die VACUUM-Datei — auf manchen Container-FS schlägt das fehl. Stattdessen explizit `Path("/data/.diag")` + `unlink(missing_ok=True)` im finally.
- **Kein** Schreiben in `/tmp` — HA-Add-on-Tmpfs ist klein. **Immer** unter `/data/.diag/`.
- **Kein** `app.state.diagnostics = ...` — Settings sind Singleton via `lru_cache`, keine Mutationen.
- **Kein** Wrapper `{data: ..., success: true}` — Stream + RFC 7807 (CLAUDE.md Regel 4).
- **Kein** Nav-/Footer-Link auf `/diagnostics` — bewusst versteckt, die echte Diagnose-UI kommt mit Story 4.1.
- **Keine** Cycle-Liste, **kein** Toast, **kein** „Export kopiert"-Klipboard-Pfad — das ist Scope von Story 4.5.
- **Kein** `i18n`/`$t('...')`-Wrapper — deutsche Strings hardcoded (CLAUDE.md).
- **Keine** SQL-Migration — diese Story ändert das Schema nicht.
- **Kein** `SUPERVISOR_TOKEN`, **kein** Lizenz-State, **kein** Pfad-Dump in `meta.json` oder im Log.

### Test- und Entwicklungs-Hinweise

- `pytest`-Fixture für die Tmp-DB kann den bestehenden `make_db_factory`-Helper aus `backend/tests/unit/_controller_helpers.py` wiederverwenden, sofern er `meta`-Tabelle bereits erzeugt; ansonsten genügt `connection_context` + `await conn.executescript(...)` im Setup.
- ZIP-Inhalts-Asserts via `zipfile.ZipFile(io.BytesIO(response.content))` — `response.content` reicht für unit-tests, der Streaming-Pfad wird durch FastAPI-`TestClient` automatisch gepuffert. **Echtes** Streaming-Verhalten (AC 9) ist nicht via TestClient testbar; ein manueller Smoke-Test mit `curl` reicht hier — als Hinweis im Completion-Notes dokumentieren.
- Privacy-Sanity (AC 13): die ZIP-Bytes als `bytes` lesen und auf die vier Verbots-Strings prüfen reicht. **Keine** semantische Inhalts-Analyse — die DB enthält per Schema keine Tokens.
- Frontend-Test für `window.location.assign`: in jsdom ist `window.location` write-protected; entweder `Object.defineProperty(window, 'location', { value: { assign: vi.fn(), ... } })` oder einen kleinen `navigate.ts`-Wrapper anlegen, den der Test mocken kann. Die Wrapper-Variante ist sauberer und testbar — kein Problem, sie für diese eine Aufrufstelle einzubauen.
- ISO-Timestamp-Helper: `datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%SZ")` — Sekunden ohne Subsekunden, `:` durch `-` ersetzt.

### Project Structure Notes

- Backend bleibt eigenständiges uv-Projekt unter `backend/` (CLAUDE.md — kein Monorepo-Workspace).
- Neues Modul `backend/src/solalex/diagnostics/` parallel zu `executor/`, `kpi/`, `ha_client/`. Aktuell kein Bedarf für Sub-Module — alles in `export.py`. Falls Story 4.1+ später kuratierte Diagnose-Daten dort ablegen, lebt das Modul weiter; falls nicht, bleibt es klein.
- Frontend `routes/Diagnostics.svelte` parallel zu den bestehenden Wizard-/Running-Routen.
- snake_case in API-JSON, Python, SQL; `PascalCase` für Svelte-Komponenten-Datei (CLAUDE.md Regel 1).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5: Diagnose-Export als strukturierter Bug-Report (kippbar)] — abgegrenzte Schwester-Story, bewusst nicht ersetzt
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: Diagnose-Route mit abgesetztem Opening + Letzte 100 Regelzyklen] — Folge-Story, übernimmt die offizielle UI-Surface
- [Source: _bmad-output/planning-artifacts/architecture.md#Backup] — `VACUUM INTO`-Pattern für atomische Snapshots
- [Source: _bmad-output/planning-artifacts/architecture.md#Logging] — stdlib `logging` + `JSONFormatter` (Story 4.0)
- [Source: _bmad-output/planning-artifacts/prd.md#NFR40] — Diagnose-Export-Filename mit Timestamp
- [Source: CLAUDE.md#5 harte Regeln] — JSON ohne Wrapper, snake_case, `get_logger(__name__)`
- [Source: _bmad-output/implementation-artifacts/4-0-debug-logging-toggle-und-hot-path-debug-trace.md] — Vorgänger-Story, etabliert `SOLALEX_LOG_LEVEL`-Pattern für Add-on-Optionen

## Previous Story Intelligence

Story 4.0 (Status `review` zum Zeitpunkt dieser Story-Erstellung) etabliert genau den Mechanismus, auf dem 4.0a aufsetzt:

- **Add-on-Option → Env → Settings**: Story 4.0 hat das Pattern für `SOLALEX_LOG_LEVEL` ausgerollt. Story 4.0a klont es 1:1 für `SOLALEX_ADDON_VERSION`. Die Test-Erweiterungen in `test_config.py` aus 4.0 sind die Vorlage.
- **`get_logger(__name__)`-Disziplin**: Story 4.0 hat alle neuen Call-Sites darauf festgepflockt. 4.0a hält sich daran — kein `print`, kein `logging.getLogger` direkt.
- **Logs unter `/data/logs/`**: Story 4.0 hat dort die `RotatingFileHandler`-Pipeline finalisiert (10 MB / 5 Files). 4.0a liest exakt aus `settings.log_dir`, also genau dieses Verzeichnis.
- **DEBUG-Hot-Path-Records aus Story 4.0**: tauchen automatisch in den exportierten Logs auf, sobald `log_level: debug` aktiv ist und ein Vorfall reproduziert wird. Genau das ist der Workflow „Debug an → Vorfall reproduzieren → Diagnose exportieren" aus dem Epic-4-Briefing.
- **Keine Doppel-Sanitizing**: Story 4.0 AC 14 hat zugesichert, dass DEBUG-Records bereits sicher sind (keine Tokens, keine WS-Frames). 4.0a verlässt sich darauf — kein zusätzlicher Filter im Export-Pfad.
- **Tests via `caplog` und Tmp-Dirs**: das Pattern aus `test_common_logging.py` (Story 4.0) ist die Blaupause für `test_diagnostics_export.py`.

Frühere Epic-3-Learnings, die für diese Story relevant bleiben:

- **WAL-Verträglichkeit**: WAL-Mode + `VACUUM INTO` ist getestet als kompatibel (CLAUDE.md, architecture.md). Diese Story muss das nicht erneut beweisen — der Test prüft nur, dass die Operation atomar abgeschlossen wird.
- **Test-Stabilität bei Lifespan-Wiring**: Story 5.1a hat gezeigt, dass `app.state`-Mutationen im Lifespan-Setup zu Test-Flakiness führen können. 4.0a vermeidet das, indem die Route auf `get_settings()` zugreift statt auf `app.state`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `cd backend && uv run pytest tests/unit/test_config.py -q` — Red/Green für `Settings.addon_version`.
- `cd backend && uv run pytest tests/unit/test_config.py tests/unit/test_diagnostics_export.py -q` — Diagnose-Export-Unit-Suite grün.
- `cd backend && uv run ruff check` — grün.
- `cd backend && uv run mypy --strict src` — grün.
- `cd backend && uv run pytest` — 264 Tests grün.
- `cd frontend && npm run test -- Diagnostics.test.ts gate.test.ts` — fokussierte Frontend-Tests grün.
- `cd frontend && npm run lint` — grün.
- `cd frontend && npm run check` — grün, 0 Errors/Warnings.
- `cd frontend && npm run test` — 56 Tests grün.

### Completion Notes List

- `SOLALEX_ADDON_VERSION` wird im s6-Run-Script aus `bashio::addon.version` exportiert und in `Settings.addon_version` mit Default `unknown` verfügbar gemacht.
- Backend-Export liefert `GET /api/v1/diagnostics/export` als `StreamingResponse` mit Windows-kompatiblem ZIP-Filename, `Cache-Control: no-store`, atomischem SQLite-`VACUUM INTO`-Snapshot unter `/data/.diag/`, allowlisted `meta.json` und `logs/solalex.log*`.
- ZIP-Erzeugung nutzt stdlib `zipfile` über einen kleinen Queue-Writer; der DB-Snapshot wird per `finally` entfernt, Failure vor Response-Start wird als RFC-7807 `diagnostics_export_failed` zurückgegeben.
- Versteckte Frontend-Route `#/diagnostics` rendert nur Header, Subline und Button; Button nutzt native `window.location.assign(...)` zum Download-Endpunkt, ohne Fetch/Blob/State.
- `evaluateGate` lässt `/diagnostics` früh durch; es wurde kein sichtbarer Nav- oder Footer-Link hinzugefügt.
- Manuelles echtes Streaming/Parallel-Polling aus AC 9 ist in Unit-Tests nicht vollständig beweisbar; die Implementierung ist als `StreamingResponse` gebaut und vermeidet Full-Heap-Prebuffering der ZIP über den Queue-Writer.

### File List

- `addon/rootfs/etc/services.d/solalex/run`
- `_bmad-output/implementation-artifacts/4-0a-diagnose-schnellexport-db-dump-logs-zip.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/src/solalex/api/middleware.py`
- `backend/src/solalex/api/routes/diagnostics.py`
- `backend/src/solalex/config.py`
- `backend/src/solalex/diagnostics/__init__.py`
- `backend/src/solalex/diagnostics/export.py`
- `backend/src/solalex/main.py`
- `backend/tests/unit/test_config.py`
- `backend/tests/unit/test_diagnostics_export.py`
- `frontend/src/App.svelte`
- `frontend/src/lib/gate.test.ts`
- `frontend/src/lib/gate.ts`
- `frontend/src/routes/Diagnostics.svelte`
- `frontend/src/routes/Diagnostics.test.ts`

### Review Findings

Code-Review 2026-04-25 (3 parallele Layer: Blind Hunter, Edge Case Hunter, Acceptance Auditor). 13 Patches, 2 Defer, 13 dismissed.

- [x] [Review][Patch] Worker-Thread-Deadlock + Tmp-DB-Leak bei Client-Disconnect [backend/src/solalex/diagnostics/export.py:_QueueWriter.push / _stream_zip_bytes] — `push()` blockiert via `asyncio.run_coroutine_threadsafe(queue.put(item), loop).result()` aus dem Worker-Thread. Bei Client-Disconnect cancelt der Generator-`finally` den `worker_task`, aber `asyncio.to_thread` kann den OS-Thread nicht unterbrechen → Thread-Leak + Tmp-DB bleibt liegen. Fix: `consumer_done`-Flag im `_QueueWriter` setzen; `push` mit `future.result(timeout=…)` + Flag-Check oder `put_nowait` mit Cancel-Sentinel.
- [x] [Review][Patch] Symlink-Exfil über versteckte Route [backend/src/solalex/diagnostics/export.py:_collect_log_files] — `path.is_file()` folgt Symlinks; ein Symlink in `/data/logs/solalex.log.evil → /etc/passwd` würde mitexportiert. Fix: `is_symlink()`-Check und/oder `resolve().is_relative_to(log_dir.resolve())`.
- [x] [Review][Patch] Concurrent-Export-Race auf identischem Tmp-Dateinamen [backend/src/solalex/diagnostics/export.py:_prepare_vacuum_target] — Zwei Requests innerhalb derselben UTC-Sekunde produzieren denselben `solalex_diag_<ts>.db`-Pfad; `unlink(missing_ok=True)` + `VACUUM INTO` löschen sich gegenseitig die Datei mid-stream. Fix: `uuid4().hex[:8]`-Suffix oder PID an den Tmp-Filename hängen.
- [x] [Review][Patch] Logrotation-TOCTOU zwischen `stat()` und `open()` [backend/src/solalex/diagnostics/export.py:_collect_log_files → _write_file_entry] — Logger rotiert zwischen `_collect_log_files` (stat) und `_write_file_entry` (open) → `FileNotFoundError` mid-stream → korrupte ZIP nach bereits gesendetem `meta.json`. Fix: `try/except FileNotFoundError` um den `open()`-Aufruf je File; vanished File überspringen.
- [x] [Review][Patch] `_unlink_missing_ok` schluckt nur `FileNotFoundError`, nicht `PermissionError`/`OSError` [backend/src/solalex/diagnostics/export.py:_unlink_missing_ok] — Auf Read-Only-FS oder bei Disk-Full schlägt das Unlink mit `OSError` fehl; Tmp-Datei bleibt liegen, Cleanup-Branch reraised aus `finally`. Fix: `except OSError` mit `logger.warning("diag_tmp_unlink_failed", …)`.
- [x] [Review][Patch] `await worker_task` maskiert Original-Exception [backend/src/solalex/diagnostics/export.py:_stream_zip_bytes trailing await] — Im Exception-Pfad cancelt `finally` den Worker; das anschließende `await worker_task` reraised `CancelledError` und überschreibt das gerade gehobene `BaseException`. Fix: trailing `await` mit `try: await worker_task except CancelledError: pass`.
- [x] [Review][Patch] `addon_version` whitespace/leerstring kein Fallback [backend/src/solalex/diagnostics/export.py:build_meta_json] — Nur `container_arch` hat `or "unknown"`; `addon_version=" "` oder `""` landet roh in `meta.json`. Fix: `(settings.addon_version or "").strip() or "unknown"`.
- [x] [Review][Patch] Log-Glob `solalex.log*` zu breit [backend/src/solalex/diagnostics/export.py:_collect_log_files] — Matched `solalex.log.bak`, `solalex.log.user-edit`, `solalex.log.1.gz`. Fix: explizit `solalex.log` + `glob("solalex.log.[0-9]*")` mergen.
- [x] [Review][Patch] No-op `await conn.commit()` nach `VACUUM INTO` [backend/src/solalex/diagnostics/export.py:vacuum_into_temp] — `VACUUM INTO` ist auto-commit und kann nicht in einer Transaktion laufen. Fix: Zeile entfernen.
- [x] [Review][Patch] `_read_db_schema_version` schluckt Fehler still → 0 [backend/src/solalex/diagnostics/export.py:_read_db_schema_version] — Bei `sqlite3.Error` (z. B. fehlende `meta`-Tabelle) wird stumm 0 geliefert; Forensik kann „echt 0" nicht von „nicht lesbar" unterscheiden. Fix: `logger.warning("diag_meta_read_failed", error=str(e))` im Except-Branch.
- [x] [Review][Patch] `duration_ms` nur im Erfolgs-Log [backend/src/solalex/diagnostics/export.py:_stream_zip_bytes worker] — Failure-Pfad loggt keine Dauer; für Forensik wertvoll. Fix: zusätzlichen `logger.warning("diagnostics_export_failed", extra={"duration_ms": …})` im Worker-Except-Pfad.
- [x] [Review][Patch] `test_diagnostics_export_cleans_up_on_vacuum_failure` ist trivial-grün [backend/tests/unit/test_diagnostics_export.py:226-239] — Der Mock erstellt und löscht seine eigene Datei vor dem Raise; der echte `_unlink_missing_ok`-Branch im produktiven `vacuum_into_temp` wird nicht exerziert. Fix: Test stattdessen Read-Only-Tmp-Dir simulieren oder reale `vacuum_into_temp`-Funktion mit Permission-Error patchen.
- [x] [Review][Patch] Kein Debounce auf Export-Button → Doppelklick triggert Concurrent-Race [frontend/src/routes/Diagnostics.svelte:exportDiagnostics] — Hängt an Patch #3 (Race auf Tmp-Filename); zusätzlich gute UX. Fix: `disabled`-State nach Klick für 2-3 s, oder Click-Counter mit `event.preventDefault()` für Folgeclicks.
- [x] [Review][Defer] Streaming partial ZIP nicht von vollständigem unterscheidbar [backend/src/solalex/api/routes/diagnostics.py + export.py] — Wenn der Worker mid-stream raised, sieht der Browser einen erfolgreichen Download mit korrupter ZIP. Mitigation wäre HTTP-Trailer/Checksum oder volle Buffering — beides außerhalb des Story-Scopes. Deferred (HTTP/ZIP-Semantik-Limit, kein konkreter Bug).
- [x] [Review][Defer] Kein Size-Cap für Logs / Memory-Pressure bei Multi-GB-DB [backend/src/solalex/diagnostics/export.py:_write_file_entry] — Bei nicht-rotierter Logger-Konfiguration oder sehr großer DB kann Export sehr groß / langlaufend werden. Operationelle Sorge, kein Bug. Deferred.

## Change Log

| Datum      | Änderung                                                                                                                                                                                                                                                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-25 | Story 4.0a implementiert — `SOLALEX_ADDON_VERSION`-Env/Settings, versteckte `/diagnostics`-Route, Backend-ZIP-Export mit atomischem SQLite-Snapshot + Logs + `meta.json`, RFC-7807-Failure-Pfad, Frontend-Button-Download, Gate-Ausnahme und Backend-/Frontend-Tests. CI-Gates: Ruff, MyPy, Pytest, ESLint, svelte-check, Vitest grün. |
| 2026-04-25 | Initial Story-Erstellung Story 4.0a — versteckte Diagnose-Schnellexport-Route mit DB-Dump (atomisch via `VACUUM INTO`) + Logs als ZIP. Schwester-Story zu 4.5 (kuratierter JSON), eingeschoben zwischen 4.0 (review) und 4.1 (backlog). Roher Forensik-Pfad ohne Diagnose-Tab-Abhängigkeit, damit Beta-Vorfälle ab sofort in einem Klick zusammengezogen werden können.    |
