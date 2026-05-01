# Solalex by ALKLY

**Sekundengenaue aktive Nulleinspeisung und Akku-Pool-Steuerung als Home-Assistant-Add-on.**

Solalex steuert Wechselrichter und Akkus sekundengenau über die Home-Assistant-WebSocket-API.
100 % lokal, keine Telemetry, kein Cloud-Zwang — nur der monatliche Lizenz-Check verlässt
Dein Netz.

> **Status:** Beta. Aktive Erprobung mit ausgewählten Beta-Tester:innen.

## Installation

Voraussetzung: **Home Assistant OS** auf `amd64` oder `aarch64`. Andere HA-Varianten
(Supervised, Container, Core) werden in der Beta nicht unterstützt.

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store**.
2. Oben rechts **⋮ → Repositories**.
3. URL eintragen: `https://github.com/thealkly/SolalexBeta`
4. Nach dem Refresh erscheint **Solalex by ALKLY** in der Add-on-Liste.
5. **Installieren**, dann starten. Nach dem Start öffnet sich der Setup-Wizard im
   Home-Assistant-Ingress-Frame.

## Unterstützte Hardware (Day 1)

- **Wechselrichter:** Hoymiles / OpenDTU, Trucki, ESPHome, MQTT-bridged (Generic-Adapter
  über HA-Capabilities — Domain + `unit_of_measurement`)
- **Akku:** Marstek Venus 3E/D
- **Smart Meter:** Shelly 3EM, ESPHome SML, Tibber, MQTT-bridged (Generic-Adapter)

Weitere Adapter (z. B. Anker Solix, vendor-spezifische Tuning-Profile) sind für
Folge-Releases geplant.

## Sicherheits- und Datenschutz-Grundsätze

- **100 % lokal:** keine Cloud-Roundtrips für Steuerung oder Monitoring.
- **Closed-Loop-Readback:** jeder Schreib-Befehl an die Hardware wird verifiziert,
  bevor der nächste Zyklus läuft.
- **Rate-Limit + Fail-Safe:** persistierte Schreib-Limits pro Gerät; bei
  Kommunikations-Ausfall hält Solalex das letzte bekannte Limit, statt freizugeben.
- **Egress-Whitelist:** nur `*.lemonsqueezy.com` für den monatlichen Lizenz-Check;
  alles andere wird im Build per CI-Test geblockt.

## Lizenz

Proprietär — siehe [LICENSE](LICENSE). Source ist zur Auditierbarkeit offen, aber
nicht freie Software.

## Kontakt & Support

ALKLY — info@alkly.de
