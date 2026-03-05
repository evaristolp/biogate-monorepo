-- Week 6: document_uploads table for file metadata and extraction method.
-- Populated when files are processed by the ingestion pipeline (upload, upload_and_audit, batch).

CREATE TABLE IF NOT EXISTS document_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID REFERENCES audits(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    file_size_bytes INTEGER,
    mime_type TEXT,
    extraction_method TEXT NOT NULL,
    vendors_extracted INTEGER NOT NULL DEFAULT 0,
    extraction_confidence REAL,
    processing_time_ms INTEGER,
    needs_review_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_uploads_audit_id ON document_uploads(audit_id);
CREATE INDEX IF NOT EXISTS idx_document_uploads_created_at ON document_uploads(created_at);

COMMENT ON TABLE document_uploads IS 'Metadata for each file processed by multi-format ingestion; links to audit when part of full audit';
