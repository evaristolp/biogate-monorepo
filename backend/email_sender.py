"""
Optional email delivery for audit reports.

Uses Resend when RESEND_API_KEY is set; otherwise falls back to SMTP
(env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, BIOGATE_EMAIL_FROM).
If neither is configured, sending is skipped and no error is raised.
"""

import base64
import logging
import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Simple validation: at least one @ and a dot in the domain
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(value: str) -> bool:
    if not value or not value.strip():
        return False
    return _EMAIL_RE.match(value.strip()) is not None


def _resend_configured() -> bool:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()
    return bool(api_key and from_addr)


def _smtp_configured() -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()
    return bool(host and user and password and from_addr)


def _build_body_text(
    audit_id: str,
    vendor_count: int,
    risk_summary: dict,
    certificate_id: str | None,
    base_url: str | None,
) -> str:
    red = risk_summary.get("red", 0)
    amber = risk_summary.get("amber", 0)
    yellow = risk_summary.get("yellow", 0)
    green = risk_summary.get("green", 0)
    lines = [
        "Your BioGate vendor screening audit is complete.",
        "",
        f"Audit ID: {audit_id}",
        f"Vendors screened: {vendor_count}",
        "",
        "Risk summary:",
        f"  Red:    {red}",
        f"  Amber:  {amber}",
        f"  Yellow: {yellow}",
        f"  Green:  {green}",
        "",
    ]
    if certificate_id and base_url:
        lines.append(f"Verify this certificate: {base_url.rstrip('/')}/verify/{certificate_id}")
    lines.extend(["", "— BioGate"])
    return "\n".join(lines)


def _send_via_resend(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    certificate_pdf_base64: str | None,
    certificate_id: str | None,
    audit_id: str,
) -> bool:
    """Send via Resend API. Returns True on success, False on failure (logged)."""
    try:
        import resend
        resend.api_key = os.getenv("RESEND_API_KEY", "").strip()
        from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()

        params = {
            "from": from_addr,
            "to": [to_email.strip()],
            "subject": subject,
            "text": body_text,
        }
        if certificate_pdf_base64:
            params["attachments"] = [
                {
                    "filename": f"biogate-certificate-{certificate_id or audit_id}.pdf",
                    "content": certificate_pdf_base64,
                }
            ]
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.warning("Resend send failed: %s", e, exc_info=True)
        return False


def _send_via_smtp(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    certificate_pdf_base64: str | None,
    certificate_id: str | None,
    audit_id: str,
) -> bool:
    """Send via SMTP. Returns True on success, False on failure (logged)."""
    from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    try:
        port = int(port_str)
    except ValueError:
        port = 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email.strip()
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if certificate_pdf_base64:
        try:
            pdf_bytes = base64.b64decode(certificate_pdf_base64, validate=True)
        except Exception as e:
            logger.warning("Could not decode certificate PDF for email: %s", e)
        else:
            part = MIMEApplication(pdf_bytes, _subtype="pdf")
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"biogate-certificate-{certificate_id or audit_id}.pdf",
            )
            msg.attach(part)

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email.strip()], msg.as_string())
        return True
    except Exception as e:
        logger.warning("SMTP send failed: %s", e)
        return False


def send_audit_report_email(
    *,
    to_email: str,
    audit_id: str,
    risk_summary: dict,
    vendor_count: int,
    certificate_pdf_base64: str | None = None,
    certificate_id: str | None = None,
    base_url: str | None = None,
) -> None:
    """
    Send one email with audit summary and optional Compliance Certificate PDF.

    Uses Resend if RESEND_API_KEY and BIOGATE_EMAIL_FROM are set; otherwise
    uses SMTP when configured. If neither is configured or to_email is invalid,
    returns without raising. Logs and swallows send failures so the API response
    is not affected.
    """
    if not _is_valid_email(to_email):
        logger.warning("Email delivery skipped: invalid address %r", to_email[:50] if to_email else "")
        return
    if not _resend_configured() and not _smtp_configured():
        logger.info(
            "Email delivery skipped: set RESEND_API_KEY and BIOGATE_EMAIL_FROM (or SMTP_*) to enable."
        )
        return

    subject = f"BioGate Audit Report – {audit_id[:8]}"
    body_text = _build_body_text(
        audit_id=audit_id,
        vendor_count=vendor_count,
        risk_summary=risk_summary,
        certificate_id=certificate_id,
        base_url=base_url,
    )
    to_stripped = to_email.strip()

    sent = False
    if _resend_configured():
        logger.info("Sending audit report email to %s via Resend ...", to_stripped)
        sent = _send_via_resend(
            to_email=to_stripped,
            subject=subject,
            body_text=body_text,
            certificate_pdf_base64=certificate_pdf_base64,
            certificate_id=certificate_id,
            audit_id=audit_id,
        )
    if not sent and _smtp_configured():
        sent = _send_via_smtp(
            to_email=to_stripped,
            subject=subject,
            body_text=body_text,
            certificate_pdf_base64=certificate_pdf_base64,
            certificate_id=certificate_id,
            audit_id=audit_id,
        )

    if sent:
        logger.info("Audit report email sent to %s for audit %s", to_stripped, audit_id)
    else:
        logger.warning("Audit report email could not be sent to %s for audit %s", to_stripped, audit_id)
