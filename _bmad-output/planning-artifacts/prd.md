---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-01b-continue', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - docs/PRD-Solalex-MVP-2.md
  - docs/Solalex-Beta-Plan.md
  - docs/Solalex-Deep-Research.md
  - docs/Temp Research/ALKLY_Kundenanalyse_Personas_Report.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-14.md
  - docs/Wettbewerber_01_EVCC.md
  - docs/Wettbewerber_01_EVCC_Supplement_Optimizer.md
  - docs/Wettbewerber_02_Akkudoktor_EOS.md
  - docs/Wettbewerber_03_OpenDTU_DIY.md
  - docs/Wettbewerber_04_openWB.md
documentCounts:
  briefs: 0
  prdDrafts: 1
  plans: 1
  research: 2
  brainstorming: 1
  competitors: 5
  projectDocs: 0
workflowType: 'prd'
classification:
  projectType: iot_embedded
  projectSubtype: edge_orchestrator
  deploymentModel: local_premise
  distributionChannel: ha_addon_store
  licensingModel: one_time_purchase_freemium
  domain: energy
  domainSubtype: consumer_pv
  complexity: high
  projectContext: greenfield_code_brownfield_planning
tagline: 'Steuert deinen Solar lokal und sekundengenau.'
vision:
  coreInsight: 'HA als Entity-Layer ist der Moat — Solalex orchestriert, baut keine Treiber'
  differentiator: 'Aktive, sekundengenaue Steuerung — nicht Prognose, nicht Beobachtung'
  valueProps:
    - 'Du integrierst. Solalex regelt.'
    - 'Steuert deinen Solar lokal und sekundengenau.'
  realProblem: 'Cloud-Müdigkeit + Preisspread — Solar gekauft für Autarkie, Software sabotiert sie'
  whyNow:
    rational: 'Bezug ~30ct vs. Einspeisung 0-8ct = 4-5x Spread, jede kWh zählt ökonomisch'
    emotional: 'Cloud-Müdigkeit, Abo-Aversion, Autarkie-Versprechen sabotiert'
    structural: 'HA-Ökosystem reif, Wettbewerber-Lücke bei Akku-Steuerung, BKW-Boom DACH'
    enabler: 'AI-Tooling für Solo-Dev, ALKLY-Funnel (YouTube, 300 Blueprint-Kunden, 107 Warteliste)'
  moat:
    layer1_technical: 'HA-Entity-Layer + sekundengenaue Regelung + SetpointProvider-Interface'
    layer2_market: 'ALKLY-Brand, YouTube-Trust, Discord-Community, Beta-Pioneers, Installateurs-Netzwerk'
  kpiPyramid:
    hero: 'Euro-Wert (selbst-gesteuerte kWh × Bezugspreis)'
    beleg: 'Selbst verbraucht (kWh) + Selbst gesteuert (kWh)'
    delta: 'Monats-Ersparnis vs. optionale 7-Tage-Baseline (v1.1)'
  uxPrinciples:
    - 'Pull, nicht Push — Solalex piekst nie, antwortet wenn gefragt'
    - 'Dashboard: 2 Sekunden bis zur Kernaussage'
    - 'Charakter bei eigenem Tun, Fakten bei Zahlen — strikt getrennt'
  openDecisions:
    - 'Geschäftsmodell: Freemium (1 Gerät frei / Multi = Pro) vs. 30-Tage-Trial + dann kostenpflichtig — noch offen, Trial favorisiert nach Party-Mode-Runde'
    - 'Grace Period bei fehlgeschlagener monatlicher Lizenzprüfung — wie viele Tage Weiterbetrieb? (z.B. 14 Tage)'
  decisions:
    - 'Lizenzprüfung: 1x pro Monat statt nur einmalig bei Aktivierung — mit Graceful Degradation bei Offline'
  partyModeInsights:
    - 'Blueprint-Import-Wizard statt Clean Cut (P0 MVP)'
    - 'SetpointProvider-Interface in Woche 1 (Forecast-Naht)'
    - 'Regelungs-Watchdog mit Closed-Loop-Readback + Fail-Safe (P0 MVP)'
    - 'Solalex Lite gestrichen — HA Container/Core best-effort ohne Support'
    - 'Pre-Order-Phase Woche 5-6 als Intent-Beleg'
---

# Product Requirements Document - Solalex

**App Name:** Solalex
**Brand:** ALKLY (alkly.de)
**Tagline:** Steuert deinen Solar lokal und sekundengenau.
**Author:** Alex
**Date:** 2026-04-15

---

## Executive Summary

Du hast Tausende Euro in Solar investiert — und trotzdem fließt dein Strom für Centbeträge ins Netz. Der Spread ist brutal: ~30 ct/kWh Bezug, 0–8 ct/kWh Einspeisung. Jede Kilowattstunde, die dein Haus verlässt statt sie selbst zu verbrauchen, ist ein 4–5× Verlust. Dazu kommt: Hersteller-Apps sind träge und cloud-abhängig, bestehende Lösungen erfordern YAML-Expertise oder Abonnements, und keine Lösung am Markt steuert deinen Akku zuhause produktionsreif — lokal, ohne Cloud, ohne Abo.

**Solalex ändert das.** Lokal. Automatisch. Ab der ersten Sekunde.

**Solalex** ist ein Home Assistant Add-on das Wechselrichter, Akkus und Verbraucher sekundengenau steuert — nicht überwacht, nicht prognostiziert, sondern aktiv regelt. Ein PID-Regler mit Hardware-spezifischen Defaults erreicht ±5 W Genauigkeit. Ein Setup-Wizard mit Auto-Detection macht die Erstkonfiguration in unter 10 Minuten möglich. Danach vergisst du, dass Solalex läuft — bis du abends auf das Dashboard schaust und siehst, wie viel Euro Solalex heute für dich gesteuert hat.

**Kern-Prinzipien:**
- **100 % lokal im Betrieb** — null Cloud-Pings für Steuerung oder Daten, keine stille Telemetrie. Lizenzprüfung einmal pro Monat (mit Graceful Degradation bei vorübergehendem Offline-Status)
- **Pull, nicht Push** — Solalex piekst nie; das Dashboard antwortet in 2 Sekunden mit einer Euro-Zahl als Kern-Aussage
- **Sichtbarer Beweis** — dreistufige KPI-Pyramide: Euro-Ersparnis (Headline) → kWh selbst verbraucht und aktiv gesteuert (Beleg) → Monats-Delta vs. Baseline (optional)
- **Aktiv, nicht prognostisch** — v1 regelt reaktiv und sekundengenau; eine architektonische Naht für Forecast-Erweiterung ist ab Tag 1 vorhanden
- **Persönlichkeit ohne Lärm** — Solalex kommuniziert mit einem definierten Charakter, der Vertrauen schafft, ohne zu nerven. Fakten sprechen für sich, der Charakter spricht über sein eigenes Tun

### Was Solalex besonders macht

**1. Dein Strom bleibt bei dir.** Solalex steuert Wechselrichter und Akkus so, dass nahezu null Watt ans Netz verschenkt werden — automatisch, ohne dass du eingreifen musst. Was andere Lösungen nur beobachten oder prognostizieren, regelt Solalex aktiv.

**2. Alles was Home Assistant kennt, kennt Solalex.** Solalex baut keine eigenen Hardware-Treiber. Es nutzt die Geräte, die bereits in deinem HA als Entities existieren — und erbt damit die Kompatibilität von 2000+ Integrationen. Kein anderes Steuerungstool nutzt diese Hebelwirkung.

**3. Deine Batterie schaltet nie unkontrolliert ab.** Jeder Steuerbefehl wird per Closed-Loop-Verifikation geprüft. Bei Kommunikationsausfall greift ein automatischer Fail-Safe — Solalex steuert nie blind.

**4. Dein bestehendes Setup wird respektiert.** 300 bestehende Blueprint-Kunden werden nicht zum Neustart gezwungen. Ein Import-Wizard erkennt bestehende Konfigurationen und übernimmt sie als Solalex-Preset.

**5. Vertrauen durch Transparenz.** Öffentliche Roadmap auf GitHub, Community-Support auf Discord, Beta-Pioneers-Programm, ALKLY YouTube-Kanal als persönlicher Draht zum Entwickler. Solalex ist kein anonymes Produkt — es hat ein Gesicht.

### Geschäftsmodell

Einmalkauf über LemonSqueezy. Kein Abo. Das genaue Preismodell (Einmalkauf nach 30-Tage-Testversion vs. Freemium-Staffelung) wird durch Beta-Feedback validiert. Distribution über Custom Add-on Repository auf GitHub mit automatischen Updates über das HA Add-on Store System.

### Go-to-Market

Geschlossene Beta mit Bewerbung — nicht jeder bekommt Zugang. 20 ausgewählte Tester nach Hardware-Diversität und Skill-Level, mit wöchentlichem Feedback-Rhythmus. Launch erst nach Tester-Bestätigung „launch-ready". Danach öffentlicher Launch mit YouTube-Video, Newsletter an 300 Blueprint-Kunden und Early-Bird-Preis.

### Markt und Validierung

Geschätzt 500.000+ PV-Haushalte mit Home Assistant im DACH-Raum (bei ~3 Mio. PV-Anlagen DE und ~15–20 % HA-Affinität in der technik-affinen Teilmenge). Validiert durch 107 Wartelisten-Einträge mit Hardware-Daten, 300 bestehende Blueprint-Käufer und eine wachsende ALKLY-Reichweite (YouTube, Newsletter, Quiz).

**Zielmarkt:** Primär Balkonkraftwerk-Besitzer (1–3 kWp) mit Akku und HA. Sekundär Eigenheim-Optimierer (3–10+ kWp). DACH, deutschsprachig. Englisch ab v2.

## Projektklassifikation

