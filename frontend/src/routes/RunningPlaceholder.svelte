<script lang="ts">
</script>

<main class="running-page">
  <section class="running-card">
    <p class="eyebrow">Solalex</p>
    <h1>Solalex läuft</h1>
    <p class="running-hint">Dashboard folgt mit Epic 5.</p>
  </section>
</main>

<style>
  .running-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: clamp(20px, 4vw, 40px);
  }

  .running-card {
    width: min(100%, 760px);
    margin: 0 auto;
    border-radius: calc(var(--radius-card) + 4px);
    border: 1px solid color-mix(in srgb, var(--color-accent-primary) 40%, transparent);
    background: color-mix(in srgb, var(--color-surface) 92%, var(--color-bg) 8%);
    box-shadow: var(--shadow-2);
    padding: clamp(20px, 4vw, 40px);
  }

  h1 {
    margin: 0 0 var(--space-2) 0;
    font-size: clamp(1.8rem, 2.6vw, 2.4rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
    color: var(--color-accent-primary);
  }

  .running-hint {
    color: var(--color-text-secondary);
    margin: 0;
  }
</style>
