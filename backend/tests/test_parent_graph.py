"""Tests for parent company graph resolution."""

import json
import tempfile
from pathlib import Path

import pytest
import sys
from pathlib import Path as P
_ROOT = P(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.scoring.parent_graph import resolve_parent_chain
import backend.scoring.parent_graph as pg_module


@pytest.fixture(autouse=True)
def reset_graph_cache():
    """Reset graph cache so tests use intended graph."""
    pg_module._graph_data = None
    yield
    pg_module._graph_data = None


def test_complete_genomics_to_bgi_group():
    """Complete Genomics resolves to BGI Group (depth 1)."""
    chain = resolve_parent_chain("Complete Genomics", max_depth=2)
    assert len(chain) >= 2
    assert chain[0]["entity"] == "Complete Genomics"
    assert chain[0]["depth"] == 0
    assert chain[1]["entity"] == "BGI Group"
    assert chain[1]["depth"] == 1


def test_second_degree_subsidiary():
    """Second-degree subsidiary (Complete Genomics Inc) traces to BGI Group at depth 2."""
    chain = resolve_parent_chain("Complete Genomics Inc", max_depth=2)
    assert len(chain) >= 3
    assert chain[0]["entity"] == "Complete Genomics Inc"
    entities = [c["entity"] for c in chain]
    assert "BGI Genomics" in entities
    assert "BGI Group" in entities
    depths = [c["depth"] for c in chain]
    assert 2 in depths


def test_unknown_vendor_returns_empty():
    """Vendor not in graph returns empty chain."""
    chain = resolve_parent_chain("Unknown Corp Inc", max_depth=2)
    assert chain == []


def test_case_insensitive():
    """Case-insensitive matching: Wuxi Biologics matches WuXi Biologics."""
    chain = resolve_parent_chain("WUXI BIOLOGICS", max_depth=2)
    assert len(chain) >= 2
    assert chain[0]["entity"].lower() == "wuxi biologics"


def test_circular_reference_no_infinite_loop():
    """If graph has a cycle, resolution stops without infinite loop."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({
            "metadata": {},
            "edges": [
                {"parent_name": "A", "child_name": "C", "relationship_type": "subsidiary", "source_citation": ""},
                {"parent_name": "B", "child_name": "A", "relationship_type": "subsidiary", "source_citation": ""},
                {"parent_name": "C", "child_name": "B", "relationship_type": "subsidiary", "source_citation": ""},
            ]
        }, f)
        path = Path(f.name)
    try:
        chain = resolve_parent_chain("C", max_depth=5, graph_path=path)
        assert len(chain) <= 6
    finally:
        path.unlink(missing_ok=True)
