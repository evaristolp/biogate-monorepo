-- Week 6: compliance_certificates table for PDF certificate storage and verification.
-- certificate_id is the public ID used in GET /verify/{certificate_id}.

CREATE TABLE IF NOT EXISTS compliance_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    report_version INTEGER,
    pdf_hash_hex TEXT NOT NULL,
    signature_hex TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_compliance_certificates_id ON compliance_certificates(id);
CREATE INDEX IF NOT EXISTS idx_compliance_certificates_audit_id ON compliance_certificates(audit_id);

COMMENT ON TABLE compliance_certificates IS 'Generated Compliance Certificate PDFs: hash and signature for GET /verify/{certificate_id}';
