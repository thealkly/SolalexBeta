<script lang="ts">
  import { onMount } from 'svelte';
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';
  import type { DeviceResponse } from '../lib/api/types.js';

  // Story 3.6 — Settings surface for post-commissioning Akku-bounds and
  // night-discharge window. Hidden route (#/settings); no Running.svelte
  // link by design (analogous to 4.0a Diagnose-Schnellexport).

  let loading = $state(true);
  let loadError = $state<string | null>(null);

  // True when the commissioned device set has a wr_charge — the form
  // renders only then. Drossel-only setups land on the no-battery hint.
  let hasBattery = $state(false);
  let setupNotActivated = $state(false);
  // Story 2.6 — drives the visible hardware-card so the user can edit
  // their setup without a SQL reset. Mirrors getDevices() result.
  let allDevices = $state<DeviceResponse[]>([]);

  let minSoc = $state(15);
  let maxSoc = $state(95);
  let nightDischargeEnabled = $state(true);
  let nightStart = $state('20:00');
  let nightEnd = $state('06:00');

  // Tracks the last-known-safe Min-SoC so the user can revert from the
  // plausibility-confirm block without losing context.
  let lastSafeMinSoc = $state(15);

  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let savedNotice = $state<string | null>(null);

  // True after Save is clicked for a Min-SoC value < 10 % — gates the
  // regular Save button until they pick "Trotzdem speichern" or revert.
  let lowMinSocPending = $state(false);
  // Sticks once the user explicitly accepted the low-Min-SoC warning;
  // travels into the PATCH body so the backend lets the value through.
  let lowMinSocAcknowledged = $state(false);

  let gapInvalid = $derived(maxSoc <= minSoc + 10);
  let nightWindowEmpty = $derived(nightDischargeEnabled && nightStart === nightEnd);
  let canSave = $derived(
    hasBattery && !gapInvalid && !nightWindowEmpty && !lowMinSocPending && !saving,
  );

  // Story 2.6 — friendly labels for the hardware-card.
  const HARDWARE_TYPE_LABELS: Record<string, string> = {
    generic: 'Wechselrichter (allgemein)',
    marstek_venus: 'Marstek Venus',
    generic_meter: 'Smart Meter (allgemein)',
  };

  function describeRole(role: string): string {
    switch (role) {
      case 'wr_limit':
        return 'Wechselrichter-Limit';
      case 'wr_charge':
        return 'Akku-Ladeleistung';
      case 'battery_soc':
        return 'Akku-SoC';
      case 'grid_meter':
        return 'Smart-Meter';
      default:
        return role;
    }
  }

  function navigateToHardwareEdit(): void {
    window.location.hash = '#/hardware-edit';
  }

  let gridMeterDevice = $derived(
    allDevices.find((d) => d.role === 'grid_meter') ?? null,
  );
  let gridMeterInvertSign = $derived(
    gridMeterDevice ? parseConfig(gridMeterDevice.config_json).invert_sign === true : false,
  );

  function parseConfig(raw: string): Record<string, unknown> {
    try {
      const parsed: unknown = JSON.parse(raw || '{}');
      if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // Fall through to empty defaults.
    }
    return {};
  }

  function loadFromDevice(device: DeviceResponse): void {
    const cfg = parseConfig(device.config_json);
    if (typeof cfg.min_soc === 'number') minSoc = cfg.min_soc;
    if (typeof cfg.max_soc === 'number') maxSoc = cfg.max_soc;
    if (typeof cfg.night_discharge_enabled === 'boolean')
      nightDischargeEnabled = cfg.night_discharge_enabled;
    if (typeof cfg.night_start === 'string') nightStart = cfg.night_start;
    if (typeof cfg.night_end === 'string') nightEnd = cfg.night_end;
    lastSafeMinSoc = minSoc >= 10 ? minSoc : 15;
    lowMinSocAcknowledged = minSoc >= 5 && minSoc < 10;
    lowMinSocPending = false;
  }

  onMount(async () => {
    const startTs = Date.now();
    try {
      const devices = await client.getDevices();
      allDevices = devices;
      setupNotActivated =
        devices.length === 0 || devices.some((d) => d.commissioned_at === null);
      const wrCharge = devices.find((d) => d.role === 'wr_charge' && d.commissioned_at !== null);
      if (wrCharge) {
        hasBattery = true;
        setupNotActivated = false;
        loadFromDevice(wrCharge);
      }
    } catch (err) {
      loadError = isApiError(err) ? err.detail : 'Verbindungsfehler. Bitte Seite neu laden.';
    } finally {
      const elapsed = Date.now() - startTs;
      if (elapsed < 400) {
        await new Promise<void>((resolve) => setTimeout(resolve, 400 - elapsed));
      }
      loading = false;
    }
  });

  function handleMinSocChange(): void {
    savedNotice = null;
    if (minSoc >= 10) {
      lowMinSocPending = false;
      lowMinSocAcknowledged = false;
      lastSafeMinSoc = minSoc;
    } else if (minSoc >= 5) {
      lowMinSocPending = false;
      lowMinSocAcknowledged = false;
    } else {
      // Field constraint < 5 — backend would reject; handleSave surfaces
      // the error inline before making a PATCH request.
      lowMinSocPending = false;
      lowMinSocAcknowledged = false;
    }
  }

  function cancelLowMinSocConfirm(): void {
    minSoc = lastSafeMinSoc;
    lowMinSocPending = false;
    lowMinSocAcknowledged = false;
  }

  async function confirmLowMinSocAndSave(): Promise<void> {
    lowMinSocAcknowledged = true;
    lowMinSocPending = false;
    await handleSave();
  }

  async function handleSave(): Promise<void> {
    if (!hasBattery || gapInvalid || nightWindowEmpty) return;
    saveError = null;
    savedNotice = null;
    if (minSoc < 5) {
      saveError = 'Min-SoC muss mindestens 5 % betragen.';
      return;
    }
    if (minSoc < 10 && !lowMinSocAcknowledged) {
      lowMinSocPending = true;
      return;
    }
    saving = true;
    try {
      const response = await client.patchBatteryConfig({
        min_soc: minSoc,
        max_soc: maxSoc,
        night_discharge_enabled: nightDischargeEnabled,
        night_start: nightStart,
        night_end: nightEnd,
        ...(minSoc < 10 ? { acknowledged_low_min_soc: lowMinSocAcknowledged } : {}),
      });
      minSoc = response.min_soc;
      maxSoc = response.max_soc;
      nightDischargeEnabled = response.night_discharge_enabled;
      nightStart = response.night_start;
      nightEnd = response.night_end;
      lastSafeMinSoc = minSoc >= 10 ? minSoc : lastSafeMinSoc;
      lowMinSocAcknowledged = minSoc >= 5 && minSoc < 10;
      lowMinSocPending = false;
      savedNotice = 'Einstellungen gespeichert.';
    } catch (err) {
      saveError = isApiError(err)
        ? err.detail
        : 'Speichern fehlgeschlagen. Bitte erneut versuchen.';
    } finally {
      saving = false;
    }
  }

  // Konfig-Reset — drops devices + meta.forced_mode + reloads the
  // controller. Inline-Confirm only (UX-DR30 — no modal). Disclaimer-
  // Acceptance bleibt bewusst stehen: Reset wirft die Hardware-Config
  // weg, nicht die rechtliche Zustimmung.
  let resetConfirmOpen = $state(false);
  let resetting = $state(false);
  let resetError = $state<string | null>(null);

  function openResetConfirm(): void {
    resetError = null;
    resetConfirmOpen = true;
  }

  function cancelResetConfirm(): void {
    resetConfirmOpen = false;
  }

  async function confirmReset(): Promise<void> {
    resetting = true;
    resetError = null;
    try {
      await client.resetConfig();
      // Force a full reload so App.svelte re-fetches devices via
      // evaluateGate and lands the user on the welcome screen — a
      // simple hash change would not refresh devicesCache.
      window.location.hash = '#/';
      window.location.reload();
    } catch (err) {
      resetError = isApiError(err)
        ? err.detail
        : 'Zurücksetzen fehlgeschlagen. Bitte erneut versuchen.';
      resetting = false;
    }
  }
