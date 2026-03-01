"""
UFLPA Entity List Ingestion Script for BioGate (BIOSECURE Act compliance).

Reads UFLPA entity data from a local JSON file (data/uflpa_entities.json)
and loads into Supabase watchlist_entities. The UFLPA list is maintained by
DHS (https://www.dhs.gov/uflpa-entity-list) and is not in the trade.gov
Consolidated Screening List. This file-based approach allows easy updates
and can be swapped later for a scraper or API source.

Run: python scripts/ingest_uflpa.py

Requires .env with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# --- Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SOURCE_LIST = "UFLPA"
RISK_CATEGORY = "FORCED_LABOR"
MIN_UFLPA_ENTITIES = 3  # Fail if fewer — file may be incomplete or path wrong

# Path to entity list JSON (relative to repo root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
UFLPA_JSON_PATH = os.path.join(REPO_ROOT, "data", "uflpa_entities.json")

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


def _normalize_aliases(aliases: object) -> list[str]:
    """Ensure aliases is a list of non-empty strings."""
    if aliases is None:
        return []
    if isinstance(aliases, list):
        return [str(a).strip() for a in aliases if a and str(a).strip()]
    if isinstance(aliases, str):
        return [aliases.strip()] if aliases.strip() else []
    return []


def load_entities_from_json() -> tuple[list[dict], str]:
    """
    Read UFLPA entities from data/uflpa_entities.json.
    Returns (list of watchlist_entities rows, hex SHA-256 hash of file content).
    """
    logger.info("Reading UFLPA entity list from %s", UFLPA_JSON_PATH)
    if not os.path.isfile(UFLPA_JSON_PATH):
        logger.error("Entity list file not found: %s", UFLPA_JSON_PATH)
        raise SystemExit(1)

    try:
        with open(UFLPA_JSON_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.error("Failed to read %s: %s", UFLPA_JSON_PATH, e)
        raise SystemExit(1) from e

    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logger.info("Read %d bytes, SHA-256: %s", len(content), file_hash)

    try:
        raw_list = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", UFLPA_JSON_PATH, e)
        raise SystemExit(1) from e

    if not isinstance(raw_list, list):
        logger.error("JSON root must be an array of entities, got %s", type(raw_list).__name__)
        raise SystemExit(1)

    list_version = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entities = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            logger.warning("Skipping non-object item at index %d", i)
            continue
        entity_name = item.get("entity_name") or item.get("name") or ""
        if not str(entity_name).strip():
            logger.warning("Skipping item at index %d: missing entity_name", i)
            continue
        entity_name = _normalize_entity_name(str(entity_name))
        aliases = _normalize_aliases(item.get("aliases"))
        country = item.get("country")
        if country is not None:
            country = str(country).strip() or None
        list_date_added = item.get("list_date_added")
        if list_date_added is not None:
            list_date_added = str(list_date_added).strip() or None

        entities.append({
            "source_list": SOURCE_LIST,
            "entity_name": entity_name,
            "aliases": aliases,
            "country": country,
            "list_date_added": list_date_added,
            "list_version": list_version,
            "risk_category": RISK_CATEGORY,
            "raw_data": dict(item),
        })

    return entities, file_hash


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        raise SystemExit(1)

    logger.info("Starting UFLPA Entity List ingestion")
    try:
        entities, file_hash = load_entities_from_json()
    except SystemExit:
        raise

    if len(entities) < MIN_UFLPA_ENTITIES:
        logger.critical(
            "Only %d UFLPA entities in file (minimum %d). "
            "File may be incomplete or path wrong; aborting.",
            len(entities),
            MIN_UFLPA_ENTITIES,
        )
        raise SystemExit(1)

    logger.info("Loaded %d UFLPA entities", len(entities))

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Full refresh: remove existing UFLPA rows
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

    logger.info("UFLPA Entity List ingestion completed successfully. Total entities: %d", inserted)


if __name__ == "__main__":
    main()
    sys.exit(0)
