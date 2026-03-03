"""
Parent company resolution: traverse subsidiary graph from child to root (BCC).
Used by risk scoring to flag first- and second-degree BCC subsidiaries.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "parent_company_graph.json"
_graph_data: dict[str, Any] | None = None


def _normalize_name(name: str) -> str:
    """Case-insensitive, strip; optional canonicalization (e.g. WuXi / Wuxi)."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.split()).strip()


def _load_graph(path: Path | None = None) -> dict[str, Any]:
    global _graph_data
    if _graph_data is not None:
        return _graph_data
    p = path or Path(os.environ.get("BIOGATE_PARENT_GRAPH_PATH", str(_DEFAULT_GRAPH_PATH)))
    p = p.resolve()
    if not p.exists():
        logger.warning("Parent company graph not found at %s", p)
        _graph_data = {"metadata": {}, "edges": []}
        return _graph_data
    _graph_data = json.loads(p.read_text())
    return _graph_data


def resolve_parent_chain(
    vendor_name: str,
    max_depth: int = 2,
    graph_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Resolve vendor name to chain of parents up to max_depth.
    Returns list of {entity, relationship_type, depth} from matched subsidiary up to root.
    Handles case-insensitive matching and cycles (stops at cycle).
    """
    vendor_name = _normalize_name(vendor_name)
    if not vendor_name:
        return []

    data = _load_graph(graph_path)
    edges = data.get("edges") or []

    # Build child -> parent(s). Use first parent if multiple (seed data has one parent per child).
    child_to_parent: dict[str, tuple[str, str]] = {}  # child_normalized -> (parent_name, relationship_type)
    for e in edges:
        parent = _normalize_name(e.get("parent_name") or "")
        child = _normalize_name(e.get("child_name") or "")
        if not child or not parent:
            continue
        if child not in child_to_parent:
            child_to_parent[child] = (parent, (e.get("relationship_type") or "subsidiary"))

    vendor_lower = vendor_name.lower()
    matched_child: str | None = None
    for child_norm in child_to_parent:
        if child_norm.lower() == vendor_lower:
            matched_child = child_norm
            break
    if matched_child is None:
        return []

    chain: list[dict[str, Any]] = []
    visited: set[str] = set()
    current: str = matched_child
    depth = 0
    rel = "subsidiary"

    while depth <= max_depth and current not in visited:
        visited.add(current)
        if current == matched_child:
            chain.append({"entity": current, "relationship_type": "self", "depth": 0})
        else:
            chain.append({"entity": current, "relationship_type": rel, "depth": depth})

        if current not in child_to_parent:
            break
        parent, rel = child_to_parent[current]
        parent_norm = _normalize_name(parent)
        if parent_norm in visited:
            logger.debug("Cycle detected at parent %s, stopping", parent_norm)
            break
        depth += 1
        current = parent_norm

    return chain


def get_graph_metadata(graph_path: Path | None = None) -> dict[str, Any]:
    """Return metadata block from graph (version, last_updated, disclaimer)."""
    data = _load_graph(graph_path)
    return data.get("metadata") or {}
