# Wettbewerber-Profil 2: Akkudoktor EOS
**Tiefen-Analyse mit Original-Nutzerstimmen, Begeisterungs-Features und Solarbot-Differenzierung**

Stand: April 2026 · Quellen: GitHub (`Akkudoktor-EOS/EOS`, `Duetting/ha_eos_addon`, `ohAnd/EOS_connect`, `solectrus`), Akkudoktor-Forum, meintechblog.de, EOS ReadTheDocs, YouTube @akkudoktor, Podigee Podcast "Besser Wissen"

---

## 1. Schnellprofil

**Name:** Akkudoktor EOS (Energy Optimization System)
**Typ:** Open-Source-Optimierungs-Engine, **kein Regler**
**Lizenz:** Vollständig Open Source (Apache 2.0), keine Sponsor-Tokens, keine Paywall
**Sterne auf GitHub:** ~1.560 (`Akkudoktor-EOS/EOS`, April 2026)
**Forks:** ~122
**Sprache:** Python (Server, REST API, Genetic Algorithm)
**Gründer:** Dr. Andreas Schmitz (YouTube @akkudoktor, ~150k+ Subscriber)
**Erstes Commit:** Februar 2024
**Erste versionierte Release:** v0.1.0 (September 2025) — vorher 1,5 Jahre "v0.0.0"
**Primäre Zielgruppe:** Tech-affine Power-User mit PV + Speicher + dynamischem Stromtarif, Bereitschaft zur Selbstintegration

---

## 2. Was EOS fundamental ist (und vor allem: was es NICHT ist)

Hier ist die wichtigste Erkenntnis der gesamten Analyse, und sie steht wörtlich im EOS-README:

> **"AkkudoktorEOS does not control your home automation assets. It must be integrated into a home automation system. If you do not use a home automation system or you feel uncomfortable with the configuration effort needed for the integration you should better use other solutions."**

Das ist eine bemerkenswert ehrliche Selbstbeschreibung — und sie definiert exakt die Marktöffnung für Solarbot. **EOS ist kein Regler, kein Controller, kein "Solarbot" — es ist ein Optimierungs-Gehirn, das Pläne ausspuckt.** Was mit diesen Plänen passiert, muss der Nutzer selbst lösen.

In der EOS-Dokumentation steht es noch klarer: *"Based on the input data, the EOS uses a genetic algorithm to create a cost-optimized schedule for the coming hours from numerous simulations of the overall system."*

**Architektur in einem Satz:** EOS bekommt PV-Prognose, Wetter, Strompreise, Lastprofil und SoC als Input — und liefert nach 2–3 Minuten einen 48-Stunden-Plan als JSON zurück. Dieser Plan sagt: "Lade Akku zwischen 02:00 und 04:00 mit X Watt aus dem Netz, entlade ihn zwischen 18:00 und 21:00 für Eigenverbrauch." Ob, wie und wann dieser Plan ausgeführt wird, ist nicht EOS' Sache.

Das ist ein wissenschaftlich saubereres Modell als alle anderen Wettbewerber — und gleichzeitig die größte Mainstream-Hürde, die man sich vorstellen kann.

---

## 3. Begeisterungs-Features — was Nutzer an EOS lieben

### 3.1 Wissenschaftliche Tiefe und Glaubwürdigkeit

Aus dem EOS-Forum (akkudoktor.net/t/eos-vs-evcc-vs-solaranzeige): *"Erstmal vielen Dank für die tollen Inhalte hier und auf dem YouTube-Kanal. Ich bin ein langjähriger Follower und erfreue mich immer wieder an den wissenschaftlichen Ausarbeitungen, denen es anderen Kanälen, die sich mit diesen Themen befassen, leider oft fehlt."*

Andreas Schmitz hat einen Doktortitel und kommuniziert auf einem Niveau, das die Community als "endlich mal jemand, der Ahnung hat" wahrnimmt. EOS profitiert davon massiv. Im Podigee-Podcast "Besser Wissen" beschreibt er selbst seinen Weg vom Balkonkraftwerk-Bastler zum YouTube-Kanal mit viel Authentizität.

**Lehre für Solarbot:** Wissenschaftliche Glaubwürdigkeit ist ein knappes Gut in diesem Markt. Solarbot kann hier nicht mit Andreas konkurrieren — aber Solarbot kann **technische Ehrlichkeit** zur Marke machen: dokumentierte Akzeptanzkriterien (siehe EEPROM-Patch), öffentliche Mess-Ergebnisse, transparente Schwächen-Kommunikation. Das ist die "kleine Schwester der Wissenschaftlichkeit" — und sie ist erreichbar.

