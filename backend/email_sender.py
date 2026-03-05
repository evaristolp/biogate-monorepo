"""
Optional email delivery for audit reports.

Uses SMTP (env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, BIOGATE_EMAIL_FROM).
If any are unset, sending is skipped and no error is raised.
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


def _smtp_configured() -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()
    return bool(host and user and password and from_addr)


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

    If SMTP is not configured or to_email is invalid, returns without raising.
    Logs and swallows send failures so the API response is not affected.
    """
    if not _is_valid_email(to_email):
        logger.warning("Email delivery skipped: invalid address %r", to_email[:50] if to_email else "")
        return
    if not _smtp_configured():
        logger.debug("Email delivery skipped: SMTP not configured")
        return

    from_addr = os.getenv("BIOGATE_EMAIL_FROM", "").strip()
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    try:
        port = int(port_str)
    except ValueError:
        port = 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()

    red = risk_summary.get("red", 0)
    amber = risk_summary.get("amber", 0)
    yellow = risk_summary.get("yellow", 0)
    green = risk_summary.get("green", 0)

    body_lines = [
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
        body_lines.append(f"Verify this certificate: {base_url.rstrip('/')}/verify/{certificate_id}")
    body_lines.append("")
    body_lines.append("— BioGate")

    msg = MIMEMultipart()
    msg["Subject"] = f"BioGate Audit Report – {audit_id[:8]}"
    msg["From"] = from_addr
    msg["To"] = to_email.strip()
    msg.attach(MIMEText("\n".join(body_lines), "plain", "utf-8"))

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
        logger.info("Audit report email sent to %s for audit %s", to_email.strip(), audit_id)
    except Exception as e:
        logger.warning("Failed to send audit report email to %s: %s", to_email.strip(), e)
