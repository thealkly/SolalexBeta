<script lang="ts">
  let checked = $state(false);

  function handleContinue(): void {
    // localStorage can throw SecurityError in sandboxed iframes or
    // QuotaExceededError when storage is full. Always navigate so the user is
    // never stuck on the disclaimer page; the App-level gate will re-prompt on
    // the next load if persistence actually failed.
    try {
      localStorage.setItem('solalex_pre_disclaimer_accepted', '1');
    } catch (err) {
      console.warn('Could not persist pre-disclaimer acceptance', err);
    }
    window.location.hash = '#/config';
  }
</script>

<main class="pre-disclaimer-page">
  <header class="pre-disclaimer-header">
    <p class="eyebrow">Solalex Setup</p>
    <h1>Bevor es losgeht</h1>
  </header>

  <section class="pre-disclaimer-card">
    <div id="pre-disclaimer-text" class="pre-disclaimer-text">
      <p>
        Solalex steuert deine PV-/Akku-/Verbraucherlogik über Home Assistant. Bitte aktiviere
        Solalex nur, wenn deine Anlage fachgerecht installiert ist und du sicher bist, dass die
        gewählten Entitäten, Grenzwerte und Geräte korrekt sind.
      </p>
      <p>
        Solalex ersetzt keine Elektrofachkraft, keine Anlagenprüfung und keinen Netzschutz. Die
        App darf nicht für sicherheitskritische Funktionen verwendet werden. Falsche Einstellungen,
        fehlerhafte Sensorwerte, instabile Verbindungen oder parallele Automationen können zu
        unerwünschtem Verhalten führen.
      </p>
      <p>
        Ich bestätige, dass ich für Installation, Konfiguration und Betrieb meiner Anlage selbst
        verantwortlich bin und Solalex nur innerhalb der zulässigen technischen und rechtlichen
        Grenzen verwende.
      </p>
    </div>

    <label class="checkbox-row">
      <input type="checkbox" bind:checked aria-describedby="pre-disclaimer-text" />
      <span
        >Ich habe die Sicherheitshinweise gelesen und verstanden. Ich bin für die korrekte
        Installation, Konfiguration und den sicheren Betrieb meiner Anlage selbst verantwortlich.</span
      >
    </label>

    {#if checked}
      <button type="button" class="continue-button" onclick={handleContinue}>Weiter</button>
    {/if}
  </section>
</main>

<style>
  .pre-disclaimer-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background: radial-gradient(circle at 50% 0%, rgb(0 214 180 / 8%), transparent 36%),
      var(--color-bg);
    color: var(--color-text);
  }

  .pre-disclaimer-header {
    width: min(100%, 640px);
    margin: 0 auto;
  }

  .pre-disclaimer-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .pre-disclaimer-card {
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

  .pre-disclaimer-text {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .pre-disclaimer-text p {
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

  .continue-button {
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

  .continue-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 32px color-mix(in srgb, var(--color-accent-primary) 56%, transparent);
  }
</style>
