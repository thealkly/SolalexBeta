# Deep Research Report: Solalex — Home Assistant Add-on

**Version:** 1.3
**Erstellt:** 25. März 2026
**Aktualisiert:** 10. April 2026 (Add-on-Architektur committed)
**Für:** Alex Kly / ALKLY
**Methode:** Web-Research, Quellenanalyse, technische Dokumentation

---

## Zusammenfassung der wichtigsten Empfehlungen

1. **Architektur:** **Home Assistant Add-on** — committed am 10. April 2026 nach Architektur-Diskussion. Python 3.13 + FastAPI. Distribution über Custom Add-on Repository auf GitHub.
2. **Kommunikation:** Ausschließlich über HA WebSocket API. Kein direktes MQTT, keine direkte Hardware-Kommunikation. (V1.5 evaluiert MQTT Discovery für HA-Entities-Bereitstellung.)
3. **Lizenzmodell:** Einmalkauf über LemonSqueezy, Aktivierung nach Funktionstest, danach offline-fähig.
4. **Preis:** TBD (Optionen: 29 EUR einmalig, 1 EUR/Monat, Staffelung)
5. **MVP-Fokus:** Nulleinspeisung + 1 Akku-Steuerung + Setup-Wizard mit Auto-Detection (siehe PRD)
6. **V1.5-Fokus:** MQTT Discovery für HA-Entities + dynamische Stromtarife
7. **V2-Fokus:** Kaskaden-Modell für Überschuss-Verteilung und Entlade-Priorisierung
8. **Timeline:** 9 Wochen total (Spike Woche 0 + Build Wochen 1-6 + Launch Wochen 7-8)
9. **Voraussetzung beim Nutzer:** Home Assistant OS oder HA Supervised (kein Container, kein Core)

---

## 1. Architektur-Entscheidung: Add-on (committed)

### Warum Add-on und nicht Custom Integration

Beide Optionen wurden evaluiert. Das Ergebnis: **Add-on gewinnt für Solalex's Anforderungen**, primär aus geschäftlichen und betrieblichen Gründen.

| Kriterium | Add-on | Custom Integration |
|---|---|---|
| **UI-Freiheit** | Voll (FastAPI + Svelte) | Voll (Custom Panel möglich) |
| **HA-Entities nativ** | Nein (V1.5 via MQTT) | Ja |
| **Crash-Isolation** | **Stark** (eigener Container) | Schwach (im HA-Core) |
| **Lizenzierung praktikabel** | **Ja** | Schwierig (offen lesbarer Code) |
| **Update ohne HA-Reboot** | **Ja** (10 Sek) | Nein (1-2 Min) |
| **Eigene Datenbank/Storage** | **Ja** (`/data` Volume) | Begrenzt |
| **Library-Freiheit** | **Voll** | An HA-Core gebunden |
| **Eigene Logs** | **Ja** | Vermischt mit HA-Logs |
| **Installations-Reichweite** | HA OS + Supervised (~85%) | Alle HA-Typen (100%) |
| **Community-Akzeptanz kommerziell** | **Höher** | Niedriger |

### Die Trade-offs

**Was wir aufgeben:**
- Native HA-Entities im MVP (kommt in V1.5 via MQTT Discovery)
- ~10-15% der HA-Nutzer (HA Container und HA Core User)
- Etwas aufwändigere Installation als HACS

**Was wir gewinnen:**
- Solides Fundament für ein kommerzielles Produkt
- Crash-Isolation für Produktions-Stabilität
- Saubere Update-Pipeline ohne HA-Reboot
- Volle Kontrolle über Storage, Libraries, Logs

### Was Add-on bedeutet (technisch)

**Add-on (seit HA 2026.2 offiziell als "App" bezeichnet):** Eigenständiger Docker-Container neben HA. Eigene Weboberfläche über Ingress, eigene Prozesse, kommuniziert mit HA über WebSocket API.

Solalex läuft in einem isolierten Container mit:
- Eigenem Python 3.13 + FastAPI
- Persistenz in `/data` (überlebt Updates)
- Ingress-eingebettete UI im HA-Frame
- WebSocket-Verbindung zu HA über `ws://supervisor/core/websocket`
- SUPERVISOR_TOKEN automatisch verfügbar als Umgebungsvariable

