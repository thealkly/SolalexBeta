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
  it('renders checkbox unchecked and no Aktivieren-Button in initial state', () => {
    const { html } = render(DisclaimerActivation, {});
    expect(html).toContain('type="checkbox"');
    // Button is inside {#if checked} — checked starts false, so not in DOM
    expect(html).not.toContain('Aktivieren');
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
});

describe('DisclaimerActivation — commission() API contract', () => {
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

  it('ApiError carries the German detail string for inline display', async () => {
    mockFetch.mockResolvedValue(errCommission(500, 'Server nicht erreichbar.'));

    try {
      await commission();
    } catch (err) {
      if (isApiError(err)) {
        expect(err.detail).toBe('Server nicht erreichbar.');
        expect(err.status).toBe(500);
      }
    }
  });
});
