# Supplement zum EVCC-Profil: Der Optimizer (evopt)
**Ergänzung zu Wettbewerber_01_EVCC.md · Stand: April 2026**

Quellen: `evcc-io/optimizer` GitHub-Repo, `docs.evcc.io/en/docs/features/optimizer`, EVCC-Blog Januar 2026, Discussions #23042, #23045, #23153, #23163, #23173, #23213, #23812, Release Notes April 2026

---

## 1. Warum dieses Supplement

Als die EVCC-Analyse (Wettbewerber_01_EVCC.md) geschrieben wurde, war der Optimizer bereits bekannt, aber nicht in der Tiefe untersucht. Alex hat nun gezielt nach dem aktuellen Stand gefragt — weil EVCC damit **in Solalexs Kern-Territorium vorstößt**: Hausbatterie-Optimierung.

Die Frage, die dieses Supplement beantwortet: **Wie ernst müssen wir den EVCC Optimizer als Bedrohung für Solalex nehmen?**

Die kurze Antwort: **Ernst, aber die Bedrohung ist in den nächsten 12–18 Monaten noch nicht real — und die Architektur-Entscheidungen des Optimizers spielen Solalex sogar in die Hände.**

Die lange Antwort im Folgenden.

---

## 2. Was der EVCC Optimizer ist

Der Optimizer (offizieller Name: **evopt**) ist ein **separater Python-Dienst**, der mit EVCC kommuniziert und auf Basis von Gleichungssystemen und Statistik Kosten-optimale Energieflüsse berechnet.

**Eigene Selbstbeschreibung aus dem EVCC-Blog (1. Januar 2026):** *"Heute regeln wir einzelne Komponenten oft individuell. Der Optimizer hat das Ziel, das Gesamtsystem zu optimieren: Paralleles Laden mehrerer Fahrzeuge, Hausbatterien und Verbraucher – basierend auf Preissignalen, PV-Vorhersagen und Hausverbrauchsprognosen. Seit Mitte 2025 arbeitet eine Gruppe von Leuten an einem Optimierungsalgorithmus für evcc. Er basiert auf Gleichungssystemen und Statistik. Produktmarketing würde das vmtl. AI nennen."*

**Aus der offiziellen Dokumentation (`docs.evcc.io/en/docs/features/optimizer`):** *"evcc works rule-based and deterministically. This works great for many setups. E.g. a solar system, battery, and one vehicle. More complex scenarios push this approach to its limits: Multiple vehicles: Which one should be charged first? Battery or vehicle: Where should the available energy go? Dynamic tariffs: Is it worth charging from the grid tonight, or will there be enough solar energy tomorrow? The optimizer can answer these questions."*

**Technisch:**
- Eigenes GitHub-Repo: `evcc-io/optimizer`
- Python-basiert, setzt `uv` und `make` voraus
- Läuft als separater Dienst (Docker-Container, HA-Add-on oder systemd-Service)
- Kommuniziert mit EVCC über `EVOPT_URI` Environment-Variable
- Wird über einen Cloud-Dienst (`optimizer.evcc.io`) angesprochen — oder lokal

---

## 3. Die fünf entscheidenden Fakten

### 3.1 Der Optimizer ist "purely information-only" — er regelt NICHTS

Das ist der mit Abstand wichtigste Fakt. Aus Issue #23042 (offizielles Epic für Optimizer-Verbesserungen) wörtlich:

*"NOTE: at this time, the optimizer is purely information-only ('what would happen if we actually used this'). It is not used to make actual decisions."*

Und aus der offiziellen Dokumentation: *"The optimizer is currently informational only. It shows forecasts and potential savings but does not yet actively control anything."*

Und aus der deutschen Version: *"Der Optimizer ist in einem frühen Entwicklungsstadium. Die angezeigten Daten sind derzeit informativ. Steuerungsaktionen folgen in zukünftigen Versionen."*

**Übersetzung in Klartext:** Nach ~9 Monaten aktiver Entwicklung (Mitte 2025 bis April 2026) zeigt der Optimizer nur **Forecasts und Einsparpotenziale an**. Er trifft keine einzige reale Steuerungsentscheidung. Die Lücke zwischen "Vorhersage zeigen" und "Akku tatsächlich regeln" ist eine Lücke von Monaten bis Jahren — wie man an Solalex sieht, der diese Lücke seit Jahren löst, braucht man dafür Hysterese, EEPROM-Schutz, Deadbands, Fail-Safes, Multi-WR-Handling und einen Haufen Edge-Case-Logik.

