import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'svelte/server';
import { isApiError } from '../lib/api/errors.js';
import { commission } from '../lib/api/client.js';
import DisclaimerActivation from './DisclaimerActivation.svelte';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function okCommission() {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'commissioned',
        commissioned_at: '2026-04-23T12:00:00Z',
        device_count: 1,
      }),
  } as unknown as Response;
}

function errCommission(status: number, detail: string) {
  return {
    ok: false,
    status,
    json: () =>
      Promise.resolve({
        type: 'urn:solalex:commission-error',
        title: 'Aktivierungsfehler',
        detail,
      }),
  } as unknown as Response;
}

describe('DisclaimerActivation — SSR initial state', () => {
  it('renders checkbox unchecked and no activate button in initial state', () => {
    const { html } = render(DisclaimerActivation, {});
    // Pair the negative assertion below with a concrete positive counter-
    // assertion — otherwise an empty/broken render (html === '') would
    // silently pass the `.not.toMatch` check (Story 3.2 Review P16).
    expect(html.length).toBeGreaterThan(200);
    expect(html).toContain('type="checkbox"');
    // The activate button lives behind `{#if checked || committing}`; assert on
    // its distinctive class rather than a bare "Aktivieren" substring to avoid
    // collisions with the error header "Aktivierungsfehler" or future copy
    // tweaks (Review P11).
    expect(html).not.toMatch(/<button[^>]*class="[^"]*activate-button/);
    expect(html).toContain('Bevor es losgeht');
  });

  it('contains all three required disclaimer sentences', () => {
    const { html } = render(DisclaimerActivation, {});
    expect(html).toContain('Solalex steuert deine Solaranlage aktiv und sekundengenau');
    expect(html).toContain('konfigurierten Entities deiner Hardware');
    expect(html).toContain('inkompatible Firmware können nicht durch Solalex verhindert werden');
  });

  it('contains the checkbox label and back link', () => {
    const { html } = render(DisclaimerActivation, {});
    expect(html).toContain('Ich habe den Hinweis gelesen');
    expect(html).toContain('Zurück zum Funktionstest');
    expect(html).toContain('#/functional-test');
  });

  it('wires the checkbox to the disclaimer paragraph via aria-describedby', () => {
    const { html } = render(DisclaimerActivation, {});
    expect(html).toMatch(/id="disclaimer-text"/);
    expect(html).toMatch(/aria-describedby="disclaimer-text"/);
  });
});

// These tests exercise `client.commission()` directly. We keep them here next to
// the component because the component's only job is to invoke this client
// helper, and SSR rendering cannot simulate the button click itself. Interactive
// coverage is an accepted gap — see Story 2.3 Review Decision D2.
describe('commission() API contract (client-level, used by DisclaimerActivation)', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('posts to /api/v1/setup/commission and returns CommissioningResponse', async () => {
    mockFetch.mockResolvedValue(okCommission());

    const result = await commission();

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/setup/commission');
    expect(init.method).toBe('POST');
    expect(result.status).toBe('commissioned');
    expect(result.commissioned_at).toBe('2026-04-23T12:00:00Z');
  });

  it('throws ApiError with RFC-7807 detail on failure', async () => {
    mockFetch.mockResolvedValue(errCommission(500, 'Server nicht erreichbar.'));

    await expect(commission()).rejects.toSatisfy(isApiError);
  });

  it('ApiError carries RFC-7807 title, detail and status for inline display', async () => {
    mockFetch.mockResolvedValue(errCommission(500, 'Server nicht erreichbar.'));

    let caught: unknown;
    try {
      await commission();
    } catch (err) {
      caught = err;
    }

    // Without this guard the test would silently pass if commission() ever
    // stopped throwing (Review P13). `toBeDefined` makes the missing throw
    // an explicit failure.
    expect(caught).toBeDefined();
    expect(isApiError(caught)).toBe(true);
    if (isApiError(caught)) {
      expect(caught.detail).toBe('Server nicht erreichbar.');
      expect(caught.title).toBe('Aktivierungsfehler');
      expect(caught.status).toBe(500);
    }
  });
});
