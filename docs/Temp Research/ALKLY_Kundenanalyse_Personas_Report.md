# ALKLY Solalex — Kundenanalyse, Personas & Funnel-Report

**Datengrundlage:** 6 Umfragen, 498 individuelle Datensätze  
**Analyse-Stand:** 15.April 2026  
**Erstellt für:** Alexander Kly, ALKLY

---

## Executive Summary

Über alle Datenquellen hinweg zeigt sich ein klares Bild: Die ALKLY-Zielgruppe besteht aus PV-Besitzern mit Batteriespeicher, die ihren Eigenverbrauch maximieren wollen, aber an der technischen Komplexität der Steuerung scheitern. Der mit Abstand stärkste Trend in der Warteliste ist das **Marstek-Segment** — 44% aller Wartenden nutzen einen Marstek-Speicher und haben massive Probleme mit dessen Steuerung. Die Zahlungsbereitschaft liegt robust bei **25€ Median (einmalig)**, das Abo-Modell wird von **96% klar abgelehnt**. YouTube ist der dominierende Akquise-Kanal, ConvertKit-Newsletter der stärkste Wartelisten-Treiber.

---

## 1. Datenquellen-Überblick

| Datenquelle | n | Zeitraum | Zielgruppe |
|---|---|---|---|
| Warteliste Überschussmanager | 165 | Jun 2025 – Apr 2026 | Potentielle Solalex-Käufer |
| Onboarding v3 Blueprint | 120 | Aug 2024 – fortlaufend | Neue Blueprint-Kunden |
| Betatest v1 | 17 | Jun 2024 | Early Adopter |
| Betatest v2 | 20 | Jun 2024 | Early Adopter |
| Update-Survey Bestandskunden | 53 | Jul 2024 | Aktive Blueprint-Nutzer |
| Quiz / Lead Magnet | 123 | Jun 2025 – fortlaufend | Top-of-Funnel Interessenten |
| **Gesamt** | **498** | | |

---

## 2. Warteliste Überschussmanager — Deep Dive (n=165)

Die Warteliste ist die wichtigste Datenquelle, da sie die konkrete Kaufabsicht für Solalex repräsentiert.

### 2.1 Wachstumsdynamik

Die Warteliste zeigt exponentielles Wachstum seit Anfang 2026:

| Monat | Neue Anmeldungen | Kumulativ |
|---|---|---|
| Jun 2025 | 31 (Launch-Spike) | 31 |
| Jul–Okt 2025 | 17 | 48 |
| Nov–Dez 2025 | 1 | 49 |
| Jan 2026 | 12 | 61 |
| Feb 2026 | 23 | 84 |
| Mär 2026 | **48** | 132 |
| Apr 2026 (Halbmonat) | 30 | **162** |

**Interpretation:** Die Winterpause (Nov–Dez) ist typisch für den PV-Markt. Ab Januar explodiert die Nachfrage — getrieben durch Saisonstart und vermutlich das Marstek-Phänomen (neue Speicher werden verbaut, Nutzer suchen Steuerungslösungen). März 2026 ist der stärkste Monat bisher, und April liegt auf Kurs für den neuen Rekord.

**Akquise-Kanal:** 112 von 114 getrackten Zugriffen kommen über **ConvertKit** (Newsletter-Funnel). Der Newsletter ist damit der mit Abstand wichtigste Treiber für die Warteliste.


### 2.2 Home-Assistant-Erfahrungslevel

| Level | n | Anteil |
|---|---|---|
| Einsteiger | 63 | 38% |
| Fortgeschritten | 94 | 57% |
| Profi | 11 | 7% |

**Schlüsselinsight:** Fast 4 von 10 Interessenten stufen sich als **Einsteiger** ein. Das ist ein gewaltiges Signal für die UX-Anforderungen — Solalex muss ohne YAML, Node-RED oder tiefe HA-Kenntnisse funktionieren. Die Fortgeschrittenen sind zwar in der Mehrzahl, aber das Produkt darf sie nicht mit Simplizität langweilen, sondern muss „einfach UND tiefgehend" sein.


### 2.3 PV-Anlagengröße

| Segment | n | Anteil |
|---|---|---|
| < 1 kWp (Mini-BKW) | 15 | 9% |
| 1–3 kWp (typisches BKW) | 67 | **41%** |
| 3–10 kWp (großes BKW / kleine Dachanlage) | 53 | **32%** |
| > 10 kWp (Dachanlage) | 28 | 17% |

**Schlüsselinsight:** 73% der Warteliste haben Anlagen zwischen 1 und 10 kWp — das ist der Sweet Spot. Bemerkenswert: Fast ein Fünftel hat bereits >10 kWp Dachanlagen. Diese Gruppe ist größer als erwartet und zeigt, dass Solalex nicht nur ein Balkonkraftwerk-Tool ist. 49% der Wartenden haben Anlagen >3 kWp, was den ursprünglichen Fokus auf reine Balkonkraftwerke deutlich erweitert.


