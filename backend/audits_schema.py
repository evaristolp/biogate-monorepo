"""
CSV schema for vendor audit uploads (BioGate /audits/upload).

Defines required/optional columns and validation rules. Maps to audits/vendors
data model per Technical Architecture Plan v1.1. Extensible for future columns.
Uses csv module with proper quoting; preprocesses rows with extra columns (comma in
vendor name) so "WuXi AppTec Co., Ltd." parses as a single vendor_name.
"""

import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

# Known country names and abbreviations for post-parse validation (ISO 3166–style).
# Used to flag unknown country values as ingestion_warnings; fuzzy match fixes typos (e.g. Switerland).
_COUNTRY_NAMES_AND_CODES: dict[str, str] = {
    "us": "United States", "usa": "United States", "united states": "United States",
    "united states of america": "United States", "u.s.": "United States", "u.s.a.": "United States",
    "uk": "United Kingdom", "gb": "United Kingdom", "united kingdom": "United Kingdom",
    "great britain": "United Kingdom",
    "cn": "China", "china": "China", "prc": "China", "people's republic of china": "China",
    "de": "Germany", "germany": "Germany", "deutschland": "Germany",
    "fr": "France", "france": "France",
    "jp": "Japan", "japan": "Japan",
    "in": "India", "india": "India",
    "nl": "Netherlands", "netherlands": "Netherlands",
    "ch": "Switzerland", "switzerland": "Switzerland",
    "sg": "Singapore", "singapore": "Singapore",
    "kr": "South Korea", "south korea": "South Korea",
    "tw": "Taiwan", "taiwan": "Taiwan",
    "hk": "Hong Kong", "hong kong": "Hong Kong",
    "ca": "Canada", "canada": "Canada",
    "au": "Australia", "australia": "Australia",
    "ie": "Ireland", "ireland": "Ireland",
    "es": "Spain", "spain": "Spain",
    "it": "Italy", "italy": "Italy",
    "se": "Sweden", "sweden": "Sweden",
    "no": "Norway", "norway": "Norway",
    "fi": "Finland", "finland": "Finland",
    "dk": "Denmark", "denmark": "Denmark",
    "be": "Belgium", "belgium": "Belgium",
    "at": "Austria", "austria": "Austria",
    "pl": "Poland", "poland": "Poland",
    "pt": "Portugal", "portugal": "Portugal",
    "il": "Israel", "israel": "Israel",
    "ru": "Russia", "russia": "Russia",
    "br": "Brazil", "brazil": "Brazil",
    "mx": "Mexico", "mexico": "Mexico",
    "za": "South Africa", "south africa": "South Africa",
    "lu": "Luxembourg", "luxembourg": "Luxembourg",
}

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


def _normalize_country(raw: str) -> tuple[str | None, str]:
    """
    Returns (normalized_country_name, source) where source is 'exact' | 'fuzzy' | 'unknown'.
    Unknown values are returned as (None, 'unknown') so callers can warn or reject.
    """
    if not raw or not isinstance(raw, str):
        return None, "unknown"
    low = raw.strip().lower()
    if not low:
        return None, "unknown"
    if low in _COUNTRY_NAMES_AND_CODES:
        return _COUNTRY_NAMES_AND_CODES[low], "exact"
    try:
        from rapidfuzz import fuzz, process
        best_match, score, _ = process.extractOne(low, _COUNTRY_NAMES_AND_CODES.keys(), scorer=fuzz.ratio)
        if score >= 80:
            return _COUNTRY_NAMES_AND_CODES[best_match], "fuzzy"
    except Exception:
        pass
    return None, "unknown"


def _is_known_country(value: str) -> bool:
    if not value or not isinstance(value, str):
        return True
    normalized, source = _normalize_country(value)
    return source != "unknown"


def _preprocess_csv_row(row: list[str], expected_columns: int) -> list[str]:
    """
    If a row has more columns than expected (e.g. comma inside vendor name),
    rejoin the first N fields so the row has expected_columns cells.
    Rejoin with comma to restore the original punctuation (e.g. "Co., Ltd.").
    """
    if len(row) <= expected_columns:
        return row
    excess = len(row) - expected_columns
    vendor_name = ",".join(row[: excess + 1]).strip()
    return [vendor_name] + row[excess + 1 :]


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
    Uses csv.reader so fields with commas can be quoted; rows with too many columns
    (unquoted comma in vendor name) are repaired by rejoining leading cells.
    Each warning is a dict: row_number (1-based), raw_row_data (dict), warning_type (str).
    warning_type can be "empty_vendor_name" or "unknown_country".
    Country values are fuzzy-matched (e.g. Switerland -> Switzerland); only truly unknown trigger a warning.
    """
    buf = StringIO(content)
    reader = csv.reader(buf)
    raw_headers = next(reader, None) or []
    canonical_to_orig, normalized_map = _build_column_mapping(raw_headers)
    expected_columns = len(raw_headers)
    rows: list[dict[str, Any]] = []
    ingestion_warnings: list[dict[str, Any]] = []
    for row_index, row in enumerate(reader, start=2):
        if len(row) > expected_columns:
            row = _preprocess_csv_row(row, expected_columns)
        values = (list(row) + [""] * expected_columns)[:expected_columns]
        raw_row_data = dict(zip(raw_headers, values))
        out: dict[str, Any] = {}
        for canonical, col_orig in canonical_to_orig.items():
            if canonical in ALLOWED_COLUMNS:
                val = (raw_row_data.get(col_orig, "") or "").strip() or None
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
        if country_val is not None and str(country_val).strip():
            normalized_country, country_source = _normalize_country(str(country_val))
            if country_source != "unknown":
                out["country"] = normalized_country
            else:
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
    Uses same reader + row preprocess as parse so quoted and comma-in-name rows are handled.
    """
    errors: list[ValidationError] = []
    buf = StringIO(content)
    reader = csv.reader(buf)
    raw_headers = next(reader, None) or []
    canonical_to_orig, normalized = _build_column_mapping(raw_headers)
    expected_columns = len(raw_headers)

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
        if len(row) > expected_columns:
            row = _preprocess_csv_row(row, expected_columns)
        values = (list(row) + [""] * expected_columns)[:expected_columns]
        row_dict = dict(zip(raw_headers, values))

        if vendor_name_col:
            raw_val = row_dict.get(vendor_name_col, "")
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
            val = (row_dict.get(col_orig, "") or "").strip()
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
