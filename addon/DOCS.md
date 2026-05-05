# Solalex by ALKLY — Add-on Dokumentation

Diese Datei ist die offizielle In-HA-Dokumentation des Add-ons. Der HA-Supervisor
rendert sie im Add-on-Detail-View.

## Installation

1. **Einstellungen → Add-ons → Add-on-Store** öffnen.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/alkly/solalex`
4. Nach dem Refresh erscheint **Solalex by ALKLY** in der Liste. **Installieren**.
5. Nach Start öffnet sich der Setup-Wizard im Ingress-Frame.

## Voraussetzungen

- **Home Assistant OS** (ausschließlich — siehe Abschnitt „Unterstützte
  HA-Versionen" für Details zu nicht unterstützten Varianten).
- Mindestens einen unterstützten Wechselrichter oder Akku im HA-Netzwerk.
- Gültige Solalex-Lizenz (wird im Wizard via LemonSqueezy gekauft).

## Unterstützte HA-Versionen

- **Minimum:** 2026.4.0 (im `addon/config.yaml` via `homeassistant:`-Feld
  gepinnt; niedrigere Versionen erhalten eine Install-Warning im Add-on-Store).
- **Getestet bis:** 2026.4.3 (aktuelle stable zum Release-Zeitpunkt).
- **Unterstützt:** ausschließlich **Home Assistant OS**.
- **Nicht unterstützt:** Home Assistant Supervised, Home Assistant Container,
  Home Assistant Core.

Du weißt nicht, welche Variante du hast? Öffne in HA:
**Einstellungen → System → Info**.

## Unterstützte Hardware (Day 1)

- **Hoymiles / OpenDTU** — Wechselrichter-Limit-Regelung
- **Marstek Venus 3E/D** — Akku-Lade-/Entlade-Steuerung
- **Shelly 3EM** — Smart-Meter-Lesung

Weitere Adapter (Anker Solix, Generic HA Entity) folgen in v1.5.

## Ressourcen-Budget (Raspberry Pi 4 Referenz)

- **Idle-RSS Ziel:** ≤ 150 MB
- **Idle-CPU Ziel:** ≤ 2 %
- **Aktiver Regelzyklus:** kurze Peaks bis ~10 % CPU

### Messung (Story 1.1 Skeleton, lokal via Docker)

| Messgröße | Gemessen | Ziel | Status |
|---|---|---|---|
| Idle-RSS | 64.9 MiB | ≤ 150 MB | ✅ 43 % des Budgets |
| Idle-CPU | 0.49 % | ≤ 2 % | ✅ 25 % des Budgets |

> Gemessen auf Docker Desktop (macOS, Apple Silicon) mit dem amd64-Image
> via Rosetta-Emulation. Auf einem echten Pi 4 (aarch64 nativ) sind die
> Werte tendenziell niedriger. Finale Validation erfolgt in der Beta-Phase
> auf echter Pi-4-Hardware.

## Daten-Persistenz

Alle dauerhaften Daten (SQLite-DB, Lizenz, Logs, Backup-Slot) liegen unter
`/data/` und überleben Add-on-Restart sowie Update.

```
/data/
├── solalex.db         # Betriebsdaten (KPIs, Config, Audit)
├── license.json       # Lizenz-Check-Response
├── logs/
│   └── solalex.log    # JSON-Zeilen, 10 MB × 5 Rotation
└── .backup/
    └── solalex.db     # 1-Slot-Backup vor jedem Update
