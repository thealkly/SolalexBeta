-- Initial schema: meta table for key/value store and devices table.
-- Managed by persistence/migrate.py — do NOT run manually.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id               INTEGER  PRIMARY KEY AUTOINCREMENT,
    type             TEXT     NOT NULL,
    role             TEXT     NOT NULL,
    entity_id        TEXT     NOT NULL,
    adapter_key      TEXT     NOT NULL,
    config_json      TEXT     NOT NULL DEFAULT '{}',
    last_write_at    TIMESTAMP,
    commissioned_at  TIMESTAMP,
    created_at       TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at       TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(entity_id, role)
);
