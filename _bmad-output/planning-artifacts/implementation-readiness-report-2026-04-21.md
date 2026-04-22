---
stepsCompleted: ['step-01-document-discovery', 'step-02-prd-analysis', 'step-03-epic-coverage-validation', 'step-04-ux-alignment', 'step-05-epic-quality-review', 'step-06-final-assessment']
assessor: 'bmad-check-implementation-readiness (Claude)'
assessedOn: '2026-04-21'
filesUnderReview:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# Implementation Readiness Assessment Report

**Date:** 2026-04-21
**Project:** SolalexDevelopment

## Document Inventory (Step 1)

| Typ | Datei | Größe | Zeilen | Stand |
|---|---|---|---|---|
| PRD | `prd.md` | 59,984 B | 736 | 2026-04-20 |
| Architecture | `architecture.md` | 4,547 B | 74 | 2026-04-20 |
| Epics & Stories | `epics.md` | 83,493 B | 1.589 | 2026-04-21 |
| UX-Design | `ux-design-specification.md` | 30,274 B | 349 | 2026-04-20 |

**Duplikate:** keine.
**Fehlende Pflichtdokumente:** keine.
**Auffälligkeit (zur späteren Prüfung):** `architecture.md` ist ungewöhnlich knapp (74 Zeilen) im Verhältnis zum Umfang von PRD und Epics.

