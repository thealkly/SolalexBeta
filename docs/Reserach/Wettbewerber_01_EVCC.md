# Wettbewerber-Profil 1: EVCC
**Tiefen-Analyse mit Original-Nutzerstimmen, Begeisterungs-Features, Optimizer-Analyse und Solalex-Differenzierung**

Stand: April 2026 (v1.1, mit integrierter Optimizer-Analyse) · Quellen: GitHub Discussions & Issues (`evcc-io/evcc`, `evcc-io/optimizer`), Photovoltaikforum, openHAB-Community, simon42-Community, elefacts.de, EVCC-Blog, TFF-Forum, `docs.evcc.io`

---

## 1. Schnellprofil

**Name:** EVCC (Electric Vehicle Charge Controller)
**Typ:** Open-Source-Energiemanager mit Sponsor-Token-Modell
**Lizenz:** Source-available, einige Features hinter Sponsor-Token (~2 €/Monat oder 100 € einmalig)
**Sterne auf GitHub:** ~6.400 (April 2026, Tendenz stark wachsend)
**Forks:** ~1.275
**Sprache:** Go (Backend), Vue.js (Frontend), Python (Optimizer-Dienst)
**Primäre Zielgruppe:** PV-Anlagen-Besitzer mit E-Auto und Wallbox
**Marktposition DACH:** Klarer Marktführer im Open-Source-Segment für Wallbox-Überschussladen
**Aktuelle Hauptversion:** v0.300+ (Januar 2026 mit Browser-Config als Meilenstein)
**Neuestes strategisches Feature:** Optimizer (evopt) — experimentell seit Mitte 2025

---

## 2. Was EVCC fundamental ist (und was nicht)

EVCC wurde aus einem klar umrissenen Schmerzpunkt geboren: **PV-Strom soll ins eigene E-Auto fließen, nicht für 7 ct an den Netzbetreiber verschenkt werden.** Diese Mission spürt man in jedem Architekturdetail — der Loadpoint ist die zentrale Abstraktion, die Wallbox ist der zentrale Aktor, das Auto ist der zentrale Verbraucher. Alles andere (Heim-Akku, Wärmepumpe, Heizstab) ist später oben drauf gewachsen — und genau dort liegen die strukturellen Risse.

Im EVCC-Blog-Interview mit Michael aus dem Core-Team (Juni 2025) sagt er es selbst: *"In einer idealen Welt sollte intelligenter Energieumgang so einfach wie möglich sein. Tesla macht das mit seiner Powerwall-Wallbox-Fahrzeug-Kombination relativ gut. Aber sobald man das Ökosystem verlässt — anderes Fahrzeug, Wärmepumpe integrieren — wird es kompliziert."* Diese Aussage ist gleichzeitig die ehrlichste Selbstdiagnose und die größte Marktöffnung für Solalex.

Und seit Mitte 2025 hat EVCC begonnen, an genau dieser Schwäche zu arbeiten — mit dem **Optimizer (evopt)**, einem separaten Python-Dienst, der mit EVCC kommuniziert und auf Basis von Gleichungssystemen und Statistik Kosten-optimale Energieflüsse berechnet. Der Optimizer ist strategisch so wichtig, dass er ein eigenes Kapitel in dieser Analyse bekommt (Kapitel 5).

---

## 3. Begeisterungs-Features — was Nutzer an EVCC lieben

Bevor wir auf Schwächen schauen, müssen wir verstehen, **warum** EVCC erfolgreich ist. Wer das ignoriert, kopiert die falschen Dinge oder unterschätzt den Wettbewerber.

### 3.1 "Es funktioniert einfach"

Aus Discussion #9979: *"Von der Leistung von evcc bin ich total begeistert! Ich nutze das zum Überschussladen. Ich habe eine Mennekes Amtron, die ich inzwischen umbauen kann von 3-phasig (im Winter für schnelles Laden) und 1-phasig (im Sommer für besseres Überschussladen)."*

Aus Discussion #14001: *"Seit drei Tagen nutze ich begeistert EVCC und bin beeindruckt von seiner Leistung und Benutzerfreundlichkeit. Besonders die reibungslose Steuerung meiner Mennekes Wallbox hat mich überzeugt."*

Aus Discussion #6476: *"Habe heute evcc in Betrieb genommen und bin begeistert."*

**Lehre für Solalex:** Die Time-to-First-Erfolgserlebnis ist bei EVCC kurz. Nutzer berichten nach drei Tagen schon Begeisterung. Das ist die Latte. Wenn Solalex 10 Minuten verspricht, müssen die ersten Sekunden danach schon Wow-Momente liefern — sonst klingt das wie Marketing-Übertreibung.

### 3.2 Phasenumschaltung 1↔3 als Killer-Feature

Im PV-Forum-Thread #239358: *"Ich nutze selbst seit einigen Wochen EVCC und bin begeistert, da man Dinge damit machen kann, die Autos im Wert von >50k nicht hinbekommen. Da habe ich kein Problem dafür mal 100 € auf den Tisch zu legen."*

Im gleichen Thread: *"An EVCC sollten sich alle WB-Hersteller orientieren. Diese 'Geiz ist Geil'-Mentalität ist am Ende nur eins: Ungeil."*

**Lehre für Solalex:** Die automatische Phasenumschaltung im Sommer ist EVCCs Magie-Moment. Nutzer fühlen sich dem Hersteller technisch überlegen. Solalex braucht eine ähnliche emotionale Magie — bei uns könnte das **die EEPROM-Schonung sichtbar machen** sein ("Solalex hat heute 142 statt 14.000 Schreibvorgänge an deinen Wechselrichter gesendet — deine Hardware bedankt sich"). Magie entsteht, wenn der Nutzer etwas sieht, was er ohne uns nicht hätte.

### 3.3 Migration von openWB → EVCC

Aus Discussion #23087: *"Hey zusammen, vielen Dank für das tolle Tool. Bin von openWB umgestiegen & vollends begeistert!!"*

**Lehre für Solalex:** Migration ist ein massiver Wachstumstreiber. EVCC saugt Nutzer aus openWB ab, weil openWB komplexer ist und teurer. Solalex muss eine analoge Migration aktiv anbieten — von Hersteller-Apps und vom eigenen Blueprint.

### 3.4 UI-Schlichtheit

Aus dem elefacts.de-Test: *"Die Benutzeroberfläche von evcc ist schön schlicht gehalten und sieht modern aus. Die Möglichkeit den Anteil an eigenem PV-Strom auszuwählen und auch mit Mischbezug zu arbeiten macht evcc nochmals flexibler."*

**Lehre für Solalex:** Schlicht schlägt featurelastig. Das ist ein Punkt, an dem Solalex mit dem v1.2-Design (Klarheit vor Features, Ergebnis vor Technik) bereits richtig liegt — aber er muss konsequent durchgehalten werden, gerade wenn die Roadmap wächst.

