-- Manual overrides for vendor risk tier (compliance officer downgrade with justification).
-- risk_reasoning on vendors: human-readable explanation from risk scoring engine.

ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS risk_reasoning TEXT;

COMMENT ON COLUMN vendors.risk_reasoning IS 'Human-readable reasoning from risk scoring engine for audit trail';

CREATE TABLE IF NOT EXISTS vendor_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    original_tier TEXT NOT NULL CHECK (original_tier IN ('red', 'amber', 'yellow', 'green')),
    override_tier TEXT NOT NULL CHECK (override_tier IN ('red', 'amber', 'yellow', 'green')),
    justification TEXT NOT NULL,
    overridden_by TEXT NOT NULL,
    overridden_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    superseded_by UUID REFERENCES vendor_overrides(id)
);

CREATE INDEX IF NOT EXISTS idx_vendor_overrides_vendor_audit_active
    ON vendor_overrides(vendor_id, audit_id, is_active);

COMMENT ON TABLE vendor_overrides IS 'Manual tier overrides with justification for audit trail; only downgrades allowed';
