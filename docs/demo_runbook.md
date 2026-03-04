## BioGate multi-format ingestion demo runbook

This runbook walks through a full demo of BioGate’s multi-format ingestion and
audit pipeline for an investor or stakeholder.

### 1. Prerequisites

- Python 3.12+
- Supabase project with:
  - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` available.
  - Migrations in `backend/migrations/` applied in order (001 → 004).
- Local `.env` at repo root:

```bash
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
ANTHROPIC_API_KEY=<key>   # optional, for Claude vendor normalization + PDF extraction
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
pip install -r scripts/requirements.txt
```

### 2. Prime the watchlists

Populate `watchlist_entities` and `watchlist_snapshots`:

```bash
python scripts/run_all_ingestion.py
```

This runs the BIS, OFAC, and UFLPA ingestion scripts and ensures the audit
pipeline has watchlist data to match against.

### 3. Start the API

From the repo root:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Verify health:

```bash
curl http://127.0.0.1:8000/health
```

If `BIOGATE_API_KEY` is set in the environment, include
`Authorization: Bearer <BIOGATE_API_KEY>` on protected routes.

### 4. CSV-based audit (baseline)

Use the existing CSV fixture to show the classic pipeline:

```bash
curl -X POST \
  -H "Authorization: Bearer $BIOGATE_API_KEY" \
  -F "file=@tests/fixtures/test_10_vendors.csv" \
  http://127.0.0.1:8000/audits/upload_and_audit
```

Highlight in the response:

- `audit_id` and `vendor_count`.
- `risk_summary` by tier.
- `vendors` entries for:
  - `BGI Research`, `Huawei Technologies`, `Complete Genomics`, etc.
- Optional `report` if the JSON risk report was generated and stored.

### 5. Multi-format ingestion (Excel)

Create or use a small Excel file with columns like:

- `Vendor Name`
- `Country`
- `Product`

For example (conceptual structure):

| Vendor Name       | Country | Product                |
|-------------------|---------|------------------------|
| BGI Genomics      | CN      | Sequencing instruments |
| Acme Biotech LLC  | US      | PCR reagents           |

Run ingestion-only preview:

```bash
curl -X POST \
  -H "Authorization: Bearer $BIOGATE_API_KEY" \
  -F "file=@/path/to/vendors.xlsx" \
  http://127.0.0.1:8000/audits/upload
```

Call out in the response:

- `vendors_extracted` (should match the number of valid rows).
- `extraction_method: "EXCEL_PARSER"`.
- Any `warnings` about skipped or malformed rows.

Run a full audit on the same Excel file:

```bash
curl -X POST \
  -H "Authorization: Bearer $BIOGATE_API_KEY" \
  -F "file=@/path/to/vendors.xlsx" \
  http://127.0.0.1:8000/audits/upload_and_audit
```

Explain:

- The ingestion engine converted Excel rows into canonical vendor records.
- The audit pipeline then:
  - Applied normalization (optional Claude, if configured).
  - Performed fuzzy and exact watchlist matching.
  - Applied the risk scoring engine and parent company graph.
- The response mirrors the CSV audit shape, with an `ingestion` block providing
  extraction metadata.

### 6. Multi-format ingestion (PDF text)

Use a text-based PDF (e.g. purchase order or vendor list). The PDF should have
vendor/company names and optional country hints in text or simple tables.

Preview ingestion:

```bash
curl -X POST \
  -H "Authorization: Bearer $BIOGATE_API_KEY" \
  -F "file=@/path/to/vendors.pdf" \
  http://127.0.0.1:8000/audits/upload
```

Discuss:

- `extraction_method: "PDF_TEXT"`.
- `vendors_extracted` and `needs_review`.
- `warnings` if Claude is unavailable (e.g. missing `ANTHROPIC_API_KEY`).

Run a full audit:

```bash
curl -X POST \
  -H "Authorization: Bearer $BIOGATE_API_KEY" \
  -F "file=@/path/to/vendors.pdf" \
  http://127.0.0.1:8000/audits/upload_and_audit
```

### 7. Inspect stored JSON risk report

Given an `audit_id` from a CSV/Excel/PDF upload:

```bash
curl -H "Authorization: Bearer $BIOGATE_API_KEY" \
  http://127.0.0.1:8000/audits/<audit_id>/report
```

Show:

- `report_metadata.pipeline_version` and `scoring_config_version`.
- `summary.vendors_by_tier` and `overall_risk_assessment`.
- An example `vendors` entry with:
  - `raw_input_name`, `normalized_name`, `country`, `parent_company`.
  - `risk_tier` vs `effective_tier`.
  - `match_evidence` and any override history.

### 8. Known limitations (v1)

- Image, email, and DOCX handlers are wired but do not yet perform automatic
  vendor extraction; they surface clear warnings instead.
- PDF extraction relies on Claude when `ANTHROPIC_API_KEY` is configured; in
  environments without that key, PDF ingestion will typically yield zero
  vendors (but will never crash the API).
- Multi-format CLI for end-to-end audits is not yet exposed as a separate
  script; use the FastAPI `POST /audits/upload_and_audit` endpoint for full
  demos.

