"""
Manual override: effective tier resolution and override application.
Overrides can only reduce risk tier (downgrade); original tier is preserved for audit.
"""

from typing import Any

# Risk order: higher index = higher risk. Override allowed only to a lower index.
TIER_ORDER = {"green": 0, "yellow": 1, "amber": 2, "red": 3}


def tier_rank(tier: str) -> int:
    return TIER_ORDER.get((tier or "").lower(), -1)


def is_lower_risk(new_tier: str, current_tier: str) -> bool:
    """True if new_tier is strictly lower risk than current_tier."""
    return tier_rank(new_tier) < tier_rank(current_tier)


def get_effective_tier(supabase_client: Any, vendor_id: str, audit_id: str) -> tuple[str, str | None]:
    """
    Return (effective_tier, override_id_if_any).
    If an active override exists, use override_tier; else use vendor.risk_tier.
    """
    override_resp = (
        supabase_client.table("vendor_overrides")
        .select("override_tier, id")
        .eq("vendor_id", vendor_id)
        .eq("audit_id", audit_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    overrides = override_resp.data or []
    if overrides:
        return (overrides[0]["override_tier"], str(overrides[0]["id"]))
    vendor_resp = (
        supabase_client.table("vendors")
        .select("risk_tier")
        .eq("id", vendor_id)
        .eq("audit_id", audit_id)
        .limit(1)
        .execute()
    )
    vendors = vendor_resp.data or []
    if not vendors:
        return ("green", None)
    return (vendors[0].get("risk_tier") or "green", None)


def apply_override(
    supabase_client: Any,
    vendor_id: str,
    audit_id: str,
    override_tier: str,
    justification: str,
    overridden_by: str,
) -> dict[str, Any]:
    """
    Create a new override and supersede any existing active override.
    Validates that override_tier is lower risk than current effective tier.
    Returns the new override row and disclaimer.
    """
    effective, _ = get_effective_tier(supabase_client, vendor_id, audit_id)
    if not is_lower_risk(override_tier, effective):
        raise ValueError(
            "Overrides can only reduce risk tier, not increase it. "
            "To flag additional risk, create a new audit or contact BioGate support."
        )
    vendor_resp = (
        supabase_client.table("vendors")
        .select("risk_tier")
        .eq("id", vendor_id)
        .eq("audit_id", audit_id)
        .limit(1)
        .execute()
    )
    vendors = vendor_resp.data or []
    original_tier = (vendors[0].get("risk_tier") or "green") if vendors else "green"

    # Deactivate current active override(s)
    supabase_client.table("vendor_overrides").update({"is_active": False}).eq(
        "vendor_id", vendor_id
    ).eq("audit_id", audit_id).eq("is_active", True).execute()

    # Insert new override
    row = {
        "vendor_id": vendor_id,
        "audit_id": audit_id,
        "original_tier": original_tier,
        "override_tier": override_tier,
        "justification": justification,
        "overridden_by": overridden_by,
    }
    ins = supabase_client.table("vendor_overrides").insert(row).execute()
    data = ins.data
    if not data or len(data) != 1:
        raise RuntimeError("Failed to create override record")
    out = dict(data[0])
    out["disclaimer"] = (
        "This override and its consequences are your organization's responsibility. "
        "BioGate records this action for audit trail purposes."
    )
    return out
