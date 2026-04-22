# Wettbewerber-Profil 3: OpenDTU + DIY-Skripte
**Tiefen-Analyse mit Original-Nutzerstimmen, Begeisterungs-Features, regulatorischen Risiken und Solarbot-Differenzierung**

Stand: April 2026 · Quellen: GitHub (`tbnobody/OpenDTU`, `hoylabs/OpenDTU-OnBattery`, `Selbstbau-PV/*`, GitLab `p3605/hoymiles-tarnkappe`), Photovoltaikforum, Akkudoktor-Forum, ioBroker-Forum, HomeMatic-Forum, Shelly-Forum, BornCity-Blog, panelretter.de, blinkyparts.com, selbstbau-pv.de

---

## 1. Vorbemerkung — warum diese Analyse anders ist als die zwei vorherigen

EVCC und EOS sind **Produkte** mit einem Maintainer-Team, einer Roadmap und einer Marke. OpenDTU + DIY ist etwas anderes: **eine Bewegung, ein Ökosystem, eine Bastler-Kultur.** Es gibt nicht "die" DIY-Lösung — es gibt OpenDTU als Hardware-Brücke, OpenDTU-OnBattery als Fork mit Dynamic Power Limiter, ein Dutzend Python-Skript-Forks (alle abstammend von einem Ur-Projekt namens "hoymiles-tarnkappe" auf GitLab), Node-RED-Flows, ioBroker-Adapter, IP-Symcon-Module und unzählige individuelle Bastel-Setups.

Diese Welt zu analysieren bedeutet: **Wir analysieren die Pioniere, von denen Solarbot lernen und deren Wissen Solarbot in Software gießen muss — ohne ihre Komplexität zu erben.** Die DIY-Bastler werden nie zu Solarbot-Kunden, aber sie sind die wichtigsten **Multiplikatoren** für die Mainstream-Zielgruppe, die Solarbot bedient. Wenn die DIY-Community Solarbot respektiert ("ja, das ist ehrlich gemacht und nimmt unsere Erkenntnisse auf"), wird sie es ihren Eltern, Geschwistern und Nachbarn empfehlen. Das ist ein riesiger Hebel.

Diese Analyse ist daher länger und tiefer als die vorherigen — weil sie nicht nur einen Wettbewerber beschreibt, sondern ein gesamtes Ökosystem, das Solarbot teilweise kannibalisieren und teilweise rekrutieren kann.

---

## 2. Die Bestandteile des DIY-Stacks im Überblick

### 2.1 OpenDTU (Original, von tbnobody)

**Was es ist:** Eine ESP32-basierte Hardware/Firmware-Brücke, die mit Hoymiles-Mikrowechselrichtern über deren proprietäres Funkprotokoll (NRF24L01+ für 2,4 GHz HM-Serie, CMT2300A für 868 MHz HMS/HMT-Serie) kommuniziert. Stellt ein Webinterface, eine REST-API und MQTT-Topics bereit.

**GitHub-Sterne:** ~2.100 (`tbnobody/OpenDTU`), ~567 Forks
**Maintainer:** Thomas Basler (tbnobody), Jan und ein wachsendes Community-Team
**Erstes Release:** Sommer 2022
**Relevanter Quote von panelretter.de:** *"Das ganze Projekt nennt sich OpenDTU und besteht aus einem WLAN-fähigen Mikrocontroller (ESP32) und einem Funktransceiver (NRF24). Mit der entsprechenden Software lässt sich so binnen 30 min ein voll funktionsfähiges Gateway mit Webinterface zaubern!"*

### 2.2 OpenDTU-OnBattery (Fork von hoylabs)

**Was es ist:** Ein Fork von OpenDTU, der zusätzlich Batterie-Management-Systeme (BMS), Power-Meter und einen **Dynamic Power Limiter (DPL)** unterstützt. Aus dem README: *"Its Dynamic Power Limiter can adjust the power production of one or more solar- and/or battery-powered inverter(s) to the actual household consumption. In this way, it is possible to implement a zero export policy."*

**GitHub-Sterne:** ~472 (`hoylabs/OpenDTU-OnBattery`), ~101 Forks
**Maintainer:** hoylabs-Team
**Besonderheit:** Kann eine echte Nulleinspeisung **ohne externe Software** umsetzen — der DPL läuft direkt auf dem ESP32. Das ist die "all-in-one"-Antwort der DIY-Welt.

### 2.3 Selbstbau-PV-Python-Skripte und Forks

**Was es ist:** Eine Familie von Python-Skripten, die alle auf das Ur-Projekt `hoymiles-tarnkappe` von p3605 auf GitLab zurückgehen. Jedes Skript liest einen Smart Meter (Shelly 3EM, Shelly Pro 3EM, Tasmota, IR-Lesekopf, Emlog, Cerbo GX), berechnet die Nulleinspeisung und schreibt die neue Wirkleistungs-Grenze über die OpenDTU-REST-API in den Wechselrichter.

**Bekannte Forks:**
- `Selbstbau-PV/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EM` (Original-Fork von der Selbstbau-PV-Initiative)
- `svnhpl/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EMpro` (für den Pro 3EM mit anderer API)
- `mcleinn/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-CerboGX` (für Victron Cerbo GX)
- `zfrank2601/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Emlog` (für Emlog)
- ein Dutzend weitere

**Charakteristik:** Jeder Fork löst ein einzelnes, sehr spezifisches Setup. Wenn der Smart Meter wechselt, wechselt auch das Skript — oder es wird gepatcht. Es gibt keinen Maintainer im klassischen Sinne, kein Versions-Management, keine Update-Sicherheit.

### 2.4 Node-RED-Flows, ioBroker-Adapter, IP-Symcon-Module

**Was es ist:** Plattform-spezifische Implementierungen der gleichen Logik. Node-RED-Flows nutzen visuell gepatchte Boxen, ioBroker-Adapter integrieren OpenDTU als "Geräte-Adapter", IP-Symcon-Module wie `roastedelectrons/HoymilesOpenDTU` machen das Gleiche für die IP-Symcon-Welt.

**Beispiel iobroker-Forum:** *"Ich habe einen Hoymiles HM-600 und der sendet erfolgreich seine Daten in den IO-Broker über die OpenDTU. Laut Dokumentation von openDTU kann ich die Leistungsbegrenzung auch auf dem Weg in den Wechselrichter schreiben. Wenn ich das aber mache, dann erscheint der neue Wert nur kurz beim Objekt in IOBroker und wird danach dann wieder von der DTU überschrieben. Was habe ich übersehen?"*

