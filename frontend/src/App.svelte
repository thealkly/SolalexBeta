<script lang="ts">
  import { onMount } from 'svelte';
  import avatarUrl from '../static/avatar-alex.png';
  import Config from './routes/Config.svelte';
  import DisclaimerActivation from './routes/DisclaimerActivation.svelte';
  import FunctionalTest from './routes/FunctionalTest.svelte';
  import RunningPlaceholder from './routes/RunningPlaceholder.svelte';
  import * as client from './lib/api/client.js';

  let backendStatus = $state<'unknown' | 'ok' | 'error'>('unknown');
  let currentRoute = $state('/');

  const healthUrl = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api/health`;

  const statusLabels: Record<'unknown' | 'ok' | 'error', string> = {
    unknown: 'unbekannt',
    ok: 'verbunden',
    error: 'Fehler',
  };

  function normalizeRoute(hash: string): string {
    const route = hash.replace(/^#/, '').trim();
    if (route === '' || route === '/') {
      return '/';
    }
    return route.startsWith('/') ? route : `/${route}`;
  }

  function ensureDefaultRoute(): void {
    if (!window.location.hash) {
      window.location.hash = '#/';
    }
  }

  const VALID_ROUTES = new Set(['/', '/config', '/functional-test', '/running', '/disclaimer']);

  function syncRoute(): void {
    currentRoute = normalizeRoute(window.location.hash);
    if (!VALID_ROUTES.has(currentRoute)) {
      window.location.hash = '#/';
    }
  }

  async function ping(signal?: AbortSignal): Promise<void> {
    try {
      const res = await fetch(healthUrl, { signal });
      if (signal?.aborted) return;
      backendStatus = res.ok ? 'ok' : 'error';
    } catch (err) {
      if ((err as { name?: string })?.name === 'AbortError') return;
      backendStatus = 'error';
    }
  }

  onMount(() => {
    const ac = new AbortController();

    ensureDefaultRoute();
    syncRoute();
    void ping(ac.signal);

    void (async () => {
      try {
        const devices = await client.getDevices();
        if (ac.signal.aborted) return;
        if (devices.length === 0) return;
        const allCommissioned = devices.every((d) => d.commissioned_at !== null);
        if (allCommissioned) {
          window.location.hash = '#/running';
        } else if (currentRoute === '/') {
          window.location.hash = '#/functional-test';
        }
      } catch {
        // Backend not yet ready — stay on current route
      }
    })();

    const handleHashChange = () => syncRoute();
    window.addEventListener('hashchange', handleHashChange);

    let pingAttempts = 0;
    const pingRetryInterval = setInterval(async () => {
      if (backendStatus === 'ok' || pingAttempts >= 3) {
        clearInterval(pingRetryInterval);
        return;
      }
      pingAttempts++;
      await ping(ac.signal);
    }, 5000);

    return () => {
      ac.abort();
      window.removeEventListener('hashchange', handleHashChange);
      clearInterval(pingRetryInterval);
    };
  });
</script>

<main class="app-shell" data-route={currentRoute}>
  {#if currentRoute === '/config'}
    <Config />
  {:else if currentRoute === '/functional-test'}
    <FunctionalTest />
  {:else if currentRoute === '/disclaimer'}
    <DisclaimerActivation />
  {:else if currentRoute === '/running'}
    <RunningPlaceholder />
  {:else}
    <section class="empty-state-card">
      <header class="empty-state-header">
        <p class="eyebrow">Solalex</p>
        <h1>Willkommen bei Solalex</h1>
        <p class="intro">
          Du bist startklar. Richte jetzt in wenigen Schritten deinen Setup-Wizard ein und starte mit lokaler
          Energie-Steuerung.
        </p>
      </header>

      <div class="cta-row">
        <a class="setup-button" href="#/config">Setup starten</a>
        <div class="meta">
          <span class="status-label">Backend:</span>
          <span class="status-value" data-state={backendStatus}>{statusLabels[backendStatus]}</span>
        </div>
      </div>
    </section>

    <footer class="app-footer">
      <div class="brand">
        <img src={avatarUrl} alt="Alex Kly" class="avatar" />
        <span>Made by Alex Kly</span>
      </div>

      <nav class="footer-links" aria-label="Weiterfuehrende Links">
        <a href="https://alkly.de/discord/" target="_blank" rel="noreferrer">Discord</a>
        <a href="https://github.com/alkly/solalex" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://alkly.de/datenschutz/" target="_blank" rel="noreferrer">Datenschutz</a>
      </nav>

      <span class="status-chip local-badge">100 % lokal</span>
    </footer>
  {/if}
</main>
