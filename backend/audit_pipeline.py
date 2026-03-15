"""
Full audit pipeline: persist audit + vendors, run fuzzy matching, update and return results.
Uses Supabase (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) and scripts.fuzzy_match.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Ensure repo root is on path so we can import scripts.fuzzy_match
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.fuzzy_match import match_vendor, exact_match_vendor

from backend.scoring.parent_graph import resolve_parent_chain
from backend.scoring.risk_engine import (
    score_vendor,
    strip_corporate_suffixes,
    is_biosecure_direct_match,
    resolve_biosecure_subsidiary,
    canonical_biosecure_entity_for_grouping,
    is_known_safe,
)

load_dotenv(dotenv_path=_REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Placeholder UUID for "default" organization until multi-tenant
DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"

def normalize_vendor_name(raw: str) -> str:
    """
    Clean up the INPUT vendor name for display/storage: strip whitespace, standardize casing.
    normalized_name is the cleaned version of the user's input, NOT the watchlist match.
    E.g. "BGI Genomics" -> "Bgi Genomics", "  sigma-aldrich  " -> "Sigma-Aldrich".
    """
    if not raw or not isinstance(raw, str):
        return ""
    return " ".join(raw.split()).title()


def run_audit_pipeline(
    rows: list[dict[str, Any]],
    supabase_client: Any,
    *,
    ingestion_warnings: list[dict[str, Any]] | None = None,
    total_rows_uploaded: int | None = None,
    rows_skipped: int | None = None,
) -> dict[str, Any]:
    """
    Create audit + vendors, run fuzzy match for each vendor, update records, return results.
    rows: list of dicts with at least vendor_name; optional country.
    ingestion_warnings: optional structured warnings (empty_vendor_name, unknown_country) to store on audit.
    total_rows_uploaded / rows_skipped: optional counts for certificate summary.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    if not SUPABASE_URL.startswith("https://"):
        raise RuntimeError(f"SUPABASE_URL must use https://, got: {SUPABASE_URL!r}")

    now = datetime.now(timezone.utc).isoformat()

    # 1. Create audit
    audit_row = {
        "organization_id": DEFAULT_ORGANIZATION_ID,
        "status": "processing",
        "submitted_at": now,
    }
    audit_resp = supabase_client.table("audits").insert(audit_row).execute()
    audit_data = audit_resp.data
    if not audit_data or len(audit_data) != 1:
        raise RuntimeError("Failed to create audit record")
    audit_id = audit_data[0]["id"]

    if ingestion_warnings is not None or total_rows_uploaded is not None or rows_skipped is not None:
        update_payload: dict[str, Any] = {}
        if ingestion_warnings is not None:
            update_payload["ingestion_warnings"] = ingestion_warnings
        if total_rows_uploaded is not None:
            update_payload["total_rows_uploaded"] = total_rows_uploaded
        if rows_skipped is not None:
            update_payload["rows_skipped"] = rows_skipped
        if update_payload:
            supabase_client.table("audits").update(update_payload).eq("id", audit_id).execute()

    # 2. Insert vendors (normalized_name from simple cleanup for now; Claude + match next)
    vendor_rows = []
    for r in rows:
        raw_input = (r.get("vendor_name") or "").strip()
        vendor_rows.append({
            "audit_id": audit_id,
            "raw_input_name": raw_input,
            "normalized_name": normalize_vendor_name(raw_input),
            "country": r.get("country"),
            "risk_tier": None,
            "match_evidence": None,
        })
    vendors_resp = supabase_client.table("vendors").insert(vendor_rows).execute()
    vendors_data = vendors_resp.data or []
    if len(vendors_data) != len(rows):
        raise RuntimeError("Failed to insert vendor records")

    # 3. Claude normalization (batch); skip or fall back safely if unavailable or in async context
    raw_names = [r["raw_input_name"] for r in vendor_rows]
    claude_results: list[dict[str, Any]] = []
    try:
        from .vendor_normalizer import normalize_vendors as claude_normalize_vendors
        # asyncio.run() cannot be called from a running event loop (e.g. FastAPI request
        # handlers), so detect that case and skip normalization rather than raising.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            raise RuntimeError("Claude normalization skipped in async context")
        claude_results = asyncio.run(claude_normalize_vendors(raw_names))
    except ImportError as e:
        logger.warning("Claude normalizer not available (install anthropic): %s", e)
    except RuntimeError as e:
        logger.warning("Claude normalization disabled: %s", e)
    except Exception as e:
        logger.warning("Claude normalization failed, using input names: %s", e)
    # Map Claude result by raw_name for lookup
    claude_by_raw: dict[str, dict[str, Any]] = {}
    for item in claude_results:
        rn = (item.get("raw_name") or "").strip()
        if rn:
            claude_by_raw[rn] = item

    # 4. Build normalized_vendors (merge Claude + vendor row), run fuzzy match, then parent check
    risk_summary: dict[str, int] = {"red": 0, "amber": 0, "yellow": 0, "green": 0}
    vendor_updates: list[dict[str, Any]] = []
    for i, v in enumerate(vendors_data):
        raw_name = vendor_rows[i]["raw_input_name"]
        # Initialize fields with safe defaults so that the exception handler
        # can still build a complete update payload without UnboundLocalError.
        normalized_name = normalize_vendor_name(raw_name)
        parent_company_hint: str | None = None
        country_hint: str | None = vendor_rows[i].get("country")
        suppressed_match: dict[str, Any] | None = None
        equipment_type_hint: str | None = None
        risk_source: str | None = None
        parent_match_evidence: dict[str, Any] | None = None
        parent_chain: list[dict[str, Any]] = []

        try:
            claude = claude_by_raw.get(raw_name) or {}
            normalized_name = (claude.get("normalized_name") or "").strip() or normalize_vendor_name(raw_name)
            parent_company_hint = (claude.get("parent_company_hint") or "").strip() or None
            country_hint = (claude.get("country_hint") or "").strip() or None
            equipment_type_hint = (claude.get("equipment_type_hint") or "").strip() or None

            match_name = normalized_name or raw_name
            # 0. Subsidiary resolution: known BIOSECURE subsidiary → RED (e.g. WuXi STA → WuXi AppTec)
            subsidiary_parent = resolve_biosecure_subsidiary(raw_name) or resolve_biosecure_subsidiary(normalized_name or "")
            if subsidiary_parent:
                matches = [{
                    "matched_name": subsidiary_parent,
                    "score": 100,
                    "source_list": "BIOSECURE_NAMED",
                    "country": None,
                    "match_type": "subsidiary_resolution",
                }]
                logger.info("BIOSECURE subsidiary resolution for vendor_index=%d -> %s", i, subsidiary_parent)
            elif is_biosecure_direct_match(raw_name) or is_biosecure_direct_match(normalized_name or ""):
                # 1. Hardcoded BIOSECURE bypass: if raw or normalized contains named entity → RED, skip fuzzy
                canonical = canonical_biosecure_entity_for_grouping(raw_name) or canonical_biosecure_entity_for_grouping(normalized_name or "")
                matched_name = canonical or (raw_name or normalized_name)
                matches = [{
                    "matched_name": matched_name,
                    "score": 100,
                    "source_list": "BIOSECURE_NAMED",
                    "country": None,
                    "match_type": "name",
                }]
                logger.info("BIOSECURE direct match for vendor_index=%d (bypass fuzzy)", i)
            else:
                # 2. Pre-fuzzy: match on root entity name (strip corporate suffixes to reduce false positives)
                query_name = strip_corporate_suffixes(match_name) or match_name
                exact = exact_match_vendor(query_name)
                if exact:
                    matches = [dict(exact)]
                    logger.info("Exact watchlist match for vendor_index=%d (RED)", i)
                else:
                    matches = match_vendor(query_name, threshold=60, top_n=5)
            if matches:
                logger.info(
                    "Fuzzy match completed for vendor_index=%d, top_score=%s, candidates=%d",
                    i,
                    matches[0]["score"],
                    len(matches),
                )
            else:
                logger.info("No fuzzy matches for vendor_index=%d", i)
            fuzzy_score = matches[0]["score"] if matches else 0
            match_evidence_raw = [dict(m) for m in matches] if matches else []

            # Known-safe vendor + fuzzy-only match → suppress flag (do not promote to yellow/amber).
            if matches and (matches[0].get("score") or 0) < 100 and is_known_safe(normalized_name or raw_name):
                m0 = matches[0]
                suppressed_match = {
                    "list": m0.get("source_list", ""),
                    "matched_entity": m0.get("matched_name") or m0.get("matched_entity", ""),
                    "score": m0.get("score", 0),
                    "reason": "known_safe_vendor_fuzzy_suppressed",
                }
                matches = []
                match_evidence_raw = []
                fuzzy_score = 0

            # Resolve parent chain from graph (vendor name and parent_company_hint)
            for name in [match_name, parent_company_hint]:
                if not name:
                    continue
                chain = resolve_parent_chain(name, max_depth=2)
                if len(chain) > len(parent_chain):
                    parent_chain = chain
            if parent_company_hint:
                parent_query = strip_corporate_suffixes(parent_company_hint) or parent_company_hint
                parent_matches = match_vendor(parent_query, threshold=60, top_n=5)
                if parent_matches:
                    parent_score = parent_matches[0]["score"]
                    if parent_score > fuzzy_score:
                        risk_source = "parent_company"
                        parent_match_evidence = dict(parent_matches[0])
                        logger.info(
                            "Parent company override applied for vendor_index=%d",
                            i,
                        )

            # Risk scoring engine: tier, confidence, reasoning from config + graph
            try:
                risk_result = score_vendor(
                    match_evidence_raw,
                    country=country_hint or vendor_rows[i].get("country"),
                    parent_chain=parent_chain if parent_chain else None,
                    parent_company_is_biosecure_named=bool(
                        parent_company_hint and is_biosecure_direct_match(parent_company_hint)
                    ),
                    semantic_score=None,
                    vendor_name=match_name,
                )
            except Exception as e:
                logger.exception(
                    "Risk scoring failed for vendor_index=%d, defaulting to yellow: %s",
                    i,
                    e,
                    exc_info=True,
                )
                risk_result = None

            if risk_result is not None:
                tier = risk_result.tier
                effective_score = risk_result.confidence_score
                match_evidence = [m.model_dump() for m in risk_result.match_evidence]
                risk_reasoning = risk_result.reasoning
            else:
                tier = "yellow"
                effective_score = int(round(fuzzy_score))
                match_evidence = match_evidence_raw
                risk_reasoning = "Scoring failed; conservative default tier applied."

            # Country enrichment: if vendor country empty and we have a match, use match or subsidiary parent country.
            country_source = "unknown"
            if country_hint or vendor_rows[i].get("country"):
                country_source = "uploaded"
            elif match_evidence_raw and isinstance(match_evidence_raw[0], dict):
                m0 = match_evidence_raw[0]
                if m0.get("match_type") == "subsidiary_resolution" or m0.get("source_list") == "BIOSECURE_NAMED":
                    # Subsidiary or BIOSECURE direct: all current BCC parents are China-based
                    country_hint = "China"
                    country_source = "enriched_from_subsidiary_parent"
                else:
                    match_country = m0.get("country")
                    if match_country and str(match_country).strip():
                        country_hint = str(match_country).strip()
                        country_source = "enriched from watchlist"
        except Exception as e:
            logger.exception(
                "Vendor processing failed for vendor_index=%d, defaulting to yellow: %s",
                i,
                e,
                exc_info=True,
            )
            tier = "yellow"
            effective_score = 0
            match_evidence = []
            risk_reasoning = "End-to-end vendor processing failed; conservative default tier applied."
            country_source = "uploaded" if vendor_rows[i].get("country") else "unknown"
            # Restore conservative, non-null hints so downstream payload
            # construction never fails even when early processing did.
            normalized_name = normalize_vendor_name(raw_name)
            country_hint = vendor_rows[i].get("country")
            parent_company_hint = None
            equipment_type_hint = None
            risk_source = None
            parent_match_evidence = None
            parent_chain = []

        risk_summary[tier] += 1

        # Collect vendor updates for batched upsert to avoid per-vendor HTTP calls.
        update_payload = {
            "id": v["id"],
            "audit_id": audit_id,
            "raw_input_name": raw_name,
            "normalized_name": normalized_name or None,
            "country": country_hint or vendor_rows[i].get("country"),
            "country_source": country_source,
            "parent_company": parent_company_hint,
            "equipment_type": equipment_type_hint,
            "risk_tier": tier,
            "match_evidence": match_evidence,
            "risk_source": risk_source,
            "parent_match_evidence": parent_match_evidence,
            "effective_score": effective_score,
            "risk_reasoning": risk_reasoning,
        }
        if suppressed_match is not None:
            update_payload["suppressed_match"] = suppressed_match
        vendor_updates.append(update_payload)

    # Deduplication: group only by matched watchlist entity (source_list + matched_name).
    # Vendors that did not match anything are NOT grouped — each is its own row.
    def _entity_key(me: list | dict) -> tuple[str, str] | None:
        if isinstance(me, dict):
            matches = me.get("matches", me) if isinstance(me.get("matches"), list) else []
        else:
            matches = me if isinstance(me, list) else []
        if not matches or not isinstance(matches[0], dict):
            return None
        m = matches[0]
        src = str(m.get("source_list") or "").strip()
        name = str(m.get("matched_name") or "").strip()
        if not src or not name:
            return None
        return (src, name)

    by_entity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    ungrouped: list[dict[str, Any]] = []
    for u in vendor_updates:
        me = u.get("match_evidence") or []
        key = _entity_key(me)
        if key is not None:
            by_entity.setdefault(key, []).append(u)
        else:
            ungrouped.append(u)

    for _key, group in by_entity.items():
        resolved_group = [u["raw_input_name"] for u in group]
        for u in group:
            me = u.get("match_evidence") or []
            if isinstance(me, list) and me and isinstance(me[0], dict):
                u["match_evidence"] = {"matches": me, "resolved_group": resolved_group}
            else:
                u["match_evidence"] = {"matches": me if isinstance(me, list) else [], "resolved_group": resolved_group}

    for u in ungrouped:
        me = u.get("match_evidence") or []
        # Each ungrouped vendor is its own row; resolved_group = just this vendor's name
        u["match_evidence"] = {
            "matches": me if isinstance(me, list) else [],
            "resolved_group": [u["raw_input_name"]],
        }
        if u.get("suppressed_match") is not None:
            u["match_evidence"]["suppressed_match"] = u["suppressed_match"]
            del u["suppressed_match"]

    # Persist vendor scoring results in batches (upsert on primary key id).
    batch_size = 500
    for i in range(0, len(vendor_updates), batch_size):
        batch = vendor_updates[i : i + batch_size]
        supabase_client.table("vendors").upsert(batch, on_conflict="id").execute()

    # 5. Update audit complete
    supabase_client.table("audits").update({
        "status": "complete",
        "completed_at": now,
    }).eq("id", audit_id).execute()

    # 6. Generate and store JSON risk report (with audit versioning)
    report: dict[str, Any] | None = None
    certificate_id: str | None = None
    certificate_pdf_base64: str | None = None
    try:
        from backend.report import generate_risk_report
        from backend.config.scoring_config import get_scoring_config
        report = generate_risk_report(str(audit_id), supabase_client)
        config = get_scoring_config()

        # Compute next version number for this audit so history is preserved.
        try:
            existing = (
                supabase_client.table("audit_reports")
                .select("version")
                .eq("audit_id", audit_id)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            if existing.data:
                latest_version = existing.data[0].get("version") or 0
                next_version = int(latest_version) + 1
            else:
                next_version = 1
        except Exception as e:
            logger.warning("Could not determine existing audit report versions, defaulting to 1: %s", e)
            next_version = 1

        report_row = {
            "audit_id": audit_id,
            "report_json": report,
            "version": next_version,
            "pipeline_version": "1.0",
            "scoring_config_version": config.version,
        }
        supabase_client.table("audit_reports").insert(report_row).execute()

        # 6b. Generate Compliance Certificate PDF only when we have a valid report.
        if report is not None:
            try:
                from backend.certificate import generate_certificate_pdf, store_certificate
                import base64
                base_url = os.getenv("BIOGATE_BASE_URL", "http://localhost:8000")
                private_key_pem = os.getenv("BIOGATE_CERTIFICATE_PRIVATE_KEY") or None
                cert_id = str(__import__("uuid").uuid4())
                pdf_bytes, pdf_hash_hex, signature_hex = generate_certificate_pdf(
                    report,
                    cert_id,
                    base_url,
                    private_key_pem=private_key_pem,
                )
                store_certificate(
                    supabase_client,
                    str(audit_id),
                    next_version,
                    pdf_hash_hex,
                    signature_hex,
                    certificate_id=cert_id,
                )
                certificate_id = cert_id
                certificate_pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
            except Exception as cert_exc:
                logger.warning("Compliance certificate generation failed: %s", cert_exc)
    except Exception as e:
        logger.warning("Failed to generate or store risk report: %s", e)

    # 7. Fetch updated vendors for response
    vendors_final_resp = supabase_client.table("vendors").select("*").eq(
        "audit_id", audit_id
    ).order("created_at").execute()
    vendors_final = vendors_final_resp.data or []

    return {
        "audit_id": str(audit_id),
        "vendor_count": len(vendors_final),
        "risk_summary": risk_summary,
        "vendors": vendors_final,
        "report": report,
        "certificate_id": certificate_id,
        "certificate_pdf_base64": certificate_pdf_base64,
    }
