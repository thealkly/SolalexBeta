# Soalex — Add-on Dokumentation

Diese Datei ist die offizielle In-HA-Dokumentation des Add-ons. Der HA-Supervisor
rendert sie im Add-on-Detail-View.

## Installation

1. **Einstellungen → Add-ons → Add-on-Store** öffnen.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/thealkly/SoalexBeta`
4. Nach dem Refresh erscheint **Soalex** in der Liste. **Installieren**.
5. Nach Start öffnet sich der Setup-Wizard im Ingress-Frame.

## Voraussetzungen

- **Home Assistant OS** (ausschließlich — siehe Abschnitt „Unterstützte
  HA-Versionen" für Details zu nicht unterstützten Varianten).
- Mindestens einen unterstützten Wechselrichter oder Akku im HA-Netzwerk.
- Gültige Soalex-Lizenz (wird im Wizard via LemonSqueezy gekauft).

## Unterstützte HA-Versionen

- **Minimum:** 2026.4.0 (im `addon/config.yaml` via `homeassistant:`-Feld
  gepinnt; niedrigere Versionen erhalten eine Install-Warning im Add-on-Store).
- **Getestet bis:** 2026.4.3 (aktuelle stable zum Release-Zeitpunkt).
- **Unterstützt:** ausschließlich **Home Assistant OS**.
- **Nicht unterstützt:** Home Assistant Supervised, Home Assistant Container,
  Home Assistant Core.

Du weißt nicht, welche Variante du hast? Öffne in HA:
**Einstellungen → System → Info**.

## Unterstützte Hardware (Day 1)

- **Wechselrichter:** Hoymiles / OpenDTU, Trucki, ESPHome, MQTT-bridged — Limit-Regelung für Nulleinspeisung (Generic-Adapter über HA-Capabilities).
- **Akku:** Marstek Venus, Zendure SolarFlow, SolakonONE, Anker Solix, Hoymiles MS A2, Growatt Noah — Lade-/Entlade-Steuerung (Generic-Battery-Adapter, Topologie automatisch erkannt).
- **Smart Meter:** Shelly 3EM, ESPHome SML, Tibber, MQTT-bridged — Einspeisungs-Messung (Generic-Adapter).

Vendor-spezifische Tuning-Profile (z. B. Hoymiles-Drossel-Deadband) folgen in v1.5.

## Ressourcen-Budget (Raspberry Pi 4 Referenz)

- **Idle-RSS Ziel:** ≤ 150 MB
- **Idle-CPU Ziel:** ≤ 2 %
- **Aktiver Regelzyklus:** kurze Peaks bis ~10 % CPU

### Messung (Story 1.1 Skeleton, lokal via Docker)

| Messgröße | Gemessen | Ziel | Status |
|---|---|---|---|
| Idle-RSS | 64.9 MiB | ≤ 150 MB | ✅ 43 % des Budgets |
| Idle-CPU | 0.49 % | ≤ 2 % | ✅ 25 % des Budgets |

> Gemessen auf Docker Desktop (macOS, Apple Silicon) mit dem amd64-Image
> via Rosetta-Emulation. Auf einem echten Pi 4 (aarch64 nativ) sind die
> Werte tendenziell niedriger. Finale Validation erfolgt in der Beta-Phase
> auf echter Pi-4-Hardware.

## Daten-Persistenz

Alle dauerhaften Daten (SQLite-DB, Lizenz, Logs, Backup-Slot) liegen unter
`/data/` und überleben Add-on-Restart sowie Update.

```
/data/
├── soalex.db         # Betriebsdaten (KPIs, Config, Audit)
├── license.json       # Lizenz-Check-Response
├── logs/
│   └── soalex.log    # JSON-Zeilen, 10 MB × 5 Rotation
└── .backup/
    └── soalex.db     # 1-Slot-Backup vor jedem Update
