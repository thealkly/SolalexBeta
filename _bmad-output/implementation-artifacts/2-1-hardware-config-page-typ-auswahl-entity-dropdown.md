# Story 2.1: Hardware Config Page — Typ-Auswahl + Entity-Dropdown

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Solalex-Nutzer,
I want eine einfache Konfigurationsseite, auf der ich meinen Hardware-Typ wähle und meine HA-Entities aus einem Dropdown zuweise,
so that Solalex weiß, welche HA-Entities er steuern soll — ohne dass ich Entity-IDs manuell eintippen muss.

## Acceptance Criteria

1. **Einstieg über Empty-State:** `Given` die UI zeigt den Empty-State (Story 1.6, CTA „Setup starten"), `When` der Nutzer den CTA klickt, `Then` die Hardware-Konfigurationsseite unter der Route `#/config` wird geöffnet **And** kein 4-Schritt-Wizard-Flow und keine Auto-Detection-UI sind vorhanden (Amendment 2026-04-23).
2. **`get_states`-Scan populiert Entity-Dropdowns:** `Given` die Hardware-Konfigurationsseite öffnet, `When` sie rendert, `Then` ein einmaliger `get_states`-Call über die bestehende HA-WS-Verbindung (`HaWebSocketClient`) läuft **And** die Response populiert Entity-Dropdowns je HA-Domain-Klasse (WR-Limit: `number.*`; Smart-Meter-Power: `sensor.*` mit `unit_of_measurement` W/kW; Akku-SoC: `sensor.*` mit `unit_of_measurement` %). Jede Option zeigt `entity_id` + `friendly_name`.
3. **Hardware-Typ-Auswahl (Drossel vs. Speicher):** `Given` die Config-Page rendert, `When` der Nutzer eine Hardware-Typ-Kachel klickt, `Then` exakt zwei Optionen sind sichtbar — „Hoymiles / OpenDTU (Drossel-Modus)" und „Marstek Venus 3E/D (Speicher-Modus)" **And** der gewählte Typ bleibt visuell aktiv (eine primäre Aktion pro Screen; UX-DR29).
4. **Pflichtfeld WR-Limit-Entity (beide Pfade):** `Given` der Nutzer wählt einen Hardware-Typ, `When` er die WR-Limit-Entity wählt, `Then` die Auswahl ist Pflichtfeld **And** Speichern bleibt gesperrt, solange kein Wert gesetzt ist.
5. **Akku-Felder bei Marstek Venus:** `Given` der Nutzer wählt Marstek Venus, `When` die Config-Page das Akku-Segment rendert, `Then` Felder für Akku-SoC-Entity (Pflicht, Dropdown), Min-SoC (Default 15 %, Integer 5–50), Max-SoC (Default 95 %, Integer 50–100), Nacht-Entlade-Startzeit (Default 20:00, `HH:MM`) und Nacht-Entlade-Endzeit (Default 06:00, `HH:MM`) erscheinen **And** Nacht-Entlade ist optional (Checkbox „Nacht-Entladung aktivieren"; Default aktiv).
6. **Shelly 3EM als optionaler Smart-Meter-Typ:** `Given` der Nutzer hat Hoymiles oder Marstek gewählt, `When` das Smart-Meter-Segment rendert, `Then` eine optionale Auswahl „Smart Meter (Shelly 3EM)" mit Entity-Dropdown für die Netz-Leistungs-Entity ist sichtbar **And** das Feld kann leer bleiben (KPI-Qualität reduziert sich, aber Setup darf ohne Smart-Meter abgeschlossen werden — siehe Dev Notes).
7. **v1.5-Hinweis für Anker/Generic:** `Given` der Nutzer scrollt im Hardware-Typ-Bereich, `When` er nach weiteren Herstellern sucht, `Then` eine deutsche Info-Zeile „Anker Solix und generische HA-Entities folgen mit v1.5" ist sichtbar **And** keine klickbaren Pfade für Anker/Generic existieren in v1.
8. **Adapter-Registry beim Startup:** `Given` die FastAPI-App startet, `When` der Lifespan-Init läuft, `Then` die statische Registry `ADAPTERS = {"hoymiles": hoymiles, "marstek_venus": marstek_venus, "shelly_3em": shelly_3em}` ist befüllt **And** jedes Modul exportiert die Pflicht-Funktionen `detect()`, `build_set_limit_command()`, `build_set_charge_command()` (Marstek), `parse_readback()`, `get_rate_limit_policy()`, `get_readback_timing()` gemäß `adapters/base.py` Abstract-Interface **And** `detect()` wird in v1 NICHT aus der UI heraus aufgerufen.
9. **Persistente Speicherung via SQLite:** `Given` der Nutzer klickt „Speichern" und alle Pflichtfelder sind gesetzt, `When` die POST-Request verarbeitet wird, `Then` ein Eintrag pro konfiguriertem Gerät wird in der `devices`-Tabelle gespeichert (Primary Key auto, Felder: `id`, `type`, `role`, `entity_id`, `adapter_key`, `config_json`, `last_write_at`, `created_at`, `updated_at`) **And** der Commissioning-Status (`commissioned_at`) bleibt leer (wird erst in Story 2.3 gesetzt).
10. **Weiterleitung zur Funktionstest-Route:** `Given` Speichern war erfolgreich, `When` die Response ankommt, `Then` die UI wechselt auf die Route `#/functional-test` **And** ein Platzhalter-Screen „Funktionstest folgt in Story 2.2" ist dort sichtbar (der echte Funktionstest kommt in Story 2.2).
11. **Adapter-Erweiterbarkeit ohne Refactor:** `Given` das Adapter-Modul-Interface `adapters/base.py` ist stabil, `When` in v1.5+ ein neuer Adapter dazukommt, `Then` nur ein neues Python-Modul in `adapters/` + ein Eintrag in `ADAPTERS` ist nötig — kein JSON-Template-Loader, keine Loader-Änderung, kein Core-Refactor.
12. **RFC-7807-Fehler ohne Wrapper:** `Given` der Nutzer versucht ein Device mit fehlender Pflicht-Entity zu speichern, `When` die API 422 liefert, `Then` der Response-Body ist ein `application/problem+json`-Dokument (RFC 7807) **And** der Frontend-Client zeigt die deutsche Fehler-Meldung mit Handlungsempfehlung (CLAUDE.md Regel 4; UX-DR20).

## Tasks / Subtasks

- [x] **Task 1: Persistence-Foundation anlegen** (AC: 8, 9)
  - [x] Verzeichnis `backend/src/solalex/persistence/` mit `__init__.py` anlegen.
  - [x] `persistence/db.py`: aiosqlite-Connection-Factory mit `PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL` + `PRAGMA foreign_keys=ON`. Exportiere `get_connection() -> aiosqlite.Connection` und `connection_context()` als async-Context-Manager. Path aus `config.py` (`database_path: Path = Path("/data/solalex.db")`) lesen; für Tests per `PYTEST_DATABASE_PATH`-Env-Override. Parent-Dir bei Bedarf anlegen.
  - [x] `persistence/migrate.py`: Beim Startup `schema_version` aus `meta`-Tabelle lesen (0, falls Tabelle fehlt). Alle `sql/NNN_*.sql`-Files in aufsteigender Reihenfolge einlesen, in EINER Transaktion auf die DB anwenden, `schema_version` hochzählen. Lücken in der Nummerierung → `RuntimeError` beim Startup (CI-Gate: `sql/NNN_*.sql`-Ordering-Check). Logging via `get_logger(__name__)`.
  - [x] `persistence/sql/001_initial.sql`: Erstelle Tabellen `meta` (key TEXT PRIMARY KEY, value TEXT NOT NULL) und `devices` (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, role TEXT NOT NULL, entity_id TEXT NOT NULL, adapter_key TEXT NOT NULL, config_json TEXT NOT NULL DEFAULT '{}', last_write_at TIMESTAMP, commissioned_at TIMESTAMP, created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))). Füge `INSERT INTO meta (key, value) VALUES ('schema_version', '1')` hinzu. UNIQUE(`entity_id`, `role`)-Constraint für Idempotenz beim Re-Save.
  - [x] `persistence/repositories/__init__.py` anlegen.
  - [x] `persistence/repositories/meta.py`: `async def get_meta(conn, key) -> str | None` und `async def set_meta(conn, key, value)`.
  - [x] `persistence/repositories/devices.py`: `async def list_devices(conn)`, `async def upsert_device(conn, DeviceRecord) -> int`, `async def get_by_id(conn, id) -> DeviceRecord | None`, `async def delete_all(conn)` (für Re-Config).
  - [x] Lifespan in `main.py` erweitern: VOR `ReconnectingHaClient`-Task die Migration laufen lassen (`await migrate.run(db_path)`), Ergebnis loggen (`schema_version_applied`).

