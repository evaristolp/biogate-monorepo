# BioGate

BIOSECURE Act / UFLPA vendor screening: CSV upload → normalization → watchlist fuzzy match → risk tiers.

## Repo layout

- **backend/** — FastAPI app (`/health`, `/audits/upload`), audit pipeline, migrations
- **scripts/** — Watchlist ingestion (BIS, OFAC, UFLPA), fuzzy match, `run_all_ingestion.py`
- **data/** — UFLPA entity JSON and sample data
- **frontend/** — Placeholder for future UI
- **tests/** — Integration tests (10-vendor CSV, risk tiers), fixtures

## Prerequisites

- Python 3.12+
- Supabase project (for DB and optional pgvector)
- `.env` at repo root (see below)

## Setup (fresh checkout)

1. **Clone and enter repo**
   ```bash
   git clone <repo-url>
   cd biogate-monorepo
   ```

2. **Create `.env`** (do not commit; use `.env.example` as template if provided)
   ```bash
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
   ANTHROPIC_API_KEY=<key>   # optional, for Claude vendor normalization
   ```
   **Important:** Use the **service role** key (Project Settings → API → `service_role` secret), not the anon/public key. The backend needs it to create audits and write to the database.

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   pip install -r scripts/requirements.txt
   ```

4. **Apply database migrations**  
   Run the SQL in `backend/migrations/` in order (001 → … → 009) in the Supabase SQL Editor (or your migration tool).

5. **Run watchlist ingestion** (populates `watchlist_entities` and `watchlist_snapshots`)
   ```bash
   python scripts/run_all_ingestion.py
   ```

6. **Start the API**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

7. **Submit a CSV**
   - CSV must include a `vendor_name` column; optional: `country`, `supplier_id`, etc.
   - Example: `tests/fixtures/test_10_vendors.csv`
   - `curl -X POST -F "file=@tests/fixtures/test_10_vendors.csv" http://127.0.0.1:8000/audits/upload_and_audit"`
   - Response includes `audit_id`, `risk_summary`, and `vendors` with `risk_tier` and `match_evidence`.

## Multi-format ingestion

- **Supported formats (v1)**: CSV, Excel (`.xlsx` / `.xls`), text-based PDF, images (vision), email (body + attachments re-routed through pipeline). DOCX is wired but vendor extraction is experimental.
- **Document uploads**: Each processed file is recorded in `document_uploads` (file metadata, extraction method, vendors extracted, confidence).
- **Ingestion-only API** (for preview / QA):
  - `POST /audits/upload` with multipart `file` (CSV, Excel, PDF, image, email, DOCX).
  - Returns extraction metadata only:
    - `status`, `vendors_extracted`, `errors`, `warnings`, `extraction_method`, `confidence`, `processing_time_ms`, `needs_review`.
- **Full audit API** (multi-format → Supabase audit pipeline):
  - `POST /audits/upload_and_audit` with multipart `file` (CSV, Excel, text-based PDF).
  - Runs the ingestion engine, then feeds extracted vendors into `run_audit_pipeline`.
  - Response matches the CSV path plus an `ingestion` block:
    - Top-level: `audit_id`, `vendor_count`, `risk_summary`, `vendors`, `report`, `certificate_id`, `certificate_pdf_base64`.
    - `ingestion`: `vendors_extracted`, `errors`, `warnings`, `extraction_method`, `confidence`, `processing_time_ms`, `needs_review`.
- **Multi-source (folder) audit**: One audit from many files (e.g. a folder of CSVs, PDFs, receipts):
  - `POST /audits/upload_and_audit_batch` with multipart `files` (one or more files).
  - All extracted vendors are merged into a single audit; errors/warnings are prefixed by filename.
  - Same response shape as `upload_and_audit`, with `ingestion.sources_processed` and `extraction_method: "MULTIPLE"`.
  - Example: `curl -X POST -F "files=@vendors.csv" -F "files=@invoice.pdf" -F "files=@receipt.jpg" http://127.0.0.1:8000/audits/upload_and_audit_batch`

### CLI examples

- **Ingestion-only (debugging vendor extraction)**:

  ```bash
  python scripts/run_audit.py --input path/to/vendors.xlsx --output extraction.json
  ```

- **End-to-end document audit (multi-format → Supabase)**:

  A dedicated CLI wrapper can be added to call `backend.ingestion.orchestrator.run_document_audit` with your Supabase credentials; for now, use the FastAPI endpoint `POST /audits/upload_and_audit` as shown above.

## Compliance Certificate (Week 6)

- After each audit, a **Compliance Certificate** PDF is generated (WeasyPrint) with BioGate letterhead, audit date, org name, watchlist sources, full vendor table with tiers and evidence, attestation, and a verification QR code.
- The PDF hash is signed with `BIOGATE_CERTIFICATE_PRIVATE_KEY` (PEM). Set `BIOGATE_CERTIFICATE_PUBLIC_KEY` for signature verification.
- **GET /verify/{certificate_id}** (public) returns JSON: `certificate_id`, `audit_id`, `issued_at`, `pdf_hash`, `signature_valid`.
- Optional env: `BIOGATE_BASE_URL` (default `http://localhost:8000`) for the verification URL embedded in the QR code.
- The audit response includes `certificate_id` and `certificate_pdf_base64`; decode and save as PDF to open in Adobe Reader.

### Email delivery (optional)

- **Single-file and batch audit** endpoints accept an optional form field `email`. When set and SMTP is configured, the backend sends one email to that address with the risk summary and the Compliance Certificate PDF attached.
- **Env vars** (all optional; if any are missing, email is skipped and no error is raised):
  - `BIOGATE_EMAIL_FROM` — From address (e.g. `noreply@biogate.us`)
  - `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASSWORD`
- Example: `curl -X POST -F "file=@vendors.csv" -F "email=you@example.com" http://127.0.0.1:8000/audits/upload_and_audit`

## Tests

- **Unit + integration (requires Supabase env)**  
  `pytest`

- **Unit only (no Supabase)**  
  `SUPABASE_URL= SUPABASE_SERVICE_ROLE_KEY= pytest`  
  (integration tests are skipped)

## CI

- **GitHub Actions**  
  `.github/workflows/ci.yml` runs on push: install deps, import API, run `pytest`.  
  `.github/workflows/daily_ingestion.yml` runs at 02:00 UTC: `python scripts/run_all_ingestion.py` using repo secrets.

## Schema

Migrations in `backend/migrations/` define:

- `organizations`, `audits`, `vendors` (audit pipeline)
- `watchlist_entities`, `watchlist_snapshots` (watchlist ingestion)
- `document_uploads` (file metadata per ingestion; Week 6)
- `audit_reports`, `compliance_certificates` (risk report + certificate verification)
- `vendor_embeddings` (pgvector, optional)

Run them in order to recreate the schema from scratch.

## Troubleshooting

### "Permission denied for table audits" (or similar) on upload

The backend must connect to Supabase with the **service role** key, not the anon key. The service role bypasses Row Level Security and has full access to tables.

- **Fix:** Set `SUPABASE_SERVICE_ROLE_KEY` to the **service_role** secret from Supabase: **Project Settings → API** → under "Project API keys", copy the `service_role` key (marked secret). Do not use the `anon` public key.
- After updating the env var, restart the backend (or redeploy). Uploads should then succeed.
