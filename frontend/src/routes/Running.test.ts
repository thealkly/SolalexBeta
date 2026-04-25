// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import Running from './Running.svelte';
import type { DeviceResponse, RecentCycle, StateSnapshot } from '../lib/api/types.js';

// Mock the fetch-based client helpers so the component exercises pure render
// logic against a controlled StateSnapshot stream — no backend needed.
const getDevicesMock = vi.fn<() => Promise<DeviceResponse[]>>();
const getStateSnapshotMock = vi.fn<() => Promise<StateSnapshot>>();

vi.mock('../lib/api/client.js', () => ({
  getDevices: () => getDevicesMock(),
  getStateSnapshot: () => getStateSnapshotMock(),
  runFunctionalTest: vi.fn(),
  commission: vi.fn(),
  saveDevices: vi.fn(),
  getEntities: vi.fn(),
}));

function device(overrides: Partial<DeviceResponse>): DeviceResponse {
  return {
    id: 1,
    type: 'generic',
    role: 'wr_limit',
    entity_id: 'number.opendtu_limit_nonpersistent_absolute',
    adapter_key: 'generic',
    config_json: '{}',
    last_write_at: null,
    commissioned_at: '2026-04-24T12:00:00Z',
    created_at: '2026-04-24T12:00:00Z',
    updated_at: '2026-04-24T12:00:00Z',
    ...overrides,
  };
}

let _cycleIdCounter = 0;
function cycle(overrides: Partial<RecentCycle> = {}): RecentCycle {
  _cycleIdCounter += 1;
  return {
    id: _cycleIdCounter,
    ts: '2026-04-24T12:00:00Z',
    device_id: 1,
    mode: 'drossel',
    source: 'solalex',
    sensor_value_w: null,
    target_value_w: 100,
    readback_status: 'passed',
    latency_ms: 50,
    ...overrides,
  };
}

function snapshot(overrides: Partial<StateSnapshot> = {}): StateSnapshot {
  return {
    entities: [],
    test_in_progress: false,
    last_command_at: null,
    current_mode: 'idle',
    recent_cycles: [],
    rate_limit_status: [],
    ...overrides,
  };
}

async function flushPolling(): Promise<void> {
  // Two microtask ticks — one for the devices promise, one for the polling
  // subscribe flush that drives the derived state.
  await Promise.resolve();
  await Promise.resolve();
  await tick();
  await tick();
}