### 2.4 Wechselrichter-Markt

| Hersteller | n | Anteil |
|---|---|---|
| Hoymiles | 42 | **27%** |
| Anker | 16 | 10% |
| Growatt | 9 | 6% |
| Huawei | 8 | 5% |
| Deye | 6 | 4% |
| SMA | 5 | 3% |
| Fronius | 4 | 3% |
| APsystems | 3 | 2% |
| Sonstige (38% einzelne) | 59 | 38% |

**Hoymiles ist klar #1** mit über einem Viertel Marktanteil im Wartelisten-Segment. Anker auf Platz 2 ist interessant, da Anker sowohl WR als auch Speicher in einem System liefert. Die „Sonstigen" 38% verteilen sich auf Dutzende Marken — ein Zeichen dafür, dass der Hardware-agnostische Ansatz von Solalex (Steuerung via HA-Entities) genau richtig ist.

**WR aus Home Assistant steuerbar?** Ja: 115 (72%) | Nein: 44 (28%). Das bedeutet: 28% der Warteliste braucht noch Integration-Hilfe, bevor Solalex überhaupt greifen kann.


### 2.5 Akku-Speicher — Die Marstek-Überraschung

| Speicher-Marke | n | Anteil |
|---|---|---|
| **Marstek** | **73** | **44%** |
| Anker Solix | 15 | 10% |
| Zendure | 11 | 7% |
| DIY / Selbstbau | 6 | 4% |
| BYD | 4 | 2% |
| EcoFlow | 2 | 1% |
| Kein Akku | 2 | 1% |
| Sonstige (kWh-Angaben, QCells, Enphase, etc.) | 52 | 31% |

**DAS Schlüsselinsight des gesamten Reports:** Fast die Hälfte aller Wartelisten-Interessenten nutzt einen **Marstek-Speicher**. Marstek ist erst seit Ende 2025 populär geworden (1 Anmeldung im Juni 2025 → 26 allein im März 2026). Die Marstek-Welle ist der primäre Wachstumstreiber der Warteliste.

**Warum?** Marstek-Speicher (Venus 3E, Venus D, CT002) haben massive Steuerungsprobleme: Cloud-Abhängigkeit, WLAN-Abbrüche, unzuverlässige Regelung, keine native HA-Integration. Die Nutzer suchen verzweifelt nach einer lokalen Lösung.

**Marstek-Segment-Profil (n=73):**

- HA-Level: Einsteiger 33%, Fortgeschritten 66%, Profi 3%
- PV-Größe: Gleichmäßig verteilt (1–3 kWp: 34%, 3–10 kWp: 36%, >10 kWp: 25%)
- Bisherige Steuerung: 42% haben keine, 56% haben bereits eine (aber sind offensichtlich unzufrieden)
- Preisbereitschaft: Ø29€, Median 25€
- Timeline: Explosionsartiger Anstieg ab Jan 2026 (7 → 18 → 26 → 16 Anmeldungen/Monat)


### 2.6 Gewünschte Verbraucher-Steuerung

| Verbraucher | n | Anteil |
|---|---|---|
| Spül-/Waschmaschine | 81 | **49%** |
| Wallbox / E-Auto | 59 | **36%** |
| Klima / Split-Klima | 54 | 33% |
| Wärmepumpe | 44 | 27% |
| Heizstab | 38 | 23% |
| Pool | 37 | 22% |

**Zusätzlich genannt (Freitext, n=52):** Trockner (am häufigsten), Infrarotheizung, E-Bike Ladung, Server/Netzwerk, Pumpen/Bewässerung, Krypto-Miner (2x), Brauchwasserwärmepumpe.

Die Top-3 (Waschmaschine, Wallbox, Klima) signalisieren klar, dass Solalex über reine Nulleinspeisung hinausgehen muss — die Nutzer wollen **intelligente Verbraucher-Priorisierung**.

**Verbraucher bereits in HA steuerbar?** Ca. 43 sagten klar „Ja", 16 „Nein", Rest „Teilweise" oder spezifische Geräte. Viele nutzen Smart Plugs (Shelly, Tasmota, Zigbee) als Steuerungsbrücke.


### 2.7 Bisherige Überschusssteuerung

| Status | n |
|---|---|
| Hat noch **keine** Steuerung | 73 (47%) |
| Hat **bereits** eine Steuerung | 79 (51%) |

Von denen mit bestehender Steuerung (n=77 mit Angabe):

| Lösung | n |
|---|---|
| **EVCC** | 11 |
| Eigenbau HA-Automation | 7 |
| Node-RED | 4 |
| ALKLY Blueprint | 3 |
| OpenDTU on Battery | 3 |
| Zendure App | 3 |
| Anker App | 2 |
| Sonstige / unklar | 43 |

