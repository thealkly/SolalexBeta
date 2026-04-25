<script lang="ts">
  const exportUrl = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api/v1/diagnostics/export`;
  let exportInFlight = $state(false);

  function exportDiagnostics(): void {
    if (exportInFlight) return;
    exportInFlight = true;
    window.location.assign(exportUrl);
    // Re-enable after a short cooldown — no fetch state to track since browser owns the download.
    setTimeout(() => {
      exportInFlight = false;
    }, 3000);
  }
</script>

<main class="diagnostics-page">
  <header class="diagnostics-header">
    <h1>Diagnose-Schnellexport</h1>
    <p>
      Versteckte Forensik-Route. Lädt einen rohen Schnappschuss (DB + Logs) als ZIP
      herunter. Für vollständige Bug-Reports wartet bitte auf den Diagnose-Tab.
    </p>
  </header>

  <button
    type="button"
    class="export-button"
    disabled={exportInFlight}
    onclick={exportDiagnostics}
  >
    Diagnose exportieren
  </button>
</main>

<style>
  .diagnostics-page {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: clamp(20px, 4vw, 40px);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .diagnostics-header,
  .export-button {
    width: min(100%, 760px);
    margin: 0 auto;
  }

  .diagnostics-header h1 {
    margin: 0;
    font-size: clamp(1.6rem, 2.4vw, 2.2rem);
    line-height: 1.1;
  }

  .diagnostics-header p {
    margin: var(--space-2) 0 0 0;
    max-width: 62ch;
    color: var(--color-text-secondary);
    font-size: 0.95rem;
    line-height: 1.55;
  }

  .export-button {
    min-height: 44px;
    border: 0;
    border-radius: 8px;
    background: var(--color-accent-primary);
    color: white;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .export-button:hover {
    filter: brightness(0.95);
  }

  .export-button:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
</style>
