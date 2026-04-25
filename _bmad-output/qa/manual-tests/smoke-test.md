# Solalex — Manueller Smoke-Test (GUI im HA-Ingress)

**Zweck.** Nachweisen, dass das Add-on nach einem Update grundsätzlich startet, der Setup-Walkthrough vom Disclaimer bis zum Live-Betrieb komplett durchläuft, und der Live-Betriebs-View Polling/Chart/Zyklen-Liste anzeigt. Kein vollständiger Funktions-Test — nur "rauchts oder läufts an?".

**Dauer:** ~10–15 min bei grünem Pfad.
**Letzte Aktualisierung:** 2026-04-25 (Story 2.4 Generic-Adapter-Refit: Trucki/ESPHome-SML laufen direkt ueber HA-Standardattribute).

---

## 1. Test-Umgebung

| Punkt | Wert |
|---|---|
| Test-HA | echtes Home Assistant mit installiertem Solalex-Add-on |
| Solalex-Build | aktueller Beta-Build aus Custom Repository (vor Test updaten) |
| Browser | Desktop, aktueller Stand |
| Devtools | offen lassen — Console-Errors gelten als Smoke-Test-Fail |

### 1.1 Hardware-Inventar (echte Test-HW)

| Rolle | Entity-ID | Hinweis |
|---|---|---|
| Wechselrichter (write) | `input_number.t2sgf72a29_t2sgf72a29_set_target` | Trucki-Stick als ESPHome-Wrapper für Hoymiles. Domain `input_number`, **nicht** `number`. |
| Wechselrichter (Output-Readback) | `sensor.t2sgf72a29_t2sgf72a29_output` | tatsächliche Einspeise-Leistung des WR (W) |
| Smart Meter (Netz) | `sensor.00_smart_meter_sml_current_load` | ESPHome SML-Reader. **Vorzeichen: negativ = Einspeisung, positiv = Bezug** |
| Akku-SoC | `sensor.esp_victron_state_of_charge` | Victron via ESPHome — für Speicher-Modus (Story 3.4) reserviert, **im Smoke nicht verwendet** |

### 1.2 Generic-Compat-Erwartung

Seit Story 2.4 nutzt Solalex fuer Wechselrichter und Smart Meter generische HA-Standardattribute statt vendor-spezifischer Entity-ID-Patterns.

| Rolle | Erwartete Detection |
|---|---|
| Wechselrichter-Limit | Domain `number` oder `input_number` + `unit_of_measurement` `W` oder `kW` |
| Smart Meter | Domain `sensor` + `unit_of_measurement` `W` oder `kW` |

**Erwartung:** Die echte Trucki-Limit-Entity `input_number.t2sgf72a29_t2sgf72a29_set_target` und die ESPHome-SML-Entity `sensor.00_smart_meter_sml_current_load` sind direkt im Config-Dropdown sichtbar. Template-Helpers sind nicht mehr Teil des Normalpfads.

### 1.3 Vorbedingungen vor Testbeginn

- [ ] Die echten HA-Entities aus §1.1 haben `unit_of_measurement: W` oder `kW`
- [ ] HA-Sidebar zeigt Solalex-Eintrag
- [ ] Im HA-Add-on-Store ist die neueste Solalex-Version installiert (siehe ST-00)
- [ ] Es laufen **keine** parallelen HA-Automationen, die `input_number.t2sgf72a29_t2sgf72a29_set_target` schreiben (sonst kollidiert der Closed-Loop-Readback im Funktionstest)

### 1.4 Abbruch-Kriterien (Test sofort stoppen)

- Add-on-Container crasht / restartet im Loop
- HA-Ingress liefert leere Seite / 502 / weißen Bildschirm > 10 s
- Browser-Console zeigt unbehandelte JS-Errors (rote Einträge)
- Funktionstest sendet einen Limit-Wert > 3000 W an den Trucki-Stick (Generic-Inverter Default-Range ist `(2, 3000)` W — alles drüber wäre ein echter Range-Check-Bug)

---

## 2. Smoke-Test-Fälle

