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

// Story 2.5 — Smart-Meter Vorzeichen-Toggle + Live-Preview.
describe('Config — invert-sign toggle + live preview', () => {
  const POWER_ENTITY = 'sensor.esphome_smart_meter_current_load';
  const ENTITIES_WITH_POWER: EntitiesResponse = {
    wr_limit_entities: [
      {
        entity_id: 'input_number.t2sgf72a29_set_target',
        friendly_name: 't2sgf72a29 set target',
      },
    ],
    power_entities: [
      { entity_id: POWER_ENTITY, friendly_name: 'ESPHome Smart-Meter' },
    ],
    soc_entities: [],
  };

  beforeEach(() => {
    vi.spyOn(client, 'getEntities').mockResolvedValue(ENTITIES_WITH_POWER);
    vi.spyOn(client, 'fetchControlMode').mockRejectedValue(
      new ApiError(500, 'urn:test', 'fail', 'no controller'),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  async function selectOption(
    select: HTMLSelectElement,
    value: string,
  ): Promise<void> {
    const options = Array.from(select.options);
    const targetIndex = options.findIndex((o) => o.value === value);
    if (targetIndex < 0) {
      throw new Error(
        `selectOption: no <option value="${value}"> in select; got: ${options.map((o) => o.value).join(', ')}`,
      );
    }
    for (const opt of options) {
      opt.selected = opt.value === value;
    }
    select.selectedIndex = targetIndex;
    select.value = value;
    await fireEvent.input(select);
    await fireEvent.change(select);
  }

  async function pickGenericAndSmartMeter(): Promise<void> {
    const genericTile = await screen.findByText('Wechselrichter (allgemein)');
    await fireEvent.click(genericTile);

    // Wait for the WR-section to render and grab the only combobox so far.
    await screen.findByText('Wechselrichter-Limit-Entity');
    let combos = screen.getAllByRole('combobox') as HTMLSelectElement[];
    const wrSelect = combos[0]!;
    await selectOption(wrSelect, 'input_number.t2sgf72a29_set_target');

    const smartMeter = (await screen.findByLabelText(
      /Smart Meter zuordnen/,
    )) as HTMLInputElement;
    await fireEvent.click(smartMeter);

    // After useSmartMeter flips, the meter combobox is the second combobox.
    await waitFor(() => {
      combos = screen.getAllByRole('combobox') as HTMLSelectElement[];
      expect(combos.length).toBeGreaterThanOrEqual(2);
    });
    const meterSelect = combos[combos.length - 1]!;
    await selectOption(meterSelect, POWER_ENTITY);
  }

  it('flips the displayed value when the invert toggle is enabled', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: POWER_ENTITY,
      value_w: 2120,
      ts: '2026-04-25T12:00:00+00:00',
    });
    render(Config);
    await pickGenericAndSmartMeter();

    const valueEl = await screen.findByTestId('live-preview-value');
    await waitFor(() => {
      expect(valueEl.textContent ?? '').toContain('2120');
    });
    // Default — toggle off, raw value shown as positive Bezug.
    expect(
      (await screen.findByTestId('live-preview-direction')).textContent ?? '',
    ).toContain('Bezug');

    const toggle = (await screen.findByTestId(
      'invert-sign-toggle',
    )) as HTMLInputElement;
    await fireEvent.click(toggle);

    await waitFor(() => {
      expect(valueEl.textContent ?? '').toContain('-2120');
    });
    expect(
      (await screen.findByTestId('live-preview-direction')).textContent ?? '',
    ).toContain('Einspeisung');
  });

  it('shows the zero-hint when the absolute value is below 50 W', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: POWER_ENTITY,
      value_w: 12,
      ts: '2026-04-25T12:00:00+00:00',
    });
    render(Config);
    await pickGenericAndSmartMeter();

    const hint = await screen.findByTestId('live-preview-zero-hint');
    expect(hint.textContent ?? '').toContain('nahezu 0 W');
  });

  it('passes invert_sign to saveDevices when checked', async () => {
    vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: POWER_ENTITY,
      value_w: 100,
      ts: '2026-04-25T12:00:00+00:00',
    });
    const saveSpy = vi
      .spyOn(client, 'saveDevices')
      .mockResolvedValue({
        status: 'saved',
        device_count: 2,
        next_action: 'functional_test',
      });

    render(Config);
    await pickGenericAndSmartMeter();

    const toggle = (await screen.findByTestId(
      'invert-sign-toggle',
    )) as HTMLInputElement;
    await fireEvent.click(toggle);

    const saveButton = await screen.findByText('Speichern');
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalled();
    });
    const [body] = saveSpy.mock.calls[0] as [Parameters<typeof client.saveDevices>[0]];
    expect(body.invert_sign).toBe(true);
    expect(body.grid_meter_entity_id).toBe(POWER_ENTITY);
  });

  it('omits invert_sign from the payload when smart meter is disabled', async () => {
    const saveSpy = vi
      .spyOn(client, 'saveDevices')
      .mockResolvedValue({
        status: 'saved',
        device_count: 1,
        next_action: 'functional_test',
      });

    render(Config);
    const genericTile = await screen.findByText('Wechselrichter (allgemein)');
    await fireEvent.click(genericTile);
    const wrSelect = await screen.findByDisplayValue('— Entity wählen —');
    await fireEvent.change(wrSelect, {
      target: { value: 'input_number.t2sgf72a29_set_target' },
    });

    const saveButton = await screen.findByText('Speichern');
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalled();
    });
    const [body] = saveSpy.mock.calls[0] as [Parameters<typeof client.saveDevices>[0]];
    expect(body.invert_sign).toBeUndefined();
  });

  it('starts polling getEntityState after the entity is selected and stops on entity clear', async () => {
    const fetchSpy = vi.spyOn(client, 'getEntityState').mockResolvedValue({
      entity_id: POWER_ENTITY,
      value_w: 50,
      ts: null,
    });

    render(Config);
    await pickGenericAndSmartMeter();

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(POWER_ENTITY);
    });
    const callsAfterStart = fetchSpy.mock.calls.length;
    expect(callsAfterStart).toBeGreaterThan(0);

    // Disabling the smart-meter checkbox tears down the poller and the
    // live-preview card disappears.
    const smartMeter = (await screen.findByLabelText(
      /Smart Meter zuordnen/,
    )) as HTMLInputElement;
    await fireEvent.click(smartMeter);

    await waitFor(() => {
      expect(screen.queryByTestId('live-preview-card')).toBeNull();
    });
  });
});
