<script lang="ts">
  import { onMount } from 'svelte';

  let backendStatus = $state<'unknown' | 'ok' | 'error'>('unknown');
  let currentRoute = $state('/');
  let isDarkTheme = $state(false);

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

  function syncRoute(): void {
    currentRoute = normalizeRoute(window.location.hash);
    if (currentRoute !== '/' && currentRoute !== '/wizard') {
      window.location.hash = '#/';
    }
  }

  function resolveThemeMode(): 'dark' | 'light' {
    const html = document.documentElement;
    const body = document.body;
    const htmlTheme = html.getAttribute('data-theme');
    const bodyTheme = body.getAttribute('data-theme');

    if (htmlTheme === 'dark' || bodyTheme === 'dark') {
      return 'dark';
    }

    if (htmlTheme === 'light' || bodyTheme === 'light') {
      return 'light';
    }

    const classHint = `${html.className} ${body.className}`.toLowerCase();
    if (/(^| )dark( |$)/.test(classHint)) {
      return 'dark';
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(): void {
    const mode = resolveThemeMode();
    isDarkTheme = mode === 'dark';
    if (document.documentElement.getAttribute('data-theme') === mode) return;
    document.documentElement.setAttribute('data-theme', mode);
  }

  async function ping(): Promise<void> {
    try {
      const res = await fetch(healthUrl);
      backendStatus = res.ok ? 'ok' : 'error';
    } catch {
      backendStatus = 'error';
    }
  }

  onMount(() => {
    ensureDefaultRoute();
    syncRoute();
    applyTheme();
    void ping();

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleMediaChange = () => applyTheme();
    const handleHashChange = () => syncRoute();
    const observer = new MutationObserver(() => applyTheme());

    window.addEventListener('hashchange', handleHashChange);
    mediaQuery.addEventListener('change', handleMediaChange);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
    observer.observe(document.body, { attributes: true, attributeFilter: ['data-theme', 'class'] });

    let pingAttempts = 0;
    const pingRetryInterval = setInterval(async () => {
      if (backendStatus === 'ok' || pingAttempts >= 3) {
        clearInterval(pingRetryInterval);
        return;
      }
      pingAttempts++;
      await ping();
    }, 5000);

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      mediaQuery.removeEventListener('change', handleMediaChange);
      observer.disconnect();
      clearInterval(pingRetryInterval);
    };
  });
</script>

<main class="app-shell" data-route={currentRoute}>
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
      <a class="setup-button" href="#/wizard">Setup starten</a>
      <div class="meta">
        <span class="status-label">Backend:</span>
        <span class="status-value" data-state={backendStatus}>{statusLabels[backendStatus]}</span>
      </div>
    </div>
  </section>

  <footer class="app-footer">
    <div class="brand">
      <span class="avatar" aria-hidden="true">AK</span>
      <span>Made by Alex Kly</span>
    </div>

    <nav class="footer-links" aria-label="Weiterfuehrende Links">
      <a href="https://alkly.de/discord/" target="_blank" rel="noreferrer">Discord</a>
      <a href="https://alkly.de" target="_blank" rel="noreferrer">Alkly</a>
      <a href="https://alkly.de/macherwerkstatt/" target="_blank" rel="noreferrer">Macherwerkstatt</a>
    </nav>

    <span class="status-chip local-badge">100 % lokal</span>
  </footer>
</main>