Jeder Fall ist atomar abhakbar. Reihenfolge ist Walkthrough-Reihenfolge — bei rotem Befund nicht zum nächsten Fall springen, sondern in §3 protokollieren.

### ST-00 — Add-on Update & Start

**Vorbedingung:** Solalex ist als Add-on installiert, Custom Repository ist hinzugefügt.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | HA → Settings → Add-ons → Solalex | Add-on-Detail-Seite lädt | ☐ |
| 2 | "Check for updates" / Repository-Refresh | Neue Version wird angezeigt (falls vorhanden) | ☐ |
| 3 | "Update" klicken, warten bis Status `Started` | Update läuft ohne Error im Add-on-Log | ☐ |
| 4 | Add-on-Log einsehen | Letzte ~20 Zeilen zeigen FastAPI-Startup, kein Traceback, kein `ERROR` | ☐ |
| 5 | "Open Web UI" oder Sidebar-Eintrag klicken | Solalex-Ingress lädt in < 3 s | ☐ |

**Notiz:** Falls Story 4.0 (Debug-Logging-Toggle) bereits gemerged ist, Log-Level auf `debug` setzen für mehr Sichtbarkeit. Sonst Default lassen.

---

### ST-01 — Pre-Setup-Disclaimer (Erstinstallation)

**Vorbedingung:** Erster Aufruf nach Update **oder** `localStorage` im Browser-Tab geleert (DevTools → Application → Local Storage → Eintrag `solalex_pre_disclaimer_accepted` löschen, wenn vorhanden).

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Solalex-UI öffnen | Route `#/pre-disclaimer`, Header "Bevor es losgeht" | ☐ |
| 2 | Drei Absätze Disclaimer-Text lesbar | Layout zentriert, Card-Container, kein Overflow | ☐ |
| 3 | Checkbox "Ich habe die Sicherheitshinweise gelesen…" anklicken | Checkbox aktiviert, **darunter erscheint Button "Weiter"** | ☐ |
| 4 | "Weiter" klicken | Navigation zu `#/config`, kein Zwischen-Loader > 400 ms | ☐ |
| 5 | URL-Hash ist `#/config` | ☐ | |

**Falls Disclaimer wegen persistiertem `localStorage` übersprungen wird:** das ist erwartetes Verhalten. Trotzdem durch `#/pre-disclaimer` manuell ansteuern und prüfen, dass die Seite rendert.

---

### ST-02 — Hardware-Konfiguration

**Vorbedingung:** Route `#/config` ist offen. Die echten Trucki-/ESPHome-Entities aus §1.1 sind in Home Assistant vorhanden und liefern `unit_of_measurement`.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Seite initial | Skeleton-Pulse für ≥ 400 ms, dann Header "Hardware konfigurieren" | ☐ |
| 2 | Sektion "Hardware-Typ" sichtbar | Zwei Tiles: "Wechselrichter (allgemein)" und "Marstek Venus 3E/D"; Wechselrichter-Sub-Label nennt Hoymiles/OpenDTU, Trucki, ESPHome | ☐ |
| 3 | Tile **"Wechselrichter (allgemein)"** klicken | Tile-Border wechselt auf Akzentfarbe, Sektion "Wechselrichter-Limit-Entity" wird gerendert | ☐ |
| 4 | Dropdown "— Entity wählen —" öffnen | Echte Trucki-Entity `input_number.t2sgf72a29_t2sgf72a29_set_target` ist gelistet → auswählen | ☐ |
| 5 | Checkbox "Smart Meter zuordnen" anhaken | Sub-Label nennt Shelly 3EM, ESPHome SML, Tibber; zweites Dropdown "Netz-Leistungs-Entity" erscheint | ☐ |
| 6 | Smart-Meter-Dropdown öffnen | Echte ESPHome-SML-Entity `sensor.00_smart_meter_sml_current_load` ist gelistet → auswählen | ☐ |
| 7 | Button "Speichern" wird sichtbar | Klick → "Speichern…"-State, dann Navigation zu `#/functional-test` | ☐ |