</script>

<main class="settings-page">
  <header class="settings-header">
    <p class="eyebrow">Solalex</p>
    <h1>Einstellungen</h1>
  </header>

  {#if loading}
    <div class="skeleton-section" data-testid="settings-skeleton">
      <div class="skeleton-pulse" style="height: 120px;"></div>
      <div class="skeleton-pulse" style="height: 120px; margin-top: 16px;"></div>
    </div>
  {:else if loadError}
    <div class="error-block">
      <p>{loadError}</p>
    </div>
  {:else if allDevices.length > 0}
    <section class="settings-section" data-testid="hardware-card">
      <h2>Hardware-Konfiguration</h2>
      <ul class="hardware-list">
        {#each allDevices as device (device.id)}
          <li class="hardware-row">
            <span class="hardware-role">{describeRole(device.role)}</span>
            <span class="hardware-meta">
              <span class="hardware-type">
                {HARDWARE_TYPE_LABELS[device.adapter_key] ?? device.adapter_key}
              </span>
              <span class="hardware-entity">{device.entity_id}</span>
              {#if device.role === 'grid_meter' && gridMeterInvertSign}
                <span class="hardware-tag" data-testid="invert-sign-tag">
                  Vorzeichen invertiert
                </span>
              {/if}
              {#if device.commissioned_at === null}
                <span class="hardware-tag warn" data-testid="not-commissioned-tag">
                  Funktionstest erforderlich
                </span>
              {/if}
            </span>
          </li>
        {/each}
      </ul>
      <div class="confirm-actions" style="margin-top: 12px;">
        <button
          type="button"
          class="ghost-button"
          onclick={navigateToHardwareEdit}
          data-testid="hardware-edit-button"
        >
          Hardware ändern
        </button>
      </div>
    </section>
  {/if}

  {#if !loading && !loadError}
    {#if setupNotActivated}
    <section class="settings-section" data-testid="not-activated-hint">
      <h2>Noch nicht aktiviert</h2>
      <p class="hint">
        Diese versteckte Seite ist erst nach der Inbetriebnahme vollständig nutzbar.
        Schließe den Setup-Wizard ab, danach kannst du hier Akku-Grenzen und Nacht-Entladung
        bearbeiten.
      </p>
    </section>
  {:else if !hasBattery}
    <section class="settings-section" data-testid="no-battery-hint">
      <h2>Kein Akku konfiguriert</h2>
      <p class="hint">
        Dieses Setup hat keinen Akku. Min-/Max-SoC und Nacht-Entladung sind hier nicht
        konfigurierbar. Wenn du später einen Akku hinzufügst, nutze den Reset-Button unten und
        durchlaufe den Setup-Wizard erneut.
      </p>
    </section>
  {:else}
    <section class="settings-section">
      <h2>Akku-Konfiguration</h2>
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
              oninput={handleMinSocChange}
              aria-label="Min-SoC"
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
              aria-label="Max-SoC"
            />
            <span class="field-unit">%</span>
          </div>
        </label>
      </div>
      {#if gapInvalid}
        <p class="error-line" data-testid="gap-error">
          Max-SoC muss mehr als 10 % über Min-SoC liegen.
        </p>
      {/if}
      {#if lowMinSocPending}
        <div class="confirm-block" data-testid="low-min-soc-confirm">
          <p class="warn-line">
            Min-SoC unterhalb Herstellerspezifikation (Marstek Venus: empfohlen ≥ 10 %) —
            Akku-Schäden bei wiederholter Tiefentladung möglich.
          </p>
          <div class="confirm-actions">
            <button
              type="button"
              class="ghost-button"
              onclick={cancelLowMinSocConfirm}
              data-testid="low-min-soc-cancel"
            >
              Abbrechen
            </button>
            <button
              type="button"
              class="warn-button"
              onclick={confirmLowMinSocAndSave}
              disabled={saving || gapInvalid || nightWindowEmpty}
              data-testid="low-min-soc-confirm-save"
            >
              Trotzdem speichern
            </button>
          </div>
        </div>
      {/if}
    </section>

    <section class="settings-section">
      <h2>Nacht-Entladung</h2>
      <label class="checkbox-row">
        <input type="checkbox" bind:checked={nightDischargeEnabled} />
        <span>Nacht-Entladung aktivieren</span>
      </label>
      {#if nightDischargeEnabled}
        <div class="field-row" style="margin-top: 12px;">
          <label class="field-label">
            Startzeit
            <input
              type="time"
              bind:value={nightStart}
              class="time-input"
              aria-label="Nacht-Start"
            />
          </label>
          <label class="field-label">
            Endzeit
            <input type="time" bind:value={nightEnd} class="time-input" aria-label="Nacht-Ende" />
          </label>
        </div>
        {#if nightWindowEmpty}
          <p class="error-line" data-testid="night-window-error">
            Start- und Endzeit müssen sich unterscheiden.
          </p>
        {/if}
      {/if}
    </section>

    <div class="save-row">
      <button
        type="button"
        class="save-button"
        onclick={handleSave}
        disabled={!canSave}
        data-testid="settings-save"
      >
        {saving ? 'Speichern…' : 'Speichern'}
      </button>
      {#if saveError}
        <p class="error-line" data-testid="save-error">{saveError}</p>
      {/if}
      {#if savedNotice}
        <p class="confirm-line" data-testid="save-confirm">{savedNotice}</p>
      {/if}
    </div>
  {/if}
  {/if}

  {#if !loading && !loadError}
    <section class="settings-section danger-section" data-testid="reset-section">
      <h2>Konfiguration zurücksetzen</h2>
      <p class="hint">
        Löscht alle eingerichteten Geräte (Wechselrichter, Akku, Smart Meter) und alle bisher
        aufgezeichneten Regelzyklen. Danach landest du wieder am Anfang und kannst den Setup-Wizard
        frisch durchlaufen — z.&nbsp;B. um einen neuen Akku einzurichten.
      </p>
      {#if !resetConfirmOpen}
        <div class="confirm-actions">
          <button
            type="button"
            class="warn-button"
            onclick={openResetConfirm}
            data-testid="reset-open"
          >
            Konfiguration zurücksetzen
          </button>
        </div>
      {:else}
        <div class="confirm-block" data-testid="reset-confirm">
          <p class="warn-line">
            Wirklich alle Geräte löschen? Aufgezeichnete Regelzyklen und Latenzmessungen werden mit
            gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.
          </p>
          <div class="confirm-actions">
            <button
              type="button"
              class="ghost-button"
              onclick={cancelResetConfirm}
              disabled={resetting}
              data-testid="reset-cancel"
            >
              Abbrechen
            </button>
            <button
              type="button"
              class="warn-button"
              onclick={confirmReset}
              disabled={resetting}
              data-testid="reset-confirm-action"
            >
              {resetting ? 'Lösche…' : 'Ja, alles löschen'}
            </button>
          </div>
          {#if resetError}
            <p class="error-line" data-testid="reset-error">{resetError}</p>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</main>

<style>
  .settings-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .settings-header {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .settings-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
  }

  .settings-section {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    padding: var(--space-3);
  }

  .settings-section h2 {
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

  .time-input {
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 0.9rem;
  }

  .field-unit {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
  }

  .hardware-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .hardware-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: var(--color-bg);
  }

  .hardware-role {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-secondary);
  }

  .hardware-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    font-size: 0.92rem;
  }

  .hardware-type {
    font-weight: 600;
  }

  .hardware-entity {
    color: var(--color-text-secondary);
    font-family: monospace;
    font-size: 0.85rem;
  }

  .hardware-tag {
    font-size: 0.78rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-text) 8%, transparent);
    color: var(--color-text-secondary);
  }

  .hardware-tag.warn {
    background: color-mix(in srgb, var(--color-accent-warning) 18%, transparent);
    color: var(--color-accent-warning);
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

  .confirm-block {
    margin-top: var(--space-2);
    padding: var(--space-2);
    border-radius: 10px;
    border: 1px solid color-mix(in srgb, var(--color-accent-warning) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent-warning) 8%, var(--color-bg) 92%);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .warn-line {
    margin: 0;
    color: var(--color-accent-warning);
    font-size: 0.92rem;
    line-height: 1.4;
  }

  .confirm-actions {
    display: flex;
    gap: var(--space-2);
  }

  .ghost-button {
    height: 40px;
    padding: 0 16px;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
    background: transparent;
    color: var(--color-text);
    font-family: var(--font-sans);
    font-weight: 600;
    cursor: pointer;
  }

  .warn-button {
    height: 40px;
    padding: 0 16px;
    border-radius: 8px;
    border: 0;
    background: var(--color-accent-warning);
    color: white;
    font-family: var(--font-sans);
    font-weight: 700;
    cursor: pointer;
  }

  .warn-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
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
    align-self: flex-start;
  }

  .save-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .hint {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-text-secondary);
    line-height: 1.5;
  }

  .error-line {
    margin: var(--space-1) 0 0 0;
    font-size: 0.88rem;
    color: var(--color-accent-warning);
  }

  .confirm-line {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-accent-primary);
  }

  .danger-section {
    border-color: color-mix(in srgb, var(--color-accent-warning) 30%, transparent);
  }
</style>