**Interpretation:** EVCC ist der einzig relevante Wettbewerber — aber mit 11 von 79 nutzen es nur 14% der „Vorgesteuerten". Die meisten basteln selbst oder nutzen die (unzureichende) Hersteller-App. Das bestätigt: Es gibt keinen dominanten Marktführer im Segment „Überschusssteuerung für BKW + kleines PV".


### 2.8 Feature-Bewertung (Skala 1–5, n=144)

| Feature | Durchschnitt | Median | ≥4 (Wichtig+Sehr wichtig) |
|---|---|---|---|
| Nulleinspeisung + dyn. Einspeisebegrenzung | **4.23** | 5 | **83%** |
| 100% Lokal / keine Cloud | **4.23** | 5 | **79%** |
| Einfaches Setup (kein YAML/Node-RED) | **4.10** | 5 | **73%** |
| Lokale Sekundenregelung (±5W) | 3.85 | 4 | 67% |
| Einfache Geräte-Priorisierung | 3.22 | 3 | 43% |
| Multi-WR synchron steuern | 2.44 | 3 | 38% |

**Klares Ranking der Prioritäten:**
1. **Nulleinspeisung funktioniert zuverlässig** — Kernversprechen, non-negotiable
2. **100% Lokal** — Gleichauf, bestätigt die Deep-Research-Erkenntnis
3. **Einfaches Setup** — Dritte Säule, passt zum Einsteiger-Anteil
4. Sekundenregelung — Nice-to-have, aber nicht ganz so kritisch
5. Geräte-Priorisierung — Mittlere Priorität, v2-Feature
6. Multi-WR — Nischenbedarf, niedrigste Priorität


### 2.9 Preisbereitschaft & Geschäftsmodell

**Einmalpreis (n=138):**

| Preisklasse | n | Anteil | Kumuliert (≥) |
|---|---|---|---|
| 0–10€ | 16 | 12% | 100% |
| 10–20€ | 24 | 17% | 88% |
| 20–30€ | 37 | **27%** | 71% |
| 30–50€ | 22 | 16% | 44% |
| 50–100€ | 28 | **20%** | 28% |
| 100€+ | 11 | 8% | 8% |

Median: **25€** | Durchschnitt: 45€ (durch Ausreißer verzerrt)

**Optimaler Preispunkt:** Bei 25€ sind 71% der Befragten „im Boot". Bei 30€ noch 44%. Bei 20€ steigt man auf 88%, verliert aber Revenue. **25–30€ ist der Sweet Spot.**

**Monatlich (n=140):** 41% sagen klar 0€ — sie wollen kein Abo. Nur 4% der Warteliste wählen „Abo & Updates" als Modell (vs. **96% „Einmaliger Kauf & Updates"**). Das Abo-Modell ist damit praktisch tot.

**Cross-Analyse Preis × HA-Level:**

| Level | Ø Preis | Median |
|---|---|---|
| Einsteiger | ~30€ | 30€ |
| Fortgeschritten | 39€ | 25€ |
| Profi | 24€ | 20€ |

Profis zahlen weniger — sie kennen Alternativen und Open-Source. Einsteiger sind bereit, mehr zu zahlen, weil sie die Zeitersparnis höher bewerten.


### 2.10 Top-Ärgernisse (Freitext-Analyse, n=146)

Die Freitext-Analyse der Warteliste ergibt folgende Cluster:

| Ärgernis-Cluster | Häufigkeit | Beispiel-Zitate |
|---|---|---|
| **Strom verschenken / Netzeinspeisung** | 28% | „verschenke zu viel an den Energielieferer", „Solarstrom geht im Netz verloren" |
| **Akku-Management / Lade-Logik** | 27% | „Laden und Entladen funktioniert nicht richtig", „gegenseitiges laden der Speicher" |
| **Trägheit / Latenz der Steuerung** | 6% | „Trägheit der Ansteuerung über Anker cloud", „WLAN-Latenzen beim Marstek" |
| **Noch keine Steuerung** | 6% | „Das ich keine habe :-)", „Ist nicht da" |
| **Komplexität / fehlendes Wissen** | 3% | „YAML :-)", „Keinen Plan wann ich was einschalten sollte" |
| **Cloud-Abhängigkeit** | 3% | „Cloud Anbindung", „Ich möchte das es ohne Hersteller App läuft" |
| **Multi-WR / Multi-Speicher** | 2% | „Zwei Batterien parallel steuern", „Zwei Akkus synchron steuern" |

**Marstek-spezifische Ärgernisse (aus Freitext destilliert):**
- „Extrem häufige Ausfälle der Datenübertragung zu Marstek"
- „Der Marstek kommuniziert via WLAN. Das führt zu Latenzen"
- „CT002 hängt sich alle 6 Wochen auf"
- „6 Marstek Venus E mit dem messbaren Überstrom optimal zu laden"
- „Marstek KI-Unterstützung funktioniert nicht zufriedenstellend"
- „Venus nicht mehr über den CT002 gesteuert"
- „Marstek sauber in mein System integrieren"