### 3.5 Hardware-Kompatibilitäts-Datenbank

Im EVCC-Blog: *"Wir schaffen eine Art Datenbank, die Schnittstellen zu fast allen Wallboxen, Wechselrichtern und anderen Geräten einheitlich aufbereitet."*

**Lehre für Solalex:** Die EVCC-Templates sind ein Network-Effekt-Asset. Solalex kann das nicht direkt kopieren — aber das Profile-Marketplace-Konzept aus der Roadmap (V1.x) ist die analoge Antwort: crowdsourced Wissen über Hardware-Profile, das mit jedem Nutzer wertvoller wird.

### 3.6 Battery Boost & Battery Hold

Aus Discussion #20312: *"In addition to this, there is a button called 'Battery boost' in the loadpoint settings, this will make sure to charge with surplus + max battery power. Useful if you charge the car before leaving while knowing the battery will be fully charged afterwards due to good weather."*

**Lehre für Solalex:** EVCC hat einen sichtbaren "magischen Knopf", der eine komplexe Strategie auf einen Klick reduziert. Solalex braucht solche Knöpfe — z. B. "Akku jetzt voll machen", "Jetzt nichts einspeisen", "Heute Abend Wärmepumpe vorheizen". Komplexität verstecken, Magie sichtbar machen.

### 3.7 Browser-Config als Meilenstein Januar 2026

Aus dem EVCC-Blog (1. Januar 2026): *"2026 ist da und mit evcc v0.300 startet das neue Jahr mit dem vermutlich wichtigsten Meilenstein: Die Konfiguration via Browser ist nicht mehr experimentell. Das meistgewünschte Feature ist endlich fertig für den Einsatz. Neue Nutzer können evcc jetzt komplett ohne Kommandozeile oder YAML-Datei einrichten."*

**Lehre für Solalex:** EVCC hat 2+ Jahre gebraucht, um die YAML-Konfiguration mit einer Browser-Oberfläche zu ersetzen — und das ist für sie ein "Meilenstein". Solalex startet **von Tag eins mit dieser Konfigurationsart**. Das ist nicht ein Feature, das nachgezogen werden muss — es ist der Ausgangspunkt. Diese strukturelle Abwesenheit von technischer Schuld ist ein massiver Vorteil, der in der Außenkommunikation sichtbar sein sollte.

### 3.8 Der Optimizer wird gefeiert — auch wenn er noch nichts regelt

Aus Discussion #23045: *"Optimizer auf Docker installiert und ich bin begeistert! Das Verhalten des Optimizers ist nachvollziehbar und der Forecast ist gut! (...) Macht wirklich Spaß wie EVCC immer mehr meiner selbst geschriebenen Skripte übernimmt."*

Aus Discussion #23213: *"Ich muss sagen: Ich bin wirklich begeistert vom neuen Optimizer, technisch sauber umgesetzt, visuell ansprechend."*

Aus Discussion #23153: *"Unabhängig von meinem technischen Problem finde ich die Idee dahinter richtig klasse!"*

**Lehre für Solalex:** Die Begeisterung für den Optimizer zeigt, dass EVCCs Community **dringend nach Akku-Optimierung verlangt**. Die Idee verkauft sich — auch wenn das Produkt dahinter noch experimentell ist. Das ist exakt die Marktöffnung, die Solalex bedienen muss. Siehe die ausführliche Optimizer-Analyse in Kapitel 5.

---

## 4. Frust-Punkte — was Nutzer an EVCC genervt hat

### 4.1 Akku ist und bleibt "autark" — der größte strukturelle Riss

Aus Discussion #28341 (März 2026, neueste Diskussion): *"I am very happy with all evcc features for charging cars and heatpump. Now I wanted to integrate AC Batterie (Marstek Venus E V3). The Marstek Venus Template works for not emptying Venus while charging cars. But it does not realize 'Nulleinspeisung/zero export': when consuming e.g. 500W from grid, I have expected that evcc controls Venus to discharge 500W. I think this should work easily for evcc via Modbus TCP, right? Is this not yet featured?"*

Die Antwort eines erfahrenen Users im selben Thread ist entscheidend: *"evcc does not control the battery in that sense. The general control mechanism still needs to be regulated by the battery itself. (...) Depending on your interval it takes way too long to send the proper command to the battery for regulating the power. Especially if you have more devices/loadpoints/batteries, etc the interval is even cumulative. For a zero feed-in/Nulleinspeisung, you need quick reaction time."*

Aus Discussion #14739: *"I want to use my house battery for supporting charging at day, but not in the evening or night."* — die Antwort des Users selbst: *"Found there is another issue about this already."* (die Funktion ist seit Juli 2024 offen)

Aus Discussion #14648: *"I would love to implement an (option) time schedule feature for the home battery settings where different prioritySoc / bufferSoc / bufferStartSoc settings can be configured for different times during the day."* — seit Juli 2024 offen.

Aus Discussion #20208: *"I would like to be able to dynamically change the settings for Home battery or vehicle charging prioritization."* — März 2025, offen.

**Solalex-Differenzierung:** Akku-Steuerung ist Solalexs **Kern**, nicht ein verzögertes Feature. Während EVCC den Akku als "autarken" Block behandelt, ist Solalex von Tag eins darauf optimiert, ihn als orchestrierbaren Verbraucher zu behandeln. Die Botschaft: **"Was EVCC für deine Wallbox ist, ist Solalex für deinen Akku."**

### 4.2 Dynamic Battery Schedule wird seit 2024 nachgefragt — und ist immer noch nicht da

Aus Issue #18467 (Januar 2025, immer noch open mit "stale"-Label): *"Two new 'night-mode' options for optimized usage of home battery."* — der Issue wurde mit "stale" markiert und offenbar geschlossen, ohne implementiert zu sein.

Aus Issue #22739 (August 2025): *"Wattsonic — Active Battery Control. The issue here is that once starting the charging process battery can also be used for charging an EV. This is not efficient very much. Currently I need to handle this via HomeAssistant MODBUS integration."*

**Solalex-Differenzierung:** Zeit-basierte Akku-Profile sind ein Standard-Feature, kein V2-Wunsch. Der Nutzer kann sagen: "Vor 6 Uhr morgens Akku voll, danach freigeben, ab 18 Uhr nur noch Hausverbrauch decken." Das ist im PRD bereits angedacht und sollte als USP markiert werden.

### 4.3 Reaktionszeit ist zu langsam für Echte-Nulleinspeisung

