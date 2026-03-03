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
   - `curl -X POST -F "file=@tests/fixtures/test_10_vendors.csv" http://127.0.0.1:8000/audits/upload`
   - Response includes `audit_id`, `risk_summary`, and `vendors` with `risk_tier` and `match_evidence`.

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