### 3.2 Der Optimizer ist experimentell, fragil und mit schweren Stabilitätsproblemen

Aus Discussion #23213 (offizielle HA-Einrichtungsanleitung): *"EVOpt ist Work in Progress (WIP), also noch in einer frühen Entwicklungsphase. Es dient vorrangig zum Anschauen und Experimentieren. Für Support oder Beiträge bitte KEINE Issues oder Pull Requests im GitHub Repository öffnen."*

Der Maintainer verbietet explizit Support-Anfragen und Issues. Das ist ein klares Signal, dass das Feature **nicht produktionsreif** ist.

Aus Discussion #23812 (September 2025), Kommentar des Maintainers: *"The optimizer implementation ist an incomplete prototype. The battery charge and discharge power is covered by #23559."*

Aus Discussion #23153 — ein User beschreibt die Aktivierung unter Home Assistant:

*"Ohne Strompreise und ohne Forecastprovider funktioniert der Optimizer nicht. ABER: Nachdem ich die beiden Komponenten in EVCC konfiguriert hatte, wurde EVCC extrem instabil. Es wurden ständig Messwerte von der Wallbox oder vom Inverter als veraltet gemeldet. Wenn man dann in die Logs schaute sah man dass die Daten fehlten weil EVCC zwischendurch abgestürzt und neugestartet war. Wenn es lief war es sehr zäh, ich habe dann gesehen dass mein Raspi in HA mit 90-100% angezeigt wird. Normal sehe ich da 10%. Der Effekt bleibt auch bestehen wenn ich in EVCC beides wieder rausnehme und neu starte. Was geholfen hat, war EVCC komplett zu deinstallieren und eine Sicherung vom Vortag einzuspielen."*

Übersetzt: Ein User hat den Optimizer aktiviert, sein Raspberry Pi ging von 10 % CPU auf 90–100 %, EVCC crashte ständig, und er musste EVCC **komplett deinstallieren und ein Backup vom Vortag zurückspielen**. Das ist kein Komfort-Bug, das ist ein **System-Killer**.

Aus Discussion #23163 (August 2025): *"since updating to v0.207.4, the message 'optimizer: not enough slots for optimization: 0' is logged exactly every 5 minutes."* — nach dem Update werden alle 5 Minuten Fehler geloggt, ohne dass der User etwas geändert hat.

Aus Discussion #23173 (Raspberry Pi): *"So I have disabled / removed the Optimizer for now, using the commands listed above to get rid of the errors and any potential negative impact it might have on EVCC's core functions."* — der User hat den Optimizer wieder abgeschaltet, aus Sorge um die **Kern-Funktionen** von EVCC.

### 3.3 Der Optimizer erfordert einen Sponsor Token — der Frust-Geschichte hat

Aus Discussion #23173 wörtlich: *"Important: The Optimizer can only be used with a sponsor token."*

Aus Discussion #23153: *"Um evopt unter HA zum laufen zu bringen gibt es ein paar Stolpersteine. Es wird ein Sponsortoken benötigt egal ob einmal Token oder monatlich."*

Und ein besonders aussagekräftiger User-Kommentar: *"Meine Wallbox ist eine Tinkerforge ohne Sponsortoken. Das erklärt es."* — dieser User kann den Optimizer gar nicht nutzen, weil seine Wallbox keinen Sponsor-Bonus liefert.

**Diese Abhängigkeit wird im EVCC-Profil bereits als grundlegendes Frust-Thema dokumentiert.** In der EVCC-Analyse haben wir Discussion #27634 zitiert, in der ein User beschreibt, dass sein "lifetime token" plötzlich abgelaufen ist. Der Optimizer multipliziert diesen Frust, weil er ein weiteres Premium-Feature hinter dem Sponsor-Token versteckt — und damit ein wachsendes Zwei-Klassen-System in der EVCC-Community etabliert.

### 3.4 Der Optimizer ist Cloud-basiert — oder kompliziert lokal

Aus der offiziellen Dokumentation: *"The optimizer is Python-based and leverages the strong ecosystem for mathematical optimisation and statistics. It is not part of evcc itself but a standalone service. When enabled, the cloud service optimizer.evcc.io is called."*

