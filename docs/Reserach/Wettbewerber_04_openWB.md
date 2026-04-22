# Wettbewerber-Profil 4: openWB
**Tiefen-Analyse mit Original-Nutzerstimmen, Begeisterungs-Features und Solarbot-Differenzierung**

Stand: April 2026 · Quellen: openWB-Forum (forum.openwb.de), Photovoltaikforum, TFF-Forum (Tesla Fahrer & Freunde), Akkudoktor-Forum, openWB-Wiki, e-mobileo Shop, openWB-Website, GitHub `snaptec/openWB`

---

## 1. Schnellprofil

**Name:** openWB
**Typ:** Kommerzielles Hardware+Software-Bundle (Wallbox + Energiemanagement-System)
**Gesellschaftsform:** openWB GmbH & Co KG (deutsche Firma)
**Lizenz:** Open Source (GitHub `snaptec/openWB`), Hardware kommerziell
**Software-Versionen:** 1.9 (Legacy, "Auslaufmodell"), 2.x (aktuell, viele Bugs noch in Bearbeitung)
**Modelle:** series2 Custom, standard, standard+, Pro, Duo
**Preisrange:** ~1.000 € bis ~2.500 € pro Wallbox (je nach Modell und Optionen)
**Primäre Zielgruppe:** PV-Anlagen-Besitzer mit Eigenheim, oft mit größerer Anlage (10+ kWp), die eine Wallbox + Energiemanagement aus einer Hand wollen
**Marktposition:** Premium-Anbieter im DACH-Raum, oft als "die teure, aber gute" Lösung wahrgenommen

---

## 2. Was openWB fundamental ist

openWB ist die einzige der bisher analysierten Lösungen, die **Hardware und Software gekoppelt verkauft**. Das ist sowohl die größte Stärke als auch die größte Schwäche — und es definiert den fundamentalen Unterschied zu Solarbot.

Die Selbstbeschreibung des Inhabers im TFF-Forum ist klar: *"In einigen Threads hier wurde die openWB bereits erwähnt. Letztes Jahr hauptsächlich als Bastellösung, derweil hat sich aber einiges getan und der Status steht ihr definitiv nicht mehr zu. Die Bausatzvariante gibt es immer noch, ebenso aber auch eine ansehnliche Variante mit Touchscreen Display. (...) Was unterscheidet die openWB von anderen Wallboxen? Eines der Kernfeatures ist das PV-geführte Laden. Dazu kommt Lastmanagement und Hausanschlussüberwachung mit bis zu 3 Ladepunkten."*

Eine andere User-Aussage trifft das Wesen exakt: *"Was viele Leute nicht sehen — openWB ist keine WB, sondern eine vielseitige EMS-Software, die DURCH den 1x-Preis der WB (Hardware) dauerhaft bezahlt ist."*

Das ist openWBs strategische DNA: **Die Wallbox ist der Trojaner, die EMS-Software ist das Produkt.** Wer nur eine Wallbox will, kauft eine günstigere. Wer ein lokales, deutsches, ehrliches Energiemanagement-System will, das ohne Cloud läuft und eine Wallbox als Beigabe mitbringt, kauft openWB.

Und genau hier liegt die Marktöffnung für Solarbot: **Wer kein 1.500-€-Hardware-Bundle kaufen will, sondern nur die Software-Intelligenz braucht — den lässt openWB systematisch links liegen.**

---

## 3. Begeisterungs-Features — was Nutzer an openWB lieben

### 3.1 Lastmanagement und Hausanschlussüberwachung

Das ist openWBs technisches Kron-Juwel. Aus dem Photovoltaikforum-Thread "Empfehlung Wechselrichter" (Januar 2026): *"Es sollen zukünftig auch 2 Wallboxen hinzukommen. (Beide zusammen max. 11 kW + Lastmanagement). Priorisierung Bsp. Batterie, E-Auto, Wärmepumpe (PV-Ready), my-PV / AC-THOR Heizstab. (...) Ansonsten sollte es sicherlich mit OpenWB oder evcc das Thema Lastmanagement und Priorisierung kein unmögliches Unterfangen sein."*

openWB wird in der DACH-Community **fast immer in einem Atemzug** mit dem Wort "Lastmanagement" genannt. Das ist eine Marken-Assoziation, die EVCC fehlt (siehe EVCC-Analyse, dort steht explizit im FAQ: "Es ist jedoch heute noch kein Lastmanagement möglich").

Aus Forum-Thread #8271: *"Mit der openWB-software2 kann jede openWB unabhängige Lademodi nutzen — auch 2x PV-Laden. Cool ist auch das Lastmanagement, was softwaremäßig Überlastungen von LSS vorbeugt. (...) Ich bin sehr begeistert, was die Wallbox alles kann."*

**Lehre für Solarbot:** Lastmanagement zwischen mehreren Verbrauchern ist openWBs Stärke und EVCCs offene Baustelle. Solarbot kann hier eine **dritte Position** einnehmen: nicht "Lastmanagement zwischen mehreren Wallboxen" (das ist openWBs Domäne), sondern "**Priorisierung zwischen Verbrauchern unterschiedlicher Klassen**" — Akku vs. Wärmepumpe vs. Heizstab vs. (über EVCC) Auto. Das ist eine andere Achse — und sie ist im V1.x-Roadmap-Plan bereits angedacht.

### 3.2 Modularer Hardware-Aufbau und Reparierbarkeit

Aus dem Photovoltaikforum-Thread "Wer hat negative Erfahrungen mit der OpenWB?": *"Die Verkabelung kann man sicher schöner machen, aber der Vorteil ist einfach, dass die Box aus einzelnen Standard-Teilen aufgebaut ist. In der Taiwan-Box kannst du dann nach dem Ableben eines Kondensators die ganze Box wegwerfen, bei der openWB tauscht du die entsprechende Komponente einfach aus. War übrigens auch einer der Gründe, weshalb ich die openWB gekauft habe."*

Das ist eine identitätsstiftende Aussage: openWB ist **reparierbar**, im Gegensatz zu Wegwerf-Hardware aus Asien. Das spricht eine Wertegruppe an, die sich über Hardware-Souveränität definiert.

