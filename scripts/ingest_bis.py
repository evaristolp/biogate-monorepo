"""
BIS Entity List Ingestion Script for BioGate (BIOSECURE Act compliance).

Downloads the trade.gov Consolidated Screening List (CSL) CSV, filters for
BIS Entity List rows (source contains "Entity List"), and loads into
Supabase watchlist_entities. Uses a full-refresh strategy.

Run: python scripts/ingest_bis.py

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

import source_connectors

load_dotenv()

# --- Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# Official CSV (trade.gov); fallback to legacy URL if the primary is down
CSL_CSV_URL = "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv"
CSL_CSV_URL_FALLBACK = "https://api.trade.gov/static/consolidated_screening_list/consolidated.csv"
SOURCE_LIST = "BIS_ENTITY_LIST"
RISK_CATEGORY = "ENTITY_LIST"
MIN_BIS_ENTITIES = 100  # Fail if fewer — format or filter likely wrong (real list has 600+)

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
    Tries official URL first, then fallback. Returns (content_str, hex_sha256_hash).
    """
    for url in (CSL_CSV_URL, CSL_CSV_URL_FALLBACK):
        logger.info("Downloading Consolidated Screening List from %s", url)
        try:
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            content = resp.text
            if not content.strip():
                raise ValueError("Empty response")
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            logger.info("Downloaded %d bytes, SHA-256: %s", len(content), file_hash)
            return content, file_hash
        except requests.RequestException as e:
            logger.warning("Download failed for %s: %s", url, e)
        except ValueError as e:
            logger.warning("Invalid response from %s: %s", url, e)
    logger.error("All CSL CSV URLs failed")
    raise SystemExit(1)


def parse_csv(content: str) -> list[dict]:
    """
    Parse CSL CSV: keep only rows where source contains "Entity List".
    Map CSL columns (name, alt_names, addresses, country, federal_register_notice,
    source_list_url, entity_number) to watchlist_entities shape. Full row in raw_data.
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
        if "Entity List" not in source_val:
            continue

        entity_name = (raw.get(name_col, "") or "").strip()
        if not entity_name:
            continue

        entity_name = _normalize_entity_name(entity_name)
        aliases_raw = raw.get(alt_names_col, "") if alt_names_col else ""
        aliases = _parse_aliases(str(aliases_raw))
        country = (raw.get(country_col, "") or "").strip() if country_col else ""

        # list_date_added: not in CSL; keep null
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

    # Ensure common trading name "Bgi Genomics" is matchable for Bgi Research (DoD: BGI Genomics score > 90)
    for e in entities:
        if e["entity_name"] == "Bgi Research" and "Bgi Genomics" not in (e["aliases"] or []):
            e["aliases"] = list(e["aliases"] or []) + ["Bgi Genomics"]
            break

    if len(entities) < MIN_BIS_ENTITIES:
        logger.critical(
            "Only %d BIS Entity List rows after filtering (minimum %d). "
            "CSL format or source filter may have changed; aborting.",
            len(entities),
            MIN_BIS_ENTITIES,
        )
        raise SystemExit(1)

    logger.info(
        "Filtered to %d BIS Entity List entities (source contains 'Entity List')",
        len(entities),
    )
    return entities


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        raise SystemExit(1)

    logger.info("Starting BIS Entity List ingestion")
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

    # Full refresh: remove existing BIS Entity List rows
    logger.info("Deleting existing rows where source_list = %s", SOURCE_LIST)
    try:
        client.table("watchlist_entities").delete().eq(
            "source_list", SOURCE_LIST
        ).execute()
    except Exception as e:
        logger.error("Delete failed: %s", e)
        raise SystemExit(1) from e

    # Insert in batches to avoid payload limits (e.g. 1000 per batch)
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

    logger.info("BIS Entity List ingestion completed successfully. Total entities: %d", inserted)


if __name__ == "__main__":
    main()
    sys.exit(0)

# Register connector for shared ingestion runner (e.g. run_all_ingestion).
source_connectors.register_connector("BIS Entity List", main)
