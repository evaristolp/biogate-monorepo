"""Unit tests for audit pipeline helpers: BIOSECURE bypass and corporate suffix stripping."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.audit_pipeline import (
    strip_corporate_suffixes,
    is_biosecure_direct_match,
    normalize_vendor_name,
)


def test_strip_corporate_suffixes_technologies():
    assert strip_corporate_suffixes("Agilent Technologies") == "Agilent"
    assert strip_corporate_suffixes("Waters Corporation") == "Waters"


def test_strip_corporate_suffixes_corp_inc():
    assert strip_corporate_suffixes("Planet Technology Corp") == "Planet"
    assert strip_corporate_suffixes("Kepler Corporation") == "Kepler"


def test_strip_corporate_suffixes_co_ltd():
    assert strip_corporate_suffixes("Foo Co Ltd") == "Foo"
    assert strip_corporate_suffixes("BGI Genomics Co Ltd") == "BGI Genomics"


def test_strip_corporate_suffixes_empty():
    assert strip_corporate_suffixes("") == ""
    assert strip_corporate_suffixes("   ") == ""


def test_is_biosecure_direct_match_wuxi():
    assert is_biosecure_direct_match("WuXi AppTec") is True
    assert is_biosecure_direct_match("Wuxi AppTec") is True
    assert is_biosecure_direct_match("WuXi Biologics") is True


def test_is_biosecure_direct_match_bgi():
    assert is_biosecure_direct_match("BGI Shenzhen") is True
    assert is_biosecure_direct_match("BGI Group") is True
    assert is_biosecure_direct_match("BGI Genomics Co Ltd") is True
    assert is_biosecure_direct_match("Hangzhou BGI Genomics") is True


def test_is_biosecure_direct_match_mgi():
    assert is_biosecure_direct_match("MGI Tech Co Ltd") is True


def test_is_biosecure_direct_match_complete_genomics():
    assert is_biosecure_direct_match("Complete Genomics") is True


def test_is_biosecure_direct_match_negative():
    assert is_biosecure_direct_match("Agilent Technologies") is False
    assert is_biosecure_direct_match("Illumina") is False
    assert is_biosecure_direct_match("Huawei Technologies") is False  # Not a BCC; flag via BIS/OFAC only
    assert is_biosecure_direct_match("") is False


def test_normalize_vendor_name():
    assert normalize_vendor_name("  BGI Genomics  ") == "Bgi Genomics"
    assert normalize_vendor_name("sigma-aldrich") == "Sigma-Aldrich"
