# Solalex — Manueller Smoke-Test (GUI im HA-Ingress)

**Zweck.** Nachweisen, dass das Add-on nach einem Update grundsätzlich startet, der Setup-Walkthrough vom Disclaimer bis zum Live-Betrieb komplett durchläuft, und der Live-Betriebs-View Polling/Chart/Zyklen-Liste anzeigt. Kein vollständiger Funktions-Test — nur "rauchts oder läufts an?".

**Dauer:** ~10–15 min bei grünem Pfad.
**Letzte Aktualisierung:** 2026-04-25 (Sprint-Stand: Epic 1+2 done, 3.1–3.3 done, 5.1a done).

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

### 1.2 ⚠ Compat-Vor-Befund (vor erstem Klick lesen)

Die obigen Entities **matchen die aktuelle Auto-Detection nicht**. Konkret im Code:

| Adapter | Detection-Pattern | Deine Entity bricht weil … |
|---|---|---|
| `hoymiles` ([adapters/hoymiles.py:28](backend/src/solalex/adapters/hoymiles.py#L28)) | `^number\..+_limit_nonpersistent_absolute$` | Domain ist `input_number` und Suffix ist `_set_target` |
| `shelly_3em` ([adapters/shelly_3em.py:26](backend/src/solalex/adapters/shelly_3em.py#L26)) | `^sensor\..+_(total_)?power$` + uom ∈ {W, kW} | Suffix ist `_current_load`, nicht `_power`/`_total_power` |

**Erwartung:** Im Config-Dropdown wirst Du Deine Trucki-Limit-Entity und Deine ESPHome-Smart-Meter-Entity **nicht** sehen. Das ist **kein Bug**, sondern der erwartete Test-Befund — Deine Hardware ist Compat-Fall für den **Generic-HA-Entity-Adapter (v1.5, Backlog)**.

**Vorgehensweise:**
- **Variante A (ehrlicher Smoke):** Test wie vorgesehen durchführen, ST-02 dokumentiert den Block — Smoke gilt als „bestanden bis ST-02, danach blockiert durch fehlende Hardware-Compat". Konkrete Story-Implikation: Generic-HA-Adapter aus v1.5 wird zur Beta-Voraussetzung für Setups wie Deins.
- **Variante B (End-zu-End-Walkthrough mit Workaround):** Vor Testbeginn HA-Template-Helpers anlegen, die die Patterns erfüllen — siehe [Anhang §5](#5-anhang-workaround-template-helpers-für-variante-b). Dann läuft der komplette Walkthrough durch, allerdings indirekt über Helpers.

### 1.3 Vorbedingungen vor Testbeginn

- [ ] Variante A oder B festgelegt (s. §1.2)
- [ ] Falls Variante B: HA-Template-Helpers nach §6 angelegt und im Developer-Tools `state` der Helper-Entities verifiziert
- [ ] HA-Sidebar zeigt Solalex-Eintrag
- [ ] Im HA-Add-on-Store ist die neueste Solalex-Version installiert (siehe ST-00)
- [ ] Es laufen **keine** parallelen HA-Automationen, die `input_number.t2sgf72a29_t2sgf72a29_set_target` schreiben (sonst kollidiert der Closed-Loop-Readback im Funktionstest)

### 1.4 Abbruch-Kriterien (Test sofort stoppen)

- Add-on-Container crasht / restartet im Loop
- HA-Ingress liefert leere Seite / 502 / weißen Bildschirm > 10 s
- Browser-Console zeigt unbehandelte JS-Errors (rote Einträge)
- Funktionstest sendet einen Limit-Wert > 1500 W an den Trucki-Stick (Hoymiles `get_limit_range` ist auf `(2, 1500)` W konfiguriert — alles drüber wäre ein echter Range-Check-Bug)

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

**Vorbedingung:** Route `#/config` ist offen. Vorgehen je nach Variante (siehe §1.2):
- **Variante A:** Du erwartest, dass Trucki/ESPHome im Dropdown fehlen.
- **Variante B:** Helper aus §6 sind angelegt — die Helper-Entities sollten erscheinen.

| # | Schritt | Erwartung Variante A (ohne Workaround) | Erwartung Variante B (mit Helpers) | ☐ |
|---|---|---|---|---|
| 1 | Seite initial | Skeleton-Pulse für ≥ 400 ms, dann Header "Hardware konfigurieren" | (gleich) | ☐ |
| 2 | Sektion "Hardware-Typ" sichtbar | Zwei Tiles: "Hoymiles / OpenDTU (Drossel-Modus)" und "Marstek Venus 3E/D (Speicher-Modus)" + Hinweis "Anker Solix und generische HA-Entities folgen mit v1.5" | (gleich) | ☐ |
| 3 | Tile **"Hoymiles / OpenDTU"** klicken | Tile-Border wechselt auf Akzentfarbe, Sektion "Wechselrichter-Limit-Entity" wird gerendert | (gleich) | ☐ |
| 4 | Dropdown "— Entity wählen —" öffnen | **Liste leer** oder zeigt Hinweis „Keine passenden Entities gefunden. Prüfe deine HA-Integration und lade die Seite neu." → ✅ erwarteter Befund, ST-02 ist hier blockiert. **Stop und §3 ausfüllen.** | Helper `number.solalex_test_wr_limit_nonpersistent_absolute` ist gelistet → auswählen | ☐ |
| 5 | Checkbox "Smart Meter (Shelly 3EM) zuordnen" anhaken | Variante A endet hier, kein Save-Button erscheint, weil Pflichtfeld WR-Limit unbefüllt — Befund notieren | Zweites Dropdown "Netz-Leistungs-Entity" mit Helper `sensor.solalex_test_grid_power` (uom=W) | ☐ |
| 6 | Helper-Smart-Meter-Entity wählen | n/a | Eintrag wird gewählt | ☐ |
| 7 | Button "Speichern" wird sichtbar | n/a | Klick → "Speichern…"-State, dann Navigation zu `#/functional-test` | ☐ |

**Variante A — was im Befund-Protokoll (§3) stehen muss:**
- Test-ID: `ST-02`
- Befund: „WR-Limit-Dropdown leer mit echter Trucki-Hardware (`input_number.t2sgf72a29_t2sgf72a29_set_target`); Smart-Meter-Dropdown leer mit ESPHome-SML (`sensor.00_smart_meter_sml_current_load`). Auto-Detection-Patterns matchen nicht — siehe [adapters/hoymiles.py:28](backend/src/solalex/adapters/hoymiles.py#L28) und [adapters/shelly_3em.py:26](backend/src/solalex/adapters/shelly_3em.py#L26)."
- Schwere: `block` für reale Beta-Tester mit nicht-Day-1-Hardware → Generic-HA-Entity-Adapter (v1.5) wird zur Beta-Voraussetzung
- Nächster Schritt: entweder Variante B aktivieren oder Test hier abschließen

---

### ST-03 — Funktionstest mit Closed-Loop-Readback

**⚠ Achtung:** Dieser Test sendet einen **realen Schreibbefehl** an Deinen Trucki/Hoymiles-WR. Zeitpunkt so wählen, dass eine kurzzeitige Limit-Änderung am WR keine Probleme macht (kein laufender Eigenverbrauch-kritischer Vorgang).

**Vorbedingung:** Route `#/functional-test`, Hardware ist gespeichert.

| # | Schritt | Erwartung | ☐ |
|---|---|---|---|
| 1 | Seite öffnet | Header "Funktionstest", Karte "Zielhardware" zeigt "Hoymiles / OpenDTU" + Liste der konfigurierten Entities mit Role-Tag | ☐ |
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

### Variante A (ohne Workaround) — Pass-Definition

Erwartet ist **Teil-Bestehen**: ST-00 + ST-01 grün, ST-02 dokumentiert den Compat-Block.

- [ ] ST-00, ST-01: alle Schritte abgehakt, keine Console-Errors
- [ ] ST-02 zeigt erwartetes Verhalten (leeres WR-Limit-Dropdown bei Trucki, leeres Smart-Meter-Dropdown bei ESPHome) und der Befund ist in §3 mit Schwere `block` (Beta-Compat) eingetragen
- [ ] Add-on-Container läuft stabil weiter, keine Tracebacks im Log

→ **Build ist „smoke-grün bis zur erwarteten HW-Compat-Grenze"**. Inhaltliche Folge: Generic-HA-Adapter (v1.5) zwingend für Beta-Tester mit Nicht-Day-1-Hardware.

### Variante B (mit Template-Helpers) — Pass-Definition

Erwartet ist **End-zu-End-Bestehen**.

- [ ] ST-00 bis ST-05: alle Schritte abgehakt, kein roter Bildschirm, keine Console-Errors
- [ ] Funktionstest hat über die Helper-Brücke ein `passed` mit echtem WR-Output-Schwenk ergeben (real geschriebener Limit-Wert + Readback-Mismatch < Toleranz)
- [ ] Live-Betriebs-View hat ≥ 1 echten Regelzyklus aufgezeichnet
- [ ] Polling läuft stabil über mindestens 60 s ohne Drop
- [ ] Add-on-Log nach Smoke-Test ist frei von Tracebacks

→ **Build ist „smoke-grün end-to-end"**. Vollständige Test-Suiten (Drossel-Stress, Rate-Limit, Idle/Drossel-Wechsel, Failover) folgen separat.

---

## 5. Anhang: Workaround Template-Helpers für Variante B

Nur lesen, wenn Du den End-zu-End-Walkthrough trotz fehlender Auto-Detection-Compat durchspielen willst. Die Helpers proxien Deine echte Hardware so, dass die Adapter-Patterns greifen.

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

Für den Schreibpfad **kannst Du nicht direkt einen Template-Sensor benutzen** (Hoymiles-Adapter erwartet Domain `number` zum Schreiben — siehe [adapters/hoymiles.py:49-53](backend/src/solalex/adapters/hoymiles.py#L49-L53), `service_data={"entity_id": …, "value": watts}` über `number.set_value`).

Sauberster Weg: ein **Number-Helper über die UI** anlegen mit ID, die das Pattern erfüllt. Da HA UI-Helper standardmäßig die Domain `input_number` vergeben, brauchst Du stattdessen einen **YAML-`number`-Helper über `template:`**:

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

Erwartete Entity-ID nach HA-Restart/Reload: `number.solalex_test_wr_limit_nonpersistent_absolute` — matcht das Hoymiles-Pattern.

### 5.2 Smart-Meter-Helper (Domain `sensor`, Suffix `_power`, uom `W`)

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Solalex Test Grid Power"
        unique_id: solalex_test_grid_power
        unit_of_measurement: "W"
        device_class: power
        # Smart-Meter-Vorzeichen passt bereits: neg=Einspeisung, pos=Bezug.
        # Shelly-Adapter erwartet das gleiche Vorzeichen — direkter Pass-through.
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
