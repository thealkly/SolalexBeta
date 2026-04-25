// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import LivePreviewCard from './LivePreviewCard.svelte';
import * as client from '../api/client.js';
import { ApiError } from '../api/errors.js';

// Story 2.5 — sub-component for the smart-meter sign-convention toggle and
// the live-watt readout that drives it. Tested in isolation so the polling
// lifecycle, the toggle invocation and the watt formatting can be verified
// without driving Config.svelte's two <select bind:value> dropdowns.

const ENTITY = 'sensor.esphome_smart_meter_current_load';

interface Harness {
  invertSign: boolean;
  changes: boolean[];
}

function makeProps(invertSign: boolean): {
  entityId: string;
  invertSign: boolean;
  onInvertSignChange: (next: boolean) => void;
  __harness: Harness;
} {
  const harness: Harness = { invertSign, changes: [] };
  return {
    entityId: ENTITY,
    invertSign,
    onInvertSignChange: (next: boolean) => {
      harness.invertSign = next;
      harness.changes.push(next);
    },
    __harness: harness,
  };
}

describe('LivePreviewCard', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('renders the watt value as positive Bezug when raw value is positive and toggle is off', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: ENTITY,
      value_w: 2120,
      ts: '2026-04-25T12:00:00+00:00',
    });

    render(LivePreviewCard, makeProps(false));

    const valueEl = await screen.findByTestId('live-preview-value');
    await waitFor(() => {
      expect(valueEl.textContent ?? '').toContain('2120');
    });
    const direction = await screen.findByTestId('live-preview-direction');
    expect(direction.textContent ?? '').toContain('Bezug');
  });

  it('flips the displayed value when the invert toggle is enabled', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: ENTITY,
      value_w: 2120,
      ts: '2026-04-25T12:00:00+00:00',
    });

    const { rerender } = render(LivePreviewCard, makeProps(false));

    const valueEl = await screen.findByTestId('live-preview-value');
    await waitFor(() => {
      expect(valueEl.textContent ?? '').toContain('2120');
    });

    // Re-render with invertSign=true to simulate the parent flipping the
    // toggle (the actual toggle click delegates to the parent prop).
    await rerender(makeProps(true));

    await waitFor(() => {
      expect(valueEl.textContent ?? '').toContain('-2120');
    });
    const direction = await screen.findByTestId('live-preview-direction');
    expect(direction.textContent ?? '').toContain('Einspeisung');
  });

  it('shows the zero-hint when the absolute value is below 50 W', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: ENTITY,
      value_w: 12,
      ts: null,
    });

    render(LivePreviewCard, makeProps(false));

    const hint = await screen.findByTestId('live-preview-zero-hint');
    expect(hint.textContent ?? '').toContain('nahezu 0 W');
  });

  it('invokes onInvertSignChange when the toggle is clicked', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: ENTITY,
      value_w: 100,
      ts: null,
    });

    const props = makeProps(false);
    render(LivePreviewCard, props);

    const toggle = (await screen.findByTestId(
      'invert-sign-toggle',
    )) as HTMLInputElement;
    await fireEvent.click(toggle);

    expect(props.__harness.changes).toEqual([true]);
  });

  it('starts polling on mount and stops on unmount', async () => {
    const fetchSpy = vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: ENTITY,
      value_w: 50,
      ts: null,
    });

    const { unmount } = render(LivePreviewCard, makeProps(false));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(ENTITY);
    });
    const callsAfterMount = fetchSpy.mock.calls.length;
    expect(callsAfterMount).toBeGreaterThan(0);

    unmount();

    // After unmount, no further polls land — advance the clock and confirm
    // the call count stays put. Allow one in-flight call to complete.
    vi.advanceTimersByTime(2000);
    await Promise.resolve();
    expect(fetchSpy.mock.calls.length).toBeLessThanOrEqual(callsAfterMount + 1);
  });

  it('displays the German error message when the polling call rejects', async () => {
    vi.spyOn(client, 'getEntityState').mockRejectedValue(
      new ApiError(503, 'urn:test', 'down', 'Backend nicht erreichbar.'),
    );

    render(LivePreviewCard, makeProps(false));

    await waitFor(() => {
      const card = screen.getByTestId('live-preview-card');
      expect(card.textContent ?? '').toContain('Backend nicht erreichbar.');
    });
  });
});
