-- Story 3.8: Surplus-Export-Mode (Mode.EXPORT). Extends the CHECK constraint
-- on control_cycles.mode and latency_measurements.mode to accept 'export'.
-- Forward-only; SQLite cannot ALTER an existing CHECK constraint, so the
-- canonical fix is the CREATE _new + INSERT…SELECT + DROP + RENAME pattern.
-- Indexes are dropped together with the old table and recreated against the
-- renamed one (SQLite does not migrate indexes through DROP/RENAME).

BEGIN;

-- control_cycles -----------------------------------------------------------

CREATE TABLE control_cycles_new (
    id                INTEGER   PRIMARY KEY AUTOINCREMENT,
    ts                TIMESTAMP NOT NULL,
    device_id         INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    mode              TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi','export')),
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

INSERT INTO control_cycles_new (
    id, ts, device_id, mode, source, sensor_value_w, target_value_w,
    readback_status, readback_actual_w, readback_mismatch, latency_ms,
    cycle_duration_ms, reason
)
SELECT
    id, ts, device_id, mode, source, sensor_value_w, target_value_w,
    readback_status, readback_actual_w, readback_mismatch, latency_ms,
    cycle_duration_ms, reason
FROM control_cycles;

DROP TABLE control_cycles;
ALTER TABLE control_cycles_new RENAME TO control_cycles;

CREATE INDEX IF NOT EXISTS idx_control_cycles_ts ON control_cycles(ts DESC);
CREATE INDEX IF NOT EXISTS idx_control_cycles_device ON control_cycles(device_id);

-- latency_measurements ----------------------------------------------------

CREATE TABLE latency_measurements_new (
    id         INTEGER   PRIMARY KEY AUTOINCREMENT,
    device_id  INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    command_at TIMESTAMP NOT NULL,
    effect_at  TIMESTAMP NOT NULL,
    latency_ms INTEGER   NOT NULL,
    mode       TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi','export'))
);

INSERT INTO latency_measurements_new (
    id, device_id, command_at, effect_at, latency_ms, mode
)
SELECT
    id, device_id, command_at, effect_at, latency_ms, mode
FROM latency_measurements;

DROP TABLE latency_measurements;
ALTER TABLE latency_measurements_new RENAME TO latency_measurements;

CREATE INDEX IF NOT EXISTS idx_latency_device_ts ON latency_measurements(device_id, command_at DESC);

COMMIT;
