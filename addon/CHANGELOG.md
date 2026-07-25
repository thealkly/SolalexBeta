# Changelog — Soalex Add-on

Dieses Changelog betrifft nur das HA-Add-on-Artefakt (Container + Manifest).
Repo-weites Changelog: `/CHANGELOG.md`.

## 0.1.178 — 2026-07-25

Fokus: der Setup-Wizard wurde rundum erneuert — er scannt deine Anlage, kennt die gängigen Marken und zeigt unter jedem Auswahlfeld live, was Soalex gerade liest. Dazu eine Bug-Welle direkt aus euren Nacht-Diagnosen (Befehls-Schleifen, Neustart-Sprünge, Datenbank-Wachstum) und eine härtere Haus-Akku-Koordination.

### Neu

- **Der Setup-Wizard scannt deine Anlage und kennt deine Marke.** Beim Erst-Setup startet Soalex mit „Soalex hat in deinem Home Assistant gefunden … Passt das?" — Akku, Wechselrichter und Smart Meter werden vorerkannt, inklusive Marken-Erkennung (Marstek, Zendure, Anker, SolakonONE, Hoymiles, Growatt u. a.) mit passenden Vorbelegungen und einer marken-personalisierten Bestätigung. Die Auswahl läuft über übersichtliche Karten mit Piktogrammen statt langer Dropdowns, und eine Anlagen-Inventur („Was gehört zu deiner Anlage?") führt der Reihe nach durch alle Geräte. Wichtig dabei: Soalex filtert nichts mehr still weg — jeder aussortierte Sensor bleibt sichtbar mit einem Ein-Satz-Grund und ist trotzdem wählbar. Und wer lieber selbst auswählt: der manuelle Pfad ist an jeder Stelle einen Klick entfernt.
- **Live-Werte unter jedem Auswahlfeld im Setup.** Beim Einrichten zeigt Soalex jetzt direkt unter der Auswahl, was der gewählte Sensor gerade meldet: der Ladestand als „Dein Akku meldet gerade 67 %" (mit Warnung, wenn der Wert nicht nach einem Ladestand aussieht), die Lade-/Entladeleistung mit ihrem stellbaren Bereich („Gerade eingestellt: 0 W · stellbar 100–2400 W"), der Modus-Schalter mit seiner aktiven Option. Ein vertauschter Sensor, eine tote Entity oder ein falscher Schalter fällt damit im Setup-Moment auf — nicht erst im Betrieb als „Akku reagiert nicht". Der häufigste Beta-Stolperstein („die richtigen Sensoren auswählen") wird damit deutlich entschärft.
- **Ladestand-Grenzen gelten jetzt pro Akku.** Entlade- und Ladegrenze stellst du bei mehreren Akkus jetzt für jeden Akku einzeln ein (Einstellungen → Verhalten → Akku) — statt einer Grenze für die ganze Anlage.
- **Anker Solix & Co.: neue Stopp-Strategie „Kein Idle-Modus — Stopp schreibt 0 W".** Geräte, deren Modus-Auswahl keinen Ruhe-Modus kennt oder deren Steuer-Felder nur im Freigabe-Modus existieren (Anker Solarbank 3, Solix Max AC via Modbus), stoppen jetzt sauber über einen 0-W-Befehl, ohne den Betriebsmodus zu verlassen. Der Funktionstest entzieht sich dabei nicht mehr selbst die Freigabe (vorher: Timeout-Hänger im Setup), und beim Nachbearbeiten eines Akkus bleiben gespeicherte Modus-Optionen sichtbar, auch wenn die Integration sie gerade nicht liefert.
- **Diagnose-Paket deutlich ausgebaut.** Der Export enthält jetzt eine Kurz-Historie der wichtigsten Sensoren, Koordinations-Ereignisse als eigene Zeitreihe und pro Regel-Eintrag mehr Kontext (Sensor-Alter, Ladestand zum Zeitpunkt der Entscheidung). Support-Analysen brauchen damit deutlich weniger Rückfragen.

### Behoben