### 2.11 Feature-Wünsche (Freitext-Analyse, n=137)

Die destillierten Top-Wünsche aus allen Freitext-Antworten:

1. **Nulleinspeisung / Eigenverbrauch maximieren** — Grunderwartung, vielfach wiederholt
2. **Dynamische Stromtarife berücksichtigen** (Tibber, aWATTar) — Akku günstig laden, teuer entladen; mindestens 8 explizite Nennungen
3. **Solar-Forecast / Prognosen einbeziehen** — SoC-Ziel erreichen, Akku nicht vorzeitig vollmachen; 6+ Nennungen
4. **Mehrere Akkus / Multi-Speicher** — Insbesondere DC+AC Speicher-Kombinationen; 7+ Nennungen
5. **Verbraucher-Priorisierung mit Bedingungen** — „Heizung nur bei Anwesenheit", „Auto-SoC als Prioritätsfaktor"
6. **MQTT-Anbindung** — 3 explizite Nennungen
7. **Baukastenprinzip** — „von Basis zu Erweiterungen, um schnell Grundfunktionen nutzen zu können"
8. **Fehlerzustände erkennen** — „Anlage in sicheren Zustand überführen"

---

## 3. Onboarding Blueprint-Kunden (n=120)

### 3.1 Profil der Blueprint-Käufer

**HA-Erfahrung:**

| Erfahrung | n |
|---|---|
| < 1 Monat | 27 (24%) |
| 1–6 Monate | 21 (18%) |
| ~1 Jahr | 47 (41%) |
| 2+ Jahre | 6 (5%) |

42% der Blueprint-Kunden haben weniger als 6 Monate HA-Erfahrung — sie brauchen intensive Onboarding-Hilfe. Die größte Gruppe (~1 Jahr) kennt HA, ist aber kein Profi.

**Akquise-Kanal (n=90):**

| Kanal | n | Anteil |
|---|---|---|
| **YouTube** | 36 | **40%** |
| Google/Suche | 21 | 23% |
| Facebook | 2 | 2% |
| HA Forum/Community | 1 | 1% |
| Sonstige | 30 | 33% |

**YouTube ist der #1 Kundenmagnet.** Über ein Drittel aller Blueprint-Kunden kommen direkt über Alex' YouTube-Videos.

**PV-Hardware (n=113):**

WR: Hoymiles (34) und Anker (34) dominieren gleichauf, gefolgt von Growatt (16). Akku: Anker Solix (34), Growatt NOAH (18), Zendure (5).

**Größter Wunsch (n=110):**

| Wunsch | Anteil |
|---|---|
| Kein Strom verschenken | 30% |
| Akku optimal laden/entladen | 17% |
| Eigenverbrauch maximieren | 9% |
| Automatisierung ohne Eingriff | 5% |

**Aktuelle Probleme (n=101):**

| Problem | Anteil |
|---|---|
| Akku-Logik (Laden/Entladen) | 17% |
| Anker/Cloud-Steuerung | 13% |
| WR/Integration fehlt | 9% |
| Setup schwierig | 5% |

**Warum ALKLY Blueprint?** Top-Gründe: „HA bereits im Einsatz", „Hardware-unabhängig", „erschien nach Recherche als sinnvollste Lösung", „YouTube-Video gesehen", „keine Ahnung von YAML", „keine andere gefunden".


### 3.2 Zusammenfassung Blueprint-Segment

Der typische Blueprint-Kunde hat seit ca. einem Jahr Home Assistant, nutzt ein Balkonkraftwerk mit Anker oder Hoymiles WR, hat einen Anker Solix Speicher, und kam über YouTube. Sein Kernproblem: Er verschenkt Strom und bekommt die Akku-Steuerung nicht zuverlässig hin.

---

## 4. Quiz / Lead Magnet (n=123)

Das Quiz erreicht den breitesten Top-of-Funnel und zeigt, wo potenzielle Kunden stehen.

### 4.1 Reifegrad der Nutzer

**Nulleinspeise-Level Score:** Ø69 von 125 (Median 65). Die Verteilung zeigt eine klassische Normalverteilung mit leichter Rechtsschiefe — die meisten sind „auf dem Weg", aber noch nicht am Ziel.

**Aktuelle Steuerungsmethode:**

| Methode | n | Anteil |
|---|---|---|
| **Aktuell noch nichts** | 55 | **45%** |
| Home Assistant | 20 | 16% |
| Shelly App | 15 | 12% |
| Andere Hardware | 13 | 11% |
| Anker/Zendure App | 12 | 10% |
| OpenDTU on Battery | 6 | 5% |

**45% haben noch GAR KEINE Steuerung** — das ist der größte Pool an potentiellen Neukunden.

**WR steuerbar?** Ja, lokal: 54 (44%) | Nur Cloud: 34 (28%) | Nein: 33 (27%)

