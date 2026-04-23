import { ApiError } from './errors.js';
import type {
  CommissioningResponse,
  DeviceResponse,
  EntitiesResponse,
  FunctionalTestResponse,
  HardwareConfigRequest,
  SaveDevicesResponse,
  StateSnapshot,
} from './types.js';

const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let type = 'urn:solalex:error';
    let title = 'Fehler';
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as Record<string, unknown>;
      type = typeof body['type'] === 'string' ? body['type'] : type;
      title = typeof body['title'] === 'string' ? body['title'] : title;
      detail = typeof body['detail'] === 'string' ? body['detail'] : detail;
    } catch {
      // ignore JSON parse errors — keep fallback values
    }
    throw new ApiError(res.status, type, title, detail);
  }
  return res.json() as Promise<T>;
}

export async function getEntities(): Promise<EntitiesResponse> {
  return request<EntitiesResponse>('/api/v1/setup/entities');
}

export async function saveDevices(config: HardwareConfigRequest): Promise<SaveDevicesResponse> {
  return request<SaveDevicesResponse>('/api/v1/devices/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
}

export async function runFunctionalTest(): Promise<FunctionalTestResponse> {
  return request<FunctionalTestResponse>('/api/v1/setup/test', { method: 'POST' });
}

export async function commission(): Promise<CommissioningResponse> {
  return request<CommissioningResponse>('/api/v1/setup/commission', { method: 'POST' });
}

export async function getStateSnapshot(): Promise<StateSnapshot> {
  return request<StateSnapshot>('/api/v1/control/state');
}

export async function getDevices(): Promise<DeviceResponse[]> {
  return request<DeviceResponse[]>('/api/v1/devices/');
}
