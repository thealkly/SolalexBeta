# Story 3.6: User-Config — Min/Max-SoC & Nacht-Entlade-Zeitfenster

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Nutzer,
I want Min-SoC, Max-SoC pro Akku-Setup und ein Nacht-Entlade-Zeitfenster nach der Inbetriebnahme im Settings-Bereich konfigurieren können,
so that ich die Leitplanken für meinen Akku an meine Akku-Spec und meinen Tagesrhythmus anpasse — ohne den Setup-Wizard erneut zu durchlaufen oder das Add-on neu zu starten.

**Scope-Pflock:** Diese Story baut zwei orthogonale Bausteine zum bestehenden System (Story 2.1 hat die Felder bereits im Wizard erfasst, aber post-Commissioning weder Edit-UI noch Controller-Live-Reload, und die Nacht-Entlade-Konfiguration ist im Controller bisher folgenlos persistiert):

1. **Settings-Route + PATCH-Endpoint** — Neue versteckte Route `/settings`, in der der commissioned User Min-SoC, Max-SoC, Nacht-Entlade-Toggle und Zeitfenster ändert. Persistierung via `PATCH /api/v1/devices/battery-config` (kein erneuter Wizard-Durchlauf). Live-Reload des Controllers nach Save (kein Add-on-Neustart).
2. **Nacht-Entlade-Zeitfenster im Speicher-Modus** — Erweiterung von `_policy_speicher` (und implizit `_policy_multi`-Speicher-Branch): Wenn `night_discharge_enabled=True` und die aktuelle lokale Uhrzeit **außerhalb** des konfigurierten `[night_start, night_end]`-Fensters liegt, wird die Entladung (Bezug-Branch) gegated — der Akku bleibt auf SoC stehen, statt die Tages-Energiereserve in der Mittagspause zu verheizen.