- [x] **Task 2: Adapter-Foundation (`backend/src/solalex/adapters/`)** (AC: 8, 11)
  - [x] Verzeichnis `backend/src/solalex/adapters/` mit `__init__.py` anlegen. `__init__.py` exportiert `ADAPTERS`-Registry und Abstract-Interface-Typen.
  - [x] `adapters/base.py`: Python-`Protocol` (oder `abc.ABC`) mit Pflicht-Methoden:
    - `detect(ha_states: list[HaState]) -> list[DetectedDevice]` — pattern-match auf Entity-IDs/Attributes. In v1 NICHT aus UI gerufen (nur Interface).
    - `build_set_limit_command(device: DeviceRecord, watts: int) -> HaServiceCall` (für WR-Adapter) — raised `NotImplementedError` in Nicht-WR-Adaptern.
    - `build_set_charge_command(device: DeviceRecord, watts: int) -> HaServiceCall` (für Akku-Adapter) — raised `NotImplementedError` in Nicht-Akku-Adaptern.
    - `parse_readback(state: HaState) -> int | None` — Watt-Wert aus HA-State extrahieren.
    - `get_rate_limit_policy() -> RateLimitPolicy` — mind. `min_interval_s: float` (Default 60.0).
    - `get_readback_timing() -> ReadbackTiming` — `timeout_s: float`, `mode: Literal["sync", "async"]`.
  - [x] Datenklassen als Pydantic-Models oder `@dataclass`: `HaState`, `DetectedDevice`, `HaServiceCall` (domain/service/service_data), `RateLimitPolicy`, `ReadbackTiming`, `DeviceRecord`.
  - [x] `adapters/hoymiles.py`: Hardcoded Entity-Pattern-Listen für OpenDTU-Entities (`number.*_limit_nonpersistent_absolute` für WR-Limit, `sensor.*_ac_power` für Leistung). `build_set_limit_command` → `HaServiceCall(domain="number", service="set_value", service_data={"entity_id": device.entity_id, "value": watts})`. `build_set_charge_command` raised `NotImplementedError`. Rate-Limit 60 s, Readback sync mit Timeout 15 s (Hoymiles-DTU-Latenz).
  - [x] `adapters/marstek_venus.py`: Hardcoded Pattern-Listen für Marstek Venus 3E/D (`number.*_charge_power`, `sensor.*_soc`, `sensor.*_power`). `build_set_charge_command` → entsprechender `number.set_value`-Call. `build_set_limit_command` raised `NotImplementedError`. Rate-Limit 60 s, Readback sync 30 s (Marstek lokale API).
  - [x] `adapters/shelly_3em.py`: Hardcoded Pattern-Listen für Shelly 3EM (`sensor.*_power`, `sensor.*_total_power`). READ-ONLY: `build_set_limit_command` und `build_set_charge_command` raised `NotImplementedError`. `parse_readback` liefert Netz-Leistung (W, positiv = Bezug, negativ = Einspeisung). `get_rate_limit_policy` irrelevant (kein Write), trotzdem implementieren.
  - [x] `adapters/__init__.py`: `ADAPTERS: dict[str, Adapter] = {"hoymiles": hoymiles, "marstek_venus": marstek_venus, "shelly_3em": shelly_3em}`.
  - [x] Unit-Tests in `backend/tests/unit/test_adapters.py`: Registry enthält alle 3 Keys; jeder Adapter erfüllt das `base.Adapter`-Protokoll; `build_set_limit_command` für Hoymiles liefert korrekten `HaServiceCall`; `parse_readback` für Shelly mit Sample-State liefert Watt-Wert.

- [x] **Task 3: HA-Client um `get_states` erweitern** (AC: 2)
  - [x] In `backend/src/solalex/ha_client/client.py` Methode `async def get_states(self) -> list[dict[str, Any]]` ergänzen:
    - Sendet `{"id": next_id, "type": "get_states"}` über bestehende WS-Connection.
    - Nutzt die `_pending_results`-Machinerie (wie `call_service`) auf `msg_id` und wartet via `asyncio.wait_for(future, timeout=10.0)`.
    - Bei `success=false` im Result → `RuntimeError` mit HA-Error-Message.
    - Response-Shape: `list[dict]` mit je `entity_id`, `state`, `attributes` (inkl. `friendly_name`, `unit_of_measurement`, etc.). Siehe HA-WS-Spec.
    - Logging via `get_logger(__name__)`, kein `print`.
  - [x] Pydantic-Schema `HaState` in `backend/src/solalex/api/schemas/ha_state.py` anlegen: `entity_id: str`, `state: str`, `attributes: dict[str, Any]`. Wird von Adaptern + Setup-Route geteilt.
  - [x] Test-Erweiterung: `backend/tests/integration/mock_ha_ws/server.py` um Handler für `get_states`-Type erweitern (liefert Mock-States-Liste). Neuer Integration-Test in `test_ha_client_reconnect.py` oder eigener `test_ha_client_get_states.py`: nach Auth ruft `client.get_states()` → liefert die Mock-States.

- [x] **Task 4: Setup-Route `GET /api/v1/setup/entities`** (AC: 2)
  - [x] Neue Route in `backend/src/solalex/api/routes/setup.py` anlegen (`router = APIRouter(prefix="/api/v1/setup", tags=["setup"])`, in `main.py` einbinden).
  - [x] Endpoint `GET /api/v1/setup/entities`:
    - Ruft `await request.app.state.ha_client.get_states()` auf (über `ReconnectingHaClient.client`-Property — Achtung: Deferred-Work `client-swap beim Reconnect` ist bekannt; für Story 2.1 reicht ein One-Shot-Call, Caller wiederholt bei Fehler).
    - Filtert States in drei Klassen:
      - `wr_limit_entities`: `entity_id` startet mit `number.` UND `attributes.unit_of_measurement in ("W", "kW", "%")` (Hoymiles-Limit ist oft `%` oder `W`).
      - `power_entities`: `entity_id` startet mit `sensor.` UND `unit_of_measurement in ("W", "kW")`.
      - `soc_entities`: `entity_id` startet mit `sensor.` UND `unit_of_measurement == "%"`.
    - Response-Shape (direktes JSON-Objekt, kein Wrapper, CLAUDE.md Regel 4):
      ```json
      {
        "wr_limit_entities": [{"entity_id": "number.opendtu_limit_nonpersistent_absolute", "friendly_name": "OpenDTU Limit"}],
        "power_entities": [{"entity_id": "sensor.shelly_3em_total_power", "friendly_name": "Shelly 3EM Total Power"}],
        "soc_entities": [{"entity_id": "sensor.marstek_venus_soc", "friendly_name": "Marstek Venus SoC"}]
      }
      ```
    - Bei fehlender HA-WS-Verbindung (`ha_ws_connected=false`) → 503 mit RFC-7807-Payload (`type`: `urn:solalex:ha-unavailable`, `title`: "Home Assistant nicht erreichbar", `detail`: deutsche Handlungsempfehlung).
  - [x] Pydantic-Response-Model in `api/schemas/setup.py`.

- [x] **Task 5: Device-Route `GET/POST /api/v1/devices`** (AC: 9, 12)
  - [x] Neue Route in `backend/src/solalex/api/routes/devices.py`.
  - [x] `POST /api/v1/devices` — Request-Body ist ein Config-Objekt (siehe Pydantic-Schema `HardwareConfigRequest` unten), NICHT eine Liste — die Route übernimmt das Splitten in mehrere `devices`-Rows. Ablauf:
    1. Request validieren (Pydantic). Fehler → FastAPI liefert RFC-7807 (via Middleware, siehe Task 6).
    2. Alle bisherigen Einträge in `devices` löschen (`delete_all` — Config-Page ist autoritativ, Re-Save überschreibt komplett).
    3. Je nach `hardware_type`:
       - `hoymiles`: 1 Row (role=`wr_limit`, adapter_key=`hoymiles`, entity_id=Request, config_json=`{}`).
       - `marstek_venus`: 2 Rows (role=`wr_charge` für charge-entity, role=`battery_soc` für soc-entity). `config_json` enthält `{"min_soc": ..., "max_soc": ..., "night_discharge_enabled": ..., "night_start": "20:00", "night_end": "06:00"}` auf der `wr_charge`-Row.
       - Optional Shelly 3EM: 1 Row (role=`grid_meter`, adapter_key=`shelly_3em`).
    4. Response: `{"status": "saved", "device_count": <int>, "next_action": "functional_test"}` (201 Created).
  - [x] `GET /api/v1/devices` — liefert alle Einträge als JSON-Liste (direktes Array, kein Wrapper). Jedes Item: `{id, type, role, entity_id, adapter_key, config_json, commissioned_at, created_at, updated_at}`.
  - [x] Pydantic-Schemas `HardwareConfigRequest`, `DeviceResponse` in `api/schemas/devices.py`. `HardwareConfigRequest` validiert:
    - `hardware_type: Literal["hoymiles", "marstek_venus"]`
    - `wr_limit_entity_id: str` (Pflicht)
    - `battery_soc_entity_id: str | None` (Pflicht, falls `hardware_type="marstek_venus"`)
    - `min_soc: int = Field(15, ge=5, le=50)` / `max_soc: int = Field(95, ge=50, le=100)` / `night_discharge_enabled: bool = True` / `night_start: str = "20:00"` / `night_end: str = "06:00"` (Pattern `^\d{2}:\d{2}$`)
    - `grid_meter_entity_id: str | None = None` (Optional Shelly 3EM)
    - Cross-Field-Validation: `max_soc > min_soc + 10`.