**Lehre für Solarbot:** Solarbot ist Software, daher gibt es nichts zu reparieren — aber wir können das gleiche **Werte-Versprechen** geben: **"Solarbot bleibt funktionsfähig, auch wenn ALKLY morgen verschwindet."** Das ist der Software-Pendant zur Hardware-Reparierbarkeit. Konkret: lokale Lizenz-Validierung, keine Cloud-Pflicht, klare Lizenz-Regeln im Insolvenz-Fall.

### 3.3 Touchscreen, MID-Eichung, Plug & Charge

openWB liefert physische Premium-Features, die andere Lösungen nicht haben:
- 7-Zoll-Touchscreen-Display direkt an der Wallbox (für die series2 standard+ und Pro)
- Integrierter MID-geeichter Zähler (rechtssicher für Mietverhältnisse, gewerbliche Abrechnung)
- Plug & Charge mit ISO-15118-Ladecontroller in der Pro-Variante
- Bidirektionales Laden (V2G/V2H) vorbereitet
- Allstromsensitiver Fehlerstromschutz (FI Typ B) integriert
- UV-beständiges Gehäuse für Außenbereich

Aus dem e-mobileo-Shop: *"openWB series2 Pro ist das ideale Modell für gehobene Ansprüche, ist bereits für bidirektionales Laden (V2G, V2H, ...) vorbereitet und beherrscht Plug & Charge."*

**Lehre für Solarbot:** Wir können diese Hardware-Premium-Features nicht liefern. Aber wir können sie **respektieren** und eine andere Differenzierung bauen: **"Solarbot ist die Software-Intelligenz für Leute, die keine 2.000-€-Wallbox brauchen — oder die ihre Wallbox schon haben."** Das ist eine ehrliche Marktöffnung, die niemanden beleidigt.

### 3.4 Deutsche Firma, deutscher Support, deutsche Wertschöpfung

openWB ist eine deutsche GmbH & Co KG mit Sitz und Entwicklung in Deutschland. Das ist ein massives Vertrauenssignal in einer Branche, in der die meisten Konkurrenten chinesische Cloud-Dienste oder amerikanische Hyperscaler nutzen.

Aus dem Forum-Support-Thread: *"Vor 2 Wochen wurde zur noch besseren Partnerunterstützung auch eine Tel.-Hotline eingerichtet, wo alle geschulten Partner im Notfall zugreifen können."*

**Lehre für Solarbot:** Alex und ALKLY sind ebenfalls deutsch. Das ist ein gemeinsamer Wert, kein Konkurrenz-Punkt. Solarbot kann sich als **"die deutsche Software-Antwort auf den deutschen Hardware-Pionier"** positionieren — also komplementär, nicht konfrontativ.

### 3.5 Open Source als Vertrauenssignal

Auch wenn openWB Hardware verkauft: Die Software ist auf GitHub (`snaptec/openWB`) öffentlich einsehbar. Das ist eine seltene Ehrlichkeit in einem kommerziellen Produkt, und sie wird in der Community geschätzt.

**Lehre für Solarbot:** Solarbot ist closed-source. Aber wir können die gleichen **Werte** leben: öffentliche Roadmap, transparente Issue-Tracker, klare Kommunikation. Das ist nicht das Gleiche wie Open Source — aber es ist mehr als das, was die Hersteller-Apps (Anker, Zendure) je liefern werden.

### 3.6 Migration von DIY zur kommerziellen Lösung als bewusste Reife-Geschichte

openWB ist 2018 als "openSource Wallbox Bastel-Idee" gestartet (Original-Quote des Gründers im TFF-Forum) und hat sich systematisch professionalisiert. Diese Reife-Geschichte ist Teil der Marken-Identität: *"Letztes Jahr hauptsächlich als Bastellösung, derweil hat sich aber einiges getan und der Status steht ihr definitiv nicht mehr zu."*

**Lehre für Solarbot:** Solarbots Migration vom Blueprint-Produkt (300+ Käufer) zum vollständigen Solarbot-System ist eine analoge Reife-Geschichte. Die sollte erzählt werden — als Vertrauenssignal an die Beta-Tester und frühen Käufer. Eine Story-Line wie *"Vom Blueprint zur ersten echten Software für die Energiewende-Heimanwender"* ist authentisch und glaubwürdig.

---

## 4. Frust-Punkte — was openWB-Nutzer in den Wahnsinn treibt

### 4.1 Akku-Steuerung ist offiziell nicht vorhanden

Das ist **die** strukturelle Schwäche. Aus mehreren Threads:

**Aus Thread #8729 ("Bei Laden über dynamischen Stromtarif wird Hausbatterie entladen"):** *"Es kann ja auch nicht anders sein, weil openWB die Batterie nicht steuern kann. Du müsstest die Entladung der Batterie selbst sperren, um das zu verhindern."*

**Aus Thread #6332 ("Sofortladen ohne Speicherentladung möglich?"):** *"Nein, denn die OWB kann den Speicher nicht steuern, nur auslesen."*

**Aus Thread #4059 ("Speicher Überschussladen mit openWB Steuerung"):** *"openWB ist nicht wirklich dazu da einen Batteriespeicher zu steuern."* — der User hatte gehofft, openWB würde einen 230V-Speicher über die Wallbox steuern.

**Workaround eines Users:** *"Ich habe einen zusätzlichen Zähler eingebaut und die OWB zwischen diesem und dem Messpunkt des Wechselrichters angeschlossen. Dadurch 'sieht' der Wechselrichter den Verbrauch der OWB nicht und leert dementsprechend auch den Speicher nicht, wenn die OWB das Auto lädt. PV-geführtes Laden ist trotzdem möglich, weil die OWB den zusätzlichen Zähler als Messpunkt nutzt, aber erst, wenn der Speicher voll ist. Für den WR ist das dann schon 'Einspeisung'. Seine Berechnungen für Eigenverbrauch und Autarkie sind damit grundsätzlich falsch. Laden aus dem Speicher ist mit dieser Konfiguration natürlich grundsätzlich unmöglich."*