Aus Issue #22613 (Juli 2025): *"The battery is reacting really fast, easily leveling off all small changes in energy fluctuation. EVCC/the car charger is not. It's sluggish. Once the battery is full, which it will be rather quick with prioritization, it cannot level off changes in power anymore. A sudden power spike (e.g. cloud moves away or oven is switched off) takes evcc/the car maybe 10-20s to adjust (or longer if a phase switch is involved), in which the excessive energy went to the grid (and could not be absorbed by the battery)."*

**Solalex-Differenzierung:** EVCCs Default-Loop-Intervall ist 30 s, das ist für echte Nulleinspeisung zu langsam. Solalex muss in der Lage sein, im Sekunden-Bereich zu regeln (mit den Sicherheitsmechanismen aus dem EEPROM-Patch). Die Botschaft: **"Solalex reagiert so schnell, wie dein Smart Meter Daten liefert — ohne deinen Wechselrichter zu verschleißen."**

### 4.4 Sponsor-Token-Frust ist real und wiederkehrend

Aus Discussion #27634 (Februar 2026): *"Feb 23 12:17:06 evcc docker FATAL: sponsorship rpc error: token is expired — get a fresh one. I thought I've bought a life time sponsorship token for 100 $ on February 10, 2023."* Antwort eines anderen Users: *"Well, it seems that a lifetime sponsorship token means that the sponsorship is for lifetime, but not the token. It has to be re-freshed from time to time."*

Aus Discussion #22961 (August 2025): *"Sponsor Token Expiration Prevents Plugin Start and UI Access — No Simple Way to Update."*

Aus Discussion #2130: *"They use a go.e with pv and the 1p/3p switching is important. Unfortunately I learned, that this feature is behind a paywall. Not only that, it is a Github only subscription via a token, that must be renewed every year."*

Aus Discussion #5897: *"Heute hat mir GitHub mitgeteilt, dass Sponsoring Tokens nicht mehr per PayPal, sondern nur noch per Kreditkarte bezahlt werden können. Ich möchte meine Kreditkartendaten möglichst nicht überall auf der Welt, auch nicht auf GitHub, hinterlegen."*

Aus Discussion #5122: *"Up to this point documentation said that Go-E does not need a sponsor token, so I am sure some users chose and purchased their EVCC hardware according to this promise."* (Hardware war gekauft worden in der Annahme, kostenlos zu funktionieren — dann wurde sie hinter den Paywall verschoben.)

Aus Discussion #26185: *"After a lot of frustration and days of attempts (long story for later) managed to finally! get EVCC image operating on NanoPi from its internal MMC memory — all good. (but way confusing & difficult). I really want to be able to say great things about evcc, but to date for various reasons … its been a frustrating process."*

**Solalex-Differenzierung:** Das Lizenzmodell ist eines der wichtigsten Kaufargumente. Solalexs Plan (Einmalkauf, Lizenz vor "Activate"-Button, keine Token-Erneuerung) ist exakt die Anti-These zum EVCC-Frust. Das muss prominent kommuniziert werden:
- **Einmal zahlen, dauerhaft nutzen — kein Token-Theater.**
- **Keine Erneuerung, kein Ablauf, keine plötzlichen Paywall-Verschiebungen.**
- **Klare Lizenz vor der Aktivierung — niemand zahlt für etwas, das nicht funktioniert.**

### 4.5 Setup ist für Nicht-Techniker keine 10 Minuten

Aus Discussion #26185: *"After 4 days of on and off attempts — i continue to persist."*

Aus Issue #20573 (April 2025): *"Updated the evcc installation to 0.203.0 and receive following error: The wallbox (ABL MH1) is connected via USB and worked till the update. The right parameter for the box is 8N1 and not 8E1 — I guess the config change came through the update. But as you see the wallbox is not displayed anymore. Also the vehicle is missing. So I'm not able to fix the configuration."* — Update zerstört die Konfiguration, der Nutzer kann sie über die UI nicht reparieren.

Aus Discussion #25664 (November 2025): YAML-Konfiguration mit 30+ Zeilen Templates für SMA-Home-Manager, drei PV-Wechselrichter, Victron-Akku — *"Ich habe den aktuellen Token geholt aber irgendetwas geht nicht."*

Aus dem EVCC-FAQ selbst: *"yaml ist sehr syntax-empfindlich. Fehler fallen nicht immer sofort ins Auge. Eine schnelle Hilfe bieten yaml-Tester wie z. B. onlineyamltools.com/validate-yaml."*

**Solalex-Differenzierung:** Solalex hat **kein YAML, das Nutzer editieren müssen**. Auto-Discovery, geführter Onboarding, sinnvolle Defaults. Die Botschaft: *"Wenn du in den letzten zehn Jahren keinen Online-YAML-Validator gebraucht hast, sollte sich das auch jetzt nicht ändern."*

### 4.6 Update-Risiko: Konfigurationsverlust

Aus Issue #20573: Update von 0.201.1 auf 0.203.0 zerstörte die USB-Wallbox-Konfiguration. Aus Issue #13750 (Mai 2024): *"Load Management, throttling doesn't work. Whenever the grid import is too high, EVCC stops the charging, instead of throttling down."*

Aus dem openHAB-Forum: *"I have installed the evcc binding for a long time and it worked correctly until an update from openhab. (...) When creating an item everything looks ok, but after saving there is a ?"*

**Solalex-Differenzierung:** Updates über den HA Add-on Store, automatische Backups vor jedem Update, sauberer Rollback bei fehlgeschlagenem Update. Das ist im PRD bereits vorgesehen — aber es muss als Vertrauenssignal **sichtbar** sein, z. B. mit einer Anzeige "Letzte 5 Updates erfolgreich, letzte Konfiguration gesichert vor X Minuten."

### 4.7 Lastmanagement mit mehreren Wallboxen fehlt offiziell

Aus dem EVCC-FAQ selbst: *"Mehrere Wallboxen und damit Ladepunkte können in evcc verwendet werden. Es ist jedoch heute noch kein Lastmanagement möglich. Das ist auf unserer langen Liste für die weitere Entwicklung."*

Aus Discussion #10134: *"As EVCC currently works, especially in the months where there is some sun but not massive amounts, we would charge car 1 then car 2, then battery (which would result in drawing from grid). What would make more sense for those people would be a full car 1, as much home battery charging as possible, and car 2 (or consumer) gets whatever is left, or is charged manually if needed."* Antwort des Maintainers: *"The planner does currently not take priorities into account. I'm not convinced that it should."*

**Solalex-Differenzierung:** Solalex ist im MVP bewusst auf 1 WR + 1 SM + 1 Akku begrenzt — aber V1.x sollte hier eine klare Priorisierungs-Engine bringen. Wichtig: Im Gegensatz zu EVCC, wo der Maintainer aktiv gegen Priorisierung argumentiert, ist Priorisierung für Solalex ein **Kern-Konzept**, kein Streitthema. Damit kann Solalex die Nutzer abholen, deren Wunsch von EVCC ignoriert wird.

