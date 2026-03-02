"""Tests for /audits/upload endpoint."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


"""Tests for /audits/upload endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@patch("backend.main.run_audit_pipeline")
def test_upload_valid_csv(mock_pipeline):
    mock_pipeline.return_value = {
        "audit_id": "11111111-1111-1111-1111-111111111111",
        "vendor_count": 2,
        "risk_summary": {"red": 0, "amber": 1, "yellow": 0, "green": 1},
        "vendors": [
            {"id": "v1", "raw_input_name": "Acme Biotech", "risk_tier": "green"},
            {"id": "v2", "raw_input_name": "BGI Genomics", "risk_tier": "amber"},
        ],
    }
    csv_content = b"vendor_name,supplier_id,country\nAcme Biotech,SUP-001,US\nBGI Genomics,SUP-002,CN"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit_id"] == "11111111-1111-1111-1111-111111111111"
    assert data["vendor_count"] == 2
    assert data["risk_summary"] == {"red": 0, "amber": 1, "yellow": 0, "green": 1}
    assert len(data["vendors"]) == 2
    mock_pipeline.assert_called_once()


def test_upload_missing_required_column():
    csv_content = b"supplier_id,country\nSUP-001,US"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert data["row_count"] == 0
    assert any(e["code"] == "MISSING_REQUIRED_COLUMN" for e in data["errors"])


def test_upload_empty_vendor_name():
    csv_content = b"vendor_name,supplier_id\n,SUP-001\nValid Vendor,SUP-002"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any(e["code"] == "EMPTY_REQUIRED_FIELD" for e in data["errors"])


def test_upload_non_csv_rejected():
    resp = client.post("/audits/upload", files={"file": ("data.txt", b"not csv", "text/plain")})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"
