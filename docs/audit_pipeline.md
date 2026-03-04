## BioGate audit pipeline README

This document describes the end-to-end CLI audit pipeline implemented in the monorepo as of Phase 1 / Week 5.

- **Entry point**: `scripts/run_audit.py`
- **Core pipeline**: `backend/audit_pipeline.py`
- **Schema / validation**: `backend/audits_schema.py`
- **Risk scoring**: `backend/scoring/risk_engine.py`, `backend/scoring/parent_graph.py`, `backend/config/scoring_config.py`
- **Report generation**: `backend/report.py`, `backend/schemas/risk_report.py`
- **Watchlists**: `scripts/ingest_bis.py`, `scripts/ingest_ofac.py`, `scripts/ingest_uflpa.py`

### 1. Data sources

- **BIS Entity List / OFAC SDN / UFLPA**: ingested into the `watchlist_entities` and `watchlist_snapshots` tables by the ingestion scripts under `scripts/`.
- **Vendor CSV**: user-supplied CSV containing vendor names (and optional countries), validated by `backend.audits_schema`.
- **Overrides and parent graph**:
  - Manual overrides stored in `vendor_overrides`.
  - Parent company relationships in `backend/scoring/parent_graph.py`.

### 2. Environment and configuration

- Required env vars (typically in `.env` at repo root):
  - `SUPABASE_URL` (must be `https://...`)
  - `SUPABASE_SERVICE_ROLE_KEY`
- Optional:
  - `ANTHROPIC_API_KEY` for Claude-powered vendor normalization.
- Configuration:
  - `backend/config/scoring_config.py` defines thresholds, weights, and country-of-concern lists.

### 3. CLI runner (`scripts/run_audit.py`)

Recommended usage:

```bash
python scripts/run_audit.py --input vendors.csv --output report.json
```

Behaviour:

1. Resolves the repository root and loads `.env`.
2. Validates the input CSV using `validate_csv`; on error, prints codes/messages and exits non-zero.
3. Parses rows with `parse_validated_csv`.
4. Creates a Supabase client and calls `backend.audit_pipeline.run_audit_pipeline(rows, client)`.
5. Prints a summary (audit id, vendor count, risk summary).
6. If `--output` is provided and a JSON risk report is available, writes it to the given path.

The script works from a clean checkout as long as Python deps are installed and the required env vars are set.

### 4. Core pipeline (`backend/audit_pipeline.py`)

High-level steps:

1. **Guardrails**:
   - Verifies `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present.
   - Enforces `SUPABASE_URL` to use `https://`.
2. **Audit creation**:
   - Inserts a new row into `audits` with `status="processing"` and timestamps.
3. **Vendor insertion**:
   - Normalizes vendor names with `normalize_vendor_name` and stores `raw_input_name` and `normalized_name` in `vendors`.
4. **Claude normalization (optional)**:
   - Batch-calls `vendor_normalizer.normalize_vendors` when available and safe (no running event loop).
   - Enriches vendors with country, parent company, and equipment type hints.
5. **Matching and scoring (per vendor)**:
   - BIOSECURE direct-match shortcut (named entities → **Red** without fuzzy match).
   - Exact match by stripped corporate suffixes.
   - Fuzzy match via `scripts.fuzzy_match` for remaining cases.
   - Parent company expansion via `resolve_parent_chain` and a second match pass on parent names.
   - Risk scoring via `score_vendor`, producing:
     - `risk_tier`, `effective_score`, `match_evidence`, `risk_reasoning`, and optional `risk_source` / `parent_match_evidence`.
   - Robust error handling:
     - Any failure during matching or scoring for a vendor is logged with the vendor index.
     - That vendor is still updated in the DB with a conservative **Yellow** tier and explanatory `risk_reasoning`.
6. **Batch upsert**:
   - Vendor updates are written back to `vendors` in batches of 500 using upsert on `id`.
7. **Audit completion**:
   - `audits.status` updated to `"complete"` with `completed_at` timestamp.
8. **JSON risk report + versioning**:
   - Calls `backend.report.generate_risk_report` to build a schema-validated report.
   - Looks up existing `audit_reports` rows for this `audit_id` to determine the next integer `version`.
   - Inserts a new row into `audit_reports` with:
     - `audit_id`, `version`, `report_json`, `pipeline_version`, `scoring_config_version`.
   - This preserves a full history of report versions for a given audit.
9. **Return shape**:
   - Returns a dict containing:
     - `audit_id`, `vendor_count`, `risk_summary`, `vendors`, and `report` (risk report dict, or `None` on failure).

### 5. JSON risk report (`backend/report.py`)

Responsibilities:

- Fetches audit and vendor rows for a given `audit_id`.
- Fetches and aggregates override history from `vendor_overrides`.
- Fetches watchlist metadata from `watchlist_snapshots`.
- Computes effective tiers, recommendations, and summary statistics.
- Produces:
  - `report_metadata` (including `pipeline_version` and `scoring_config_version`),
  - `watchlist_metadata`,
  - `summary`,
  - `vendors`,
  - `disclaimers`.
- Validates the final report against `backend/schemas/risk_report_schema.json` using `jsonschema`.

### 6. Error handling guarantees

- Missing or non-HTTPS Supabase URL → hard failure with clear message.
- Failure to create the audit or insert vendors → hard failure.
- Per-vendor failures (matching or scoring) are:
  - Logged with vendor index.
  - Defaulted to Yellow with explanatory `risk_reasoning`.
- Failure to generate or store the risk report is logged but does not prevent the audit from completing; the CLI will still receive vendor-level results.

### 7. Logging and security

- Logs are designed to avoid leaking raw vendor names:
  - Matching and scoring logs reference vendor indices and aggregate stats (scores, counts).
- All Supabase traffic is forced over HTTPS via the `SUPABASE_URL` scheme check.
- Secrets (Supabase keys, API keys) are loaded from environment variables, not hardcoded.