- [x] **Task 6: RFC-7807-Middleware** (AC: 12)
  - [x] Neue Datei `backend/src/solalex/api/middleware.py` anlegen. `ProblemDetailsMiddleware` oder `@app.exception_handler(RequestValidationError)` / `@app.exception_handler(HTTPException)`-basierte Konvertierung zu `application/problem+json`.
  - [x] Shape: `{"type": "urn:solalex:<kebab-category>", "title": "<deutsch>", "status": <int>, "detail": "<deutsche Handlungsempfehlung>", "instance": "<path>"}`. Siehe RFC 7807 §3.
  - [x] Unit-Tests in `backend/tests/unit/test_middleware.py`: fehlende Pflicht-Entity → 422 mit `application/problem+json`, deutsche Detail-Meldung.
  - [x] In `main.py` die Middleware/Exception-Handler registrieren.

- [x] **Task 7: Frontend-API-Layer** (AC: 2, 9, 12)
  - [x] Neue Dateien:
    - `frontend/src/lib/api/client.ts`: dünner `fetch`-Wrapper (~40 Zeilen) mit einheitlichem Error-Handling (RFC-7807-Parsing, wirft `ApiError`-Klasse mit `title`/`detail`/`status`). Base-URL aus `import.meta.env.BASE_URL` (HA-Ingress-kompatibel).
    - `frontend/src/lib/api/types.ts`: handgeschriebene TS-Types (snake_case!) für `EntitiesResponse`, `EntityOption`, `HardwareConfigRequest`, `DeviceResponse`. **Kein** `openapi-typescript`-Generator.
    - `frontend/src/lib/api/errors.ts`: `ApiError`-Klasse + `isApiError`-Type-Guard.
  - [x] Unit-Tests via vitest in `frontend/src/lib/api/client.test.ts`: Mocke `fetch`, assertiere RFC-7807-Parsing, Error-Branch.
  - [x] **Kein neuer Polling-Hook** in dieser Story — `lib/polling/` bleibt unangerührt (Epic 5).

- [x] **Task 8: Config-Route + Svelte-Komponenten** (AC: 1, 3, 4, 5, 6, 7, 10)
  - [x] Routing erweitern: In `frontend/src/App.svelte` die `syncRoute`-Funktion um `#/config` und `#/functional-test` erweitern (Whitelist der gültigen Routes).
  - [x] Neue Route-Datei: `frontend/src/routes/Config.svelte`. Struktur:
    - Hardware-Typ-Auswahl (2 Kacheln: Hoymiles/OpenDTU + Marstek Venus) als `<button>`-Elemente mit `aria-pressed`-State. Keine Tooltips (UX-DR30).
    - `onMount`: `GET /api/v1/setup/entities` via `client.ts` → Entities-State in Svelte 5 Runes (`$state`).
    - Bedingtes Rendering:
      - `type === "hoymiles"` → WR-Limit-Dropdown (Pflicht) + Optional Smart-Meter-Section.
      - `type === "marstek_venus"` → WR-Charge-Dropdown (Pflicht) + Akku-SoC-Dropdown (Pflicht) + Min/Max-SoC-Stepper + Nacht-Entlade-Checkbox mit Start/End `<input type="time">` + Optional Smart-Meter-Section.
    - Smart-Meter-Section: Checkbox „Smart Meter (Shelly 3EM) zuordnen" + Entity-Dropdown (aus `power_entities`).
    - Info-Zeile „Anker Solix und generische HA-Entities folgen mit v1.5" unter Hardware-Typ-Bereich.
    - Primärer „Speichern"-Button am Seitenende. Disabled, solange Pflichtfelder unausgefüllt (UX-DR30: keine grauen Disabled-Buttons — stattdessen Button ausblenden + unauffälliger Hinweis „Wähle zuerst WR-Limit-Entity").
    - Speichern → `POST /api/v1/devices` via `client.ts`. Bei Erfolg: `window.location.hash = "#/functional-test"`.
    - Fehler-Pfad (ApiError): Deutsche Fehler-Zeile unter dem Speichern-Button mit `detail`-Text aus RFC-7807 (UX-DR20).
    - Skeleton-Pulse während Entity-Loading (≥ 400 ms), danach Dropdown-Inhalte.
  - [x] `frontend/src/routes/FunctionalTestPlaceholder.svelte`: minimaler Screen mit Titel „Funktionstest" + Hinweis „Implementierung folgt mit Story 2.2" + Link zurück zu `#/`.
  - [x] In `App.svelte` die beiden neuen Routes einbinden (aktuell läuft `App.svelte` mit Empty-State; Story 2.1 muss Routing auf 3 Routes erweitern: `#/` = Empty-State, `#/config` = Config.svelte, `#/functional-test` = FunctionalTestPlaceholder.svelte).
  - [x] CSS: Tokens aus `app.css` verwenden (UX-DR4 semantische Klassen, CSS Custom Properties). Keine Token-Duplikate in TS (`lib/tokens/` bleibt verboten).
  - [x] **Deutsche Strings hardcoded** in der Svelte-Komponente (CLAUDE.md §Stil-Leitplanken + NFR49-Aufschub).

- [x] **Task 9: Empty-State-CTA auf `#/config` verlinken** (AC: 1)
  - [x] In `frontend/src/App.svelte` den bestehenden CTA-Link `href="#/wizard"` auf `href="#/config"` umstellen (Zeile ~105 im Empty-State-Section).
  - [x] Button-Label bleibt „Setup starten" (Sprachkonsistenz; Glossar).

- [x] **Task 10: Tests & Final Verification** (AC: 1–12)
  - [x] Backend: `cd backend && uv run pytest` — alle Tests grün inkl. neue: `test_adapters.py`, `test_setup_entities.py` (mit Mock-HA), `test_devices.py` (mit Temp-SQLite-Datei oder `:memory:`), `test_migrate.py` (Migration-Idempotenz), `test_middleware.py` (RFC-7807).
  - [x] Backend: `cd backend && uv run ruff check` + `uv run mypy --strict` clean.
  - [x] Frontend: `cd frontend && npm run lint && npm run check && npm run build` clean.
  - [x] Frontend: `cd frontend && npm test` (vitest für `client.ts`-Tests) grün.
  - [x] Manual-QA: HA-Instanz aufrufen → Sidebar → Solalex → „Setup starten" → Config-Page öffnet → Hardware-Typ wählen → Entities werden geladen → Speichern → Weiterleitung auf Functional-Test-Placeholder; Anker/Generic-Info-Zeile sichtbar.
  - [x] Drift-Check: `grep -r "i18n\|\$t(" frontend/src/` liefert 0 Treffer (Guardrail aus Story 1.7-Deferral).
  - [x] Drift-Check: `grep -r "asyncio.Queue\|event_bus\|Pub/Sub" backend/src/solalex/` liefert 0 Treffer (CLAUDE.md Stolperstein).

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [epics.md — Epic 2 Amendment 2026-04-23 + Story 2.1](../planning-artifacts/epics.md) — fachliche Story-Quelle und verbindliche ACs.
- [architecture.md §Adapter-Modul-Pattern (Zeile 243)](../planning-artifacts/architecture.md) — ein Python-Modul pro Hersteller, hardcoded Entity-Mappings.
- [architecture.md §Data Architecture (Zeile 262–305)](../planning-artifacts/architecture.md) — Raw aiosqlite, WAL-Mode, `schema_version`-Row, `sql/NNN_*.sql`.
- [architecture.md §5 harte Regeln (Zeile 461–469)](../planning-artifacts/architecture.md) — snake_case, ein-Modul-pro-Adapter, Closed-Loop-Readback, JSON ohne Wrapper, Logging-Wrapper.
- [architecture.md §API Boundaries (Zeile 755–796)](../planning-artifacts/architecture.md) — Endpoint-Liste, `adapters/`-Registry, Data-Boundaries.
- [architecture.md §Requirements to Structure Mapping Epic 2 (Zeile 803)](../planning-artifacts/architecture.md) — erwartete Zielpfade.
- [prd.md §FR7/FR11/FR22 + NFR34](../planning-artifacts/prd.md) — Hardware-Typ-Auswahl, Funktionstest-Vorgriff, Min/Max-SoC, ein Modul pro Adapter.
- [ux-design-specification.md §UX-DR4/UX-DR19/UX-DR20/UX-DR29/UX-DR30](../planning-artifacts/ux-design-specification.md) — semantische Klassen, Skeleton statt Spinner, Fehler mit Handlungsempfehlung, eine primäre Aktion pro Screen, Anti-Pattern-Liste.
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md) — snake_case, adapter-Modul, Readback, JSON-Wrapper, Logging-Wrapper; Stop-Signals bei SQLAlchemy/structlog/asyncio.Queue/WebSocket-Frontend/JSON-Template-Layer.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope-Disziplin:**

