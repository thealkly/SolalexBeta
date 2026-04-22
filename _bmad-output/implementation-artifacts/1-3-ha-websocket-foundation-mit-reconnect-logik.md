# Story 1.3: HA WebSocket Foundation mit Reconnect-Logik

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Solalex-Backend,
I want eine stabile HA-WebSocket-Verbindung mit SUPERVISOR_TOKEN-Auth und automatischem Reconnect,
so that alle späteren Epics sich auf einen verlässlichen Kommunikationskanal zu HA verlassen können.

## Acceptance Criteria

1. **Auth mit SUPERVISOR_TOKEN:** `Given` das Add-on startet, `When` der WebSocket-Client verbindet, `Then` die Verbindung zu `ws://supervisor/core/websocket` wird mit `SUPERVISOR_TOKEN` (aus Env-Var) authentifiziert **And** der Auth-Success-Event (`{"type": "auth_ok"}`) wird über `get_logger(__name__)` strukturiert im Log bestätigt.
2. **Exponentielles Backoff-Reconnect:** `Given` eine bestehende WebSocket-Verbindung, `When` sie unterbrochen wird (Socket-Fehler, Auth-Revoke, Supervisor-Rotation), `Then` exponentielles Backoff-Reconnect startet mit **1 s → 2 s → 4 s → 8 s → 16 s → max. 30 s** (verdoppelnd, bei 30 s gekappt, unendlich wiederholend).
3. **Persistente Subscription-Liste + Auto-Re-Subscribe:** `Given` der Client hatte aktive Subscriptions (z. B. `subscribe_trigger` auf `state_changed`-Events, registriert von späteren Epics), `When` ein Reconnect erfolgreich ist, `Then` alle in-Memory persistierten Subscriptions werden automatisch re-subscribt **And** bestehende Message-IDs werden durch frische ersetzt (HA vergibt neue Subscription-IDs pro Connection).
4. **Strukturiertes Error-Logging + Health-Status-Marker:** `Given` ein Kommunikationsfehler (Socket-Timeout, ungültige JSON, Auth-Fail), `When` er auftritt, `Then` er wird mit Kontext (Fehler-Typ, letzter HA-Message-ID, Reconnect-Versuchs-Zähler) im strukturierten JSON-Log unter `/data/logs/` via `get_logger(__name__)` protokolliert **And** ein in-Memory-Flag `ha_ws_connected` wird auf `false` gesetzt, bis Auth-Success wieder eintritt.
5. **Mock-HA-WebSocket-Integrationstest:** `Given` ein Test-Setup mit Mock-HA-WebSocket (pytest-Fixture), `When` ein simulierter Abbruch ausgelöst wird, `Then` der Client reconnected innerhalb 30 s automatisch ohne manuelle Intervention **And** die Test-Assertion verifiziert den Backoff-Zeitplan (mit Time-Mock) sowie das Re-Subscribe einer vor dem Abbruch registrierten Subscription.
6. **Health-Endpoint um HA-WS-Status erweitert (CLAUDE.md Regel 4 — kein Wrapper):** `Given` der Container läuft, `When` `GET /api/health` aufgerufen wird, `Then` der Endpoint liefert JSON als direktes Objekt mit mindestens `{"status": "ok", "ha_ws_connected": bool, "uptime_seconds": int}` (keine `{data: …, success: …}`-Hülle) **And** HTTP-Status ist `200`, solange der Prozess läuft — auch bei verlorener HA-WS-Verbindung (Zustand steckt im Payload, nicht im HTTP-Code) **And** der Endpoint ist HA-Binary-Sensor-tauglich und überträgt keine Telemetrie (NFR17).

## Tasks / Subtasks

- [ ] **Task 1: `ha_client`-Modul-Struktur anlegen** (AC: 1, 2, 3, 4)
  - [ ] Verzeichnis erzeugen: `backend/src/solalex/ha_client/` mit `__init__.py`
  - [ ] Dateien anlegen: `client.py`, `reconnect.py`, `types.py` (laut [architecture.md §637-640](../planning-artifacts/architecture.md))
  - [ ] `types.py`: Pydantic/TypedDict-Modelle für HA-WS-Messages — mindestens `AuthRequest`, `AuthResponse`, `SubscribeTriggerRequest`, `SubscribeEventsRequest`, `StateChangedEvent`, `CallServiceRequest`, `ResultResponse` (snake_case in Field-Namen — Regel 1 CLAUDE.md)
