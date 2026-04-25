---
name: qa-smoketest
description: Run Solalex post-release smoketest against the real tester HA via ha-mcp. Use when the user says "qa smoketest", "/qa-smoketest", "test the beta", or wants to verify a freshly installed Solalex release on the connected Home Assistant instance.
---

# Solalex QA Smoketest

## Purpose

Beobachte eine **frisch auf Alex' Tester-HA installierte Solalex-Beta** über ha-mcp und reporte ob die Kernfunktionen sichtbar arbeiten. Der Test läuft *passiv* (nur Read-Operations gegen HA) — Solalex schreibt selbst, du beobachtest.

## When to Run

Alex hat eine neue Beta lokal installiert oder ein GitHub-Release `v*-beta.*` gemacht und will wissen, ob's tut. Trigger sind:

- Slash-Command: `/qa-smoketest <release-tag>` (z.B. `/qa-smoketest v0.1.1-beta.8`)
- Freitext: "starte qa smoketest", "test die beta", "smoketest das release"

Wenn kein Release-Tag mitgegeben wurde: **frag einmal kurz** ("Welche Beta-Version testen wir? z.B. `v0.1.1-beta.8`"), dann starte.

## Activation Steps

1. **Anleitung laden:** Lies [qa/agent-smoketest/AGENT.md](../../../qa/agent-smoketest/AGENT.md) komplett. Das ist deine Master-Spec für diesen Run.
2. **Release-Tag klären:** Aus Slash-Command-Args, sonst kurz fragen.
3. **Ankündigung an Alex:** Eine Zeile, was du gleich tust ("Smoketest gegen Tester-HA läuft, ~60s mit 30s-Beobachtungs-Pause für Check 4").
4. **Procedure abarbeiten:** Folge §5 in AGENT.md, Check 1 → Check 6, in dieser Reihenfolge, mit den dort beschriebenen Stop-Conditions.
5. **Tools:** Nur `mcp__ha-mcp__*`. Keine Bash, keine Edit/Write, keine externen MCP-Server. Bei Tool-Bedarf außerhalb ha-mcp: **abbrechen**, nicht improvisieren.
6. **Report:** YAML-Block exakt nach §6 in AGENT.md als allerletzten Output. Davor darf Reasoning/Zwischen-Logs stehen.

## Hard Rules

- **Read-Only gegen HA.** Keine Schreib-Operationen, keine Restarts, keine Config-Änderungen, keine Backups. Solalex regelt selbst — du schaust zu.
- **Failed-pessimistisch:** bei Unsicherheit `fail` oder `skipped` reporten, nicht raten.
- **Keine Code-Änderungen, keine Commits, keine PRs.** Du bist QA, nicht Dev.
- **Token-Budget ~80k:** wenn du mehr brauchst → abbrechen mit `overall: fail`, `notes: ["agent_overrun"]`.

## Output

Am Ende **genau ein** YAML-Block im Format aus AGENT.md §6. Alex liest den als Übersicht, kopiert ihn ggf. in eine Test-Notiz oder einen GitHub-Release-Kommentar.

Wenn `overall: fail` oder `partial`: zusätzlich ein bis drei Sätze auf Deutsch davor mit der wichtigsten Beobachtung — Alex soll auf einen Blick wissen, ob er einen Bug-Hunt starten muss.
