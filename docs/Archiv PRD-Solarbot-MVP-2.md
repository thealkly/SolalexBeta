# Product Requirements Document: Solarbot MVP

## by ALKLY

**Version:** 1.3
**Status:** Architektur festgelegt — bereit für Build
**Erstellt:** 25. März 2026
**Aktualisiert:** 10. April 2026 (Add-on-Architektur committed)
**Autor:** Alex Kly / ALKLY

---

## Glossar (Verbindliche Begriffe)

| Begriff | Bedeutung |
|---------|-----------|
| **Akku** | Batteriespeicher (nicht "Speicher" oder "Batterie") |
| **Wechselrichter (WR)** | Bei Erstnennung ausgeschrieben, danach WR |
| **Smart Meter** | Zähler/Messgerät am Hausanschluss |
| **Setup-Wizard** | Die geführte Erstkonfiguration |
| **Solarbot** | Produktname (immer kapitalisiert) |
| **Add-on** | HA Add-on (= "App" seit HA 2026.2) — eigenständiger Docker-Container neben HA |
| **Kaskade** | Das V2-Priorisierungsmodell |

---

## Product Overview

**App Name:** Solarbot
**Brand:** ALKLY (alkly.de)
**Tagline:** Steuert deinen PV-Überschuss lokal und sekundengenau über Home Assistant. Ohne Cloud, ohne YAML.
**Launch Goal:** 100 aktive Nutzer + NPS > 8 innerhalb von 30 Tagen nach Launch
**Target Launch:** 9 Wochen total (Spike Woche 0 + Build Wochen 1-6 + Launch Wochen 7-8)

### Einordnung in die ALKLY Produktwelt

| Stufe | Produkt | Preis | Funktion |
|-------|---------|-------|----------|
| 1 | YouTube / Newsletter / Quiz | Kostenlos | Reichweite, Vertrauen |
| 2 | Nulleinspeisungs-Blueprint | 19,99 EUR | Einstieg, Problemlösung |
| 3 | **Solarbot** | **TBD** | **Upgrade vom Blueprint, volle Steuerung** |
| 4 | Setup-Booster (Zoom 1:1) | 99 EUR | Premium-Support |
| 5 | ESPHome Meisterkurs | 149 EUR | Weiterbildung |
| 6 | Macherwerkstatt Live | 29 EUR/Monat | Community, Live-Calls |

### ALKLY Produkt-Test (Drei Hürden)

| Hürde | Solarbot | Status |
|-------|----------|--------|
| Lokaler Betrieb | Läuft komplett im HA Add-on Container, kein Internet nötig | Bestanden |
| Datenhoheit | Keine Daten verlassen das lokale Netzwerk (außer Lizenz-Aktivierung) | Bestanden |
| Lokale Interfaces | Eigene Web-UI im HA-Panel (Ingress), keine Hersteller-App nötig | Bestanden |

---

## Architektur-Entscheidung: Home Assistant Add-on

Solarbot wird als **Home Assistant Add-on** gebaut, nicht als Custom Integration. Diese Entscheidung wurde am 10. April 2026 getroffen (siehe Solarbot-Architecture-Spike.md für die Hintergründe).

### Warum Add-on

| Vorteil | Bedeutung für Solarbot |
|---------|------------------------|
| **Crash-Isolation** | Wenn Anker Cloud-API hängt oder Solarbot crasht, läuft HA weiter. Kritisch für ein kommerzielles Produkt. |
| **Lizenzierung** | Container-Isolation macht kommerzielle Modelle praktikabler. Community akzeptiert kommerzielle Add-ons besser als kommerzielle Integrationen. |
| **Saubere Updates** | Add-on-Updates ohne HA-Neustart in 10 Sekunden, statt 1-2 Min HA-Reboot. |
| **Volle Python-Umgebung** | Beliebige Libraries und Versionen, eigene C-Extensions möglich, unabhängig von HA-Core-Versionen. |
| **Eigene Datenbank** | `/data`-Ordner für Diagnose-Logs, Regelungs-Historie, Lizenz-Cache. |
| **UI-Freiheit** | FastAPI + Svelte + Tailwind ohne HA-Restriktionen. Volle Design-Kontrolle. |
| **Saubere Diagnose-Logs** | Eigener Log-Tab im Add-on-Bereich. Wichtig für Bug-Reports und Support. |