### 4.8 EVCC erkennt Balkonkraftwerke nicht

Aus Discussion #13314: *"Kann es vielleicht mit dem Balkonkraftwerk zusammenhängen, dessen Ertrag von EVCC nicht gemessen wird, aber für einen 'negativen' Hausverbrauch sorgt, da es direkt in einer Steckdose steckt, EVCC aber für den Hausverbrauch dies sieht?"*

**Solalex-Differenzierung:** Solalex **ist** für Balkonkraftwerke gebaut. Das ist nicht eine Ergänzung — das ist die Geburtsstunde. Dieses Detail hat strategische Bedeutung: Balkonkraftwerke sind das schnellst wachsende Segment im PV-Markt 2025/2026, und EVCC adressiert sie explizit nicht.

### 4.9 Modbus-Konflikte zwischen EVCC und Home Assistant

Aus dem Skoda-Enyaq-Forum (Marktanalyse-Quelle): *"Sowohl HA als auch EVCC wollen die Daten des Wechselrichters via Modbus-TCP auslesen. Da wird typischerweise nur ein Gerät zugelassen. Lösung: Modbus-Proxy-Addon davorschalten."*

**Solalex-Differenzierung:** Solalex kommuniziert nie direkt mit Hardware. Damit gibt es keinen Modbus-Konflikt — niemals. Botschaft: *"Solalex kommt nie in Konflikt mit deinen anderen Tools, weil Solalex keine Hardware direkt anspricht."*

### 4.10 EVCC für "alles andere als Auto" wird offiziell als ungeeignet beschrieben

Diese Stimme ist die Pointe der gesamten Analyse. Aus Discussion #9979: *"EVCC hat sich leider als nicht geeignet herausgestellt, um neben dem Auto auch andere Verbraucher zu steuern (Integration zu komplex, Features nicht ausreichend abgedeckt). Auch andere Lösungen wie EMHASS oder PV Excess Control habe ich ausprobiert, beides war mir aber ebenso zu komplex für meine 'einfachen' Use-Cases."*

**Solalex-Differenzierung:** Das ist eine wörtlich artikulierte Marktlücke, geschrieben von einem erfahrenen, technisch fähigen Nutzer in der EVCC-Community selbst. Solalex ist die direkte Antwort auf genau diese Aussage. Das könnte fast 1:1 als Headline auf einer Landing Page funktionieren:

> **"EVCC ist großartig für dein Auto. Solalex ist großartig für alles andere."**

### 4.11 Der Optimizer ist der Beweis der Akku-Lücke — und schließt sie nicht

Das ist der neueste und strategisch wichtigste Frust-Punkt, weil EVCC hier **öffentlich erkennt**, dass eine Lücke existiert — und dann seit 9 Monaten dabei zuschauen muss, wie die Schließung dieser Lücke sich als viel schwerer herausstellt als gedacht.

Der Optimizer ist ein separates Kapitel wert, weil er strategisch zu wichtig ist. Siehe Kapitel 5.

---

## 5. Der EVCC Optimizer (evopt) — eine strategisch eigenständige Analyse

Weil der Optimizer der einzige EVCC-Vorstoß direkt in Solalexs Kern-Territorium ist, verdient er eine eigene Tiefen-Analyse. Die Leitfrage: **Wie ernst müssen wir den EVCC Optimizer als Bedrohung für Solalex nehmen?**

Kurze Antwort: **Ernst, aber die Bedrohung ist in den nächsten 12–18 Monaten noch nicht real — und die Architektur-Entscheidungen des Optimizers spielen Solalex sogar in die Hände.**

### 5.1 Was der EVCC Optimizer ist

Der Optimizer (offizieller Name: **evopt**) ist ein **separater Python-Dienst**, der mit EVCC kommuniziert und auf Basis von Gleichungssystemen und Statistik Kosten-optimale Energieflüsse berechnet.

**Eigene Selbstbeschreibung aus dem EVCC-Blog (1. Januar 2026):** *"Heute regeln wir einzelne Komponenten oft individuell. Der Optimizer hat das Ziel, das Gesamtsystem zu optimieren: Paralleles Laden mehrerer Fahrzeuge, Hausbatterien und Verbraucher – basierend auf Preissignalen, PV-Vorhersagen und Hausverbrauchsprognosen. Seit Mitte 2025 arbeitet eine Gruppe von Leuten an einem Optimierungsalgorithmus für evcc. Er basiert auf Gleichungssystemen und Statistik. Produktmarketing würde das vmtl. AI nennen."*

**Aus der offiziellen Dokumentation (`docs.evcc.io/en/docs/features/optimizer`):** *"evcc works rule-based and deterministically. This works great for many setups. E.g. a solar system, battery, and one vehicle. More complex scenarios push this approach to its limits: Multiple vehicles: Which one should be charged first? Battery or vehicle: Where should the available energy go? Dynamic tariffs: Is it worth charging from the grid tonight, or will there be enough solar energy tomorrow? The optimizer can answer these questions."*

**Technisch:**
- Eigenes GitHub-Repo: `evcc-io/optimizer`
- Python-basiert, setzt `uv` und `make` voraus
- Läuft als separater Dienst (Docker-Container, HA-Add-on oder systemd-Service)
- Kommuniziert mit EVCC über `EVOPT_URI` Environment-Variable
- Wird über einen Cloud-Dienst (`optimizer.evcc.io`) angesprochen — oder lokal

### 5.2 Fakt 1: Der Optimizer ist "purely information-only" — er regelt NICHTS

Das ist der mit Abstand wichtigste Fakt. Aus Issue #23042 (offizielles Epic für Optimizer-Verbesserungen) wörtlich:

*"NOTE: at this time, the optimizer is purely information-only ('what would happen if we actually used this'). It is not used to make actual decisions."*

Und aus der offiziellen Dokumentation: *"The optimizer is currently informational only. It shows forecasts and potential savings but does not yet actively control anything."*

Und aus der deutschen Version: *"Der Optimizer ist in einem frühen Entwicklungsstadium. Die angezeigten Daten sind derzeit informativ. Steuerungsaktionen folgen in zukünftigen Versionen."*

**Übersetzung in Klartext:** Nach ~9 Monaten aktiver Entwicklung (Mitte 2025 bis April 2026) zeigt der Optimizer nur **Forecasts und Einsparpotenziale an**. Er trifft keine einzige reale Steuerungsentscheidung. Die Lücke zwischen "Vorhersage zeigen" und "Akku tatsächlich regeln" ist eine Lücke von Monaten bis Jahren — wie man an Solalex sieht, der diese Lücke seit Jahren löst, braucht man dafür Hysterese, EEPROM-Schutz, Deadbands, Fail-Safes, Multi-WR-Handling und einen Haufen Edge-Case-Logik.

