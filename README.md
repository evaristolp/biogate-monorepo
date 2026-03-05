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

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   pip install -r scripts/requirements.txt
   ```

4. **Apply database migrations**  
   Run the SQL in `backend/migrations/` in order (001 → 002 → 003 → 004) in the Supabase SQL Editor (or your migration tool).

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

- **Supported formats (v1)**: CSV, Excel (`.xlsx` / `.xls`), text-based PDF. Image, email, and DOCX ingestion are wired but vendor extraction is currently experimental (no automatic vendors returned yet).
- **Ingestion-only API** (for preview / QA):
  - `POST /audits/upload` with multipart `file` (CSV, Excel, PDF, image, email, DOCX).
  - Returns extraction metadata only:
    - `status`, `vendors_extracted`, `errors`, `warnings`, `extraction_method`, `confidence`, `processing_time_ms`, `needs_review`.
- **Full audit API** (multi-format → Supabase audit pipeline):
  - `POST /audits/upload_and_audit` with multipart `file` (CSV, Excel, text-based PDF).
  - Runs the ingestion engine, then feeds extracted vendors into `run_audit_pipeline`.
  - Response matches the CSV path plus an `ingestion` block:
    - Top-level: `audit_id`, `vendor_count`, `risk_summary`, `vendors`, `report`.
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
- `vendor_embeddings` (pgvector, optional)

Run them in order to recreate the schema from scratch.
