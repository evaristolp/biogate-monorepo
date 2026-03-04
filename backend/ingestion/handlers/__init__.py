"""
Handler implementations for the BioGate ingestion engine.

Each handler is responsible for a specific media type (CSV, Excel, PDF,
images, email, Word, etc.) and produces `ExtractionResult` objects.

Handlers follow a simple, typed interface so that new formats can be
added without changing the ingestion pipeline:

    def some_handler(file_path: str) -> ExtractionResult: ...

The routing logic that chooses which handler to invoke lives in
`backend.ingestion.router.detect_handler` and
`backend.ingestion.pipeline.process_document`.
"""

from __future__ import annotations

from typing import Callable

from backend.ingestion.base import ExtractionResult


IngestionHandler = Callable[[str], ExtractionResult]

__all__ = [
    "IngestionHandler",
]

