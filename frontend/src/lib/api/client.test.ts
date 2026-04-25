import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isApiError } from './errors.js';
import { getEntities, getEntityState, saveDevices } from './client.js';
import type { EntitiesResponse, EntityState } from './types.js';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function okResponse(body: unknown): Response {
  return {
    ok: true,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

function errResponse(status: number, body: unknown): Response {
  return {
    ok: false,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

function badJsonResponse(status: number): Response {
  return {
    ok: false,
    status,
    json: () => Promise.reject(new SyntaxError('Unexpected token')),
  } as unknown as Response;
}

describe('getEntities', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('returns parsed EntitiesResponse on 200', async () => {
    const data: EntitiesResponse = {
      wr_limit_entities: [{ entity_id: 'number.opendtu', friendly_name: 'OpenDTU Limit' }],
      power_entities: [],
      soc_entities: [],
    };
    mockFetch.mockResolvedValue(okResponse(data));

    const result = await getEntities();
    expect(result.wr_limit_entities).toHaveLength(1);
    expect(result.wr_limit_entities[0]!.entity_id).toBe('number.opendtu');
  });

  it('throws ApiError with RFC-7807 fields on 503', async () => {
    mockFetch.mockResolvedValue(
      errResponse(503, {
        type: 'urn:solalex:ha-unavailable',
        title: 'Home Assistant nicht erreichbar',
        detail: 'Prüfe die HA-Verbindung und lade die Seite neu.',
      }),
    );

    await expect(getEntities()).rejects.toSatisfy((err: unknown) => isApiError(err));

    try {
      await getEntities();
    } catch (err) {
      if (isApiError(err)) {
        expect(err.status).toBe(503);
        expect(err.type).toBe('urn:solalex:ha-unavailable');
        expect(err.detail).toBe('Prüfe die HA-Verbindung und lade die Seite neu.');
      }
    }
  });

  it('throws ApiError with fallback values when body is not valid JSON', async () => {
    mockFetch.mockResolvedValue(badJsonResponse(500));

    try {
      await getEntities();
    } catch (err) {
      expect(isApiError(err)).toBe(true);
      if (isApiError(err)) {
        expect(err.status).toBe(500);
        expect(err.type).toBe('urn:solalex:error');
      }
    }
  });
});

describe('saveDevices', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('posts JSON and returns SaveDevicesResponse on 201', async () => {
    mockFetch.mockResolvedValue(
      okResponse({ status: 'saved', device_count: 1, next_action: 'functional_test' }),
    );

    const result = await saveDevices({
      hardware_type: 'generic',
      wr_limit_entity_id: 'number.opendtu_limit',
    });

    expect(result.status).toBe('saved');
    expect(result.device_count).toBe(1);

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' });
  });

  it('throws ApiError with German detail on 422', async () => {
    mockFetch.mockResolvedValue(
      errResponse(422, {
        type: 'urn:solalex:validation-error',
        title: 'Validierungsfehler',
        detail: 'wr_limit_entity_id ist erforderlich.',
      }),
    );

    try {
      await saveDevices({ hardware_type: 'generic', wr_limit_entity_id: '' });
    } catch (err) {
      expect(isApiError(err)).toBe(true);
      if (isApiError(err)) {
        expect(err.status).toBe(422);
        expect(err.detail).toBe('wr_limit_entity_id ist erforderlich.');
      }
    }
  });
});

describe('getEntityState', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('returns parsed EntityState on 200', async () => {
    const data: EntityState = {
      entity_id: 'sensor.esphome_smart_meter_current_load',
      value_w: 2120,
      ts: '2026-04-25T12:00:00+00:00',
    };
    mockFetch.mockResolvedValue(okResponse(data));

    const result = await getEntityState(
      'sensor.esphome_smart_meter_current_load',
    );
    expect(result.value_w).toBe(2120);
    const [url] = mockFetch.mock.calls[0] as [string];
    expect(url).toContain(
      'entity_id=sensor.esphome_smart_meter_current_load',
    );
  });

  it('throws ApiError on 403 for non-whitelisted entity', async () => {
    mockFetch.mockResolvedValue(
      errResponse(403, {
        type: 'urn:solalex:forbidden',
        title: 'Forbidden',
        detail: "Entity 'sensor.foo' nicht im Whitelist-Set",
      }),
    );

    try {
      await getEntityState('sensor.foo');
    } catch (err) {
      expect(isApiError(err)).toBe(true);
      if (isApiError(err)) {
        expect(err.status).toBe(403);
      }
    }
  });
});
