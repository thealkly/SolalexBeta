# Soalex

**Sekundengenaue aktive Nulleinspeisung und Akku-Pool-Steuerung als Home-Assistant-Add-on.**

Soalex steuert Wechselrichter und Akkus sekundengenau über die Home-Assistant-WebSocket-API.
100 % lokal, keine Telemetry, kein Cloud-Zwang — nur der monatliche Lizenz-Check verlässt
Dein Netz.

> **Status:** Beta. Aktive Erprobung mit ausgewählten Beta-Tester:innen.

## Was ist neu?

Die vollständige Versionshistorie mit allen Details steht im
**[Changelog](./addon/CHANGELOG.md)**. Hier die Kurzfassung der letzten Releases:

- **0.1.174** — Koordination mit einem zweiten, unabhängigen Haus-Akku (Huawei,
  Fronius, Sonnen, E3/DC & Co.), Akkus laden sich jetzt gegenseitig statt
  Überschuss einzuspeisen, kein „Speichern"-Button mehr in den Einstellungen
  (alles speichert sofort), Fix für einen nicht mehr reagierenden Akku im
  Mehr-Akku-Betrieb.
- **0.1.173** — Reine PV-Wechselrichter (nur Ausgangsleistung steuerbar, z. B.
  Trucki2Shelly) laufen über den ruhigen Akku-Steuerpfad statt über einen
  eigenen Wechselrichter-Regler; experimenteller Überschuss-Verbraucher
  (schaltet z. B. eine Klimaanlage statt einzuspeisen); spürbar ruhigerer
  Mehr-Akku-Betrieb.
- **0.1.172** — Entladesperre bei Wallbox-/EVCC-Ladung: Soalex entlädt deinen
  Akku nicht mehr, während dein Auto lädt.

Ältere Versionen (Multi-Akku-Einführung, SoC-loses Steuern, Zero-Tuning-Reaktionstest
u. v. m.) stehen ebenfalls im [Changelog](./addon/CHANGELOG.md).

## Installation

