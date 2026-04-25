<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import { usePolling } from '../lib/polling/usePolling.js';
  import LineChart from '../lib/components/charts/LineChart.svelte';
  import type { ChartSeries } from '../lib/components/charts/LineChart.svelte';
  import type { DeviceResponse, FunctionalTestResponse } from '../lib/api/types.js';

  const WINDOW_MS = 5000;

  const ROLE_LABELS: Record<string, string> = {
    wr_limit: 'Wechselrichter-Limit',
    wr_charge: 'Ladeleistung',
    battery_soc: 'Akku-SoC',
    grid_meter: 'Netz-Leistung',
  };

  const ROLE_COLORS: Record<string, string> = {
    wr_limit: 'var(--color-accent-primary)',
    wr_charge: 'var(--color-accent-primary)',
    battery_soc: 'var(--color-text-secondary)',
    grid_meter: 'var(--color-accent-warning)',
  };

  type TestPhase = 'idle' | 'running' | 'passed' | 'failed' | 'timeout';

  let devices = $state<DeviceResponse[]>([]);
  let loadError = $state<string | null>(null);
  let testPhase = $state<TestPhase>('idle');
  let testResult = $state<FunctionalTestResponse | null>(null);
  let testError = $state<string | null>(null);
  let chartPoints = $state<Record<string, { t: number; v: number }[]>>({});
  let nowTs = $state(Date.now());

  const polling = usePolling(client.getStateSnapshot, 1000);

  let chartSeries: ChartSeries[] = $derived(
    devices
      .filter((d) => d.role in ROLE_COLORS)
      .map((d) => ({
        label: ROLE_LABELS[d.role] ?? d.role,
        color: ROLE_COLORS[d.role] ?? 'var(--color-text)',
        data: chartPoints[d.entity_id] ?? [],
      })),
  );

  $effect(() => {
    return polling.data.subscribe((snapshot) => {
      if (!snapshot) return;
      const ts = Date.now();
      nowTs = ts;
      const cutoff = ts - WINDOW_MS - 500;
      const next: Record<string, { t: number; v: number }[]> = { ...chartPoints };
      for (const entity of snapshot.entities) {
        // Guard against HA sentinels ("unavailable", "unknown") which the
        // backend serialises as strings — pushing those into the chart
        // would poison yRange with NaN and blank the SVG path.
        if (typeof entity.state !== 'number' || !Number.isFinite(entity.state)) continue;
        const prev = next[entity.entity_id] ?? [];
        next[entity.entity_id] = [...prev, { t: ts, v: entity.state }].filter((p) => p.t >= cutoff);
      }
      chartPoints = next;
    });
  });

  onMount(async () => {
    try {
      devices = await client.getDevices();
    } catch (err) {
      loadError = isApiError(err) ? err.detail : 'Verbindungsfehler beim Laden der Geräte.';
    }
  });

  onDestroy(() => {
    polling.stop();
  });

  async function handleStartTest(): Promise<void> {
    testPhase = 'running';
    testResult = null;
    testError = null;
    chartPoints = {};
    polling.start();

    try {
      const result = await client.runFunctionalTest();
      testResult = result;
      testPhase = result.status as TestPhase;
    } catch (err) {
      testPhase = 'failed';
      testError = isApiError(err)
        ? err.detail
        : 'Funktionstest fehlgeschlagen. Prüfe die HA-Verbindung.';
    } finally {
      polling.stop();
    }
  }

  function formatRole(role: string): string {
    return ROLE_LABELS[role] ?? role;
  }

  function hardwareLabel(devices: DeviceResponse[]): string {
    if (devices.some((d) => d.adapter_key === 'generic')) return 'Wechselrichter';
    if (devices.some((d) => d.adapter_key === 'marstek_venus')) return 'Marstek Venus';
    return 'Unbekannte Hardware';
  }
</script>