### Nachteile und wie wir damit umgehen

**1. Nur HA OS und HA Supervised**
Add-ons brauchen den HA Supervisor. Nutzer mit HA Container oder HA Core (geschätzt 10-15% der Gesamtbasis) können Solarbot nicht installieren.

*Mitigation:* Auf der Landing Page klar kommunizieren. In V2 evaluieren ob eine reduzierte "Solarbot Lite" Custom Integration für diese Gruppe Sinn ergibt.

**2. Installation hat einen Schritt mehr als HACS**
Nutzer müssen das Custom Repository im Add-on Store hinzufügen, statt in HACS.

*Mitigation:* 90-Sekunden YouTube-Anleitung, Screenshots in der README, Discord-Support für die ersten Wochen.

**3. Keine nativen HA-Entities im MVP**
Solarbot stellt im MVP keine HA-Sensoren bereit. Nutzer können Solarbot-Daten nicht direkt in Lovelace-Karten oder Automationen verwenden.

*Mitigation:* Alle wichtigen Daten und Steuerungen sind in der Solarbot-eigenen UI sichtbar. **In V1.5 wird MQTT Discovery evaluiert**, sodass Solarbot optional HA-Entities bereitstellt — wenn der Nutzer einen MQTT-Broker hat (Mosquitto Add-on).

### Technologie-Stack

- **Container:** Docker, basiert auf HA Add-on Base Image
- **Backend:** Python 3.13 + FastAPI (async)
- **Kommunikation mit HA:** WebSocket API (`ws://supervisor/core/websocket`)
- **Auth:** SUPERVISOR_TOKEN (automatisch verfügbar im Add-on Container)
- **Frontend:** Svelte + Tailwind CSS, DM Sans Schrift, ALKLY Farben
- **UI-Einbettung:** HA Ingress (zeigt Solarbot-UI im HA-Frame, eigener Sidebar-Eintrag)
- **Persistenz:** SQLite-Datenbank im `/data`-Ordner für Diagnose-Logs und Konfiguration
- **Verteilung:** Custom Add-on Repository auf GitHub (`alkly/solarbot`)
- **Updates:** Automatisch über HA Add-on Store System

---

## Für wen ist Solarbot?

### Primärer Nutzer: Der Balkonkraftwerk-Macher

Männer, 25-55 Jahre, DACH-Raum. Technisch versiert, aber keine Programmierer. Hat ein Balkonkraftwerk mit 1-3 kWp, einen Akku (Anker, Marstek oder DIY) und Home Assistant läuft bereits. Er will seinen Solarstrom optimal nutzen, hat aber keine Lust auf YAML-Gefrickel oder Cloud-Abhängigkeit.

**Sein aktueller Schmerz:**
- Verschenkt täglich 1-3 kWh Strom ans Netz
- Die Hersteller-App ist träge und cloud-abhängig
- Sein aktuelles Setup ist ein Flickenteppich aus Automationen
- EVCC ist für E-Autos gedacht, nicht für Balkonkraftwerke
- YAML-Helfer und Blueprints sind verwirrend und schwingen

**Was er braucht:**
- Nulleinspeisung die einfach läuft
- Akku smart laden und entladen, ohne Cloud
- Ein Setup das in 10 Minuten steht

### Sekundärer Nutzer: Der Eigenheim-Optimierer

Hat eine größere PV-Anlage (3-10+ kWp) mit Speicher (SMA, Huawei, Growatt). Will den Eigenverbrauch maximieren. Technisch fortgeschrittener.

### Validierte Daten (107 Umfrageantworten)

- 46x haben 1-3 kWp (Balkonkraftwerk)
- 33x haben 3-10 kWp, 19x haben >10 kWp
- 62x Fortgeschrittene HA-Nutzer, 35x Einsteiger
- Top-WR: Hoymiles (28x), Anker (14x), SMA (11x)
- 81 von 107 haben ihren WR bereits aus HA steuerbar
- 94% wollen Einmalkauf, kein Abo

### Voraussetzung beim Nutzer

**Hard Requirement:** Solarbot läuft nur auf Home Assistant OS oder Home Assistant Supervised. Nutzer mit HA Container oder HA Core werden auf der Landing Page klar darauf hingewiesen.

