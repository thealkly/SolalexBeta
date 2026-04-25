<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import { usePolling } from '../lib/polling/usePolling.js';
  import LineChart, { formatWatts } from '../lib/components/charts/LineChart.svelte';
  import type { ChartSeries } from '../lib/components/charts/LineChart.svelte';
  import type {
    ControlMode,
    DeviceResponse,
    EntitySnapshot,
    RecentCycle,
    StateSnapshot,
  } from '../lib/api/types.js';

  const WINDOW_MS = 5000;

  const MODE_LABEL: Record<ControlMode, string> = {
    drossel: 'Drossel',
    speicher: 'Speicher',
    multi: 'Multi',
    export: 'Einspeisung',
    idle: 'Idle',
  };

  // Story 5.1d — explanatory subtitle for the current mode. Describes what
  // the mode does, not how it feels (CLAUDE.md UX-DR30 — Charakter-Zeile
  // beschreibt Tun, nicht Zahl). ``idle`` covers boot + post-disconnect.
  const MODE_EXPLANATION: Record<ControlMode, string> = {
    drossel: 'Drossel — verhindert ungewollte Einspeisung durch WR-Limit-Anpassung',
    speicher: 'Speicher — Akku gleicht Einspeisung und Bezug aus',
    multi: 'Multi — Akku zuerst, WR-Limit als Fallback bei vollem Speicher',
    export: 'Einspeisung — gezielt Überschuss ins Netz, Akku ist voll',
    idle: 'Idle — wartet auf erstes Sensor-Event',
  };

  // Story 5.1d — German Klartext for the cycle Status-Spalte. Mapping is
  // driven by ``readback_status`` plus a ``reason``-prefix discriminator
  // for the noop / vetoed branches. Returned ``dataStatus`` feeds the
  // CSS attribute selectors in the style block. See AC 2 mapping table.
  type CycleStatusView = {
    label: string;
    dataStatus: string;
    tooltip: string;
  };

  function formatCycleStatus(cycle: RecentCycle): CycleStatusView {
    const reason = cycle.reason ?? '';
    const tooltip = reason || (cycle.readback_status ?? 'noop');
    switch (cycle.readback_status) {
      case 'passed':
        return { label: 'Übernommen', dataStatus: 'passed', tooltip };
      case 'failed':
        return { label: 'Fehlgeschlagen', dataStatus: 'failed', tooltip };
      case 'timeout':
        return { label: 'Timeout', dataStatus: 'timeout', tooltip };
      case 'vetoed':
        if (reason.startsWith('fail_safe:')) {
          return { label: 'Fail-Safe', dataStatus: 'vetoed', tooltip };
        }
        return { label: 'Abgelehnt', dataStatus: 'vetoed', tooltip };
      case 'noop':
      case null:
      default:
        if (reason.startsWith('mode_switch:')) {
          return { label: 'Mode-Wechsel', dataStatus: 'noop-mode-switch', tooltip };
        }
        if (reason.startsWith('hardware_edit:')) {
          return { label: 'Hardware geändert', dataStatus: 'noop-hardware-edit', tooltip };
        }
        if (reason.startsWith('noop: deadband')) {
          return { label: 'Im Toleranzbereich', dataStatus: 'noop-deadband', tooltip };
        }
        if (reason.startsWith('noop: kein_wr_limit_device')) {
          return { label: 'Kein Wechselrichter', dataStatus: 'noop-no-wr', tooltip };
        }
        if (reason.startsWith('noop: min_step_nicht_erreicht')) {
          return { label: 'Schritt zu klein', dataStatus: 'noop-min-step', tooltip };
        }
        if (reason.startsWith('noop: kein_soc_messwert')) {
          return { label: 'SoC fehlt', dataStatus: 'noop-no-soc', tooltip };
        }
        if (reason.startsWith('noop: nicht_grid_meter_event')) {
          return { label: 'Beobachtung', dataStatus: 'noop-other', tooltip };
        }
        if (reason.startsWith('noop: max_soc_erreicht')) {
          return { label: 'Max-SoC erreicht', dataStatus: 'noop-max-soc', tooltip };
        }
        if (reason.startsWith('noop: min_soc_erreicht')) {
          return { label: 'Min-SoC erreicht', dataStatus: 'noop-min-soc', tooltip };
        }
        if (reason.startsWith('noop: nacht_gate_aktiv')) {
          return { label: 'Nacht-Modus aktiv', dataStatus: 'noop-night-gate', tooltip };
        }
        if (reason.startsWith('noop: wr_limit_state_cache_miss')) {
          return { label: 'WR-Status fehlt', dataStatus: 'noop-no-wr-state', tooltip };
        }
        if (reason.startsWith('noop: sensor_nicht_numerisch')) {
          return { label: 'Sensor-Wert ungültig', dataStatus: 'noop-sensor-bad', tooltip };
        }
        if (reason.startsWith('noop: kein_akku_pool')) {
          return { label: 'Kein Akku', dataStatus: 'noop-no-pool', tooltip };
        }
        return { label: 'Beobachtung', dataStatus: 'noop-other', tooltip };
    }
  }

  let devices = $state<DeviceResponse[]>([]);
  let loadError = $state<string | null>(null);
  let snapshot = $state<StateSnapshot | null>(null);
  let gridBuffer = $state<{ t: number; v: number }[]>([]);
  let readbackBuffer = $state<{ t: number; v: number }[]>([]);
  let targetBuffer = $state<{ t: number; v: number }[]>([]);
  let nowTs = $state(Date.now());
  let lastUpdateTs = $state<number | null>(null);
  const STALE_AFTER_MS = 5000;
  const isStale = $derived(lastUpdateTs !== null && nowTs - lastUpdateTs > STALE_AFTER_MS);

  const polling = usePolling(client.getStateSnapshot, 1000);

  const gridMeter = $derived(devices.find((d) => d.role === 'grid_meter'));
  const wrLimit = $derived(devices.find((d) => d.role === 'wr_limit'));
  // Story 2.6 — surface a hint banner when a control device exists but
  // hasn't been (re-)commissioned yet. Triggered after a hardware swap
  // via /hardware-edit so the user sees they need to re-run the
  // functional test before regulation resumes.
  const needsRefunctionalTest = $derived(
    devices.some(
      (d) => (d.role === 'wr_limit' || d.role === 'wr_charge') && d.commissioned_at === null,
    ),
  );

  const chartSeries: ChartSeries[] = $derived.by(() => {
    const series: ChartSeries[] = [];
    if (gridMeter) {
      series.push({
        label: 'Netz-Leistung',
        color: 'var(--color-accent-warning)',
        data: gridBuffer,
      });
    }
    if (wrLimit) {
      series.push({
        label: 'Target-Limit',
        color: 'var(--color-accent-primary)',
        data: targetBuffer,
      });
      series.push({
        label: 'Readback',
        color: 'var(--color-text-secondary)',
        data: readbackBuffer,
      });
    }
    return series;
  });

  const activeRateLimit = $derived.by(() => {
    const snap = snapshot;
    if (!snap) return null;
    // Math.min — the UI labels this as the *next* write (soonest unlock).
    // Math.max would surface the device furthest from being writable, which
    // contradicts the hint and makes short-cooldown devices invisible.
    const active = snap.rate_limit_status
      .map((r) => r.seconds_until_next_write)
      .filter((s): s is number => typeof s === 'number' && s > 0);
    if (active.length === 0) return null;
    return Math.min(...active);
  });

  // Story 5.1d — surface up to 50 cycles. Existing CSS max-height + scroll
  // on .cycle-list keeps the visible window manageable while making the
  // longer history reachable for diagnosis.
  const recentCycles = $derived(snapshot?.recent_cycles.slice(0, 50) ?? []);
  const currentMode = $derived<ControlMode>(snapshot?.current_mode ?? 'idle');
  const testInProgress = $derived(snapshot?.test_in_progress ?? false);

  // Story 5.1d — Status-Tile inputs derived from the snapshot.
  function findEntityByRole(role: string): EntitySnapshot | undefined {
    const snap = snapshot;
    if (!snap) return undefined;
    return snap.entities.find((e) => e.role === role);
  }

  const gridEntity = $derived(findEntityByRole('grid_meter'));
  const wrLimitEntity = $derived(findEntityByRole('wr_limit'));
  const socEntity = $derived(findEntityByRole('battery_soc'));
  const haWsConnected = $derived<boolean>(snapshot?.ha_ws_connected ?? true);
  const haWsDisconnectedSince = $derived<string | null>(snapshot?.ha_ws_disconnected_since ?? null);
  const haWsDisconnectedSeconds = $derived.by(() => {
    if (haWsConnected) return null;
    if (haWsDisconnectedSince === null) return null;
    const since = new Date(haWsDisconnectedSince).getTime();
    if (!Number.isFinite(since)) return null;
    return Math.max(0, Math.floor((nowTs - since) / 1000));
  });

  // Battery-min/max from the device.config_json (Settings persistence).
  const batteryConfig = $derived.by(() => {
    const dev = devices.find((d) => d.role === 'wr_charge');
    if (!dev) return null;
    try {
      const cfg = JSON.parse(dev.config_json) as Record<string, unknown>;
      const minSoc = typeof cfg.min_soc === 'number' ? (cfg.min_soc as number) : null;
      const maxSoc = typeof cfg.max_soc === 'number' ? (cfg.max_soc as number) : null;
      return { minSoc, maxSoc };
    } catch {
      return null;
    }
  });

  $effect(() => {
    return polling.data.subscribe((snap) => {
      if (!snap) return;
      snapshot = snap;
      const ts = Date.now();
      nowTs = ts;
      lastUpdateTs = ts;
      const cutoff = ts - WINDOW_MS - 500;
      if (gridMeter) {
        const entry = snap.entities.find((e) => e.entity_id === gridMeter.entity_id);
        if (entry && typeof entry.state === 'number' && Number.isFinite(entry.state)) {
          gridBuffer = [...gridBuffer, { t: ts, v: entry.state }].filter((p) => p.t >= cutoff);
        }
      }
      if (wrLimit) {
        const entry = snap.entities.find((e) => e.entity_id === wrLimit.entity_id);
        if (entry && typeof entry.state === 'number' && Number.isFinite(entry.state)) {
          readbackBuffer = [...readbackBuffer, { t: ts, v: entry.state }].filter(
            (p) => p.t >= cutoff,
          );
        }
        // Buffer the latest dispatch target at client-receive time so the
        // Target-Limit series stays aligned with grid/readback (both use
        // Date.now()), not the original cycle timestamp. Without this the
        // series is invisible whenever the newest cycle is older than
        // WINDOW_MS (common with WR-adapter 60 s rate-limits) and suffers
        // from NTP skew between browser and HA host.
        const latestTarget = snap.recent_cycles.find(
          (c) => c.device_id === wrLimit.id && c.target_value_w !== null,
        )?.target_value_w;
        if (typeof latestTarget === 'number' && Number.isFinite(latestTarget)) {
          targetBuffer = [...targetBuffer, { t: ts, v: latestTarget }].filter((p) => p.t >= cutoff);
        }
      }
    });
  });

  // Wall-clock ticker for nowTs. Required so the update-indicator can flip to
  // stale even when polling hangs (no subscribe callback fires in that case).
  // Polling-tick alone would only advance nowTs on successful snapshots — see
  // AC 7 (stale after >5 s of silence) and Running.test.ts stale-dot case.
  let clockTimerId: ReturnType<typeof setInterval> | null = null;

  onMount(async () => {
    try {
      devices = await client.getDevices();
    } catch (err) {
      loadError = isApiError(err) ? err.detail : 'Verbindungsfehler beim Laden der Geräte.';
      return;
    }
    polling.start();
    clockTimerId = setInterval(() => {
      nowTs = Date.now();
    }, 1000);
  });

  onDestroy(() => {
    polling.stop();
    if (clockTimerId !== null) {
      clearInterval(clockTimerId);
      clockTimerId = null;
    }
  });

  function formatRelative(iso: string): string {
    const then = new Date(iso).getTime();
    if (!Number.isFinite(then)) return '—';
    const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (secs < 60) return `vor ${secs} s`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `vor ${mins} min`;
    const hours = Math.floor(mins / 60);
    return `vor ${hours} h`;
  }

  // Relative-time stamp for the live update heartbeat. Fed by ageMs (number),
  // not an ISO string, so the polling tick can drive re-renders cheaply via
  // nowTs without building Date instances every frame.
  function formatStaleRelative(ageMs: number): string {
    const ms = Math.max(0, ageMs);
    if (ms < 2000) return 'gerade eben';
    const secs = Math.floor(ms / 1000);
    if (secs < 60) return `vor ${secs} s`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `vor ${mins} min`;
    const hours = Math.floor(mins / 60);
    return `vor ${hours} h`;
  }

  function formatTarget(w: number | null): string {
    return w === null ? '—' : `${w} W`;
  }

  function formatLatency(ms: number | null): string {
    return ms === null ? '—' : `${ms} ms`;
  }

  function formatSensor(w: number | null): string {
    if (w === null) return '—';
    return `${Math.round(w)} W`;
  }

  // Story 5.1d — Netz-Leistung tile sub-label per sign of effective_value_w.
  // ``effective_value_w`` already incorporates the Story 2.5 ``invert_sign``
  // override so the sub-label stays aligned with the controller's view.
  function formatGridSubLabel(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return '—';
    if (Math.abs(value) < 30) return 'nahezu 0 W';
    if (value > 0) return 'Bezug aus dem Netz';
    return 'Einspeisung ins Netz';
  }

  function formatGridValue(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return '—';
    const rounded = Math.round(value);
    const sign = rounded > 0 ? '+' : '';
    return `${sign}${rounded} W`;
  }

  function formatSocValue(state: number | string | null): string {
    if (typeof state !== 'number' || !Number.isFinite(state)) return '—';
    return `${Math.round(state)} %`;
  }

  function formatWrLimitValue(state: number | string | null): string {
    if (typeof state !== 'number' || !Number.isFinite(state)) return '—';
    return `${Math.round(state)} W`;
  }