---

## 2. Kommunikation mit Home Assistant

### Im MVP: Reine WebSocket API

Solalex greift nie direkt auf Hardware zu. Alle Geräte sind bereits als HA-Entities vorhanden. Solalex nutzt:

**Sensoren lesen:** `subscribe_trigger` auf state_changed Events (Echtzeit, kein Polling)
```json
{"type": "subscribe_trigger", "trigger": {"platform": "state", "entity_id": "sensor.shelly_3em_power"}}
```

**Services aufrufen:** `call_service` für z.B. number.set_value (WR-Limit setzen)
```json
{"type": "call_service", "domain": "number", "service": "set_value", "target": {"entity_id": "number.opendtu_limit_nonpersistent_absolute"}, "service_data": {"value": 450}}
```

**Entity-Liste:** `get_states` für Auto-Detection im Setup-Wizard
**Auth:** SUPERVISOR_TOKEN (automatisch im Add-on Container verfügbar)

### In V1.5: MQTT Discovery für HA-Entities

Damit Nutzer Solalex-Daten in Lovelace-Karten und Automationen verwenden können, kommt in V1.5 (Monat 2 nach Launch) eine optionale MQTT-Schnittstelle:

- Solalex publisht Daten als MQTT-Topics auf den HA-eigenen Mosquitto-Broker
- HA Discovery erstellt automatisch Sensoren und Schalter daraus
- Voraussetzung: Mosquitto Add-on läuft (haben die meisten HA-Nutzer)

So bleibt das MVP fokussiert auf die Add-on-eigene UI, und die HA-Entity-Integration kommt als sauberes Update.

---

## 3. Programmiersprache und Stack

**Python 3.13** ist die richtige Wahl: Beste AI-Tooling-Unterstützung (Claude, Copilot, Cursor), HA-Core ist Python, exzellente Bibliotheken für WebSocket und async. Python 3.13 (seit HA 2024.12) bringt Performance-Verbesserungen.

**FastAPI** als Web-Framework: Schnell, async-native, automatische OpenAPI-Doku, perfekt für Single-Container Add-ons.

**Svelte + Tailwind** für das Frontend: Klein, schnell, ohne große Build-Pipeline. DM Sans als Schrift, ALKLY-Farben.

**SQLite** für Persistenz: Im `/data`-Ordner des Add-ons. Überlebt Updates und Neustarts. Perfekt für Diagnose-Logs (Regelzyklen, Fehler) und Konfiguration.

---

## 4. Regelungstechnik: ±5W Genauigkeit

**PID-Regler (empfohlen)** mit folgenden Anti-Schwingungs-Maßnahmen:

- **Deadband/Totzone:** Erst ab ±10W Abweichung reagieren
- **Rate Limiting:** Maximal alle 3-5 Sekunden ein neues WR-Limit setzen
- **Glättung/Moving Average:** Durchschnitt der letzten 3-5 Messwerte
- **Anti-Windup:** I-Anteil begrenzen wenn WR am Limit ist
- **Smarte Defaults pro Hardware:** Hoymiles (aggressiv, 10W Deadband), Anker (sanft, 30W Deadband)

**Realistische Genauigkeit:** ±5W bei Hoymiles/OpenDTU (5-15s Reaktionszeit), ±30W bei Anker Solix (30-90s Cloud-Latenz).

---

## 5. Entwicklung und Verteilung

### Entwicklung

- **Repository:** `alkly/solalex` auf GitHub (privat während Entwicklung, public beim Launch)
- **Lokale Entwicklung:** HA Dev Container für VS Code, oder direktes lokales Mounten in HA `/addons/local/`
- **Testing:** Auf echtem Raspberry Pi 4 mit HA OS

### Verteilung als Add-on

- **Custom Add-on Repository auf GitHub:** Nutzer fügen die Repo-URL im HA Add-on Store hinzu
- **Docker-Images** werden via GitHub Actions gebaut (Multi-Arch: amd64, aarch64 für Raspberry Pi)
- **Automatische Updates** über das HA Add-on Store System (HA prüft regelmäßig auf neue Versionen und bietet Updates an)

