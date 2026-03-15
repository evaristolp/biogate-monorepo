"""
Compliance Certificate PDF generator (Week 6).
Uses WeasyPrint to render JSON risk report to a signed PDF with QR verification.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _escape_html(s: str) -> str:
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_certificate_html(report: dict[str, Any], verification_url: str, qr_data_uri: str) -> str:
    if not report:
        return ""
    meta = report.get("report_metadata") or {}
    summary = report.get("summary") or {}
    by_tier = summary.get("vendors_by_tier") or {}
    vendors = report.get("vendors") or []
    watchlist = report.get("watchlist_metadata") or []
    disclaimers = report.get("disclaimers") or []
    ingestion_warnings = report.get("ingestion_warnings") or []

    org_name = _escape_html(meta.get("organization_name", "Default Organization"))
    audit_id = _escape_html(str(meta.get("audit_id", "")))
    generated = meta.get("generated_at") or datetime.now(timezone.utc).isoformat()
    if isinstance(generated, str) and "T" in generated:
        generated = generated.split("T")[0] + " " + generated.split("T")[1][:8]
    generated = _escape_html(str(generated))
    pipeline_ver = _escape_html(str(meta.get("pipeline_version", "1.0")))
    config_ver = _escape_html(str(meta.get("scoring_config_version", "")))

    overall = _escape_html(summary.get("overall_risk_assessment", ""))
    total = summary.get("total_vendors", 0)
    total_rows = summary.get("total_rows_uploaded")
    rows_skipped = summary.get("rows_skipped")
    unique_entities = summary.get("unique_entities")
    red = by_tier.get("red", 0)
    amber = by_tier.get("amber", 0)
    yellow = by_tier.get("yellow", 0)
    green = by_tier.get("green", 0)

    if total_rows is not None and rows_skipped is not None:
        summary_line = f"Total rows uploaded: {total_rows} | Vendors screened: {total} | Rows skipped: {rows_skipped} (see Ingestion Warnings)"
    else:
        summary_line = f"Total vendors: {total}"
    if unique_entities is not None:
        summary_line += f" | Unique entities: {unique_entities} | Total vendor entries: {total}"
    summary_line = _escape_html(summary_line)

    watchlist_rows = ""
    for w in watchlist[:10]:
        sl = _escape_html(w.get("source_list", ""))
        sd = _escape_html(str(w.get("snapshot_date", "")))
        rc = w.get("record_count", 0)
        watchlist_rows += f"<tr><td>{sl}</td><td>{sd}</td><td>{rc}</td></tr>"

    # Build one row per unique entity (grouped by matched watchlist entity); ungrouped = one row each.
    seen_entity_keys: set[tuple[str, str]] = set()
    vendor_rows = ""
    country_footnote_used = False
    for v in vendors[:500]:
        evidence = v.get("match_evidence") or []
        if evidence and isinstance(evidence[0], dict):
            src = str(evidence[0].get("source_list") or "").strip()
            name = str(evidence[0].get("matched_name") or "").strip()
            entity_key = (src, name) if (src and name) else (str(v.get("vendor_id") or ""), str(v.get("raw_input_name") or ""))
        else:
            entity_key = (str(v.get("vendor_id") or ""), str(v.get("raw_input_name") or ""))
        if entity_key in seen_entity_keys:
            continue
        seen_entity_keys.add(entity_key)
        tier = (v.get("effective_tier") or v.get("risk_tier") or "green").lower()
        resolved_group = v.get("resolved_group") or []
        list_label = ""
        if evidence and isinstance(evidence[0], dict) and evidence[0].get("source_list"):
            list_label = " [" + _escape_html(evidence[0].get("source_list", "")) + "]"
        if resolved_group:
            name_display = _escape_html(resolved_group[0]) + list_label
            if len(resolved_group) > 1:
                name_display += " — " + str(len(resolved_group)) + " uploaded vendor entries: " + _escape_html(", ".join(resolved_group[:10]))
                if len(resolved_group) > 10:
                    name_display += _escape_html(", … (" + str(len(resolved_group)) + " total)")
        else:
            name_display = _escape_html((v.get("raw_input_name") or "").strip() or "—") + list_label
        country = _escape_html(str(v.get("country") or ""))
        if (v.get("country_source") or "").strip().lower() == "enriched from watchlist":
            country = country + "*" if country else "*"
            country_footnote_used = True
        # Green = no match; never show a watchlist name as evidence for green.
        if tier == "green":
            ev_str = "No matches found"
        elif not evidence or not isinstance(evidence[0], dict):
            ev_str = "No matches found"
        else:
            m = evidence[0]
            ev_str = _escape_html((m.get("source_list") or "") + " — " + (m.get("matched_name") or "—"))
        vendor_rows += f'<tr class="tier-{tier}"><td>{name_display}</td><td>{tier}</td><td>{country}</td><td>{ev_str}</td></tr>'

    ingestion_warnings_block = ""
    if ingestion_warnings:
        ingestion_warnings_block = "<div class=\"section\"><h2>Ingestion Warnings</h2><p>The following rows were skipped or had issues:</p><table><tr><th>Row</th><th>Reason</th><th>Raw data</th></tr>"
        for w in ingestion_warnings[:100]:
            row_num = w.get("row_number", "—")
            wtype = _escape_html((w.get("warning_type") or "unknown").replace("_", " "))
            raw = w.get("raw_row_data") or {}
            raw_str = _escape_html(", ".join(f"{k}: {v}" for k, v in list(raw.items())[:5]))
            if len(raw) > 5:
                raw_str += "…"
            ingestion_warnings_block += f"<tr><td>{row_num}</td><td>{wtype}</td><td>{raw_str}</td></tr>"
        ingestion_warnings_block += "</table></div>"

    footnote_block = ""
    if country_footnote_used:
        footnote_block = "<p class=\"footnote\">* Country enriched from watchlist data; not provided in uploaded vendor file.</p>"

    disclaimer_block = "".join(f"<p>{_escape_html(d)}</p>" for d in disclaimers[:3])

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>BioGate Compliance Certificate</title>
  <style>
    @page {{ size: A4; margin: 2cm; }}
    body {{ font-family: Georgia, serif; font-size: 10pt; color: #222; line-height: 1.4; }}
    .letterhead {{ border-bottom: 2px solid #1a365d; padding-bottom: 8px; margin-bottom: 16px; }}
    .letterhead h1 {{ margin: 0; font-size: 18pt; color: #1a365d; }}
    .letterhead .tagline {{ margin: 0; font-size: 9pt; color: #4a5568; }}
    .meta {{ margin-bottom: 16px; }}
    .meta table {{ border-collapse: collapse; }}
    .meta th {{ text-align: left; padding-right: 12px; font-weight: 600; }}
    .section {{ margin-top: 16px; }}
    .section h2 {{ font-size: 12pt; color: #1a365d; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
    th, td {{ border: 1px solid #cbd5e0; padding: 6px 8px; text-align: left; }}
    th {{ background: #edf2f7; font-weight: 600; }}
    .tier-red {{ background: #fed7d7; }}
    .tier-amber {{ background: #feebc8; }}
    .tier-yellow {{ background: #fefcbf; }}
    .tier-green {{ background: #c6f6d5; }}
    .attestation {{ margin-top: 20px; padding: 12px; background: #f7fafc; border: 1px solid #e2e8f0; }}
    .signature-block {{ margin-top: 20px; display: flex; align-items: flex-start; gap: 24px; }}
    .qr {{ flex-shrink: 0; }}
    .qr img {{ width: 100px; height: 100px; }}
    .verify {{ font-size: 9pt; color: #4a5568; }}
  </style>
</head>
<body>
  <div class="letterhead">
    <h1>BioGate</h1>
    <p class="tagline">BIOSECURE Act Compliance Certificate</p>
  </div>

  <div class="section methodology">
    <h2>Methodology</h2>
    <p>Vendors are screened against configured watchlists. Match evidence indicates which list (if any) was matched; Green-tier vendors with no match show "No matches found". Country may be enriched from watchlist data when not provided in the upload.</p>
  </div>

  <div class="meta">
    <table>
      <tr><th>Organization</th><td>{org_name}</td></tr>
      <tr><th>Audit ID</th><td>{audit_id}</td></tr>
      <tr><th>Report date</th><td>{generated}</td></tr>
      <tr><th>Pipeline version</th><td>{pipeline_ver}</td></tr>
      <tr><th>Scoring config</th><td>{config_ver}</td></tr>
    </table>
  </div>

  <div class="section">
    <h2>Summary</h2>
    <p><strong>Overall:</strong> {overall}</p>
    <p>{summary_line}</p>
    <p>Red: {red}, Amber: {amber}, Yellow: {yellow}, Green: {green}</p>
  </div>

  {ingestion_warnings_block}

  <div class="section">
    <h2>Watchlist sources</h2>
    <table>
      <tr><th>Source list</th><th>Snapshot date</th><th>Record count</th></tr>
      {watchlist_rows}
    </table>
  </div>

  <div class="section">
    <h2>Vendor table (tiers and evidence)</h2>
    <table>
      <tr><th>Vendor name</th><th>Tier</th><th>Country</th><th>Match Evidence</th></tr>
      {vendor_rows}
    </table>
    {footnote_block}
  </div>

  <div class="attestation">
    <h2>Attestation</h2>
    <p>This report was generated by BioGate based on the submitted vendor data and current watchlist snapshots. 
    It is intended to support BIOSECURE Act supply chain due diligence and does not constitute legal advice.</p>
    {disclaimer_block}
  </div>

  <div class="signature-block">
    <div class="qr">
      <img src="{qr_data_uri}" alt="Verification QR code"/>
    </div>
    <div class="verify">
      <p><strong>Digital signature</strong></p>
      <p>This certificate is signed. Verify authenticity by scanning the QR code or visiting:</p>
      <p>{_escape_html(verification_url)}</p>
    </div>
  </div>
</body>
</html>
"""


