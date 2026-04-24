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

  // Epoch-Token: jeder ``start()``-Aufruf erhöht den Token, sodass
  // verspätete ``fetchFn()``-Antworten aus älteren Start/Stop-Zyklen
  // keine aktuellen Store-Werte überschreiben (Story 2.2 Review P22/P23).
  let epoch = 0;

  async function tick(forEpoch: number): Promise<void> {
    try {
      const result = await fetchFn();
      if (forEpoch !== epoch) return;
      data.set(result);
      error.set(null);
    } catch (err) {
      if (forEpoch !== epoch) return;
      error.set(err);
    }
  }

  function start(): void {
    stop();
    epoch += 1;
    const currentEpoch = epoch;
    void tick(currentEpoch);
    timerId = setInterval(() => {
      void tick(currentEpoch);
    }, intervalMs);
  }

  function stop(): void {
    // Bumping the epoch invalidates any in-flight fetch so its eventual
    // resolution cannot bleed into the next session's ``data``/``error``.
    epoch += 1;
    if (timerId !== null) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  return { data, error, start, stop };
}