**Akku vorhanden?** Kein Akku: 39 (32%) | < 2 kWh: 24 (20%) | 2–5 kWh: 31 (25%) | > 5 kWh: 27 (22%)

### 4.2 Wichtigkeit lokale Steuerung

| Bewertung | n | Anteil |
|---|---|---|
| **Extrem wichtig** | 58 | **48%** |
| Nice to have | 44 | 36% |
| Gar nicht | 19 | 16% |

Fast die Hälfte sagt „extrem wichtig" — bestätigt das Wartelisten-Signal.

### 4.3 Was bremst die Nutzer?

| Bremse | n |
|---|---|
| **Zu wenig HA-Wissen** | 53 |
| **Keine Übersicht, wie loslegen** | 50 |
| Keine WR-Kontrolle | 33 |
| Akku zu klein | 23 |
| PV zu klein | 20 |
| Bei mir läuft alles | 16 |
| Keine Live-Daten | 14 |

**Die Top-2-Bremsen sind Wissen und Orientierung, nicht Hardware.** Das ist eine massive Chance: Solalex kann beide Probleme gleichzeitig lösen — durch ein einfaches Setup und ein Dashboard, das Orientierung bietet.

### 4.4 Überstrom-Nutzung

| Nutzungsart | n |
|---|---|
| Noch nicht / keine Verbraucher | 71 |
| E-Auto | 22 |
| Wasser-Boiler | 21 |
| Pool/Teich | 14 |
| Split-Klima | 13 |

71 von 123 (58%) nutzen ihren Überstrom noch gar nicht — ein enormes Potential.

### 4.5 Größter Traum (Freitext, Auswahl)

„So viel Solarstrom selber nutzen und so wenig wie möglich verschenken", „100% Autarkie mit BKW", „komplette Autarkie", „Akkuspeicher und eine intelligente Steuerung", „Eine gute Nulleinspeise-Steuerung wäre schön", „Das wenig Strom ins Netz abgegeben wird — vor einem Jahr war das egal, da hatten wir noch den alten Zähler der sich rückwärts drehte."

---

## 5. Bestandskunden-Zufriedenheit (n=53)

**Zufriedenheit (1–10): Ø7.2, Median 8**

| Score | n |
|---|---|
| 9–10 (Promoter) | 19 (36%) |
| 7–8 (Zufrieden) | 16 (30%) |
| 5–6 (Neutral) | 14 (26%) |
| 1–4 (Unzufrieden) | 3 (6%) |

Nur 6% sind unzufrieden — das Blueprint-Produkt hat eine solide Basis. Aber 26% im neutralen Bereich zeigen Verbesserungspotential — genau diese Gruppe ist die Solalex-Migrationszielgruppe.

**Beliebteste Features:** „Schnelle Anpassung", „die Ganztagsgeschichte", „dass ich durch die Helfer alles genau verfolgen kann"

**Top-Herausforderungen:** „Die richtigen Entitäten zu finden", „bekomme es nicht hin", „Jeder Speicher ist anders und jede Stromerfassung ist unterschiedlich", „die Einspeisung vermeiden"

**Feature-Wünsche der Bestandskunden:** „Null-Einspeisung mit Lade-Priorität", „Steuerung von mehreren Wechselrichtern", „Anpassungswert von weiteren Faktoren abhängig machen"

---

## 6. Personas

Basierend auf der datengestützten Cluster-Analyse definieren sich fünf klar unterscheidbare Personas.

---

### Persona 1: „Marstek-Micha" — Der frustrierte Aufrüster
**Segment-Größe: ~44% der Warteliste (73 von 165)**

**Demografisches Profil:** Mann, 35–55 Jahre, technisch interessiert aber kein Entwickler. Hat ein Eigenheim mit bestehender PV-Anlage (typisch 3–10 kWp Dachanlage). Hat kürzlich einen Marstek-Speicher (Venus 3E, Venus D) gekauft, um seinen Eigenverbrauch zu erhöhen.

**HA-Level:** Fortgeschritten (66%), kennt HA seit 1–2 Jahren

**Hardware:** Bestehendes PV-System + Marstek-Speicher als Nachrüstlösung. Häufig Hoymiles WR. Oft bereits einen Shelly 3EM oder IR-Lesekopf installiert.

**Frustration:** Der Marstek-Speicher verspricht intelligente Steuerung, liefert aber nicht: WLAN-Abbrüche, Cloud-Abhängigkeit, der CT002 hängt sich auf, die „KI-Steuerung" funktioniert nicht, zwei Speicher gleichzeitig steuern ist unmöglich. „Extrem häufige Ausfälle der Datenübertragung zu Marstek und damit Ausfall der Steuerung."

**Schmerzpunkt-Zitat:** „Mein größtes Ärgernis ist eine nicht funktionierende Null-Einspeisung. Die Steuerung via App ist zu träge."