Das ist der erste Punkt, an dem EVCC seine eigene Core-DNA verletzt. Bisher war EVCC stolz auf "100 % lokal". Der Optimizer ruft standardmäßig einen Cloud-Dienst (`optimizer.evcc.io`) auf. Man kann ihn zwar lokal laufen lassen (als HA-Add-on, Docker-Container oder systemd-Service), aber:

Aus Discussion #23173: *"Ja, diese Anleitung nutzt die evopt.evcc.io Url. Die ist leider nur mit einem Sponsortoken abrufbar. Man kann evopt aber auch lokal laufen lassen und das umgehen. (...) Schade, dann wird man wahrscheinlich ein bisschen was im evopt Code ändern müssen, um die Sponsortokenvalidierung zu entfernen."*

Übersetzt: Auch die lokale Variante braucht einen Sponsor Token — es sei denn, der User modifiziert den Optimizer-Quellcode, um die Token-Validierung zu entfernen. Das ist ein Setup-Schmerz, der 98 % der Mainstream-User ausschließt.

### 3.5 Die Installation ist ein Setup-Albtraum

Aus Discussion #23173 (offizielle Raspberry-Pi-Anleitung), hier die **erforderlichen Schritte** für einen normalen User:

```
sudo mkdir /etc/systemd/system/evcc.service.d \
  && printf "[Service]\nEnvironment=\"EVOPT_URI=...\"\n" \
  | sudo tee /etc/systemd/system/evcc.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart evcc
```

Dazu: Installation von `uv` und `make`, Konfiguration von Tarifen (grid, feedin, solar), Einrichtung von Forecast-Providern, Validierung des Sponsor Tokens, Debugging der `optimizer.evcc.io`-URL vs. `localhost`, Behebung von "not enough slots"-Fehlern.

Aus Discussion #23045 (Docker-Installation): Ein User beschreibt, dass er evopt und evcc beide auf einer Synology-NAS im Docker Host-Network-Mode laufen lässt, alle Tarife konfiguriert hat, einen Sponsor Token besitzt, EVCC problemlos läuft — **und trotzdem den Optimizer-Menüpunkt in EVCC nicht sieht.**

Aus Discussion #23045 ein anderer verzweifelter User: *"In Home Assistant I added the option 'EVOPT_URI' and the environment variable is in fact visible in the container when issuing 'env'. It is also visible in '/proc/1/environ', so evcc should be able to pick it up."* — der User ist in `/proc/1/environ` unterwegs, um Environment-Variablen zu debuggen. Das ist Linux-Administration auf mittlerem Niveau.

---

## 4. Trotz aller Kritik: Die Optimizer-Idee ist gut und wird Fans finden

Es wäre unfair, das Feature kleinzureden. Es gibt echte Begeisterung in der Community:

Aus Discussion #23045: *"Optimizer auf Docker installiert und ich bin begeistert! Das Verhalten des Optimizers ist nachvollziehbar und der Forecast ist gut! Da es ja vor allem um die Optimierung der Hausbatterie geht wäre es super wenn wir demnächst auch eine Option haben die unsere Batterie auch steuert und die Ladung aus dem Netz erlaubt. Das ist ja mein Lieblingssport in der dunklen Jahreszeit. (...) Macht wirklich Spaß wie EVCC immer mehr meiner selbst geschriebenen Skripte übernimmt."*

Aus Discussion #23213: *"Ich muss sagen: Ich bin wirklich begeistert vom neuen Optimizer, technisch sauber umgesetzt, visuell ansprechend."*

Aus Discussion #23153: *"Unabhängig von meinem technischen Problem finde ich die Idee dahinter richtig klasse! Am liebsten wäre mir solcast Peak abhängig die Batterie in der früh sogar zu entladen, sodass meine 60 % Drosselung mittags optimiert werden kann."*

**Die Idee ist gut.** Die Vision ist gut. Die Visualisierung ist gut. Die technische Umsetzung im Prototyp ist sauber. Aber — und das ist entscheidend — **die Lücke zwischen Prototyp und Produktionsreife ist riesig.** Und genau in dieser Lücke hat Solalex seine Marktöffnung.

---

## 5. Die strategische Einordnung für Solalex

### 5.1 Was bedeutet der Optimizer für die Solalex-These?

Die Solalex-These lautet: *"Akku-Steuerung ist die universelle Lücke aller Wallbox-fokussierten Lösungen."*

Der Optimizer beweist diese These — **und unterstreicht sie gleichzeitig**. EVCC erkennt das Problem, sieht die Marktlücke, und beginnt, eine Lösung zu bauen. Das ist **Validierung** für Solalexs Marktthese.