### Beispiel User Story

"Markus, 38, Ingenieur aus Stuttgart. Hat ein Balkonkraftwerk mit Hoymiles HMS-800 und einem Anker Solix E1600. HA läuft auf einem Raspberry Pi 4 mit HA OS. Er sieht im YouTube-Video von ALKLY: Solarbot ist da. Er deaktiviert seinen Blueprint, geht in den HA Add-on Store, fügt das Solarbot-Repository hinzu, installiert das Add-on, klickt auf 'Show in sidebar' und 'Start on boot', startet es. Solarbot erscheint in der Sidebar. Klick drauf, Setup-Wizard läuft, Auto-Detection findet Shelly 3EM und OpenDTU. Nach 8 Minuten läuft die Nulleinspeisung. Am nächsten Tag: 0W Einspeisung, Akku voll bis 14 Uhr."

---

## Das Problem das wir lösen

PV-Besitzer mit Home Assistant verschenken Strom, weil es keine einfache, lokale Lösung für Überschusssteuerung und Akku-Management gibt, die ohne YAML, Cloud oder Bastler-Expertise funktioniert.

### Warum existierende Lösungen nicht reichen

| Lösung | Problem für unsere Nutzer |
|--------|---------------------------|
| **EVCC** | Für E-Autos gebaut, nicht für BKW. Braucht YAML-Config |
| **Clever-PV** | Cloud-Pflicht, Abo-Modell (3-5 EUR/Monat) |
| **OpenDTU on Battery** | Nur Hoymiles, kein Multi-Akku, begrenzte Steuerung |
| **ALKLY Blueprint** | Nur Nulleinspeisung, kein Multi-Akku, YAML-Helfer nötig |
| **Hersteller-Apps** | Cloud-Zwang, träge (30-90s Latenz) |
| **Node-RED / DIY** | Flickenteppich, nicht wartbar |

Detaillierte Konkurrenzanalyse siehe Solarbot-Deep-Research.md.

---

## Migrationspfad: Vom Blueprint zu Solarbot

Der Wechsel vom Nulleinspeisungs-Blueprint zu Solarbot ist ein **sauberer Cut**, kein Parallelbetrieb:

1. **Vor der Solarbot-Installation:** Nutzer deaktiviert die Blueprint-Automation in HA
2. **Nutzer löscht die zugehörigen Input-Number-Helfer** (optional)
3. **Solarbot Add-on installieren** und Setup-Wizard durchlaufen
4. **Solarbot übernimmt die Steuerung** der gleichen WR-Entity

**Warum sauberer Cut?** Zwei Systeme die parallel das gleiche WR-Limit setzen führen zu Konflikten und Schwingungen. Im Setup-Wizard wird Schritt 0 prüfen, ob noch eine aktive Blueprint-Automation auf der gewählten WR-Entity existiert.

**Upgrade-Anreiz:** Bestehende Blueprint-Käufer bekommen einen Rabatt-Code für Solarbot.

---

## MVP Features

### Must Have für Launch (P0)

#### 1. Nulleinspeisung

- **Was:** PID-Regler im Add-on der das WR-Leistungslimit per HA WebSocket API sekundengenau anpasst
- **Erfolgskriterien:**
  - [ ] Einspeisung bleibt unter ±5W (Hoymiles) bzw. ±30W (Anker)
  - [ ] Kein Schwingen bei normalen Lastsprüngen
  - [ ] Smarte Defaults pro Systemtyp
  - [ ] Wiederanlauf nach HA-Neustart oder Add-on-Restart in unter 2 Minuten
- **Priorität:** P0

#### 2. Akku-Steuerung

- **Was:** Laden bei Überschuss, Entladen zur Grundlast-Deckung. Min/Max SoC konfigurierbar. Nachtentladung.
- **Erfolgskriterien:**
  - [ ] Akku lädt automatisch bei PV-Überschuss
  - [ ] Akku entlädt nachts für Grundlast
  - [ ] Min/Max SoC konfigurierbar (z.B. 10%-95%)
  - [ ] Funktioniert mit Anker Solix und Generic HA Entity
- **Priorität:** P0

#### 3. Setup-Wizard

