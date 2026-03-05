import hashlib
import os
from typing import Any

from fastapi import Header, HTTPException
from supabase import create_client


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """
    Placeholder auth dependency.

    If BIOGATE_API_KEY is set, require `Authorization: Bearer <key>` for protected routes.
    If unset, auth is effectively disabled (useful for local/dev and CI).
    """
    expected = os.getenv("BIOGATE_API_KEY")
    if not expected:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing Bearer token"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Invalid token"},
        )


def _get_supabase_for_limits() -> Any:
    """
    Lightweight Supabase client specifically for usage/credit tracking.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CONFIG_MISSING",
                "message": "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to enforce free-usage limits.",
            },
        )
    return create_client(url, key)


def _get_free_credit_limit() -> int | None:
    """
    Read BIOGATE_FREE_CREDITS from env.

    When unset or invalid, usage limiting is disabled (always allow).
    """
    raw = os.getenv("BIOGATE_FREE_CREDITS")
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def _build_identity(
    authorization: str | None,
    x_biogate_user: str | None,
) -> str | None:
    """
    Build a stable identity string for usage tracking.

    Priority:
    - X-Biogate-User (e.g. email or user id), lowercased
    - Authorization Bearer token (SHA-256 hashed)
    """
    if x_biogate_user:
        ident = x_biogate_user.strip().lower()
        if ident:
            return f"user:{ident}"

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            return f"api_key:{token_hash}"

    return None


def _enforce_free_credits(
    *,
    identity: str | None,
    endpoint: str,
) -> None:
    """
    Increment and enforce a simple "free credits" usage counter per (identity, endpoint).

    - Limit is BIOGATE_FREE_CREDITS (default disabled when unset).
    - Uses Supabase table `usage_counters` (see migration 010).
    """
    max_uses = _get_free_credit_limit()
    if max_uses is None:
        # Free-tier limiting disabled; always allow.
        return

    if not identity:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "IDENTITY_REQUIRED",
                "message": "Free-tier limiting is enabled. Provide X-Biogate-User or Authorization header so usage can be tracked.",
            },
        )

    supabase = _get_supabase_for_limits()
    table = supabase.table("usage_counters")

    resp = (
        table.select("id,count")
        .eq("identity", identity)
        .eq("endpoint", endpoint)
        .limit(1)
        .execute()
    )

    rows = resp.data or []
    if rows:
        row = rows[0]
        current_count = int(row.get("count") or 0)
        if current_count >= max_uses:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "FREE_TIER_EXHAUSTED",
                    "message": f"Free usage limit reached for this endpoint (max {max_uses} runs).",
                    "max_uses": max_uses,
                },
            )
        new_count = current_count + 1
        table.update({"count": new_count}).eq("id", row.get("id")).execute()
    else:
        table.insert(
            {
                "identity": identity,
                "endpoint": endpoint,
                "count": 1,
            }
        ).execute()


def require_free_credits_full_audit(
    authorization: str | None = Header(default=None),
    x_biogate_user: str | None = Header(default=None),
) -> None:
    """
    Dependency for /audits/upload_and_audit: enforces N free full-audit runs per identity.
    """
    identity = _build_identity(authorization, x_biogate_user)
    _enforce_free_credits(identity=identity, endpoint="audits/upload_and_audit")


def require_free_credits_batch_audit(
    authorization: str | None = Header(default=None),
    x_biogate_user: str | None = Header(default=None),
) -> None:
    """
    Dependency for /audits/upload_and_audit_batch: enforces N free batch audit runs per identity.
    """
    identity = _build_identity(authorization, x_biogate_user)
    _enforce_free_credits(identity=identity, endpoint="audits/upload_and_audit_batch")

