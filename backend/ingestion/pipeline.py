from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from backend.ingestion.base import (
    ExtractionMethod,
    ExtractionResult,
    ExtractedVendor,
)
from backend.ingestion.router import detect_handler, is_pdf_text_extractable
from backend.ingestion.handlers.excel import extract_from_excel
from backend.ingestion.handlers.pdf_text import extract_from_pdf_text
from backend.ingestion.handlers.vision import extract_from_vision
from backend.ingestion.handlers.email import extract_from_email
from backend.ingestion.handlers.docx import extract_from_docx
from backend.audits_schema import parse_validated_csv_with_warnings, validate_csv

logger = logging.getLogger(__name__)


def normalize_extracted_vendors(vendors: Iterable[ExtractedVendor]) -> None:
    """
    Enrich ExtractedVendor records using the existing normalization batch function.

    Bridges ingestion-layer ExtractedVendor objects to the Claude-powered
    normalization that operates on raw vendor names.
    """
    vendor_list: List[ExtractedVendor] = list(vendors)
    if not vendor_list:
        return

    raw_names = [v.raw_name for v in vendor_list]

    # Primary path: dedicated batch normalizer (if present).
    normalizer_results: List[dict] = []
    try:
        from backend.normalize import normalize_vendors_batch  # type: ignore[attr-defined]

        try:
            normalizer_results = normalize_vendors_batch(raw_names)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("normalize_vendors_batch failed, falling back to async normalizer: %s", exc)
            normalizer_results = []
    except Exception:  # pragma: no cover - defensive
        # Fall back to the async vendor_normalizer if the batch API is not available.
        try:
            from backend.vendor_normalizer import normalize_vendors

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                logger.warning("Skipping vendor normalization in async context (event loop already running).")
                normalizer_results = []
            else:
                normalizer_results = asyncio.run(normalize_vendors(raw_names))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Vendor normalization unavailable; proceeding with raw extracted names: %s", exc)
            normalizer_results = []

    if not normalizer_results:
        return

    by_raw = {str(item.get("raw_name") or "").strip(): item for item in normalizer_results}

    for vendor in vendor_list:
        key = (vendor.raw_name or "").strip()
        if not key:
            continue
        data = by_raw.get(key)
        if not data:
            continue

        normalized_name = (data.get("normalized_name") or "").strip() or None
        country_hint = (data.get("country_hint") or "").strip() or None
        parent_company_hint = (data.get("parent_company_hint") or "").strip() or None
        equipment_type_hint = (data.get("equipment_type_hint") or "").strip() or None

        if normalized_name:
            vendor.normalized_name = normalized_name
        if country_hint and not vendor.country_hint:
            vendor.country_hint = country_hint
        if parent_company_hint and not vendor.parent_company_hint:
            vendor.parent_company_hint = parent_company_hint
        if equipment_type_hint and not vendor.equipment_type_hint:
            vendor.equipment_type_hint = equipment_type_hint


def _csv_to_extraction_result(file_path: str) -> ExtractionResult:
    result = ExtractionResult(extraction_method=ExtractionMethod.CSV_PARSER)

    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        msg = f"Failed to read CSV file: {exc}"
        logger.error(msg)
        result.errors.append(msg)
        return result

    validation = validate_csv(content)
    if validation.errors:
        # Surface row-level data quality problems even when the file is still ingestible.
        for err in validation.errors:
            result.errors.append(
                f"{err.code}: {err.message}"
                + (f" (row={err.row}, column={err.column})" if err.row or err.column else "")
            )

        rows_with_issues = sorted({e.row for e in validation.errors if e.row is not None})
        if rows_with_issues:
            result.warnings.append(
                f"CSV contains {len(rows_with_issues)} row(s) with validation issues; invalid rows may be skipped."
            )

    if not validation.valid:
        result.warnings.append("CSV validation failed; no vendors extracted.")
        return result

    rows, ingestion_warnings = parse_validated_csv_with_warnings(content)
    vendors: List[ExtractedVendor] = []

    for idx, row in enumerate(rows, start=1):
        raw_name = (row.get("vendor_name") or "").strip()
        if not raw_name:
            continue

        vendor = ExtractedVendor(
            raw_name=raw_name,
            country_hint=(row.get("country") or None),
            parent_company_hint=(row.get("parent_company") or None),
            equipment_type_hint=(row.get("product_category") or None),
            extraction_confidence=0.9,
            source_context=f"CSV row {idx + 1}",  # +1 for header row
        )
        vendors.append(vendor)

    result.vendors = vendors
    result.ingestion_warnings_structured = ingestion_warnings
    rows_skipped = len([w for w in ingestion_warnings if w.get("warning_type") == "empty_vendor_name"])
    result.rows_skipped = rows_skipped
    result.total_rows_uploaded = len(rows) + rows_skipped
    if vendors:
        result.extraction_confidence = sum(v.extraction_confidence for v in vendors) / len(vendors)
    else:
        result.warnings.append("No vendor rows found in CSV.")

    return result


