<script lang="ts">
  import { onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import type { EntityOption } from '../lib/api/types.js';

  let loading = $state(true);
  let loadError = $state<string | null>(null);

  let wrLimitEntities = $state<EntityOption[]>([]);
  let powerEntities = $state<EntityOption[]>([]);
  let socEntities = $state<EntityOption[]>([]);

  let hardwareType = $state<'hoymiles' | 'marstek_venus' | null>(null);
  let wrLimitEntityId = $state('');
  let batterySocEntityId = $state('');
  let minSoc = $state(15);
  let maxSoc = $state(95);
  let nightDischargeEnabled = $state(true);
  let nightStart = $state('20:00');
  let nightEnd = $state('06:00');
  let useSmartMeter = $state(false);
  let gridMeterEntityId = $state('');

  let saving = $state(false);
  let saveError = $state<string | null>(null);

  let canSave = $derived(
    hardwareType !== null &&
      wrLimitEntityId !== '' &&
      (hardwareType !== 'marstek_venus' || batterySocEntityId !== '') &&
      (!useSmartMeter || gridMeterEntityId !== ''),
  );

  let allEntitiesEmpty = $derived(
    !loading &&
      !loadError &&
      wrLimitEntities.length === 0 &&
      powerEntities.length === 0 &&
      socEntities.length === 0,
  );

  onMount(async () => {
    const startTs = Date.now();
    try {
      const entities = await client.getEntities();
      wrLimitEntities = entities.wr_limit_entities;
      powerEntities = entities.power_entities;
      socEntities = entities.soc_entities;
    } catch (err) {
      loadError = isApiError(err)
        ? err.detail
        : 'Verbindungsfehler. Bitte Seite neu laden.';
    } finally {
      const elapsed = Date.now() - startTs;
      if (elapsed < 400) {
        await new Promise<void>((resolve) => setTimeout(resolve, 400 - elapsed));
      }
      loading = false;
    }
  });

  function selectType(type: 'hoymiles' | 'marstek_venus'): void {
    hardwareType = type;
    wrLimitEntityId = '';
    batterySocEntityId = '';
  }

  async function handleSave(): Promise<void> {
    if (!hardwareType || !canSave) return;
    saving = true;
    saveError = null;
    try {
      await client.saveDevices({
        hardware_type: hardwareType,
        wr_limit_entity_id: wrLimitEntityId,
        battery_soc_entity_id:
          hardwareType === 'marstek_venus' ? batterySocEntityId : undefined,
        grid_meter_entity_id:
          useSmartMeter && gridMeterEntityId ? gridMeterEntityId : undefined,
        min_soc: hardwareType === 'marstek_venus' ? minSoc : undefined,
        max_soc: hardwareType === 'marstek_venus' ? maxSoc : undefined,
        night_discharge_enabled:
          hardwareType === 'marstek_venus' ? nightDischargeEnabled : undefined,
        night_start: hardwareType === 'marstek_venus' ? nightStart : undefined,
        night_end: hardwareType === 'marstek_venus' ? nightEnd : undefined,
      });
      window.location.hash = '#/functional-test';
    } catch (err) {
      saveError = isApiError(err)
        ? err.detail
        : 'Speichern fehlgeschlagen. Bitte erneut versuchen.';
    } finally {
      saving = false;
    }
  }
</script>

<main class="config-page">
  <header class="config-header">
    <p class="eyebrow">Solalex Setup</p>
    <h1>Hardware konfigurieren</h1>
  </header>

  {#if loading}
    <div class="skeleton-section">
      <div class="skeleton-pulse" style="height: 120px;"></div>
      <div class="skeleton-pulse" style="height: 48px; margin-top: 16px;"></div>
      <div class="skeleton-pulse" style="height: 48px; margin-top: 12px;"></div>
    </div>
  {:else if loadError}
    <div class="error-block">
      <p>{loadError}</p>
    </div>
  {:else}
    {#if allEntitiesEmpty}
      <div class="error-block">
        <p>
          Home Assistant hat keine passenden Entities geliefert. Prüfe, ob Hoymiles/Marstek/Shelly
          als Integrationen eingerichtet sind, und lade die Seite neu.
        </p>
      </div>
    {/if}
    <section class="config-section">
      <h2>Hardware-Typ</h2>
      <div class="type-tiles">
        <button
          class="type-tile"
          class:active={hardwareType === 'hoymiles'}
          aria-pressed={hardwareType === 'hoymiles'}
          onclick={() => selectType('hoymiles')}
        >
          <span class="tile-title">Hoymiles / OpenDTU</span>
          <span class="tile-sub">Drossel-Modus</span>
        </button>
        <button
          class="type-tile"
          class:active={hardwareType === 'marstek_venus'}
          aria-pressed={hardwareType === 'marstek_venus'}
          onclick={() => selectType('marstek_venus')}
        >
          <span class="tile-title">Marstek Venus 3E/D</span>
          <span class="tile-sub">Speicher-Modus</span>
        </button>
      </div>
      <p class="info-line">Anker Solix und generische HA-Entities folgen mit v1.5</p>
    </section>

    {#if hardwareType}
      <section class="config-section">
        <h2>
          {hardwareType === 'hoymiles' ? 'Wechselrichter-Limit-Entity' : 'Ladeleistungs-Entity'}
        </h2>
        {#if wrLimitEntities.length === 0}
          <p class="hint">
            Keine passenden Entities gefunden. Prüfe deine HA-Integration und lade die Seite neu.
          </p>
        {:else}
          <select bind:value={wrLimitEntityId} class="entity-select">
            <option value="">— Entity wählen —</option>
            {#each wrLimitEntities as opt (opt.entity_id)}
              <option value={opt.entity_id}>{opt.friendly_name} ({opt.entity_id})</option>
            {/each}
          </select>
        {/if}
      </section>

      {#if hardwareType === 'marstek_venus'}
        <section class="config-section">
          <h2>Akku-SoC-Entity</h2>
          {#if socEntities.length === 0}
            <p class="hint">Keine SoC-Entities gefunden. Prüfe deine HA-Integration.</p>
          {:else}
            <select bind:value={batterySocEntityId} class="entity-select">
              <option value="">— SoC-Entity wählen —</option>
              {#each socEntities as opt (opt.entity_id)}
                <option value={opt.entity_id}>{opt.friendly_name} ({opt.entity_id})</option>
              {/each}
            </select>
          {/if}
        </section>

        <section class="config-section">
          <h2>Ladelimits</h2>
          <div class="field-row">
            <label class="field-label">
              Min-SoC
              <div class="input-unit-row">
                <input
                  type="number"
                  bind:value={minSoc}
                  min="5"
                  max="40"
                  class="number-input"
                />
                <span class="field-unit">%</span>
              </div>
            </label>
            <label class="field-label">
              Max-SoC
              <div class="input-unit-row">
                <input
                  type="number"
                  bind:value={maxSoc}
                  min="51"
                  max="100"
                  class="number-input"
                />
                <span class="field-unit">%</span>
              </div>
            </label>
          </div>
        </section>

        <section class="config-section">
          <label class="checkbox-row">
            <input type="checkbox" bind:checked={nightDischargeEnabled} />
            <span>Nacht-Entladung aktivieren</span>
          </label>
          {#if nightDischargeEnabled}
            <div class="field-row" style="margin-top: 12px;">
              <label class="field-label">
                Startzeit
                <input type="time" bind:value={nightStart} class="time-input" />
              </label>
              <label class="field-label">
                Endzeit
                <input type="time" bind:value={nightEnd} class="time-input" />
              </label>
            </div>
          {/if}
        </section>
      {/if}

      <section class="config-section">
        <label class="checkbox-row">
          <input type="checkbox" bind:checked={useSmartMeter} />
          <span>Smart Meter (Shelly 3EM) zuordnen</span>
        </label>
        {#if useSmartMeter}
          {#if powerEntities.length === 0}
            <p class="hint" style="margin-top: 12px;">Keine Leistungs-Entities gefunden.</p>
          {:else}
            <select bind:value={gridMeterEntityId} class="entity-select" style="margin-top: 12px;">
              <option value="">— Netz-Leistungs-Entity wählen —</option>
              {#each powerEntities as opt (opt.entity_id)}
                <option value={opt.entity_id}>{opt.friendly_name} ({opt.entity_id})</option>
              {/each}
            </select>
          {/if}
        {/if}
      </section>

      <div class="save-row">
        {#if canSave}
          <button class="save-button" onclick={handleSave} disabled={saving}>
            {saving ? 'Speichern…' : 'Speichern'}
          </button>
        {:else}
          <p class="hint">
            Wähle zuerst
            {#if useSmartMeter && gridMeterEntityId === ''}
              {hardwareType === 'marstek_venus'
                ? 'Ladeleistungs-Entity, Akku-SoC-Entity und Smart-Meter-Entity'
                : 'WR-Limit-Entity und Smart-Meter-Entity'}.
            {:else}
              {hardwareType === 'marstek_venus'
                ? 'Ladeleistungs-Entity und Akku-SoC-Entity'
                : 'WR-Limit-Entity'}.
            {/if}
          </p>
        {/if}
        {#if saveError}
          <p class="error-line">{saveError}</p>
        {/if}
      </div>
    {/if}
  {/if}
</main>

<style>
  .config-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background: radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%),
      var(--color-bg);
    color: var(--color-text);
  }

  .config-header {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .config-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .config-section {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    padding: var(--space-3);
  }

  .config-section h2 {
    margin: 0 0 var(--space-2) 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .skeleton-section {
    width: min(100%, 640px);
    margin: 0 auto;
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
    border-radius: var(--radius-card);
  }

  @keyframes pulse {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
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

  .type-tiles {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-2);
  }

  .type-tile {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: var(--space-2);
    border-radius: 12px;
    border: 1px solid color-mix(in srgb, var(--color-text) 16%, transparent);
    background: var(--color-bg);
    color: var(--color-text);
    cursor: pointer;
    text-align: left;
    transition: border-color 120ms ease, background 120ms ease;
  }

  .type-tile:hover {
    border-color: color-mix(in srgb, var(--color-accent-primary) 60%, transparent);
    background: color-mix(in srgb, var(--color-accent-primary) 6%, var(--color-bg) 94%);
  }

  .type-tile.active {
    border-color: var(--color-accent-primary);
    background: color-mix(in srgb, var(--color-accent-primary) 12%, var(--color-bg) 88%);
  }

  .tile-title {
    font-weight: 600;
    font-size: 0.95rem;
  }

  .tile-sub {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .info-line {
    margin: var(--space-2) 0 0 0;
    font-size: 0.82rem;
    color: var(--color-text-secondary);
  }

  .entity-select {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 0.9rem;
    appearance: auto;
  }

  .entity-select:focus {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 1px;
  }

  .field-row {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .field-label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.88rem;
    color: var(--color-text-secondary);
  }

  .input-unit-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .number-input {
    width: 80px;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 0.9rem;
  }

  .number-input:focus {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 1px;
  }

  .field-unit {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
  }

  .time-input {
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 0.9rem;
  }

  .time-input:focus {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 1px;
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    cursor: pointer;
    font-size: 0.9rem;
  }

  .checkbox-row input[type='checkbox'] {
    width: 16px;
    height: 16px;
    accent-color: var(--color-accent-primary);
  }

  .save-row {
    width: min(100%, 640px);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .save-button {
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
    transition: transform 120ms ease, box-shadow 120ms ease;
    align-self: flex-start;
  }

  .save-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 0 32px color-mix(in srgb, var(--color-accent-primary) 56%, transparent);
  }

  .save-button:disabled {
    opacity: 0.7;
    cursor: default;
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

  @media (max-width: 480px) {
    .type-tiles {
      grid-template-columns: 1fr;
    }
  }
</style>
