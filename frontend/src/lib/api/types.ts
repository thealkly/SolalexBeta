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
  // Story 2.6 Decision (Wizard-Subset replace): explicit ``null`` clears
  // the override on the backend (``_merge_config`` drops None-valued
  // incoming keys); ``undefined`` keeps the existing value untouched.
  min_limit_w?: number | null;
  max_limit_w?: number | null;
  // Story 2.5 — Smart-Meter sign-convention override.
  invert_sign?: boolean;
}

// Story 2.5 — single-entity live preview for the smart-meter sign toggle.
export interface EntityState {
  entity_id: string;
  value_w: number | null;
  ts: string | null;
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
  // Story 5.1d — UI-ready fields owned by the backend.
  // ``effective_value_w`` is the post-``invert_sign`` (Story 2.5) value
  // for ``role === 'grid_meter'``; for other roles it falls back to the
  // raw numeric ``state`` (or ``null`` when non-numeric). ``display_label``
  // is the German glossar label keyed by role so the frontend does not
  // maintain a parallel mapping table.
  effective_value_w: number | null;
  display_label: string | null;
}

export type CycleSource = 'solalex' | 'manual' | 'ha_automation';
export type CycleReadbackStatus = 'passed' | 'failed' | 'timeout' | 'vetoed' | 'noop';

export interface RecentCycle {
  id: number;
  ts: string;
  device_id: number;
  // Story 5.1d — extended with ``audit`` (mode_switch / hardware_edit
  // noop rows) and ``export`` (Story 3.8 surplus-export). Mirror of the
  // Pydantic ``CycleMode`` literal in backend/api/schemas/control.py.
  mode: 'drossel' | 'speicher' | 'multi' | 'audit' | 'export';
  source: CycleSource;
  sensor_value_w: number | null;
  target_value_w: number | null;
  readback_status: CycleReadbackStatus | null;
  latency_ms: number | null;
  // Story 5.1d — Klartext rationale for the cycle list. ``null`` for
  // pre-existing rows that predate the migration; the UI renders a
  // generic „Beobachtung" fallback in that case.
  reason: string | null;
}

export interface RateLimitEntry {
  device_id: number;
  seconds_until_next_write: number | null;
}

// Story 5.1d — extended with ``export`` (Story 3.8 surplus-export). The
// ``audit`` cycle-row mode never reaches ``current_mode`` (controller
// can't be in audit-mode, only its noop rows are tagged audit-like via
// the ``reason`` column). Mirror of the Pydantic ``current_mode`` literal.
export type ControlMode = 'drossel' | 'speicher' | 'multi' | 'export' | 'idle';

// Story 3.5 — manual mode override.
// Backend Literal["drossel","speicher","multi","export"] | null mirrors here:
// `null` = auto-detection active; the radio UI maps null to "auto".
// Story 3.8 added ``"export"`` so a Beta-tester can pin EXPORT for
// diagnostics; the Settings radio UI keeps ``ForcedModeChoice`` narrow
// (no EXPORT option) — surplus-export is meant to be reached via the
// per-WR toggle, not a global force-pin.
export type ForcedMode = 'drossel' | 'speicher' | 'multi' | 'export';
export type ForcedModeChoice = 'drossel' | 'speicher' | 'multi' | 'auto';

// Setup-baseline (auto-detected from topology) is never EXPORT — that
// state only ever exists as an active hysteresis state or a manual pin.
export type BaselineMode = 'drossel' | 'speicher' | 'multi';

export interface ControlModeResponse {
  forced_mode: ForcedMode | null;
  active_mode: ForcedMode;
  baseline_mode: BaselineMode;
}

export interface StateSnapshot {
  entities: EntitySnapshot[];
  test_in_progress: boolean;
  last_command_at: string | null;
  current_mode: ControlMode;
  recent_cycles: RecentCycle[];
  rate_limit_status: RateLimitEntry[];
  // Story 5.1d — HA-WS connection diagnostics for the Connection-Tile.
  // ``ha_ws_disconnected_since`` is set on disconnect, cleared on connect.
  ha_ws_connected: boolean;
  ha_ws_disconnected_since: string | null;
}

// Story 3.6 — Settings PATCH /api/v1/devices/battery-config.
export interface BatteryConfigPatchRequest {
  min_soc: number;
  max_soc: number;
  night_discharge_enabled: boolean;
  night_start: string;
  night_end: string;
  acknowledged_low_min_soc?: boolean;
}

export interface BatteryConfigResponse {
  min_soc: number;
  max_soc: number;
  night_discharge_enabled: boolean;
  night_start: string;
  night_end: string;
}

export interface ResetConfigResponse {
  status: string;
  deleted_devices: number;
}