def process_document(file_path: str, audit_id: str, org_id: str) -> ExtractionResult:
    """
    Main ingestion orchestrator for all document types.

    Detects the appropriate handler for the given file, delegates extraction,
    normalizes vendor entities, and returns a unified ExtractionResult.
    """
    start = time.perf_counter()

    handler_name, mime_type = detect_handler(file_path)
    logger.info(
        "Processing document via ingestion pipeline",
        extra={
            "audit_id": audit_id,
            "org_id": org_id,
            "file_path": file_path,
            "handler_name": handler_name,
            "mime_type": mime_type,
        },
    )

    if handler_name == "csv_parser":
        result = _csv_to_extraction_result(file_path)
    elif handler_name == "excel_parser":
        result = extract_from_excel(file_path)
    elif handler_name in {"pdf_parser", "pdf_text_parser", "pdf_vision_parser"}:
        # Support both legacy 'pdf_parser' and the newer split handlers.
        use_text = handler_name == "pdf_text_parser"
        if handler_name == "pdf_parser":
            use_text = is_pdf_text_extractable(file_path)

        if use_text:
            result = extract_from_pdf_text(file_path)
        else:
            result = extract_from_vision(file_path, is_pdf=True)
    elif handler_name == "image_vision_parser":
        result = extract_from_vision(file_path, is_pdf=False)
    elif handler_name == "email_parser":
        result = extract_from_email(file_path, audit_id=audit_id, org_id=org_id)
    elif handler_name == "docx_parser":
        result = extract_from_docx(file_path)
    else:
        result = ExtractionResult()
        result.warnings.append(f"No ingestion handler registered for MIME type {mime_type!r}")

    # Step 3: flag low-confidence vendors for review.
    if result.vendors:
        for vendor in result.vendors:
            if vendor.extraction_confidence < 0.7:
                vendor.needs_review = True

    # Step 4: normalize vendors via Claude-backed batch normalizer.
    try:
        normalize_extracted_vendors(result.vendors)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("normalize_extracted_vendors failed; continuing with raw vendors: %s", exc)

    # Derive aggregate confidence if handler did not set it.
    if result.vendors and not result.extraction_confidence:
        result.extraction_confidence = sum(v.extraction_confidence for v in result.vendors) / len(result.vendors)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    result.processing_time_ms = elapsed_ms
    result.mime_type = mime_type

    logger.info(
        "Completed ingestion pipeline",
        extra={
            "audit_id": audit_id,
            "org_id": org_id,
            "file_path": file_path,
            "handler_name": handler_name,
            "mime_type": mime_type,
            "vendor_count": len(result.vendors),
            "extraction_method": result.extraction_method.value if isinstance(result.extraction_method, ExtractionMethod) else str(result.extraction_method),
            "extraction_confidence": result.extraction_confidence,
            "processing_time_ms": result.processing_time_ms,
        },
    )

    return result


__all__ = [
    "process_document",
    "normalize_extracted_vendors",
]

