import logging
import os
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from supabase import create_client

from .auth import (
    require_auth,
    require_free_credits_batch_audit,
    require_free_credits_full_audit,
)
from .audits_schema import MAX_FILE_SIZE_BYTES
from backend.ingestion.orchestrator import run_document_audit, run_document_audit_from_paths
from backend.document_uploads import record_document_upload
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


def _is_permission_denied(err: BaseException) -> bool:
    """True if the error is a Postgres/Supabase permission-denied on a table."""
    parts = []
    if getattr(err, "message", None):
        parts.append(str(err.message).lower())
    if getattr(err, "details", None):
        parts.append(str(err.details).lower())
    parts.append(str(err).lower())
    if getattr(err, "args", ()):
        parts.extend(str(a).lower() for a in err.args)
    text = " ".join(parts)
    return "permission denied" in text and "table" in text


def _raise_config_error_if_permission_denied(err: BaseException) -> None:
    """If err looks like a DB permission error, raise a 503 with deployment guidance."""
    if _is_permission_denied(err):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DB_PERMISSION_DENIED",
                "message": (
                    "Permission denied for a database table. The backend must use the Supabase "
                    "service role key (not the anon key). In Supabase: Project Settings → API → "
                    "use the secret 'service_role' key for SUPABASE_SERVICE_ROLE_KEY."
                ),
            },
        ) from err


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


@app.get("/verify/{certificate_id}")
async def verify_certificate_endpoint(certificate_id: str):
    """
    Public verification endpoint: returns JSON confirming certificate authenticity.
    Scan the QR code on the Compliance Certificate or visit this URL with the certificate ID.
    """
    try:
        supabase = _get_supabase()
    except HTTPException:
        raise
    from backend.certificate import verify_certificate as do_verify
    result = do_verify(certificate_id, supabase)
    if result is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return result


@app.post("/audits/upload")
async def audits_upload(file: UploadFile = File(...), _: None = Depends(require_auth)):
    """
    Run the multi-format ingestion pipeline on an uploaded document.

    Accepts multipart/form-data with 'file' field. The file may be CSV, Excel,
    PDF, image, email, or DOCX. Returns high-level extraction metadata suitable
    for front-end review workflows.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_FILE", "message": "Uploaded file must have a filename"},
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

    suffix = "".join(Path(file.filename).suffixes) or ".dat"
    tmp_path = _REPO_ROOT / "tmp" / f"upload-{uuid.uuid4().hex}{suffix}"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        tmp_path.write_bytes(content)

        # For now we use simple placeholders; these identifiers are primarily
        # for logging / observability within the ingestion pipeline.
        audit_id = "api-upload"
        org_id = "api-user"

        from backend.ingestion.pipeline import process_document

        result = process_document(str(tmp_path), audit_id=audit_id, org_id=org_id)

        needs_review_count = sum(1 for v in result.vendors if v.needs_review)

        try:
            supabase = _get_supabase()
            record_document_upload(
                supabase,
                file.filename or "unknown",
                len(content),
                result,
                audit_id=None,
            )
        except HTTPException:
            pass
        except Exception as e:
            _raise_config_error_if_permission_denied(e)
            raise

        return {
            "status": "ok",
            "vendors_extracted": len(result.vendors),
            "errors": result.errors,
            "warnings": result.warnings,
            "extraction_method": (
                result.extraction_method.value
                if hasattr(result.extraction_method, "value")
                else str(result.extraction_method)
            ),
            "confidence": result.extraction_confidence,
            "processing_time_ms": result.processing_time_ms,
            "needs_review": needs_review_count,
        }
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            # Best-effort cleanup; do not fail the request if deletion fails.
            pass


@app.post("/audits/upload_and_audit_batch")
async def audits_upload_and_audit_batch(
    files: list[UploadFile] = File(..., description="Multiple files (e.g. folder of CSVs, PDFs, images) for one audit"),
    auth_ok: None = Depends(require_auth),
    credits_ok: None = Depends(require_free_credits_batch_audit),
):
    """
    Run a single audit from multiple source files (folder / multi-source audit).

    Accepts multipart/form-data with 'files' field containing one or more files.
    Each file can be CSV, Excel, PDF, image, email, or DOCX. All extracted
    vendors are merged into one audit. Response shape matches upload_and_audit,
    with ingestion errors/warnings prefixed by filename.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail={"code": "NO_FILES", "message": "At least one file is required. Use 'files' for multiple sources."},
        )

    for f in files:
        if not f.filename or not f.filename.strip():
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_FILE", "message": "Every uploaded file must have a filename"},
            )

    tmp_dir = None
    paths: list[str] = []
    total_size = 0
    try:
        tmp_dir = tempfile.mkdtemp(prefix="biogate-batch-")
        tmp_path = Path(tmp_dir)
        used_names: set[str] = set()
        used_count: dict[str, int] = {}
        for i, upload in enumerate(files):
            content = await upload.read()
            total_size += len(content)
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "FILE_TOO_LARGE",
                        "message": f"File {upload.filename} exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit",
                    },
                )
            base_name = (Path(upload.filename).name or "").strip() or f"file_{i}.bin"
            if base_name in used_names:
                count = used_count[base_name]
                stem, ext = Path(base_name).stem, Path(base_name).suffix
                name = f"{stem}_{count}{ext}"
                used_count[base_name] = count + 1
            else:
                used_names.add(base_name)
                used_count[base_name] = 1
                name = base_name
            out_path = tmp_path / name
            out_path.write_bytes(content)
            paths.append(str(out_path))

        try:
            supabase = _get_supabase()
        except HTTPException:
            raise

        try:
            audit_result, extraction_result = run_document_audit_from_paths(
                paths,
                supabase,
                audit_id_hint="api-upload",
                org_id_hint="api-user",
            )
        except Exception as e:
            _raise_config_error_if_permission_denied(e)
            raise

        if audit_result is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INGESTION_FAILED",
                    "message": "No valid vendor rows could be extracted from the uploaded files.",
                    "ingestion": {
                        "vendors_extracted": len(extraction_result.vendors),
                        "errors": extraction_result.errors,
                        "warnings": extraction_result.warnings,
                        "extraction_method": (
                            extraction_result.extraction_method.value
                            if hasattr(extraction_result.extraction_method, "value")
                            else str(extraction_result.extraction_method)
                        ),
                        "confidence": extraction_result.extraction_confidence,
                        "processing_time_ms": extraction_result.processing_time_ms,
                    },
                },
            )

        record_document_upload(
            supabase,
            f"batch ({len(paths)} files)",
            total_size,
            extraction_result,
            audit_id=audit_result["audit_id"],
        )

        needs_review_count = sum(1 for v in extraction_result.vendors if v.needs_review)
        audit_payload = dict(audit_result)
        audit_payload["ingestion"] = {
            "vendors_extracted": len(extraction_result.vendors),
            "sources_processed": len(paths),
            "errors": extraction_result.errors,
            "warnings": extraction_result.warnings,
            "extraction_method": (
                extraction_result.extraction_method.value
                if hasattr(extraction_result.extraction_method, "value")
                else str(extraction_result.extraction_method)
            ),
            "confidence": extraction_result.extraction_confidence,
            "processing_time_ms": extraction_result.processing_time_ms,
            "needs_review": needs_review_count,
        }
        return audit_payload
    finally:
        if tmp_dir:
            try:
                for p in paths:
                    try:
                        Path(p).unlink(missing_ok=True)
                    except Exception:
                        pass
                Path(tmp_dir).rmdir()
            except Exception:
                pass