| Dimension | Einordnung |
|---|---|
| **Projekttyp** | IoT Embedded / Edge Orchestrator |
| **Deployment** | Lokale Premise (HA Add-on, Docker-Container) |
| **Distribution** | HA Custom Add-on Repository (GitHub) |
| **Lizenzmodell** | Einmalkauf (Testversion vs. Freemium — offen, wird in Beta validiert) |
| **Domain** | Energy / Consumer PV |
| **Komplexität** | Hoch (Echtzeit-Regelung, Multi-Hersteller, kommerziell, Fail-Safe) |
| **Projektkontext** | Greenfield Code, Brownfield Planning |
| **Tech-Stack** | Python 3.13 + FastAPI, Svelte + Tailwind, SQLite, HA WebSocket API |
| **Zielmarkt** | DACH, deutschsprachig (Englisch ab v2) |

## Success Criteria

### User Success

**Hero-KPI (Produkt-Versprechen):** Euro-Wert der gesteuerten Ersparnis pro Haushalt. Das Dashboard zeigt in 2 Sekunden: „Solalex hat dir diesen Monat X € gesteuert."

**Beleg-KPI:** kWh selbst verbraucht + kWh selbst gesteuert — strikt getrennt, keine kontrafaktischen Schätzungen.

**Delta-KPI (ab v1.1, opt-in):** Monats-Ersparnis vs. optionale 7-Tage-Baseline.

**Attributions-Regel „selbst gesteuert":** Nur kWh, die Solalex aktiv zugewiesen hat — Akku-Lade-/Entladebefehle, Verbraucher-Aktivierung, WR-Drossel. Passiver Selbstverbrauch zählt separat.

**Bezugspreis in v1:** Nutzerseitig konfigurierbar (Default 30 ct/kWh, jederzeit anpassbar). Live-Tarife folgen in v1.5.

**Emotionale Aha-Momente:**
- Nach Setup: 0 W Einspeisung beim ersten Sonnenstand, Akku lädt sauber
- Täglich: Dashboard öffnen → Euro-Zahl ohne Scrollen, ohne Nachdenken
- Erste Woche: „Ich muss nicht mehr eingreifen — das läuft"

**Zielgröße pro Haushalt:** Im Median ≥ X €/Monat gesteuert. Konkreter X-Wert wird aus den ersten 10 Beta-Haushalten in Woche 6-7 abgeleitet (bewusst leer, bis reale Daten vorliegen).

### Business Success

**Launch (erste 30 Tage):**

| Metrik | Ziel |
|---|---|
| Aktive Nutzer | 100 (= installiert + Lizenz aktiviert) |
| NPS | > 8 |
| Setup-Abschluss | > 80 % in unter 10 Min |
| Support-Anfragen | < 2 pro Nutzer |
| Blueprint-Upgrade-Rate | > 20 % der 300 Kunden (≥ 60 Migrationen) |

**Wachstum (Monat 2-3):**

| Metrik | Ziel |
|---|---|
| Aktive Nutzer gesamt | 250 |
| Retention (30 Tage) | > 70 % |
| GitHub Stars | 50+ |

**Funnel:** Warteliste → Kauf ≥ 40 % Conversion bei Launch (≥ 65 Käufe aus 165 Wartenden).

### Technical Success

**Regelungs-Qualität:**
- Nulleinspeisung stabil auf Hoymiles/OpenDTU (±5 W) und Marstek Venus (±30 W Toleranz, lokale API-Latenz-abhängig)
- Akku-Steuerung produktionsreif für Marstek Venus 3E/D (Day-1, non-negotiable — Kern-Segment). Anker Solix + Generic HA Entity verschoben auf Beta-Week-6 / v1.5 (Amendment 2026-04-22)
- Kein Schwingen bei Lastsprüngen (Deadband + Rate Limiting + Moving Average)

**Stabilität & Sicherheit:**
- 24-Stunden-Dauertest ohne Absturz oder Schwingung
- Closed-Loop-Readback für jeden Steuerbefehl + Fail-Safe bei Kommunikationsausfall
- Wiederanlauf nach HA-/Add-on-Neustart < 2 Min
- 0 kritische Bugs (Crashes, Datenverlust) zum Launch

**Lizenzierung & Lokalität:**
- Monatliche Lizenzprüfung mit Graceful Degradation bei Offline
- Keine Cloud-Pings für Steuerung oder Daten
- Lizenz vor „Aktivieren"-Button im Wizard

**Diagnose:**
- Letzte 100 Regelzyklen + 20 Fehler + aktuelle Verbindungs-Stati stets einsehbar
- Export-Funktion für Bug-Reports

### Measurable Outcomes

**Beta-Gates (Launch-Voraussetzung, Woche 6-7):**
- Add-on-Installation erfolgreich ≥ 18 von 20 Testern
- Setup < 15 Min ≥ 80 % (Akzeptanzkriterium)
- Setup < 10 Min ≥ 50 % (Beta-Zielwert; 80 % ist Launch-Ziel)
- NPS > 8 bei Beta-Testern
- 0 offene kritische Bugs
- ≥ 12 von 20 Testern sagen explizit „würde kaufen"

**Launch-Gates:**
- YouTube-Launch-Video aufgenommen (inkl. Add-on-Installation)
- Newsletter an Blueprint-Kunden vorbereitet
- Custom Add-on Repository auf GitHub public
- Landing-Hinweis „Benötigt Home Assistant OS" prominent
- Beta-Tester bestätigen explizit „launch-ready"

## Product Scope

Kompakter Phasenüberblick. Detaillierte Strategy, Resource Requirements, Kipp-Reihenfolge und Risk Mitigation siehe **Project Scoping & Phased Development** weiter unten.

### MVP — v1 (Launch)

Reaktive Nulleinspeisung mit Adaptiver Regelungs-Strategie (Drossel / Speicher / Multi-Modus) · Akku-Pool-Abstraktion (v1 Gleichverteilung) · **Hardware Day-1 (3 Hersteller): Hoymiles/OpenDTU · Marstek Venus 3E/D · Shelly 3EM** · 1 WR + 1 SM + 1 Akku pro Instanz · Setup-Wizard (4 Schritte) mit Auto-Detection + Funktionstest · Dashboard mit Euro-Wert (REST + 1-s-Polling) · Diagnose-Tab · HA Add-on (Python 3.13 + FastAPI + Svelte + SQLite) · LemonSqueezy mit monatlicher Graceful-Degradation · Deutsch only.

**Geschäftsmodell offen (Beta-Entscheidung):** 30-Tage-Trial (Favorit) vs. Freemium 1-Gerät-Free/Multi-Pro.
**Bewusst NICHT im MVP:** MQTT Discovery · dynamische Tarife · Kaskaden · Multi-WR/Multi-Akku · Forecast · Englisch · Wallbox als gesteuerter Verbraucher · Anker Solix-Adapter · Generic-HA-Entity-Adapter · kryptografische Lizenz-Signatur · i18n-Infrastruktur · WebSocket-Live-Stream (REST + Polling in v1).

### Growth — v1.5 (Monat 2)

MQTT Discovery für native HA-Entities · Dynamische Stromtarife mit Preis-Gates (Tibber, aWATTar, EPEX Spot, Nordpool) · Optionale 7-Tage-Baseline für Delta-KPI · **Anker Solix-Adapter und Generic HA Entity-Adapter (aus v1 verschoben, Amendment 2026-04-22)** · WebSocket-Live-Stream-Upgrade falls Polling-Latenz beißt · optionale kryptografische Lizenz-Signatur (wenn Anti-Tamper-Bedarf klar wird).

### Growth — v2 (Monat 3–4)

Kaskaden-Modell (Überschuss + Entlade mit Gates) · Multi-WR + Multi-Akku mit SoC-Balance · Solar-Forecast über SetpointProvider · **Haus-Profile** (5 One-Click-Presets: Eigenverbrauch max / Autarkie / Tarife / Komfort / Winter) · Englische UI + i18n-Infrastruktur · Failsafe-Modus · Erweiterte Adapter-Module (Huawei, SMA, Growatt, Fronius).

### Vision — v3+

Peak-Shaving · Speed-Aware-Pool-Verteilung · Wallbox als First-Class-Verbraucher · NL-Internationalisierung (ab 2027) · Community Template Store · Installateur-Programm (B2B2C) · Optional Solalex Lite (Custom Integration für HA Container/Core) · CRA-Compliance-Framework (SBOM, Vulnerability-Process).

## User Journeys

### Journey 1: Marstek-Micha — Kern-Segment, Happy Path

**Opening Scene:** Sonntagnachmittag, 15:40 Uhr. Michael sitzt auf der Couch, Laptop auf dem Schoß. Draußen scheint die Sonne auf sein 8,6-kWp-Dach. Der Marstek CT002 hängt wieder fest — dritte Woche in Folge. Seine zwei Venus 3E zeigen im Hersteller-App-Dashboard widersprüchliche SoC-Werte. Er hat eine Stunde mit der Marstek-App probiert, dann 40 Minuten in YAML-Configs rumgewurschtelt. Jetzt: 1.600 W Sonne draußen, 0 W landet im Akku. Er schüttelt den Kopf: „Ich habe 4.000 Euro für zwei Akkus bezahlt, damit sie nichts tun?"

**Rising Action:** YouTube schlägt ein ALKLY-Video vor — „Marstek-Speicher in Home Assistant steuern". Drei Minuten später öffnet er die Solalex-Landingpage. Er liest: „Du integrierst. Solalex regelt." HA-OS-Check grün, Wartelisten-Platz frei. Er trägt sich ein, bekommt sofort eine E-Mail mit der Repository-URL. Add-on-Store → URL hinzufügen → 2 Klicks installiert. Setup-Wizard startet im HA-Frame. Auto-Detection findet den Shelly 3EM und beide Marstek Venus in 4 Sekunden. Er wählt Kauf, LemonSqueezy öffnet sich, zahlt, kommt zurück.