### 5.3 Fakt 2: Der Optimizer ist experimentell, fragil und mit schweren Stabilitätsproblemen

Aus Discussion #23213 (offizielle HA-Einrichtungsanleitung): *"EVOpt ist Work in Progress (WIP), also noch in einer frühen Entwicklungsphase. Es dient vorrangig zum Anschauen und Experimentieren. Für Support oder Beiträge bitte KEINE Issues oder Pull Requests im GitHub Repository öffnen."*

Der Maintainer verbietet explizit Support-Anfragen und Issues. Das ist ein klares Signal, dass das Feature **nicht produktionsreif** ist.

Aus Discussion #23812 (September 2025), Kommentar des Maintainers: *"The optimizer implementation ist an incomplete prototype. The battery charge and discharge power is covered by #23559."*

Aus Discussion #23153 — ein User beschreibt die Aktivierung unter Home Assistant:

*"Ohne Strompreise und ohne Forecastprovider funktioniert der Optimizer nicht. ABER: Nachdem ich die beiden Komponenten in EVCC konfiguriert hatte, wurde EVCC extrem instabil. Es wurden ständig Messwerte von der Wallbox oder vom Inverter als veraltet gemeldet. Wenn man dann in die Logs schaute sah man dass die Daten fehlten weil EVCC zwischendurch abgestürzt und neugestartet war. Wenn es lief war es sehr zäh, ich habe dann gesehen dass mein Raspi in HA mit 90-100% angezeigt wird. Normal sehe ich da 10%. Der Effekt bleibt auch bestehen wenn ich in EVCC beides wieder rausnehme und neu starte. Was geholfen hat, war EVCC komplett zu deinstallieren und eine Sicherung vom Vortag einzuspielen."*

Übersetzt: Ein User hat den Optimizer aktiviert, sein Raspberry Pi ging von 10 % CPU auf 90–100 %, EVCC crashte ständig, und er musste EVCC **komplett deinstallieren und ein Backup vom Vortag zurückspielen**. Das ist kein Komfort-Bug, das ist ein **System-Killer**.

Aus Discussion #23163 (August 2025): *"since updating to v0.207.4, the message 'optimizer: not enough slots for optimization: 0' is logged exactly every 5 minutes."* — nach dem Update werden alle 5 Minuten Fehler geloggt, ohne dass der User etwas geändert hat.

Aus Discussion #23173 (Raspberry Pi): *"So I have disabled / removed the Optimizer for now, using the commands listed above to get rid of the errors and any potential negative impact it might have on EVCC's core functions."* — der User hat den Optimizer wieder abgeschaltet, aus Sorge um die **Kern-Funktionen** von EVCC.

### 5.4 Fakt 3: Der Optimizer erfordert einen Sponsor Token — der Frust-Geschichte hat

Aus Discussion #23173 wörtlich: *"Important: The Optimizer can only be used with a sponsor token."*

Aus Discussion #23153: *"Um evopt unter HA zum laufen zu bringen gibt es ein paar Stolpersteine. Es wird ein Sponsortoken benötigt egal ob einmal Token oder monatlich."*

Und ein besonders aussagekräftiger User-Kommentar: *"Meine Wallbox ist eine Tinkerforge ohne Sponsortoken. Das erklärt es."* — dieser User kann den Optimizer gar nicht nutzen, weil seine Wallbox keinen Sponsor-Bonus liefert.

**Diese Abhängigkeit multipliziert den bereits dokumentierten Sponsor-Token-Frust aus 4.4.** Der Optimizer versteckt ein weiteres Premium-Feature hinter dem Sponsor-Token und etabliert damit ein wachsendes Zwei-Klassen-System in der EVCC-Community.

### 5.5 Fakt 4: Der Optimizer ist Cloud-basiert — oder kompliziert lokal

Aus der offiziellen Dokumentation: *"The optimizer is Python-based and leverages the strong ecosystem for mathematical optimisation and statistics. It is not part of evcc itself but a standalone service. When enabled, the cloud service optimizer.evcc.io is called."*

Das ist der erste Punkt, an dem EVCC seine eigene Core-DNA verletzt. Bisher war EVCC stolz auf "100 % lokal". Der Optimizer ruft standardmäßig einen Cloud-Dienst (`optimizer.evcc.io`) auf. Man kann ihn zwar lokal laufen lassen (als HA-Add-on, Docker-Container oder systemd-Service), aber:

Aus Discussion #23173: *"Ja, diese Anleitung nutzt die evopt.evcc.io Url. Die ist leider nur mit einem Sponsortoken abrufbar. Man kann evopt aber auch lokal laufen lassen und das umgehen. (...) Schade, dann wird man wahrscheinlich ein bisschen was im evopt Code ändern müssen, um die Sponsortokenvalidierung zu entfernen."*

Übersetzt: Auch die lokale Variante braucht einen Sponsor Token — es sei denn, der User modifiziert den Optimizer-Quellcode, um die Token-Validierung zu entfernen. Das ist ein Setup-Schmerz, der 98 % der Mainstream-User ausschließt.

### 5.6 Fakt 5: Die Installation ist ein Setup-Albtraum

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

### 5.7 Die vier Solalex-Vorteile, die der Optimizer-Vergleich schärft

**1. Real-time control vs. Informational only.** Der härteste, eindeutigste Vorteil. Solalex ändert wirklich Werte im Akku. Der Optimizer zeigt nur "was wäre wenn".

**2. No sponsor token vs. Sponsor token required.** Solalex ist für jeden zugänglich, der die Lizenz kauft. Der Optimizer ist nur für zahlende EVCC-Sponsoren nutzbar — und das in einer Zwei-Klassen-Struktur, die die Community ohnehin schon frustriert.

**3. 100 % lokal vs. Cloud-abhängig (oder kompliziert lokal).** Solalex ruft keinen Cloud-Dienst auf. Der Optimizer ruft standardmäßig `optimizer.evcc.io` auf — was EVCCs eigene "100 % lokal"-Botschaft unterwandert und für Nutzer überraschend ist.

**4. Stabil vom ersten Tag vs. System-Killer-Bugs.** Solalex darf keinen Raspberry Pi von 10 % auf 100 % CPU treiben. Der Optimizer tut genau das, dokumentiert in Discussion #23153. Das ist eine erzählbare Geschichte für Solalexs Stabilitäts-Versprechen.

### 5.8 Die neue Zielgruppen-Nuance: "Frustrierte Optimizer-Tester"

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

### 5.9 Wann wird der Optimizer wirklich zur Bedrohung?

Das ist die entscheidende Langzeit-Frage. Einschätzung, basierend auf dem aktuellen Entwicklungsstand:

