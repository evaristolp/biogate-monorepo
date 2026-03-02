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

from scripts.fuzzy_match import match_vendor

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Placeholder UUID for "default" organization until multi-tenant
DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"

# Risk tiers by highest match score (aligned with observed match quality)
TIER_RED = 80    # confirmed watchlist match
TIER_AMBER = 65  # probable match, needs human review
TIER_YELLOW = 50  # low confidence match


def _score_to_tier(score: int) -> str:
    if score >= TIER_RED:
        return "red"
    if score >= TIER_AMBER:
        return "amber"
    if score >= TIER_YELLOW:
        return "yellow"
    return "green"


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

    # 3. Claude normalization (batch); skip if unavailable
    raw_names = [r["raw_input_name"] for r in vendor_rows]
    claude_results: list[dict[str, Any]] = []
    try:
        from .vendor_normalizer import normalize_vendors as claude_normalize_vendors
        claude_results = asyncio.run(claude_normalize_vendors(raw_names))
    except ImportError as e:
        logger.warning("Claude normalizer not available (install anthropic): %s", e)
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
    for i, v in enumerate(vendors_data):
        raw_name = vendor_rows[i]["raw_input_name"]
        claude = claude_by_raw.get(raw_name) or {}
        normalized_name = (claude.get("normalized_name") or "").strip() or normalize_vendor_name(raw_name)
        parent_company_hint = (claude.get("parent_company_hint") or "").strip() or None
        country_hint = (claude.get("country_hint") or "").strip() or None
        equipment_type_hint = (claude.get("equipment_type_hint") or "").strip() or None

        # Fuzzy match on normalized name (or raw if same)
        match_name = normalized_name or raw_name
        matches = match_vendor(match_name, threshold=50, top_n=5)
        logger.info(
            "match_vendor(%r) -> %s",
            match_name,
            [(m["matched_name"], m["score"], m.get("source_list")) for m in matches] if matches else "[]",
        )
        fuzzy_score = matches[0]["score"] if matches else 0
        match_evidence = [dict(m) for m in matches] if matches else None

        risk_source: str | None = None
        parent_match_evidence: dict[str, Any] | None = None
        effective_score = int(round(fuzzy_score))

        # After normalization, before risk tier: if vendor has parent_company, match parent on watchlist.
        # If parent's score > vendor's score, use parent's score as effective_score and set risk_source to parent_company.
        if parent_company_hint:
            parent_matches = match_vendor(parent_company_hint, threshold=50, top_n=5)
            if parent_matches:
                parent_score = parent_matches[0]["score"]
                if parent_score > fuzzy_score:
                    effective_score = int(round(parent_score))
                    risk_source = "parent_company"
                    parent_match_evidence = dict(parent_matches[0])
                    logger.info(
                        "parent_company overrides: %r -> %s (parent score %s > vendor %s), effective_score=%s",
                        parent_company_hint,
                        parent_match_evidence.get("matched_name"),
                        parent_score,
                        fuzzy_score,
                        effective_score,
                    )

        tier = _score_to_tier(int(effective_score))
        # Bump to at least amber when risk came from parent match
        if risk_source == "parent_company" and tier == "green":
            tier = "amber"
        risk_summary[tier] += 1

        supabase_client.table("vendors").update({
            "normalized_name": normalized_name or None,
            "country": country_hint or vendor_rows[i].get("country"),
            "parent_company": parent_company_hint,
            "equipment_type": equipment_type_hint,
            "risk_tier": tier,
            "match_evidence": match_evidence,
            "risk_source": risk_source,
            "parent_match_evidence": parent_match_evidence,
            "effective_score": effective_score,
        }).eq("id", v["id"]).execute()

    # 5. Update audit complete
    supabase_client.table("audits").update({
        "status": "complete",
        "completed_at": now,
    }).eq("id", audit_id).execute()

    # 6. Fetch updated vendors for response
    vendors_final_resp = supabase_client.table("vendors").select("*").eq(
        "audit_id", audit_id
    ).order("created_at").execute()
    vendors_final = vendors_final_resp.data or []

    return {
        "audit_id": str(audit_id),
        "vendor_count": len(vendors_final),
        "risk_summary": risk_summary,
        "vendors": vendors_final,
    }