### Installationsablauf für Endnutzer

```
1. HA → Settings → Add-ons → Add-on Store
2. Drei-Punkte-Menü → Repositories
3. URL hinzufügen: https://github.com/alkly/solalex
4. Solalex-Add-on installieren
5. "Show in sidebar" und "Start on boot" aktivieren
6. Solalex starten → erscheint in der Sidebar
7. Setup-Wizard läuft beim ersten Öffnen
```

Ein Schritt mehr als HACS-Integration, aber sauberer Standard-Weg in HA.

---

## 6. Konkurrenzanalyse

### 6.1 Feature-Matrix

| Feature | **Solalex** (geplant) | **EVCC** | **Clever-PV** | **OpenDTU on Battery** |
|---|---|---|---|---|
| **Architektur** | HA Add-on | Standalone Go-App + HA Add-on | Cloud-Service | ESP-Firmware |
| **Zielgruppe** | BKW + kleine PV mit HA | E-Auto-Fahrer | Alle PV-Besitzer | Hoymiles + DIY-Akku |
| **Nulleinspeisung** | ±5W, sekundengenau | Nicht der Fokus | Eco-Offset (grob) | Dynamischer Power Limiter |
| **Akku-Steuerung** | Ja (V2: Multi-Akku) | Nein | Begrenzt | Nur 1 Akku |
| **Verbraucher-Priorisierung** | Kaskaden-Modell (V2) | Nur Wallbox | Ja | Nein |
| **Dynamische Tarife** | V1.5 | Ja | Ja | Nein |
| **100% Lokal** | Ja | Ja | Nein (Cloud-Pflicht) | Ja |
| **Ohne YAML** | Ja | Nein (evcc.yaml) | Ja (App) | Web-UI vorhanden |
| **Preis** | TBD | 2 EUR/Monat oder 100 EUR einmalig | 3-5 EUR/Monat | Kostenlos |

### 6.2 EVCC

In Go geschrieben, fokussiert auf E-Auto-Überschussladen. Über 80 Wallboxen unterstützt. **Wird auch als HA Add-on angeboten** — also denselben Distributionsweg den wir für Solalex wählen. Lizenzmodell: Sponsoring-Token über Creem.io (2 EUR/Monat oder 100 EUR Lifetime). Bestimmte Wallboxen erfordern Sponsor-Token.

**Wichtig für uns:** EVCC zeigt, dass kommerzielle HA Add-ons funktionieren. Die Community akzeptiert das Modell, auch wenn es kontrovers diskutiert wird.

**Schwächen für unsere Zielgruppe:**
- Nicht auf BKW/kleine Anlagen ausgelegt
- Primär Auto-fokussiert, keine echte Nulleinspeisung
- Konfiguration über YAML-Datei
- Kein Multi-Akku-Management

### 6.3 Clever-PV

Bayerisches Startup. Cloudbasiert, App-gesteuert. Pricing-Stufen:
- **Kostenlos:** Monitoring + manuelle Steuerung
- **Starter:** ~3 EUR/Monat — 1 Verbraucher automatisch
- **Clever:** ~5 EUR/Monat — Alle Verbraucher, Priorisierung, historisches Monitoring

500+ kompatible Geräte über Cloud-APIs der Hersteller.

**Schwächen (= unsere Chancen):**
- Cloud-Pflicht (versagt beim ALKLY Produkt-Test)
- Update-Intervalle alle 15 Sekunden bis 5 Minuten — keine sekundengenaue Regelung
- Abo-Modell (94% unserer Nutzer wollen Einmalkauf)
- Keine HA-Integration

### 6.4 Relevante Open-Source-Projekte

- **Solar Optimizer** (jmcollin78/solar_optimizer): HA Custom Integration für Verbraucher-Priorisierung. Kostenlos, aber kein Dashboard und keine Akku-Steuerung. Aus Frankreich.
- **HSEM** (woopstar/hsem): Huawei-spezifisch, berechnet optimale Lade-/Entladezeiten.
- **Anker Solix X1 Modbus** (HA Community, Januar 2026): Lokale Steuerung ohne Cloud.

