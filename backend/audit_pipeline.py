"""
Full audit pipeline: persist audit + vendors, run fuzzy matching, update and return results.
Uses Supabase (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) and scripts.fuzzy_match.
"""

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

    # 2. Insert vendors (normalized_name set from input cleanup; risk_tier, match_evidence after match)
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

    # 3. Fuzzy match each vendor (same params as fuzzy_match.py: threshold=50, top_n=5, token_sort_ratio)
    risk_summary: dict[str, int] = {"red": 0, "amber": 0, "yellow": 0, "green": 0}
    for i, v in enumerate(vendors_data):
        raw_name = vendor_rows[i]["raw_input_name"]
        matches = match_vendor(raw_name, threshold=50, top_n=5)
        logger.info(
            "match_vendor(%r) -> %s",
            raw_name,
            [(m["matched_name"], m["score"], m.get("source_list")) for m in matches] if matches else "[]",
        )
        top_score = matches[0]["score"] if matches else 0
        tier = _score_to_tier(top_score)
        risk_summary[tier] += 1
        # normalized_name already set from input cleanup; only update risk_tier and match_evidence
        match_evidence = [dict(m) for m in matches] if matches else None

        supabase_client.table("vendors").update({
            "risk_tier": tier,
            "match_evidence": match_evidence,
        }).eq("id", v["id"]).execute()

    # 4. Update audit complete
    supabase_client.table("audits").update({
        "status": "complete",
        "completed_at": now,
    }).eq("id", audit_id).execute()

    # 5. Fetch updated vendors for response
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
