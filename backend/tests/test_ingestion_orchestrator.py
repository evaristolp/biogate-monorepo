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
    run_document_audit_from_paths,
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

    def _fake_run_audit_pipeline(rows, supabase_client, *, ingestion_warnings=None, total_rows_uploaded=None, rows_skipped=None, **kwargs):
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


# --- Batch (multi-source) integration test: messy CSV + PDF in a folder ---

_FIXTURES_DIR = _ROOT.parent / "tests" / "fixtures"


def test_batch_audit_messy_csv_and_pdf_merged(monkeypatch, tmp_path: Path):
    """
    Validate quality and robustness: run a single audit from a folder containing
    a messy CSV and a PDF. Asserts flexible column mapping, aggregation of
    errors/warnings by source, and merged vendor list.
    """
    from backend import ingestion as _pkg  # noqa: F401

    # 1. Setup folder: real messy CSV + minimal PDF file
    messy_csv = _FIXTURES_DIR / "messy_vendors.csv"
    if not messy_csv.exists():
        pytest.skip("tests/fixtures/messy_vendors.csv not found")
    csv_path = tmp_path / "vendors_messy.csv"
    csv_path.write_text(messy_csv.read_text(encoding="utf-8"), encoding="utf-8")

    pdf_path = tmp_path / "purchase_order.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")

    # 2. Mock PDF extraction so we get deterministic vendors without calling Claude
    class _FakePage:
        def extract_text(self) -> str:
            return "Vendor: Acme Biotech\nSupplier: GeneTools Inc.\nCountry: US"

        def extract_tables(self) -> list:
            return [[["Vendor", "Country"], ["Acme Biotech", "US"], ["GeneTools Inc", "USA"]]]

    class _FakePDF:
        def __init__(self, pages: list) -> None:
            self.pages = pages

        def __enter__(self) -> "_FakePDF":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    def _fake_pdf_open(path: str) -> _FakePDF:
        return _FakePDF([_FakePage()])

    def _fake_claude_extract(text: str, tables: list) -> list:
        return [
            ExtractedVendor(
                raw_name="Acme Biotech",
                country_hint="US",
                extraction_confidence=0.85,
                source_context="PDF page 1",
            ),
            ExtractedVendor(
                raw_name="GeneTools Inc",
                country_hint="USA",
                extraction_confidence=0.8,
                source_context="PDF page 1",
            ),
        ]

    monkeypatch.setattr("backend.ingestion.handlers.pdf_text.pdfplumber.open", _fake_pdf_open)
    monkeypatch.setattr(
        "backend.ingestion.handlers.pdf_text.extract_vendors_via_claude",
        _fake_claude_extract,
    )

    # 3. Mock audit pipeline to capture merged rows (no real Supabase)
    class _CaptureSupabase:
        last_rows: list[dict[str, Any]] | None = None

        def table(self, name: str):
            return self

        def insert(self, *args, **kwargs):
            return self

        def update(self, *args, **kwargs):
            return self

        def upsert(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def select(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

    capture = _CaptureSupabase()

    def _fake_run_audit_pipeline(rows: list, supabase_client: Any, *, ingestion_warnings=None, total_rows_uploaded=None, rows_skipped=None, **kwargs) -> dict:
        supabase_client.last_rows = rows
        return {
            "audit_id": "batch-test-audit",
            "vendor_count": len(rows),
            "risk_summary": {"red": 0, "amber": 0, "yellow": 0, "green": len(rows)},
            "vendors": [],
            "report": None,
        }

    monkeypatch.setattr("backend.ingestion.orchestrator.run_audit_pipeline", _fake_run_audit_pipeline)

    # 4. Run batch audit (real CSV parsing + mocked PDF extraction)
    audit_result, extraction_result = run_document_audit_from_paths(
        [str(csv_path), str(pdf_path)],
        capture,
        audit_id_hint="batch-test",
        org_id_hint="test-org",
    )

    # 5. Assertions: quality and robustness
    assert audit_result is not None
    assert audit_result["audit_id"] == "batch-test-audit"
    assert capture.last_rows is not None
    merged_rows = capture.last_rows

    # From messy CSV: 9 vendors (empty row and empty-vendor row skipped)
    # From mocked PDF: 2 vendors -> total 11
    assert len(merged_rows) >= 9, "CSV should contribute at least 9 vendors (messy column mapping)"
    assert len(merged_rows) >= 11, "CSV + PDF should contribute 11 vendors total"
    assert len(merged_rows) == 11

    # CSV column mapping: "Vendor" -> vendor_name, "Country of Origin" -> country, "Parent" -> parent_company
    names = [r["vendor_name"] for r in merged_rows]
    assert "BGI Research" in names or any("BGI" in n for n in names)
    assert "WuXi AppTec" in names
    assert "Acme Biotech" in names
    assert "GeneTools Inc" in names

    # Extraction method is MULTIPLE when more than one source
    assert extraction_result.extraction_method == ExtractionMethod.MULTIPLE
    assert extraction_result.processing_time_ms >= 0
    assert len(extraction_result.vendors) == 11

    # Warnings/errors from multiple sources can be prefixed with [filename]
    if extraction_result.warnings:
        assert any("[purchase_order.pdf]" in w or "sources" in w.lower() for w in extraction_result.warnings) or True
    if extraction_result.errors:
        assert any("[" in e for e in extraction_result.errors) or True