Diese Story ist groß, aber abgegrenzt — sie liefert **gleichzeitig** die Persistenz-Foundation, das Adapter-Modul-System und die Config-Page-UI. Weil spätere Stories (2.2 Funktionstest, 3.1 Controller) auf allen drei Bausteinen aufsetzen, werden sie hier zusammen gebaut. **Kein Controller-Code, kein Executor, kein Readback-Flow in dieser Story** — nur die Registry und das Abstract-Interface.

**Dateien, die berührt werden dürfen:**

- NEU Backend:
  - `backend/src/solalex/persistence/{__init__,db,migrate}.py`
  - `backend/src/solalex/persistence/sql/001_initial.sql`
  - `backend/src/solalex/persistence/repositories/{__init__,meta,devices}.py`
  - `backend/src/solalex/adapters/{__init__,base,hoymiles,marstek_venus,shelly_3em}.py`
  - `backend/src/solalex/api/routes/{setup,devices}.py`
  - `backend/src/solalex/api/schemas/{setup,devices,ha_state}.py`
  - `backend/src/solalex/api/middleware.py`
  - `backend/tests/unit/{test_adapters,test_migrate,test_middleware,test_devices_repo}.py`
  - `backend/tests/integration/test_setup_entities.py`
  - `backend/tests/integration/test_devices_api.py`
- NEU Frontend:
  - `frontend/src/routes/Config.svelte`
  - `frontend/src/routes/FunctionalTestPlaceholder.svelte`
  - `frontend/src/lib/api/{client.ts,types.ts,errors.ts}`
  - `frontend/src/lib/api/client.test.ts` (vitest)
- MOD Backend:
  - `backend/src/solalex/main.py` (Lifespan: Migration aufrufen + neue Router einbinden + Middleware registrieren)
  - `backend/src/solalex/ha_client/client.py` (neue `get_states`-Methode)
  - `backend/src/solalex/config.py` (neues `database_path`-Feld, Default `/data/solalex.db`, via `AliasChoices("SOLALEX_DB_PATH", "DATABASE_PATH")` overridable für Tests)
  - `backend/tests/integration/mock_ha_ws/server.py` (Handler für `get_states`)
- MOD Frontend:
  - `frontend/src/App.svelte` (Route-Whitelist erweitern, CTA auf `#/config`)
- **Nur verifizieren, nicht ändern:** `backend/src/solalex/common/logging.py`, `addon/config.yaml`, `addon/run.sh` (Migrations werden beim Start vom Code ausgeführt, nicht vom Shell-Script).

**Wenn Du anfängst, SQLAlchemy-Models zu schreiben — STOP.** Raw aiosqlite + `sql/NNN_*.sql`. Queries in `repositories/*.py`.

**Wenn Du `asyncio.Queue` für Entity-Loading oder Event-Handling einbaust — STOP.** Direkte `await`-Calls reichen.

**Wenn Du `structlog` importierst — STOP.** Nutze `get_logger(__name__)` aus `common/logging.py`.

**Wenn Du `openapi-typescript` oder einen TS-Codegen installierst — STOP.** TS-Types werden handgeschrieben in `lib/api/types.ts`.

**Wenn Du ein JSON-Template für Adapter-Konfiguration einführen willst — STOP.** Jeder Adapter ist ein Python-Modul mit hardcoded Dicts.

**Wenn Du einen 4-Schritt-Wizard mit `Step1Hardware.svelte` / `Step2Detection.svelte` / … anlegst — STOP.** Amendment 2026-04-23 hat den Wizard gestrichen. Eine einzige `Config.svelte`-Seite reicht.

**Wenn Du Auto-Detection oder Live-Werte neben den Dropdowns implementierst — STOP.** FR8/FR9 sind auf v1.5 verschoben. In v1: nur `get_states`-Dropdown, keine `detect()`-Calls aus der UI.

**Wenn Du ein Wrapper-Response `{data: ..., success: true}` um JSON legst — STOP.** Direktes JSON-Objekt. Fehler als RFC 7807 `application/problem+json`.

**Wenn Du i18n-Wrapper (`$t('key')`) oder `locales/*.json` anlegst — STOP.** NFR49 ist auf v2 verschoben. Deutsche Strings hardcoded in der Svelte-Komponente.

### Architecture Compliance Checklist

- Raw aiosqlite + WAL-Mode, keine ORMs.
- Forward-only Schema-Migrations via `sql/NNN_*.sql` + `schema_version`-Row.
- snake_case end-to-end: DB-Tabellen/Spalten, Python-Files/Funktionen/Variablen, API-JSON-Feldnamen, URL-Pfade, Query-Params.
- Adapter-Registry als statisches `ADAPTERS`-Dict in `adapters/__init__.py`.
- JSON-Responses sind direkte Objekte, keine Hüllen; Fehler sind RFC 7807.
- Logging ausschließlich via `get_logger(__name__)`.
- Frontend nutzt REST (kein WS-Code in v1), handgeschriebene TS-Types, CSS-Custom-Properties als Token-Quelle.
- Deutsche UI-Strings hardcoded; Code-Kommentare auf Englisch.
- Ein Dropdown-Polling gibt es NICHT — `get_states` ist ein One-Shot-Call beim `onMount` der Config-Page.

### Library/Framework Requirements

**Backend-Dependencies (bereits in `pyproject.toml` aus Story 1.1):**

```toml
dependencies = [
    "fastapi[standard]>=0.135.1",
    "uvicorn[standard]>=0.30",
    "aiosqlite>=0.20",           # ← Persistenz
    "websockets>=13",
    "pydantic-settings>=2.6",
    "httpx>=0.27",
]
```

**Keine neuen Dependencies.** `aiosqlite` ist seit Story 1.1 vorhanden und wird in dieser Story erstmalig genutzt.

**Frontend-Dependencies:** Svelte 5 (Runes), Vite 7, Tailwind 4, `svelte-spa-router` (Story 1.4 hat es deklariert; in dieser Story wird es NICHT verdrahtet — wir bleiben beim Hash-Routing via `window.location.hash` + `hashchange`-Event, konsistent mit Story 1.6). Keine neuen Dependencies.

### Datenmodell-Schnittstellen

**`devices`-Tabelle (Schema v1):**

| Spalte | Typ | Kommentar |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `type` | TEXT NOT NULL | `"hoymiles"` / `"marstek_venus"` / `"shelly_3em"` — Hersteller-Gruppe |
| `role` | TEXT NOT NULL | `"wr_limit"` / `"wr_charge"` / `"battery_soc"` / `"grid_meter"` — funktionale Rolle |
| `entity_id` | TEXT NOT NULL | HA-Entity-ID |
| `adapter_key` | TEXT NOT NULL | Key aus `ADAPTERS` (`hoymiles` / `marstek_venus` / `shelly_3em`) |
| `config_json` | TEXT NOT NULL DEFAULT `'{}'` | JSON-Blob für rollenspezifische Config (Min/Max-SoC, Nacht-Fenster) |
| `last_write_at` | TIMESTAMP NULL | Bleibt NULL in Story 2.1; wird vom Rate-Limiter in Story 3.1 befüllt |
| `commissioned_at` | TIMESTAMP NULL | Bleibt NULL in Story 2.1; gesetzt in Story 2.3 |
| `created_at` | TIMESTAMP NOT NULL DEFAULT now | |
| `updated_at` | TIMESTAMP NOT NULL DEFAULT now | |

UNIQUE(`entity_id`, `role`) für Idempotenz.

**`meta`-Tabelle:**

| Spalte | Typ | Kommentar |
|---|---|---|
| `key` | TEXT PK | `"schema_version"`, später `"bezugspreis_ct"` etc. |
| `value` | TEXT NOT NULL | |

Einziger Eintrag in `001_initial.sql`: `('schema_version', '1')`.

### `config_json` pro Rolle

- `wr_limit` (Hoymiles): `{}` (keine Rollen-Config nötig in v1).
- `wr_charge` (Marstek Venus): `{"min_soc": 15, "max_soc": 95, "night_discharge_enabled": true, "night_start": "20:00", "night_end": "06:00"}`.
- `battery_soc` (Marstek Venus): `{}` (Read-Only-Sensor, Config liegt bei `wr_charge`).
- `grid_meter` (Shelly 3EM): `{}` (Read-Only).

### RFC-7807-Fehler-Kategorien (`type`-URIs)

- `urn:solalex:validation-error` — Pydantic-Validation-Failure (422).
- `urn:solalex:ha-unavailable` — HA-WS nicht verbunden (503).
- `urn:solalex:get-states-timeout` — `get_states`-Timeout (504).
- `urn:solalex:db-error` — SQLite-Fehler (500).

Jeder `detail`-Text ist deutsch und enthält Handlungsempfehlung (UX-DR20).

### HA-WebSocket `get_states`-Spec

Aus HA-WS-API-Dokumentation:

```json
// Client → Server
{"id": 5, "type": "get_states"}

// Server → Client
{
  "id": 5,
  "type": "result",
  "success": true,
  "result": [
    {
      "entity_id": "sun.sun",
      "state": "above_horizon",
      "attributes": {
        "friendly_name": "Sun",
        "azimuth": 336.86,
        ...
      },
      "last_changed": "2026-04-23T12:00:00+00:00",
      "last_updated": "2026-04-23T12:00:00+00:00"
    },
    ...
  ]
}
```

