"""Unit tests for risk scoring engine."""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.config.scoring_config import load_scoring_config, clear_scoring_config_cache
from backend.scoring.risk_engine import score_vendor, RiskTier, _match_is_plausible


@pytest.fixture(autouse=True)
def ensure_config_loaded():
    clear_scoring_config_cache()
    load_scoring_config()
    yield


# --- Red tier: direct match >= 91 or first-degree subsidiary ---

def test_red_bgi_genomics():
    """BGI Genomics: direct match to BCC (score >= 91)."""
    result = score_vendor(
        [{"matched_name": "BGI Genomics", "score": 98, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
        country=None,
    )
    assert result.tier == "red"


def test_red_huawei_technologies():
    """Huawei Technologies: direct match (score >= 91)."""
    result = score_vendor(
        [{"matched_name": "Huawei Technologies", "score": 100, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
        country=None,
    )
    assert result.tier == "red"


def test_red_mgi_tech():
    """MGI Tech: direct match (score >= 91)."""
    result = score_vendor(
        [{"matched_name": "MGI Tech", "score": 96, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
        country=None,
    )
    assert result.tier == "red"


def test_red_first_degree_subsidiary():
    """Complete Genomics: first-degree subsidiary of BGI (parent_chain depth 1)."""
    chain = [{"entity": "Complete Genomics", "relationship_type": "self", "depth": 0}, {"entity": "BGI Group", "relationship_type": "acquired_by", "depth": 1}]
    result = score_vendor([], country=None, parent_chain=chain)
    assert result.tier == "red"


def test_red_parent_company_biosecure_named():
    """Parent company is explicitly named BCC -> RED."""
    result = score_vendor(
        [], country=None, parent_company_is_biosecure_named=True
    )
    assert result.tier == "red"
    assert "Parent company is explicitly named BIOSECURE Act entity" in result.reasoning


# --- Amber tier: strong alias 70-90 or second-degree subsidiary ---

def test_amber_complete_genomics_alias():
    """Complete Genomics: strong alias match in 70-90 range (human review)."""
    result = score_vendor(
        [{"matched_name": "Complete Genomics", "score": 85, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "alias"}],
        country=None,
    )
    assert result.tier == "amber"


def test_amber_second_degree_subsidiary():
    """Second-degree subsidiary (e.g. Complete Genomics Inc -> BGI Genomics -> BGI Group)."""
    chain = [
        {"entity": "Complete Genomics Inc", "relationship_type": "self", "depth": 0},
        {"entity": "BGI Genomics", "relationship_type": "subsidiary", "depth": 1},
        {"entity": "BGI Group", "relationship_type": "subsidiary", "depth": 2},
    ]
    result = score_vendor([], country=None, parent_chain=chain)
    assert result.tier == "amber"


def test_amber_huawei_subsidiary():
    """Huawei subsidiary: strong match 70-90 -> amber."""
    result = score_vendor(
        [{"matched_name": "HiSilicon", "score": 85, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
        country=None,
    )
    assert result.tier == "amber"


# --- Yellow tier: partial match 50-69 or country-of-concern ---

def test_yellow_chinese_partial_match():
    """Chinese company with partial name match (50-69) + country flag."""
    result = score_vendor(
        [{"matched_name": "Some Chinese Entity", "score": 65, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
        country="CN",
    )
    assert result.tier == "yellow"
    assert "CN" in result.country_flags


def test_yellow_partial_match_no_country():
    """Score below country-adjusted threshold (80 when country unknown) does not count -> green."""
    result = score_vendor(
        [{"matched_name": "Some Entity", "score": 65, "source_list": "BIS_ENTITY_LIST", "country": None, "match_type": "name"}],
        country=None,
    )
    # 65 < 80 (default threshold when country unknown) so fuzzy match is ignored
    assert result.tier == "green"


def test_yellow_third_degree_chain():
    """Third-degree subsidiary chain -> Amber (fail safe)."""
    chain = [
        {"entity": "Leaf Corp", "relationship_type": "self", "depth": 0},
        {"entity": "Mid", "relationship_type": "subsidiary", "depth": 1},
        {"entity": "Root", "relationship_type": "subsidiary", "depth": 2},
        {"entity": "BCC Root", "relationship_type": "subsidiary", "depth": 3},
    ]
    result = score_vendor([], country=None, parent_chain=chain)
    assert result.tier == "amber"


# --- Green tier: no match or < 50, no country flag ---

def test_green_thermo_fisher():
    result = score_vendor([], country="US")
    assert result.tier == "green"


def test_green_illumina():
    result = score_vendor(
        [{"matched_name": "Other Co", "score": 45, "source_list": "BIS_ENTITY_LIST", "country": None, "match_type": "name"}],
        country="US",
    )
    assert result.tier == "green"


def test_green_agilent():
    result = score_vendor([], country=None)
    assert result.tier == "green"


def test_green_agilent_ignores_implausible_fuzzy_match():
    """Agilent with a weak match to an unrelated watchlist entity (no token overlap) stays green."""
    result = score_vendor(
        [{"matched_name": "Aviation Network Associates", "score": 55, "source_list": "BIS_ENTITY_LIST", "country": None, "match_type": "name"}],
        country="US",
        vendor_name="Agilent Technologies",
    )
    assert result.tier == "green"


def test_red_dahua_technology_hard_red_source():
    """Dahua Technology from BIS Entity List should be hard RED via high-severity source."""
    result = score_vendor(
        [
            {
                "matched_name": "Dahua Technology",
                "score": 92,
                "source_list": "BIS_ENTITY_LIST",
                "country": "CN",
                "match_type": "name",
                "risk_category": "ENTITY_LIST",
            }
        ],
        country="CN",
        vendor_name="Dahua Technology",
    )
    assert result.tier == "red"


def test_red_hangzhou_hikvision_hard_red_source():
    """Hangzhou Hikvision from BIS Entity List should be hard RED via high-severity source."""
    result = score_vendor(
        [
            {
                "matched_name": "Hangzhou Hikvision Digital Technology Co., Ltd.",
                "score": 93,
                "source_list": "BIS_ENTITY_LIST",
                "country": "CN",
                "match_type": "name",
                "risk_category": "ENTITY_LIST",
            }
        ],
        country="CN",
        vendor_name="Hangzhou Hikvision",
    )
    assert result.tier == "red"


def test_plausible_ignores_generic_tokens():
    """Shared token only on generic words like 'Group' or 'International' is not considered plausible."""
    # vendor and entity share only 'Group' which is in generic_tokens; should be implausible
    assert _match_is_plausible("Acme Group", "Random Group") is False


def test_match_plausible_shared_token():
    assert _match_is_plausible("Thermo Fisher Scientific", "Fisher Inc") is True
    assert _match_is_plausible("Illumina Inc", "Illumina Inc") is True


def test_match_implausible_no_shared_token():
    assert _match_is_plausible("Agilent Technologies", "Aviation Network Associates") is False


def test_green_bio_rad():
    result = score_vendor([], country="US")
    assert result.tier == "green"


def test_green_milliporesigma():
    result = score_vendor([], country="DE")
    assert result.tier == "green"


def test_green_corning():
    result = score_vendor(
        [{"matched_name": "Unrelated", "score": 40, "source_list": "BIS_ENTITY_LIST", "country": None, "match_type": "name"}],
        country="US",
    )
    assert result.tier == "green"


def test_reasoning_populated():
    """RiskTier includes non-empty reasoning."""
    result = score_vendor(
        [{"matched_name": "BGI Genomics", "score": 97, "source_list": "BIS_ENTITY_LIST", "country": "CN", "match_type": "name"}],
    )
    assert result.tier == "red"
    assert len(result.reasoning) > 0
    assert result.match_evidence


def test_country_of_concern_raises_yellow():
    """Vendor in country of concern with no match -> Yellow."""
    result = score_vendor([], country="CN")
    assert result.tier == "yellow"
    assert "CN" in result.country_flags
