// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import Diagnostics from './Diagnostics.svelte';

describe('Diagnostics route', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders header and exactly one export button', () => {
    render(Diagnostics);

    expect(screen.getByRole('heading', { name: 'Diagnose-Schnellexport' })).toBeTruthy();
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Diagnose exportieren' })).toBeTruthy();
  });

  it('button click navigates to the export endpoint', async () => {
    const assign = vi.spyOn(window.location, 'assign').mockImplementation(() => undefined);

    render(Diagnostics);
    await fireEvent.click(screen.getByRole('button', { name: 'Diagnose exportieren' }));

    expect(assign).toHaveBeenCalledTimes(1);
    const target = String(assign.mock.calls[0][0]);
    expect(target).toMatch(/\/api\/v1\/diagnostics\/export$/);
    expect(target).toBe(`${import.meta.env.BASE_URL.replace(/\/$/, '')}/api/v1/diagnostics/export`);
  });
});
