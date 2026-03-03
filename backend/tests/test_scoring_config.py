"""Tests for scoring config load and validation."""

import os
import tempfile
from pathlib import Path

import pytest

# Ensure backend is importable
import sys
from pathlib import Path as P
_ROOT = P(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.config.scoring_config import (
    ScoringConfig,
    load_scoring_config,
    get_scoring_config,
    clear_scoring_config_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    clear_scoring_config_cache()
    yield
    clear_scoring_config_cache()


def test_load_default_config():
    """Default config loads and has expected structure."""
    config = load_scoring_config()
    assert config.version == "1.0.0"
    assert config.tier_thresholds.red == 95
    assert config.tier_thresholds.amber == 70
    assert config.tier_thresholds.yellow == 50
    assert config.score_weights.fuzzy_weight == 0.5
    assert config.score_weights.semantic_weight == 0.3
    assert config.score_weights.country_weight == 0.2
    assert "CN" in config.country_of_concern
    assert "RU" in config.country_of_concern


def test_get_scoring_config_returns_cached():
    """get_scoring_config returns same instance after load."""
    c1 = load_scoring_config()
    c2 = get_scoring_config()
    assert c1 is c2


def test_load_missing_file_raises():
    """Missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_scoring_config(Path("/nonexistent/scoring_config.yaml"))


def test_load_invalid_yaml_raises():
    """Invalid YAML raises."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"version: [ broken")
        f.flush()
        path = Path(f.name)
    try:
        with pytest.raises(Exception):  # yaml or pydantic
            load_scoring_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_weights_must_sum_to_one():
    """Config with weights not summing to 1.0 fails validation."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"""
version: "1.0.0"
last_modified: "2025-01-01T00:00:00Z"
tier_thresholds:
  red: 95
  amber: 85
  yellow: 70
score_weights:
  fuzzy_weight: 0.5
  semantic_weight: 0.5
  country_weight: 0.2
country_of_concern: [CN]
""")
        f.flush()
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="sum to 1.0"):
            load_scoring_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_thresholds_must_be_ordered():
    """Config with red < amber or amber < yellow fails validation."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"""
version: "1.0.0"
last_modified: "2025-01-01T00:00:00Z"
tier_thresholds:
  red: 70
  amber: 85
  yellow: 95
score_weights:
  fuzzy_weight: 0.5
  semantic_weight: 0.3
  country_weight: 0.2
country_of_concern: [CN]
""")
        f.flush()
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="red >= amber >= yellow"):
            load_scoring_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_integration_red_threshold_80():
    """Load config with red threshold 80; verify it is used (for re-run scoring test later)."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"""
version: "1.0.0"
last_modified: "2025-01-01T00:00:00Z"
tier_thresholds:
  red: 80
  amber: 75
  yellow: 70
score_weights:
  fuzzy_weight: 0.5
  semantic_weight: 0.3
  country_weight: 0.2
country_of_concern: [CN, RU]
""")
        f.flush()
        path = Path(f.name)
    try:
        config = load_scoring_config(path)
        assert config.tier_thresholds.red == 80
        assert config.tier_thresholds.amber == 75
        assert config.tier_thresholds.yellow == 70
    finally:
        path.unlink(missing_ok=True)
