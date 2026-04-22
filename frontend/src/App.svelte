<script lang="ts">
  // Minimal hello shell for Story 1.1. Branding, design system, wizard
  // routing all land in later stories (1.4–1.6, Epic 2).
  let backendStatus = $state<'unknown' | 'ok' | 'error'>('unknown');

  async function ping() {
    try {
      const res = await fetch('./api/health');
      backendStatus = res.ok ? 'ok' : 'error';
    } catch {
      backendStatus = 'error';
    }
  }

  $effect(() => {
    ping();
  });
</script>

<main class="flex min-h-screen items-center justify-center bg-slate-50 p-8">
  <div class="max-w-md text-center">
    <h1 class="text-3xl font-bold text-slate-900">Solalex</h1>
    <p class="mt-2 text-slate-600">
      Add-on-Skeleton läuft. Setup-Wizard folgt in Epic 2.
    </p>
    <p class="mt-6 text-sm text-slate-500">
      Backend:
      <span
        class:text-emerald-600={backendStatus === 'ok'}
        class:text-rose-600={backendStatus === 'error'}
        class:text-slate-400={backendStatus === 'unknown'}
      >
        {backendStatus}
      </span>
    </p>
  </div>
</main>
