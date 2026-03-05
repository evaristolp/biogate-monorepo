#!/usr/bin/env python3
"""
Run a batch audit on messy CSV + PDF fixtures and print quality/robustness analysis.

Usage (from repo root):
  python scripts/run_batch_audit_test.py

Requires: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for full audit pipeline.
Without Supabase: set DRY_RUN=1 to only run ingestion and print extraction results.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

FIXTURES = _REPO_ROOT / "tests" / "fixtures"
MESSY_CSV = FIXTURES / "messy_vendors.csv"
MESSY_PDF = FIXTURES / "purchase_order.pdf"


def main() -> None:
    dry_run = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    if not MESSY_CSV.exists():
        print("ERROR: tests/fixtures/messy_vendors.csv not found")
        sys.exit(1)

    if not MESSY_PDF.exists():
        MESSY_PDF.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n"
        )
        print("Created minimal tests/fixtures/purchase_order.pdf for testing")

    paths = [str(MESSY_CSV)]
    if MESSY_PDF.exists():
        paths.append(str(MESSY_PDF))

    from backend.ingestion.orchestrator import run_document_audit_from_paths

    if dry_run:
        from backend.ingestion.pipeline import process_document

        print("--- DRY RUN: Ingestion only (no Supabase) ---\n")
        all_vendors = []
        all_errors = []
        all_warnings = []
        for p in paths:
            result = process_document(p, audit_id="dry-run", org_id="dry-run")
            all_vendors.extend(result.vendors)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            print(f"  {Path(p).name}: {len(result.vendors)} vendors")

        print(f"\nMerged: {len(all_vendors)} vendors total")
        for v in all_vendors[:12]:
            print(f"  - {v.raw_name!r}  (country={v.country_hint})")
        if all_warnings:
            print("\nWarnings:", all_warnings[:5])
        return

    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for full audit, or DRY_RUN=1 for ingestion-only.")
        sys.exit(1)

    supabase = create_client(url, key)
    audit_result, extraction_result = run_document_audit_from_paths(
        paths, supabase, audit_id_hint="batch-test", org_id_hint="api-user"
    )

    if audit_result is None:
        print("No vendors extracted.")
        print("Errors:", extraction_result.errors)
        sys.exit(1)

    print("--- Batch audit results ---\n")
    print(f"Audit ID: {audit_result['audit_id']}")
    print(f"Vendor count: {audit_result['vendor_count']}")
    print(f"Risk summary: {audit_result['risk_summary']}")
    if extraction_result.warnings:
        print("Warnings:", extraction_result.warnings[:5])
    for v in audit_result.get("vendors", [])[:10]:
        print(f"  {v.get('raw_input_name')} -> tier={v.get('risk_tier')}")


if __name__ == "__main__":
    main()