- [ ] **Task 2: `HaWebSocketClient` in `client.py` implementieren** (AC: 1, 3)
  - [ ] Dependency: `websockets>=13` (bereits in Story 1.1 `pyproject.toml` fixiert)
  - [ ] Klasse `HaWebSocketClient`:
    - `__init__(self, token: str, url: str = "ws://supervisor/core/websocket")` — Token aus `pydantic-settings` (siehe `config.py` aus Story 1.1)
    - `async def connect(self) -> None` — öffnet WS, erwartet `auth_required`-Message, sendet `{"type": "auth", "access_token": token}`, wartet auf `auth_ok` oder `auth_invalid`. Bei `auth_invalid`: `AuthError`-Exception (keine Retry — Token falsch).
    - `async def subscribe(self, payload: dict) -> int` — sendet Subscribe-Message mit auto-inkrementierender Message-ID, merkt sich den Payload im `_subscriptions: list[dict]`-In-Memory-Store. Gibt die neue Subscription-ID zurück.
    - `async def call_service(self, domain: str, service: str, service_data: dict) -> dict` — sendet `call_service`-Message, wartet auf matching `result`-Message. Timeout 10 s.
    - `async def listen(self, on_event: Callable[[dict], Awaitable[None]]) -> None` — Main-Loop: liest Messages, dispatched `event`-Typ an `on_event`-Callback, handled `result`-Messages via internes Future-Mapping.
    - `async def close(self) -> None` — sauberes Schließen der Connection.
  - [ ] Message-ID-Counter: `self._next_id: int = 1` (HA-WS-Protokoll-Spec: monoton ab 1, pro Connection-Session).
  - [ ] **In-Memory-Subscription-Store:** `self._subscriptions: list[dict]` — NICHT in SQLite. Subscriptions werden vom Controller bei jedem Prozess-Start neu registriert. "Persistent" im PRD/Architektur-Kontext meint: **überlebt Reconnect innerhalb desselben Prozesses**, nicht Restart.
  - [ ] Logging via `from solalex.common.logging import get_logger; log = get_logger(__name__)` (CLAUDE.md Regel 5 — kein `print`, kein `logging.getLogger`).
- [ ] **Task 3: Reconnect-Wrapper in `reconnect.py` implementieren** (AC: 2, 3, 4)
  - [ ] Klasse `ReconnectingHaClient` (wrapt `HaWebSocketClient`):
    - `async def run_forever(self, on_event: Callable) -> None` — startet `connect` → `listen`-Loop; bei Exception: Backoff-Sleep → Reconnect → Re-Subscribe.
    - Backoff-Sequenz: `[1.0, 2.0, 4.0, 8.0, 16.0, 30.0]`, dann 30 s repeat.
    - Nutze `asyncio.sleep(delay)` für Backoff — **nicht** blockierendes `time.sleep`.
    - `ha_ws_connected`-Flag als Property (`bool`) — wird von Auth-Success auf `True` gesetzt, von Socket-Error/`auth_invalid` auf `False`.
    - Re-Subscribe-Logik: nach erfolgreichem Reconnect über `self._client._subscriptions`-Liste iterieren und jeden Payload erneut senden. Neue Message-IDs werden vom `HaWebSocketClient` vergeben.
  - [ ] **Fehler-Taxonomie loggen** (AC 4):
    - `ConnectionClosed`, `ConnectionRefused` → log level `warning`, Kontext `{event: "ha_ws_disconnected", reason: <str>, next_backoff_s: <float>}`
    - `AuthError` (token invalid) → log level `error`, **kein Auto-Retry** (Token ist statisch im Add-on-Container; wenn ungültig, Supervisor-Rotation nötig). Stattdessen: `ha_ws_connected = False`, und äußerer Lifespan-Task schläft 30 s vor erneutem Connect-Versuch.
    - `asyncio.TimeoutError` bei `call_service` → log level `warning`, keine Disconnect-Aktion.
  - [ ] Bei jedem Reconnect-Versuch Attempt-Counter inkrementieren und im Log mitgeben — essentiell für Story 4.2 (Fehler-Historie).
