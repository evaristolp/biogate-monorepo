"""
Helper script to run a single BioGate audit from a CSV file.

Adds simple path validation and prints the current working directory so that
file-not-found errors are easier to diagnose.

Usage:
    python scripts/run_audit.py path/to/vendors.csv
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_audit.py path/to/vendors.csv", file=sys.stderr)
        sys.exit(1)

    # Ensure repo root is on sys.path so `backend` imports work no matter
    # where this script is invoked from.
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    csv_path_arg = sys.argv[1]
    cwd = os.getcwd()
    print(f"[run_audit] Current working directory: {cwd}")
    print(f"[run_audit] Requested CSV path: {csv_path_arg}")

    csv_path = Path(csv_path_arg)
    if not csv_path.is_absolute():
        csv_path = Path(cwd) / csv_path

    if not csv_path.exists():
        print(f"[run_audit] ERROR: CSV file not found at: {csv_path}", file=sys.stderr)
        sys.exit(2)

    # Load env so backend.main/audit_pipeline can see SUPABASE_URL, etc.
    load_dotenv(repo_root / ".env")

    # Lazy imports so this script has minimal startup cost.
    from backend.audits_schema import parse_validated_csv, validate_csv
    from backend.audit_pipeline import run_audit_pipeline
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print(
            "[run_audit] ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env",
            file=sys.stderr,
        )
        sys.exit(3)

    client = create_client(supabase_url, supabase_key)

    content = csv_path.read_text(encoding="utf-8")
    result = validate_csv(content)
    if not result.valid:
        print("[run_audit] CSV validation failed:")
        for err in result.errors:
            print(f"  - {err['code']}: {err['message']}")
        sys.exit(4)

    rows = parse_validated_csv(content)
    print(f"[run_audit] Parsed {len(rows)} vendor rows from {csv_path}")

    audit_result = run_audit_pipeline(rows, client)
    print("[run_audit] Audit completed.")
    print(f"  Audit ID: {audit_result.get('audit_id')}")
    print(f"  Vendor count: {audit_result.get('vendor_count')}")
    print(f"  Risk summary: {audit_result.get('risk_summary')}")


if __name__ == "__main__":
    main()

