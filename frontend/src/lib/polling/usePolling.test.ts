import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { usePolling } from './usePolling.js';

// Flush the microtask queue so async mock resolutions propagate.
const flush = () => Promise.resolve();

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('calls fetchFn immediately on start and sets data', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ value: 1 });
    const { data, start, stop } = usePolling(mockFetch, 1000);

    start();
    await flush();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(get(data)).toEqual({ value: 1 });
    stop();
  });

  it('polls again after the interval elapses', async () => {
    let count = 0;
    const mockFetch = vi.fn().mockImplementation(() => Promise.resolve({ n: ++count }));
    const { data, start, stop } = usePolling(mockFetch, 500);

    start();
    await flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(500);
    await flush();
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(get(data)).toEqual({ n: 2 });

    stop();
  });

  it('sets error store when fetchFn rejects', async () => {
    const fetchError = new Error('network failure');
    const mockFetch = vi.fn().mockRejectedValue(fetchError);
    const { error, start, stop } = usePolling(mockFetch, 1000);

    start();
    await flush();

    expect(get(error)).toBe(fetchError);
    stop();
  });

  it('stop prevents further interval ticks', async () => {
    const mockFetch = vi.fn().mockResolvedValue({});
    const { start, stop } = usePolling(mockFetch, 500);

    start();
    await flush();
    stop();

    const callsAfterStop = mockFetch.mock.calls.length;
    vi.advanceTimersByTime(2000);
    await flush();

    expect(mockFetch.mock.calls.length).toBe(callsAfterStop);
  });

  it('restarting after stop fires a new immediate tick', async () => {
    const mockFetch = vi.fn().mockResolvedValue({});
    const { start, stop } = usePolling(mockFetch, 500);

    start();
    await flush();
    stop();
    const callsBeforeRestart = mockFetch.mock.calls.length;

    start();
    await flush();

    expect(mockFetch.mock.calls.length).toBeGreaterThan(callsBeforeRestart);
    stop();
  });
});
