"""
CSV schema for vendor audit uploads (BioGate /audits/upload).

Defines required/optional columns and validation rules. Maps to audits/vendors
data model per Technical Architecture Plan v1.1. Extensible for future columns.
Uses csv.DictReader for correct handling of quoted fields (e.g. "WuXi AppTec Co., Ltd.").
"""

import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

# Known country names and abbreviations for post-parse validation (ISO 3166–style).
# Used to flag unknown country values as ingestion_warnings without failing the row.
_COUNTRY_NAMES_AND_CODES: frozenset[str] = frozenset({
    "us", "usa", "united states", "united states of america",
    "uk", "gb", "united kingdom", "great britain",
    "cn", "china", "prc", "people's republic of china",
    "de", "germany", "deutschland",
    "fr", "france", "jp", "japan", "in", "india",
    "nl", "netherlands", "ch", "switzerland", "sg", "singapore",
    "kr", "south korea", "tw", "taiwan", "hk", "hong kong",
    "ca", "canada", "au", "australia", "ie", "ireland",
    "es", "spain", "it", "italy", "se", "sweden", "no", "norway",
    "fi", "finland", "dk", "denmark", "be", "belgium", "at", "austria",
    "pl", "poland", "pt", "portugal", "il", "israel", "ru", "russia",
    "br", "brazil", "mx", "mexico", "za", "south africa",
})

# Canonical internal column names. Input CSV headers can be messy; we map them
# dynamically to these canonical names using fuzzy-ish normalization.
REQUIRED_COLUMNS = frozenset({"vendor_name"})
OPTIONAL_COLUMNS = frozenset({"country", "parent_company", "supplier_id", "product_category", "notes"})
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


def _build_column_mapping(raw_headers: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build a mapping from canonical field names -> original CSV header, using
    a priority list of candidate header names. Returns (canonical_to_orig, normalized_map).
    """
    normalized_map = {_normalize_header(h): h for h in raw_headers}
    headers_lower = set(normalized_map.keys())

    def pick(candidates: list[str]) -> str | None:
        for cand in candidates:
            key = _normalize_header(cand)
            if key in headers_lower:
                return key
        return None

    # Vendor name column: prefer explicit "vendor_name", then common variants.
    vendor_candidates = [
        "vendor_name",
        "vendor",
        "vendor name",
        "company",
        "company_name",
        "supplier",
        "supplier_name",
        "supplier name",
        "name",
    ]
    country_candidates = [
        "country",
        "country_of_origin",
        "vendor_country",
        "country_code",
    ]
    parent_candidates = [
        "parent_company",
        "parent",
        "parent company",
        "ultimate_parent",
        "ultimate_parent_company",
    ]

    canonical_to_orig: dict[str, str] = {}

    vendor_key = pick(vendor_candidates)
    if vendor_key:
        canonical_to_orig["vendor_name"] = normalized_map[vendor_key]

    country_key = pick(country_candidates)
    if country_key:
        canonical_to_orig["country"] = normalized_map[country_key]

    parent_key = pick(parent_candidates)
    if parent_key:
        canonical_to_orig["parent_company"] = normalized_map[parent_key]

    return canonical_to_orig, normalized_map


def _is_known_country(value: str) -> bool:
    if not value or not isinstance(value, str):
        return True
    key = value.strip().lower()
    return key in _COUNTRY_NAMES_AND_CODES


def parse_validated_csv(content: str) -> list[dict[str, Any]]:
    """
    Parse CSV content into list of row dicts (keys normalized).
    Assumes content has already been validated with validate_csv().
    Silently drops rows with empty/whitespace-only vendor_name (use
    parse_validated_csv_with_warnings to get those as ingestion_warnings).
    Uses csv.DictReader so quoted fields (e.g. "WuXi AppTec Co., Ltd.") parse correctly.
    """
    rows, _ = parse_validated_csv_with_warnings(content)
    return rows


def parse_validated_csv_with_warnings(content: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Parse CSV content and return (valid_rows, ingestion_warnings).
    Uses csv.DictReader for correct handling of quoted fields.
    Each warning is a dict: row_number (1-based), raw_row_data (dict), warning_type (str).
    warning_type can be "empty_vendor_name" or "unknown_country".
    """
    reader = csv.DictReader(StringIO(content))
    raw_headers = reader.fieldnames or []
    canonical_to_orig, _ = _build_column_mapping(raw_headers)
    rows: list[dict[str, Any]] = []
    ingestion_warnings: list[dict[str, Any]] = []
    for row_index, row in enumerate(reader, start=2):
        raw_row_data = dict(row)
        out: dict[str, Any] = {}
        for canonical, col_orig in canonical_to_orig.items():
            if canonical in ALLOWED_COLUMNS:
                val = (row.get(col_orig, "") or "").strip() or None
                out[canonical] = val

        vendor_name = (out.get("vendor_name") or "").strip()
        if not vendor_name:
            ingestion_warnings.append({
                "row_number": row_index,
                "raw_row_data": raw_row_data,
                "warning_type": "empty_vendor_name",
            })
            continue
        if not any(c.isalnum() for c in vendor_name):
            ingestion_warnings.append({
                "row_number": row_index,
                "raw_row_data": raw_row_data,
                "warning_type": "empty_vendor_name",
            })
            continue

        out["vendor_name"] = vendor_name
        country_val = out.get("country")
        if country_val is not None and str(country_val).strip() and not _is_known_country(str(country_val)):
            ingestion_warnings.append({
                "row_number": row_index,
                "raw_row_data": raw_row_data,
                "warning_type": "unknown_country",
            })
        rows.append(out)
    return rows, ingestion_warnings


def validate_csv(content: str) -> ValidationResult:
    """
    Validate CSV content against the audits upload schema.
    Returns ValidationResult with errors; no persistence.
    """
    errors: list[ValidationError] = []
    reader = csv.DictReader(StringIO(content))
    raw_headers = reader.fieldnames or []
    canonical_to_orig, normalized = _build_column_mapping(raw_headers)
    headers_lower = set(normalized.keys())

    # Require that we can identify at least one vendor-name-like column.
    if "vendor_name" not in canonical_to_orig:
        errors.append(
            ValidationError(
                code="MISSING_REQUIRED_COLUMN",
                message="Could not find a vendor name column. "
                "Tried headers like: vendor_name, vendor, company, supplier, name.",
            )
        )
        return ValidationResult(valid=False, row_count=0, errors=errors)

    row_count = 0
    vendor_name_col = canonical_to_orig["vendor_name"]

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
            raw_val = row.get(vendor_name_col, "")
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
            elif not any(c.isalnum() for c in val):
                errors.append(
                    ValidationError(
                        code="INVALID_VENDOR_NAME",
                        message="vendor_name must contain at least one letter or digit",
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

        # Field-length checks for all other recognized columns; unknown columns are ignored.
        for col_lower, col_orig in normalized.items():
            if _normalize_header(col_orig) == _normalize_header(vendor_name_col):
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

    # Row-level data quality issues (e.g. empty or punctuation-only vendor_name)
    # should not prevent ingestion entirely; they are surfaced as errors but the
    # file is still considered structurally valid so that good rows can be used.
    fatal_codes = {"ROW_LIMIT_EXCEEDED"}
    is_valid = not any(e.code in fatal_codes for e in errors)

    return ValidationResult(
        valid=is_valid,
        row_count=row_count,
        errors=errors,
    )