Gleichzeitig zeigt der Optimizer, wie schwer diese Aufgabe wirklich ist. Nach 9 Monaten aktiver Entwicklung hat ein großes Open-Source-Team mit starker Community und kommerzieller Sponsoring-Finanzierung **noch nicht einen einzigen realen Steuerungsbefehl** an einen Akku geschickt. Sie zeigen nur Vorhersagen.

**Das ist nicht Unfähigkeit — das ist die tatsächliche Komplexität des Problems.** Echtzeitregelung eines Akkus ist fundamental schwieriger als das Vorhersagen optimaler Ladezeiten. Man braucht:

- Hardware-spezifische Kommunikationsprotokolle (Modbus, proprietäre APIs)
- EEPROM-Schutz und Schreibfrequenz-Management
- Hysterese und Deadbands für stabile Regelung
- Fail-Safe-Modi bei Kommunikationsausfall
- Multi-Hersteller-Support mit Edge-Cases pro Modell
- Notabschaltungs-Logik bei Fehlern
- Integration mit bestehenden Wechselrichter-Regelungen (damit man sich nicht gegenseitig stört)

Solalex beschäftigt sich mit all dem seit 2+ Jahren im Rahmen des Nulleinspeisungs-Blueprints. EVCC fängt jetzt erst damit an.

### 5.2 Die neue, schärfere Positionierung gegenüber EVCC

Die bisherige Co-Existenz-Botschaft aus der EVCC-Analyse lautete: *"EVCC ist großartig für dein Auto. Solalex ist großartig für alles andere."*

Nach der Optimizer-Analyse wird diese Botschaft **noch präziser und ehrlicher**:

> **"EVCC plant. Solalex regelt."**

Oder ausführlicher:

> **"Während EVCC experimentelle Vorhersagen für deinen Akku zeigt, regelt Solalex ihn schon heute — real, lokal, stabil und produktionsreif."**

Oder noch ehrlicher, mit Anerkennung:

> **"Der EVCC Optimizer beweist, wie wichtig Akku-Optimierung ist. Solalex macht es seit Jahren — nicht als Prototyp, sondern als produktionsreife Lösung."**

Das ist keine Herabsetzung von EVCC — es ist eine **faire, technisch korrekte** Beschreibung des Status. Der Optimizer ist explizit als experimentell gekennzeichnet. Diese Tatsache ist kein Geheimnis, sondern steht in der offiziellen Dokumentation.

### 5.3 Die vier Solalex-Vorteile, die der Optimizer-Vergleich schärft

**1. Real-time control vs. Informational only.** Der härteste, eindeutigste Vorteil. Solalex ändert wirklich Werte im Akku. Der Optimizer zeigt nur "was wäre wenn".

**2. No sponsor token vs. Sponsor token required.** Solalex ist für jeden zugänglich, der die Lizenz kauft. Der Optimizer ist nur für zahlende EVCC-Sponsoren nutzbar — und das in einer Zwei-Klassen-Struktur, die die Community ohnehin schon frustriert.

**3. 100 % lokal vs. Cloud-abhängig (oder kompliziert lokal).** Solalex ruft keinen Cloud-Dienst auf. Der Optimizer ruft standardmäßig `optimizer.evcc.io` auf — was EVCCs eigene "100 % lokal"-Botschaft unterwandert und für Nutzer überraschend ist.

**4. Stabil vom ersten Tag vs. System-Killer-Bugs.** Solalex darf keinen Raspberry Pi von 10 % auf 100 % CPU treiben. Der Optimizer tut genau das, dokumentiert in Discussion #23153. Das ist eine erzählbare Geschichte für Solalexs Stabilitäts-Versprechen.

### 5.4 Die neue Zielgruppen-Nuance: "Frustrierte Optimizer-Tester"

Durch den Optimizer entsteht eine neue, sehr konkrete Akquisitions-Persona:

**Der frustrierte Optimizer-Tester.** Das ist ein technisch versierter EVCC-Nutzer, der:
- Einen Sponsor Token hat (also zahlungsbereit ist)
- Den Optimizer installiert hat (also das Problem kennt)
- Feststellt, dass er nur Vorhersagen sieht (also das Feature-Gap kennt)
- Eine echte Akku-Steuerung will (also Solalexs Kern-Feature braucht)
- HA bereits nutzt (also die Infrastruktur hat)
- Eventuell sogar durch den Optimizer-Setup-Prozess erschöpft ist