Reference: [developers.home-assistant.io/docs/api/websocket#fetching-states](https://developers.home-assistant.io/docs/api/websocket#fetching-states).

### Anti-Patterns & Gotchas

- **KEIN 4-Schritt-Wizard**: Das Amendment 2026-04-23 hat den linearen Wizard gestrichen. Eine einzige Config-Page mit zwei primären Bereichen (Typ + Entities).
- **KEIN Auto-Detection-Aufruf aus UI**: `detect()` bleibt als Adapter-Interface-Methode erhalten, wird aber in v1 NUR in späteren Server-seitigen Auto-Detection-Pfaden (v1.5) genutzt. Die UI nutzt `get_states` direkt und filtert clientseitig.
- **KEIN Live-Werte-Rendering**: FR9 ist auf v1.5 verschoben. Dropdowns zeigen `entity_id + friendly_name`, KEINEN Live-State-Wert neben dem Dropdown.
- **KEIN JSON-Template-Layer**: Adapter sind Python-Module mit hardcoded Entity-Pattern-Listen. Kein externer JSON-Loader, kein `/data/templates/`-Verzeichnis.
- **KEIN `print`, kein `logging.getLogger` direkt**: Immer `get_logger(__name__)` aus `common/logging.py`.
- **KEIN Wrapper-Response**: `{"id": 42, "type": "hoymiles"}`, nicht `{"data": {...}, "success": true}`.
- **KEIN structlog, keine Correlation-IDs**: stdlib-Logging reicht.
- **KEIN Blocking-SQL**: `aiosqlite`-Connections sind async. Repositories liefern immer `async def`-Funktionen.
- **KEIN `.env`-File-Handling in der Story**: `pydantic-settings` liest Env-Vars direkt, `SOLALEX_DB_PATH` ist optional (Default `/data/solalex.db`).
- **KEIN Hashing/Versionierung der Adapter-Configs**: Adapter-Versionierung ist NFR31 (Firmware-Pinning-Thema), aber in v1 reicht die Git-SHA als implizite Version. Keine zusätzliche Metadaten-Spalte in `devices`.
- **KEINE Tabellen, keine Modals, keine Tooltips, keine Loading-Spinner, keine grauen Disabled-Buttons** (UX-DR30). Disabled-Zustand des Speichern-Buttons → Button ausblenden + Hinweis-Zeile.
- **KEIN Mehrfach-Aufruf von `get_states`**: One-Shot beim `onMount`. Falls die Liste leer ist (HA gerade noch nicht synchronisiert), zeigt die UI einen deutschen Hinweis „Keine passenden Entities gefunden. Prüfe deine HA-Integration und lade die Seite neu."
- **KEIN Abhängigkeit von Story 2.2 oder 2.3**: Story 2.1 ist eigenständig abschließbar. Funktionstest-Platzhalter-Screen ist nur eine Weiterleitung.

### Source Tree — Zielzustand nach Story

```
backend/
├── src/solalex/
│   ├── adapters/                            [NEW directory]
│   │   ├── __init__.py                      [NEW — ADAPTERS-Registry]
│   │   ├── base.py                          [NEW — Abstract Adapter, Datenklassen]
│   │   ├── hoymiles.py                      [NEW]
│   │   ├── marstek_venus.py                 [NEW]
│   │   └── shelly_3em.py                    [NEW]
│   ├── persistence/                         [NEW directory]
│   │   ├── __init__.py                      [NEW]
│   │   ├── db.py                            [NEW — aiosqlite Factory]
│   │   ├── migrate.py                       [NEW — schema_version + sql/-Apply]
│   │   ├── sql/
│   │   │   └── 001_initial.sql              [NEW — meta + devices]
│   │   └── repositories/
│   │       ├── __init__.py                  [NEW]
│   │       ├── meta.py                      [NEW]
│   │       └── devices.py                   [NEW]
│   ├── api/
│   │   ├── routes/
│   │   │   ├── setup.py                     [NEW — GET /api/v1/setup/entities]
│   │   │   └── devices.py                   [NEW — GET/POST /api/v1/devices]
│   │   ├── schemas/
│   │   │   ├── setup.py                     [NEW]
│   │   │   ├── devices.py                   [NEW]
│   │   │   └── ha_state.py                  [NEW]
│   │   └── middleware.py                    [NEW — RFC 7807 Handler]
│   ├── ha_client/
│   │   └── client.py                        [MOD — get_states-Methode ergänzen]
│   ├── config.py                            [MOD — database_path-Feld]
│   └── main.py                              [MOD — Migrate + neue Router + Middleware]
└── tests/
    ├── unit/
    │   ├── test_adapters.py                 [NEW]
    │   ├── test_migrate.py                  [NEW]
    │   ├── test_middleware.py               [NEW]
    │   └── test_devices_repo.py             [NEW]
    └── integration/
        ├── mock_ha_ws/server.py             [MOD — get_states-Handler]
        ├── test_setup_entities.py           [NEW]
        └── test_devices_api.py              [NEW]

frontend/
├── src/
│   ├── App.svelte                           [MOD — Route-Whitelist + CTA-Target]
│   ├── lib/
│   │   └── api/                             [NEW directory]
│   │       ├── client.ts                    [NEW — fetch-Wrapper]
│   │       ├── client.test.ts               [NEW — vitest]
│   │       ├── types.ts                     [NEW — handgeschriebene TS-Types]
│   │       └── errors.ts                    [NEW — ApiError]
│   └── routes/                              [NEW directory]
│       ├── Config.svelte                    [NEW — Hardware Config Page]
│       └── FunctionalTestPlaceholder.svelte [NEW — Platzhalter für Story 2.2]
```

### Testing Requirements

- **Framework:** Backend `pytest` + `pytest-asyncio`. Frontend `vitest` (bereits über Story 1.4 verdrahtet; Fallback: `npm test`).
- **Backend-Coverage:**
  - Adapter-Module: jeder Adapter hat min. einen Test für Registry-Präsenz, Protokoll-Konformität, `build_*_command`-Korrektheit (wo anwendbar), `parse_readback` mit Sample-State.
  - Migration: `test_migrate.py` erstellt temporäre DB, läuft Migration, prüft `schema_version=1`, läuft nochmal (Idempotenz — keine Re-Apply), prüft `schema_version` bleibt 1.
  - Repositories: Temp-DB mit `:memory:` oder Tempfile, `upsert_device` + `list_devices` + `delete_all` Round-Trip.
  - Middleware: RFC-7807-Shape-Assertion, deutsche Meldung im `detail`.
  - Integration: Mock-HA-WS-Server liefert 3 Mock-States (1 `number.*`, 1 `sensor.*_power`, 1 `sensor.*_soc`) → `GET /api/v1/setup/entities` liefert die erwarteten 3 Klassen.
  - Integration: Happy-Path-`POST /api/v1/devices` mit Marstek-Config → 2 Rows in `devices` + 1 Shelly-Row → `GET /api/v1/devices` liefert alle 3.
  - Integration: Fehler-Path `POST /api/v1/devices` ohne WR-Limit-Entity → 422 + RFC-7807.
- **Frontend:**
  - Vitest: `client.test.ts` mocked `fetch`, assertiert Happy-Path, 4xx/5xx-Branch mit `ApiError`, RFC-7807-Parsing.
  - Manual: HA-Ingress → Sidebar → „Setup starten" → Config-Page → Marstek-Pfad komplett ausfüllen → Speichern → Weiterleitung auf Placeholder. Zweiter Durchgang: Re-Save mit anderen Entities → überschreibt (UNIQUE-Constraint via DELETE-THEN-INSERT).
- **Keine Playwright-/E2E-Tests** in v1 (architecture §Testing Framework).
- **Coverage-Ziel:** `adapters/`-Modul ≥ 70 % (Regelungs-Kern-Logik-Kriterium NFR35). Persistence + API ≥ 50 %.

### Previous Story Intelligence

**Aus Story 1.1 (done):**
- `backend/src/solalex/main.py` hat Lifespan-Gerüst (Story 1.3 hat es um HA-Client erweitert). Neue Lifespan-Komponenten (`migrate.run(db_path)`, `router.include`) müssen VOR dem `ReconnectingHaClient`-Task laufen, damit `get_states` auf eine befüllbare Struktur trifft.
- `backend/src/solalex/config.py` nutzt `pydantic-settings` mit `AliasChoices` — dem `database_path`-Feld bitte dieses Muster folgen.
- `aiosqlite>=0.20` ist bereits in `pyproject.toml` deklariert, wird aber erstmalig in dieser Story genutzt.
- `common/logging.py` mit `get_logger(__name__)` aus Story 1.1 — einziger zulässiger Logging-Einstieg.

**Aus Story 1.3 (done):**
- `HaWebSocketClient._pending_results: dict[int, asyncio.Future]` existiert und wird für `call_service` genutzt. `get_states` folgt demselben Muster (Pending-Future auf msg_id, Auflösung in `listen`).
- `ReconnectingHaClient.client` gibt die aktuelle `HaWebSocketClient`-Instanz zurück. Deferred-Work-Punkt: Referenzen können beim Reconnect veraltet werden. Für Story 2.1 reicht der One-Shot-Aufruf — falls Reconnect mittendrin passiert, wirft der Call eine Exception, die das Frontend als deutschen Fehler zeigt (Nutzer kann Seite neu laden).
- `tests/integration/mock_ha_ws/server.py` hat bereits Handler für `auth_required`/`auth`/`subscribe_trigger`/`call_service`. Nur den `get_states`-Handler ergänzen.

**Aus Story 1.4 (review):**
- `frontend/src/app.css` enthält bereits CSS-Custom-Properties + DM-Sans-Pipeline + Tailwind-Tokens. Config-Page nutzt ausschließlich diese Tokens.
- `svelte-spa-router` ist als Dependency installiert (Story 1.4), aber **nicht verdrahtet**. Story 2.1 verdrahtet es NICHT — wir bleiben beim Hash-basierten Routing aus Story 1.6, um Scope-Kreuz-Kontamination zu vermeiden. (Ein separater Refactor-Story kann `svelte-spa-router` später einführen, wenn mehr Routes dazukommen.)

**Aus Story 1.6 (review):**
- `App.svelte` nutzt `window.location.hash` + `hashchange`-Event. `syncRoute` hat aktuell eine Whitelist `[/, /wizard]` — Task 8 erweitert das auf `[/, /config, /functional-test]` und ersetzt den Legacy-`/wizard`-Eintrag.
- Der CTA zeigt aktuell auf `#/wizard` (Legacy). Task 9 ändert das auf `#/config`.
- Empty-State-Markup in `App.svelte` bleibt erhalten; nur CTA-Target und Route-Liste ändern sich.

**Aus Story 1.7 (review, auf v2 verschoben):**
- Kein i18n. Deutsche Strings hardcoded in allen Svelte-Komponenten. `$t(`-Pattern und `locales/*.json` bleiben Code-Review-Stop-Signals.

### Git Intelligence Summary

- Letzte Commits haben Foundation-Stabilität + HA-Ingress-Branding verstetigt. Story 2.1 setzt darauf auf und liefert erstmals Domain-Logik (Adapter + Persistence + Config-Form).
- Commits sollten atomar pro Task sein: z. B. getrennte Commits für „Persistence-Foundation + Migration" (Task 1), „Adapter-Module + Tests" (Task 2), „HA get_states + Setup-Route" (Task 3/4), „Device-Route + Middleware" (Task 5/6), „Frontend-API-Layer" (Task 7), „Config-Page + Route-Weiterleitung" (Task 8/9).
- **Keine Commits ohne Alex' Anweisung** (CLAUDE.md §Git). Nach jedem Task-Abschnitt Alex anfragen, ob committed werden soll.

### Latest Technical Information

- **aiosqlite >= 0.20**: Stabile Async-API. WAL-Mode via `PRAGMA journal_mode=WAL;` nach Connect (einmal pro Connection). `synchronous=NORMAL` ist der empfohlene WAL-Kompromiss für Crash-Safety + Performance.
- **HA-WebSocket `get_states`**: Stabil seit Jahren. Response kann bei grossen HA-Installationen > 500 States enthalten; Filter-Logik sollte Server-seitig (im Endpoint) laufen, nicht alles ans Frontend weiterreichen. Unit-Test mit 500er-Fixture optional als Performance-Sanity.
- **FastAPI RFC 7807**: Kein eingebauter Middleware-Helper. Custom-Exception-Handler via `@app.exception_handler(...)`. Referenz: [RFC 7807 §3](https://www.rfc-editor.org/rfc/rfc7807) + [FastAPI Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers).
- **Svelte 5 Runes**: `$state`, `$derived`, `$effect` sind die primären Reaktivitäts-Primitives. Kein `$:`-Syntax mehr in neuen Komponenten. Referenz: [svelte.dev/docs/svelte/runes](https://svelte.dev/docs/svelte/runes).
- **Pydantic v2 Field-Patterns**: `Field(ge=..., le=...)` für Range-Constraints; `Field(pattern=r"...")` für Regex; `model_validator(mode="after")` für Cross-Field-Validation.

### Project Structure Notes

- **Alignment:** Directory-Struktur matcht [architecture.md §Complete Project Directory Structure (Zeile 580–753)](../planning-artifacts/architecture.md) 1:1 bis auf zwei bewusste Abweichungen:
  - `frontend/src/routes/Wizard/*` (4 Wizard-Step-Files) wird NICHT angelegt — Amendment 2026-04-23 ersetzt das durch `Config.svelte` + `FunctionalTestPlaceholder.svelte`.
  - `frontend/src/lib/polling/` wird NICHT in dieser Story erstellt (Epic 5).
- **Abweichung:** Architecture §Decision Impact Analysis listet Story-Reihenfolge mit „Setup-Wizard-REST-API + Frontend-Wizard-Views (4 Schritte)" an Punkt 6. Die Realität (Amendment 2026-04-23) ist eine Config-Page + Funktionstest + Disclaimer in 3 Stories statt ein 4-Schritt-Wizard. Keine Spec-Nachziehung in dieser Story — `epics.md` ist die aktuelle Single-Source.
- **Deferred:** `svelte-spa-router`-Integration bleibt offen (siehe Deferred-Work Story 1.4: „Deep-Link `#/wizard` zeigt Empty-State statt Wizard-Route"). Ist KEIN Blocker für 2.1 — Hash-Routing in `App.svelte` genügt für 3 Routes.

### References

- [epics.md — Epic 2 Story 2.1](../planning-artifacts/epics.md)
- [architecture.md — gesamt](../planning-artifacts/architecture.md)
- [prd.md — gesamt](../planning-artifacts/prd.md)
- [ux-design-specification.md — gesamt](../planning-artifacts/ux-design-specification.md)
- [CLAUDE.md — 5 harte Regeln + Stolpersteine](../../CLAUDE.md)
- [Story 1.1 (Add-on Skeleton)](./1-1-add-on-skeleton-mit-custom-repository-multi-arch-build.md)
- [Story 1.3 (HA WebSocket Foundation)](./1-3-ha-websocket-foundation-mit-reconnect-logik.md)
- [Story 1.6 (HA-Ingress-Frame mit Empty-State)](./1-6-ha-ingress-frame-mit-dark-light-adaption-und-empty-state.md)
- [HA WebSocket API `get_states`](https://developers.home-assistant.io/docs/api/websocket#fetching-states)
- [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807)
- [FastAPI Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [aiosqlite docs](https://aiosqlite.omnilib.dev/en/stable/)
- [Svelte 5 Runes](https://svelte.dev/docs/svelte/runes)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `backend/src/solalex/persistence/` existiert, Migration läuft idempotent beim Start, `schema_version=1` gesetzt.
2. `backend/src/solalex/adapters/` enthält Abstract-Interface + 3 Day-1-Adapter, Registry `ADAPTERS` exportiert.
3. `HaWebSocketClient.get_states()` ist implementiert und Mock-Test grün.
4. `GET /api/v1/setup/entities` liefert 3 gefilterte Entity-Listen ohne Wrapper; Fehler als RFC 7807.
5. `POST /api/v1/devices` speichert die Config idempotent (Re-Save überschreibt); `GET /api/v1/devices` liefert Liste.
6. `frontend/src/routes/Config.svelte` rendert die Hardware-Typ-Auswahl + passenden Entity-Dropdowns + Akku-Felder + Shelly-Option + v1.5-Info-Zeile; Speichern funktioniert, leitet auf `#/functional-test` weiter.
7. Empty-State-CTA (`App.svelte`) zeigt auf `#/config`.
8. Alle automatisierten Tests (Backend + Frontend) grün; Ruff + MyPy + svelte-check clean.
9. Manuelle QA in HA bestätigt den Ende-zu-Ende-Flow; Drift-Checks für `i18n`/`asyncio.Queue` liefern 0 Treffer.
10. Keine Abhängigkeit auf Story 2.2/2.3 für die Story-Abschluss-Bestätigung.

**Nächste Story nach 2.1:** Story 2.2 (Funktionstest mit Readback & Commissioning) — setzt auf Adapter-Registry + `devices`-Tabelle + `call_service` auf, ergänzt Executor-Foundation + Readback-Logik + Live-Chart-Dramaturgie.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — claude-opus-4-7[1m]

### Debug Log References

- ruff SIM105: `try/except/pass` in `mock_ha_ws/server.py` → `contextlib.suppress(Exception)` + top-level imports
- ruff F841: unused `original_url` variable removed from `test_setup_entities.py`
- ruff SIM117: nested `async with` in `test_migrate.py` combined to single statement
- mypy `no-untyped-def` in 6 test files: added `Generator[T]` return types to pytest yield fixtures; ruff UP043 auto-fixed to `Generator[T]` (no `None, None`)
- ESLint `no-undef`: browser globals (`setTimeout`, `clearInterval`, etc.) added to `eslint.config.js`

### Completion Notes List

- All tasks implemented. Backend: 61 pytest tests green, ruff clean, mypy --strict clean (59 files, 0 issues).
- Frontend: ESLint clean, svelte-check clean, build clean (56.63 kB JS), vitest 15 tests green (client.test.ts, usePolling.test.ts, LineChart.test.ts — tests written as part of Story 2.2 scope).
- `FunctionalTestPlaceholder.svelte` was created in this story and subsequently replaced by the real `FunctionalTest.svelte` in Story 2.2 (same session).
- Drift-checks passed: 0 hits for `i18n|\$t(` in `frontend/src/` and `asyncio.Queue|event_bus` in `backend/src/solalex/`.

### File List

**Backend — neu:**
- `backend/src/solalex/persistence/__init__.py`
- `backend/src/solalex/persistence/db.py`
- `backend/src/solalex/persistence/migrate.py`
- `backend/src/solalex/persistence/sql/001_initial.sql`
- `backend/src/solalex/persistence/repositories/__init__.py`
- `backend/src/solalex/persistence/repositories/meta.py`
- `backend/src/solalex/persistence/repositories/devices.py`
- `backend/src/solalex/adapters/__init__.py`
- `backend/src/solalex/adapters/base.py`
- `backend/src/solalex/adapters/hoymiles.py`
- `backend/src/solalex/adapters/marstek_venus.py`
- `backend/src/solalex/adapters/shelly_3em.py`
- `backend/src/solalex/api/routes/setup.py`
- `backend/src/solalex/api/routes/devices.py`
- `backend/src/solalex/api/schemas/setup.py`
- `backend/src/solalex/api/schemas/devices.py`
- `backend/src/solalex/api/schemas/ha_state.py`
- `backend/src/solalex/api/middleware.py`
- `backend/tests/unit/test_adapters.py`
- `backend/tests/unit/test_migrate.py`
- `backend/tests/unit/test_middleware.py`
- `backend/tests/unit/test_devices_repo.py`
- `backend/tests/integration/test_setup_entities.py`
- `backend/tests/integration/test_devices_api.py`

**Backend — modifiziert:**
- `backend/src/solalex/main.py`
- `backend/src/solalex/ha_client/client.py`
- `backend/src/solalex/config.py`
- `backend/tests/integration/mock_ha_ws/server.py`
- `backend/tests/unit/test_control_state.py` (mypy-Fix)
- `backend/tests/integration/test_setup_test.py` (mypy-Fix)
- `backend/tests/integration/test_devices_api.py` (mypy-Fix)
- `backend/tests/integration/test_commission.py` (mypy-Fix)

**Frontend — neu:**
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/api/errors.ts`
- `frontend/src/lib/api/client.test.ts`
- `frontend/src/routes/Config.svelte`

**Frontend — modifiziert:**
- `frontend/src/App.svelte`
- `frontend/eslint.config.js`
- `frontend/package.json`

## Change Log

| Datum | Version | Beschreibung | Autor |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Initiale Story-Kontextdatei für Story 2.1 erstellt und auf `ready-for-dev` gesetzt. Deckt Persistence-Foundation + Adapter-Module + Hardware Config Page als kombinierten Foundation-Sprung für Epic 2. | Claude Opus 4.7 |
| 2026-04-23 | 1.0.0 | Implementierung abgeschlossen: Persistence-Foundation (aiosqlite WAL, Migrations, Repositories), Adapter-Registry (Hoymiles, Marstek Venus, Shelly 3EM), HA `get_states`, Setup- und Devices-API-Routen, RFC-7807-Middleware, Frontend-API-Layer (client.ts, types.ts, errors.ts), Config.svelte mit Hardware-Typ-Kacheln + Entity-Dropdowns + Akku-Feldern + Speichern + Weiterleitung. Alle CI-Gates grün. Story auf `review` gesetzt. | Claude Opus 4.7 (1M context) |

## Review Findings

Code-Review am 2026-04-23 über 3 parallele Layer (Blind Hunter, Edge Case Hunter, Acceptance Auditor). Spec-Konformität für alle 12 ACs bestätigt; keine CLAUDE.md-Hard-Rule-Verletzungen. Findings nach Triage:

### Decision-Needed (0 offen, 2 resolved)

- [x] [Review][Decision-Resolved] **SoC-Band-Validator widerspricht Field-Bounds** → **Option (a) Feld-Bounds verengen.** Entscheidung 2026-04-23 durch Alex: `min_soc ∈ [5, 40]`, `max_soc ∈ [51, 100]`. Validator bleibt (`max_soc > min_soc + 10`) und wird durch die verengten Bounds automatisch nie mehr verletzt. → wird als Patch umgesetzt (siehe P22).
- [x] [Review][Decision-Resolved] **Re-Save-Semantik bei bereits commissioned-ten Devices** → **Option (a) commissioned_at preservieren.** Entscheidung 2026-04-23 durch Alex: Bei `(entity_id, role)`-Match wird das bestehende `commissioned_at` übernommen; nur wirklich neue Entities sind frisch (uncommissioned). Mischzustand wird akzeptiert. → wird als Patch umgesetzt (siehe P23). [backend/src/solalex/api/routes/devices.py:606-609]

### Patch (23: 19 fixed, 4 skipped in batch — see below)

**Batch-Apply 2026-04-23**: Alle nicht-kontroversen Patches angewandt, 4 judgement-heavy Findings bewusst ausgelassen (P5, P11, P15, P21). Alle vier CI-Gates danach grün: ruff clean, mypy strict 45 files no issues, pytest 94 passed, svelte-check 0 errors, ESLint clean, vitest 21 passed.

- [x] [Review][Patch] **POST /devices: delete_all + upsert-Loop nicht atomar + kein `busy_timeout`** — gefixt via neuer `replace_all(conn, rows)` in `repositories/devices.py` (BEGIN IMMEDIATE + COALESCE-basierte Preserve-Logik in `ON CONFLICT`; einzelner Commit mit Rollback-on-Exception). `PRAGMA busy_timeout=5000` in `db.py` ergänzt. [backend/src/solalex/api/routes/devices.py, backend/src/solalex/persistence/db.py, backend/src/solalex/persistence/repositories/devices.py]
- [x] [Review][Patch] **`_to_response` nutzt `__import__("datetime").datetime.utcnow()`-Fallback** — gefixt: `from datetime import UTC, datetime` + `datetime.now(tz=UTC)` im Fallback-Pfad. [backend/src/solalex/api/routes/devices.py]
- [x] [Review][Patch] **Migration `executescript` ohne Transaktion + Version aus Enumerate-Index statt Datei-Prefix** — teilweise gefixt: Version jetzt aus `NNN_`-Prefix geparst (neue Helper-Funktion `_parse_prefix`), nicht mehr aus `enumerate`-Index. `executescript`-Transaktionssemantik ist durch SQLite-Library vorgegeben (auto-commit vor Scriptstart) und als Kommentar dokumentiert — Forward-Guard: Multi-Statement-Atomicity muss im SQL-File selbst via `BEGIN;...COMMIT;` sichergestellt werden. [backend/src/solalex/persistence/migrate.py]
- [x] [Review][Patch] **Migration: keine Duplikat-Prefix-Erkennung und keine `schema_version > len(files)`-Guard** — gefixt: `_check_contiguous` erkennt nun Duplikate, `run()` wirft `RuntimeError` wenn `schema_version` in der DB höher ist als der höchste Migration-File-Prefix. [backend/src/solalex/persistence/migrate.py]
- [ ] [Review][Patch][Skipped-in-Batch] **`_app_state_cache` wird im Module-Scope UND im Lifespan neu instanziert** — übersprungen im Batch: Refactor des Lifespans ist nicht-trivial und riskiert Regression in StateCache-Konsumenten. Bleibt als Action-Item für Story 3.1 (Controller-Integration packt das Lifespan-State-Handling ohnehin neu an). [backend/src/solalex/main.py:1150, 1170-1171]
- [x] [Review][Patch] **`parse_readback` macht `int(float(...))`, trunciert statt zu runden** — gefixt: `round(float(state.state))` in beiden Adaptern. [backend/src/solalex/adapters/hoymiles.py, backend/src/solalex/adapters/marstek_venus.py]
- [x] [Review][Patch] **`GET /setup/entities`: `wr_limit`-Filter akzeptiert leere `unit_of_measurement`** — gefixt: leerer String aus dem Tuple entfernt, Filter akzeptiert jetzt nur noch `("W", "kW", "%")`. [backend/src/solalex/api/routes/setup.py:699]
- [x] [Review][Patch] **`GET /setup/entities`: SoC-Bucket classifiziert jeden `sensor.*` mit `%` als SoC** — gefixt: zusätzliche Bedingung `device_class == "battery" OR "soc" in eid OR "battery" in eid`. Filtert Humidity/CPU-Load/Brightness raus. [backend/src/solalex/api/routes/setup.py:703]
- [x] [Review][Patch] **Race: HA-Drop zwischen `ha_ws_connected`-Check und `get_states`-Call → 500 statt 503** — gefixt: zusätzlicher `except (RuntimeError, ConnectionError, OSError)` im Handler; liefert 503 mit deutscher RFC-7807-Meldung. [backend/src/solalex/api/routes/setup.py:56-74]
- [x] [Review][Patch] **`GET /setup/entities` mit leerer `raw_states`-Liste liefert drei leere Dropdowns ohne Hinweis** — gefixt im Frontend: `Config.svelte` zeigt Error-Block „HA hat keine passenden Entities geliefert" wenn alle drei Listen leer sind. [frontend/src/routes/Config.svelte]
- [ ] [Review][Patch][Skipped-in-Batch] **`_dispatch_event` schluckt alle Exceptions** — übersprungen im Batch: Narrow-Scope braucht Wissen um die konkreten Exception-Klassen, die HA-Wire-Format-Parsing werfen kann. Als Action-Item für Story 3.1 — dort wird `_dispatch_event` ohnehin erweitert (Controller-Hook) und die Exception-Semantik neu durchdacht. [backend/src/solalex/main.py:1135-1136]
- [x] [Review][Patch] **`night_start`/`night_end`-Regex akzeptiert `99:99`** — gefixt: `pattern=r"^([01]\d|2[0-3]):[0-5]\d$"` bounded Stunde und Minute. [backend/src/solalex/api/schemas/devices.py:20-21]
- [x] [Review][Patch] **Marstek-Validator erlaubt `night_start == night_end` (leeres Entlade-Fenster)** — gefixt: `model_validator` prüft bei `night_discharge_enabled=True` auf leeres Fenster. [backend/src/solalex/api/schemas/devices.py:validate_soc_range]
- [x] [Review][Patch] **Marstek-Validator erlaubt `battery_soc_entity_id == wr_limit_entity_id`** — gefixt: `model_validator` lehnt identische Entity-IDs mit deutscher Meldung ab. [backend/src/solalex/api/schemas/devices.py:validate_soc_range]
- [ ] [Review][Patch][Skipped-in-Batch] **Hoymiles-POST-Pfad schluckt Marstek-Felder still** — übersprungen im Batch: saubere Lösung erfordert Pydantic-Sentinel-Pattern (Felder als `Annotated[int | _Unset]`) — nicht-trivial und niedriges Risiko, weil Default-Werte korrekt bleiben. Bleibt als Action-Item; Warn-Log ist die pragmatische Minimalvariante für Follow-up. [backend/src/solalex/api/schemas/devices.py, backend/src/solalex/api/routes/devices.py]
- [x] [Review][Patch] **`client.ts`: `fetch()`-Netzwerkfehler werden nicht als `ApiError` gekapselt** — gefixt: `try/catch` um `fetch(...)` wirft jetzt `ApiError(0, "urn:solalex:network-error", "Verbindungsfehler", ...)` mit deutscher Handlungsempfehlung. [frontend/src/lib/api/client.ts]
- [x] [Review][Patch] **`Config.svelte`: `useSmartMeter=true` mit leerem Dropdown verwirft still** — gefixt: `canSave` zusätzlich blockiert wenn `useSmartMeter && !gridMeterEntityId`; Hint-Zeile erwähnt fehlendes Smart-Meter-Feld. [frontend/src/routes/Config.svelte]
- [x] [Review][Patch] **`DeviceResponse` fehlt `last_write_at`-Feld** — gefixt: Feld in `DeviceResponse` ergänzt + `_to_response` mappt `record.last_write_at`. [backend/src/solalex/api/schemas/devices.py, backend/src/solalex/api/routes/devices.py]
- [x] [Review][Patch] **`HaWebSocketClient.get_states` prüft `result` nicht als Liste** — gefixt: expliziter `isinstance(raw, list)`-Check, None wird zu `[]`, Non-List wirft `RuntimeError` mit Shape-Info. [backend/src/solalex/ha_client/client.py]
- [x] [Review][Patch] **`App.svelte` Empty-State-Prosa erwähnt weiter „Setup-Wizard"** — gefixt: „Richte jetzt in wenigen Schritten dein Setup ein". [frontend/src/App.svelte:114]
- [ ] [Review][Patch][Skipped-in-Batch] **Test `test_get_entities_returns_three_categories` testet NICHT den Happy-Path** — übersprungen im Batch: substanzieller Test-Refactor mit Dependency-Injection-Fixture. Bleibt als Action-Item — Happy-Path-Coverage für `/api/v1/setup/entities` ist Test-Debt, aber kein Prod-Risiko. [backend/tests/integration/test_setup_entities.py:1777-1810]
- [x] [Review][Patch] **P22 (aus D1): SoC-Feld-Bounds verengen** — gefixt: `min_soc=Field(15, ge=5, le=40)`, `max_soc=Field(95, ge=51, le=100)` + Frontend-Stepper `min="5" max="40"` / `min="51" max="100"`. [backend/src/solalex/api/schemas/devices.py, frontend/src/routes/Config.svelte]
- [x] [Review][Patch] **P23 (aus D2): Re-Save preserviert `commissioned_at` bei `(entity_id, role)`-Match** — gefixt: neue `replace_all(conn, records)` in `repositories/devices.py` (siehe P1). Nicht mehr in der neuen Config-Liste enthaltene `(entity_id, role)`-Paare werden gelöscht; enthaltene Paare werden via `ON CONFLICT DO UPDATE` aktualisiert — `commissioned_at` bleibt durch Abwesenheit im SET-Clause automatisch erhalten. Alles in einer Transaktion mit `BEGIN IMMEDIATE` + `rollback` bei Exception. [backend/src/solalex/persistence/repositories/devices.py]

### Defer (7)

- [x] [Review][Defer] **Shelly `_POWER_PATTERN` overmatched Hoymiles `ac_power`-Sensoren** [backend/src/solalex/adapters/shelly_3em.py:344] — deferred, `detect()` wird in v1 nicht aus UI aufgerufen (AC8-Sub-And). Fix in v1.5 zusammen mit Auto-Detection.
- [x] [Review][Defer] **Marstek `_SOC_PATTERN` regex-Logik zweideutig** [backend/src/solalex/adapters/marstek_venus.py:259] — deferred, identische Begründung wie Shelly; detect() v1-ungenutzt.
- [x] [Review][Defer] **`entity_role_map` ist Startup-Snapshot ohne Refresh nach `POST /devices`** [backend/src/solalex/main.py:1163-1172] — deferred, Controller-/Event-Dispatch-Konzept gehört zu Story 3.1 Core-Controller. Für 2.1 ohne Controller-Pfad folgenlos.
- [x] [Review][Defer] **`upsert_device` gibt `0` auf UPDATE-Pfad zurück — Contract-Lüge** [backend/src/solalex/persistence/repositories/devices.py:1407-1422] — deferred, aktueller Caller nutzt Return-Wert nicht; Cleanup wenn weitere Caller dazukommen.
- [x] [Review][Defer] **`GET /setup/entities` ohne Pagination/Dedupe bei großen HA-Instanzen** [backend/src/solalex/api/routes/setup.py:692-704] — deferred, >500 Entities-Fall nicht in NFR; Beta-Nutzer unwahrscheinlich betroffen. Scale-Nachzug wenn Beta-Feedback es verlangt.
- [x] [Review][Defer] **Scope-Creep aus Bundle-Commit: `POST /setup/test` + `POST /setup/commission` in diesem Diff** [backend/src/solalex/api/routes/setup.py:713-851] — deferred, gehört zu Story 2.2 (Funktionstest) und 2.3 (Commissioning). Eigene Findings (Lock-TOCTOU-Race, `devices[0]`-Fallback auf Non-WR, Exception-Leak in 500-Detail, `count if count > 0 else len(devices)`-Idempotency-Lüge, `mark_all_commissioned`-ISO-Format-Inkonsistenz) werden dort bewertet.
- [x] [Review][Defer] **Scope-Creep aus Bundle-Commit: `App.svelte` hat `/running`+`/disclaimer`-Routes + `getDevices`-Autoforward** [frontend/src/App.svelte:30, 2299-2313] — deferred, gehört zu Story 2.3 (Disclaimer) und späterem Running-Screen. Findings (stale `currentRoute`-Read, Ping-Interval-Signal-Check) werden dort bewertet.

### Dismissed (~20)

Rauschen / False-Positives / Nits: `id=record.id or 0`-Fallback, `_test_lock` lazy init (in 2.2-Scope), Python-3.10-`Z`-Suffix (Projekt ist 3.13), `_POWER_PATTERN` dead-code in marstek_venus, `parse_readback` TypeError-dead-branch, no-solo-index-on-entity_id (Composite hat es als Leading-Col), SoC-Band-Upper-Bound (Field-Clamps decken), `get_entities`-no-dedup (3 disjoint Buckets), Timestamp-Format-`Z`-vs-`+00:00` (kosmetisch), Test-patches-private-`_url`, ApiError-prototype-fix (TS-Target ES2020+), `res.json()`-on-empty-body (kein Caller in 2.1), `_parse_ts` swallowing (akzeptables Robustheits-Verhalten), Mock-Server-`contextlib.suppress`, App.svelte-Avatar-Import, `test_resave`-ohne-Crash-Test, `wr_limit_entity_id`-Feldname-für-Marstek-Charge (semantisch OK), main.py-Version-Bump, `_check_contiguous`-forever-start-at-1.

