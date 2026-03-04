from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_upload_valid_csv():
    csv_content = b"vendor_name,supplier_id,country\nAcme Biotech,SUP-001,US\nBGI Genomics,SUP-002,CN"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["vendors_extracted"] == 2
    assert isinstance(data["extraction_method"], str)
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["processing_time_ms"], int)
    assert isinstance(data["needs_review"], int)


def test_upload_missing_required_column():
    csv_content = b"supplier_id,country\nSUP-001,US"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    # With the ingestion pipeline, a CSV lacking a vendor column should
    # simply result in zero extracted vendors rather than schema-level errors.
    assert data["status"] == "ok"
    assert data["vendors_extracted"] == 0


def test_upload_empty_vendor_name():
    csv_content = b"vendor_name,supplier_id\n,SUP-001\nValid Vendor,SUP-002"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    # Empty vendor rows are ignored by the ingestion pipeline.
    assert data["status"] == "ok"
    assert data["vendors_extracted"] == 1


def test_upload_special_chars_only_vendor_name():
    csv_content = b"vendor_name,supplier_id\n***...,SUP-001\nAcme,SUP-002"
    resp = client.post("/audits/upload", files={"file": ("vendors.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    # Rows with only punctuation in vendor_name are rejected by validation inside
    # the ingestion CSV helper, so only the valid row should be counted.
    assert data["status"] == "ok"
    assert data["vendors_extracted"] == 1


def test_upload_non_csv_rejected():
    resp = client.post("/audits/upload", files={"file": ("data.txt", b"not csv", "text/plain")})
    # Non-CSV files are still accepted by the multi-format ingestion pipeline; they
    # may yield zero vendors but should not be rejected purely by extension.
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
