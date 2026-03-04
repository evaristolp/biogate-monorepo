from __future__ import annotations

from pathlib import Path
from typing import Any

import sys

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.ingestion.base import ExtractedVendor, ExtractionResult, ExtractionMethod  # noqa: E402
from backend.ingestion.orchestrator import (  # noqa: E402
    run_document_audit,
    _extracted_vendors_to_rows,
)


def test_extracted_vendors_to_rows_normalizes_and_filters():
    vendors = [
        ExtractedVendor(raw_name="  Acme Corp  ", country_hint="US", equipment_type_hint="Sequencers"),
        ExtractedVendor(raw_name="!!!", country_hint=None),
        ExtractedVendor(raw_name="", country_hint=None),
    ]
    rows = _extracted_vendors_to_rows(vendors)
    assert len(rows) == 1
    row = rows[0]
    assert row["vendor_name"] == "Acme Corp"
    assert row["country"] == "US"
    assert row["product_category"] == "Sequencers"


class _DummySupabase:
    def __init__(self):
        self.last_rows: list[dict[str, Any]] | None = None

    def table(self, *args, **kwargs):  # pragma: no cover - not used in this test
        raise AssertionError("Supabase client should not be used directly in orchestrator tests")


def test_run_document_audit_calls_audit_pipeline(monkeypatch, tmp_path: Path):
    from backend import ingestion as _pkg  # noqa: F401

    # Prepare fake extracted vendors
    extraction = ExtractionResult(
        vendors=[
            ExtractedVendor(raw_name="Acme Corp", country_hint="US"),
        ],
        extraction_method=ExtractionMethod.CSV_PARSER,
    )

    def _fake_process_document(path: str, audit_id: str, org_id: str) -> ExtractionResult:
        return extraction

    def _fake_run_audit_pipeline(rows, supabase_client):
        supabase_client.last_rows = rows
        return {"audit_id": "test-audit", "vendor_count": len(rows), "risk_summary": {}, "vendors": []}

    monkeypatch.setattr("backend.ingestion.orchestrator.process_document", _fake_process_document)
    monkeypatch.setattr("backend.ingestion.orchestrator.run_audit_pipeline", _fake_run_audit_pipeline)

    dummy_supabase = _DummySupabase()
    dummy_path = tmp_path / "dummy.csv"
    dummy_path.write_text("Vendor\nAcme Corp\n", encoding="utf-8")

    audit_result, extraction_result = run_document_audit(str(dummy_path), dummy_supabase)

    assert audit_result is not None
    assert audit_result["audit_id"] == "test-audit"
    assert dummy_supabase.last_rows is not None
    assert dummy_supabase.last_rows[0]["vendor_name"] == "Acme Corp"
    assert extraction_result is extraction


def test_run_document_audit_returns_none_when_no_rows(monkeypatch, tmp_path: Path):
    empty_extraction = ExtractionResult(vendors=[], extraction_method=ExtractionMethod.CSV_PARSER)

    def _fake_process_document(path: str, audit_id: str, org_id: str) -> ExtractionResult:
        return empty_extraction

    monkeypatch.setattr("backend.ingestion.orchestrator.process_document", _fake_process_document)

    dummy_supabase = _DummySupabase()
    dummy_path = tmp_path / "dummy.csv"
    dummy_path.write_text("", encoding="utf-8")

    audit_result, extraction_result = run_document_audit(str(dummy_path), dummy_supabase)
    assert audit_result is None
    assert extraction_result is empty_extraction

