<script lang="ts">
  import { onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import LivePreviewCard from '../lib/components/LivePreviewCard.svelte';
  import type {
    DeviceResponse,
    EntityOption,
    ForcedMode,
    ForcedModeChoice,
    HardwareConfigRequest,
  } from '../lib/api/types.js';

  // Story 2.6 — single-source-of-truth Config component used both for
  // initial setup (default) and for post-commissioning hardware edits
  // (editMode + initialDevices). Edit-mode pre-fills state from the
  // existing devices, swaps Save semantics to PUT, and routes back to
  // /running on success rather than /functional-test.
  interface Props {
    editMode?: boolean;
    initialDevices?: DeviceResponse[];
    /**
     * Story 2.6 review P5: callback fired after a successful PUT in
     * editMode so the App-level devices cache can be refreshed before
     * the user navigates back. Without this hook the cache stays at the
     * pre-edit snapshot until the next full-page mount, and a quick
     * round-trip Settings → Hardware ändern → Hardware ändern would
     * show stale data.
     */
    onSaved?: (devices: DeviceResponse[]) => void;
  }

  let {
    editMode = false,
    initialDevices = [],
    onSaved,
  }: Props = $props();

  let loading = $state(true);
  let loadError = $state<string | null>(null);

  let wrLimitEntities = $state<EntityOption[]>([]);
  let powerEntities = $state<EntityOption[]>([]);
  let socEntities = $state<EntityOption[]>([]);

  let hardwareType = $state<'generic' | 'marstek_venus' | null>(null);
  let wrLimitEntityId = $state('');
  let batterySocEntityId = $state('');
  let minSoc = $state(15);
  let maxSoc = $state(95);
  let nightDischargeEnabled = $state(true);
  let nightStart = $state('20:00');
  let nightEnd = $state('06:00');
  let useSmartMeter = $state(false);
  let gridMeterEntityId = $state('');
  // Story 2.6 — captures the pre-edit snapshot so the warn-banner can
  // detect WR / hardware-type swaps that would force a re-functional-test.
  let initialWrEntityId = $state('');
  let initialHardwareType = $state<'generic' | 'marstek_venus' | null>(null);
  // Story 2.5 — sign-convention override. The toggle value is buffered
  // here and only persisted alongside the rest of the config when the
  // user hits "Speichern". The polling + watt readout live in the
  // dedicated <LivePreviewCard> sub-component.
  let invertSign = $state(false);
  // Generic-inverter limit-range override (Story 2.4 Review D3).
  // Empty string = use adapter default (2 / 3000 W).
  let minLimitW = $state<string>('');
  let maxLimitW = $state<string>('');

  let saving = $state(false);
  let saveError = $state<string | null>(null);

  // Story 3.5 — manual mode override (Beta-tester escape hatch).
  // null GET response = controller wired but no override active; choice
  // 'auto' maps to forced_mode null. Errors revert the radio so the UI
  // never lies about backend state.
  let modeOverrideAvailable = $state(false);
  let modeChoice = $state<ForcedModeChoice>('auto');
  let modeBaseline = $state<ForcedMode | null>(null);
  let modeOverrideError = $state<string | null>(null);
  let modeOverridePending = $state(false);

  let canSave = $derived(
    hardwareType !== null &&
      wrLimitEntityId !== '' &&
      (hardwareType !== 'marstek_venus' || batterySocEntityId !== '') &&
      (!useSmartMeter || gridMeterEntityId !== ''),
  );

  // Show the global empty-state banner when the user is missing the
  // entity list they actually need — not only when *all three* lists are
  // empty (Story 2.4 Review P11). Without a hardware-type pick yet, both
  // wr_limit and meter are relevant; once the user picked, soc is only
  // relevant for marstek_venus.
  let allEntitiesEmpty = $derived(
    !loading &&
      !loadError &&
      wrLimitEntities.length === 0 &&
      powerEntities.length === 0 &&
      (hardwareType !== 'marstek_venus' || socEntities.length === 0),
  );

  function safeParseConfig(raw: string): Record<string, unknown> {
    try {
      const parsed: unknown = JSON.parse(raw || '{}');
      if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // Fall through to empty defaults — malformed config_json must not
      // poison the edit form.
    }
    return {};
  }

  function loadStateFromInitialDevices(devices: DeviceResponse[]): void {
    const wrLimit = devices.find((d) => d.role === 'wr_limit');
    const wrCharge = devices.find((d) => d.role === 'wr_charge');
    const batterySoc = devices.find((d) => d.role === 'battery_soc');
    const gridMeter = devices.find((d) => d.role === 'grid_meter');

    if (wrCharge) {
      hardwareType = 'marstek_venus';
      wrLimitEntityId = wrCharge.entity_id;
      const cfg = safeParseConfig(wrCharge.config_json);
      if (typeof cfg.min_soc === 'number') minSoc = cfg.min_soc;
      if (typeof cfg.max_soc === 'number') maxSoc = cfg.max_soc;
      if (typeof cfg.night_discharge_enabled === 'boolean')
        nightDischargeEnabled = cfg.night_discharge_enabled;
      if (typeof cfg.night_start === 'string') nightStart = cfg.night_start;
      if (typeof cfg.night_end === 'string') nightEnd = cfg.night_end;
    } else if (wrLimit) {
      hardwareType = 'generic';
      wrLimitEntityId = wrLimit.entity_id;
      const cfg = safeParseConfig(wrLimit.config_json);
      if (typeof cfg.min_limit_w === 'number') minLimitW = String(cfg.min_limit_w);
      if (typeof cfg.max_limit_w === 'number') maxLimitW = String(cfg.max_limit_w);
    }

    if (batterySoc) {
      batterySocEntityId = batterySoc.entity_id;
    }

    if (gridMeter) {
      useSmartMeter = true;
      gridMeterEntityId = gridMeter.entity_id;
      const cfg = safeParseConfig(gridMeter.config_json);
      invertSign = cfg.invert_sign === true;
    }

    initialWrEntityId = wrLimitEntityId;
    initialHardwareType = hardwareType;
  }

  // Story 2.6 — warn-banner trigger: WR-entity swap OR hardware-type
  // swap force a new functional test, so the user gets a heads-up
  // before clicking save. The guard intentionally fires while the user
  // is mid-clear (``wrLimitEntityId === ''``) — the banner reflects
  // "save will null commissioned_at", which is true the moment the
  // initial value is no longer the current value, regardless of whether
  // the user has finished picking the replacement (review P10).
  let needsRefunctionalTest = $derived(
    editMode &&
      hardwareType !== null &&
      ((initialWrEntityId !== '' && wrLimitEntityId !== initialWrEntityId) ||
        (initialHardwareType !== null &&
          hardwareType !== initialHardwareType)),
  );

  function entityLabel(opt: EntityOption): string {
    // Avoid "number.x (number.x)" duplication when HA didn't expose a
    // friendly_name and the backend fell back to the entity_id (Story 2.4
    // Review P12).
    return opt.friendly_name === opt.entity_id
      ? opt.entity_id
      : `${opt.friendly_name} (${opt.entity_id})`;
  }

  // Story 2.6 review P5: when the user opens /hardware-edit via a
  // direct URL hit, App.svelte may still be loading the devices cache
  // and pass us ``initialDevices=[]``. Without this effect the form
  // would render Defaults and a Save would replace the real config.
  // Latch a one-shot apply so subsequent prop updates (e.g. after a
  // successful PUT writes back to the cache) do not stomp on user
  // edits in a still-mounted Config component.
  let initialDevicesApplied = $state(false);
  $effect(() => {
    if (!editMode) return;
    if (initialDevicesApplied) return;
    if (initialDevices.length === 0) return;
    loadStateFromInitialDevices(initialDevices);
    initialDevicesApplied = true;
  });

  onMount(async () => {
    const startTs = Date.now();
    if (editMode && initialDevices.length > 0 && !initialDevicesApplied) {
      loadStateFromInitialDevices(initialDevices);
      initialDevicesApplied = true;
    }
    try {
      const entities = await client.getEntities();
      wrLimitEntities = entities.wr_limit_entities;
      powerEntities = entities.power_entities;
      socEntities = entities.soc_entities;
    } catch (err) {
      loadError = isApiError(err) ? err.detail : 'Verbindungsfehler. Bitte Seite neu laden.';
    } finally {
      const elapsed = Date.now() - startTs;
      if (elapsed < 400) {
        await new Promise<void>((resolve) => setTimeout(resolve, 400 - elapsed));
      }
      loading = false;
    }
    // Mode-override card surfaces only when the backend has a controller
    // wired up (post-commissioning or in development). Failure here keeps
    // the section hidden — the rest of the wizard stays usable.
    try {
      const mode = await client.fetchControlMode();
      modeBaseline = mode.baseline_mode;
      modeChoice = mode.forced_mode ?? 'auto';
      modeOverrideAvailable = true;
    } catch {
      modeOverrideAvailable = false;
    }
  });

  async function handleModeChange(next: ForcedModeChoice): Promise<void> {
    const previousChoice = modeChoice;
    if (next === modeChoice) return;
    modeChoice = next;
    modeOverrideError = null;
    modeOverridePending = true;
    try {
      const mode = await client.setForcedMode(next === 'auto' ? null : next);
      modeBaseline = mode.baseline_mode;
      modeChoice = mode.forced_mode ?? 'auto';
    } catch (err) {
      // Revert the radio so the UI cannot diverge from backend state.
      modeChoice = previousChoice;
      modeOverrideError = isApiError(err)
        ? err.detail
        : 'Modus-Wechsel fehlgeschlagen. Bitte erneut versuchen.';
    } finally {
      modeOverridePending = false;
    }
  }

  function selectType(type: 'generic' | 'marstek_venus'): void {
    hardwareType = type;
    wrLimitEntityId = '';
    batterySocEntityId = '';
  }

  async function handleSave(): Promise<void> {
    if (!hardwareType || !canSave) return;
    saving = true;
    saveError = null;
    try {
      const minLimitParsed = minLimitW.trim() === '' ? undefined : Number(minLimitW);
      const maxLimitParsed = maxLimitW.trim() === '' ? undefined : Number(maxLimitW);
      const payload: HardwareConfigRequest = {
        hardware_type: hardwareType,
        wr_limit_entity_id: wrLimitEntityId,
        battery_soc_entity_id:
          hardwareType === 'marstek_venus' ? batterySocEntityId : undefined,
        grid_meter_entity_id:
          useSmartMeter && gridMeterEntityId ? gridMeterEntityId : undefined,
        invert_sign:
          useSmartMeter && gridMeterEntityId ? invertSign : undefined,
        min_soc: hardwareType === 'marstek_venus' ? minSoc : undefined,
        max_soc: hardwareType === 'marstek_venus' ? maxSoc : undefined,
        night_discharge_enabled:
          hardwareType === 'marstek_venus' ? nightDischargeEnabled : undefined,
        night_start: hardwareType === 'marstek_venus' ? nightStart : undefined,
        night_end: hardwareType === 'marstek_venus' ? nightEnd : undefined,
        min_limit_w:
          hardwareType === 'generic' &&
          minLimitParsed !== undefined &&
          Number.isFinite(minLimitParsed)
            ? minLimitParsed
            : undefined,
        max_limit_w:
          hardwareType === 'generic' &&
          maxLimitParsed !== undefined &&
          Number.isFinite(maxLimitParsed)
            ? maxLimitParsed
            : undefined,
      };
      if (editMode) {
        // Pass the response back to the App-level cache so a follow-up
        // navigation to Settings or another /hardware-edit visit reads
        // the post-PUT state instead of a stale snapshot (review P5).
        const updated = await client.updateDevices(payload);
        onSaved?.(updated);
        window.location.hash = '#/running';
      } else {
        await client.saveDevices(payload);
        window.location.hash = '#/functional-test';
      }
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
    <p class="eyebrow">Solalex {editMode ? '' : 'Setup'}</p>
    <h1>{editMode ? 'Hardware ändern' : 'Hardware konfigurieren'}</h1>
  </header>

  {#if editMode && needsRefunctionalTest}
    <section class="warn-banner" data-testid="refunctional-test-warn">
      <p>
        Diese Änderung erfordert einen erneuten Funktionstest. Solalex pausiert die Drossel-
        und Speicher-Regelung für den neuen Wechselrichter, bis du den Test bestätigt hast.
      </p>
    </section>
  {/if}

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
          Home Assistant hat keine passenden Entities geliefert. Prüfe, ob deine
          Wechselrichter-/Akku-/Smart-Meter-Integration aktiv ist und passende Power-Sensoren
          bereitstellt.
        </p>
      </div>
    {/if}
    <section class="config-section">
      <h2>Hardware-Typ</h2>
      <div class="type-tiles">
        <button
          class="type-tile"
          class:active={hardwareType === 'generic'}
          aria-pressed={hardwareType === 'generic'}
          onclick={() => selectType('generic')}
        >
          <span class="tile-title">Wechselrichter (allgemein)</span>
          <span class="tile-sub">z. B. Hoymiles/OpenDTU, Trucki, ESPHome</span>
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
      <p class="info-line">Anker Solix folgt mit v1.5</p>
    </section>

    {#if hardwareType}
      <section class="config-section">
        <h2>
          {hardwareType === 'generic' ? 'Wechselrichter-Limit-Entity' : 'Ladeleistungs-Entity'}
        </h2>
        {#if wrLimitEntities.length === 0}
          <p class="hint">
            Keine passenden Entities gefunden. Prüfe deine HA-Integration und lade die Seite neu.
          </p>
        {:else}
          <select bind:value={wrLimitEntityId} class="entity-select">
            <option value="">— Entity wählen —</option>
            {#each wrLimitEntities as opt (opt.entity_id)}
              <option value={opt.entity_id}>{entityLabel(opt)}</option>
            {/each}
          </select>
        {/if}
      </section>

      {#if hardwareType === 'generic'}
        <section class="config-section">
          <h2>WR-Limit-Bereich (optional)</h2>
          <p class="hint" style="margin-bottom: 12px;">
            Lass die Felder leer, wenn dein Wechselrichter zwischen 2 W und 3000 W steuerbar ist.
            Bei größeren Inverter-Stacks (z. B. Hoymiles HMT-2250, OpenDTU-Multi) oder wenn du
            0 W als „aus" senden willst, hier den Hardware-Bereich überschreiben.
          </p>
          <div class="field-row">
            <label class="field-label">
              Min-Limit
              <div class="input-unit-row">
                <input
                  type="number"
                  bind:value={minLimitW}
                  min="0"
                  max="10000"
                  placeholder="2"
                  class="number-input"
                />
                <span class="field-unit">W</span>
              </div>
            </label>
            <label class="field-label">
              Max-Limit
              <div class="input-unit-row">
                <input
                  type="number"
                  bind:value={maxLimitW}
                  min="1"
                  max="10000"
                  placeholder="3000"
                  class="number-input"
                />
                <span class="field-unit">W</span>
              </div>
            </label>
          </div>
        </section>
      {/if}

      {#if hardwareType === 'marstek_venus'}
        <section class="config-section">
          <h2>Akku-SoC-Entity</h2>
          {#if socEntities.length === 0}
            <p class="hint">Keine SoC-Entities gefunden. Prüfe deine HA-Integration.</p>
          {:else}
            <select bind:value={batterySocEntityId} class="entity-select">
              <option value="">— SoC-Entity wählen —</option>
              {#each socEntities as opt (opt.entity_id)}
                <option value={opt.entity_id}>{entityLabel(opt)}</option>
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
                <input type="number" bind:value={minSoc} min="5" max="40" class="number-input" />
                <span class="field-unit">%</span>
              </div>
            </label>
            <label class="field-label">
              Max-SoC
              <div class="input-unit-row">
                <input type="number" bind:value={maxSoc} min="51" max="100" class="number-input" />
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
          <span class="checkbox-text">
            <span>Smart Meter zuordnen</span>
            <span class="checkbox-sub">z. B. Shelly 3EM, ESPHome SML, Tibber</span>
          </span>
        </label>
        {#if useSmartMeter}
          {#if powerEntities.length === 0}
            <p class="hint" style="margin-top: 12px;">Keine Leistungs-Entities gefunden.</p>
          {:else}
            <select bind:value={gridMeterEntityId} class="entity-select" style="margin-top: 12px;">
              <option value="">— Netz-Leistungs-Entity wählen —</option>
              {#each powerEntities as opt (opt.entity_id)}
                <option value={opt.entity_id}>{entityLabel(opt)}</option>
              {/each}
            </select>
          {/if}
        {/if}

        {#if useSmartMeter && gridMeterEntityId !== ''}
          <LivePreviewCard
            entityId={gridMeterEntityId}
            {invertSign}
            onInvertSignChange={(next) => (invertSign = next)}
          />
        {/if}
      </section>

      <div class="save-row">
        {#if canSave}
          <button
            class="save-button"
            onclick={handleSave}
            disabled={saving}
            data-testid="config-save"
          >
            {saving
              ? editMode
                ? 'Übernehme…'
                : 'Speichern…'
              : editMode
                ? 'Änderungen übernehmen'
                : 'Speichern'}
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

    {#if modeOverrideAvailable}
      <section class="config-section" data-testid="mode-override-section">
        <h2>Regelungs-Modus</h2>
        <p class="hint" style="margin-bottom: 12px;">
          Solalex erkennt den Modus normalerweise selbst. Diese Option überschreibt die
          Auto-Erkennung — nur für Tests oder wenn der Auto-Modus nicht passt.
        </p>
        <div class="mode-radio-group" role="radiogroup" aria-label="Regelungs-Modus">
          {#each [{ value: 'auto', label: 'Automatisch (empfohlen)' }, { value: 'drossel', label: 'Drossel' }, { value: 'speicher', label: 'Speicher' }, { value: 'multi', label: 'Multi' }] as opt (opt.value)}
            <label class="mode-radio-row">
              <input
                type="radio"
                name="forced_mode"
                value={opt.value}
                checked={modeChoice === opt.value}
                disabled={modeOverridePending}
                onchange={() => handleModeChange(opt.value as ForcedModeChoice)}
              />
              <span>{opt.label}</span>
            </label>
          {/each}
        </div>
        {#if modeChoice !== 'auto' && modeBaseline}
          <p class="hint" style="margin-top: 12px;" data-testid="mode-baseline-hint">
            Manuell überschrieben: <strong>{modeChoice}</strong> — auto-erkannter Modus wäre:
            <strong>{modeBaseline}</strong>.
          </p>
        {/if}
        {#if modeOverrideError}
          <p class="error-line" style="margin-top: 12px;" data-testid="mode-override-error">
            {modeOverrideError}
          </p>
        {/if}
      </section>
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
    background:
      radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%), var(--color-bg);
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
    transition:
      border-color 120ms ease,
      background 120ms ease;
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

  .mode-radio-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mode-radio-row {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    cursor: pointer;
    font-size: 0.92rem;
  }

  .mode-radio-row input[type='radio'] {
    accent-color: var(--color-accent-primary);
  }

  .mode-radio-row input[type='radio']:disabled {
    cursor: default;
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
    transition:
      transform 120ms ease,
      box-shadow 120ms ease;
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

  .warn-banner {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 50%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 12%, var(--color-bg) 88%);
    padding: var(--space-3);
    color: var(--color-text);
  }

  .warn-banner p {
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.4;
  }

  @media (max-width: 480px) {
    .type-tiles {
      grid-template-columns: 1fr;
    }
  }
</style>