**Climax:** Funktionstest läuft. Solalex setzt ein Akku-Lade-Kommando von 300 W auf Venus 1 — Readback bestätigt: „300 W, Akku lädt." Dasselbe auf Venus 2. Micha atmet aus. Er klickt „Aktivieren". Neun Minuten nach Install zeigt das Dashboard: **0 W Einspeisung · Venus-Pool lädt mit 1.400 W · +0,08 € in der ersten Minute**.

**Resolution:** Am nächsten Abend schaut er beim Dashboard-Öffnen auf seine Euro-Zahl: „Heute gesteuert: 2,40 €". Keine Benachrichtigung, kein Pieksen, kein Support-Ticket. Er postet in seinem Forum-Thread: „Bin raus, Marstek läuft endlich." Am Sonntag darauf öffnet er Solalex einmal kurz — Zahl sieht gut aus — schließt wieder. Das ist der Punkt, an dem er weiß: das Ding macht seinen Job.

**Offenbarte Capabilities:** Auto-Detection Marstek Venus 3E/D (lokale API), Akku-Pool-Abstraktion für ≥ 2 Venus, Closed-Loop-Readback als Funktionstest, LemonSqueezy-Flow im Wizard, Dashboard-Euro-Zahl als 2-Sekunden-Kernaussage, „keine Pieks"-Default.

### Journey 2: Beta-Björn — Migration vom Blueprint, Happy Path

**Opening Scene:** Björn, 44, Bestandskunde seit 14 Monaten. Der Nulleinspeisungs-Blueprint läuft stabil, aber er hat drei selbst-gebaute Automationen für Anker Solix E1600 Nacht-Entladung dazu-gebastelt. Donnerstagmorgen kommt die Newsletter-Mail von Alex: „Blueprint-Kunde? Solalex ist live. Dein Rabatt-Code liegt bei."

**Rising Action:** Björn installiert das Solalex-Add-on über die Repository-URL. Beim ersten Start fragt der Wizard: „Wir haben 1 aktive Nulleinspeisungs-Blueprint-Automation erkannt. Importieren?" Er klickt Ja. Solalex liest die Input-Number-Helfer, übernimmt die Zielwerte, erkennt, dass die Entity `number.opendtu_limit_nonpersistent_absolute` bereits im Blueprint verwendet wurde und schlägt eben die als WR-Limit-Entity vor. Björn bestätigt. Schritt 2 Akku: Min-SoC 15 %, Max-SoC 95 %, Nacht-Entladung ab 20:00 Uhr — alles als Default-Vorschlag aus seiner bisherigen Konfiguration.

**Climax:** Der Wizard stellt den Wechsel explizit dar: „Blueprint-Automation wird deaktiviert. Solalex übernimmt ab Aktivierung die Regelung." Björn liest zweimal — das ist die Stelle, an der er misstrauisch war. Funktionstest läuft, Solalex setzt das WR-Limit testweise, Readback ok. Er klickt „Aktivieren". Parallel deaktiviert Solalex die Blueprint-Automation sauber.

**Resolution:** 48 Stunden später postet Björn im ALKLY-Discord #beta-pioneers: „Kürzeste Migration meines Lebens. Eigenbau-Automationen darf ich jetzt auch wegräumen." Für Björn heißt Erfolg: sein Setup ist schlanker als vorher. Er bewirbt sich zwei Wochen später für das Installateurs-Programm.

**Offenbarte Capabilities:** Blueprint-Import-Wizard mit Auto-Erkennung der Helfer und Entities, sanfter Cut (Blueprint-Deaktivierung durch Solalex), Default-Übernahme bestehender SoC-/Zeit-Werte, Rabatt-Code-Flow über LemonSqueezy, zweistufiger „bist du sicher"-Moment bei der Umschaltung.

### Journey 3: Neugier-Nils — Einsteiger, Happy Path

**Opening Scene:** Nils, 31, hat letzte Woche sein erstes Balkonkraftwerk mit Hoymiles HMS-800 aufgehängt. HA läuft auf einem Raspberry Pi 4, den er nach einem YouTube-Tutorial eingerichtet hat. Automationen? Nichts. YAML? Zweimal geöffnet, zweimal zugeklappt. Er entdeckt die Solalex-Landingpage über die Wartelisten-Mail. Oben steht gleich: „Benötigt Home Assistant OS." Er prüft HA → Einstellungen → „Raspberry Pi 4, HA OS". Passt.

**Rising Action:** Installation Schritt für Schritt nach Landingpage-Anleitung. Repository hinzufügen — Screenshots helfen. Add-on installieren → starten → Klick in die Sidebar. Wizard begrüßt ihn. Schritt 1 Hardware-Auswahl, drei Pfade. Er klickt Hoymiles. Auto-Detection findet OpenDTU + Entities. Live-Werte rechts: „AC-Leistung: 412 W" — die Zahl, die er vorher nur in der OpenDTU-UI gesehen hat. Er nickt: ja, das ist mein System.

**Climax:** Er hat keinen Akku — Wizard erkennt das und überspringt den Akku-Schritt lautlos. Schritt Smart Meter: Shelly 3EM wird gefunden. Funktionstest: Solalex setzt kurz das WR-Limit auf 50 W — er sieht die Einspeisung live fallen und wieder steigen. In diesem Moment passiert das Wichtigste der Journey: **er versteht zum ersten Mal, was da eigentlich passiert**. Nicht, weil jemand es erklärt hat, sondern weil er den Effekt seiner Hardware selbst gesehen hat.

**Resolution:** Nach 12 Minuten (Nils ist langsam, liest alles zweimal) läuft Solalex. Das Dashboard zeigt „0 W Einspeisung · Heute gesteuert: 0,14 €". Die Zahl ist klein — halbe Sonne am Nachmittag, kein Akku. Aber sie ist da. Er postet seinen ersten Community-Beitrag im ALKLY-Discord: „Bin Einsteiger, hat funktioniert." Eine Woche später bestellt er sich einen 3-kWh-Akku — weil er jetzt versteht, was der bringt.

**Offenbarte Capabilities:** Drei-Pfade-Wizard mit klarer Hardware-Wahl, Live-Werte neben jedem Sensor im Wizard, „kein Akku"-Pfad ohne tote Schritte, Funktionstest als sichtbarer Lern-Moment, Landing-Page-Check für HA-Installationstyp, Discord als niedrigschwelliger Einstieg.

### Journey 4: Alex Kly — Hersteller-Support, Beta-Phase

**Opening Scene:** Freitag, 09:15 Uhr. Alex öffnet Discord. In #solalex-beta: Björn hat gepostet: „Mein Solalex hängt seit gestern 22 Uhr. Akku lädt nicht mehr. Log sagt nichts." Zwei andere Tester haben mit „+1, gleiches Problem" reagiert. Alex schluckt, öffnet GitHub Issues — noch nichts gemeldet.

**Rising Action:** Alex schreibt in Discord: „Ich brauche bitte einen Diagnose-Export von allen drei — Solalex → Diagnose → Exportieren. Und den Add-on-Log aus HA → Settings → Add-ons → Solalex → Logs." Innerhalb einer Stunde hat er drei JSON-Exports und drei Log-Dumps. Gemeinsamer Nenner: alle drei laufen Marstek Venus 3E mit Firmware 1.14.8 — gestern Abend automatisch auf 1.15.0 upgedated. Seitdem antwortet die lokale API mit einem leicht geänderten JSON-Key.

**Climax:** Alex pusht in zwei Stunden einen Hotfix-Branch auf `alkly/solalex`. GitHub Actions baut, zehn Minuten später. Er postet in Discord: „Update ist im Store. Automatisch in 10 Minuten bei euch. Bitte bestätigen." Eine Stunde später: drei grüne Haken. Er öffnet die GitHub-Roadmap und ergänzt „Firmware-Version-Pinning + versionstolerante Adapter" als P1 für v1.1.

**Resolution:** Björn dankt öffentlich im Channel, Alex postet den Fix-Commit als Link, alle drei Tester schreiben einen kurzen Absatz fürs Launch-Video. Alex Kly bleibt das Gesicht von Solalex — kein anonymer Support, kein Ticket-System, keine Automated-Response. Für die Community ist das der Moment, an dem sie wissen: da sitzt ein Mensch dran, und der macht seinen Job.

**Offenbarte Capabilities:** Diagnose-Export-Funktion als Pflicht im MVP, Discord + GitHub Issues als getrennte Support-Kanäle mit klaren Rollen, Add-on-Store-Autoupdate als Fast-Hotfix-Pfad, strukturiertes Bug-Report-Template mit HW-/Firmware-Angaben, öffentliche Roadmap als Vertrauenssignal, Alex Kly als sichtbare Person hinter der Marke.

### Journey Requirements Summary

Aus den vier Journeys ergeben sich die Kern-Capabilities, die im PRD verbindlich sein müssen:

- **Setup & Onboarding:** Zwei-Pfade-Wizard (Hoymiles/OpenDTU · Marstek Venus) · Auto-Detection für OpenDTU, Shelly 3EM, Marstek Venus · Live-Werte neben jedem Sensor · Funktionstest als Lern-Moment und Readback-Validierung · Landing-Page-Check für Home Assistant OS. Anker + Generic-Pfad + Blueprint-Import folgen v1.5.
- **Regelung & Akku-Pool:** Multi-Venus als interner Pool (≥ 2 Einheiten ohne UX-Komplikation) · reaktive Nulleinspeisung · Akku-Schutz mit Min/Max-SoC · Nacht-Entladung in Zeitfenstern · „kein Akku"-Pfad ohne tote Wizard-Schritte
- **Dashboard & Kommunikation:** Euro-Zahl als 2-Sekunden-Kernaussage · sichtbarer Selbstverbrauch + selbst gesteuert als Beleg · Stille-statt-Pieks-Default
- **Diagnose & Support:** Diagnose-Tab mit letzten 100 Zyklen + Export-Funktion · Add-on-Logs als zweiter Datenpunkt · strukturiertes Bug-Report-Template
- **Community & Marke:** Discord #beta-pioneers + #solalex-support getrennt · GitHub Issues + öffentliche Roadmap · Alex Kly namentlich als Hersteller
- **Vertrieb & Lizenz:** LemonSqueezy-Flow innerhalb des Wizards · Rabatt-Code-Pfad für Blueprint-Kunden · Funktionstest vor Lizenzaktivierung · sanfter Blueprint-Cut (Deaktivierung + Werte-Übernahme als Default)

