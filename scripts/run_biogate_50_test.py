"""
Run the BioGate audit pipeline against data/biogate_50_company_test_set.csv
and compare actual tiers to the expected_tier column.

Usage (from repo root):
    python scripts/run_biogate_50_test.py
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _csv_path() -> Path:
    return _repo_root() / "data" / "biogate_50_company_test_set.csv"


def main() -> None:
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    load_dotenv(repo_root / ".env")

    from supabase import create_client
    from backend.audit_pipeline import run_audit_pipeline

    csv_path = _csv_path()
    if not csv_path.exists():
        print(f"[biogate_50_test] CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print(
            "[biogate_50_test] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env",
            file=sys.stderr,
        )
        sys.exit(2)

    client = create_client(supabase_url, supabase_key)

    # Load fixture CSV
    rows: list[Dict[str, Any]] = []
    expected: Dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vendor_name = (row.get("vendor_name") or "").strip()
            country = (row.get("country") or "").strip() or None
            exp_tier = (row.get("expected_tier") or "").strip().lower()
            if not vendor_name:
                continue
            rows.append({"vendor_name": vendor_name, "country": country})
            if exp_tier:
                expected[vendor_name] = exp_tier

    if not rows:
        print("[biogate_50_test] No vendor rows parsed from CSV", file=sys.stderr)
        sys.exit(3)

    print(f"[biogate_50_test] Parsed {len(rows)} vendor rows from {csv_path}")

    result = run_audit_pipeline(rows, client)
    vendors = result.get("vendors") or []
    by_name: Dict[str, Dict[str, Any]] = {v.get("raw_input_name"): v for v in vendors}

    mismatches: list[str] = []
    missing: list[str] = []
    for vendor_name, exp_tier in expected.items():
        v = by_name.get(vendor_name)
        if not v:
            missing.append(vendor_name)
            continue
        actual = (v.get("risk_tier") or "green").lower()
        eff = (v.get("effective_tier") or actual).lower()
        if eff != exp_tier:
            mismatches.append(
                f"{vendor_name}: expected={exp_tier}, risk_tier={actual}, effective_tier={eff}"
            )

    print(f"[biogate_50_test] Audit ID: {result.get('audit_id')}")
    print(f"[biogate_50_test] Vendor count: {result.get('vendor_count')}")
    print(f"[biogate_50_test] Risk summary: {result.get('risk_summary')}")

    if missing:
        print("\n[biogate_50_test] Vendors missing from audit result:")
        for name in missing:
            print(f"  - {name}")

    if mismatches:
        print("\n[biogate_50_test] Tier mismatches:")
        for line in mismatches:
            print(f"  - {line}")
        sys.exit(4)

    print("\n[biogate_50_test] All expected tiers match effective tiers.")


if __name__ == "__main__":
    main()

