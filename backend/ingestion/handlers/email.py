from __future__ import annotations

from email import message_from_string
from email.message import Message
from pathlib import Path
from typing import List

from backend.ingestion.base import ExtractionMethod, ExtractionResult


def _load_email_text(path: Path) -> str:
    try:
        raw_bytes = path.read_bytes()
    except Exception:
        return ""

    try:
        text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        # Fallback: treat bytes as latin-1; content is only used for potential
        # future parsing, not persisted.
        text = raw_bytes.decode("latin-1", errors="ignore")
    return text


def _extract_plain_bodies(msg: Message) -> List[str]:
    bodies: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True) or b""
                    bodies.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True) or b""
            bodies.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
        except Exception:
            pass
    return [b.strip() for b in bodies if b and b.strip()]


def extract_from_email(file_path: str) -> ExtractionResult:
    """
    Minimal email ingestion stub.

    For this iteration we only ensure that .eml/.msg style files do not
    crash the pipeline. We load the message, attempt to extract plain-text
    bodies, and return an ExtractionResult with zero vendors and clear
    warnings indicating that email extraction is experimental.
    """
    result = ExtractionResult(extraction_method=ExtractionMethod.EMAIL_PARSER)
    path = Path(file_path)

    text = _load_email_text(path)
    if not text:
        result.warnings.append("Email parser could not read message body; no vendors extracted.")
        return result

    try:
        msg = message_from_string(text)
        bodies = _extract_plain_bodies(msg)
        if not bodies:
            result.warnings.append(
                "Email parser did not find any plain-text bodies; vendor extraction is not implemented yet."
            )
        else:
            # We keep the body content implicit for now; future iterations may
            # feed this text into the same LLM-based extractor used for PDFs.
            result.warnings.append(
                "Email ingestion is experimental; vendor extraction is not implemented yet."
            )
    except Exception as exc:
        result.errors.append(f"Failed to parse email message: {exc}")

    return result


__all__ = [
    "extract_from_email",
]

