import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from supabase import create_client

from .auth import require_auth
from .audits_schema import (
    MAX_FILE_SIZE_BYTES,
    parse_validated_csv,
    validate_csv,
)
from .audit_pipeline import run_audit_pipeline
from backend.overrides import apply_override, get_effective_tier
from backend.report import generate_risk_report

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_REPO_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(title="BioGate API")


@app.on_event("startup")
def _ensure_scoring_config_loaded():
    """Load and validate scoring config on startup; fail fast if missing or invalid."""
    from backend.config import load_scoring_config
    load_scoring_config()


def _get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CONFIG_MISSING",
                "message": "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set",
            },
        )
    return create_client(url, key)


@app.get("/health")
def health_check():
    """
    Heartbeat endpoint to verify the server is alive.
    Required for Week 1 Technical Foundation.
    """
    return {
        "status": "healthy",
        "service": "BioGate",
        "version": "1.0",
    }


@app.post("/audits/upload")
async def audits_upload(file: UploadFile = File(...), _: None = Depends(require_auth)):
    """
    Validate vendor audit CSV, persist to Supabase, run fuzzy matching, return full results.
    Accepts multipart/form-data with 'file' field.
    Returns audit_id, vendor_count, risk_summary, and vendors list with match_evidence.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_FILE_TYPE", "message": "File must be a .csv"},
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit",
            },
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_ENCODING",
                "message": f"File must be UTF-8 encoded: {e!s}",
            },
        ) from e

    result = validate_csv(text)
    if not result.valid:
        return result.to_response()

    rows = parse_validated_csv(text)
    if not rows:
        return {
            "valid": False,
            "row_count": 0,
            "errors": [{"code": "NO_VALID_ROWS", "message": "No vendor rows to process"}],
        }

    try:
        supabase = _get_supabase()
    except HTTPException:
        raise

    try:
        return run_audit_pipeline(rows, supabase)
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "PIPELINE_ERROR", "message": str(e)},
        ) from e


class OverrideBody(BaseModel):
    override_tier: str = Field(..., pattern="^(red|amber|yellow|green)$")
    justification: str = Field(..., min_length=20, description="Minimum 20 characters required for audit trail.")
    overridden_by: str = Field(..., min_length=1)


@app.post("/audits/{audit_id}/vendors/{vendor_id}/override")
async def post_vendor_override(
    audit_id: str,
    vendor_id: str,
    body: OverrideBody,
    _: None = Depends(require_auth),
):
    """
    Downgrade a vendor's risk tier with justification. Overrides can only reduce risk.
    Returns override record and legal disclaimer.
    """
    try:
        supabase = _get_supabase()
    except HTTPException:
        raise
    # Ensure audit and vendor exist and vendor belongs to audit
    audit_resp = supabase.table("audits").select("id").eq("id", audit_id).limit(1).execute()
    if not audit_resp.data or len(audit_resp.data) == 0:
        raise HTTPException(status_code=404, detail="Audit not found")
    vendor_resp = (
        supabase.table("vendors").select("id").eq("id", vendor_id).eq("audit_id", audit_id).limit(1).execute()
    )
    if not vendor_resp.data or len(vendor_resp.data) == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        result = apply_override(
            supabase,
            vendor_id,
            audit_id,
            body.override_tier,
            body.justification,
            body.overridden_by,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "OVERRIDE_INVALID", "message": str(e)},
        ) from e


@app.get("/audits/{audit_id}/vendors/{vendor_id}/overrides")
async def get_vendor_overrides(
    audit_id: str,
    vendor_id: str,
    _: None = Depends(require_auth),
):
    """Return override history for this vendor in this audit (newest first)."""
    try:
        supabase = _get_supabase()
    except HTTPException:
        raise
    vendor_resp = (
        supabase.table("vendors").select("id").eq("id", vendor_id).eq("audit_id", audit_id).limit(1).execute()
    )
    if not vendor_resp.data or len(vendor_resp.data) == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    resp = (
        supabase.table("vendor_overrides")
        .select("*")
        .eq("vendor_id", vendor_id)
        .eq("audit_id", audit_id)
        .order("overridden_at", desc=True)
        .execute()
    )
    return {"overrides": resp.data or []}


@app.get("/audits/{audit_id}/report")
async def get_audit_report(
    audit_id: str,
    _: None = Depends(require_auth),
):
    """Return the stored JSON risk report for an audit. 404 if not found."""
    try:
        supabase = _get_supabase()
    except HTTPException:
        raise
    resp = (
        supabase.table("audit_reports")
        .select("report_json")
        .eq("audit_id", audit_id)
        .limit(1)
        .execute()
    )
    if not resp.data or len(resp.data) == 0:
        raise HTTPException(status_code=404, detail="Report not found for this audit.")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=resp.data[0]["report_json"],
        media_type="application/json",
    )