Das ist ein **physischer Workaround mit Verkabelungs-Tricks**, der die Funktionalität teilweise zerstört, weil der Wechselrichter falsche Werte sieht.

Ein anderer User (mit Node-RED): *"ich hab mir was in Node-Red gebaut wo ich einen Schalter umlege 'EV-Ladung abziehen' und dann wird nur der Hausverbrauch +200W bei unter 80% SoC entladen."* — also ein selbstgebauter Workaround in einer ganz anderen Software.

**Es gibt zwar einen Lichtblick:** Aus Thread #8588 ("Hausakku bei Ladung sperren"): *"Unterstützt dein System aktive Batteriesteuerung, kannst du im 'Batterieeinstellungen' Dialog die Option 'Entladesperre beim Schnelladen' aktivieren. Damit wird die Hausbatterie in einen Sperrzustand versetzt, wenn ein Schnellladevorgang aktiv ist."*

Aber: Diese Funktion ist **nur ein binärer Sperr-Schalter** für ausgewählte Hardware — nicht eine echte Akku-Steuerung. Und ein anderer User pointiert das wunderbar: *"So oder so: EVCC hat bereits eine, wenn auch rudimentäre, aktive Speicher-Steuerung, OpenWB nicht."*

**Solarbot-Differenzierung:** Das ist ein massiver Trumpf für Solarbot. **Akku-Steuerung ist Solarbots Kern, nicht eine optionale Sperr-Funktion.** Während openWB den Akku als unkontrollierbare Black Box behandelt, ist Solarbot von Tag eins darauf optimiert. Botschaft: **"Was openWB für deine Wallbox ist, ist Solarbot für deinen Akku."**

Das ist die gleiche Botschaft, die wir auch gegen EVCC verwenden — aber gegen openWB ist sie noch stärker, weil openWB tatsächlich eine professionelle Wallbox-Lösung ist und die Akku-Lücke in der gleichen Architektur-Klasse besteht.

### 4.2 SD-Karten-Tod als wiederkehrender Albtraum

Das ist mit Abstand der häufigste konkrete Frust-Punkt — und er wird seit Jahren beschrieben.

**Aus Thread #6737 ("SD-Karte defekt OpenWB Standard+"):** *"Hallo, ich habe seit 29.03.23 dasselbe Problem, OpenWB Duo 2020 meldet sich nicht mehr. Heute kam Elektriker hat alles durchgemessen, aber alles ist okay. (...) Wie immer, wenn die Tür auf ist, wollte ich ein Backup (ISO Image) der SD Karte machen, weil das hier empfohlen war. Schon bei Einstecken meldet mein Windows, ob die SD karte neu formatiert werden soll, um sie benutzen zu können."*

**Aus Thread #2430 ("Wo sitzt die SD-Karte"):** *"Bei mir ist auch die SD-Karte defekt. Hat mich etwas überrascht. Daher meine Fragen: Ist das eher ein Ausnahmefall oder muss ich künftig regelmäßig mit einem Crash rechnen und fleißig Backups erstellen?"*

**Aus Thread #119244 ("SD Karte - Langzeit Haltbarkeit"):** *"'Lang'zeitbericht: Mir sind seit 2021 2 SD-Karten ausgefallen. Die erste war die originale von openWB. Ich weiß nicht mehr wann genau die übern Jordan ist. Auf jeden Fall ist dann die damals 'neue' gestern wieder ausgefallen, mit einem komischen Fehlerbild — anscheinend typisch für einen SD-Karten-Defekt: Die Startseite kommt zwar, lädt aber ewig."*

**Aus Thread #5740 ("Vermutlich SD Karte defekt - wie geht es weiter?"):** *"Die OpenWB lässt sich nicht mehr aufrufen und bei einem Startversuch kommen diverse Fehlermeldungen im Display. Ich würde mal auf eine defekte SD Karte tippen. (...) Nun sehe ich aber, dass es wohl kein Image gibt und man sich an den Support wenden soll."*

**Aus Thread #1674 ("Speicherkarte offenbar defekt"):** *"Die Einstellungen bekomme ich aus dem Backup vom November ja wieder raus, aber die Daten sind halt weg. Kann man defekte SD-Karten irgendwie zum Leben erwecken, um noch an die Daten ranzukommen? (Und ja, ich schreibe heute 100 Mal: 'ich soll regelmäßig ein Backup machen')"*

**Die offizielle Antwort der Community ist immer die gleiche:** *"Backup ist immer wichtig. Ist aber auch kein großer Aufwand wenn man es einmal eingerichtet hat."* Aber wenn die Box stirbt, ohne dass ein aktuelles Backup existiert, sind oft monatelange Verbrauchsdaten weg.

**Solarbot-Differenzierung:** Solarbot läuft auf der HA-Installation des Nutzers. HA hat eingebaute Backup-Mechanismen (Snapshots), die unabhängig von Solarbot funktionieren. Solarbot selbst speichert Konfiguration als HA-Add-on, also im HA-Backup-Mechanismus. **Es gibt keinen separaten "Solarbot stirbt, Daten weg"-Ausfallpunkt.** Das ist ein massiver Stabilitäts-Vorteil — und sollte aktiv vermarktet werden: *"Solarbot teilt sich das Schicksal deines Home Assistant. Wenn HA läuft, läuft Solarbot. Wenn HA gesichert ist, ist Solarbot gesichert."*

### 4.3 Software 2.x: Update-Drama und Konfigurationsverlust

Die Migration von der "Legacy"-Software 1.9 auf die neue Software 2.x ist seit 2023 ein dauerndes Drama. Hier sind die Stimmen:

**Aus Thread #7469 ("Update von 1.9 auf 2.0 Probleme"):** *"Habe wie beschrieben die SD Karte getauscht und neu gebootet. (...) Habe die Einstellungen für das von openwb gekaufte EVU Kit gemacht (siehe Anhang) und gespeichert. Nach dem Speichern habe ich das evu kit wieder aufgerufen. Die eingegeben Daten fehlten. Siehe Anhang. Das gleiche passiert auch bei meinem Wechselrichter von SMA."*

