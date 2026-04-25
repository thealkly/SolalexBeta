// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Config from './Config.svelte';
import * as client from '../lib/api/client.js';
import { ApiError } from '../lib/api/errors.js';
import type {
  ControlModeResponse,
  EntitiesResponse,
  ForcedMode,
} from '../lib/api/types.js';

// Story 3.5 — Config-Seite Override-UI tests.
//
// We mock the API client at the module boundary instead of stubbing fetch.
// The component imports `* as client`, so vi.spyOn on the named exports is
// the cleanest seam without touching network code.

const EMPTY_ENTITIES: EntitiesResponse = {
  wr_limit_entities: [],
  power_entities: [],
  soc_entities: [],
};

function modeResponse(overrides: Partial<ControlModeResponse> = {}): ControlModeResponse {
  return {
    forced_mode: null,
    active_mode: 'speicher',
    baseline_mode: 'speicher',
    ...overrides,
  };
}

describe('Config — mode-override section', () => {
  beforeEach(() => {
    vi.spyOn(client, 'getEntities').mockResolvedValue(EMPTY_ENTITIES);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders the mode-override radio group when fetchControlMode succeeds', async () => {
    vi.spyOn(client, 'fetchControlMode').mockResolvedValue(modeResponse());
    render(Config);
    const section = await screen.findByTestId('mode-override-section');
    expect(section).toBeTruthy();
    expect(screen.getByLabelText('Automatisch (empfohlen)')).toBeTruthy();
    expect(screen.getByLabelText('Drossel')).toBeTruthy();
    expect(screen.getByLabelText('Speicher')).toBeTruthy();
    expect(screen.getByLabelText('Multi')).toBeTruthy();
  });

  it('hides the override section when fetchControlMode throws', async () => {
    vi.spyOn(client, 'fetchControlMode').mockRejectedValue(
      new ApiError(500, 'urn:test', 'fail', 'no controller'),
    );
    render(Config);
    // Wait for the entities fetch to settle so the skeleton is gone.
    await screen.findByText(/Hardware-Typ/i);
    expect(screen.queryByTestId('mode-override-section')).toBeNull();
  });

  it('calls setForcedMode and updates the baseline-hint when a non-auto radio is picked', async () => {
    vi.spyOn(client, 'fetchControlMode').mockResolvedValue(modeResponse());
    const setForcedMode = vi
      .spyOn(client, 'setForcedMode')
      .mockResolvedValue(
        modeResponse({ forced_mode: 'drossel', active_mode: 'drossel' }),
      );
    render(Config);
    const drossel = (await screen.findByLabelText('Drossel')) as HTMLInputElement;
    await fireEvent.click(drossel);
    await waitFor(() => {
      expect(setForcedMode).toHaveBeenCalledWith<['drossel']>('drossel');
    });
    const hint = await screen.findByTestId('mode-baseline-hint');
    expect(hint.textContent ?? '').toContain('drossel');
    expect(hint.textContent ?? '').toContain('speicher');
  });

  it('reverts the radio selection when setForcedMode rejects', async () => {
    vi.spyOn(client, 'fetchControlMode').mockResolvedValue(
      modeResponse({ forced_mode: 'drossel', active_mode: 'drossel' }),
    );
    vi.spyOn(client, 'setForcedMode').mockRejectedValue(
      new ApiError(500, 'urn:test', 'fail', 'backend down'),
    );
    render(Config);
    const auto = (await screen.findByLabelText('Automatisch (empfohlen)')) as HTMLInputElement;
    expect(auto.checked).toBe(false);
    const drossel = (await screen.findByLabelText('Drossel')) as HTMLInputElement;
    expect(drossel.checked).toBe(true);

    await fireEvent.click(auto);
    const errorLine = await screen.findByTestId('mode-override-error');
    expect(errorLine.textContent ?? '').toContain('backend down');
    // Reverted: drossel still checked, auto still unchecked.
    const drosselAfter = screen.getByLabelText('Drossel') as HTMLInputElement;
    const autoAfter = screen.getByLabelText('Automatisch (empfohlen)') as HTMLInputElement;
    expect(drosselAfter.checked).toBe(true);
    expect(autoAfter.checked).toBe(false);
  });

  it('shows the baseline hint with the auto-detected mode when override is active', async () => {
    vi.spyOn(client, 'fetchControlMode').mockResolvedValue(
      modeResponse({
        forced_mode: 'multi' as ForcedMode,
        active_mode: 'multi',
        baseline_mode: 'speicher',
      }),
    );
    render(Config);
    const hint = await screen.findByTestId('mode-baseline-hint');
    expect(hint.textContent ?? '').toContain('multi');
    expect(hint.textContent ?? '').toContain('speicher');
  });
});
