---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - docs/Solalex-Deep-Research.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-14.md
  - docs/ALKLY_CI_Brand_Guidelines.md
  - docs/solalex-design-system.md
workflowType: 'ux-design'
project_name: 'Solalex'
user_name: 'Alex'
date: '2026-04-20'
---

# UX Design Specification Solalex

**Author:** Alex
**Date:** 2026-04-20
**Brand:** ALKLY
**Tagline:** Steuert deinen Solar lokal und sekundengenau.

---

## Executive Summary

### Project Vision

Solalex ist kein Dashboard, das Zahlen zeigt, und keine App, die sich konfigurieren lässt. Solalex ist ein unsichtbarer Regler mit einem sichtbaren Beweis — eine Maschine, die ab Sekunde 1 autonom arbeitet, eingebettet im HA-Ingress-Frame, und dem Nutzer einmal am Abend mit genau einer Zahl sagt: „Das hat's dir heute gebracht."

Die UI läuft als HA-Ingress-embedded Web-App (FastAPI + Svelte) auf Desktop und Tablet in der HA-Sidebar. Sie rendert in v1 konsistent im ALKLY-Light-Look (Dark-Mode gestrichen, Amendment 2026-04-23). Und sie muss fühlbar cooler wirken als jedes Hersteller-App, jedes EVCC-Dashboard und jede generische SmartHome-Oberfläche — weil PV als Domain mehr emotionale Aufladung verträgt: es geht um das eigene Haus, eigenes Geld, eigene Autarkie.

Kern-Designprinzipien:
- **Ergebnis vor Technik** — Euro vor kWh, Ersparnis vor Watt.
- **Charakter bei Tun, Fakten bei Zahlen** — strikt getrennt. Zahlen entertainen nie.
- **Sichtbare Autonomie** — der Regel-Modus, die aktive Entscheidung, der Idle-State als positive Aussage. Solalex zeigt Denken, nicht nur Zustände.
- **Pull, nicht Push** — keine Benachrichtigungen. Wenn der Nutzer das Dashboard öffnet, muss es sofort lebendig wirken, auch wenn nichts passiert.
- **100% lokal, auch in Assets** — DM Sans als selbst-gehostete WOFF2 im Add-on-Container. Kein Google-Fonts-CDN, kein externes Preconnect. Lokalität ist nicht nur Backend-Prinzip, sondern Design-Prinzip.

### Target Users

Vier Personas prägen die UX-Entscheidungen (aus PRD-Journeys destilliert):

**Marstek-Micha (44% der Warteliste, Kern-Segment)** — Frustrierter Bastler, hat nach drei Wochen YAML-Kampf gekündigt. Will, dass „es endlich läuft". UX-Implikation: Wizard führt in unter 10 Minuten zum Erfolg. Akku-Pool darf keine Komplexität nach aussen zeigen. Der Funktionstest ist der emotionale Beweis-Moment („Readback bestätigt, Akku lädt").

**Beta-Björn (Blueprint-Kunde, IT-affin)** — Hat bereits eine funktionierende Lösung, ist skeptisch gegenüber Migration. UX-Implikation: Die Migration muss sichtbar schlanker werden als vorher. Zwei-Schritte-„bist du sicher"-Moment bei der Übernahme. Blueprint-Automation wird durch Solalex deaktiviert, sichtbar, deterministisch.

**Neugier-Nils (31, Einsteiger, erstes BKW)** — YAML-scheu, liest alles zweimal. UX-Implikation: Live-Werte neben jedem Sensor im Wizard als „ja, das bin ich"-Moment. „Kein Akku"-Pfad wird lautlos übersprungen. Funktionstest wird zur Mini-Demo, in der er zum ersten Mal versteht, was seine Hardware kann.

**Alex Kly (Gesicht der Marke)** — Macht Support selbst in Discord. UX-Implikation: Diagnose-Export ist ein einziger Klick. Charakter-Zeilen im Dashboard spiegeln seine YouTube-Tonalität (direkt, Du-Ansprache, konkret). Kein anonymes Produkt — Solalex hat erkennbar ein Gesicht.

### Key Design Challenges

**1. HA-Ingress-Frame ist eine fremde Box.** Wir haben kein volles Browserfenster, keine URL-Kontrolle, HA-Sidebar steht links. Breite variiert stark: Desktop 1200px+, Tablet 768px, Mobile-HA-App 420px. Das bestehende interne Design-System ist Mobile-First (420px). Für v1 brauchen wir ein responsives System mit drei klaren Breakpoints (420 / 768 / 1200+) und einer Layout-Shift-Logik, die auf Desktop nicht wie eine hochgezogene Mobile-App wirkt.

