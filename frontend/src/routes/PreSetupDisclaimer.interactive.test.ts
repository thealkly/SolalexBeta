// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import PreSetupDisclaimer from './PreSetupDisclaimer.svelte';

// Cover AC 4 (no disabled attribute in checked state), AC 5 (button appears
// after check and routes to #/config) and AC 6 (localStorage is written on
// continue). These cases cannot be expressed in SSR rendering because the
// flow depends on checkbox state and click handlers.

describe('PreSetupDisclaimer — interactive flow', () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = '';
  });

  afterEach(() => {
    // @testing-library/svelte registers auto-cleanup only when vitest runs
    // with `globals: true`. We run with `globals: false`, so call cleanup
    // explicitly to tear down each rendered component between tests.
    cleanup();
    localStorage.clear();
    window.location.hash = '';
  });

  it('shows no continue button until the checkbox is checked', () => {
    render(PreSetupDisclaimer);
    expect(screen.queryByRole('button', { name: /weiter/i })).toBeNull();
  });

  it('renders the continue button without a disabled attribute after check (AC 4)', async () => {
    render(PreSetupDisclaimer);
    const checkbox = screen.getByRole('checkbox');
    await fireEvent.click(checkbox);
    const button = await screen.findByRole('button', { name: /weiter/i });
    expect(button.hasAttribute('disabled')).toBe(false);
  });

  it('sets localStorage and routes to #/config when continue is clicked (AC 5, 6)', async () => {
    render(PreSetupDisclaimer);
    const checkbox = screen.getByRole('checkbox');
    await fireEvent.click(checkbox);
    const button = await screen.findByRole('button', { name: /weiter/i });
    await fireEvent.click(button);
    expect(localStorage.getItem('solalex_pre_disclaimer_accepted')).toBe('1');
    expect(window.location.hash).toBe('#/config');
  });

  it('still navigates when localStorage.setItem throws (sandboxed iframe / quota)', async () => {
    const originalSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new DOMException('storage blocked', 'SecurityError');
    };
    try {
      render(PreSetupDisclaimer);
      const checkbox = screen.getByRole('checkbox');
      await fireEvent.click(checkbox);
      const button = await screen.findByRole('button', { name: /weiter/i });
      await fireEvent.click(button);
      // handleContinue swallows the throw and navigates anyway so the user is
      // never stuck on the disclaimer page. Next-load gate re-prompts.
      expect(window.location.hash).toBe('#/config');
    } finally {
      Storage.prototype.setItem = originalSetItem;
    }
  });
});
