-- Migration 003 - rename vendor-specific adapter keys to generic day-1 keys.
-- Forward-only. Rollback is handled by backup-file replace on previous-version restart.

UPDATE devices SET adapter_key = 'generic' WHERE adapter_key = 'hoymiles';
UPDATE devices SET adapter_key = 'generic_meter' WHERE adapter_key = 'shelly_3em';
UPDATE devices SET type = 'generic' WHERE type = 'hoymiles';
UPDATE devices SET type = 'generic_meter' WHERE type = 'shelly_3em';
