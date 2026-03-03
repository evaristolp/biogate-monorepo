"""
BioGate vendor screening: fuzzy match vendor names against watchlist entities.

Loads watchlist_entities from Supabase once and reuses in memory for fast lookups.
Uses rapidfuzz token_sort_ratio for matching (handles word order differences).
Target: <500ms per vendor lookup after initial load.

Run: python scripts/fuzzy_match.py "BGI Genomics"
"""

import logging
import os
import sys
from typing import TypedDict

from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Loaded once, reused for all matches
_watchlist_choices: list[str] = []
# (entity_name, source_list, country, match_type, risk_category)
_watchlist_meta: list[tuple[str, str, str | None, str, str | None]] = []


class MatchResult(TypedDict):
    matched_name: str
    score: int
    source_list: str
    country: str | None
    match_type: str
    risk_category: str | None


def load_watchlist() -> None:
    """Fetch ALL watchlist_entities from Supabase (paginated) and build in-memory search index."""
    global _watchlist_choices, _watchlist_meta
    if _watchlist_choices:
        return

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    page_size = 1000
    offset = 0
    all_data: list[dict] = []

    while True:
        resp = (
            client.table("watchlist_entities")
            .select("entity_name, aliases, source_list, country, risk_category")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = resp.data if resp.data is not None else []
        all_data.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    logger.info("Loaded %d entities from watchlist_entities", len(all_data))

    choices: list[str] = []
    meta: list[tuple[str, str, str | None, str, str | None]] = []

    for row in all_data:
        entity_name = (row.get("entity_name") or "").strip()
        if not entity_name:
            continue
        source_list = (row.get("source_list") or "").strip()
        country = row.get("country")
        if country is not None:
            country = str(country).strip() or None
        risk_category = row.get("risk_category")
        if risk_category is not None:
            risk_category = str(risk_category).strip() or None

        # Index canonical name
        choices.append(entity_name)
        meta.append((entity_name, source_list, country, "name", risk_category))

        # Index each alias
        aliases = row.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases] if aliases.strip() else []
        for a in aliases:
            a = (a or "").strip()
            if a and a != entity_name:
                choices.append(a)
                meta.append((entity_name, source_list, country, "alias", risk_category))

    _watchlist_choices = choices
    _watchlist_meta = meta
    logger.info("Indexed %d searchable names (entities + aliases)", len(choices))


def _normalize_for_exact(s: str) -> str:
    """Normalize for exact match: strip, lowercase, collapse whitespace."""
    if not s or not isinstance(s, str):
        return ""
    return " ".join(s.split()).lower().strip()


def exact_match_vendor(
    vendor_name: str,
) -> MatchResult | None:
    """
    Exact match (case-insensitive, trimmed) against watchlist entity names and aliases.
    If the vendor name exactly matches a known BCC/watchlist name, returns a single
    MatchResult with score 100 so the pipeline can immediately flag RED. Run this
    before fuzzy matching to avoid threshold edge cases on known entities.
    """
    load_watchlist()
    if not vendor_name or not _watchlist_choices:
        return None
    needle = _normalize_for_exact(vendor_name)
    if not needle:
        return None
    for idx, choice in enumerate(_watchlist_choices):
        if _normalize_for_exact(choice) == needle:
            entity_name, source_list, country, match_type, risk_category = _watchlist_meta[idx]
            return MatchResult(
                matched_name=entity_name,
                score=100,
                source_list=source_list or "",
                country=country,
                match_type=match_type or "name",
                risk_category=risk_category,
            )
    return None


def match_vendor(
    vendor_name: str,
    threshold: int = 50,
    top_n: int = 5,
) -> list[MatchResult]:
    """
    Search vendor name against all watchlist entity names and aliases.
    Returns top N matches at or above threshold (token_sort_ratio).
    Uses case-insensitive matching so title-cased ingested names (e.g. "Bgi Genomics")
    still match queries like "BGI Genomics". Deduplicates by entity.
    """
    load_watchlist()
    if not vendor_name or not _watchlist_choices:
        return []

    # Get enough raw matches so we can dedupe by entity and take top_n (allow deep matches)
    limit = max(top_n * 20, 200)
    raw = process.extract(
        vendor_name,
        _watchlist_choices,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
        score_cutoff=threshold,
        processor=default_process,
    )

    # (choice, score, index) -> group by (entity_name, source_list), keep best score
    best_by_entity: dict[tuple[str, str], tuple[int, str | None, str, str | None]] = {}
    for _choice, score, idx in raw:
        entity_name, source_list, country, match_type, risk_category = _watchlist_meta[idx]
        key = (entity_name, source_list)
        if key not in best_by_entity or score > best_by_entity[key][0]:
            best_by_entity[key] = (score, country, match_type, risk_category)

    # Sort by score desc, take top_n
    sorted_entries = sorted(
        [
            (entity_name, source_list, score, country, match_type, risk_category)
            for (entity_name, source_list), (score, country, match_type, risk_category) in best_by_entity.items()
        ],
        key=lambda x: -x[2],
    )[:top_n]

    return [
        MatchResult(
            matched_name=entity_name,
            score=score,
            source_list=source_list,
            country=country,
            match_type=match_type,
            risk_category=risk_category,
        )
        for entity_name, source_list, score, country, match_type, risk_category in sorted_entries
    ]


def match_vendor_list(
    vendor_names: list[str],
    threshold: int = 50,
    top_n: int = 5,
) -> list[dict]:
    """
    Run match_vendor for each vendor name. Watchlist is loaded once and reused.
    Returns list of { "vendor_name": str, "matches": list[MatchResult] }.
    """
    load_watchlist()
    return [
        {"vendor_name": name, "matches": match_vendor(name, threshold=threshold, top_n=top_n)}
        for name in vendor_names
    ]


def _print_table(vendor_name: str, matches: list[MatchResult]) -> None:
    """Print matches as a formatted table."""
    if not matches:
        print(f"No matches above threshold for: {vendor_name!r}\n")
        return

    col_names = ["matched_name", "score", "source_list", "country", "match_type", "risk_category"]
    widths = [max(len(col_names[i]), 4) for i in range(len(col_names))]
    for m in matches:
        widths[0] = max(widths[0], len(str(m.get("matched_name", ""))))
        widths[1] = max(widths[1], len(str(m.get("score", ""))))
        widths[2] = max(widths[2], len(str(m.get("source_list", ""))))
        widths[3] = max(widths[3], len(str(m.get("country") or "")))
        widths[4] = max(widths[4], len(str(m.get("match_type", ""))))
        widths[5] = max(widths[5], len(str(m.get("risk_category") or "")))

    sep = "  "
    header = sep.join(n.ljust(widths[i]) for i, n in enumerate(col_names))
    ruler = "-" * len(header)
    print(f"Vendor: {vendor_name!r}\n")
    print(header)
    print(ruler)
    for m in matches:
        row = (
            str(m.get("matched_name", "")).ljust(widths[0]),
            str(m.get("score", "")).ljust(widths[1]),
            str(m.get("source_list", "")).ljust(widths[2]),
            (str(m.get("country")) if m.get("country") is not None else "").ljust(widths[3]),
            str(m.get("match_type", "")).ljust(widths[4]),
            str(m.get("risk_category") or "").ljust(widths[5]),
        )
        print(sep.join(row))
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fuzzy_match.py \"<vendor name>\"", file=sys.stderr)
        sys.exit(1)

    vendor_name = sys.argv[1]
    matches = match_vendor(vendor_name)
    _print_table(vendor_name, matches)
