import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from supabase import create_client

from .audits_schema import (
    MAX_FILE_SIZE_BYTES,
    parse_validated_csv,
    validate_csv,
)
from .audit_pipeline import run_audit_pipeline

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(title="BioGate API")


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
async def audits_upload(file: UploadFile = File(...)):
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
