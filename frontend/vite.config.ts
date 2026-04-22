import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

// HA Ingress serves the SPA under an unpredictable path — use relative asset
// URLs so the bundle works regardless of the mount prefix.
export default defineConfig({
  base: './',
  plugins: [svelte(), tailwindcss()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    target: 'es2022',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8099',
    },
  },
});
