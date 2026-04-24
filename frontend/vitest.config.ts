import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

// happy-dom is opt-in per test file via `// @vitest-environment happy-dom` so
// SSR-only specs (`svelte/server` rendering) stay on the default `node`
// environment and interactive specs get a DOM + browser globals like
// `localStorage` and `window.location`.
//
// `resolve.conditions = ['browser']` forces Svelte 5 to resolve its main
// export to the client runtime (needed by `@testing-library/svelte` → `mount`).
// SSR tests still work because they import `svelte/server` explicitly, which
// has its own subpath export unaffected by this condition.
export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      conditions: ['browser'],
    },
    test: {
      environment: 'node',
      globals: false,
      include: ['src/**/*.test.ts'],
    },
  }),
);
