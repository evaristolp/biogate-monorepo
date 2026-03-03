"""
Shared registry for watchlist source connectors.

Each connector registers itself with a human-readable name and a callable
that performs a full ingestion run (download/parse + Supabase upsert +
snapshot). New watchlist sources can be added by:

- implementing an ingest_<source>.py module with a main() function, then
- calling source_connectors.register_connector("Display Name", main)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass
class SourceConnector:
    """Simple connector descriptor for a watchlist source."""

    name: str
    run: Callable[[], None]


_CONNECTORS: Dict[str, SourceConnector] = {}


def register_connector(name: str, func: Callable[[], None]) -> None:
    """
    Register a watchlist source connector.

    - name: Human-readable display name (e.g. "BIS Entity List").
    - func: Zero-argument callable that performs ingestion (usually main()).
    """
    _CONNECTORS[name] = SourceConnector(name=name, run=func)


def get_connectors() -> List[SourceConnector]:
    """Return all registered connectors (order not guaranteed)."""
    return list(_CONNECTORS.values())