**Fail in ST-02:** Wenn Trucki oder ESPHome-SML fehlen, erst in HA Developer Tools prüfen, ob `unit_of_measurement` `W` oder `kW` gesetzt ist. Fehlt das Attribut, ist der optionale Template-Helper-Anhang weiterhin nutzbar; ist das Attribut vorhanden, ist es ein Story-2.4-Bug.

---

### SR-01 — Vorzeichen-Verifikation Smart-Meter (Story 2.5)

**Vorbedingung:** Route `#/config`, Smart-Meter wurde gewählt (Schritt 6 aus ST-02), `gridMeterEntityId` ist gesetzt. Eine schaltbare Last mit ≥ 1 kW Aufnahme (Wasserkocher, Heizlüfter, Backofen) ist greifbar.

**Ziel:** Sicherstellen, dass die Vorzeichen-Konvention des Smart-Meters mit Solalex' Erwartung (positiv = Bezug, negativ = Einspeisung) übereinstimmt — vor dem Speichern, ohne nachträgliches Debugging.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Live-Preview-Card unter dem Smart-Meter-Block lesen | Zeigt aktuellen Sensor-Wert in Watt + Konventions-Hinweis ("Bezug aus dem Netz" / "Einspeisung ins Netz" / "nahezu 0 W") | ☐ |
| 2 | Last (Wasserkocher) einschalten und ~5 s warten | Live-Wert steigt deutlich an (≥ 1000 W über vorigem Wert) | ☐ |
| 3 | Hinweis-Satz auswerten | Bei korrekter Konvention: "Bezug aus dem Netz". Bei falscher Konvention: Wert FÄLLT statt zu steigen oder Hinweis sagt "Einspeisung", obwohl Last läuft | ☐ |
| 4 | Falls Konvention falsch: Toggle "Vorzeichen invertieren" anklicken | Live-Wert flippt sofort ohne Polling-Delay; Hinweis-Satz wechselt; Wert steigt jetzt korrekt mit der Last | ☐ |
| 5 | Last ausschalten | Live-Wert fällt zurück auf vorigen Bereich (oder ins negative bei Mittagseinspeisung) | ☐ |
| 6 | Speichern → Funktionstest fortsetzen | Toggle-Zustand wird mit gespeichert (im Add-on-Log: `devices_saved`-Eintrag) | ☐ |

**Fail in SR-01:** Live-Preview-Card zeigt "Live-Wert konnte nicht geladen werden." → Backend-Endpoint `GET /api/v1/setup/entity-state` ist nicht erreichbar oder Entity ist nicht im Whitelist-Set. Prüfe Add-on-Log auf `entity_state_subscribe_failed` oder 403-Antworten.

**Hinweis:** ESPHome SML mit Standard-OBIS-Mapping liefert oft `negativ = Bezug` (Test SR-01 zeigt das sofort). Shelly 3EM und Tibber Pulse liefern Solalex-konform (`positiv = Bezug`).

---

### SH-01 — Hardware-Wechsel im laufenden Betrieb (Story 2.6)

**Vorbedingung:** Setup ist commissioned (mind. ein WR + optional Smart-Meter), `/running` läuft.