**Was diese Story NICHT tut:**
- Keine Änderung an `_evaluate_mode_switch` / `_record_mode_switch_cycle` / `_policy_multi`-Routing (3.5 bleibt unangetastet — `_policy_multi` ruft `_policy_speicher`, der den Nacht-Gate enthält, weiter wie gehabt).
- Keine Änderung an `Mode.EXPORT` / `_policy_export` (Story 3.8 ist parallel `ready-for-dev` — Surplus-Export ignoriert das Nacht-Fenster, weil EXPORT nur bei Pool-Voll greift und dann ohnehin keine Entladung stattfindet).
- Keine Anpassung an `select_initial_mode` oder Mode-Override-UI (3.5 bleibt der Owner — die bestehende „Regelungs-Modus"-Card aus Config.svelte wird nicht migriert).
- Kein neuer SQL-Schema-Migration. Schlüssel `min_soc`, `max_soc`, `night_discharge_enabled`, `night_start`, `night_end` leben seit 2.1 in `wr_charge.config_json`. Die PATCH-Route schreibt nur denselben Blob neu.
- Keine Smart-Meter-/WR-Limit-Edits post-Commissioning (Hardware-Identität bleibt locked — Re-Commissioning ist explizit out-of-scope).
- Kein Settings-Link in `Running.svelte` für die Generic-User-Discovery (Settings ist v1 versteckt, analog zu 4.0a Diagnose-Route — Beta-User bekommen die URL aus Discord/Doku).
- Kein Forecast-/Solar-Calendar (sunrise/sunset-Berechnung) — das Nacht-Fenster ist eine starre Wand-Uhr-Zeitspanne in lokaler Container-Zeitzone.
- Keine Override-Plausibilitäts-Schranke für Max-SoC (Hersteller-Schäden bei Überladung sind hardwareseitig durch Marstek-BMS abgesichert; nur Min-SoC braucht den Tiefentlade-Hinweis).

**Architektur-Bezug:** Story-Diff liegt in 3 Backend-Files (`api/schemas/devices.py`, `api/routes/devices.py`, `controller.py`), 2 Frontend-Files (neue `routes/Settings.svelte`, App-Routing-Anpassung in `App.svelte`), 1 erweitertem `client.ts` und neuen Repository-Helpern in `persistence/repositories/devices.py`. **Keine SQL-Migration**, **keine neue Dependency**.

**Scope-Tension Hard-Floor vs. Plausibilitäts-Warnung (aufgelöst):** Story-2.1 erzwingt `min_soc ≥ 5` per Pydantic `ge=5`. Story-3.6 AC 3 verlangt eine zweistufige UX: < 5 % darf eingegeben werden, aber löst eine UI-Warnung „Unterhalb Herstellerspezifikation — Akku-Schäden möglich" + zweite Bestätigung aus. **Aufgelöst:** Pydantic-Floor bleibt **bei 5 %** (Marstek-BMS-Schutzgrenze, hardware-seitig definitiv). Werte zwischen 5 % und 10 % triggern in der **UI** den Plausibilitäts-Hinweis (aber kein zweiter Backend-Roundtrip — der Confirm-Dialog ist reine Frontend-Logik). Werte < 5 % werden im Backend rejected (HTTP 422). Begründung: Marstek Venus 3E spezifiziert Mindest-SoC 10 %; 5 % ist absolute Hardware-Untergrenze. Eine Eingabe von z. B. 7 % ist zulässig aber riskant → Warnung + zweite Bestätigung fängt versehentliche Tiefentladung ab.

**Scope-Tension Live-Reload (aufgelöst):** AC 6 verlangt „ohne Add-on-Neustart vom Controller aufgenommen". `_policy_speicher` liest die SoC-Bounds in jedem Sensor-Event über `_read_soc_bounds(charge_device)` — die Helper liest aus dem **gecachten** `DeviceRecord.config_json`-String. Dieser Cache wird bei `lifespan` einmalig aus der DB geladen und im `Controller._battery_pool.members[*].charge_device` gehalten. **Aufgelöst:** Nach erfolgreichem PATCH ruft die Route synchron `controller.reload_devices_from_db()` auf — eine neue async Methode am `Controller`, die `list_devices(conn)` neu zieht und den `_battery_pool`, `_devices_by_role` sowie `_wr_limit_device` rebuildet. Der Reload ist **idempotent** und kollidiert nicht mit laufenden Dispatch-Tasks (per-Device-Lock aus 3.1 schützt; Reload schreibt nur Referenzen am Controller-Objekt, keine Member-State-Mutation). Begründung: DB-Read pro Sensor-Event wäre Performance-Regression (Story 3.4 Review wies das explizit zurück); Reload-on-Save ist die etablierte Lösung.

**Scope-Tension Time-Zone (aufgelöst):** Container läuft per Default in HA Supervisor TZ (= `TZ`-Env-Var, übernommen vom Host). Backend speichert alle Timestamps **UTC-aware** (`_utc_now()` in `controller.py`). **Aufgelöst:** Der Nacht-Entlade-Helper liest `datetime.now()` **ohne tz** (lokale Container-Zeit) und vergleicht reine `HH:MM`-Strings. Begründung: Der User konfiguriert das Fenster in seiner Wand-Uhr-Logik („Nacht beginnt um 20 Uhr"). Wenn der HA-Container in `Europe/Berlin` läuft, ist `datetime.now().time()` ≡ Berliner Wand-Uhr — exakt was der User erwartet. Der bestehende `now_fn`-Hook bleibt UTC-aware (Audit-Cycles, Dwell-Time); der Nacht-Helper bekommt ein eigenes `local_now_fn`-Injection-Argument, damit Tests deterministisch laufen. **Kein** ZoneInfo-Lookup, **keine** TZ-Migration der DB-Spalten. v1.5 darf das auf einen HA-Config-Hook ausbauen, falls User-Feedback es verlangt.

**Scope-Tension Settings-Discovery (aufgelöst):** UX-Spec Zeile 278 erwähnt „Settings → Diagnose öffnen", aber es gibt heute **keine** Settings-Surface. AC 1 sagt „Settings-Bereich der UI". `Running.svelte` ist die Beta-Landing post-Commissioning — sie hat keine Settings-Verlinkung. **Aufgelöst:** Settings-Route ist v1 **versteckt** (analog 4.0a Diagnose-Schnellexport). Beta-User erreichen `#/settings` via Discord/Beta-Doku. v1.5 verdrahtet Settings + Diagnose in einer dedicated Footer-/Header-Nav (eigene Story). Begründung: Discovery-UI für Settings würde Running.svelte's Mini-Shell-Pattern aus 5.1a brechen; das Risiko, einen halbgaren Nav-Knopf zu bauen, ist höher als der Nutzen. Der Settings-Eintrag in `App.svelte::VALID_ROUTES` plus ein Eintrag in `App.svelte::WIZARD_ROUTES` (oder ein neues `POST_COMMISSIONING_ROUTES`-Set) genügt — ein commissioned User darf `#/settings` betreten, ein nicht-commissioned User wird auf `#/disclaimer` gegated.

## Acceptance Criteria

1. **Settings-Route erreichbar nur post-Commissioning (FR22, FR20):** `Given` der User ist commissioned (`devices.every(d => d.commissioned_at !== null)` ist `true`), `When` er `#/settings` aufruft, `Then` rendert `App.svelte` `<Settings />` ohne Redirect, **And** der `evaluateGate`-Decision-Tree liefert `{kind: 'stay'}` für `currentRoute === '/settings'` bei commissioned-State, **And** `'/settings'` ist in `VALID_ROUTES` aufgenommen (sonst Hash-Reset auf `/`), **And** `'/settings'` ist **nicht** in `WIZARD_ROUTES` (sonst würde 2.3a-Gate einen commissioned User auf `#/running` zurückwerfen — Test: `evaluateGate({devices: [commissioned], currentRoute: '/settings', preAccepted: true, allowAutoForward: false}) === {kind: 'stay'}`), **And** ein nicht-commissioned User wird auf `#/disclaimer` (oder `#/`) gegated wie für andere Wizard-Routes (Test: `evaluateGate({devices: [{commissioned_at: null}], currentRoute: '/settings', preAccepted: false, allowAutoForward: false}).kind === 'redirect'`).

2. **Settings-UI rendert Akku-Konfiguration (FR22, FR20):** `Given` `#/settings` ist erreichbar, `When` `Settings.svelte` rendert, `Then` lädt es per `client.getDevices()` die aktuelle Devices-Liste und extrahiert das `wr_charge`-Device (falls vorhanden); aus dessen `config_json` werden `min_soc`, `max_soc`, `night_discharge_enabled`, `night_start`, `night_end` als Initial-Werte der Form-Felder befüllt (Defaults `15`, `95`, `true`, `"20:00"`, `"06:00"` bei nicht-existenten Keys). **And** wenn **kein** `wr_charge`-Device existiert (drossel-only-Setup ohne Akku), zeigt die Seite einen deutschen Hinweis-Text „Dieses Setup hat keinen Akku. Min-/Max-SoC und Nacht-Entlade sind hier nicht konfigurierbar." und blendet das Form-Feld-Card aus.

3. **Validation Min < Max-SoC (Epic-AC 2):** `Given` der User editiert die Min-/Max-SoC-Felder, `When` er einen Wert setzt der `min_soc + 10 ≥ max_soc` macht (z. B. `min_soc=80, max_soc=85`), `Then` zeigt die UI vor dem Save eine **Inline-Error-Zeile** unter der Card mit dem Klartext „Max-SoC muss mehr als 10 % über Min-SoC liegen" und der Save-Button ist disabled. **And** wenn der User trotzdem an die Backend-Route POSTet (z. B. via direkter API), antwortet das Backend mit `422 Unprocessable Entity` und dem identischen RFC-7807-Detail-Text (bestehende Pydantic-Validierung in `HardwareConfigRequest.validate_soc_range` greift symmetrisch im neuen `BatteryConfigPatchRequest`-Schema — gemeinsamer `validate_soc_range`-Validator extrahiert).

4. **Plausibilitäts-Warnung Min-SoC < 10 % (Epic-AC 3):** `Given` der User trägt einen Min-SoC zwischen 5 und 9 ein, `When` der Save-Button geklickt wird, `Then` öffnet die UI **kein** Modal (UX-DR30 — keine Modals), sondern zeigt einen **inline Confirm-Block** unter dem Input mit:
   - Roter Warntext: „Min-SoC unterhalb Herstellerspezifikation (Marstek Venus: empfohlen ≥ 10 %) — Akku-Schäden bei wiederholter Tiefentladung möglich."
   - Zwei Buttons: „Abbrechen" (resettet auf den letzten validen Wert ≥ 10) und „Trotzdem speichern" (sendet PATCH mit `acknowledged_low_min_soc: true` Header oder Body-Field).
   - **Bis** der User „Trotzdem speichern" klickt, ist der reguläre Save-Button disabled.
   **And** das Backend-Schema `BatteryConfigPatchRequest` hat ein optionales `acknowledged_low_min_soc: bool = False`-Feld; wenn `min_soc < 10` und `acknowledged_low_min_soc=False` → `422` mit RFC-7807-Detail „Min-SoC unter Herstellerspezifikation — Bestätigung erforderlich (acknowledged_low_min_soc=true)". **Werte < 5** werden weiterhin **hart** rejected (Pydantic-Floor `ge=5`).

5. **Nacht-Entlade-Zeitfenster-Picker (Epic-AC 4):** `Given` der `night_discharge_enabled`-Toggle ist `true`, `When` der User die Settings-Seite rendert, `Then` zeigt sie zwei `<input type="time">`-Felder (Start, Ende) mit den persistierten Werten als Initial-Display. **And** wenn `night_discharge_enabled=false`, sind die Time-Inputs ausgeblendet (kein disabled — komplettes Hide). **And** das Pydantic-Schema validiert `night_start` und `night_end` mit Regex `^([01]\d|2[0-3]):[0-5]\d$` (Wieder-Verwendung aus 2.1).

6. **Validation Nacht-Fenster nicht leer (existing 2.1-Regel):** `Given` `night_discharge_enabled=true`, `When` `night_start === night_end` (z. B. beide `20:00`), `Then` rejected das Backend mit `422` und Klartext „Nacht-Entlade-Fenster darf nicht leer sein — Start- und Endzeit müssen sich unterscheiden" (Pydantic-Validator wiederverwendet, jetzt auch im PATCH-Pfad).

7. **PATCH-Endpoint Persistierung (Epic-AC 6):** `Given` der User hat valide Werte eingetragen und „Speichern" geklickt, `When` `PATCH /api/v1/devices/battery-config` mit Body `{min_soc, max_soc, night_discharge_enabled, night_start, night_end, acknowledged_low_min_soc?}` einläuft, `Then` validiert FastAPI das Body via `BatteryConfigPatchRequest`, **And** das Backend lädt das aktuelle `wr_charge`-Device aus der DB; existiert keines → `404 Not Found` mit Detail „Kein wr_charge-Device commissioned — Akku-Setup nicht vorhanden", **And** das Backend mergt die neuen Keys in den existierenden `config_json`-Blob (andere Keys wie `allow_surplus_export` aus 3.8 bleiben erhalten — kein Vollersatz), **And** persistiert via `update_device_config_json(conn, device_id, new_config_json)` (neuer Repository-Helper) als atomarer Single-Row-Update mit `commit`, **And** ruft synchron `request.app.state.controller.reload_devices_from_db()` auf, **And** antwortet mit `200 OK` und der **aktualisierten** `BatteryConfigResponse` (`min_soc, max_soc, night_discharge_enabled, night_start, night_end`) — kein Wrapper (CLAUDE.md Regel 4).

8. **Controller Live-Reload (Epic-AC 6):** `Given` der PATCH ruft `controller.reload_devices_from_db()`, `When` die Methode läuft, `Then` lädt sie via `connection_context(self._db_path)` (neues Init-Field in 3.6 oder Reuse `db_conn_factory`) frisch `await list_devices(conn)`, **And** baut `devices_by_role`, `_battery_pool` (`BatteryPool.from_devices(devices, ADAPTERS)`) und `_wr_limit_device` neu, **And** ersetzt die Felder am laufenden Controller-Objekt, **And** logged `_logger.info('controller_reload_devices', extra={...})` mit `pool_member_count` + `wr_charge_present`, **And** **kein** Mode-Switch wird ausgelöst (`_current_mode`, `_mode_baseline`, `_mode_switched_at`, `_forced_mode` bleiben unangetastet), **And** Subscriptions an HA-WS bleiben unverändert (Hardware-Entity-IDs sind locked — nur `config_json` ändert sich; `controller.reload_devices_from_db` triggert **nicht** `ensure_entity_subscriptions`). **Per-Device-Lock-Sicherheit:** Reload schreibt nur Felder am Controller; In-flight Dispatch-Tasks halten ihre eigenen `DeviceRecord`-Referenzen aus dem Closure und sehen erst beim **nächsten** Sensor-Event den neuen Pool. Akzeptiert (kein Race-Risk: alte und neue Bounds sind beide valide; SoC ändert sich um < 1 % pro Sekunde).

9. **Nacht-Entlade-Gate in `_policy_speicher` (Epic-AC 5, FR20):** `Given` `Mode.SPEICHER` (oder `Mode.MULTI`-Speicher-Branch) ist aktiv, **And** das `wr_charge`-Device hat `config_json.night_discharge_enabled=true` und ein konfiguriertes Fenster `[night_start, night_end]`, `When` `_policy_speicher` einen **Bezug-Branch** (Discharge — `smoothed > 0` UND nicht Min-SoC-gecappt) eintreten würde, **And** die aktuelle lokale Zeit `local_now().time()` liegt **außerhalb** des Fensters (siehe AC 11 Wraparound-Logik), `Then` returned `_policy_speicher` `[]` (kein Decision, kein Discharge-Setpoint), **And** das `_speicher_min_soc_capped`-Flag wird **nicht** gesetzt (es ist semantisch ein zeit-basiertes Gate, kein SoC-Cap), **And** ein einmaliges `_logger.info('speicher_discharge_blocked_outside_night_window', extra={'aggregated_pct', 'night_start', 'night_end', 'local_time'})` wird beim Eintritt in den Block-State geschrieben (Flag-Pattern analog `_speicher_max_soc_capped` aus 3.4 — neues Feld `self._speicher_night_gate_active: bool = False`, das beim Verlassen des Gates resettet). **Außerhalb des Bezug-Branches** (Charge / Deadband / Min-SoC-Cap) hat das Nacht-Fenster **keine** Wirkung — Laden bei PV-Überschuss ist tagsüber wie nachts erlaubt.

10. **Charge-Branch unbeeinflusst (FR15):** `Given` `Mode.SPEICHER` ist aktiv und Pool unter Max-SoC, `When` Einspeisung anliegt (`smoothed < 0`) und die lokale Zeit liegt außerhalb des Nacht-Fensters, `Then` läuft der Charge-Pfad ungehindert (Setpoint wird gesetzt). **Begründung:** Das Nacht-Fenster regelt nur die **Entladung zur Grundlast-Deckung**. Eine Einspeisung am Mittag (PV-Überschuss) muss den Akku laden, unabhängig vom Fenster.

11. **Wraparound-Logik für Mitternachts-überspannende Fenster (Epic-AC 5):** `Given` ein Nacht-Fenster `[night_start='20:00', night_end='06:00']` (Default — überspannt Mitternacht), `When` der Helper prüft, ob `local_now().time()` im Fenster liegt, `Then` ist die Logik: `start ≤ end` → `start ≤ now < end` (z. B. `[10:00, 14:00]` Tagesfenster); `start > end` → `now ≥ start OR now < end` (z. B. `[20:00, 06:00]` überspannt Mitternacht). **Edge-Case:** `start == end` ist via Pydantic-Validator (AC 6) ausgeschlossen — kein Test nötig.

12. **Disabled-Toggle bypassed das Gate (FR20):** `Given` `night_discharge_enabled=false`, `When` `_policy_speicher` läuft, `Then` ist das Nacht-Fenster komplett egal — Discharge bei Bezug ist 24/7 erlaubt (vorbehaltlich Min-SoC). **Test:** `test_speicher_discharge_allowed_anytime_when_night_disabled` — simuliert Mittagszeit mit `night_discharge_enabled=false` und Bezug → Discharge-Setpoint wird produziert.

13. **Default-Werte bei fehlenden Keys (Robustness):** `Given` ein älteres `wr_charge.config_json`, das die Nacht-Keys nicht enthält (Pre-3.6-Wizard, theoretisch Pre-2.1 — in Praxis gibt es keinen kommerziellen User mit so altem Schema, aber Tests/Edge-Cases existieren), `When` der Helper `_read_night_discharge_window(charge_device)` läuft, `Then` returned er `(enabled=True, start='20:00', end='06:00')` (Wizard-Defaults), **And** die `_policy_speicher`-Logik greift mit den Defaults — keine Exception, kein Crash.

14. **Helper `_read_night_discharge_window` (Architektur):** `Given` die Logik braucht die drei Keys aus `charge_device.config_json`, `When` der Helper aufgerufen wird, `Then` lebt er als Modul-Top-Level-Funktion in `controller.py` — **analog `_read_soc_bounds`**: `def _read_night_discharge_window(charge_device: DeviceRecord) -> tuple[bool, str, str]` (returns `(enabled, start_hhmm, end_hhmm)`). Defensive try/except gegen JSON-Parse-Fehler (gleiches Pattern wie `_read_soc_bounds`); Regex-Fallback auf `"20:00"/"06:00"` bei malformierten Strings; bool-Coerce für `enabled` (None/Missing → True).

15. **Helper `_is_in_night_window` (Pure Function):** `Given` die Wraparound-Logik soll testbar sein, `When` der Helper definiert wird, `Then` lebt er als Modul-Top-Level-Funktion: `def _is_in_night_window(local_time: time, start_hhmm: str, end_hhmm: str) -> bool`. Pure Function, kein I/O. Keine Logger-Calls. Tests injizieren `local_time = time(hour=21)` o. ä. direkt.

16. **`local_now_fn`-Injection in Controller (Test-Determinismus):** `Given` der Nacht-Helper braucht die lokale Wand-Uhr, `When` der Controller seine `_policy_speicher` aufruft, `Then` nutzt er **nicht** `datetime.now()` direkt, sondern eine injizierte `Callable[[], datetime]` namens `self._local_now_fn` (Default: `datetime.now` ohne tz — unterscheidet sich bewusst vom UTC-`now_fn` aus 3.5 für Audit-Cycles). **Constructor-Param:** `local_now_fn: Callable[[], datetime] = datetime.now`. Tests übergeben `local_now_fn=lambda: datetime(2026, 1, 1, 12, 0)` für Mittagszeit-Szenarien.

17. **Controller-Reload-API: Methode `reload_devices_from_db`:** `Given` die PATCH-Route triggert den Reload, `When` `Controller.reload_devices_from_db(self) -> None` definiert wird, `Then` lebt sie als async-Methode am Controller (nicht als Modul-Top-Level — sie mutiert Controller-Felder). Signatur: `async def reload_devices_from_db(self) -> None`. **Side-Effects (in dieser Reihenfolge):**
    1. `async with self._db_conn_factory() as conn: devices = await list_devices(conn)`.
    2. Rebuild `devices_by_role` aus `commissioned`-Devices (gleiches Filter wie in `lifespan`).
    3. Rebuild `battery_pool = BatteryPool.from_devices(devices, self._adapter_registry)`.
    4. Atomarer Field-Replace: `self._devices_by_role = devices_by_role; self._battery_pool = battery_pool; self._wr_limit_device = devices_by_role.get('wr_limit')`.
    5. `_logger.info('controller_reload_devices', extra={'pool_member_count': len(battery_pool.members) if battery_pool else 0, 'wr_charge_present': 'wr_charge' in devices_by_role, 'wr_limit_present': 'wr_limit' in devices_by_role})`.
    6. **Kein** Reset von `_speicher_buffers`, `_drossel_buffers`, `_speicher_last_setpoint_w`, `_speicher_pending_setpoints`, `_speicher_max_soc_capped`, `_speicher_min_soc_capped`, `_mode_switched_at` — Buffer-State und Hysterese-State sind **nicht** Device-gebunden, sondern Sensor-gebunden, und überleben den Reload.
    7. **Kein** Mode-Switch, **kein** Audit-Cycle.
    8. **Kein** HA-WS-Re-Subscribe (Entity-IDs sind locked — `lifespan` hat sie schon abonniert).

18. **Pre-Save-Smoothing-Buffer-Drift vermeiden (Defensive):** `Given` der User saved Min-SoC um 5 Punkte hoch (z. B. von 15 auf 20), `When` der Pool aktuell bei `aggregated_pct=18` parkt, `Then` triggert der nächste Sensor-Event den `_speicher_min_soc_capped`-Branch (neuer Min ist 20, aggregated 18 < 20). **Akzeptiert:** Cap-Flag setzt sich auf `True`, Discharge wird gegated, `_logger.info('speicher_mode_at_min_soc')` schreibt einmal — exakt das, was der User will. **Test:** `test_reload_then_min_soc_now_above_aggregated_caps_immediately`.

19. **Akku-Tile-„Kein Akku"-Hinweis (Epic-AC 1, drossel-only-Setup):** `Given` der User hat ein WR-only-Setup commissioned, `When` `Settings.svelte` lädt, `Then` zeigt es eine **deutsche** Hinweis-Karte (kein Error-Block, kein Modal) mit dem Titel „Kein Akku konfiguriert" und dem Body-Text „Dieses Setup hat keinen Akku. Min-/Max-SoC und Nacht-Entlade sind hier nicht konfigurierbar. Wenn du später einen Akku hinzufügst, durchläufst du den Setup-Wizard erneut." **And** ein Settings-Save-Button wird **nicht** gerendert. **Begründung:** Story 3.6 covered explizit nur Akku-Bounds; Hardware-Identität-Edits sind out-of-scope.

20. **API-Endpoint `PATCH /api/v1/devices/battery-config`:** `Given` der neue Endpoint im bestehenden `api/routes/devices.py`, `When` Story 3.6 ihn ergänzt, `Then` ergänzt die Datei eine Route:
    - **Method:** `PATCH`. **Pfad:** `/api/v1/devices/battery-config`. **Body:** Pydantic `BatteryConfigPatchRequest` mit `min_soc: int = Field(ge=5, le=40)`, `max_soc: int = Field(ge=51, le=100)`, `night_discharge_enabled: bool`, `night_start: str = Field(pattern=...)`, `night_end: str = Field(pattern=...)`, `acknowledged_low_min_soc: bool = False`. **Validator** (`@model_validator mode='after'`): identische Logik zu `HardwareConfigRequest.validate_soc_range` für die SoC-Bounds und das Nacht-Fenster (gemeinsame Helper-Functions, **kein** Copy-Paste — siehe Task 4).
    - **Response:** `BatteryConfigResponse` (`min_soc`, `max_soc`, `night_discharge_enabled`, `night_start`, `night_end`).
    - **Implementierung:** Lädt aktuelle Devices, sucht `wr_charge`-Row, mergt Update-Keys in `config_json`, persistiert via Repository-Helper, ruft `controller.reload_devices_from_db()`.
    - **Kein Wrapper** um JSON (CLAUDE.md Regel 4): `{"min_soc": 15, "max_soc": 95, ...}` direkt. Fehler folgen RFC 7807 (Middleware bestehend).
    - **License/Disclaimer-Gate:** Identisch zu `POST /api/v1/devices/` (heute keines — der `setup`-Pfad ist offen). PATCH bleibt analog offen (Settings ist post-Commissioning-Surface, Commissioning impliziert Disclaimer-Akzeptanz).

21. **Repository-Helper `update_device_config_json`:** `Given` die PATCH-Route braucht einen targeted Update, `When` der Helper definiert wird, `Then` lebt er in `persistence/repositories/devices.py`: `async def update_device_config_json(conn: aiosqlite.Connection, device_id: int, new_config_json: str, *, commit: bool = True) -> None`. SQL: `UPDATE devices SET config_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?`. **Kein** UPSERT — der Helper rejected non-existing IDs durch zero rowcount; die Route prüft die Existenz via `get_by_id` davor.

22. **Frontend — `Settings.svelte` rendert Form-Card:** `Given` `Settings.svelte` ist neu unter `frontend/src/routes/Settings.svelte`, `When` die Komponente rendert, `Then`:
    - Header: `<h1>Einstellungen</h1>` + Eyebrow „Solalex".
    - Card 1 „Akku-Konfiguration" mit den Min/Max-SoC-Inputs + Plausibilitäts-Confirm-Block (siehe AC 4).
    - Card 2 „Nacht-Entladung" mit Toggle + Time-Inputs (siehe AC 5).
    - Save-Button mit Klartext „Speichern" — disabled bei Validation-Error oder pending Plausibilitäts-Confirm.
    - Skeleton-Pulse während des initialen `getDevices()`-Calls (≥ 400 ms gegen Pop-In, gleiches Pattern wie 2.1).
    - Inline-Error-Zeilen unter den jeweiligen Feldern (kein Toast — UX-DR30).
    - Strings deutsch, hardcoded (CLAUDE.md — keine i18n).
    - Drossel-only-Setup → AC 19 Kein-Akku-Hinweis.

23. **Frontend — `client.ts::patchBatteryConfig`:** `Given` die Settings-Page braucht den Save-Call, `When` der Client erweitert wird, `Then` exportiert er:
    ```ts
    export async function patchBatteryConfig(body: BatteryConfigPatchRequest): Promise<BatteryConfigResponse>
    ```
    **And** die TS-Types `BatteryConfigPatchRequest` und `BatteryConfigResponse` in `lib/api/types.ts` ergänzen — analog zum `HardwareConfigRequest`-Muster.

24. **Frontend — Routing & Gate-Update:** `Given` die neue Route, `When` `App.svelte` und `lib/gate.ts` angepasst werden, `Then`:
    - `App.svelte::VALID_ROUTES` enthält `'/settings'`.
    - `App.svelte` rendert `<Settings />` für `currentRoute === '/settings'`.
    - `lib/gate.ts::WIZARD_ROUTES` enthält `'/settings'` **NICHT** (commissioned User darf rein) — das Set bleibt auf den Commissioning-Pfad-Routen begrenzt.
    - `lib/gate.ts::evaluateGate` returniert `{kind: 'stay'}` für `currentRoute === '/settings'` bei `allCommissioned=true`. Bei `!preAccepted` wird auf `#/disclaimer` gegated (gleicher Branch wie heute für Non-Wizard-Routes).
    - `evaluateGate` returniert für `'/settings'` bei `devices.length === 0 && preAccepted` ebenfalls `{kind: 'stay'}` (User landet in der „Kein Akku"-Hinweis-Card aus AC 19 — kein impliziter Wizard-Kick).
    - **Eingeschoben in `gate.ts`:** Wenn `'/settings'` aufgerufen wird ohne dass `wr_charge` commissioned ist, bleibt der User auf der Seite (AC 19 Hinweis-Card). **Kein** Redirect-Loop mit `/running`.

25. **Tests Backend (Pytest):** Neue Test-Datei + Erweiterungen:
    - `backend/tests/unit/test_battery_config_route.py` (neu):
      - `test_patch_battery_config_persists_and_reloads` — Patch mit validem Body → DB hat neue Keys + `controller.reload_devices_from_db` wurde aufgerufen.
      - `test_patch_validates_min_max_gap` (AC 3) — `min_soc=80, max_soc=85` → 422 mit Detail-Text.
      - `test_patch_low_min_soc_requires_acknowledgment` (AC 4) — `min_soc=7` ohne `acknowledged_low_min_soc` → 422.
      - `test_patch_low_min_soc_accepted_with_acknowledgment` (AC 4) — `min_soc=7` mit `acknowledged_low_min_soc=True` → 200.
      - `test_patch_min_soc_below_5_always_rejected` (AC 4 Hard-Floor) — `min_soc=4` mit Acknowledgment → 422.
      - `test_patch_empty_night_window_rejected` (AC 6) — `night_start=night_end=20:00` → 422.
      - `test_patch_no_wr_charge_returns_404` (AC 7 Drossel-Only) — Setup ohne `wr_charge` → 404.
      - `test_patch_preserves_other_config_keys` (AC 7 Merge-Semantik) — pre-existing `allow_surplus_export=True` bleibt nach PATCH erhalten.
    - `backend/tests/unit/test_controller_night_discharge.py` (neu):
      - `test_speicher_discharge_blocked_outside_night_window` (AC 9) — `local_now=12:00`, Bezug, SoC 50 → `[]`.
      - `test_speicher_discharge_allowed_inside_night_window` (AC 9 positiv) — `local_now=22:00`, Bezug, SoC 50 → Decisions returned.
      - `test_speicher_discharge_window_wraparound_around_midnight` (AC 11) — `[20:00,06:00]`, `local_now=01:00` → Inside; `local_now=10:00` → Outside.
      - `test_speicher_discharge_window_wraparound_at_boundaries` (AC 11) — `local_now == night_start` → Inside; `local_now == night_end` → Outside.
      - `test_speicher_discharge_window_disabled_bypasses_gate` (AC 12) — `enabled=False`, `local_now=12:00`, Bezug → Decisions returned.
      - `test_speicher_charge_unaffected_by_night_window` (AC 10) — `local_now=12:00` (outside), Einspeisung → Charge-Decisions returned.
      - `test_speicher_night_gate_logs_once_on_entry` (AC 9 Flag-Pattern) — Sequenz Outside→Outside→Outside, Mock-Logger.info → genau 1 Aufruf für `speicher_discharge_blocked_outside_night_window`.
      - `test_speicher_night_gate_resets_when_window_re_entered` (AC 9 Flag-Reset).
      - `test_read_night_discharge_window_defaults_for_missing_keys` (AC 13) — Empty `config_json` → `(True, '20:00', '06:00')`.
      - `test_read_night_discharge_window_handles_malformed_json` (AC 13) — Invalid JSON → Defaults + warning-log.
      - `test_is_in_night_window_pure_function_table` (AC 15) — Parametrized Tests-Tabelle für 8–10 Boundary-/Wraparound-Fälle.
    - `backend/tests/unit/test_controller_reload.py` (neu):
      - `test_reload_devices_picks_up_new_config_json` (AC 8) — DB-Update auf `wr_charge.config_json`, Reload, dann `_read_soc_bounds(controller._battery_pool.members[0].charge_device)` → neue Werte.
      - `test_reload_does_not_clear_speicher_buffers` (AC 17 Schritt 6) — `_speicher_buffers` vor und nach Reload identisch.
      - `test_reload_does_not_change_current_mode` (AC 17 Schritt 7) — `current_mode`, `_mode_baseline`, `_mode_switched_at`, `_forced_mode` unverändert.
      - `test_reload_with_pool_now_empty_falls_back_to_drossel_only` (Edge — User hat alle Akku-Devices aus DB gelöscht, theoretisch unmöglich via PATCH, aber defensiv) — Pool wird `None`, Speicher-Policy returned `[]`.
      - `test_reload_logs_info_record` (AC 17 Schritt 5).
    - **Erweiterung** `backend/tests/unit/test_controller_speicher_policy.py` (existiert in 3.4): zwei zusätzliche Tests, die explizit verifizieren, dass die Default-Werte für das Nacht-Fenster den Bestandstest-Lauf nicht brechen (Backwards-Compat).
    - Coverage-Ziel: ≥ 90 % Line-Coverage auf allen Änderungen in `controller.py` (Helper + Reload + Policy-Branch) und in `api/routes/devices.py` (PATCH-Route).
    - Alle vier Hard-CI-Gates grün: `ruff check`, `mypy --strict`, `pytest`, SQL-Migrations-Ordering (unverändert — **keine neue Migration in 3.6**).

26. **Tests Frontend (Vitest + @testing-library/svelte):** Neue Test-Datei:
    - `frontend/src/routes/Settings.test.ts`:
      - `test_renders_skeleton_then_form` — Skeleton ≥ 400 ms, dann Form.
      - `test_renders_no_battery_hint_for_drossel_only_setup` (AC 19).
      - `test_min_soc_above_max_minus_10_disables_save` (AC 3).
      - `test_low_min_soc_shows_plausibility_warning_and_blocks_save` (AC 4).
      - `test_low_min_soc_accept_then_save_calls_patch_with_ack_flag` (AC 4).
      - `test_low_min_soc_cancel_resets_to_safe_value` (AC 4).
      - `test_night_window_inputs_hidden_when_toggle_off` (AC 5).
      - `test_save_calls_patch_battery_config_with_correct_body` (AC 7, 23).
      - `test_patch_error_renders_inline_error_line` (UX-DR30).
    - `frontend/src/lib/gate.test.ts` (existiert): Neue Test-Cases für `'/settings'`-Route:
      - `test_settings_route_allowed_for_commissioned_user`.
      - `test_settings_route_redirects_to_disclaimer_when_pre_disclaimer_not_accepted`.
      - `test_settings_route_stay_when_no_devices_yet_but_pre_accepted`.
    - **Coverage:** Bestehende Vitest-Schwelle (siehe 5.1a/4.0a Setup) gilt auch hier.
    - ESLint, svelte-check, Prettier — alle grün.

27. **Pipeline-Reference-Flow (3.6 Add-on auf 3.4/3.5):**
    ```
    User saves Settings →
      PATCH /api/v1/devices/battery-config (Pydantic validate)        [3.6 NEW]
        ↓
      get_by_id(wr_charge_id) → {config_json: existing}                [persistence]
        ↓
      merge new_keys into existing config_json (json.dumps roundtrip)  [3.6 NEW]
        ↓
      update_device_config_json(conn, wr_charge_id, merged)            [3.6 NEW repo helper]
        ↓
      controller.reload_devices_from_db()                               [3.6 NEW method]
        ↓ (atomic field-replace)
      response 200 {min_soc, max_soc, ...}                              [3.6 NEW]

    Next sensor event (grid_meter) →
      controller.on_sensor_update(...)                                  [unchanged from 3.5]
        ↓
      _evaluate_mode_switch(...)                                        [unchanged from 3.5]
        ↓
      _dispatch_by_mode(Mode.SPEICHER, device, sensor_value)            [unchanged from 3.4]
        ↓
      _policy_speicher(...)                                             [3.6 EXTENDED]
        ├─ _read_soc_bounds(charge_device)                              [unchanged from 3.4]
        ├─ smoothing buffer + smoothed                                  [unchanged from 3.4]
        ├─ Min-SoC / Max-SoC cap branches                               [unchanged from 3.4]
        ├─ if smoothed > 0 (discharge intent):                          [3.6 NEW gate]
        │    enabled, start, end = _read_night_discharge_window(...)
        │    if enabled and not _is_in_night_window(local_now, start, end):
        │      log once via _speicher_night_gate_active flag
        │      return []
        ├─ ... rest of policy unchanged ...
    ```

28. **Scope-Eingrenzung Diff:** Erwarteter Diff-Umfang:
    - 1 MOD Backend: `backend/src/solalex/controller.py` (+ ~80 LOC: 2 Helper, 1 Field, 1 Policy-Branch, 1 reload-Method, 1 Constructor-Param).
    - 1 MOD Backend: `backend/src/solalex/api/schemas/devices.py` (+ ~40 LOC: `BatteryConfigPatchRequest`, `BatteryConfigResponse`, gemeinsame Validator-Helper).
    - 1 MOD Backend: `backend/src/solalex/api/routes/devices.py` (+ ~50 LOC: PATCH-Route).
    - 1 MOD Backend: `backend/src/solalex/persistence/repositories/devices.py` (+ ~15 LOC: `update_device_config_json`).
    - 1 MOD Backend: `backend/src/solalex/main.py` (+ ~3 LOC: `local_now_fn` + `db_path` an Controller falls neu nötig — siehe Task 6).
    - 3 NEU Backend Tests: `test_battery_config_route.py`, `test_controller_night_discharge.py`, `test_controller_reload.py`.
    - 1 NEU Frontend: `frontend/src/routes/Settings.svelte`.
    - 1 NEU Frontend Test: `frontend/src/routes/Settings.test.ts`.
    - 1 MOD Frontend: `frontend/src/App.svelte` (Route + Render-Branch).
    - 1 MOD Frontend: `frontend/src/lib/gate.ts` (Routing-Whitelist).
    - 1 MOD Frontend Test: `frontend/src/lib/gate.test.ts`.
    - 1 MOD Frontend: `frontend/src/lib/api/client.ts` (`patchBatteryConfig`).
    - 1 MOD Frontend: `frontend/src/lib/api/types.ts` (`BatteryConfigPatchRequest`, `BatteryConfigResponse`).
    - **Keine SQL-Migration**, **keine neue Dependency**, **keine** Änderung an `Mode`-Enum, `_evaluate_mode_switch`, `_record_mode_switch_cycle`, `_policy_drossel`, `_policy_multi`, `set_forced_mode`, `select_initial_mode`, `BatteryPool` (außer Reuse `from_devices`).

## Tasks / Subtasks

- [x] **Task 1: Pydantic-Schema `BatteryConfigPatchRequest` + gemeinsame Validator-Helper** (AC: 3, 4, 5, 6, 20)
  - [x] Neue Datei-Sektion in `api/schemas/devices.py` (oder neue `api/schemas/battery_config.py` falls Schema-Datei sonst zu groß wird — Empfehlung: in `devices.py` belassen, weil eng verwandt mit `HardwareConfigRequest`).
  - [x] Extrahiere gemeinsame Validator-Logik in zwei freie Funktionen (Modul-Top-Level in `devices.py`):
    - `def _validate_soc_gap(min_soc: int, max_soc: int) -> None` — raised `ValueError` bei `max_soc <= min_soc + 10` (Pattern aus `validate_soc_range`).
    - `def _validate_night_window(enabled: bool, start: str, end: str) -> None` — raised `ValueError` bei `enabled and start == end`.
  - [x] `HardwareConfigRequest.validate_soc_range` so refactorn, dass es die zwei freien Funktionen aufruft (DRY — Story 2.1 keeps work). **Behavior unchanged** — `test_devices_routes.py`-Tests müssen weiterhin grün sein.
  - [x] Neue Klasse `BatteryConfigPatchRequest`:
    ```python
    class BatteryConfigPatchRequest(BaseModel):
        min_soc: int = Field(..., ge=5, le=40)
        max_soc: int = Field(..., ge=51, le=100)
        night_discharge_enabled: bool
        night_start: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
        night_end: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
        acknowledged_low_min_soc: bool = False

        @model_validator(mode="after")
        def validate(self) -> "BatteryConfigPatchRequest":
            _validate_soc_gap(self.min_soc, self.max_soc)
            _validate_night_window(
                self.night_discharge_enabled, self.night_start, self.night_end
            )
            if self.min_soc < 10 and not self.acknowledged_low_min_soc:
                raise ValueError(
                    "Min-SoC unter Herstellerspezifikation — "
                    "Bestätigung erforderlich (acknowledged_low_min_soc=true)"
                )
            return self
    ```
  - [x] Neue Response-Klasse `BatteryConfigResponse(BaseModel)` mit den 5 nicht-`acknowledged_low_min_soc`-Feldern.
  - [x] **STOP:** **Kein** `min_limit_w` / `max_limit_w` ins PATCH-Schema aufnehmen — das sind Hardware-Limits und liegen in `wr_limit.config_json`, nicht in `wr_charge.config_json`. Story 3.6 covered nur Akku-Config.

- [x] **Task 2: Repository-Helper `update_device_config_json`** (AC: 21)
  - [x] In `persistence/repositories/devices.py` neue Funktion ergänzen:
    ```python
    async def update_device_config_json(
        conn: aiosqlite.Connection,
        device_id: int,
        new_config_json: str,
        *,
        commit: bool = True,
    ) -> int:
        async with conn.execute(
            "UPDATE devices SET config_json = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
            "WHERE id = ?",
            (new_config_json, device_id),
        ) as cur:
            rowcount = cur.rowcount or 0
        if commit:
            await conn.commit()
        return int(rowcount)
    ```
  - [x] Returntyp ist `int` (rowcount), damit der Caller `404` liefern kann bei `0`.
  - [x] **STOP:** Kein UPSERT, kein Trigger-Mechanismus. Pure UPDATE, atomar via aiosqlite-Transaction.
  - [x] **STOP:** Keine `replace_all`-Wiederverwendung — wir wollen genau **eine** Spalte ändern, nicht das ganze Set rebuilden (würde `commissioned_at` invalidieren).

- [x] **Task 3: Controller — `reload_devices_from_db` + Konstruktor-Param** (AC: 8, 17)
  - [x] In `controller.py::Controller.__init__` neuen Constructor-Param ergänzen:
    ```python
    local_now_fn: Callable[[], datetime] = datetime.now,
    ```
    Speichern als `self._local_now_fn`. **Hinweis:** Default ist `datetime.now` (ohne tz-Argument) — bewusst lokale Zeit, getrennt vom UTC-`now_fn`.
  - [x] Neue async-Methode am `Controller`:
    ```python
    async def reload_devices_from_db(self) -> None:
        async with self._db_conn_factory() as conn:
            devices = await list_devices(conn)
        devices_by_role: dict[str, DeviceRecord] = {}
        for device in devices:
            if device.commissioned_at is not None:
                devices_by_role[device.role] = device
        battery_pool = BatteryPool.from_devices(devices, self._adapter_registry)
        self._devices_by_role = devices_by_role
        self._battery_pool = battery_pool
        self._wr_limit_device = devices_by_role.get("wr_limit")
        _logger.info(
            "controller_reload_devices",
            extra={
                "pool_member_count": (
                    len(battery_pool.members) if battery_pool else 0
                ),
                "wr_charge_present": "wr_charge" in devices_by_role,
                "wr_limit_present": "wr_limit" in devices_by_role,
            },
        )
    ```
  - [x] Import `from solalex.battery_pool import BatteryPool` falls noch nicht vorhanden — der TYPE_CHECKING-Guard für `BatteryPool` (Zeile 48–51) muss ggf. zu Runtime-Import upgraded werden, **wenn** sonst der `from_devices`-Call nicht möglich ist. **Empfehlung:** Lazy-Import innerhalb der Methode (`from solalex.battery_pool import BatteryPool` lokaler Import), um den bestehenden Cycle-Guard nicht zu verletzen.
  - [x] **STOP:** **Keine** Resets von `_speicher_buffers`, `_drossel_buffers`, `_speicher_last_setpoint_w`, `_speicher_pending_setpoints`, Cap-Flags, `_mode_*`-Felder. Buffer-State ist Sensor-gebunden, nicht Device-Identität-gebunden.
  - [x] **STOP:** Reload schreibt **keine** `control_cycles`-Audit-Row. Ist ein Config-Reload, kein Mode-/Policy-Switch.
  - [x] **STOP:** Keine HA-WS-Re-Subscriptions. Entity-IDs sind locked post-Commissioning.

- [x] **Task 4: PATCH-Route `/api/v1/devices/battery-config`** (AC: 7, 20)
  - [x] In `api/routes/devices.py` nach der `save_devices`-Route eine neue `@router.patch(...)` ergänzen:
    ```python
    @router.patch("/battery-config", response_model=BatteryConfigResponse)
    async def patch_battery_config(
        request: Request,
        body: BatteryConfigPatchRequest,
    ) -> BatteryConfigResponse:
        db_path = get_settings().db_path
        async with connection_context(db_path) as conn:
            devices = await list_devices(conn)
        wr_charge = next(
            (d for d in devices if d.role == "wr_charge" and d.commissioned_at is not None),
            None,
        )
        if wr_charge is None or wr_charge.id is None:
            raise ProblemHTTPException(
                status_code=404,
                detail="Kein wr_charge-Device commissioned — Akku-Setup nicht vorhanden",
                title="Kein Akku-Setup",
                type_="urn:solalex:no-battery",
            )
        try:
            existing_config: dict[str, Any] = json.loads(wr_charge.config_json or "{}")
            if not isinstance(existing_config, dict):
                existing_config = {}
        except json.JSONDecodeError:
            existing_config = {}
        existing_config.update(
            {
                "min_soc": body.min_soc,
                "max_soc": body.max_soc,
                "night_discharge_enabled": body.night_discharge_enabled,
                "night_start": body.night_start,
                "night_end": body.night_end,
            }
        )
        async with connection_context(db_path) as conn:
            rows = await update_device_config_json(
                conn, wr_charge.id, json.dumps(existing_config)
            )
        if rows == 0:
            raise ProblemHTTPException(
                status_code=404,
                detail="wr_charge-Device verschwand zwischen GET und UPDATE",
                title="Race Condition",
                type_="urn:solalex:race",
            )
        controller = request.app.state.controller
        await controller.reload_devices_from_db()
        _logger.info(
            "battery_config_patched",
            extra={
                "device_id": wr_charge.id,
                "min_soc": body.min_soc,
                "max_soc": body.max_soc,
                "night_discharge_enabled": body.night_discharge_enabled,
            },
        )
        return BatteryConfigResponse(
            min_soc=body.min_soc,
            max_soc=body.max_soc,
            night_discharge_enabled=body.night_discharge_enabled,
            night_start=body.night_start,
            night_end=body.night_end,
        )
    ```
  - [x] `ProblemHTTPException`-Import (oder existing exception-Pattern aus dem Repo, prüfen via `grep -rn "ProblemHTTPException\|HTTPException" backend/src/solalex/api/`). Falls das Repo eine eigene `problem_details.py` hat — diese verwenden. Sonst FastAPI `HTTPException(status_code=404, detail="...")` und Middleware konvertiert zu RFC 7807.
  - [x] **STOP:** **Keine** `replace_all`-Aufrufe — würde `commissioned_at` zurücksetzen.
  - [x] **STOP:** Keine `forced_mode`-Logik im PATCH — Mode-Override hat seinen eigenen Endpoint (`PUT /api/v1/control/mode` aus 3.5).
  - [x] **STOP:** Keine separate Audit-Tabelle für Config-Changes (out-of-scope; `_logger.info('battery_config_patched', ...)` reicht).

- [x] **Task 5: Controller — `_read_night_discharge_window` + `_is_in_night_window` Helpers** (AC: 13, 14, 15)
  - [x] In `controller.py` (am Modul-Top-Level, **nicht** als Methode am Controller) zwei neue Helper-Functions ergänzen, **direkt unterhalb** von `_read_soc_bounds` (Zeile ~1249):
    ```python
    def _read_night_discharge_window(
        charge_device: DeviceRecord,
    ) -> tuple[bool, str, str]:
        """Return ``(enabled, start_hhmm, end_hhmm)`` from charge_device.config_json.

        Wizard 2.1 + Settings 3.6 persist these keys. Defaults match the
        Wizard defaults (enabled=True, 20:00–06:00). Malformed payloads
        collapse to defaults rather than crashing the dispatch task.
        """
        try:
            cfg = charge_device.config()
        except Exception:
            _logger.exception(
                "speicher_night_window_parse_failed",
                extra={"entity_id": charge_device.entity_id},
            )
            return (True, "20:00", "06:00")
        if not isinstance(cfg, dict):
            return (True, "20:00", "06:00")
        raw_enabled = cfg.get("night_discharge_enabled", True)
        enabled = bool(raw_enabled) if raw_enabled is not None else True
        raw_start = cfg.get("night_start", "20:00")
        raw_end = cfg.get("night_end", "06:00")
        start = raw_start if isinstance(raw_start, str) and _is_valid_hhmm(raw_start) else "20:00"
        end = raw_end if isinstance(raw_end, str) and _is_valid_hhmm(raw_end) else "06:00"
        return (enabled, start, end)


    _HHMM_PATTERN: Final = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


    def _is_valid_hhmm(s: str) -> bool:
        return bool(_HHMM_PATTERN.match(s))


    def _is_in_night_window(
        local_time_obj: time, start_hhmm: str, end_hhmm: str
    ) -> bool:
        """Return True if local_time_obj falls within the [start, end) window.

        Wraparound semantics: if start > end (e.g. 20:00–06:00), the
        window spans midnight — return True for now >= start OR now < end.
        Boundaries: now == start → in; now == end → out.
        """
        start_h, start_m = (int(x) for x in start_hhmm.split(":"))
        end_h, end_m = (int(x) for x in end_hhmm.split(":"))
        start_t = time(hour=start_h, minute=start_m)
        end_t = time(hour=end_h, minute=end_m)
        if start_t <= end_t:
            return start_t <= local_time_obj < end_t
        return local_time_obj >= start_t or local_time_obj < end_t
    ```
  - [x] Imports am Top von `controller.py` ergänzen: `from datetime import time` (oder zur bestehenden `from datetime import UTC, datetime, timedelta`-Zeile hinzufügen) und `import re` (existiert ggf. nicht — prüfen).
  - [x] **STOP:** Helpers sind **Pure Functions**. Kein I/O, keine Logger-Calls außer dem definierten `_logger.exception` im JSON-Parse-Fehlerpfad.
  - [x] **STOP:** Kein ZoneInfo-Lookup, keine `pytz`-Dep. Reine `datetime.time`-Vergleiche.

- [x] **Task 6: Controller — Nacht-Gate in `_policy_speicher`** (AC: 9, 10, 12)
  - [x] In `_policy_speicher` (Zeile ~862 in `controller.py`), **nach** dem Min-SoC-Cap-Branch (Zeile ~940 `if smoothed > 0 and aggregated <= min_soc:`) und **vor** dem Sign-Flip-Block (Zeile ~952), einen neuen Gate-Branch ergänzen:
    ```python
    # Story 3.6 — Nacht-Entlade-Zeitfenster gate.
    # Only the discharge intent (smoothed > 0, would discharge) is gated;
    # charge (smoothed < 0, surplus PV) flows freely 24/7. Outside-window
    # discharge falls through to []; ``_speicher_night_gate_active`` flag
    # keeps the once-per-band log line discipline (Story 3.4 Cap-Flag pattern).
    if smoothed > 0:
        enabled, start_hhmm, end_hhmm = _read_night_discharge_window(first_charge)
        if enabled:
            local_now = self._local_now_fn()
            if not _is_in_night_window(local_now.time(), start_hhmm, end_hhmm):
                if not self._speicher_night_gate_active:
                    _logger.info(
                        "speicher_discharge_blocked_outside_night_window",
                        extra={
                            "aggregated_pct": aggregated,
                            "night_start": start_hhmm,
                            "night_end": end_hhmm,
                            "local_time": local_now.strftime("%H:%M"),
                        },
                    )
                    self._speicher_night_gate_active = True
                return []
            else:
                self._speicher_night_gate_active = False
        else:
            self._speicher_night_gate_active = False
    else:
        self._speicher_night_gate_active = False
    ```
  - [x] In `Controller.__init__` neues Field initialisieren:
    ```python
    # Story 3.6 — once-per-band log discipline for the night-discharge gate.
    self._speicher_night_gate_active: bool = False
    ```
  - [x] In `_record_mode_switch_cycle` (Zeile ~593) das Reset um den neuen Flag ergänzen:
    ```python
    self._speicher_max_soc_capped = False
    self._speicher_min_soc_capped = False
    self._speicher_night_gate_active = False  # 3.6 — fresh log on next entry
    ```
  - [x] **STOP:** Gate **ausschließlich** im Bezug-Branch (`smoothed > 0`). Charge (`smoothed < 0`) wird **niemals** gegated.
  - [x] **STOP:** Gate gilt **nicht** für Surplus-Export (`Mode.EXPORT` aus 3.8). EXPORT setzt das WR-Limit, schreibt **keinen** Akku-Discharge — Nacht-Fenster ist orthogonal.
  - [x] **STOP:** Gate beeinflusst **nicht** den `_speicher_min_soc_capped`-Flag. Beide Flags koexistieren unabhängig.
  - [x] **STOP:** Bei `enabled=False` resettet der Flag immer auf `False` — der einmal-pro-Eintritt-Log-Trick gilt nicht für ein deaktiviertes Feature.

- [x] **Task 7: `main.py` — `local_now_fn` durchreichen + Reload-Hook** (AC: 8, 17)
  - [x] In `main.py::lifespan` Controller-Konstruktor (Zeile ~239) keinen neuen Param explizit übergeben (`datetime.now` ist Default). Der Default deckt Production. Tests können den Default in `Controller(...)` überschreiben.
  - [x] **Wenn** der Controller-`db_conn_factory`-Param ausreichend ist für `reload_devices_from_db` (er ist) — **keine** `db_path`-Doppelung nötig.
  - [x] **Stop:** Kein neuer Lifespan-Aufruf von `reload_devices_from_db` beim Startup. Der initial-Load passiert weiterhin im klassischen Lifespan-Block — Reload ist nur post-PATCH-Trigger.

- [x] **Task 8: Frontend — Types + Client** (AC: 23)
  - [x] In `frontend/src/lib/api/types.ts`:
    ```ts
    export interface BatteryConfigPatchRequest {
      min_soc: number;
      max_soc: number;
      night_discharge_enabled: boolean;
      night_start: string;
      night_end: string;
      acknowledged_low_min_soc?: boolean;
    }

    export interface BatteryConfigResponse {
      min_soc: number;
      max_soc: number;
      night_discharge_enabled: boolean;
      night_start: string;
      night_end: string;
    }
    ```
  - [x] In `frontend/src/lib/api/client.ts`:
    ```ts
    export async function patchBatteryConfig(
      body: BatteryConfigPatchRequest,
    ): Promise<BatteryConfigResponse> {
      return request<BatteryConfigResponse>('/api/v1/devices/battery-config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    }
    ```
  - [x] **Imports** der neuen Types aus `./types.js` ergänzen (Top von `client.ts`).

- [x] **Task 9: Frontend — `Settings.svelte`** (AC: 1, 2, 3, 4, 5, 19, 22)
  - [x] Neue Datei `frontend/src/routes/Settings.svelte` mit Svelte-5-Runes:
    - `<script lang="ts">` mit `$state`-Variablen für die 5 Form-Felder, Save-Status, Plausibilitäts-Confirm-Status, Load-Skeleton-Status.
    - `onMount` lädt `client.getDevices()`, sucht `wr_charge`-Device commissioned, parst dessen `config_json`, befüllt die `$state`s. Falls kein `wr_charge` → renderToggle für AC 19.
    - `$derived` für `canSave` (Validation gates: `max_soc >= min_soc + 11`, `!low_min_pending_confirm`, alle Felder gesetzt).
    - Inline-Plausibilitäts-Confirm-Block mit „Abbrechen" / „Trotzdem speichern" — beim „Trotzdem speichern" wird das `acknowledged_low_min_soc=true`-Flag im PATCH-Body mitgesendet; sonst `false`/weggelassen.
    - `handleSave` → `client.patchBatteryConfig(body)` → bei `200` re-load der Werte + grüner Inline-Confirmation („Einstellungen gespeichert"); bei `422`/`404` → Inline-Error mit `err.detail` (RFC-7807-Mapping via `isApiError`).
    - **Kein** Redirect nach Save (anders als 2.1's `#/functional-test`-Redirect — die Settings-Page bleibt offen).
    - Strings deutsch hardcoded (CLAUDE.md). Glossar: „Akku" (nicht „Batterie"), „Nacht-Entladung" (nicht „Nacht-Discharge").
    - Tailwind-Klassen + CSS Custom Properties analog zu Config.svelte (gleicher visueller Sprache).
  - [x] **STOP:** **Kein** Modal, **kein** Toast, **kein** Loading-Spinner (UX-DR30). Skeleton-Pulse ≥ 400 ms ist erlaubt.
  - [x] **STOP:** **Kein** „Speichern und in Funktionstest gehen"-Pattern — Settings ist eigenständig.
  - [x] **STOP:** **Kein** Mode-Override-Card kopieren (lebt in Config.svelte aus 3.5; das ist ok für v1, Migration ist out-of-scope).
  - [x] **STOP:** **Kein** Surplus-Export-Toggle (Story 3.8 ist parallel-ready-for-dev und hat seinen eigenen UI-Touch in `Config.svelte`; Settings.svelte zieht den Toggle in v1.5 nach, falls er post-Commissioning editierbar werden soll).

- [x] **Task 10: Frontend — Routing in `App.svelte` + `lib/gate.ts`** (AC: 1, 24)
  - [x] In `App.svelte`:
    ```ts
    const VALID_ROUTES = new Set([
      '/', '/config', '/functional-test', '/running', '/disclaimer',
      '/activate', '/diagnostics', '/settings',  // 3.6
    ]);
    ```
    + Render-Branch:
    ```svelte
    {:else if currentRoute === '/settings'}
      <Settings />
    ```
    + Import `import Settings from './routes/Settings.svelte';`
  - [x] In `lib/gate.ts`:
    - `WIZARD_ROUTES` **NICHT** ergänzen (settings ist post-Commissioning).
    - In `evaluateGate`: Vor dem `allCommissioned`-Check ein expliziter Branch `if (currentRoute === '/settings')`:
      ```ts
      if (currentRoute === '/settings') {
        if (!preAccepted) return { kind: 'redirect', hash: '#/disclaimer' };
        return { kind: 'stay' };
      }
      ```
      **Begründung:** `/settings` ist eine eigenständige Surface — weder Wizard noch Diagnose. Der Branch räumt sie aus dem `WIZARD_ROUTES`-Pfad, der für commissioned User ein `#/running`-Redirect triggern würde.
    - Test-Cases ergänzen (siehe AC 26).
  - [x] **STOP:** Kein Footer-/Sidebar-Link in `Running.svelte` oder `App.svelte` zur Settings-Page. Versteckt = nur via direkter URL.

- [x] **Task 11: Backend Tests** (AC: 25)
  - [x] `backend/tests/unit/test_battery_config_route.py` mit den 8 Test-Cases. Verwendung des bestehenden FastAPI-Test-Client-Patterns (`httpx.AsyncClient` + Lifespan-Override, analog `tests/unit/test_devices_routes.py`).
  - [x] `backend/tests/unit/test_controller_night_discharge.py` mit den 11 Test-Cases. Verwendung der Helpers aus `_controller_helpers.py` (FakeHaClient, In-Memory-DB, `build_marstek_pool`). Pure-Function-Tests für `_is_in_night_window` und `_read_night_discharge_window` brauchen keinen Controller-Setup — direkt aus `solalex.controller` importieren.
  - [x] `backend/tests/unit/test_controller_reload.py` mit den 5 Test-Cases. Reload-Triggering via direkter `await controller.reload_devices_from_db()`-Aufruf.
  - [x] **Drift-Check** — beim ersten Pytest-Run sicherstellen, dass die bestehenden 339 Tests aus 3.5 weiterhin grün sind (Backwards-Compat).
  - [x] `cd backend && uv run ruff check .` → grün.
  - [x] `cd backend && uv run mypy --strict src/ tests/` → grün.

- [x] **Task 12: Frontend Tests** (AC: 26)
  - [x] `frontend/src/routes/Settings.test.ts` mit den 9 Test-Cases. Pattern aus `Config.test.ts` und `DisclaimerActivation.test.ts` übernehmen — `render(Settings)` + `findByRole`/`getByLabelText` + `userEvent` für Save-Click + `vi.mock('../lib/api/client.js', ...)`.
  - [x] `frontend/src/lib/gate.test.ts` um 3 neue Cases erweitern.
  - [x] `cd frontend && npm run lint` → grün.
  - [x] `cd frontend && npm run check` → grün.
  - [x] `cd frontend && npm run test` → grün (alle bisherigen + neue Tests).

- [x] **Task 13: Drift-Checks & Verification** (AC: 28)
  - [x] `grep -rE "battery_config" backend/src/solalex/` → Treffer in `api/routes/devices.py` (Route), `api/schemas/devices.py` (Schema). Keine Treffer in `controller.py` (außer `_read_night_discharge_window`-Helper-Name).
  - [x] `grep -rE "reload_devices_from_db" backend/` → Treffer in `controller.py` (Definition) + `api/routes/devices.py` (Aufruf) + Tests.
  - [x] `grep -rE "_is_in_night_window\|_read_night_discharge_window" backend/src/solalex/` → Treffer in `controller.py` und Tests.
  - [x] `grep -rE "ZoneInfo|pytz|tzlocal" backend/src/solalex/` → 0 Treffer (keine TZ-Dep).
  - [x] `grep -rE "structlog|APScheduler|cryptography|numpy|pandas|SQLAlchemy" backend/src/solalex/` → 0 Treffer (Story 3.5-Pattern).
  - [x] `grep -rE "004_.*\.sql" backend/src/solalex/persistence/sql/` → ggf. Treffer aus Story 3.8 (parallel-Ready-for-Dev), aber **nicht** aus 3.6. SQL-Ordering: 001 + 002 + 003 (+ ggf. 004 aus 3.8) lückenlos.
  - [x] **Manual-Smoke** (sofern lokal verfügbar): commissioned Setup, `curl -X PATCH http://localhost:8099/api/v1/devices/battery-config -H 'Content-Type: application/json' -d '{"min_soc":20,"max_soc":92,"night_discharge_enabled":true,"night_start":"21:00","night_end":"05:00"}'` → 200 + `controller_reload_devices` im Log + nächster Sensor-Event nutzt neue Bounds.

## Dev Notes

### Architektur-Bezugspunkte (Pflichtlektüre)

- [architecture.md — Cut #10 JSON-Template-Verbot Zeile 1088](../planning-artifacts/architecture.md) — Generic-Adapter liest **keine** Templates aus Files; vendor-Spezifika (auch User-Config-Bounds) leben in `device.config_json`-Override-Keys. Story 3.6 nutzt **dieselbe** Override-Mechanik für die Akku-Bounds, die Story 2.1 angelegt hat.
- [architecture.md — `device.config_json`-Override-Schema Zeile 1106–1117](../planning-artifacts/architecture.md) — Schema-Pattern. Story 3.6 erweitert die Liste der editierbaren Keys um `min_soc`, `max_soc`, `night_discharge_enabled`, `night_start`, `night_end` (alle bereits in 2.1 angelegt — nur Edit-Surface fehlt).
- [architecture.md — Amendment 2026-04-25 Surplus-Export Zeile 1129–1199](../planning-artifacts/architecture.md) — Story 3.8 fügt `allow_surplus_export`-Toggle in **dasselbe** `wr_charge.config_json`-Schema. **Wichtig:** PATCH-Route in 3.6 muss **andere** Keys als die 5 explizit gemergt erhalten (AC 7 Merge-Semantik), sonst überschreibt 3.6 den 3.8-Toggle.
- [prd.md — FR20 Zeile 603 + FR22 Zeile 608](../planning-artifacts/prd.md) — Nutzer-Konfiguration für Nacht-Entlade-Zeitfenster + Min/Max-SoC. Beta-Launch-relevante Funktionalitäten.
- [prd.md — Zeile 295 + 317 Akku-Schutz mit Min/Max-SoC](../planning-artifacts/prd.md) — Nutzer-Leitplanken-Argumentation. Plausibilitäts-Schranke (AC 4) folgt direkt aus Zeile 317 „verhindern, dass Nutzer Solalex in schädliche Konfigurationen bringen".
- [ux-design-specification.md — Zeile 256 Björn-Use-Case](../planning-artifacts/ux-design-specification.md) — explizite Erwähnung der Konfiguration „Min-SoC 15 %, Max-SoC 95 %, Nacht-Entladung ab 20:00 Uhr" als Nutzer-Erwartung.
- [ux-design-specification.md — UX-DR30 Zeile ~278](../planning-artifacts/ux-design-specification.md) — Anti-Pattern-Liste: keine Modals, keine Tooltips, keine Toasts. Plausibilitäts-Confirm in 3.6 ist deshalb als **inline** Confirm-Block implementiert, nicht als Modal.
- [CLAUDE.md — 5 harte Regeln](../../CLAUDE.md) — snake_case API-JSON, kein Wrapper, `get_logger(__name__)`. Story 3.6 Schema-Felder sind alle snake_case (`min_soc`, nicht `minSoc`).
- [Story 2.1 — Hardware Config Page](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md) — Schema-Owner für `min_soc`/`max_soc`/`night_discharge_enabled`/`night_start`/`night_end`-Felder. **Pflichtlektüre für gemeinsamen Pydantic-Validator-Refactor (Task 1).**
- [Story 2.3a — Pre-Setup-Disclaimer-Gate](./2-3a-pre-setup-disclaimer-gate.md) — `lib/gate.ts::evaluateGate`-Logik. Pflichtlektüre für AC 24 Routing-Update.
- [Story 3.4 — Speicher-Modus](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md) — `_policy_speicher`-Logik, Cap-Flag-Pattern (`_speicher_max_soc_capped`/`_speicher_min_soc_capped`), `_read_soc_bounds`. **Pflichtlektüre.** Nacht-Gate-Flag (`_speicher_night_gate_active`) folgt exakt dem Pattern.
- [Story 3.5 — Adaptive Mode Switching](./3-5-adaptive-strategie-auswahl-hysterese-basierter-modus-wechsel-inkl-multi-modus.md) — `_record_mode_switch_cycle` resettet die Cap-Flags. Story 3.6 ergänzt den Reset um `_speicher_night_gate_active` (Task 6 letzte Subtask).
- [Story 4.0a — Diagnose-Schnellexport](./4-0a-diagnose-schnellexport-db-dump-logs-zip.md) — Pattern „versteckte Route, nur via direkter URL". Story 3.6 spiegelt das für Settings.
- [Story 5.1a — Live-Betriebs-View](./5-1a-live-betriebs-view-post-commissioning-mini-shell.md) — `Running.svelte`-Mini-Shell, Polling-Pattern. Story 3.6 fügt **keine** Settings-Verlinkung dort ein.

### Technical Requirements (DEV AGENT GUARDRAILS)

**Scope:** Backend (3 Files mod, 1 File mod-extend) + Frontend (1 NEU Settings.svelte + 4 Files mod). **Keine SQL-Migration, keine Adapter-Änderung, keine neue Dependency.**

**Mini-Diff-Prinzip:** Erwarteter Diff-Umfang siehe AC 28.

**Dateien, die berührt werden dürfen:**

- **MOD Backend:**
  - `backend/src/solalex/api/schemas/devices.py` — gemeinsame Validator-Helper extrahieren + neue `BatteryConfigPatchRequest` + `BatteryConfigResponse`. **`HardwareConfigRequest`-Behavior bleibt unverändert.**
  - `backend/src/solalex/api/routes/devices.py` — neue `@router.patch("/battery-config")`-Route.
  - `backend/src/solalex/persistence/repositories/devices.py` — neuer Helper `update_device_config_json`.
  - `backend/src/solalex/controller.py` — `_local_now_fn`-Constructor-Param + `_speicher_night_gate_active`-Field + `_read_night_discharge_window`-Helper + `_is_in_night_window`-Helper + `_is_valid_hhmm`-Helper + Nacht-Gate-Branch in `_policy_speicher` + `reload_devices_from_db`-Methode + Reset-Erweiterung in `_record_mode_switch_cycle`. Imports: `time` aus `datetime`, optional `re` für `_HHMM_PATTERN`.

- **MOD Frontend:**
  - `frontend/src/App.svelte` — `VALID_ROUTES` + Render-Branch + Import.
  - `frontend/src/lib/gate.ts` — Settings-Branch in `evaluateGate`.
  - `frontend/src/lib/api/client.ts` — `patchBatteryConfig`-Funktion.
  - `frontend/src/lib/api/types.ts` — Request/Response-Types.

- **NEU Frontend:**
  - `frontend/src/routes/Settings.svelte` — Settings-Surface.

- **NEU Backend (Tests):**
  - `backend/tests/unit/test_battery_config_route.py`
  - `backend/tests/unit/test_controller_night_discharge.py`
  - `backend/tests/unit/test_controller_reload.py`

- **NEU Frontend (Tests):**
  - `frontend/src/routes/Settings.test.ts`
  - Erweiterung `frontend/src/lib/gate.test.ts`.

- **NICHT anfassen:**
  - `backend/src/solalex/persistence/sql/*.sql` — **keine neue Migration**. Schema unverändert.
  - `backend/src/solalex/persistence/migrate.py` — unverändert.
  - `backend/src/solalex/adapters/*` — keine Adapter-Änderung. `MarstekVenusAdapter.get_speicher_params` bleibt; `_read_soc_bounds`/`_read_night_discharge_window` lesen aus `device.config_json` direkt.
  - `backend/src/solalex/battery_pool.py` — Pool ist 3.3 final; 3.6 nutzt nur `from_devices`.
  - `backend/src/solalex/executor/*` — Veto-Kaskade, Rate-Limiter, Readback unverändert.
  - `backend/src/solalex/state_cache.py` — keine Änderung am Cache-Pattern.
  - `backend/src/solalex/api/routes/control.py` — Mode-Override aus 3.5 unverändert.
  - `backend/src/solalex/main.py` — Lifespan unverändert (Reload ist post-PATCH-getriggert, nicht Lifespan-getriggert).
  - `frontend/src/routes/Config.svelte` — Setup-Wizard bleibt unverändert; das Mode-Override-Card aus 3.5 bleibt dort. Settings.svelte ist eine eigenständige Datei.
  - `frontend/src/routes/Running.svelte` — Mini-Shell aus 5.1a unverändert; **kein** Settings-Link.
  - `frontend/src/routes/Diagnostics.svelte` — unverändert.
  - `pyproject.toml`, `frontend/package.json` — keine neue Dep.

**STOP-Bedingungen (Verletzung = Pull-Request-Block):**

- Wenn du eine neue SQL-Migration `004_*.sql` oder `005_*.sql` für die Akku-Config anlegst — **STOP**. Schema ist unverändert; Werte leben in `wr_charge.config_json` als JSON-String (Architecture Cut #10).
- Wenn du das `wr_charge.config_json`-Schema in eine Pydantic-Klasse zwingen willst, die persistent in der DB liegt — **STOP**. Architecture-Pattern ist „raw JSON-String mit defensiver Parse-Logik" (`_read_soc_bounds`-Vorlage).
- Wenn du das Settings-UI in `Config.svelte` integrierst (Mode-Switch innerhalb derselben Komponente) — **STOP**. Config.svelte ist Setup-Wizard; Settings.svelte ist post-Commissioning-Surface. Vermischen wirft Routing- und Test-Komplexität in eine Datei, die schon 720 Zeilen hat.
- Wenn du `replace_all` für den PATCH-Pfad nutzt — **STOP**. `replace_all` re-INSERTet alle Devices und kann `commissioned_at` invalidieren. PATCH ist Single-Row-Update via `update_device_config_json`.
- Wenn du den Nacht-Gate auf Charge-Branch (`smoothed < 0`) anwendest — **STOP**. AC 10. Charge ist 24/7 erlaubt.
- Wenn du den Nacht-Gate auf `_policy_drossel` anwendest — **STOP**. Drossel ist eine WR-Limit-Regelung ohne Akku-Bezug. Nacht-Fenster ist Akku-Discharge-Schutz.
- Wenn du den Nacht-Gate auf `_policy_export` (Story 3.8) anwendest — **STOP**. Export setzt das WR-Limit auf Hardware-Max bei Pool-Voll. Es gibt keine Akku-Discharge in Export. Nacht-Fenster ist semantisch orthogonal.
- Wenn du `ZoneInfo`/`pytz`/`tzlocal` als Dep einführst — **STOP**. v1 nutzt naive `datetime.now()` für lokale Zeit (Container-TZ).
- Wenn du `_local_now_fn` mit `_now_fn` (UTC) zusammenlegst — **STOP**. Audit-Cycles brauchen UTC, Wand-Uhr-Vergleiche brauchen lokale Zeit. Zwei separate Hooks.
- Wenn du den Plausibilitäts-Confirm als Modal renderst — **STOP**. UX-DR30. Inline-Confirm-Block im Form-Flow.
- Wenn du `acknowledged_low_min_soc` als HTTP-Header statt Body-Field implementierst — **STOP**. Body-Field ist konsistent mit dem Rest der API (CLAUDE.md Regel 4 — direkt am Objekt).
- Wenn du das Mode-Override-Card aus `Config.svelte` nach `Settings.svelte` migrierst — **STOP**. Out-of-scope; v1.5-Refactor.
- Wenn du den Surplus-Export-Toggle (3.8) in Settings.svelte rendern willst — **STOP**. 3.8 ist parallel-ready-for-dev; UI lebt in `Config.svelte` per 3.8-AC.
- Wenn du in der PATCH-Route das gesamte `config_json` ersetzt statt mergen — **STOP**. AC 7 Merge-Semantik. `allow_surplus_export` und andere zukünftige Keys müssen erhalten bleiben.
- Wenn du `Controller.reload_devices_from_db` einen Mode-Switch oder Audit-Cycle schreiben lässt — **STOP**. AC 17 Schritt 7. Reload ist Config-Reload, nicht Mode-Reload.
- Wenn du `Controller.reload_devices_from_db` Speicher-Buffer / Drossel-Buffer / Cap-Flags resettest — **STOP**. AC 17 Schritt 6. Buffer-State überlebt Reload.
- Wenn du `Controller.reload_devices_from_db` als Background-Task startest — **STOP**. Synchron, weil die HTTP-Response auf den abgeschlossenen Reload warten soll (nächster Sensor-Event nutzt neue Werte).
- Wenn du Wraparound-Logik mit `if start <= end` invertierst — **STOP**. AC 11 Reihenfolge: `start <= end` → linearer Bereich; `start > end` → Wraparound. Boundaries: `now == start` → Inside; `now == end` → Outside (Halb-offenes Intervall `[start, end)`).
- Wenn du den Settings-Save-Button als „Speichern und Funktionstest" implementierst — **STOP**. Settings ist eigenständig; kein Funktionstest-Re-Run.
- Wenn du in der `Settings.svelte` einen Toast oder Spinner zeigst — **STOP**. UX-DR30. Inline-Pattern.
- Wenn du `'/settings'` in `WIZARD_ROUTES` von `gate.ts` einfügst — **STOP**. AC 24. Settings ist post-Commissioning-Surface; commissioned User sollen rein dürfen.
- Wenn du die existierende `HardwareConfigRequest`-Validierung breakest (Behavior-Diff in `test_devices_routes.py`) — **STOP**. Refactor in Task 1 muss verhaltens-erhaltend sein.
- Wenn du eine neue Tabelle `battery_config_history` für Audit-Trail anlegst — **STOP**. v1 hat keinen Config-Audit-Trail. `_logger.info('battery_config_patched', ...)` reicht.

### Architecture Compliance (5 harte Regeln aus CLAUDE.md)

1. **snake_case überall:** Alle neuen Symbole (`patch_battery_config`, `update_device_config_json`, `_read_night_discharge_window`, `_is_in_night_window`, `_is_valid_hhmm`, `_speicher_night_gate_active`, `reload_devices_from_db`, `local_now_fn`, `BatteryConfigPatchRequest`, `BatteryConfigResponse`) sind snake_case bzw. PascalCase für Klassen (Sprach-Konvention). API-JSON-Felder sind snake_case (`min_soc`, `night_discharge_enabled`, `acknowledged_low_min_soc`).
2. **Ein Python-Modul pro Adapter:** Nicht direkt anwendbar — 3.6 berührt keinen Adapter. Mono-Modul-Prinzip zieht: Helper-Funktionen leben in `controller.py`, nicht in `controller/night.py`.
3. **Closed-Loop-Readback:** Nicht relevant — Settings-Save löst **keinen** Hardware-Write aus. Der nächste regulär getriggerte Sensor-Event durchläuft die normale Veto-Kaskade unverändert.
4. **JSON-Responses ohne Wrapper:** PATCH-Response ist `{"min_soc": ..., "max_soc": ..., ...}` direkt. Fehler folgen RFC 7807 (bestehende Middleware).
5. **Logging via `get_logger(__name__)`:** Alle neuen Logs nutzen `_logger`. `_logger.info('controller_reload_devices', ...)`, `_logger.info('speicher_discharge_blocked_outside_night_window', ...)`, `_logger.info('battery_config_patched', ...)`. `_logger.exception('speicher_night_window_parse_failed', ...)` für defensive JSON-Parse-Fehler.

### Library & Framework Requirements

- **Keine neuen Dependencies.** Alle Bausteine aus stdlib (`datetime.time`, `re`, `json`).
- **Python 3.13** (`pyproject.toml` unverändert).
- **Pydantic v2** (in 2.1+ etabliert) — `model_validator`, `Field`-Constraints.
- **FastAPI** — `@router.patch(...)`, `Request`-Injection.
- **Svelte 5 Runes** ($state, $derived, onMount, snake_case-Form-Body) — Pattern aus `Config.svelte`.
- **Vitest + @testing-library/svelte + happy-dom** — Pattern aus 2.3a, 3.5 (Config.test.ts), 4.0a (existing Vitest-Stack).
- **Kein structlog, kein APScheduler, kein cryptography, kein numpy/pandas, kein SQLAlchemy.** stdlib `logging` via `get_logger`.
- **Keine i18n-Wrapper** — deutsche Strings hardcoded in Svelte.

### File Structure Requirements

- **Settings.svelte als eigenständige Komponente** unter `frontend/src/routes/`. Nicht mit Config.svelte vermischen.
- **PATCH-Route in der bestehenden `api/routes/devices.py`** — kein neues Routes-File. `devices`-Resource-Coherence.
- **Schemas in `api/schemas/devices.py`** — kein neues Schema-File. `validate_soc_range`-Refactor reduziert Code-Duplication.
- **Controller-Helpers (`_read_night_discharge_window`, `_is_in_night_window`, `_is_valid_hhmm`) als Modul-Top-Level-Funktionen** in `controller.py`, **direkt unterhalb** von `_read_soc_bounds`. Nicht als Methoden am Controller (vermeidet zirkuläre Test-Setup, klare Pure-Function-Semantik).
- **`reload_devices_from_db` als Methode am Controller** (nicht Modul-Top-Level) — sie mutiert Controller-Felder.
- **Test-Files spiegeln Source-Pfade:**
  - `tests/unit/test_battery_config_route.py` — PATCH-Route + Schema-Validierung.
  - `tests/unit/test_controller_night_discharge.py` — Nacht-Gate-Logik in Speicher-Policy.
  - `tests/unit/test_controller_reload.py` — Reload-Methode.

### Testing Requirements

- **Pytest + pytest-asyncio + MyPy strict + Ruff** — alle 4 CI-Gates grün.
- **Vitest + ESLint + svelte-check + Prettier** — Frontend-CI-Gates grün.
- **Coverage ≥ 90 %** auf allen neuen Backend-Lines (Helpers, Reload, Policy-Branch, PATCH-Route).
- **Vitest-Coverage-Schwelle:** wie in 5.1a/4.0a/3.5 etabliert.
- **Deterministische Time-Tests:** `local_now_fn`-Injection bestimmt die lokale Zeit. Wraparound-Tests nutzen `time(hour=…, minute=…)` direkt für die Pure Function.
- **Pure-Function-Tests:** `_is_in_night_window` und `_read_night_discharge_window` brauchen **keinen** Controller-Setup — direkt importieren und Parametrize-Tests.
- **Reload-Tests:** Verifizieren Idempotenz (zweimal Reload nacheinander = identisches Ergebnis), Field-Replace-Atomizität (alle drei Felder gleichzeitig oder gar nicht).
- **PATCH-Tests:** Verwenden `httpx.AsyncClient` mit FastAPI-App-Lifespan-Override (Pattern aus `tests/unit/test_devices_routes.py` und `test_control_routes.py`).
- **Frontend-Tests:** `vi.mock('../lib/api/client.js', ...)` für `getDevices` und `patchBatteryConfig`. `userEvent.type` für Number-Inputs; `userEvent.click` für Save-Button und Confirm-Buttons.

### Previous Story Intelligence

**Aus Story 3.5 (jüngste, höchste Relevanz — Mode-Switch + Reset-Pattern):**

- **`_record_mode_switch_cycle` resettet `_speicher_max_soc_capped` und `_speicher_min_soc_capped` (3.4-Pattern).** Story 3.6 ergänzt den Reset um den neuen `_speicher_night_gate_active`-Flag (Task 6).
- **Constructor-Param-Pattern:** 3.5 hat `forced_mode` und `now_fn` als optionale Constructor-Params eingeführt. 3.6 nutzt das Pattern für `local_now_fn`.
- **Audit-Cycle-Mock-Pattern:** `_record_mode_switch_cycle` hat einen Try/Except gegen DB-Failures (AC 9 in 3.5). 3.6 hat **keine** Audit-Cycle (Reload ist Config-only), aber das Logger-`_logger.exception`-Pattern bei JSON-Parse-Fehlern bleibt.
- **`set_forced_mode` ist async, weil es `_record_mode_switch_cycle` aufruft.** `reload_devices_from_db` ist async, weil es `await list_devices(conn)` aufruft. Beide folgen dem etablierten Sync/Async-Mix.

**Aus Story 3.4 (Speicher-Policy + Cap-Flag-Pattern):**

- **Cap-Flag-Pattern (`_speicher_max_soc_capped`/`_speicher_min_soc_capped`):** Logger-Aufruf nur beim Eintritt in den Cap-State, Reset beim Verlassen — exakt das Verhalten, das 3.6 für `_speicher_night_gate_active` braucht. Implementation 1:1 übernehmen.
- **`_read_soc_bounds(charge_device)`-Pattern:** Defensive JSON-Parse mit Fallback-Defaults, Log bei Malformed. Story 3.6 schreibt `_read_night_discharge_window` als Twin (Task 5).
- **`_policy_speicher`-Sign-Convention:** `smoothed > 0` = Bezug = Discharge-Intent; `smoothed < 0` = Einspeisung = Charge-Intent. Nacht-Gate gilt **nur** für `smoothed > 0` (AC 9, AC 10).
- **`_speicher_buffers`-Sensor-gebunden, nicht Device-gebunden.** Reload muss die Buffer **nicht** anfassen (AC 17 Schritt 6).

**Aus Story 3.3 (Battery Pool):**

- **`BatteryPool.from_devices(devices, ADAPTERS)` ist idempotent + side-effect-frei** — sicher in `reload_devices_from_db` aufzurufen.
- **`pool.get_soc(state_cache)`** — liest aus Cache; Reload mutiert den Pool, aber der Cache bleibt unberührt.

**Aus Story 3.2 (Drossel-Policy):**

- **`_drossel_buffers` sind grid-meter-gebunden.** Reload tangiert sie nicht. Drossel-Policy ist Akku-agnostisch — Nacht-Gate gilt nicht für Drossel.

**Aus Story 3.1 (Foundation):**

- **`now_fn`-Injection (UTC).** Bleibt bestehen für Audit-Cycles und Dwell-Time.
- **`db_conn_factory` als Closure** — Reload-Methode kann sie unverändert verwenden.
- **Per-Device-Lock** — schützt In-flight-Dispatches; Reload mutiert nur Controller-Felder, kein Lock-Konflikt.

**Aus Story 2.1 (Hardware Config Page):**

- **`HardwareConfigRequest.validate_soc_range`** — Pattern für gemeinsamen Validator-Refactor (Task 1).
- **`night_discharge_enabled` + `night_start` + `night_end` werden bereits seit 2.1 in `wr_charge.config_json` persistiert.** Story 3.6 macht sie **zum ersten Mal funktional** (Controller-Gate).
- **`replace_all`-Pattern preserved `commissioned_at` durch ON CONFLICT UPDATE.** Story 3.6 nutzt **nicht** replace_all für PATCH — Single-Row-Update.

**Aus Story 2.3 / 2.3a (Disclaimer-Gates):**

- **`evaluateGate`-Decision-Tree.** Story 3.6 ergänzt einen Settings-Branch (AC 24).
- **`WIZARD_ROUTES`-Set** — Settings ist **kein** Wizard-Mitglied.

**Aus Story 4.0a (Diagnose-Schnellexport):**

- **„Versteckte Route, nur direkter URL"-Pattern.** Settings folgt 1:1.

**Aus Story 5.1a (Live-Betriebs-View):**

- **Polling-Endpoint `/api/v1/control/state` reagiert auf neue Bounds in der Frontend-Anzeige nahtlos** — Settings-Save → Controller-Reload → nächster Sensor-Event nutzt neue Bounds → State-Cache mirror → Polling-Antwort enthält neue Werte. Kein zusätzlicher Pfad nötig.

### Git Intelligence Summary

**Letzte 5 Commits (chronologisch, neueste zuerst):**

- `0a19a08 feat(control): adaptive mode selection and surplus export workflow` — Story 3.5 abgeschlossen + 3.8 Architektur-Amendment. Pattern aus 3.5 (`_evaluate_mode_switch`, Constructor-Param-Erweiterung, Reset-Logik) sind direkt relevant für 3.6.
- `59aba38 chore(release): beta 0.1.1-beta.8` — Sync-Release.
- `65d675e feat(4.0a): Diagnose-Schnellexport (DB-Dump + Logs als ZIP) + Code-Review-Patches` — Versteckte-Route-Pattern (Settings folgt 1:1).
- `21b0306 fix(4.0): code-review patches — 13 findings + is_self_echo flag` — Logging-Disziplin (sanitize, isEnabledFor-Guards). 3.6 nutzt `_logger.info` und `_logger.exception` analog.
- `1a22d8f fix(2.4): code-review patches — config_json validation, kW/input_number setup endpoint, UI limit-range overrides` — `device.config_json`-Override-Mechanik, gleiche Mechanik wie 3.6 für Akku-Bounds.

**Relevante Code-Patterns aus den Commits:**

- **`_speicher_max_soc_capped`/`_speicher_min_soc_capped`-Flag-Pattern (3.4):** Direkt Vorlage für `_speicher_night_gate_active`.
- **`_record_mode_switch_cycle` Cap-Flag-Reset (3.5):** Erweiterung um `_speicher_night_gate_active`.
- **`HardwareConfigRequest`-Pydantic-Validierung mit `model_validator(mode='after')` (2.1, 2.4):** Vorlage für `BatteryConfigPatchRequest`.
- **`replace_all`-Pattern preserves commissioning (2.1):** Story 3.6 nutzt es **nicht** — neuer Single-Row-Helper.
- **`evaluateGate`-Routing-Whitelist (2.3a):** Erweiterung für Settings.
- **„Versteckte Route nur direkter URL" (4.0a):** Pattern für Settings.
- **`device.config_json`-Override-Schema (2.4):** Pattern für die Werte, die in 3.6 editiert werden.

### Latest Tech Information

- **Python 3.13** — `time`-Klasse aus `datetime` ist stdlib, supports `<`, `<=`, `==` Vergleiche direkt. Wraparound-Logik nutzt diese Vergleichsoperatoren ohne extra Bibliothek.
- **`json.loads` + `json.dumps`** — stdlib. `json.dumps(obj)` ohne `indent` produziert kompaktes JSON; das Repository persistiert kompakt.
- **Pydantic 2 `model_validator(mode='after')`** — klassenmethoden-Pattern; läuft nach Field-Validators. Bestehendes Pattern in `HardwareConfigRequest`.
- **FastAPI `@router.patch(...)`** — analog zu existing `@router.post(...)`-Pattern. `request: Request`-Injection für `app.state.controller`-Zugriff.
- **Svelte 5 Runes (`$state`, `$derived`)** — etabliert in Config.svelte / Running.svelte.

### Project Structure Notes

- Alignment with [unified-project-structure.md](../planning-artifacts/architecture.md#directory-layout): Settings.svelte unter `frontend/src/routes/`. Backend-Schemas in `api/schemas/devices.py`, Routes in `api/routes/devices.py`. Repositories in `persistence/repositories/devices.py`. Tests gespiegelt unter `tests/unit/`.
- Keine Konflikte oder Variances zur Architektur — Story 3.6 folgt allen etablierten Patterns aus Stories 2.1, 3.4, 3.5.

### References

- [Story 3.6 in epics.md (Zeile 998–1028)](../planning-artifacts/epics.md#story-36)
- [Architecture Cut #10 (JSON-Template-Verbot, Zeile 1088)](../planning-artifacts/architecture.md)
- [Architecture `device.config_json`-Override-Schema (Zeile 1106)](../planning-artifacts/architecture.md)
- [Architecture Amendment 2026-04-25 Surplus-Export (Zeile 1129)](../planning-artifacts/architecture.md)
- [PRD FR20 Nacht-Entlade (Zeile 603)](../planning-artifacts/prd.md)
- [PRD FR22 Min/Max-SoC-Konfiguration (Zeile 608)](../planning-artifacts/prd.md)
- [PRD Akku-Schutz-Argumentation (Zeile 295, 317)](../planning-artifacts/prd.md)
- [UX Björn-Use-Case (Zeile 256)](../planning-artifacts/ux-design-specification.md)
- [UX-DR30 Anti-Patterns](../planning-artifacts/ux-design-specification.md)
- [CLAUDE.md 5 harte Regeln](../../CLAUDE.md)
- [Story 2.1 — Hardware Config Page (Pflichtlektüre Validator-Refactor)](./2-1-hardware-config-page-typ-auswahl-entity-dropdown.md)
- [Story 2.3a — Pre-Setup-Disclaimer-Gate (Routing-Pattern)](./2-3a-pre-setup-disclaimer-gate.md)
- [Story 3.4 — Speicher-Modus (Cap-Flag-Pattern, `_read_soc_bounds`)](./3-4-speicher-modus-akku-lade-entlade-regelung-innerhalb-soc-grenzen.md)
- [Story 3.5 — Adaptive Mode Switching (Reset-Pattern, Constructor-Param)](./3-5-adaptive-strategie-auswahl-hysterese-basierter-modus-wechsel-inkl-multi-modus.md)
- [Story 4.0a — Diagnose-Schnellexport (Versteckte-Route-Pattern)](./4-0a-diagnose-schnellexport-db-dump-logs-zip.md)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] via /bmad-dev-story (2026-04-25)

### Debug Log References

— Backend: 377 Tests grün (vorher 339, +38 neu); Ruff + MyPy --strict grün.
— Frontend: 73 Tests grün (vorher 61, +12 neu); ESLint + svelte-check + Prettier + Vite-Build grün.

### Completion Notes List

- **Backend Schema (Task 1):** `BatteryConfigPatchRequest` + `BatteryConfigResponse` in
  `api/schemas/devices.py` ergänzt. Validator-Logik in zwei freie Helper extrahiert
  (`_validate_soc_gap`, `_validate_night_window`); `HardwareConfigRequest.validate_soc_range`
  ruft jetzt dieselben Helper auf — Behavior unverändert (Bestandstest-Suite grün).
  Validator-Methode des PATCH-Schemas heißt `validate_constraints`, weil `validate` mit
  Pydantic-`BaseModel.validate` kollidiert hätte (mypy --strict-Hint).
- **Repository (Task 2):** `update_device_config_json` als pure Single-Row-UPDATE in
  `persistence/repositories/devices.py` ergänzt. Returns rowcount, kein UPSERT,
  preserves `commissioned_at` und alle anderen Spalten.
- **Controller (Tasks 3, 5, 6, 7):**
  - Konstruktor-Param `local_now_fn: Callable[[], datetime] = datetime.now` ergänzt
    (separater Hook, nicht mit `now_fn` UTC zusammengelegt).
  - Modul-Top-Level-Helpers `_HHMM_PATTERN`, `_is_valid_hhmm`,
    `_read_night_discharge_window`, `_is_in_night_window` direkt unterhalb von
    `_read_soc_bounds` ergänzt (analoges Pattern, Pure Functions).
  - `_speicher_night_gate_active`-Flag in `__init__` initialisiert; Reset in
    `_record_mode_switch_cycle` neben den SoC-Cap-Flags.
  - Nacht-Gate-Branch in `_policy_speicher` direkt nach dem Min-SoC-Cap-Branch und
    vor dem Sign-Flip-Block — gilt **nur** für `smoothed > 0` (Bezug); Charge-Branch
    läuft 24/7 unverändert.
  - Async-Methode `reload_devices_from_db` rebuildet `devices_by_role`,
    `_battery_pool` und `_wr_limit_device`. Schreibt **kein** Audit-Cycle, ändert
    **keinen** Mode-State, resettet **keine** Buffer/Cap-Flags. Lazy-Import von
    `BatteryPool` und `list_devices` innerhalb der Methode (vermeidet Cycle-Guard).
  - main.py blieb unverändert — Default `datetime.now` deckt Production.
- **PATCH-Route (Task 4):** `PATCH /api/v1/devices/battery-config` in
  `api/routes/devices.py`. Lädt `wr_charge`, mergt die fünf Keys in den existierenden
  `config_json`-Blob (preserves `allow_surplus_export` aus 3.8 — Test deckt das
  explizit ab), persistiert via Repository-Helper, ruft `controller.reload_devices_from_db()`
  synchron, antwortet direkt mit dem Response-Objekt (kein Wrapper, CLAUDE.md Regel 4).
  404 bei nicht-vorhandenem `wr_charge`. Standard-`HTTPException` plus
  `register_exception_handlers`-Middleware liefert RFC-7807-Format.
- **Existing-Test-Erweiterung (Task 11):** `_make_speicher_controller`-Helper in
  `test_controller_speicher_policy.py` injiziert jetzt einen deterministischen
  `local_now_fn` (Default 22:00 — innerhalb des Default-Nacht-Fensters), damit die
  Bestandstests von 3.4 unter dem neuen Gate weiterlaufen.
- **Backend Tests (Task 11):**
  - `test_battery_config_route.py` — 8 Test-Cases (Persistierung + Reload, Min/Max-Gap,
    Plausibilitäts-Confirm, Hard-Floor < 5, leeres Nacht-Fenster, drossel-only → 404,
    Merge-Semantik mit `allow_surplus_export`).
  - `test_controller_night_discharge.py` — 24 Tests (Pure-Function-Tabelle für
    `_is_in_night_window` 12 Boundary-/Wraparound-Fälle, `_is_valid_hhmm`-Tests,
    `_read_night_discharge_window`-Defaults/Malformed/Disabled, plus 8 Integrations-
    Tests für Outside/Inside/Wraparound/Boundaries/Disabled/Charge-unaffected/
    Once-per-band-log/Flag-Reset).
  - `test_controller_reload.py` — 6 Tests (Reload picks up new bounds, Buffer
    preservation, Mode-State unchanged, Pool-empty fallback, log-record, Pre-Save
    Min-SoC drift).
- **Frontend Types/Client (Task 8):** `BatteryConfigPatchRequest` + `BatteryConfigResponse`
  in `lib/api/types.ts` (snake_case JSON, CLAUDE.md Regel 1) und
  `patchBatteryConfig`-Funktion in `lib/api/client.ts`.
- **Frontend Settings.svelte (Task 9):** Neue Komponente unter `routes/Settings.svelte`.
  Skeleton-Pulse während des `getDevices()`-Calls (≥ 400 ms gegen Pop-In, gleicher
  Helper wie 2.1). Akku-Konfig-Card mit Min/Max-SoC-Inputs + Inline-Plausibilitäts-
  Confirm-Block (UX-DR30 — kein Modal). Nacht-Entladung-Card mit Toggle + Time-Inputs
  (Toggle off → Time-Inputs komplett ausgeblendet). Save-Button disabled bei
  Validation-Error oder pending Plausibilitäts-Confirm. Drossel-only-Setup → AC 19
  „Kein Akku konfiguriert"-Hinweis. Inline-Confirm-Line nach erfolgreichem Save.
  Strings deutsch hardcoded.
- **Frontend Routing (Task 10):** `App.svelte` lädt `Settings`-Komponente; `/settings` in
  `VALID_ROUTES`. `lib/gate.ts::evaluateGate` bekommt einen Settings-Branch direkt
  nach `/diagnostics`: pre-disclaimer-Gate funktioniert, aber kein Wizard-Redirect.
  `WIZARD_ROUTES` bleibt unverändert (Settings ist post-commissioning). Kein
  Settings-Link in `Running.svelte` — Discovery via Discord/Doku.
- **Frontend Tests (Task 12):**
  - `Settings.test.ts` — 9 Test-Cases (Skeleton, Drossel-only-Hinweis, Gap-Disable,
    Plausibilitäts-Confirm-Block, Cancel-Reset, Night-Toggle-Hide, Patch-Body-Shape,
    Confirm-Save mit Ack-Flag, PATCH-Error-Inline).
  - `gate.test.ts` — 3 neue Cases für `/settings`-Route (commissioned User stay,
    pre-disclaimer-Redirect, devices empty + preAccepted stay).
- **Drift-Checks (Task 13):**
  - 0 Treffer für `ZoneInfo|pytz|tzlocal` (keine TZ-Dep eingeführt).
  - 0 Treffer für `structlog|APScheduler|cryptography|numpy|pandas|SQLAlchemy`.
  - SQL-Migrations-Liste unverändert: `001`, `002`, `003` (keine `004` aus 3.6 —
    3.8 wird sie ergänzen).
  - Alle 4 Hard-CI-Gates grün.

### File List

**MOD Backend:**
- `backend/src/solalex/api/schemas/devices.py` — `_validate_soc_gap` + `_validate_night_window`-Helper, `BatteryConfigPatchRequest` + `BatteryConfigResponse`, `HardwareConfigRequest.validate_soc_range` ruft die Helper.
- `backend/src/solalex/api/routes/devices.py` — `PATCH /api/v1/devices/battery-config`-Route + Imports.
- `backend/src/solalex/persistence/repositories/devices.py` — `update_device_config_json`-Helper.
- `backend/src/solalex/controller.py` — `local_now_fn`-Konstruktor-Param, `_speicher_night_gate_active`-Flag, `_HHMM_PATTERN`, `_is_valid_hhmm`, `_read_night_discharge_window`, `_is_in_night_window`, Nacht-Gate-Branch in `_policy_speicher`, `reload_devices_from_db`-Methode, Reset im `_record_mode_switch_cycle`.

**NEU Backend Tests:**
- `backend/tests/unit/test_battery_config_route.py`
- `backend/tests/unit/test_controller_night_discharge.py`
- `backend/tests/unit/test_controller_reload.py`

**MOD Backend Tests:**
- `backend/tests/unit/test_controller_speicher_policy.py` — `_make_speicher_controller`-Helper injiziert `local_now_fn` (Default 22:00, innerhalb Nacht-Fenster) für Backwards-Compat.

**MOD Frontend:**
- `frontend/src/App.svelte` — `Settings`-Import + `/settings` in `VALID_ROUTES` + Render-Branch.
- `frontend/src/lib/gate.ts` — Settings-Branch in `evaluateGate`.
- `frontend/src/lib/api/client.ts` — `patchBatteryConfig`-Funktion.
- `frontend/src/lib/api/types.ts` — `BatteryConfigPatchRequest`, `BatteryConfigResponse`.

**NEU Frontend:**
- `frontend/src/routes/Settings.svelte`

**NEU Frontend Tests:**
- `frontend/src/routes/Settings.test.ts`

**MOD Frontend Tests:**
- `frontend/src/lib/gate.test.ts` — 3 neue Test-Cases für `/settings`-Route.

### Change Log

- 2026-04-25 — Story 3.6 implementiert via `/bmad-dev-story`: User-Config Min/Max-SoC + Nacht-Entlade-Zeitfenster. Settings-Route + PATCH-Endpoint mit Pydantic-Validator-Refactor + Plausibilitäts-Inline-Confirm + Repository-Helper + Controller-Reload + Modul-Top-Level-Night-Helper + Nacht-Gate im Bezug-Branch von `_policy_speicher`. ~38 neue Backend-Tests, 12 neue Frontend-Tests. Keine SQL-Migration, keine neue Dependency. Backwards-Compat in `test_controller_speicher_policy.py` über `local_now_fn`-Default 22:00.
