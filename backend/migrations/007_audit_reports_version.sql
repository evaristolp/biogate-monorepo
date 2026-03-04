-- Add version column to audit_reports for report versioning history.

ALTER TABLE audit_reports
ADD COLUMN IF NOT EXISTS version INTEGER;

-- Backfill any existing rows to version 1 where null.
UPDATE audit_reports
SET version = 1
WHERE version IS NULL;

-- Index for fast lookups by audit_id + version.
CREATE INDEX IF NOT EXISTS idx_audit_reports_audit_id_version
    ON audit_reports (audit_id, version);