Das ist exemplarisch: Selbst erfahrene ioBroker-User stolpern über die "MQTT cmd vs status"-Falle (siehe später Pain Point #5).

### 2.5 Hoymiles-Tarnkappe (das Ur-Projekt auf GitLab)

**Was es ist:** Das ursprüngliche Skript von p3605 auf GitLab, das vermutlich 2022 entstanden ist und alle anderen Skript-Forks initiiert hat. Heute eher als historische Referenz wichtig — alle aktiven Skripte sind Forks von Forks.

---

## 3. Begeisterungs-Features — was Bastler an OpenDTU + DIY lieben

### 3.1 Volle Datenkontrolle ohne Hersteller-Cloud

Die größte emotionale Energie kommt von Nutzern, die der Hoymiles-Cloud (DTU-Pro, S-Miles) nicht trauen — und es gibt verdammt gute Gründe dafür (siehe Pain Point #11 zur Bundesnetzagentur).

Aus borncity.com: *"Ich verwende ausschließlich Hoymiles WR des Typ2, also mit Sub 1GHz Funk und in Verbindung mit einer OpenSource DTU (OpenDTU)."* Der User will Hoymiles-Hardware, aber nicht Hoymiles-Software. OpenDTU ist die einzige Lösung.

**Lehre für Solarbot:** Das ist die gleiche emotionale Strömung, die wir auch bei Anker-Solix-Frust sehen. **Lokale Datensouveränität ist das wichtigste emotionale Verkaufsargument im DACH-Markt.** Solarbot muss diese Botschaft konsequent bedienen — und kann gleichzeitig auch OpenDTU als "lokalen Partner" anerkennen, ohne sich abzugrenzen.

### 3.2 Die "Ich habe es selbst gebaut"-Genugtuung

Aus dem panelretter.de-Blog: *"Mit der entsprechenden Software lässt sich so binnen 30 min ein voll funktionsfähiges Gateway mit Webinterface zaubern!"* Der Stolz auf die eigene Bastelei ist in jedem Forenbeitrag spürbar.

Aus dem blinkyparts.com-Shop (Bewertung des OpenDTU-Bausatzes): *"Hatte ja schon länger keinen Lötkolben mehr in der Hand, aber mit der sehr ausführlichen Beschreibung und dem perfekt zusammengestellten Bausatz war die Steuerung im Handumdrehen gelötet und zusammengebaut. Super auch, dass schon eine Firmware geflasht war und somit einfach ein OTA-Update auf die neueste Firmware gemacht werden konnte. Damit hat alles problemlos funktioniert, ich bin begeistert!"*

**Lehre für Solarbot:** Wir können diese Genugtuung **nicht** liefern und sollten es auch nicht versuchen. Bastler werden nie zu Solarbot-Kunden, weil ihnen genau dieses Erfolgserlebnis fehlt. Aber wir können einen analogen Moment schaffen: **das "Es funktioniert sofort"-Erfolgserlebnis** mit einer schönen Erst-Aktivierung, einer Live-Bestätigung "Solarbot regelt jetzt — schau, wie der Netzbezug auf null fällt" und einer Statistik nach 24 Stunden ("Solarbot hat heute X kWh Netzbezug verhindert"). Andere Emotion, gleicher Effekt.

### 3.3 Open Source als Kultur, nicht nur als Lizenz

Aus Discussion #311 (`tbnobody/OpenDTU`): *"Hallo zusammen, ich bin begeistert von dem Projekt. Super Arbeit!!!"*

Aus Discussion #704 (`hoylabs/OpenDTU-OnBattery`): *"Hi, bin jetzt auch erfolgreicher DTU on Battery Nutzer und total begeistert. Ich hatte knapp 3 Jahre ein ESmart3, womit ich eigentlich recht zufrieden war, bis ich auf dieses Projekt gestoßen bin."*

Aus Issue #551 (`tbnobody/OpenDTU`): *"Hi, besten Dank für das tolle Projekt. Ich benutze die openDTU sehr gerne und bin über das Web design und die Stabilität sehr begeistert."*

Die Open-Source-Kultur ist hier **identitätsstiftend**, nicht nur funktional. Nutzer fühlen sich Teil einer Bewegung, die "es den großen Herstellern zeigt".

**Lehre für Solarbot:** Solarbot ist closed-source, aber er kann **Open-Source-Werte** leben: öffentliche Roadmap, transparente Issues, ehrliche Kommunikation, Anerkennung der DIY-Vorgänger im eigenen Marketing. Eine Zeile wie *"Solarbot wäre ohne die Pionierarbeit von OpenDTU, OpenDTU-OnBattery und der Selbstbau-PV-Community niemals möglich gewesen — wir verneigen uns"* ist Gold wert. Das ist nicht nur höflich, das ist strategisch klug.

### 3.4 Dynamic Power Limiter in OpenDTU-OnBattery

Aus Discussion #2086: *"Was du konkret meinst, ist Dynamische Leistungsanpassung, je nach Verbrauch. Ja, dafür ist OpenDTU onBattery konzipiert. (...) Tasmota meldet Verbrauch 100W, aber dein Wechselrichter kann 800W liefern, regelt der Dynamische Power Limiter den WR so weit runter, dass er nur mit 20% arbeitet."*

Der DPL ist das Herzstück von OpenDTU-OnBattery und beweist, dass **eine echte Nulleinspeisung allein auf dem ESP32 möglich ist**. Das ist technisch beeindruckend.

Aus dem Wiki: *"Then you can expect your inverter to react in the range of 2 to 3 seconds."* — das ist eine Reaktionszeit, die Solarbot kennen und einordnen muss.

**Lehre für Solarbot:** Die 2–3 Sekunden Reaktionszeit von OpenDTU-OnBattery sind die **Latte, gegen die wir gemessen werden**. Solarbot muss das gleiche oder besser liefern — und gleichzeitig die EEPROM-Schonung dazu, die DPL nicht hat.

### 3.5 Hardware-Bausätze als Eintrittskarte

Anbieter wie blinkyparts.com, panelretter.de und selbstbau-pv.de verkaufen fertige Bausätze für 30–50 €. Das senkt die Hürde erheblich — der Nutzer muss nicht selbst Hardware aussuchen, sondern bekommt ein Komplettpaket.

**Lehre für Solarbot:** Das ist eine Vertriebs-Idee, die wir adaptieren können. Eine Partnerschaft mit einem deutschen Solar-Shop, der "Solarbot Starter Kit" (Shelly Pro 3EM + Lizenz + Anleitung) als Bundle verkauft, wäre ein massiver Distribution-Hebel für die Mainstream-Zielgruppe.

### 3.6 Die "Hardware ist ehrlich"-Mentalität

Aus borncity.com: *"OpenDTU, AhoyDTU verwendet werden, welche im Notfall auch einfach (weil nicht auf dem Dach montiert) Update- und Austauschbar sind."*

Der User schätzt OpenDTU, weil es **physisch kontrollierbar** ist — wenn die Hoymiles-Cloud ausfällt, ist die OpenDTU davon nicht betroffen. Wenn der ESP32 stirbt, kostet ein neuer 5 €. Das ist Resilienz durch Trivialität.

**Lehre für Solarbot:** Solarbot ist Software, kein physisches Stück Hardware. Aber wir können die gleiche Resilienz-Idee leben: **Solarbot funktioniert auch dann, wenn unsere Server alle abbrennen**, weil die Lizenz nach Aktivierung lokal validiert wird, weil keine Cloud-Pflicht besteht, und weil im Worst Case der Code einfach weiterläuft. Diese Resilienz muss in der Lizenz-Architektur verankert sein und in der Marketing-Botschaft sichtbar werden.

---

## 4. Frust-Punkte — was die DIY-Welt in den Wahnsinn treibt

### 4.1 Funkverbindung Hoymiles ↔ OpenDTU ist ein Glücksspiel

Das ist der mit Abstand häufigste Frust-Typ in den Foren. Die Funkverbindung zwischen ESP32+NRF24/CMT2300A und dem Hoymiles-Wechselrichter ist anfällig für unzählige Faktoren: Entfernung, Wände, Antennen-Typ, Antennen-Ausrichtung, Wetter, Nachbarn mit ähnlicher Hardware, Frequenz-Drift, Hardware-Defekte.

**Aus Discussion #1553 (OpenDTU-OnBattery):** *"Empfang erfolgreich ca. 87 % und bei Empfang Fehler: Teilweise empfangen ca. 13 %! Andere haben hingegen Werte von 100%! Somit wird dies der Grund sein, warum die 'letzte Aktualisierung' nicht immer in dem von mir vorgegebenen Takt (1 Sek oder 3 Sek oder x Sek) stattfindet. Ich habe bereits dieses Funkmodul gegen dieses Funkmodul ausgetauscht, da einige hier gemeint haben, mit diesem Funkmodul sei der Empfang besser. Der Empfang mag vielleicht besser sein, aber nur marginal. Jetzt habe ich versucht mittels eines längeren (ca. 150 cm anstatt 20 cm) 8-adrigen Kabels mehr Distanz zwischen dem Funkmodul und der Antenne des Mikrowechselrichters zu schaffen."*

Der User hat also: das Modul gewechselt, Antennen verlängert, Position experimentiert — und kommt trotzdem nur auf 87 %. Antwort eines anderen Users: *"Was bei mir eine Besserung gebracht hat, ist die NRF-Antenne aus dem Abstrahlwinkel der Wifi-Antenne zu bringen. Mit einer Abschirmung des NRF-Modules, sowie einer Abschirmung des ESP32-S3 könnte es noch besser werden, hab ich aber noch nicht probiert."* — also: nicht nur die Position, sondern auch elektromagnetische Abschirmung muss optimiert werden.

**Aus Discussion #2383 (OpenDTU-OnBattery):** *"Ich habe das Problem dass meine Inverter, aufgrund der Örtlichkeit, tlw recht schlecht mittels Funk erreichbar sind, was zu retransmit führt. Aus diesem Grund möchte ich den Funktransfer auf ein minimum reduzieren."* — der User schaltet OpenDTU manuell tagesabhängig ein und aus, um die Funk-Last zu reduzieren.

**Aus dem Akkudoktor-Forum (April 2026):** *"Ich habe ein vorkonfigurierte openDTU LAN gekauft, Netzwerkadresse ist fest eingegeben. Regelmäßig verliert die DTU die Netzwerkverbindung. Auf dem Display wird schön der Ertrag angezeigt und summiert, über LAN ist sie nicht mehr erreichbar. Um sie wieder ins Netzwerk zu bekommen muß man sie vom Strom trennen."*

**Aus dem Photovoltaikforum (Juli 2025):** *"Innerhalb kürzester Zeit musste ich jetzt schon zum zweiten mal die CMT2300A Frequenz um 0,25 MHz erhöhen, da die Verbindung zwischen WR und OpenDTU nicht mehr vorhanden war. Angefangen habe ich bei 865,00 MHz und nun stehe ich bei 865,50 MHz um eine Verbindung hinzubekommen."* — der User muss manuell die Funk-Frequenz nachjustieren, wie ein Funkamateur.

**Solarbot-Differenzierung:** Solarbot kommuniziert nie direkt über Funk mit dem Wechselrichter. Solarbot liest HA-Entitäten — und die HA-Integration kümmert sich um die Funk-Probleme (oder nicht). Wenn die Funk-Verbindung instabil ist, ist das ein **Hardware-/Integrations-Problem**, nicht ein Solarbot-Problem. Solarbot kann das im Diagnose-Tab transparent machen ("Letzte Aktualisierung der Wechselrichter-Entität vor 47 Sekunden — möglicherweise Funk-Problem"), aber Solarbot muss es nicht lösen. Das ist ein **massives Komplexitäts-Outsourcing**, das wir konsequent kommunizieren müssen.

### 4.2 EEPROM-Verschleiß — die unsichtbare Hardware-Zerstörung

Diesen Punkt haben wir bereits im PRD-Patch verankert, aber er gehört in dieser Analyse noch einmal in Original-Stimmen.

**Aus dem Photovoltaikforum (2026, "Growatt MIC & Marstek Venus E 3.0: 100% Software-Nulleinspeisung Via HA und Node-RED OHNE EEPROM-Verschleiß"):** *"Wenn man jetzt per Skript die Nulleinspeisung regelt und dafür sekündlich die Holding-Register für die Wirkleistungsgrenze überschreibt, triggert man ständige Schreibvorgänge auf genau diesen Speicher (da der WR diese Settings stromausfallsicher ablegen will). Bei 86.400 Sekunden am Tag ist das theoretische Limit der Schreibzyklen extrem schnell erreicht. Ob sich der EEPROM in der Praxis dann wirklich nach ein paar Monaten verabschiedet oder deutlich länger durchhält, steht natürlich auf einem anderen Stern. Ich wollte für mein Setup einfach nur das Risiko von vornherein minimieren."*

**Antwort von Alex auf alkly.de (existierender Blog):** *"Soweit ich verstanden habe soll man mit diesem Wechselrichter und Home Assistant aber keine Nulleinspeisung machen, da die Werte in den Dauerhaften-Speicher geschrieben werden und dies langfristig zu einem Schaden führen kann."*

Der User, der das Problem identifiziert hat, hat als Workaround einen "SDM-Emulator" gebaut — ein virtueller Stromzähler, der dem Wechselrichter über Modbus-ID 2 Zähler-Daten schickt, statt Wirkleistungs-Grenzen ins Holding-Register zu schreiben. Damit landen die Werte nur im RAM und nicht im EEPROM.

Das ist eine **brillante DIY-Lösung** — und sie zeigt, dass die Bastler-Welt Workarounds für ihre eigenen architektonischen Probleme bauen muss. Solarbots Architektur eliminiert dieses Problem strukturell.

**Solarbot-Differenzierung:** Wir haben das im PRD bereits geregelt (siehe Kapitel "Hardware-schonende Regelung" im PRD-Patch). Aber für die Außenkommunikation gegenüber DIY-Bastlern müssen wir es noch deutlicher machen: **"Solarbot übernimmt die EEPROM-Schonung für dich, ohne dass du einen SDM-Emulator bauen musst."** Das ist eine Aussage, die die DIY-Community nicht beleidigt, sondern anerkennt — und gleichzeitig zeigt, warum Mainstream-Nutzer Solarbot brauchen.

### 4.3 Multi-Wechselrichter-Setups sind ein Murks

**Aus dem Photovoltaikforum (Hoymiles HMS-1600-4T, 2024):** *"Soweit ich das mal gelesen habe liegt das daran, das 4 MPPT verbaut sind und OpenDTU damit nicht klar kommt wenn nicht alle Eingänge belegt sind. Nun zur eigentlichen Frage? Kann ich kurzfristig ein Modul per Y-Kabel auf 2 separate MPPT Eingänge schalten oder ist das eh nicht so gut?"*

**Aus Discussion #667 (OpenDTU-OnBattery, "Dynamic Power Limiter ohne Batterie - Nulleinspeisung zu viel ins Netz"):** *"die openDTU-onBattery hat im Hintergrund einen Skalierungsmechanismus. Woher der genau kommt, kann ich nicht sagen. Er ist scheinbar recht umstritten, ist aber so noch in der Software. die Hoymiles limitieren nicht einfach auf der AC Seite, sondern drosseln die MPPT gleichmäßig. Wenn du bspw. mit einem HM-800 nur 200W erzeugen willst, werden beide MPPT (und damit beide Eingänge) gleichmäßig auf 100W gedrosselt. hast du nun nur 1 Paneel angeschlossen, kämen, aufgrund der Hoymiles internen Logik, dennoch nur 100W heraus."*

Übersetzt: Wenn ein Nutzer einen 4-MPPT-Wechselrichter hat, aber nur 2 oder 3 Module anschließt, regelt OpenDTU-OnBattery falsch — und es musste ein "Skalierungsmechanismus" eingebaut werden, um das zu kompensieren. Der Maintainer schreibt selbst, dass dieser Mechanismus "umstritten" ist.

**Aus Discussion #1946 (`tbnobody/OpenDTU`):** *"Ja, die OpenDTU braucht ca. 2 Minuten um die MQTT-Steuerungsbefehle von der Nulleinspeisung des HA an den WR 2 zu senden."* — bei zwei Wechselrichtern hat ein User 2 Minuten Latenz.

**Solarbot-Differenzierung:** Multi-WR ist im MVP bewusst ausgeschlossen. Aber wenn Solarbot V1.x oder V2 Multi-WR unterstützt, dann **sauber, dokumentiert, mit eigener Verteilungs-Logik pro WR-Modell**. Wir können aus dem OpenDTU-OnBattery-"umstrittenen Skalierungsmechanismus" lernen und gleich sauber bauen.

### 4.4 OpenDTU-OnBattery hat Bugs, die monatelang die Regelung killen

**Aus dem README von OpenDTU-OnBattery (April 2026):** *"Version 2.0.4: Inverter reports 100% power limit after 4 minutes without limit updates, causing the DPL to stop working (#1901). Recommendation: Avoid version 2.0.4 completely."*

Der Maintainer warnt selbst öffentlich davor, eine bestimmte Hoymiles-Firmware-Version zu nutzen — weil sie OpenDTU-OnBattery faktisch unbrauchbar macht. Der User-Workaround ist, dem Hoymiles-Support eine E-Mail zu schreiben und um ein Firmware-Downgrade zu bitten.

**Aus dem Photovoltaikforum (Juli 2025):** *"Du könntest aber den Hoymiles Service um ein downgrade bitten. Klappt wohl in der Regel."*

Das ist ein erstaunlicher Workflow: Nutzer müssen Hoymiles per E-Mail bitten, ihre Firmware downzugraden, damit OpenDTU-OnBattery wieder funktioniert.

**Solarbot-Differenzierung:** Solarbot ist nie auf eine bestimmte Wechselrichter-Firmware-Version angewiesen, weil Solarbot keine direkte Hardware-Kommunikation hat. Wenn die HA-Integration mit einer Firmware-Version ein Problem hat, ist das **das Problem der HA-Integration**, nicht von Solarbot. Diese Trennung ist ein massives Stabilitäts-Argument.

### 4.5 Die "MQTT cmd vs status"-Falle

Diese Pain ist exemplarisch für die DIY-Komplexität. Mehrere Discussions zeigen das gleiche Muster:

**Aus Discussion #874 (`tbnobody/OpenDTU`):** *"Nun finde ich keinen Weg, dieses Limit wieder zu ändern. Weder in der Web GUI kann ich das ändern noch ist der Datenpunkt via MQTT erreichbar. Ich habe die Diskussion zur MQTT-Struktur gesehen. Es fehlt bei mir der Bereich cmd."* Antwort: *"Ich war zu blind, die Einstellung via openDTU habe ich nun gefunden."*

**Aus Discussion #1158 (`tbnobody/OpenDTU`):** *"Ich möchte mit einem Script in HA den Wert 'Limit non persistence absolut' verändern, aber egal wie ich den Wert verändere, der auch im MQTT-Explorer an der richtigen Stelle ankommt, es kommt keine Änderung am Wechselrichter an."*

**Aus Discussion #1636 (OpenDTU-OnBattery):** *"Aber das Hauptproblem ist, dass wenn ich den Wert über MQTT ändere, er innerhalb weniger Sekunden wieder auf den vorherigen Wert zurückgestellt wird."* Lösung: *"Habe das Problem selber finden können. Man kann den Wechselrichter nicht über das Topic 'status' regeln. Das ist scheinbar 'read-only'. (...) Bei mir war der Kanal 'cmd' im Topic der Wechselrichter nicht vorhanden bzw. angelegt."*

Die Falle: Die OpenDTU veröffentlicht Werte unter `status/...` (read-only) und akzeptiert Befehle unter `cmd/...` (write). Wenn ein Nutzer (verständlicherweise) versucht, den `status`-Wert zu ändern, denkt er, es funktioniert — der MQTT-Explorer zeigt den neuen Wert — aber der Wechselrichter bekommt nichts. Das ist ein klassisches "Pit of failure"-Design.

**Solarbot-Differenzierung:** Solarbot lässt den Nutzer nie in solche Fallen tappen. Auto-Discovery der HA-Entitäten, sinnvolle Defaults, schreib-fähige Entitäten werden **automatisch** ausgewählt, nicht-schreibfähige werden **explizit ausgeschlossen** mit einer klaren Fehlermeldung. Diese Unterscheidung machen wir transparent und nehmen sie dem Nutzer ab.

### 4.6 Selbstbau-PV-Skripte: kein Support, kein Update-Pfad

Diese Stimme ist besonders aufschlussreich, weil sie zeigt, was passiert, wenn ein DIY-Bastler an seine Grenzen stößt.

**Aus dem Shelly-Forum (April 2024):** *"Naja, eine OpenDTU habe ich zusammengelötet, aber ein Programmierer bin ich überhaupt nicht; mqtt, influxdb etc. waren bis vor ein paar Tagen noch Fremdworte für mich. Wie ich die Daten aus den HM800 über mosquitto in eine influxdb bekomme, habe ich im Netz gefunden, und das funktioniert auch, aber bei den Shellys komme ich nicht voran. Die entsprechenden Shelly-Seiten verwirren mich mehr, als sie nutzen, sie setzen ein Grundwissen voraus, das ich nicht habe."*

Der User hat dann das selbstbau-pv.de-Skript gefunden — aber: *"Das Skript wurde für einen Shelly 3EM geschrieben und funktioniert damit wohl auch, Francesco hat aber die neueren Pro 3EM eingebaut, und damit bekomme ich nur: 'Fehler beim Abrufen der Daten von Shelly 3EM'. Für die neueren Pro 3EM muss man diese Zeilen wohl ein bisschen anpassen, aber ich habe keinen Schimmer, wie."*

Und dann der **Killer-Punkt**: *"Natürlich habe ich mich erstmal mit meiner Frage an selbstbau-pv.de gewandt, sie bieten ja Hilfe an, leider habe ich als Antwort nur bekommen: 'wir leisten keinen Support für das Python Script. Ich kann dir da leider nicht weiterhelfen.'"*

Der Anbieter, der das Skript verbreitet, hilft bei Problemen nicht. Der Nutzer sitzt allein vor einem nicht-funktionierenden Setup.

**Aus Issue #16 (Selbstbau-PV-Repo):** *"Hello, it would be very helpful for me, if somebody could modify this python script for a shelly 3EM pro, which has a different API than shelly 3EM."* — der gleiche Nutzer hat einen Fork-Wunsch geöffnet, der dann ein anderer User (svnhpl) als eigenes Repo gelöst hat.

**Aus Issue #24 (Selbstbau-PV-Repo, Februar 2024):** *"Hello, after upgrading to the new OpenDTU Firmware the python script is not working any more. No Data from opendtu."*

Das Repo hat über 30 offene Issues. Maintainer-Aktivität ist sporadisch.

**Solarbot-Differenzierung:** Solarbot ist **unterstützt**. Es gibt einen Lizenz-Holder, der für Bugfixes verantwortlich ist. Es gibt einen Discord, in dem geantwortet wird. Es gibt regelmäßige Updates über den HA Add-on Store. Das ist der fundamentale Unterschied zwischen einem **Produkt** und einem **DIY-Projekt** — und es ist genau das, wofür Mainstream-Nutzer bezahlen.

Marketing-Botschaft: **"Solarbot ist nicht kostenlos. Aber wenn du ein Problem hast, antworten wir."**

### 4.7 Acht Komponenten für ein Setup, das funktionieren soll

Ein typisches DIY-Setup besteht aus:
1. **Hoymiles Wechselrichter** (Hardware, oft 100–300 €)
2. **OpenDTU oder OpenDTU-OnBattery** (ESP32 + Funk-Modul, Bausatz 30–50 €)
3. **Smart Meter** (Shelly 3EM, Shelly Pro 3EM, IR-Lesekopf, Tasmota, oder ähnliches)
4. **Raspberry Pi** (für Python-Skripte oder Home Assistant)
5. **Python-Skript** (Selbstbau-PV-Fork oder Eigenbau)
6. **MQTT-Broker** (Mosquitto, oft als HA-Add-on)
7. **InfluxDB + Grafana** (für die Visualisierung)
8. **systemd / Cron / Docker** (damit das Skript überhaupt läuft)

Wenn der Nutzer einen Akku hat, kommen noch dazu: Akku-Hardware mit BMS, Akku-spezifische OpenDTU-OnBattery-Konfiguration (priority, voltage thresholds, SoC-Quelle), Schalt-Logik für Bypass-Modus.

**Aus Discussion #294 (Akkudoktor-EOS, der mit OpenDTU vergleichbar ist):** Bereits 8 bewegliche Teile, jedes davon eine potenzielle Fehlerquelle.

**Solarbot-Differenzierung:** Solarbot ist 1 Add-on. Über dem HA, das sowieso schon läuft. Keine zusätzlichen Container, keine Python-Versionen, keine MQTT-Topics, kein Cron. Marketing-Botschaft: **"Bei OpenDTU baust du. Bei Solarbot startest du."**

### 4.8 Die "Es lief, dann kam ein Update, dann lief es nicht mehr"-Falle

**Aus Issue #24 (Selbstbau-PV-Repo):** *"Hello after upgrading to the new OpenDTU Firmware the python script is not working any more."*

**Aus dem Photovoltaikforum:** *"Habe die Anlage Mitte Mai mit der 1.0.27 in Betrieb genommen. Hatte diese Probleme nicht. Habe mit der 1.0.27 zwei komplette Aufhänger des WR gehabt, wo ich dann Nachts die Anlage komplett stromlos machen musste. Danach lief sie wieder. Aus diesem Grund hab ich mir die 2.0.04 aufspielen lassen (und wegen der dynamischen Kanalregelung). Auch das eingestellte Limit hat er behalten...und nicht nach ein paar Minuten wieder zurückgestellt."*

Updates lösen ein Problem und schaffen das nächste. Es gibt keine "stable"-Linie — Nutzer testen und hoffen.

**Solarbot-Differenzierung:** Solarbot hat einen klaren Update-Pfad über den HA Add-on Store, mit automatischen Backups vor dem Update und Rollback-Möglichkeit. Das ist im PRD bereits angedacht und sollte hier nochmal als prominentes Differenzierungs-Merkmal markiert werden.

### 4.9 Hardware kann zerstört werden — und wird zerstört

**Aus dem ioBroker-Forum:** *"Leider scheint das der WR des HM-600 nicht so lustig zu finden und stürzt ab. Ich denke mal das es WR ist der abstürzt da ich über die openDTU den WR neu starten kann und es geht weiter (bis zum nächsten Absturz)."*

Der Wechselrichter hängt sich auf und muss regelmäßig neu gestartet werden. Workaround: WLAN-Steckdose, die einmal am Tag vor Sonnenaufgang den WR neu startet.

**Aus dem Akkudoktor-Forum:** *"Die Hardware des OpenDTU hängt bei mir an einer W-Lan Steckdose und wird einmal am Tag vor Sonnenaufgang neu gestartet. Läuft bisher ziemlich rund. Auf Holz klopf."*

Die Bastler haben gelernt, dass ihre Setups nur mit prophylaktischen Reboots stabil laufen. Das ist akzeptiert — aber für Mainstream-User wäre das ein Albtraum.

**Solarbot-Differenzierung:** Solarbot regelt mit EEPROM-Schonung (siehe PRD-Patch) und hektiert nie. Das ist ein implizites Versprechen, dass Solarbot Hardware nicht beschädigt — und es ist messbar (siehe Akzeptanzkriterium <500 Schreibvorgänge/Tag).

### 4.10 Programmier-Wissen wird vorausgesetzt — und fehlt oft

Aus dem oben zitierten Shelly-Forum: *"Naja, eine OpenDTU habe ich zusammengelötet, aber ein Programmierer bin ich überhaupt nicht."*

Aus Discussion #311: *"Die Anleitung habe ich soweit verstanden, aber ich verstehe einen Punkt nicht 'Building the WebApp' was soll man da erstellen und wo und wozu?"* — der User versteht nicht, dass er den Frontend-Code selbst kompilieren muss, weil das in der DIY-Welt selbstverständlich ist.

Aus Issue #817 (`tbnobody/OpenDTU`, neuer User): *"What happened? I was on AHOY with an NRF24L01+ board. (...) But whatever I try the board does not seem to connect. (...) Tried to find some helpful discussions here, but seems this issue is not discussed at all."*

Die Lernkurve ist nicht steil — sie ist eine Klippe. Neue Nutzer scheitern oft schon am ersten Schritt.

**Solarbot-Differenzierung:** Solarbot setzt **null Programmier-Wissen** voraus. Keine Kompilierung, keine ESP-Flash-Tools, keine NRF24-Pinouts, keine MQTT-Topic-Namen. Das ist im PRD bereits zentral verankert.

### 4.11 Der regulatorische Schock — die Bundesnetzagentur und die Hoymiles-Funkstörung

Das ist die brisanteste Geschichte der gesamten Analyse, weil sie den **strategischen Risiko-Horizont** der DIY-Welt zeigt.

**Aus borncity.com (30. Juli 2025):** *"In vielen Balkonkraftwerken werden (neben Deye) Wechselrichter des Anbieters Hoymiles verwendet. Die Wechselrichter verwenden eine Kommunikationskomponente (DTU), die massive Funkstörungen im 868 MHz Band verursachen. (...) Marvin schrieb dazu: 'Ich habe hier einen interessanten Beitrag auf reddit bezüglich der dtu w lite s von hoymiles gesehen, und habe das an meiner dtu auch feststellen können'. Das Thema ist uralt, der CCC hat vor sechs Jahren einen Vortrag zum Thema gehalten."*

Die Bundesnetzagentur hat im Sommer 2025 begonnen, Funkstörungen durch Hoymiles-Wechselrichter im 868-MHz-Band zu untersuchen — und das hat direkte Implikationen für OpenDTU/CMT2300A-Setups, die im selben Frequenzbereich arbeiten.

**Aus dem HomeMatic-Forum (Juli 2025):** *"Ich habe einen HM-800 mit OpenDTU über ein NRF24 Funkmodul - also 2.4GHz - angebunden. (...) Ohne Anfrage der DTU funkt der WR nix. Das sind gleich 2 Randbedingungen, die die Störung verhindern. Zum einen die alten WRs, die noch nicht auf 868 MHz kommunizieren, zum anderen die Selbstbau-DTUs, die ihre Arbeit wohl korrekt machen."*

Die Aussage relativiert die Schuld auf die offiziellen Hoymiles-DTUs (DTU-Pro, DTU W-Lite S) und entlastet OpenDTU teilweise. Aber der Imageschaden für die gesamte Hoymiles-DIY-Welt ist real.

**Implikationen für die DIY-Welt:**
- Es ist nicht ausgeschlossen, dass die Bundesnetzagentur in den kommenden Monaten oder Jahren weitere Eingriffe vornimmt
- HMS/HMT-Wechselrichter im 868-MHz-Band stehen unter besonderer Beobachtung
- Im Worst Case könnten Hoymiles-Geräte regulatorisch eingeschränkt oder zurückgerufen werden
- Selbst wenn das nicht passiert: Das Vertrauen in die Hardware ist beschädigt

**Solarbot-Differenzierung:** Solarbot ist **regulatorisch unauffällig** — wir senden nichts, wir hören keine Funkfrequenzen ab, wir bauen keine Hardware. Falls die DIY-Welt durch Bundesnetzagentur-Eingriffe Schaden nimmt, ist Solarbot das natürliche "Refugium": **lokale Kontrolle, ohne die regulatorische Last der Funk-Hardware.**

Diese Erkenntnis sollte in der Marketing-Botschaft nicht offensiv ausgespielt werden (das wäre respektlos gegenüber der DIY-Community), aber sie sollte als **stilles Vertrauenssignal** im Hintergrund stehen.

---

## 5. Strukturelle Schwächen des DIY-Modells

**S1: Wartungsschuld wächst mit jedem Setup.** Jeder Bastler hat sein eigenes Setup, jedes Setup braucht eigene Pflege. Das skaliert nicht.

**S2: Maintainer-Bus-Faktor.** Wenn tbnobody, hoylabs oder p3605 morgen aufhören würden, würde die DIY-Welt langsam auseinanderfallen. Es gibt keine institutionellen Garantien.

**S3: Hardware-Frequenz-Risiken.** Sub-1-GHz-Funk (CMT2300A) ist Gegenstand regulatorischer Untersuchungen. Das kann jederzeit eskalieren.

**S4: Hoymiles als alleiniger Ankerpunkt.** Die gesamte DIY-Welt baut auf einer einzigen Marke auf. Wenn Hoymiles strategische Änderungen vornimmt (Verschlüsselung, neue Firmware-Versionen, EOL bestimmter Modelle), fällt alles wie ein Kartenhaus zusammen.

**S5: Skript-Kompatibilität ist fragil.** Jede neue OpenDTU-Firmware-Version, jede neue Shelly-API-Version, jede neue Hoymiles-Firmware-Version kann ein DIY-Skript brechen. Es gibt kein zentrales Test-System, keine CI/CD, keine Garantien.

**S6: Programmier-Wissen wird vorausgesetzt.** Der Pool potenzieller DIY-Nutzer ist limitiert. Mainstream-Wachstum ist strukturell ausgeschlossen.

**S7: Kein kommerzieller Support.** Im Fall der Fälle ist der Nutzer auf Forum-Goodwill angewiesen. Keine SLAs, keine Verantwortlichkeit.

---

## 6. Solarbot-Differenzierung — wo wir konkret anders sind

| Dimension | OpenDTU + DIY | Solarbot |
|---|---|---|
| Hardware-Anbindung | Direkt über Funk (NRF24/CMT2300A) | Über HA-Entitäten |
| Setup-Aufwand | Tage bis Wochen, Löt-Wissen + Programmier-Wissen nötig | 10 Minuten, geführter Flow |
| Komponenten | 8+ bewegliche Teile | 1 Add-on |
| Funk-Risiko | Bundesnetzagentur-Untersuchung läuft | Kein Funk, kein Risiko |
| Hardware-Lock-in | Nur Hoymiles (+ TSUN/Solenso) | Jeder Wechselrichter mit HA-Integration |
| EEPROM-Schutz | Manuell oder gar nicht | Architektur-immanent |
| Update-Pfad | Manuell, oft brechen Updates Setups | HA Add-on Store, automatisch + Rollback |
| Multi-WR-Support | "Umstrittener Skalierungsmechanismus" | V1.x mit sauberer Multi-Profile-Logik |
| Support | Community-Goodwill | Lizenz-basiert, professionell |
| Zielgruppe | Bastler mit Lötkolben + Python | Mainstream-Balkonkraftwerk-Nutzer |
| Doku-Qualität | Verstreut, oft veraltet | Strukturiert, single source of truth |
| Update-Sicherheit | "Hoffen, dass es nach dem Update noch läuft" | Atomic Update mit Rollback |

---

## 7. Co-Existenz-Strategie: Respekt und Anerkennung statt Frontalangriff

Die DIY-Community ist **nicht** die Zielgruppe. Aber sie ist eine extrem wichtige **Multiplikator-Gruppe**. Jeder Bastler ist gleichzeitig der "PV-Experte" in seiner Familie und seinem Freundeskreis — und wenn er Solarbot empfiehlt, weil er weiß "das ist die richtige Lösung für meine Schwester, die nicht so viel basteln will", ist das mehr wert als jede bezahlte Anzeige.

**Strategische Empfehlung:**

**1. Anerkennung in der eigenen Doku.** Ein Abschnitt in der Solarbot-Doku oder auf alkly.de mit dem Titel **"Wir verneigen uns vor den Pionieren"**, in dem OpenDTU, OpenDTU-OnBattery, hoymiles-tarnkappe und die Selbstbau-PV-Initiative explizit gewürdigt werden. Eine Zeile wie *"Solarbot wäre ohne die Pionierarbeit dieser Projekte niemals möglich gewesen. Wir haben aus euren Schmerzen gelernt, und wir hoffen, das was wir bauen, macht den Weg für die nächste Million Nutzer einfacher."* ist Gold wert.

**2. Klare Positions-Trennung.** Wir sagen nicht *"Solarbot ist besser als OpenDTU"*. Wir sagen *"Solarbot ist für Leute, die nicht löten und nicht programmieren wollen — also für 95 % der Balkonkraftwerk-Käufer."* Das beleidigt niemanden in der DIY-Welt, weil es nicht ihre Identität in Frage stellt.

**3. Aktive Wertschätzung in den Foren.** Wenn Alex selbst (oder das Solarbot-Team) im OpenDTU-Discord, im Akkudoktor-Forum, im Photovoltaikforum auftaucht, dann mit einer dienenden Haltung: Fragen beantworten, Workarounds teilen, Wissen geben. Solarbot wird nicht "verkauft", sondern **organisch erwähnt**, wenn es passt: *"Hey, wenn du nicht selbst basteln willst, schau mal Solarbot an — das ist die Mainstream-Antwort auf den Ansatz, den ihr hier macht."*

**4. Eine Brücke für "müde" Bastler.** Es gibt eine wachsende Gruppe von Nutzern, die mal angefangen haben zu basteln — und nach 2 Jahren Setup-Pflege die Lust verlieren. Diese Gruppe ist die wertvollste Zielgruppe für Solarbot überhaupt. Eine Migration-Anleitung "Von OpenDTU + Selbstbau-PV-Skript zu Solarbot in 30 Minuten" sollte ein V1-Doku-Asset sein.

**5. Tooling-Brücke (V2-Idee).** Solarbot könnte langfristig die Daten von OpenDTU-OnBattery's Dynamic Power Limiter direkt einlesen und ergänzen — z. B. die Hardware-Funk-Statistiken im Diagnose-Tab anzeigen. Das wäre eine echte technische Anerkennung der DIY-Vorgänger.

---

## 8. Was Solarbot von OpenDTU + DIY lernen muss

**1. EEPROM-Schonung als Default, nicht als Option.** Die DIY-Welt hat das Problem identifiziert und Workarounds gebaut. Solarbot muss diese Workarounds als **eingebaute Defaults** liefern. Der PRD-Patch ist die richtige Antwort.

**2. Hysterese, Mittelwerte, Glättung.** Die DIY-Foren sind voll von "lieber 3-5 Minuten Mittelwert statt Echtzeit"-Empfehlungen. Solarbot muss das von Tag eins richtig machen.

**3. Dynamic Power Limiter als Konzept.** OpenDTU-OnBattery hat den DPL erfunden. Solarbot muss eine analoge Engine haben, nur eine Schicht höher: **Dynamic Entity Limiter**, der HA-Entitäten regelt statt direkter Hardware.

**4. Hardware-Wissen pro WR-Modell.** OpenDTU-OnBattery hat den "umstrittenen Skalierungsmechanismus" für 4-MPPT-WR mit teilweise belegten Eingängen. Solarbot muss ähnliches Wissen pro WR-Modell hinterlegen — und im Profile-Marketplace (V1.x) crowdsourcen.

**5. Snap-to-Step-Werte.** Die DIY-Skripte runden oft auf 10-W-Schritte, weil das die Wechselrichter-Reaktion stabilisiert. Im PRD-Patch ist das bereits als X.2.5 verankert.

**6. Diagnose-Statistik mit echten Werten.** OpenDTU zeigt eine Funkstatistik (Empfang erfolgreich %, Empfang Fehler %). Solarbot muss eine analoge Statistik zeigen: "Schreibvorgänge heute: 142, davon erfolgreich: 142". Das ist Vertrauen durch Zahlen.

**7. Nachts NRF inaktiv schalten.** Aus Issue #551: *"Allerdings fehlt mir eine Möglichkeit die Kommunikation vom NRF zum Inverter anzuhalten, da ich das sinnlose polling über 10-12h einfach unnötig finde."* Solarbot kann das Analog: **Nachts schreibt Solarbot nichts**, weil es nichts zu regeln gibt. Das ist Energieersparnis und Hardware-Schonung gleichzeitig.

---

## 9. Was Solarbot konkret besser machen muss als die DIY-Welt — die fünf Prioritäten

**Priorität 1: Null Bastelei.**
Kein Lötkolben, kein ESP32, kein NRF24, keine Funk-Antennen, keine Frequenz-Justierung, keine MQTT-Topics, keine `cmd/status`-Verwirrung. Die direkte Antwort auf 10+ Forenstimmen.

**Priorität 2: Architektur statt Workaround.**
EEPROM-Schonung, Hysterese, Glättung, Snap-to-Step — alles als **strukturelle Defaults**, nicht als optionale Patches, die der Nutzer selbst aktivieren muss. Der PRD-Patch ist die Grundlage.

**Priorität 3: Profi-Support statt Forum-Lottery.**
Wenn ein Nutzer ein Problem hat, gibt es eine Antwort. Nicht "wir leisten keinen Support für das Skript", sondern aktives Discord, dokumentierte Fehler-Codes, Eskalations-Pfad. Die direkte Antwort auf den Selbstbau-PV-Support-Frust.

**Priorität 4: Hardware-Agnostik.**
Solarbot funktioniert mit jedem Wechselrichter, der eine HA-Integration hat — nicht nur Hoymiles. Damit ist Solarbot resilient gegen Hoymiles-spezifische Risiken (Bundesnetzagentur, Firmware-Probleme, Hardware-EOL).

**Priorität 5: Update-Sicherheit.**
Updates über den HA Add-on Store, mit automatischen Backups und Rollback. Die direkte Antwort auf "Update kam, Setup ist kaputt"-Geschichten.

---

## 10. Botschaften, die direkt verwendbar sind

Drei fertige Sätze für Landing Page, Pitch und Outreach:

> **"Bei OpenDTU baust du. Bei Solarbot startest du."**

> **"Wir verneigen uns vor den DIY-Pionieren — und übersetzen ihre Erkenntnisse für die nächste Million Nutzer."**

> **"Wenn du nicht löten und nicht programmieren willst, aber trotzdem die volle Kontrolle über deinen Solarstrom haben willst — Solarbot ist die Antwort."**

Und eine vierte, etwas mutigere Botschaft, die nur dann benutzt werden sollte, wenn die Funkstörungs-Geschichte weiter eskaliert:

> **"Solarbot funkt nicht. Solarbot stört nicht. Solarbot regelt einfach — über die HA-Entitäten, die du sowieso schon hast."**

---

## 11. Risiken und blinde Flecken

**Risiko 1: Die DIY-Community sieht Solarbot als Trittbrettfahrer.** Sehr real. **Mitigation:** Anerkennung der Pioniere in der eigenen Doku, dienende Haltung in den Foren, niemals abwertende Sprache.

**Risiko 2: Hoymiles oder die Bundesnetzagentur greift hart durch.** Wenn die HMS/HMT-Serie zurückgerufen oder eingeschränkt wird, ist die DIY-Welt im Chaos. Solarbot muss **darauf vorbereitet sein**, sowohl technisch (Multi-Hersteller-Support) als auch kommunikativ (kein Schadenfreude-Marketing).

**Risiko 3: OpenDTU-OnBattery wird so gut, dass auch Mainstream-Nutzer es schaffen.** Möglich, aber unwahrscheinlich, weil die Funk-Brücke und die Hardware-Bastelei strukturelle Hürden bleiben.

**Risiko 4: Solarbot wirkt im Vergleich zur DIY-Welt teuer.** Bastler werden sagen "Aber OpenDTU + Skript ist kostenlos!" Das ist ein Argument, das wir aufnehmen müssen — mit der Antwort "Kostenlos im Geld, teuer in der Zeit". Eine Zeile wie *"Solarbot kostet [X] € einmalig. Die durchschnittliche DIY-Lösung kostet 0 € — aber 30 Stunden deiner Zeit. Was ist deine Stunde wert?"* könnte direkt auf die Landing Page.

**Risiko 5: Wir unterschätzen die Bedeutung der DIY-Community als Multiplikator.** Wenn Alex sich zu offensiv positioniert und die Bastler beleidigt, verlieren wir den wichtigsten organischen Marketing-Kanal. Diese Gruppe muss respektiert werden, immer.

---

## 12. Konkrete nächste Schritte

**Sofort (vor Spike-Phase):**
- Eine kurze Notiz im PRD ergänzen, dass die DIY-Community als **Multiplikator-Gruppe**, nicht als Konkurrenz behandelt wird.
- Den Abschnitt "Wir verneigen uns vor den Pionieren" als Doku-Asset planen — nicht erst zum Launch, sondern schon für die Pre-Launch-Kommunikation.

**Vor Beta:**
- Migration-Anleitung schreiben: *"Von OpenDTU + Python-Skript zu Solarbot in 30 Minuten"*. Das ist ein konkretes Asset, das in den DIY-Foren organisch geteilt wird.
- 2–3 prominente DIY-Bastler als Beta-Tester gewinnen, die parallel ihr OpenDTU-Setup behalten und Solarbot vergleichen können. Ihre Erfahrungs-Berichte sind unbezahlbar.

**Beta-Phase:**
- Aktive, freundliche Präsenz im OpenDTU-Discord, OpenDTU-OnBattery-Discussions, Akkudoktor-Forum (Sektion DIY), Photovoltaikforum (Sektion Balkonkraftwerk). Keine Werbung — nur Hilfe und Wissen.
- Eine Live-Demo von Alex auf YouTube: "Solarbot vs. mein OpenDTU-OnBattery-Setup im direkten Vergleich". Ehrlich, mit allen Vor- und Nachteilen.

**Post-Launch:**
- Einen "Profi-Tier" für DIY-Nutzer einführen, die Solarbot zusätzlich zu ihrem OpenDTU-Setup nutzen wollen — z. B. mit erweiterten Diagnose-Features, API-Zugriff, oder Multi-WR-Support. Damit fängt Solarbot auch die "müden Bastler" ein, die ihre Grundinfrastruktur behalten wollen.

---

## 13. Die wichtigste Erkenntnis dieser Analyse

Die DIY-Welt ist **nicht** Solarbots Konkurrenz. Sie ist Solarbots Vorgeschichte, Solarbots Lehrer und Solarbots wichtigster Multiplikator. Wenn wir das richtig spielen, machen die Bastler mehr Marketing für uns als jede bezahlte Kampagne — weil sie genau wissen, wie schwer das alles ist, und sie erkennen, wenn jemand eine ehrliche Lösung baut.

Die strategische Position ist klar: **Solarbot ist die DIY-Erfahrung, in Software gegossen, für die nächste Million Nutzer.** Wir verkaufen nicht die Magie — wir verkaufen die Komplexitäts-Ersparnis. Wir zerstören keine Bastelfreude — wir machen Solar-Optimierung für Menschen zugänglich, die nie basteln werden.

Wenn das gelingt, ist Solarbot nicht nur ein Produkt — Solarbot ist die Brücke zwischen zwei Welten: der frühen, idealistischen, technisch tiefen DIY-Welt und der kommenden, breiten Mainstream-Bewegung der Energiewende. Diese Brücke zu bauen, ist eine Mission, die größer ist als jeder einzelne Verkaufs-Call. Und sie ist es, die Solarbot von einem Produkt zu einem Bewegungs-Treiber macht.

---

## 14. Anhang: Übersicht der zitierten Quellen

**GitHub-Repositories:**
- `tbnobody/OpenDTU` (~2.100 Sterne)
- `hoylabs/OpenDTU-OnBattery` (~472 Sterne)
- `Selbstbau-PV/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EM`
- `svnhpl/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EMpro`
- `mcleinn/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-CerboGX`
- `zfrank2601/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Emlog`
- `roastedelectrons/HoymilesOpenDTU` (IP-Symcon-Modul)
- GitLab `p3605/hoymiles-tarnkappe` (das Ur-Skript)

**Forenbeiträge:** Photovoltaikforum (mehrere Threads), Akkudoktor-Forum (mehrere Threads), ioBroker-Forum, HomeMatic-Forum, Shelly-Forum, simon42-Community

**Blogs und Shops:** borncity.com (Bundesnetzagentur-Geschichte, 30. Juli 2025), panelretter.de, blinkyparts.com, selbstbau-pv.de, alkly.de (Alex' eigener Blog)

**GitHub-Discussions zitiert:** #311, #551, #874, #1158, #1599, #1636, #1553, #1702, #1946, #2086, #2383, #2501, #704, #221, #311, #667, #1617, plus Issues #16, #24, #817, sowie das OpenDTU-OnBattery-Wiki "Dynamic Power Limiter"

Alle Zitate sind im Original-Wortlaut wiedergegeben, um das authentische Stimmungsbild der DIY-Community zu erhalten.