## Domain-Specific Requirements

Solalex operiert im DACH-Consumer-PV-Segment als Edge-Software auf Home Assistant. Domain-Constraints kommen aus drei Richtungen: **Regulatorik** (DACH-Energierecht, DSGVO, EU CRA), **Hardware-Safety** (kein Netz-Exportverlust, keine Hardware-Beschädigung) und **HA-Ökosystem** (Add-on-Architektur, Entity-Layer als alleiniger Integrationspunkt).

### Compliance & Regulatorik

- **Einspeise-Begrenzung:** Solalex respektiert die WR-/Netz-Limits, die in den HA-Entities vorgegeben sind — keine Überschreibung gesetzlicher oder technischer Caps. Für Balkonkraftwerke (DE/AT 800 W, CH abhängig) bleibt die Durchsetzung des Limits beim Wechselrichter; Solalex steuert nur innerhalb.
- **DSGVO:** Durch 100 %-lokal-Betrieb im MVP weitgehend entschärft. Einzige Drittland-/Online-Datenübertragung: Lizenzprüfung (Zahlungsanbieter TBD, LemonSqueezy als Merchant-of-Record-Favorit). Privacy-Policy-Passage in Launch-Dokumentation verbindlich.
- **EU Cyber Resilience Act (CRA, scharf ab 2027):** Solalex fällt als kommerzielles Software-Produkt mit digitalen Elementen unter den CRA. Ab 2027 vor-Inverkehrbringen-Anforderungen: Software-Bill-of-Materials (SBOM), Vulnerability-Handling-Prozess, CE-Konformität. Als **Future-Requirement** ab v2-Zeitraum einzuplanen.
- **Installations-Disclaimer:** Vor Lizenzaktivierung im Setup-Wizard muss der Nutzer explizit bestätigen: „Keine Garantien für Hardware-Schäden oder Stromausfälle." Als sichtbare Checkbox im Wizard (nicht versteckt in AGB).

### Safety & Hardware-Schutz

- **EEPROM-/Schreibzyklen-Schutz:** Wechselrichter und Akku-BMS haben herstellerspezifische Schreibzyklus-Limits (z. B. Hoymiles ~1 Mio., undokumentiert bei Marstek). Solalex implementiert **hardware-spezifisches Rate-Limiting** (Default ≤ 1 Schreibbefehl pro Device/Minute, per Adapter-Modul überschreibbar, persistent über Restart hinweg) um Hardware-Verschleiß zu vermeiden.
- **Closed-Loop-Readback:** Jeder Steuerbefehl wird per Readback auf Erfolgsquittung geprüft. Bei ausbleibender Antwort → Fail-Safe-Modus (deterministischer Safe-State, kein blindes Weiter-Steuern).
- **Kein unkontrollierter Netz-Export:** Rate Limiting und Deadband verhindern Aussteuerung über das Limit hinaus. Safe-State bei Kommunikations-Ausfall = letztes bekanntes WR-Limit halten, nicht freigeben.
- **Nutzer-Leitplanken:** Min/Max-SoC, Zeitfenster, Hardware-spezifische Defaults verhindern, dass Nutzer Solalex in schädliche Konfigurationen bringen (z. B. Tiefentladung unter Akku-Spezifikation).

### Technical Constraints

- **Home Assistant als alleiniger Entity-Layer:** Keine Direkt-Hardware-Kommunikation in v1 (kein Modbus, kein MQTT-Direkt, kein Cloud-API-Call zu Herstellern). Solalex liest und schreibt ausschließlich über HA-WebSocket-API. Dieser Constraint ist Moat und Architektur-Disziplin zugleich.
- **HA-Versions-Kompatibilität:** Solalex supportet die **aktuelle Home-Assistant-Version**. Supported-Range und Upgrade-Lag-Tolerance werden in der Release-Dokumentation festgelegt; Add-on-Isolation schirmt vor WebSocket-API-Breaks ab.
- **End-to-End-Regelungs-Latenz als Messgröße:** Sekunden-Regelung ist technisch machbar, aber die Latenz zwischen Solalex-Befehl und messbarem Effekt am Smart Meter variiert stark nach Hardware-Stack (Hoymiles/OpenDTU: 5–15 s; Anker Cloud: 30–90 s; Marstek lokale API: noch zu messen). **Solalex misst diese E2E-Latenz pro Device automatisch und loggt sie in SQLite.** Sie ist essenzielle Eingabe für hardware-spezifische Regelungs-Parameter (Deadband, Rate Limit, Reaktionsschwellen) und im Diagnose-Tab sichtbar.
- **Add-on-Isolation:** Crash-Resistenz gegenüber HA durch Container-Architektur. Solalex-Absturz beeinflusst HA nicht.

### Integration Requirements

- **Distribution:** Custom Add-on Repository auf GitHub (`alkly/solalex`), Auto-Updates via HA Add-on Store.
- **Lizenz-/Zahlungsflow:** Zahlungsanbieter TBD — LemonSqueezy als Favorit für EU-USt.-Merchant-of-Record. Lizenzprüfung einmalig online bei Aktivierung, danach monatlich mit Graceful Degradation offline-fähig.
- **MQTT Discovery (v1.5 oder v2):** Optionaler Upgrade-Pfad für native HA-Entities — Voraussetzung ist Mosquitto-Add-on beim Nutzer. Solalex publisht dann Topics, HA erstellt automatisch Sensoren/Schalter.

### Domain-Spezifische Risiken

| Risiko | Mitigation |
|---|---|
| Hersteller-Firmware-Update bricht lokale API (z. B. Marstek-JSON-Key) | Versionstolerante Adapter, Firmware-Version-Pinning, Hotfix-Pfad via Add-on-Store-Autoupdate |
| Hersteller-Cloud-API ändert sich/wird kostenpflichtig (Anker, v1.5) | Generic-HA-Entity-Adapter als Fallback (folgt v1.5); Abhängigkeit auf Landing transparent kommuniziert |
| HA-Kern-Update bricht WebSocket-API | Add-on-Isolation fängt Brüche ab, supported-Version-Range dokumentiert, Regressions-Testing nach HA-Release |
| Nutzer konfiguriert schädliche Werte (Tiefentladung, aggressives Limit) | Hardware-Defaults + Plausibilitäts-Checks im Wizard, Min/Max-Grenzen als Nutzer-Leitplanken |
| DACH-Regulatorik-Änderungen (BKW-Grenze, §14a-Pflichten) | Konfiguration über Dashboard, nicht hardcoded; schnelle Release-Zyklen über Add-on-Store |
| Haftung bei Hardware-Schaden | Vor-Aktivierung-Disclaimer, AGB-Verweis, optional: Produkthaftungs-Versicherung (Alex-Todo) |
| CRA-Compliance ab 2027 | Future-Requirement in v2-Planung; SBOM, Vulnerability-Process rechtzeitig etablieren |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Akku-Pool als Architektur-Abstraktion.** Beliebige Anzahl Speicher werden intern als logischer Pool gesteuert (Gesamt-SoC, -Leistung). v1 mit Gleichverteilung, v2 mit SoC-Balance. Kein anderes Consumer-PV-Tool abstrahiert Speicher in dieser Form — Speicher sind heute entweder einzeln, via Hersteller-App autark, oder manuell orchestriert.

**2. HA als alleiniger Entity-Layer + Moat.** Solalex baut bewusst keine eigenen Hardware-Treiber. Stattdessen Konsum von ≥ 2.000 HA-Integrationen als alleinige Quelle. Strategische Disziplin, nicht Workaround: solange HA eine Hardware kennt, kennt Solalex sie auch. Skaliert mit dem HA-Ökosystem, nicht mit eigener Treiber-Arbeit.

**3. Closed-Loop-Readback + Fail-Safe als durchgängiges Pattern.** Jeder Steuerbefehl wird per Readback auf Erfolgsquittung geprüft, deterministischer Safe-State bei Ausfall. Standard-Pattern aus Industrial-Control, in Consumer-PV-Tools bisher nur partiell oder gar nicht implementiert.

**4. End-to-End-Latenz-Messung als Regel-Parameter-Input.** Solalex misst pro Device die E2E-Latenz zwischen Befehl und messbarem Zähler-Effekt und nutzt diese empirische Messgröße für hardware-spezifische Deadband- und Rate-Limit-Parameter. Adaptive Regelung aus realem Verhalten statt hardcoded Defaults.

**5. SetpointProvider-Interface als Forecast-Naht.** v1 ist bewusst reaktiv ohne Forecast, aber die Interface-Naht für Forecast-Quellen ist ab Tag 1 architektonisch vorhanden. v2-Upgrade ohne Refactor.

**6. Attribution-Regel mit Event-Source-Flag.** Jeder Steuerbefehl wird mit `source: solalex | manual | ha_automation` getaggt. Erlaubt die saubere KPI-Attribution für „selbst gesteuert" statt kontrafaktischer Schätzungen. Ermöglicht den Hero-KPI Euro-Wert als ehrliche, prüfbare Zahl.

**7. Charakter/Persönlichkeit über Templates statt LLM.** Markenstimme im Dashboard (Charakter bei eigenem Tun, Fakten bei Zahlen) ohne Cloud-LLM. 100 %-lokal-Versprechen bleibt gewahrt.