def _generate_qr_data_uri(url: str, size: int = 100) -> str:
    try:
        import qrcode
        buf = io.BytesIO()
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))
        img.save(buf, format="PNG")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("QR code generation failed: %s", e)
        return ""


def _sign_hash(hash_hex: str, private_key_pem: str) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from cryptography.hazmat.backends import default_backend

    key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
        backend=default_backend(),
    )
    digest = bytes.fromhex(hash_hex)
    sig = key.sign(digest, padding.PKCS1v15(), Prehashed(hashes.SHA256()))
    return sig.hex()


def _verify_signature(hash_hex: str, signature_hex: str, public_key_pem: str) -> bool:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from cryptography.hazmat.backends import default_backend

    key = serialization.load_pem_public_key(
        public_key_pem.encode(),
        backend=default_backend(),
    )
    digest = bytes.fromhex(hash_hex)
    sig = bytes.fromhex(signature_hex)
    try:
        key.verify(sig, digest, padding.PKCS1v15(), Prehashed(hashes.SHA256()))
        return True
    except Exception:
        return False


def verify_certificate(certificate_id: str, supabase_client: Any) -> dict[str, Any] | None:
    """
    Load certificate by id and return verification JSON.
    Returns None if not found.
    """
    resp = (
        supabase_client.table("compliance_certificates")
        .select("id, audit_id, report_version, pdf_hash_hex, signature_hex, issued_at")
        .eq("id", certificate_id)
        .limit(1)
        .execute()
    )
    if not resp.data or len(resp.data) == 0:
        return None
    row = resp.data[0]
    public_key_pem = os.getenv("BIOGATE_CERTIFICATE_PUBLIC_KEY") or ""
    signature_valid = False
    if public_key_pem and row.get("signature_hex"):
        signature_valid = _verify_signature(
            row["pdf_hash_hex"],
            row["signature_hex"],
            public_key_pem,
        )
    return {
        "certificate_id": str(row["id"]),
        "audit_id": str(row["audit_id"]),
        "report_version": row.get("report_version"),
        "issued_at": row.get("issued_at"),
        "pdf_hash": row.get("pdf_hash_hex"),
        "signature_valid": signature_valid,
    }