Bestätigt durch User: ✅ (Auswahl „C").

## PRD Analysis (Step 2)

Quelle: `_bmad-output/planning-artifacts/prd.md` (vollständig gelesen, 736 Zeilen).

### Functional Requirements

**Installation & Lizenz**
- **FR1:** Nutzer kann Solalex als HA Add-on über das Custom Repository `alkly/solalex` installieren.
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „HA OS oder Supervised" vor dem Download-Schritt.
- **FR3:** Nutzer erwirbt die Lizenz aus dem Setup-Wizard heraus (Weiterleitung zu LemonSqueezy, Rückkehr in den Wizard).
- **FR4:** Nutzer bestätigt vor Lizenz-Aktivierung den Installations-Disclaimer als sichtbare Checkbox.
- **FR5:** Solalex verifiziert die Lizenz einmalig online bei Aktivierung und monatlich erneut, mit Graceful Degradation bei Offline-Status.
- **FR6:** Bestandskunden können einen Rabatt-Code (Blueprint-Migration) im Kaufflow einlösen.

**Setup & Onboarding**
- **FR7:** Nutzer wählt im Setup-Wizard zwischen drei Hardware-Pfaden: Hoymiles, Anker, Manuell.
- **FR8:** Solalex erkennt kompatible HA-Entities automatisch (OpenDTU, Shelly 3EM, Anker Solix, Marstek Venus 3E/D).
- **FR9:** Nutzer sieht Live-Werte neben jedem erkannten Sensor im Wizard zur Bestätigung.
- **FR10:** Solalex überspringt den Akku-Schritt lautlos, wenn kein Akku erkannt wird.
- **FR11:** Solalex führt vor Aktivierung einen Funktionstest durch (testweises Setzen von WR-Limit oder Akku-Setpoint, Readback-Prüfung).
- **FR12:** Solalex erkennt und importiert bestehende Nulleinspeisungs-Blueprint-Automationen inkl. Helfer-Werte (mit expliziter Deaktivierung des alten Blueprints bei Aktivierung). *Kippbar → Fallback manueller JSON-Import.*

**Regelung & Steuerung**
- **FR13:** Solalex wählt die Regelungs-Strategie je erkanntem Hardware-Setup automatisch (Drossel / Speicher / Multi-Modus).
- **FR14:** Solalex regelt im Drossel-Modus reaktiv auf Nulleinspeisung per WR-Limit.
- **FR15:** Solalex lädt im Speicher-Modus Akkus bei PV-Überschuss und entlädt zur Grundlast-Deckung innerhalb der konfigurierten SoC-Grenzen.
- **FR16:** Solalex wechselt zur Laufzeit deterministisch zwischen Modi mit Hysterese (z. B. Drossel aktiv ab SoC ≥ 97 %, deaktiv erst bei SoC ≤ 93 %).
- **FR17:** Solalex verifiziert jeden Steuerbefehl per Closed-Loop-Readback.
- **FR18:** Solalex geht bei Kommunikations-Ausfall in einen deterministischen Fail-Safe-Zustand (letztes bekanntes Limit halten, nicht freigeben).
- **FR19:** Solalex respektiert hardware-spezifische Rate-Limits zur EEPROM-Schonung (Default ≤ 1 Schreibbefehl pro Device/Minute, per Device-Template überschreibbar).
- **FR20:** Nutzer kann Nacht-Entlade-Zeitfenster konfigurieren.

**Akku-Management**
- **FR21:** Solalex abstrahiert mehrere Akkus als internen Pool mit Gleichverteilung in v1 (Marstek Venus Multi, Anker Solix, Generic).
- **FR22:** Nutzer konfiguriert Min-SoC und Max-SoC pro Akku-Setup.
- **FR23:** Solalex zeigt SoC pro Einzel-Akku und aggregiert für den Pool.

**Monitoring & Dashboard**
- **FR24:** Nutzer sieht im Dashboard den aktuellen Euro-Wert der gesteuerten Ersparnis als 2-Sekunden-Kernaussage.
- **FR25:** Nutzer sieht die Beleg-KPIs (kWh selbst verbraucht + kWh selbst gesteuert) getrennt ausgewiesen, nicht aggregiert.
- **FR26:** Nutzer kann den Bezugspreis (Default 30 ct/kWh) im Dashboard jederzeit anpassen.
- **FR27:** Solalex attribuiert Steuerbefehle mit Event-Source-Flag (`solalex` / `manual` / `ha_automation`) und nutzt dies als Basis der KPI-Berechnung.
- **FR28:** Nutzer sieht den aktuellen Regelungs-Modus (Drossel / Speicher / Multi) im Dashboard.
- **FR29:** Solalex zeigt einen sichtbaren „aktiver Idle-State"-Zustand, wenn keine Steuerung nötig ist.
- **FR30:** Solalex zeigt Charakter-Zeilen bei eigenem Tun und Fakten bei Zahlen (strikt getrennt). *Kippbar → Fallback Neutral-Mode.*

**Diagnose & Support**
- **FR31:** Solalex protokolliert die letzten 100 Regelzyklen (Zeitstempel, Sensorwert, gesetztes Limit, Latenz, Modus).
- **FR32:** Solalex zeigt die letzten 20 Fehler/Warnungen mit Klartext-Beschreibung.
- **FR33:** Solalex zeigt die aktuellen Verbindungs-Stati (HA WebSocket, konfigurierte Entities, Lizenz-Status).
- **FR34:** Solalex misst die End-to-End-Regelungs-Latenz pro Device automatisch (Befehl-Auslösung → messbarer Effekt am Smart Meter) und loggt sie in SQLite.
- **FR35:** Nutzer kann Diagnose-Daten als strukturierten Bug-Report exportieren. *Kippbar → Fallback HA-Panel-Log-Download.*
- **FR36:** Solalex stellt ein strukturiertes Bug-Report-Template in GitHub Issues bereit (Hardware-/Firmware-Felder, Log-/Diagnose-Export-Platzhalter).

**Updates & Administration**
- **FR37:** Solalex wird über den HA Add-on Store aktualisiert (manueller oder Nutzer-aktivierter Auto-Update).
- **FR38:** Solalex sichert vor jedem Update `solalex.db`, `license.json` und `templates/` in `/data/.backup/vX.Y.Z/` (letzte 5 Stände).
- **FR39:** Nutzer kann bei fehlgeschlagenem Update manuell auf eine ältere Version zurückrollen; Solalex stellt `.backup/` automatisch wieder her.
- **FR40:** Solalex unterstützt die aktuelle Home-Assistant-Version und deklariert die supported Range in `addon.yaml`.

**Branding & UI-Identität**
- **FR41:** Solalex nutzt in allen UI-Flächen durchgängig das ALKLY-Design-System (Farben, DM Sans, Spacing/Radius/Elevation-Tokens).
- **FR42:** Solalex erscheint im HA-Sidebar mit ALKLY-Branding (Icon + Name „Solalex by ALKLY").
- **FR43:** UI ist im HA-Ingress-Frame eingebettet und adaptiert HA-Theme-Modi (Dark/Light) ohne Bruch der ALKLY-Farbidentität.

**Total FRs: 43** (davon 4 explizit kippbar: FR12, FR30, FR35, plus FR34-UI-Anzeige als Nebenbedingung).

### Non-Functional Requirements

Zur Traceability werden die NFRs (im PRD als Bullet-Listen geführt) hier laufend nummeriert.

**Performance**
- **NFR1:** Regel-Zyklus-Dauer ≤ 1 s vom Sensor-Event bis Command-Dispatch (interne Verarbeitung).
- **NFR2:** Dashboard Time-to-First-Data-Display ≤ 2 s ab Klick in Sidebar.
- **NFR3:** Setup-Wizard Auto-Detection ≤ 5 s bei durchschnittlichem HA-Setup.
- **NFR4:** Funktionstest-Durchführung ≤ 15 s (inkl. Readback).
- **NFR5:** Memory Footprint ≤ 150 MB RSS im Idle, ≤ 300 MB RSS im Setup-Wizard-Peak.
- **NFR6:** CPU Footprint auf Raspberry Pi 4 ≤ 2 % Idle, ≤ 15 % Regelungs-Burst.
- **NFR7:** E2E-Regelungs-Latenz hardware-abhängig (5–90 s); keine Zusagen-Wert, aber Messung ist Pflicht (FR34), Garantie ist Transparenz.

**Reliability & Availability**
- **NFR8:** Wiederanlauf-Zeit ≤ 2 Min nach HA-/Add-on-Neustart.
- **NFR9:** 24-h-Dauertest als Launch-Gate: 0 unbehandelte Exceptions, keine Schwingungen, keine unkontrollierten Einspeisungen unter Lastprofil `load_profile_sine_wave.csv` (0–3.000 W).
- **NFR10:** 0 kritische Bugs zum Launch (Datenverlust / unkontrollierter Stromfluss / Add-on-Absturz ohne Wiederanlauf < 2 min).
- **NFR11:** Fail-Safe bei Kommunikationsausfall: deterministischer Safe-State (letztes Limit halten).
- **NFR12:** Lizenz-Offline-Toleranz 14 Tage Graceful Period, danach Funktions-Drossel (kein Stopp ohne Vorwarnung).

**Security**
- **NFR13:** Container-Isolation: HA Add-on Sandbox, keine externen Port-Expositionen (nur über HA Ingress).
- **NFR14:** Auth: `SUPERVISOR_TOKEN` als alleiniger Mechanismus gegenüber HA; keine eigene Nutzer-Verwaltung.
- **NFR15:** Lizenz-Signatur kryptografisch verifiziert beim Start (`/data/license.json`).
- **NFR16:** Ausgehende Verbindungen nur HTTPS (LemonSqueezy); kein Plaintext, keine ungeprüften Endpunkte.
- **NFR17:** Keine Telemetry ohne Opt-in; Zero default-tracking.
- **NFR18:** Installations-Disclaimer als sichtbare Checkbox vor Lizenz-Aktivierung (deckt auch FR4).

**Privacy & Data Protection**
- **NFR19:** 100 % lokaler Betrieb: alle Regelungs-, Sensor- und Konfigurationsdaten bleiben in `/data/` auf dem HA-Host.
- **NFR20:** Einzige Drittland-Interaktion LemonSqueezy-Lizenzprüfung (USA, Merchant of Record).
- **NFR21:** Datenminimierung bei Lizenzprüfung: nur Lizenz-Token + Add-on-Version, keine Geräte-/Verbrauchsdaten.
- **NFR22:** Privacy-Policy verbindlich in Launch-Doku, im Wizard verlinkt.
- **NFR23:** DSGVO-Compliance durch lokalen Betrieb + keine personenbezogenen Daten im Standard-Flow.

**Usability & Design Quality**
- **NFR24:** ≥ 80 % der Nutzer schließen Setup in < 10 Min ab (Launch-Ziel); Beta-Zwischenziel ≥ 50 % < 10 Min; Akzeptanz ≥ 80 % < 15 Min.
- **NFR25:** Dashboard-Kernaussage (Euro-Wert) in < 2 s erfassbar ohne Scrollen und ohne Interaktion.
- **NFR26:** Design-Quality-Ziel: durchgängiges ALKLY-Design-System, Mikrointeraktionen, max. eine Primär-Aktion pro Screen, responsive Desktop + Tablet, HA-Dark/Light ohne Farb-Bruch; messbar ≥ 4/5 Beta-Tester bestätigen „sieht hochwertig aus".
- **NFR27:** Pull-nicht-Push: keine proaktiven Benachrichtigungen außerhalb des Dashboards (kein E-Mail, Push, HA-Notification).
- **NFR28:** Copy-Richtlinie „Fakten bei Zahlen, Charakter bei Tun" strikt getrennt; Glossar verbindlich (Akku / Wechselrichter / Smart Meter / Setup-Wizard).

**Integration Reliability**
- **NFR29:** HA WebSocket Reconnect mit exponentiellem Backoff (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, automatisches Re-Subscribe.
- **NFR30:** HA-Versions-Kompatibilitätsmatrix in `addon.yaml`; Install-Warning bei inkompatibler HA-Version.
- **NFR31:** Device-Template-Versionierung mit Firmware-Pinning (Marstek/Anker) und versionstoleranten JSON-Key-Adaptern.
- **NFR32:** MQTT (ab v1.5) mindestens QoS 1, Retained Messages für Discovery, Mosquitto-Add-on als Voraussetzung.
- **NFR33:** GitHub Actions Build-Pipeline multi-arch (amd64, aarch64), automatisierte Release-Builds bei Tag-Push.

**Maintainability**
- **NFR34:** Code-Sprachregel: UI/Kommunikation Deutsch, Code-Kommentare Englisch.
- **NFR35:** Modulare Architektur: ein Python-Modul pro Device-Template (`adapters/...`); Core-Regelung in `core/controller.py` hardware-agnostisch.
- **NFR36:** Test-Coverage ≥ 70 % für Regelungs-Kern-Logik, ≥ 50 % gesamt; Adapter-Integration-Tests mit Mock-HA.
- **NFR37:** Strukturiertes Logging (JSON), alle Exceptions mit Kontext.
- **NFR38:** Code-Verständlichkeit (Solo-Dev-Kriterium): jedes Modul in ≤ 30 Min nachvollziehbar.

**Observability**
- **NFR39:** Strukturiertes Logging in `/data/logs/` (JSON, rotiert 10 MB / 5 Dateien).
- **NFR40:** Add-on-Logs zusätzlich im HA-Log-Panel sichtbar.
- **NFR41:** Diagnose-Export als versioniertes JSON-Schema (`solalex-diag-v1.json`).
- **NFR42:** E2E-Latenz-Messung automatisch pro Device, persistent in SQLite (`latency_measurements`-Tabelle).
- **NFR43:** Regelungs-Zyklen mit Source-Flag (`solalex / manual / ha_automation`) für KPI-Attribution (deckt FR27).
- **NFR44:** Health-Status pro konfigurierter HA-Entity (letzte erfolgreiche Kommunikation, Readback-Erfolgsquote).

**Scalability (selektiv)**
- **NFR45:** Device-Template-System muss ≥ 10 weitere Hersteller in v2–v3 erlauben ohne Core-Refactor.
- **NFR46:** LemonSqueezy-Lizenz-API skaliert unproblematisch (Merchant-of-Record-Infrastruktur).
- **NFR47:** Discord + GitHub Issues als selbsttragende Peer-Support-Kanäle (Alex skaliert nicht linear mit Kundenzahl).
- **NFR48:** Bewusst nicht skaliert: Server-Infrastruktur, Multi-Tenancy, DB-Sharding.

**Accessibility (selektiv, nicht Launch-Gate)**
- **NFR49:** Tastatur-Navigation für alle Wizard-Schritte.
- **NFR50:** Farbkontrast im ALKLY-Design-System ≥ WCAG 2.1 AA für Text auf Hintergrund.
- **NFR51:** Post-MVP-Ziel WCAG 2.1 AA gesamt (nicht Launch-Gate).
- **NFR52:** Nicht im MVP: Screen-Reader-Optimierung, Sprachsteuerung, High-Contrast-Mode.

**Localization**
- **NFR53:** MVP Deutsch only.
- **NFR54:** v2 Englisch als erste Zielsprache (NL folgt).
- **NFR55:** i18n-ready ab v1: alle UI-Strings extrahiert in `locales/de.json`, kein Hard-Coding.

**Total NFRs: 55** (nummeriert; im PRD als Bullet-Liste geführt).

### Additional Requirements

**Domain-Requirements / Regulatorik**
- **DR1:** Einspeise-Begrenzung durch WR/Netz-Limits aus HA-Entities — Solalex schreibt nur innerhalb. Für BKW (DE/AT 800 W, CH abhängig) bleibt Durchsetzung beim WR.
- **DR2:** Installations-Disclaimer „Keine Garantien für Hardware-Schäden oder Stromausfälle" als sichtbare Checkbox vor Aktivierung (nicht in AGB versteckt) — deckt FR4/NFR18.
- **DR3:** EU CRA ab 2027: SBOM, Vulnerability-Handling, CE-Konformität als Future-Requirement (v2+).

**Safety & Hardware-Schutz**
- **DR4:** Hardware-spezifisches Rate-Limiting zum EEPROM-Schutz (deckt FR19).
- **DR5:** Closed-Loop-Readback auf allen Schreib-Pfaden (deckt FR17).
- **DR6:** Safe-State bei Kommunikationsausfall = letztes bekanntes WR-Limit halten (deckt FR18/NFR11).
- **DR7:** Nutzer-Leitplanken (Min/Max-SoC, Zeitfenster, HW-Defaults) verhindern schädliche Konfiguration.

**Technical Constraints**
- **TC1:** HA WebSocket API als alleiniger Kanal (`ws://supervisor/core/websocket`, Auth via `SUPERVISOR_TOKEN`), keine Direkt-Hardware-Kommunikation in v1.
- **TC2:** Subscription `subscribe_trigger` auf `state_changed`, Call via `call_service` (`number.set_value`, `switch.turn_on/off`, `button.press`).
- **TC3:** Add-on-Isolation (Container, Alpine 3.19 + Python 3.13).
- **TC4:** Persistenz in `/data/` mit `solalex.db`, `license.json`, `templates/`, `.backup/`, `logs/`.
- **TC5:** HA Ingress als UI-Kanal, kein Port-Expose nach außen.
- **TC6:** Distribution über Custom Add-on Repository `alkly/solalex`, Auto-Updates via Add-on Store, Multi-Arch (amd64/aarch64).

**Integration Requirements**
- **IR1:** LemonSqueezy-Favorit als Merchant of Record; Lizenzprüfung einmalig bei Aktivierung, dann monatlich mit Graceful Degradation.
- **IR2:** MQTT Discovery ab v1.5/v2 als optionaler Upgrade-Pfad (Mosquitto-Add-on vorausgesetzt).

**Geschäftsmodell & Go-to-Market (Beta-Entscheidung offen)**
- **BM1:** Geschäftsmodell noch offen: 30-Tage-Trial (Favorit) vs. Freemium 1-Gerät-Free/Multi-Pro — wird in Beta entschieden, beide Varianten als Toggle im Lizenz-Backend möglich.
- **BM2:** Early-Bird-Preis für erste 50 Käufer; Rabatt-Code für 300 Blueprint-Bestandskunden (deckt FR6).
- **BM3:** Beta-Gates (Woche 6–7): Install ≥ 18/20, Setup < 15 Min ≥ 80 %, Setup < 10 Min ≥ 50 %, NPS > 8, 0 offene kritische Bugs, ≥ 12/20 „würde kaufen".
- **BM4:** Launch-Gates: YouTube-Launch-Video, Newsletter an Blueprint-Kunden, Repo `alkly/solalex` public, Landing-Hinweis „benötigt HA OS/Supervised", Beta-Tester bestätigt „launch-ready".

**Timeline**
- **TL1:** Woche 0 Spike (Marstek-Spike nicht verhandelbar), Wochen 1–6 Build, Wochen 6–7 Beta (20 Tester aus 165 Wartenden, 30 Pre-Auswahl), Woche 8 Launch.

**Innovation-spezifische Kontrakte**
- **IN1:** SetpointProvider-Interface in Woche 1 als Forecast-Naht (Proof-of-Plumbing via Mock-Quelle in Beta, kein echter Forecast in v1).
- **IN2:** Adaptive Regelungs-Strategie (Drossel / Speicher / Multi) mit Hysterese und Mindest-Verweildauer zur Oszillations-Vermeidung (deckt FR13/FR16).
- **IN3:** E2E-Latenz-Messung als adaptive Regelungs-Parameter-Quelle (deckt FR34/NFR42).
- **IN4:** Charakter-Templates statt LLM — lokal, deckt NFR19/NFR28.

### PRD Completeness Assessment

**Stärken**
- Sehr klare Priorisierung: MVP, Kipp-Reihenfolge, „Nicht im MVP"-Liste explizit dokumentiert.
- Launch- und Beta-Gates mit harten Zahlen belegt (Setup-Zeit, NPS, Conversion, Install-Erfolg).
- 4 konkrete User-Journeys mit expliziter Capability-Ableitung + Summary-Section (Traceability zwischen Journey und FR/Capability ist gegeben).
- Safety-/Regulatory-Kapitel ausgeprägt (CRA, DSGVO, EEPROM-Schutz, Closed-Loop-Readback, Disclaimer, §14a).
- KPI-Definition mit klarer Attribution-Regel und Event-Source-Flag (FR27) hebt Hero-KPI über das übliche Dashboard-Niveau.
- Adaptive Regelungs-Strategie ist präzise beschrieben (Drossel/Speicher/Multi + Hysterese + Modus-Wechsel).

**Lücken / Unschärfen für spätere Schritte**
- **Ziel-Euro-Wert pro Haushalt** ist bewusst leer („X €/Monat") — wird erst aus Beta-Woche 6–7 finalisiert. Akzeptabel, muss aber im Epic-Coverage als „offener Wert" auftauchen.
- **Grace Period (Lizenz)**: Einmal im PRD als „14 Tage" (NFR12), einmal als offene Entscheidung in Frontmatter (`openDecisions`). Inkonsistenz — später in Epic-Validation prüfen.
- **Geschäftsmodell (Trial vs. Freemium)** ist für Entwicklung nicht blockierend (Toggle-Architektur), muss aber in den Lizenz-Epics als dual-konfigurierbar verankert sein.
- **Telemetry/Observability**: im Betrieb Null, aber Beta-Feedback-Sammlung (A/B bei Charakter-Templates, „würde kaufen"-Abfrage, E2E-Latenz-Export) braucht einen klaren, opt-in-konformen Kanal.
- **§14a EnWG** wird nur als „v3+"-Ziel genannt; kein aktueller Constraint dokumentiert, ob Solalex mit §14a-Steuerbox-Szenarien interferiert (Netzbetreiber-Dimmsignal vs. Solalex-WR-Limit).
- **Bezugspreis-Konfigurierbarkeit** (FR26) — fehlt Klarheit zu Mehrtarif- und Zeit-Fenster-Logik in v1 (wahrscheinlich nicht enthalten, aber nicht explizit ausgeschlossen).
- **Entities, die Solalex schreibt**: FR17/TC2 referenzieren `number.set_value`, `switch.turn_on/off`, `button.press` — andere Typen (`select`, `input_*`) nicht genannt; je nach HW-Adapter relevant.
- **Rollback-Orchestrierung**: FR39 beschreibt den Rollback-Pfad, aber nicht die Schema-Migrations-Strategie von `solalex.db` (Abwärtskompatibilität zwischen `vX.Y` und `vX-1`).
- **architecture.md ist auffällig dünn (74 Zeilen)** — muss in Step 3 gegen diese Requirements-Fülle geprüft werden.

**Gesamtbild:** PRD ist inhaltlich **sehr reif** und tauglich als Assessment-Basis. Die offenen Punkte sind bewusste Beta-Entscheidungen, keine Konzept-Lücken. Einzige echte Inkonsistenz: Grace Period 14 Tage (NFR12) vs. „offene Entscheidung" im Frontmatter.

## Epic Coverage Validation (Step 3)

Quelle: `_bmad-output/planning-artifacts/epics.md` (vollständig gelesen, 1.589 Zeilen).

### Epic-Struktur (Übersicht)

| Epic | Titel | Stories | FRs claim | ACs-Reife |
|---|---|---|---|---|
| Epic 1 | Add-on Foundation & Branding | 7 (1.1–1.7) | FR1, FR2, FR41, FR42, FR43 | Vollständig |
| Epic 2 | Setup-Wizard & Hardware-Onboarding | 3 (2.1–2.3) | FR7, FR8, FR9, FR11 | Vollständig |
| Epic 3 | Aktive Nulleinspeisung & Akku-Pool | 7 (3.1–3.7) | FR13–FR23 | Vollständig |
| Epic 4 | Diagnose, Latenz, Support-Workflow | 6 (4.1–4.6) | FR31–FR36 | Vollständig |
| Epic 5 | Dashboard mit Euro-Wert & Live-Visualisierung | 7 (5.1–5.7) | FR24–FR30 | Vollständig |
| Epic 6 | Updates, Backup & Add-on-Lifecycle | 4 (6.1–6.4) | FR37–FR40 | **Stubs — ACs offen** ⚠️ |
| Epic 7 | Lizenzierung & Commercial Activation | 5 (7.1–7.5) | FR3–FR6 | Vollständig |

**Total Stories: 39** (davon 4 Stubs in Epic 6).

### Coverage Matrix (PRD FRs ↔ Epics & Stories)

Verified durch Querlesen der Epic-Stories gegen die PRD-FRs:

| FR | Claim im Epic-Doc | Verifizierte Story-Abdeckung | Status |
|---|---|---|---|
| FR1 | Epic 1 | Story 1.1 (Add-on Skeleton mit Custom Repo & Multi-Arch-Build) | ✓ Covered |
| FR2 | Epic 1 | Story 1.2 (Landing-Page-Voraussetzungs-Hinweis + HA-Versions-Range) | ✓ Covered |
| FR3 | Epic 7 | Story 7.2 (LemonSqueezy-Kauf-Flow im Wizard) | ✓ Covered |
| FR4 | Epic 7 | Story 7.1 (Installations-Disclaimer als sichtbare Checkbox) | ✓ Covered |
| FR5 | Epic 7 | Story 7.3 (Signatur-Verif. beim Start) + Story 7.4 (monatliche Re-Validation, 14-Tage-Grace) | ✓ Covered |
| FR6 | Epic 7 | Story 7.2 (Rabatt-Code-Einlösung im Checkout) | ✓ Covered |
| FR7 | Epic 2 | Story 2.1 (Wizard-Shell mit drei Hardware-Pfaden) | ✓ Covered |
| FR8 | Epic 2 | Story 2.2 (Auto-Detection via Device-Template-System) | ✓ Covered |
| FR9 | Epic 2 | Story 2.2 (Live-Werte neben jeder Entity im Wizard) | ✓ Covered |
| FR10 | **Deferred → v1.5** | Nicht im MVP-Scope | ⚠️ Deferred (siehe Finding F-2) |
| FR11 | Epic 2 | Story 2.3 (Funktionstest mit Live-Chart-Dramaturgie + Readback) | ✓ Covered |
| FR12 | **Deferred → v1.5** | Nicht im MVP-Scope (bereits im PRD als kippbar markiert) | ⚠️ Deferred (PRD-konform) |
| FR13 | Epic 3 | Story 3.5 (Adaptive Strategie-Auswahl Drossel/Speicher/Multi) | ✓ Covered |
| FR14 | Epic 3 | Story 3.2 (Drossel-Modus) | ✓ Covered |
| FR15 | Epic 3 | Story 3.4 (Speicher-Modus mit SoC-Grenzen) | ✓ Covered |
| FR16 | Epic 3 | Story 3.5 (Hysterese 97/93 %, Mindest-Verweildauer) | ✓ Covered |
| FR17 | Epic 3 | Story 3.1 (Core-Controller Pipeline inkl. Readback) | ✓ Covered |
| FR18 | Epic 3 | Story 3.7 (Fail-Safe bei Kommunikations-Ausfall) | ✓ Covered |
| FR19 | Epic 3 | Story 3.1 (EEPROM-Rate-Limit im Executor), Story 3.2/3.4 verweisen | ✓ Covered |
| FR20 | Epic 3 | Story 3.6 (Nacht-Entlade-Zeitfenster konfigurierbar) | ✓ Covered |
| FR21 | Epic 3 | Story 3.3 (Akku-Pool-Abstraktion, Gleichverteilung) | ✓ Covered |
| FR22 | Epic 3 | Story 3.6 (Min/Max-SoC-Konfiguration + Plausibilitäts-Checks) | ✓ Covered |
| FR23 | Epic 3 | Story 3.3 (SoC pro Einzel-Akku + Pool-Aggregat) | ✓ Covered |
| FR24 | Epic 5 | Story 5.1 (Dashboard-Shell, Hero-Zone, Euro-Wert in < 2 s) | ✓ Covered |
| FR25 | Epic 5 | Story 5.3 (Beleg-KPIs getrennt ausgewiesen) | ✓ Covered |
| FR26 | Epic 5 | Story 5.2 (Bezugspreis-Anpassung inline per Stepper) | ✓ Covered |
| FR27 | Epic 5 (Daten) + Epic 3 (Writer) | Story 3.1 (Writer) + Story 5.3 (KPI-Berechnung aus Source-Flag) | ✓ Covered |
| FR28 | Epic 5 | Story 5.5 (Aktueller Regelmodus + Wechsel-Animation) | ✓ Covered |
| FR29 | Epic 5 | Story 5.6 (Aktiver Idle-State als positive Aussage) | ✓ Covered |
| FR30 | Epic 5 (kippbar) | Story 5.7 (Charakter-Zeile über Hero + Neutral-Mode-Fallback) | ✓ Covered (kippbar) |
| FR31 | Epic 4 | Story 4.1 (Letzte 100 Regelzyklen aus `control_cycles`) | ✓ Covered |
| FR32 | Epic 4 | Story 4.2 (Letzte 20 Fehler mit Klartext + Handlungsempfehlung) | ✓ Covered |
| FR33 | Epic 4 | Story 4.3 (Verbindungs-Status HA-WS, Entities, Lizenz) | ✓ Covered |
| FR34 | Epic 3 (Messung) + Epic 4 (Auswertung) | Story 3.1 (`latency_measurements`-Log) + Story 4.4 (Median/P95/Max-Auswertung) | ✓ Covered |
| FR35 | Epic 4 (kippbar) | Story 4.5 (Diagnose-Export `solalex-diag-v1.json`) | ✓ Covered (kippbar) |
| FR36 | Epic 4 | Story 4.6 (GitHub-Issues Bug-Report-Template + Direktlink) | ✓ Covered |
| FR37 | Epic 6 | Story 6.1 **Stub** — User-Story vorhanden, ACs fehlen | ⚠️ AC-Gap |
| FR38 | Epic 6 | Story 6.2 **Stub** — User-Story vorhanden, ACs fehlen | ⚠️ AC-Gap |
| FR39 | Epic 6 | Story 6.3 **Stub** — User-Story vorhanden, ACs fehlen | ⚠️ AC-Gap |
| FR40 | Epic 6 + Epic 1 | Story 1.2 (Install-Warning + `addon.yaml`-Range) + Story 6.4 **Stub** | ✓ Partiell (Story 1.2) + ⚠️ AC-Gap (6.4) |
| FR41 | Epic 1 | Story 1.4 (ALKLY-Design-System-Foundation: Tokens + DM-Sans-Pipeline) | ✓ Covered |
| FR42 | Epic 1 | Story 1.5 (HA-Sidebar-Registrierung mit ALKLY-Branding) | ✓ Covered |
| FR43 | Epic 1 | Story 1.6 (HA-Ingress-Frame mit Dark/Light-Adaption + Empty-State) | ✓ Covered |

### Coverage Statistics

- **Total PRD FRs:** 43
- **FRs vollständig in MVP-Epics mit ACs abgedeckt:** 37 (86 %)
- **FRs im MVP-Scope abgedeckt, aber Story-Stubs ohne ACs (Epic 6):** 4 (FR37, FR38, FR39, FR40 ein Teil)
- **FRs nach v1.5 deferred:** 2 (FR10, FR12)
- **Coverage effektiv (inkl. Stubs als „vorgesehen"):** 41 / 43 = **95 % MVP-Scope**, mit expliziter Deferral-Begründung für 2 FRs

### Missing Requirements / Findings

#### Critical Missing Coverage

*Keine FRs komplett fehlend.* Alle 43 FRs sind adressiert (abgedeckt, kippbar oder explizit deferred).

#### High Priority — AC-Gaps (Epic 6 Stubs)

- **F-1 (Epic 6 Stubs — FR37/FR38/FR39/FR40 Teil 2)**: Epic 6 ist im Dokument explizit als „Rohes Epic — Stories als Stubs mit User-Story, ohne detaillierte Acceptance Criteria" markiert. Stories 6.1–6.4 verweisen auf PRD/Architecture, aber ohne Given/When/Then-ACs.
  - **Impact:** Epic 6 ist Launch-relevant (Updates, Backup, Rollback, Versions-Matrix). Ein Rollout ohne Backup/Rollback-Pfad ist für ein kommerzielles HA Add-on kritisch.
  - **Empfehlung:** ACs vor Phase-4-Implementierung ausschreiben — insbesondere Story 6.2 (Backup-Rotation, atomare Semantik) und Story 6.3 (Rollback inkl. **DB-Schema-Rückwärtskompatibilität** — im PRD nicht spezifiziert).
  - **Story 1.2 vs. Story 6.4 Überlappung:** `addon.yaml`-Range wird in beiden behandelt. Story 6.4 sollte die Release-Compatibility-Tests fokussieren, Story 1.2 die initiale Deklaration.

#### Medium Priority — Deferrals zur Überprüfung

- **F-2 (FR10 Deferral ohne PRD-Autorisierung)**: FR10 („Akku-Schritt lautlos überspringen") wurde im Epic-Doc nach v1.5 verschoben. FR10 war im PRD **nicht** in der Kipp-Reihenfolge (FR12, FR30, FR35, FR34-UI-Anzeige) und ist zentral für Journey 3 (Neugier-Nils). Die Logik ist trivial („wenn kein Akku erkannt → Akku-Schritt ausblenden").
  - **Impact:** Nils-Journey verliert einen der „Happy-Path"-Momente. Einsteiger ohne Akku sehen einen toten Wizard-Schritt, was gegen die UX-Regel „max. eine primäre Aktion pro Screen, keine toten Schritte" verstößt.
  - **Empfehlung:** FR10 in Epic 2 Story 2.2 aufnehmen (Akku-Schritt wird geskippt, wenn Auto-Detection kein Akku-Template matcht). Aufwand: ~1 Wizard-Branch.

- **F-3 (FR12 Deferral — konform zur PRD-Kipp-Reihenfolge)**: FR12 (Blueprint-Import) ist im PRD als Kipp-Rang 1 markiert. Epics-Doc setzt die Kippung bereits um.
  - **Impact:** Journey 2 (Beta-Björn) hängt maßgeblich an FR12 — der „sanfte Cut" ist der Kern der Journey. Fallback „manueller JSON-Import" ist UX-schwächer als der Wizard.
  - **Empfehlung:** Bewusste Management-Entscheidung — zu confirmen, dass Björns Journey durch den Fallback ausreichend bedient wird. Sonst vor Beta nachziehen.

#### Low Priority — Inkonsistenzen

- **F-4 (Grace-Period-Definition 14 Tage)**: NFR12 (PRD) und Story 7.4 (Epic) hart-kodieren 14 Tage; PRD-Frontmatter listet Grace Period aber noch unter `openDecisions`. Epic hat die Entscheidung faktisch vollzogen → **Inkonsistenz mit `openDecisions`-Liste**.
  - **Empfehlung:** PRD-Frontmatter `openDecisions` aktualisieren (Grace entschieden: 14 Tage); oder Story 7.4 erneut zur Disposition stellen.

- **F-5 (Geschäftsmodell Trial vs. Freemium — Toggle-Architektur)**: PRD hält BM explizit offen (Beta-Entscheidung). Epic 7 ist BM-agnostisch (nur „Kauf bei LemonSqueezy"). Kein Gap, aber **keine Story** adressiert das „Toggle im Lizenz-Backend"-Feature aus dem PRD (BM1).
  - **Empfehlung:** Entweder Story 7.2/7.3 um Toggle-Fähigkeit (Trial-Timer vs. Sofort-Kauf-Unterscheidung) ergänzen, oder Toggle-Architektur als Architecture-Detail aufnehmen.

- **F-6 (§14a-Steuerbox-Interferenz)**: PRD hat §14a nur als v3+-Ziel. Kein Epic adressiert aktuell, wie Solalex bei gleichzeitiger Netzbetreiber-Dimmung reagiert (Netzbetreiber setzt WR-Limit → konfligiert Solalex?). Niedrige Priorität für MVP, aber erwähnenswert.

#### NFR-Coverage (Kurz-Audit)

Die Epics-Doc listet NFRs explizit in den „Cross-cutting concerns"-Abschnitten pro Epic und nummeriert sie selbst (1–49, leicht abweichend von der PRD-Nummerierung durch Zusammenfassung mehrerer Einzel-Bullets). Stichproben-Check:

| NFR-Thema | Cross-Cutting-Ankerung | Story-Verifikation |
|---|---|---|
| NFR1 ≤ 1 s Regel-Zyklus | Epic 3 | Story 3.1 AC „Pipeline-Gesamtdauer ≤ 1 s" ✓ |
| NFR2 Dashboard TTFD ≤ 2 s | Epic 1 + Epic 5 | Story 1.6 AC + Story 5.1 AC ✓ |
| NFR3 Auto-Detection ≤ 5 s | Epic 2 | Story 2.2 AC ✓ |
| NFR5/6 RAM/CPU-Budget | Epic 1 | Story 1.1 AC (RSS ≤ 150 MB, CPU ≤ 2 %) ✓ |
| NFR9 24-h-Dauertest | Epic 3 | Story 3.7 letzter AC ✓ |
| NFR12 14-Tage-Grace | Epic 7 | Story 7.4 ✓ |
| NFR14 SUPERVISOR_TOKEN | Epic 1 | Story 1.3 AC ✓ |
| NFR15 Lizenz-Signatur | Epic 7 | Story 7.3 ✓ |
| NFR18 Disclaimer-Checkbox | Epic 7 | Story 7.1 ✓ |
| NFR26 ALKLY-Design-System | Epic 1 + Epic 5 | Story 1.4 + Story 5.* ✓ |
| NFR29 WS-Reconnect-Backoff | Epic 1 | Story 1.3 AC ✓ |
| NFR42 `latency_measurements` | Epic 3 | Story 3.1 AC ✓ |
| NFR48/49 i18n | Epic 1 | Story 1.7 ✓ |
| NFR46 Tastatur-Navigation | Epic 2 + Epic 5 | Story 2.1 AC + Story 5.1 AC (Kürzel 1/2/3/4/D/?) ✓ |

**Nicht explizit in einer Story-AC verankert (Cross-cutting-Architektur-Prinzipien):**
- **NFR17 (Keine Telemetry ohne Opt-in, Zero default-tracking)**: Nur in Architektur-Narrativ. Keine Acceptance, die „kein Egress außer LemonSqueezy" testet. **Empfehlung:** Story 1.1 oder Story 7.2 um AC „Outbound-HTTP-Audit: nur `*.lemonsqueezy.com` erreichbar/erwartet" ergänzen.
- **NFR23 (DSGVO-Compliance durch lokalen Betrieb)**: Implicit durch Architektur, nicht durch eine Story garantiert. Low priority, Privacy-Policy-Doku (NFR22) deckt das narrativ.
- **NFR33 (UI Deutsch / Code Englisch)**: Projekt-Standard, keine Story nötig.
- **NFR35 (Test-Coverage ≥ 70 % Kern / ≥ 50 % gesamt)**: Engineering-Meta, keine Story. Sollte in CI/Quality-Gates landen.
- **NFR40 (`solalex-diag-v1.json` Schema-Versionierung)**: Epic 4 Story 4.5 covered ✓, aber Schema-Evolution-Strategie nicht spec'd.

### Summary Step 3

- **FR-Coverage MVP = 95 %** (41/43 FRs). Keine unauffälligen Lücken.
- **Deferrals nachvollziehbar**, mit Ausnahme **F-2 (FR10)** — Empfehlung zur Nachbesserung.
- **Hauptlücke: Epic 6 ist ein AC-Stub** — vor Phase-4-Implementation ist die AC-Ausarbeitung zwingend.
- **NFR-Ankerung überwiegend sauber**, mit kleinen Lücken bei NFR17/NFR23 (Telemetry-/Egress-Audit), die sich durch eine zusätzliche AC in Story 1.1 oder 7.2 schließen ließen.
- **6 Findings** insgesamt (F-1 Critical, F-2 High, F-3/F-4/F-5/F-6 Medium/Low).

## UX Alignment Assessment (Step 4)

### UX Document Status

**Gefunden:** `_bmad-output/planning-artifacts/ux-design-specification.md` (349 Zeilen, Frontmatter `stepsCompleted: [1, 2, 3, 4, 5]`).

- Reife: **Hoch** — Executive Summary, Personas aus PRD-Journeys destilliert, Kern-UX-Prinzipien, Plattform-Strategie (420/768/1200+), Emotional-Journey-Mapping, Anti-Patterns, UX-Patterns mit Inspirations-Referenzen (Apple Fitness, Robinhood, Linear, Tesla, Things 3, Copilot).
- In den Epics sind **30 UX-Design-Requirements (UX-DR1–UX-DR30)** explizit extrahiert und den Epics/Stories zugeordnet — das Coverage-Mapping ist bereits geleistet.

### UX ↔ PRD Alignment

| PRD-Element | UX-Entsprechung | Status |
|---|---|---|
| Personas aus 4 Journeys (Micha, Björn, Nils, Alex) | Vollständig übernommen in „Target Users" | ✓ Aligned |
| Core-KPI Euro-Wert in < 2 s (NFR2/NFR25) | „Defining Experience" und „Moment 1 — 2-Sekunden-Hit" | ✓ Aligned |
| Pull nicht Push (NFR27) | „Experience Principle 4" + Anti-Pattern „keine Push-Notifications" | ✓ Aligned |
| Charakter bei Tun / Fakten bei Zahlen (NFR28, FR30) | Prinzip 2, „Charakter atmet mit den Zahlen" | ✓ Aligned |
| Aktiver Idle-State (FR29) | Design Opportunity F + Moment 4 + Emotional-Journey-Eintrag 14:00 | ✓ Aligned |
| Modus sichtbar (FR28) | Design Opportunity D („Modus-Wechsel inszeniert") + Moment 5 | ✓ Aligned |
| Transparenz-Overlay „Wie berechnet?" | „Trust-Anchors im Dashboard" + PRD-implizit via FR24 | ✓ Aligned, Story 5.1 AC konkretisiert |
| Bezugspreis-Anpassung (FR26) | „Inline-Editing für Bezugspreis" + Pattern „Stepper unter Zahl" | ✓ Aligned, Story 5.2 ✓ |
| „Kein Akku" lautlos übersprungen (FR10) | „Effortless Interaction 2" + Neugier-Nils-Persona | ⚠️ **Konflikt** — Epic hat FR10 nach v1.5 verschoben, UX-Regime setzt MVP voraus |
| Blueprint-Import ein Ja-Klick (FR12) | „Effortless Interaction 3" + Beta-Björn-Journey | ⚠️ **Konflikt** — PRD-konform gekippt, aber UX nennt es als Effortless-Kern-Interaktion |
| Funktionstest als Dramaturgie (FR11) | Design Opportunity C + Moment 2 + UX-DR17 | ✓ Aligned, Story 2.3 setzt es um |
| Disclaimer vor Aktivierung (FR4) | Implizit in Platform-Strategy „Disclaimer vor Aktivierung" | ✓ Aligned, Story 7.1 ✓ |
| 100 % lokal (NFR19) — Assets | Prinzip 6 + DM-Sans-WOFF2-Pipeline + Anti-Pattern „keine Fremd-Fonts via CDN" | ✓ Aligned, Story 1.4 ✓ |
| Accessibility WCAG AA (NFR50) | UX-DR26/UX-DR27 + Anti-Pattern „graue Disabled-Buttons" | ✓ Aligned |
| Deutsch only / i18n-ready (NFR53/NFR55) | Keine explizite UX-Sprachregel, aber konsistent da Copy-Beispiele in DE und Charakter-Templates in `locales/de.json` | ✓ Aligned, Story 1.7 deckt i18n |

**UX-Additionen über PRD hinaus (teilweise nicht als FR formalisiert):**

| UX-Element | PRD-Status | Epics-Status |
|---|---|---|
| Stats-Tab mit Monats-Aggregat („April: 18,40 €") | Impliziert durch KPIs, kein expliziter FR | Story 5.1: Statistik-Tab als Platzhalter „Folgt in v1.5" ⚠️ |
| Tastatur-Kürzel `1/2/3/4/D/?` | Nicht im PRD | UX-DR25, Story 5.1 AC ✓ |
| Optimistic-UI-Rollback | Nicht im PRD | UX-DR24, keine dedizierte Story-AC (nur generische Fehler-Regel) |
| Skeleton-State < 400 ms | NFR nicht ausformuliert | UX-DR19, Story 4.1/5.1 AC erwähnen „Skeleton-Pulse" ✓ |
| Command-Palette | Nicht im PRD | „v2" ausgeflaggt |
| Wizard-Resume nach Unterbrechung | Nicht im PRD | Story 2.1 AC deckt das ✓ |
| Transparenz-Overlay-Formel | Impliziert (FR24 2-s-Kernaussage) | Story 5.1 AC ✓ |
| Bottom-Nav → Left-Nav adaptiv ab 1024 px | Nicht im PRD | UX-DR6, Story 5.1 AC ✓ |
| Activity-Ring / Energy-Ring | Nicht im PRD (Visualisierung) | UX-DR10, Story 5.4 ✓ |
| Flow-Visualisierung mit SVG-Particles | Nicht im PRD | UX-DR11, Story 5.4 ✓ |
| Custom-PV-Ikonographie (keine Feather/Lucide) | Nicht im PRD | UX-DR22, Story 5.4 AC ✓ |

**Bewertung:** UX bringt eine ganze Reihe visueller Innovationen (Energy-Ring, Flow-Visualisierung, Custom-Icons, Transparenz-Overlay, Stats-Kontext), die das PRD nicht als FRs nennt, die aber die Design-Quality-Ziele (NFR26) operationalisieren. Die Epics haben diese sauber als UX-DR-nummerierte Requirements übernommen und den Stories zugeordnet — **UX ↔ Epics-Abdeckung ist vollständig**.

### UX ↔ Architecture Alignment

**Schwerpunkt-Gap.** Die `architecture.md` ist **unvollständig** — nur 74 Zeilen, Frontmatter `stepsCompleted: [1, 2]`. Sie enthält ausschließlich:

1. Requirements Overview (Verweise auf PRD)
2. Technical Constraints (PRD-Fixpunkte)
3. Cross-Cutting Concerns (10 Prinzipien benannt, nicht detailliert)
4. Architektonische Spannungsfelder (5 Fragen **offen**, nicht entschieden)
5. PRD-Rückwirkungen (3 Hinweise)

**Was fehlt (alles Implementierungs-relevant für UX):**

| Architektur-Aspekt | Benötigt für UX | Status in `architecture.md` |
|---|---|---|
| Frontend-Daten-Kontrakt (REST vs. WebSocket-Push) | Flow-Particles, Energy-Ring-Atmen, Live-Chart im Funktionstest, Modus-Wechsel-Animation | ⚠️ **Offen** (als Spannungsfeld benannt) |
| SVG/Canvas-Rendering-Strategie für 60-fps-Flow-Particles auf Pi 4 | UX-DR11, Story 5.4 | ❌ Nicht behandelt |
| Svelte-State-Management (Stores, Kontext) | Dashboard-Live-Updates, Optimistic-UI-Rollback | ❌ Nicht behandelt |
| CSS-Token-Pipeline + Dark/Light-Switch ohne Reload | UX-DR1, UX-DR7, Story 1.6 AC | ❌ Nicht behandelt |
| DM-Sans-WOFF2-Subsetting-Pipeline | UX-DR2, Story 1.4 AC | ❌ Nicht behandelt |
| FastAPI-Route-Schema (Ingress-Path, API-Endpunkte, WebSocket-Topics) | Alle UI-Stories | ❌ Nicht behandelt |
| SQLite-Schema für `control_cycles`, `latency_measurements`, KPI-Aggregate | Story 3.1, 4.1, 4.4, 5.3 | ⚠️ Als „Spannungsfeld" genannt, nicht gelöst |
| Adapter-Pattern für Device-Templates (Python-Protokoll + JSON-Schema) | Epic 2 Story 2.2, Epic 3 alle | ⚠️ Als Cross-Cutting genannt, nicht designt |
| SetpointProvider-Interface-Signatur | Epic 3 Story 3.1 | ⚠️ Prinzip bestätigt, Signatur fehlt |
| Backup-Rotation-Transaktion (atomar, crash-safe) | Epic 6 Story 6.2 | ❌ Nicht behandelt |
| DB-Schema-Migration / Rollback-Kompatibilität | Epic 6 Story 6.3 | ❌ Nicht behandelt |
| HA-WebSocket-Subscription-Layer (Backoff, Re-Subscribe) | Story 1.3 AC | ⚠️ Als Prinzip genannt, kein Design |
| i18n-Wiring zwischen Svelte und FastAPI | Story 1.7 | ❌ Nicht behandelt |
| Responsive-Layout-Engine (3 Breakpoints) | UX-DR5 | ❌ Nicht behandelt |

### Warnings

- **W-1 CRITICAL — Architecture-Doku ist unvollständig.** `architecture.md` ist auf der Project-Context-Stufe stehengeblieben (Frontmatter `stepsCompleted: [1, 2]`). Alle Detail-Designs fehlen: API-Schema, SQLite-Tabellenstruktur, Svelte-State-Management, Adapter-Kontrakt, Backup-Transaktionen, Rollback-Kompatibilität. Ohne diese Arbeit haben die Epic-Stories zwar eine inhaltliche Zielmarke, aber keinen technischen Kontrakt.
  - **Impact auf Phase 4:** Entwicklungs-Tasks (Story-Dev) würden implizite Architekturentscheidungen auf dem Weg treffen — inkonsistent, parallel in mehreren Stories neu erfunden, Rückbau-teuer. Solo-Dev-Risiko.
  - **Empfehlung:** Architecture auf Steps 3+ fortführen BEVOR die ersten Implementierungs-Stories gestartet werden. Pflicht-Komponenten: (a) Frontend-Datenkontrakt (WS/REST), (b) SQLite-Schema für die 3 Haupt-Tabellen, (c) Adapter-Interface + JSON-Template-Schema, (d) SetpointProvider-Signatur, (e) Backup-Rotation-Semantik, (f) DM-Sans-/CSS-Token-Pipeline.

- **W-2 HIGH — UX-Regime ↔ Epic-Deferral FR10 (Kein Akku lautlos)**. UX stützt sich unter „Effortless Interaction 2" und in der Nils-Persona auf diesen Mechanismus. Epic deferriert nach v1.5. Entweder UX anpassen (expliziten „Kein Akku"-Hinweis im Wizard) **oder** FR10 in Epic 2 Story 2.2 nachziehen (geringer Aufwand, Branch-Logik). Ich empfehle Variante B (Nachziehen), wie bereits in Finding F-2 notiert.

- **W-3 HIGH — UX-Regime ↔ Epic-Deferral FR12 (Blueprint-Ja-Klick)**. UX beschreibt den Ein-Klick-Import als Kern der Björn-Journey. Kippung ist PRD-konform (Rang 1), aber die **UX-Dokumentation sollte den Fallback (manueller JSON-Import) explizit durchspielen**, damit die Journey-Qualität für Björn nicht in der Beta scheitert. Sonst Erwartungs-/Realitätsbruch.

- **W-4 HIGH — WebSocket vs. REST-Polling-Spannung**. Die Architektur flaggt WS-Live-Stream als Kipp-Kandidat. UX setzt WS faktisch voraus (Flow-Particles, Atmen, Modus-Wechsel-Animation, Funktionstest-Live-Chart). Bei REST-Polling (2 s) reißt die UX-Qualität. Entscheidung muss vor Phase 4 getroffen und im PRD/Arch verankert werden — **„WS-Live-Stream ist nicht kippbar, wenn die Design-Quality-Ziele NFR26 erreicht werden sollen"**.

- **W-5 MEDIUM — Stats-Tab-Monatsaggregat ist UX-Anker, aber v1.5 in Epic 5**. UX-Emotional-Journey „Monatsende: 18,40 € im April" und Story 5.1 („Statistik-Platzhalter folgt in v1.5") sind inkonsistent in der **Stärke der UX-Behauptung** — UX listet es als emotionalen Anker, Epic schiebt. Empfehlung: entweder Monats-Aggregat als Mini-Feature im MVP (einfache `SUM`-Query) oder UX-Journey um „heute-zentrierte" Narrative kürzen, damit MVP-Erwartung realistisch bleibt.

- **W-6 MEDIUM — Solo-Dev-Code-Complexity vs. UX-Ambition**. UX listet 14 Custom-Components (Hero-Zahl, Charakter-Zeile, Energy-Ring, Flow-Visualisierung, Status-Chips, Bottom-Nav-Glass, Idle-State, Inline-Stepper, Transparenz-Overlay, Funktionstest-Dramaturgie, Modus-Wechsel-Animation, Skeleton, Fehler-Pattern, Footer) plus Custom-PV-Icon-Set (6+ Icons). Mit 8 Wochen Solo-Dev-Budget und Safety-kritischer Regelung (Epic 3) ist das sportlich. Architecture-Dokument sollte eine Komponenten-Reihenfolge / Priorisierungs-Empfehlung geben (welche Komponenten sind MVP-kritisch, welche v1.1-fähig).

- **W-7 LOW — Command-Palette (UX-Pattern, v2)**. UX erwähnt als „v2"; kein MVP-Risiko.

### Summary Step 4

- **UX-Dokument ist reif und detailliert**, UX-DR1–UX-DR30 sind bereits in die Epics übersetzt (gute Kette).
- **UX ↔ PRD**: Alignment hoch, 2 Inkonsistenzen (W-2, W-3) durch Epic-Deferrals verursacht.
- **UX ↔ Architecture**: **Kritische Lücke** — Architecture ist nicht auf dem Reifegrad, den UX und Epics voraussetzen. Das ist der **größte Einzelfaktor**, der die Implementation-Readiness derzeit blockiert.
- **7 Warnings** (W-1 Critical, W-2/W-3/W-4 High, W-5/W-6 Medium, W-7 Low).

## Epic Quality Review (Step 5)

Rigorous check gegen die create-epics-and-stories-Best-Practices: User-Value, Epic-Unabhängigkeit, Story-Abhängigkeiten, AC-Qualität, DB-Timing, Starter-Template.

### Epic-Level Assessment

| Epic | User-Value | Unabhängigkeit | Story-Sizing | AC-Reife | Gesamturteil |
|---|---|---|---|---|---|
| Epic 1 | ✓ Klar (Install + Sidebar + Foundation) | ✓ Steht allein | 7 Stories, OK-Größe | ✓ Given/When/Then durchgehend | 🟢 OK |
| Epic 2 | ✓ Klar (Setup in < 10 Min) | ⚠️ Story 2.3 hat Forward-Dep zu Epic 3 Story 3.1 | 3 Stories, angemessen | ✓ Vollständig | 🟠 Akzeptabel (mit Dependency-Flag) |
| Epic 3 | ✓ Klar („Strom bleibt im Haus") | ✓ Auf Epic 1/2 aufbauend | 7 Stories, gut unterteilt | ✓ Vollständig | 🟢 OK |
| Epic 4 | ✓ Klar (Problem-Diagnose) | ⚠️ Story 4.3 hat „Platzhalter" für Epic 7 | 6 Stories, angemessen | ✓ Vollständig | 🟢 OK (Graceful-Degradation OK) |
| Epic 5 | ✓ Klar (Dashboard-Hero-Moment) | ✓ Auf Epic 1/3 aufbauend | 7 Stories, gut | ✓ Vollständig | 🟢 OK |
| Epic 6 | ✓ Klar (sichere Updates) | ✓ | 4 Stories, aber **alle Stubs** | ❌ Keine detaillierten ACs | 🔴 Nicht implementierungs-ready |
| Epic 7 | ✓ Klar (kommerzielles Produkt) | ✓ Wraps Epic 2 + hook in Epic 4 | 5 Stories, gut | ✓ Vollständig | 🟢 OK |

### 🔴 Critical Violations

- **Q-1 (Epic 6 — alle 4 Stories ohne detaillierte Acceptance Criteria).** Stories 6.1, 6.2, 6.3, 6.4 haben User-Story-Form und Verweis auf PRD, aber keine Given/When/Then. Wortlaut im Dokument: „*Rohes Epic — Stories als Stubs mit User-Story, ohne detaillierte Acceptance Criteria. Auszuarbeiten kurz vor Beta-Start oder in v1.1-Planung.*"
  - **Violation der Best Practice:** „Testable, Specific, Complete Acceptance Criteria".
  - **Remediation:** Story 6.1–6.4 ausschreiben. Mindest-ACs:
    - Story 6.2: atomare Backup-Kopie mit Rotation auf 5 Stände; Schema der `.backup/vX.Y.Z/`-Verzeichnisse; Fehlerpfad bei Speicher-Mangel.
    - Story 6.3: Restore-Schritte bei fehlgeschlagenem Start; **DB-Schema-Downgrade-Kompatibilität** (fehlt komplett im Planungsstand); Nutzer-Kommunikation im Fehlerfall.
    - Story 6.4: konkrete Versions-Syntax in `addon.yaml`; Release-Matrix-Test-Story; Überschneidung mit Story 1.2 auflösen (Story 1.2 legt an, Story 6.4 pflegt das Update-Verhalten).
    - Story 6.1: Auto-Update vs. manual-Update-Schalter im Add-on-Config.

### 🟠 Major Issues

- **Q-2 (Forward-Dependency Epic 2 Story 2.3 → Epic 3 Story 3.1).** Story 2.3 (Funktionstest) setzt ein testweises `number.set_value` oder Akku-Setpoint ab und verifiziert per Readback. Genau diese „Pipeline Sensor → Policy → Executor → Readback" wird aber in Epic 3 Story 3.1 eingeführt. Ohne Story 3.1 kann Story 2.3 technisch nicht abgeschlossen werden.
  - **Violation:** Epic N cannot require Epic N+1 to work (hier Epic 2 → Epic 3).
  - **Impact:** Implementierungs-Reihenfolge Epic 1 → Epic 2 → Epic 3 wäre blockiert. Korrekte Reihenfolge: Epic 1 → Epic 3 Story 3.1 → Rest Epic 2 → Rest Epic 3.
  - **Remediation-Optionen:**
    1. **Bevorzugt:** „Minimal-Executor für Funktionstest" in eine neue Story 1.8 (Epic 1) auslagern — nur `call_service` mit Readback, ohne Policy/Rate-Limit. Story 3.1 erweitert später auf die volle Pipeline.
    2. Alternative: Story 2.3 und Story 3.1 explizit als **Bundle** markieren (müssen gemeinsam implementiert werden).
    3. Implementierungs-Reihenfolge im Sprint-Plan offen dokumentieren (Epic 3 Story 3.1 vor Rest Epic 2).

- **Q-3 (Story 2.2 AC enthält Reference auf Story 3.5 / Hysterese-Detail-Werte).** Story 2.2 Auto-Detection ist sauber, kein Eingriff. Aber die Entscheidung, welcher Modus am Ende läuft (Drossel/Speicher/Multi), fällt in Story 3.5 Strategie-Auswahl. Das Commissioning-Event in Story 2.3 schreibt eine Konfiguration, der konkrete Regelmodus wird aber erst in 3.5 gesetzt. Kein technisches Problem, aber **Erwartungslücke in der AC-Formulierung**: „Solalex übernimmt die Konfiguration in den Regelungs-Zustand" (Story 2.3) — welcher Regelungs-Zustand, wenn Epic 3 noch nicht ausgeliefert?
  - **Remediation:** AC in Story 2.3 um den Null-/Leerzustand ergänzen: „Wenn Epic 3 noch nicht aktiv → Solalex persistiert Konfiguration, aber Regelung pausiert bis Core-Controller verfügbar."

- **Q-4 (Story 4.3 Forward-Reference zu Epic 7 akzeptabel, aber explizit macht es besser).** AC: „bis Epic 7 produktiv wird, ist der Wert `unvalidated` Default". Das ist technisch sauber (Graceful-Degradation), aber die Best-Practice „No forward references" wird formal berührt. Da Epic 4 ohne Epic 7 voll funktionsfähig bleibt (zeigt `unvalidated`, statt Fehler), akzeptabel — als **minor issue** stehen lassen.

### 🟡 Minor Concerns

- **Q-5 (Epic 1 enthält 3 von 7 rein-technischen Foundation-Stories).** Stories 1.3 (WS-Foundation), 1.4 (Design-Token-Pipeline), 1.7 (i18n-Foundation) haben keinen direkten User-Value, sondern sind Enabler.
  - **Best-Practice-Bewertung:** Für ein Greenfield-Add-on mit nur-Supervised-Base-Image ist das legitim („Set up initial project from starter template"-Muster). Epic 1 als Ganzes liefert User-Value (Installation + Sichtbarkeit); die Enabler-Stories sind notwendig.
  - **Minor:** Ein saubererer Ansatz wäre, 1.3/1.4/1.7 als Sub-Tasks in Story 1.1 einzubetten — so bleibt Epic 1 durchgängig user-facing. Nicht kritisch, aber sauberer.

- **Q-6 (Story 1.2 adressiert Landing-Page + `addon.yaml`-Range — zwei Artefakte in verschiedenen Repos).** Die Landing-Page liegt auf alkly.de (separates Projekt), die `addon.yaml`-Deklaration im `alkly/solalex`-Repo. Eine Story über Repo-Grenzen hinweg ist messy.
  - **Remediation:** Story 1.2 in zwei Stories splitten: 1.2a (Landing-Page-Update, Marketing) und 1.2b (`addon.yaml`-Version-Range + Install-Warning-Mechanik).

- **Q-7 (Epic 3 Story 3.3 „Akku-Pool-Abstraktion" ist technisch-infrastrukturell).** Titel und User-Story sind teilweise backend-orientiert. Akzeptabel, aber User-Value liegt in Story 3.4 (Speicher-Modus) und Story 3.5 (adaptive Strategie).
  - **Bewertung:** OK für Epic 3 als Ganzes, kein Eingriff nötig.

- **Q-8 (Story 5.1 AC „In MVP nur Home-Tab populiert; Statistik/Geräte/Einstellungen Platzhalter").** Settings-Tab muss aber mindestens die Einstellungen aus Story 3.6 (Min/Max-SoC, Nacht-Entlade-Zeitfenster) und Story 5.2 (Bezugspreis) aufnehmen. „Platzhalter v1.5" ist misleading — Settings ist MVP-notwendig, nur die darüber hinausgehende Stats-/Devices-Funktionalität ist deferred.
  - **Remediation:** AC präziser formulieren: „Home-Tab voll; Settings-Tab mit MVP-relevanten Einstellungen (Akku-Grenzen, Bezugspreis, Zeitfenster); Statistik/Geräte-Tabs als Platzhalter."

- **Q-9 (Story 5.7 AC Dataflow).** AC sagt Charakter-Templates liegen in `locales/de.json` unter `character.*`-Namespace — gut. Aber die **Regel, wann welcher Template-Satz gezogen wird** (Modus, aktive Zuweisung, Akku-voll-Trigger), ist nicht formalisiert. Könnte zu inkonsistenter Tonalität führen.
  - **Remediation:** AC um State-Machine / Mapping-Regel für Charakter-Template-Auswahl ergänzen.

- **Q-10 (NFR17 „Keine Telemetry" / NFR23 „DSGVO" ohne AC-Verankerung).** Bereits in Step 3 Finding F-6 notiert, hier formalisiert: Architektur-Prinzip ohne Test-Story. Empfehlung: In Story 7.2 oder Story 1.1 eine AC „Outbound-Requests-Audit — nur `*.lemonsqueezy.com` erlaubt" als harte Leitplanke.

### Dependency-Map (Implementation-Order)

Aus den Quality-Findings ergibt sich folgende empfohlene Implementation-Reihenfolge (nicht Epic-Nummernreihenfolge):

```
Epic 1 [1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7]
          ↓
Epic 3 [3.1 (Core Controller — wird in Epic 2.3 benötigt!)]
          ↓
Epic 2 [2.1 → 2.2 → 2.3 (nutzt 3.1)]
          ↓
Epic 3 [3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7]
          ↓                            ↓
Epic 4 [4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6]
          ↓
Epic 5 [5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7]
          ↓
Epic 7 [7.1 → 7.2 → 7.3 → 7.4 → 7.5 (nutzt 4.3)]
          ↓
Epic 6 [6.1 → 6.2 → 6.3 → 6.4] (ACs müssen vorher ausgeschrieben werden!)
```

**Wichtigste Umsortierung:** Epic 3 Story 3.1 **vor** Epic 2 Story 2.3. Sonst ist Epic 2 nicht abschließbar.

### DB/Entity Creation Timing

Check gegen „Tables created only when first needed":

| Tabelle | Story | Timing |
|---|---|---|
| `solalex.db` initialisiert (leer) | 1.1 | ✓ JIT — leer |
| `control_cycles` | 3.1 | ✓ JIT |
| `latency_measurements` | 3.1 | ✓ JIT |
| Settings (min/max SoC, Zeitfenster) | 3.6 | ✓ JIT |
| Bezugspreis | 5.2 | ✓ JIT |
| Disclaimer-Audit-Trail | 7.1 | ✓ JIT |
| `last_validated`-Timestamp | 7.4 | ✓ JIT |
| Wizard-Fortschritt-Persistenz | 2.1 (aus AC) | ✓ JIT |

**Bewertung:** DB-Timing ist sauber JIT. **Gap:** Es gibt kein zentrales Schema-Migration-Konzept — jede Story muss ALTER TABLE / CREATE TABLE IF NOT EXISTS selbst handhaben. Das sollte in Architecture-Doku (W-1) verankert werden: eine einfache Migration-Library (z. B. `yoyo-migrations` oder hand-built Versions-Counter in `schema_migrations`).

### Starter-Template-Check

Architecture definiert Base: HA Add-on Base Image (Alpine 3.19) + Python 3.13 + FastAPI-Skelett + Svelte-Skelett. Story 1.1 setzt diesen Stack auf: Dockerfile (multi-arch), `run.sh`, FastAPI-App, Svelte-Build, SQLite-Init. Das entspricht dem Starter-Template-Pattern. ✓

### Greenfield-Setup-Check

- Initial project setup ✓ (Story 1.1)
- Dev-environment-Konfig → nicht explizit, aber via Dockerfile impliziert
- CI/CD-Pipeline früh ✓ (GitHub Actions in Story 1.1)
- i18n-Foundation früh ✓ (Story 1.7)

### Best-Practices-Compliance Checkliste

| Kriterium | Epic 1 | Epic 2 | Epic 3 | Epic 4 | Epic 5 | Epic 6 | Epic 7 |
|---|---|---|---|---|---|---|---|
| Epic delivers user value | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Epic functions independently | ✓ | ⚠️ (2.3 → 3.1) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Stories appropriately sized | ✓ | ✓ | ✓ | ✓ | ✓ | ⚠️ (Stubs) | ✓ |
| No forward dependencies | ✓ | ❌ (Q-2) | ✓ | ⚠️ (Q-4 tolerable) | ✓ | ✓ | ✓ |
| DB tables created when needed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Clear acceptance criteria | ✓ | ✓ | ✓ | ✓ | ✓ | ❌ (Q-1) | ✓ |
| Traceability to FRs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Summary Step 5

- **1 Critical** (Q-1: Epic 6 ohne ACs).
- **3 Major** (Q-2 Forward-Dep 2.3→3.1, Q-3 AC-Lücke Commissioning-Zustand, Q-4 Tolerable Graceful-Reference Epic 4→7).
- **6 Minor** (Q-5 bis Q-10: Epic-1-Technical-Stories, Story-1.2-Split, Settings-Formulierung, Charakter-Template-Mapping, NFR17-AC-Anker, sonstige Kosmetik).
- **Implementation-Reihenfolge** weicht von Epic-Nummern ab: Epic 3 Story 3.1 gehört vor Epic 2 Story 2.3.
- **Starter-Template-Muster** und **DB-JIT-Creation** sauber eingehalten.

## Summary and Recommendations (Step 6)

### Overall Readiness Status

🟠 **NEEDS WORK** — Planungsstand ist inhaltlich weit fortgeschritten, aber **zwei Blocker** müssen vor Phase-4-Implementierung geschlossen werden:

1. **`architecture.md` ist unvollständig** (74 Zeilen, nur Project-Context-Stufe) — kritische Detail-Designs fehlen (API-Schema, SQLite-Schema, Svelte-State-Management, Adapter-Interface, DM-Sans-/CSS-Pipeline, Backup-Transaktions-Semantik, Rollback-DB-Kompatibilität). Eine Solo-Dev-Implementation ohne diese Arbeit würde dieselben Design-Fragen in mehreren Stories neu beantworten — inkonsistent, rückbau-teuer.
2. **Epic 6 („Updates, Backup & Lifecycle") ist ein AC-Stub** — 4 Stories mit User-Story, aber ohne Given/When/Then. Das ist für ein kommerzielles Add-on mit Safety-kritischer Regelung nicht tragbar: Ein fehlerhaftes Update kann die 14-Tage-Grace-Period nicht sinnvoll schützen, wenn der Rollback-Pfad nicht designt ist.

Wenn diese beiden Punkte adressiert sind, **können** Phase 4 (Implementierung) starten. Alle anderen Findings sind parallel oder im Sprint auflösbar.

### Bestandsaufnahme der Findings

| Kategorie | Anzahl | Davon Critical | Davon High/Major | Davon Medium/Low/Minor |
|---|---|---|---|---|
| Step 3 — FR/Epic-Coverage | 6 | 1 (F-1) | 2 (F-2, F-3) | 3 (F-4, F-5, F-6) |
| Step 4 — UX-Alignment | 7 | 1 (W-1) | 3 (W-2, W-3, W-4) | 3 (W-5, W-6, W-7) |
| Step 5 — Epic-Quality | 10 | 1 (Q-1) | 3 (Q-2, Q-3, Q-4) | 6 (Q-5 – Q-10) |
| **Gesamt** | **23** | **3** | **8** | **12** |

**Die 3 Critical Findings sind effektiv 2 Probleme** (F-1 und Q-1 sind beide die Epic-6-Lücke). W-1 ist die Architecture-Lücke. Also **2 strukturelle Blocker**, 21 ergänzende Findings.

### Critical Issues Requiring Immediate Action

**C-1 (Architecture-Doku vervollständigen, W-1)**
- Architecture-Workflow auf Steps 3+ fortführen.
- Mindest-Deliverables für Phase-4-Start:
  1. Frontend-Datenkontrakt: WebSocket-Live-Push als Standard (REST nur für initiale Hydration) — Entscheidung treffen und verankern (NFR26 und UX-Regime machen WS faktisch zum MVP-Muss, nicht kippbar).
  2. SQLite-Schema für `control_cycles`, `latency_measurements`, `settings`, `license`, `audit_trail` inkl. einfacher Schema-Migration (Versions-Counter in `schema_migrations`).
  3. Adapter-Interface als Python-Protocol + JSON-Template-Schema (JSON-Schema-Datei, versioniert).
  4. SetpointProvider-Interface-Signatur (Default-Noop-Implementation gezeigt).
  5. Backup-Rotation-Semantik (atomar, crash-safe, rotiert auf 5 Stände) + Rollback-DB-Downgrade-Strategie.
  6. DM-Sans-WOFF2-Pipeline + CSS-Token-Struktur (Tailwind-Config + CSS-Custom-Properties-Layer).
  7. Responsive-Layout-Engine 420/768/1200+ (Strategy doc, keine Implementierung).

**C-2 (Epic 6 ACs ausschreiben, F-1/Q-1)**
- Story 6.1 Auto-Update-Schalter: Config-Mechanismus via `addon.yaml` Options + UI-Toggle.
- Story 6.2 Backup-Rotation: atomare Semantik, Fehler bei Speicher-Mangel, Log-Eintrag.
- Story 6.3 Rollback + DB-Downgrade-Kompatibilität (dickster Brocken — braucht Architektur-Input aus C-1.5).
- Story 6.4 `addon.yaml`-Version-Range: konkrete Syntax, Release-Compatibility-Test-Story; Überschneidung mit Story 1.2 eindeutig abgrenzen.

### High-Priority Issues (vor oder im ersten Sprint-Block)

**H-1 (Forward-Dependency Epic 2 → Epic 3, Q-2)**
- Story 3.1 (Core-Controller-Pipeline) **vor** Story 2.3 (Funktionstest) implementieren. Alternative: Minimal-Executor-Story 1.8 anlegen.
- Sprint-Plan muss die Story-Reihenfolge 1.1 → … → 1.7 → 3.1 → 2.1 → 2.2 → 2.3 → 3.2 → … respektieren.

**H-2 (WebSocket-Live-Stream als MVP-Muss, W-4)**
- Im PRD `openDecisions` **streichen**, dass WS kippbar sei. NFR26 + UX-Regime erzwingen WS.
- In Architecture (siehe C-1.1) verankern.

**H-3 (FR10 „Kein Akku lautlos überspringen" zurück in Epic 2 Story 2.2, F-2)**
- Trivialer Branch („wenn keine Akku-Entity-Template matcht → Akku-Wizard-Schritt überspringen"), aber UX-Journey-zentral (Neugier-Nils).
- Deferral-Entscheidung rückgängig machen oder UX-Doc explizit anpassen.

**H-4 (FR12 Blueprint-Import — Fallback-UX ausarbeiten, W-3)**
- Wenn FR12 Kipp-Rang 1 bleibt, muss der Fallback (manueller JSON-Import) in Story 2.2 oder einer neuen Story präzise beschrieben werden. Sonst Beta-Björn-Journey-Bruch.

**H-5 (Grace-Period-Inkonsistenz, F-4)**
- PRD-Frontmatter `openDecisions` aktualisieren: 14 Tage entschieden.
- Sicherstellen, dass Story 7.4 und NFR12 den gleichen Wert haben (ist gegeben).

**H-6 (Commissioning-Null-Zustand AC, Q-3)**
- Story 2.3 AC um „Wenn Core-Controller noch nicht aktiv: Konfiguration persistieren, Regelung pausiert" ergänzen.

### Medium/Low-Priority Issues (können im Implementation-Sprint aufgeräumt werden)

- Story 1.2 in zwei Stories splitten (Landing-Page vs. `addon.yaml`; Q-6).
- Story 5.1 AC präzisieren (Settings-Tab MVP-nötig, nicht Platzhalter; Q-8).
- Story 5.7 Charakter-Template-Auswahlregel spezifizieren (Q-9).
- NFR17/NFR23 als AC in Story 1.1 oder 7.2 verankern (Egress-Audit; F-6/Q-10).
- Geschäftsmodell-Toggle-Architektur entscheiden (Trial vs. Freemium; F-5).
- Solo-Dev-Component-Priorisierung in Architecture dokumentieren (14 UX-Custom-Components; W-6).
- Stats-Tab-Monats-Aggregat: entweder als kleine MVP-Erweiterung aufnehmen oder UX-Journey entschärfen (W-5).
- §14a-Steuerbox-Interferenz: zumindest ein Diagnose-Case vorsehen (F-6).

### Recommended Next Steps

1. **Architecture-Workflow re-aktivieren** (bmad-create-architecture oder vergleichbar): Mindest-Deliverables aus C-1 produzieren. **Zeitbedarf-Schätzung:** 2–4 Tage Solo-Dev.
2. **Epic 6 ACs ausschreiben** (bmad-create-epics-and-stories oder manuell): C-2. **Zeitbedarf:** 0.5–1 Tag.
3. **PRD-Patch für Grace-Period (H-5) und WS-nicht-kippbar (H-2)**: 10 Minuten.
4. **Epic 2 / Epic 3 Sprint-Reihenfolge finalisieren** (H-1) und im Epic-Doc explizit als „Implementation Order" festhalten: 1 Stunde.
5. **FR10-Rückführung (H-3) und FR12-Fallback-UX (H-4)** entscheiden: 2 Stunden.
6. **Medium/Low-Findings** parallel aufräumen oder im jeweiligen Story-Sprint.
7. **Danach:** `bmad-sprint-planning` oder direkt `bmad-dev-story` / `bmad-quick-dev` starten.

### Positive Aspekte (unverändert lassen)

- PRD (736 Zeilen) ist inhaltlich ausgereift, mit klaren Kipp-Reihenfolgen, Launch-/Beta-Gates und exakten KPI-Definitionen.
- UX-Spec (349 Zeilen) ist eine der stärksten Strecken des Planungsstandes — mit klarer Inspirations-Strategie, Anti-Patterns und 30 ausformulierten UX-Design-Requirements.
- Epics 1–5 und 7 haben durchgängig Given/When/Then-ACs in Story-Qualität, die direkt in Dev-Tasks umsetzbar sind.
- FR-Coverage ist bei 95 % MVP-Scope, die verbleibenden 5 % sind explizit deferred-begründet (nicht übersehen).
- Traceability FR ↔ NFR ↔ UX-DR ↔ Epic ↔ Story ist bereits im Epics-Dokument geleistet — außergewöhnlich saubere Vorarbeit.

### Final Note

This assessment identified **23 issues across 3 categories** (Coverage, UX-Alignment, Epic-Quality). **2 davon sind strukturelle Blocker** (Architecture-Lücke + Epic-6-Stubs), **6 sind High-Priority** (Forward-Dep, WS-Entscheidung, FR10-Rückführung, FR12-Fallback, Grace-Period-Konsistenz, Commissioning-Null-Zustand), **12 sind Medium/Low**. Address the 2 blockers and 6 high-priority items before proceeding to implementation. Die Medium-/Low-Findings lassen sich parallel im Sprint-Verlauf adressieren. 

Wenn die 2 Blocker geschlossen sind, ist der Planungsstand **sehr gut** für Phase 4.

**Assessed on:** 2026-04-21 · **Assessor:** bmad-check-implementation-readiness (Claude Opus 4.7)





