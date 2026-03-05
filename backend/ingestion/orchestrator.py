from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Tuple

from backend.audit_pipeline import run_audit_pipeline
from backend.ingestion.base import ExtractedVendor, ExtractionMethod, ExtractionResult
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


def run_document_audit_from_paths(
    file_paths: List[str],
    supabase_client: Any,
    *,
    audit_id_hint: str = "document-audit",
    org_id_hint: str = "document-audit",
) -> Tuple[dict[str, Any] | None, ExtractionResult]:
    """
    Run a single audit from multiple source files (e.g. a folder of CSVs, PDFs, images).

    Each file is processed by the ingestion pipeline; all extracted vendors are
    merged and fed into one audit. Errors and warnings are aggregated across
    sources (with source filename prefix). Returns the same shape as
    run_document_audit; extraction_method is MULTIPLE when len(file_paths) > 1.
    """
    if not file_paths:
        empty = ExtractionResult(extraction_method=ExtractionMethod.MULTIPLE)
        empty.errors.append("No files provided")
        return None, empty

    all_vendors: List[ExtractedVendor] = []
    all_errors: List[str] = []
    all_warnings: List[str] = []
    total_ms = 0
    methods_used: List[str] = []
    last_result: ExtractionResult | None = None

    for file_path in file_paths:
        path = Path(file_path)
        name = path.name
        result = process_document(str(path), audit_id=audit_id_hint, org_id=org_id_hint)
        last_result = result
        all_vendors.extend(result.vendors)
        for e in result.errors:
            all_errors.append(f"[{name}] {e}")
        for w in result.warnings:
            all_warnings.append(f"[{name}] {w}")
        total_ms += result.processing_time_ms or 0
        if result.extraction_method and result.extraction_method != ExtractionMethod.MULTIPLE:
            methods_used.append(result.extraction_method.value)

    single_method = last_result.extraction_method if (len(file_paths) == 1 and last_result) else ExtractionMethod.MULTIPLE
    combined = ExtractionResult(
        vendors=all_vendors,
        extraction_method=single_method,
        extraction_confidence=sum(v.extraction_confidence for v in all_vendors) / len(all_vendors) if all_vendors else 0.0,
        processing_time_ms=total_ms,
        errors=all_errors,
        warnings=all_warnings,
    )
    if len(file_paths) > 1 and methods_used:
        combined.warnings.insert(0, f"Processed {len(file_paths)} sources: {', '.join(methods_used)}")

    rows = _extracted_vendors_to_rows(combined.vendors)
    if not rows:
        return None, combined

    audit_result = run_audit_pipeline(rows, supabase_client)
    return audit_result, combined


__all__ = [
    "run_document_audit",
    "run_document_audit_from_paths",
]

