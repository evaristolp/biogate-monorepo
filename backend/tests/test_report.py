"""Tests for risk report generation and schema validation."""

import json
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_report_schema_valid():
    """Generated report validates against JSON Schema."""
    from backend.report import generate_risk_report
    from backend.config.scoring_config import load_scoring_config, clear_scoring_config_cache
    from backend.schemas.risk_report import DEFAULT_DISCLAIMER
    from unittest.mock import patch
    clear_scoring_config_cache()
    load_scoring_config()

    audit_id = str(uuid4())
    org_id = "00000000-0000-0000-0000-000000000001"
    vendor_id = str(uuid4())
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": audit_id, "organization_id": org_id}
    ]
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {
            "id": vendor_id,
            "raw_input_name": "Test Vendor",
            "normalized_name": "Test Vendor",
            "country": "US",
            "parent_company": None,
            "equipment_type": None,
            "risk_tier": "green",
            "match_evidence": [],
        }
    ]
    mock.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    mock.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    mock.table.return_value.select.return_value.order.return_value.execute.return_value.data = []

    with patch("backend.report.get_effective_tier", return_value=("green", None)):
        report = generate_risk_report(audit_id, mock)
    assert "report_metadata" in report
    assert "summary" in report
    assert report["summary"]["total_vendors"] == 1
    assert report["summary"]["vendors_by_tier"]["green"] == 1
    assert report["vendors"][0]["effective_tier"] == "green"
    assert report["vendors"][0]["raw_input_name"] == "Test Vendor"
    assert DEFAULT_DISCLAIMER in report["disclaimers"]


def test_report_schema_structure():
    """Report has all required top-level keys."""
    from backend.schemas.risk_report import RiskReport, ReportMetadata, ReportSummary, VendorsByTier
    from backend.schemas.risk_report import DEFAULT_DISCLAIMER
    from uuid import uuid4
    report = RiskReport(
        report_metadata=ReportMetadata(audit_id=uuid4(), organization_id=uuid4()),
        summary=ReportSummary(
            total_vendors=0,
            vendors_by_tier=VendorsByTier(),
            overall_risk_assessment="No vendors.",
            flagged_vendor_count=0,
        ),
        vendors=[],
        disclaimers=[DEFAULT_DISCLAIMER],
    )
    d = report.model_dump(mode="json")
    assert "report_metadata" in d and "summary" in d and "vendors" in d and "disclaimers" in d
