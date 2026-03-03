# Daily Watchlist Ingestion – Troubleshooting

## How to find the exact error in GitHub Actions

1. **Open your repo on GitHub** → **Actions** tab.
2. Click the **"Daily Watchlist Ingestion"** workflow in the left sidebar (or the failed run in the list).
3. Click the **failed run** (red X).
4. Click the **"ingest"** job (failed job).
5. Expand **"Run all ingestion scripts"**. The step output shows:
   - Which ingestion started (BIS → OFAC → UFLPA).
   - The **full Python traceback** if a script raised an exception.
6. Look for:
   - `Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY` → secrets not set or wrong names.
   - `Download failed` / `404` / `ConnectionError` → source URL or network issue.
   - `CSL missing required columns` / `Only N ... entities (minimum M)` → CSV format or filter changed.
   - `Delete failed` / `Insert failed` → Supabase permissions or schema.

**Quick link:**  
`https://github.com/<owner>/<repo>/actions/workflows/daily_ingestion.yml`

---

## Supabase environment variables

The workflow is configured correctly. It passes secrets into the run step:

```yaml
- name: Run all ingestion scripts
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  run: python scripts/run_all_ingestion.py
```

**You must add these repository secrets:**

1. **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret** for each:
   - `SUPABASE_URL` – e.g. `https://xxxx.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` – from Supabase Dashboard → **Settings** → **API** (use **service_role**, not anon).

If either secret is missing, the first script (BIS) will exit immediately with  
`Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env`.

---

## Government source URL changes

BIS and OFAC ingestion use the **Consolidated Screening List (CSL)** CSV from trade.gov.

- **Current official CSV:**  
  `https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv`
- If the URL or CSV format changes again, update:
  - `scripts/ingest_bis.py` → `CSL_CSV_URL` and/or column handling in `parse_csv`.
  - `scripts/ingest_ofac.py` → same.

See [trade.gov Consolidated Screening List](https://www.trade.gov/consolidated-screening-list) for links and updates.