```

## Keine externen Ports

Soalex kommuniziert ausschließlich über den Home-Assistant-Ingress-Proxy.
Es gibt keine externen Port-Expositionen. Dies ist eine harte Policy
(AC 7 Story 1.1, NFR28) und wird im `addon/config.yaml` via `ports: {}`
durchgesetzt.

## Akku-Regelung — wie Soalex misst und einstellt

Soalex regelt deinen Akku mit einem PI-Regler. Beim ersten Setup misst der Wizard
einmal die Reaktion deiner Anlage (Sprungantwort gegen den Smart Meter) und
leitet daraus passende Tuning-Werte ab — Reaktionsstärke (Kp), Restausgleich (Ti),
Totzeit (Tp) und Trägheit (Td). Die Werte stehen jederzeit unter
**Einstellungen → Verhalten → Akku → System-Reaktion**: dort siehst du die
gemessenen Zahlen, wann zuletzt gemessen wurde, und kannst die Reaktion neu
vermessen lassen — etwa nach einem Akku-Wechsel oder einer geänderten Smart-Meter-
Position. Wenn keine Messung vorliegt, regelt Soalex mit einem konservativen
Default (Kp = 0,5 / Ti = 5 s).

## Cloud-Akkus (Anker Solix & Co)

Akkus, die ihre Steuerbefehle über die Hersteller-Cloud verarbeiten — Anker Solix
Solarbank ist der typische Vertreter — haben eine Reaktionszeit von rund 30 s
(Roundtrip Home Assistant → Cloud → Akku → Smart Meter). Das ist deutlich länger
als bei lokalen Akkus (Marstek Venus, Zendure SolarFlow, SolakonONE liegen bei
1–3 s). Soalex erkennt das automatisch beim Reaktionstest und schlägt dir eine
passende **Wartezeit zwischen Anpassungen** vor. Die Empfehlung erscheint als
„Empfohlene Wartezeit: X s" mit einem **Übernehmen**-Button in der System-
Reaktion-Karte; ohne Klick passiert nichts. Bei einer gemessenen Reaktionszeit
über 15 s bekommt die Karte zusätzlich einen Cloud-Hinweis: schnellere Settings
würden bei Cloud-Akkus zu Überschwingern beim Last-Wegfall führen, weil der Regler
zwischen zwei Schreibvorgängen unbemerkt aufintegrieren würde. Soalex friert den
Integrator deshalb für die Dauer der Wartezeit ein — sichtbar im Live-Stream als
Detail-Zeile „Wartet auf Hardware".

## Haushalts-Regeln (Zusammenspiel mehrerer Geräte)

Unter **Einstellungen → Verhalten → Haushalts-Regeln** liegen alle Regeln, die
nicht für einen einzelnen Akku gelten, sondern für deine ganze Anlage. Jede
Regel ist unabhängig ein- oder ausschaltbar, gilt für alle Akkus gemeinsam
und speichert sich sofort beim Ändern (kein Speichern-Button).

- **Wann darf entladen werden?** Ein tägliches Zeitfenster (Von/Bis), in dem
  deine Akkus überhaupt entladen dürfen — z. B. um nachts einen Mindest-
  Ladestand als Blackout-Puffer zu behalten. Standard: der ganze Tag.
- **Akku nicht entladen, während die Wallbox lädt.** Wählst du den Lade-
  Sensor deiner Wallbox bzw. den Ladepunkt-Status von EVCC, hält Soalex den
  Akku zurück, solange das Auto lädt — der Akku-Strom soll nicht den Umweg
  über die Wallbox nehmen. Laden und Nulleinspeisung laufen normal weiter.
  Für EVCC empfiehlt sich der Status-Sensor mit Wert „C" (lädt), nicht der
  „freigegeben"-Schalter. Über „Sensor nicht dabei? Alle anzeigen" findest du
  auch `binary_sensor`-/`input_boolean`-Entitäten, falls dein Wallbox-Sensor
  dort liegt.
- **Zweiter Haus-Akku mit eigener Regelung.** Für Setups mit einem
  zusätzlichen, großen Haus-Akku, der seine eigene Nulleinspeisung macht
  (z. B. Huawei, Fronius, Sonnen, E3/DC): Soalex lädt nicht, während der
  Haus-Akku entlädt, und entlädt nicht, während der Haus-Akku lädt — so
  schiebt kein Akku Strom in den anderen (teure Doppel-Wandlung). Dafür den
  Leistungssensor des Haus-Akkus wählen (positiv = entlädt); zeigt dein
  Sensor es andersherum, hilft die „Vorzeichen umkehren"-Checkbox. Reagiert
  der Sensor länger nicht (z. B. `unavailable`), fällt die Regel bewusst
  „offen" zurück statt zu blockieren — Soalex regelt dann normal weiter,
  statt eine Nacht lang stillzustehen.
- **Überschuss an andere Akkus weitergeben.** Ist ein Akku voll und es ginge
  trotzdem Strom ins Netz, gibt Soalex den Überschuss an deine noch leeren
  Akkus weiter, statt ihn einzuspeisen — die Akkus laden sich gegenseitig.
  Nur relevant mit mehr als einem Akku, standardmäßig aus.
- **Überschuss nutzen statt einspeisen** *(Experimentell)*. Ist dein Akku
  voll und es ginge trotzdem Strom ins Netz, kann Soalex stattdessen ein
  gewähltes Gerät einschalten (z. B. eine Klimaanlage), damit der Überschuss
  im Haus bleibt. Fällt der Überschuss weg oder ist der Akku nicht mehr
  voll, schaltet Soalex wieder aus. Bewusst zurückhaltend gehalten —
  Feedback willkommen.

## Robustheit

- **Closed-Loop-Readback:** Jeder Steuerbefehl an die Hardware wird nach
  dem Senden aus Home Assistant zurückgelesen. Stimmen Soll- und Ist-Wert
  nicht überein, schlägt der Cycle fehl und der Audit-Trail im Live-Tab
  zeigt den Grund.
- **Sensor-Verfügbarkeits-Guard:** Bevor Soalex einen Wert schreibt,
  prüft es, ob der Readback-Sensor in Home Assistant gerade einen Wert
  liefert. Ist der Sensor `unavailable` / `unknown` (z. B. Marstek-Modbus
  zwischen zwei Polls), überspringt Soalex den Schreibvorgang und
  schreibt eine Audit-Zeile „Sensor nicht verfügbar". Das verhindert
  blinde Schreibversuche und reduziert Log-Rauschen in HA. Notfall-Bypass
  für Hardware ohne sinnvollen Availability-State: in der DB für das
  betreffende Device `config_json["skip_readback_availability_check"] =
  true` setzen — kein UI in v1.
- **Rate-Limit pro Gerät:** Standard 30 s Mindestabstand zwischen
  Schreibvorgängen pro WR/Akku (lokale Akkus 2 s), persistent in der DB
  (überlebt Restart).
- **Rückmeldungs-Modus pro Gerät:** Die Rückmeldungs-Prüfung lässt sich
  pro Wechselrichter und pro Akku auf drei Stufen einstellen
  (Einstellungen → Verhalten → Profi-Einstellungen):
  - *Mit Rückmeldung* (Standard) — Soalex prüft nach jedem Befehl den
    Leistungs- bzw. Echo-Sensor. Empfohlen für getestete Hardware.
  - *Nur Soll-Wert-Echo* — Soalex prüft nur, ob die Soll-Wert-Zahl
    übernommen wurde, nicht die tatsächliche Leistung. Sinnvoll für
    Akkus mit langsamem oder grob gerundetem Leistungs-Sensor
    (SolakonONE, Anker Solix, Zendure-Cloud): deren Sensor meldet
    minutenlang denselben Wert und löste sonst einen falschen
    Sicherheits-Stopp aus.
  - *Ohne Rückmeldung* — Soalex prüft **nicht**, ob die Hardware den
    Befehl tatsächlich ausführt. Nur wählen, wenn die Hardware keinen
    brauchbaren Leistungs- oder Rückmelde-Sensor hat. Was wegfällt:
    keine Bestätigung, dass der Befehl ankam, und (ohne hinterlegten
    Leistungs-Sensor) auch kein „Vermutlich Akku leer/voll"-Schutz.
    Was bleibt: Schreibpause, Hardware-Grenzen und der Verbindungs-
    Fail-Safe greifen weiterhin. Diese Stufe ist bewusst hinter eine
    Bestätigungs-Checkbox gelegt. Empfehlung: nach Möglichkeit einen
    Leistungs-Sensor unter „Hardware" hinterlegen — dann fängt der
    verzögerte Effektivitäts-Schutz auch hier eine tote Hardware ab.

## Soalex Status in Home Assistant

Nach dem Setup-Wizard legt Soalex acht Input-Helper in Home Assistant an,
die den internen Steuer-Status jederzeit per HA-Card oder Statistik-Graph
sichtbar machen. Sie liegen unter **Einstellungen → Geräte & Dienste →
Helfer** mit dem Filter `soalex_*`.

| Entity | Typ | Bedeutung |
| --- | --- | --- |
| `input_text.soalex_active_mode` | input_text | Aktuell aktiver Modus: `drossel`, `speicher`, `multi`, `export`, `paused`, `fail_safe`, `unknown` |
| `input_text.soalex_last_cycle_reason` | input_text | Letzter Cycle-Reason aus dem Audit-Trail (z. B. `noop: deadband`, `dispatched`, `fail_safe: range_check_violation`) |
| `input_text.soalex_last_command_at` | input_text | UTC-ISO-8601-Zeitstempel des letzten Schreibvorgangs |
| `input_text.soalex_fail_safe_state` | input_text | `inactive` (alles ok), `active_hold` (Fail-Safe greift), `active_release` (Erholung gerade aktiv) |
| `input_number.soalex_cycle_age_seconds` | input_number (`state_class=measurement`) | Sekunden seit dem letzten Cycle (0 = gerade jetzt; > 60 = Controller hängt) |
| `input_number.soalex_recent_cycles_count` | input_number (`state_class=measurement`) | Anzahl Cycles in der letzten Stunde |
| `input_number.soalex_fail_safes_today` | input_number (`state_class=measurement`) | Anzahl Fail-Safe-Events seit lokal-Mitternacht |
| `input_number.soalex_mode_switches_today` | input_number (`state_class=measurement`) | Anzahl Mode-Wechsel (z. B. DROSSEL → SPEICHER) seit lokal-Mitternacht |

**Update-Verhalten:** Soalex aktualisiert die Helper nach jedem Cycle, gedrosselt auf max. 1 Update pro Helper pro 30 s. Bei Mode-Wechsel, Fail-Safe-Übergang oder Wechsel des Reason-Prefixes wird der Update sofort durchgereicht.

**Tages-Counter:** `fail_safes_today` und `mode_switches_today` sind in-memory; sie resetten bei lokal-Mitternacht und beim Add-on-Restart. Den vollständigen Tagesverlauf hält der HA-Recorder via `state_class: measurement` — Mid-Day-Restarts erscheinen als Sprung-zu-0 + Wieder-Anstieg.

**Helper manuell gelöscht?** Soalex schreibt eine Warnung ins Log (`status_helper_publish_failed`) und macht weiter — die Steuerung ist davon nicht betroffen. Den Helper kannst du wieder anlegen, indem du den Wizard erneut durchläufst (Geräte → Reset → Wizard → Aktivieren).

### Diagnose-Endpoint `/api/v1/diagnostics/devices`

Für tiefere QA-Inspektion liefert das Add-on über die Ingress-API einen direkten Snapshot pro angelegtem Device. Beispiel-Response:

```json
{
  "devices": [
    {
      "id": 1,
      "type": "generic_battery",
      "role": "wr_charge",
      "entity_id": "number.akku_charge",
      "adapter_key": "generic_battery",
      "topology": "multi_entity",
      "battery_control": { "topology": "multi_entity", "discharge_setpoint_entity": "...", "...": "..." },
      "wizard_completed": true,
      "last_write_at": "2026-05-04T03:42:11Z",
      "last_cycle_reason": "dispatched",
      "writes_24h": 2881,
      "fail_safes_24h": 0,
      "noops_24h": 84219,
      "noop_reason_top3": [
        { "reason": "noop: deadband", "count": 45112 },
        { "reason": "noop: rate_limited", "count": 23001 },
        { "reason": "noop: wr_limit_state_cache_miss", "count": 16106 }
      ]
    }
  ],
  "generated_at": "2026-05-04T05:50:00Z"
}
```

`window_h` (Query-Parameter, Default 24, Max 168) wählt das Aggregat-Fenster. Der Endpoint ist auf p99 ≤ 200 ms ausgelegt (4 Devices × 100 000 Cycles).

## Support & Issues

- **Bug-Reports:** Über den Diagnose-Tab des Add-ons (ab Epic 4).
  Bis dahin: [GitHub Issues](https://github.com/thealkly/SoalexBeta/issues).
- **Kontakt:** info@alkly.de

---

Soalex — ein **Alex Kly** Produkt.
