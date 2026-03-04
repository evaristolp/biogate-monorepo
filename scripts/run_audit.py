"""
CLI entrypoint for running the BioGate multi-format ingestion pipeline.

Usage (preferred):
    python scripts/run_audit.py --input vendors.csv --output extraction.json

For backwards compatibility, a single positional argument still works:
    python scripts/run_audit.py vendors.csv
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the BioGate ingestion pipeline on a document.")
    parser.add_argument(
        "--input",
        "-i",
        dest="input_path",
        help="Path to input document (CSV, Excel, PDF, image, email, DOCX).",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_path",
        help="Path to write JSON extraction result (optional).",
    )
    parser.add_argument(
        "positional_input",
        nargs="?",
        help="(Deprecated) Positional path to input document.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args(sys.argv[1:])
    input_arg = args.input_path or args.positional_input
    if not input_arg:
        print(
            "Usage: python scripts/run_audit.py --input vendors.csv [--output extraction.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Ensure repo root is on sys.path so `backend` imports work no matter
    # where this script is invoked from.
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    cwd = os.getcwd()
    print(f"[run_audit] Current working directory: {cwd}")
    print(f"[run_audit] Requested input path: {input_arg}")

    input_path = Path(input_arg)
    if not input_path.is_absolute():
        input_path = Path(cwd) / input_path

    if not input_path.exists():
        print(f"[run_audit] ERROR: Input file not found at: {input_path}", file=sys.stderr)
        sys.exit(2)

    # Load env so ingestion and normalization can see API keys, etc.
    load_dotenv(repo_root / ".env")

    from backend.ingestion.pipeline import process_document

    result = process_document(str(input_path), audit_id="cli-run", org_id="cli-user")

    vendor_count = len(result.vendors)
    extraction_method = (
        result.extraction_method.value if hasattr(result.extraction_method, "value") else str(result.extraction_method)
    )
    avg_conf = result.extraction_confidence
    processing_ms = result.processing_time_ms

    print("[run_audit] Ingestion completed.")
    print(f"  Vendor count: {vendor_count}")
    print(f"  Extraction method: {extraction_method}")
    print(f"  Average confidence: {avg_conf:.3f}")
    print(f"  Processing time (ms): {processing_ms}")

    output_path = args.output_path
    if output_path:
        out_path = Path(output_path)
        if not out_path.is_absolute():
            out_path = Path(cwd) / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(result)
        em = payload.get("extraction_method")
        if em is not None:
            payload["extraction_method"] = getattr(em, "value", str(em))
        out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(f"[run_audit] Wrote JSON extraction result to: {out_path}")


if __name__ == "__main__":
    main()


