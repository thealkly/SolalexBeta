<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import { usePolling } from '../lib/polling/usePolling.js';
  import LineChart from '../lib/components/charts/LineChart.svelte';
  import type { ChartSeries } from '../lib/components/charts/LineChart.svelte';
  import type { ControlMode, DeviceResponse, StateSnapshot } from '../lib/api/types.js';

  const WINDOW_MS = 5000;

  const MODE_LABEL: Record<ControlMode, string> = {
    drossel: 'Drossel',
    speicher: 'Speicher',
    multi: 'Multi',
    idle: 'Idle',
  };

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
      (d) =>
        (d.role === 'wr_limit' || d.role === 'wr_charge') &&
        d.commissioned_at === null,
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

  const recentCycles = $derived(snapshot?.recent_cycles.slice(0, 10) ?? []);
  const currentMode = $derived<ControlMode>(snapshot?.current_mode ?? 'idle');
  const testInProgress = $derived(snapshot?.test_in_progress ?? false);

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
  </header>

  {#if needsRefunctionalTest && !loadError && !testInProgress}
    <section
      class="refunctional-test-banner"
      data-testid="refunctional-test-banner"
    >
      <p>
        Funktionstest erforderlich für den neuen Wechselrichter — Solalex pausiert die
        Regelung, bis der Test bestätigt ist.
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
    <section class="running-card">
      <div class="chart-wrap">
        <LineChart series={chartSeries} windowMs={WINDOW_MS} now={nowTs} />
      </div>
      {#if chartSeries.length > 0}
        <ul class="chart-legend" aria-label="Diagramm-Legende">
          {#each chartSeries as series (series.label)}
            <li class="legend-item">
              <span class="legend-dot" style="background: {series.color};"></span>
              <span class="legend-label">{series.label}</span>
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
        <ul class="cycle-list" aria-label="Letzte Regelzyklen">
          {#each recentCycles as cycle (cycle.id)}
            <li class="cycle-row">
              <span class="cycle-ts">{formatRelative(cycle.ts)}</span>
              <span class="cycle-source" data-source={cycle.source}>
                {cycle.source}
              </span>
              <span class="cycle-target">{formatTarget(cycle.target_value_w)}</span>
              <span class="cycle-readback" data-status={cycle.readback_status ?? 'noop'}>
                {cycle.readback_status ?? 'noop'}
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
  .mode-chip[data-mode='multi'] {
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
    grid-template-columns: 90px 100px 80px 80px 64px;
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
    color: var(--color-text-secondary);
  }

  .cycle-target,
  .cycle-latency {
    color: var(--color-text);
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
    align-items: center;
    gap: 8px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
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