Speichern, neu öffnen, Daten weg. Das ist ein klassischer kritischer Bug, und er passierte während des Roll-outs einer neuen Major-Version.

**Aus Thread #8063 ("openWB bootet mehrfach am Tag nach Update auf 2.x"):** Ein User berichtet, dass die openWB nach dem Update auf 2.x stündlich neu startet. Antwort des Admins: *"Wir haben gerade ein neues Patch-Release freigegeben (2.1.2-Patch.2), welches die Probleme mit der rc.local und somit den Neustarts behebt. Wichtig: Das Update sollte nach Möglichkeit nicht gemacht werden, wenn der nächste Neustart durch den Bug in den nächsten 5 Minuten ansteht! Lieber einen weiteren Reboot abwarten, damit das Update nicht durch ein sehr blödes Timing zwischendurch abgewürgt wird."*

Übersetzt: **Update darf nicht in einem 5-Minuten-Fenster vor dem nächsten Bug-Reboot passieren — sonst geht das Update kaputt und die Box ist im undefinierten Zustand.** Das ist eine erschreckende User-Experience-Anweisung.

**Aus Thread #9161 ("Lohnt sich der Umstieg auf 2.0?"):** *"Ich habe vor Kurzem einen Umstiegsversuch mit meiner series2 Duo unternommen und diesen nach rund 14 Tagen abgebrochen (also die 1.9er SD gut aufbewahren)."*

Der User hat 14 Tage versucht, ist gescheitert, ist zurück auf die alte SD-Karte. Das ist ein Update-Erlebnis, das Nutzer für lange Zeit prägt.

**Aus Thread #7360 ("Konfigurationsprobleme nach Update auf Software 2.0"):** Ein DIY-openWB-Nutzer mit zwei Ladepunkten kann nach dem Update keine Verriegelung mehr aktivieren, der zweite Ladepunkt startet überhaupt nicht. Antwort: *"Das Problem ist, dass man die später tausendfach genutzte sw2 ungern für 'DIY-Sonderlocken' auslegt."* — Übersetzung: Die neue Software ignoriert bewusst Edge-Cases, die in der alten Version funktionierten.