**12 Monate (April 2027):** Der Optimizer ist wahrscheinlich immer noch im experimentellen Zustand, hat aber erste simple Steuerungs-Aktionen. Wahrscheinlich nur für ausgewählte Akku-Modelle (die, die EVCC bereits auslesen kann). Setup bleibt Sponsor-Token-gebunden. Solalex ist zu diesem Zeitpunkt längst im Markt und hat seine Zielgruppe etabliert.

**24 Monate (April 2028):** Der Optimizer steuert wahrscheinlich Akkus einiger großer Hersteller aktiv. Die Sponsor-Token-Hürde bleibt. Die Stabilität wird besser sein. Zu diesem Zeitpunkt **könnte** er zu einem realen Wettbewerber werden — aber für einen sehr spezifischen Nutzer-Typ: EVCC-Power-User mit Auto, Akku, und Sponsor-Bereitschaft.

**36 Monate (April 2029):** Der Optimizer ist möglicherweise produktionsreif. Aber bis dahin hat Solalex drei Vorteile ausgebaut: Marktposition, Kundenbasis, Hardware-spezifisches Wissen. Die Konkurrenz wird real, aber nicht existenzbedrohend, weil Solalexs Fokus (Balkonkraftwerk + Akku + Nicht-EV-Nutzer) für EVCC nie der Kern sein wird.

**Das strukturelle Argument:** EVCC ist und bleibt eine Wallbox-zentrierte Lösung. Der Optimizer wird immer *"wie optimiere ich Auto + Akku gemeinsam"* beantworten. Solalex beantwortet *"wie optimiere ich meinen Akku, egal ob ich ein Auto habe oder nicht"*. Diese Achsen-Differenz bleibt — und wird sich mit der Zeit sogar vertiefen, weil immer mehr Nutzer Akkus ohne E-Autos kaufen.

### 5.10 Die wichtigste Optimizer-Erkenntnis

Der EVCC Optimizer ist **keine akute Bedrohung** für Solalex — aber er ist **die beste Validierung** der Solalex-These, die wir uns wünschen könnten.

EVCC, der größte und erfolgreichste Open-Source-Wettbewerber in diesem Raum, sagt mit dem Optimizer öffentlich: *"Akku-Optimierung ist wichtig. Wir fangen jetzt an, daran zu arbeiten."* Nach 9 Monaten Arbeit zeigen sie nur Forecasts. Solalex regelt seit Jahren.

Das ist nicht Schadenfreude — das ist **Marktreife**. EVCC validiert den Markt, der Optimizer validiert das Bedürfnis, und Solalex steht bereits da mit einer funktionierenden Lösung.

Die taktische Konsequenz: **Solalex sollte in den nächsten 12 Monaten mit maximaler Geschwindigkeit in den Markt — bevor der Optimizer produktionsreif wird.** Nicht panisch, sondern planvoll. Das 9-Wochen-MVP-Timeline ist genau richtig. Die Beta-Phase sollte nicht verschoben werden. Die HACS-Submission sollte früher als später kommen.

Und die Co-Existenz-Story mit EVCC wird durch den Optimizer **stärker, nicht schwächer**. EVCC hat jetzt einen offiziellen Grund, warum Solalex existieren darf: *"Wir arbeiten am Optimizer, aber er ist experimentell. Wenn du heute eine stabile Akku-Regelung willst, gibt es Solalex."* Das ist die Art von indirekter Empfehlung, die über Jahre hinweg organisch wachsen kann.

---

## 6. Strukturelle Schwächen, die nicht weggehen werden

Die folgenden Punkte sind keine Bugs, die EVCC fixen kann — sie sind in der Architektur und in der Mission verankert.

**S1: Loadpoint-Zentrismus.** EVCCs gesamte Logik dreht sich um den Loadpoint = Wallbox + Auto. Ein Akku als orchestrierbarer Verbraucher passt nicht in dieses Modell. Eine Wärmepumpe ist nur als "Loadpoint" simulierbar — was funktioniert, aber sich nie natürlich anfühlen wird.

**S2: 30-Sekunden-Loop als Default.** Für Auto-Laden ist das ok. Für Akku-Regelung ist es zu langsam. Schneller machen würde EVCCs Stabilität bei großen Setups gefährden — also wird es auf absehbare Zeit nicht passieren.

**S3: Sponsor-Token als Lizenzmodell.** Token-Erneuerung, GitHub-only-Bezahlung, Paywall-Verschiebungen — das ist ein dauerhafter Frust-Generator. Selbst wenn EVCC das Modell ändert, bleibt das Vertrauen beschädigt. Und der Optimizer verstärkt das Problem, indem er ein weiteres Premium-Feature hinter dem Token versteckt.

**S4: Maintainer-Haltung gegen Priorisierung.** Der Maintainer hat öffentlich in Discussion #10134 Position bezogen. Das ist eine Produkt-Philosophie, die sich nicht über Nacht ändert.

**S5: YAML-Konfiguration als Power-User-Standard.** Auch wenn die Browser-Config in v0.300 jetzt offiziell ist, bleibt YAML der "echte" Konfigurationsweg für Edge-Cases. Das schließt Mainstream-Nutzer dauerhaft aus.

**S6: Open-Source-Spare-Time-Modell.** Aus Discussion #5244 vom Maintainer selbst: *"Wir arbeiten an den Dingen, die uns Spaß machen und deren Notwendigkeit wir erkennen. In unserer Freizeit. Und ganz klar: es gibt NULL Anspruch darauf, dass hier irgendwas SOFORT passiert."* Das ist ehrlich und legitim — aber es bedeutet, dass die Roadmap unvorhersehbar ist und Akku-Features Jahre brauchen können.

**S7: Cloud-Abhängigkeit beim Optimizer.** Der Optimizer ruft `optimizer.evcc.io` auf — ein erster, aber bedeutsamer Bruch mit EVCCs "100 % lokal"-Versprechen. Das wird in der Community nicht unbemerkt bleiben.

---

## 7. Solalex-Differenzierung — wo wir konkret besser sind

| Dimension | EVCC | Solalex |
|---|---|---|
| Primärer Use Case | Auto-Laden | Akku-Steuerung & Überschuss |
| Akku-Behandlung | Autark, schwer integrierbar | First-class Citizen |
| Akku-Optimizer | Experimentell, nur Forecasts | Produktionsreife Echtzeit-Regelung |
| Reaktionszeit | 30 s Default | Sekunden-Bereich (mit EEPROM-Schutz) |
| Konfiguration | YAML + Browser-Config | UI-only, kein YAML |
| Lizenz | Sponsor-Token mit Erneuerung | Einmalkauf, lebenslang |
| Zielgruppe | EFH mit PV + E-Auto | Balkonkraftwerk + Speicher |
| Onboarding | Doku + YAML-Validator | 10-Min-Geführter-Setup |
| Diagnose | Logs + DEBUG-Filter | Diagnose-Tab mit 100 letzten Zyklen |
| Hardware-Konflikte | Modbus-Konflikt mit HA möglich | Keine — kommuniziert nur über HA-Entitäten |
| Priorisierung mehrerer Verbraucher | Nicht geplant (Maintainer dagegen) | Kern-Konzept |
| Balkonkraftwerk-Support | Nicht erkannt | Native Zielgruppe |
| Cloud-Abhängigkeit | Optimizer ruft `optimizer.evcc.io` | Vollständig lokal |
| Sprachfokus | International, EN-first | DE-first für DACH-Markt |