**8. Adaptive Regelungs-Strategie je Setup-Typ.** Solalex erkennt im Setup-Wizard das Hardware-Regime und wählt die passende Regelungs-Logik automatisch — kein Config-Item, sondern Ergebnis der Erkennung:
- **Drossel-Modus** (reiner WR): WR-Limit regelt auf aktuellen Hausverbrauch, verlust-minimierend durch schnelle Abregelung, respektiert EEPROM-Schreib-Limits mit Deadband
- **Speicher-Modus** (WR + Akku): Akku-Pool nimmt Überschuss auf, WR-Limit bleibt auf Max; nur bei Akku-Voll → Übergang zu Drossel
- **Multi-Modus** (WR + Multi-Akku): Akku-Pool zuerst, dann WR-Drossel; v2 mit Verbraucher-Kaskade
- **Modus-Wechsel zur Laufzeit** deterministisch mit Hysterese: Akku-Voll → Drossel greift, Akku-knapp-voll keine Oszillation; Akku-leer nachts → kein Drossel-Anstieg
- Drossel und Speicher sind **zwei eigenständige Regelungs-Regime** mit unterschiedlicher Dynamik (WR 5–15 s, Akku 30–90 s) und unterschiedlicher Energie-Logik (Verlust vs. Verschiebung). Nutzer wählt Hardware, Solalex wählt Strategie.

### Market Context & Competitive Landscape

*(interne Analyse — keine externe Positionierung)*

Der DACH-Consumer-PV-Markt ist fragmentiert in vier Cluster:
- **Hersteller-Apps** (Cloud-abhängig, 15-90 s Latenz, unzuverlässig)
- **Open-Source-Energiemanager** (Auto-fokussiert, Akku als autark behandelt)
- **Cloud-SaaS-Optimizer** (Abo-Modell, Cloud-Pflicht)
- **DIY-Node-RED / Blueprint** (Bastler-Ebene, Flickenteppich)

