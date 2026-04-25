// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Settings from './Settings.svelte';
import * as client from '../lib/api/client.js';
import { ApiError } from '../lib/api/errors.js';
import type { BatteryConfigResponse, DeviceResponse } from '../lib/api/types.js';

// Story 3.6 — Settings page tests. Mocks live at the API client boundary
// so the route stays responsible for shaping the body and reacting to
// RFC-7807 errors.

function makeWrCharge(configOverrides: Record<string, unknown> = {}): DeviceResponse {
  return {
    id: 1,
    type: 'marstek_venus',
    role: 'wr_charge',
    entity_id: 'number.marstek_charge_power',
    adapter_key: 'marstek_venus',
    config_json: JSON.stringify({
      min_soc: 15,
      max_soc: 95,
      night_discharge_enabled: true,
      night_start: '20:00',
      night_end: '06:00',
      ...configOverrides,
    }),
    last_write_at: null,
    commissioned_at: '2026-04-25T12:00:00Z',
    created_at: '2026-04-25T12:00:00Z',
    updated_at: '2026-04-25T12:00:00Z',
  };
}

function patchResponse(overrides: Partial<BatteryConfigResponse> = {}): BatteryConfigResponse {
  return {
    min_soc: 15,
    max_soc: 95,
    night_discharge_enabled: true,
    night_start: '20:00',
    night_end: '06:00',
    ...overrides,
  };
}

describe('Settings — initial render', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders skeleton then form once devices arrive', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
    render(Settings);
    expect(screen.getByTestId('settings-skeleton')).toBeTruthy();
    await screen.findByLabelText('Min-SoC', {}, { timeout: 2000 });
    // Form rendered → skeleton gone.
    expect(screen.queryByTestId('settings-skeleton')).toBeNull();
  });

  it('renders the no-battery hint for a drossel-only setup', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      {
        id: 1,
        type: 'generic',
        role: 'wr_limit',
        entity_id: 'number.opendtu_limit',
        adapter_key: 'generic',
        config_json: '{}',
        last_write_at: null,
        commissioned_at: '2026-04-25T12:00:00Z',
        created_at: '2026-04-25T12:00:00Z',
        updated_at: '2026-04-25T12:00:00Z',
      },
    ]);
    render(Settings);
    const hint = await screen.findByTestId('no-battery-hint');
    expect(hint.textContent ?? '').toContain('Kein Akku');
    expect(screen.queryByTestId('settings-save')).toBeNull();
  });

  it('renders a not-activated hint for pre-commissioning devices', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      { ...makeWrCharge(), commissioned_at: null },
    ]);
    render(Settings);
    const hint = await screen.findByTestId('not-activated-hint');
    expect(hint.textContent ?? '').toContain('Noch nicht aktiviert');
    expect(screen.queryByTestId('no-battery-hint')).toBeNull();
    expect(screen.queryByTestId('settings-save')).toBeNull();
  });
});

