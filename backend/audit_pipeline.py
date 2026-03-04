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
) -> dict[str, Any]:
    """
    Create audit + vendors, run fuzzy match for each vendor, update records, return results.
    rows: list of dicts with at least vendor_name; optional country.
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
            # 1. Hardcoded BIOSECURE bypass: if raw or normalized contains named entity → RED, skip fuzzy
            if is_biosecure_direct_match(raw_name) or is_biosecure_direct_match(normalized_name or ""):
                matches = [{
                    "matched_name": raw_name or normalized_name,
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
        update_payload: dict[str, Any] = {
            # Include required columns so PostgREST upsert never attempts to write NULLs
            # into NOT NULL fields (even on conflict updates).
            "id": v["id"],
            "audit_id": audit_id,
            "raw_input_name": raw_name,
            "normalized_name": normalized_name or None,
            "country": country_hint or vendor_rows[i].get("country"),
            "parent_company": parent_company_hint,
            "equipment_type": equipment_type_hint,
            "risk_tier": tier,
            "match_evidence": match_evidence,
            "risk_source": risk_source,
            "parent_match_evidence": parent_match_evidence,
            "effective_score": effective_score,
            "risk_reasoning": risk_reasoning,
        }
        vendor_updates.append(update_payload)

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
        "report": report if "report" in locals() else None,
    }