### 3.2 Open Source ohne Token-Theater

Im Gegensatz zu EVCC ist EOS vollständig Open Source ohne jede Paywall. Das ist eine implizite Stärke, die nicht viel diskutiert wird, aber emotional sehr wirkt — die Community vertraut Andreas, weil er nichts zurückhält.

**Lehre für Solarbot:** Solarbots Lizenzmodell (Einmalkauf, klar, fair) ist nicht Open Source — und das ist okay. Aber die **Werte hinter Open Source** (Transparenz, keine versteckten Mechanismen, kein Lock-in) müssen Solarbot trotzdem prägen. Ein Versprechen wie "Wenn Solarbot je eingestellt wird, machen wir den Code öffentlich" wäre ein extrem starkes Vertrauenssignal.

### 3.3 Dynamische Strompreis-Optimierung mit PV-Forecast

Aus Discussion #446: *"Ich nutze Aktuell zur Daten-Sammlung Home-Assistant. Ich lese beide Verbrauchszähler aus, habe von jedem WR die Aktuelle Leistung."* — der User will EOS einsetzen, weil er einen dynamischen Stromtarif hat und einen Akku, den er optimieren will. Das ist EOS' Kern-Use-Case.

Aus dem Forum-Thread "EOS - Einspeisen vom Akku ins Netz mit dynamischem Einspeisetarif" (April 2025): *"Ich habe das EOS im Docker laufen und bastel die OptimizationParameters im IObroker blockly zusammen. Über http POST schick ich dem EOS das Objekt und bekomme nach 2-3min die OptimizeResponse."*

**Lehre für Solarbot:** Dynamische Tarife sind das größte EMS-Wachstumsfeld 2026/2027. EOS hat hier eine wissenschaftlich fundierte Lösung — aber sie ist für 95 % der Nutzer unerreichbar, weil zu komplex. Solarbot kann eine **vereinfachte Variante** anbieten ("Lade Akku zu den 4 günstigsten Stunden des Tages") oder langfristig EOS als optionalen Forecast-Provider integrieren (mehr dazu in Kapitel 7).

### 3.4 Genetic Algorithm als Magie-Faktor

Aus der EOS-Dokumentation: *"The plan calculated by EOS is cost-optimized due to the genetic algorithm used, but not necessarily cost-optimal, since genetic algorithms do not always find the global optimum, but usually find good local optima very quickly in a large solution space."*

Aus dem Forum (Februar 2026): *"Aus Interesse hatte ich mir den bestehenden Code von eurem EOS angesehen, insbesondere die Optimierung bezüglich: dynamischer Strompreis und Batterieladung und -Entladung. Ihr nutzt dafür aktuell einen genetischen Algorithmus."* — der User hat als Mathematiker ein eigenes Modell mit OR-Tools gebaut, weil er den genetischen Ansatz für suboptimal hält.

**Lehre für Solarbot:** Komplexität verkauft sich an die Top-1 % der Power-User, schreckt aber 99 % ab. Solarbot soll die **wahrgenommene Magie** liefern, nicht die mathematische. Ein Diagnose-Tab, der zeigt "Solarbot hat heute 7,80 € gespart" wirkt stärker als jeder genetische Algorithmus, der niemand außerhalb des Mathematik-Studiums versteht.

### 3.5 Aktive Community mit prominenten Botschaftern

Aus dem EOS-README: *"Andreas Schmitz, the Akkudoktor, uses EOS integrated in his NodeRED home automation system for OpenSource Energieoptimierung. Jörg, meintechblog, uses EOS for day-ahead optimization for time-variable energy prices."*

Andreas selbst nutzt es täglich, Jörg von meintechblog hat ein 60-Minuten-YouTube-Video zur Installation gemacht, mehrere Sub-Projekte (`EOS_connect`, `ha_eos_addon`, `EOS-EVCC-Node-Red-Integration`) sind unabhängig entstanden, um EOS zugänglicher zu machen. Das ist ein lebendiges Ökosystem.

**Lehre für Solarbot:** Prominente Botschafter sind Wachstumstreibstoff. Solarbot braucht 3–5 sichtbare Power-User aus der HA-Community, die öffentlich zeigen "So nutze ich Solarbot." Das ist der wichtigste Marketing-Hebel überhaupt — und Alex hat als ALKLY-Marke selbst schon das Zeug dazu, einer dieser Botschafter zu sein.

### 3.6 EOS Connect als Brücke

Das Drittprojekt `EOS_connect` von ohAnd ist besonders interessant: Es ist eine Brücke, die EOS-Ergebnisse einsammelt, MQTT-Nachrichten an Home Assistant schickt und Geräte steuern kann. Aus dem README: *"EOS Connect fetches real-time and forecast data, processes it via your chosen optimizer, and controls devices to optimize your energy usage and costs."*