**Ziel:** Sicherstellen, dass ein nachträglicher Hardware-Wechsel über die UI machbar ist — ohne SQL-Reset, ohne Add-on-Restart.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | `#/settings` öffnen | Sektion „Hardware-Konfiguration" zeigt aktuelle Devices + Button „Hardware ändern" | ☐ |
| 2 | „Hardware ändern" klicken | Navigation zu `#/hardware-edit`; Header heißt „Hardware ändern" (nicht „Hardware konfigurieren"); aktuelle Werte vorbefüllt | ☐ |
| 3 | Smart-Meter-Sign-Toggle umlegen (oder min/max-Limit ändern), Speichern | Button heißt „Änderungen übernehmen"; nach Klick Navigation zu `#/running`; **kein** Funktionstest-Banner; Live-Chart zeigt invertierten Wert / neue Limits korrekt | ☐ |
| 4 | Erneut `#/settings` → „Hardware ändern" | Edit-Form lädt mit den jetzt aktuellen Werten | ☐ |
| 5 | WR-Entity wechseln (anderes `input_number.<…>`-Ziel wählen), Speichern | Warn-Banner „Diese Änderung erfordert einen erneuten Funktionstest" erscheint vor Save; nach Save Navigation zu `#/running`; Banner „Funktionstest erforderlich für den neuen Wechselrichter" mit Link „Funktionstest starten" sichtbar | ☐ |
| 6 | „Funktionstest starten" klicken | Navigation zu `#/functional-test`; Test wie ST-03 läuft durch; nach Bestätigung kehrt `/running` zurück, Banner verschwindet | ☐ |
| 7 | Diagnose-Trail prüfen (sofern verfügbar oder via `solalex.db`-Query) | `control_cycles` enthält Einträge mit `reason='hardware_edit: …'` und `readback_status='noop'` | ☐ |

**Fail in SH-01:**
- `#/hardware-edit` redirected zu `#/disclaimer` → Pre-Setup-Disclaimer-LocalStorage geblockt; manuell akzeptieren in `#/disclaimer`.
- Save mit identischer Config schreibt einen `hardware_edit`-Cycle → No-op-Diff-Logik defekt; im Add-on-Log nach `devices_updated` mit `diff_kind='identical'` filtern.
- Reload-Hook nicht ausgeführt: Drossel-Policy regelt nach WR-Wechsel das alte Device → `controller.reload_devices_from_db` schlug fehl, Add-on-Log nach `controller_reload_devices` filtern.

---

### ST-03 — Funktionstest mit Closed-Loop-Readback

**⚠ Achtung:** Dieser Test sendet einen **realen Schreibbefehl** an Deinen Trucki/Hoymiles-WR. Zeitpunkt so wählen, dass eine kurzzeitige Limit-Änderung am WR keine Probleme macht (kein laufender Eigenverbrauch-kritischer Vorgang).

**Vorbedingung:** Route `#/functional-test`, Hardware ist gespeichert.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Seite öffnet | Header "Funktionstest", Karte "Zielhardware" zeigt "Wechselrichter" + Liste der konfigurierten Entities mit Role-Tag | ☐ |
| 2 | Button "Funktionstest starten" sichtbar | Klick auslösen | ☐ |
| 3 | Test läuft | Karte mit "Test läuft…" + Live-Chart, X-Achse 5 s gleitend, Y zeigt Werte | ☐ |
| 4 | Innerhalb von ≤ 15 s | Result-Karte erscheint mit grünem Tick (`✓`) und Text **"Readback erfolgreich — XXXX W (Soll: YYYY W, Toleranz ±Z W)"** + Latenz in ms | ☐ |
| 5 | Button "ja ich akzeptiere das" anklicken | Navigation zu `#/activate` | ☐ |

**Bei Fail:** Roter Tick (`✗`) + Text "Readback-Mismatch…" oder "Timeout — kein Readback innerhalb von 15 s". Dann **nicht** weitertesten — in §3 protokollieren mit:
- Soll-/Ist-Wert
- Latenz (falls angezeigt)
- Add-on-Log-Auszug der letzten ~30 s
- ob `solalex.control_cycles`-Tabelle einen Eintrag mit `readback_status='failed'` enthält (falls einsehbar)

---

### ST-04 — Aktivierung (Commissioning)

**Vorbedingung:** Route `#/activate`.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Seite zeigt | Header "Bevor es losgeht", Disclaimer-Text, Checkbox unchecked | ☐ |
| 2 | Checkbox anhaken | Button "Aktivieren" erscheint | ☐ |
| 3 | "Aktivieren" klicken | Button-Text wechselt zu "Wird aktiviert…", Button bleibt disabled bis Antwort | ☐ |
| 4 | Antwort vom Backend | Navigation zu `#/running`, kein Error-Toast | ☐ |

**Fail-Pfade:**
- "Keine Verbindung zum Add-on" → Add-on tot, ST-00 schlug heimlich fehl
- "Aktivierung fehlgeschlagen" + Detail → Backend-Error, Log prüfen

---

### ST-05 — Live-Betriebs-View (Story 5.1a)

**Vorbedingung:** Route `#/running`, Add-on ist commissioned.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Seite öffnet | Header "Live-Betrieb", Mode-Chip oben rechts mit Label `Idle` / `Drossel` / `Speicher` / `Multi` | ☐ |
| 2 | Live-Chart-Karte | LineChart-SVG mit Serien "Netz-Leistung", "Target-Limit", "Readback" — alle drei je nach Konfiguration sichtbar | ☐ |
| 3 | Polling läuft | DevTools → Network → wiederkehrende `GET /api/v1/control/state` im 1-s-Takt, Status 200 | ☐ |
| 4 | Mode-Chip | Bei aktiver Drossel-Regelung: Chip wechselt sichtbar von `Idle` auf `Drossel` (Akzentfarbe), sobald erstes Sensor-Event kam | ☐ |
| 5 | Karte "Letzte Zyklen" | Initial: "Noch keine Zyklen erfasst." → nach erstem Regelzyklus: Liste füllt sich mit Spalten `vor X s`, `solalex/manual/ha_automation`, `Target W`, `passed/failed/timeout/vetoed`, `latency_ms` | ☐ |
| 6 | Falls Rate-Limit aktiv | Hinweis "Nächster Write in N s" wird zwischen Chart und Zyklen-Liste sichtbar, N zählt herunter | ☐ |
| 7 | Browser-Tab 60 s offen lassen | Chart-Punkte wandern von rechts nach links, alte Punkte (> 5 s) verschwinden, kein Memory-Leak (Tab bleibt responsiv) | ☐ |
| 8 | Browser-Reload (`Cmd+R`) | Seite kommt sauber zurück, Polling startet neu, kein "Verbindungsfehler beim Laden der Geräte." | ☐ |

---

### SD-01 — Diagnose-Klartext im Live-Betrieb (Story 5.1d)

**Vorbedingung:** Solalex commissioned, Drossel-Mode aktiv, Solar > Last (leichte Einspeisung).

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Route `#/running` öffnen | Mode-Chip „Drossel" + Erklärungs-Zeile „Drossel — verhindert ungewollte Einspeisung durch WR-Limit-Anpassung" direkt unter dem H1 | ☐ |
| 2 | Status-Tile-Reihe oberhalb des Charts sichtbar | „Netz-Leistung" (mit Sub-Label „Bezug aus dem Netz" / „Einspeisung ins Netz" / „nahezu 0 W"), „Wechselrichter-Limit" + Sub „Aktuelles Limit", „Verbindung" zeigt „Verbunden" (grüner Akzent) | ☐ |
| 3 | Cycle-Liste hat Header | Zeile „vor / Quelle / Ziel / Status / Latenz" über der Liste, dezent in Akzent-grau | ☐ |
| 4 | Wasserkocher anschalten (Last) | Cycle-Status wechselt von „Im Toleranzbereich" auf „Übernommen" (grün-Akzent) mit Watt-Zahl in Ziel-Spalte | ☐ |
| 5 | Wasserkocher aus, Tab offen lassen | Status nach 1–2 Zyklen wieder „Im Toleranzbereich"; Ziel-Spalte zeigt „— (gemessen X W)" | ☐ |
| 6 | Hover über Status-Spalte | Native Browser-Tooltip mit vollem Backend-`reason` (z. B. `noop: deadband (smoothed=12w, deadband=20w)`) erscheint | ☐ |
| 7 | HA-Container neu starten (Supervisor → Reload Add-ons) | Connection-Tile wechselt auf „Getrennt" (Warning-Farbe) mit Sub-Zeile „vor X s" — Counter zählt sekundengenau hoch | ☐ |
| 8 | Reconnect abwarten (≤ 30 s) | Connection-Tile wieder „Verbunden", Sub-Zeile „Home Assistant" | ☐ |
| 9 | In der Cycle-Liste scrollen | Bis zu 50 Zyklen sichtbar (statt vorher 10), Scroll innerhalb der Karte funktioniert | ☐ |

