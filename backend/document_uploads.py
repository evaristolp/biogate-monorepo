"""
Record document upload metadata in document_uploads table (Week 6).
"""

from __future__ import annotations

import logging
from typing import Any

from backend.ingestion.base import ExtractionMethod, ExtractionResult

logger = logging.getLogger(__name__)


def record_document_upload(
    supabase_client: Any,
    file_name: str,
    file_size_bytes: int,
    result: ExtractionResult,
    audit_id: str | None = None,
) -> None:
    """
    Insert a row into document_uploads with file metadata and extraction result.
    Call after process_document (or per-file in batch). audit_id is None for ingestion-only uploads.
    """
    method_val = (
        result.extraction_method.value
        if isinstance(result.extraction_method, ExtractionMethod)
        else str(result.extraction_method)
    )
    needs_review = sum(1 for v in result.vendors if v.needs_review)
    row = {
        "audit_id": audit_id,
        "file_name": file_name or "unknown",
        "file_size_bytes": file_size_bytes,
        "mime_type": result.mime_type,
        "extraction_method": method_val,
        "vendors_extracted": len(result.vendors),
        "extraction_confidence": result.extraction_confidence,
        "processing_time_ms": result.processing_time_ms,
        "needs_review_count": needs_review,
    }
    try:
        supabase_client.table("document_uploads").insert(row).execute()
    except Exception as e:
        logger.warning("Failed to insert document_uploads row: %s", e)