Es **füllt genau die Lücke**, die EOS architektonisch offen lässt. Aber es ist selbst wieder ein Drittprojekt, das eingerichtet werden muss — und das zeigt, wie viele bewegliche Teile am Ende nötig sind.

**Lehre für Solarbot:** Die Existenz von EOS Connect beweist, dass die Lücke real ist. Solarbot ist im Grunde "EOS Connect für Mainstream-Nutzer, ohne EOS dahinter" — also der gleiche Bedarf, einfacher gelöst.

---

## 4. Frust-Punkte — was Nutzer an EOS in den Wahnsinn treibt

### 4.1 "Extrem knifflig und kompliziert, nur für Experten"

Die deutlichste Stimme aus der gesamten EOS-Community kommt vom Solectrus-Maintainer in Discussion #3912 (auf GitHub):

> *"Ich schätze EOS momentan als ein Tool mit sehr viel Potential ein. Leider ist die Ansteuerung, also die Bereitstellung von Daten für eine Berechnung durch EOS, derzeit extrem knifflig und kompliziert und nur für Experten, der ich leider nicht bin, sehr aufwändig."*

Das ist ein erfahrener Open-Source-Entwickler, der ein eigenes PV-Dashboard-Projekt betreibt — und selbst er sagt, EOS sei "nur für Experten". Wenn das jemand mit dieser Tech-Tiefe sagt, ist die Mainstream-Hürde nicht hoch — sie ist eine Mauer.

**Solarbot-Differenzierung:** Solarbots Versprechen "10 Minuten Setup, kein YAML, kein JSON, kein Node-RED" ist die direkte Anti-These. Der Solectrus-Maintainer aus Discussion #3912 ist der **prototypische Solarbot-Käufer**: technisch versiert, aber zeit-knapp und Komplexitäts-müde.

### 4.2 Der Feeding-Albtraum

Aus dem Akkudoktor-Forum (Discussion "EOS Installation und Konfiguration", Dezember 2025): *"Was ich versucht habe, ist meinen Stromzählerstand als 'load0_emr'-key an EOS zu senden und dann meine Last mit 'LoadAkkudoktorAdjusted' anzupassen. Allerdings kommen da extrem kleine Werte für jede Stunde heraus (0.05, ...)."* — und in der nächsten Antwort des selben Users: *"Um meine eigene load0_emr nutzen zu können, musste ich meinen Zählerstand mit 1000 multiplizieren, da EOS Wh statt kWh als Einheit erwartet. Daher waren die Werte fast bei 0."*

Aus Discussion #294: *"Currently the most work in this repo is updating the EOS source code and check if the changes still work with the documentation."*

**Solarbot-Differenzierung:** Solarbot liest HA-Entitäten direkt aus, mit automatischer Einheitenerkennung. Kein Wh-vs-kWh-Drama, keine Multiplikatoren, keine JSON-Keys, keine REST-Calls. Diese Aussage könnte fast 1:1 in eine Vergleichstabelle: *"Bei EOS musst du wissen, ob deine Werte in Wh oder kWh sind. Bei Solarbot musst du gar nichts wissen."*

### 4.3 Tagelange Installations-Frust auch für erfahrene Nutzer

