import { writable, type Writable } from 'svelte/store';

export interface PollingHook<T> {
  data: Writable<T | null>;
  error: Writable<unknown>;
  start(): void;
  stop(): void;
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number,
): PollingHook<T> {
  const data = writable<T | null>(null);
  const error = writable<unknown>(null);
  let timerId: ReturnType<typeof setInterval> | null = null;

  async function tick(): Promise<void> {
    try {
      data.set(await fetchFn());
      error.set(null);
    } catch (err) {
      error.set(err);
    }
  }

  function start(): void {
    stop();
    void tick();
    timerId = setInterval(() => {
      void tick();
    }, intervalMs);
  }

  function stop(): void {
    if (timerId !== null) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  return { data, error, start, stop };
}