### 6.5 Zigbee2MQTT als Architektur-Vorbild

Nicht direkt Konkurrenz, aber lehrreich: **Zigbee2MQTT** ist eines der erfolgreichsten HA Add-ons überhaupt. Es zeigt, dass:
- Die Add-on-Distribution für komplexe Anwendungen funktioniert
- Eigene Web-UI über Ingress sehr gut ankommt
- Nutzer gerne Add-ons mit eigenständigem Charakter installieren
- HA-Entity-Bereitstellung über MQTT Discovery (genau unser V1.5-Plan) bei Nutzern beliebt ist

---

## 7. Lizenzierung und Monetarisierung

### 7.1 Empfehlung: LemonSqueezy + Offline-Caching

**Warum LemonSqueezy:**
- Übernimmt EU-Steuern (USt.) automatisch als Merchant of Record
- Generiert Rechnungen, Lizenzschlüssel-System integriert
- 5% + 0,50 EUR pro Transaktion (bei 29 EUR ≈ 1,95 EUR Gebühr)
- Webhooks für Automatisierung
- Dashboard für Verkäufe und Kunden-Management

**Implementierung "lokal-freundlich" im Add-on:**
1. Nutzer kauft über LemonSqueezy → bekommt Key per E-Mail
2. Nach dem Funktionstest im Setup-Wizard: Key eingeben
3. Einmalige Online-Validierung gegen LemonSqueezy API
4. Bei Erfolg: Signierte Lizenzdatei in `/data/license.json` gespeichert
5. Danach: Nur noch lokale Datei prüfen, kein Internet nötig
6. Optional: Alle 90 Tage Re-Validierung mit Graceful Degradation

So bleibt Solalex 100% lokal im Betrieb — nur die einmalige Aktivierung braucht Internet.

### 7.2 Warum Add-on hier ein Vorteil ist

Im Vergleich zur Custom Integration ist das Add-on für Lizenzierung besser geeignet:
- **Container-Isolation** macht das Auskommentieren von Lizenz-Checks aufwändiger
- **Code kann gepackt werden** (kompilierte Python-Bytecode oder Cython)
- **Sensible Logik** kann in einen Server packen, der nur mit gültiger Lizenz antwortet
- **Community akzeptiert** kommerzielle Add-ons besser als kommerzielle Integrationen

Trotzdem bleibt es eine "Ehrenschranke" — wer wirklich will, kann sie umgehen. Echter Schutz kommt durch Updates, Support, Community, Bequemlichkeit.

### 7.3 Preismodell: TBD

| Modell | Preis | Pro | Contra |
|--------|-------|-----|--------|
| Einmalkauf (Beta) | 29 EUR | Einfach, 94% wollen das | Möglicherweise zu wenig für Nachhaltigkeit |
| Monatlich | 1 EUR/Monat | Wiederkehrend, niedrige Hürde | Abo-Aversion (6%), Cloud-Assoziation |
| Staffelung | Basic 29 / Pro 49 / Supporter 79 EUR | Verschiedene Zahlungsbereitschaften | Komplexität |

**Entscheidung nach Beta-Feedback.** Muss zum ALKLY Ascending Transaction Model passen.

### 7.4 Rechtliches (DE/EU)

- **Impressum, AGB, Widerrufsbelehrung** (bei digitalen Gütern: Verzicht möglich bei Zustimmung vor Aktivierung)
- **DSGVO-konform** (passend zu ALKLY Plausible-Analytics)
- **Steuern:** LemonSqueezy als Merchant of Record vereinfacht erheblich
- **Gewerbeanmeldung** beim lokalen Gewerbeamt

---

## 8. Hardware-Kompatibilität

### 8.1 Hoymiles (über OpenDTU) — Priorität 1