describe('Settings — validation gates', () => {
  beforeEach(() => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('disables save and shows the gap error when min_soc + 10 >= max_soc', async () => {
    render(Settings);
    const min = (await screen.findByLabelText('Min-SoC')) as HTMLInputElement;
    const max = (await screen.findByLabelText('Max-SoC')) as HTMLInputElement;
    // 15+10 == 25 → gap-invalid (UI keeps the user from saving even when
    // the HTML5 number-input range hints would otherwise flag the field).
    await fireEvent.input(min, { target: { value: '15' } });
    await fireEvent.input(max, { target: { value: '25' } });
    const save = screen.getByTestId('settings-save') as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    expect(screen.getByTestId('gap-error')).toBeTruthy();
  });

  it('shows the plausibility confirm on save and then blocks the regular save', async () => {
    render(Settings);
    const min = (await screen.findByLabelText('Min-SoC')) as HTMLInputElement;
    await fireEvent.input(min, { target: { value: '7' } });
    expect(screen.queryByTestId('low-min-soc-confirm')).toBeNull();
    await fireEvent.click(screen.getByTestId('settings-save'));
    const confirm = await screen.findByTestId('low-min-soc-confirm');
    expect(confirm.textContent ?? '').toContain('Herstellerspezifikation');
    const save = screen.getByTestId('settings-save') as HTMLButtonElement;
    expect(save.disabled).toBe(true);
  });

  it('cancel resets min_soc to the last safe value', async () => {
    render(Settings);
    const min = (await screen.findByLabelText('Min-SoC')) as HTMLInputElement;
    await fireEvent.input(min, { target: { value: '7' } });
    await fireEvent.click(screen.getByTestId('settings-save'));
    await screen.findByTestId('low-min-soc-confirm');
    await fireEvent.click(screen.getByTestId('low-min-soc-cancel'));
    await waitFor(() => {
      const after = screen.getByLabelText('Min-SoC') as HTMLInputElement;
      expect(after.value).toBe('15');
    });
    expect(screen.queryByTestId('low-min-soc-confirm')).toBeNull();
  });

  it('hides the night-window inputs when the toggle is off', async () => {
    render(Settings);
    const checkbox = (await screen.findByLabelText(
      'Nacht-Entladung aktivieren',
    )) as HTMLInputElement;
    expect(screen.queryByLabelText('Nacht-Start')).toBeTruthy();
    await fireEvent.click(checkbox);
    expect(screen.queryByLabelText('Nacht-Start')).toBeNull();
    expect(screen.queryByLabelText('Nacht-Ende')).toBeNull();
  });
});

describe('Settings — save flow', () => {
  beforeEach(() => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('calls patchBatteryConfig with the form body and shows the saved confirmation', async () => {
    const patch = vi
      .spyOn(client, 'patchBatteryConfig')
      .mockResolvedValue(patchResponse({ min_soc: 20, max_soc: 90 }));
    render(Settings);
    const min = (await screen.findByLabelText('Min-SoC')) as HTMLInputElement;
    const max = (await screen.findByLabelText('Max-SoC')) as HTMLInputElement;
    await fireEvent.input(min, { target: { value: '20' } });
    await fireEvent.input(max, { target: { value: '90' } });
    await fireEvent.click(screen.getByTestId('settings-save'));
    await waitFor(() => {
      expect(patch).toHaveBeenCalledTimes(1);
    });
    const call = patch.mock.calls[0]?.[0];
    expect(call).toMatchObject({
      min_soc: 20,
      max_soc: 90,
      night_discharge_enabled: true,
      night_start: '20:00',
      night_end: '06:00',
    });
    // Standard save (min_soc >= 10) must not include the ack flag.
    expect(call?.acknowledged_low_min_soc).toBeUndefined();
    await screen.findByTestId('save-confirm');
  });

  it('confirm-then-save sends acknowledged_low_min_soc=true', async () => {
    const patch = vi
      .spyOn(client, 'patchBatteryConfig')
      .mockResolvedValue(patchResponse({ min_soc: 7 }));
    render(Settings);
    const min = (await screen.findByLabelText('Min-SoC')) as HTMLInputElement;
    await fireEvent.input(min, { target: { value: '7' } });
    await fireEvent.click(screen.getByTestId('settings-save'));
    await fireEvent.click(screen.getByTestId('low-min-soc-confirm-save'));
    await waitFor(() => {
      expect(patch).toHaveBeenCalledTimes(1);
    });
    const call = patch.mock.calls[0]?.[0];
    expect(call?.min_soc).toBe(7);
    expect(call?.acknowledged_low_min_soc).toBe(true);
  });

  it('treats an already persisted low min_soc as acknowledged for later saves', async () => {
    vi.mocked(client.getDevices).mockResolvedValue([makeWrCharge({ min_soc: 7 })]);
    const patch = vi
      .spyOn(client, 'patchBatteryConfig')
      .mockResolvedValue(patchResponse({ min_soc: 7, night_discharge_enabled: false }));
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    const checkbox = screen.getByLabelText('Nacht-Entladung aktivieren') as HTMLInputElement;
    await fireEvent.click(checkbox);
    await fireEvent.click(screen.getByTestId('settings-save'));
    await waitFor(() => {
      expect(patch).toHaveBeenCalledTimes(1);
    });
    const call = patch.mock.calls[0]?.[0];
    expect(call?.min_soc).toBe(7);
    expect(call?.acknowledged_low_min_soc).toBe(true);
    expect(screen.queryByTestId('low-min-soc-confirm')).toBeNull();
  });

  it('renders the inline error line on PATCH failure', async () => {
    vi.spyOn(client, 'patchBatteryConfig').mockRejectedValue(
      new ApiError(
        422,
        'urn:solalex:validation-error',
        'Validierungsfehler',
        'Backend hat den Wert abgelehnt.',
      ),
    );
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    await fireEvent.click(screen.getByTestId('settings-save'));
    const err = await screen.findByTestId('save-error');
    expect(err.textContent ?? '').toContain('abgelehnt');
  });
});

describe('Settings — Konfig-Reset', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders the reset card for the marstek setup', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    expect(screen.getByTestId('reset-section')).toBeTruthy();
    expect(screen.getByTestId('reset-open')).toBeTruthy();
  });

  it('renders the reset card for a drossel-only setup so a new akku can be added', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      {
        id: 1,
        type: 'generic',
        role: 'wr_limit',
        entity_id: 'number.opendtu_limit',
        adapter_key: 'generic',
        config_json: '{}',
        last_write_at: null,
        commissioned_at: '2026-04-25T12:00:00Z',
        created_at: '2026-04-25T12:00:00Z',
        updated_at: '2026-04-25T12:00:00Z',
      },
    ]);
    render(Settings);
    await screen.findByTestId('no-battery-hint');
    expect(screen.getByTestId('reset-open')).toBeTruthy();
  });

  it('opens the inline confirm and cancels back without calling the API', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
    const reset = vi.spyOn(client, 'resetConfig');
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    await fireEvent.click(screen.getByTestId('reset-open'));
    expect(screen.getByTestId('reset-confirm')).toBeTruthy();
    await fireEvent.click(screen.getByTestId('reset-cancel'));
    expect(screen.queryByTestId('reset-confirm')).toBeNull();
    expect(reset).not.toHaveBeenCalled();
  });

  it('confirm calls resetConfig and triggers a full reload', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
    const reset = vi
      .spyOn(client, 'resetConfig')
      .mockResolvedValue({ status: 'reset', deleted_devices: 3 });
    const reload = vi.fn();
    // happy-dom's location.reload is read-only; stub via defineProperty.
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, hash: '#/settings', reload },
    });
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    await fireEvent.click(screen.getByTestId('reset-open'));
    await fireEvent.click(screen.getByTestId('reset-confirm-action'));
    await waitFor(() => {
      expect(reset).toHaveBeenCalledTimes(1);
      expect(reload).toHaveBeenCalledTimes(1);
    });
    expect(window.location.hash).toBe('#/');
  });

  it('renders the inline error line on reset failure and keeps the confirm open', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrCharge()]);
    vi.spyOn(client, 'resetConfig').mockRejectedValue(
      new ApiError(
        500,
        'urn:solalex:internal-error',
        'Interner Fehler',
        'Backend konnte nicht zurücksetzen.',
      ),
    );
    render(Settings);
    await screen.findByLabelText('Min-SoC');
    await fireEvent.click(screen.getByTestId('reset-open'));
    await fireEvent.click(screen.getByTestId('reset-confirm-action'));
    const err = await screen.findByTestId('reset-error');
    expect(err.textContent ?? '').toContain('zurücksetzen');
    expect(screen.getByTestId('reset-confirm')).toBeTruthy();
  });
});