---

### ST-06 — Spot-Checks nach Live-Betrieb

Kurze Querschecks, jeweils 1 Klick, ohne erneutes Setup.

| # | Check | Erwartung | ☐ |
|---|---|---|---|
| 1 | URL-Hash auf `#/functional-test` setzen, während `#/running` läuft | Funktionstest-Seite öffnet, "Test läuft…" wird **nicht** automatisch ausgelöst | ☐ |
| 2 | Auf `#/running` zurücknavigieren | Falls währenddessen ein Test gelaufen wäre: Karte "Funktionstest läuft — Regelung pausiert." mit Link wäre sichtbar gewesen. Im Smoke-Pfad: normaler Live-Betriebs-View | ☐ |
| 3 | Add-on im HA neustarten | Nach Restart kommt UI direkt nach `#/running` (Disclaimer + Setup nicht erneut) | ☐ |
| 4 | DevTools → Console | Keine roten Errors, keine Warnings über fehlende Polling-Antworten | ☐ |
| 5 | Add-on-Log nach 5 min Live-Betrieb | Reguläre Zyklen-Logs (JSON-Format), keine Tracebacks, keine "rate limit hit" als Error (nur Info) | ☐ |

---

## 3. Befund-Protokoll

Pro auffälligem Befund eine Zeile, auch wenn der Test sonst grün durchläuft.