Steuerung über HA-Entities die von der OpenDTU MQTT Integration bereitgestellt werden. Relevante Entities: `number.opendtu_limit_nonpersistent_absolute` (Limit setzen), `sensor.opendtu_ac_power` (Leistung lesen). Latenz: 10-30 Sekunden. Unterstützte Modelle: HM-300, HM-600, HM-800, HM-1500, HMS-Serie, HMT-Serie.

### 8.2 Anker Solix (über HACS Integration)

Steuerung über Anker Cloud API via HA Integration (thomluther/ha-anker-solix). Entities für Einspeiselimit, SoC, Leistung. Latenz: 30-90 Sekunden (Cloud-abhängig). Seit Januar 2026 gibt es für Anker Solix X1 eine experimentelle Modbus-Integration ohne Cloud.

### 8.3 Weitere Hersteller

- **Marstek:** Modbus TCP/RTU über HA Modbus Integration
- **Zendure:** HACS Integration (Cloud-API)
- **Growatt:** Modbus TCP, mehrere HA-Integrationen
- **SMA:** Modbus TCP + Speedwire, offizielle HA Core Integration
- **Huawei:** Modbus TCP, HSEM-Projekt zeigt umfangreiche Steuerung

### 8.4 Abstraktionsschicht

Solalex arbeitet ausschließlich mit HA-Entities. Solange ein Gerät als Entity in HA existiert, kann Solalex es nutzen. Kein herstellerspezifischer Code nötig — nur Entity-IDs in der Konfiguration. Auto-Detection im Wizard findet bekannte Entity-Muster.

### 8.5 Smart Meter

- **Shelly 3EM / Pro 3EM:** WiFi, Update alle 1 Sekunde
- **PowerFox poweropti:** IR-Lesekopf, Update alle 2-3 Sekunden
- **SML IR-Lesekopf (DIY):** Günstigste Option, 1-10 Sekunden

### 8.6 Hardware-Voraussetzung beim Nutzer

- **Home Assistant OS** auf Raspberry Pi 4, NUC oder vergleichbar (geschätzt 70-85% der HA-Nutzer)
- **Home Assistant Supervised** auf eigener Linux-Installation (geschätzt 5-10%)

**Nicht unterstützt:** HA Container (Docker ohne Supervisor), HA Core (manuelle Python-Installation). Diese ~10-15% der HA-Nutzer sind ausgeschlossen.

---

## 9. V1.5: MQTT Discovery und dynamische Tarife (Kurzfassung)

Nach dem MVP kommen zwei Features als V1.5 (Monat 2 nach Launch):

**MQTT Discovery für HA-Entities:** Solalex publisht seine wichtigsten Daten als MQTT-Topics auf den HA-eigenen Mosquitto-Broker. HA erstellt daraus automatisch native Sensoren und Schalter. So kann der Nutzer Solalex-Daten in Lovelace-Karten und Automationen verwenden.

**Dynamische Stromtarife:** Solalex liest einen Strompreis-Sensor aus HA (Tibber, aWATTar, EPEX Spot, Nordpool — alle als HACS-Integrationen verfügbar). Die Regelung berücksichtigt dann Preis-Optimierung: Akku aus dem Netz laden wenn Strom billig ist, bewusst einspeisen wenn Preise negativ sind.

Beides sind starke Verkaufsargumente gegen EVCC und Clever-PV.

---

## 10. V2-Konzept: Kaskaden-Modell (Kurzfassung)

Das Kaskaden-Modell verteilt PV-Überschuss tagsüber durch eine Prioritätsliste von Geräten und zieht nachts Energie aus mehreren Akkus in definierter Reihenfolge. Jeder Listeneintrag hat ein Gate (Aktivierungsbedingung, inklusive Strompreis-Bedingungen) und ein Ziel.

**Vollständige Beschreibung mit Beispielen, Datenmodell und UI-Mockups: siehe PRD-Solalex-MVP.md (Abschnitt "V2-Konzept") und Solalex-Onboarding-UX.md.**

---

## 11. MVP-Roadmap

### Phase 0: Add-on Validierungs-Spike (Woche 0)

Validierung der Add-on-Architektur durch einen minimalen aber realistischen PoC. Hypothesen testen: Latenz, Ressourcen, Persistenz, Lizenz-Aktivierung. Detaillierter Plan: siehe Solalex-Architecture-Spike.md

