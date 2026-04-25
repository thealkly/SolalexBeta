// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Config from './Config.svelte';
import * as client from '../lib/api/client.js';
import { ApiError } from '../lib/api/errors.js';
import type {
  ControlModeResponse,
  DeviceResponse,
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

// Story 2.6 — Config.svelte editMode + initialDevices props.
describe('Config — editMode (Story 2.6)', () => {
  beforeEach(() => {
    vi.spyOn(client, 'getEntities').mockResolvedValue(EMPTY_ENTITIES);
    vi.spyOn(client, 'fetchControlMode').mockRejectedValue(
      new ApiError(500, 'urn:test', 'fail', 'no controller'),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders the edit-mode header instead of "Hardware konfigurieren"', async () => {
    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.x',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
    });
    await screen.findByText('Hardware ändern');
    expect(screen.queryByText('Hardware konfigurieren')).toBeNull();
  });

  it('pre-selects the generic hardware tile when an existing wr_limit is present', async () => {
    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.x',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
    });
    const genericTile = await screen.findByText('Wechselrichter (allgemein)');
    const button = genericTile.closest('button');
    expect(button?.getAttribute('aria-pressed')).toBe('true');
  });

  it('renders the warn-banner only after a WR-entity swap', async () => {
    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.original',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
    });

    // Initial render — no swap yet.
    await screen.findByText('Hardware ändern');
    expect(screen.queryByTestId('refunctional-test-warn')).toBeNull();
  });

  it('shows the warn-banner after a hardware-type swap (review P6 positive case)', async () => {
    // We drive the swap through the hardware-type tile button (which is
    // a real <button onclick>, propagates fine under happy-dom) rather
    // than the entity <select bind:value> dropdown — Svelte 5 runes
    // setters are not reached by happy-dom-dispatched change events.
    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.original',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
    });

    await screen.findByText('Hardware ändern');
    // Click the Marstek-tile to flip hardwareType — triggers the
    // ``initialHardwareType !== hardwareType`` branch of the
    // ``needsRefunctionalTest`` derived value. We use ``findByText``
    // because the tile only renders after the entities-fetch settles
    // and the loading skeleton is replaced.
    const marstekTitle = await screen.findByText('Marstek Venus 3E/D');
    expect(screen.queryByTestId('refunctional-test-warn')).toBeNull();
    const marstekTile = marstekTitle.closest('button');
    expect(marstekTile).not.toBeNull();
    await fireEvent.click(marstekTile!);

    await waitFor(() => {
      expect(screen.queryByTestId('refunctional-test-warn')).not.toBeNull();
    });
  });

  it('renders the edit-mode save-button label "Änderungen übernehmen"', async () => {
    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.x',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
    });

    // ``canSave`` requires wrLimitEntityId !== '' which is set via
    // initialDevices pre-fill. The save-button materialises with the
    // edit-mode label.
    const saveBtn = await screen.findByTestId('config-save');
    expect(saveBtn.textContent?.trim()).toBe('Änderungen übernehmen');
    expect(saveBtn.textContent?.trim()).not.toBe('Speichern');
  });

  it('redirects to #/running and fires onSaved after a successful PUT', async () => {
    const updatedDevices: DeviceResponse[] = [
      {
        id: 1,
        type: 'generic',
        role: 'wr_limit',
        entity_id: 'input_number.x',
        adapter_key: 'generic',
        config_json: '{}',
        last_write_at: null,
        commissioned_at: null, // post-PUT: WR-swap nulled it
        created_at: '2026-04-25T12:00:00Z',
        updated_at: '2026-04-25T12:00:01Z',
      },
    ];
    const updateSpy = vi
      .spyOn(client, 'updateDevices')
      .mockResolvedValue(updatedDevices);
    let savedSnapshot: DeviceResponse[] | null = null;
    const onSaved = (devices: DeviceResponse[]) => {
      savedSnapshot = devices;
    };

    // Pre-set the location so we can detect the change deterministically.
    window.location.hash = '#/hardware-edit';

    render(Config, {
      editMode: true,
      initialDevices: [
        {
          id: 1,
          type: 'generic',
          role: 'wr_limit',
          entity_id: 'input_number.x',
          adapter_key: 'generic',
          config_json: '{}',
          last_write_at: null,
          commissioned_at: '2026-04-25T12:00:00Z',
          created_at: '2026-04-25T12:00:00Z',
          updated_at: '2026-04-25T12:00:00Z',
        },
      ],
      onSaved,
    });

    const saveBtn = await screen.findByTestId('config-save');
    await fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(window.location.hash).toBe('#/running');
    });
    expect(savedSnapshot).toEqual(updatedDevices);
  });
});

// Story 2.5 — Smart-Meter Vorzeichen-Toggle + Live-Preview behaviour
// is covered in `LivePreviewCard.test.ts` (invert toggle, watt readout,
// polling lifecycle). The Config.svelte integration only wires the
// gridMeterEntityId/invertSign state through to `saveDevices`; that
// wiring is verified by `tests/integration/test_devices_api.py` on the
// backend (round-trips invert_sign into grid_meter.config_json).
//
// Driving Config's two <select bind:value> dropdowns from
// @testing-library/svelte under happy-dom does not propagate the
// change event back into Svelte 5's bind:value binding (the value is
// set on the DOM node, but the rune setter is never invoked). Rather
// than adding ad-hoc test-only props, we rely on the smaller surfaces
// above plus the SR-01 manual-smoke-test on real hardware.
