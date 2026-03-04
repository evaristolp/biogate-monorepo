from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Tuple

from backend.audit_pipeline import run_audit_pipeline
from backend.ingestion.base import ExtractedVendor, ExtractionResult
from backend.ingestion.pipeline import process_document


def _extracted_vendors_to_rows(vendors: Iterable[ExtractedVendor]) -> list[dict[str, Any]]:
    """
    Convert ExtractedVendor records into the row shape expected by
    backend.audit_pipeline.run_audit_pipeline (i.e. the same canonical
    keys produced by parse_validated_csv()).
    """
    rows: List[dict[str, Any]] = []

    for v in vendors:
        # Prefer normalized_name when available, otherwise fall back to raw_name.
        name = (v.normalized_name or v.raw_name or "").strip()
        if not name:
            continue
        # Skip rows whose names are only punctuation/whitespace, mirroring
        # CSV validation behaviour.
        if not any(c.isalnum() for c in name):
            continue

        row: dict[str, Any] = {
            "vendor_name": name,
        }
        if v.country_hint:
            row["country"] = v.country_hint
        if v.parent_company_hint:
            row["parent_company"] = v.parent_company_hint
        if v.equipment_type_hint:
            # Map into product_category to align with existing optional columns.
            row["product_category"] = v.equipment_type_hint

        rows.append(row)

    return rows


def run_document_audit(
    file_path: str,
    supabase_client: Any,
    *,
    audit_id_hint: str = "document-audit",
    org_id_hint: str = "document-audit",
) -> Tuple[dict[str, Any] | None, ExtractionResult]:
    """
    High-level orchestrator: run multi-format ingestion and then feed the
    extracted vendors into the existing audit pipeline.

    Returns a tuple of (audit_result, extraction_result).
    - audit_result is the dict returned by run_audit_pipeline, or None if
      no valid vendor rows were extracted.
    - extraction_result is always returned so callers (API/CLI) can surface
      ingestion errors/warnings alongside audit output.
    """
    path = Path(file_path)
    extraction_result = process_document(str(path), audit_id=audit_id_hint, org_id=org_id_hint)

    rows = _extracted_vendors_to_rows(extraction_result.vendors)
    if not rows:
        # Surface ingestion metadata to caller; audit_result remains None so that
        # API / CLI layers can decide whether to treat this as a hard failure.
        return None, extraction_result

    audit_result = run_audit_pipeline(rows, supabase_client)
    return audit_result, extraction_result


__all__ = [
    "run_document_audit",
]