**2. ~~Dark/Light-Mode-Adaption mit ALKLY-Farbidentität~~ — v1-Cut (Amendment 2026-04-23).** Solalex rendert in v1 ausschließlich im ALKLY-Light-Look, unabhängig vom HA-Theme-Signal. Kein `[data-theme="dark"]`-Override, kein MutationObserver. Dark-Mode ist Kandidat für v1.5.

**3. Setup-Wizard vs. Daily-Dashboard — zwei UX-Regime.** Der Wizard ist linear, bildschirmfüllend, fokussiert, eine primäre Aktion pro Screen. Das Dashboard ist parallel, modular, glanz-orientiert, mehrere parallele Informations-Zonen. Beide dürfen sich nicht fremd anfühlen, aber auch nicht identisch sein. Einheitliche Tokens, unterschiedliche Komposition.

**4. „Pull, nicht Push" verlangt einen aktiven Idle-State.** Wenn nichts passiert, darf das Dashboard nicht leer wirken. Das ist der #51-Claim aus dem Brainstorming: idle ≠ kaputt. Lösung: sanftes Atmen des Energy Rings, Teal-Soft-Background, kurze Charakter-Zeile („Alles im Ziel. Ich überwache weiter.").

**5. Diagnose-Tab für Nerds, ohne Einsteiger einzuschüchtern.** Alex braucht ihn als Support-Werkzeug, Micha darf ihn nicht aus Versehen öffnen und panisch werden. Lösung: Diagnose ist eine bewusst abgesetzte Route („Für Fortgeschrittene"), mit einer freundlichen Einleitungszeile und einem prominenten Export-Button, der den Nerd-Kram in ein JSON verpackt.

**6. Keine externen Assets.** Kein Google Fonts, kein CDN-Bundle, keine Telemetry-Pixel, keine Analytics-Skripte. Das zwingt uns zu einem disziplinierten Asset-Pipeline-Setup mit WOFF2-Subsetting, selbst-gehostetem DM Sans, lokal eingebetteten SVG-Icons. Das ist Aufwand, aber Teil der Markensubstanz.

### Design Opportunities

Hier wird Solalex sichtbar cooler als der Markt.

**A. „Gedanken-Layer" im Dashboard.** Eine dezente Zeile über dem Euro-Wert erzählt den aktuellen Regel-Modus narrativ: „Venus-Pool lädt mit 1.400 W · Überschuss wird gespeichert." Kein Balken-Chart, sondern eine animierte Status-Kette mit Piktogrammen. Das ist der Moat gegen jedes andere PV-Tool — Solalex zeigt Denken, nicht Zustände.

**B. Flow-Visualisierung statt Zahlen-Kacheln.** PV → Haus / Akku / Netz als animated flow: SVG-Paths mit moving particles in Teal (Erzeugung/Überschuss) und Rot (Bezug/Verbrauch), nicht als klassisches Energieflussdiagramm. Finanz-Apps zeigen „Geld fließt" — Solalex zeigt „Energie fließt", mit derselben emotionalen Qualität.

**C. Funktionstest als Dramaturgie.** Der Moment, in dem Solalex zum ersten Mal das WR-Limit testweise setzt, wird zur Mini-Demo mit Live-Chart, Readback-Check als animiertem Tick, Ergebnis-Feedback. Das ist der Wow-Moment aus Nils' Journey 3. Jede spätere PV-Erfahrung wird an diesem Moment gemessen.

**D. Modus-Wechsel sichtbar inszeniert.** Akku-voll → Drossel-Übergang wird nicht versteckt, sondern animiert: Ring wechselt Farbe, Badge rotiert, kurzer Status-Text erklärt. Zeigt dem Nutzer: ich denke gerade aktiv. Das ist die visuelle Beweisführung für die adaptive Regelungs-Strategie (Innovation #8 aus PRD).

**E. Custom-gebaute PV-Ikonographie statt Stock-Icons.** Wechselrichter, Akku, Smart Meter, Shelly, Marstek-Silhouette, Hoymiles-Typ — eigene Icons in 1,5px-Stroke, konsistent mit DM-Sans-Geometrie. Feather/Lucide fallen im PV-Kontext sofort auf. Eigene Icons sind Markenaufbau.

**F. „Nichts zu tun"-Zustand als positive Aussage.** Kein leeres Dashboard. Sanftes Atmen, Teal-Soft-Background, Charakter-Zeile: „Alles im Ziel. Ich überwache weiter." Das löst die #51-Herausforderung aus dem Brainstorming ohne Nerv-Faktor.

**G. Lokale Font-Pipeline als CI-Feature.** DM Sans als WOFF2-Subset im Add-on-Container (4 Weights, Latin + Latin-Extended, ~120 kB). Keine externen Requests. Diese Entscheidung wird über ein kleines „100% lokal"-Footer-Badge kommuniziert — kein Marketing-Banner, sondern subtiler Beweis.

**H. Mikro-Haptik durch Animation.** Cubic-Bezier-Easings mit leichtem Overshoot für Toggles (0.34, 1.56, 0.64, 1). Stagger-Delays in Listen (50ms pro Element). Puls auf genau einem Live-Status-Dot pro Screen. Keine Animation länger als 1200ms. Das ist das Delta zwischen „funktioniert" und „fühlt sich hochwertig an".

## Core User Experience

### Defining Experience

Solalexs gesamte UX steht oder fällt mit genau einer Interaktion: Der Nutzer öffnet das Dashboard aus der HA-Sidebar und sieht innerhalb von 2 Sekunden eine Euro-Zahl, die sagt, wie viel Solalex heute für ihn gesteuert hat.

Das ist kein Feature. Das ist der Produkt-Lackmustest. Wenn der Moment nicht klickt (keine Scroll-Bewegung, keine Interpretation, keine Zweideutigkeit), scheitert Solalex. Wenn er klickt, wird er jeden Abend wiederholt und baut tägliches Vertrauen auf.

**Core Loop:**

1. Sidebar-Klick auf „Solalex" (1 Klick)
2. Dashboard rendert mit Euro-Zahl als visuellem Held (unter 2 s)
3. Optionaler Blick auf Energy Ring und Flow (Live-Zustand)
4. Dashboard wieder zu — Solalex arbeitet autonom weiter

Die sekundäre Interaktion ist der Setup-Wizard: einmalig, dramaturgisch aufgeladen, aber danach strukturell irrelevant.

### Platform Strategy

| Dimension | Entscheidung |
|---|---|
| Primärkontext | Home Assistant Ingress-Frame (iframe-embedded Web-App) |
| Rendering-Surface | Svelte-SPA, serverseitig von FastAPI, WebSocket-Live-Updates |
| Input-Primat | Dual — Touch (Tablet vom Sofa) und Maus/Tastatur (Desktop am Arbeitsplatz) |
| Breakpoints | 420 (Mobile-HA-App) / 768 (Tablet) / 1200+ (Desktop) |
| Offline-Verhalten | Voll funktional — HA-Verbindung ist lokal, LemonSqueezy nur einmal/Monat |
| Theme-Adaption | Statischer ALKLY-Light-Look; keine HA-Theme-Adaption in v1 (Amendment 2026-04-23) |
| Browser-Matrix | Chromium-basiert (HA Companion-Apps), Safari (iPad), Firefox — keine IE/Legacy |
| Assets | 100% lokal: DM Sans als WOFF2 im Container, SVG-Icons inline, keine externen Requests |
| Notifications | Keine. Pull, nicht Push. HA-Notifications sind bewusst nicht genutzt |

**Kein Mobile-First-Bias.** Das ist ein Bruch mit dem bisherigen internen Design-System. Grund: Desktop im HA-Frame (1200px+) ist der dominante Zugriffs-Context, nicht Mobile. Design wird Desktop-canonical entwickelt, dann runterskaliert.

### Effortless Interactions

**1. Hardware wird nicht konfiguriert, sondern erkannt.** Auto-Detection scannt `get_states`, matcht gegen Device-Templates, zeigt Live-Werte zur Bestätigung. Der Nutzer klickt „Das bin ich", nicht „Entity auswählen".

**2. „Kein Akku" wird lautlos übersprungen.** Der Wizard fragt nicht, sondern überspringt Schritte, die keinen Sinn machen.

**3. Blueprint-Import ist ein „Ja"-Klick.** Solalex erkennt das bestehende Blueprint, liest die Helfer, übernimmt Werte, deaktiviert das Alte.

**4. Modus-Wechsel passieren ohne Nutzer-Eingriff.** Drossel ↔ Speicher ↔ Multi werden automatisch per Hysterese gewählt. Der Nutzer sieht den Modus, kann ihn nicht setzen.

**5. Funktionstest zeigt Effekt, bevor er erklärt wird.** Solalex setzt testweise das WR-Limit auf 50 W. Der Nutzer sieht die Einspeisung live fallen und versteht in Sekunde 3, was passiert, ohne Erklärungstext.

**6. Diagnose-Export ist ein Klick.** Strukturiertes JSON in den Zwischenspeicher oder als Download. Kein Form-Ausfüllen.

**7. Bezugspreis-Änderung ist inline.** Klick auf die Euro-Zahl, Stepper erscheint, Anpassung 30 → 32 ct, Zahl aktualisiert live. Kein Einstellungs-Dialog.

### Critical Success Moments

**Moment 1: Der 2-Sekunden-Dashboard-Hit.** Wenn Solalex die 2-Sekunden-Kernaussage verfehlt, ist das Produkt jeden Abend tot. TTFD unter 2 s, Euro-Zahl im oberen Drittel, kein Scrolling nötig.

**Moment 2: Der Funktionstest-Klick.** Emotional für Micha („Readback bestätigt, Akku lädt"), Verstehens-Moment für Nils. Wenn dieser Moment flackert oder unklar ist, kippt das Vertrauen.

**Moment 3: Die erste Euro-Zahl am Abend nach Setup.** Klein, aber real. Anker für die nächsten 30 Tage Nutzung. Null oder unglaubwürdig = Trial tot.

**Moment 4: Der Idle-State als positive Aussage.** Sanftes Atmen, Teal-Soft-Hintergrund, Zeile „Alles im Ziel. Ich überwache weiter." Wenn das wie ein Fehler aussieht, verliert Solalex seinen Differentiator.

**Moment 5: Modus-Wechsel als sichtbarer Beweis der Intelligenz.** Ring-Farbe-Shift, Badge-Rotation, kurze Status-Zeile. Zeigt: Solalex denkt. Wenn versteckt, bleibt Solalex Blackbox.

~~**Moment 6: Dark-Mode-Umschaltung ohne Bruch.**~~ — **v1-Cut (Amendment 2026-04-23).** Entfällt, da Dark-Mode nicht Teil von v1.

### Experience Principles

**1. Ergebnis vor Technik.** Euro vor kWh. Ersparnis vor Watt. Technische Werte sind immer nachgeordnet und kleiner als das Ergebnis.

**2. Charakter bei Tun, Fakten bei Zahlen.** Strikt getrennte Zonen. Zahlen sind nackt, präzise, ohne Adjektive. Charakter-Zeilen nur, wenn Solalex über sein eigenes Tun berichtet.

**3. Sichtbare Autonomie, nicht Kontroll-Illusion.** Der Nutzer sieht, was Solalex tut, kann es aber nicht fein-steuern. Keine Schieberegler für Deadbands, keine Modus-Selektoren.

**4. Pull, nicht Push, aber lebendig beim Öffnen.** Keine Benachrichtigungen. Aber wenn das Dashboard geöffnet wird, muss es sofort atmen, fließen, reagieren, auch im Idle-State.

**5. Jede Sekunde Latenz kostet Vertrauen.** TTFD unter 2 s ist ein Produkt-Versprechen, kein Performance-Ziel. WebSocket statt REST, Skeleton-States nur für unter 400 ms, optimistische UI wo möglich.

**6. Lokal auch in Assets.** DM Sans als WOFF2, Icons als inline SVG, keine externen Requests. Ein einziges `preconnect` auf Google-Fonts würde die Marke widerlegen.

**7. Desktop ist canonical, Mobile/Tablet sind Ableitungen.** Bruch mit Convention, aber HA-Ingress-Desktop ist der dominante Kontext. Design wird für 1200px+ entworfen, dann runterskaliert.

**8. Keine Überraschungen nach Start.** Was Solalex einschaltet, schaltet Solalex auch aus. Keine „Geist-Verbraucher", keine unerklärten Aktionen.

## Desired Emotional Response

### Primary Emotional Goals

**Dominantes Gefühl: Gelassene Souveränität.**

Solalex erzeugt kein „Yeah, ich hab's im Griff"-Bastler-Stolz. Solalex erzeugt die ruhige Souveränität eines Hausbesitzers, der weiß, dass die Maschine für ihn arbeitet, und der deshalb nicht mehr drüber nachdenken muss. Das Vorbild ist ein gut eingestellter Thermostat in einem teuren Haus: du weißt, er läuft, du weißt, er ist gut, und genau deshalb denkst du 99% der Zeit nicht an ihn. Wenn du doch hinschaust, siehst du ein schönes Display, eine klare Zahl, und du denkst: „Passt."

Die zweite Schicht ist stille Befriedigung. Nicht laut, nicht feierlich, nicht mit Konfetti-Animation. Sondern die Art von Befriedigung, die man bei einer eleganten Finanzapp beim Monats-Blick empfindet: „Sieh an. Das hat sich gelohnt."

### Emotional Journey Mapping

| Phase | Vorher (Frust-Zustand) | Solalex-Zustand (Ziel) |
|---|---|---|
| Entdeckung (Landingpage) | Skepsis — „Wieder ein Tool, das Cloud braucht?" | Erleichterung — „Endlich einer, der sagt: lokal, einmalig, läuft" |
| Installation | Angst — „Zwei Stunden Fummelei" | Überraschung — „Das war's? Drei Klicks?" |
| Auto-Detection | Unsicherheit — „Wähle ich die richtige Entity?" | Wiedererkennung — „Ja, das bin ich. Der Wert stimmt." |
| Funktionstest | Skepsis — „Funktioniert das wirklich bei mir?" | Staunen — „Oh. Das Netz geht gerade tatsächlich auf null. Live." |
| Erster Tag | Sorge — „Macht das jetzt wirklich was?" | Vertrauen — „Abends 2,40 € — klein, aber ehrlich. Der Anfang." |
| Daily Glance (ab Tag 7) | Langeweile oder Abhängigkeit | Gelassenheit — „Passt. Zuklappen, weitermachen." |
| Idle-State (14:00, nichts passiert) | Verwirrung — „Läuft das noch?" | Ruhe — „Er überwacht. Alles im Ziel." |
| Support-Fall (Firmware-Break) | Panik + Wut | Gemeinschaft — „Alex hat das im Discord gesehen. Hotfix in 2 h. Kein Konzern." |
| Monatsende | Nichts oder Ernüchterung | Stille Befriedigung — „18,40 € im April. Sommer kommt." |

### Micro-Emotions

**1. Vertrauen vs. Skepsis** — der tragende Balken. Solalex operiert in einem Markt voller Cloud-Abzocker und Hobby-Bastelei. Jede UI-Entscheidung muss Vertrauen aufbauen: das „100% lokal"-Footer-Badge, der Funktionstest als sichtbarer Beweis, die Charakter-Zeilen in Alex' Stimme, die strenge Trennung von „Zahlen nackt, Charakter über Tun". Vertrauen ist keine Marketing-Kategorie, sondern UX-Substanz.

**2. Zuversicht vs. Verwirrung.** Jeder Wizard-Schritt muss so klar sein, dass der Nutzer am Ende sagt „Ich habe das verstanden", nicht „Ich habe das abgeklickt". Der Funktionstest ist der Lakritzstein-Moment für Nils — er versteht in 3 Sekunden, was seine Hardware kann, weil er den Effekt live sieht.

**3. Befriedigung vs. Ungeduld.** Die Euro-Zahl wird nicht übertrieben. Wenn sie 0,14 € sagt, ist das die Wahrheit. Die UI feiert das nicht, sondern zeigt es nüchtern. Die Nüchternheit selbst ist der emotionale Anker: „Solalex lügt mich nicht an."

**4. Gelassenheit vs. Kontrollzwang.** Der Nutzer soll die Zahl sehen, zuklappen, gehen. Wenn er anfängt, am Dashboard zu fummeln, Modi zu setzen, Deadbands zu justieren, haben wir UX-technisch verloren. Die UI muss sich anfühlen, dass es nichts zu tun gibt. Das ist gewollt.

**5. Zugehörigkeit vs. Isolation.** Alex Kly ist namentlich sichtbar. Discord-Link ist im Footer. GitHub-Roadmap ist verlinkt. Der Nutzer ist nicht allein — er ist Teil einer kleinen, klugen Community, die ihr Solar-Setup selbst in die Hand nimmt. ALKLY-„Macher"-Identity-Shift in UX übersetzt.

**6. Staunen vs. Langeweile.** Drei bis fünf Momente pro Monat, in denen der Nutzer einen Blick hat, der sagt: „Mega cool gemacht." Das ist die emotionale Reserve gegen alle anderen PV-Tools: Funktionstest-Dramaturgie, Flow-Animation, Modus-Wechsel-Übergang.

### Anti-Emotions (aktiv vermeiden)

| Anti-Emotion | Entstehungs-Pfad | UX-Gegenmaßnahme |
|---|---|---|
| Frust | YAML-Fragen, Entity-Auswahl ohne Kontext, gescheiterter Funktionstest ohne Klartext | Auto-Detection + Live-Werte + lesbare Fehler-Meldungen mit Handlungsempfehlung |
| Panik | Rote Fehlermeldung ohne Kontext, Dashboard-Crash, Akku-Modus-Oszillation | Fail-Safe-Modus deterministisch, Fehler haben Handlungsempfehlung (Anti-Pattern aus Design-System) |
| Bevormundung | „Nur für Profis"-Disclaimer, lange Tutorials, erklärende Tooltips | Tooltips explizit verboten. Wenn etwas erklärt werden muss, ist das Label falsch. |
| Langeweile | Statisches Dashboard, Idle-State wie tot | Sanftes Atmen, Flow-Animation, Modus-Badge bewegt sich subtil |
| Überforderung | Zu viele Aktionen, mehr als 3 primäre Buttons | Max. 3 Aktionen pro Screen |
| Misstrauen | Unerklärte Cloud-Calls, Analytics-Skripte | 100%-lokal-Badge, offener Event-Source-Flag, Zahlen immer messbar attribuiert |
| Einsamkeit | Anonymes Produkt, kein Gesicht | Alex Kly namentlich im Produkt, Discord-Link, GitHub-Roadmap |
| Reue | Gekauft, funktioniert nicht, kein Rückweg | 30-Tage-Trial, Disclaimer vor Aktivierung, Graceful-Degradation bei Lizenz-Offline |

### Design Implications

**Vertrauen → Euro-Zahl als Hero, nicht Watt.** Technische Präzision des Hero-KPI beweist, dass Solalex nicht mit Prozenten rumrechnet. Die Zahl ist verifizierbar gegen Netz-Zähler. Das Dashboard hat ein „Wie wird das berechnet?"-Link direkt unter der Zahl (Klick öffnet inline-Panel mit Formel, keine Modal).

**Zuversicht → Live-Werte im Wizard.** Jeder Sensor zeigt im Wizard seinen aktuellen Wert („AC-Leistung: 412 W"). Der Nutzer bestätigt nicht eine Entity, sondern eine Messgröße, die er erkennt.

**Befriedigung → Monatsansicht mit gesammelter Summe.** Stats-Tab oder Home-Screen-Card: „April 2026: 18,40 € gesteuert". Nüchtern, ohne Jubel, aber präsent.

**Gelassenheit → Idle-State mit Atmen.** Der Energy Ring atmet langsam (60 bpm wie ruhiger Puls), Farbe sehr sanftes Teal, Zeile „Alles im Ziel. Ich überwache weiter." Keine blinkenden Elemente.

**Zugehörigkeit → Footer mit Alex' Micro-Avatar.** 24px rund, Text „Made by Alex Kly · Discord · GitHub · Privacy". Sichtbar, aber nicht dominant.

**Staunen → Funktionstest als Mini-Demo.** Nicht nur Checkliste, sondern live-Chart mit WR-Limit-Verlauf, Netz-Einspeisung, SoC. Die 30 Sekunden sind eine Mini-Reportage über das, was Solalex gerade tut.

**Trust-Anchors im Dashboard:**
- Zahl kann angetippt werden und zeigt „heute gesteuert: 1.247 Wh × 30 ct/kWh = 0,37 €" (Transparenz-Overlay)
- Event-Source-Flag ist im Diagnose-Tab sichtbar, im Normalbetrieb versteckt
- Letztes Readback-Timestamp als 9pt-Text im Footer

### Emotional Design Principles

**1. Nüchternheit als Vertrauensstifter.** Die Zahlen werden nicht verkauft. Ein Euro ist ein Euro, nicht „dein grüner Moment". Sprache ist konkret, direkt, Alex'sche Du-Ansprache ohne Verkaufs-Patina.

**2. Ruhe als Default-Ton.** Animationen subtil, Farben getokt, Layouts geordnet. Solalex ist kein Schreihals. Selbst der Hero-Moment (2-Sekunden-Zahl) ist ruhig inszeniert — keine Eintritts-Animation länger als 400 ms.

**3. Staunen nur dort, wo es ehrlich ist.** Drei Momente verdienen Glanz: Funktionstest, Modus-Wechsel, erste Euro-Zahl am Abend. Außerhalb dieser Momente wird Glanz reduziert — sonst stumpft er ab.

**4. Charakter atmet mit den Zahlen.** Je kleiner die Euro-Zahl, desto leiser der Charakter. „0,00 € gesteuert" → keine Charakter-Zeile. „2,40 €" → sachliche Zeile. „18,40 €/Monat" → ruhige Feier („Solider Monat."). Niemals umgekehrt.

**5. Idle ist ein Feature, kein Bug.** Wenn Solalex nichts tut, sagt das Dashboard das laut. Der Idle-State ist die UX-Metapher für „die Maschine funktioniert, du kannst weggehen".

**6. Anti-Patina, Anti-Bling.** Keine Gradients, die nach 2027 aussehen wie 2020. Keine Glassmorphism-Exzesse außerhalb der Bottom-Nav. Die UI soll in 5 Jahren noch zeitlos wirken — deshalb Timeless-Tokens statt Trend-Effekte.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

Solalex zieht Inspiration bewusst nicht aus SmartHome-Apps (Gimmick-Dashboards oder Ingenieurs-Cockpits), sondern aus Domains mit hoher emotionaler Aufladung und klarer Einzelzahl-Dominanz.

**Apple Wallet / Apple Fitness** — Die eine Zahl regiert den Screen. Kein Clutter, keine Tab-Navigation auf der Startansicht. Fitness zeigt Ring, Wallet zeigt Karte. Beide dominieren visuell. Solalex übernimmt: Hero-Zone mit Euro-Zahl als absoluter Mittelpunkt, Activity-Ring als Inspiration für Energy Ring — aber PV-spezifisch. Solalex übernimmt nicht: die feiern-die-Zahlen-Ästhetik. Ring bleibt, Konfetti nicht.

**Robinhood / N26 / Trade Republic** — Finanz-Zahlen mit Animation, die sich lebendig anfühlen ohne effekthascherisch zu sein. „Geld bewegt sich" wird visuell spürbar: Line-Charts mit weichem Anstieg, Pulsing-Indicators für Live-Daten, Gradient-Flächen als Subtilität. Solalex übernimmt: Flow-Logik (Geld fließt → Energie fließt), Line-Chart-Ästhetik, Live-Mikro-Puls. Solalex übernimmt nicht: die rot/grüne Aggressivität bei Kursschwankungen.

**Linear** — Tastatur-First-Bedienung, fluide Transitions, sofortige Reaktion. Die App fühlt sich wie ein Werkzeug an, nicht wie ein Tool. Solalex übernimmt: Transitions-Timing, Command-Palette-Denkweise (v2), Typografie-Disziplin. Solalex übernimmt nicht: die Dichte an Funktionen.

**Tesla App** — Auto als animiertes 2D/3D-Element im Zentrum. Sichtbare Ladung, sichtbarer Status. Der Nutzer sieht das Gerät, nicht die Zahlen. Solalex übernimmt: das Haus als zentrales visuelles Element der Flow-Visualisierung, Akku als kleines Thermometer mit SoC-Füllung. Solalex übernimmt nicht: 3D-Render-Aufwand — wir bleiben 2D-SVG, ist schneller, lokaler, zeitloser.

**Things 3 / Craft (macOS-Ästhetik)** — Ruhe, Weißraum, DM-Sans-würdige Typografie, Mikro-Details (Checkbox-Animation mit leichtem Spring), dezente Farbakzente. Solalex übernimmt: Spacing-Disziplin (8px-Raster), Shadow-System (2 Ebenen max), „Atmen"-Qualität. Solalex übernimmt nicht: skeuomorphe Tendenzen.

**Strava (Statistik-Screen)** — Performance-Zahlen in Kontext (heute vs. Woche vs. Monat) mit narrativen Annotations. Solalex übernimmt: Kontext-Zahlen im Stats-Tab (April: 18,40 € · März: 12,60 € · +46%), narrative Einordnung — aber in Solalex-Ruhe („Solider Monat.", nicht „Personal Best!").

**Zigbee2MQTT Web-UI** — Als HA-Add-on-Referenz und bewusste Untergrenze. Solalex muss sichtbar besser aussehen als Zigbee2MQTT, um den Premium-Preis zu rechtfertigen. Zigbee2MQTT ist das Niveau, das HA-Power-User als „OK" empfinden. Solalex muss „Woah" auslösen.

**Copilot (iOS) / Cashflow** — Monats-Übersicht mit einer dominanten Zahl + 3 Kontext-Kacheln, Kategorisierung durch Farbcode, Vertrauen durch Transparenz. Solalex übernimmt: Monats-Ansicht-Aufbau, „Transparenz-Overlay" beim Antippen der Hero-Zahl.

### Transferable UX Patterns

**Navigation-Patterns**

- Bottom-Nav mit 4 Reitern (Home / Geräte / Statistik / Einstellungen), ruhig, immer sichtbar. Keine Hamburger-Menüs. Auf Desktop (ab 1024px) wird die Bottom-Nav zu einer Left-Nav mit Icon+Label.
- Diagnose als abgesetzte Route (nicht in Bottom-Nav, sondern über Settings → „Diagnose öffnen"). Schützt Einsteiger vor Zufallstreffer.
- Kein Tab-Swipe. Navigation ist explizit — Tap/Klick, keine Swipe-Gesten. HA-Ingress macht Swipe-Gesten unzuverlässig (iframe-Grenze).

**Interaction-Patterns**

- Inline-Editing für Bezugspreis: Tap auf die Zahl → Stepper erscheint unter der Zahl, keine Modal. Enter/Blur speichert.
- Transparenz-Overlay: Tap auf Hero-Zahl → Inline-Panel fährt aus mit Formel und Quelle.
- Tastatur-Kürzel (Linear-Stil): `1/2/3/4` springt zwischen Hauptansichten, `D` öffnet Diagnose, `?` zeigt Shortcut-Referenz. Klein, aber für Alex/Björn ein Qualitätsmerkmal.
- Live-Feedback im Funktionstest (Robinhood-Stil): während Solalex das WR-Limit setzt, zeigt sich ein Live-Chart mit 5-Sekunden-Fenster. Readback als Checkmark-Animation (Spring-Easing).
- Optimistic UI (Linear-Stil): Toggle schaltet sofort um, WebSocket-Bestätigung kommt nach. Bei Failure rollt Toggle zurück mit sanfter Animation + Fehler-Zeile.

**Visual-Patterns**

- Activity-Ring-Metapher (Apple Fitness): zentraler Ring zeigt aktuelle Leistungs-Balance (Erzeugung vs. Verbrauch). Teal für Überschuss, Rot für Bezug, Grau für Neutral. Kein „Ziel-Tracker", sondern „Zustand-Visualisierer".
- Flow-Animation (Tesla): Energie fließt sichtbar zwischen PV-Icon → Haus-Icon → Akku-Icon → Netz-Icon. Particles auf SVG-Paths, Geschwindigkeit proportional zur Leistung.
- Line-Chart mit Gradient-Fill (Robinhood): Tagesverlauf mit weichem Anstieg, Fläche darunter als Gradient Teal→Transparent. Zwei überlagerte Linien (Erzeugung + Verbrauch) im Stats-Tab.
- Card-basierte Modularität: alles in Cards mit 16px Radius, 18–20px Padding, 1px Border (statt Shadow). Modular, zeitlos.
- Dezente Glass-Nav (Bottom-Nav mit 92% Opacity + Blur). Nur dieses Element darf Glassmorphism — sonst wirkt die UI nach 2020 statt 2026.

**Content-Patterns**

- Charakter-Zeile über dem Hero (eigenes Pattern, inspiriert von Alex' YouTube-Tonalität): „Venus-Pool lädt mit 1.400 W · Überschuss wird gespeichert." Klein (14px), 500-Weight, Teal oder Text-Secondary.
- Nüchternes Zahlen-Display (Copilot): Hero ist 56–72px DM Sans Bold, tracking -0.02em, immer mit Einheit („€") in 60% Opacity daneben.
- Status-Chips mit Icon + Label (Linear): 32px hoch, 12px Radius, Icon 16px, Label 13px. Verwendung für Regelmodus, Verbindungsstatus, Lizenz.

### Anti-Patterns to Avoid

- Keine Tabellen. Daten werden als Cards, Charts oder Listen dargestellt.
- Keine Modal-Dialoge. Alles passiert inline oder auf eigenem Screen.
- Keine Tooltips. Wenn etwas erklärt werden muss, ist das Label falsch.
- Keine roten Fehler ohne Kontext. Jeder Fehler enthält eine Handlungsempfehlung.
- Keine Loading-Spinner ohne Inhalt. Skeleton-States mit grauem Pulse.
- Keine technischen IDs sichtbar. „Hoymiles HM-800" statt `sensor.hoymiles_hm800_power`.
- Keine verschachtelte Navigation. Max. 1 Ebene tief.
- Keine grauen Disabled-Buttons. Disabled-State = ausblenden.
- Keine YAML/JSON-Bearbeitung, keine „Advanced"-Editoren in der MVP-UI.
- Keine Push-Notifications. Pull-only.
- Keine Fremd-Fonts via CDN. DM Sans ist selbst-gehostet, Punkt.
- Keine Zahlen ohne Einheit. 1.400 steht nie allein, es ist immer 1.400 W.
- Keine Sternchen, keine Erklär-Fußnoten.
- Keine Gamification. Keine Badges, Streaks, Achievements. PV ist kein Spiel.
- Keine Slider für technische Werte. Deadbands, Rate-Limits, Aggressivität sind nicht nutzer-steuerbar.
- Keine „Neu"-Badges und keine Announcement-Banner.

### Design Inspiration Strategy

**Zu übernehmen (Adopt):**
- Hero-Zahl-Dominanz von Apple Wallet/Fitness → Euro-Zahl als unangefochtener Mittelpunkt
- Flow-Animation-Qualität von Tesla-App → Energy Flow als primäre Visualisierung
- Line-Chart-Ästhetik von Robinhood → Tagesverlauf-Chart
- Ruhe-Qualität von Things 3/Craft → Spacing, Typografie, Ton-Haltung
- Transparenz-Overlay von Copilot → „Wie berechnet?"-Mechanik
- Tastatur-Kürzel-Disziplin von Linear → für Alex/Björn

**Zu adaptieren (Adapt):**
- Activity-Ring von Apple Fitness → PV-spezifisch, ohne Ring-Schließen-Feiern
- Bottom-Nav-Glass nur dort, nicht durchgehend
- Tesla-Geräte-Animation als 2D-SVG, nicht 3D
- Copilot-Monats-Ansicht in Solalex-ruhig statt Finanz-App-dramatisch

**Zu vermeiden (Avoid):**
- SmartHome-App-Clutter (Lovelace-Wildwuchs)
- EVCC/openWB-Ingenieurs-Ästhetik (Tabellen, YAML-sichtbar)
- Hersteller-App-Patina (Cloud-Login, App-Store-Banner)
- Trendige 2022-Effekte (Neumorphism, wilde Glassmorphism)
- Fitness-App-Gamification
- Finanz-App-Dramatik

**Kompass-Satz für jede Design-Entscheidung:**

> Würde Alex in einem YouTube-Video sagen: „Das ist mega cool gemacht, und es wirkt nicht aufdringlich"?
> Wenn ja: rein. Wenn nein: raus.