**Kaufmotiv:** Will endlich eine zuverlässige, lokale Steuerung, die seinen Marstek sauber in Home Assistant integriert. Bereit, 25€ zu zahlen. Will kein Abo.

**Was Solalex liefern muss:** Marstek-Integration in HA (MQTT/lokale API), zuverlässige Nulleinspeisung ohne Cloud, Multi-Speicher-Fähigkeit, einfaches Setup.

**Akquise-Pfad:** Newsletter → Warteliste → Kauf bei Launch. Kommt über YouTube oder Google-Suche nach „Marstek Home Assistant" oder „Marstek Nulleinspeisung".

---

### Persona 2: „Balkon-Benni" — Der BKW-Optimierer
**Segment-Größe: ~25% der Warteliste + Großteil der Blueprint-Kunden**

**Demografisches Profil:** Mann, 28–45 Jahre, Mietwohnung oder Eigenheim mit Balkon. Hat ein klassisches Balkonkraftwerk (1–2 kWp, 2 Module). Oft Anker-Solix- oder Hoymiles-System.

**HA-Level:** Einsteiger bis Fortgeschritten (50/50). Hat HA seit wenigen Monaten, oft wegen des BKW installiert.

**Hardware:** 2x 400–500W Module, Anker MI80 oder Hoymiles HM/HMS, Anker Solix E1600 Speicher. Shelly 3EM am Zähler. Typisch unter 2 kWp.

**Frustration:** Verschenkt täglich 100–300 Wh an Strom, weil die Anker-App zu träge/ungenau steuert. „Hab jetzt selbst ne Automation gebastelt, die jede Minute die Solarbank nach Hausverbrauch einstellt. Bin bei ca. 97% Selbstverbrauch." Aber das ist fragil und aufwändig.

**Schmerzpunkt-Zitat:** „Kein Strom zu verschenken" — der am häufigsten genannte Wunsch über alle Umfragen hinweg.

**Kaufmotiv:** Will maximalen Eigenverbrauch aus seinem kleinen System holen. Hat ein festes Budget (BKW war schon eine Investition). 20–25€ ist seine Schmerzgrenze.

**Was Solalex liefern muss:** 10-Minuten-Setup, Anker/Hoymiles-Erkennung, sichtbare Einsparungen im Dashboard.

**Akquise-Pfad:** YouTube-Video „Nulleinspeisung mit Home Assistant" → Blueprint-Kauf → Warteliste für Solalex. Klassischer Upgrade-Pfad.

---

### Persona 3: „Dach-Daniel" — Der Hausbesitzer mit System
**Segment-Größe: ~17% der Warteliste**

**Demografisches Profil:** Mann, 40–60, Hausbesitzer. Hat eine professionell installierte Dachanlage (>10 kWp) mit Hybrid-WR (Huawei, Fronius, SMA) und großem Speicher (BYD, Pylontech, 10+ kWh). Oft EVCC für die Wallbox.

**HA-Level:** Fortgeschritten bis Profi. Nutzt HA für Smart Home insgesamt.

**Hardware:** 10+ kWp PV, Hybrid-WR, Großspeicher, Wallbox, Wärmepumpe. Hat bereits EVCC laufen, aber das deckt nur E-Auto-Laden ab.

**Frustration:** EVCC steuert die Wallbox gut, aber für den Rest (Heizstab, Wärmepumpe, Klima, Pool) gibt es keine gute Lösung. „EVCC ist primär auf Autos ausgelegt" und „Etwas unflexibel mit EVCC. Funktioniert nur gut für die Wallbox."

**Schmerzpunkt-Zitat:** „Fehlende Open-Source-Standards und konkrete Lösungen für eine Vielzahl an Geräten."

**Kaufmotiv:** Sucht eine Ergänzung zu EVCC für Geräte-Priorisierung. Preisbereitschaft höher (30–50€), aber auch anspruchsvoller. Will Peak-Shaving, dynamische Tarife, Solar-Forecast.

**Was Solalex liefern muss:** EVCC-Koexistenz, Verbraucher-Priorisierung, Forecast-Integration, Multi-WR-Support.

**Akquise-Pfad:** HA-Community → Google-Suche → Warteliste. Weniger über YouTube.

---

### Persona 4: „Neugier-Nils" — Der Quiz-Teilnehmer ohne Setup
**Segment-Größe: ~45% des Quiz-Traffics (55 von 123)**

**Demografisches Profil:** 25–45, hat sich gerade ein BKW gekauft oder plant es. Hat vielleicht einen Raspberry Pi mit HA installiert, aber noch keine Automationen.

**HA-Level:** Absoluter Einsteiger. „Zu wenig Home Assistant Wissen" (53 Nennungen).

**Hardware:** 0,8–2 kWp BKW. Oft noch kein Akku (32%), kein WR-Steuerung (27%), keine Strommessung (24%).

**Frustration:** „Keine Übersicht, wie ich loslegen soll" (50 Nennungen). Er weiß, dass er Strom verschenkt, aber nicht, wie er das ändern kann. Die technische Hürde ist zu hoch.

