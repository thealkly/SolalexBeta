---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
workflowType: 'epics-and-stories'
project_name: 'Solalex'
user_name: 'Alex'
date: '2026-04-22'
amendments:
  - date: '2026-04-22'
    title: 'Scope- und Komplexitäts-Reduktion (16 Cuts)'
    summary: 'Epic 2 Wizard 7→4 Schritte; 3 Adapter Day-1 (Hoymiles + Marstek + Shelly); keine JSON-Templates; Epic 3 Controller-Mono-Modul + persistenter Rate-Limiter; Epic 5 REST-Polling statt WS; Epic 6 1 Backup-Slot + Backup-File-Replace-Rollback; Epic 7 Story 7.3 (Signatur) gestrichen; Story 1.7 (i18n) auf v2. Details im Amendment-Log am Ende.'
  - date: '2026-04-23'
    title: 'Epic 2 — Wizard entfernt, Config-Page mit manuellem Entity-Dropdown'
    summary: 'Epic 2 auf 3 schlanke Stories reduziert: Config-Page (Hardware-Typ + get_states-Dropdown), Funktionstest mit Readback, Disclaimer + Aktivieren. Auto-Detection (FR8) und Live-Werte (FR9) auf v1.5 verschoben. Adapter-Modul-Interface bleibt vollständig — detect() wird in der UI-Journey in v1 nicht aufgerufen.'
---

# Solalex - Epic Breakdown

_Amendment 2026-04-22: Epic-Scope an Architecture-Amendment 2026-04-22 angeglichen. Details im Amendment-Log am Dokumentende._

## Overview

This document provides the complete epic and story breakdown for **Solalex**, decomposing the requirements from the PRD, UX Design Specification and Architecture Decision Document into implementable stories for the MVP (v1).

**Projektname:** Solalex (Arbeitsname, Markenrechts-Vorbehalt)
**Brand:** ALKLY
**Tagline:** Steuert deinen Solar lokal und sekundengenau.
**Projekttyp:** IoT Embedded / Edge Orchestrator (HA Add-on)
**Sprache:** Deutsch (UI, hardcoded in v1 — i18n-Layer ab v2), Englisch (Code-Kommentare)

---

## Requirements Inventory

### Functional Requirements

**Installation & Lizenz**

- **FR1:** Nutzer kann Solalex als HA Add-on über das Custom Repository `alkly/solalex` installieren.
- **FR2:** Nutzer sieht auf der Landing-Page explizit die Voraussetzung „Home Assistant OS" vor dem Download-Schritt. Home Assistant Supervised, Container und Core sind ausdrücklich nicht unterstützt (Amendment 2026-04-23, KISS-Cut).
- **FR3:** Nutzer erwirbt die Lizenz aus dem Setup-Wizard heraus (Weiterleitung zu LemonSqueezy, Rückkehr in den Wizard).
- **FR4:** Nutzer bestätigt vor Lizenz-Aktivierung den Installations-Disclaimer als sichtbare Checkbox.
- **FR5:** Solalex verifiziert die Lizenz einmalig online bei Aktivierung und monatlich erneut, mit Graceful Degradation bei Offline-Status (14-Tage-Grace).
- **FR6:** Bestandskunden können einen Rabatt-Code (Blueprint-Migration) im Kaufflow einlösen.

**Setup & Onboarding**

- **FR7:** Nutzer wählt im Setup-Wizard zwischen zwei Hardware-Pfaden: Hoymiles/OpenDTU, Marstek Venus. *Anker + Manuell-Generic-Pfad auf v1.5 verschoben (Amendment 2026-04-22).*
- **FR8:** Solalex erkennt kompatible HA-Entities automatisch für die Day-1-Hardware: OpenDTU (Hoymiles), Marstek Venus 3E/D, Shelly 3EM. *Anker Solix + Generic-Pfad auf v1.5 verschoben (Amendment 2026-04-22).*
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
- **FR19:** Solalex respektiert hardware-spezifische Rate-Limits zur EEPROM-Schonung (Default ≤ 1 Schreibbefehl pro Device/Minute, per Adapter-Modul überschreibbar, persistent über Restart via `devices.last_write_at`).
- **FR20:** Nutzer kann Nacht-Entlade-Zeitfenster konfigurieren.

**Akku-Management**

- **FR21:** Solalex abstrahiert mehrere Akkus als internen Pool mit Gleichverteilung in v1 (Marstek Venus Multi). *Anker Solix + Generic-Pool-Support auf v1.5 verschoben (Amendment 2026-04-22).*
- **FR22:** Nutzer konfiguriert Min-SoC und Max-SoC pro Akku-Setup.
- **FR23:** Solalex zeigt SoC pro Einzel-Akku und aggregiert für den Pool.

**Monitoring & Dashboard**

- **FR24:** Nutzer sieht im Dashboard den aktuellen Euro-Wert der gesteuerten Ersparnis als 2-Sekunden-Kernaussage.
- **FR25:** Nutzer sieht die Beleg-KPIs (kWh selbst verbraucht + kWh selbst gesteuert) getrennt ausgewiesen, nicht aggregiert.
- **FR26:** Nutzer kann den Bezugspreis (Default 30 ct/kWh) im Dashboard jederzeit anpassen.
- **FR27:** Solalex attribuiert Steuerbefehle mit Event-Source-Flag (`solalex` / `manual` / `ha_automation`) und nutzt dies als Basis der KPI-Berechnung.
- **FR28:** Nutzer sieht den aktuellen Regelungs-Modus (Drossel / Speicher / Multi) im Dashboard.
- **FR29:** Solalex zeigt einen sichtbaren „aktiver Idle-State"-Zustand, wenn keine Steuerung nötig ist („Alles im Ziel. Überwache weiter.").
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
- **FR38:** Solalex sichert vor jedem Update `solalex.db` und `license.json` in `/data/.backup/` (ein Slot, atomisch via `VACUUM INTO .tmp → fsync → rename → fsync(dir)`). *Von „letzte 5 Stände" auf „1 Slot" reduziert im Amendment 2026-04-22 — HA bietet native System-Snapshots, der Add-on-interne Slot braucht nur die letzte vor-Update-Version.*
- **FR39:** Nutzer kann bei fehlgeschlagenem Update manuell auf eine ältere Version zurückrollen (HA Add-on Store). Beim Start der vorherigen Add-on-Version erkennt `run.sh` ein `schema_version`-Mismatch und überschreibt `/data/solalex.db` aus `/data/.backup/solalex.db`. *Backup-File-Replace-Semantik statt Alembic-Downgrade — Amendment 2026-04-22.*
- **FR40:** Solalex unterstützt die aktuelle Home-Assistant-Version und deklariert die supported Range in `addon/config.yaml`.

**Branding & UI-Identität**