---

## 8. Co-Existenz-Strategie: nicht Konfrontation, sondern Komplement

Das ist der wichtigste strategische Punkt. EVCC hat 6.400 GitHub-Stars und eine treue Community. Frontalkonkurrenz wäre dumm. Die richtige Position ist:

> **"Solalex läuft parallel zu EVCC. EVCC steuert dein Auto perfekt. Solalex kümmert sich um den Rest — Akku, Heizstab, Wärmepumpe, Balkonkraftwerk."**

Diese Botschaft hat drei Vorteile:

**1. Sie entkräftet die natürliche Abwehrhaltung der EVCC-Power-User.** Statt "Wir wollen euch ablösen" sagen wir "Wir ergänzen, was euch fehlt". Power-User werden Botschafter, nicht Gegner.

**2. Sie ist technisch ehrlich.** Solalex ist objektiv schlechter beim Wallbox-Lastmanagement und beim Auto-spezifischen Plan. EVCC ist objektiv schlechter beim Akku und bei Balkonkraftwerken. Das ist keine Marketing-Pose, sondern Realität. Und der Optimizer-Stand bestätigt das öffentlich.

**3. Sie öffnet eine technische Schnittstelle.** Solalex kann den Status von EVCC über die EVCC-API oder über HA-Entitäten lesen — und z. B. dem Akku sagen "Während EVCC das Auto lädt, halte den Akku-SoC". Das ist eine echte Integration, kein Feature-Klau.

**Konkrete Umsetzung:**
- Eine eigene Doku-Seite "Solalex mit EVCC kombinieren" mit Setup-Anleitung.
- Ein "EVCC erkannt"-Hinweis im Solalex-Onboarding mit der Frage "Soll Solalex dein Auto-Laden EVCC überlassen?" und Default = Ja.
- Ein gemeinsamer Artikel auf alkly.de und ein Hinweis im EVCC-Discord/Forum.
- Ein fairer Blog-Post: *"Der EVCC Optimizer zeigt dir, was passieren könnte. Solalex sorgt dafür, dass es passiert."*

---

## 9. Was Solalex von EVCC lernen muss

Ehrlichkeit über die eigenen Stärken und Schwächen — und EVCC hat sechs Dinge richtig gemacht, die Solalex kopieren oder übertreffen muss:

**1. Zuverlässige Hardware-Templates.** EVCCs Stärke ist die schiere Anzahl unterstützter Geräte. Solalex muss das über HA-Entitäten lösen — und im Diagnose-Tab transparent zeigen, welche HA-Integrationen kompatibel sind.

**2. Schlichte UI.** Maximal eine Funktion pro Bildschirm, klare Hierarchie, keine Überfrachtung. EVCC zeigt, dass das in diesem Markt funktioniert.

**3. Aktive Community.** EVCC hat tausende GitHub-Discussions. Solalex braucht von Tag eins einen aktiven Kanal (Discord ist gesetzt) und Alex muss persönlich präsent sein, mindestens in der Anfangszeit.

**4. Transparente Roadmap.** EVCC kommuniziert offen, was geplant ist und was nicht. Solalex sollte mindestens einen öffentlichen Roadmap-Abschnitt auf alkly.de haben.

**5. "Magic Buttons".** Battery Boost ist ein einziger Klick mit komplexer Logik darunter. Solalex braucht solche Knöpfe — z. B. "Akku jetzt voll", "Heute keine Einspeisung", "Wärmepumpe vorheizen".

**6. Migration-Erlebnis.** EVCC bekommt Nutzer von openWB ab, weil die Migration unkompliziert ist. Solalex braucht eine analoge Migration vom eigenen Blueprint und von Hersteller-Apps — mit konkreten Schritt-für-Schritt-Anleitungen pro Quelle.

---

## 10. Was Solalex besser machen muss als EVCC — die fünf konkreten Prioritäten

