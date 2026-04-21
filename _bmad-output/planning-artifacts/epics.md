---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
workflowType: 'epics-and-stories'
project_name: 'Solarbot'
user_name: 'Alex'
date: '2026-04-21'
---

# Solarbot - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for **Solarbot**, decomposing the requirements from the PRD, UX Design Specification and Architecture Decision Document into implementable stories for the MVP (v1).

**Projektname:** Solarbot (Arbeitsname, Markenrechts-Vorbehalt)
**Brand:** ALKLY
**Tagline:** Steuert deinen Solar lokal und sekundengenau.
**Projekttyp:** IoT Embedded / Edge Orchestrator (HA Add-on)
**Sprache:** Deutsch (UI), Englisch (Code-Kommentare)

---

## Requirements Inventory

### Functional Requirements

**Installation & Lizenz**

- **FR1:** Nutzer kann Solarbot als HA Add-on über das Custom Repository `alkly/solarbot` installieren.
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „HA OS oder Supervised" vor dem Download-Schritt.
- **FR3:** Nutzer erwirbt die Lizenz aus dem Setup-Wizard heraus (Weiterleitung zu LemonSqueezy, Rückkehr in den Wizard).
- **FR4:** Nutzer bestätigt vor Lizenz-Aktivierung den Installations-Disclaimer als sichtbare Checkbox.
- **FR5:** Solarbot verifiziert die Lizenz einmalig online bei Aktivierung und monatlich erneut, mit Graceful Degradation bei Offline-Status (14-Tage-Grace).
- **FR6:** Bestandskunden können einen Rabatt-Code (Blueprint-Migration) im Kaufflow einlösen.

**Setup & Onboarding**

- **FR7:** Nutzer wählt im Setup-Wizard zwischen drei Hardware-Pfaden: Hoymiles, Anker, Manuell.
- **FR8:** Solarbot erkennt kompatible HA-Entities automatisch (OpenDTU, Shelly 3EM, Anker Solix, Marstek Venus 3E/D).
- **FR9:** Nutzer sieht Live-Werte neben jedem erkannten Sensor im Wizard zur Bestätigung.
- **FR10:** Solarbot überspringt den Akku-Schritt lautlos, wenn kein Akku erkannt wird.
- **FR11:** Solarbot führt vor Aktivierung einen Funktionstest durch (testweises Setzen von WR-Limit oder Akku-Setpoint, Readback-Prüfung).
- **FR12:** Solarbot erkennt und importiert bestehende Nulleinspeisungs-Blueprint-Automationen inkl. Helfer-Werte (mit expliziter Deaktivierung des alten Blueprints bei Aktivierung). *Kippbar → Fallback manueller JSON-Import.*

**Regelung & Steuerung**

- **FR13:** Solarbot wählt die Regelungs-Strategie je erkanntem Hardware-Setup automatisch (Drossel / Speicher / Multi-Modus).
- **FR14:** Solarbot regelt im Drossel-Modus reaktiv auf Nulleinspeisung per WR-Limit.
- **FR15:** Solarbot lädt im Speicher-Modus Akkus bei PV-Überschuss und entlädt zur Grundlast-Deckung innerhalb der konfigurierten SoC-Grenzen.
- **FR16:** Solarbot wechselt zur Laufzeit deterministisch zwischen Modi mit Hysterese (z. B. Drossel aktiv ab SoC ≥ 97 %, deaktiv erst bei SoC ≤ 93 %).
- **FR17:** Solarbot verifiziert jeden Steuerbefehl per Closed-Loop-Readback.
- **FR18:** Solarbot geht bei Kommunikations-Ausfall in einen deterministischen Fail-Safe-Zustand (letztes bekanntes Limit halten, nicht freigeben).
- **FR19:** Solarbot respektiert hardware-spezifische Rate-Limits zur EEPROM-Schonung (Default ≤ 1 Schreibbefehl pro Device/Minute, per Device-Template überschreibbar).
- **FR20:** Nutzer kann Nacht-Entlade-Zeitfenster konfigurieren.

**Akku-Management**

- **FR21:** Solarbot abstrahiert mehrere Akkus als internen Pool mit Gleichverteilung in v1 (Marstek Venus Multi, Anker Solix, Generic).
- **FR22:** Nutzer konfiguriert Min-SoC und Max-SoC pro Akku-Setup.
- **FR23:** Solarbot zeigt SoC pro Einzel-Akku und aggregiert für den Pool.

**Monitoring & Dashboard**

- **FR24:** Nutzer sieht im Dashboard den aktuellen Euro-Wert der gesteuerten Ersparnis als 2-Sekunden-Kernaussage.
- **FR25:** Nutzer sieht die Beleg-KPIs (kWh selbst verbraucht + kWh selbst gesteuert) getrennt ausgewiesen, nicht aggregiert.
- **FR26:** Nutzer kann den Bezugspreis (Default 30 ct/kWh) im Dashboard jederzeit anpassen.
- **FR27:** Solarbot attribuiert Steuerbefehle mit Event-Source-Flag (`solarbot` / `manual` / `ha_automation`) und nutzt dies als Basis der KPI-Berechnung.
- **FR28:** Nutzer sieht den aktuellen Regelungs-Modus (Drossel / Speicher / Multi) im Dashboard.
- **FR29:** Solarbot zeigt einen sichtbaren „aktiver Idle-State"-Zustand, wenn keine Steuerung nötig ist („Alles im Ziel. Überwache weiter.").
- **FR30:** Solarbot zeigt Charakter-Zeilen bei eigenem Tun und Fakten bei Zahlen (strikt getrennt). *Kippbar → Fallback Neutral-Mode.*

**Diagnose & Support**

- **FR31:** Solarbot protokolliert die letzten 100 Regelzyklen (Zeitstempel, Sensorwert, gesetztes Limit, Latenz, Modus).
- **FR32:** Solarbot zeigt die letzten 20 Fehler/Warnungen mit Klartext-Beschreibung.
- **FR33:** Solarbot zeigt die aktuellen Verbindungs-Stati (HA WebSocket, konfigurierte Entities, Lizenz-Status).
- **FR34:** Solarbot misst die End-to-End-Regelungs-Latenz pro Device automatisch (Befehl-Auslösung → messbarer Effekt am Smart Meter) und loggt sie in SQLite.
- **FR35:** Nutzer kann Diagnose-Daten als strukturierten Bug-Report exportieren. *Kippbar → Fallback HA-Panel-Log-Download.*
- **FR36:** Solarbot stellt ein strukturiertes Bug-Report-Template in GitHub Issues bereit (Hardware-/Firmware-Felder, Log-/Diagnose-Export-Platzhalter).

**Updates & Administration**

- **FR37:** Solarbot wird über den HA Add-on Store aktualisiert (manueller oder Nutzer-aktivierter Auto-Update).
- **FR38:** Solarbot sichert vor jedem Update `solarbot.db`, `license.json` und `templates/` in `/data/.backup/vX.Y.Z/` (letzte 5 Stände).
- **FR39:** Nutzer kann bei fehlgeschlagenem Update manuell auf eine ältere Version zurückrollen; Solarbot stellt `.backup/` automatisch wieder her.
- **FR40:** Solarbot unterstützt die aktuelle Home-Assistant-Version und deklariert die supported Range in `addon.yaml`.

**Branding & UI-Identität**