Voraussetzung: **Home Assistant OS** auf `amd64` oder `aarch64`. Andere HA-Varianten
(Supervised, Container, Core) werden in der Beta nicht unterstützt.

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store**.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/thealkly/SoalexBeta`
4. Nach dem Refresh erscheint **Soalex** in der Add-on-Liste.
5. **Installieren**, dann starten. Nach dem Start öffnet sich der Setup-Wizard im
   Home-Assistant-Ingress-Frame.

**Update:** Einstellungen → Add-ons → Soalex → **Update**, sobald eine neue Version
angeboten wird — läuft ohne erneuten Wizard-Durchlauf, deine Konfiguration bleibt
erhalten.

**Beta-Laufzeit:** jede Beta-Version ist ab dem Build-Zeitpunkt 30 Tage lang aktiv.
Ab 7 Tagen vor Ablauf zeigt der Live-Screen einen Hinweis-Banner, danach einen
deutlichen „Beta-Phase beendet"-Banner und die Steuerung pausiert, bis du auf die
nächste Version updatest. Kein Datenverlust, keine Neueinrichtung nötig — einfach
updaten.

## Was Soalex kann

### Nulleinspeisung & Akku-Steuerung

Soalex hält deine Einspeisung sekundengenau auf null (oder auf einen von dir
gewählten kleinen Toleranz-Wert) und lädt/entlädt deinen Akku passend zum
gerade verfügbaren Überschuss bzw. Bezug. Die Reaktionsgeschwindigkeit deiner
Hardware wird beim Einrichten einmal automatisch gemessen (Zero-Tuning) — du
musst nichts von Hand einstellen. Jeder Schreibbefehl wird per Closed-Loop-
Readback verifiziert, bevor der nächste Zyklus läuft.

### Mehrere Akkus gleichzeitig (Multi-Akku)

Hast du mehr als einen Akku, verwaltet Soalex alle als gemeinsamen Pool: Laden
und Entladen wird sinnvoll über alle Akkus verteilt, jeder Akku lässt sich
einzeln einrichten, ändern oder nachträglich hinzufügen. Ein nicht mehr
reagierender Akku (z. B. wegen einer toten Verbindung) bekommt seinen Anteil
entzogen — der Rest des Pools regelt normal weiter.

### Ohne Ladestand-Sensor (SoC-los)

Hat dein Akku-Setup keinen auslesbaren Ladestand (z. B. eine CAN-/BMS-Bridge
ohne SoC-Wert), kann Soalex trotzdem regeln — über die Leistung; „voll" und
„leer" erkennt dann die Hardware selbst.

### Haushalts-Regeln (Zusammenspiel mehrerer Geräte)

Unter **Einstellungen → Verhalten → Haushalts-Regeln** liegen Regeln, die für
deine ganze Anlage gelten statt für einen einzelnen Akku. Jede ist unabhängig
ein-/ausschaltbar und speichert sofort beim Ändern:

- **Wann darf entladen werden?** Tägliches Zeitfenster (Von/Bis), in dem deine
  Akkus überhaupt entladen dürfen — z. B. für einen nächtlichen Blackout-Puffer.
- **Akku nicht entladen, während die Wallbox lädt.** Lade-Sensor deiner Wallbox
  bzw. Ladepunkt-Status von EVCC hinterlegen — Soalex hält den Akku zurück,
  solange das Auto lädt. Laden und Nulleinspeisung laufen normal weiter.
- **Zweiter Haus-Akku mit eigener Regelung.** Für Setups mit einem
  zusätzlichen, großen Haus-Akku mit eigener Nulleinspeisung (Huawei, Fronius,
  Sonnen, E3/DC): Leistungssensor des Haus-Akkus wählen, Soalex lädt/entlädt
  dann nie gegen ihn.
- **Überschuss an andere Akkus weitergeben.** Ist ein Akku voll und es ginge
  trotzdem Strom ins Netz, gibt Soalex den Überschuss an deine noch leeren
  Akkus weiter.
- **Überschuss nutzen statt einspeisen** *(experimentell)*. Schaltet ein
  gewähltes Gerät (z. B. eine Klimaanlage) ein, statt Überschuss einzuspeisen.

Ausführliche Erklärung jeder Regel: [addon/DOCS.md](./addon/DOCS.md#haushalts-regeln-zusammenspiel-mehrerer-geräte).

### Diagnose & Support

Acht Home-Assistant-Helfer (`input_text.soalex_*` / `input_number.soalex_*`)
zeigen den internen Status jederzeit als Karte oder Statistik-Graph. Über den
Diagnose-Tab im Add-on lässt sich ein vollständiges Diagnose-Bundle (DB-Snapshot,
Laufzeit-Zustand, Logs) exportieren — das ist der schnellste Weg zu Beta-Support.

## Unterstützte Hardware (Day 1)

- **Wechselrichter:** Hoymiles / OpenDTU, Trucki, ESPHome, MQTT-bridged (Generic-Adapter
  über HA-Capabilities — Domain + `unit_of_measurement`)
- **Akku:** Marstek Venus, Zendure SolarFlow, SolakonONE, Anker Solix, Hoymiles MS A2,
  Growatt Noah (Generic-Battery-Adapter — Topologie automatisch erkannt)
- **Smart Meter:** Shelly 3EM, ESPHome SML, Tibber, MQTT-bridged (Generic-Adapter)

Vendor-spezifische Tuning-Profile (z. B. Hoymiles-Drossel-Deadband) sind für
Folge-Releases geplant.

## Sicherheits- und Datenschutz-Grundsätze

- **100 % lokal:** keine Cloud-Roundtrips für Steuerung oder Monitoring.
- **Closed-Loop-Readback:** jeder Schreib-Befehl an die Hardware wird verifiziert,
  bevor der nächste Zyklus läuft.
- **Rate-Limit + Fail-Safe:** persistierte Schreib-Limits pro Gerät; bei
  Kommunikations-Ausfall hält Soalex das letzte bekannte Limit, statt freizugeben.
- **Egress-Whitelist:** nur `*.lemonsqueezy.com` für den monatlichen Lizenz-Check;
  alles andere wird im Build per CI-Test geblockt.

## Weiterführende Dokumentation

- **[Changelog](./addon/CHANGELOG.md)** — vollständige Versionshistorie.
- **[DOCS.md](./addon/DOCS.md)** — ausführliche Nutzungs-Doku: Installation,
  unterstützte HA-Versionen, Ressourcen-Budget, Daten-Persistenz, Akku-Regelung
  im Detail, Cloud-Akkus, Haushalts-Regeln, Robustheit/Fail-Safes, Status-Helper
  in Home Assistant.

## Lizenz

Proprietär — siehe [LICENSE](LICENSE). Source ist zur Auditierbarkeit offen, aber
nicht freie Software.

## Kontakt & Support

Alex Kly — info@alkly.de