**Aus dem aktuellen Alpha-Test-Thread (Thread #141060, Software 2.2.0 Alpha 1):** Ein Beta-Tester berichtet:
- *"Variabler Strompreis wird im Status nicht angezeigt — neu Laden der Konfiguration von Tibber löste es auch nicht"*
- *"Auf dem iPhone erhalte ich in der 'App' ständig (etwa alle 60s) die Meldung über Verbindungsabbrüche"*
- *"Es ist in Safari Browser nicht möglich Werte mit Komma oder Punkt einzugeben — Feld wird rot"*
- *"Auf dem Smartphone (iPhone 15 Pro/das kleine) Formatierungsfehler bei allen Slidern"*

Das ist die aktuelle Beta-Software. UI-Bugs auf iPhones, Eingabe-Validierung bricht in Safari, Strompreis-Anzeige bricht. Und **das ist die Premium-Lösung**, für die Nutzer 1.500 € bezahlt haben.

**Solarbot-Differenzierung:** Solarbots Update-Pfad ist **fundamental anders**:
- Updates über den HA Add-on Store (atomar, mit Rollback)
- Konfiguration wird automatisch mitgewandert (HA-Standard)
- Keine SD-Karten-Tausch-Aktionen
- Keine "5-Minuten-Bug-Fenster"
- Konsequente Versionierung mit klaren Migrations-Schritten

Im PRD ist das bereits angedacht und sollte hier nochmal als prominentes Differenzierungs-Merkmal markiert werden. Botschaft: **"Solarbot updatet sich selbst. Du machst nichts."**

### 4.4 Lieferzeiten und Vorkasse-Frust

**Aus Thread "Wer hat negative Erfahrungen mit der OpenWB?":** *"Das Projekt liest sich sehr gut. Deshalb habe ich im Mai eine 2x11kw Duo bestellt und 2000 Euro VORKASSE bezahlt. Aus Lieferung nach ca 12 Wochen werden jetzt ca. 20 Wochen. Das habe ich erst erfahren auf Nachfrage, nachdem 10 Wochen vorüber waren. Der Kundenservice antwortet. Inhaltlich ehrlich ist man nicht und schiebt es auf ein 'überrennen' aufgrund der Förderung. Planen lässt sich leider so nicht, auch keinen Elektriker motivieren."*

**Aus Thread #6535 ("Erfahrungen mit dem Support"):** Ein bekannter openWB-Fan beschwert sich über Funkstille beim Support: *"Bereits am Folgetag hat mich der Support kontaktiert und um die Zugangsdaten der openWB-Cloud gebeten, die ich dann auch umgehend bereitgestellt habe. Soweit alles i.O. Danach allerdings Funkstille. Am 30.01. habe ich mal vorsichtig nachgefragt, ob meine Zugangsdaten angekommen seien — keine Reaktion."*

2.000 € Vorkasse, doppelte Lieferzeit, Support antwortet nicht. Das ist Hardware-Geschäft im Jahr 2024 — und es zeigt einen fundamentalen Nachteil des Hardware-Modells: **Wenn etwas schiefgeht, hängt man fest.**

**Solarbot-Differenzierung:** Solarbot hat keinen Lieferprozess. Kein Versand, keine Vorkasse, keine 20-Wochen-Wartezeiten. Klick → installiert → läuft. Das ist nicht nur ein Convenience-Vorteil, das ist ein **fundamentaler Geschäftsmodell-Vorteil** — und in Zeiten von Lieferketten-Unsicherheit ein massives Verkaufsargument.

### 4.5 Hoher Preis im Vergleich zu Standard-Wallboxen

Aus dem TFF-Forum (Thread "openWB series2 standard+ & Model Y"): *"Wir haben die openWB dann gecancelt und uns für ein Drittel des Preises den Tesla Gen 3 Wall Connector (inkl. Förderung) geholt. Für uns klappt das wunderbar. Zudem ändert sich unser Fahr- und Ladeprofil andauernd, da müsste ich auch bei der openWB laufend nachkonfigurieren. (...) Bei anderen Herstellern mag die open WB noch mehr Sinn machen. Ich vermisse sie beim Tesla nicht und auch wenn 1000 Euro Ersparnis schnell 'verladen' sind, gespart ist gespart."*

Aus Thread #8271 ("Richtige Komponenten?"): *"Die openWB Pro klingt zwar interessant, aber ich benötige bidirektionales Laden auch in Zukunft nicht und die Fahrzeugidentifikation ist mir der Aufpreis von 1200€ nicht wert. Mir geht es nur um Überschussladen für erstmal 2 Fahrzeuge und die OpenWB ist so schon nicht die preiswerteste Wallbox und ist doppelt so teuer wie die vom Installateur vorgeschlagenen KEBA-Wallboxen."*

Eine openWB kostet je nach Modell 1.000–2.500 €. Eine generische 11-kW-Wallbox kostet 400–700 €. Der Aufpreis ist die Software-Intelligenz — aber für viele Nutzer ist dieser Aufpreis nicht verständlich, weil sie die Software-Tiefe nicht erkennen.

**Solarbot-Differenzierung:** Solarbot kostet ein Bruchteil davon — und liefert die Software-Intelligenz **ohne Hardware-Verpflichtung**. Das ist eine gigantische Marktöffnung für die Gruppe, die "openWB klingt cool, aber ich gebe keine 1.500 € für eine Wallbox aus" sagt.

Konkrete Botschaft: **"openWB ist die deutsche Premium-Hardware-Lösung. Solarbot ist die deutsche Premium-Software-Lösung — ohne Hardware-Pflicht."**

### 4.6 Lastmanagement bei Netzwerk-Ausfall: keine Sicherheit

**Aus Thread #4533 ("Lastmanagement, bei Ausfall der Messung"):** *"Bin ehrlich gesagt etwas überrascht, dass die Hausanschlussüberwachung anscheinend nicht zufriedenstellend umgesetzt ist. Es geht ja nicht nur um Zählerausfälle, der Router kann sich aufhängen, das Netzwerk kann warum auch immer gestört sein, ein Switch geht hinüber usw. Der Hinweis auf die elektrischen Absicherungen ist ja wohl nicht ernst gemeint?"*

Antwort eines anderen Users: *"Zusammengefasst bedeutet das doch, fällt das Netzwerk aus und aufgrund dessen kann eine Fremd-WB nicht mehr gesteuert werden, ist das ein absolutes No-Go aufgrund dessen z.B. das Lastmanagement gegenüber dem VNB nicht bestätigt wird. Fällt hingegen das Netzwerk aus und die openWB bekommt die für das Lastmanagement zwingend notwendigen Informationen nicht mehr, erfolgt keine Anpassung der Ladeleistung um den Hausanschluss vor einer eventuellen Überlast zu schützen, sondern die Ladung läuft unverändert weiter."*

Übersetzt: openWBs Lastmanagement schützt **nicht zuverlässig** vor Hausanschluss-Überlast, wenn das Netzwerk hängt. Das ist ein schweres Sicherheits-Fragezeichen für eine Lösung, die explizit als "Lastmanagement-System" vermarktet wird.

**Solarbot-Differenzierung:** Solarbot macht **kein** klassisches Wallbox-Lastmanagement (das ist EVCCs/openWBs Domäne). Aber Solarbot kann transparenter mit Ausfällen umgehen: Im Diagnose-Tab wird sichtbar, wenn eine Quelle länger nicht aktualisiert wurde, und Fail-Safe-Modi lassen sich konfigurieren. Das ist im PRD bereits angedacht.

### 4.7 Konfiguration ist DIY-historisch komplex geblieben

Mehrere Threads zeigen, dass die openWB-Konfiguration eine Lernkurve hat, die für Mainstream-Nutzer zu steil ist.

**Aus Thread #6535:** *"So flexibel die Box ist, so komplex kann sie sein. Es gibt sehr viele Features, sehr viele unterstützte Hersteller von PV Anlagen, und die Masse an BEV kommt auch erst jetzt so auf die WB Hersteller zu."*

**Aus Thread #7145 ("Update von Software 1.9x auf 2.x"):** *"Die '+'-Dialoge und der Prozess, etwas neues konfigurieren zu können, sind etwas ungewöhnlich, da nach '+' der ergänzte Zweig nicht automatisch geöffnet wird. Was ich vermisse und auch den Unmut von anderen Benutzern der Wallbox auf sich ziehen wird: Das schnelle Umschalten über das Wallbox-Display von 'PV' auf 'Sofort-Laden' mit zwei Klicks."*

Selbst ein Power-User, der den Umstieg professionell durchführt, findet die UI-Hierarchie und das Bedienkonzept unintuitiv.

**Solarbot-Differenzierung:** Solarbots UX-Plan (Klarheit vor Features, Ergebnis vor Technik, Freude durch Reduktion) ist die direkte Antithese. Wir können einen klaren Vergleich machen: openWB hat 50+ Konfigurations-Optionen pro Ladepunkt, Solarbot hat 5 Hauptmodi. Beide haben ihren Platz — aber für die Mainstream-Zielgruppe ist Solarbot zugänglicher.

### 4.8 MQTT-Komplexität bei HA-Integration

**Aus dem openWB-Forum (HA-Integration):** *"Die openWB ist per MQTT komplett von außen steuerbar und auch konfigurierbar. Es ist ein bekanntes Problem, dass nicht ordnungsgemäß eingerichtete Integrationen Probleme ganz grundsätzlicher Art bereiten."*

Übersetzt: openWB lässt sich über MQTT mit HA verbinden, aber die Integration ist fragil und kann Grundfunktionen brechen. Der Support empfiehlt: erst openWB standalone konfigurieren, dann erst HA dranhängen.

**Solarbot-Differenzierung:** Solarbot **ist** ein HA Add-on. Es gibt keine externe Integration, keine MQTT-Bridge, keine "Standalone vs. mit HA"-Unterscheidung. Solarbot ist HA-nativ, von der ersten Sekunde an.

### 4.9 Cloud-Support-Modell vs. echte lokale Kontrolle

openWB hat einen Cloud-Dienst (openWB-Cloud) für Remote-Zugriff und Support-Aktionen. Mehrere Threads zeigen, dass dieser Cloud-Dienst auch für scheinbar simple Aktionen erforderlich ist (z. B. die Umstellung von 11 auf 22 kW über den Shop).

Das ist nicht "böse Cloud" wie bei Anker — aber es ist ein Hybrid, der die "100 % lokal"-Botschaft schwächt.

**Solarbot-Differenzierung:** Solarbot ist **keine** Cloud-Anbindung. Lizenz-Aktivierung läuft einmal, danach ist alles lokal. Botschaft: *"Wenn dein Internet ausfällt, läuft Solarbot weiter. Wenn ALKLY morgen verschwindet, läuft Solarbot weiter."*

### 4.10 Hardware-Lock-in trotz "Open Source"-Versprechen

Auch wenn die Software offen ist: Wer eine openWB-Hardware kauft, ist faktisch an das openWB-Ökosystem gebunden. Die SD-Karten sind personalisiert (siehe Thread #6737: *"Die Karten sind personalisiert. Unter Anderem mit der Seriennummer."*), die Hardware lässt sich nicht trivial mit fremder Software flashen, und der Support deckt nur das eigene Setup ab.

Das ist nicht vorwerfbar — aber es ist ein **echter Lock-in**, der in der Marketing-Botschaft "Open Source" gerne übersehen wird.

**Solarbot-Differenzierung:** Solarbot hat **null Hardware-Lock-in**. Der Nutzer kann morgen aufhören, Solarbot zu nutzen, und seine HA-Installation läuft weiter. Das ist eine Form von Freiheit, die nur Software-only-Lösungen bieten können.

---

## 5. Strukturelle Schwächen — die Architektur-Wahrheiten

**S1: Hardware-Geschäft hat Lieferketten-Risiken.** Wenn ESP32 oder Steckdosen-Komponenten knapp werden, leiden die Lieferzeiten. Solarbot hat dieses Problem null.

**S2: SD-Karten-Speicher ist ein bekanntes Single-Point-of-Failure.** openWB nutzt es seit Jahren und hat es nicht gelöst. Das ist eine architektonische Entscheidung, die nicht reversibel ist, ohne die gesamte Hardware-Linie zu überarbeiten.

**S3: Software 2.x ist seit zwei Jahren in der Migration.** Das zeigt, wie schwer eine grundlegende Architektur-Modernisierung in einem Hardware-gebundenen Produkt ist.

**S4: Akku-Steuerung ist nicht geplant.** Im Forum gibt es seit Jahren Anfragen, openWB hat sie nie priorisiert — vermutlich, weil es nicht zur Wallbox-Identität passt.

**S5: openWB hat ein zweischneidiges Verhältnis zu DIY.** Der Gründer beschreibt openWB als "ehemals Bastelprojekt, jetzt seriös" — das hat einen alten DIY-Teil der Userbase entfremdet, der jetzt zu EVCC oder OpenDTU abwandert.

**S6: Premium-Preis bei wachsendem Wettbewerbsdruck.** EVCC liefert Wallbox-Steuerung kostenlos für zahllose Drittanbieter-Wallboxen. Das setzt openWB unter Druck — entweder müssen sie billiger werden, oder sie müssen rechtfertigen, warum die eigene Hardware den Aufpreis wert ist.

**S7: Cloud-Dienst als versteckte Abhängigkeit.** Auch wenn die Cloud "nur" für Support-Zwecke ist: Sie ist da, sie könnte ausfallen, und sie schwächt die "100 % lokal"-Story.

---

## 6. Solarbot-Differenzierung — wo wir konkret anders sind

| Dimension | openWB | Solarbot |
|---|---|---|
| Geschäftsmodell | Hardware + Software gebündelt | Software-only, Add-on |
| Einstiegspreis | 1.000 € (Custom) bis 2.500 € (Pro) | Bruchteil |
| Lieferzeit | 12–20 Wochen | Sofort-Download |
| Akku-Steuerung | Nicht möglich | Kern-Feature |
| Wallbox-Steuerung | Stärke (eigene Box) | Nicht Solarbots Domäne |
| Lastmanagement | Mehrere Wallboxen | Verbraucher-Priorisierung (Akku/WP/Heizstab/EVCC) |
| SD-Karten-Tod-Risiko | Wiederkehrend | Null (HA-basiert) |
| Update-Pfad | SD-Karten-Tausch + Bug-Fenster | HA Add-on Store, atomar |
| Konfigurations-Komplexität | DIY-historisch hoch | Minimalistisch by design |
| Cloud-Abhängigkeit | Hybrid (Support-Cloud) | Vollständig lokal |
| Hardware-Lock-in | Faktisch ja (personalisierte SD) | Null |
| Zielgruppe | Premium-EFH mit Wallbox-Bedarf | Balkonkraftwerk + Speicher |
| Migration-Pfad | Schmerzhaft (1.9 → 2.x) | Updates automatisch |

---

## 7. Co-Existenz-Strategie: Komplementäre Positionierung statt Konfrontation

openWB ist anders zu positionieren als die bisherigen Wettbewerber. Es ist **nicht** ein offener Konkurrent wie EVCC (gegen den wir mit Co-Existenz arbeiten), und es ist **nicht** ein potenzieller Partner wie EOS. Es ist ein **etablierter Premium-Hardware-Anbieter** in einem angrenzenden Segment, und der richtige Umgang ist:

**1. Respekt vor der Pionierarbeit.** openWB hat 2018 als Bastelprojekt angefangen und ist heute eine ernstzunehmende Firma mit deutscher Wertschöpfung. Das verdient Anerkennung — und ist **gemeinsame Wertegrundlage** mit ALKLY/Solarbot.

**2. Klare Markt-Trennung.** openWB ist die Lösung für: "Ich brauche eine deutsche, lokale, professionelle Wallbox mit Energiemanagement und ich gebe gerne 1.500–2.500 € dafür aus." Solarbot ist die Lösung für: "Ich habe schon eine Wallbox (oder will eine günstige), und ich brauche die Akku-Steuerungs-Intelligenz."

**3. Kein direkter Vergleich auf der Landing Page.** openWB ist eine **angrenzende Kategorie**, kein direkter Wettbewerber. Wir vergleichen uns nicht mit Wallbox-Anbietern auf der Landing Page, weil wir keine Wallbox sind.

**4. Software-Intelligenz für openWB-Nutzer als V2-Idee.** Wenn ein openWB-Nutzer gleichzeitig einen Akku hat (und das ist die wachsende Zielgruppe), kann Solarbot als **Komplement** dienen: openWB regelt das Auto, Solarbot regelt den Akku. Beide laufen auf der gleichen HA-Installation. Das ist eine technisch saubere Integration.

**5. Eine sehr konkrete Zielgruppen-Brücke.** Es gibt eine Gruppe von openWB-Nutzern, die **frustriert** sind, weil openWB ihren Akku nicht steuert. Diese Gruppe ist eine **wertvolle Solarbot-Zielgruppe**, weil sie HA bereits nutzt, das technische Verständnis hat und Solarbot als die fehlende Puzzle-Stelle erkennt.

---

## 8. Was Solarbot von openWB lernen muss

**1. Lastmanagement als Konzept ernst nehmen.** openWB hat das Konzept seit Jahren etabliert. Solarbot muss eine analoge "Verbraucher-Priorisierung" liefern — auch wenn es eine andere Achse ist (Akku/WP/Heizstab statt mehrere Wallboxen). Im PRD V1.x angedacht.

**2. Premium-Anspruch in der UX.** openWB hat einen klaren Premium-Anspruch: "Wir sind teurer, aber wir liefern Qualität." Solarbot ist nicht teuer im Vergleich, aber wir können einen analogen Qualitäts-Anspruch leben: **"Solarbot ist nicht das Billigste, aber das Beste — für das, was es tut."**

**3. Deutsche Wertschöpfung als Vertrauenssignal.** openWB nutzt das systematisch in der Außenwirkung. ALKLY ist ebenfalls deutsch — das sollte stärker in der Solarbot-Außenkommunikation sein.

**4. Modulare Hardware-Idee als Software-Pendant.** openWB ist reparierbar, weil die Komponenten austauschbar sind. Solarbot kann analog **modular und transparent** sein — z. B. mit klaren Schnittstellen, Profile-Marketplace (V1.x), einer Architektur, die Drittanbieter-Erweiterungen ermöglicht.

**5. Forum als Community-Kraft.** openWB hat ein extrem aktives Forum (forum.openwb.de) mit hunderten von Threads pro Woche. Das ist ein massiver Vermögenswert. Alex hat schon einen Discord — der sollte die gleiche Energie und Frequenz bekommen.

**6. Open-Source-Software trotz kommerzieller Hardware.** openWB beweist, dass sich Open Source und kommerzielles Geschäftsmodell **nicht ausschließen müssen**. Solarbot ist closed-source — aber wir können langfristig darüber nachdenken, ob Teile (z. B. die Profile-Marketplace-Definitionen) Open Source werden.

---

## 9. Was Solarbot konkret besser machen muss als openWB — die fünf Prioritäten

**Priorität 1: Akku-Steuerung als nicht-verhandelbarer Kern.**
Während openWB den Akku als Black Box behandelt, ist Solarbots gesamte Architektur darauf ausgelegt, Akkus zu orchestrieren. Direkte Antwort auf 4+ openWB-Forenstimmen, die diese Lücke schmerzhaft beschreiben.

**Priorität 2: Null-SD-Karten-Risiko.**
Solarbot teilt sich das Schicksal der HA-Installation. HA hat eingebaute Backup-/Snapshot-Mechanismen. Es gibt keinen separaten "Solarbot stirbt"-Ausfallpunkt. Direkte Antwort auf jahrelangen SD-Karten-Tod-Frust.

**Priorität 3: Atomare Updates ohne Bug-Fenster.**
Solarbot updatet sich über den HA Add-on Store, mit automatischen Backups und sauberem Rollback. Direkte Antwort auf das Software-2.x-Migrations-Drama von openWB.

**Priorität 4: Sofortige Verfügbarkeit ohne Lieferzeit.**
Klick → installiert → läuft. Keine 20-Wochen-Wartezeiten, keine Vorkasse. Direkte Antwort auf den 2.000-€-Vorkasse-Frust aus dem PV-Forum.

**Priorität 5: 100 % lokal, ohne Hybrid-Cloud.**
Lizenz-Aktivierung einmal, danach vollständig lokal. Keine "Support-Cloud", keine "Cloud-Synchronisation", nichts. Direkte Antwort auf openWBs hybriden Cloud-Ansatz.

---

## 10. Botschaften, die direkt verwendbar sind

Drei fertige Sätze für Landing Page, Pitch und Outreach:

> **"openWB ist die deutsche Premium-Wallbox mit Software. Solarbot ist die deutsche Premium-Software ohne Hardware-Pflicht."**

> **"Was openWB für deine Wallbox ist, ist Solarbot für deinen Akku."**

> **"Keine SD-Karten, keine Lieferzeiten, keine Update-Bug-Fenster. Solarbot teilt sich das Schicksal deines Home Assistant — und wenn das läuft, läuft Solarbot."**

Eine vierte Botschaft, speziell für die "frustrierten openWB-Nutzer":

> **"Du hast eine openWB und einen Akku, der dich frustriert? Solarbot regelt deinen Akku — openWB lädt weiter dein Auto. Beide leben friedlich auf der gleichen Home-Assistant-Installation."**

---

## 11. Risiken und blinde Flecken

**Risiko 1: openWB baut Akku-Steuerung in V2.2 oder V2.3 nach.** Möglich, aber unwahrscheinlich, weil es nicht zur Marken-DNA passt. Falls doch, bleibt Solarbots Setup-Einfachheit und das fehlende Hardware-Bundle trotzdem differenzierend.

**Risiko 2: openWB-Community fühlt sich angegriffen.** Real, aber durch die "komplementäre Positionierung"-Strategie minimiert. Wir greifen openWB nirgends frontal an — wir sagen nur: "Wir bedienen ein anderes Segment."

**Risiko 3: Wir unterschätzen das deutsche Premium-Hardware-Segment.** openWB beweist, dass es eine Käufergruppe gibt, die für Qualität und deutsche Wertschöpfung gerne 1.500 € zahlt. Solarbot zielt auf eine andere Gruppe — aber die Existenz dieser Gruppe sollte uns nicht überraschen.

**Risiko 4: openWB schmiedet Allianzen mit Speicher-Herstellern.** Das wäre ein direkter Angriff auf Solarbots Kern. Mitigation: Solarbot baut früh seine eigenen Partnerschaften zu Speicher-Shops auf (siehe DIY-Analyse, Punkt zur Distribution über selbstbau-pv.de etc.).

**Risiko 5: Cloud-Dienst-Skandal trifft openWB.** Falls openWBs Support-Cloud kompromittiert wird, kann das die gesamte deutsche Premium-Wallbox-Branche unter Druck setzen. Solarbot ist davor sicher, weil es keine Cloud hat.

---

## 12. Konkrete nächste Schritte

**Sofort (vor Spike-Phase):**
- Im PRD verankern, dass openWB als **angrenzende Kategorie**, nicht als direkter Wettbewerber behandelt wird. Solarbot vergleicht sich nicht mit Wallbox-Anbietern.
- Eine **konkrete Zielgruppen-Persona** für "openWB-Nutzer mit Akku-Frust" definieren — das ist eine sehr wertvolle Akquisitions-Quelle.

**Vor Beta:**
- Eine kurze Doku-Seite "Solarbot mit openWB kombinieren" vorbereiten — fair, technisch korrekt, ohne Konkurrenz-Sprech. Das ist ein Asset für die Brücken-Zielgruppe.
- Im openWB-Forum (sehr vorsichtig, sehr respektvoll) testen, ob Akku-Steuerungs-Frage einen Hinweis auf Solarbot rechtfertigt — niemals als Spam, immer als hilfreiche Information.

**Beta-Phase:**
- 2–3 openWB-Nutzer als Beta-Tester gewinnen, die einen Akku haben und die Lücke schmerzhaft kennen. Ihre Erfahrungs-Berichte sind besonders wertvoll, weil sie die "Komplement"-Story aus erster Hand erzählen können.
- Ein Vergleichs-Artikel auf alkly.de: *"openWB vs. Solarbot — wofür brauchst du was?"* Fair, beide Tools positiv, klare Empfehlung "wenn du eine Wallbox kaufen willst und Geld hast: openWB. Wenn du einen Akku optimieren willst: Solarbot."

**Post-Launch:**
- Beobachten, ob aus dem openWB-Forum Anfragen kommen ("ich habe eine openWB, aber meinen Akku will sie nicht steuern — was tun?"). Diese User sind die wertvollste Solarbot-Akquisitionsquelle aus der openWB-Welt.
- Falls openWB jemals eine HA-Integration verbessert: Solarbot kann darauf aufbauen. Wir lesen openWB-Daten als "Wallbox-Verbraucher" und priorisieren entsprechend.

---

## 13. Die wichtigste Erkenntnis dieser Analyse

openWB ist die einzige der vier bisher analysierten Lösungen, die **als direkte Vergleichs-Folie** für Solarbot **nicht** taugt — weil sie ein anderes Geschäftsmodell ist (Hardware + Software gebündelt), eine andere Zielgruppe bedient (Premium-EFH mit Wallbox-Bedarf) und ein anderes Preissegment besetzt (10–25× teurer).

Aber: openWB ist **kulturell** eine wichtige Referenz. Die Community-Stimmen aus dem openWB-Forum zeigen, was deutsche Solar-Power-User wirklich wollen:

- Lokale Kontrolle ohne China-Cloud
- Deutsche Wertschöpfung
- Reparierbarkeit / Open Source
- Lastmanagement und Priorisierung
- Ehrliche Kommunikation
- Lange Lebensdauer (auch wenn die Realität mit SD-Karten-Tod und Update-Drama dem Anspruch nicht immer gerecht wird)

Das sind exakt die **gleichen Werte**, die Solarbot leben muss. openWB ist nicht der Feind — openWB ist die deutsche Premium-Hardware-Schwester, mit der Solarbot **gemeinsam ein Ökosystem** bilden kann. Und die wertvollste taktische Erkenntnis: **Solarbot kann die Software-Antwort für die Akku-Lücke sein, die openWB seit Jahren offen lässt.**

Wenn das gelingt, ist Solarbot nicht nur ein Konkurrent in einem überfüllten Markt — Solarbot ist die fehlende Komponente in einem deutschen Premium-Energiemanagement-Stack, der heute aus openWB (Wallbox), Solarbot (Akku) und HA (Backbone) besteht. Das ist eine Position, die niemand sonst in dieser Klarheit bedient.

---

## 14. Anhang: Übersicht der zitierten Quellen

**Foren:**
- forum.openwb.de (>15 Threads zitiert: #6535, #6737, #6855, #7145, #7360, #7396, #7469, #7880, #8063, #8271, #8588, #8663, #8729, #9161, #9744, #119244, #141060, #141060)
- Photovoltaikforum (Threads "Wer hat negative Erfahrungen mit der OpenWB?", "WR-Empfehlung bei openWB Pro", "Empfehlung Wechselrichter")
- TFF Forum (Threads "openWB - Informationen und Fragen", "openWB series2 standard+ & Model Y")

**Shops und Hersteller-Seiten:**
- e-mobileo.de (openWB series2 Pro, standard+)
- openWB-Wiki und GitHub `snaptec/openWB`

**Insgesamt:** ~25 Original-Quellen, alle auf Deutsch, primär aus dem deutschen Solar- und E-Mobilitäts-Ökosystem zwischen 2019 und 2026. Alle Zitate sind im Original-Wortlaut wiedergegeben.