- **FR41:** Solarbot nutzt in allen UI-Flächen (Dashboard, Setup-Wizard, Diagnose-Tab, Config) durchgängig das ALKLY-Design-System: ALKLY-Farben als Primär-/Sekundär-/Akzent-Palette, DM Sans als Schrift, einheitliche Spacing-/Radius-/Elevation-Tokens.
- **FR42:** Solarbot erscheint im HA-Sidebar mit ALKLY-Branding (Icon + Name „Solarbot by ALKLY").
- **FR43:** UI ist im HA-Ingress-Frame eingebettet und adaptiert HA-Theme-Modi (Dark/Light-Mode-Umschaltung ohne Bruch der ALKLY-Farbidentität).

### NonFunctional Requirements

**Performance**

- **NFR1:** Regel-Zyklus-Dauer ≤ 1 s vom Sensor-Event bis Command-Dispatch (interne Verarbeitung).
- **NFR2:** Dashboard Time-to-First-Data-Display ≤ 2 s ab Klick in Sidebar.
- **NFR3:** Setup-Wizard Auto-Detection ≤ 5 s bei durchschnittlichem HA-Setup.
- **NFR4:** Funktionstest-Durchführung ≤ 15 s (inkl. Readback).
- **NFR5:** Memory Footprint ≤ 150 MB RSS im Idle, ≤ 300 MB RSS im Setup-Wizard-Peak.
- **NFR6:** CPU Footprint ≤ 2 % im Idle, ≤ 15 % im Regelungs-Burst (Raspberry Pi 4).
- **NFR7:** E2E-Regelungs-Latenz hardware-abhängig (5–90 s), Messung ist Pflicht (FR34) — Solarbot garantiert Transparenz über Latenz, keine Latenz-Zusage.

**Reliability & Availability**

- **NFR8:** Wiederanlauf-Zeit ≤ 2 Min nach HA-/Add-on-Neustart (bis Regelung wieder aktiv).
- **NFR9:** 24-h-Dauertest als Launch-Gate (0 unbehandelte Exceptions, keine Schwingungen, keine unkontrollierten Einspeisungen unter `load_profile_sine_wave.csv`, 0–3.000 W).
- **NFR10:** 0 kritische Bugs zum Launch (Datenverlust / unkontrollierter Stromfluss / Absturz ohne Wiederanlauf < 2 min).
- **NFR11:** Deterministischer Safe-State bei Kommunikationsausfall (letztes bekanntes WR-Limit halten, nicht freigeben).
- **NFR12:** Lizenz-Offline-Toleranz 14 Tage Graceful-Period, danach Funktions-Drossel (kein Stopp ohne Vorwarnung).

**Security**

- **NFR13:** Container-Isolation in HA Add-on Sandbox, keine externen Port-Expositionen (nur HA Ingress).
- **NFR14:** SUPERVISOR_TOKEN als alleiniger Auth-Mechanismus gegenüber HA; keine eigene Nutzer-Verwaltung.
- **NFR15:** Lizenz-Signatur kryptografisch verifiziert beim Start (`/data/license.json`).
- **NFR16:** Ausgehende Verbindungen nur HTTPS (LemonSqueezy); kein Plaintext, keine ungeprüften Endpunkte.
- **NFR17:** Keine Telemetry ohne Opt-in (Zero default-tracking).
- **NFR18:** Installations-Disclaimer als sichtbare Checkbox vor Lizenz-Aktivierung.

**Privacy & Data Protection**

- **NFR19:** 100 % lokaler Betrieb — alle Regelungs-, Sensor- und Konfigurationsdaten bleiben in `/data/` auf dem HA-Host.
- **NFR20:** Einzige Drittland-Interaktion = LemonSqueezy-Lizenzprüfung (DSGVO-konformes Merchant-of-Record-Vertragsverhältnis).
- **NFR21:** Datenminimierung bei Lizenzprüfung (nur Lizenz-Token + Add-on-Version, keine Geräte-/Verbrauchsdaten).
- **NFR22:** Privacy-Policy verbindlich in Launch-Dokumentation, im Wizard verlinkt.
- **NFR23:** DSGVO-Compliance durch lokalen Betrieb + keine personenbezogenen Daten im Standard-Flow.

**Usability & Design Quality**

- **NFR24:** Setup-Ziel ≥ 80 % der Nutzer schließen Setup in < 10 Min ab (Launch).
- **NFR25:** Dashboard-Kernaussage (Euro-Wert) in < 2 s erfassbar ohne Scrollen, ohne Interaktion.
- **NFR26:** Durchgängiges ALKLY-Design-System (Farb-Tokens, DM Sans, einheitliche Spacing/Radius/Elevation), Mikrointeraktionen, max. 1 primäre Aktion pro Bildschirm, responsive Layouts, HA-Dark/Light-Mode-Unterstützung; messbar: ≥ 4 von 5 Beta-Testern geben Feedback „sieht hochwertig aus".
- **NFR27:** Pull nicht Push — keine proaktiven Benachrichtigungen außerhalb des Dashboards (kein E-Mail, kein Push, kein HA-Notification).
- **NFR28:** Fakten bei Zahlen, Charakter bei Tun — strikt getrennt; Glossar verbindlich: Akku (nicht Batterie/Speicher), Wechselrichter/WR (bei Erstnennung ausgeschrieben), Smart Meter, Setup-Wizard.

**Integration Reliability**

- **NFR29:** HA WebSocket Reconnect mit exponentiellem Backoff (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, automatisches Re-Subscribe.
- **NFR30:** HA-Version-Kompatibilitäts-Matrix in `addon.yaml` deklariert; Install-Warning bei inkompatibler HA-Version.
- **NFR31:** Device-Template-Versionierung mit Firmware-Pinning (Marstek/Anker); versionstolerante JSON-Key-Adapter.
- **NFR32:** GitHub Actions Build-Pipeline Multi-Arch (amd64, aarch64), automatisierte Release-Builds bei Tag-Push.

**Maintainability**

- **NFR33:** Code-Sprachregel: UI/Kommunikation in Deutsch, Code-Kommentare in Englisch.
- **NFR34:** Modulare Architektur — ein Python-Modul pro Device-Template (`adapters/marstek_venus.py`, `adapters/anker_solix.py`, …); Core-Regelung in `core/controller.py` hardware-agnostisch.
- **NFR35:** Test-Coverage ≥ 70 % für Regelungs-Kern-Logik, ≥ 50 % gesamt; alle Adapter mit Integration-Tests gegen Mock-HA.
- **NFR36:** Strukturiertes JSON-Logging, alle Exceptions mit Kontext.
- **NFR37:** Solo-Dev-Kriterium — jedes Modul in ≤ 30 Min nachvollziehbar.

**Observability**

- **NFR38:** Strukturiertes Logging in `/data/logs/` (JSON, rotiert 10 MB / 5 Dateien).
- **NFR39:** Add-on-Logs zusätzlich im HA-Log-Panel sichtbar (Standard-Add-on-Verhalten).
- **NFR40:** Diagnose-Export als versioniertes JSON-Schema (`solarbot-diag-v1.json`).
- **NFR41:** E2E-Latenz-Messung automatisch pro Device, persistent in SQLite (`latency_measurements`-Tabelle).
- **NFR42:** Regelungs-Zyklen mit Source-Flag (`solarbot` / `manual` / `ha_automation`) für saubere KPI-Attribution (FR27).
- **NFR43:** Health-Status pro konfigurierter HA-Entity (letzte erfolgreiche Kommunikation, Readback-Erfolgsquote).

**Scalability**

- **NFR44:** Device-Template-System muss ≥ 10 weitere Hersteller (Huawei, SMA, Growatt, Fronius, Zendure, …) in v2–v3 ohne Core-Refactor erlauben.
- **NFR45:** LemonSqueezy-Lizenz-API trägt skalierungs-unproblematisch (Merchant-of-Record-Infrastruktur).

**Accessibility (selektiv, nicht Launch-Gate)**

- **NFR46:** Tastatur-Navigation für alle Wizard-Schritte.
- **NFR47:** Farbkontrast im ALKLY-Design-System ≥ WCAG 2.1 AA für Text auf Hintergrund.

**Localization**

- **NFR48:** MVP Deutsch only.
- **NFR49:** i18n-ready ab v1 — alle UI-Strings extrahiert in `locales/de.json`, kein Hard-Coding.

### Additional Requirements

*Aus dem Architecture Decision Document extrahiert — technische und infrastrukturelle Anforderungen, die Epic/Story-Entscheidungen direkt beeinflussen.*

**Starter / Base Image:**

- Kein klassischer Greenfield-Starter. **Base: HA Add-on Base Image (Alpine 3.19)**, aufgestockt auf **Python 3.13**. Impact auf Epic 1 Story 1: Add-on-Gerüst mit `addon.yaml`, `Dockerfile` (multi-arch), `run.sh`, FastAPI-App-Skeleton, Svelte-Skeleton, SQLite-Init.

**Tech-Stack (fixiert, nicht verhandelbar):**

- Backend: Python 3.13 + FastAPI
- Frontend: Svelte + Tailwind (lokal gehostet, kein CDN)
- Datenbank: SQLite in `/data/solarbot.db`
- Integrations-Kanal: HA WebSocket API (`ws://supervisor/core/websocket`) mit `SUPERVISOR_TOKEN` Auth (vom Supervisor automatisch bereitgestellt)

**Distribution & Build:**

- Custom Add-on Repository auf GitHub `alkly/solarbot` (privat → public zum Launch)
- GitHub Actions als Build-Pipeline: Multi-Arch-Build (amd64, aarch64), GitHub Container Registry als Image-Host
- Auto-Update via HA Add-on Store Mechanismus

**Persistenz & Backup:**

- `/data/` als Standard-Add-on-Volume (überlebt Updates und Restart)
- Strukturierte Ablage: `solarbot.db`, `license.json`, `templates/`, `.backup/vX.Y.Z/` (letzte 5 Stände), `logs/` (rotiert 10 MB / 5 Dateien)
- Backup-Rotation vor jedem Update

**Externe Services (einzige Grenze):**

- LemonSqueezy als alleiniger Merchant-of-Record, nur für Lizenz-Aktivierung und monatliche Re-Validierung
- Kein Telemetry-Server, kein Analytics-Endpunkt, kein Crash-Report ohne Opt-in

**Hardware Day-1 Katalog (produktionsreif):**

- Wechselrichter: Hoymiles/OpenDTU
- Akkus: Anker Solix, Marstek Venus 3E/D
- Smart Meter: Shelly 3EM
- Fallback: Generic HA Entity (manueller Pfad)

**Cross-Cutting Patterns (architektonisch zwingend in mehreren Epics):**

- Closed-Loop-Readback + Fail-Safe als durchgängiges Pattern für jeden Steuerbefehl (Epic Regelung)
- Event-Source-Attribution (`source: solarbot | manual | ha_automation`) als Basis aller KPIs (Epic Dashboard + Diagnose)
- E2E-Latenz-Messung pro Device als Input für hardware-spezifische Regel-Parameter (Epic Regelung + Diagnose)
- EEPROM-Rate-Limiting (≤ 1 Schreibbefehl/Device/Minute Default) (Epic Regelung)
- Device-Template-System als JSON-Schema und Erweiterungspunkt (Epic Setup + Adapter-Epic)
- Strukturiertes JSON-Logging (Epic Diagnose)
- i18n-Ready ab v1 — alle UI-Strings in `locales/de.json` (alle UI-Epics)
- Lizenz-Gated Startup mit Signatur-Verifikation (Epic Lizenz)
- Backup-Rotation (letzte 5 Stände) vor jedem Update (Epic Updates)
- ALKLY-Design-System (Token-basiert, Dark/Light-konform) (alle UI-Epics)

**Safety-Grenze (architektonisches Prinzip):**

- Policy/Provider liefern nur Vorschläge, Executor entscheidet mit Veto-Rechten (Range-Check, Rate-Limit, Readback) → Impact auf Regelungs-Epic und SetpointProvider-Interface
- SetpointProvider-Interface in v1 als Naht für v2-Forecast-Erweiterung, Default-Implementation = aktuelles reaktives Verhalten (zero-cost in v1)

**Ressourcen-Budget (Raspberry Pi 4 Referenz):**

- Memory (idle): ≤ 150 MB RSS, (Peak Wizard): ≤ 300 MB RSS
- CPU (idle): ≤ 2 %, (Regelungs-Burst): ≤ 15 %

**Reconnect-Logik (zwingend in HA-WebSocket-Layer):**

- Exponentielles Backoff (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, Re-Subscribe nach Reconnect

### UX Design Requirements

*Aus der UX Design Specification extrahiert — design-seitige Arbeitspakete, die Epic/Story-Entscheidungen direkt beeinflussen.*

**Design-Token-System & Foundation**

- **UX-DR1:** Design-Token-System aufbauen: ALKLY-Farbpalette (Teal/Rot) mit **modus-spezifischer Saturation** für Dark/Light (Teal im Dark mit mehr Glow, Rot im Light mit mehr Sättigung), Primär/Sekundär/Akzent-Rollen.
- **UX-DR2:** DM-Sans-WOFF2-Font-Pipeline lokal im Add-on-Container (4 Weights: Regular/Medium/Semibold/Bold, Latin + Latin-Extended Subset, ~120 kB total) — **keine externen CDN-Requests**, kein `preconnect` auf Google Fonts.
- **UX-DR3:** Spacing-Raster auf 8px-Basis, Radius-Tokens (16px für Cards), 2-Ebenen-Shadow-System, alles als CSS-Custom-Properties.
- **UX-DR4:** Semantische CSS-Klassen statt Hard-Coded-Werte durchgängig (z. B. `.text-hero`, `.status-chip`, `.energy-ring`).

**Responsive Layout & Platform**

- **UX-DR5:** Responsive Layout-System mit 3 Breakpoints (420px Mobile-HA-App / 768px Tablet / 1200px+ Desktop), **Desktop-canonical entworfen**, dann runterskaliert (Bruch mit Mobile-First-Bias des bestehenden internen DS).
- **UX-DR6:** Navigation adaptiv: Bottom-Nav unter 1024px, Left-Nav ab 1024px (identische 4 Reiter Home/Geräte/Statistik/Einstellungen).
- **UX-DR7:** Dark/Light-Mode-Adaption via HA-Theme-Detection ohne Bruch der ALKLY-Identität.

**Kern-Komponenten (reusable UI components)**

- **UX-DR8:** **Hero-Zahl-Component** — Euro-Wert 56–72px DM Sans Bold, tracking -0.02em, Einheit „€" in 60 % Opacity, tap-aktiviertes Transparenz-Overlay mit Formel.
- **UX-DR9:** **Charakter-Zeile-Component** — über Hero, 14px 500-Weight, narrative Regel-Modus-Kette mit Piktogrammen, Teal oder Text-Secondary Farbe.
- **UX-DR10:** **Energy-Ring-Component** — Activity-Ring-Metapher (inspiriert Apple Fitness), Teal für Überschuss, Rot für Bezug, Grau für Neutral, mit Atmen-Animation im Idle.
- **UX-DR11:** **Flow-Visualisierung-Component** — SVG-Paths mit moving particles zwischen PV/Haus/Akku/Netz-Icons, Particle-Geschwindigkeit proportional zur Leistung (inspiriert Tesla-App, 2D-SVG statt 3D).
- **UX-DR12:** **Status-Chip-Component** — 32px Höhe, 12px Radius, Icon 16px + Label 13px, Verwendung für Regelmodus / Verbindung / Lizenz.
- **UX-DR13:** **Bottom-Nav-Glass-Component** — Glassmorphism (92 % Opacity + Blur) als einziges Glas-Element der UI.
- **UX-DR14:** **Idle-State-Component** — sanftes Atmen (60 bpm Puls), Teal-Soft-Background, Charakter-Zeile „Alles im Ziel. Ich überwache weiter."
- **UX-DR15:** **Inline-Stepper-Component** — Bezugspreis-Anpassung durch Tap auf Euro-Zahl, Stepper erscheint unter der Zahl (kein Modal), Enter/Blur speichert.
- **UX-DR16:** **Transparenz-Overlay-Component** — Inline-Panel fährt beim Tap auf Hero-Zahl aus mit Formel + Quelle (keine Modal).
- **UX-DR17:** **Funktionstest-Dramaturgie-Component** — Live-Chart mit 5-s-Fenster, WR-Limit-Verlauf, Netz-Einspeisung, SoC; Readback als Checkmark-Animation mit Spring-Easing.
- **UX-DR18:** **Modus-Wechsel-Animation-Component** — Ring-Farbe-Shift, Badge-Rotation, kurzer Status-Text für Drossel ↔ Speicher ↔ Multi.
- **UX-DR19:** **Skeleton-State-Component** — grauer Pulse für Lade-Zustände < 400 ms (Spinner verboten).
- **UX-DR20:** **Fehler-Pattern-Component** — jeder Fehler enthält Handlungsempfehlung; keine nackten roten Meldungen ohne Kontext.
- **UX-DR21:** **Footer-Component** — Alex-Kly-Micro-Avatar 24px rund + „Made by Alex Kly · Discord · GitHub · Privacy" + dezentes „100 % lokal"-Badge.

**Custom-Assets**

- **UX-DR22:** Custom PV-Ikonographie — eigene SVG-Icons in 1,5px-Stroke für Wechselrichter, Akku, Smart Meter, Shelly, Marstek-Silhouette, Hoymiles-Typ (konsistent mit DM-Sans-Geometrie, inline eingebettet, keine Feather/Lucide-Stock-Icons).

**Interaktion & Animation**

- **UX-DR23:** Mikro-Animationen: Cubic-Bezier-Easing mit leichtem Overshoot `(0.34, 1.56, 0.64, 1)` für Toggles, Stagger-Delays 50 ms in Listen, Puls auf genau einem Live-Status-Dot pro Screen, **keine Animation > 1200 ms**.
- **UX-DR24:** Optimistic-UI-Pattern — Toggle schaltet sofort um, WebSocket-Bestätigung nachträglich, Rollback bei Failure mit sanfter Animation + Fehler-Zeile.
- **UX-DR25:** Tastatur-Kürzel — `1/2/3/4` für Haupt-Views, `D` öffnet Diagnose, `?` zeigt Shortcut-Referenz (Linear-Stil für Alex/Björn).

**Accessibility**

- **UX-DR26:** Tastatur-Navigation für alle Wizard-Schritte voll funktional.
- **UX-DR27:** Farbkontrast-Audit ≥ WCAG 2.1 AA für Text auf Hintergrund in beiden Theme-Modi (Dark + Light).

**Special Routes / View-Regie**

- **UX-DR28:** Diagnose-Route bewusst abgesetzt („Für Fortgeschrittene", nicht in Bottom-Nav), erreichbar über Settings → „Diagnose öffnen"; einsteiger-geschützt mit freundlicher Einleitungszeile und prominentem Export-Button.
- **UX-DR29:** Setup-Wizard als linear-fokussiertes UX-Regime (bildschirmfüllend, **eine primäre Aktion pro Screen**) vs. Dashboard als parallel-modulares UX-Regime — einheitliche Tokens, unterschiedliche Komposition.

**Anti-Pattern-Durchsetzung**

- **UX-DR30:** Anti-Patterns als Lint-/Review-Regeln durchsetzen: keine Tabellen, keine Modal-Dialoge, keine Tooltips, keine technischen IDs sichtbar, keine Gamification (Badges/Streaks/Achievements), keine Loading-Spinner, keine grauen Disabled-Buttons, keine Gradients/Glassmorphism außerhalb der Bottom-Nav, keine „Neu"-Badges, keine Announcement-Banner, keine Push-Notifications.

### FR Coverage Map

| FR | Epic | Thema |
|---|---|---|
| FR1 | Epic 1 | Installation via Custom Add-on Repository `alkly/solarbot` |
| FR2 | Epic 1 | Landing-Page HA-OS/Supervised-Voraussetzungs-Hinweis |
| FR3 | Epic 7 | LemonSqueezy-Kauf-Flow im Wizard |
| FR4 | Epic 7 | Installations-Disclaimer als sichtbare Checkbox |
| FR5 | Epic 7 | Monatliche Lizenz-Verifikation mit 14-Tage-Grace |
| FR6 | Epic 7 | Rabatt-Code-Einlösung (Blueprint-Migration) |
| FR7 | Epic 2 | Drei Hardware-Pfade im Wizard (Hoymiles/Anker/Manuell) |
| FR8 | Epic 2 | Auto-Detection kompatibler HA-Entities |
| FR9 | Epic 2 | Live-Werte neben jedem erkannten Sensor |
| FR10 | **v1.5 / deferred** | Lautloses Überspringen des Akku-Schritts (aus MVP verschoben) |
| FR11 | Epic 2 | Funktionstest mit Readback vor Commissioning |
| FR12 | **v1.5 / deferred** | Blueprint-Automation-Import (aus MVP verschoben, war bereits kippbar) |
| FR13 | Epic 3 | Automatische Regelungs-Strategie-Wahl (Drossel/Speicher/Multi) |
| FR14 | Epic 3 | Drossel-Modus auf Nulleinspeisung per WR-Limit |
| FR15 | Epic 3 | Speicher-Modus mit Lade-/Entlade-Logik in SoC-Grenzen |
| FR16 | Epic 3 | Deterministischer Modus-Wechsel mit Hysterese |
| FR17 | Epic 3 | Closed-Loop-Readback für jeden Steuerbefehl |
| FR18 | Epic 3 | Fail-Safe bei Kommunikations-Ausfall |
| FR19 | Epic 3 | EEPROM-Rate-Limiting je Device-Template |
| FR20 | Epic 3 | Konfigurierbare Nacht-Entlade-Zeitfenster |
| FR21 | Epic 3 | Akku-Pool-Abstraktion mit Gleichverteilung |
| FR22 | Epic 3 | Min/Max-SoC-Konfiguration |
| FR23 | Epic 3 | SoC-Anzeige pro Einzel-Akku + Pool-Aggregat |
| FR24 | Epic 5 | Euro-Wert der gesteuerten Ersparnis als Dashboard-Hero |
| FR25 | Epic 5 | Beleg-KPIs (kWh selbst verbraucht + kWh selbst gesteuert) |
| FR26 | Epic 5 | Bezugspreis-Anpassung inline im Dashboard |
| FR27 | Epic 5 | Event-Source-Flag als KPI-Attribution-Basis |
| FR28 | Epic 5 | Aktueller Regelungs-Modus im Dashboard |
| FR29 | Epic 5 | Aktiver Idle-State als positive Aussage |
| FR30 | Epic 5 | Charakter-Zeilen bei eigenem Tun (kippbar, Fallback Neutral-Mode) |
| FR31 | Epic 4 | Protokoll der letzten 100 Regelzyklen |
| FR32 | Epic 4 | Letzte 20 Fehler/Warnungen mit Klartext |
| FR33 | Epic 4 | Verbindungs-Stati (HA-WS, Entities, Lizenz) |
| FR34 | Epic 4 | E2E-Regelungs-Latenz-Messung pro Device |
| FR35 | Epic 4 | Diagnose-Export als strukturierter Bug-Report (kippbar) |
| FR36 | Epic 4 | GitHub-Issues Bug-Report-Template |
| FR37 | Epic 6 | Updates über HA Add-on Store |
| FR38 | Epic 6 | Backup vor Update in `/data/.backup/vX.Y.Z/` (letzte 5 Stände) |
| FR39 | Epic 6 | Manueller Rollback mit automatischer Backup-Wiederherstellung |
| FR40 | Epic 6 | HA-Version-Range in `addon.yaml` deklariert |
| FR41 | Epic 1 | Durchgängiges ALKLY-Design-System |
| FR42 | Epic 1 | ALKLY-Branding im HA-Sidebar |
| FR43 | Epic 1 | HA-Ingress-Frame mit Dark/Light-Mode-Adaption |

**Coverage:** 41 / 43 FRs im MVP-Scope abgedeckt · 2 FRs (FR10, FR12) explizit nach v1.5 verschoben ✓

## Epic List

### Epic 1: Add-on Foundation & Branding

**User-Outcome:** Solarbot ist über das Custom Repository installierbar, im HA-Sidebar sichtbar, gebrandet, mit ALKLY-Design-System-Foundation und tragfähiger HA-WebSocket-Verbindung. Keine Lizenz-Gate — Add-on startet und ist für Entwicklung und Beta-Test nutzbar.

**FRs covered:** FR1, FR2, FR41, FR42, FR43

**Cross-cutting concerns begründet hier:** Container-Isolation (NFR13), SUPERVISOR_TOKEN-Auth (NFR14), HA-WS-Reconnect mit exponentiellem Backoff (NFR29), Design-System-Foundation (NFR26, UX-DR1–UX-DR7), Multi-Arch-Build via GitHub Actions (NFR32), Ressourcen-Budget Pi 4 (NFR5, NFR6), lokale DM-Sans-Font-Pipeline (UX-DR2), i18n-ready ab v1 (NFR49).

### Epic 2: Setup-Wizard & Hardware-Onboarding

**User-Outcome:** Nutzer schließt den Wizard in < 10 Min ab. Hardware ist auto-detektiert (Hoymiles/OpenDTU/Anker/Marstek/Shelly), Live-Werte sind bestätigt, der Funktionstest hat per Closed-Loop-Readback bewiesen, dass Steuerung funktioniert. Zustand danach: „Solarbot weiß, was er steuert." *Hinweis: „Aktivieren" am Ende des Wizards bedeutet Commissioning (Inbetriebnahme), nicht Lizenz-Aktivierung — die Lizenz-Schale kommt in Epic 7.*

**FRs covered (MVP):** FR7, FR8, FR9, FR11

**Explicitly deferred nach v1.5:** FR10 (lautloses Überspringen Akku-Schritt), FR12 (Blueprint-Automation-Import)

**Cross-cutting concerns begründet hier:** Device-Template-System als JSON-Schema (Architecture), Closed-Loop-Readback im Funktionstest, Wizard-UX-Regime „linear, 1 Aktion pro Screen" (UX-DR29), Funktionstest-Dramaturgie mit Live-Chart (UX-DR17), Auto-Detection-Performance ≤ 5 s (NFR3), Tastatur-Navigation für Wizard (NFR46, UX-DR26).

### Epic 3: Aktive Nulleinspeisung & Akku-Pool-Steuerung

**User-Outcome:** Solarbot regelt produktiv mit adaptiver Strategie (Drossel / Speicher / Multi-Modus), Akku-Pool-Abstraktion mit Gleichverteilung, Hysterese-basierten Modus-Wechseln, Closed-Loop-Readback und Fail-Safe. Zustand danach: „Solarbot arbeitet — der Strom bleibt im Haus."

**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23

**Cross-cutting concerns begründet hier:** SetpointProvider-Interface mit Default-Noop als zero-cost v2-Forecast-Naht (Architecture), Event-Source-Attribution `source: solarbot | manual | ha_automation` als KPI-Basis (NFR42), EEPROM-Rate-Limiting Default ≤ 1 Schreibbefehl/Device/Minute (FR19), E2E-Latenz-Messung pro Device als Input für Regel-Parameter (FR34, wird in Epic 4 ausgewertet), Safety-Grenze „Policy schlägt vor / Executor entscheidet mit Veto: Range-Check + Rate-Limit + Readback" (Architecture), Regel-Zyklus ≤ 1 s (NFR1), Fail-Safe mit letztem bekannten WR-Limit (NFR11), 24-h-Dauertest als Launch-Gate (NFR9).

### Epic 4: Diagnose, Latenz-Messung & Support-Workflow

**User-Outcome:** Alex bekommt mit einem Klick einen strukturierten Diagnose-Export von einem Beta-Tester. Nutzer sieht Verbindungs-Status, letzte 100 Regelzyklen, letzte 20 Fehler, E2E-Latenz pro Device. GitHub-Issues hat ein Bug-Report-Template mit Hardware-/Firmware-Feldern. Zustand danach: „Wenn etwas hakt, kann es sauber gemeldet werden."

**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36

**Cross-cutting concerns begründet hier:** Strukturiertes JSON-Logging rotiert 10 MB / 5 Dateien (NFR36, NFR38), Diagnose-Export als versioniertes Schema `solarbot-diag-v1.json` (NFR40), E2E-Latenz persistent in SQLite `latency_measurements`-Tabelle (NFR41), Health-Status pro Entity mit Readback-Erfolgsquote (NFR43), Diagnose-Route bewusst abgesetzt („Für Fortgeschrittene", einsteiger-geschützt, UX-DR28), Fehler-Pattern mit Handlungsempfehlung (UX-DR20).

### Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung

**User-Outcome:** Nutzer öffnet Dashboard und sieht in < 2 s die Euro-Kernaussage. Beleg-KPIs, Regelmodus, Idle-State, Energy-Ring und Flow-Visualisierung machen die Arbeit von Solarbot sichtbar. Zustand danach: „Solarbot beweist seinen Wert sichtbar."

**FRs covered:** FR24, FR25, FR26, FR27, FR28, FR29, FR30

**Cross-cutting concerns begründet hier:** Dashboard-TTFD ≤ 2 s (NFR2, NFR25) als Produkt-Versprechen, 14 Kern-Komponenten aus UX-Spec (Hero-Zahl UX-DR8, Charakter-Zeile UX-DR9, Energy-Ring UX-DR10, Flow-Visualisierung UX-DR11, Status-Chips UX-DR12, Bottom-Nav-Glass UX-DR13, Idle-State UX-DR14, Inline-Stepper UX-DR15, Transparenz-Overlay UX-DR16, Modus-Wechsel-Animation UX-DR18, Skeleton-State UX-DR19, Fehler-Pattern UX-DR20, Footer UX-DR21), Custom-PV-Ikonographie in 1,5 px-Stroke (UX-DR22), Mikro-Animationen mit Cubic-Bezier (UX-DR23), Optimistic-UI (UX-DR24), Tastatur-Kürzel 1/2/3/4/D/? (UX-DR25), Anti-Pattern-Durchsetzung (UX-DR30), Pull nicht Push (NFR27), Fakten/Charakter-Trennung (NFR28).

### Epic 6: Updates, Backup & Add-on-Lifecycle

**User-Outcome:** Updates verlaufen reibungslos via Add-on Store. Vor jedem Update wird automatisch ein rotierendes Backup angelegt (letzte 5 Stände). Bei fehlgeschlagenem Update kann manuell zurückgerollt werden. HA-Versions-Range ist deklariert. Zustand danach: „Solarbot bleibt über Wochen wartbar — auch wenn ein Update mal hakt."

**FRs covered:** FR37, FR38, FR39, FR40

**Cross-cutting concerns begründet hier:** Backup-Rotation vor jedem Update auf `/data/.backup/vX.Y.Z/` (Architecture), HA-Version-Compatibility-Matrix in `addon.yaml` mit Install-Warning (NFR30), Multi-Arch-Release-Build bei Tag-Push via GitHub Actions (NFR32, ergänzt Epic 1), Wiederanlauf ≤ 2 Min nach Neustart (NFR8), versionstolerante Adapter mit Firmware-Pinning (NFR31).

### Epic 7: Lizenzierung & Commercial Activation

**User-Outcome:** Solarbot wird zum kommerziellen Produkt. LemonSqueezy-Kauf-Flow im Wizard, Installations-Disclaimer als Checkbox vor Aktivierung, Lizenz-Signatur-Verifikation beim Start, monatliche Re-Validation mit 14-Tage-Grace, Rabatt-Code für Blueprint-Bestandskunden. Zustand danach: „Solarbot ist launch-ready."

**FRs covered:** FR3, FR4, FR5, FR6

**Cross-cutting concerns begründet hier:** Lizenz-Signatur kryptografisch verifiziert beim Start (NFR15), Installations-Disclaimer als sichtbare Checkbox (NFR18), 14-Tage-Grace-Period bei Offline (NFR12), LemonSqueezy als einzige Drittland-Interaktion HTTPS-only (NFR16, NFR20), Datenminimierung bei Lizenzprüfung (nur Token + Version, NFR21), Privacy-Policy verbindlich im Wizard verlinkt (NFR22), Graceful Degradation ohne abruptes Stoppen (NFR12).

---

## Epic 1: Add-on Foundation & Branding

Solarbot ist über das Custom Repository installierbar, im HA-Sidebar sichtbar, gebrandet, mit ALKLY-Design-System-Foundation und tragfähiger HA-WebSocket-Verbindung. Keine Lizenz-Gate — Add-on startet und ist für Entwicklung und Beta-Test nutzbar.

### Story 1.1: Add-on Skeleton mit Custom Repository & Multi-Arch-Build

As a Entwickler,
I want ein lauffähiges HA Add-on-Gerüst im Custom Repository `alkly/solarbot` mit Multi-Arch-Docker-Build,
So that Solarbot über den HA Add-on Store installierbar ist und das Fundament für alle weiteren Features trägt.

**Acceptance Criteria:**

**Given** das Repository `alkly/solarbot`
**When** Code gepusht und getaggt wird
**Then** GitHub Actions baut Docker-Images für `amd64` + `aarch64` und publisht sie in GitHub Container Registry
**And** Release-Builds werden bei Tag-Push automatisch getriggert

**Given** eine HA-Instanz mit HA OS oder Supervised
**When** der Nutzer das Custom Repository in den Add-on-Store einfügt
**Then** Solarbot erscheint im Store als installierbar

**Given** das Add-on ist installiert
**When** der Container startet
**Then** ein FastAPI-Prozess (Python 3.13) lauscht auf dem Ingress-Port
**And** die SQLite-Datei `/data/solarbot.db` wird initialisiert (leer, produktive Tabellen kommen in späteren Stories dazu)

**Given** der Container läuft
**When** die Svelte-Frontend-Route aufgerufen wird
**Then** ein minimaler Svelte + Tailwind-Build lädt ohne Fehler

**Given** `/data/` als Persistenz-Volume
**When** das Add-on neu gestartet wird
**Then** `/data/`-Inhalt bleibt erhalten

**Given** Raspberry Pi 4 als Referenz-Hardware
**When** das Add-on im Idle läuft
**Then** RSS ≤ 150 MB und CPU ≤ 2 %

**Given** der Container
**When** er läuft
**Then** keine externen Port-Expositionen außer HA-Ingress

### Story 1.2: Landing-Page-Voraussetzungs-Hinweis + HA-Versions-Range

As a Interessent auf alkly.de,
I want vor dem Download-Schritt klar zu sehen, welche HA-Installationstypen und welche HA-Version unterstützt werden,
So that ich kein fehlgeschlagenes Setup erlebe und die Voraussetzungen vorher kenne.

**Acceptance Criteria:**

**Given** die Solarbot-Landing-Page auf alkly.de
**When** der Besucher die Seite öffnet
**Then** oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile „Benötigt Home Assistant OS oder Supervised" sichtbar

**Given** der Check-Block auf der Landing-Page
**When** er gelesen wird
**Then** HA Container und HA Core sind explizit als „nicht supported, best-effort ohne Support" markiert

**Given** ein Nutzer versucht Solarbot auf einer nicht-unterstützten HA-Version zu installieren
**When** der Add-on-Store die Installation prüft
**Then** eine Install-Warning wird gezeigt
**And** die supported HA-Version-Range ist in `addon.yaml` deklariert

### Story 1.3: HA WebSocket Foundation mit Reconnect-Logik

As a Solarbot-Backend,
I want eine stabile HA-WebSocket-Verbindung mit SUPERVISOR_TOKEN-Auth und automatischem Reconnect,
So that alle späteren Epics sich auf einen verlässlichen Kommunikationskanal zu HA verlassen können.

**Acceptance Criteria:**

**Given** das Add-on startet
**When** der WebSocket-Client verbindet
**Then** die Verbindung zu `ws://supervisor/core/websocket` wird mit `SUPERVISOR_TOKEN` authentifiziert
**And** der Auth-Success-Event wird im Log bestätigt

**Given** eine bestehende WebSocket-Verbindung
**When** sie unterbrochen wird
**Then** exponentielles Backoff-Reconnect startet (1 s → 2 s → 4 s → max. 30 s)

**Given** der Client hatte Subscriptions
**When** der Reconnect erfolgreich ist
**Then** alle persistierten Subscriptions werden automatisch re-subscribt

**Given** ein Kommunikationsfehler
**When** er auftritt
**Then** er wird mit Kontext im strukturierten JSON-Log unter `/data/logs/` protokolliert
**And** die Verbindung wird als „verloren" markiert für spätere Health-Status-Queries

**Given** ein Test-Setup mit Mock-HA-WebSocket
**When** ein simulierter Abbruch ausgelöst wird
**Then** der Client reconnected innerhalb 30 s automatisch ohne manuelle Intervention

### Story 1.4: ALKLY-Design-System-Foundation — Tokens & lokale DM-Sans-Pipeline

As a Frontend-Entwickler,
I want eine getokte Design-Foundation mit ALKLY-Farbpalette, Spacing-/Radius-/Shadow-Tokens und lokaler DM-Sans-Font-Pipeline,
So that alle späteren UI-Stories auf einem konsistenten visuellen Fundament aufbauen und das 100 %-lokal-Versprechen auch in Assets eingehalten wird.

**Acceptance Criteria:**

**Given** eine Komponente referenziert ein Farb-Token
**When** sie rendert
**Then** Primär-/Sekundär-/Akzent-Farben (ALKLY-Teal, ALKLY-Rot) sind als CSS Custom Properties verfügbar
**And** Dark-Mode-Varianten (Teal mit Glow) und Light-Mode-Varianten (Rot mit Sättigung) sind getrennt definiert

**Given** eine Komponente setzt Padding oder Margin
**When** sie rendert
**Then** das 8-px-Raster wird via Tokens durchgesetzt (`--space-1: 8px`, `--space-2: 16px`, …)

**Given** eine Card rendert
**When** der Default-Radius greift
**Then** der Radius-Token beträgt 16 px

**Given** eine Komponente braucht Erhebung
**When** sie rendert
**Then** genau zwei Shadow-Ebenen (`--shadow-1`, `--shadow-2`) stehen zur Verfügung, nicht mehr

**Given** die lokale DM-Sans-Pipeline
**When** der Build läuft
**Then** WOFF2-Dateien für 4 Weights (Regular/Medium/Semibold/Bold) mit Latin + Latin-Extended-Subset im Container-Image eingebettet sind
**And** Gesamtgröße ≤ 120 kB

**Given** die gerenderte App
**When** Netzwerk-Requests analysiert werden
**Then** kein Request zu `fonts.googleapis.com`, `fonts.gstatic.com` oder einem anderen CDN
**And** kein `preconnect`-Link im HTML

**Given** eine Svelte-Komponente
**When** sie semantische Klassen nutzt
**Then** `.text-hero`, `.status-chip`, `.energy-ring` sind im Design-System-Modul definiert und dokumentiert

### Story 1.5: HA-Sidebar-Registrierung mit ALKLY-Branding

As a Solarbot-Nutzer,
I want nach der Installation einen sichtbaren „Solarbot by ALKLY"-Eintrag im HA-Sidebar,
So that ich Solarbot in meiner gewohnten HA-Navigation wiederfinde.

**Acceptance Criteria:**

**Given** das Add-on ist installiert und gestartet
**When** der Nutzer HA öffnet
**Then** der HA-Sidebar zeigt den Eintrag „Solarbot by ALKLY" mit ALKLY-Icon

**Given** `addon.yaml`
**When** Ingress konfiguriert ist
**Then** die Ingress-URL ist deklariert und das Icon ist als Asset im Image eingebettet

**Given** der Sidebar-Eintrag
**When** der Nutzer ihn klickt
**Then** der Solarbot-UI-Frame öffnet im HA-Panel

### Story 1.6: HA-Ingress-Frame mit Dark/Light-Adaption und Empty-State

As a Solarbot-Nutzer,
I want beim ersten Öffnen einen sauber gerenderten Begrüßungsscreen in HA-Theme-konformem Dark- oder Light-Mode mit ALKLY-Identität,
So that ich sofort weiß: Solarbot ist da und wartet auf mich.

**Acceptance Criteria:**

**Given** der Sidebar-Klick
**When** der Solarbot-UI-Frame lädt
**Then** die Svelte-App wird im HA-Ingress-iframe vollständig gerendert
**And** die TTFD ist < 2 s

**Given** HA ist im Dark-Mode
**When** Solarbot-UI rendert
**Then** Hintergrund, Text und Akzente nutzen Dark-Mode-Token-Varianten
**And** Teal hat den Dark-Mode-Glow ohne bleiche Zonen

**Given** HA ist im Light-Mode
**When** Solarbot-UI rendert
**Then** Light-Mode-Token-Varianten werden genutzt
**And** Rot behält seine Warnkraft-Sättigung

**Given** Empty-State (Wizard noch nicht abgeschlossen)
**When** die UI rendert
**Then** ein Begrüßungs-Screen zeigt Solarbot-Titel, kurze Einleitung und einen primären „Setup starten"-Button

**Given** der Footer
**When** das Dashboard oder der Empty-State rendert
**Then** ein 24-px-runder Alex-Avatar + „Made by Alex Kly · Discord · GitHub · Privacy"-Links + dezentes „100 % lokal"-Badge sind sichtbar

**Given** die UI
**When** der Nutzer das HA-Theme wechselt
**Then** Solarbot-UI adaptiert ohne Reload und ohne Farbbruch

### Story 1.7: i18n-Foundation mit `locales/de.json`

As a Solarbot-Internationalisierer,
I want alle UI-Strings aus der Foundation in `locales/de.json` extrahiert mit einem i18n-Helper im Svelte-Code,
So that ab v2 englische UI ohne Code-Refactor möglich ist.

**Acceptance Criteria:**

**Given** das Svelte-Projekt
**When** eine Komponente einen String anzeigt
**Then** der String wird über einen i18n-Helper (`$t('key.path')`) geladen, niemals hartcodiert

**Given** die Datei `locales/de.json`
**When** sie geöffnet wird
**Then** alle UI-Strings aus Story 1.6 (Empty-State, Footer, Setup-starten-Button) sind als strukturierte Keys hinterlegt

**Given** ein Build-Check
**When** der Build läuft
**Then** er schlägt fehl, wenn ein hartcodierter UI-String in Svelte-Komponenten gefunden wird (außer in Logs/Debug-Ausnahmen)

**Given** `locales/de.json`
**When** ein Key fehlt
**Then** ein Fallback-String (Key-Pfad) wird angezeigt und als Missing-Translation im Log vermerkt

---

## Epic 2: Setup-Wizard & Hardware-Onboarding

Nutzer schließt den Wizard in < 10 Min ab. Hardware ist auto-detektiert (Hoymiles/OpenDTU/Anker/Marstek/Shelly), Live-Werte sind bestätigt, der Funktionstest hat per Closed-Loop-Readback bewiesen, dass Steuerung funktioniert. „Aktivieren" am Ende des Wizards bedeutet Commissioning (Inbetriebnahme), nicht Lizenz-Aktivierung — die Lizenz-Schale kommt in Epic 7.

### Story 2.1: Wizard-Shell mit drei Hardware-Pfaden (Linear, 1 Aktion pro Screen)

As a Nutzer,
I want einen klar strukturierten Wizard mit drei Einstiegs-Pfaden (Hoymiles, Anker, Manuell) und genau einer primären Aktion pro Screen,
So that ich ohne Nachdenken den richtigen Weg durch mein Setup finde.

**Acceptance Criteria:**

**Given** die UI zeigt den Empty-State
**When** der Nutzer „Setup starten" klickt
**Then** der Wizard öffnet bildschirmfüllend im HA-Ingress-Frame

**Given** Schritt 1 des Wizards
**When** er rendert
**Then** genau drei Hardware-Pfad-Karten werden angezeigt: „Hoymiles / OpenDTU", „Anker Solix", „Manuell (Generic HA Entity)"

**Given** ein Wizard-Screen
**When** er rendert
**Then** maximal eine primäre Aktion ist sichtbar

**Given** der Nutzer ist im Wizard
**When** er mit der Tastatur navigiert
**Then** alle Schritte und Entscheidungen sind voll per Tab/Enter/Pfeiltasten bedienbar

**Given** der Nutzer unterbricht den Wizard (Browser schließen, HA-Reload)
**When** er Solarbot erneut öffnet
**Then** der Wizard-Fortschritt wird aus SQLite wiederhergestellt und setzt an der letzten bestätigten Stelle fort

**Given** der Nutzer will zurück
**When** er auf „Zurück" klickt
**Then** der vorherige Schritt wird ohne Datenverlust wieder angezeigt

### Story 2.2: Auto-Detection mit Device-Template-System & Live-Werten

As a Nutzer,
I want dass Solarbot meine Hardware im Wizard automatisch erkennt und mir Live-Werte neben jedem Sensor anzeigt,
So that ich per Wiedererkennung bestätige („Das bin ich.") statt kryptische Entity-IDs zu wählen.

**Acceptance Criteria:**

**Given** der Wizard ist bei Schritt „Hardware-Erkennung"
**When** der Nutzer auf den gewählten Pfad klickt
**Then** Solarbot führt einen `get_states`-Scan gegen HA aus und matcht die Response gegen das Device-Template-System

**Given** das Device-Template-System
**When** Templates geladen werden
**Then** Day-1-Templates für OpenDTU (Hoymiles), Anker Solix, Marstek Venus 3E/D, Shelly 3EM und Generic HA Entity sind als versionierte JSON-Dateien in `/data/templates/` verfügbar

**Given** ein Template
**When** es geparst wird
**Then** es enthält Entity-Pattern (Regex), Steuerung-Semantik (WR-Limit / Akku-Setpoint / Charge-Discharge-Toggle), Default-Regelungs-Parameter (Deadband, Rate-Limit, EEPROM-Intervall) und Latenz-Erwartung

**Given** eine `get_states`-Response mit kompatiblen Entities
**When** der Scan läuft
**Then** die Auto-Detection-Latenz ist ≤ 5 s

**Given** eine erkannte Entity
**When** der Wizard sie listet
**Then** ein Live-Wert neben dem Entity-Namen wird angezeigt (z. B. „AC-Leistung: 412 W") und aktualisiert sich über den WebSocket-Kanal

**Given** ein Nutzer sieht die erkannten Entities
**When** er eine bestätigt
**Then** ein einziger Klick („Das bin ich") reicht als Zustimmung, keine Dropdown-Auswahl von Entity-IDs

**Given** keine kompatiblen Entities werden gefunden
**When** der Scan abgeschlossen ist
**Then** ein Handlungsvorschlag wird angezeigt („Keine Hardware erkannt — prüfe deine HA-Integration oder nutze den manuellen Pfad"), kein nackter Fehler

### Story 2.3: Funktionstest mit Live-Chart-Dramaturgie & Commissioning

As a Nutzer vor der Inbetriebnahme,
I want einen sichtbaren Funktionstest, in dem Solarbot testweise mein WR-Limit oder meinen Akku-Setpoint setzt und mir den Effekt live zeigt,
So that ich vor der Aktivierung mit eigenen Augen bestätige, dass die Steuerung bei mir funktioniert.

**Acceptance Criteria:**

**Given** der Wizard hat alle Konfigurations-Schritte abgeschlossen
**When** der Nutzer „Funktionstest starten" klickt
**Then** Solarbot setzt testweise das WR-Limit (Drossel-Setup) oder einen Akku-Setpoint (Speicher-Setup)

**Given** der Funktionstest läuft
**When** er rendert
**Then** ein Live-Chart mit 5-Sekunden-Fenster zeigt WR-Limit-Verlauf, Netz-Einspeisung und SoC parallel

**Given** ein gesetzter Steuerbefehl
**When** Solarbot per Readback-Pattern prüft
**Then** ein Checkmark-Tick mit Spring-Easing erscheint bei Bestätigung; bei ausbleibender Bestätigung innerhalb Timeout-Schwelle erscheint ein roter Cross-Tick

**Given** der Funktionstest läuft
**When** er beginnt
**Then** er schließt in ≤ 15 s ab

**Given** der Funktionstest schlägt fehl
**When** der Fehler angezeigt wird
**Then** ein konkreter Handlungsvorschlag ist enthalten („Entity nicht erreichbar — prüfe HA-Integration XY") statt einer nackten Meldung

**Given** der Funktionstest war erfolgreich
**When** der Nutzer „Aktivieren" klickt
**Then** Solarbot übernimmt die Konfiguration in den Regelungs-Zustand und schreibt die Commissioning-Entscheidung als Event in den Log

**Given** der Commissioning-Status ist gesetzt
**When** der Nutzer Solarbot wieder öffnet
**Then** der Wizard startet nicht mehr (Empty-State verschwindet), Solarbot steht im Regel-Modus

---

## Epic 3: Aktive Nulleinspeisung & Akku-Pool-Steuerung

Solarbot regelt produktiv mit adaptiver Strategie (Drossel / Speicher / Multi-Modus), Akku-Pool-Abstraktion mit Gleichverteilung, Hysterese-basierten Modus-Wechseln, Closed-Loop-Readback und Fail-Safe. Zustand danach: „Solarbot arbeitet — der Strom bleibt im Haus."

### Story 3.1: Core Controller Pipeline (Sensor → Policy → Executor) + Event-Source + Readback + Rate-Limit

As a Solarbot-Backend,
I want eine hardware-agnostische Core-Controller-Pipeline, die Sensor-Events zu Steuerbefehlen verarbeitet, Source-Attribution schreibt, Readback prüft und EEPROM-Rate-Limits durchsetzt,
So that alle späteren Modi (Drossel, Speicher, Multi) und alle Device-Templates denselben Safety-Layer und dieselbe Event-Basis nutzen.

**Acceptance Criteria:**

**Given** ein Sensor-Event kommt über die WebSocket-Subscription
**When** der Controller es verarbeitet
**Then** die Pipeline läuft Sensor → Policy → Executor → Readback mit einer Gesamtdauer ≤ 1 s

**Given** ein Policy-Vorschlag
**When** der Executor ihn erhält
**Then** die Veto-Kaskade prüft Range-Check, Rate-Limit und Readback-Erwartung, bevor der Steuerbefehl an HA geht

**Given** ein erfolgreicher Steuerbefehl
**When** er ausgelöst wird
**Then** er wird mit Source-Flag (`source: solarbot`) in SQLite-Tabelle `control_cycles` geschrieben (Timestamp, Sensor-Value, gesetztes Limit, Modus, Source)

**Given** ein manuelles oder HA-Automation-triggered Event
**When** es erkannt wird
**Then** der Source-Flag ist entsprechend `manual` bzw. `ha_automation`

**Given** jeder Steuerbefehl
**When** er gesendet wurde
**Then** ein Readback-Check via State-Subscription prüft innerhalb des Template-spezifischen Timeout-Fensters die Bestätigung

**Given** ein Device-Template definiert Rate-Limit (Default ≤ 1 Schreibbefehl/Device/Minute)
**When** der Executor den nächsten Befehl prüft
**Then** Befehle innerhalb des Intervalls werden unterdrückt und im Log markiert

**Given** das SetpointProvider-Interface
**When** kein Forecast-Provider aktiv ist
**Then** die Default-Noop-Implementation liefert „current reactive behavior" zurück — Interface ist in `core/setpoint_provider.py` definiert mit Docstring „v2-Forecast-Naht"

**Given** die E2E-Latenz-Messung
**When** ein Steuerbefehl ausgelöst wird
**Then** die Zeit zwischen Befehl und messbarem Smart-Meter-Effekt wird in `latency_measurements`-Tabelle geloggt

### Story 3.2: Drossel-Modus — WR-Limit-Regelung für Nulleinspeisung

As a Balkon-Benni / Neugier-Nils ohne Akku,
I want dass Solarbot bei PV-Überschuss das WR-Limit reaktiv runterregelt, damit keine Watt ans Netz verschenkt werden,
So that meine Hoymiles / OpenDTU-Hardware nulleinspeisungs-konform läuft ohne Bastelei.

**Acceptance Criteria:**

**Given** Drossel-Modus ist aktiv
**When** der Smart-Meter positive Einspeisung meldet
**Then** der Controller berechnet ein neues WR-Limit und schickt `number.set_value` via Executor

**Given** eine Regelungs-Entscheidung
**When** die Sensor-Schwankung im Deadband liegt (Hardware-spezifisch, z. B. ±5 W Hoymiles, ±30 W Anker aus Template)
**Then** kein neuer Steuerbefehl wird ausgelöst (Stabilisierung)

**Given** eine Lastsprung-Situation
**When** ein Haushaltsverbraucher zuschaltet
**Then** Drossel reagiert innerhalb 1 Regel-Zyklus ohne Schwingen (Moving Average / Glättungs-Konstante aus Template)

**Given** Hoymiles / OpenDTU-Hardware
**When** Drossel regelt
**Then** ±5 W-Toleranz wird eingehalten

**Given** das Template definiert EEPROM-Rate-Limit
**When** aufeinanderfolgende Drossel-Zyklen nötig wären
**Then** Rate-Limit aus Story 3.1 wird respektiert

### Story 3.3: Akku-Pool-Abstraktion mit Gleichverteilung & SoC-Aggregation

As a Marstek-Micha mit 2× Venus 3E (Kernsegment),
I want dass Solarbot meine Akkus intern als logischen Pool behandelt mit Gleichverteilung in v1 und aggregiertem SoC-Wert,
So that ich keine Multi-Akku-Komplexität im UI sehe und der Pool wie ein einziger Speicher reagiert.

**Acceptance Criteria:**

**Given** ≥ 1 Akku ist konfiguriert
**When** der Akku-Pool initialisiert wird
**Then** eine Pool-Abstraktion wrappt alle Akkus in einer einheitlichen API (`pool.set_setpoint(W)`, `pool.get_soc()`)

**Given** ein Pool-Setpoint von N Watt
**When** er auf 2 Akkus verteilt wird
**Then** jeder Akku bekommt N/2 Watt (Gleichverteilung v1, Rundung auf Template-konforme Schrittweite)

**Given** ein Pool mit mehreren Akkus
**When** `get_soc()` abgefragt wird
**Then** der Pool liefert aggregierten SoC (gewichteter Mittelwert nach Kapazität) UND eine Breakdown-Map pro Einzel-Akku

**Given** ein einzelner Akku im Pool wird offline
**When** der Pool davon erfährt
**Then** die verbleibenden Akkus übernehmen den vollen Setpoint (Fallback-Modus = 1 Hauptspeicher aktiv, andere statisch)

**Given** das Template-System
**When** der Pool für einen Marstek-Venus-Pool initialisiert wird
**Then** die Kommunikation zu jedem Akku läuft über die Adapter-Module (`adapters/marstek_venus.py`), nicht über Direct-Hardware-Calls

### Story 3.4: Speicher-Modus — Akku-Lade/-Entlade-Regelung innerhalb SoC-Grenzen

As a Marstek-Micha / Beta-Björn mit Akku,
I want dass Solarbot bei PV-Überschuss den Akku-Pool lädt und bei Grundlast aus dem Pool entlädt, respektierend die Min/Max-SoC-Grenzen,
So that mein Strom im Haus bleibt und die Akku-Gesundheit nicht durch Tiefentladung oder Überladung leidet.

**Acceptance Criteria:**

**Given** Speicher-Modus ist aktiv
**When** der Smart-Meter positive Einspeisung meldet
**Then** der Controller berechnet einen Pool-Lade-Setpoint und delegiert an den Akku-Pool aus Story 3.3

**Given** Speicher-Modus ist aktiv
**When** Grundlast-Verbrauch erkannt wird und Pool-SoC über Min-Grenze
**Then** der Controller berechnet einen Pool-Entlade-Setpoint zur Deckung der Grundlast

**Given** der Pool erreicht Max-SoC
**When** weiterhin Überschuss anliegt
**Then** Lade-Befehle werden nicht mehr erhöht (Hard-Cap), Modus-Wechsel zu Drossel wird geflaggt

**Given** der Pool erreicht Min-SoC
**When** Entlade-Anfrage kommt
**Then** Entlade stoppt (Hard-Cap), Netz-Bezug wird zugelassen

**Given** Anker Solix Hardware
**When** Speicher regelt
**Then** ±30 W-Toleranz wird eingehalten

**Given** ein Schreibbefehl an einen Einzel-Akku im Pool
**When** er ausgelöst wird
**Then** der Rate-Limit aus Story 3.1 wird pro Device durchgesetzt

### Story 3.5: Adaptive Strategie-Auswahl & Hysterese-basierter Modus-Wechsel (inkl. Multi-Modus)

As a Nutzer mit hybridem Setup (WR + Multi-Akku),
I want dass Solarbot meine Regelungs-Strategie automatisch aus dem erkannten Hardware-Setup ableitet und zwischen Drossel / Speicher / Multi-Modus ohne Oszillation wechselt,
So that ich nie einen Modus manuell einstellen muss und im Grenzbereich (Akku-knapp-voll) kein Flackern entsteht.

**Acceptance Criteria:**

**Given** die Wizard-Konfiguration aus Epic 2
**When** Solarbot startet
**Then** die Regelungs-Strategie wird automatisch aus dem Hardware-Regime abgeleitet: nur WR → Drossel, WR+Akku → Speicher (mit Drossel als Fallback), WR+Multi-Akku → Multi-Modus

**Given** Multi-Modus
**When** PV-Überschuss anliegt
**Then** Akku-Pool wird zuerst geladen, erst bei Pool-Voll greift Drossel

**Given** Multi-Modus mit leerem Pool
**When** es Nacht wird
**Then** kein Drossel-Anstieg, kein unsinniger Schreibbefehl

**Given** der Modus-Wechsel Akku-voll → Drossel
**When** er getriggert wird
**Then** Drossel aktiv ab SoC ≥ 97 %, deaktiv erst bei SoC ≤ 93 % (Hysterese)

**Given** der Modus-Wechsel
**When** er ausgelöst wird
**Then** eine Mindest-Verweildauer pro Modus (z. B. 60 s) verhindert Oszillation

**Given** ein Modus-Wechsel ist erfolgt
**When** er abgeschlossen ist
**Then** ein Event mit Timestamp, alter/neuer Modus und Trigger-Grund wird im Log und in der `control_cycles`-Tabelle geschrieben (Grundlage für UI-Anzeige FR28 in Epic 5)

### Story 3.6: User-Config — Min/Max-SoC & Nacht-Entlade-Zeitfenster

As a Nutzer,
I want Min-SoC, Max-SoC pro Akku-Setup und ein Nacht-Entlade-Zeitfenster konfigurieren können,
So that ich die Leitplanken für meinen Akku an meine Akku-Spec und meinen Tagesrhythmus anpasse.

**Acceptance Criteria:**

**Given** der Settings-Bereich der UI
**When** der Nutzer Akku-Konfiguration öffnet
**Then** zwei Eingabefelder für Min-SoC (Default 15 %) und Max-SoC (Default 95 %) sind sichtbar

**Given** eine Nutzereingabe
**When** Min-SoC ≥ Max-SoC
**Then** Validierung schlägt fehl mit Handlungsvorschlag („Min muss kleiner Max sein")

**Given** Plausibilitäts-Grenzen aus dem Device-Template
**When** ein Nutzer z. B. Min-SoC < 5 % eingibt
**Then** Warnung zeigt „Unterhalb Herstellerspezifikation — Akku-Schäden möglich" und erfordert zweite Bestätigung

**Given** der Settings-Bereich
**When** der Nutzer Nacht-Entlade konfiguriert
**Then** ein Zeitfenster-Picker (Start-/Endzeit, z. B. 20:00–06:00) ist verfügbar

**Given** Nacht-Entlade-Zeitfenster ist aktiv
**When** die aktuelle Uhrzeit im Fenster liegt UND Pool-SoC > Min-SoC
**Then** der Speicher-Modus entlädt zur Grundlast-Deckung

**Given** eine Konfigurationsänderung
**When** der Nutzer speichert
**Then** die Werte werden in SQLite persistiert und ohne Add-on-Neustart vom Controller aufgenommen

### Story 3.7: Fail-Safe bei Kommunikations-Ausfall

As a Nutzer,
I want dass Solarbot bei Kommunikationsausfall (HA-WS, Entity, Readback-Timeout) in einen deterministischen Safe-State geht und nicht blind weiter steuert,
So that mein Netz-Export und meine Hardware nie unkontrolliert aus dem Ruder laufen.

**Acceptance Criteria:**

**Given** der WebSocket-Kanal fällt aus (Reconnect läuft)
**When** der Controller das erkennt
**Then** Solarbot setzt keine neuen Schreibbefehle mehr, das zuletzt gesetzte WR-Limit bleibt am WR bestehen (nicht freigeben)

**Given** eine Entity antwortet nicht auf Readback innerhalb Timeout-Fenster
**When** das passiert
**Then** diese Entity wird als „unhealthy" markiert, der Controller pausiert Befehle für diese Entity, der Modus-State wird im Log festgehalten

**Given** Fail-Safe ist aktiv
**When** die Kommunikation wieder hergestellt ist
**Then** Controller prüft aktuellen Sensor-Zustand gegen erwarteten, nimmt Regelung wieder auf (Recovery-Logik), logged Event „Fail-Safe aufgehoben"

**Given** die Fail-Safe-Logik
**When** sie getriggert wird
**Then** im Log wird ein Entry mit Timestamp, Grund (WS / Readback-Timeout / Range-Fehler), betroffener Entity und aktuell gehaltenem Wert geschrieben

**Given** ein Test-Setup mit simuliertem WebSocket-Ausfall
**When** der Ausfall 30 s dauert
**Then** Solarbot hält das letzte Limit, kein neuer Schreibbefehl wird gesendet

**Given** der 24-h-Dauertest als Launch-Gate
**When** er läuft
**Then** 0 unbehandelte Exceptions, keine Schwingungen, keine unkontrollierten Einspeisungen unter `load_profile_sine_wave.csv` 0–3000 W

---

## Epic 4: Diagnose, Latenz-Messung & Support-Workflow

Alex bekommt mit einem Klick einen strukturierten Diagnose-Export von einem Beta-Tester. Nutzer sieht Verbindungs-Status, letzte 100 Regelzyklen, letzte 20 Fehler, E2E-Latenz pro Device. GitHub-Issues hat ein Bug-Report-Template mit Hardware-/Firmware-Feldern.

### Story 4.1: Diagnose-Route mit abgesetztem Opening + Letzte 100 Regelzyklen

As a Alex (Support) / fortgeschrittener Nutzer,
I want eine bewusst abgesetzte Diagnose-Route mit einsteiger-freundlichem Einleitungs-Screen und einer Liste der letzten 100 Regelzyklen,
So that ich Beta-Probleme nachvollziehen kann, ohne dass Micha oder Nils versehentlich in einen Nerd-Modus geraten.

**Acceptance Criteria:**

**Given** der Settings-Bereich der UI
**When** der Nutzer „Diagnose öffnen" klickt
**Then** eine neue Route wird geöffnet, die nicht in der Bottom-/Left-Nav erscheint

**Given** die Diagnose-Route
**When** sie rendert
**Then** oben ein freundlicher Hinweis „Für Fortgeschrittene — hier siehst du, was Solarbot intern tut. Bei Supportanfragen: Export-Button rechts oben." wird angezeigt

**Given** die Diagnose-Route
**When** sie rendert
**Then** ein Navigations-Skeleton für Sub-Sektionen (Zyklen / Fehler / Verbindungen / Latenz / Export) ist sichtbar

**Given** die Sektion „Zyklen"
**When** sie geöffnet wird
**Then** eine Liste der letzten 100 Regelzyklen aus der `control_cycles`-Tabelle wird dargestellt mit Spalten: Timestamp, Sensor-Wert, gesetztes Limit, Modus, Latenz, Source

**Given** die Zyklen-Liste mit 100 Einträgen
**When** sie rendert
**Then** keine Layout-Sprünge, Performance ist flüssig (optional Virtualisierung)

**Given** der Nutzer sucht einen spezifischen Zyklus
**When** er ein Filter-Feld nutzt
**Then** er kann nach Source (`solarbot` / `manual` / `ha_automation`) und Modus filtern

**Given** eine Ladung > 400 ms
**When** die Liste rendert
**Then** ein grauer Skeleton-Pulse wird gezeigt, kein Spinner

### Story 4.2: Letzte 20 Fehler & Warnungen mit Klartext + Handlungsempfehlung

As a Alex / Nutzer,
I want die letzten 20 Warnungen und Fehler in Klartext mit konkretem Handlungsvorschlag sehen,
So that ich ein Problem selbst einordnen kann — oder es im Bug-Report sauber beschreiben.

**Acceptance Criteria:**

**Given** die Diagnose-Route
**When** die Sektion „Fehler" geöffnet wird
**Then** eine Liste der letzten 20 Events mit Severity ≥ WARN wird angezeigt

**Given** jeder Fehler-Eintrag
**When** er rendert
**Then** er enthält Timestamp, Severity-Badge (WARN / ERROR), Klartext-Beschreibung und konkreten Handlungsvorschlag

**Given** ein Beispiel-Fehler „Entity `number.opendtu_limit_nonpersistent_absolute` antwortet nicht"
**When** der Fehler angezeigt wird
**Then** Handlungsvorschlag „Prüfe OpenDTU-Integration in HA → Einstellungen → Integrationen" ist sichtbar

**Given** ein Fehler hat zusätzlichen Kontext (Exception-Trace, JSON-Payload)
**When** der Nutzer auf den Eintrag klickt
**Then** ein Inline-Panel fährt aus mit dem technischen Detail (keine Modal)

**Given** keine Fehler in den letzten Zyklen
**When** die Sektion rendert
**Then** ein positiver Leerzustand „Keine Fehler. Solarbot läuft sauber." wird angezeigt

### Story 4.3: Verbindungs-Status-Panel (HA-WS, Entities, Lizenz)

As a Alex / Nutzer,
I want auf einen Blick sehen, ob HA-WebSocket verbunden ist, welche Entities gesund sind und ob die Lizenz gültig ist,
So that ich bei Problemen sofort weiß, wo die Ursache zu suchen ist.

**Acceptance Criteria:**

**Given** die Sektion „Verbindungen"
**When** sie rendert
**Then** drei Status-Bereiche sind sichtbar: HA WebSocket, konfigurierte Entities, Lizenz-Status

**Given** der HA-WebSocket-Status
**When** er rendert
**Then** er zeigt einen Status-Chip (`connected` / `reconnecting` / `lost`) mit Last-Auth-Timestamp

**Given** die Entity-Liste
**When** sie rendert
**Then** jede konfigurierte Entity zeigt: Name, Healthy/Unhealthy-Badge, letzte erfolgreiche Kommunikation (Timestamp), Readback-Erfolgsquote (z. B. „98 % über letzte 24 h")

**Given** eine Entity ist unhealthy
**When** sie gelistet wird
**Then** der Status-Chip ist rot mit Handlungsvorschlag bei Klick

**Given** der Lizenz-Status
**When** er rendert
**Then** er zeigt einen der Zustände: `valid` / `grace` (mit Tage-verbleibend-Countdown) / `offline-for-X-days` / `unvalidated` (bis Epic 7 produktiv wird, ist der Wert `unvalidated` Default)

**Given** die Status-Anzeige
**When** sich ein Status ändert
**Then** die UI aktualisiert sich via WebSocket ohne Reload

### Story 4.4: E2E-Regelungs-Latenz-Auswertung im Diagnose-Tab

As a Alex,
I want die gemessene E2E-Latenz pro Device mit Median / P95 / Max sehen,
So that ich hardware-spezifische Regel-Parameter (Deadband, Rate Limit) empirisch justieren kann.

**Acceptance Criteria:**

**Given** die `latency_measurements`-Tabelle aus Story 3.1
**When** sie konsumiert wird
**Then** in der Sektion „Latenz" werden Median, P95 und Max pro Device für die letzten 24 h angezeigt

**Given** eine Device-spezifische Latenz-Zeile
**When** sie rendert
**Then** sie zeigt Device-Name (aus Template), Median (ms), P95 (ms), Max (ms), Anzahl Messungen

**Given** ein Ausreißer (Latenz > 2 × Median)
**When** er in den Messungen vorkommt
**Then** er ist in einer Detail-Sicht (Klick auf Zeile) sichtbar mit Timestamp und zugehöriger Zyklus-Referenz

**Given** verschiedene Hardware-Stacks (Hoymiles 5–15 s, Anker Cloud 30–90 s, Marstek lokal TBD)
**When** Latenz-Werte verglichen werden
**Then** unterschiedliche Hardware-Klassen sind visuell separierbar

**Given** ein Beta-Tester
**When** er seinen Diagnose-Export an Alex sendet
**Then** die Latenz-Summary ist dort enthalten

### Story 4.5: Diagnose-Export als strukturierter Bug-Report (kippbar)

As a Beta-Tester / Alex,
I want per einem Klick einen strukturierten Diagnose-Export als JSON-Datei erhalten, der alle relevanten Informationen enthält,
So that Bug-Reports binnen Minuten komplett sind und nicht in Hin-und-Her-E-Mails zerfasern.

**Acceptance Criteria:**

**Given** die Diagnose-Route
**When** der Nutzer „Diagnose exportieren" klickt
**Then** ein strukturiertes JSON-Schema `solarbot-diag-v1.json` wird erzeugt

**Given** der Export
**When** er erzeugt wird
**Then** er enthält: Schema-Version, Zeitstempel, Add-on-Version, HA-Version, Container-Arch, aktive Device-Templates mit Version, Firmware-Versionen (falls erfassbar), letzte 100 Zyklen, letzte 20 Fehler, Verbindungs-Status-Snapshot, Latenz-Summary, aktueller Regel-Modus

**Given** der Export
**When** er ausgelöst wird
**Then** er wird als Download angeboten UND in den Zwischenspeicher kopiert mit Toast „Export kopiert"

**Given** der Export
**When** er erzeugt wird
**Then** er enthält keine personenbezogenen Daten, keine Lizenz-Token, keine HA-Auth-Token (Review-Checkliste im Code dokumentiert)

**Given** diese Story wird gekippt
**When** der Fallback greift
**Then** im Diagnose-Tab ist stattdessen ein prominenter Link „HA-Panel-Log herunterladen" zur Standard-Add-on-Log-Download-Funktion platziert

### Story 4.6: GitHub-Issues Bug-Report-Template

As a Beta-Tester / Support-Anfrager,
I want ein strukturiertes GitHub-Issue-Template im Repository, das alle Pflichtfelder für einen Bug-Report vorgibt,
So that Alex nicht nachfragen muss, welche Hardware/Firmware ich nutze.

**Acceptance Criteria:**

**Given** das Repository `alkly/solarbot`
**When** ein Nutzer einen neuen Issue anlegt
**Then** ein Template „Bug Report" wird als Default vorgeschlagen

**Given** das Template
**When** es gerendert wird
**Then** es enthält Pflichtfelder: Hardware (WR-Modell + Firmware, Akku-Modell + Firmware, Smart Meter), HA-Installationstyp + Version, Solarbot-Version, Beschreibung, erwartetes Verhalten, tatsächliches Verhalten, Platzhalter für Diagnose-Export-Anhang

**Given** der Diagnose-Tab
**When** der Nutzer „Fehler melden" klickt
**Then** ein Direktlink zum GitHub-Issue-Template mit vorausgefüllten Basis-Feldern (Solarbot-Version, HA-Version, Container-Arch) wird geöffnet

**Given** das Template
**When** es im Repository existiert
**Then** es liegt unter `.github/ISSUE_TEMPLATE/bug-report.yml` (YAML-Form für strukturiertes Parsing durch GitHub)

---

## Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung

Nutzer öffnet Dashboard und sieht in < 2 s die Euro-Kernaussage. Beleg-KPIs, Regelmodus, Idle-State, Energy-Ring und Flow-Visualisierung machen die Arbeit von Solarbot sichtbar.

### Story 5.1: Dashboard-Shell mit Responsive Navigation + Hero-Zone (Euro-Wert als 2-s-Kernaussage)

As a Nutzer,
I want beim Öffnen des Dashboards in weniger als 2 Sekunden eine Euro-Zahl sehen, die mir sagt, was Solarbot heute für mich gesteuert hat,
So that ich abends mit einem Blick weiß: es hat sich gelohnt.

**Acceptance Criteria:**

**Given** der Nutzer klickt auf „Solarbot" in der HA-Sidebar
**When** das Dashboard lädt
**Then** die Hero-Zone mit Euro-Wert ist in < 2 s sichtbar

**Given** die Hero-Zone
**When** sie rendert
**Then** der Euro-Wert ist 56–72 px DM Sans Bold mit tracking -0.02em, „€"-Einheit in 60 % Opacity daneben

**Given** die Hero-Zahl
**When** der Nutzer sie antippt
**Then** ein Inline-Transparenz-Overlay fährt aus mit Formel „heute gesteuert: X Wh × Y ct/kWh = Z €" und Quelle

**Given** das Dashboard
**When** auf Viewport < 1024 px gerendert
**Then** eine Bottom-Nav mit 4 Reitern (Home / Geräte / Statistik / Einstellungen) ist sichtbar mit Glass-Effect (92 % Opacity + Blur)

**Given** das Dashboard
**When** auf Viewport ≥ 1024 px gerendert
**Then** eine Left-Nav (identische 4 Reiter) ersetzt die Bottom-Nav

**Given** in MVP nur Home-Tab populiert
**When** Statistik / Geräte / Einstellungen gedrückt werden
**Then** Platzhalter mit „Folgt in v1.5" oder grundlegende Settings (für Epic 3.6 / Epic 4) sind verfügbar

**Given** der Nutzer ist im Dashboard
**When** er `1` / `2` / `3` / `4` drückt
**Then** der entsprechende Tab wird geöffnet; `D` öffnet Diagnose; `?` zeigt Shortcut-Referenz

**Given** Ladungen > 400 ms
**When** die Hero-Zone rendert
**Then** Skeleton-Pulse statt Spinner

**Given** das Dashboard
**When** gerendert
**Then** Footer mit Alex-Micro-Avatar + Links + „100 % lokal"-Badge ist sichtbar

### Story 5.2: Bezugspreis-Anpassung inline per Stepper

As a Nutzer,
I want den Bezugspreis direkt am Dashboard per Tap auf ein kleines Preis-Badge anpassen,
So that meine Euro-Berechnung meiner realen Strompreissituation entspricht (Default 30 ct/kWh).

**Acceptance Criteria:**

**Given** der Default-Bezugspreis
**When** die App erstmalig rendert
**Then** 30 ct/kWh ist gesetzt und in SQLite persistiert

**Given** ein kleines Preis-Badge neben der Hero-Zahl (Tap auf die Hero-Zahl öffnet das Transparenz-Overlay, das Badge öffnet den Stepper)
**When** der Nutzer auf das Badge tippt
**Then** ein Inline-Stepper erscheint unter der Zahl mit aktuellem Preis und ±-Buttons

**Given** der Stepper
**When** der Nutzer den Wert ändert
**Then** Enter oder Blur speichert den neuen Wert in SQLite

**Given** eine Preis-Änderung
**When** gespeichert
**Then** die Hero-Zahl aktualisiert sich live (Neu-Berechnung aus gesteuerten Wh × neuem Preis)

**Given** der Preis-Wert
**When** negativ oder > 200 ct eingegeben wird
**Then** Validierung verhindert das mit Handlungsvorschlag

**Given** keine Modal-Dialoge
**When** Bezugspreis editiert wird
**Then** alles inline, kein Dialog-Fenster

### Story 5.3: Beleg-KPIs getrennt ausgewiesen (kWh selbst verbraucht + kWh selbst gesteuert)

As a Nutzer,
I want unter der Euro-Zahl zwei separate Beleg-Kacheln sehen, die strikt trennen, was passiv selbst verbraucht vs. aktiv von Solarbot gesteuert wurde,
So that meine Euro-Zahl nachvollziehbar und prüfbar ist.

**Acceptance Criteria:**

**Given** das Dashboard unter der Hero-Zone
**When** es rendert
**Then** zwei separate Kacheln „Selbst verbraucht: X kWh" und „Selbst gesteuert: Y kWh" werden angezeigt

**Given** die KPI-Berechnung
**When** „selbst gesteuert" aggregiert wird
**Then** werden nur Zyklen mit Source-Flag `solarbot` aus der `control_cycles`-Tabelle gezählt

**Given** die KPI-Berechnung
**When** „selbst verbraucht" aggregiert wird
**Then** PV-Erzeugung minus Netz-Einspeisung wird genommen (umfasst auch passiven Eigenverbrauch)

**Given** beide Kacheln
**When** sie rendern
**Then** sie sind strikt getrennt, keine Aggregation, keine Gesamt-Zahl

**Given** die Zahlen
**When** sie rendern
**Then** sie sind nackt, ohne Adjektive, ohne Trend-Icons

**Given** noch keine Daten in Zyklen-Tabelle (frischer Commissioning)
**When** die Kacheln rendern
**Then** sie zeigen „0 kWh" mit Fußnote „Messung beginnt ab Aktivierung", kein Fehlerzustand

### Story 5.4: Energy-Ring & Flow-Visualisierung mit Custom-PV-Icons

As a Nutzer,
I want eine lebendige Live-Visualisierung, die zeigt, woher Energie kommt und wohin sie fließt,
So that ich auf einen Blick verstehe, was Solarbot gerade tut — nicht nur in Zahlen, sondern visuell.

**Acceptance Criteria:**

**Given** die Hero-Zone
**When** sie rendert
**Then** ein zentraler Energy-Ring zeigt die Leistungs-Balance (Erzeugung vs. Verbrauch) — Teal für Überschuss, Rot für Bezug, Grau für Neutral

**Given** Live-Sensor-Daten
**When** sie via WebSocket aktualisieren
**Then** der Ring adaptiert in Echtzeit ohne Reload

**Given** unter dem Ring
**When** die Flow-Visualisierung rendert
**Then** PV / Haus / Akku / Netz-Icons sind via SVG-Paths mit moving particles verbunden

**Given** die Particle-Geschwindigkeit
**When** Energie fließt
**Then** sie ist proportional zur aktuellen Leistung (z. B. 100 W → langsam, 2000 W → schnell)

**Given** die Icons
**When** sie rendern
**Then** sie nutzen Custom-PV-Ikonographie in 1,5 px Stroke (Wechselrichter, Akku, Smart Meter, Shelly, Marstek-Silhouette, Hoymiles-Typ), keine Feather / Lucide-Stock-Icons

**Given** ein Haushalt ohne Akku
**When** die Flow-Visualisierung rendert
**Then** das Akku-Element ist nicht sichtbar (dynamisches Layout)

**Given** eine Übergangsanimation
**When** sie läuft
**Then** Cubic-Bezier-Easing mit leichtem Overshoot `(0.34, 1.56, 0.64, 1)`, Stagger-Delays 50 ms, keine Animation > 1200 ms

### Story 5.5: Aktueller Regelmodus + Modus-Wechsel-Animation

As a Nutzer,
I want immer sehen, in welchem Modus Solarbot gerade regelt (Drossel / Speicher / Multi) und wenn er wechselt, soll das sichtbar sein,
So that ich verstehe, dass Solarbot denkt und aktiv entscheidet — nicht nur einen statischen Zustand zeigt.

**Acceptance Criteria:**

**Given** Solarbot ist im Regelbetrieb
**When** das Dashboard rendert
**Then** ein Status-Chip zeigt den aktuellen Modus (z. B. „Speicher-Modus" mit Icon)

**Given** ein Modus-Wechsel tritt ein (Story 3.5 triggert Event)
**When** das Event im Dashboard ankommt
**Then** der Ring wechselt Farbe mit Fade-Übergang, der Modus-Chip rotiert, eine kurze Status-Zeile erklärt den Wechsel („Akku voll → Drossel übernimmt")

**Given** eine Modus-Wechsel-Animation
**When** sie läuft
**Then** sie dauert ≤ 1200 ms

**Given** der Nutzer will Details
**When** er auf den Modus-Chip klickt
**Then** eine Inline-Beschreibung fährt aus („Im Speicher-Modus lädt Solarbot den Akku bei Überschuss und entlädt zur Grundlast-Deckung", keine Modal)

**Given** keine Oszillation (aus Story 3.5 Hysterese)
**When** Modus-Wechsel passieren
**Then** keine flackernden Chip-Wechsel im Dashboard

### Story 5.6: Aktiver Idle-State als positive Aussage

As a Nutzer (z. B. mittags, nichts passiert gerade),
I want dass Solarbot mir im Idle-Zustand aktiv sagt „alles im Ziel — ich überwache weiter", statt leer oder tot zu wirken,
So that ich nicht denke, das Ding sei kaputt, wenn gerade keine Steuerung nötig ist.

**Acceptance Criteria:**

**Given** Solarbot regelt aktuell nicht (keine Überschuss, keine Entlade-Anforderung)
**When** das Dashboard rendert
**Then** ein erkennbarer Idle-State wird gezeigt, nicht ein leerer Screen oder Fehlerzustand

**Given** der Idle-State
**When** er rendert
**Then** der Energy-Ring atmet langsam (60 bpm wie ruhiger Puls), Hintergrund ist Teal-Soft

**Given** der Idle-State
**When** er aktiv ist
**Then** eine Charakter-Zeile „Alles im Ziel. Ich überwache weiter." wird über dem Ring angezeigt

**Given** der Übergang Idle → Aktiv
**When** er eintritt
**Then** Atem-Animation wird weich gestoppt und normaler Modus-Ring wird sichtbar

**Given** der Idle-State
**When** er länger als 30 Sekunden anhält
**Then** keine blinkenden Elemente, keine Eskalation — Ruhe bleibt bestehen

### Story 5.7: Charakter-Zeile über Hero bei eigenem Tun (kippbar → Fallback Neutral-Mode)

As a Nutzer,
I want über der Euro-Zahl eine kurze narrative Zeile sehen, die mir sagt, was Solarbot gerade tut (z. B. „Venus-Pool lädt mit 1.400 W · Überschuss wird gespeichert"),
So that das Dashboard sich lebendig anfühlt und Solarbot Charakter hat — ohne dass Zahlen selbst dramatisiert werden.

**Acceptance Criteria:**

**Given** Solarbot regelt aktiv
**When** das Dashboard rendert
**Then** über der Euro-Zahl ist eine Charakter-Zeile (14 px, 500-Weight, Teal oder Text-Secondary) sichtbar mit narrativer Beschreibung des aktuellen Tuns und Piktogrammen

**Given** die Charakter-Zeile
**When** sie rendert
**Then** sie beschreibt ausschließlich Solarbots eigenes Tun (Modus, aktive Zuweisung) — niemals die Zahlen selbst

**Given** Zahlenwerte im Dashboard
**When** sie rendern
**Then** sie sind nackt, ohne emotionale Adjektive (kein „super", kein „stark")

**Given** eine kleine Euro-Zahl (z. B. 0,14 €)
**When** die Charakter-Zeile rendert
**Then** sie ist sachlich, nicht beschönigend

**Given** eine sehr kleine Euro-Zahl (0,00 €)
**When** die UI rendert
**Then** keine Charakter-Zeile wird angezeigt (nur Idle-State aus Story 5.6)

**Given** diese Story wird gekippt
**When** der Fallback greift
**Then** Neutral-Mode ist aktiv: keine Charakter-Zeilen, nur nackte Modus-Chips und Zahlen

**Given** Charakter-Templates
**When** sie geladen werden
**Then** sie liegen in `locales/de.json` unter einem `character.*`-Namespace, nicht hartcodiert

---

## Epic 6: Updates, Backup & Add-on-Lifecycle

*Rohes Epic — Stories als Stubs mit User-Story, ohne detaillierte Acceptance Criteria. Auszuarbeiten kurz vor Beta-Start oder in v1.1-Planung.*

Updates verlaufen reibungslos via Add-on Store. Vor jedem Update wird automatisch ein rotierendes Backup angelegt (letzte 5 Stände). Bei fehlgeschlagenem Update kann manuell zurückgerollt werden. HA-Versions-Range ist deklariert.

### Story 6.1: Auto-Update via HA Add-on Store

As a Nutzer,
I want Solarbot automatisch (oder nach manueller Bestätigung) über den HA Add-on Store aktualisieren können,
So that ich Bugfixes und neue Features ohne Bastelei bekomme.

*FR37. ACs offen — siehe PRD „HA Add-on Store als alleiniger Update-Kanal", „Auto-Update durch Nutzer aktivierbar".*

### Story 6.2: Backup-Rotation vor jedem Update

As a Solarbot-Lifecycle,
I want vor jedem Update automatisch `solarbot.db`, `license.json` und `templates/` in `/data/.backup/vX.Y.Z/` sichern und maximal die letzten 5 Stände behalten,
So that bei einem fehlgeschlagenen Update der vorherige Zustand wiederherstellbar ist.

*FR38. ACs offen — siehe Architecture-Persistence-Block.*

### Story 6.3: Manueller Rollback-Pfad mit automatischer Backup-Wiederherstellung

As a Nutzer nach fehlgeschlagenem Update,
I want über den HA Add-on Store eine ältere Version zurückinstallieren können und Solarbot stellt `/data/.backup/` automatisch wieder her,
So that ich nie einen Update-Hotfix fürchte.

*FR39. ACs offen — siehe PRD „Rollback-Pfad bei fehlgeschlagenem Start nach Update".*

### Story 6.4: HA-Version-Kompatibilitäts-Matrix in `addon.yaml`

As a Nutzer mit älterer oder neuerer HA-Version,
I want dass Solarbot die unterstützte HA-Version-Range deklariert und bei Inkompatibilität eine Install-Warning zeigt,
So that ich nicht eine Version installiere, die bei mir nicht läuft.

*FR40. ACs offen — überschneidet sich mit Story 1.2 (bereits dort deklariert), diese Story formalisiert die Update-Matrix und Release-Compatibility-Tests.*

---

## Epic 7: Lizenzierung & Commercial Activation

Solarbot wird zum kommerziellen Produkt. LemonSqueezy-Kauf-Flow im Wizard, Installations-Disclaimer als Checkbox vor Aktivierung, Lizenz-Signatur-Verifikation beim Start, monatliche Re-Validation mit 14-Tage-Grace, Rabatt-Code für Blueprint-Bestandskunden. Dieses Epic legt eine Lizenz-Schale um den bereits funktionierenden Wizard (Epic 2), ohne Epic 2 zu refactorn.

### Story 7.1: Installations-Disclaimer als sichtbare Checkbox vor Aktivierung

As a Nutzer beim Commissioning,
I want einen klar sichtbaren Disclaimer-Hinweis mit einer aktiven Checkbox bestätigen, bevor ich Solarbot das erste Mal aktiviere,
So that ich explizit zustimme und weiß, dass ich keine Hardware-Schadens-Garantien habe.

**Acceptance Criteria:**

**Given** der Wizard hat den Funktionstest (Story 2.3) erfolgreich abgeschlossen
**When** der Nutzer zur Aktivierung gelangt
**Then** ein Disclaimer-Screen wird vor dem „Aktivieren"-Button angezeigt

**Given** der Disclaimer-Screen
**When** er rendert
**Then** der Text ist sichtbar (nicht in AGB versteckt) und enthält „Keine Garantien für Hardware-Schäden oder Stromausfälle. Solarbot steuert innerhalb technischer Limits, ersetzt aber keine Hersteller-Garantien."

**Given** der Disclaimer-Screen
**When** er rendert
**Then** eine aktive Checkbox „Ich habe den Disclaimer gelesen und akzeptiere die Bedingungen" muss aktiv gesetzt werden, bevor der „Aktivieren"-Button klickbar wird

**Given** der Privacy-Policy-Link
**When** der Disclaimer rendert
**Then** ein Link zur Privacy-Policy ist prominent platziert

**Given** die Disclaimer-Bestätigung
**When** der Nutzer abschickt
**Then** Timestamp und Version des Disclaimer-Textes werden in SQLite gespeichert als Audit-Trail

### Story 7.2: LemonSqueezy-Kauf-Flow im Wizard + Rabatt-Code-Einlösung

As a Nutzer vor der Aktivierung,
I want aus dem Wizard heraus direkt zu LemonSqueezy weitergeleitet werden, dort kaufen, einen optionalen Rabatt-Code einlösen und in den Wizard zurückkehren,
So that der Kauf nahtlos ohne Medienbruch erfolgt.

**Acceptance Criteria:**

**Given** der Nutzer hat den Disclaimer (Story 7.1) bestätigt
**When** der Nutzer „Jetzt kaufen" klickt
**Then** eine LemonSqueezy-Checkout-Seite wird in einem neuen Tab oder Fenster geöffnet mit vorbereitetem Produkt

**Given** der Nutzer ist Blueprint-Bestandskunde
**When** er im LemonSqueezy-Checkout einen Rabatt-Code eingibt
**Then** der Code wird verifiziert und der Preis reduziert

**Given** der Kauf ist abgeschlossen
**When** LemonSqueezy den Callback auslöst
**Then** ein Lizenz-Token wird an Solarbot zurückgegeben und in `/data/license.json` persistiert

**Given** der Nutzer kehrt zum Wizard zurück
**When** das Lizenz-Token vorhanden ist
**Then** der Wizard übergibt automatisch zum „Aktivieren"-Button (Freischaltung)

**Given** der Kauf scheitert oder wird abgebrochen
**When** der Nutzer zurückkehrt
**Then** ein Handlungsvorschlag wird angezeigt („Kauf nicht abgeschlossen. Du kannst es erneut versuchen oder den Support kontaktieren.")

**Given** ausgehende Kommunikation zu LemonSqueezy
**When** sie läuft
**Then** ausschließlich HTTPS, kein Plaintext

**Given** die Datenübertragung
**When** sie geschieht
**Then** nur Lizenz-Token, Add-on-Version und HA-Architektur werden übertragen, keine Geräte- oder Verbrauchsdaten

### Story 7.3: Lizenz-Signatur-Verifikation beim Start

As a Solarbot-Startprozess,
I want die Lizenz-Datei kryptografisch per Signatur verifizieren, bevor Solarbot regelt,
So that Manipulations-Versuche (Lizenz-Fälschung) zuverlässig erkannt werden.

**Acceptance Criteria:**

**Given** das Add-on startet
**When** der Init-Hook läuft
**Then** `/data/license.json` wird geladen und per öffentlichem Schlüssel-Signatur-Verifikation geprüft

**Given** die Signatur ist gültig
**When** Verifikation erfolgt
**Then** der Regelbetrieb wird freigegeben

**Given** die Signatur ist ungültig (z. B. manipulierte Datei)
**When** Verifikation scheitert
**Then** Solarbot startet im „Unvalidated"-Modus, zeigt im Dashboard prominenten Hinweis und blockiert aktive Regelung

**Given** `/data/license.json` fehlt (frisches Setup vor Kauf)
**When** das Add-on startet
**Then** der Wizard-Empty-State wird angezeigt, keine Fehlermeldung

**Given** die Lizenz-Verifikation
**When** sie läuft
**Then** sie dauert ≤ 200 ms (Startup-Performance)

### Story 7.4: Monatliche Re-Validation mit 14-Tage-Graceful-Period

As a lizensiertes Solarbot-Add-on,
I want einmal pro Monat die Lizenz online gegen LemonSqueezy re-validieren und bei Offline-Status die letzten 14 Tage tolerant sein,
So that temporäre Internet-Ausfälle keine Nutzer-Drosslung auslösen, aber langfristiger Lizenz-Missbrauch erkannt wird.

**Acceptance Criteria:**

**Given** das Add-on läuft seit einem Monat seit letzter erfolgreicher Validation
**When** der Trigger feuert
**Then** eine HTTPS-Request zu LemonSqueezy prüft die Lizenz

**Given** die Re-Validation ist erfolgreich
**When** die Antwort zurückkommt
**Then** der `last_validated`-Timestamp wird in SQLite aktualisiert, der Nutzer sieht nichts

**Given** die Re-Validation schlägt fehl (Offline, Timeout, Server-Fehler)
**When** das passiert
**Then** Solarbot setzt den Lizenz-Status auf `grace` und startet den 14-Tage-Countdown

**Given** der `grace`-Zustand
**When** er aktiv ist
**Then** der Nutzer sieht einen dezenten Hinweis im Dashboard („Lizenz-Prüfung ausstehend, X Tage Puffer verbleiben") mit Handlungsvorschlag „Bitte Internet-Verbindung prüfen"

**Given** die 14 Tage Grace sind abgelaufen
**When** weiterhin keine Re-Validation erfolgreich ist
**Then** Solarbot wechselt in Funktions-Drossel (Regelung pausiert, Dashboard zeigt Handlungsvorschlag), nicht harter Stopp

**Given** nach Grace-Ablauf erfolgreich re-validiert
**When** der Status sich ändert
**Then** Solarbot nimmt Regelung sofort wieder auf, logged Recovery-Event

**Given** die Re-Validation
**When** sie durchgeführt wird
**Then** nur Lizenz-Token und Add-on-Version werden übertragen, keine Geräte- oder Verbrauchsdaten

### Story 7.5: Lizenz-Status-Integration in Diagnose-Panel (Epic 4)

As a Alex (Support),
I want den aktuellen Lizenz-Status im Diagnose-Panel aus Epic 4.3 (Verbindungs-Status) sauber sehen,
So that bei Support-Anfragen sofort klar ist, ob der Grund ein Lizenz-Problem ist.

**Acceptance Criteria:**

**Given** das Verbindungs-Status-Panel aus Story 4.3
**When** es rendert und Epic 7 ist ausgeliefert
**Then** der Lizenz-Status zeigt echte Werte statt `unvalidated`-Platzhalter: `valid` / `grace (Tage verbleibend)` / `offline-for-X-days` / `expired`

**Given** der `grace`-Status
**When** er angezeigt wird
**Then** ein Countdown in Tagen und Stunden ist sichtbar

**Given** der Diagnose-Export aus Story 4.5
**When** er erzeugt wird
**Then** der Lizenz-Status (anonymisiert, ohne Token) ist im JSON enthalten

**Given** die Lizenz-Historie
**When** der Nutzer im Diagnose-Panel nachschaut
**Then** die letzten 5 Re-Validation-Events sind einsehbar (Timestamp, Status, ggf. Fehler)
