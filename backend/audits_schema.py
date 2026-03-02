"""
CSV schema for vendor audit uploads (BioGate /audits/upload).

Defines required/optional columns and validation rules. Maps to audits/vendors
data model per Technical Architecture Plan v1.1. Extensible for future columns.
"""

import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

REQUIRED_COLUMNS = frozenset({"vendor_name"})
OPTIONAL_COLUMNS = frozenset({"supplier_id", "product_category", "country", "notes"})
ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 10_000
MAX_FIELD_LENGTH = 500


@dataclass
class ValidationError:
    code: str
    message: str
    row: int | None = None
    column: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    row_count: int
    errors: list[ValidationError] = field(default_factory=list)

    def to_response(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "row_count": self.row_count,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "row": e.row,
                    "column": e.column,
                }
                for e in self.errors
            ],
        }


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_")


def parse_validated_csv(content: str) -> list[dict[str, Any]]:
    """
    Parse CSV content into list of row dicts (keys normalized).
    Assumes content has already been validated with validate_csv().
    Returns list of dicts with keys: vendor_name, country (optional), etc.
    """
    reader = csv.DictReader(StringIO(content))
    raw_headers = reader.fieldnames or []
    normalized = {_normalize_header(h): h for h in raw_headers}
    rows: list[dict[str, Any]] = []
    for row in reader:
        out: dict[str, Any] = {}
        for col_lower, col_orig in normalized.items():
            if col_lower in ALLOWED_COLUMNS:
                val = (row.get(col_orig, "") or "").strip() or None
                out[col_lower] = val
        if out.get("vendor_name"):
            rows.append(out)
    return rows


def validate_csv(content: str) -> ValidationResult:
    """
    Validate CSV content against the audits upload schema.
    Returns ValidationResult with errors; no persistence.
    """
    errors: list[ValidationError] = []
    reader = csv.DictReader(StringIO(content))
    raw_headers = reader.fieldnames or []
    normalized = {_normalize_header(h): h for h in raw_headers}
    headers_lower = set(normalized.keys())

    missing = REQUIRED_COLUMNS - headers_lower
    if missing:
        errors.append(
            ValidationError(
                code="MISSING_REQUIRED_COLUMN",
                message=f"Required column(s) missing: {', '.join(sorted(missing))}",
            )
        )

    unknown = headers_lower - ALLOWED_COLUMNS
    if unknown:
        errors.append(
            ValidationError(
                code="UNKNOWN_COLUMN",
                message=f"Unknown column(s): {', '.join(sorted(unknown))}",
            )
        )

    if errors:
        return ValidationResult(valid=False, row_count=0, errors=errors)

    row_count = 0
    vendor_name_col = "vendor_name" if "vendor_name" in headers_lower else None

    for i, row in enumerate(reader):
        row_count += 1
        if row_count > MAX_ROWS:
            errors.append(
                ValidationError(
                    code="ROW_LIMIT_EXCEEDED",
                    message=f"Maximum {MAX_ROWS} rows allowed",
                    row=row_count + 1,
                )
            )
            break

        if vendor_name_col:
            orig_col = normalized.get("vendor_name", "")
            raw_val = row.get(orig_col, "")
            val = (raw_val or "").strip()
            if not val:
                errors.append(
                    ValidationError(
                        code="EMPTY_REQUIRED_FIELD",
                        message="vendor_name cannot be empty",
                        row=i + 2,
                        column="vendor_name",
                    )
                )
            elif len(val) > MAX_FIELD_LENGTH:
                errors.append(
                    ValidationError(
                        code="FIELD_TOO_LONG",
                        message=f"vendor_name exceeds {MAX_FIELD_LENGTH} characters",
                        row=i + 2,
                        column="vendor_name",
                    )
                )

        for col_lower, col_orig in normalized.items():
            if col_lower == "vendor_name":
                continue
            val = (row.get(col_orig, "") or "").strip()
            if val and len(val) > MAX_FIELD_LENGTH:
                errors.append(
                    ValidationError(
                        code="FIELD_TOO_LONG",
                        message=f"{col_orig} exceeds {MAX_FIELD_LENGTH} characters",
                        row=i + 2,
                        column=col_lower,
                    )
                )

    return ValidationResult(
        valid=len(errors) == 0,
        row_count=row_count,
        errors=errors,
    )