### Phase 1: Build (Wochen 1-6)

| Woche | Aufgabe |
|-------|---------|
| 1 | Add-on Grundgerüst, FastAPI, WebSocket-Anbindung |
| 2 | PID-Regler, Nulleinspeisung-Logik, Anti-Schwingung |
| 3 | Setup-Wizard mit Auto-Detection und Live-Werten (Svelte UI) |
| 4 | Akku-Steuerung, Dashboard, Diagnose-Tab |
| 5 | LemonSqueezy Lizenz-Integration, Funktionstest |
| 6 | Beta-Start, Bugfixes, Dokumentation |

### Phase 2: Launch (Wochen 7-8)

- Bugfixes aus Beta-Feedback
- YouTube Launch-Video (inkl. Add-on-Installation)
- Newsletter an Blueprint-Nutzer
- Custom Repository auf public stellen
- Early-Bird-Preis für erste 50 Käufer

Beta-Plan im Detail: siehe Solalex-Beta-Plan.md

### Phase 3: V1.5 (Monat 2 nach Launch)

- MQTT Discovery für HA-Entities
- Dynamische Stromtarife (Tibber, aWATTar, etc.)

### Phase 4: V2 (Monat 3-4)

- Überschuss-Kaskade (Verbraucher-Priorisierung mit SoC-Gates und Preis-Gates)
- Entlade-Kaskade (Multi-Akku-Priorisierung)
- Multi-Wechselrichter und Multi-Akku
- Englische UI
- Energiefluss-Dashboard

### Optional: Solalex Lite (V2+)

Falls die Beta zeigt, dass viele Interessenten HA Container oder HA Core nutzen und nicht migrieren wollen: Eine reduzierte Custom Integration als "Solalex Lite" mit Basis-Funktionalität (Nulleinspeisung) ohne UI. Wird nach Beta-Daten entschieden.

### Risiken

| Risiko | Mitigation |
|--------|------------|
| Anker Cloud-API ändert sich | Generic HA Adapter als Fallback |
| Regelung schwingt | Auto-Tuning-Defaults, Deadband |
| HA Container/Core Nutzer ausgeschlossen | Klar kommunizieren, V2 evaluieren |
| Add-on Installation zu komplex | Video-Anleitung, Discord-Support |
| Weniger als 50 Nutzer | Early-Bird, YouTube, Blueprint-Upgrade |
| HA Update bricht WebSocket API | Eigener Container = isoliert |

---

## Quellenverzeichnis

- HA Developer Docs (Add-on, WebSocket API): developers.home-assistant.io
- HA Release 2026.2 (Apps Refactoring): home-assistant.io/blog/2026/02/04/release-20262/
- EVCC Sponsoring: sponsor.evcc.io, docs.evcc.io/docs/sponsorship
- Clever-PV: clever-pv.com/de/
- OpenDTU-OnBattery: opendtu-onbattery.net/
- Anker Solix Integration: github.com/thomluther/ha-anker-solix
- LemonSqueezy License API: docs.lemonsqueezy.com/api/license-api
- Keygen.sh Offline Licensing: keygen.sh/docs/choosing-a-licensing-model/offline-licenses/
- Solar Optimizer: github.com/jmcollin78/solar_optimizer
- HSEM: github.com/woopstar/hsem
- Zigbee2MQTT (als Add-on Vorbild): zigbee2mqtt.io
- HA Add-on Tutorial: developers.home-assistant.io/docs/add-ons/

---

## Verwandte Dokumente

- **PRD-Solalex-MVP.md** — Was wir bauen, MVP Features, V1.5/V2-Roadmap, Kaskaden-Modell ausführlich
- **Solalex-Architecture-Spike.md** — Add-on Validierungs-Spike in Woche 0
- **Solalex-Onboarding-UX.md** — Add-on Installation und Setup-Wizard im Detail
- **Solalex-Beta-Plan.md** — Auswahl, Onboarding und Management der 20 Beta-Tester

---

*Version 1.3 — 10. April 2026 — Add-on-Architektur committed*
