# Solalex — Add-on Dokumentation

Diese Datei ist die offizielle In-HA-Dokumentation des Add-ons. Der HA-Supervisor
rendert sie im Add-on-Detail-View.

## Installation

1. **Einstellungen → Add-ons → Add-on-Store** öffnen.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/alkly/solalex`
4. Nach dem Refresh erscheint Solalex in der Liste. **Installieren**.
5. Nach Start öffnet sich der Setup-Wizard im Ingress-Frame.

## Voraussetzungen

- Home Assistant OS oder Supervised (Container-only ist nicht supported,
  da das Add-on-Konzept voraussetzt).
- Mindestens einen unterstützten Wechselrichter oder Akku im HA-Netzwerk.
- Gültige Solalex-Lizenz (wird im Wizard via LemonSqueezy gekauft).

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

## Support & Issues

- **Bug-Reports:** Über den Diagnose-Tab des Add-ons (ab Epic 4).
  Bis dahin: [GitHub Issues](https://github.com/alkly/solalex/issues).
- **Kontakt:** info@alkly.de
