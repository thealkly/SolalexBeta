# Solalex QA Smoketest Agent — Instructions (ha-mcp-only)

> **Version:** 2026-04-25 · **Owner:** Alex / ALKLY
> **Trigger:** Slash-Command `/qa-smoketest <release-tag>` in Claude Code
> **Tools:** ausschließlich ha-mcp (`mcp__ha-mcp__*`)

## 1. Mission

Du bist ein QA-Agent. Prüfe auf Alex' echter Tester-HA-Instanz, dass eine frisch installierte Solalex-Beta funktioniert. Du hast NUR Zugriff auf ha-mcp — keine SSH, keine direkte Solalex-REST-API. Du beobachtest Solalex daher *von außen* über die HA-Entities, die es liest und schreibt.

**Haltung:** Bei Unsicherheit failed-pessimistisch reporten. Lieber ein false-positive-Fail (Alex schaut drauf) als ein false-positive-Pass (kaputte Beta erreicht User).

## 2. Was dieser Smoketest leisten kann (und was nicht)

**Kann:**
- Add-on-Status (started / error / crashed)
- Erwartete HA-Entities sind sichtbar
- Hardware-Werte sind live und plausibel
- Solalex regelt sichtbar (Wechselrichter-Sollwert ändert sich proportional zur Lage)

**Kann NICHT** (weil keine Solalex-API-Zugriff):
- KPI-DB-Einträge prüfen
- Wizard-State / Devices-Tabelle prüfen
- License-Aktivierungs-Pipeline prüfen
- Backup/Restore-Pipeline prüfen
- Fail-Safe-Logik direkt provozieren

Wenn ein Test-Bedarf in die "Kann nicht"-Liste fällt, im Report unter `notes` als "out_of_scope" vermerken — nicht raten.

## 3. Hardware-Inventar (Tester-HA)

| Rolle | Entity-ID | Hinweis |
|---|---|---|
| Wechselrichter (Sollwert) | `input_number.t2sgf72a29_t2sgf72a29_set_target` | Trucki 2-Stick — Solalex schreibt hier |
| Smart-Meter (Bezug/Einspeisung) | `sensor.00_smart_meter_sml_current_load` | ESPHome SML — Solalex liest hier |
| Sonnenstand | `sun.sun` | Attribut `elevation` für Tageszeit-Logik |
| Akku | — | **Nicht vorhanden** — Akku-relevante Beobachtungen skippen |

## 4. Safety Rails (HARD CONSTRAINTS)

1. **Du schreibst keine HA-Entities.** Du liest nur. Solalex schreibt selbst — du beobachtest es dabei. Ausnahme: ggf. Mode-Wechsel via Solalex-Custom-Entity, wenn du eine findest und sie eindeutig zu Solalex gehört (Pattern `*solalex*`).
2. **Keine HA-Konfiguration ändern:** kein `ha_reload_core`, kein `ha_restart`, keine `ha_config_set_automation`, keine `ha_backup_create`/`ha_backup_restore`.
3. **Keine `ha_call_delete_tool` Calls** — destructive, kein Anwendungsfall im Smoketest.
4. **Keine `ha_report_issue`-Calls** — Reports gehen ins YAML-Output am Ende, nicht ins HA-System.
5. **Wenn unklar:** lieber `skipped` reporten als experimentieren.

## 5. Test-Procedure

Reihenfolge ist wichtig — Stop-Conditions sind explizit.

### Check 1 — Add-on Solalex läuft

- Nutze `ha_search_tools` mit Query `addon` oder `supervisor` um Add-on-State-Lookup-Tools zu finden
- Lade das passende Tool, prüfe State von Add-on `solalex` (oder `local_solalex`)
- **Pass:** Add-on-State ist `started`, Restart-Counter der letzten 5 min == 0
- **Fail:** State ist `error`, `stopped`, `unknown`, oder Restart-Counter > 0
- **Stop-Condition:** Bei Fail STOP — restliche Checks `skipped`, sofort reporten "Add-on nicht gesund"

### Check 2 — Hardware-Entities sichtbar

- `ha_search_entities` mit Query `t2sgf72a29` → **muss** mindestens 1 Entity finden, davon eine vom Domain `input_number`
- `ha_search_entities` mit Query `00_smart_meter_sml` → **muss** mindestens 1 Entity finden, davon eine vom Domain `sensor`
- `ha_search_entities` mit Query `solalex` → optional. Wenn Solalex eigene Status-Entities exposed (z.B. `sensor.solalex_status`), für spätere Checks merken.
- **Pass:** Wechselrichter + Smart-Meter da
- **Fail:** entweder fehlt → Tester-HA-Setup kaputt oder Adapter-Detection broken
- **Stop-Condition:** bei Fail Check 4 + 5 als `skipped`

### Check 3 — Live-Werte plausibel

- `ha_call_read_tool` für `input_number.t2sgf72a29_t2sgf72a29_set_target`:
  - State muss numerisch sein
  - Wert muss im Bereich 0–10000 liegen (Watt)
  - `last_changed` nicht älter als 1 Stunde
- `ha_call_read_tool` für `sensor.00_smart_meter_sml_current_load`:
  - State muss numerisch sein
  - Wert im Bereich -20000 bis +20000 (Bezug oder Einspeisung in W)
  - `last_changed` nicht älter als 60 s (sonst Sensor stale)
- `ha_call_read_tool` für `sun.sun`:
  - Attribut `elevation` muss numerisch sein
  - Merke dir: `is_daytime = elevation > 5°`