@app.post("/audits/upload_and_audit")
async def audits_upload_and_audit(
    file: UploadFile = File(...),
    auth_ok: None = Depends(require_auth),
    credits_ok: None = Depends(require_free_credits_full_audit),
):
    """
    Run a full audit using the multi-format ingestion pipeline.

    Accepts multipart/form-data with 'file' field. The file may be CSV, Excel,
    or text-based PDF (additional formats are experimental). Extracted vendors
    are fed into the existing audit pipeline so the response shape matches the
    CSV-based flow (`audit_id`, `risk_summary`, `vendors`, `report`), with an
    additional `ingestion` block that surfaces extraction metadata.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_FILE", "message": "Uploaded file must have a filename"},
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

    suffix = "".join(Path(file.filename).suffixes) or ".dat"
    tmp_path = _REPO_ROOT / "tmp" / f"upload-{uuid.uuid4().hex}{suffix}"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        tmp_path.write_bytes(content)

        try:
            supabase = _get_supabase()
        except HTTPException:
            raise

        try:
            audit_result, extraction_result = run_document_audit(
                str(tmp_path),
                supabase,
                audit_id_hint="api-upload",
                org_id_hint="api-user",
            )
        except Exception as e:
            _raise_config_error_if_permission_denied(e)
            raise

        if audit_result is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INGESTION_FAILED",
                    "message": "No valid vendor rows could be extracted from the document.",
                    "ingestion": {
                        "vendors_extracted": len(extraction_result.vendors),
                        "errors": extraction_result.errors,
                        "warnings": extraction_result.warnings,
                        "extraction_method": (
                            extraction_result.extraction_method.value
                            if hasattr(extraction_result.extraction_method, "value")
                            else str(extraction_result.extraction_method)
                        ),
                        "confidence": extraction_result.extraction_confidence,
                        "processing_time_ms": extraction_result.processing_time_ms,
                    },
                },
            )

        record_document_upload(
            supabase,
            file.filename or "unknown",
            len(content),
            extraction_result,
            audit_id=audit_result["audit_id"],
        )

        needs_review_count = sum(1 for v in extraction_result.vendors if v.needs_review)
        audit_payload = dict(audit_result)
        audit_payload["ingestion"] = {
            "vendors_extracted": len(extraction_result.vendors),
            "errors": extraction_result.errors,
            "warnings": extraction_result.warnings,
            "extraction_method": (
                extraction_result.extraction_method.value
                if hasattr(extraction_result.extraction_method, "value")
                else str(extraction_result.extraction_method)
            ),
            "confidence": extraction_result.extraction_confidence,
            "processing_time_ms": extraction_result.processing_time_ms,
            "needs_review": needs_review_count,
        }
        return audit_payload
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            # Best-effort cleanup; do not fail the request if deletion fails.
            pass


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
