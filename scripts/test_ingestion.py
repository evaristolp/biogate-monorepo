"""
Unit tests for the BioGate ingestion pipeline and fuzzy matching.

Run: pytest scripts/test_ingestion.py -v
From repo root: pytest scripts/test_ingestion.py -v (requires pythonpath to include scripts)
"""

import os
import sys
from unittest.mock import patch

import pytest

# Ensure scripts directory is on path for imports when running tests from repo root
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import ingest_bis
import fuzzy_match


# --- 1. Name normalization (from ingest_bis) ---


def test_normalize_entity_name_extra_whitespace_stripped():
    # Multiple spaces collapsed to single, then title case
    assert ingest_bis._normalize_entity_name("  BGI   Genomics  ") == "Bgi Genomics"


def test_normalize_entity_name_title_casing_applied():
    assert ingest_bis._normalize_entity_name("bgi genomics") == "Bgi Genomics"
    assert ingest_bis._normalize_entity_name("ACME CORP") == "Acme Corp"


def test_normalize_entity_name_empty_string_returns_empty():
    assert ingest_bis._normalize_entity_name("") == ""


def test_normalize_entity_name_none_returns_empty():
    assert ingest_bis._normalize_entity_name(None) == ""


# --- 2. Alias parsing (from ingest_bis) ---


def test_parse_aliases_semicolon_separated():
    assert ingest_bis._parse_aliases("alias1; alias2; alias3") == ["alias1", "alias2", "alias3"]


def test_parse_aliases_pipe_separated():
    assert ingest_bis._parse_aliases("alias1|alias2") == ["alias1", "alias2"]


def test_parse_aliases_empty_string_returns_empty_list():
    assert ingest_bis._parse_aliases("") == []


def test_parse_aliases_none_returns_empty_list():
    assert ingest_bis._parse_aliases(None) == []


def test_parse_aliases_comma_separated():
    assert ingest_bis._parse_aliases("a, b, c") == ["a", "b", "c"]


# --- 3–5. Fuzzy match with mocked watchlist ---

# Test watchlist: (choices, meta) for injection into fuzzy_match
TEST_CHOICES = [
    "Bgi Genomics Co., Ltd.",
    "Acme Corporation",
    "Example Inc.",
    "BGI",
]
TEST_META: list[tuple[str, str, str | None, str]] = [
    ("Bgi Genomics Co., Ltd.", "BIS_ENTITY_LIST", "China", "name"),
    ("Acme Corporation", "OFAC_SDN", "United States", "name"),
    ("Example Inc.", "BIS_ENTITY_LIST", None, "name"),
    ("BGI", "BIS_ENTITY_LIST", "China", "alias"),  # alias for Bgi Genomics
]


def _inject_test_watchlist():
    fuzzy_match._watchlist_choices = list(TEST_CHOICES)
    fuzzy_match._watchlist_meta = list(TEST_META)


def _mock_load_watchlist():
    _inject_test_watchlist()


def test_fuzzy_match_exact():
    """Exact entity name should return a high score (e.g. 100 or close)."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        results = fuzzy_match.match_vendor("Bgi Genomics Co., Ltd.", threshold=50, top_n=5)
    assert len(results) >= 1
    top = results[0]
    assert top["matched_name"] == "Bgi Genomics Co., Ltd."
    assert top["score"] >= 90
    assert top["source_list"] == "BIS_ENTITY_LIST"
    assert top["match_type"] == "name"


def test_fuzzy_match_no_match():
    """Completely unrelated name should return no matches above threshold."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        results = fuzzy_match.match_vendor("Xyzzzzzzzzzzzzz Qqqqqqq", threshold=50, top_n=5)
    assert len(results) == 0


def test_fuzzy_match_partial():
    """Partial name like 'BGI' should return related entities above threshold."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        results = fuzzy_match.match_vendor("BGI", threshold=50, top_n=5)
    assert len(results) >= 1
    matched_names = [r["matched_name"] for r in results]
    assert "Bgi Genomics Co., Ltd." in matched_names or "BGI" in matched_names
    assert results[0]["score"] >= 50


def test_exact_match_vendor_returns_red_score():
    """Exact match (case-insensitive) against a known BCC name returns single result with score 100 (RED)."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        result = fuzzy_match.exact_match_vendor("Bgi Genomics Co., Ltd.")
    assert result is not None
    assert result["matched_name"] == "Bgi Genomics Co., Ltd."
    assert result["score"] == 100
    assert result["source_list"] == "BIS_ENTITY_LIST"


def test_exact_match_vendor_case_insensitive():
    """Exact match is case-insensitive so 'BGI' matches watchlist alias 'BGI'."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        result = fuzzy_match.exact_match_vendor("BGI")
    assert result is not None
    assert result["matched_name"] == "BGI"
    assert result["score"] == 100


def test_exact_match_vendor_no_match_returns_none():
    """Non-matching name returns None (fuzzy pass will run)."""
    fuzzy_match._watchlist_choices = []
    fuzzy_match._watchlist_meta = []
    with patch.object(fuzzy_match, "load_watchlist", side_effect=_mock_load_watchlist):
        result = fuzzy_match.exact_match_vendor("Unknown Corp")
    assert result is None