- **Was:** Grafischer Wizard in der Add-on Web-UI. Drei Pfade (Hoymiles, Anker, Manuell), Auto-Detection per `get_states`, Live-Werten und Funktionstest
- **Erfolgskriterien:**
  - [ ] **Zielwert:** 80% der Nutzer schließen Setup in unter **10 Minuten** ab
  - [ ] **Akzeptanzkriterium:** Beta-Tester schließen Setup in unter **15 Minuten** ab
  - [ ] Auto-Detection für OpenDTU, Shelly 3EM, Anker Solix
  - [ ] Live-Werte neben jedem Sensor zur Bestätigung
  - [ ] Funktionstest am Ende (WR-Limit wird gesetzt und geprüft)
  - [ ] Lizenzaktivierung nach Funktionstest, vor "Aktivieren"-Button
- **Priorität:** P0

#### 4. Diagnose-Tab

- **Was:** Tab in der Solarbot Add-on UI mit den letzten 100 Regelzyklen, aktuellen Werten und Fehlerlogs. Speicherung in SQLite im `/data`-Ordner.
- **Erfolgskriterien:**
  - [ ] Letzte 100 Regelzyklen sichtbar (Zeitstempel, Sensorwert, gesetztes Limit, Latenz)
  - [ ] Letzte 20 Fehler/Warnungen mit Klartext-Beschreibung
  - [ ] Aktuelle Verbindungs-Stati (HA WebSocket, Entities erreichbar)
  - [ ] Export-Funktion für Bug-Reports (JSON oder Text)
- **Priorität:** P0

### Multi-Device-Beschränkung im MVP

Das MVP unterstützt bewusst nur **eine** Konfiguration pro Komponente:
- **1 Wechselrichter**
- **1 Smart Meter**
- **1 Akku**

Multi-Device ist V2.

### Sprachen im MVP

**Nur Deutsch.** Englisch und weitere Sprachen kommen in V2.

### HA-Entities

**Im MVP stellt Solarbot keine nativen HA-Entities bereit.** Alle Daten und Steuerungen sind in der Solarbot Add-on UI verfügbar.

**In V1.5 (Monat 2):** Optionale MQTT Discovery Integration. Wenn der Nutzer den Mosquitto Add-on installiert hat, kann Solarbot seine Daten als MQTT-Topics publishen, woraus HA automatisch Entities erstellt. Damit können Nutzer dann Solarbot-Daten in Lovelace-Karten und Automationen verwenden.

### NICHT im MVP

| Feature | Geplant für |
|---------|------------|
| **HA-Entities (via MQTT Discovery)** | V1.5 |
| **Dynamische Stromtarife** (Tibber, aWATTar) | V1.5 |
| **Überschuss-Kaskade** (Verbraucher-Priorisierung) | V2 |
| **Entlade-Kaskade** (Multi-Akku-Priorisierung) | V2 |
| Multi-Wechselrichter | V2 |
| Multi-Akku | V2 |
| Englische UI | V2 |
| Solarprognose | V3 |
| Wallbox als Verbraucher | V3+ |
| **Solarbot Lite** (Custom Integration für HA Container/Core) | V2 (nach Bedarf) |

---

## V1.5: MQTT Discovery und dynamische Tarife

Nach dem MVP kommen zwei Features als V1.5 (Monat 2 nach Launch), die Solarbot deutlich aufwerten ohne grundlegend etwas zu ändern:

### MQTT Discovery für HA-Entities

Solarbot publisht seine wichtigsten Daten als MQTT-Topics:
- `solarbot/grid_power` (Netzbezug)
- `solarbot/inverter_power` (WR-Leistung)
- `solarbot/battery_soc` (Akkustand)
- `solarbot/regulation_active` (Regelung an/aus)

Mit Discovery-Metadaten erstellt HA daraus automatisch Sensoren und Schalter. Voraussetzung: Mosquitto Add-on läuft (haben die meisten HA-Nutzer eh).

### Dynamische Stromtarife

Solarbot liest einen Strompreis-Sensor aus HA (Tibber, aWATTar, EPEX Spot, Nordpool — alle als HACS-Integrationen verfügbar). Die Regelung berücksichtigt dann:
- Akku **aus dem Netz** laden wenn Strom billig ist
- Akku entladen wenn Strom teuer ist
- Bewusst einspeisen wenn Preise negativ sind

Das ist ein starkes Verkaufsargument gegen EVCC und Clever-PV.

