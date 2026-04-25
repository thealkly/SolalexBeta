import { describe, expect, it } from 'vitest';
import type { DeviceResponse } from './api/types.js';
import { evaluateGate } from './gate.js';

function makeDevice(overrides: Partial<DeviceResponse> = {}): DeviceResponse {
  return {
    id: 1,
    type: 'generic',
    role: 'inverter',
    entity_id: 'number.inverter_limit',
    adapter_key: 'generic',
    config_json: '{}',
    last_write_at: null,
    commissioned_at: null,
    created_at: '2026-04-24T00:00:00Z',
    updated_at: '2026-04-24T00:00:00Z',
    ...overrides,
  };
}

// evaluateGate is the pure decision core behind Story 2.3a AC 1, 7, 10:
// first-launch users must land on #/disclaimer, direct URL hits on gated
// routes must redirect, and reloads must preserve the current route when
// legitimate.

describe('evaluateGate — devices not yet loaded', () => {
  it('stays put while the initial device fetch is in flight', () => {
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: null,
        preAccepted: false,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('keeps the hidden diagnostics route reachable before setup state is known', () => {
    expect(
      evaluateGate({
        currentRoute: '/diagnostics',
        devices: null,
        preAccepted: false,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });
});

describe('evaluateGate — commissioned users', () => {
  const commissioned = [makeDevice({ commissioned_at: '2026-04-24T00:00:00Z' })];

  it('redirects to /running when landing on any wizard route', () => {
    for (const route of ['/', '/disclaimer', '/activate', '/functional-test', '/config']) {
      expect(
        evaluateGate({
          currentRoute: route,
          devices: commissioned,
          preAccepted: true,
          allowAutoForward: true,
        }),
      ).toEqual({ kind: 'redirect', hash: '#/running' });
    }
  });

  it('stays on /running itself (no redirect loop)', () => {
    expect(
      evaluateGate({
        currentRoute: '/running',
        devices: commissioned,
        preAccepted: true,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('ignores preAccepted=false when all devices are commissioned', () => {
    // Returning user whose localStorage was cleared; commissioning state wins
    // so they are not forced back through the pre-disclaimer.
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: commissioned,
        preAccepted: false,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/running' });
  });
});

describe('evaluateGate — uncommissioned users, pre-disclaimer not accepted (AC 1, 7)', () => {
  it('redirects a first-launch user from / to /disclaimer', () => {
    expect(
      evaluateGate({
        currentRoute: '/',
        devices: [],
        preAccepted: false,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/disclaimer' });
  });

  it('redirects direct URL hits on #/config to /disclaimer', () => {
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: [],
        preAccepted: false,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/disclaimer' });
  });

  it('redirects direct URL hits on #/functional-test to /disclaimer', () => {
    expect(
      evaluateGate({
        currentRoute: '/functional-test',
        devices: [],
        preAccepted: false,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/disclaimer' });
  });

  it('redirects direct URL hits on #/activate to /disclaimer', () => {
    expect(
      evaluateGate({
        currentRoute: '/activate',
        devices: [],
        preAccepted: false,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/disclaimer' });
  });

  it('stays on /disclaimer itself (no redirect loop)', () => {
    expect(
      evaluateGate({
        currentRoute: '/disclaimer',
        devices: [],
        preAccepted: false,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });
});

describe('evaluateGate — uncommissioned users, pre-disclaimer accepted', () => {
  it('stays on /config after reload (AC 10)', () => {
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: [],
        preAccepted: true,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('stays on /config on initial load when the user explicitly navigated there', () => {
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: [],
        preAccepted: true,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('stays on / when devices are empty (no auto-forward to functional test yet)', () => {
    // Accepted user hasn't committed any hardware yet — landing on `/` should
    // show the welcome card, not yank them forward.
    expect(
      evaluateGate({
        currentRoute: '/',
        devices: [],
        preAccepted: true,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('auto-forwards from / to /functional-test when devices exist but are not commissioned', () => {
    const draft = [makeDevice({ commissioned_at: null })];
    expect(
      evaluateGate({
        currentRoute: '/',
        devices: draft,
        preAccepted: true,
        allowAutoForward: true,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/functional-test' });
  });

  it('does NOT auto-forward from / on hashchange (user navigated back deliberately)', () => {
    const draft = [makeDevice({ commissioned_at: null })];
    expect(
      evaluateGate({
        currentRoute: '/',
        devices: draft,
        preAccepted: true,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'stay' });
  });
});

describe('evaluateGate — Story 3.6 settings route', () => {
  const commissioned = [makeDevice({ commissioned_at: '2026-04-24T00:00:00Z' })];

  it('lets a commissioned user reach /settings without a wizard redirect', () => {
    expect(
      evaluateGate({
        currentRoute: '/settings',
        devices: commissioned,
        preAccepted: true,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'stay' });
  });

  it('redirects to /disclaimer when pre-disclaimer is not accepted', () => {
    expect(
      evaluateGate({
        currentRoute: '/settings',
        devices: commissioned,
        preAccepted: false,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'redirect', hash: '#/disclaimer' });
  });

  it('stays on /settings when no devices yet but pre-disclaimer is accepted', () => {
    // Drossel-only setup or pre-commissioning user landing on /settings via
    // the hidden URL — the page itself renders the AC 19 hint.
    expect(
      evaluateGate({
        currentRoute: '/settings',
        devices: [],
        preAccepted: true,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'stay' });
  });
});

describe('evaluateGate — partial commissioning', () => {
  it('treats any uncommissioned device as "not fully commissioned"', () => {
    const mixed = [
      makeDevice({ id: 1, commissioned_at: '2026-04-24T00:00:00Z' }),
      makeDevice({ id: 2, commissioned_at: null }),
    ];
    expect(
      evaluateGate({
        currentRoute: '/config',
        devices: mixed,
        preAccepted: true,
        allowAutoForward: false,
      }),
    ).toEqual({ kind: 'stay' });
  });
});
