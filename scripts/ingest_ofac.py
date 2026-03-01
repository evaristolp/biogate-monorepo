"""
OFAC SDN List Ingestion Script for BioGate (BIOSECURE Act compliance).

Downloads the trade.gov Consolidated Screening List (CSL) CSV, filters for
OFAC Specially Designated Nationals (SDN) rows (source contains
"Specially Designated Nationals"), and loads into Supabase watchlist_entities.
Uses a full-refresh strategy.

Run: python scripts/ingest_ofac.py

Requires .env with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
"""

import csv
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from io import StringIO

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# --- Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CSL_CSV_URL = "https://api.trade.gov/static/consolidated_screening_list/consolidated.csv"
SOURCE_LIST = "OFAC_SDN"
RISK_CATEGORY = "SDN"
MIN_OFAC_ENTITIES = 200  # Fail if fewer — format or filter likely wrong (SDN has thousands)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _normalize_entity_name(name: str) -> str:
    """Strip extra whitespace and standardize casing (title case)."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.split()).title()


def _parse_aliases(aliases_str: str) -> list[str]:
    """Parse aliases from semicolon- or comma-separated string into a list."""
    if not aliases_str or not isinstance(aliases_str, str):
        return []
    for sep in (";", "|", ","):
        if sep in aliases_str:
            return [a.strip() for a in aliases_str.split(sep) if a.strip()]
    return [aliases_str.strip()] if aliases_str.strip() else []


def _find_column(row: dict, *candidates: str) -> str:
    """Case-insensitive column lookup; returns first matching column name (key) or empty string."""
    keys_lower = {k.strip().lower(): k for k in row.keys()}
    for c in candidates:
        if c.lower() in keys_lower:
            return keys_lower[c.lower()]
    return ""


def download_csv() -> tuple[str, str]:
    """
    Download Consolidated Screening List CSV from trade.gov.
    Returns (content_str, hex_sha256_hash).
    """
    logger.info("Downloading Consolidated Screening List from %s", CSL_CSV_URL)
    try:
        resp = requests.get(CSL_CSV_URL, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Download failed: %s", e)
        raise SystemExit(1) from e

    content = resp.text
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logger.info("Downloaded %d bytes, SHA-256: %s", len(content), file_hash)
    return content, file_hash


def parse_csv(content: str) -> list[dict]:
    """
    Parse CSL CSV: keep only rows where source contains "Specially Designated Nationals".
    Map CSL columns (name, alt_names, country, etc.) to watchlist_entities shape. Full row in raw_data.
    """
    reader = csv.DictReader(StringIO(content))
    rows = list(reader)
    if not rows:
        logger.error("CSV is empty or has no data rows")
        raise SystemExit(1)

    sample = rows[0]
    source_col = _find_column(sample, "source", "Source")
    name_col = _find_column(sample, "name", "Name")
    if not source_col or not name_col:
        logger.error(
            "CSL missing required columns 'source' or 'name'. Available: %s",
            list(sample.keys()),
        )
        raise SystemExit(1)

    alt_names_col = _find_column(sample, "alt_names", "alt names", "aliases")
    country_col = _find_column(sample, "country", "Country")

    entities = []
    for raw in rows:
        source_val = (raw.get(source_col, "") or "").strip()
        if "Specially Designated Nationals" not in source_val:
            continue

        entity_name = (raw.get(name_col, "") or "").strip()
        if not entity_name:
            continue

        entity_name = _normalize_entity_name(entity_name)
        aliases_raw = raw.get(alt_names_col, "") if alt_names_col else ""
        aliases = _parse_aliases(str(aliases_raw))
        country = (raw.get(country_col, "") or "").strip() if country_col else ""

        list_date_added = None

        entities.append({
            "source_list": SOURCE_LIST,
            "entity_name": entity_name,
            "aliases": aliases,
            "country": country or None,
            "list_date_added": list_date_added,
            "list_version": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "risk_category": RISK_CATEGORY,
            "raw_data": {k: v for k, v in raw.items()},
        })

    if len(entities) < MIN_OFAC_ENTITIES:
        logger.critical(
            "Only %d OFAC SDN rows after filtering (minimum %d). "
            "CSL format or source filter may have changed; aborting.",
            len(entities),
            MIN_OFAC_ENTITIES,
        )
        raise SystemExit(1)

    logger.info(
        "Filtered to %d OFAC SDN entities (source contains 'Specially Designated Nationals')",
        len(entities),
    )
    return entities


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        raise SystemExit(1)

    logger.info("Starting OFAC SDN List ingestion")
    try:
        content, file_hash = download_csv()
    except SystemExit:
        raise

    try:
        entities = parse_csv(content)
    except SystemExit:
        raise

    logger.info("Parsed %d entities", len(entities))
    if not entities:
        logger.error("No entities to insert")
        raise SystemExit(1)

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Full refresh: remove existing OFAC SDN rows
    logger.info("Deleting existing rows where source_list = %s", SOURCE_LIST)
    try:
        client.table("watchlist_entities").delete().eq(
            "source_list", SOURCE_LIST
        ).execute()
    except Exception as e:
        logger.error("Delete failed: %s", e)
        raise SystemExit(1) from e

    # Insert in batches to avoid payload limits
    batch_size = 500
    inserted = 0
    for i in range(0, len(entities), batch_size):
        batch = entities[i : i + batch_size]
        try:
            client.table("watchlist_entities").insert(batch).execute()
            inserted += len(batch)
            logger.info("Inserted batch %d–%d (%d total)", i + 1, i + len(batch), inserted)
        except Exception as e:
            logger.error("Insert failed at batch starting at index %d: %s", i, e)
            raise SystemExit(1) from e

    # Record snapshot
    snapshot_row = {
        "source_list": SOURCE_LIST,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "record_count": inserted,
        "file_hash": file_hash,
    }
    try:
        client.table("watchlist_snapshots").insert(snapshot_row).execute()
        logger.info(
            "Created watchlist_snapshots row: date=%s, record_count=%d, file_hash=%s",
            snapshot_row["snapshot_date"],
            snapshot_row["record_count"],
            snapshot_row["file_hash"],
        )
    except Exception as e:
        logger.error("Snapshot insert failed: %s", e)
        raise SystemExit(1) from e

    logger.info("OFAC SDN List ingestion completed successfully. Total entities: %d", inserted)


if __name__ == "__main__":
    main()
    sys.exit(0)