Das ist eine **goldene Zielgruppe** für Solalex. Diese Leute verstehen die Domäne, sie verstehen den Wert von Software-Intelligenz, und sie haben bereits gezeigt, dass sie Geld für Energie-Software ausgeben.

**Konkrete Akquisitions-Idee:** Eine kurze, faire Blog-Post auf alkly.de mit dem Titel *"Der EVCC Optimizer zeigt dir, was passieren könnte. Solalex sorgt dafür, dass es passiert."* Kein Angriff, keine Herabsetzung — nur eine ehrliche Einordnung, wer welche Rolle im Stack übernimmt. Mit einem klaren CTA: "Wenn du EVCC für dein Auto und den Optimizer für Forecasts nutzt, fehlt dir noch die Akku-Steuerung. Genau da kommt Solalex rein."

---

## 6. Wann wird der Optimizer wirklich zur Bedrohung?

Das ist die entscheidende Langzeit-Frage. Meine Einschätzung, basierend auf dem, was ich gesehen habe:

**12 Monate (April 2027):** Der Optimizer ist wahrscheinlich immer noch im experimentellen Zustand, hat aber erste simple Steuerungs-Aktionen. Wahrscheinlich nur für ausgewählte Akku-Modelle (die, die EVCC bereits auslesen kann). Setup bleibt Sponsor-Token-gebunden. Solalex ist zu diesem Zeitpunkt längst im Markt und hat seine Zielgruppe etabliert.

**24 Monate (April 2028):** Der Optimizer steuert wahrscheinlich Akkus einiger großer Hersteller aktiv. Die Sponsor-Token-Hürde bleibt. Die Stabilität wird besser sein. Zu diesem Zeitpunkt **könnte** er zu einem realen Wettbewerber werden — aber für einen sehr spezifischen Nutzer-Typ: EVCC-Power-User mit Auto, Akku, und Sponsor-Bereitschaft.

**36 Monate (April 2029):** Der Optimizer ist möglicherweise produktionsreif. Aber bis dahin hat Solalex drei Vorteile ausgebaut: Marktposition, Kundenbasis, Hardware-spezifisches Wissen. Die Konkurrenz wird real, aber nicht existenzbedrohend, weil Solalexs Fokus (Balkonkraftwerk + Akku + Nicht-EV-Nutzer) für EVCC nie der Kern sein wird.

**Das strukturelle Argument:** EVCC ist und bleibt eine Wallbox-zentrierte Lösung. Der Optimizer wird immer *"wie optimiere ich Auto + Akku gemeinsam"* beantworten. Solalex beantwortet *"wie optimiere ich meinen Akku, egal ob ich ein Auto habe oder nicht"*. Diese Achsen-Differenz bleibt — und wird sich mit der Zeit sogar vertiefen, weil immer mehr Nutzer Akkus ohne E-Autos kaufen.

---

## 7. Patch-Vorschläge für das bestehende EVCC-Profil

Die folgenden Änderungen sollten in Wettbewerber_01_EVCC.md v1.1 integriert werden:

**Patch 1: Neuer Frust-Punkt in Kapitel 4 ("Frust-Punkte")**
> **"4.X: Der Optimizer ist der Beweis, dass EVCC die Akku-Lücke erkennt — und ihn noch nicht geschlossen hat."** Mit den Zitaten aus 3.1–3.5 dieses Supplements.

**Patch 2: Verschärfte Botschaft in Kapitel 10 ("Botschaften")**
Hinzufügen:
> **"EVCC plant. Solalex regelt."**
> **"Während EVCC experimentelle Vorhersagen für deinen Akku zeigt, regelt Solalex ihn schon heute — real, lokal, stabil und produktionsreif."**

**Patch 3: Neuer Risiko-Punkt in Kapitel 11**
> **"Risiko: EVCC Optimizer wird 2027–2028 produktionsreif."** Mit der Einordnung aus Kapitel 6 dieses Supplements: real, aber nicht existenzbedrohend, weil die Achsen-Differenz (EV-zentriert vs. Akku-zentriert) strukturell bleibt.

**Patch 4: Neue Zielgruppen-Nuance in Kapitel 12 ("Konkrete nächste Schritte")**
> **"Frustrierte Optimizer-Tester als Akquisitions-Zielgruppe identifizieren."** Mit der Blog-Post-Idee aus Kapitel 5.4 dieses Supplements.

