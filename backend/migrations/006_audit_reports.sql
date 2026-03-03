-- Store generated JSON risk report per audit (one row per audit, overwritten on regenerate).

CREATE TABLE IF NOT EXISTS audit_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE UNIQUE,
    report_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pipeline_version TEXT,
    scoring_config_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_reports_audit_id ON audit_reports(audit_id);

COMMENT ON TABLE audit_reports IS 'Generated JSON risk report per audit; used by GET /audits/{id}/report';
