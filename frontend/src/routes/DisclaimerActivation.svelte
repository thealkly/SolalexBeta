<script lang="ts">
  import * as client from '../lib/api/client.js';
  import { isApiError } from '../lib/api/errors.js';

  let checked = $state(false);
  let committing = $state(false);
  let errorMessage = $state('');

  async function commission(): Promise<void> {
    if (committing) return;
    committing = true;
    errorMessage = '';
    try {
      await client.commission();
      window.location.hash = '#/running';
    } catch (err) {
      errorMessage = isApiError(err) ? err.detail : 'Aktivierung fehlgeschlagen.';
      committing = false;
    }
  }
</script>

<main class="disclaimer-page">
  <header class="disclaimer-header">
    <p class="eyebrow">Solalex Setup</p>
    <h1>Bevor es losgeht</h1>
  </header>

  <section class="disclaimer-card">
    <p class="disclaimer-text">
      Solalex steuert deine Solaranlage aktiv und sekundengenau. Du bist verantwortlich dafür,
      dass die konfigurierten Entities deiner Hardware entsprechen. Fehlfunktionen durch falsche
      Entity-Zuweisung oder inkompatible Firmware können nicht durch Solalex verhindert werden.
    </p>

    <label class="checkbox-row">
      <input type="checkbox" bind:checked />
      <span>Ich habe den Hinweis gelesen und übernehme die Verantwortung für meine Anlage.</span>
    </label>

    {#if checked}
      <button class="activate-button" onclick={commission}>
        {committing ? 'Wird aktiviert …' : 'Aktivieren'}
      </button>
    {/if}

    {#if errorMessage}
      <p class="error-line">{errorMessage}</p>
    {/if}
  </section>

  {#if !committing}
    <a href="#/functional-test" class="back-link">← Zurück zum Funktionstest</a>
  {/if}
</main>

<style>
  .disclaimer-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background: radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%),
      var(--color-bg);
    color: var(--color-text);
  }

  .disclaimer-header {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .disclaimer-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .disclaimer-card {
    width: min(100%, 640px);
    margin: 0 auto;
    border-radius: var(--radius-card);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, var(--color-bg) 4%);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .disclaimer-text {
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.6;
    color: var(--color-text-secondary);
  }

  .checkbox-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    cursor: pointer;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .checkbox-row input[type='checkbox'] {
    flex-shrink: 0;
    margin-top: 2px;
    width: 16px;
    height: 16px;
    accent-color: var(--color-accent-primary);
    cursor: pointer;
  }

  .activate-button {
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

  .activate-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 32px color-mix(in srgb, var(--color-accent-primary) 56%, transparent);
  }

  .error-line {
    margin: 0;
    font-size: 0.88rem;
    color: var(--color-accent-warning);
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    width: min(100%, 640px);
    margin: 0 auto;
    height: 36px;
    padding: 0 16px;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--color-accent-primary) 40%, transparent);
    color: var(--color-accent-primary);
    text-decoration: none;
    font-size: 0.88rem;
    font-weight: 500;
    width: fit-content;
  }
</style>
