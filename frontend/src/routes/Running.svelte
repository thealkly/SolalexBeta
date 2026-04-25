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

  const polling = usePolling(client.getStateSnapshot, 1000);

  const gridMeter = $derived(devices.find((d) => d.role === 'grid_meter'));
  const wrLimit = $derived(devices.find((d) => d.role === 'wr_limit'));

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

  onMount(async () => {
    try {
      devices = await client.getDevices();
    } catch (err) {
      loadError = isApiError(err) ? err.detail : 'Verbindungsfehler beim Laden der Geräte.';
      return;
    }
    polling.start();
  });

  onDestroy(() => {
    polling.stop();
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
    </div>
    <h1>Live-Betrieb</h1>
  </header>

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

  .error-block {
    width: min(100%, 760px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 8%, var(--color-bg) 92%);
    padding: var(--space-3);
    color: var(--color-accent-warning);
  }
</style>