Keine der Lösungen kombiniert: **lokal + Akku-first + Multi-Hardware über HA-Entities + Einmalkauf + Sekunden-Regelung mit Safety-Layer**. Die HA-Entity-Layer-Strategie ist der strukturelle Unterschied — nicht Feature-Inflation, sondern Architektur-Disziplin. Nach außen wird diese Innovation aus eigener Stärke kommuniziert („Du integrierst. Solalex regelt."), nicht als Vergleich.

### Validation Approach

| Innovation | Validierung |
|---|---|
| Akku-Pool | ≥ 3 Marstek-Beta-Tester mit 2+ Venus-Einheiten bestätigen saubere Lade-/Entladeverteilung |
| HA-Entity-Layer-Moat | Hardware-Diversität in v1-Beta (Marstek + Hoymiles + Shelly) demonstriert Hebelwirkung; weitere Hersteller (Anker, SMA, Huawei, Growatt) in v1.5 / v2 als Skalierungs-Beleg |
| Closed-Loop-Readback + Fail-Safe | 24 h Dauertest unter echten Lastsprüngen, 0 unbehandelte Exceptions, keine unkontrollierte Einspeisung |
| E2E-Latenz-Messung | Automatische Messdatei-Generierung pro Beta-Tester, konsolidierte Analyse nach Woche 7 → finale hardware-spezifische Defaults im Release-Build |
| SetpointProvider-Interface | Mock-Forecast-Quelle in Beta als Proof-of-Plumbing (kein echter Forecast in v1, nur Interface-Kontrakt) |
| Attribution-Regel | Cross-Check „selbst gesteuert"-KPI gegen manuell gerechneten Akku-/WR-Log bei 3 Beta-Testern |
| Charakter-Templates | A/B-Prompt bei Beta-Testern: „Stört dich die Tonalität, oder baut sie Vertrauen?" im Woche-7-Tally |
| Adaptive Regelungs-Strategie | Zweigeteiltes Beta-Gate: Drossel-Modus stabil ±5 W bei Hoymiles (Nils-Setup) UND Speicher-Modus stabil ±30 W bei Marstek Venus (Micha-Setup) plus explizit sauberer Modus-Wechsel „Akku-voll → Drossel" ohne Oszillation |

### Risk Mitigation (Innovation-specific)

- **Akku-Pool-Fehlverteilung:** Fallback-Modus = 1 Hauptspeicher aktiv, andere statisch
- **HA-Entity-Layer-Abhängigkeit:** Supported-Version-Range klar definiert, eigene Regressions-Tests nach HA-Releases, Add-on-Isolation fängt Breaks ab
- **Latenz-Messung liefert widersprüchliche Daten (z. B. bei Cloud-API-Ausreißern):** Fallback auf hardware-spezifische Defaults aus Dokumentation/Community; Ausreißer-Filterung vor Parameter-Berechnung
- **SetpointProvider-Naht nicht genutzt:** Zero-Cost in v1 — die Naht kostet nichts, Forecast kommt erst in v2
- **Attribution zu streng oder zu lasch:** Nutzer-Opt-in-Toggle im Dashboard erlaubt alternative „alle kWh zählen"-Sicht, Default bleibt die strenge Regel
- **Charakter-Templates wirken abgedroschen:** Templates sind konfigurierbar, können pro Update nachgeschärft werden; bei Beta-Ablehnung schlichter „Neutral-Mode" als Fallback
- **Modus-Wechsel-Oszillation** (WR+Akku im Grenzbereich Akku-knapp-voll): Hysterese-Schwellen (z. B. Drossel aktiv ab SoC ≥ 97 %, deaktiv erst bei SoC ≤ 93 %), plus Mindest-Verweildauer pro Modus

## Edge-Orchestrator Specific Requirements

### Project-Type Overview

Solalex wird trotz der Einordnung **iot_embedded** kein klassisches Embedded-Device. Die präzisere Kategorie ist **Edge Orchestrator**: Software, die auf vorhandener Edge-Infrastruktur (Home Assistant auf Raspberry Pi 4 / NUC) läuft und dort vorhandene IoT-Geräte orchestriert — ohne eigene Firmware, eigene Hardware oder Direkt-Kommunikation. Dieser Charakter prägt alle technischen Entscheidungen: kein Geräte-Provisioning, kein Power-Profile, kein OTA-für-Firmware. Stattdessen: Container-Runtime-Disziplin, Entity-basiertes Steuerungsmodell und Add-on-Store-Update-Pfad.

### Hardware Compatibility & Abstraction

- **Unterstützte Hardware nur via HA-Entities.** Ein Gerät ist kompatibel, sobald es in HA eine passende Entity-Signatur aufweist (z. B. `number.opendtu_limit_nonpersistent_absolute` für WR-Limits, `sensor.solarbank_e1600_soc` für Akku-SoC).
- **Adapter-Modul-Pattern (Amendment 2026-04-22).** Pro Hersteller/Modell ein Python-Modul in `backend/src/solalex/adapters/<vendor>.py` mit hardcoded Entity-Pattern-Liste, Steuerung-Semantik (WR-Limit / Akku-Setpoint / Charge-Discharge-Toggle), Default-Regelungs-Parameter (Deadband, Rate Limit, EEPROM-Schutz-Intervall) und Readback-Timing-Semantik (Timeout, Async-Readback-Support). Abstract-Interface in `adapters/base.py`. **Kein externer JSON-Template-Layer** in v1; Erweiterung = neues Python-Modul.
- **Auto-Detection pro Wizard-Durchlauf:** Solalex scannt `get_states`-Response gegen alle bekannten Templates, ordnet Matches den Geräten zu, zeigt Live-Werte zur Bestätigung.
- **Supported Day-1:** Hoymiles/OpenDTU, Marstek Venus 3E/D, Shelly 3EM. Nach Beta-Week-6 / v1.5: Anker Solix, Generic HA Entity (manueller Pfad). Reduktion beschlossen im Amendment 2026-04-22 (Solo-Dev-Scope, Waitlist-Signal Marstek = 44 % Kern-Segment).

### Connectivity & Integration Protocol

- **HA WebSocket API als alleiniger Kanal.** Endpoint: `ws://supervisor/core/websocket`. Auth via `SUPERVISOR_TOKEN` (automatisch im Add-on-Container verfügbar).
- **Subscription-Pattern:** `subscribe_trigger` auf `state_changed`-Events der konfigurierten Entities (Echtzeit, kein Polling).
- **Call-Pattern:** `call_service` für Steuerbefehle (`number.set_value`, `switch.turn_on/off`, `button.press`).
- **Reconnect-Logik:** Exponentielles Backoff bei WebSocket-Abbruch (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, Re-Subscribe nach Reconnect.
- **MQTT Discovery in v1.5** als optionaler Nebenkanal zur Entity-Bereitstellung (Solalex publisht Topics auf Mosquitto-Add-on, HA erstellt Sensoren/Schalter).

### Security Model

- **Container-Isolation:** Add-on-Container läuft neben HA, getrennter Prozessraum. Crash beeinflusst HA nicht, umgekehrt ebenfalls.
- **Supervisor-Token:** Einziger Auth-Mechanismus zu HA. Wird vom Supervisor bereitgestellt, läuft automatisch mit Container-Lebenszyklus.
- **Keine ausgehende Cloud-Kommunikation im Betrieb.** Einzige Online-Kommunikation: LemonSqueezy-Lizenzprüfung (einmalig bei Aktivierung, monatlich Re-Validierung mit Graceful Degradation). Kein Telemetry, kein Analytics-Ping, kein Crash-Report ohne explizites User-Opt-in.
- **Lizenz-Validierung:** Lizenz-Key in `/data/license.json`, LemonSqueezy-Online-Check bei Aktivierung und monatlich (14-Tage-Grace bei Offline). **Keine kryptografische Signatur in v1** — gestrichen im Amendment 2026-04-22 (die 14-Tage-Grace macht Offline-Crack ohnehin trivial; Anti-Tamper-Signatur als v1.5-Option dokumentiert, wenn Bedarf klar wird).
- **Installations-Disclaimer** (siehe Domain-Requirements) als sichtbare Checkbox vor Aktivierung.
- **Keine Admin-Funktionen außerhalb HA.** Solalex nutzt HA-Nutzer-Kontext, macht keine eigene Nutzer-Verwaltung.

### Update Mechanism

- **HA Add-on Store als alleiniger Update-Kanal.** GitHub Actions baut Docker-Images multi-arch (amd64, aarch64), GitHub Container Registry hostet. Custom Add-on Repository `alkly/solalex` als Quelle.
- **Auto-Update durch Nutzer aktivierbar** (Standard: manuell, um Kontrolle zu behalten; Empfehlung in Doku: auto aktivieren).
- **Backup vor Update:** SQLite `/data/solalex.db` + `/data/license.json` + `/data/templates/` werden vor jedem Update in `/data/.backup/vX.Y.Z/` gespiegelt (letzte 5 Stände).
- **Rollback-Pfad:** Bei fehlgeschlagenem Start nach Update → Add-on bleibt in Halt-Status, Nutzer kann manuell via Add-on-Store eine ältere Version zurückinstallieren; `/data/.backup/` wird beim Start der älteren Version automatisch gespiegelt.
- **Version-Compatibility-Matrix:** `addon/config.yaml` deklariert supported HA-Version-Range. Bei inkompatibler HA-Version zeigt Add-on-Store Install-Warnung.

### Container Runtime

- **Base Image:** HA Add-on Base Image (Alpine 3.19), auf Python 3.13 aufgestockt.
- **Ressourcen-Budget:**
  - Memory (idle): ≤ 150 MB RSS
  - Memory (Peak beim Setup-Wizard mit Live-Werten): ≤ 300 MB RSS
  - CPU (idle): ≤ 2 % auf Raspberry Pi 4
  - CPU (Regelungs-Burst): ≤ 15 % auf Raspberry Pi 4
- **Persistenz:** `/data/` (Add-on-Standard-Volume, überlebt Updates und Restart), enthält `solalex.db`, `license.json`, `templates/`, `.backup/`, `logs/` (rotiert auf 10 MB / 5 Dateien).
- **Ingress:** HA-Ingress-URL rendert Svelte-UI im HA-Frame. Sidebar-Eintrag mit Icon. Kein direkter Port-Expose nach außen.

### Implementation Considerations

- **Solo-Dev mit AI-Tooling:** Alex entwickelt mit Claude Code. Test-First mit pytest, Komponenten-Isolation für adapter-spezifische Logik (ein Python-Modul pro Adapter).
- **Timeline:** Woche 0 Spike, Wochen 1-6 Build, Wochen 6-7 Beta, Woche 8 Launch.
- **Anti-Schuldenregeln:** Kein eigener Hardware-Treiber trotz Versuchung; keine Telemetry-Server-Infrastruktur zum Start; kein Custom-Gerätetyp in v1 (nur kuratierter Katalog).
- **Haupt-Risiken:** HA-WebSocket-API-Breaking-Change nach HA-Release (Mitigation via Regressions-Tests); Hersteller-Firmware-Update (Mitigation via versionstolerante Adapter); Solo-Dev-Überlastung (Mitigation via Kipp-Reihenfolge im MVP-Scope).

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP-Typ: Problem-Solving MVP.** Nicht Experience-, Platform- oder Revenue-MVP. Der MVP muss drei Probleme lösen:
1. **Marstek-Micha's Kern-Schmerz** — stabile Multi-Venus-Regelung ohne Cloud
2. **Balkon-Benni's Fundament** — zuverlässige Nulleinspeisung mit Hoymiles/OpenDTU (Anker folgt v1.5)
3. **Solalex's Glaubwürdigkeit als kommerzielles Produkt** — Funktionstest, Lizenz, Disclaimer, 24h-Test

**Philosophie: Stability over Features.** Jede Feature-Entscheidung prüft sich gegen: „Beschädigt das die Stabilität des Kerns?" Wenn ja, raus. Ein stabiles kleines MVP schlägt ein fragiles großes.

**Anti-Ziele:**
- Kein Feature nur, weil es innovativ klingt
- Keine Ergänzung, die die Kipp-Liste nicht überlebt
- Keine halben Features (Forecast-Stub, Multi-WR-Attrappe, etc.)

### Resource Requirements

- **Solo-Dev Alex Kly** mit AI-Tooling (Claude, Cursor). Keine externe Entwicklung, kein Budget für bezahlte Features.
- **9-Wochen-Timeline:** Woche 0 Spike, Wochen 1–6 Build, Wochen 6–7 Beta, Woche 8 Launch.
- **20 Beta-Tester** als externe Validierungs-Ressource (gefiltert aus 165 Wartenden, 30 Pre-Auswahl als Puffer).
- **Discord + GitHub Issues** als Support-Infrastruktur — keine eigene Support-Mannschaft, Alex skaliert sich über die Community.

### MVP Feature Set (Phase 1 — v1)

**Core Journeys supported (v1):** Marstek-Micha · Neugier-Nils · Alex Kly (Support). **Beta-Björn (Anker-Blueprint-Migration) rückt auf v1.5** wegen verschobenen Anker-Adapter + Blueprint-Import-Scope (Amendment 2026-04-22). Journey 2 bleibt als Narrativ/Vision im Dokument — Björn kann ab v1.5 nahtlos migrieren.

**Must-Have Capabilities (nicht kippbar):**
- Reaktive Nulleinspeisung mit Closed-Loop-Readback + Fail-Safe
- Adaptive Regelungs-Strategie (Drossel / Speicher / Multi-Modus, deterministische Modus-Wechsel mit Hysterese)
- Akku-Pool-Abstraktion (v1 Gleichverteilung) für Marstek Venus (Day-1). Anker Solix Multi-Device nach v1.5.
- Hardware-Day-1 (3 Hersteller): Hoymiles/OpenDTU, Marstek Venus 3E/D, Shelly 3EM. Anker Solix + Generic HA Entity auf Beta-Week-6 / v1.5 (Amendment 2026-04-22).
- Setup-Wizard mit Auto-Detection, Live-Werten, Funktionstest
- Hardware-spezifische Default-Regelungs-Parameter via Adapter-Module + E2E-Latenz-Messung
- Diagnose-Tab mit letzten 100 Regelzyklen
- Dashboard mit Euro-Wert als 2-Sekunden-Kernaussage
- Funktionstest + Installations-Disclaimer vor Lizenz-Aktivierung
- LemonSqueezy-Integration (Kauf + monatliche Re-Validation mit Graceful Degradation)
- Add-on-Container (Python 3.13 + FastAPI + Svelte + SQLite) im HA Add-on Store
- Deutsch only

**Must-Have Infrastructure (nicht Code, aber Launch-Voraussetzung):**
- GitHub `alkly/solalex` (privat → public zum Launch)
- Discord #solalex-beta + #solalex-support (getrennt)
- GitHub Issues + öffentliche Roadmap
- Landing-Page mit Home-Assistant-OS-Check
- YouTube-Launch-Video

### Post-MVP Features

**Phase 2 — v1.5 (Monat 2 nach Launch):**
- MQTT Discovery → native HA-Entities
- Dynamische Stromtarife mit Preis-Gates (Tibber, aWATTar, EPEX Spot, Nordpool)
- 7-Tage-Baseline für Delta-KPI
- Blueprint-Import-Wizard (falls in MVP gekippt)
- Diagnose-Export-Funktion (falls in MVP gekippt)
- Character-Templates (falls in MVP gekippt)

**Phase 3 — v2 (Monat 3–4):**
- Kaskaden-Modell: Überschuss-Verteilung + Entlade-Priorisierung mit Gates
- Multi-WR + Multi-Akku (SoC-Balance)
- Solar-Forecast über SetpointProvider-Naht
- Haus-Profile: 5 One-Click-Presets (Eigenverbrauch max / Autarkie / Tarife / Komfort / Winter) als Abkürzung für Einsteiger und als ergänzender Layer für Power-User
- Englische UI
- Failsafe-Modus (deterministischer Safe-State + Auto-Recovery)
- Erweiterte Adapter-Module (Huawei, SMA, Growatt, Fronius)

**Phase 4 — v3+ (Vision):**
- Peak-Shaving (§14a-EnWG-kompatibel)
- Speed-Aware-Pool-Verteilung
- Wallbox als First-Class-Verbraucher
- NL-Internationalisierung (0 ct Einspeisung ab 2027)
- Community Template Store
- Installateur-Programm (B2B2C)
- Solalex Lite (optionale Custom Integration für HA Container/Core)
- CRA-Compliance-Framework (SBOM, Vulnerability-Process)

### Kipp-Reihenfolge bei Zeitnot (Wochen 5–7)

Wenn Solo-Dev-Bandbreite nicht reicht, wird in dieser Reihenfolge gekippt:

| Kipp-Rang | Was wird gekippt | Fallback | Nachziehen in |
|---|---|---|---|
| 1 | Blueprint-Import-Wizard | manuell-JSON-Import + Doku | v1.5 |
| 2 | Diagnose-Export-Funktion | HA-Panel-Log-Download | v1.5 |
| 3 | Character-Templates | Neutral-Mode (Dashboard ohne Charakter-Zeilen) | v1.1 |
| 4 | E2E-Latenz-Messung im UI sichtbar | nur SQLite-Log, keine UI-Anzeige | v1.1 |

**Nicht kippbar (Safety + Glaubwürdigkeit):**
- Closed-Loop-Readback + Fail-Safe
- Marstek + Hoymiles + Shelly Day-1 (3 Hersteller, Amendment 2026-04-22)
- Funktionstest + Installations-Disclaimer vor Lizenz
- Euro-Wert im Dashboard
- LemonSqueezy-Integration
- 24h-Dauertest

### Risk Mitigation Strategy (Scope-Ebene)

**Technical Risks:**
- **Marstek lokale API instabil oder undokumentiert** (Hauptrisiko des Projekts): Spike-Phase Woche 0 MUSS die Marstek-Kommunikation end-to-end validieren, bevor Wochen 1–6 beginnen. Firmware-Pin im Adapter-Modul + versionstolerante Key-Behandlung. Fallback bei Scheitern: Hoymiles-only-Launch, Marstek rückt nach v1.5.
- **Marstek lokale API-Latenz (v1):** Hardware-spezifische Deadband-Defaults (±30 W-Toleranz), keine ±5 W-Zusage für Marstek im Marketing — Marstek bekommt eigene Toleranz-Kommunikation. (Anker Cloud-API-Latenz als v1.5-Thema.)
- **HA-WebSocket-API-Breaking-Change während Launch:** Container-Isolation schützt, supported-Range dokumentiert, Hotfix-Pfad via Add-on-Store binnen 24 h demonstriert in Journey 4.

**Market Risks:**
- **Warteliste → Kauf-Conversion < 40 %:** Early-Bird-Preis für erste 50 Käufer, YouTube-Marstek-Video als SEO-Hebel (44 % der Warteliste), Blueprint-Kunden-Newsletter, Discord-Hype-Sequenz in Launch-Woche.
- **Geschäftsmodell-Entscheidung (Trial vs. Freemium) kippt Funnel:** Beta-Feedback entscheidet, beide Modelle als Toggle im Lizenz-Backend möglich, finale Entscheidung vor Launch-Announcement.
- **NPS < 8 wegen Setup-Komplexität:** ≥ 5 Einsteiger in Beta als Härtetest, Setup-Simplification-Fenster vor Launch.

**Resource Risks:**
- **Solo-Dev-Ausfall:** Keine Team-Mitigation möglich — strukturelles Risiko, das im PRD transparent bleibt. Mitigation auf Community-Ebene: Discord als Peer-Support, Installateure als zukünftige Multiplikatoren.
- **Scope-Creep durch Discord-Anfragen während Beta:** Kipp-Reihenfolge + „Nicht im MVP"-Liste öffentlich auf GitHub-Roadmap, Alex sagt strukturell Nein und verweist auf öffentliche Priorisierung.
- **Beta-Tester-Ausfälle (< 15 von 20 aktiv):** Pre-Auswahl von 30 Kandidaten als Puffer, Kick-off Zoom sichert persönliches Commitment, wöchentliches Tally-Feedback als Anker.

## Functional Requirements

### Installation & Lizenz

- **FR1:** Nutzer kann Solalex als HA Add-on über das Custom Repository `alkly/solalex` installieren.
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „Home Assistant OS" vor dem Download-Schritt. Home Assistant Supervised, Home Assistant Container und Home Assistant Core sind ausdrücklich nicht unterstützt (Amendment 2026-04-23, KISS-Cut: Support-Matrix auf eine known-good Host-Konfiguration beschränkt).
- **FR3:** Nutzer erwirbt die Lizenz aus dem Setup-Wizard heraus (Weiterleitung zu LemonSqueezy, Rückkehr in den Wizard).
- **FR4:** Nutzer bestätigt vor Lizenz-Aktivierung den Installations-Disclaimer als sichtbare Checkbox.
- **FR5:** Solalex verifiziert die Lizenz einmalig online bei Aktivierung und monatlich erneut, mit Graceful Degradation bei Offline-Status.
- **FR6:** Bestandskunden können einen Rabatt-Code (Blueprint-Migration) im Kaufflow einlösen.

### Setup & Onboarding

- **FR7:** Nutzer wählt im Setup-Wizard zwischen zwei Hardware-Pfaden: Hoymiles/OpenDTU, Marstek Venus. Anker + Generic-Pfad folgen v1.5.
- **FR8:** Solalex erkennt kompatible HA-Entities automatisch für die Day-1-Hardware (OpenDTU, Marstek Venus 3E/D, Shelly 3EM). Anker Solix + Generic-Pfad nach Beta-Week-6 / v1.5.
- **FR9:** Nutzer sieht Live-Werte neben jedem erkannten Sensor im Wizard zur Bestätigung.
- **FR10:** Solalex überspringt den Akku-Schritt lautlos, wenn kein Akku erkannt wird.
- **FR11:** Solalex führt vor Aktivierung einen Funktionstest durch (testweises Setzen von WR-Limit oder Akku-Setpoint, Readback-Prüfung).
- **FR12:** Solalex erkennt und importiert bestehende Nulleinspeisungs-Blueprint-Automationen inklusive Helfer-Werte (mit expliziter Deaktivierung des alten Blueprints bei Aktivierung). *Kippbar → Fallback manueller JSON-Import.*

### Regelung & Steuerung

- **FR13:** Solalex wählt die Regelungs-Strategie je erkanntem Hardware-Setup automatisch (Drossel / Speicher / Multi-Modus).
- **FR14:** Solalex regelt im Drossel-Modus reaktiv auf Nulleinspeisung per WR-Limit.
- **FR15:** Solalex lädt im Speicher-Modus Akkus bei PV-Überschuss und entlädt zur Grundlast-Deckung innerhalb der konfigurierten SoC-Grenzen.
- **FR16:** Solalex wechselt zur Laufzeit deterministisch zwischen Modi mit Hysterese (z. B. Drossel aktiv ab SoC ≥ 97 %, deaktiv erst bei SoC ≤ 93 %).
- **FR16a (Amendment 2026-04-25 Surplus-Export):** Wenn am betreffenden Wechselrichter `device.config_json.allow_surplus_export = true` gesetzt ist, ersetzt der Mode-Switch SPEICHER → DROSSEL bei Pool-Voll durch SPEICHER → EXPORT. EXPORT setzt das WR-Limit auf den Hardware-Max-Wert (`device.config_json.max_limit_w`), wodurch die PV-Erzeugung eingespeist wird, statt am MPPT (PV-intern oder Akku-intern) abgeregelt. Default `allow_surplus_export = false` preserve das ursprüngliche Nulleinspeisungs-Verhalten — strenge Klasse-1-User (Anlagen ohne Inbetriebnahme-Anmeldung beim Netzbetreiber) bleiben unbeeinflusst. Im MULTI-Modus mit Toggle ON ruft die Cap-Branch-Logik `_policy_export` statt `_policy_drossel` (kein Mode-Switch — MULTI bleibt MULTI). Implementiert in Story 3.8.
- **FR17:** Solalex verifiziert jeden Steuerbefehl per Closed-Loop-Readback.
- **FR18:** Solalex geht bei Kommunikations-Ausfall in einen deterministischen Fail-Safe-Zustand (letztes bekanntes Limit halten, nicht freigeben).
- **FR19:** Solalex respektiert hardware-spezifische Rate-Limits zur EEPROM-Schonung (Default ≤ 1 Schreibbefehl pro Device/Minute, per Adapter-Modul überschreibbar, persistent über Restart).
- **FR20:** Nutzer kann Nacht-Entlade-Zeitfenster konfigurieren.

### Akku-Management

- **FR21:** Solalex abstrahiert mehrere Akkus als internen Pool mit Gleichverteilung in v1 (Marstek Venus Multi). Anker Solix + Generic-Pool-Support nach Beta-Week-6 / v1.5.
- **FR22:** Nutzer konfiguriert Min-SoC und Max-SoC pro Akku-Setup.
- **FR23:** Solalex zeigt SoC pro Einzel-Akku und aggregiert für den Pool.

### Monitoring & Dashboard

- **FR24:** Nutzer sieht im Dashboard den aktuellen Euro-Wert der gesteuerten Ersparnis als 2-Sekunden-Kernaussage.
- **FR25:** Nutzer sieht die Beleg-KPIs (kWh selbst verbraucht + kWh selbst gesteuert) getrennt ausgewiesen, nicht aggregiert.
- **FR26:** Nutzer kann den Bezugspreis (Default 30 ct/kWh) im Dashboard jederzeit anpassen.
- **FR27:** Solalex attribuiert Steuerbefehle mit Event-Source-Flag (`solalex` / `manual` / `ha_automation`) und nutzt dies als Basis der KPI-Berechnung.
- **FR28:** Nutzer sieht den aktuellen Regelungs-Modus (Drossel / Speicher / Multi) im Dashboard.
- **FR29:** Solalex zeigt einen sichtbaren „aktiver Idle-State"-Zustand, wenn keine Steuerung nötig ist („Alles im Ziel. Überwache weiter.").
- **FR30:** Solalex zeigt Charakter-Zeilen bei eigenem Tun und Fakten bei Zahlen (strikt getrennt). *Kippbar → Fallback Neutral-Mode.*

### Diagnose & Support

- **FR31:** Solalex protokolliert die letzten 100 Regelzyklen (Zeitstempel, Sensorwert, gesetztes Limit, Latenz, Modus).
- **FR32:** Solalex zeigt die letzten 20 Fehler/Warnungen mit Klartext-Beschreibung.
- **FR33:** Solalex zeigt die aktuellen Verbindungs-Stati (HA WebSocket, konfigurierte Entities, Lizenz-Status).
- **FR34:** Solalex misst die End-to-End-Regelungs-Latenz pro Device automatisch (Befehl-Auslösung → messbarer Effekt am Smart Meter) und loggt sie in SQLite.
- **FR35:** Nutzer kann Diagnose-Daten als strukturierten Bug-Report exportieren. *Kippbar → Fallback HA-Panel-Log-Download.*
- **FR36:** Solalex stellt ein strukturiertes Bug-Report-Template in GitHub Issues bereit (Hardware-/Firmware-Felder, Log-/Diagnose-Export-Platzhalter).

### Updates & Administration

- **FR37:** Solalex wird über den HA Add-on Store aktualisiert (manueller oder Nutzer-aktivierter Auto-Update).
- **FR38:** Solalex sichert vor jedem Update `solalex.db`, `license.json` und `templates/` in `/data/.backup/vX.Y.Z/` (letzte 5 Stände).
- **FR39:** Nutzer kann bei fehlgeschlagenem Update manuell auf eine ältere Version zurückrollen; Solalex stellt `.backup/` automatisch wieder her.
- **FR40:** Solalex unterstützt die aktuelle Home-Assistant-Version und deklariert die supported Range in `addon/config.yaml`.

### Branding & UI-Identität

- **FR41:** Solalex nutzt in allen UI-Flächen (Dashboard, Setup-Wizard, Diagnose-Tab, Config) durchgängig das ALKLY-Design-System: ALKLY-Farben als Primär-/Sekundär-/Akzent-Palette, DM Sans als Schrift, einheitliche Spacing-/Radius-/Elevation-Tokens.
- **FR42:** Solalex erscheint im HA-Sidebar mit ALKLY-Branding (Icon + Name „Solalex by ALKLY").
- **FR43:** UI ist im HA-Ingress-Frame eingebettet und rendert konsistent im ALKLY-Light-Look. **Keine HA-Theme-Adaption in v1** (Amendment 2026-04-23: Dark-Mode aus Scope gestrichen; Revisit in v1.5 möglich).

## Non-Functional Requirements

### Performance

- **Regel-Zyklus-Dauer:** ≤ 1 s vom Sensor-Event bis Command-Dispatch (interne Verarbeitung).
- **Dashboard Time-to-First-Data-Display:** ≤ 2 s ab Klick in Sidebar.
- **Setup-Wizard Auto-Detection:** ≤ 5 s bei durchschnittlichem HA-Setup.
- **Funktionstest-Durchführung:** ≤ 15 s (inkl. Readback).
- **Memory Footprint:** ≤ 150 MB RSS im Idle, ≤ 300 MB RSS im Setup-Wizard-Peak.
- **CPU Footprint (Raspberry Pi 4):** ≤ 2 % im Idle, ≤ 15 % im Regelungs-Burst.
- **E2E-Regelungs-Latenz:** hardware-abhängig (5–90 s je Device-Stack), kein Zusagen-Wert — aber **Messung ist Pflicht** (FR34). Solalex garantiert nicht Latenz, Solalex garantiert Transparenz über Latenz.

### Reliability & Availability

- **Wiederanlauf-Zeit:** ≤ 2 Min nach HA-/Add-on-Neustart (bis Regelung wieder aktiv).
- **24-h-Dauertest als Launch-Gate:** 0 unbehandelte Exceptions, keine Schwingungen, keine unkontrollierten Einspeisungen unter simuliertem Lastprofil (`load_profile_sine_wave.csv`, 0–3.000 W).
- **0 kritische Bugs** zum Launch (Definition: Datenverlust ODER unkontrollierter Stromfluss ODER Add-on-Absturz ohne Wiederanlauf < 2 min).
- **Fail-Safe bei Kommunikationsausfall:** Deterministischer Safe-State (letztes bekanntes WR-Limit halten, nicht freigeben).
- **Lizenz-Offline-Toleranz:** 14 Tage Graceful-Period, danach Funktions-Drossel (aber kein Stopp ohne Vorwarnung).

### Security

- **Container-Isolation:** HA Add-on Sandbox, keine externen Port-Expositionen (nur über HA Ingress).
- **Auth:** SUPERVISOR_TOKEN als alleiniger Mechanismus gegenüber HA. Keine eigene Nutzer-Verwaltung.
- **Lizenz-Validierung:** LemonSqueezy-Online-Check bei Aktivierung und monatlich, Lizenz-Key in `/data/license.json`. Kryptografische Signatur gestrichen im Amendment 2026-04-22 (v1.5-Option).
- **Ausgehende Verbindungen:** nur HTTPS (LemonSqueezy). Kein Plaintext, keine ungeprüften Endpunkte.
- **Keine Telemetry ohne Opt-in.** Zero default-tracking.
- **Installations-Disclaimer** als sichtbare Checkbox vor Lizenz-Aktivierung.

### Privacy & Data Protection

- **100 % lokaler Betrieb:** Alle Regelungs-, Sensor- und Konfigurationsdaten bleiben in `/data/` auf dem HA-Host.
- **Einzige Drittland-Interaktion:** LemonSqueezy-Lizenzprüfung (USA-Server, DSGVO-konformes Vertragsverhältnis als Merchant of Record).
- **Datenminimierung:** Lizenzprüfung überträgt nur Lizenz-Token + Add-on-Version, keine Geräte- oder Verbrauchsdaten.
- **Privacy-Policy** verbindlich in Launch-Dokumentation, im Wizard verlinkt.
- **DSGVO-Compliance** durch lokalen Betrieb + keine personenbezogenen Daten im Standard-Flow.

### Usability & Design Quality

- **Setup-Ziel:** ≥ 80 % der Nutzer schließen Setup in < 10 Min ab (Launch).
- **Dashboard-Kernaussage** (Euro-Wert) in < 2 Sekunden erfassbar ohne Scrollen, ohne Interaktion.
- **Design-Quality-Ziel (operationalisiert „richtig coole und schöne UI"):**
  - Durchgängiges ALKLY-Design-System: Farb-Tokens (Primär/Sekundär/Akzent), DM Sans, einheitliche Spacing/Radius/Elevation
  - Mikrointeraktionen (Transitions, Hover-States, Loading-Feedback) für wahrnehmbare Qualität
  - Max. eine primäre Aktion pro Bildschirm — keine UI-Überfrachtung
  - Responsive Layouts (Desktop + Tablet-Breite im HA-Ingress)
  - **Messbar:** ≥ 4 von 5 Beta-Testern geben explizit Feedback „sieht hochwertig aus" oder vergleichbar (Woche-7-Tally)
- **Pull nicht Push:** Keine proaktiven Benachrichtigungen außerhalb des Dashboards (kein E-Mail, kein Push, kein HA-Notification).
- **Fakten bei Zahlen, Charakter bei Tun:** Strikt getrennt in Copy-Richtlinien. Glossar verbindlich: Akku (nicht Batterie/Speicher), Wechselrichter/WR (bei Erstnennung ausgeschrieben), Smart Meter, Setup-Wizard.

### Integration Reliability

- **HA WebSocket Reconnect:** Exponentielles Backoff (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, automatisches Re-Subscribe.
- **HA-Version-Kompatibilitäts-Matrix** in `addon/config.yaml` deklariert; Install-Warning bei inkompatibler HA-Version.
- **Adapter-Modul-Versionierung** mit Firmware-Pinning bei Marstek (v1) und Anker (ab v1.5); versionstolerante Key-Behandlung im Adapter-Code.
- **MQTT (v1.5):** mindestens QoS 1, Retained Messages für Discovery, Mosquitto-Add-on als Voraussetzung.
- **GitHub Actions Build-Pipeline:** Multi-Arch (amd64, aarch64), automatisierte Release-Builds bei Tag-Push.

### Maintainability

- **Code-Sprachregel:** UI/Kommunikation in Deutsch, Code-Kommentare in Englisch.
- **Modulare Architektur:** ein Python-Modul pro Adapter (`adapters/hoymiles.py`, `adapters/marstek_venus.py`, `adapters/shelly_3em.py` in v1; `adapters/anker_solix.py`, `adapters/generic.py` ab v1.5); Core-Regelung in `controller.py` hardware-agnostisch (Mono-Modul mit Enum-Dispatch, Amendment 2026-04-22).
- **Test-Coverage:** ≥ 70 % für Regelungs-Kern-Logik, ≥ 50 % gesamt. Alle Adapter haben Integration-Tests mit Mock-HA.
- **Strukturiertes Logging** (JSON-Format), alle Exceptions mit Kontext.
- **Code-Verständlichkeit:** Solo-Dev-Kriterium — jedes Modul in ≤ 30 Min nachvollziehbar.

### Observability

- **Strukturiertes Logging** in `/data/logs/` (JSON, rotiert 10 MB / 5 Dateien).
- **Add-on-Logs** zusätzlich im HA-Log-Panel sichtbar (Standard-Add-on-Verhalten).
- **Diagnose-Export** als versioniertes JSON-Schema (`solalex-diag-v1.json`).
- **E2E-Latenz-Messung** automatisch pro Device, persistent in SQLite (`latency_measurements`-Tabelle).
- **Regelungs-Zyklen mit Source-Flag** (`solalex / manual / ha_automation`) für saubere KPI-Attribution (FR27).
- **Health-Status** pro konfigurierter HA-Entity (letzte erfolgreiche Kommunikation, Readback-Erfolgsquote).

### Scalability (selektiv)

- **Hardware-Abdeckung:** Adapter-Modul-Pattern muss ≥ 10 weitere Hersteller (Huawei, SMA, Growatt, Fronius, Zendure, …) in v2–v3 erlauben ohne Core-Refactor — ein Python-Modul pro Hersteller in `adapters/`, Core-Controller hardware-agnostisch. (Umformuliert im Amendment 2026-04-22 — vorher: „Device-Template-System als JSON-Schema".)
- **Kundenwachstum:** LemonSqueezy-Lizenz-API trägt skalierungs-unproblematisch (Merchant-of-Record-Infrastruktur).
- **Community-Skalierung:** Discord + GitHub Issues als selbsttragende Peer-Support-Kanäle — Alex skaliert nicht linear mit Kundenzahl.
- **Bewusst nicht skaliert:** Server-Infrastruktur, Multi-Tenancy, Datenbank-Sharding — Solalex ist und bleibt single-user-local.

### Accessibility (selektiv, nicht Launch-Gate)

- **Tastatur-Navigation** für alle Wizard-Schritte.
- **Farbkontrast** im ALKLY-Design-System ≥ WCAG 2.1 AA für Text auf Hintergrund.
- **Post-MVP-Ziel:** WCAG 2.1 AA gesamt (nicht Launch-Gate).
- **Nicht im MVP:** Screen-Reader-Optimierung, Sprachsteuerung, High-Contrast-Mode.

### Localization

- **MVP:** Deutsch only.
- **v2:** Englisch als erste Zielsprache (NL-Markt folgt).
- **Infrastruktur:** hardcoded deutsche Strings in Svelte-Komponenten in v1 — i18n-Infrastruktur auf v2 verschoben (Amendment 2026-04-22). Wenn Englisch kommt, folgt ein gezieltes Refactor (`$t('key')`-Wrapper + `locales/de.json` + `locales/en.json` in ein dedicated Story).