| Test-ID | Befund | Schwere | Reproduzierbar? | Add-on-Log-Snippet |
|---|---|---|---|---|
|  |  |  |  |  |

**Schwere-Skala:**
- `block` — Smoke-Test gilt als fehlgeschlagen, Beta-Release nicht möglich
- `warn` — Kann released werden, muss aber als bekannter Befund dokumentiert sein
- `note` — kosmetisch, Doku-Eintrag reicht

---

## 4. Pass-Kriterien (für „Smoke grün")

- [ ] ST-00 bis ST-05: alle Schritte abgehakt, kein roter Bildschirm, keine Console-Errors
- [ ] Funktionstest hat direkt gegen die echte Trucki-Entity ein `passed` mit echtem WR-Output-Schwenk ergeben
- [ ] Live-Betriebs-View hat ≥ 1 echten Regelzyklus aufgezeichnet
- [ ] Polling läuft stabil über mindestens 60 s ohne Drop
- [ ] Add-on-Log nach Smoke-Test ist frei von Tracebacks

→ **Build ist „smoke-grün end-to-end"**. Vollständige Test-Suiten (Drossel-Stress, Rate-Limit, Idle/Drossel-Wechsel, Failover) folgen separat.

---

## 5. Anhang: Optionale Template-Helpers fuer Edge-Cases ohne `unit_of_measurement`

Nur lesen, wenn Deine echten Entities keine `unit_of_measurement`-Attribute liefern. Die Helpers proxien Deine echte Hardware so, dass der Generic-Adapter ueber Domain + UoM matchen kann.

**Wichtig:** Der WR-Limit-Helper ist eine echte `number`-Entity, die per HA-Automation an Deinen Trucki-`input_number` durchschreibt. Damit fließt der Schreibbefehl real auf den WR — Closed-Loop-Readback ist also realistisch, nicht simuliert.

### 5.1 WR-Limit-Helper (Domain `number`, Suffix `_limit_nonpersistent_absolute`)

In HA `configuration.yaml` (oder via UI: Settings → Devices & Services → Helpers → "Number"):

```yaml
# configuration.yaml — Beispiel; UI-Helper-Variante ist äquivalent.
input_number:
  # Weiter-Verwendung des bestehenden Trucki-Set-Targets
  # (lassen wie es ist; Helper unten setzt es)

template:
  - sensor:
      - name: "Solalex Test WR AC Power"
        unique_id: solalex_test_wr_ac_power
        unit_of_measurement: "W"
        device_class: power
        state: "{{ states('sensor.t2sgf72a29_t2sgf72a29_output') }}"
```