---

## V2-Konzept: Kaskaden-Modell für Priorisierung

### Überschuss-Kaskade (Tag)

Der Überschuss fließt durch eine Prioritätsliste. Jedes Gerät nimmt sich was es braucht, der Rest fließt weiter.

Jeder Slot hat drei Eigenschaften:
- **Was:** Gerät/Aktion (Akku, Klimaanlage, Wallbox)
- **Gate:** Bedingung zur Aktivierung (Immer, SoC über X%, Überschuss über X Watt, Zeitfenster, **Strompreis unter X ct/kWh**)
- **Ziel:** Wann das Gerät "satt" ist

Beispiel:
```
Überschuss: 1200W
  → [Prio 1] Akku bis 80% (Gate: Immer) → nimmt 400W
  → [Prio 2] Wallbox (Gate: Akku >60% UND >1400W) → nimmt 0W
  → [Prio 3] Klimaanlage (Gate: Akku >70%) → nimmt 800W
  → [Prio 4] Akku auf 100% (Gate: Alle anderen versorgt) → nimmt 0W
  → Netz: 0W
```

### Entlade-Kaskade (Nacht)

Gleiche Logik, umgekehrt. Der Bedarf zieht aus den Quellen:
```
Grundlast: 300W
  → [Quelle 1] Akku A (min 20% SoC) → liefert 300W
  → [Quelle 2] Akku B (min 10% SoC) → nicht nötig
  → [Quelle 3] Netz (Fallback)
```

### Datenmodell (V2)

```json
{
  "surplus_cascade": [
    {
      "id": "battery_primary_80",
      "type": "battery",
      "entity_control": "number.solarbank_e1600_preset...",
      "entity_soc": "sensor.solarbank_e1600_soc",
      "target_soc": 80,
      "gate": {"type": "always"},
      "max_power": 400
    },
    {
      "id": "climate_living",
      "type": "switch",
      "entity_control": "switch.klimaanlage",
      "gate": {
        "type": "and",
        "conditions": [
          {"type": "soc_above", "entity": "sensor.solarbank_e1600_soc", "value": 70},
          {"type": "price_below", "entity": "sensor.tibber_price", "value": 0.20}
        ]
      },
      "min_surplus": 500
    }
  ],
  "discharge_cascade": [
    {
      "id": "battery_a",
      "entity_soc": "sensor.solarbank_e1600_soc",
      "min_soc": 20,
      "time_window": {"start": "20:00", "end": "06:00"}
    }
  ]
}
```

### UI: Drag-and-Drop Prioritätsliste (V2)

Nutzer ziehen Geräte in die gewünschte Reihenfolge. Pro Gerät: Gate-Bedingung, SoC-Ziel, Min-Überschuss. Mockups im Onboarding-UX-Dokument.

---

## Technische Eckpunkte

**Architektur:** Home Assistant Add-on (festgelegt am 10. April 2026)
**Backend:** Python 3.13 + FastAPI
**Frontend:** Svelte + Tailwind CSS, DM Sans, ALKLY Farben
**HA-Kommunikation:** WebSocket API (`ws://supervisor/core/websocket`), kein direktes MQTT (außer V1.5 Discovery)
**Auth:** SUPERVISOR_TOKEN
**Persistenz:** SQLite in `/data/solarbot.db`
**Lizenzierung:** LemonSqueezy (einmalige Aktivierung nach Funktionstest, danach offline-fähig)
**Update-Mechanismus:** Automatisch über HA Add-on Store System
**Verteilung:** Custom Add-on Repository auf GitHub (`alkly/solarbot`)
**Preismodell:** TBD (Optionen: 29 EUR einmalig, 1 EUR/Monat, Staffelung)
**Installations-Voraussetzung:** Home Assistant OS oder HA Supervised (kein HA Container, kein HA Core)

---

## Erfolgsmetriken

### Launch (Erste 30 Tage)

| Metrik | Ziel |
|--------|------|
| Aktive Nutzer | 100 |
| NPS Score | > 8 |
| Setup-Abschlussrate | > 80% in unter 10 Min |
| Support-Anfragen | < 2 pro Nutzer |
| Blueprint-Upgrade-Rate | > 20% der 300 Blueprint-Nutzer |

### Wachstum (Monat 2-3)