def generate_certificate_pdf(
    report: dict[str, Any],
    certificate_id: str,
    base_url: str,
    *,
    private_key_pem: str | None = None,
) -> tuple[bytes, str, str]:
    """
    Render the risk report to a PDF, optionally sign it, and return (pdf_bytes, pdf_hash_hex, signature_hex).
    signature_hex is empty if private_key_pem is not provided.
    """
    verification_url = f"{base_url.rstrip('/')}/verify/{certificate_id}"
    qr_data_uri = _generate_qr_data_uri(verification_url)

    html = _build_certificate_html(report, verification_url, qr_data_uri)

    try:
        from weasyprint import HTML
        from weasyprint import CSS
    except ImportError as e:
        raise RuntimeError("weasyprint is required for certificate generation; pip install weasyprint") from e

    pdf_buffer = io.BytesIO()
    HTML(string=html).write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    signature_hex = ""
    if private_key_pem:
        try:
            signature_hex = _sign_hash(pdf_hash, private_key_pem)
        except Exception as e:
            logger.warning("Certificate signing failed: %s", e)

    return pdf_bytes, pdf_hash, signature_hex


def store_certificate(
    supabase_client: Any,
    audit_id: str,
    report_version: int,
    pdf_hash_hex: str,
    signature_hex: str,
    certificate_id: str | None = None,
) -> str:
    """
    Insert a row into compliance_certificates. Returns the certificate_id (new or passed in).
    """
    cert_id = certificate_id or str(uuid4())
    row = {
        "id": cert_id,
        "audit_id": audit_id,
        "report_version": report_version,
        "pdf_hash_hex": pdf_hash_hex,
        "signature_hex": signature_hex,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase_client.table("compliance_certificates").insert(row).execute()
    return cert_id
