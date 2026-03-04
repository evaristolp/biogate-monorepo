from __future__ import annotations

from pathlib import Path
from typing import Any, List

import sys

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.ingestion.base import ExtractedVendor  # noqa: E402
from backend.ingestion.handlers.excel import (  # noqa: E402
    detect_columns,
    extract_vendor_from_row,
    _extract_from_sheet,
)
from backend.ingestion.handlers.pdf_text import extract_from_pdf_text  # noqa: E402
from backend.ingestion.handlers.email import extract_from_email  # noqa: E402
from backend.ingestion.handlers.docx import extract_from_docx  # noqa: E402


class _FakeSheet:
    def __init__(self, title: str, rows: List[List[Any]]) -> None:
        self.title = title
        self._rows = rows

    def iter_rows(self, values_only: bool = False):
        # The excel handler requests values_only=False but only ever inspects
        # the cell.value attribute; for tests we can return the raw values.
        return self._rows


def test_excel_detect_columns_and_extract_vendor():
    header = ["Vendor Name", "Country", "Product"]
    row = ["Acme Corp", "US", "Sequencing instruments"]
    header_idx, col_map = detect_columns([header, row])
    assert header_idx == 0
    assert col_map["name"] == 0
    assert col_map["country"] == 1
    assert col_map["equipment"] == 2

    vendor = extract_vendor_from_row(row, col_map)
    assert isinstance(vendor, ExtractedVendor)
    assert vendor.raw_name == "Acme Corp"
    assert vendor.country_hint == "US"
    assert vendor.equipment_type_hint == "Sequencing instruments"


def test_excel_extract_from_sheet_sets_context():
    rows = [
        ["Vendor", "Country"],
        ["BGI Genomics", "CN"],
    ]
    sheet = _FakeSheet("Sheet1", rows)
    vendors = _extract_from_sheet(sheet)  # type: ignore[arg-type]
    assert len(vendors) == 1
    v = vendors[0]
    assert v.raw_name == "BGI Genomics"
    assert "Sheet 'Sheet1', Row 2" in v.source_context
    assert v.extraction_confidence > 0


def test_email_handler_returns_result(tmp_path: Path):
    eml_path = tmp_path / "test.eml"
    eml_path.write_text(
        "From: test@example.com\nTo: dest@example.com\nSubject: Vendor\n\n"
        "Acme Corp provided sequencing instruments.",
        encoding="utf-8",
    )
    result = extract_from_email(str(eml_path))
    assert result.extraction_method.name == "EMAIL_PARSER"
    # For now we do not attempt vendor extraction; ensure we at least surface a warning.
    assert not result.vendors
    assert result.warnings or result.errors is not None


def test_docx_handler_handles_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    result = extract_from_docx(str(missing))
    assert result.extraction_method.name == "DOCX_PARSER"
    assert not result.vendors
    assert result.errors  # file-not-found surfaced


def test_pdf_text_handler_uses_claude_via_monkeypatch(monkeypatch, tmp_path: Path):
    # Create a tiny "PDF" file; content is irrelevant because we fully mock pdfplumber
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

    class _FakePage:
        def extract_text(self) -> str:
            return "Acme Corp\tUS"

        def extract_tables(self):
            return []

    class _FakePDF:
        def __init__(self, pages):
            self.pages = pages

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_open(path: str):
        return _FakePDF([_FakePage()])

    def _fake_extract_vendors(text: str, tables):
        return [
            ExtractedVendor(
                raw_name="Acme Corp",
                country_hint="US",
                extraction_confidence=0.8,
                source_context="test",
            )
        ]

    monkeypatch.setattr("backend.ingestion.handlers.pdf_text.pdfplumber.open", _fake_open)
    monkeypatch.setattr("backend.ingestion.handlers.pdf_text.extract_vendors_via_claude", _fake_extract_vendors)

    result = extract_from_pdf_text(str(pdf_path))
    assert result.extraction_method.name == "PDF_TEXT"
    assert len(result.vendors) == 1
    assert result.page_count == 1
    assert pytest.approx(result.extraction_confidence, rel=1e-3) == 0.8