Aus dem Forum-Thread "Wie starte ich am Sinnvollsten?" (Discussion #446): *"Nach etlichen Versuchen habe ich es geschafft. :-) Erst zu alte Pythonversion, dann Systempartition voll … Nun läuft es im Homeverzeichnis. Auf der Startseite sehe ich 'EOS Dashboard' und 'Configuration' und dann folgen unendlich viele Einstellungen."*

Aus dem Forum-Thread "Erste Schritte mit EOS, HomeAssistant und EOS connect" (Oktober 2025): *"ich versuche gerade seit einigen Tagen, EOS mit Home Assistant zum Laufen zu bekommen. Nach dem das Ganze grundsätzlich zu Laufen scheint, komme ich jetzt nicht mehr weiter."*

Aus dem Thread "EOS auf Proxmox wieder zum laufen bringen nach upgrade" (Juli 2025, ein belgischer User auf Deutsch): *"Monaten her hab Ich auf nen kleine Proxmox Maschine EOS installiert, folgend der Youtube Video von Jörg von Meintechblog. Damals habe Ich nur ungefähr bis 40 minuten von der 60 minuten daurende Video durch gemacht."* — 60 Minuten Video für eine Installation, und der User schaffte es nur bis zur 40. Minute.

Aus dem Akkudoktor-Forum (Februar 2026, "Fehler bei der Installation des EOS HomeAssistant Add-Ons"): *"Ich wollte das EOS als 'App' in HomeAssistant laufen lassen, der bei mir auf Proxmox läuft. Leider bekomme ich eine Fehlermeldung: RuntimeError: NumPy was built with baseline optimizations: (X86_V2) but your machine doesn't support: (X86_V2)."* — selbst die HA-Add-on-Variante scheitert an CPU-Architektur-Inkompatibilität.

**Solarbot-Differenzierung:** Solarbot installiert sich über den HA Add-on Store mit einem Klick. Keine Python-Versionen, keine Docker-Compose-Files, keine NumPy-Architektur-Fehler, keine 60-Minuten-Video-Anleitungen. Botschaft: *"Solarbot installierst du in der Zeit, in der du das EOS-Tutorial-Intro siehst."*

### 4.4 2–3 Minuten Berechnungszeit pro Optimierung

Aus dem Forum-Thread "EOS - Einspeisen vom Akku ins Netz" (April 2025): *"Über http POST schick ich dem EOS das Objekt und bekomme nach 2-3min die OptimizeResponse."*

Aus Discussion #294: *"the first run may take — depending on your hardware EOS is running — several minutes (and may look strange). On my Synology DS220+ approximately 4 minutes."*

Das ist für ein 48-Stunden-Optimierungsproblem ok, aber für jede Form von Echtzeit-Nutzung undenkbar.

**Solarbot-Differenzierung:** Solarbot reagiert auf Smart-Meter-Änderungen im Sekundenbereich. EOS kann Solarbot perfekt **ergänzen** — als langfristiger Plan-Geber, der Solarbots Echtzeit-Regelung mit Forecast-Wissen anreichert. Aber EOS kann Solarbot nicht **ersetzen**.

### 4.5 Genetic Algorithm findet "nicht immer das Optimum"

Aus der EOS-Doku selbst: *"genetic algorithms do not always find the global optimum, but usually find good local optima very quickly in a large solution space."*

Aus dem Forum (Februar 2026): *"Eigentlich hatte ich es via Cplex lösen wollen, bin dann jedoch auf Python und OR-Tools umgestiegen."* — ein User baut EOS von einem genetischen auf einen linearen Optimierungs-Algorithmus um, weil er die Lösung als suboptimal empfindet.

**Solarbot-Differenzierung:** Solarbot verspricht keine globale Kosten-Optimierung. Solarbot verspricht **"so wenig Netzbezug wie möglich, so wenig Hardware-Belastung wie nötig"** — und das ist ein Versprechen, das wir tatsächlich einhalten können. Wir sollten uns niemals in eine "wir sind besser optimiert als EOS"-Diskussion ziehen lassen, weil wir dort verlieren würden. Unser Versprechen ist ein anderes: **Einfachheit und Zuverlässigkeit, nicht mathematische Brillanz.**

### 4.6 Stundenraster trotz 15-Minuten-Marktstandard

Aus dem Forum-Thread "Strom Börsenpreis viertelstündlich 15-min Takt 1. Oktober" (Oktober 2025): *"In dem Zeitraum 8.10. 18-19 Uhr würde EOS den Stundenpreis von 18,4 ct/kWh nutzen. Liegt also relativ genau im Mittel zwischen den beiden Werten von dir. Ich denke EOS liegt damit für kurze Spitzen jetzt natürlich mit der Optimierung daneben."*

Seit 1. Oktober 2025 läuft die deutsche Strombörse im 15-Minuten-Raster. EOS rechnet weiter im Stundenraster — und liegt damit bei kurzen Preis-Spitzen daneben.

**Solarbot-Differenzierung:** Solarbot reagiert auf Echtzeit-Werte, nicht auf vorberechnete Stunden-Pläne. Bei einem Tibber-Preis-Crash um 14:23 reagiert Solarbot innerhalb von Sekunden — EOS reagiert zur nächsten vollen Stunde, mit dem gemittelten Wert.

### 4.7 EOS Connect, EOS Add-on, Node-RED, MQTT — der Tool-Wirrwarr

Um EOS in einer normalen Heim-Installation nutzbar zu machen, braucht man je nach Setup eine erstaunliche Anzahl an beweglichen Teilen:

- **EOS** (Docker-Container oder HA-Add-on)
- **EOS Connect** oder **EOS-EVCC-Node-Red-Integration** oder **eigener Node-RED-Flow** zur Daten-Aufbereitung
- **MQTT-Broker** für die Kommunikation
- **Solcast oder andere PV-Forecast-Quelle**
- **Wetter-API**
- **Stromtarif-API (Tibber/aWATTar)**
- **Lastprofil-Daten aus HA**
- **Eine eigene Logik**, die die EOS-Ausgabe in Geräte-Steuerbefehle übersetzt

Das ist eine **8-teilige Toolchain** für etwas, das ein Mainstream-Nutzer als "schalte meinen Akku schlau" beschreibt.

Aus Discussion #294: *"I'm not sure if there is a way to combinate this addon and EOS connect."* — selbst die Entwickler der Sub-Projekte sind sich unsicher, wie ihre eigenen Tools zusammenpassen.

**Solarbot-Differenzierung:** Solarbot ist **ein** Add-on. Punkt. Keine externen Brücken, keine zusätzlichen Container, kein MQTT-Broker pflicht. Botschaft: *"EOS braucht 8 Komponenten. Solarbot braucht eine."*

### 4.8 Dokumentation läuft hinterher

Aus meintechblog.de (Mai 2025): *"Hab auch eben länger mit Andreas gequatscht. Bei den Inputs gibts wohl noch Baustellen, sodass derzeitig nicht alles funktioniert."*

Aus dem Forum (mehrere Threads): *"Eine default.config.json gibt es wohl nicht mehr. Da ist die Dokumentation u.U. noch nicht aktualisiert."*

EOS ist seit Februar 2024 in aktiver Entwicklung, aber erst im September 2025 gab es die erste versionierte Release. Die Doku hinkt der Code-Realität hinterher — verständlich für ein Spare-Time-Projekt, aber für Mainstream-Nutzer ein Killer.

**Solarbot-Differenzierung:** Solarbot startet mit Dokumentation als First-Class-Citizen. Der bestehende Plan (PRD, Onboarding, Architecture Spike, Beta Plan, Deep Research als v1.2) zeigt, dass Alex das schon richtig denkt. Das ist ein klarer Vorteil — man darf ihn aber nicht verspielen, wenn die Codebase wächst.

### 4.9 Kein Hardware-Support, sondern API-Definitionen

Aus dem Forum-Thread "Kompatibel Services und WR?" (Juni 2025): *"Hi Leute, noch ist kein WR ausgesucht für die PV Anlage die im Herbst installiert wird und das EOS klingt nach genau dem, was ich gesucht habe. Was mir fehlt ist der Überblick (vielleicht finde ich nur den richtigen Link)."*

Antwort: Es gibt keine Liste unterstützter Hardware, weil EOS keine Hardware unterstützt. Das ist für den User eine echte Enttäuschung, weil das Marketing es so klingen lässt, als wäre es eine fertige Lösung.

**Solarbot-Differenzierung:** Solarbot hat ebenfalls keine Hardware-Liste — aber Solarbot **braucht** auch keine, weil er HA-Entitäten konsumiert. Das muss klar kommuniziert werden: *"Wenn deine Hardware in Home Assistant funktioniert, funktioniert sie mit Solarbot. Punkt."* Das ist eine ehrlichere und entwaffnendere Aussage als "wir unterstützen 47 Hersteller" — und sie ist auch noch wahr.

### 4.10 Die ehrliche Selbstdiagnose im README

Es ist selten, dass ein Projekt im eigenen README so klar sagt "wenn du das nicht willst, nimm was anderes". Aber genau das tut EOS:

> *"If you do not use a home automation system or you feel uncomfortable with the configuration effort needed for the integration you should better use other solutions."*

Das ist eine Einladung an Solarbot, dort zu stehen, wo EOS aufhört. Wir können diese Aussage praktisch wörtlich auf unsere Landing Page übernehmen: *"Wenn du EOS magst, aber dich der Konfigurationsaufwand abschreckt — Solarbot ist die Lösung dafür."*

---

## 5. Strukturelle Schwächen — die Architektur-Wahrheiten

**S1: EOS ist Brain, nicht Hands.** Diese Architektur-Entscheidung ist bewusst getroffen und wird nicht zurückgenommen. EOS wird auf absehbare Zeit kein Regler werden — und das ist gut so, aber es lässt die "letzte Meile" zur Hardware komplett offen.

**S2: Stundenraster ist im Algorithmus verankert.** Eine Migration auf 15-Minuten-Raster ist in Discussions geplant, aber nicht trivial — der genetische Algorithmus wird viermal langsamer, wenn er viermal so viele Slots optimieren muss.

**S3: Python + Docker + NumPy als Stack.** Das schließt schwache Hardware (Raspberry Pi der ersten Generationen, alte CPUs ohne X86_V2-Support, ARM-Derivate ohne piwheels-Pakete) systematisch aus. EOS ist in der Praxis ein "Synology NAS / Proxmox / Intel NUC"-Tool.

**S4: REST-API als primäres Interface.** Das ist sauber und maschinenlesbar, aber für Nicht-Programmierer eine absolute Mauer.

**S5: Spare-Time-Projekt ohne kommerziellen Druck.** Andreas verdient sein Geld mit YouTube und Beratung, nicht mit EOS. Damit gibt es keinen Druck, Mainstream-Tauglichkeit zu erreichen — und "Mainstream-Tauglichkeit" ist nicht das Ziel des Projekts. Das ist legitim, schließt aber 95 % des Marktes aus.

**S6: Genetic-Algorithm-Charakter.** Der Algorithmus liefert "good local optima", nicht garantierte Optima. Das ist mathematisch ehrlich, aber für eine Marketing-Botschaft schwer zu verkaufen.

---

## 6. Solarbot-Differenzierung — wo wir konkret anders sind

| Dimension | EOS | Solarbot |
|---|---|---|
| Funktion | Optimierungs-Plan-Generator | Echtzeit-Regler |
| Reaktionszeit | 2–3 Min Berechnung, dann Stundenraster | Sekunden |
| Steuert Hardware? | Nein, nur Pläne | Ja, über HA-Entitäten |
| Setup-Aufwand | Tage bis Wochen | 10 Minuten |
| Konfiguration | JSON, REST-API, Node-RED-Flows | Geführter UI-Flow |
| Tools nötig | EOS + EOS Connect + Node-RED + MQTT + Forecast-Provider | nur Solarbot |
| Zielgruppe | Tech-Power-User mit Optimierungs-Wissen | Balkonkraftwerk + Speicher Mainstream |
| Strompreis-Granularität | Stundenraster | Echtzeit-getrieben |
| Mathematik | Genetic Algorithm, "good local optima" | Deterministische Regelung mit Hysterese |
| Forecast | 48 h, integriert | Aktuell keiner (V2 möglich, evtl. via EOS) |
| Lizenz | Open Source (Apache 2.0) | Einmalkauf, lebenslang |
| Marktreife | v0.1 (September 2025) | Geplant v1.0 (Q3 2026) |

---

## 7. Co-Existenz-Strategie: EOS als möglicher Forecast-Provider für Solarbot V2

Das ist die strategisch interessanteste Erkenntnis dieser Analyse: **EOS und Solarbot sind nicht nur keine Konkurrenten — sie sind potenziell perfekte Partner.**

Die Architektur ist klar:

```
EOS (Brain)  →  Plan  →  Solarbot (Hands)  →  HA-Entitäten  →  Hardware
```

EOS löst das **Was und Wann** ("Lade Akku zwischen 02:00 und 04:00 mit 800 W aus dem Netz"). Solarbot löst das **Wie** ("Wandele diesen Plan in HA-Service-Calls um, regle in Echtzeit nach, schone die Hardware, dokumentiere die Aktionen im Diagnose-Tab").

**Konkrete Umsetzung als V2-Feature:**
- Solarbot bekommt einen optionalen Reiter "Forecast-Provider" mit Auswahl: keiner / Solarbot intern (Heuristiken) / **EOS (extern)** / Solcast / etc.
- Wenn EOS gewählt ist, holt Solarbot regelmäßig den EOS-Plan über die REST-API ab und nutzt ihn als Soll-Vorgabe für die Akku-Strategie.
- Die Echtzeit-Regelung läuft weiter über Solarbot — EOS ändert nur die Akku-Soll-Pläne und Schwellwerte.

**Vorteile dieser Strategie:**
1. **Keine Frontalkonkurrenz mit Andreas Schmitz.** Er hat eine massive Community, die wir nicht antagonisieren wollen.
2. **Solarbot wird zur "letzten Meile" für die EOS-Power-User.** Ein klarer Mehrwert für beide Communities.
3. **Solarbot bekommt fortgeschrittene Optimierungs-Logik, ohne sie selbst bauen zu müssen.** Das wäre Jahre an Entwicklungsarbeit.
4. **Wir können in Marketing und Doku ehrlich sagen: "Solarbot funktioniert standalone, kann aber optional mit EOS gekoppelt werden."**

**Risiko:** Andreas könnte Solarbot als "kommerziellen Trittbrettfahrer" wahrnehmen, wenn die Kommunikation schief läuft. **Mitigation:** Sehr früh persönlicher Kontakt zu Andreas, ehrliche Vorstellung als komplementär, evtl. Sponsoring eines EOS-Features oder einer Doku-Verbesserung als Zeichen guten Willens. Das wären 200–500 €, die strategisch viel mehr Wert haben.

---

## 8. Was Solarbot von EOS lernen muss

**1. Wissenschaftlichkeit als Vertrauenssignal.** Andreas' "Dr." auf der Page ist ein Wettbewerbsvorteil, den wir nicht haben. Aber wir können **dokumentierte Tests und Mess-Ergebnisse** liefern — z. B. die EEPROM-Schreibstatistik aus dem PRD-Patch, oder ein öffentlich zugängliches Dashboard mit "Solarbot in unserem Testhaus über die letzten 30 Tage".

**2. Open-Source-Vibes ohne Open Source.** Selbst wenn Solarbot ein bezahltes Add-on ist, kann der **Geist** Open Source sein: öffentliche Roadmap, transparente Issues, ehrliche Limitations-Doku. Das schafft Vertrauen, das Anker und Zendure nie haben werden.

**3. Mathematische Tiefe, vermarktet als Einfachheit.** Hinter jedem "magischen Knopf" in Solarbot steht eine Berechnung. Diese Berechnung muss nachvollziehbar sein (für die Power-User, die sie sehen wollen), aber unsichtbar (für die Mainstream-User, die sie nicht sehen wollen).

**4. Echte Community-Pflege.** Andreas antwortet selbst in seinem Forum, regelmäßig, persönlich, freundlich. Das ist die wichtigste Marketing-Investition seiner Marke. Alex hat als ALKLY-Brand schon das Zeug dazu — es muss nur konsequent durchgehalten werden, auch wenn die Userbase wächst.

**5. Transparente Kommunikation über Schwächen.** EOS sagt offen "Genetic Algorithm findet nicht immer das Optimum" und "Wenn dir die Konfiguration zu viel ist, nimm was anderes". Das ist mehr wert als jede Marketing-Übertreibung. Solarbot muss ähnlich ehrlich sein — z. B. mit einer "Wann Solarbot nicht das Richtige für dich ist"-Sektion in der Doku.

---

## 9. Was Solarbot konkret besser machen muss als EOS — die fünf Prioritäten

**Priorität 1: Eine-Komponenten-Installation.**
Solarbot ist ein HA Add-on, nichts anderes. Keine externe Brücke, kein zweiter Container, kein MQTT-Broker pflicht. Direkte Antwort auf den 8-teiligen EOS-Tool-Wirrwarr.

**Priorität 2: Sekunden-Reaktionszeit statt Stundenraster.**
Solarbot reagiert auf Last- und PV-Änderungen in Echtzeit. Direkte Antwort auf den 2–3-Minuten-Berechnungs-Zyklus von EOS und das Stundenraster, das seit Oktober 2025 nicht mehr zum Marktstandard passt.

**Priorität 3: HA-Entitäten statt JSON-API.**
Solarbot kommuniziert mit dem, was im HA-System schon da ist. Kein REST-Call, kein JSON-Schema-Wissen, kein "Wh-vs-kWh-Drama". Direkte Antwort auf die Forum-Stimme, die tagelang mit "load0_emr" gekämpft hat.

**Priorität 4: 10-Minuten-Setup als Akzeptanzkriterium.**
Mess-bar. Akzeptiert. In der Spike-Phase validiert. Direkte Antwort auf die "Tage- und wochenlangen Installations-Frust"-Stimmen.

**Priorität 5: "Ehrliche Selbstdiagnose"-Kultur in der Doku.**
Solarbot sollte eine Sektion "Wann Solarbot nicht das Richtige für dich ist" in der Doku haben — z. B. *"Wenn du dynamische Tarife mit Forecast-basierter Mehrtages-Optimierung willst, schau dir EOS an. Solarbot konzentriert sich auf Echtzeit-Regelung."* Diese Ehrlichkeit erzeugt mehr Vertrauen als jede Werbung.

---

## 10. Botschaften, die direkt verwendbar sind

Drei fertige Sätze, alle aus EOS-Stimmen abgeleitet:

> **"EOS ist ein wissenschaftlich fundierter Optimizer für Power-User. Solarbot ist die zuverlässige Echtzeit-Regelung für alle anderen."**

> **"EOS denkt in Stunden, Solarbot reagiert in Sekunden. Beides hat seinen Platz — und sie ergänzen sich perfekt."**

> **"Wenn EOS dich begeistert, aber die Installation dich abschreckt: Solarbot ist die Antwort."**

---

## 11. Risiken und blinde Flecken

**Risiko 1: Andreas Schmitz baut EOS Connect oder ein "EOS-Lite" zum Mainstream-Tool aus.** Das ist möglich, aber unwahrscheinlich, weil seine Brand wissenschaftlich-technisch positioniert ist und nicht Mainstream-User-zentriert. **Mitigation:** Frühzeitiger Kontakt, Co-Existenz-Botschaft, evtl. Kooperation.

**Risiko 2: Die Community sieht Solarbot als "Kommerziellen Klau" einer Open-Source-Idee.** Das ist real und sensibel. **Mitigation:** Solarbot positioniert sich klar **anders** — nicht als "EOS für Doofe", sondern als "Echtzeit-Regler für Mainstream". Das sind zwei verschiedene Produkte für zwei verschiedene Zielgruppen.

**Risiko 3: Andreas bekommt durch die wachsende Tibber/aWATTar-Welle plötzlich Mainstream-Reichweite.** Möglich, aber dann braucht EOS trotzdem eine "letzte Meile"-Lösung — und Solarbot ist genau diese.

**Risiko 4: Wir unterschätzen Andreas' Marken-Reichweite und kommunizieren respektlos.** Das wäre fatal. **Mitigation:** Jede öffentliche Erwähnung von EOS aus Solarbot-Mund muss mit Wertschätzung erfolgen. Andreas hat fundamentale Arbeit für die DACH-Solar-Community geleistet, und das muss anerkannt werden.

---

## 12. Konkrete nächste Schritte

**Sofort (vor Spike):**
- Persönlicher Kontakt zu Andreas Schmitz aufnehmen — kurzes, freundliches Hello, Vorstellung von Solarbot, klare Kommunikation der Co-Existenz-Strategie. Idealerweise ein 30-Minuten-Videocall.
- Prüfen, ob es bereits Solarbot-relevante EOS-Discussions gibt, in denen Solarbot als Komplement vorgestellt werden kann (ohne Spam, einfach als hilfreiche Information).

**Vor Beta:**
- Eine Doku-Seite vorbereiten: *"Solarbot vs. EOS: Wann nutze ich was?"* — fair, technisch korrekt, beide Tools positiv.
- Die "Wann Solarbot nicht das Richtige für dich ist"-Sektion schreiben, mit EOS als prominenter Empfehlung für den Power-User-Use-Case.

**V1 → V2 Roadmap:**
- Ein V2-Feature definieren: **EOS als optionaler Forecast-Provider in Solarbot.** Das wäre eine technisch sehr saubere Integration über die EOS-REST-API, die beide Tools wertvoller macht.
- Ein gemeinsamer Blog-Artikel auf alkly.de und/oder dem Akkudoktor-Forum: "Wie Solarbot und EOS perfekt zusammenarbeiten."

**Post-Launch:**
- Beobachten, ob aus der EOS-Community Anfragen kommen ("ich liebe EOS, aber kann ich es einfacher haben?"). Diese User sind die wertvollsten Solarbot-Käufer überhaupt — sie verstehen die Domäne und sind bereit zu zahlen.

---

## 13. Die wichtigste Erkenntnis dieser Analyse

EOS und EVCC sind völlig verschiedene Wettbewerber, und sie erfordern völlig verschiedene Strategien. EVCC ist ein **direkter funktionaler Wettbewerber** im Wallbox-Segment, mit dem Solarbot durch klare Co-Existenz-Botschaft umgehen muss. EOS ist ein **architektonischer Komplement-Kandidat**, mit dem Solarbot perspektivisch eine technische Integration aufbauen kann.

Die emotionale Marktöffnung sieht ähnlich aus — beide Communities sind frustriert von der Komplexität — aber die Lösung ist verschieden. Bei EVCC sagen wir "wir machen das, was du willst, einfacher und ohne Token". Bei EOS sagen wir "wir machen das, was EOS nicht macht: die letzte Meile zur Hardware".

Wenn Solarbot diese zwei verschiedenen Botschaften klar trennt und nicht vermischt, hat er eine seltene Position: **Konkurrent für EVCC, Komplement für EOS, Antithese zu Hersteller-Apps.** Das ist eine Position, die in der gesamten DACH-EMS-Landschaft niemand sonst besetzt — und sie ist verteidigbar.

---

*Diese Analyse basiert auf dem GitHub-Repo `Akkudoktor-EOS/EOS` (1.560 Sterne, 122 Forks), 12 Forenbeiträgen aus dem Akkudoktor-Forum, der EOS-ReadTheDocs-Dokumentation, dem GitHub-Discussion #294 und #446 (Akkudoktor-EOS), Discussion #3912 (solectrus), den Sub-Projekten `EOS_connect` (ohAnd) und `ha_eos_addon` (Duetting), einem meintechblog.de-Installationsguide, dem Podigee-Podcast "Besser Wissen" mit Andreas Schmitz und einer YouTube-Interview-Ankündigung vom Januar 2026. Alle Zitate sind im Original-Wortlaut wiedergegeben.*
