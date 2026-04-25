export interface EntityOption {
  entity_id: string;
  friendly_name: string;
}

export interface EntitiesResponse {
  wr_limit_entities: EntityOption[];
  power_entities: EntityOption[];
  soc_entities: EntityOption[];
}

export interface HardwareConfigRequest {
  hardware_type: 'generic' | 'marstek_venus';
  wr_limit_entity_id: string;
  battery_soc_entity_id?: string;
  grid_meter_entity_id?: string;
  min_soc?: number;
  max_soc?: number;
  night_discharge_enabled?: boolean;
  night_start?: string;
  night_end?: string;
  min_limit_w?: number;
  max_limit_w?: number;
}

export interface SaveDevicesResponse {
  status: string;
  device_count: number;
  next_action: string;
}

export interface DeviceResponse {
  id: number;
  type: string;
  role: string;
  entity_id: string;
  adapter_key: string;
  config_json: string;
  last_write_at: string | null;
  commissioned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FunctionalTestResponse {
  status: 'passed' | 'failed' | 'timeout';
  test_value_w: number;
  actual_value_w: number | null;
  tolerance_w: number;
  latency_ms: number | null;
  reason: string | null;
  device_entity_id: string;
}

export interface CommissioningResponse {
  status: string;
  commissioned_at: string;
  device_count: number;
}

export interface EntitySnapshot {
  entity_id: string;
  state: number | null;
  unit: string;
  role: string;
  timestamp: string | null;
}

export type CycleSource = 'solalex' | 'manual' | 'ha_automation';
export type CycleReadbackStatus = 'passed' | 'failed' | 'timeout' | 'vetoed' | 'noop';

export interface RecentCycle {
  id: number;
  ts: string;
  device_id: number;
  mode: ControlMode;
  source: CycleSource;
  sensor_value_w: number | null;
  target_value_w: number | null;
  readback_status: CycleReadbackStatus | null;
  latency_ms: number | null;
}

export interface RateLimitEntry {
  device_id: number;
  seconds_until_next_write: number | null;
}

export type ControlMode = 'drossel' | 'speicher' | 'multi' | 'idle';

// Story 3.5 — manual mode override.
// Backend Literal["drossel","speicher","multi"] | null mirrors here:
// `null` = auto-detection active; the radio UI maps null to "auto".
export type ForcedMode = 'drossel' | 'speicher' | 'multi';
export type ForcedModeChoice = ForcedMode | 'auto';

export interface ControlModeResponse {
  forced_mode: ForcedMode | null;
  active_mode: ForcedMode;
  baseline_mode: ForcedMode;
}

export interface StateSnapshot {
  entities: EntitySnapshot[];
  test_in_progress: boolean;
  last_command_at: string | null;
  current_mode: ControlMode;
  recent_cycles: RecentCycle[];
  rate_limit_status: RateLimitEntry[];
}