- **Abgelehnte Befehle brachten den Regler aus dem Takt — Schluss mit nächtlichen Befehls-Schleifen.** Schlug die Hardware-Bestätigung eines gelandeten Befehls fehl, plante Soalex intern vom veralteten Stand weiter — daraus konnten sich nachts stundenlange Wiederhol-Schleifen aufbauen (real gemessen: 681 vergebliche 0-W-Befehle in einer Nacht). Jetzt bleibt der interne Arbeitspunkt auch bei fehlgeschlagener Bestätigung synchron; die Schleife stirbt nach dem ersten Versuch.
- **Neustart startet entlade-nur-Wechselrichter am echten Limit statt bei „0 W angenommen".** Nach einem Add-on-Neustart kannte Soalex das aktuelle Limit eines entlade-nur-Wechselrichters (Trucki, Hoymiles-Limit) nicht und regelte vom falschen Startpunkt los. Jetzt liest Soalex beim Start das anliegende Limit und setzt dort sanft fort.
- **Setup-Wizard blockt Ausgangs-Felder als Ladeleistung.** Wer versehentlich eine Ausgangs-Leistungs-Number (z. B. `…_set_output`) als Ladeleistung wählte, bekam einen Akku, der nie lud — jetzt erklärt der Wizard den Fehler direkt am Feld und verweist auf die Topologie „Nur Ausgangs-Leistung steuerbar".
- **Akku-Leistungs-Sensor-Vorschlag greift nicht mehr zu PV-String- oder Gesamt-Sensoren.** Die Auto-Erkennung schlug in manchen Setups einen PV-String- oder Summen-Sensor als Akku-Leistung vor — mit der Folge, dass der „Akku reagiert nicht"-Check gegen den falschen Sensor prüfte.
- **Mehr-Akku-Setups: falsche „Rollen-Kollision"-Warnung entfernt.** Bei mehreren Akkus warnte das Log fälschlich vor doppelten Rollen — mehrere Akkus sind normal und melden jetzt nichts mehr.
- **Die Datenbank wächst nicht mehr unbegrenzt.** Routine-Einträge („nichts zu tun") sammelten sich mit ~20.000 Zeilen pro Tag; sie werden jetzt nach 7 Tagen aufgeräumt (beim ersten Lauf: ~69.000 Zeilen). Alle relevanten Einträge — Befehle, Schutz-Ereignisse, Messungen — bleiben wie bisher 30 Tage erhalten.
- **Ein hängender Befehl konnte die Steuerung eines Geräts dauerhaft blockieren.** Brach ein Schreibbefehl an ungünstiger Stelle ab (z. B. Verbindungs-Abriss mitten im Versand), blieb eine interne Sperre für dieses Gerät hängen — jeder weitere Befehl inklusive der Sicherheits-Stopps wartete dann für immer; nur ein Neustart half. Die Sperre wird jetzt in jedem Fall wieder freigegeben.
- **Nacht-Fenster stoppt keine laufende Ladung mehr.** Eine fast fertig eingeregelte Ladung nahe der Null-Linie wurde vom Entlade-Zeitfenster fälschlich als Entladung eingestuft und zyklisch auf 0 gestellt. Das Fenster unterscheidet jetzt sauber anhand des Arbeitspunkts.
- **Fehlermeldungen bei Befehls-Abbrüchen sind jetzt lesbar.** Reagierte die Hardware-Integration nicht rechtzeitig (Timeout), stand im Verlauf bisher eine leere Meldung („Vorbereitung fehlgeschlagen: …: "). Jetzt steht die Ursache dabei.
- **Zweit-Akku-Koordination: drei Feinschliffe aus dem Code-Review.** Die „Akku hilft Akku"-Umladung (experimentell) respektiert jetzt auch den Haus-Akku-Vorrang (sie startet nicht, während dein Fremd-Akku lädt) und fährt nach einer Verbindungs-Störung sanft statt mit einem Sprung wieder an. Die Rückkehr an den alten Arbeitspunkt nach einer Haus-Akku-Pause wird intern nicht mehr doppelt gezählt.
- **Interne Zeitmessung der Befehls-Bestätigung korrigiert.** Die Frische-Prüfung der Hardware-Rückmeldung startete bisher schon vor dem eigentlichen Versand — bei viel gleichzeitigem Verkehr konnten dadurch korrekte Bestätigungen als „zu alt" verworfen werden.

### Verbessert

- **Haus-Akku-Koordination: Eskalations-Sperre gegen „Aufschaukeln".** Ein pulsender Fremd-Akku (z. B. SENEC-Entlade-Stöße im Minuten-Takt) konnte mit Soalex eine Pumpe bilden — das Netz pendelte mit mehreren Kilowatt hin und her. Erkennt Soalex jetzt zwei Konflikt-Episoden binnen fünf Minuten, hält es den Arbeitspunkt, statt weiter zu erhöhen, bis fünf Minuten Ruhe herrschen. Einzelne kurze Blips verhalten sich exakt wie bisher (reduzieren statt stoppen, danach sofort weiter am alten Arbeitspunkt).
- **Mehr-Akku-Zuteilung flattert nicht mehr bei Ladestand-Gleichstand.** Standen zwei Akkus auf demselben Ladestand, wechselte die Zuteilung bei jedem Zehntel-Prozent-Flicker das führende Gerät — beide fuhren Dauer-Rampen. Ein Akku übernimmt die Führung jetzt erst ab 3 Prozentpunkten Vorsprung.

## 0.1.177 — 2026-07-17

Fokus: die größte Fix-Welle der Beta bisher — direkt aus euren Diagnose-Paketen vom 12.–16. Juli. Mehr-Akku-Setups verteilen jetzt fair, kW-Zähler funktionieren, und wenn ein anderes System dazwischenfunkt, sagt Soalex es dir offen.

### Behoben

- **Mehr-Akku-Setups entladen jetzt den vollsten Akku zuerst.** Bisher gewann bei mehreren Akkus strukturell immer derselbe — er wurde jede Nacht bis zur Untergrenze leergefahren, während die anderen voll blieben („er nimmt immer nur den schnellsten Akku"). Die Balance-Regel hat die Ladestände schlicht nie zu sehen bekommen. Jetzt gilt: Entladen bevorzugt den vollsten, Laden den leersten Akku — die Stände gleichen sich über den Tag an.
- **Zähler, die in kW melden, werden korrekt umgerechnet.** Meldet dein Smart Meter (z. B. Shelly Pro 3EM je nach Firmware) in Kilowatt statt Watt, sah Soalex bisher dauerhaft ~0 W und blieb komplett untätig. Jetzt rechnet Soalex die Einheit auf allen Regel-Pfaden um.
- **Zähler- oder Sensor-Wechsel greift sofort.** Nach dem Tausch der Smart-Meter-Entity (z. B. weil Home Assistant sie umbenannt hat) lief die Regelung bis zum nächsten Add-on-Neustart ins Leere. Jetzt wird die neue Entity sofort live geschaltet.
- **Ladestand-„Bouncing" an der Untergrenze gestoppt.** Bei wenig Sonne wurde der Akku 1 % über die Untergrenze geladen und sofort wieder entladen — im schlimmsten Fall über 100 Richtungswechsel am Tag. Nach Erreichen der Untergrenze wartet Soalex jetzt, bis der Ladestand wieder 2 Prozentpunkte darüber liegt.
- **„Dein Stromnetz schwankt gerade stark" klebt nicht mehr den ganzen Tag.** Die Meldung bewertete bisher den ganzen Tag kumulativ und blieb ab Mittag oft dauerhaft stehen; jetzt zählt ein gleitendes 10-Minuten-Fenster.
- **Pausieren blockiert nicht mehr mit „außerhalb der Hardware-Grenzen".** Beim Pausieren eines entlade-nur-Wechselrichters (z. B. Growatt NOAH / Hoymiles-Limit) lief das Herunterfahren gegen die Bereichs-Prüfung und blieb auf dem letzten Wert stehen. Jetzt fährt die Pause sauber auf 0.
- **Schlafende Wechselrichter erzeugen nachts keine Befehls-Schleifen mehr.** Geht ein PV-Wechselrichter nachts in den Schlafmodus, wiederholte Soalex die 0-W-Rücknahme im Sekunden-Takt (hunderte vergebliche Befehle pro Nacht). Jetzt erkennt Soalex die Situation und wartet ruhig.

### Neu

- **Fremd-Steuerung wird erkannt und gemeldet.** Überschreibt ein anderes System deine Soll-Werte (Zendure-HEMS/App-Modus, OpenDTU-OnBattery-DPL, Geräte-interner Energiesparplan), verlor Soalex bisher still jeden Befehl — und du hast nur gesehen, dass „nichts passiert". Jetzt erkennt Soalex das Muster und meldet es offen als Hinweis. Grundsatz bleibt: pro Anlage darf nur **eine** Nulleinspeisungs-Regelung aktiv sein.
- **Ziel-Netzbezug ist jetzt eine Anlagen-Einstellung.** „Wie viel Netzbezug ist okay?" gilt für deinen ganzen Haushalt und lebt jetzt oben in Einstellungen → Verhalten → „Deine Anlage" — statt versteckt pro Akku.

### Verbessert

- **Haus-Akku-Koordination: reduzieren statt stoppen.** Springt dein zweiter Haus-Akku kurz an (z. B. SENEC an der Wolkenkante), kappt Soalex die Ladung deines Akkus jetzt nur um genau diesen Betrag, statt sie komplett auf 0 zu schneiden — und setzt danach sofort am alten Arbeitspunkt fort statt minutenlang neu heranzutasten. Weniger Relais-Zyklen, keine verlorene halbe Stunde Ladung pro Wolke.
- **Standard-Profil reagiert flotter auf Lastwechsel.** Das Regelungs-Profil steuert jetzt auch die Reaktions-Geschwindigkeit; „Standard" regelt Lastsprünge (Wasserkocher aus → Überschuss) spürbar schneller aus als bisher. Wem das zu lebhaft ist: Profil „Schonend" entspricht dem bisherigen Tempo — ein Klick in Einstellungen → Verhalten → Akku.
- **Ein Akku, der zeitweise nicht liefert, kommt schneller zurück.** Die Sperre für nicht-liefernde Akkus prüft jetzt in ruhiger Kadenz neu, statt auf veralteter Beweislage dauerhaft zu blockieren.
- **Diagnose-Export zeigt die Koordinations-Sensoren.** Haus-Akku-, Wallbox- und Überschuss-Verbraucher-Zustand liegen jetzt im Diagnose-Paket — Support-Analysen brauchen keine Rückfragen mehr dazu.
- **Stille Vorarbeit fürs Haus-Modell.** Soalex zeichnet Strompreis-Historie auf und macht die intern gelernten Anlagen-Werte in der Diagnose sichtbar. Kein Einfluss auf die Regelung.

## 0.1.176 — 2026-07-11

Fokus: die „Überschuss nutzen statt einspeisen"-Funktion kann jetzt beliebige Geräte schalten — nicht nur eine Klimaanlage.

### Neu

- **Überschuss-Verbraucher: jetzt Schalter, Input-Boolean oder Automation statt nur Klima (experimentell).** Ist dein Akku voll und es ginge trotzdem Strom ins Netz, konnte Soalex bisher nur eine Klimaanlage einschalten. Jetzt kannst du dafür genauso einen normalen Schalter (`switch`), ein Input-Boolean oder eine Automation wählen — Soalex schaltet das Gerät bei Überschuss ein und wieder aus, sobald der Überschuss wegfällt oder der Akku nicht mehr voll ist. **So richtest du es ein:** Einstellungen → Verhalten → Haushalts-Regeln → „Überschuss nutzen statt einspeisen" → dein Gerät wählen. Standardmäßig aus; Laden und Nulleinspeisung laufen normal weiter. Hinweis: Eine gewählte Automation wird bei Überschuss aktiviert und bei Wegfall wieder deaktiviert — trag also keine Automation ein, die ohnehin dauerhaft aktiv bleiben soll.

## 0.1.175 — 2026-07-10

Fokus: ein Datenverlust-Bug beim Erweitern eines Mehr-Akku-Setups ist geschlossen, neue oder getauschte Akkus werden ab jetzt vor der Live-Steuerung erst geprüft, und ein Datenbank-Fix macht deine Diagnose-Historie zuverlässiger.

### Neu

- **Neuer Akku oder Hardware-Tausch: erst ein Funktionstest, dann Live-Steuerung.** Fügst du deiner Anlage einen weiteren Akku hinzu oder tauschst du unter „Akku ändern" die Hardware aus, steuert Soalex die neue Einheit jetzt nicht mehr sofort live mit. Sie bleibt inaktiv, bis ein gezielter Funktionstest bestätigt, dass Verbindung und Rückmeldung stimmen — die App leitet dich dafür automatisch zum passenden Test. So gehen keine Befehle unbemerkt an eine falsch konfigurierte oder gerade nicht erreichbare Einheit; nach bestandenem Test übernimmt Soalex den Akku zuverlässig in die Mehr-Akku-Regelung.

### Verbessert

- **Weniger Fehlalarme „Akku reagiert nicht" bei Cloud-Akkus.** Die Erkennung, ob ein Akku auf einen Befehl tatsächlich mit Leistung reagiert, wartet jetzt automatisch länger bei Akkus, deren Sensor sich seltener meldet (z. B. Zendure mit Melde-Lücken von rund 35 Sekunden) — schnelle, lokal angebundene Akkus werden weiterhin genauso zügig erkannt.
- **Automatische Schutz-Pause hebt sich nicht mehr zu früh selbst auf.** Pausierte Soalex einen nicht reagierenden Akku automatisch, konnte sich die Pause bisher innerhalb von Sekundenbruchteilen wieder selbst aufheben, sobald der Ladestand kurz unauffällig aussah — ohne dass das eigentliche Problem behoben war. Jetzt vergehen mindestens 5 Minuten, bevor sich eine automatische Pause selbst wieder lösen kann.
- **Verlauf bleibt beim Geräte-Entfernen erhalten.** Entfernst du einen Akku oder Wechselrichter, sichert Soalex jetzt dessen komplette Diagnose-Historie (Regel-Zyklen, Latenz-Messungen, Reaktionstests) statt sie zu löschen. Ein Hardware-Tausch mit gleichbleibender Entity-ID behält außerdem deine bisherigen Verhalten-Einstellungen (z. B. Maximal-Leistung, Toleranzbereich).
- **Interne Vorarbeit an einem Haus-Modell.** Soalex beobachtet jetzt still im Hintergrund deine Anlage genauer — Akku-Kapazität und Wirkungsgrad, dein typisches Lastprofil über den Tag, die Treffsicherheit deiner PV-Prognose. Für dich noch nicht sichtbar und ohne Einfluss auf die aktuelle Regelung; legt die Basis für genauere Prognosen und mehr Automatik in kommenden Versionen.

### Behoben

- **Akku-Setup erweitern konnte bestehende Akku-Pools samt Verlauf löschen.** Bei internen Tests des neuen Funktionstest-Schritts (siehe oben) zeigte sich: das Hinzufügen eines weiteren Akkus zu einem laufenden Mehr-Akku-Setup konnte alle bisherigen Akku-Pools inklusive mehrtägiger Diagnose-Historie löschen. Betraf ausschließlich diese interne Testversion, nie ein veröffentlichtes Release. Die ineinandergreifenden Ursachen im Erweiterungs-Ablauf sind jetzt geschlossen.
- **Lücken in der Diagnose-Historie durch Datenbank-Sperren.** Bei viel gleichzeitigem Schreibzugriff auf die Datenbank (z. B. im Mehr-Akku-Betrieb) konnten Regel-Zyklen und Diagnose-Einträge verloren gehen (Fehler „database is locked") — in einem beobachteten Fall über die Hälfte der Einträge an einem Tag. Betraf die Diagnose-/Verlaufs-Anzeige, nicht die eigentliche Steuerung deiner Hardware. Ursache (Reihenfolge zweier Datenbank-Einstellungen beim Verbindungsaufbau) behoben.

## 0.1.174 — 2026-07-07

Fokus: neue Haushalts-Regeln fürs Zusammenspiel mehrerer Geräte — Soalex kennt jetzt einen zweiten, unabhängigen Haus-Akku und lässt volle Akkus die leeren mitversorgen. Dazu ein handfester Zuverlässigkeits-Fix im Mehr-Akku-Betrieb und ein direkterer Einstellungs-Bildschirm.

### Neu

- **Koordination mit einem zweiten Haus-Akku.** Hast du zusätzlich zu deinem Soalex-Akku einen großen Haus-Akku mit eigener Nulleinspeisungs-Regelung (z. B. Huawei, Fronius, Sonnen, E3/DC), arbeitet Soalex jetzt nie dagegen: Dein Soalex-Akku lädt nicht, während der Haus-Akku entlädt, und entlädt nicht, während der Haus-Akku lädt — sonst schiebt ein Akku Strom in den anderen (teure Doppel-Wandlung). **So richtest du es ein:** Einstellungen → Verhalten → Haushalts-Regeln → „Zweiter Haus-Akku mit eigener Regelung" → dort den Leistungssensor deines Haus-Akkus wählen (positiv = entlädt). Zeigt der Sensor Laden/Entladen vertauscht an, gibt's eine „Vorzeichen umkehren"-Checkbox darunter. Ohne gewählten Sensor ist die Regel aus — für Setups ohne zweiten Haus-Akku ändert sich nichts.
- **Akkus laden sich gegenseitig (Überschuss-Weitergabe).** Hast du mehrere Akkus und einer ist voll, während noch Strom ins Netz ginge, gibt Soalex den Überschuss jetzt an deine noch leeren Akkus weiter, statt ihn einzuspeisen. **So richtest du es ein:** Einstellungen → Verhalten → Haushalts-Regeln → „Überschuss an andere Akkus weitergeben" → Kästchen „Akkus laden sich gegenseitig" anhaken. Standardmäßig aus. Nur relevant, wenn du mehr als einen Akku hast; Geräte, die das selbst können (Zendure, Anker), sind davon unabhängig.
- **Neuer Onboarding-Schritt für reine PV-Wechselrichter.** Beim Ersteinrichten ist der PV-Wechselrichter jetzt ein eigener Geräte-Typ im Setup-Wizard mit einer klaren Bestätigung der Topologie. Betrifft nur neue Setups — bestehende bleiben unverändert.
- **Einstellungen speichern sofort — kein „Speichern"-Button mehr.** Jedes Feld unter Einstellungen → Verhalten speichert sich jetzt automatisch, sobald du es änderst. Die Bestätigung siehst du direkt am Feld: ein kurzes grünes Aufleuchten plus ein „Gespeichert"-Hinweis für 5 Sekunden. Kein Vergessen des Speichern-Klicks mehr, keine verworfenen Änderungen beim Verlassen der Seite.

### Verbessert

- **Wallbox-Entladesperre: der Auslöser-Sensor ist jetzt vollständig wählbar.** Die Sensor-Auswahl für „Akku nicht entladen, während die Wallbox lädt" zeigte bisher keine `binary_sensor`- oder `input_boolean`-Entitäten — genau dort liegt aber typischerweise der „lädt gerade"-Schalter von EVCC & Co. (z. B. `binary_sensor.evcc_lp1_charging`). Jetzt gibt es dort — wie im Setup-Wizard — einen „Sensor nicht dabei? Alle anzeigen"-Button, der auch diese Entitäten zeigt.
- Deutlicher sichtbares Speichern-Feedback in den Einstellungen (größere, kontrastreichere Bestätigungs-Chips).

### Behoben

- **Mehr-Akku-Betrieb: ein nicht mehr reagierender Akku bekam trotzdem seinen vollen Anteil zugeteilt.** Wurde ein Akku über Nacht durch eine Zeitüberschreitung, abgelehnte Befehle oder einen toten Sensor unbrauchbar, teilte Soalex ihm trotzdem weiter seinen vollen Anteil an Lade-/Entlade-Leistung zu, statt ihn an einen gesunden Akku weiterzugeben. In einem beobachteten Fall kostete das rund 2,5 kWh unnötigen Netzbezug in einer einzigen Nacht, obwohl ein gesunder, voller Akku bereitstand. Soalex erkennt einen nicht liefernden Akku jetzt zuverlässig und gibt seinen Anteil an einen funktionierenden Akku weiter.

## 0.1.173 — 2026-07-03

Großes Update mit dem Fokus auf reine PV-Wechselrichter, mehr Ruhe im Mehr-Akku-Betrieb und einem ersten Blick auf die Verbraucher-Steuerung.

### Neu

- **Reine PV-Wechselrichter & entlade-nur-Speicher.** Wechselrichter, bei denen sich nur die Ausgangsleistung steuern lässt (z. B. Trucki2Shelly, Balkon-PV mit Speicher davor), laufen jetzt über denselben ruhigen Steuerpfad wie ein Akku — kein eigener, zickiger Wechselrichter-Regler mehr. Beim Einrichten gibt es dafür die neue Auswahl „Nur Ausgangs-Leistung steuerbar".
- **Überschuss-Verbraucher (experimentell).** Ist dein Akku voll und es bleibt Überschuss übrig, kann Soalex jetzt einen Verbraucher (z. B. ein Klimagerät) an- und ausschalten, statt den Strom ins Netz zu schicken. Bewusst zurückhaltend gehalten — erster Schritt, Feedback willkommen.

### Verbessert

- **Ruhigerer Mehr-Akku-Betrieb.** Mehrere Fixes gegen Rand-Effekte im Pool: keine verbotene Einspeisung mehr am Morgen, kein gleichzeitiges Laden und Entladen zweier Akkus, saubere Ladestand-Grenzen über die ganze Anlage.
- **Genaueres Steuertempo.** Soalex misst die Reaktionszeit deiner Hardware jetzt zuverlässiger und passt sein Tempo automatisch an — ohne dass du etwas einstellen musst.
- **Weniger Fehlalarme bei PV-Wechselrichtern.** Ein zeitweise nicht verfügbarer Rückmelde-Sensor (nachts, bei Wolken) friert die Steuerung nicht mehr ein.

### Behoben

- Absturz beim Schalten eines Klimageräts im neuen Verbraucher-Modul.
- Einrichtungs- und Anzeige-Feinschliff bei PV-Wechselrichter-Setups.

## 0.1.172 — 2026-06-27

Kleines, fokussiertes Update auf das große Multi-Akku-Release. Headline: **Soalex entlädt deinen Akku nicht mehr, während deine Wallbox lädt.**

### Neu

- **Entladesperre bei Wallbox-/EVCC-Ladung.** Lädt gerade dein Auto, hält Soalex den Akku zurück, statt ihn ins Auto leerzuräumen — der Akku-Strom soll nicht den Umweg über die Wallbox nehmen. Du hinterlegst dafür deine Wallbox bzw. EVCC in Settings → Verhalten unter den Haushalts-Regeln (gilt für deine ganze Anlage). Laden bleibt immer erlaubt: Überschuss über den Wallbox-Bedarf hinaus lädt deinen Akku ganz normal weiter.

### Verbessert

- **Interne Vorarbeit** für genauere Fehler-Ursachen pro Akku im Mehr-Akku-Betrieb (für dich noch nicht sichtbar, legt die Basis für klarere Diagnose-Hinweise).

## 0.1.171 — 2026-06-26

Das bisher größte Beta-Update. Headline: **Soalex steuert jetzt mehrere Akkus gleichzeitig.** Dazu Steuerung **ohne Ladestand-Sensor**, ein deutlich einfacherer Reaktionstest und viele Stabilitäts-Fixes aus eurem Beta-Feedback.

### Neu

- **Mehrere Akkus parallel (Multi-Akku).** Soalex verwaltet jetzt mehrere Akku-Pools zugleich, verteilt Laden und Entladen sinnvoll über alle und lässt jeden Akku einzeln einstellen, ändern und hinzufügen.
- **Akku ohne Ladestand-Sensor steuern.** Setups ohne auslesbaren SoC (CAN-/BMS-Bridge, ESPHome) können den Akku jetzt trotzdem regeln lassen — Soalex arbeitet über die Leistung, „voll" und „leer" erkennt die Hardware selbst.
- **Entlade-nur-Wechselrichter** (z. B. Trucki2Shelly) lassen sich jetzt im Wizard einrichten — auch wenn der Akku dahinter nicht auslesbar ist.
- **Entlade-Zeitfenster für den ganzen Haushalt:** das Nacht-Fenster gilt jetzt global für alle Akkus statt pro Gerät.
- **Wechselrichter nachträglich hinzufügen:** ein WR lässt sich zu einem bestehenden Akku-Setup ergänzen.

### Verbessert

- **Einfacherer Reaktionstest:** misst nur noch, wie schnell deine Hardware antwortet, und schlägt daraus die passende Pause vor — kein verwirrendes Tuning mehr.
- **Langsame Cloud-Hardware** wird nicht mehr als Fehler gewertet: ein verzögertes Kommando heißt jetzt „Hardware antwortet langsam" statt Fail-Safe.
- **Live-Screen:** die WR-Limit-Kachel zeigt den tatsächlich gesetzten Wert statt des rohen HA-Zustands.
- **Akku-Schrittweite** ist jetzt in Prozent (%) einstellbar, mit Hilfetexten in Settings → Verhalten.
- **Diagnose-Export** trägt eine stabile Installations-ID — einfacherer Beta-Support.

### Behoben

- **Nächtliche Akku-Entladung ins Netz** korrigiert (Schrittweite von der Hardware-Quantisierung entkoppelt).
- **Marstek im Standby** wird zuverlässig wieder aufgeweckt.
- **Mehr-Akku-Robustheit:** ein toter Pool verdeckt nicht mehr den Status gesunder Pools, ein eingefrorener Marstek-Status wird automatisch erkannt, und globales Speichern löscht keine fremden Akku-Pools mehr.
- **Cloud-Akku-Fehlalarm nachts** behoben — der Wirkungs-Check greift erst ab 100 W Sollwert.

## 0.1.170 — 2026-06-15

- chore(bmad): finalize 3.49/3.50 review and 3.51 planning
- fix(controller): Status-Check-Reaktivierung, Commit-Takt-Epoch-Divergenz & setpoint_echo-Trailing-Power (Diag 2026-06-14)
- feat(ui): Story 3.50 — opt-in "Reaktionsstärke" (β) im Akku-Profi-Tier mit Live-Vorschau
- fix(ui): Story 3.49 — min_step raus aus Regelungs-Profil-Bundle, Frisch=Standard, ehrliches Wording

## 0.1.169 — 2026-06-13

- docs(qa): Tagesanalyse 2026-06-12 — Marstek Venus, Story-3.47-Inkrement-Regler erster Tag
- feat(controller): Story 3.48 — Auto-Commit-Takt via sign-gefiltertem T3-Grid-Response-Schätzer

## 0.1.168 — 2026-06-12

- feat(controller): Story 3.47 — Inkrement-Regler ersetzt das Positions-PI im Speicher-Pfad
- fix(addon): config.yaml in den Frontend-Builder-Stage kopieren — Über-Soalex-Version zeigte "dev" statt der Release-Version
- fix(tests): mypy-strict Tuple-Vergleiche im Story-3.46-Test entpacken (CI fährt mypy ., nicht nur src)

## 0.1.167 — 2026-06-11

- fix(controller): PI integriert Commit-Intervall statt 1 s am un-gefrorenen Tick (Story 3.46) — Arbeitspunkt-Gedächtnis-Fix + Ship-Gate-Materialitäts-Guard

## 0.1.166 — 2026-06-10

- feat: UI-Jargon-Wording-Pass (Story 5.18) + rate_limit_freeze Send-Epoch-Hotfix (Story 3.45)

## 0.1.165 — 2026-06-10

- fix(settings): stale Profil-Picker-Texte — drei statt vier Schwellen, Verb-Pakt im Standard-Hint

## 0.1.164 — 2026-06-10

- feat(replay): ZT-8 Ship-Gate — Delta-Gate über die Pflicht-Bundles + Doku-Abschluss (Story 3.42)
- feat(controller): Write-Heartbeat gegen eingefrorenen Setpoint + Tote-Nacht-Hero (Story 3.44, Phase-0 Pre-Beta-Blocker)
- feat(migration): ZT-7 pi_tuning-Reset (non-manual, Akku-only) + Dead-Night-Gamification-Gate (Story 3.41)
- feat(settings): ZT-6 Settings-Verhalten-Umbau — read-only Live-θ-Fakt + Profi-Schublade + Dead-Night-Guardrail (Story 3.40)
- feat(wizard): ZT-5 Wizard-Cut — alle Tuning-Karten raus (Story 3.39, C-cut-all)
- feat(controller): ZT-4 Online-Oscillation-Detector (Story 3.38)
- feat(controller): ZT-3 Live-Ti-Floor + θ_cadence-Smoothing (Story 3.37)
- fix(controller): Story-3.36-Review-Patches — multi_entity-Discharge-θ-Fold + fail-loud kp_floor + Doku-Sync
- feat(controller): ZT-2 K-freier θ_kp-Kp-Dämpfer (Story 3.36) + ZT-Reihe-WIP
- fix(setup): input_number-Helfer ohne Watt-Einheit im WR-Limit/Setpoint-Picker selektierbar
- fix(wizard): Hardware-Edit-Zurück führt ins hydrierte Edit-Formular statt leeren Wizard
- docs(story): 3.33 Anti-Oszillation Akku-PI (Kadenz-Ti-Floor live + delay-aware Floor)

## 0.1.163 — 2026-06-07

- fix(reaktionstest): Magnitude-Readback für mode_switch_single via geteiltem Helfer

## 0.1.162 — 2026-06-07

- fix(live): Cycle-Stream sagt nur bei echtem Write „Soalex setzt"
- feat(5.17): Wizard-Wording-Pass — Glossar-Mode-Labels, Freigabe-Schalter, Bestätigt, Reaktionstest-Wording

## 0.1.161 — 2026-06-06

- fix(rebrand): Beta-Repo-URL korrigieren + Versions-Label/Doku/CSS-Nachzügler

## 0.1.160 — 2026-06-06

- chore(rebrand): Solalex → Soalex (Package, Add-on-Slug, Release, UI, Docs)

## 0.1.159 — 2026-06-05

- fix(3.31): Code-Review-Follow-up-Patches (10 Findings)

## 0.1.158 — 2026-06-05

- fix(build): .dockerignore — hermetischer Frontend-Build

## 0.1.157 — 2026-06-05

- feat(3.32 F+T8): Funktionstest spiegelt Live-Pfad + Frontend-Klartext + Ti-Floor-Gate
- feat(3.32 E): Ti-Floor an die gemessene Smart-Meter-Cadence (AC 5)
- feat(3.32 A+B): setpoint_echo-Default der Akku-Klasse + Graceful-Demote-before-Latch
- fix(3.32 C+D): Ramp-Down-Hart-Timeout + optimistischer Cache + Reconnect-Subscribe-Retry
- feat(4.13): Offline-Replay-Harness gegen Beta-Diag-Bundles

## 0.1.156 — 2026-06-01

- feat: Huawei LUNA 2000 SoC-Sensor-Detection (deutsche Benennung)
- fix(2.11): Wizard canSave + Idle-Picker akzeptieren Betriebsmodus-Stop

## 0.1.155 — 2026-06-01

- feat(2.11,3.31): Anker-AC-Max-Betriebsmodus-Idle + Hardware-Instabilitäts-Outer-Limits

## 0.1.154 — 2026-05-30

- feat(5.15): T2-Latenz-Insights in Welcome-Card und Tuning-Pfad
- fix(2.1a): Akku-Power-Sensor-Auto-Detect — AC-Fallback eng halten, Warn-Log dazu
- fix(2.1a): Pre-Flight idempotent — kein switch.turn_on auf bereits aktiven Switch

## 0.1.153 — 2026-05-29

- feat(5.16): Onboarding Beta-Feedback Quick-Wins
- fix(running): Confidence-Pille ohne „Vermessen", ohne Emoji

## 0.1.152 — 2026-05-28

- feat(7.6): Beta-Verfall 30 Tage seit Build

## 0.1.151 — 2026-05-28

- chore(5.15): Story-Artefakt, Sprint-Status und API-Types nachgezogen
- fix(wizard): Zendure Auto-Detect — outputlimit, kein Permission, _soclevel
- fix(running): Confidence-Pill auf kanonische #/settings/verhalten-Route
- fix(disclaimer): zeige echte Hardware-Class-Defaults statt hardcoded Werte
- feat(diagnose): Latenz-Tabelle T1/T2/T3 in Klartext

## 0.1.150 — 2026-05-27

- feat(5.10): Steckbrief-Vorschau sichtbar (Strava-Pattern) + Welcome-Card-Width-Fix

## 0.1.149 — 2026-05-27

- feat(5.13): accuracy_30w_pct als Backend-Aggregat, Frontend-Heuristik raus
- chore(5.13): Story ready-for-dev — Genauigkeits-Aggregat als Backend-Metrik
- fix(5.12): Hebel-Klartext ohne Quellen-Zitate, Sharing nur als Bild
- fix(5.12): TuningPfadCard 'Karte ausblenden' war UX-Sackgasse

## 0.1.148 — 2026-05-27

- fix(5.12): Welcome-Card-Refinement nach User-Feedback

## 0.1.147 — 2026-05-26

- feat(5.12): 24h-Welcome-Card + Mein Tuning-Pfad + Beta-Hardware-Insights

## 0.1.146 — 2026-05-26

- feat(5.11): Reaktionstest-Journal, Diagnose-APIs und Profil-Vergleich

## 0.1.145 — 2026-05-26

- chore: Marstek-local-Defaults + bundled WIP
- feat(5.10): Identity-Sprache + Setup-Steckbrief P0 (Gamification)
- feat(deps): add html-to-image for setup steckbrief PNG export

## 0.1.144 — 2026-05-21

- feat(3.30): Pause zwischen Richtungswechseln + Settings-UI
- chore: Ingress-Port 8099→8777, Alex-Kly-Hersteller in Add-on-Beschreibung
- fix(3.15): Readback-Availability-Guard sieht `unavailable` nach WS-Outage

## 0.1.143 — 2026-05-20

- chore(5.1l): Sprint-Status und FunctionalTest-Tests nachgezogen
- feat(5.1l): Onboarding-Wiedererkennung, FunctionalTest/Running-Tests
- docs(5.1l): Story-Artefakt ergänzt, Marstek-Nachmittag-QA
- feat: Story 5.1l Onboarding-Wiedererkennung + Reaktionstest als Gefallen
- feat(live): Live-Screen vereinheitlichen — h1/Enum-Chip raus, eine Wirkungs-Euro-Wahrheit, Watt-only-Bilanz
- feat(live): Netz-Leistung-Tile zeigt wieder Watt-Wert mit Vorzeichen

## 0.1.142 — 2026-05-19

- feat: finalize 5.1j config drawer model

## 0.1.141 — 2026-05-19

- feat: Heute-Bilanz, Live-Diagramm-Symmetrie und Reaktionstest-Hinweise
- docs(5.1j): Schubladen-Modell-Konsolidierung — Kp-Max ratifiziert, Quell-Refs gefixt, Sextett-Korrektur

## 0.1.140 — 2026-05-19

- feat(5.5a): Hero letzte Aktion, open-loop-Fixes, Dev-Port 8777
- chore: Ingress-Port 8099→8777, Alex-Kly-Hersteller in Add-on-Beschreibung
- feat(5.5a): Hero-Footer zeigt letzte Aktion mit Werten (Neu-Impl gegen main)

## 0.1.139 — 2026-05-19

- fix: ERROR_ADVICE für Reaktionstest Pre-Check-Log-Keys

## 0.1.138 — 2026-05-19

- feat: SPEICHER PI-Defaults nach Akku-Hardware-Klasse
- docs(qa): Tagesanalyse 2026-05-18 Trucki+Victron + Runbook-Grid-Meter-Filter-Härtung
- feat: Live-Diagramm-Symmetrie Akku/WR (Story 5.8) + chartSeries
- fix(speicher): Integrator-Windup am SoC-Cap — voller Akku entlädt jetzt bei Netzbezug

## 0.1.137 — 2026-05-16

- docs: QA-Validierung SolakonONE Story 3.28 open_loop
- feat(brand): Setup-CTAs auf Marken-Rot + Sektions-Signatur-System

## 0.1.136 — 2026-05-16

- fix: Klartext „Anpassung zu klein" für min_step und Hysterese
- feat(brand): Marken-Rot Chrome-only + Rebrand Add-on-Name auf "Soalex"

## 0.1.135 — 2026-05-16

- fix: WR-Reaktionstest PV-Headroom und abbrechbares Readback
- docs: Story 3.23 — drei offene WR-Reaktionstest-Review-Punkte ergänzt

## 0.1.134 — 2026-05-16

- feat: Story 3.28 open_loop, Migration 009 und Readback-UI

## 0.1.133 — 2026-05-16

- feat: readback_mode für WR und Akku (Story 3.28)
- fix: Marstek Venus E RS485-Steuermodus-Select als Permission-Entity priorisieren

## 0.1.132 — 2026-05-15

- feat: Story 5.1i Verhalten-Settings nach Besitz (4-Block)

## 0.1.131 — 2026-05-15

- docs: Story 5.1i Settings-Restrukturierung und UX-Spec ergänzen
- fix: Sticky-Setpoint-Schutz — Hysterese-Cap + Trend-Override (Story 3.19)

## 0.1.130 — 2026-05-15

- docs: Videoskript „Der klebende Setpoint" (Zendure Live-Befund)

## 0.1.129 — 2026-05-15

- fix: SoC-Cap nur Latch-Richtung sperren; Live-Zyklen lesbar

## 0.1.128 — 2026-05-15

- fix: Akku-Readback Single-Source und Magnituden-Vergleich (Zendure)
- fix: Funk-Bridge- und Cloud-API-Beispiele in Hardware-Klasse-Picker (Akku)

## 0.1.127 — 2026-05-15

- fix: Funktionstest Status-Stale-Recovery, Wizard-Skip und Akku-Leistungs-Anzeige

## 0.1.126 — 2026-05-15

- feat: Akku-Hardware-Klasse für Rate-Limit und Reaktionstest-Step-Timing
- fix: mode_switch_single Setpoint-Echo Sign-Vergleich gegen abs(target)

## 0.1.125 — 2026-05-14

- fix: Akku-Power-Feedback-LivePreview-Vorzeichen an Backend-Konvention

## 0.1.124 — 2026-05-14

- feat: Story 3.27 WR-Reaktionstest Bridge-Write bei niedrigem Start-Limit

## 0.1.123 — 2026-05-14

- fix: Setpoint-Echo Readback schneller + grid_target_w-Default 10 W

## 0.1.122 — 2026-05-14

- feat: Story 3.26 WR-Hardware-Klasse Funk (OpenDTU/AhoyDTU) + 2.9-Feedback-Feinschliff
- feat: Story 2.9 Wizard Power-Feedback-Picker (Akku Pflicht, WR optional)

## 0.1.121 — 2026-05-13

- fix: Akku-Rate-Limit 30s (Readback-Kopplung), passive_only PI + Min-SoC-Schutz

## 0.1.120 — 2026-05-13

- fix: Akku-Rate-Limit-Default 5s, max_soc 100, SoC-Staleness für Pool/passive

## 0.1.119 — 2026-05-13

- feat: Story 3.23 WR-UI-Symmetrie + Story 3.24 WR-Reaktionstest (API, Wizard)

## 0.1.118 — 2026-05-13

- feat: Story 2.10 Akku-Hardware-Swap, Story 3.22 Regelungs-Profile, Folge-Specs 3.23/3.24

## 0.1.117 — 2026-05-12

- fix: Story-3.20-Code-Review-Härtung, Sprint 3.20 done + Story 2.10 angelegt

## 0.1.116 — 2026-05-12

- feat: Story 3.20 Drossel-PI, Wizard-Defaults und Sprint-/Doku-Stand

## 0.1.115 — 2026-05-12

- chore: story 2.2a abgeschlossen (Setpoint-Echo readback_invert, Tests, Sprint)

## 0.1.114 — 2026-05-12

- chore: story 3.19 auf backlog (Heartbeat zugunsten UI-Tuning-Hypothese)

## 0.1.113 — 2026-05-12

- fix: story 3.21 soc-cap-gates wiederholen 0-w-stop bis echo

## 0.1.112 — 2026-05-12

- feat: funktionstest setpoint-echo fallback und hysterese-feintuning

## 0.1.111 — 2026-05-11

- fix: speicher soc-kappen erkennen bei latched setpoint und flachem meter

## 0.1.110 — 2026-05-11

- fix: story-3-18 review smoothing am grid-meter und noise-band-range

## 0.1.109 — 2026-05-11

- feat: schreib-reduktion mit hysterese und median-noise-band

## 0.1.108 — 2026-05-10

- feat(3.10b): grid_target_w für Akku-only (wr_charge) + Pool-Lead-Fallback

## 0.1.107 — 2026-05-10

- fix(3.10a): grid_target_w in MULTI-Gates und Drossel-Feed-in-Check

## 0.1.106 — 2026-05-10

- feat(3.10a): symmetrischer Mindestbezug, PI-Soll in Verhalten

## 0.1.105 — 2026-05-10

- feat(3.17): Rate-Limit-Anti-Windup PI-Speicher + Reaktionstest-Wartezeit

## 0.1.104 — 2026-05-09

- fix(4.11): Sparkline-Bar-Breite, History-Skeleton 400ms, Retry bei Fehler

## 0.1.103 — 2026-05-09

- docs: Sprint-Status 4.11 review, Story 3.17 ready, Artefakt 4.11 erweitert
- feat: Stories 4.9–4.11 Schreibhistorie, Retention und Sparkline
- fix: reaktionstest done+unzuverlässig zeigt warning + diagnose-logs

## 0.1.102 — 2026-05-09

- qa: Diagnose-Export Marstek Testsystem 2026-05-09 (meta + DB)
- fix: setpoint-echo-readback toleriert stale state bei matching value

## 0.1.101 — 2026-05-09

- fix: subscribe mode-select + permission-switch aus battery_control blob

## 0.1.100 — 2026-05-09

- Reaktionstest: idempotenter Mode-Echo; PI-Edit ohne volles Mess-Blob

## 0.1.99 — 2026-05-09

- Story 3.16c: Review-Fixes PI-Tuning, Reaktionstest und Speicher-PI

## 0.1.98 — 2026-05-09

- fix: akku-cadence-ui und reaktionstest nutzt live-battery-pool

## 0.1.97 — 2026-05-09

- fix: reaktionstest-ui bei unzuverlässigem ergebnis und tests

## 0.1.96 — 2026-05-09

- feat: implementiere PI-regelung mit reaktionstest end-to-end

## 0.1.95 — 2026-05-08

- chore: snapshot vor großer pid-regelungsänderung

## 0.1.94 — 2026-05-08

- fix: halte hero-evidence auch bei failed/timeout dispatch aktuell

## 0.1.93 — 2026-05-08

- feat: ergänze heute-gesteuert-kpi und strompreis-settings

## 0.1.92 — 2026-05-08

- docs(test): markiere review-fixes als erledigt und schärfe custom-rate-limit-test

## 0.1.91 — 2026-05-08

- fix: stabilisiere rate-limit opt-out und config-preset-verhalten

## 0.1.90 — 2026-05-08

- fix: härte speicher-range-clamp und funktionstest-diagnostik

## 0.1.89 — 2026-05-07

- fix: räume running-statusanzeige auf und ergänze footer-meta

## 0.1.88 — 2026-05-07

- fix: stabilisiere akku-funktionstest und clamp speicher-setpoints

## 0.1.87 — 2026-05-07

- fix: vereinfache narrative passiv-logik und verbessere config-edit flow

## 0.1.86 — 2026-05-07

- feat: Adapter-Defaults & Akku-Topologie-Feinschliff + neue QA-Diags

## 0.1.85 — 2026-05-06

- fix: Night-Hero-Logik und Settings-Rate-Limit-Feld nachziehen

## 0.1.84 — 2026-05-06

- fix: Solakon Numeric-Mode-Pflicht im Wizard absichern

## 0.1.83 — 2026-05-06

- fix: Mode-Option-Autodetect gegen Slot-Kollisionen härten

## 0.1.82 — 2026-05-06

- fix: Wizard-Optionen und Akku-Cooldown-Defaults nachschärfen

## 0.1.81 — 2026-05-06

- feat: Battery-Topology-Wizard und Mode-Option-Handling erweitern

## 0.1.80 — 2026-05-06

- feat: Sticky Header/Footer für Settings- und Diagnose-Seiten

## 0.1.79 — 2026-05-06

- fix: Passive-Akku-Flow und Running-UI nachschärfen

## 0.1.78 — 2026-05-05

- fix: iOS-Nav-Fallbacks in Running/Setup-Routen absichern

## 0.1.77 — 2026-05-05

- fix: SettingsVerhalten-Review-Patches und Story-Status abschließen

## 0.1.76 — 2026-05-05

- feat: Settings-Verhalten auf eine Sammel-Page konsolidieren

## 0.1.75 — 2026-05-05

- feat: Narrative-, Settings- und Diagnose-Refinements bündeln

## 0.1.74 — 2026-05-05

- feat: Settings-IA-Refactor, Verbindungsdiagnose und Health-Status erweitern

## 0.1.73 — 2026-05-05

- feat: Topologie-Default für Akku-Cooldown absichern

## 0.1.72 — 2026-05-05

- feat: Sign-Flip-Cooldown, Helper-Slugs und Klartext-Mapping

## 0.1.71 — 2026-05-04

- fix: QA-Status-Helper über HA-WebSocket anlegen
- ci: Add-on-Changelog bei Auto-Release aus Git-Log ergänzen

## 0.1.1-beta.7 — 2026-04-25

- Manifest/Release-Stand auf `0.1.1-beta.7` aktualisiert.
- Runtime- und Debug-Logging-Verbesserungen aus Story-4.0-Zyklus integriert.
- Speicher-/Controller-Stabilisierung inklusive begleitender Test-Erweiterungen.

## 0.1.0-beta.1 — 2026-04-23

- Initiales Add-on-Skeleton (Multi-Arch, amd64 + aarch64).
- FastAPI-Backend unter Ingress-Port 8099.
- Health-Endpoint `/api/health`.
- SQLite-Init unter `/data/soalex.db` (WAL-Mode).
- Minimum HA Core: 2026.4.0 deklariert (via `addon/config.yaml`
  `homeassistant:`-Feld; niedrigere Versionen erhalten Install-Warning).
- Support-Matrix auf **Home Assistant OS** beschränkt. Home Assistant
  Supervised, Container und Core werden nicht unterstützt.
- Landing-Page-Voraussetzungen (`docs/landing/voraussetzungen.md`) und
  In-Store-Doku (`addon/DOCS.md` Abschnitt „Unterstützte HA-Versionen")
  ergänzt.