**Schmerzpunkt-Zitat:** „Eine gute Nulleinspeise-Steuerung wäre schön."

**Kaufmotiv:** Sucht Orientierung, nicht Features. Wenn Solalex ihm zeigt „du brauchst XY, installiere das so, dann funktioniert es" — dann kauft er.

**Was Solalex liefern muss:** Hardware-Checkliste im Onboarding, klare „Bist du bereit?"-Prüfung, ggf. Verweis auf Hardware-Empfehlungen.

**Akquise-Pfad:** YouTube → Quiz → Newsletter → wartet auf Hardware → Warteliste → Kauf. Längster Funnel, aber größtes Volumen. Braucht Nurturing.

---

### Persona 5: „Beta-Björn" — Der treue Early Adopter
**Segment-Größe: ~37 aktive Betatester + 53 Bestandskunden = 90 Kontakte**

**Demografisches Profil:** Mann, HA-Veteran (1–3 Jahre), war beim Blueprint-Betatest dabei. Kennt Alex persönlich (Discord, YouTube-Kommentare).

**HA-Level:** Fortgeschritten. Kann YAML, kennt Entities, hat schon eigene Automationen.

**Hardware:** Bunt gemischt (Deye, Hoymiles, Anker, Growatt, Victron). Oft DIY-Speicher oder frühe Anker Solix.

**Zufriedenheit mit Blueprint:** 7.2/10 — gut, aber nicht begeistert. Sieht das Potential, weiß aber, dass es besser geht.

**Kaufmotiv:** Will das „richtige" Produkt, nicht den Workaround. Bereit für Migration. Vertraut Alex. Wird Beta-Tester für Solalex.

**Was Solalex liefern muss:** Klarer Migrationspfad vom Blueprint, Feature-Parität + Verbesserungen, aktive Community (Discord).

**Akquise-Pfad:** Bestandskunde → Newsletter/Discord → sofortiger Solalex-Kauf. Kürzester Funnel, höchste Conversion.

---

## 7. Funnel-Analyse

### 7.1 Der ALKLY-Funnel

```
AWARENESS (YouTube, Google)
    │
    ▼
INTEREST (Quiz / Lead Magnet) ────── n=123 Quiz-Teilnehmer
    │                                  └── 45% noch kein Setup
    │                                  └── 48% sagen „lokal = extrem wichtig"
    ▼
ENGAGEMENT (Newsletter via ConvertKit)
    │                                  └── 112 von 114 Wartelisten-Zugriffen via CK
    ▼
INTENT (Warteliste Solalex) ──────── n=165 Wartende
    │                                  └── 96% wollen Einmalkauf
    │                                  └── Median 25€ Zahlungsbereitschaft
    │                                  └── 44% Marstek-Segment
    ▼
CONVERSION (Blueprint-Kauf) ───────── n=120 Onboarding + 300+ aktive Nutzer
    │                                  └── Zufriedenheit 7.2/10
    │                                  └── 40% via YouTube akquiriert
    ▼
RETENTION (Update, Beta-Feedback)
    │                                  └── 53 Survey-Teilnehmer
    │                                  └── 36% Promoter (9–10/10)
    ▼
UPSELL (Solalex-Migration) ──────── Zielgruppe: Blueprint → Solalex
```

### 7.2 Conversion-Potentiale

**Quiz → Warteliste:** Von 123 Quiz-Teilnehmern mit E-Mail sind vermutlich 50–60% über den Newsletter auch auf der Warteliste gelandet. Die Quiz→Warteliste-Conversion ist vermutlich hoch, da der Newsletter stark konvertiert.

**Warteliste → Kauf:** Bei 165 Wartenden und einer konservativen 40–50% Conversion ergibt das ~65–80 Käufe bei Launch. Bei 25€ = **1.625–2.000€ Revenue allein aus der Warteliste**.

**Blueprint → Solalex:** Bei 300+ aktiven Blueprint-Nutzern und 50% Upgrade-Bereitschaft = 150 Migrations-Käufe möglich.

**Gesamt-Launch-Potential:** 215–230 Käufe × 25€ = **5.375–5.750€ Launch-Revenue**.

### 7.3 Funnel-Lücken

1. **Quiz → Warteliste-Tracking fehlt.** Es gibt keinen sauberen Weg nachzuverfolgen, ob Quiz-Teilnehmer auch zur Warteliste konvertieren. Empfehlung: UTM-Parameter im Newsletter-Link zur Warteliste.
2. **Kein Marstek-spezifischer Content.** 44% der Warteliste sind Marstek-Nutzer, aber es gibt keinen YouTube-Inhalt oder Landingpage dafür. Ein Video „Marstek Nulleinspeisung mit Home Assistant" würde massiven Traffic generieren.
3. **Kein Referral-Mechanismus.** Zufriedene Blueprint-Nutzer (36% Promoter) werden nicht systematisch als Multiplikatoren genutzt.

