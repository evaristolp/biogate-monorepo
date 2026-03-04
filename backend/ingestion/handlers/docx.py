from __future__ import annotations

from pathlib import Path

from backend.ingestion.base import ExtractionMethod, ExtractionResult


def extract_from_docx(file_path: str) -> ExtractionResult:
    """
    Minimal DOCX ingestion stub.

    To avoid additional binary parsing dependencies in this iteration, the
    handler simply verifies that the file is readable and returns an
    ExtractionResult with zero vendors and a warning explaining that DOCX
    extraction is experimental.
    """
    result = ExtractionResult(extraction_method=ExtractionMethod.DOCX_PARSER)
    path = Path(file_path)

    try:
        # Ensure the file exists and is accessible. We do not attempt to
        # parse the DOCX structure yet; that will be added in a future
        # iteration when richer extraction is required.
        if not path.exists():
            result.errors.append(f"DOCX file not found: {path}")
            return result
        # Touch the bytes so that obvious I/O failures are surfaced here.
        _ = path.read_bytes()
    except Exception as exc:
        result.errors.append(f"Failed to read DOCX file: {exc}")
        return result

    result.warnings.append(
        "DOCX ingestion is experimental; vendor extraction is not implemented yet."
    )
    return result


__all__ = [
    "extract_from_docx",
]