- [ ] **Task 4: Integration in `main.py` Lifespan** (AC: 1, 2, 6)
  - [ ] FastAPI `lifespan`-Kontext-Manager in `main.py` (ersetzt `@app.on_event("startup")`/`shutdown` — Deprecated seit FastAPI 0.110):
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        app.state.ha_client = ReconnectingHaClient(token=settings.supervisor_token)
        app.state.started_at = time.monotonic()
        app.state.ha_client_task = asyncio.create_task(
            app.state.ha_client.run_forever(on_event=_noop_event_handler)
        )
        try:
            yield
        finally:
            app.state.ha_client_task.cancel()
            await app.state.ha_client.close()
    ```
  - [ ] `_noop_event_handler` ist ein Platzhalter (`async def _noop(_: dict) -> None: pass`) — spätere Stories (3.1 Controller, 2.2 Auto-Detection) registrieren echte Handler via Subscription-Flow.
  - [ ] **Keine anderen Module** von dieser Story berühren (keine Controller-Logik, keine Adapter, keine Executor-Stub) — Scope-Disziplin.
- [ ] **Task 5: Health-Endpoint erweitern (`api/routes/health.py`)** (AC: 6)
  - [ ] Bestehenden `GET /api/health` aus Story 1.1 (lieferte nur `{"status": "ok"}`) um zwei Felder erweitern:
    ```python
    @router.get("/health")
    async def health(request: Request) -> dict:
        return {
            "status": "ok",
            "ha_ws_connected": request.app.state.ha_client.ha_ws_connected,
            "uptime_seconds": int(time.monotonic() - request.app.state.started_at),
        }
    ```
  - [ ] **Kein Wrapper** `{"data": …, "success": true}` (CLAUDE.md Regel 4). Direktes Objekt.
  - [ ] **Response-Type:** Plain `dict` oder ein dediziertes Pydantic-Modell `HealthResponse` in `api/schemas/health.py`. Pydantic bevorzugt (type-safe + OpenAPI-Doku).
  - [ ] HTTP-Status bleibt `200` auch bei `ha_ws_connected=false` — der Prozess lebt, nur der Upstream ist weg. HA-Binary-Sensor-Taugliche Payload.
  - [ ] Telemetrie-Freiheit (NFR17): keine User-IDs, keine Entities, keine Debug-Infos im Response.
- [ ] **Task 6: Mock-HA-WebSocket-Fixture + Integrationstest** (AC: 5)
  - [ ] Neuer Ordner: `backend/tests/integration/mock_ha_ws/` (laut architecture.md §688)
  - [ ] `mock_ha_ws/server.py` — minimaler `websockets`-Server, der:
    - Auf Connection `{"type": "auth_required", "ha_version": "2026.4.3"}` sendet
    - Auf `auth`-Message mit korrektem Token mit `{"type": "auth_ok"}` antwortet
    - Auf `subscribe_trigger`/`subscribe_events`-Messages eine `{"id": <id>, "type": "result", "success": true}` sendet
    - Einen `trigger_disconnect()`-Hook hat für Test-Szenarien (schließt die Connection mit Code 1011)
  - [ ] `backend/tests/integration/test_ha_client_reconnect.py`:
    - Test 1: Connect + Auth-Success → `ha_ws_connected=True`, ein Subscribe-Call, `result`-Response empfangen
    - Test 2: Erzwungenes Disconnect nach erfolgreichem Connect → Backoff-Timer (mit `asyncio`-Time-Mock via `pytest-asyncio` + `freezegun` oder manuellem `monkeypatch` auf `asyncio.sleep`) → Reconnect in < 30 s → Re-Subscribe der vor dem Abbruch registrierten Subscription
    - Test 3: Auth mit invalidem Token → `AuthError`, `ha_ws_connected=False`, kein Endlos-Retry in engem Loop
  - [ ] **Kein echter HA-Server** in CI — rein mock-basiert. Die `websockets`-Library erlaubt lokale Test-Server auf `ws://localhost:<random_port>`.