// Story 2.6 — Hardware-Card auf der Settings-Page.
describe('Settings — hardware card (Story 2.6)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  function makeWrLimit(overrides: Partial<DeviceResponse> = {}): DeviceResponse {
    return {
      id: 2,
      type: 'generic',
      role: 'wr_limit',
      entity_id: 'input_number.t2sgf72a29_set_target',
      adapter_key: 'generic',
      config_json: '{}',
      last_write_at: null,
      commissioned_at: '2026-04-25T12:00:00Z',
      created_at: '2026-04-25T12:00:00Z',
      updated_at: '2026-04-25T12:00:00Z',
      ...overrides,
    };
  }

  function makeGridMeter(invertSign = false): DeviceResponse {
    return {
      id: 3,
      type: 'generic_meter',
      role: 'grid_meter',
      entity_id: 'sensor.esphome_smart_meter_current_load',
      adapter_key: 'generic_meter',
      config_json: invertSign ? JSON.stringify({ invert_sign: true }) : '{}',
      last_write_at: null,
      commissioned_at: '2026-04-25T12:00:00Z',
      created_at: '2026-04-25T12:00:00Z',
      updated_at: '2026-04-25T12:00:00Z',
    };
  }

  it('renders the hardware-card with current devices', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      makeWrLimit(),
      makeGridMeter(),
    ]);
    render(Settings);
    const card = await screen.findByTestId('hardware-card');
    expect(card.textContent ?? '').toContain('Wechselrichter (allgemein)');
    expect(card.textContent ?? '').toContain('input_number.t2sgf72a29_set_target');
    expect(card.textContent ?? '').toContain('Smart Meter (allgemein)');
    expect(card.textContent ?? '').toContain('sensor.esphome_smart_meter_current_load');
  });

  it('shows the invert-sign tag when the grid meter has invert_sign=true', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      makeWrLimit(),
      makeGridMeter(true),
    ]);
    render(Settings);
    const tag = await screen.findByTestId('invert-sign-tag');
    expect(tag.textContent ?? '').toContain('Vorzeichen invertiert');
  });

  it('shows the not-commissioned tag when a control device is uncommissioned', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([
      makeWrLimit({ commissioned_at: null }),
      makeGridMeter(),
    ]);
    render(Settings);
    const tag = await screen.findByTestId('not-commissioned-tag');
    expect(tag.textContent ?? '').toContain('Funktionstest');
  });

  it('navigates to /hardware-edit on the "Hardware ändern" button click', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([makeWrLimit()]);
    window.location.hash = '#/settings';
    render(Settings);
    const button = await screen.findByTestId('hardware-edit-button');
    await fireEvent.click(button);
    expect(window.location.hash).toBe('#/hardware-edit');
  });

  it('hides the hardware-card when no devices exist', async () => {
    vi.spyOn(client, 'getDevices').mockResolvedValue([]);
    render(Settings);
    // Wait for the not-activated hint to render (proxy for "post-load").
    await screen.findByTestId('not-activated-hint');
    expect(screen.queryByTestId('hardware-card')).toBeNull();
  });
});
