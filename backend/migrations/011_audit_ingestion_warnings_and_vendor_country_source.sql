-- Ingestion warnings on audit (BUG-01), optional row counts, and country_source on vendors (BUG-04).

-- Audits: structured ingestion warnings and row counts for certificate summary
ALTER TABLE audits
  ADD COLUMN IF NOT EXISTS ingestion_warnings JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS total_rows_uploaded INTEGER,
  ADD COLUMN IF NOT EXISTS rows_skipped INTEGER;

COMMENT ON COLUMN audits.ingestion_warnings IS 'Structured warnings from CSV/ingestion: empty_vendor_name, unknown_country, etc.';
COMMENT ON COLUMN audits.total_rows_uploaded IS 'Total data rows in uploaded file (for certificate summary).';
COMMENT ON COLUMN audits.rows_skipped IS 'Rows skipped (e.g. empty vendor_name) for certificate summary.';

-- Vendors: country source for footnote (uploaded vs enriched from watchlist)
ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS country_source TEXT;

COMMENT ON COLUMN vendors.country_source IS 'One of: uploaded, enriched from watchlist, unknown';