- [ ] **Task 7: `config.py` erweitern (falls Story 1.1 nicht bereits gesetzt hat)** (AC: 1)
  - [ ] Sicherstellen, dass `backend/src/solalex/config.py` ein Feld `supervisor_token: str` (aus Env-Var `SUPERVISOR_TOKEN`) liest. Story 1.1 hat dieses Feld bereits angelegt — **nicht doppelt definieren**, nur verifizieren.
  - [ ] Default-Value: kein Default. Fehlt der Token → `pydantic-settings`-Validation-Fehler beim Startup (das ist korrekt: ohne Token kann der Add-on nicht arbeiten).
  - [ ] `SUPERVISOR_TOKEN` ist im HA-Add-on-Container per Supervisor automatisch gesetzt — kein Nutzer-Input nötig.
- [ ] **Task 8: Smoke-Tests & Final Verification** (AC: 1–6)
  - [ ] `uv run pytest backend/tests/integration/test_ha_client_reconnect.py` — alle 3 Tests grün
  - [ ] `uv run pytest backend/tests/unit/test_main.py` — Health-Endpoint-Test grün (neuer Shape mit `ha_ws_connected`)
  - [ ] `uv run ruff check backend/src/solalex/ha_client/` → clean
  - [ ] `uv run mypy --strict backend/src/solalex/ha_client/` → clean
  - [ ] Manuelle Verifikation per `curl http://<ingress>/api/health`: Response-Shape matcht AC 6

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md §HA-WebSocket-Reconnect (Zeile 367)](../planning-artifacts/architecture.md) — Backoff-Sequenz, persistente Subscription-Liste
- [architecture.md §ha_client/ Directory-Layout (Zeile 637-640)](../planning-artifacts/architecture.md) — `client.py`, `reconnect.py`, `types.py`
- [architecture.md §Supervisor-Token-Handling (Zeile 335)](../planning-artifacts/architecture.md) — in Memory, nicht persistieren, Re-Connect bei Rotation
- [architecture.md §Implementation Sequence #3 (Zeile 443)](../planning-artifacts/architecture.md) — HA-WS-Adapter als 3. Bootstrap-Schritt
- [architecture.md §API-Communication-Patterns (Zeile 337-367)](../planning-artifacts/architecture.md) — RFC 7807, kein asyncio.Queue-Bus
- [prd.md §Connectivity & Integration Protocol (Zeile 417-423)](../planning-artifacts/prd.md) — Endpoint, Auth, Subscription-Pattern, Reconnect-Spec
- [prd.md §Integration Reliability NFR29 (Zeile 695)](../planning-artifacts/prd.md) — Exponential-Backoff-Werte autoritativ
- [epics.md Epic 1 Story 1.3 (Zeile 512-546)](../planning-artifacts/epics.md) — Original-AC
- [CLAUDE.md — Regel 4 + 5, Anti-Patterns](../../CLAUDE.md)

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope-Disziplin:**

Diese Story berührt **ausschließlich Backend**. Kein Frontend-Code, keine Svelte-Änderungen, kein Polling-Hook (kommt in Epic 5). Kein Controller, kein Executor, keine Adapter.

**Dateien, die berührt werden dürfen:**
- NEU: `backend/src/solalex/ha_client/{__init__.py, client.py, reconnect.py, types.py}`
- NEU: `backend/src/solalex/api/schemas/health.py` (Pydantic-Modell für Health-Response)
- NEU: `backend/tests/integration/mock_ha_ws/{__init__.py, server.py}`
- NEU: `backend/tests/integration/test_ha_client_reconnect.py`
- MOD: `backend/src/solalex/main.py` (Lifespan um HA-Client-Task erweitern)
- MOD: `backend/src/solalex/api/routes/health.py` (Response-Shape erweitert)
- MOD: `backend/tests/unit/test_main.py` (Health-Test-Assertion erweitert)
- **Nur verifizieren, nicht ändern:** `backend/src/solalex/config.py` (`supervisor_token`-Feld), `backend/src/solalex/common/logging.py` (`get_logger`)

**Wenn Du anfängst, Svelte/TS/Adapter/Controller-Code zu schreiben — STOP. Falsche Story.**

**Wenn Du `asyncio.Queue` oder ein Event-Bus-Modul baust — STOP.** Event-Handler ist ein direktes Callable, das der Lifespan als `on_event`-Argument übergibt (Platzhalter `_noop` in dieser Story).

**Wenn Du die Subscription-Liste in SQLite persistierst — STOP.** "Persistent" bedeutet hier: überlebt Reconnect innerhalb desselben Prozesses. Bei Container-Restart registriert der Controller alle benötigten Subscriptions neu (kommt in Story 3.1).

### Stack-Versionen (EXAKT aus Story 1.1 übernehmen)

| Komponente | Version-Source |
|---|---|
| `websockets` | ≥ 13 (aus Story 1.1 `pyproject.toml`) |
| Python | 3.13 |
| FastAPI | ≥ 0.135.1 (Lifespan-ContextManager-Pattern, async) |
| `pytest-asyncio` | ≥ 0.24 (asyncio-Fixture-Support) |

**Keine neuen Dependencies.** Alles, was gebraucht wird, ist in Story 1.1 `pyproject.toml` deklariert.

### HA-WebSocket-Protokoll — Minimal-Spec

(Relevante Subset für Story 1.3 — vollständige Spec: [developers.home-assistant.io/docs/api/websocket](https://developers.home-assistant.io/docs/api/websocket))

**Auth-Handshake:**
```json
// Server → Client (on connect)
{"type": "auth_required", "ha_version": "2026.4.3"}

// Client → Server
{"type": "auth", "access_token": "<SUPERVISOR_TOKEN>"}

// Server → Client (success)
{"type": "auth_ok", "ha_version": "2026.4.3"}

// Server → Client (failure)
{"type": "auth_invalid", "message": "Invalid token"}
```

**Subscribe-Pattern:**
```json
// Client → Server
{"id": 1, "type": "subscribe_trigger", "trigger": {"platform": "state", "entity_id": "sensor.foo"}}

// Server → Client (acknowledgement)
{"id": 1, "type": "result", "success": true, "result": null}

// Server → Client (event, async)
{"id": 1, "type": "event", "event": {"variables": {"trigger": {...}}}}
```

**Message-ID-Regel:** Monoton ab 1 pro Connection-Session. Nach Reconnect neu ab 1.

### Anti-Patterns & Gotchas

- **KEIN `asyncio.Queue`-Pub/Sub-Bus** — Direktaufruf `on_event`-Callback, siehe [architecture.md §365](../planning-artifacts/architecture.md). Amendment 2026-04-22 hat das ausdrücklich gestrichen.
- **KEIN structlog** — stdlib `logging` via `get_logger(__name__)` (CLAUDE.md Regel 5). Story 1.1 hat den Wrapper bereits angelegt.
- **KEINE SQLite-Persistierung der Subscription-Liste** — In-Memory reicht. Re-Registrierung erfolgt durch den Controller bei jedem Prozess-Start.
- **KEIN Blocking-Sleep** (`time.sleep`) im Backoff — immer `await asyncio.sleep(delay)`. Sonst blockiert der Event-Loop den FastAPI-Uvicorn-Worker.
- **KEINE Correlation-IDs in v1** (CLAUDE.md). Kontext-Felder wie `reconnect_attempt`, `last_message_id` reichen für die Diagnose-Story (Epic 4).
- **KEIN Token-Logging** — `SUPERVISOR_TOKEN` darf nie in Logs erscheinen (auch nicht gekürzt). Security-Review-Gate.
- **KEIN Retry bei `auth_invalid`** — der Token ist im Add-on-Container statisch. Ungültig → Log als `error`, 30-s-Grace, dann neuer Connect-Versuch (eventuell wurde der Token rotiert). **Kein Tight-Loop-Retry** (würde HA-Supervisor-Logs fluten).
- **KEIN Wrapper-Response** beim Health-Endpoint (CLAUDE.md Regel 4). `{"status": "ok", "ha_ws_connected": bool, "uptime_seconds": int}` — direkt.
- **KEIN HTTP-503** bei `ha_ws_connected=false` — Prozess lebt, Zustand steckt im Payload. HA-Binary-Sensor soll genau diesen Zustand lesen können ohne auf 5xx-Fehler zu reagieren.
- **KEIN Frontend-Polling** dieses Endpunkts in dieser Story — das ist Epic 5 (Dashboard-State-Polling). Story 1.3 stellt den Endpoint nur bereit.
- **KEIN direkter Import** von `websockets.legacy.client.connect` — die Library hat die neue `async with websockets.connect(url) as ws`-API; Legacy-Pfade sind in `websockets` ≥ 13 deprecated.
- **KEIN `on_event`-Callback, der blockiert** — alle Handler müssen `async` sein. Wenn ein Handler blockiert, hängt der Listen-Loop.

### Source Tree — zu erzeugende/ändernde Dateien (Zielzustand nach Story)

```
backend/
├── src/solalex/
│   ├── main.py                                [MOD — Lifespan um HA-Client-Task]
│   ├── ha_client/                             [NEW directory]
│   │   ├── __init__.py                        [NEW — re-exports HaWebSocketClient, ReconnectingHaClient]
│   │   ├── client.py                          [NEW — HaWebSocketClient]
│   │   ├── reconnect.py                       [NEW — ReconnectingHaClient + Backoff]
│   │   └── types.py                           [NEW — TypedDicts/Pydantic für HA-WS-Messages]
│   ├── api/
│   │   ├── routes/
│   │   │   └── health.py                      [MOD — Response-Shape erweitert]
│   │   └── schemas/
│   │       ├── __init__.py                    [NEW (falls nicht von 1.1 angelegt)]
│   │       └── health.py                      [NEW — HealthResponse Pydantic-Model]
│   └── common/
│       └── logging.py                         [VERIFY — aus Story 1.1, nicht ändern]
└── tests/
    ├── unit/
    │   └── test_main.py                       [MOD — Health-Assertion erweitert]
    └── integration/                           [NEW directory (falls nicht von 1.1 angelegt)]
        ├── __init__.py                        [NEW]
        ├── mock_ha_ws/
        │   ├── __init__.py                    [NEW]
        │   └── server.py                      [NEW — Mock-WS-Server]
        └── test_ha_client_reconnect.py        [NEW — 3 Test-Szenarien]
```

### Library/Framework Requirements

**Backend-Dependencies (bereits in `pyproject.toml` aus Story 1.1):**

```toml
dependencies = [
    "fastapi[standard]>=0.135.1",
    "uvicorn[standard]>=0.30",
    "aiosqlite>=0.20",
    "websockets>=13",                     # ← genutzt in Task 2
    "pydantic-settings>=2.6",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",               # ← genutzt in Task 6
    "pytest-cov>=5",
    "ruff>=0.8",
    "mypy>=1.13",
]
```

**Keine neuen Dependencies.**

### Code-Muster — `HaWebSocketClient` (Copy-Paste-sicher, als Startpunkt)

```python
# backend/src/solalex/ha_client/client.py
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

import websockets

from solalex.common.logging import get_logger

log = get_logger(__name__)


class AuthError(Exception):
    """Raised when HA rejects the supervisor token."""


class HaWebSocketClient:
    def __init__(
        self,
        token: str,
        url: str = "ws://supervisor/core/websocket",
    ) -> None:
        self._token = token
        self._url = url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._next_id: int = 1
        self._subscriptions: list[dict[str, Any]] = []
        self._pending_results: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._connected: bool = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._url)
        auth_required = json.loads(await self._ws.recv())
        if auth_required.get("type") != "auth_required":
            raise RuntimeError(f"unexpected first message: {auth_required!r}")
        await self._ws.send(
            json.dumps({"type": "auth", "access_token": self._token})
        )
        auth_result = json.loads(await self._ws.recv())
        if auth_result.get("type") == "auth_invalid":
            raise AuthError(auth_result.get("message", "auth_invalid"))
        if auth_result.get("type") != "auth_ok":
            raise RuntimeError(f"unexpected auth response: {auth_result!r}")
        self._connected = True
        log.info("ha_ws_auth_ok", extra={"ha_version": auth_result.get("ha_version")})

    async def subscribe(self, payload: dict[str, Any]) -> int:
        assert self._ws is not None
        msg_id = self._next_id
        self._next_id += 1
        message = {"id": msg_id, **payload}
        self._subscriptions.append(payload)
        await self._ws.send(json.dumps(message))
        return msg_id

    # ... call_service, listen, close — siehe Task 2
```

**Dies ist ein Startpunkt, nicht die finale Implementation.** Der Dev-Agent ergänzt `call_service`, `listen`, `close`.

### Testing Requirements

- **Framework:** `pytest` + `pytest-asyncio`. Async-Tests als `@pytest.mark.asyncio`.
- **Mock-Server:** `websockets`-Library-eigener Server-Support (`websockets.serve`) auf `localhost`-Random-Port. Kein Docker, kein HA-Test-Container.
- **Time-Mock für Backoff-Assertion:** Entweder `freezegun` (muss zu Dev-Deps hinzugefügt werden — **vorher klären**) oder `monkeypatch`-Ersatz von `asyncio.sleep` durch eine recording/accelerating Fake-Funktion. **Bevorzugt: `monkeypatch`-Variante** (keine neue Dep).
- **Coverage-Anspruch:** `ha_client/`-Modul ≥ 70 % (Regelungs-Kern-Logik-Kriterium NFR35). Nicht kritisch für Story-Approval, aber Ziel.
- **Manual-Test auf echtem HA:** optional in der Beta-Phase. Für CI reicht Mock.

### Previous Story Intelligence — Lessons aus Story 1.1 + 1.2

**Aus Story 1.1:**
- **`common/logging.py` existiert** mit `get_logger(name)`-Wrapper (stdlib + JSONFormatter + RotatingFileHandler). **Nicht neu bauen. Nicht ersetzen.**
- **`config.py` hat `supervisor_token`-Field** via `pydantic-settings`. **Nur verifizieren.**
- **`main.py` hat Lifespan-Gerüst** (Story 1.1 Task 3). Diese Story füllt den Lifespan um die HA-Client-Task.
- **`tests/conftest.py` + `tests/unit/test_main.py` existieren**. Health-Test erweitern, nicht neu anlegen.
- **Integration-Test-Ordner (`tests/integration/`) existiert möglicherweise noch nicht** — Story 1.1 hat nur `tests/unit/` angelegt. In dieser Story neu erzeugen.

**Aus Story 1.2:**
- **Snake-case-Disziplin gilt auch für JSON-Feldnamen** — `ha_ws_connected`, `uptime_seconds` (nicht `haWsConnected`, nicht `uptimeSeconds`).
- **JSON-Response ohne Wrapper** (CLAUDE.md Regel 4) — ist in Story 1.2 als harte Regel bestätigt.
- **Version-Pin-Disziplin** in `addon/config.yaml` (Story 1.2 Task 1) bleibt unverändert — diese Story berührt `addon/` nicht.

### Git Intelligence

- **Repo-Zustand:** Nur Initial-Commit. Stories 1.1 + 1.2 sind `ready-for-dev`, noch nicht merged.
- **Story-Abhängigkeit:** Story 1.3 setzt Story 1.1 voraus (Backend-Skeleton, `config.py`, `common/logging.py`, `health.py`). Story 1.2 ist **nicht blockierend** für 1.3 (reines Config-File + Markdown).
- **Reihenfolge:** Story 1.1 → Story 1.3 (kann parallel zu 1.2 laufen, da kein Overlap in Code-Files).
- **Commit-Message-Stil (CLAUDE.md §Git):** Deutsch, kurz, Imperativ. Beispiel: `Add HA-WebSocket-Client mit Reconnect-Logik + Health-Endpoint-Erweiterung`. **Keine Commits ohne explizite Alex-Anweisung.**

### Latest Technical Information

- **`websockets`-Library ≥ 13:** Neuer API-Stil: `async with websockets.connect(url) as ws: ...`. Legacy-API (`websockets.legacy.client.connect`) ist deprecated. Quelle: [websockets.readthedocs.io](https://websockets.readthedocs.io/).
- **FastAPI Lifespan-Pattern:** `@asynccontextmanager`-basiert statt `@app.on_event("startup")` (deprecated seit 0.110). Minimal-Muster dokumentiert in [fastapi.tiangolo.com/advanced/events](https://fastapi.tiangolo.com/advanced/events/).
- **HA-WebSocket-API-Stand April 2026:** Unverändert stabil gegenüber 2025er-Spec. Auth-Handshake + `subscribe_trigger`/`call_service` sind die drei relevanten Operationen für v1.
- **`SUPERVISOR_TOKEN`-Rotation:** HA-Supervisor rotiert den Token bei Add-on-Neustart, nicht zur Laufzeit. Innerhalb eines Container-Lebens ist der Token stabil. Architektur §335 bestätigt: bei Rotation → neuer Connect.

### Project Structure Notes

- **Alignment:** `ha_client/` als Package-Verzeichnis mit drei Dateien matcht [architecture.md §637-640](../planning-artifacts/architecture.md) exakt.
- **Abweichung:** Keine.
- **Neue `tests/integration/`-Struktur:** Erstmalig in dieser Story angelegt — setzt Präzedenz für Epic 2 (Adapter-Integration-Tests) und Epic 3 (Controller-E2E-Tests).

### References

- [architecture.md – HA-WebSocket-Reconnect](../planning-artifacts/architecture.md)
- [architecture.md – ha_client Directory](../planning-artifacts/architecture.md)
- [architecture.md – Supervisor-Token-Handling](../planning-artifacts/architecture.md)
- [architecture.md – Implementation Sequence #3](../planning-artifacts/architecture.md)
- [prd.md – Connectivity & Integration Protocol](../planning-artifacts/prd.md)
- [prd.md – NFR29 HA-WS-Reconnect](../planning-artifacts/prd.md)
- [prd.md – NFR17 keine Telemetry](../planning-artifacts/prd.md)
- [epics.md – Epic 1 Story 1.3](../planning-artifacts/epics.md)
- [CLAUDE.md – 5 harte Regeln (Regel 4 + 5 besonders)](../../CLAUDE.md)
- [HA WebSocket API – developers.home-assistant.io](https://developers.home-assistant.io/docs/api/websocket)
- [websockets-Library Docs – readthedocs.io](https://websockets.readthedocs.io/)
- [FastAPI Lifespan Events – tiangolo.com](https://fastapi.tiangolo.com/advanced/events/)
- [Story 1.1 (Add-on Skeleton)](./1-1-add-on-skeleton-mit-custom-repository-multi-arch-build.md)
- [Story 1.2 (Landing-Page + HA-Version-Range)](./1-2-landing-page-voraussetzungs-hinweis-ha-versions-range.md)

### Story Completion Status

Diese Story ist abgeschlossen, wenn:

1. `backend/src/solalex/ha_client/` mit `client.py`, `reconnect.py`, `types.py` existiert und kompiliert.
2. `main.py`-Lifespan startet den HA-Client als Background-Task, cancelt sauber bei Shutdown.
3. `GET /api/health` liefert `{"status": "ok", "ha_ws_connected": bool, "uptime_seconds": int}` ohne Wrapper.
4. 3 Integration-Tests (`test_ha_client_reconnect.py`) grün — Connect/Auth, Reconnect-Backoff, AuthError-No-Retry.
5. `uv run ruff check` + `uv run mypy --strict` auf `ha_client/`-Modul clean.
6. Keine Dependency-Addition, keine Frontend-Änderung, kein Controller-Code.

**Nächste Story nach 1.3:** Story 1.4 (ALKLY-Design-System-Foundation — Frontend-Fokus, Tokens + DM-Sans-Pipeline). Story 1.3 stellt sicher, dass Controller in Story 3.1 den HA-Client direkt übernehmen kann.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
