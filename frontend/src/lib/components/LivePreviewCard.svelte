<script lang="ts">
  import { onDestroy } from 'svelte';
  import * as client from '../api/client.js';
  import { isApiError } from '../api/errors.js';
  import { usePolling } from '../polling/usePolling.js';
  import type { EntityState } from '../api/types.js';

  // Story 2.5 — Smart-Meter Vorzeichen-Toggle + Live-Preview.
  //
  // Extracted from Config.svelte so the polling lifecycle, the toggle and
  // the watt readout can be unit-tested without driving Config's two
  // <select bind:value> dropdowns (which have happy-dom interop quirks).
  // Renders the toggle and the live-watt readout; the parent owns the
  // ``invertSign`` value via the bindable prop and persists it on save.

  interface Props {
    entityId: string;
    invertSign: boolean;
    onInvertSignChange: (next: boolean) => void;
  }

  const ZERO_HINT_THRESHOLD_W = 50;

  let { entityId, invertSign, onInvertSignChange }: Props = $props();

  let rawValueW = $state<number | null>(null);
  let errorMessage = $state<string | null>(null);
  let polling: ReturnType<typeof usePolling<EntityState>> | null = null;
  let lastEntityId = '';
  // Hold the unsubscribers from the polling stores so swap-on-entity-change
  // and unmount actually release the closures (Story-2.5 review P11).
  let dataUnsub: (() => void) | null = null;
  let errorUnsub: (() => void) | null = null;

  let displayedValueW = $derived(
    rawValueW === null ? null : Math.round(invertSign ? -rawValueW : rawValueW),
  );
  // Threshold is checked against the *rendered* integer so the band
  // classification ("Bezug", "Einspeisung", "nahezu 0 W") matches the
  // number the user sees — avoids "50 W" displayed alongside a "Bezug"
  // hint (Story-2.5 review P12).
  let belowThreshold = $derived(
    displayedValueW !== null &&
      Math.abs(displayedValueW) < ZERO_HINT_THRESHOLD_W,
  );

  function startPolling(id: string): void {
    stopPolling();
    rawValueW = null;
    errorMessage = null;
    const p = usePolling<EntityState>(() => client.getEntityState(id), 1000);
    dataUnsub = p.data.subscribe((snapshot) => {
      if (snapshot === null) return;
      rawValueW = snapshot.value_w;
    });
    errorUnsub = p.error.subscribe((err) => {
      if (err === null) {
        errorMessage = null;
        return;
      }
      errorMessage = isApiError(err)
        ? err.detail
        : 'Live-Wert konnte nicht geladen werden.';
    });
    p.start();
    polling = p;
    lastEntityId = id;
  }

  function stopPolling(): void {
    if (dataUnsub !== null) {
      dataUnsub();
      dataUnsub = null;
    }
    if (errorUnsub !== null) {
      errorUnsub();
      errorUnsub = null;
    }
    if (polling !== null) {
      polling.stop();
      polling = null;
    }
    lastEntityId = '';
  }

  $effect(() => {
    if (entityId !== '' && entityId !== lastEntityId) {
      startPolling(entityId);
    } else if (entityId === '' && polling !== null) {
      stopPolling();
      rawValueW = null;
      errorMessage = null;
    }
  });

  onDestroy(() => {
    stopPolling();
  });

  function handleToggle(event: { currentTarget: { checked: boolean } }): void {
    onInvertSignChange(event.currentTarget.checked);
  }
</script>

<label class="checkbox-row" style="margin-top: 16px;">
  <input
    type="checkbox"
    checked={invertSign}
    onchange={handleToggle}
    data-testid="invert-sign-toggle"
  />
  <span class="checkbox-text">
    <span>Vorzeichen invertieren</span>
    <span class="checkbox-sub">
      Aktivieren, wenn der gewählte Sensor Bezug als negative und Einspeisung als positive
      Werte liefert (häufig bei ESPHome-SML).
    </span>
  </span>
</label>

<div class="live-preview" data-testid="live-preview-card">
  {#if errorMessage}
    <p class="error-line">{errorMessage}</p>
  {:else if displayedValueW === null}
    <div class="skeleton-pulse" style="height: 56px;"></div>
  {:else}
    <div class="live-preview-value" data-testid="live-preview-value">
      {displayedValueW > 0 ? '+' : ''}{displayedValueW} W
    </div>
    {#if belowThreshold}
      <p class="hint" data-testid="live-preview-zero-hint">
        Sensor zeigt nahezu 0 W — schalt eine große Last (Wasserkocher, Heizlüfter) ein und
        beobachte die Richtung.
      </p>
    {:else if displayedValueW > 0}
      <p class="hint" data-testid="live-preview-direction">Bezug aus dem Netz</p>
    {:else}
      <p class="hint" data-testid="live-preview-direction">Einspeisung ins Netz</p>
    {/if}
  {/if}
</div>

<style>
  .checkbox-row {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    cursor: pointer;
    font-size: 0.9rem;
  }

  .checkbox-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .checkbox-sub {
    font-size: 0.78rem;
    color: var(--color-text-secondary);
  }

  .checkbox-row input[type='checkbox'] {
    width: 16px;
    height: 16px;
    accent-color: var(--color-accent-primary);
  }

  .live-preview {
    margin-top: 16px;
    padding: var(--space-2);
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 12%, transparent);
    background: var(--color-bg);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .live-preview-value {
    font-size: clamp(1.6rem, 3vw, 2.2rem);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--color-text);
  }

  .skeleton-pulse {
    background: linear-gradient(
      90deg,
      var(--color-surface) 25%,
      color-mix(in srgb, var(--color-surface) 70%, var(--color-text) 30%) 50%,
      var(--color-surface) 75%
    );
    background-size: 200% 100%;
    animation: pulse 1.4s ease-in-out infinite;
    border-radius: 8px;
  }

  @keyframes pulse {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  .hint {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-text-secondary);
  }

  .error-line {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-accent-warning);
  }
</style>