</script>

<main class="running-page">
  <header class="running-header">
    <div class="eyebrow-row">
      <p class="eyebrow">Solalex</p>
      <span
        class="mode-chip"
        data-mode={currentMode}
        aria-label={`Aktueller Modus: ${MODE_LABEL[currentMode]}`}
      >
        {MODE_LABEL[currentMode]}
      </span>
      {#if lastUpdateTs !== null && !testInProgress}
        <span class="update-indicator" data-stale={isStale} aria-live="polite">
          <span class="update-dot"></span>
          <span class="update-text">Aktualisiert: {formatStaleRelative(nowTs - lastUpdateTs)}</span>
        </span>
      {/if}
    </div>
    <h1>Live-Betrieb</h1>
    <p class="mode-explanation" data-testid="mode-explanation">
      {MODE_EXPLANATION[currentMode]}
    </p>
  </header>

  {#if needsRefunctionalTest && !loadError && !testInProgress}
    <section class="refunctional-test-banner" data-testid="refunctional-test-banner">
      <p>
        Funktionstest erforderlich für den neuen Wechselrichter — Solalex pausiert die Regelung, bis
        der Test bestätigt ist.
      </p>
      <a class="banner-link" href="#/functional-test">Funktionstest starten</a>
    </section>
  {/if}

  {#if loadError}
    <section class="error-block">
      <p>{loadError}</p>
    </section>
  {:else if testInProgress}
    <section class="running-card">
      <p class="test-lock">Funktionstest läuft — Regelung pausiert.</p>
      <p class="test-link-row">
        <a href="#/functional-test">Zum Funktionstest</a>
      </p>
    </section>
  {:else}
    <section class="status-tiles" data-testid="status-tiles">
      {#if gridEntity}
        <div class="status-tile" data-tile="grid">
          <span class="status-tile-label">Netz-Leistung</span>
          <span class="status-tile-value">{formatGridValue(gridEntity.effective_value_w)}</span>
          <span class="status-tile-sub">{formatGridSubLabel(gridEntity.effective_value_w)}</span>
        </div>
      {/if}
      {#if wrLimitEntity}
        <div class="status-tile" data-tile="wr-limit">
          <span class="status-tile-label">Wechselrichter-Limit</span>
          <span class="status-tile-value">{formatWrLimitValue(wrLimitEntity.state)}</span>
          <span class="status-tile-sub">Aktuelles Limit</span>
        </div>
      {/if}
      {#if socEntity}
        <div class="status-tile" data-tile="soc">
          <span class="status-tile-label">Akku-SoC</span>
          <span class="status-tile-value">{formatSocValue(socEntity.state)}</span>
          {#if batteryConfig && batteryConfig.minSoc !== null && batteryConfig.maxSoc !== null}
            <span class="status-tile-sub"
              >Min {batteryConfig.minSoc} % / Max {batteryConfig.maxSoc} %</span
            >
          {:else}
            <span class="status-tile-sub">Aktueller Ladestand</span>
          {/if}
        </div>
      {/if}
      <div class="status-tile" data-tile="connection" data-connected={haWsConnected}>
        <span class="status-tile-label">Verbindung</span>
        <span class="status-tile-value">{haWsConnected ? 'Verbunden' : 'Getrennt'}</span>
        <span class="status-tile-sub">
          {#if haWsConnected}
            Home Assistant
          {:else if haWsDisconnectedSeconds !== null}
            vor {haWsDisconnectedSeconds} s
          {:else}
            warte auf Verbindung
          {/if}
        </span>
      </div>
    </section>

    <section class="running-card">
      <div class="chart-wrap">
        <LineChart series={chartSeries} windowMs={WINDOW_MS} now={nowTs} />
      </div>
      {#if chartSeries.length > 0}
        <ul class="chart-legend" aria-label="Diagramm-Legende">
          {#each chartSeries as series (series.label)}
            {@const last = series.data[series.data.length - 1]}
            <li class="legend-item">
              <span class="legend-dot" style="background: {series.color};"></span>
              <span class="legend-label">{series.label}</span>
              <span class="legend-value">{last ? formatWatts(last.v) : '—'}</span>
            </li>
          {/each}
        </ul>
      {/if}
      {#if recentCycles.length === 0}
        <p class="chart-hint">Regler wartet auf erstes Sensor-Event.</p>
      {/if}
      {#if activeRateLimit !== null}
        <p class="rate-hint">Nächster Write in {activeRateLimit} s</p>
      {/if}
    </section>

    <section class="running-card cycles-card">
      <h2>Letzte Zyklen</h2>
      {#if recentCycles.length === 0}
        <p class="cycles-empty">Noch keine Zyklen erfasst.</p>
      {:else}
        <div class="cycle-header" aria-hidden="true" data-testid="cycle-header">
          <span class="cycle-header-cell">vor</span>
          <span class="cycle-header-cell">Quelle</span>
          <span class="cycle-header-cell">Ziel</span>
          <span class="cycle-header-cell">Status</span>
          <span class="cycle-header-cell">Latenz</span>
        </div>
        <ul class="cycle-list" aria-label="Letzte Regelzyklen">
          {#each recentCycles as cycle (cycle.id)}
            {@const status = formatCycleStatus(cycle)}
            <li class="cycle-row">
              <span class="cycle-ts">{formatRelative(cycle.ts)}</span>
              <span class="cycle-source" data-source={cycle.source}>
                {cycle.source}
              </span>
              <span class="cycle-target">
                {#if cycle.target_value_w === null && cycle.sensor_value_w !== null}
                  — <span class="cycle-target-sub"
                    >(gemessen {formatSensor(cycle.sensor_value_w)})</span
                  >
                {:else}
                  {formatTarget(cycle.target_value_w)}
                {/if}
              </span>
              <span class="cycle-readback" data-status={status.dataStatus} title={status.tooltip}>
                {status.label}
              </span>
              <span class="cycle-latency">{formatLatency(cycle.latency_ms)}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  {/if}
</main>

<style>
  .running-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background:
      radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%), var(--color-bg);
    color: var(--color-text);
  }

  .running-header {
    width: min(100%, 760px);
    margin: 0 auto;
  }

  .eyebrow-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .running-header h1 {
    margin: var(--space-1) 0 0 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .mode-explanation {
    margin: 6px 0 0 0;
    font-size: 0.86rem;
    color: var(--color-text-secondary);
    max-width: 60ch;
  }

  .mode-chip {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    background: color-mix(in srgb, var(--color-text) 10%, transparent);
    color: var(--color-text-secondary);
  }

  .mode-chip[data-mode='drossel'],
  .mode-chip[data-mode='speicher'],
  .mode-chip[data-mode='multi'],
  .mode-chip[data-mode='export'] {
    background: color-mix(in srgb, var(--color-accent-primary) 18%, var(--color-surface) 82%);
    color: var(--color-accent-primary);
  }

  .running-card {
    width: min(100%, 760px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    padding: var(--space-3);
  }

  .running-card h2 {
    margin: 0 0 var(--space-2) 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* Status-Tiles row (Story 5.1d) — sits between header and chart-card. */
  .status-tiles {
    width: min(100%, 760px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .status-tile {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: var(--space-2);
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    min-width: 0;
  }

  .status-tile-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .status-tile-value {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }

  .status-tile-sub {
    font-size: 0.78rem;
    color: var(--color-text-secondary);
  }

  .status-tile[data-tile='connection'][data-connected='true'] .status-tile-value {
    color: var(--color-accent-primary);
  }

  .status-tile[data-tile='connection'][data-connected='false'] .status-tile-value {
    color: var(--color-accent-warning);
  }

  @media (max-width: 560px) {
    .status-tiles {
      grid-template-columns: 1fr;
    }
  }

  .chart-wrap {
    margin: 0;
  }

  .chart-hint,
  .rate-hint,
  .test-lock,
  .test-link-row,
  .cycles-empty {
    margin: var(--space-2) 0 0 0;
    font-size: 0.88rem;
    color: var(--color-text-secondary);
  }

  .rate-hint {
    color: var(--color-text);
    font-weight: 500;
  }

  .test-lock {
    color: var(--color-text);
    font-weight: 600;
    margin-top: 0;
  }

  .test-link-row a {
    color: var(--color-accent-primary);
    text-decoration: none;
    font-weight: 500;
  }

  .test-link-row a:hover {
    text-decoration: underline;
  }

  /* Cycle-Liste — Header above + extended status mapping (Story 5.1d). */
  .cycle-header {
    display: grid;
    grid-template-columns: 90px 100px 1fr 110px 64px;
    gap: var(--space-2);
    padding: 4px var(--space-1);
    margin-bottom: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .cycle-list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 320px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .cycle-row {
    display: grid;
    grid-template-columns: 90px 100px 1fr 110px 64px;
    gap: var(--space-2);
    align-items: center;
    padding: 6px var(--space-1);
    border-radius: 8px;
    font-size: 0.82rem;
    font-variant-numeric: tabular-nums;
  }

  .cycle-row:nth-child(even) {
    background: color-mix(in srgb, var(--color-text) 3%, transparent);
  }

  .cycle-ts {
    color: var(--color-text-secondary);
  }

  .cycle-source {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--color-text) 8%, transparent);
    color: var(--color-text-secondary);
    font-size: 0.72rem;
    font-weight: 600;
  }

  .cycle-source[data-source='solalex'] {
    background: color-mix(in srgb, var(--color-accent-primary) 14%, var(--color-surface) 86%);
    color: var(--color-accent-primary);
  }

  /* AC 4: distinct neutral grey for manual vs blue-tinged slate for
     ha_automation so users can tell them apart at a glance.
     --color-neutral-muted = gray-500 neutral; --color-brand-ink = slate-900
     (cool blue-gray). No new tokens added — Amendment 2026-04-22 keeps
     app.css as the single-source. */
  .cycle-source[data-source='manual'] {
    background: color-mix(in srgb, var(--color-neutral-muted) 18%, var(--color-surface) 82%);
    color: var(--color-neutral-muted);
  }

  .cycle-source[data-source='ha_automation'] {
    background: color-mix(in srgb, var(--color-brand-ink) 14%, var(--color-surface) 86%);
    color: var(--color-brand-ink);
  }

  .cycle-readback {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--color-text) 8%, transparent);
    color: var(--color-text-secondary);
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .cycle-readback[data-status='passed'] {
    background: color-mix(in srgb, var(--color-accent-primary) 14%, var(--color-surface) 86%);
    color: var(--color-accent-primary);
  }

  .cycle-readback[data-status='failed'],
  .cycle-readback[data-status='timeout'] {
    background: color-mix(in srgb, var(--color-accent-warning) 14%, var(--color-surface) 86%);
    color: var(--color-accent-warning);
  }

  .cycle-readback[data-status='vetoed'] {
    background: color-mix(in srgb, var(--color-accent-warning) 10%, var(--color-surface) 90%);
    color: var(--color-accent-warning);
  }

  .cycle-readback[data-status='noop-mode-switch'],
  .cycle-readback[data-status='noop-hardware-edit'] {
    background: color-mix(in srgb, var(--color-accent-primary) 10%, var(--color-surface) 90%);
    color: var(--color-accent-primary);
  }

  .cycle-readback[data-status='noop-no-wr'],
  .cycle-readback[data-status='noop-no-wr-state'],
  .cycle-readback[data-status='noop-no-pool'],
  .cycle-readback[data-status='noop-no-soc'],
  .cycle-readback[data-status='noop-sensor-bad'] {
    background: color-mix(in srgb, var(--color-accent-warning) 10%, var(--color-surface) 90%);
    color: var(--color-accent-warning);
  }

  .cycle-readback[data-status='noop-deadband'],
  .cycle-readback[data-status='noop-min-step'],
  .cycle-readback[data-status='noop-max-soc'],
  .cycle-readback[data-status='noop-min-soc'],
  .cycle-readback[data-status='noop-night-gate'],
  .cycle-readback[data-status='noop-other'] {
    background: color-mix(in srgb, var(--color-neutral-muted) 14%, var(--color-surface) 86%);
    color: var(--color-text-secondary);
  }

  .cycle-target,
  .cycle-latency {
    color: var(--color-text);
  }

  .cycle-target-sub {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin-left: 4px;
  }

  .chart-legend {
    list-style: none;
    margin: var(--space-2) 0 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    font-size: 0.82rem;
    color: var(--color-text-secondary);
  }

  .legend-item {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    align-self: center;
  }

  .legend-value {
    color: var(--color-text);
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    font-size: 0.85rem;
  }

  .update-indicator {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-left: var(--space-2);
    font-size: 0.78rem;
    color: var(--color-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .update-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--color-accent-primary);
    animation: update-pulse 1.4s ease-in-out infinite;
  }

  .update-indicator[data-stale='true'] .update-dot {
    background: var(--color-text-secondary);
    animation-play-state: paused;
  }

  @keyframes update-pulse {
    0%,
    100% {
      opacity: 0.4;
    }
    50% {
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .update-dot {
      animation: none;
    }
  }

  .error-block {
    width: min(100%, 760px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 8%, var(--color-bg) 92%);
    padding: var(--space-3);
    color: var(--color-accent-warning);
  }
  .refunctional-test-banner {
    width: 100%;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 50%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 12%, var(--color-bg) 88%);
    padding: var(--space-2) var(--space-3);
    color: var(--color-text);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .refunctional-test-banner p {
    margin: 0;
    font-size: 0.92rem;
  }

  .banner-link {
    color: var(--color-accent-warning);
    font-weight: 600;
    text-decoration: underline;
  }
</style>
