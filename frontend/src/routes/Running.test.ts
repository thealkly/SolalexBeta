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

    render(Running);
    await flushPolling();

    expect(screen.getByText('Drossel')).toBeTruthy();
    expect(screen.getByText('310 W')).toBeTruthy();
    expect(screen.getByText('300 W')).toBeTruthy();
    expect(screen.getByText('timeout')).toBeTruthy();
    expect(screen.getByText('42 ms')).toBeTruthy();
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
});
