-- BioGate audit pipeline: audits and vendors tables.
-- Run against your Supabase project (SQL Editor or migration tool).
--
-- If you already have an audits table with organization_id as TEXT, either drop and
-- re-run this migration or run:
--   ALTER TABLE audits ALTER COLUMN organization_id TYPE UUID USING organization_id::uuid;
-- (only if current values are valid UUIDs; otherwise use the DEFAULT below.)

CREATE TABLE IF NOT EXISTS audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'complete', 'failed')),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    raw_input_name TEXT NOT NULL,
    normalized_name TEXT,
    country TEXT,
    risk_tier TEXT CHECK (risk_tier IN ('red', 'amber', 'yellow', 'green')),
    match_evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vendors_audit_id ON vendors(audit_id);
CREATE INDEX IF NOT EXISTS idx_audits_organization_status ON audits(organization_id, status);

COMMENT ON TABLE audits IS 'Vendor screening audit runs (one per CSV upload)';
COMMENT ON COLUMN audits.organization_id IS 'Placeholder UUID for "default" org until multi-tenant';
COMMENT ON TABLE vendors IS 'Vendors screened in an audit; risk_tier and match_evidence from fuzzy match';
