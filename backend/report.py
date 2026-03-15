"""
Generate and store JSON risk report for an audit.
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import jsonschema

from backend.config.scoring_config import get_scoring_config
from backend.overrides import get_effective_tier as _get_effective_tier
from backend.schemas.risk_report import (
    DEFAULT_DISCLAIMER,
    ReportMetadata,
    ReportSummary,
    VendorReportItem,
    VendorsByTier,
    WatchlistMetadataItem,
)

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "risk_report_schema.json"


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


def _get_override_history(supabase_client: Any, vendor_id: str, audit_id: str) -> list[dict[str, Any]]:
    resp = (
        supabase_client.table("vendor_overrides")
        .select("*")
        .eq("vendor_id", vendor_id)
        .eq("audit_id", audit_id)
        .order("overridden_at", desc=True)
        .execute()
    )
    return [dict(r) for r in (resp.data or [])]


def _get_watchlist_snapshots(supabase_client: Any) -> list[dict[str, Any]]:
    try:
        resp = (
            supabase_client.table("watchlist_snapshots")
            .select("source_list, snapshot_date, record_count, file_hash")
            .order("snapshot_date", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.debug("Could not fetch watchlist_snapshots: %s", e)
        return []


def get_effective_tier(supabase_client: Any, vendor_id: str, audit_id: str) -> tuple[str, str | None]:
    """
    Compatibility wrapper for overrides.get_effective_tier so tests and callers
    can patch `backend.report.get_effective_tier` without knowing the internal
    module structure.
    """
    return _get_effective_tier(supabase_client, vendor_id, audit_id)


def generate_risk_report(audit_id: str, supabase_client: Any) -> dict[str, Any]:
    """
    Build full JSON risk report for an audit. Validates against JSON Schema before returning.
    """
    audit_resp = supabase_client.table("audits").select("*").eq("id", audit_id).limit(1).execute()
    if not audit_resp.data or len(audit_resp.data) == 0:
        raise ValueError(f"Audit not found: {audit_id}")
    audit = audit_resp.data[0]

    vendors_resp = (
        supabase_client.table("vendors")
        .select("*")
        .eq("audit_id", audit_id)
        .order("created_at")
        .execute()
    )
    vendors = vendors_resp.data or []

    # Fetch all overrides for this audit in a single query so we can compute
    # effective tiers and histories in memory instead of per-vendor queries.
    overrides_resp = (
        supabase_client.table("vendor_overrides")
        .select("*")
        .eq("audit_id", audit_id)
        .order("overridden_at", desc=True)
        .execute()
    )
    overrides_all = overrides_resp.data or []

    override_history_by_vendor: dict[str, list[dict[str, Any]]] = {}
    active_override_by_vendor: dict[str, dict[str, Any]] = {}
    for row in overrides_all:
        vid = str(row.get("vendor_id"))
        if not vid:
            continue
        override_history_by_vendor.setdefault(vid, []).append(dict(row))
        if row.get("is_active"):
            # rows are ordered newest-first, so first active row is the current one
            if vid not in active_override_by_vendor:
                active_override_by_vendor[vid] = dict(row)

    config = get_scoring_config()
    watchlist_rows = _get_watchlist_snapshots(supabase_client)
    # One row per source_list: keep only the most recent snapshot per source.
    latest_snapshots: dict[str, dict[str, Any]] = {}
    for r in watchlist_rows:
        key = r.get("source_list") or ""
        if key not in latest_snapshots or (str(r.get("snapshot_date") or "") > str(latest_snapshots[key].get("snapshot_date") or "")):
            latest_snapshots[key] = r
    watchlist_metadata = [
        WatchlistMetadataItem(
            source_list=r.get("source_list", ""),
            snapshot_date=str(r.get("snapshot_date", "")),
            record_count=int(r.get("record_count", 0)),
            file_hash=r.get("file_hash"),
        )
        for r in latest_snapshots.values()
    ]

    by_tier: dict[str, int] = {"red": 0, "amber": 0, "yellow": 0, "green": 0}
    entity_keys: set[tuple[str, str]] = set()
    vendor_items: list[VendorReportItem] = []
    for v in vendors:
        vid = str(v["id"])
        base_tier = (v.get("risk_tier") or "green").lower()
        active_override = active_override_by_vendor.get(vid)
        effective = (active_override.get("override_tier") or base_tier).lower() if active_override else base_tier
        by_tier[effective] = by_tier.get(effective, 0) + 1
        override_history = override_history_by_vendor.get(vid, [])
        match_evidence_raw = v.get("match_evidence") or []
        if isinstance(match_evidence_raw, dict):
            match_evidence = match_evidence_raw.get("matches") or []
            resolved_group = match_evidence_raw.get("resolved_group") or []
        else:
            match_evidence = match_evidence_raw if isinstance(match_evidence_raw, list) else []
            resolved_group = []
        if match_evidence and isinstance(match_evidence[0], dict):
            entity_keys.add((str(match_evidence[0].get("source_list") or ""), str(match_evidence[0].get("matched_name") or "")))
        else:
            entity_keys.add((vid, v.get("raw_input_name") or ""))
        recommendations: list[str] = []
        if effective in ("red", "amber"):
            recommendations.append("Manual review recommended before compliance certificate.")
        if override_history:
            recommendations.append("This vendor has one or more manual overrides on file.")
        vendor_items.append(
            VendorReportItem(
                vendor_id=UUID(vid),
                raw_input_name=v.get("raw_input_name") or "",
                normalized_name=v.get("normalized_name"),
                country=v.get("country"),
                country_source=v.get("country_source"),
                parent_company=v.get("parent_company"),
                equipment_type=v.get("equipment_type"),
                risk_tier=v.get("risk_tier") or "green",
                effective_tier=effective,
                match_evidence=match_evidence,
                resolved_group=resolved_group,
                override_history=override_history,
                recommendations=recommendations,
            )
        )

    flagged = by_tier["red"] + by_tier["amber"] + by_tier["yellow"]
    if by_tier["red"] > 0:
        overall = "High risk: one or more vendors in Red tier. Do not submit without review."
    elif by_tier["amber"] > 0:
        overall = "Elevated risk: one or more vendors in Amber tier. Manual review required."
    elif by_tier["yellow"] > 0:
        overall = "Moderate: Yellow-tier vendors present. Review recommended."
    else:
        overall = "No Red or Amber flags. Green-tier only."

    report_metadata = ReportMetadata(
        audit_id=UUID(audit_id),
        organization_id=UUID(str(audit.get("organization_id", "00000000-0000-0000-0000-000000000001"))),
        organization_name="Default Organization",
        pipeline_version="1.0",
        scoring_config_version=config.version,
    )
    summary = ReportSummary(
        total_vendors=len(vendors),
        vendors_by_tier=VendorsByTier(**by_tier),
        overall_risk_assessment=overall,
        flagged_vendor_count=flagged,
        total_rows_uploaded=audit.get("total_rows_uploaded"),
        rows_skipped=audit.get("rows_skipped"),
        unique_entities=len(entity_keys),
    )
    ingestion_warnings = audit.get("ingestion_warnings") or []
    report = {
        "report_metadata": report_metadata.model_dump(mode="json"),
        "watchlist_metadata": [m.model_dump() for m in watchlist_metadata],
        "summary": summary.model_dump(),
        "vendors": [vi.model_dump(mode="json") for vi in vendor_items],
        "disclaimers": [DEFAULT_DISCLAIMER],
        "ingestion_warnings": ingestion_warnings,
    }
    schema = _load_schema()
    schema.pop("$schema", None)
    schema.pop("schema_version", None)
    schema.pop("title", None)
    try:
        jsonschema.validate(instance=report, schema=schema)
    except jsonschema.ValidationError as e:
        logger.error("Risk report schema validation failed: %s", e.message)
        raise
    return report