describe('Running — Live-Betriebs-View', () => {
  beforeEach(() => {
    getDevicesMock.mockReset();
    getStateSnapshotMock.mockReset();
    _cycleIdCounter = 0;
  });

  afterEach(() => {
    cleanup();
  });

  it('shows the idle chip and an empty-cycles hint on a fresh snapshot', async () => {
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(snapshot());

    render(Running);
    await flushPolling();

    expect(screen.getByText('Idle')).toBeTruthy();
    expect(screen.getByText(/Noch keine Zyklen erfasst/)).toBeTruthy();
  });

  it('renders the mode chip, cycles list, and rate-limit hint when data arrives', async () => {
    getDevicesMock.mockResolvedValue([
      device({ id: 1, role: 'wr_limit' }),
      device({ id: 2, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
    ]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({
        current_mode: 'drossel',
        recent_cycles: [
          cycle({ target_value_w: 310, latency_ms: 42 }),
          cycle({
            ts: '2026-04-24T11:59:00Z',
            target_value_w: 300,
            readback_status: 'timeout',
            latency_ms: null,
          }),
        ],
        rate_limit_status: [
          { device_id: 1, seconds_until_next_write: 25 },
          { device_id: 2, seconds_until_next_write: null },
        ],
      }),
    );

    const { container } = render(Running);
    await flushPolling();

    expect(screen.getByText('Drossel')).toBeTruthy();
    // Scope value-lookups to the cycles list — the chart legend now also
    // surfaces the latest target as "310 W" (Story 5.1c scope-extension),
    // so a global getByText would hit two nodes.
    const cycleList = container.querySelector('.cycle-list');
    expect(cycleList).toBeTruthy();
    expect(cycleList?.textContent).toContain('310 W');
    expect(cycleList?.textContent).toContain('300 W');
    expect(cycleList?.textContent).toContain('timeout');
    expect(cycleList?.textContent).toContain('42 ms');
    expect(screen.getByText(/Nächster Write in 25 s/)).toBeTruthy();
  });

  it('renders the functional-test lock when test_in_progress is true', async () => {
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({
        current_mode: 'drossel',
        test_in_progress: true,
      }),
    );

    render(Running);
    await flushPolling();

    expect(screen.getByText(/Funktionstest läuft/)).toBeTruthy();
    const link = screen.getByRole('link', { name: /Zum Funktionstest/ });
    expect(link.getAttribute('href')).toBe('#/functional-test');
    // Chart + cycles list must be hidden while the lock is active.
    expect(screen.queryByText('Letzte Zyklen')).toBeNull();
  });

  it('suppresses the rate-limit hint when all devices are unlocked', async () => {
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({
        current_mode: 'idle',
        rate_limit_status: [{ device_id: 1, seconds_until_next_write: null }],
      }),
    );

    render(Running);
    await flushPolling();

    expect(screen.queryByText(/Nächster Write/)).toBeNull();
  });

  it('surfaces the soonest cooldown (Math.min) when multiple devices are rate-limited', async () => {
    // P1 regression: prior Math.max would show 55 s here and hide the fact
    // that the wr_limit device unlocks in 5 s.
    getDevicesMock.mockResolvedValue([
      device({ id: 1, role: 'wr_limit' }),
      device({ id: 2, role: 'bat_ctrl' }),
    ]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({
        current_mode: 'drossel',
        // Seed a fresh cycle so the endpoint's idle-override (>15 s) would
        // not kick in — but the test does not hit the backend, so we only
        // need the client-side min selection to work.
        recent_cycles: [cycle({ device_id: 1, target_value_w: 100 })],
        rate_limit_status: [
          { device_id: 1, seconds_until_next_write: 5 },
          { device_id: 2, seconds_until_next_write: 55 },
        ],
      }),
    );

    render(Running);
    await flushPolling();

    expect(screen.getByText(/Nächster Write in 5 s/)).toBeTruthy();
    expect(screen.queryByText(/Nächster Write in 55 s/)).toBeNull();
  });

  it('caps the cycles list at ten entries even when the payload carries more', async () => {
    // AC 14: even if the backend ever ships more than 10 cycles the UI must
    // stay bounded. Exercises the `.slice(0, 10)` guard in `recentCycles`.
    const eleven = Array.from({ length: 11 }, (_, i) =>
      cycle({
        device_id: 1,
        target_value_w: 100 + i,
        readback_status: 'passed',
        latency_ms: 10 + i,
      }),
    );
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({ current_mode: 'drossel', recent_cycles: eleven }),
    );

    const { container } = render(Running);
    await flushPolling();

    const rows = container.querySelectorAll('.cycle-list .cycle-row');
    expect(rows.length).toBe(10);
  });

  it('renders three chart series (grid / target / readback) when all data flows', async () => {
    // AC 14: chart rendert mit 3 Serien. The LineChart only draws a <path>
    // for series with ≥ 2 points, so we need two polling ticks to fill the
    // grid / readback buffers alongside the target buffer that gets fed
    // from recent_cycles at each tick.
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    try {
      getDevicesMock.mockResolvedValue([
        device({ id: 1, role: 'wr_limit', entity_id: 'number.wr_limit' }),
        device({ id: 2, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
      ]);
      getStateSnapshotMock.mockResolvedValue(
        snapshot({
          current_mode: 'drossel',
          entities: [
            {
              entity_id: 'sensor.shelly_power',
              state: -123,
              unit: 'W',
              role: 'grid_meter',
              timestamp: '2026-04-24T12:00:00Z',
            },
            {
              entity_id: 'number.wr_limit',
              state: 200,
              unit: 'W',
              role: 'wr_limit',
              timestamp: '2026-04-24T12:00:00Z',
            },
          ],
          recent_cycles: [cycle({ device_id: 1, target_value_w: 310 })],
        }),
      );

      const { container } = render(Running);
      // First tick — fires immediately from polling.start().
      await flushPolling();
      // Second tick — triggers the setInterval callback.
      await vi.advanceTimersByTimeAsync(1000);
      await flushPolling();

      const paths = container.querySelectorAll('svg.line-chart path');
      expect(paths.length).toBe(3);
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows the skeleton chart pulse and both empty-state hints on a fresh snapshot', async () => {
    // AC 7: skeleton pulse + "Regler wartet ..." + "Noch keine Zyklen ..."
    // must all be visible before the first event lands — no spinners, no
    // error-red. The chart-skeleton class is driven by LineChart's own
    // showSkeleton derive (no ≥ 2 points yet).
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(snapshot({ current_mode: 'idle' }));

    const { container } = render(Running);
    await flushPolling();

    expect(container.querySelector('.chart-skeleton')).toBeTruthy();
    expect(screen.getByText(/Regler wartet auf erstes Sensor-Event/)).toBeTruthy();
    expect(screen.getByText(/Noch keine Zyklen erfasst/)).toBeTruthy();
  });

  // Story 5.1c: Chart-Legende und Update-Indikator
  it('renders a legend entry per chart series with the right label and color', async () => {
    // AC 1+2: legend lists one entry per ChartSeries with the same color
    // token the chart's stroke uses. Setup with both wr_limit + grid_meter
    // → 3 series (Netz-Leistung, Target-Limit, Readback).
    getDevicesMock.mockResolvedValue([
      device({ id: 1, role: 'wr_limit', entity_id: 'number.wr_limit' }),
      device({ id: 2, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
    ]);
    getStateSnapshotMock.mockResolvedValue(snapshot({ current_mode: 'drossel' }));

    const { container } = render(Running);
    await flushPolling();

    const dots = container.querySelectorAll('.chart-legend .legend-dot');
    expect(dots.length).toBe(3);
    expect((dots[0] as HTMLElement).style.background).toContain('--color-accent-warning');
    expect((dots[1] as HTMLElement).style.background).toContain('--color-accent-primary');
    expect((dots[2] as HTMLElement).style.background).toContain('--color-text-secondary');
    expect(screen.getByText('Netz-Leistung')).toBeTruthy();
    expect(screen.getByText('Target-Limit')).toBeTruthy();
    expect(screen.getByText('Readback')).toBeTruthy();
  });

  it('omits the wr-related legend entries on a battery-only setup', async () => {
    // AC 1: setup ohne wr_limit-device → legend zeigt nur Netz-Leistung.
    getDevicesMock.mockResolvedValue([
      device({ id: 1, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
    ]);
    getStateSnapshotMock.mockResolvedValue(snapshot({ current_mode: 'idle' }));

    render(Running);
    await flushPolling();

    expect(screen.getByText('Netz-Leistung')).toBeTruthy();
    expect(screen.queryByText('Target-Limit')).toBeNull();
    expect(screen.queryByText('Readback')).toBeNull();
  });

  it('hides the legend when the functional-test lock is active', async () => {
    // AC 4: bei test_in_progress=true wird weder Chart noch Legende noch
    // Update-Indikator angezeigt.
    getDevicesMock.mockResolvedValue([
      device({ id: 1, role: 'wr_limit' }),
      device({ id: 2, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
    ]);
    getStateSnapshotMock.mockResolvedValue(
      snapshot({ current_mode: 'drossel', test_in_progress: true }),
    );

    const { container } = render(Running);
    await flushPolling();

    expect(container.querySelector('.chart-legend')).toBeNull();
    expect(container.querySelector('.update-indicator')).toBeNull();
  });

  it('renders the update indicator with "gerade eben" right after a fresh tick', async () => {
    // AC 6: nach erstem erfolgreichem Tick zeigt der Indikator "gerade eben".
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(snapshot({ current_mode: 'idle' }));

    render(Running);
    await flushPolling();

    expect(screen.getByText(/Aktualisiert: gerade eben/)).toBeTruthy();
  });

  it('switches to a stale dot after 5 s without a tick', async () => {
    // AC 7: nach >5 s ohne neuen Snapshot wechselt der Indikator zu stale.
    // Pattern: ersten Tick durchspielen, dann pending Promise → Wall-Clock
    // setInterval (im Component) aktualisiert nowTs unabhängig von polling.
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
    try {
      getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
      getStateSnapshotMock.mockResolvedValueOnce(snapshot({ current_mode: 'idle' }));
      // After the first successful tick, every following tick hangs forever
      // so lastUpdateTs stops being refreshed.
      getStateSnapshotMock.mockReturnValue(new Promise<StateSnapshot>(() => {}));

      const { container } = render(Running);
      await flushPolling();

      // First tick landed → indicator should be fresh.
      expect(container.querySelector('.update-indicator[data-stale="true"]')).toBeNull();

      // Advance the wall-clock 6 s — polling stays hung, but the component's
      // independent 1 s ticker keeps nowTs moving so isStale flips to true.
      await vi.advanceTimersByTimeAsync(6000);
      await tick();

      expect(container.querySelector('.update-indicator[data-stale="true"]')).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows the latest value next to each legend entry (Story 5.1c scope-extension)', async () => {
    // Setup with grid_meter only so the legend has exactly one entry whose
    // current value can be asserted unambiguously. The grid sensor delivers
    // -150 W (export) — formatWatts rounds and renders "−150 W".
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    try {
      getDevicesMock.mockResolvedValue([
        device({ id: 2, role: 'grid_meter', entity_id: 'sensor.shelly_power' }),
      ]);
      getStateSnapshotMock.mockResolvedValue(
        snapshot({
          current_mode: 'idle',
          entities: [
            {
              entity_id: 'sensor.shelly_power',
              state: -150,
              unit: 'W',
              role: 'grid_meter',
              timestamp: '2026-04-25T12:00:00Z',
            },
          ],
        }),
      );

      const { container } = render(Running);
      await flushPolling();
      await vi.advanceTimersByTimeAsync(1000);
      await flushPolling();

      const legend = container.querySelector('.chart-legend');
      expect(legend).toBeTruthy();
      const value = legend?.querySelector('.legend-value');
      // formatWatts uses U+2212 mathematical minus, not ASCII hyphen, but we
      // assert via a regex that accepts any minus-like char to stay robust.
      expect(value?.textContent).toMatch(/[−-]?150 W/);
    } finally {
      vi.useRealTimers();
    }
  });

  it('omits the update indicator before the first snapshot lands', async () => {
    // AC 8: solange noch kein Snapshot eingetroffen ist, zeigt der Indikator
    // weder Dot noch Text. Mock returns hanging promise from the start.
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockReturnValue(new Promise<StateSnapshot>(() => {}));

    const { container } = render(Running);
    await flushPolling();

    expect(container.querySelector('.update-indicator')).toBeNull();
  });

  // Story 2.6 — Funktionstest-erforderlich-Banner.
  it('renders the refunctional-test banner when a control device is uncommissioned', async () => {
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit', commissioned_at: null })]);
    getStateSnapshotMock.mockResolvedValue(snapshot());

    render(Running);
    await flushPolling();

    const banner = await screen.findByTestId('refunctional-test-banner');
    expect(banner.textContent ?? '').toContain('Funktionstest');
    expect(banner.querySelector('a[href="#/functional-test"]')).toBeTruthy();
  });

  it('does not render the refunctional-test banner for fully commissioned setups', async () => {
    getDevicesMock.mockResolvedValue([device({ id: 1, role: 'wr_limit' })]);
    getStateSnapshotMock.mockResolvedValue(snapshot());

    render(Running);
    await flushPolling();

    expect(screen.queryByTestId('refunctional-test-banner')).toBeNull();
  });
});