---

## 8. Wettbewerbslandschaft (aus Nutzer-Sicht)

| Lösung | Wartelisten-Nennungen | Stärke aus Nutzersicht | Schwäche aus Nutzersicht |
|---|---|---|---|
| EVCC | 11 | Wallbox-Laden top | „Primär auf Autos ausgelegt", für BKW ungeeignet |
| Eigenbau HA | 7 | Volle Kontrolle | Zeitintensiv, fragil, kein Support |
| Node-RED | 4 | Flexibel | Komplex, kein GUI |
| Hersteller-Apps (Anker, Marstek, Zendure) | 5+ | Einfach | Cloud, träge, unzuverlässig |
| OpenDTU on Battery | 3 | Schnell, lokal | Nur Hoymiles, kein Akku-Management |
| CleverPV | 1 | Feature-reich | „Kostet 76€ im Jahr" (Abo-Modell) |
| ALKLY Blueprint | 3 | Bewährt, vertraut | Workaround, nicht plug&play |

**Solalex-Positionierung:** Die einzige Lösung, die lokal, einfach, hardware-agnostisch UND bezahlbar (einmalig) ist.

---

## 9. Strategische Empfehlungen

### 9.1 Sofort-Maßnahmen (vor Launch)

1. **Marstek-Integration als Day-1-Feature priorisieren.** 44% der Warteliste ist ein zu großes Segment, um es zu ignorieren. Mindestens: Marstek Venus 3E und Venus D via MQTT/lokaler API steuerbar machen.
2. **YouTube-Video: „Marstek Nulleinspeisung mit Home Assistant"** — das Keywords-Potential ist riesig und die Frustration in der Community nachweisbar.
3. **Preispunkt 25€ (einmalig) kommunizieren.** Das ist der validierte Sweet Spot. Kein Abo anbieten.

### 9.2 MVP-Priorisierung (datengetrieben)

| Priorität | Feature | Datenbasis |
|---|---|---|
| P0 | Nulleinspeisung (zuverlässig, ±5W) | 83% ≥4/5, #1 Wunsch über alle Umfragen |
| P0 | 100% Lokal, keine Cloud | 79% ≥4/5, Warteliste + Quiz bestätigt |
| P0 | Einfaches Setup (10 min Ziel) | 73% ≥4/5, 38% Einsteiger in Warteliste |
| P1 | Marstek-Speicher-Integration | 44% der Warteliste, stärkstes Wachstum |
| P1 | Diagnostics-Dashboard | 27% Akku-Probleme, 6% „keine Übersicht" |
| P2 | Verbraucher-Priorisierung | 43% ≥4/5, aber Median nur 3 |
| P2 | Dynamische Stromtarife (Tibber) | 8+ explizite Nennungen, wachsender Markt |
| P2 | Solar-Forecast Integration | 6+ Nennungen |
| V2 | Multi-WR synchron | 38% ≥4/5, aber Median nur 3 |
| V2 | Multi-Speicher-Management | 7+ Nennungen (Freitext) |

### 9.3 Funnel-Optimierung

1. **Marstek-Landingpage** mit SEO für „Marstek Home Assistant", „Marstek Nulleinspeisung", „Marstek Venus 3E HA" — dieses Segment wächst explosiv.
2. **Quiz-to-Warteliste UTM-Tracking** implementieren.
3. **Blueprint-Nutzer Migration-Kampagne** vorbereiten — E-Mail-Sequenz: „Du nutzt den Blueprint? Solalex macht es 10x einfacher."
4. **Hardware-Kompatibilitätsliste** auf der Wartelisten-Seite — senkt die Unsicherheit bei den 28% mit nicht-steuerbarem WR.

---

## 10. Anhang: Datenqualität

| Quelle | Vollständigkeit | Bias-Risiko |
|---|---|---|
| Warteliste | Hoch (strukturierte Felder) | Selbstselektion: nur motivierte Interessenten |
| Onboarding | Mittel (viel Freitext, teils leer) | Nur zahlende Kunden (Survivorship Bias) |
| Quiz | Hoch (Multiple Choice) | Breit, aber weniger Kaufintention |
| Update-Survey | Niedrig (53 von 300+ Nutzern) | Antwort-Bias: zufriedenere antworten eher |
| Betatests | Sehr klein (17+20) | Early Adopter ≠ Mainstream |

**Konfidenz der Kernaussagen:**
- Marstek-Dominanz: **Sehr hoch** (direkte Messung, n=73)
- Preispunkt 25€: **Hoch** (n=138, konsistent über Segmente)
- Abo-Ablehnung: **Sehr hoch** (96% Einmalkauf, n=141)
- Feature-Prioritäten: **Hoch** (n=144, Likert-Skalen)
- YouTube als Hauptkanal: **Hoch** (40% der Onboardings, konsistent)