---

## 8. Die wichtigste Erkenntnis dieses Supplements

Der EVCC Optimizer ist **keine akute Bedrohung** für Solalex — aber er ist **die beste Validierung** der Solalex-These, die wir uns wünschen könnten.

EVCC, der größte und erfolgreichste Open-Source-Wettbewerber in diesem Raum, sagt mit dem Optimizer öffentlich: *"Akku-Optimierung ist wichtig. Wir fangen jetzt an, daran zu arbeiten."* Nach 9 Monaten Arbeit zeigen sie nur Forecasts. Solalex regelt seit Jahren.

Das ist nicht Schadenfreude — das ist **Marktreife**. EVCC validiert den Markt, der Optimizer validiert das Bedürfnis, und Solalex steht bereits da mit einer funktionierenden Lösung.

Die taktische Konsequenz: **Solalex sollte in den nächsten 12 Monaten mit maximaler Geschwindigkeit in den Markt — bevor der Optimizer produktionsreif wird.** Nicht panisch, sondern planvoll. Das 9-Wochen-MVP-Timeline ist genau richtig. Die Beta-Phase sollte nicht verschoben werden. Die HACS-Submission sollte früher als später kommen.

Und die Co-Existenz-Story mit EVCC wird durch den Optimizer **stärker, nicht schwächer**. EVCC hat jetzt einen offiziellen Grund, warum Solalex existieren darf: *"Wir arbeiten am Optimizer, aber er ist experimentell. Wenn du heute eine stabile Akku-Regelung willst, gibt es Solalex."* Das ist die Art von indirekter Empfehlung, die wir über Jahre hinweg organisch wachsen lassen können.

---

## 9. Konkrete nächste Aktionen

**Sofort:**
1. Diesen Supplement in die EVCC-Analyse als Kapitel-Ergänzung einarbeiten (oder als separates Dokument belassen — Alex' Entscheidung).
2. Die vier Patches in Kapitel 7 in eine neue EVCC-Profil-Version v1.1 einpflegen.
3. Die neue Zielgruppen-Persona "Frustrierter Optimizer-Tester" in den PRD und/oder in die Beta-Tester-Liste aufnehmen.

**Vor Beta:**
4. Blog-Post-Entwurf vorbereiten: *"Der EVCC Optimizer zeigt dir, was passieren könnte. Solalex sorgt dafür, dass es passiert."* — fair, anerkennend, mit klarer Positionierung.
5. In den Solalex-Materialien eine kurze FAQ-Antwort vorbereiten: *"Wie unterscheidet sich Solalex vom EVCC Optimizer?"* mit den vier Differenzierungs-Punkten aus 5.3.

**Beta-Phase:**
6. 1–2 Beta-Tester gezielt aus der Optimizer-Test-Community gewinnen. Diese User sind technisch versiert, zahlungsbereit und kennen die Lücke bereits.

**Post-Launch:**
7. Den Optimizer regelmäßig monitoren (alle 3–4 Monate). Sobald er echte Steuerungsaktionen liefert, Positionierung nachschärfen. Bis dahin: die aktuelle Botschaft beibehalten.

---

## 10. Anhang: Quellen

**GitHub:**
- `evcc-io/optimizer` (separates Repo)
- Issue #23042 (Epic: Improve experimental optimizer)
- Issue #23559 (Battery charge/discharge power)
- Issue #22944 (Battery max charge/discharge power)
- Discussion #23045 (How to run the Optimizer with Docker)
- Discussion #23153 (Optimizer in 0.207.4 unter Home Assistant einrichten)
- Discussion #23163 (optimizer: not enough slots)
- Discussion #23173 (How to run the Optimizer on Raspberry Pi)
- Discussion #23213 (EVCC Optimizer Einrichtung als Home Assistant Addon)
- Discussion #23812 (Questions regarding Optimizer)

**Dokumentation und Blog:**
- `docs.evcc.io/en/docs/features/optimizer` (offizielle Feature-Seite)
- `docs.evcc.io/blog/2026/01/01/highlights-browser-config-ready` (EVCC-Blog, Januar 2026, mit Optimizer-Ausblick)

**Release-Tracking:**
- `releasebot.io/updates/evcc-io/evcc` (April 2026: "optimizer error fixes")

Alle Zitate sind im Original-Wortlaut wiedergegeben, mit dem Datum, aus dem sie stammen.
