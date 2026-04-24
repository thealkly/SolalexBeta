-- Story 3.1: control_cycles ring buffer + latency_measurements.
-- Forward-only; do not edit after merge — add 003_*.sql for any further change.

CREATE TABLE IF NOT EXISTS control_cycles (
    id                INTEGER   PRIMARY KEY AUTOINCREMENT,
    ts                TIMESTAMP NOT NULL,
    device_id         INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    mode              TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi')),
    source            TEXT      NOT NULL CHECK (source IN ('solalex','manual','ha_automation')),
    sensor_value_w    REAL,
    target_value_w    INTEGER,
    readback_status   TEXT      CHECK (readback_status IN ('passed','failed','timeout','vetoed','noop')),
    readback_actual_w REAL,
    readback_mismatch INTEGER   NOT NULL DEFAULT 0,
    latency_ms        INTEGER,
    cycle_duration_ms INTEGER   NOT NULL,
    reason            TEXT
);

CREATE INDEX IF NOT EXISTS idx_control_cycles_ts ON control_cycles(ts DESC);
CREATE INDEX IF NOT EXISTS idx_control_cycles_device ON control_cycles(device_id);

CREATE TABLE IF NOT EXISTS latency_measurements (
    id         INTEGER   PRIMARY KEY AUTOINCREMENT,
    device_id  INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    command_at TIMESTAMP NOT NULL,
    effect_at  TIMESTAMP NOT NULL,
    latency_ms INTEGER   NOT NULL,
    mode       TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi'))
);

CREATE INDEX IF NOT EXISTS idx_latency_device_ts ON latency_measurements(device_id, command_at DESC);
