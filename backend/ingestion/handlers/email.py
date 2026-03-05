from __future__ import annotations

import logging
import os
import tempfile
from email import message_from_string
from email.message import Message
from pathlib import Path
from typing import List

from backend.ingestion.base import (
    ExtractionMethod,
    ExtractionResult,
)

logger = logging.getLogger(__name__)

# Max recursion depth for attachment processing (email -> attachments -> ...)
MAX_ATTACHMENT_DEPTH = 2
# Skip attachments larger than 4 MB
MAX_ATTACHMENT_BYTES = 4 * 1024 * 1024


def _load_email_text(path: Path) -> str:
    try:
        raw_bytes = path.read_bytes()
    except Exception:
        return ""

    try:
        text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
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
                    bodies.append(
                        payload.decode(
                            part.get_content_charset() or "utf-8",
                            errors="ignore",
                        )
                    )
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True) or b""
            bodies.append(
                payload.decode(
                    msg.get_content_charset() or "utf-8",
                    errors="ignore",
                )
            )
        except Exception:
            pass
    return [b.strip() for b in bodies if b and b.strip()]


def _get_attachments(msg: Message) -> List[tuple[str, bytes]]:
    """Return list of (filename, payload_bytes) for each attachment."""
    attachments: List[tuple[str, bytes]] = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        filename = filename.strip()
        if not filename:
            continue
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            if len(payload) > MAX_ATTACHMENT_BYTES:
                continue
            attachments.append((filename, payload))
        except Exception:
            continue
    return attachments


def extract_from_email(
    file_path: str,
    *,
    audit_id: str = "",
    org_id: str = "",
    _depth: int = 0,
) -> ExtractionResult:
    """
    Ingest email: parse body and attachments. Attachments are re-routed through
    the ingestion pipeline recursively (CSV, PDF, Excel, etc.). Body text is
    passed to Claude for vendor extraction when available.
    """
    result = ExtractionResult(extraction_method=ExtractionMethod.EMAIL_PARSER)
    path = Path(file_path)

    text = _load_email_text(path)
    if not text:
        result.warnings.append(
            "Email parser could not read message body; no vendors extracted."
        )
        return result

    try:
        msg = message_from_string(text)
    except Exception as exc:
        result.errors.append(f"Failed to parse email message: {exc}")
        return result

    bodies = _extract_plain_bodies(msg)
    combined_body = "\n\n".join(bodies) if bodies else ""

    # Extract vendors from body text via Claude (same as PDF text path).
    if combined_body and _depth < MAX_ATTACHMENT_DEPTH:
        try:
            from backend.ingestion.handlers.pdf_text import extract_vendors_via_claude
            vendors_from_body = extract_vendors_via_claude(
                combined_body,
                [],
            )
            for v in vendors_from_body:
                v.source_context = "Email body"
            result.vendors.extend(vendors_from_body)
        except Exception as exc:
            logger.debug("Claude body extraction failed: %s", exc)

    # Re-route each attachment through the ingestion pipeline.
    attachments = _get_attachments(msg)
    if attachments and _depth < MAX_ATTACHMENT_DEPTH:
        from backend.ingestion.pipeline import process_document
        for filename, payload in attachments:
            suffix = Path(filename).suffix or ".bin"
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix,
                    prefix="biogate-email-att-",
                ) as tmp:
                    tmp.write(payload)
                    tmp_path = tmp.name
                try:
                    sub_result = process_document(
                        tmp_path,
                        audit_id=audit_id or "email-att",
                        org_id=org_id or "email-att",
                    )
                    result.vendors.extend(sub_result.vendors)
                    for e in sub_result.errors:
                        result.errors.append(f"[{filename}] {e}")
                    for w in sub_result.warnings:
                        result.warnings.append(f"[{filename}] {w}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            except Exception as exc:
                result.errors.append(f"[{filename}] Failed to process attachment: {exc}")

    if result.vendors:
        result.extraction_confidence = (
            sum(v.extraction_confidence for v in result.vendors) / len(result.vendors)
        )

    if not result.vendors and not result.errors:
        if not bodies:
            result.warnings.append(
                "Email parser did not find any plain-text bodies; no attachments or body vendors extracted."
            )
        else:
            result.warnings.append(
                "No vendor records extracted from email body or attachments."
            )

    return result


__all__ = [
    "extract_from_email",
]