| Metrik | Ziel |
|--------|------|
| Aktive Nutzer gesamt | 250 |
| Retention (30 Tage) | > 70% |
| GitHub Stars | 50+ |

---

## Risikobewertung

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Anker Cloud-API ändert sich | Hoch | Hoch | Generic HA Adapter als Fallback |
| Regelung schwingt bei bestimmter Hardware | Hoch | Mittel | Auto-Tuning-Defaults, Deadband |
| **HA Container/Core Nutzer ausgeschlossen** | Mittel | Mittel | **Klar kommunizieren, V2 evaluieren ob Solarbot Lite** |
| **Add-on Installation zu komplex für Einsteiger** | Mittel | Mittel | **YouTube-Anleitung, Discord-Support, Beta-Test mit Einsteigern** |
| Weniger als 50 Nutzer im ersten Monat | Mittel | Mittel | Early-Bird-Preis, YouTube Launch-Video |
| HA Update bricht WebSocket API | Niedrig | Hoch | Eigener Container = isoliert |
| Beta-Tester kommen nicht zur Sache | Mittel | Hoch | Detaillierter Beta-Plan |

---

## MVP Definition of Done

Das MVP ist launch-bereit wenn:

- [ ] Solarbot läuft als HA Add-on auf Raspberry Pi 4 mit HA OS
- [ ] Nulleinspeisung läuft stabil auf Hoymiles (±5W) und Anker (±30W)
- [ ] Akku-Steuerung (Laden/Entladen mit SoC-Grenzen) funktioniert
- [ ] Setup-Wizard mit Auto-Detection und Funktionstest läuft in der Add-on Web-UI
- [ ] Diagnose-Tab zeigt Regelzyklen, Fehler und Stati
- [ ] Wiederanlauf nach HA-Neustart oder Add-on-Restart in unter 2 Minuten
- [ ] Migrationspfad vom Blueprint dokumentiert und im Wizard geprüft
- [ ] Lizenzaktivierung via LemonSqueezy nach Funktionstest funktioniert
- [ ] 24h Dauertest ohne Absturz oder Schwingung
- [ ] Custom Add-on Repository auf GitHub eingerichtet
- [ ] **5+ Beta-Tester bestätigen: Setup unter 15 Minuten** (Akzeptanzkriterium)
- [ ] **80% der Beta-Tester schließen Setup in unter 10 Minuten ab** (Zielwert)
- [ ] NPS > 8 bei Beta-Testern
- [ ] YouTube Launch-Video aufgenommen (inklusive Add-on-Installation)
- [ ] Newsletter an Blueprint-Nutzer vorbereitet
- [ ] Landing-Page-Hinweis "Benötigt HA OS oder Supervised" sichtbar

---

## Timeline (9 Wochen total)

| Woche | Phase | Aufgabe |
|-------|-------|---------|
| **0** | **Vorbereitung** | **Add-on Spike: Validierung der Architektur (siehe Spike-Dokument)** |
| 1 | Build | Add-on Grundgerüst, FastAPI, WebSocket-Anbindung, erste Sensor-Reads |
| 2 | Build | PID-Regler, Nulleinspeisung-Logik, Anti-Schwingung |
| 3 | Build | Setup-Wizard mit Auto-Detection und Live-Werten (Svelte UI) |
| 4 | Build | Akku-Steuerung, Dashboard, Diagnose-Tab |
| 5 | Build | LemonSqueezy Lizenz-Integration, Funktionstest |
| 6 | Build + Beta-Start | Bugfixes, Beta-Tester onboarden, Dokumentation |
| 7 | Launch-Vorbereitung | Bugfixes aus Beta, YouTube-Video, Newsletter |
| 8 | **Launch** | **Public Launch mit Early-Bird-Preis** |

---

## Nächste Schritte

1. **Jetzt:** PRD v1.3 reviewen und freigeben
2. **Woche 0:** Add-on Spike durchführen (siehe Solarbot-Architecture-Spike.md)
3. **Woche 0:** Beta-Tester aus Warteliste auswählen (siehe Solarbot-Beta-Plan.md)
4. **Wochen 1-6:** MVP bauen mit AI-Unterstützung
5. **Wochen 7-8:** Launch

---

*Version 1.3 — 10. April 2026 — Add-on-Architektur committed*
