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
  hardware_type: 'hoymiles' | 'marstek_venus';
  wr_limit_entity_id: string;
  battery_soc_entity_id?: string;
  grid_meter_entity_id?: string;
  min_soc?: number;
  max_soc?: number;
  night_discharge_enabled?: boolean;
  night_start?: string;
  night_end?: string;
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

export interface StateSnapshot {
  entities: EntitySnapshot[];
  test_in_progress: boolean;
  last_command_at: string | null;
}
