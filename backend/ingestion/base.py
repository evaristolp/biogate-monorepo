from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ExtractionMethod(str, Enum):
    CSV_PARSER = "CSV_PARSER"
    EXCEL_PARSER = "EXCEL_PARSER"
    PDF_TEXT = "PDF_TEXT"
    PDF_VISION = "PDF_VISION"
    IMAGE_VISION = "IMAGE_VISION"
    EMAIL_PARSER = "EMAIL_PARSER"
    DOCX_PARSER = "DOCX_PARSER"


@dataclass
class ExtractedVendor:
    raw_name: str
    normalized_name: Optional[str] = None
    country_hint: Optional[str] = None
    parent_company_hint: Optional[str] = None
    equipment_type_hint: Optional[str] = None
    extraction_confidence: float = 0.0
    source_context: str = ""
    needs_review: bool = False


@dataclass
class ExtractionResult:
    vendors: List[ExtractedVendor] = field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.CSV_PARSER
    extraction_confidence: float = 0.0
    page_count: Optional[int] = None
    processing_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