Für den Schreibpfad **kannst Du nicht direkt einen Template-Sensor benutzen**. Der Generic-Inverter-Adapter erwartet eine schreibbare `number`- oder `input_number`-Entity und ruft passend dazu `number.set_value` oder `input_number.set_value` auf.

Sauberster Weg: ein **Number-Helper über die UI** oder ein **YAML-`number`-Helper über `template:`** mit `unit_of_measurement: "W"`:

```yaml
# configuration.yaml
template:
  - number:
      - name: "Solalex Test WR Limit Nonpersistent Absolute"
        unique_id: solalex_test_wr_limit_nonpersistent_absolute
        min: 2
        max: 1500
        step: 1
        unit_of_measurement: "W"
        state: "{{ states('input_number.t2sgf72a29_t2sgf72a29_set_target') | int(0) }}"
        set_value:
          - service: input_number.set_value
            target:
              entity_id: input_number.t2sgf72a29_t2sgf72a29_set_target
            data:
              value: "{{ value }}"
```

Erwartete Entity-ID nach HA-Restart/Reload: `number.solalex_test_wr_limit_nonpersistent_absolute` — matcht den Generic-Inverter-Adapter ueber Domain `number` + UoM `W`.

### 5.2 Smart-Meter-Helper (Domain `sensor`, uom `W`)

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Solalex Test Grid Power"
        unique_id: solalex_test_grid_power
        unit_of_measurement: "W"
        device_class: power
        # Smart-Meter-Vorzeichen passt bereits: neg=Einspeisung, pos=Bezug.
        # Generic-Meter erwartet das gleiche Vorzeichen — direkter Pass-through.
        state: "{{ states('sensor.00_smart_meter_sml_current_load') }}"
```

Erwartete Entity-ID: `sensor.solalex_test_grid_power` — matcht das Shelly-3EM-Pattern (`_power`-Suffix + uom `W`).

### 5.3 Verifikations-Schritte vor Smoke-Test-Start

1. HA → Developer Tools → States → nach `solalex_test_` filtern
2. Prüfen: drei Helper-Entities existieren mit Live-Werten
3. Prüfen: `number.solalex_test_wr_limit_nonpersistent_absolute` lässt sich über UI auf einen Wert (z. B. 100) setzen → Trucki-`input_number` aktualisiert sich → WR-Output verändert sich → Helper-Sensor `sensor.solalex_test_wr_ac_power` reflektiert den neuen Wert
4. Erst danach Solalex-UI neu laden — Auto-Detection läuft beim Page-Mount, nicht live

### 5.4 Was der Workaround NICHT abdeckt

- **Speicher-Modus / Akku-SoC:** kein Helper für Victron-SoC vorgesehen (Marstek-Adapter ist Smoke-Out-of-Scope). Falls Du Story 3.4 später testest, brauchst Du analog einen Marstek-konformen SoC-Helper.
- **Mehrere parallele Schreiber:** wenn HA-Automationen das `input_number` direkt setzen, springt der Solalex-Limit aus dem Tritt. Vor dem Test deaktivieren.

---

## 6. Anhang: nicht im Smoke-Scope

Bewusst ausgeklammert, weil noch nicht implementiert oder nicht relevant für „läufts an":

- Speicher-Modus / Akku-Pool-Regelung (Story 3.4 ready-for-dev, 3.5+ backlog)
- Hysterese-basierter Mode-Wechsel (3.5)
- Min/Max-SoC + Nacht-Entlade-Fenster Wirkungstest (3.6)
- Fail-Safe bei HA-WS-Disconnect (3.7)
- Diagnose-Tab + Letzte-100-Zyklen + Bug-Report-Export (Epic 4)
- Dashboard-Hero, Euro-Wert, Energy-Ring (Epic 5 ohne 5.1a)
- Lizenz-Flow / LemonSqueezy-Kauf (Epic 7)
- Auto-Update + Backup-Restore (Epic 6)