```

## Keine externen Ports

Solalex kommuniziert ausschließlich über den Home-Assistant-Ingress-Proxy.
Es gibt keine externen Port-Expositionen. Dies ist eine harte Policy
(AC 7 Story 1.1, NFR28) und wird im `addon/config.yaml` via `ports: {}`
durchgesetzt.

## Robustheit

- **Closed-Loop-Readback:** Jeder Steuerbefehl an die Hardware wird nach
  dem Senden aus Home Assistant zurückgelesen. Stimmen Soll- und Ist-Wert
  nicht überein, schlägt der Cycle fehl und der Audit-Trail im Live-Tab
  zeigt den Grund.
- **Sensor-Verfügbarkeits-Guard:** Bevor Solalex einen Wert schreibt,
  prüft es, ob der Readback-Sensor in Home Assistant gerade einen Wert
  liefert. Ist der Sensor `unavailable` / `unknown` (z. B. Marstek-Modbus
  zwischen zwei Polls), überspringt Solalex den Schreibvorgang und
  schreibt eine Audit-Zeile „Sensor nicht verfügbar". Das verhindert
  blinde Schreibversuche und reduziert Log-Rauschen in HA. Notfall-Bypass
  für Hardware ohne sinnvollen Availability-State: in der DB für das
  betreffende Device `config_json["skip_readback_availability_check"] =
  true` setzen — kein UI in v1.
- **Rate-Limit pro Gerät:** Standard 60 s Mindestabstand zwischen
  Schreibvorgängen pro WR/Akku, persistent in der DB (überlebt Restart).

## Solalex Status in Home Assistant

Nach dem Setup-Wizard legt Solalex acht Input-Helper in Home Assistant an,
die den internen Steuer-Status jederzeit per HA-Card oder Statistik-Graph
sichtbar machen. Sie liegen unter **Einstellungen → Geräte & Dienste →
Helfer** mit dem Filter `solalex_*`.

| Entity | Typ | Bedeutung |
| --- | --- | --- |
| `input_text.solalex_active_mode` | input_text | Aktuell aktiver Modus: `drossel`, `speicher`, `multi`, `export`, `paused`, `fail_safe`, `unknown` |
| `input_text.solalex_last_cycle_reason` | input_text | Letzter Cycle-Reason aus dem Audit-Trail (z. B. `noop: deadband`, `dispatched`, `fail_safe: range_check_violation`) |
| `input_text.solalex_last_command_at` | input_text | UTC-ISO-8601-Zeitstempel des letzten Schreibvorgangs |
| `input_text.solalex_fail_safe_state` | input_text | `inactive` (alles ok), `active_hold` (Fail-Safe greift), `active_release` (Erholung gerade aktiv) |
| `input_number.solalex_cycle_age_seconds` | input_number (`state_class=measurement`) | Sekunden seit dem letzten Cycle (0 = gerade jetzt; > 60 = Controller hängt) |
| `input_number.solalex_recent_cycles_count` | input_number (`state_class=measurement`) | Anzahl Cycles in der letzten Stunde |
| `input_number.solalex_fail_safes_today` | input_number (`state_class=measurement`) | Anzahl Fail-Safe-Events seit lokal-Mitternacht |
| `input_number.solalex_mode_switches_today` | input_number (`state_class=measurement`) | Anzahl Mode-Wechsel (z. B. DROSSEL → SPEICHER) seit lokal-Mitternacht |

**Update-Verhalten:** Solalex aktualisiert die Helper nach jedem Cycle, gedrosselt auf max. 1 Update pro Helper pro 30 s. Bei Mode-Wechsel, Fail-Safe-Übergang oder Wechsel des Reason-Prefixes wird der Update sofort durchgereicht.

**Tages-Counter:** `fail_safes_today` und `mode_switches_today` sind in-memory; sie resetten bei lokal-Mitternacht und beim Add-on-Restart. Den vollständigen Tagesverlauf hält der HA-Recorder via `state_class: measurement` — Mid-Day-Restarts erscheinen als Sprung-zu-0 + Wieder-Anstieg.

**Helper manuell gelöscht?** Solalex schreibt eine Warnung ins Log (`status_helper_publish_failed`) und macht weiter — die Steuerung ist davon nicht betroffen. Den Helper kannst du wieder anlegen, indem du den Wizard erneut durchläufst (Geräte → Reset → Wizard → Aktivieren).

### Diagnose-Endpoint `/api/v1/diagnostics/devices`

Für tiefere QA-Inspektion liefert das Add-on über die Ingress-API einen direkten Snapshot pro angelegtem Device. Beispiel-Response:

```json
{
  "devices": [
    {
      "id": 1,
      "type": "generic_battery",
      "role": "wr_charge",
      "entity_id": "number.akku_charge",
      "adapter_key": "generic_battery",
      "topology": "multi_entity",
      "battery_control": { "topology": "multi_entity", "discharge_setpoint_entity": "...", "...": "..." },
      "wizard_completed": true,
      "last_write_at": "2026-05-04T03:42:11Z",
      "last_cycle_reason": "dispatched",
      "writes_24h": 2881,
      "fail_safes_24h": 0,
      "noops_24h": 84219,
      "noop_reason_top3": [
        { "reason": "noop: deadband", "count": 45112 },
        { "reason": "noop: rate_limited", "count": 23001 },
        { "reason": "noop: wr_limit_state_cache_miss", "count": 16106 }
      ]
    }
  ],
  "generated_at": "2026-05-04T05:50:00Z"
}
```

`window_h` (Query-Parameter, Default 24, Max 168) wählt das Aggregat-Fenster. Der Endpoint ist auf p99 ≤ 200 ms ausgelegt (4 Devices × 100 000 Cycles).

## Support & Issues

- **Bug-Reports:** Über den Diagnose-Tab des Add-ons (ab Epic 4).
  Bis dahin: [GitHub Issues](https://github.com/alkly/solalex/issues).
- **Kontakt:** info@alkly.de
