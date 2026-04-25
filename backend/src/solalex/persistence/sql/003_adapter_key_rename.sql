-- Migration 003 - rename vendor-specific adapter keys to generic day-1 keys.
-- Forward-only. Rollback is handled by backup-file replace on previous-version restart.

-- Wrap the four UPDATEs in an explicit transaction so a crash mid-migration
-- cannot leave devices.type and devices.adapter_key in mismatched state
-- (e.g. type='generic' but adapter_key='hoymiles' would break dispatcher
-- adapter lookup at startup).
BEGIN;
UPDATE devices SET adapter_key = 'generic' WHERE adapter_key = 'hoymiles';
UPDATE devices SET adapter_key = 'generic_meter' WHERE adapter_key = 'shelly_3em';
UPDATE devices SET type = 'generic' WHERE type = 'hoymiles';
UPDATE devices SET type = 'generic_meter' WHERE type = 'shelly_3em';
COMMIT;
