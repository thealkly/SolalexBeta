<script lang="ts">
  import { onMount } from 'svelte';
  import avatarUrl from '../static/avatar-alex.png';
  import Config from './routes/Config.svelte';
  import DisclaimerActivation from './routes/DisclaimerActivation.svelte';
  import FunctionalTest from './routes/FunctionalTest.svelte';
  import PreSetupDisclaimer from './routes/PreSetupDisclaimer.svelte';
  import Running from './routes/Running.svelte';
  import * as client from './lib/api/client.js';
  import type { DeviceResponse } from './lib/api/types.js';
  import { evaluateGate } from './lib/gate.js';

  let backendStatus = $state<'unknown' | 'ok' | 'error'>('unknown');
  let currentRoute = $state('/');
  let devicesCache = $state<DeviceResponse[] | null>(null);

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

  const VALID_ROUTES = new Set([
    '/',
    '/config',
    '/functional-test',
    '/running',
    '/disclaimer',
    '/activate',
  ]);

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

  function readPreAccepted(): boolean {
    // localStorage can throw SecurityError in sandboxed iframes or when
    // site-storage is blocked (Firefox private mode). Treat any throw as
    // "not accepted" — the user will be re-prompted, which is the safe
    // default for a legal gate.
    try {
      return localStorage.getItem('solalex_pre_disclaimer_accepted') === '1';
    } catch {
      return false;
    }
  }

  // Gate evaluator — runs on initial device-fetch AND on every hashchange so
  // direct URL edits (e.g., user types `#/config` into the address bar after
  // mount) cannot bypass the pre-disclaimer / commissioned redirects. (Story
  // 2.3a AC 7.)
  function guardCurrentRoute(allowAutoForward: boolean): void {
    const decision = evaluateGate({
      currentRoute,
      devices: devicesCache,
      preAccepted: readPreAccepted(),
      allowAutoForward,
    });
    if (decision.kind === 'redirect') {
      window.location.hash = decision.hash;
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
        devicesCache = devices;
        guardCurrentRoute(true);
      } catch {
        // Backend unreachable — surface via the status chip and suppress the
        // "Setup starten" welcome card (see main-template backendStatus check)
        // so the user can't click into a wizard the backend cannot serve.
        // The ping retry loop below keeps trying; the user recovers when the
        // backend comes back up. Review Finding P12.
        if (ac.signal.aborted) return;
        backendStatus = 'error';
      }
    })();

    const handleHashChange = () => {
      syncRoute();
      guardCurrentRoute(false);
    };
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
    <PreSetupDisclaimer />
  {:else if currentRoute === '/activate'}
    <DisclaimerActivation />
  {:else if currentRoute === '/running'}
    <Running />
  {:else}
    <section class="empty-state-card">
      <header class="empty-state-header">
        <p class="eyebrow">Solalex</p>
        <h1>Willkommen bei Solalex</h1>
        {#if backendStatus === 'error'}
          <p class="intro">
            Das Backend ist aktuell nicht erreichbar. Bitte prüfe die Add-on-Logs und starte das
            Add-on ggf. neu. Sobald die Verbindung wieder steht, geht es hier weiter.
          </p>
        {:else}
          <p class="intro">
            Du bist startklar. Richte jetzt in wenigen Schritten dein Setup ein und starte mit
            lokaler Energie-Steuerung.
          </p>
        {/if}
      </header>

      <div class="cta-row">
        {#if backendStatus !== 'error'}
          <a class="setup-button" href="#/config">Setup starten</a>
        {/if}
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
