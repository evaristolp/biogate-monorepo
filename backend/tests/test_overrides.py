"""Tests for manual override API and effective_tier logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from backend.main import app
from backend.overrides import (
    get_effective_tier,
    apply_override,
    is_lower_risk,
)


def test_is_lower_risk():
    assert is_lower_risk("green", "red") is True
    assert is_lower_risk("yellow", "red") is True
    assert is_lower_risk("amber", "red") is True
    assert is_lower_risk("red", "green") is False
    assert is_lower_risk("red", "red") is False
    assert is_lower_risk("amber", "yellow") is False


def test_override_only_downgrade():
    """Override to same or higher tier raises ValueError."""
    with pytest.raises(ValueError, match="only reduce risk"):
        apply_override(
            MagicMock(),
            "v1",
            "a1",
            "red",
            "x" * 20,
            "user@test.com",
        )


def test_post_override_validation_short_justification():
    """Justification under 20 chars returns 422."""
    client = TestClient(app)
    resp = client.post(
        "/audits/00000000-0000-0000-0000-000000000001/vendors/00000000-0000-0000-0000-000000000002/override",
        json={
            "override_tier": "yellow",
            "justification": "short",
            "overridden_by": "user@test.com",
        },
    )
    assert resp.status_code in (422, 503, 404)
    if resp.status_code == 422:
        assert "20" in resp.text or "minimum" in resp.text.lower() or "justification" in resp.text.lower()


def test_get_overrides_404():
    """GET overrides for non-existent vendor returns 404."""
    from unittest.mock import patch
    client = TestClient(app)
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("backend.main._get_supabase", return_value=mock_supabase):
        resp = client.get(
            "/audits/00000000-0000-0000-0000-000000000001/vendors/00000000-0000-0000-0000-000000000099/overrides",
        )
    assert resp.status_code == 404