- **FR41:** Solalex nutzt in allen UI-Flächen (Dashboard, Setup-Wizard, Diagnose-Tab, Config) durchgängig das ALKLY-Design-System: ALKLY-Farben als Primär-/Sekundär-/Akzent-Palette, DM Sans als Schrift, einheitliche Spacing-/Radius-/Elevation-Tokens.
- **FR42:** Solalex erscheint im HA-Sidebar mit ALKLY-Branding (Icon + Name „Solalex by ALKLY").
- **FR43:** UI ist im HA-Ingress-Frame eingebettet und rendert konsistent im ALKLY-Light-Look. **Keine HA-Theme-Adaption in v1** (Amendment 2026-04-23: Dark-Mode gestrichen; Revisit v1.5).

### NonFunctional Requirements

**Performance**

- **NFR1:** Regel-Zyklus-Dauer ≤ 1 s vom Sensor-Event bis Command-Dispatch (interne Verarbeitung).
- **NFR2:** Dashboard Time-to-First-Data-Display ≤ 2 s ab Klick in Sidebar.
- **NFR3:** Setup-Wizard Auto-Detection ≤ 5 s bei durchschnittlichem HA-Setup.
- **NFR4:** Funktionstest-Durchführung ≤ 15 s (inkl. Readback).
- **NFR5:** Memory Footprint ≤ 150 MB RSS im Idle, ≤ 300 MB RSS im Setup-Wizard-Peak.
- **NFR6:** CPU Footprint ≤ 2 % im Idle, ≤ 15 % im Regelungs-Burst (Raspberry Pi 4).
- **NFR7:** E2E-Regelungs-Latenz hardware-abhängig (5–90 s), Messung ist Pflicht (FR34) — Solalex garantiert Transparenz über Latenz, keine Latenz-Zusage.

**Reliability & Availability**

- **NFR8:** Wiederanlauf-Zeit ≤ 2 Min nach HA-/Add-on-Neustart (bis Regelung wieder aktiv).
- **NFR9:** 24-h-Dauertest als Launch-Gate (0 unbehandelte Exceptions, keine Schwingungen, keine unkontrollierten Einspeisungen unter `load_profile_sine_wave.csv`, 0–3.000 W).
- **NFR10:** 0 kritische Bugs zum Launch (Datenverlust / unkontrollierter Stromfluss / Absturz ohne Wiederanlauf < 2 min).
- **NFR11:** Deterministischer Safe-State bei Kommunikationsausfall (letztes bekanntes WR-Limit halten, nicht freigeben).
- **NFR12:** Lizenz-Offline-Toleranz 14 Tage Graceful-Period, danach Funktions-Drossel (kein Stopp ohne Vorwarnung).

**Security**

- **NFR13:** Container-Isolation in HA Add-on Sandbox, keine externen Port-Expositionen (nur HA Ingress).
- **NFR14:** SUPERVISOR_TOKEN als alleiniger Auth-Mechanismus gegenüber HA; keine eigene Nutzer-Verwaltung.
- **NFR15:** ~~Lizenz-Signatur kryptografisch verifiziert beim Start.~~ **Gestrichen im Amendment 2026-04-22.** Ersetzt durch LemonSqueezy-Online-Check + 14-Tage-Grace (NFR12). Optionale Ed25519-Signatur als v1.5-Punkt dokumentiert, falls Anti-Tamper-Bedarf klar wird.
- **NFR16:** Ausgehende Verbindungen nur HTTPS (LemonSqueezy); kein Plaintext, keine ungeprüften Endpunkte.
- **NFR17:** Keine Telemetry ohne Opt-in (Zero default-tracking).
- **NFR18:** Installations-Disclaimer als sichtbare Checkbox vor Lizenz-Aktivierung.

**Privacy & Data Protection**

- **NFR19:** 100 % lokaler Betrieb — alle Regelungs-, Sensor- und Konfigurationsdaten bleiben in `/data/` auf dem HA-Host.
- **NFR20:** Einzige Drittland-Interaktion = LemonSqueezy-Lizenzprüfung (DSGVO-konformes Merchant-of-Record-Vertragsverhältnis).
- **NFR21:** Datenminimierung bei Lizenzprüfung (nur Lizenz-Key + Add-on-Version, keine Geräte-/Verbrauchsdaten).
- **NFR22:** Privacy-Policy verbindlich in Launch-Dokumentation, im Wizard verlinkt.
- **NFR23:** DSGVO-Compliance durch lokalen Betrieb + keine personenbezogenen Daten im Standard-Flow.

**Usability & Design Quality**

- **NFR24:** Setup-Ziel ≥ 80 % der Nutzer schließen Setup in < 10 Min ab (Launch).
- **NFR25:** Dashboard-Kernaussage (Euro-Wert) in < 2 s erfassbar ohne Scrollen, ohne Interaktion.
- **NFR26:** Durchgängiges ALKLY-Design-System (Farb-Tokens, DM Sans, einheitliche Spacing/Radius/Elevation), Mikrointeraktionen, max. 1 primäre Aktion pro Bildschirm, responsive Layouts; messbar: ≥ 4 von 5 Beta-Testern geben Feedback „sieht hochwertig aus". *(Dark-Mode gestrichen Amendment 2026-04-23)*
- **NFR27:** Pull nicht Push — keine proaktiven Benachrichtigungen außerhalb des Dashboards (kein E-Mail, kein Push, kein HA-Notification).
- **NFR28:** Fakten bei Zahlen, Charakter bei Tun — strikt getrennt; Glossar verbindlich: Akku (nicht Batterie/Speicher), Wechselrichter/WR (bei Erstnennung ausgeschrieben), Smart Meter, Setup-Wizard.

**Integration Reliability**

- **NFR29:** HA WebSocket Reconnect mit exponentiellem Backoff (1 s → 2 s → 4 s → max. 30 s), persistente Subscription-Liste, automatisches Re-Subscribe.
- **NFR30:** HA-Version-Kompatibilitäts-Matrix in `addon/config.yaml` deklariert; Install-Warning bei inkompatibler HA-Version.
- **NFR31:** Adapter-Modul-Versionierung mit Firmware-Pinning (Marstek in v1; Anker ab v1.5); versionstolerante Key-Behandlung im Adapter-Python-Code.
- **NFR32:** GitHub Actions Build-Pipeline Multi-Arch (amd64, aarch64), automatisierte Release-Builds bei Tag-Push.

**Maintainability**

- **NFR33:** Code-Sprachregel: UI/Kommunikation in Deutsch, Code-Kommentare in Englisch.
- **NFR34:** Modulare Architektur — ein Python-Modul pro Adapter (`adapters/hoymiles.py`, `adapters/marstek_venus.py`, `adapters/shelly_3em.py` in v1; `adapters/anker_solix.py`, `adapters/generic.py` ab v1.5); Core-Regelung in `controller.py` hardware-agnostisch als Mono-Modul mit Enum-Dispatch (Amendment 2026-04-22).
- **NFR35:** Test-Coverage ≥ 70 % für Regelungs-Kern-Logik, ≥ 50 % gesamt; alle Adapter mit Integration-Tests gegen Mock-HA.
- **NFR36:** JSON-Logging via stdlib `logging` + `JSONFormatter`-Wrapper (~30 Zeilen in `common/logging.py`), alle Exceptions mit Kontext. *Reduziert von structlog-Dependency auf stdlib im Amendment 2026-04-22.*
- **NFR37:** Solo-Dev-Kriterium — jedes Modul in ≤ 30 Min nachvollziehbar.

**Observability**

- **NFR38:** Strukturiertes Logging in `/data/logs/` (JSON, rotiert 10 MB / 5 Dateien).
- **NFR39:** Add-on-Logs zusätzlich im HA-Log-Panel sichtbar (Standard-Add-on-Verhalten).
- **NFR40:** Diagnose-Export als JSON mit Timestamp im Filename (`solalex-diag_<ISO-Timestamp>.json`). *Schema-Versionierung gestrichen im Amendment 2026-04-22 — Schema-Änderungen folgen dem Changelog, kein eigener Versions-Namespace.*
- **NFR41:** E2E-Latenz-Messung automatisch pro Device, persistent in SQLite (`latency_measurements`-Tabelle).
- **NFR42:** Regelungs-Zyklen mit Source-Flag (`solalex` / `manual` / `ha_automation`) für saubere KPI-Attribution (FR27).
- **NFR43:** Health-Status pro konfigurierter HA-Entity (letzte erfolgreiche Kommunikation, Readback-Erfolgsquote).

**Scalability**

- **NFR44:** Adapter-Modul-Pattern muss ≥ 10 weitere Hersteller (Huawei, SMA, Growatt, Fronius, Zendure, …) in v2–v3 ohne Core-Refactor erlauben. *Umformuliert im Amendment 2026-04-22 — vorher: „Device-Template-System als JSON-Schema".*
- **NFR45:** LemonSqueezy-Lizenz-API trägt skalierungs-unproblematisch (Merchant-of-Record-Infrastruktur).

**Accessibility (selektiv, nicht Launch-Gate)**

- **NFR46:** Tastatur-Navigation für alle Wizard-Schritte.
- **NFR47:** Farbkontrast im ALKLY-Design-System ≥ WCAG 2.1 AA für Text auf Hintergrund.

**Localization**

- **NFR48:** MVP Deutsch only.
- **NFR49:** ~~i18n-ready ab v1 — alle UI-Strings extrahiert in `locales/de.json`, kein Hard-Coding.~~ **Auf v2 verschoben im Amendment 2026-04-22.** v1 hat hardcoded deutsche Strings in Svelte-Komponenten. Bei v2-Englisch folgt ein gezieltes Refactor-Story (`$t('key')`-Wrapper + `locales/de.json` + `locales/en.json`).

### Additional Requirements

*Aus dem Architecture Decision Document extrahiert — technische und infrastrukturelle Anforderungen, die Epic/Story-Entscheidungen direkt beeinflussen.*

**Starter / Base Image:**

- Kein klassischer Greenfield-Starter. **Base: HA Add-on Base Image (Alpine 3.19)**, aufgestockt auf **Python 3.13**. Impact auf Epic 1 Story 1: Add-on-Gerüst mit `addon/config.yaml`, `Dockerfile` (multi-arch), `run.sh`, FastAPI-App-Skeleton, Svelte-Skeleton, SQLite-Init.

**Tech-Stack (fixiert, nicht verhandelbar):**

- Backend: Python 3.13 + FastAPI
- Frontend: Svelte + Tailwind (lokal gehostet, kein CDN)
- Datenbank: SQLite in `/data/solalex.db`
- Integrations-Kanal: HA WebSocket API (`ws://supervisor/core/websocket`) mit `SUPERVISOR_TOKEN` Auth (vom Supervisor automatisch bereitgestellt)

**Distribution & Build:**

- Custom Add-on Repository auf GitHub `alkly/solalex` (privat → public zum Launch)
- GitHub Actions als Build-Pipeline: Multi-Arch-Build (amd64, aarch64), GitHub Container Registry als Image-Host
- Auto-Update via HA Add-on Store Mechanismus

**Persistenz & Backup (Amendment 2026-04-22):**

- `/data/` als Standard-Add-on-Volume (überlebt Updates und Restart)
- Strukturierte Ablage: `solalex.db`, `license.json`, `.backup/solalex.db` (**1 Slot**, nicht rotiert), `logs/` (rotiert 10 MB / 5 Dateien). Kein `templates/`-Verzeichnis mehr — Adapter-Entity-Mappings sind in `backend/src/solalex/adapters/<vendor>.py` hardcoded.
- Backup vor jedem Update via `VACUUM INTO .tmp → fsync → rename → fsync(dir)` (atomisch, crash-safe)
- Rollback = Add-on-Store-Downgrade; beim Start der vorherigen Version erkennt `run.sh` `schema_version`-Mismatch und überschreibt DB aus `.backup/`

**Externe Services (einzige Grenze):**

- LemonSqueezy als alleiniger Merchant-of-Record, nur für Lizenz-Aktivierung und monatliche Re-Validierung
- Kein Telemetry-Server, kein Analytics-Endpunkt, kein Crash-Report ohne Opt-in

**Hardware Day-1 Katalog (produktionsreif, Amendment 2026-04-22 — 3 Hersteller):**

- Wechselrichter: Hoymiles/OpenDTU
- Akkus: Marstek Venus 3E/D (Kern-Segment, 44 % Waitlist)
- Smart Meter: Shelly 3EM

**Verschoben auf Beta-Week-6 / v1.5:**
- Anker Solix (Akku)
- Generic HA Entity (manueller Fallback-Pfad)

**Cross-Cutting Patterns (architektonisch zwingend in mehreren Epics, Amendment 2026-04-22):**

- Closed-Loop-Readback + Fail-Safe als durchgängiges Pattern für jeden Steuerbefehl (Epic Regelung)
- Event-Source-Attribution (`source: solalex | manual | ha_automation`) als Basis aller KPIs (Epic Dashboard + Diagnose)
- E2E-Latenz-Messung pro Device als Input für hardware-spezifische Regel-Parameter (Epic Regelung + Diagnose)
- EEPROM-Rate-Limiting (≤ 1 Schreibbefehl/Device/Minute Default, persistent via `devices.last_write_at`) (Epic Regelung)
- **Adapter-Modul-Pattern** (ein Python-Modul pro Hersteller, hardcoded Entity-Mappings) als Erweiterungspunkt (Epic Setup + Adapter-Epic). *Ersetzt JSON-Template-System.*
- JSON-Logging via stdlib `logging` + `JSONFormatter`-Wrapper (Epic Diagnose)
- ~~i18n-Ready ab v1~~ **gestrichen** — hardcoded deutsche Strings, i18n-Refactor ab v2
- **Lizenz-Gated Startup via LemonSqueezy-Online-Check** (Epic Lizenz). *Keine kryptografische Signatur in v1.*
- **Backup vor jedem Update (1 Slot, atomisch via `VACUUM INTO`)** (Epic Updates). *Von „letzte 5 Stände" auf 1 reduziert.*
- ALKLY-Design-System (CSS Custom Properties als Single-Source, Light-only in v1) (alle UI-Epics) *(Dark-Mode gestrichen Amendment 2026-04-23)*
- **Direkte Funktionsaufrufe im Backend-Control-Flow** (kein Event-Bus, kein Pub/Sub) — Controller ruft KPI und State-Cache direkt auf
- **REST + 1-s-Polling** für Live-Dashboard-Updates (Epic 5) statt WebSocket — WS als v1.5-Upgrade-Pfad

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

- **UX-DR1:** Design-Token-System aufbauen: ALKLY-Farbpalette (Teal/Rot), Primär/Sekundär/Akzent-Rollen. **Light-only Token-Layer in v1** — keine modus-spezifische Saturation (Amendment 2026-04-23: Dark-Mode gestrichen).
- **UX-DR2:** DM-Sans-WOFF2-Font-Pipeline lokal im Add-on-Container (4 Weights: Regular/Medium/Semibold/Bold, Latin + Latin-Extended Subset, ~120 kB total) — **keine externen CDN-Requests**, kein `preconnect` auf Google Fonts.
- **UX-DR3:** Spacing-Raster auf 8px-Basis, Radius-Tokens (16px für Cards), 2-Ebenen-Shadow-System, alles als CSS-Custom-Properties.
- **UX-DR4:** Semantische CSS-Klassen statt Hard-Coded-Werte durchgängig (z. B. `.text-hero`, `.status-chip`, `.energy-ring`).

**Responsive Layout & Platform**

- **UX-DR5:** Responsive Layout-System mit 3 Breakpoints (420px Mobile-HA-App / 768px Tablet / 1200px+ Desktop), **Desktop-canonical entworfen**, dann runterskaliert (Bruch mit Mobile-First-Bias des bestehenden internen DS).
- **UX-DR6:** Navigation adaptiv: Bottom-Nav unter 1024px, Left-Nav ab 1024px (identische 4 Reiter Home/Geräte/Statistik/Einstellungen).
- ~~**UX-DR7:** Dark/Light-Mode-Adaption via HA-Theme-Detection ohne Bruch der ALKLY-Identität.~~ **v1-Cut (Amendment 2026-04-23)** — entfällt, Kandidat für v1.5.

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
- **UX-DR27:** Farbkontrast-Audit ≥ WCAG 2.1 AA für Text auf Hintergrund im Light-Mode. *(Dark-Mode gestrichen Amendment 2026-04-23)*

**Special Routes / View-Regie**

- **UX-DR28:** Diagnose-Route bewusst abgesetzt („Für Fortgeschrittene", nicht in Bottom-Nav), erreichbar über Settings → „Diagnose öffnen"; einsteiger-geschützt mit freundlicher Einleitungszeile und prominentem Export-Button.
- **UX-DR29:** Setup-Wizard als linear-fokussiertes UX-Regime (bildschirmfüllend, **eine primäre Aktion pro Screen**) vs. Dashboard als parallel-modulares UX-Regime — einheitliche Tokens, unterschiedliche Komposition.

**Anti-Pattern-Durchsetzung**

- **UX-DR30:** Anti-Patterns als Lint-/Review-Regeln durchsetzen: keine Tabellen, keine Modal-Dialoge, keine Tooltips, keine technischen IDs sichtbar, keine Gamification (Badges/Streaks/Achievements), keine Loading-Spinner, keine grauen Disabled-Buttons, keine Gradients/Glassmorphism außerhalb der Bottom-Nav, keine „Neu"-Badges, keine Announcement-Banner, keine Push-Notifications.

### FR Coverage Map

| FR | Epic | Thema |
|---|---|---|
| FR1 | Epic 1 | Installation via Custom Add-on Repository `alkly/solalex` |
| FR2 | Epic 1 | Landing-Page Home-Assistant-OS-Voraussetzungs-Hinweis |
| FR3 | Epic 7 | LemonSqueezy-Kauf-Flow im Wizard |
| FR4 | Epic 7 | Installations-Disclaimer als sichtbare Checkbox |
| FR5 | Epic 7 | Monatliche Lizenz-Verifikation mit 14-Tage-Grace |
| FR6 | Epic 7 | Rabatt-Code-Einlösung (Blueprint-Migration) |
| FR7 | Epic 2 | Hardware-Typ-Auswahl + manuelle Entity-Zuweisung per get_states-Dropdown |
| FR8 | **v1.5 / deferred** | Auto-Detection kompatibler HA-Entities (Pattern-Matching) |
| FR9 | **v1.5 / deferred** | Live-Werte neben Sensor-Dropdowns in Config-Page |
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
| FR40 | Epic 6 | HA-Version-Range in `addon/config.yaml` deklariert |
| FR41 | Epic 1 | Durchgängiges ALKLY-Design-System |
| FR42 | Epic 1 | ALKLY-Branding im HA-Sidebar |
| FR43 | Epic 1 | HA-Ingress-Frame mit statischem Light-Look (Dark-Mode gestrichen, Amendment 2026-04-23) |

**Coverage:** 41 / 43 FRs im MVP-Scope abgedeckt · 2 FRs (FR10, FR12) explizit nach v1.5 verschoben ✓

**Amendment 2026-04-22 — Scope-Änderungen an bestehenden FRs (keine neuen Verschiebungen, aber Inhalts-Anpassungen):**
- FR7 (Wizard-Pfade): **3 → 2 Pfade** (Hoymiles + Marstek; Anker/Manuell auf v1.5)
- FR8 (Auto-Detection): **4 → 3 Hersteller** (Hoymiles/OpenDTU + Marstek + Shelly; Anker auf v1.5)
- FR21 (Akku-Pool): **nur Marstek Venus Multi** in v1 (Anker-Pool auf v1.5)
- FR38/FR39 (Backup/Rollback): **1 Backup-Slot** + Backup-File-Replace statt Rotation-of-5 + Alembic-Downgrade
- FR40 (HA-Version-Range): unverändert
- NFR15 (Signatur): **gestrichen** — kein v1-Epic für Signatur-Verifikation
- NFR49 (i18n-ready): **auf v2 verschoben** — Story 1.7 entfällt in v1 (s. u.)

## Epic List

### Epic 1: Add-on Foundation & Branding

**User-Outcome:** Solalex ist über das Custom Repository installierbar, im HA-Sidebar sichtbar, gebrandet, mit ALKLY-Design-System-Foundation und tragfähiger HA-WebSocket-Verbindung. Keine Lizenz-Gate — Add-on startet und ist für Entwicklung und Beta-Test nutzbar.

**FRs covered:** FR1, FR2, FR41, FR42, FR43

**Cross-cutting concerns begründet hier:** Container-Isolation (NFR13), SUPERVISOR_TOKEN-Auth (NFR14), HA-WS-Reconnect mit exponentiellem Backoff (NFR29), Design-System-Foundation mit **CSS Custom Properties als Single-Source** (NFR26, UX-DR1–UX-DR7), Multi-Arch-Build via GitHub Actions (NFR32), Ressourcen-Budget Pi 4 (NFR5, NFR6), lokale DM-Sans-Font-Pipeline inkl. OFL.txt (UX-DR2). *Story 1.7 (i18n-Foundation) entfällt in v1 — siehe Amendment 2026-04-22.*

### Epic 2: Hardware-Konfiguration & Funktionstest

**User-Outcome:** Nutzer öffnet die Config-Page, wählt Hardware-Typ, pickt seine Entities aus einem get_states-Dropdown, führt den Funktionstest durch — Closed-Loop-Readback beweist, dass die Steuerung funktioniert. Zustand danach: „Solalex weiß, was er steuert."

**Amendment 2026-04-23:** Wizard (4-Schritt-Flow + Auto-Detection) entfernt. Ersetzt durch eine schlanke Hardware-Konfigurationsseite mit manuellem Entity-Dropdown (get_states-Scan populiert Optionen, Nutzer wählt selbst). Ermöglicht frühen Funktionstest ohne UI-Overhead. Adapter-Modul-Interface bleibt vollständig — `detect()` wird in der UI-Journey in v1 nicht aufgerufen.

**FRs covered (MVP):** FR7 (angepasst), FR11

**Explicitly deferred nach v1.5:** FR8 (Auto-Detection / Pattern-Matching), FR9 (Live-Werte neben Dropdowns), FR10, FR12

**Cross-cutting concerns begründet hier:** Adapter-Modul-Pattern (kein JSON-Schema), Closed-Loop-Readback im Funktionstest, get_states-Scan als Entity-Dropdown-Basis.

### Epic 3: Aktive Nulleinspeisung & Akku-Pool-Steuerung

**User-Outcome:** Solalex regelt produktiv mit adaptiver Strategie (Drossel / Speicher / Multi-Modus), Akku-Pool-Abstraktion mit Gleichverteilung, Hysterese-basierten Modus-Wechseln, Closed-Loop-Readback und Fail-Safe. Zustand danach: „Solalex arbeitet — der Strom bleibt im Haus."

**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23

**Cross-cutting concerns begründet hier:** **Controller als Mono-Modul** (`controller.py`) mit Enum-Dispatch über `Mode.DROSSEL | SPEICHER | MULTI` + Hysterese-Helper + Fail-Safe-Wrapper — *kein 6-fach-Split mehr (Amendment 2026-04-22)*. SetpointProvider-Interface mit Default-Noop als zero-cost v2-Forecast-Naht (Architecture), Event-Source-Attribution `source: solalex | manual | ha_automation` als KPI-Basis (NFR42), **EEPROM-Rate-Limiting persistent** über Restart (FR19), E2E-Latenz-Messung pro Device als Input für Regel-Parameter (FR34), Safety-Grenze „Policy schlägt vor / Executor entscheidet mit Veto: Range-Check + Rate-Limit + Readback", Regel-Zyklus ≤ 1 s (NFR1), Fail-Safe mit letztem bekannten WR-Limit (NFR11), 24-h-Dauertest als Launch-Gate (NFR9). **Interner Control-Flow = direkte Funktionsaufrufe**, kein Event-Bus.

### Epic 4: Diagnose, Latenz-Messung & Support-Workflow

**User-Outcome:** Alex bekommt mit einem Klick einen strukturierten Diagnose-Export von einem Beta-Tester. Nutzer sieht Verbindungs-Status, letzte 100 Regelzyklen, letzte 20 Fehler, E2E-Latenz pro Device. GitHub-Issues hat ein Bug-Report-Template mit Hardware-/Firmware-Feldern. Zustand danach: „Wenn etwas hakt, kann es sauber gemeldet werden."

**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36

**Cross-cutting concerns begründet hier:** JSON-Logging via **stdlib `logging` + `JSONFormatter`-Wrapper** rotiert 10 MB / 5 Dateien (NFR36, NFR38), Diagnose-Export als **unversioniertes JSON mit Timestamp im Filename** (`solalex-diag_<ISO>.json`, NFR40), E2E-Latenz persistent in SQLite `latency_measurements`-Tabelle (NFR41), Health-Status pro Entity mit Readback-Erfolgsquote (NFR43), Diagnose-Route bewusst abgesetzt („Für Fortgeschrittene", einsteiger-geschützt, UX-DR28), Fehler-Pattern mit Handlungsempfehlung (UX-DR20).

### Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung

**User-Outcome:** Nutzer öffnet Dashboard und sieht in < 2 s die Euro-Kernaussage. Beleg-KPIs, Regelmodus, Idle-State, Energy-Ring und Flow-Visualisierung machen die Arbeit von Solalex sichtbar. Zustand danach: „Solalex beweist seinen Wert sichtbar."

**FRs covered:** FR24, FR25, FR26, FR27, FR28, FR29, FR30

**Cross-cutting concerns begründet hier:** Dashboard-TTFD ≤ 2 s (NFR2, NFR25) via initialem Bulk-GET + **REST-Polling im 1-s-Takt auf `/api/v1/control/state` und `/api/v1/kpi/live`** (Amendment 2026-04-22 — WS als v1.5-Upgrade-Pfad). 14 Kern-Komponenten aus UX-Spec (Hero-Zahl UX-DR8, Charakter-Zeile UX-DR9, Energy-Ring UX-DR10, Flow-Visualisierung UX-DR11, Status-Chips UX-DR12, Bottom-Nav-Glass UX-DR13, Idle-State UX-DR14, Inline-Stepper UX-DR15, Transparenz-Overlay UX-DR16, Modus-Wechsel-Animation UX-DR18, Skeleton-State UX-DR19, Fehler-Pattern UX-DR20, Footer UX-DR21), Custom-PV-Ikonographie in 1,5 px-Stroke (UX-DR22), Mikro-Animationen mit Cubic-Bezier client-side aus letztem Polling-Frame (UX-DR23), Optimistic-UI (UX-DR24), Tastatur-Kürzel 1/2/3/4/D/? (UX-DR25), Anti-Pattern-Durchsetzung (UX-DR30), Pull nicht Push (NFR27), Fakten/Charakter-Trennung (NFR28).

### Epic 6: Updates, Backup & Add-on-Lifecycle

**User-Outcome:** Updates verlaufen reibungslos via Add-on Store. Vor jedem Update wird automatisch ein rotierendes Backup angelegt (letzte 5 Stände). Bei fehlgeschlagenem Update kann manuell zurückgerollt werden. HA-Versions-Range ist deklariert. Zustand danach: „Solalex bleibt über Wochen wartbar — auch wenn ein Update mal hakt."

**FRs covered:** FR37, FR38, FR39, FR40

**Cross-cutting concerns begründet hier:** **1-Slot-Backup** vor jedem Update via `VACUUM INTO .tmp → fsync → rename → fsync(dir)` (atomisch, crash-safe, Amendment 2026-04-22), **Rollback via Backup-File-Replace** statt Alembic-Downgrade-Pfad, HA-Version-Compatibility-Matrix in `addon/config.yaml` mit Install-Warning (NFR30), Multi-Arch-Release-Build bei Tag-Push via GitHub Actions (NFR32, ergänzt Epic 1), Wiederanlauf ≤ 2 Min nach Neustart (NFR8), versionstolerante Adapter-Module mit Firmware-Pinning (NFR31).

### Epic 7: Lizenzierung & Commercial Activation

**User-Outcome:** Solalex wird zum kommerziellen Produkt. LemonSqueezy-Kauf-Flow im Wizard, Installations-Disclaimer als Checkbox vor Aktivierung, **LemonSqueezy-Online-Check beim Start** (keine kryptografische Signatur in v1), monatliche Re-Validation mit 14-Tage-Grace, Rabatt-Code für Blueprint-Bestandskunden. Zustand danach: „Solalex ist launch-ready."

**Amendment 2026-04-22:** Story 7.3 (Lizenz-Signatur-Verifikation) gestrichen. Signatur-Infrastruktur als v1.5-Option dokumentiert, wenn Anti-Tamper-Bedarf klar wird.

**FRs covered:** FR3, FR4, FR5, FR6

**Cross-cutting concerns begründet hier:** Installations-Disclaimer als sichtbare Checkbox (NFR18), **LemonSqueezy-Online-Check bei Aktivierung + monatlich** (ersetzt NFR15 Signatur), 14-Tage-Grace-Period bei Offline (NFR12), LemonSqueezy als einzige Drittland-Interaktion HTTPS-only (NFR16, NFR20), Datenminimierung bei Lizenzprüfung (nur Key + Version, NFR21), Privacy-Policy verbindlich im Wizard verlinkt (NFR22), Graceful Degradation ohne abruptes Stoppen (NFR12). **Egress-Whitelist** (nur `*.lemonsqueezy.com`) via httpx-Transport-Hook + CI-Test.

---

## Epic 1: Add-on Foundation & Branding

Solalex ist über das Custom Repository installierbar, im HA-Sidebar sichtbar, gebrandet, mit ALKLY-Design-System-Foundation und tragfähiger HA-WebSocket-Verbindung. Keine Lizenz-Gate — Add-on startet und ist für Entwicklung und Beta-Test nutzbar.

### Story 1.1: Add-on Skeleton mit Custom Repository & Multi-Arch-Build

As a Entwickler,
I want ein lauffähiges HA Add-on-Gerüst im Custom Repository `alkly/solalex` mit Multi-Arch-Docker-Build,
So that Solalex über den HA Add-on Store installierbar ist und das Fundament für alle weiteren Features trägt.

**Acceptance Criteria:**

**Given** das Repository `alkly/solalex`
**When** Code gepusht und getaggt wird
**Then** GitHub Actions baut Docker-Images für `amd64` + `aarch64` und publisht sie in GitHub Container Registry
**And** Release-Builds werden bei Tag-Push automatisch getriggert

**Given** eine HA-Instanz mit Home Assistant OS
**When** der Nutzer das Custom Repository in den Add-on-Store einfügt
**Then** Solalex erscheint im Store als installierbar

**Given** das Add-on ist installiert
**When** der Container startet
**Then** ein FastAPI-Prozess (Python 3.13) lauscht auf dem Ingress-Port
**And** die SQLite-Datei `/data/solalex.db` wird initialisiert (leer, produktive Tabellen kommen in späteren Stories dazu)

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

**Given** der Container startet zum ersten Mal
**When** `main.py` die Datenbank initialisiert
**Then** `PRAGMA journal_mode=WAL` und `PRAGMA synchronous=NORMAL` sind aktiv
**And** eine `meta`-Tabelle mit `schema_version`-Row existiert
**And** `persistence/migrate.py` wendet alle `persistence/sql/NNN_*.sql`-Dateien forward-only an (in v1 liegt `001_initial.sql` mit leerem Produktiv-Schema vor; produktive Tabellen werden von späteren Stories ergänzt)

### Story 1.2: Landing-Page-Voraussetzungs-Hinweis + HA-Versions-Range

As a Interessent auf alkly.de,
I want vor dem Download-Schritt klar zu sehen, welche HA-Installationstypen und welche HA-Version unterstützt werden,
So that ich kein fehlgeschlagenes Setup erlebe und die Voraussetzungen vorher kenne.

**Acceptance Criteria:**

**Given** die Solalex-Landing-Page auf alkly.de
**When** der Besucher die Seite öffnet
**Then** oberhalb jedes „Install"- oder „Download"-CTAs ist prominent die Zeile „Benötigt Home Assistant OS" sichtbar

**Given** der Check-Block auf der Landing-Page
**When** er gelesen wird
**Then** Home Assistant Supervised, Home Assistant Container und Home Assistant Core sind explizit als „nicht unterstützt" markiert (kein „best-effort"-Aufweichen)

**Given** ein Nutzer versucht Solalex auf einer nicht-unterstützten HA-Version zu installieren
**When** der Add-on-Store die Installation prüft
**Then** eine Install-Warning wird gezeigt
**And** die supported HA-Version-Range ist in `addon/config.yaml` deklariert

### Story 1.3: HA WebSocket Foundation mit Reconnect-Logik

As a Solalex-Backend,
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

**Given** der Container läuft
**When** `GET /api/health` aufgerufen wird
**Then** der Endpoint liefert JSON mit mindestens `ha_ws_connected: bool` und `uptime_seconds: int` (keine Wrapper-Hülle, direktes Objekt — CLAUDE.md Regel 4)
**And** HTTP-Status ist 200, solange der Prozess läuft (auch bei verlorener HA-WS-Verbindung — der Verbindungs-Zustand steckt im Payload, nicht im HTTP-Code)
**And** der Endpoint ist HA-Binary-Sensor-tauglich und ohne Telemetrie (NFR17)

### Story 1.4: ALKLY-Design-System-Foundation — Tokens & lokale DM-Sans-Pipeline

As a Frontend-Entwickler,
I want eine getokte Design-Foundation mit ALKLY-Farbpalette, Spacing-/Radius-/Shadow-Tokens und lokaler DM-Sans-Font-Pipeline,
So that alle späteren UI-Stories auf einem konsistenten visuellen Fundament aufbauen und das 100 %-lokal-Versprechen auch in Assets eingehalten wird.

**Acceptance Criteria:**

**Given** eine Komponente referenziert ein Farb-Token
**When** sie rendert
**Then** Primär-/Sekundär-/Akzent-Farben (ALKLY-Teal, ALKLY-Rot) sind als CSS Custom Properties im Light-Look verfügbar *(Dark-Mode-Varianten gestrichen, Amendment 2026-04-23)*

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

As a Solalex-Nutzer,
I want nach der Installation einen sichtbaren „Solalex by ALKLY"-Eintrag im HA-Sidebar,
So that ich Solalex in meiner gewohnten HA-Navigation wiederfinde.

**Acceptance Criteria:**

**Given** das Add-on ist installiert und gestartet
**When** der Nutzer HA öffnet
**Then** der HA-Sidebar zeigt den Eintrag „Solalex by ALKLY" mit ALKLY-Icon

**Given** `addon/config.yaml`
**When** Ingress konfiguriert ist
**Then** die Ingress-URL ist deklariert und das Icon ist als Asset im Image eingebettet

**Given** der Sidebar-Eintrag
**When** der Nutzer ihn klickt
**Then** der Solalex-UI-Frame öffnet im HA-Panel

### Story 1.6: HA-Ingress-Frame mit statischem Light-Look und Empty-State

*(Amendment 2026-04-23: „Dark/Light-Adaption" gestrichen — UI rendert ausschließlich im ALKLY-Light-Look)*

As a Solalex-Nutzer,
I want beim ersten Öffnen einen sauber gerenderten Begrüßungsscreen im ALKLY-Light-Look,
So that ich sofort weiß: Solalex ist da und wartet auf mich.

**Acceptance Criteria:**

**Given** der Sidebar-Klick
**When** der Solalex-UI-Frame lädt
**Then** die Svelte-App wird im HA-Ingress-iframe vollständig gerendert
**And** die TTFD ist < 2 s

**Given** Empty-State (Wizard noch nicht abgeschlossen)
**When** die UI rendert
**Then** ein Begrüßungs-Screen zeigt Solalex-Titel, kurze Einleitung und einen primären „Setup starten"-Button

**Given** der Footer
**When** das Dashboard oder der Empty-State rendert
**Then** ein 24-px-runder Alex-Avatar + „Made by Alex Kly · Discord · GitHub · Privacy"-Links + dezentes „100 % lokal"-Badge sind sichtbar

### Story 1.7: ~~i18n-Foundation mit `locales/de.json`~~ — **Auf v2 verschoben (Amendment 2026-04-22)**

**Status:** Gestrichen aus v1. Kommt zurück als dedicated v2-Story, wenn englische Lokalisierung ansteht.

**Rationale:** Hardcoded deutsche Strings in Svelte-Komponenten kosten in v1 effektiv nichts. Der i18n-Helper (`$t('key')` + `locales/de.json` + Build-Check) bringt erst Wert bei ≥ 2 Sprachen. Wenn v2-Englisch kommt, ist der Refactor ein gezielter Arbeitsschritt (~1 Tag mit Claude Code): alle Strings extrahieren, Wrapper einsetzen, Keys vergeben, EN-Übersetzung hinzufügen. Früher bauen heißt bezahlte Infrastruktur ohne Gegenleistung.

**Was passiert stattdessen in v1:**
- Deutsche Strings direkt in `.svelte`-Files
- Copy-Glossar-Disziplin aus PRD (Akku, Wechselrichter, Smart Meter, Setup-Wizard) bleibt
- Keine Build-Check-Regel gegen hardcoded Strings

---

## Epic 2: Hardware-Konfiguration & Funktionstest

Nutzer öffnet die Config-Page, wählt Hardware-Typ, pickt seine Entities aus einem get_states-Dropdown, führt den Funktionstest durch — Closed-Loop-Readback beweist, dass die Steuerung funktioniert. Zustand danach: „Solalex weiß, was er steuert." *Hinweis: „Aktivieren" am Ende bedeutet Commissioning (Inbetriebnahme), nicht Lizenz-Aktivierung — die Lizenz-Schale kommt in Epic 7.*

**Amendment 2026-04-23:** Wizard (4-Schritt-Flow + Auto-Detection) entfernt. Ersetzt durch eine schlanke Hardware-Konfigurationsseite. Adapter-Modul-Interface bleibt vollständig — `detect()` wird in der UI-Journey in v1 nicht aufgerufen. Auto-Detection und Live-Werte auf v1.5 verschoben.

### Story 2.1: Hardware Config Page — Typ-Auswahl + Entity-Dropdown

As a Nutzer,
I want eine einfache Konfigurationsseite, auf der ich meinen Hardware-Typ wähle und meine Entities aus einem Dropdown zuweise,
So that Solalex weiß, welche HA-Entities er steuern soll — ohne dass ich Entity-IDs manuell eintippen muss.

**Acceptance Criteria:**

**Given** die UI zeigt den Empty-State
**When** der Nutzer „Konfigurieren" klickt
**Then** die Hardware-Konfigurationsseite wird geöffnet

**Given** die Hardware-Konfigurationsseite öffnet
**When** sie rendert
**Then** läuft ein `get_states`-Scan gegen HA; die Response populiert Entity-Dropdowns je Klasse (WR-Limit-Entity, Smart-Meter-Power-Entity, Akku-SoC-Entity)

**Given** der Nutzer wählt einen Hardware-Typ (Hoymiles/OpenDTU oder Marstek Venus)
**When** er ein Entity-Dropdown öffnet
**Then** zeigt das Dropdown alle HA-Entities aus dem `get_states`-Scan mit Entity-ID + `friendly_name`

**Given** der Nutzer wählt Marstek Venus (Akku)
**When** die Konfigurationsseite rendert
**Then** erscheinen Min/Max-SoC-Felder (Defaults: 15 % / 95 %) + optionales Nacht-Entlade-Zeitfenster (Default 20:00–06:00)

**Given** der Nutzer wählt Hoymiles/OpenDTU oder Marstek Venus
**When** er die Konfiguration speichert
**Then** ist Shelly 3EM als optionaler Smart-Meter-Typ zusätzlich konfigurierbar

**Given** Anker Solix + Generic HA Entity
**When** ein Nutzer diese Hardware hat
**Then** wird er auf v1.5 verwiesen; in v1 werden diese Pfade nicht angeboten

**Given** die Adapter-Module beim Startup registriert werden
**When** die Applikation startet
**Then** Day-1-Adapter für Hoymiles (OpenDTU), Marstek Venus 3E/D und Shelly 3EM sind als Python-Module geladen; jedes Modul exportiert `detect()`, `build_set_limit_command()`, `build_set_charge_command()` (wo anwendbar), `parse_readback()`, `get_rate_limit_policy()`, `get_readback_timing()` gemäß `adapters/base.py` Abstract-Interface

**Given** der Nutzer klickt „Speichern"
**When** alle Pflichtfelder (Hardware-Typ + WR-Limit-Entity) gesetzt sind
**Then** wird die Konfiguration in SQLite gespeichert und der Nutzer zur Funktionstest-Seite weitergeleitet

**Given** das Adapter-Modul-Interface `adapters/base.py`
**When** ein neuer Adapter (v1.5+) hinzukommt
**Then** nur ein neues Python-Modul in `adapters/` + Eintrag in der statischen Registry (`ADAPTERS = {...}`) — kein JSON-Template, keine Loader-Änderung nötig

### Story 2.2: Funktionstest mit Readback & Commissioning

As a Nutzer vor der Inbetriebnahme,
I want einen sichtbaren Funktionstest, in dem Solalex testweise mein WR-Limit oder meinen Akku-Setpoint setzt und mir das Ergebnis zeigt,
So that ich vor der Aktivierung mit eigenen Augen bestätige, dass die Steuerung bei mir funktioniert.

**Acceptance Criteria:**

**Given** die Konfiguration aus Story 2.1 ist gespeichert
**When** der Nutzer „Funktionstest starten" klickt
**Then** Solalex setzt testweise das WR-Limit (Drossel-Setup) oder einen Akku-Setpoint (Speicher-Setup)

**Given** der Funktionstest läuft
**When** er rendert
**Then** ein Live-Chart mit 5-Sekunden-Fenster zeigt WR-Limit-Verlauf, Netz-Einspeisung und SoC parallel (via 1-s-Polling auf `/api/v1/control/state`)

**Given** ein gesetzter Steuerbefehl
**When** Solalex per Readback-Pattern prüft
**Then** ein Checkmark-Tick erscheint bei Bestätigung innerhalb des Adapter-Timeouts; bei ausbleibender Bestätigung erscheint ein roter Cross-Tick

**Given** der Funktionstest läuft
**When** er beginnt
**Then** er schließt in ≤ 15 s ab

**Given** der Funktionstest schlägt fehl
**When** der Fehler angezeigt wird
**Then** ein konkreter Handlungsvorschlag ist enthalten („Entity nicht erreichbar — prüfe HA-Integration XY") statt einer nackten Meldung

**Given** der Funktionstest war erfolgreich
**When** der Nutzer „Aktivieren" klickt
**Then** Solalex übernimmt die Konfiguration in den Regelungs-Zustand und schreibt die Commissioning-Entscheidung als Event in den Log

**Given** der Commissioning-Status ist gesetzt
**When** der Nutzer Solalex wieder öffnet
**Then** die Config-Page/Funktionstest-Flow erscheint nicht mehr, Solalex steht im Regel-Modus

### Story 2.3: Disclaimer + Aktivieren

As a Nutzer,
I want einen expliziten Installations-Disclaimer vor der Aktivierung,
So that ich bewusst bestätige, dass ich die Verantwortung für die Steuerung meiner Anlage übernehme.

**Acceptance Criteria:**

**Given** der Funktionstest war erfolgreich
**When** der Nutzer „Weiter" klickt
**Then** ein Installations-Disclaimer wird als sichtbare Checkbox-Seite angezeigt (Text ist Pflicht-Lesen, Checkbox ist nicht vorangekreuzt)

**Given** die Disclaimer-Checkbox
**When** der Nutzer sie nicht angekreuzt hat
**Then** ist der „Aktivieren"-Button deaktiviert

**Given** die Disclaimer-Checkbox ist angekreuzt
**When** der Nutzer „Aktivieren" klickt
**Then** wird der Commissioning-Status in SQLite gesetzt; Epic 7 ergänzt hier den LemonSqueezy-Kauf-Flow ohne diese Story zu refactorn

---

## Epic 3: Aktive Nulleinspeisung & Akku-Pool-Steuerung

Solalex regelt produktiv mit adaptiver Strategie (Drossel / Speicher / Multi-Modus), Akku-Pool-Abstraktion mit Gleichverteilung, Hysterese-basierten Modus-Wechseln, Closed-Loop-Readback und Fail-Safe. Zustand danach: „Solalex arbeitet — der Strom bleibt im Haus."

### Story 3.1: Core Controller (Mono-Modul, Sensor → Policy → Executor) + Event-Source + Readback + persistenter Rate-Limit

As a Solalex-Backend,
I want einen hardware-agnostischen Controller (`controller.py` Mono-Modul) mit Enum-Dispatch über `Mode.DROSSEL | SPEICHER | MULTI`, der Sensor-Events zu Steuerbefehlen verarbeitet, Source-Attribution schreibt, Readback prüft und EEPROM-Rate-Limits persistent durchsetzt,
So that alle Modi und Adapter-Module denselben Safety-Layer und dieselbe Event-Basis nutzen.

**Amendment 2026-04-22:** Controller als Mono-Modul statt 6-fach-Split. Interner Control-Flow = direkte Funktionsaufrufe (`controller.on_sensor_update` → `executor.dispatch` → `state_cache.update` + `kpi.record`). Kein Event-Bus, kein asyncio.Queue. Rate-Limiter persistiert letzten Write-Timestamp in `devices.last_write_at` — nach Restart wartet der Executor mindestens `last_write_at + 60s` pro Device.

**Acceptance Criteria:**

**Given** ein Sensor-Event kommt über die HA-WS-Subscription
**When** der Controller es verarbeitet (`controller.on_sensor_update`)
**Then** die Pipeline läuft Sensor → Mode-Dispatch (Enum-Switch) → Policy → Executor → Readback mit einer Gesamtdauer ≤ 1 s

**Given** ein Policy-Vorschlag
**When** der Executor ihn erhält
**Then** die Veto-Kaskade prüft Range-Check, Rate-Limit und Readback-Erwartung, bevor der Steuerbefehl an HA geht

**Given** ein erfolgreicher Steuerbefehl
**When** er ausgelöst wird
**Then** er wird mit Source-Flag (`source: solalex`) in SQLite-Tabelle `control_cycles` geschrieben (Timestamp, Sensor-Value, gesetztes Limit, Modus, Source, Latenz) via `repositories.control_cycles.insert`

**Given** ein manuelles oder HA-Automation-triggered Event
**When** es erkannt wird
**Then** der Source-Flag ist entsprechend `manual` bzw. `ha_automation`

**Given** jeder Steuerbefehl
**When** er gesendet wurde
**Then** ein Readback-Check via State-Subscription prüft innerhalb des Adapter-spezifischen Timeout-Fensters (aus `adapters/<vendor>.get_readback_timing()`) die Bestätigung

**Given** ein Adapter-Modul definiert Rate-Limit (Default ≤ 1 Schreibbefehl/Device/Minute)
**When** der Executor den nächsten Befehl prüft
**Then** Befehle innerhalb des Intervalls werden unterdrückt und im Log markiert
**And** der Rate-Limiter liest/schreibt `devices.last_write_at` — auch nach Add-on-Restart bleibt der EEPROM-Schutz gewahrt

**Given** das SetpointProvider-Interface
**When** kein Forecast-Provider aktiv ist
**Then** die Default-Noop-Implementation liefert „current reactive behavior" zurück — Interface ist in `controller.py` als kleine Klasse `SetpointProvider` mit Docstring „v2-Forecast-Naht" definiert (kein separates Modul)

**Given** die E2E-Latenz-Messung
**When** ein Steuerbefehl ausgelöst wird
**Then** die Zeit zwischen Befehl und messbarem Smart-Meter-Effekt wird in `latency_measurements`-Tabelle geloggt

**Given** der Controller ruft KPI und State-Cache auf
**When** ein Zyklus komplett ist
**Then** `kpi.record(cycle)` und `state_cache.update(cycle)` werden als direkte Funktionsaufrufe im selben async-Context aufgerufen (kein Event-Bus, kein Pub/Sub-Dispatch)

### Story 3.2: Drossel-Modus — WR-Limit-Regelung für Nulleinspeisung

As a Balkon-Benni / Neugier-Nils ohne Akku,
I want dass Solalex bei PV-Überschuss das WR-Limit reaktiv runterregelt, damit keine Watt ans Netz verschenkt werden,
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

**Given** das Adapter-Modul definiert EEPROM-Rate-Limit
**When** aufeinanderfolgende Drossel-Zyklen nötig wären
**Then** Rate-Limit aus Story 3.1 wird respektiert (persistent über Restart)

### Story 3.3: Akku-Pool-Abstraktion mit Gleichverteilung & SoC-Aggregation

As a Marstek-Micha mit 2× Venus 3E (Kernsegment),
I want dass Solalex meine Akkus intern als logischen Pool behandelt mit Gleichverteilung in v1 und aggregiertem SoC-Wert,
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

**Given** das Adapter-Modul-Pattern (Amendment 2026-04-22)
**When** der Pool für einen Marstek-Venus-Pool initialisiert wird
**Then** die Kommunikation zu jedem Akku läuft über das Adapter-Modul `adapters/marstek_venus.py`, nicht über Direct-Hardware-Calls

### Story 3.4: Speicher-Modus — Akku-Lade/-Entlade-Regelung innerhalb SoC-Grenzen

As a Marstek-Micha / Beta-Björn mit Akku,
I want dass Solalex bei PV-Überschuss den Akku-Pool lädt und bei Grundlast aus dem Pool entlädt, respektierend die Min/Max-SoC-Grenzen,
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

**Given** Marstek Venus Hardware (Day-1-Kern-Segment)
**When** Speicher regelt
**Then** ±30 W-Toleranz wird eingehalten (lokale API-Latenz-abhängig)

**Given** Anker Solix Hardware (v1.5)
**When** der Anker-Adapter verfügbar ist
**Then** ±30 W-Toleranz wird ebenfalls eingehalten — betrifft v1.5-Scope

**Given** ein Schreibbefehl an einen Einzel-Akku im Pool
**When** er ausgelöst wird
**Then** der Rate-Limit aus Story 3.1 wird pro Device durchgesetzt

### Story 3.5: Adaptive Strategie-Auswahl & Hysterese-basierter Modus-Wechsel (inkl. Multi-Modus)

As a Nutzer mit hybridem Setup (WR + Multi-Akku),
I want dass Solalex meine Regelungs-Strategie automatisch aus dem erkannten Hardware-Setup ableitet und zwischen Drossel / Speicher / Multi-Modus ohne Oszillation wechselt,
So that ich nie einen Modus manuell einstellen muss und im Grenzbereich (Akku-knapp-voll) kein Flackern entsteht.

**Acceptance Criteria:**

**Given** die Hardware-Konfiguration aus Epic 2
**When** Solalex startet
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
I want dass Solalex bei Kommunikationsausfall (HA-WS, Entity, Readback-Timeout) in einen deterministischen Safe-State geht und nicht blind weiter steuert,
So that mein Netz-Export und meine Hardware nie unkontrolliert aus dem Ruder laufen.

**Acceptance Criteria:**

**Given** der WebSocket-Kanal fällt aus (Reconnect läuft)
**When** der Controller das erkennt
**Then** Solalex setzt keine neuen Schreibbefehle mehr, das zuletzt gesetzte WR-Limit bleibt am WR bestehen (nicht freigeben)

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
**Then** Solalex hält das letzte Limit, kein neuer Schreibbefehl wird gesendet

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
**Then** oben ein freundlicher Hinweis „Für Fortgeschrittene — hier siehst du, was Solalex intern tut. Bei Supportanfragen: Export-Button rechts oben." wird angezeigt

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
**Then** er kann nach Source (`solalex` / `manual` / `ha_automation`) und Modus filtern

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
**Then** ein positiver Leerzustand „Keine Fehler. Solalex läuft sauber." wird angezeigt

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
**Then** die UI aktualisiert sich beim nächsten 1-s-Polling-Tick auf `/api/v1/control/state` ohne Reload *(Amendment 2026-04-22 — Polling statt WS)*

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
**Then** eine strukturierte JSON-Datei `solalex-diag_<ISO-Timestamp>.json` wird erzeugt *(Amendment 2026-04-22 — unversioniert, Timestamp im Filename)*

**Given** der Export
**When** er erzeugt wird
**Then** er enthält: Schema-Version, Zeitstempel, Add-on-Version, HA-Version, Container-Arch, aktive Device-Templates mit Version, Firmware-Versionen (falls erfassbar), letzte 100 Zyklen, letzte 20 Fehler, Verbindungs-Status-Snapshot, Latenz-Summary, aktueller Regel-Modus

**Given** der Export
**When** er ausgelöst wird
**Then** er wird als Download angeboten UND in den Zwischenspeicher kopiert mit Toast „Export kopiert"

**Given** der Export
**When** er erzeugt wird
**Then** er enthält keine personenbezogenen Daten, keine Lizenz-Keys, keine HA-Auth-Token (Review-Checkliste im Code dokumentiert)

**Given** diese Story wird gekippt
**When** der Fallback greift
**Then** im Diagnose-Tab ist stattdessen ein prominenter Link „HA-Panel-Log herunterladen" zur Standard-Add-on-Log-Download-Funktion platziert

### Story 4.6: GitHub-Issues Bug-Report-Template

As a Beta-Tester / Support-Anfrager,
I want ein strukturiertes GitHub-Issue-Template im Repository, das alle Pflichtfelder für einen Bug-Report vorgibt,
So that Alex nicht nachfragen muss, welche Hardware/Firmware ich nutze.

**Acceptance Criteria:**

**Given** das Repository `alkly/solalex`
**When** ein Nutzer einen neuen Issue anlegt
**Then** ein Template „Bug Report" wird als Default vorgeschlagen

**Given** das Template
**When** es gerendert wird
**Then** es enthält Pflichtfelder: Hardware (WR-Modell + Firmware, Akku-Modell + Firmware, Smart Meter), HA-Installationstyp + Version, Solalex-Version, Beschreibung, erwartetes Verhalten, tatsächliches Verhalten, Platzhalter für Diagnose-Export-Anhang

**Given** der Diagnose-Tab
**When** der Nutzer „Fehler melden" klickt
**Then** ein Direktlink zum GitHub-Issue-Template mit vorausgefüllten Basis-Feldern (Solalex-Version, HA-Version, Container-Arch) wird geöffnet

**Given** das Template
**When** es im Repository existiert
**Then** es liegt unter `.github/ISSUE_TEMPLATE/bug-report.yml` (YAML-Form für strukturiertes Parsing durch GitHub)

---

## Epic 5: Dashboard mit Euro-Wert & Live-Visualisierung

Nutzer öffnet Dashboard und sieht in < 2 s die Euro-Kernaussage. Beleg-KPIs, Regelmodus, Idle-State, Energy-Ring und Flow-Visualisierung machen die Arbeit von Solalex sichtbar.

### Story 5.1a: Live-Betriebs-View post-Commissioning (Mini-Shell, vorgezogen — Amendment Sprint Change Proposal 2026-04-24)

As a Nutzer direkt nach Klick auf „Aktivieren",
I want sofort sehen, was Solalex gerade regelt — ein Live-Diagramm, aktueller Modus, letzte Zyklen,
So that ich Vertrauen gewinne, dass die Regelung arbeitet, bevor Epic 4 (Diagnose) und Story 5.1b (Euro-Hero) fertig sind.

**Scope-Pflock:** Diese Story zieht aus der ursprünglichen Story 5.1 nur den Shell-Grundbestand vor: Route + Live-Chart + Modus-Chip + Mini-Zyklen-Liste. Kein Euro-Wert, kein Energy-Ring, keine Responsive-Nav, keine Charakter-Zeile, kein Bezugspreis-Stepper — das bleibt komplett in Story 5.1b. Ziel: ≤ 2 Dev-Tage. Zeitliche Einordnung: **nach Story 3.2 (Drossel produktiv)**, damit der Chart beim ersten Launch echte Dispatches zeigt.

**Acceptance Criteria:**

**Given** mindestens ein Device mit `commissioned_at IS NOT NULL`
**When** das Frontend die Ingress-Route öffnet
**Then** die Route `/live` (oder `/` als Default-Route für commissioned Setups) rendert — non-commissioned Setups bleiben im Wizard-Flow aus Epic 2

**Given** die Live-Betriebs-View
**When** sie rendert
**Then** die bereits existierende `LineChart.svelte`-Komponente (aus Story 2.2) rendert mit 5-s-Sliding-Window und drei Serien: Sensor-Wert (grid_meter via Shelly 3EM, Teal/Rot nach Vorzeichen), Target-Wert (letzter Dispatch `target_value_w` aus `control_cycles`, Blau), Readback-Wert (aktueller HW-State via `adapter.parse_readback`, Grau)

**Given** die View rendert
**When** sie den aktuellen Regel-Modus anzeigt
**Then** ein Modus-Chip oben zeigt einen von `Drossel | Speicher | Multi | Idle` mit semantischem Icon — Wert stammt aus dem erweiterten `/api/v1/control/state`-Feld `current_mode`

**Given** die View rendert
**When** sie die Mini-Zyklen-Liste zeigt
**Then** unter dem Chart werden die letzten 10 Zyklen aus `control_cycles` (via `list_recent(limit=10)`) in einer kompakten Liste dargestellt: Timestamp (relativ, z. B. „vor 3 s"), Source-Badge (`solalex` / `manual` / `ha_automation`), Target-Watts, Readback-Status-Badge (`passed` / `failed` / `vetoed`), Latenz

**Given** der Rate-Limiter blockiert einen Write
**When** die View den Status anzeigt
**Then** ein kleiner Hinweis „Nächster Write in X s" rendert — berechnet aus `devices.last_write_at + min_interval_s − now` (Datenfeld `rate_limit_status` im Polling-Payload)

**Given** das Polling
**When** es läuft
**Then** `/api/v1/control/state` wird im 1-s-Takt gepollt (bestehender Hook aus 2.2), kein WebSocket, keine externe Chart-Lib (CLAUDE.md-Stolpersteine)

**Given** noch keine `control_cycles`-Einträge (frischer Commissioning, Controller hat noch nicht dispatched)
**When** die View rendert
**Then** Chart zeigt Skeleton-Pulse (≥ 400 ms, UX-DR19) mit neutraler Zeile „Regler wartet auf erstes Sensor-Event." — kein Fehlerzustand, kein Spinner

**Given** das Backend
**When** `/api/v1/control/state` antwortet
**Then** der Payload enthält zusätzlich zu den bestehenden Feldern: `current_mode: "drossel" | "speicher" | "multi" | "idle"`, `recent_cycles: [...]` (max 10 Einträge, snake_case-JSON, keine Wrapper-Hülle — CLAUDE.md Regel 4), `rate_limit_status: [{ "device_id": int, "seconds_until_next_write": int | null }, ...]`

**Given** der Controller schließt einen Zyklus ab
**When** er `state_cache.update(...)` aufruft (Story 3.1 AC 11)
**Then** er ruft zusätzlich `state_cache.update_mode(self._current_mode)` — neues Feld `current_mode` in `StateCache` mit Setter-Methode

**Given** während eines laufenden Funktionstests (Story 2.2, `state_cache.test_in_progress == True`)
**When** die View rendert
**Then** statt des Live-Betriebs-Charts wird eine Info-Zeile „Funktionstest läuft — Regelung pausiert" mit Link zur Funktionstest-Route gezeigt

**Given** Unit-Tests
**When** sie laufen
**Then** neue Tests: `test_state_snapshot_exposes_current_mode` (Backend, pytest), `test_state_snapshot_includes_recent_cycles` (Backend, pytest), `test_live_view_renders_mode_chip_and_chart` (Frontend, vitest). Coverage ≥ 90 % auf neuen Backend-Code-Pfaden. Alle 4 Hard-CI-Gates grün (ruff, mypy --strict, pytest, SQL-Migrations-Ordering — keine neue Migration)

**Given** diese Story wird gekippt (Notfall-Fallback)
**When** der Fallback greift
**Then** nach Commissioning landet der User auf einem statischen Hinweis-Screen „Solalex regelt — detaillierte Ansicht folgt in v1.0" mit Link zur Diagnose-Route (Epic 4, sobald verfügbar)

### Story 5.1b: Dashboard-Hero + Euro-Wert + Responsive Navigation (Rest-Scope nach 5.1a — Amendment Sprint Change Proposal 2026-04-24)

**Preamble:** Story 5.1a (Live-Betriebs-View, vorgezogen) hat bereits den Shell-Grundbestand geliefert (Route, `LineChart.svelte`-Integration, Modus-Chip, Mini-Zyklen-Liste, Skeleton-State). Story 5.1b ergänzt darauf aufbauend die Hero-Zone mit Euro-Wert, Bezugspreis-Transparenz-Overlay, Responsive Bottom-/Left-Nav mit Glass-Effect, Tastatur-Shortcuts und Footer. Die AC-Semantik „Hero-Zone in < 2 s sichtbar" bezieht sich auf die bereits existierende 5.1a-Route — es wird keine neue Route angelegt.

As a Nutzer,
I want beim Öffnen des Dashboards in weniger als 2 Sekunden eine Euro-Zahl sehen, die mir sagt, was Solalex heute für mich gesteuert hat,
So that ich abends mit einem Blick weiß: es hat sich gelohnt.

**Acceptance Criteria:**

**Given** der Nutzer klickt auf „Solalex" in der HA-Sidebar
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
I want unter der Euro-Zahl zwei separate Beleg-Kacheln sehen, die strikt trennen, was passiv selbst verbraucht vs. aktiv von Solalex gesteuert wurde,
So that meine Euro-Zahl nachvollziehbar und prüfbar ist.

**Acceptance Criteria:**

**Given** das Dashboard unter der Hero-Zone
**When** es rendert
**Then** zwei separate Kacheln „Selbst verbraucht: X kWh" und „Selbst gesteuert: Y kWh" werden angezeigt

**Given** die KPI-Berechnung
**When** „selbst gesteuert" aggregiert wird
**Then** werden nur Zyklen mit Source-Flag `solalex` aus der `control_cycles`-Tabelle gezählt

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
So that ich auf einen Blick verstehe, was Solalex gerade tut — nicht nur in Zahlen, sondern visuell.

**Acceptance Criteria:**

**Given** die Hero-Zone
**When** sie rendert
**Then** ein zentraler Energy-Ring zeigt die Leistungs-Balance (Erzeugung vs. Verbrauch) — Teal für Überschuss, Rot für Bezug, Grau für Neutral

**Given** Live-Sensor-Daten
**When** sie durch 1-s-Polling auf `/api/v1/control/state` aktualisiert werden
**Then** der Ring adaptiert in quasi-Echtzeit ohne Reload *(Amendment 2026-04-22 — Polling statt WS; clientseitige Animation interpoliert zwischen Frames)*

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
I want immer sehen, in welchem Modus Solalex gerade regelt (Drossel / Speicher / Multi) und wenn er wechselt, soll das sichtbar sein,
So that ich verstehe, dass Solalex denkt und aktiv entscheidet — nicht nur einen statischen Zustand zeigt.

**Acceptance Criteria:**

**Given** Solalex ist im Regelbetrieb
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
**Then** eine Inline-Beschreibung fährt aus („Im Speicher-Modus lädt Solalex den Akku bei Überschuss und entlädt zur Grundlast-Deckung", keine Modal)

**Given** keine Oszillation (aus Story 3.5 Hysterese)
**When** Modus-Wechsel passieren
**Then** keine flackernden Chip-Wechsel im Dashboard

### Story 5.6: Aktiver Idle-State als positive Aussage

As a Nutzer (z. B. mittags, nichts passiert gerade),
I want dass Solalex mir im Idle-Zustand aktiv sagt „alles im Ziel — ich überwache weiter", statt leer oder tot zu wirken,
So that ich nicht denke, das Ding sei kaputt, wenn gerade keine Steuerung nötig ist.

**Acceptance Criteria:**

**Given** Solalex regelt aktuell nicht (keine Überschuss, keine Entlade-Anforderung)
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
I want über der Euro-Zahl eine kurze narrative Zeile sehen, die mir sagt, was Solalex gerade tut (z. B. „Venus-Pool lädt mit 1.400 W · Überschuss wird gespeichert"),
So that das Dashboard sich lebendig anfühlt und Solalex Charakter hat — ohne dass Zahlen selbst dramatisiert werden.

**Acceptance Criteria:**

**Given** Solalex regelt aktiv
**When** das Dashboard rendert
**Then** über der Euro-Zahl ist eine Charakter-Zeile (14 px, 500-Weight, Teal oder Text-Secondary) sichtbar mit narrativer Beschreibung des aktuellen Tuns und Piktogrammen

**Given** die Charakter-Zeile
**When** sie rendert
**Then** sie beschreibt ausschließlich Solalexs eigenes Tun (Modus, aktive Zuweisung) — niemals die Zahlen selbst

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
**Then** sie liegen in v1 als Python-Konstanten-Liste in `kpi/character_lines.py` (z. B. `CHARACTER_LINES = {Mode.SPEICHER: [...], Mode.DROSSEL: [...]}`) — *Amendment 2026-04-22, keine i18n-Infrastruktur in v1*. Bei v2-Englisch wandert das Mapping in `locales/de.json` + `locales/en.json`.

---

## Epic 6: Updates, Backup & Add-on-Lifecycle

*Amendment 2026-04-22: Story 6.2 (1-Slot-Backup) und 6.3 (Backup-File-Replace) jetzt mit vollständigen Acceptance-Criteria.*

Updates verlaufen reibungslos via Add-on Store. Vor jedem Update wird automatisch ein 1-Slot-Backup atomisch angelegt (`VACUUM INTO` mit fsync+rename). Bei fehlgeschlagenem Update kann manuell zurückgerollt werden — das Backup-File-Replace beim Start der vorherigen Version stellt den Vor-Update-Stand wieder her. HA-Versions-Range ist deklariert.

### Story 6.1: Auto-Update via HA Add-on Store

As a Nutzer,
I want Solalex automatisch (oder nach manueller Bestätigung) über den HA Add-on Store aktualisieren können,
So that ich Bugfixes und neue Features ohne Bastelei bekomme.

*FR37. ACs offen — siehe PRD „HA Add-on Store als alleiniger Update-Kanal", „Auto-Update durch Nutzer aktivierbar".*

### Story 6.2: 1-Slot-Backup vor jedem Update (atomisch via VACUUM INTO)

As a Solalex-Lifecycle,
I want vor jedem Update automatisch `solalex.db` und `license.json` in `/data/.backup/` sichern (ein Slot, atomisch, crash-safe),
So that bei einem fehlgeschlagenen Update der vorherige Zustand wiederherstellbar ist.

**Amendment 2026-04-22:** Von „letzte 5 Stände" auf 1 Slot reduziert. HA bietet native System-Snapshots; der Add-on-interne Slot braucht nur die letzte vor-Update-Version. `templates/`-Kopie entfällt (Adapter sind Python-Module im Image).

**Acceptance Criteria:**

**Given** ein Add-on-Update beginnt
**When** `run.sh` den neuen Container bootet
**Then** vor dem Schema-Migrate-Schritt wird `VACUUM INTO '/data/.backup/solalex.db.tmp'` ausgeführt
**And** `fsync(tmp_fd)` auf das temporäre File
**And** `os.rename('/data/.backup/solalex.db.tmp', '/data/.backup/solalex.db')`
**And** `fsync(dir_fd)` auf `/data/.backup/` damit das Rename persistiert

**Given** ein Crash während des Backup-Vorgangs
**When** der Container erneut startet
**Then** `/data/.backup/solalex.db` ist entweder der alte oder der neue vollständige Stand — nie eine halb-geschriebene Datei

**Given** `license.json`
**When** der Backup-Vorgang läuft
**Then** wird es als `/data/.backup/license.json` kopiert (keine atomicity-Anforderung, read-only in dieser Phase)

**Given** der Backup-Slot
**When** er nach erfolgreichem Update bestehen bleibt
**Then** er wird erst beim nächsten Update überschrieben (kein automatisches Löschen)

**Given** die Backup-Semantik
**When** in `backup/snapshot.py` implementiert
**Then** sie folgt exakt: `VACUUM INTO .tmp` → `fsync` → `rename` → `fsync(dir)` — diese Sequenz ist in Code-Kommentar dokumentiert

### Story 6.3: Rollback via Backup-File-Replace beim Start der vorherigen Add-on-Version

As a Nutzer nach fehlgeschlagenem Update,
I want über den HA Add-on Store eine ältere Version zurückinstallieren können, und Solalex überschreibt `/data/solalex.db` automatisch aus `/data/.backup/solalex.db`, wenn der Schema-Stand nicht mehr zur Add-on-Version passt,
So that ich nie einen Update-Hotfix fürchte.

**Amendment 2026-04-22:** Backup-File-Replace statt Alembic-Downgrade-Pfad. Das Backup-Schema matcht die zugehörige Add-on-Version automatisch — keine Forward/Backward-Migrations-Pflicht nötig.

**Acceptance Criteria:**

**Given** der Nutzer installiert eine ältere Add-on-Version via HA Add-on Store
**When** der Container der alten Version startet (`run.sh`)
**Then** Schritt 1: `schema_version` aus `/data/solalex.db` lesen
**And** Schritt 2: erwartete maximale `schema_version` der installierten Add-on-Version aus `backend/src/solalex/persistence/sql/`-Verzeichnis ableiten (höchste `NNN_*.sql`-Nummer)
**And** Schritt 3: wenn DB-`schema_version` > erwartete Version → automatisches `cp /data/.backup/solalex.db /data/solalex.db` + `cp /data/.backup/license.json /data/license.json`

**Given** der Backup-Replace-Vorgang
**When** er läuft
**Then** ein Log-Eintrag mit Timestamp, alter DB-Version, erwartete Version und Replace-Status wird geschrieben

**Given** kein Backup vorhanden (z. B. Frisch-Install)
**When** ein Schema-Mismatch erkannt wird
**Then** Solalex startet im Empty-State + Wizard; der Wizard baut einen sauberen neuen Stand auf, kein Daten-Verlust-Risiko

**Given** ein erfolgreicher Rollback
**When** der Container startet
**Then** Wiederanlauf-Zeit ≤ 2 Min (NFR8) wird eingehalten

**Given** der Rollback-Pfad
**When** ein User ihn manuell auslöst (über HA Add-on Store-Downgrade)
**Then** keine weitere User-Interaktion nötig — das Backup-File-Replace läuft beim ersten Start der alten Version automatisch

### Story 6.4: HA-Version-Kompatibilitäts-Matrix in `addon/config.yaml`

As a Nutzer mit älterer oder neuerer HA-Version,
I want dass Solalex die unterstützte HA-Version-Range deklariert und bei Inkompatibilität eine Install-Warning zeigt,
So that ich nicht eine Version installiere, die bei mir nicht läuft.

*FR40. ACs offen — überschneidet sich mit Story 1.2 (bereits dort deklariert), diese Story formalisiert die Update-Matrix und Release-Compatibility-Tests.*

---

## Epic 7: Lizenzierung & Commercial Activation

Solalex wird zum kommerziellen Produkt. LemonSqueezy-Kauf-Flow im Wizard, Installations-Disclaimer als Checkbox vor Aktivierung, **LemonSqueezy-Online-Check beim Start** (keine kryptografische Signatur in v1, Amendment 2026-04-22), monatliche Re-Validation mit 14-Tage-Grace, Rabatt-Code für Blueprint-Bestandskunden. Dieses Epic legt eine Lizenz-Schale um den bereits funktionierenden Wizard (Epic 2), ohne Epic 2 zu refactorn.

### Story 7.1: Installations-Disclaimer als sichtbare Checkbox vor Aktivierung

As a Nutzer beim Commissioning,
I want einen klar sichtbaren Disclaimer-Hinweis mit einer aktiven Checkbox bestätigen, bevor ich Solalex das erste Mal aktiviere,
So that ich explizit zustimme und weiß, dass ich keine Hardware-Schadens-Garantien habe.

**Acceptance Criteria:**

**Given** der Funktionstest (Story 2.2) erfolgreich abgeschlossen und Commissioning gesetzt
**When** der Nutzer zur Aktivierung gelangt
**Then** ein Disclaimer-Screen wird vor dem „Aktivieren"-Button angezeigt

**Given** der Disclaimer-Screen
**When** er rendert
**Then** der Text ist sichtbar (nicht in AGB versteckt) und enthält „Keine Garantien für Hardware-Schäden oder Stromausfälle. Solalex steuert innerhalb technischer Limits, ersetzt aber keine Hersteller-Garantien."

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
**Then** ein Lizenz-Key wird an Solalex zurückgegeben und in `/data/license.json` als Plain-JSON persistiert (keine Signatur, Amendment 2026-04-22)

**Given** der Nutzer kehrt zum Wizard zurück
**When** der Lizenz-Key vorhanden ist
**Then** der Wizard übergibt automatisch zum „Aktivieren"-Button (Freischaltung)

**Given** der Kauf scheitert oder wird abgebrochen
**When** der Nutzer zurückkehrt
**Then** ein Handlungsvorschlag wird angezeigt („Kauf nicht abgeschlossen. Du kannst es erneut versuchen oder den Support kontaktieren.")

**Given** ausgehende Kommunikation zu LemonSqueezy
**When** sie läuft
**Then** ausschließlich HTTPS, kein Plaintext

**Given** die Datenübertragung
**When** sie geschieht
**Then** nur Lizenz-Key, Add-on-Version und HA-Architektur werden übertragen, keine Geräte- oder Verbrauchsdaten

### Story 7.3: ~~Lizenz-Signatur-Verifikation beim Start~~ — **Gestrichen (Amendment 2026-04-22)**

**Status:** Vollständig aus v1 entfernt. Als v1.5-Option dokumentiert, falls Anti-Tamper-Bedarf klar wird.

**Rationale:** Die 14-Tage-Grace (NFR12) macht Offline-Crack ohnehin trivial — Ed25519-Signatur mit einem einzelnen, im Image gebackenen Public Key hätte diesen Angriffsvektor nicht wirksam geschlossen. Kosten: `cryptography`-Dependency, Public-Key-Rotation-Gap, Build-Pipeline-Komplexität für Key-Injection, Dev-Key-Management. Nutzen in v1: gering.

**Was stattdessen in v1:**
- Lizenz-Key als Plain-JSON in `/data/license.json` (siehe Story 7.2)
- Beim Start: LemonSqueezy-Online-Check, wenn unbekannter oder ungültiger Key → `unvalidated`-Modus (wie vorher)
- Wenn kein Internet beim Start: bestehender `last_validated_at` + 14-Tage-Grace gilt
- Manipulations-Erkennung passiv über LemonSqueezy-Server-Abgleich (wenn ein Key-Fake nicht in der LemonSqueezy-DB ist, schlägt die Re-Validation fehl)

**Was nach v1.5 (optional):**
- Ed25519-Signatur über Canonical-JSON-Payload
- `public_key.pem` (oder Key-Array für Rotation) im Image
- Zusätzliche Verify-Schicht vor Regelbetrieb

### Story 7.4: Monatliche Re-Validation mit 14-Tage-Graceful-Period

As a lizensiertes Solalex-Add-on,
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
**Then** Solalex setzt den Lizenz-Status auf `grace` und startet den 14-Tage-Countdown

**Given** der `grace`-Zustand
**When** er aktiv ist
**Then** der Nutzer sieht einen dezenten Hinweis im Dashboard („Lizenz-Prüfung ausstehend, X Tage Puffer verbleiben") mit Handlungsvorschlag „Bitte Internet-Verbindung prüfen"

**Given** die 14 Tage Grace sind abgelaufen
**When** weiterhin keine Re-Validation erfolgreich ist
**Then** Solalex wechselt in Funktions-Drossel (Regelung pausiert, Dashboard zeigt Handlungsvorschlag), nicht harter Stopp

**Given** nach Grace-Ablauf erfolgreich re-validiert
**When** der Status sich ändert
**Then** Solalex nimmt Regelung sofort wieder auf, logged Recovery-Event

**Given** die Re-Validation
**When** sie durchgeführt wird
**Then** nur Lizenz-Key und Add-on-Version werden übertragen, keine Geräte- oder Verbrauchsdaten

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

---

## Amendment-Log

### 2026-04-23 — Epic 2: Wizard entfernt, Config-Page mit manuellem Entity-Dropdown

| Epic / Story | Änderung |
|---|---|
| **Epic 2 (List-Summary)** | Titel geändert: „Setup-Wizard & Hardware-Onboarding" → „Hardware-Konfiguration & Funktionstest" |
| **Epic 2 (Detail)** | Vollständig neu geschrieben: 3 Stories statt bisheriger Wizard-Struktur |
| **Story 2.1 (neu)** | Hardware Config Page: Hardware-Typ-Auswahl + get_states-Dropdown-Zuweisung. Kein Auto-Detection-Aufruf in der UI-Journey. |
| **Story 2.2 (neu)** | Funktionstest mit Readback & Commissioning (inhaltlich = alter Story 2.3) |
| **Story 2.3 (neu)** | Disclaimer + Aktivieren (inhaltlich = bisheriger Wizard-Schritt 4, minimal) |
| **FR7** | Angepasst: „Drei Hardware-Pfade im Wizard" → „Hardware-Typ-Auswahl + manuelle Entity-Zuweisung per get_states-Dropdown" |
| **FR8** | Auf v1.5 verschoben: Auto-Detection (Pattern-Matching) entfällt in v1-UI-Journey |
| **FR9** | Auf v1.5 verschoben: Live-Werte neben Dropdowns |

**Rationale:** Früher Funktionstest ohne Wizard-Overhead. `adapter.detect()` wird in v1 nicht aufgerufen — das Interface bleibt vollständig für v1.5.

**Neue v1.5-Kandidaten (ergänzt):**
- FR8 Auto-Detection mit Pattern-Matching
- FR9 Live-Werte neben Entity-Dropdowns

---

### 2026-04-22 — Scope- und Komplexitäts-Reduktion (16 Cuts)

Angleichung an Architecture-Amendment 2026-04-22. Auswirkung auf Epics:

| Epic / Story | Änderung |
|---|---|
| **Header** | Amendment-Hinweis ergänzt, Sprache-Regel aktualisiert (i18n auf v2) |
| **Requirements Inventory — FR7** | Wizard: 3 → 2 Hardware-Pfade (Hoymiles + Marstek) |
| **Requirements Inventory — FR8** | Auto-Detection: 4 → 3 Hersteller |
| **Requirements Inventory — FR19** | Rate-Limit persistent über Restart via `devices.last_write_at` |
| **Requirements Inventory — FR21** | Akku-Pool v1 nur Marstek Venus |
| **Requirements Inventory — FR38** | 1 Backup-Slot statt 5 Rotations-Stände, atomisch via VACUUM INTO |
| **Requirements Inventory — FR39** | Rollback = Backup-File-Replace statt Alembic-Downgrade |
| **NFR15 (Signatur)** | Gestrichen. Ersetzt durch LemonSqueezy-Online-Check. |
| **NFR31 (Device-Template-Versionierung)** | Umformuliert zu Adapter-Modul-Versionierung |
| **NFR34 (Modularität)** | Controller als Mono-Modul mit Enum-Dispatch |
| **NFR36 (Logging)** | stdlib statt structlog |
| **NFR40 (Diagnose-Export)** | Unversioniert, Timestamp im Filename |
| **NFR44 (Skalierbarkeit)** | Adapter-Modul-Pattern statt JSON-Template-System |
| **NFR49 (i18n-ready)** | Auf v2 verschoben |
| **Additional Requirements — Persistenz** | 1 Slot, kein `templates/`-Verzeichnis |
| **Additional Requirements — Hardware-Katalog** | 3 Hersteller Day-1, 2 auf v1.5 verschoben |
| **Cross-Cutting Patterns** | Adapter-Modul-Pattern, LemonSqueezy-Check, 1-Slot-Backup, direkte Funktionsaufrufe, REST-Polling |
| **FR Coverage Map** | Scope-Notiz im Anschluss (unten an der Tabelle) |
| **Epic 1** | Cross-cutting-Hinweis aktualisiert; CSS-Custom-Properties als Single-Source (keine TS-Tokens) |
| **Story 1.7 (i18n-Foundation)** | **Gestrichen in v1.** Rationale + v2-Plan dokumentiert. |
| **Epic 2** | Wizard 7 → 4 Schritte; 3 Adapter Day-1; hardcoded Entity-Mappings statt JSON-Templates |
| **Story 2.1** | 2 Hardware-Pfade, 4 Schritte (Hardware → Detection+Config → Funktionstest → Activation), Smart-Meter + Battery als Sub-Cards in Schritt 2 |
| **Story 2.2** | Adapter-Module statt JSON-Loader; Live-Werte via 1-s-Polling |

| **Epic 3** | Controller-Mono-Modul mit Enum-Dispatch; direkte Funktionsaufrufe; persistenter Rate-Limiter |
| **Story 3.1** | AC umgeschrieben für Mono-Modul + Direct-Calls + persistent Rate-Limit |
| **Story 3.2 / 3.3 / 3.4** | Anker-Referenzen entfernt (Marstek als Day-1-Kernsegment) |
| **Epic 4** | Logging via stdlib, Diagnose-Export unversioniert |
| **Story 4.3** | Status-Update via 1-s-Polling statt WebSocket |
| **Story 4.5** | Filename `solalex-diag_<Timestamp>.json` |
| **Epic 5** | Polling statt WS als First-Shot |
| **Story 5.4** | Energy-Ring Update via Polling mit clientseitiger Interpolation |
| **Story 5.7** | Character-Zeilen als Python-Konstanten in v1 (keine i18n-Infrastruktur) |
| **Epic 6** | Vollständige ACs für Story 6.2 (1-Slot-Backup atomisch) und Story 6.3 (Backup-File-Replace-Rollback) |
| **Epic 7** | Online-Check-Fokus, keine Signatur in v1 |
| **Story 7.2** | Lizenz-Key (vorher Lizenz-Token) als Plain-JSON in `/data/license.json` |
| **Story 7.3** | **Gestrichen in v1.** Rationale + v1.5-Plan dokumentiert. |
| **Story 7.4 / 7.5** | Sprache von Lizenz-Token auf Lizenz-Key angepasst |

**Explizit beibehalten:** Multi-Arch-Build (amd64 + aarch64), 24-h-Dauertest als Launch-Gate, Closed-Loop-Readback, Fail-Safe, E2E-Latenz-Messung, alle UX-DRs aus der UX-Spec (außer dort wo von Polling-statt-WS und Token-Single-Source-aus-CSS betroffen — diese bleiben semantisch, nur die technische Umsetzung ist vereinfacht).

**Neue v1.5-Kandidaten (aus v1 verschoben):**
- Anker Solix Adapter + Generic-HA-Entity-Pfad
- Blueprint-Automation-Import (war schon v1.5, bleibt)
- FR10 lautloses Akku-Schritt-Überspringen (trivial in 4-Schritt-Wizard, Polish)
- i18n-Infrastruktur (als Voraussetzung für v2-Englisch)
- WebSocket-Live-Stream (falls Polling-Latenz beißt)
- Kryptografische Lizenz-Signatur (falls Anti-Tamper-Bedarf klar wird)

**Kipp-Reihenfolge (angepasst für Wochen 5–7):**

| Kipp-Rang | Was wird gekippt | Fallback | Nachziehen in |
|---|---|---|---|
| 1 | Diagnose-Export-Funktion | HA-Panel-Log-Download | v1.5 |
| 2 | Character-Zeilen (Story 5.7) | Neutral-Mode | v1.1 |
| 3 | E2E-Latenz-Messung im UI sichtbar | nur SQLite-Log | v1.1 |
| 4 | Modus-Wechsel-Animation | statischer Modus-Chip-Wechsel | v1.1 |

Blueprint-Import bleibt aus der Kipp-Liste draußen — ist bereits v1.5-Scope.

**Nicht kippbar (Safety + Glaubwürdigkeit):**
- Closed-Loop-Readback + Fail-Safe
- Marstek + Hoymiles + Shelly Day-1
- Funktionstest + Installations-Disclaimer vor Lizenz
- Euro-Wert im Dashboard (REST, TTFD ≤ 2 s)
- LemonSqueezy-Integration
- 24h-Dauertest
- 1-Slot-Backup + Backup-File-Replace-Rollback