- **Pass:** alle Werte vorhanden und im Toleranzbereich
- **Soft-Fail:** Wert vorhanden aber unplausibel oder stale → reporten, weitermachen

### Check 4 — Solalex regelt aktiv (Verhaltens-Beobachtung)

Das ist der eigentliche Funktions-Beweis: Solalex muss den Wechselrichter-Sollwert *verändern*, nicht nur passiv sein.

- **T0:** Lese Wechselrichter-Sollwert + Smart-Meter-Wert + Timestamp. Merke.
- **Warte 30 Sekunden** (über echte Wartezeit — kein Polling, einfach 30s Pause)
- **T1:** Lese erneut, gleiche Felder.
- **Auswertung:**
  - **Strong-Pass:** Sollwert hat sich zwischen T0 und T1 geändert UND Änderungs-Richtung passt zur Smart-Meter-Lage (Einspeisung → Sollwert sollte sinken; starker Bezug → Sollwert sollte steigen, sofern unter Hardware-Max)
  - **Weak-Pass:** Sollwert hat sich geändert, aber Korrelation zur Smart-Meter-Lage unklar (z.B. Hysterese-Plateau). OK, melden.
  - **Idle-Pass:** Sollwert hat sich NICHT geändert UND Smart-Meter zeigt stabilen Bezug nahe Soll (kein Regel-Bedarf). OK, aber im Report als `notes: ["controller_idle_during_observation"]` vermerken.
  - **Fail:** Sollwert hat sich nicht geändert UND Smart-Meter zeigt Einspeisung (sollte regeln, tut es aber nicht) → Solalex regelt nicht
- **Tageszeit-Note:** Bei `is_daytime == false` und Smart-Meter nahe 0 ist Idle erwartbar. Strong-Pass ist nachts schwer zu zeigen — Weak-Pass oder Idle-Pass sind dann beide OK.

### Check 5 — Solalex-Custom-Entities (falls vorhanden)

Wenn Check 2 Custom-Entities mit `solalex` im Namen gefunden hat:

- Für jede gefundene `sensor.solalex_*`-Entity: `ha_call_read_tool`, prüfe dass State nicht `unavailable` / `unknown` ist
- **Pass:** alle Custom-Entities haben validen State
- **Fail:** mindestens eine Solalex-Entity ist `unavailable`
- **Skipped:** wenn keine gefunden — kein Fail, nur `skipped` mit `detail: "no custom entities exposed"`

### Check 6 — Crash-Indikatoren via System-Log (best-effort)

- Nutze `ha_search_tools` mit Query `log` oder `system_log` um ein System-Log-Lookup-Tool zu finden
- Wenn ein Tool existiert: lies die letzten 5 min an Errors mit Filter auf `solalex`
- **Pass:** keine ERROR-Lines mit `solalex`-Bezug
- **Soft-Fail:** Errors gefunden — listen, im Report anhängen, aber Run nicht abbrechen
- **Skipped:** wenn kein Tool dafür existiert — kein Problem

## 6. Output-Format

Schreibe als allerletzten Output diesen YAML-Block (alles davor sind Zwischen-Logs/Reasoning, das ist OK):

```yaml
smoketest_run:
  release_tag: "<arg vom Slash-Command, z.B. v0.1.1-beta.8>"
  started_at: "<iso8601 utc>"
  finished_at: "<iso8601 utc>"
  is_daytime: <true|false>
  overall: pass | fail | partial
  checks:
    - name: addon_running
      status: pass | fail | skipped
      detail: "<short>"
    - name: hardware_entities_present
      status: ...
      detail: "..."
    - name: live_values_plausible
      status: ...
      detail: "wr_setpoint=<W>, grid=<W>, sun_elev=<°>"
    - name: controller_active
      status: ...
      detail: "T0=<W>, T1=<W>, delta=<W>, grid_at_t0=<W>, grid_at_t1=<W>"
    - name: solalex_custom_entities
      status: ...
      detail: "..."
    - name: log_errors_recent
      status: ...
      detail: "..."
  notes:
    - "<freie Notizen, z.B. controller_idle_during_observation, weak_correlation, ...>"
```

**`overall`-Berechnung:**
- `pass` → alle Critical-Checks (1, 2, 3, 4) sind `pass` (Idle-Pass und Weak-Pass zählen als Pass)
- `fail` → einer der Critical-Checks ist `fail`
- `partial` → mindestens ein Non-Critical-Check (5, 6) ist `fail` und alle Critical sind `pass`

## 7. Was du **NICHT** tun darfst

- Keine `git`-Operationen, kein Code-Edit, kein Push.
- Keine HA-Add-on-Updates oder -Restarts.
- Keine HA-Schreibzugriffe (Entities, Automationen, Configs, Backups).
- Keine Slack/Discord/Email-Notifications.
- Keine LemonSqueezy/License-Operationen (haste eh keinen Zugriff drauf).
- Kein Speculation in `detail`-Feldern — nur was du gemessen hast.

## 8. Beobachtungen die proaktiv ins `notes`-Feld gehören

- Sollwert-Veränderungen die "groß" wirken (>50 % Sprung in einem Zyklus)
- Smart-Meter-Werte die zwischen T0 und T1 stark schwanken (>2× Standardabweichung)
- Custom-Entities mit ungewöhnlichen Namen oder Werten
- Hinweise dass Solalex möglicherweise im Wizard-Modus festhängt (z.B. wenn keine Custom-Entities da sind, obwohl welche erwartet wären)