<main class="ft-page">
  <header class="ft-header">
    <p class="eyebrow">Solalex Setup</p>
    <h1>Funktionstest</h1>
  </header>

  {#if loadError}
    <div class="error-block">
      <p>{loadError}</p>
    </div>
  {:else if devices.length > 0}
    <section class="ft-card">
      <h2>Zielhardware</h2>
      <p class="hardware-type">{hardwareLabel(devices)}</p>
      <ul class="device-list">
        {#each devices as d (d.id)}
          <li>
            <span class="role-tag">{formatRole(d.role)}</span>
            <code class="entity-id">{d.entity_id}</code>
          </li>
        {/each}
      </ul>
    </section>

    {#if testPhase === 'running'}
      <section class="ft-card">
        <div class="running-indicator">
          <span>Test läuft…</span>
        </div>
        <div class="chart-wrap">
          <LineChart series={chartSeries} windowMs={WINDOW_MS} now={nowTs} />
        </div>
      </section>
    {:else if testPhase === 'passed'}
      <section class="ft-card result-card result-passed">
        <div class="result-tick tick-passed" aria-label="Bestanden">✓</div>
        <p class="result-text">
          Readback erfolgreich — {testResult?.actual_value_w ?? '—'} W (Soll: {testResult?.test_value_w ??
            '—'} W, Toleranz ±{testResult?.tolerance_w?.toFixed(0) ?? '—'} W)
        </p>
        {#if testResult?.latency_ms !== null && testResult?.latency_ms !== undefined}
          <p class="result-sub">Latenz: {testResult.latency_ms} ms</p>
        {/if}
        <button
          class="continue-button"
          onclick={() => {
            window.location.hash = '#/activate';
          }}>ja ich akzeptiere das</button
        >
      </section>
    {:else if testPhase === 'failed' || testPhase === 'timeout'}
      <section class="ft-card result-card result-failed">
        <div class="result-tick tick-failed" aria-label="Fehlgeschlagen">✗</div>
        <p class="result-text">
          {testPhase === 'timeout'
            ? 'Timeout — kein Readback innerhalb von 15 s erhalten.'
            : 'Readback-Mismatch — der gemessene Wert liegt außerhalb der Toleranz.'}
        </p>
        {#if testError}
          <p class="error-line">{testError}</p>
        {:else if testResult?.reason}
          <p class="error-line">{testResult.reason}</p>
        {/if}
        <button class="retry-button" onclick={handleStartTest}>Erneut testen</button>
      </section>
    {:else}
      <div class="start-row">
        <button class="start-button" onclick={handleStartTest}>Funktionstest starten</button>
      </div>
    {/if}
  {:else}
    <div class="ft-card">
      <p class="hint">
        Keine Geräte konfiguriert. Bitte zuerst die Hardware-Konfiguration abschließen.
      </p>
      <a href="#/config" class="back-link" style="margin-top: 12px;">← Zur Konfiguration</a>
    </div>
  {/if}
</main>

<style>
  .ft-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background:
      radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%), var(--color-bg);
    color: var(--color-text);
  }

  .ft-header {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .ft-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .ft-card {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    padding: var(--space-3);
  }

  .ft-card h2 {
    margin: 0 0 var(--space-1) 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .hardware-type {
    font-weight: 600;
    margin: 0 0 var(--space-2) 0;
  }

  .device-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .device-list li {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.88rem;
  }

  .role-tag {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 8px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--color-accent-primary) 14%, var(--color-surface) 86%);
    color: var(--color-accent-primary);
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .entity-id {
    font-family: monospace;
    font-size: 0.82rem;
    color: var(--color-text-secondary);
  }

  .running-indicator {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--space-2);
  }

  .chart-wrap {
    margin-top: var(--space-1);
  }

  .result-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
  }

  .result-tick {
    font-size: 2.5rem;
    line-height: 1;
    font-weight: 700;
    animation: pop 400ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  .tick-passed {
    color: var(--color-accent-primary);
  }

  .tick-failed {
    color: var(--color-accent-warning);
  }

  @keyframes pop {
    from {
      opacity: 0;
      transform: scale(0.4);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .result-text {
    margin: 0;
    font-size: 0.92rem;
  }

  .result-sub {
    margin: 0;
    font-size: 0.82rem;
    color: var(--color-text-secondary);
  }

  .error-block {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 8%, var(--color-bg) 92%);
    padding: var(--space-3);
    color: var(--color-accent-warning);
  }

  .error-line {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-accent-warning);
  }

  .start-row {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .start-button,
  .continue-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 48px;
    border-radius: 999px;
    padding: 0 32px;
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-accent-primary) 92%, white 8%),
      color-mix(in srgb, var(--color-accent-primary) 76%, var(--color-brand-ink) 24%)
    );
    color: var(--color-button-text);
    font-family: var(--font-sans);
    font-weight: 700;
    font-size: 1rem;
    border: none;
    cursor: pointer;
    box-shadow: 0 0 24px color-mix(in srgb, var(--color-accent-primary) 40%, transparent);
    transition:
      transform 120ms ease,
      box-shadow 120ms ease;
  }

  .start-button:hover,
  .continue-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 32px color-mix(in srgb, var(--color-accent-primary) 56%, transparent);
  }

  .retry-button {
    display: inline-flex;
    align-items: center;
    height: 40px;
    padding: 0 20px;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 50%, transparent);
    background: transparent;
    color: var(--color-accent-warning);
    font-family: var(--font-sans);
    font-weight: 500;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 120ms ease;
  }

  .retry-button:hover {
    background: color-mix(in srgb, var(--color-accent-warning) 10%, transparent);
  }

  .hint {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-text-secondary);
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 16px;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--color-accent-primary) 40%, transparent);
    color: var(--color-accent-primary);
    text-decoration: none;
    font-size: 0.88rem;
    font-weight: 500;
  }
</style>
