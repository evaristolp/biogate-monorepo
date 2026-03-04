from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Tuple

pdfplumber = None  # type: ignore[assignment]
try:  # pragma: no cover - import-time guard
    import pdfplumber as _pdfplumber  # type: ignore[import]

    pdfplumber = _pdfplumber
except Exception:  # pragma: no cover - defensive
    pdfplumber = None

_magic = None
try:  # pragma: no cover - import-time guard
    import magic as _magic_mod  # type: ignore[import]

    _magic = _magic_mod
except Exception:  # pragma: no cover - defensive
    _magic = None


logger = logging.getLogger(__name__)


# Maps MIME types to logical handler names
MIME_TO_HANDLER: Dict[str, str] = {
    "text/csv": "csv_parser",
    "text/tab-separated-values": "csv_parser",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel_parser",
    "application/vnd.ms-excel": "excel_parser",
    "application/pdf": "pdf_parser",  # Special-cased to route to text vs vision
    "image/png": "image_vision_parser",
    "image/jpeg": "image_vision_parser",
    "image/tiff": "image_vision_parser",
    "image/heic": "image_vision_parser",
    "message/rfc822": "email_parser",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx_parser",
}


# Fallback mapping from file extensions (lowercase, with dot) to MIME types
EXTENSION_FALLBACK: Dict[str, str] = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".heic": "image/heic",
    ".tiff": "image/tiff",
    ".eml": "message/rfc822",
    ".msg": "message/rfc822",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _detect_mime_type(file_path: str) -> str:
    """
    Detect MIME type using python-magic, with extension-based fallback.

    Returns a MIME type string (e.g. 'application/pdf') or 'application/octet-stream'
    when detection is not possible.
    """
    resolved_path = os.fspath(file_path)
    mime_type = "application/octet-stream"

    if _magic is not None:
        try:
            # python-magic may raise if file is missing or backend libraries are not available
            mime = _magic.Magic(mime=True)
            detected = mime.from_file(resolved_path)
            if isinstance(detected, str) and detected:
                mime_type = detected
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("magic MIME detection failed for %s: %s", resolved_path, exc)

    if not mime_type or mime_type == "application/octet-stream":
        ext = Path(resolved_path).suffix.lower()
        fallback = EXTENSION_FALLBACK.get(ext)
        if fallback:
            mime_type = fallback

    return mime_type


def is_pdf_text_extractable(file_path: str) -> bool:
    """
    Lightweight probe to decide whether a PDF has extractable text.

    Opens the file with pdfplumber and inspects up to the first three pages.
    Returns True if any page contains more than 50 characters of text.
    """
    resolved_path = os.fspath(file_path)

    if pdfplumber is None:
        # If pdfplumber is unavailable, conservatively report that text is not extractable
        # so that the pipeline can fall back to vision-based extraction where appropriate.
        logger.debug("pdfplumber not available; treating %s as non-text-extractable PDF", resolved_path)
        return False

    try:
        with pdfplumber.open(resolved_path) as pdf:  # type: ignore[call-arg]
            max_pages = min(3, len(pdf.pages))
            for idx in range(max_pages):
                page = pdf.pages[idx]
                text = page.extract_text() or ""
                if len(text.strip()) > 50:
                    return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("pdfplumber failed to inspect %s: %s", resolved_path, exc)

    return False


def detect_handler(file_path: str) -> Tuple[str, str]:
    """
    Resolve the appropriate ingestion handler for a given file.

    Returns:
        (handler_name, detected_mime_type)

    Handler names are logical identifiers such as:
    - 'csv_parser'
    - 'excel_parser'
    - 'pdf_text_parser'
    - 'pdf_vision_parser'
    - 'image_vision_parser'
    - 'email_parser'
    - 'docx_parser'
    """
    mime_type = _detect_mime_type(file_path)

    # Special handling for PDFs: inspect content to choose text vs vision
    if mime_type == "application/pdf":
        if is_pdf_text_extractable(file_path):
            handler_name = "pdf_text_parser"
        else:
            handler_name = "pdf_vision_parser"
        return handler_name, mime_type

    handler_name = MIME_TO_HANDLER.get(mime_type)

    if handler_name is None:
        # Last-resort extension-based handler resolution even if MIME is unusual
        ext = Path(os.fspath(file_path)).suffix.lower()
        fallback_mime = EXTENSION_FALLBACK.get(ext)
        if fallback_mime:
            handler_name = MIME_TO_HANDLER.get(fallback_mime)
            if handler_name:
                mime_type = fallback_mime

    if handler_name is None:
        logger.warning("No ingestion handler registered for MIME type %s", mime_type)
        handler_name = "unknown_handler"

    return handler_name, mime_type


__all__ = [
    "MIME_TO_HANDLER",
    "EXTENSION_FALLBACK",
    "detect_handler",
    "is_pdf_text_extractable",
]