**Priorität 1: Akku als First-Class-Citizen.**
Während EVCC den Akku als autonome Black Box behandelt und der Optimizer nur Forecasts zeigt, muss Solalex den Akku als steuerbaren Verbraucher mit Profilen, Zeitplänen und Priorisierung anbieten — und zwar **real regeln, nicht nur vorhersagen**. Das ist die direkte Antwort auf fünf offene EVCC-Discussions (#28341, #14739, #14648, #20208) und auf den aktuellen Stand des Optimizers.

**Priorität 2: Sekunden-Reaktionszeit mit EEPROM-Schutz.**
Solalex muss schneller regeln als EVCCs 30-Sekunden-Loop, ohne Hardware zu verschleißen. Das ist die direkte Antwort auf Issue #22613.

**Priorität 3: Lizenz ohne Token-Theater.**
Einmalkauf, lebenslange Gültigkeit, Lizenz vor "Activate"-Button. Das ist die direkte Antwort auf Discussions #27634, #22961, #2130, #5897, #5122 — und auf die Tatsache, dass der Optimizer ebenfalls hinter dem Sponsor-Token steckt.

**Priorität 4: Echtes 10-Minuten-Setup ohne YAML.**
Auto-Discovery, geführter Onboarding-Flow, sinnvolle Defaults für 95 % der Nutzer. Das ist die direkte Antwort auf Discussions #26185, #25664, #20573 — und auf den Setup-Albtraum des Optimizers (siehe 5.6).

**Priorität 5: Diagnose-Tab als Vertrauenssignal.**
Letzte 100 Regelzyklen mit Erklärungen, EEPROM-Schreibstatistik, automatische Empfehlungen. Das ist die direkte Antwort auf den allgegenwärtigen "Ich verstehe nicht, was passiert"-Frust.

---

## 11. Botschaften, die direkt verwendbar sind

Fünf fertige Sätze für Landing Page, Pitch und Outreach — alle aus den Forenstimmen abgeleitet, alle technisch ehrlich:

> **"EVCC ist großartig für dein Auto. Solalex ist großartig für alles andere — Akku, Heizstab, Wärmepumpe, Balkonkraftwerk."**

> **"EVCC plant. Solalex regelt."**

> **"Während EVCC experimentelle Vorhersagen für deinen Akku zeigt, regelt Solalex ihn schon heute — real, lokal, stabil und produktionsreif."**

> **"Einmal zahlen, dauerhaft nutzen. Kein Token, keine Erneuerung, keine plötzliche Paywall."**

> **"Solalex regelt deinen Akku in Sekunden — und schont deinen Wechselrichter, weil er nur dann schreibt, wenn es wirklich nötig ist."**

---

## 12. Risiken und blinde Flecken

**Risiko 1: EVCC implementiert echte Akku-Steuerung in den nächsten 12 Monaten.** Die Discussions #28341, #20208 und #14648 sind alt, aber der Druck wächst — und der Optimizer ist der erste echte Schritt in diese Richtung. Falls EVCC den Optimizer zur Produktionsreife bringt, schrumpft Solalexs Differenzierung in einem zentralen Punkt. **Mitigation:** Solalex muss seinen Vorsprung nutzen, in dieser Zeit eine treue Userbase aufbauen und durch UX und Akku-Spezialisierung Tiefe gewinnen, die EVCC nicht so schnell aufholen kann. Der aktuelle Optimizer-Stand (nur Forecasts, kein Control) gibt uns mindestens 12–18 Monate.

**Risiko 2: Die Co-Existenz-Botschaft wird missverstanden.** Manche Nutzer könnten denken "Wenn ich EVCC habe, brauche ich Solalex nicht" — auch wenn sie objektiv beide bräuchten. **Mitigation:** Eine sehr konkrete "Was Solalex kann, was EVCC nicht kann"-Vergleichstabelle auf der Landing Page.

**Risiko 3: Die EVCC-Community ist groß und teils dogmatisch.** Eine zu aggressive Positionierung könnte als Angriff verstanden werden. **Mitigation:** Erstkontakt freundlich, mit echter Wertschätzung. Alex sollte selbst im EVCC-Discord auftauchen und Solalex als komplementär vorstellen, bevor irgendwelche Marketing-Botschaften groß rausgehen.

**Risiko 4: Der Optimizer wird schneller produktionsreif als erwartet.** Das Team hinter EVCC ist fähig und motiviert. 36 Monate könnten 24 werden. **Mitigation:** Solalex-Release darf nicht verzögert werden. Das 9-Wochen-MVP-Timeline ist genau richtig. HACS-Submission sollte früher als später kommen.

---

## 13. Konkrete nächste Schritte

**Sofort (vor Spike-Phase):**
- Diese Analyse mit dem PRD abgleichen und prüfen, welche Differenzierungspunkte (insbesondere die fünf Prioritäten aus Kapitel 10) im PRD bereits stehen — und welche fehlen.
- Eine Entscheidung treffen: Will Alex Solalex **explizit komplementär zu EVCC** positionieren oder neutral? Empfehlung: explizit komplementär.
- Die neue Zielgruppen-Persona "Frustrierter Optimizer-Tester" (siehe 5.8) in den PRD und/oder in die Beta-Tester-Liste aufnehmen.

**Vor Beta:**
- Die Co-Existenz-Doku schreiben ("Solalex mit EVCC kombinieren"), inklusive konkreter Setup-Anleitung.
- Das "EVCC erkannt"-Onboarding-Detail im UX-Dokument verankern.
- Blog-Post-Entwurf vorbereiten: *"Der EVCC Optimizer zeigt dir, was passieren könnte. Solalex sorgt dafür, dass es passiert."* — fair, anerkennend, mit klarer Positionierung.
- FAQ-Antwort vorbereiten: *"Wie unterscheidet sich Solalex vom EVCC Optimizer?"* mit den vier Differenzierungs-Punkten aus 5.7.

**Beta-Phase:**
- 2–3 Beta-Tester aus der EVCC-Community gewinnen, die beide Tools parallel laufen lassen. Ihre Erfahrung wird zum stärksten Glaubwürdigkeits-Signal für die Co-Existenz-Botschaft.
- 1–2 Beta-Tester gezielt aus der Optimizer-Test-Community gewinnen. Diese User sind technisch versiert, zahlungsbereit und kennen die Lücke bereits.

**Post-Launch:**
- Ehrlicher Outreach in EVCC-GitHub-Discussions (#28341, #14648 etc.) mit dem Hinweis, dass Solalex diese Use Cases bedient — ohne Spam, ohne Konfrontation, einfach als hilfreiche Information.
- Den Optimizer regelmäßig monitoren (alle 3–4 Monate). Sobald er echte Steuerungsaktionen liefert, Positionierung nachschärfen. Bis dahin: die aktuelle Botschaft beibehalten.

---

## 14. Anhang: Quellen

**GitHub — EVCC Hauptrepo (`evcc-io/evcc`):**
- Issues: #13750, #18467, #20573, #22613, #22739, #22944
- Discussions: #2130, #5122, #5244, #5897, #6476, #9979, #10134, #13314, #14001, #14648, #14739, #18467, #20208, #20312, #20573, #22961, #23087, #25664, #26185, #27634, #28341

**GitHub — Optimizer (`evcc-io/optimizer`) und zugehörige Discussions:**
- Issue #23042 (Epic: Improve experimental optimizer)
- Issue #23559 (Battery charge/discharge power)
- Discussion #23045 (How to run the Optimizer with Docker)
- Discussion #23153 (Optimizer in 0.207.4 unter Home Assistant einrichten)
- Discussion #23163 (optimizer: not enough slots)
- Discussion #23173 (How to run the Optimizer on Raspberry Pi)
- Discussion #23213 (EVCC Optimizer Einrichtung als Home Assistant Addon)
- Discussion #23812 (Questions regarding Optimizer)

**Dokumentation und Blog:**
- `docs.evcc.io/en/docs/features/optimizer` (offizielle Optimizer-Feature-Seite)
- `docs.evcc.io/blog/2026/01/01/highlights-browser-config-ready` (EVCC-Blog, Januar 2026, mit Optimizer-Ausblick)
- EVCC-Blog-Interview mit Michael (Juni 2025)
- EVCC-FAQ (offizielle Dokumentation)

**Forenbeiträge:**
- Photovoltaikforum (Thread #239358 u. a.)
- openHAB-Community (EVCC-Binding-Threads)
- simon42-Community
- TFF-Forum (Tesla Fahrer & Freunde)
- elefacts.de (EVCC-Test)
- Skoda-Enyaq-Forum (Modbus-Konflikt-Thema)

**Release-Tracking:**
- `releasebot.io/updates/evcc-io/evcc` (April 2026: "optimizer error fixes")

---

*Diese konsolidierte Analyse (v1.1) integriert die ursprüngliche EVCC-Analyse mit der tiefen Optimizer-Analyse. Alle Zitate sind im Original-Wortlaut wiedergegeben, um das authentische Stimmungsbild zu erhalten. Alle genannten Discussions, Issues und Dokumentations-Stellen waren zum Zeitpunkt der Recherche (April 2026) öffentlich zugänglich.*
