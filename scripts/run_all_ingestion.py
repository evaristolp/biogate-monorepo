"""
Run all watchlist ingestion scripts in sequence (BIS, OFAC, UFLPA).

Imports and calls main() from each script. Logs start/end of each; on failure
logs the error and continues with the others. Prints a summary at the end.

Run: python scripts/run_all_ingestion.py
"""

import logging
import os
import sys

# Ensure scripts directory is on path so we can import ingest_* modules and
# the shared source_connectors registry.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import source_connectors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_all() -> None:
    results: dict[str, str] = {}  # name -> "success" | "failed"
    errors: dict[str, str] = {}  # name -> error message

    # Import modules so they can register connectors with the shared registry.
    # This keeps individual ingest_* scripts self-contained while allowing
    # run_all_ingestion to treat them via a common SourceConnector interface.
    import ingest_bis  # noqa: F401
    import ingest_ofac  # noqa: F401
    import ingest_uflpa  # noqa: F401

    connectors = source_connectors.get_connectors()
    if not connectors:
        logger.error("No watchlist connectors registered; nothing to run.")
        sys.exit(1)

    for connector in connectors:
        display_name = connector.name
        logger.info("Starting ingestion: %s", display_name)
        try:
            connector.run()
            results[display_name] = "success"
            logger.info("Completed ingestion: %s", display_name)
        except SystemExit as e:
            if e.code != 0:
                results[display_name] = "failed"
                errors[display_name] = str(e.code) if e.code is not None else "non-zero exit"
                logger.error("Ingestion failed: %s — %s", display_name, errors[display_name])
            else:
                results[display_name] = "success"
                logger.info("Completed ingestion: %s", display_name)
        except Exception as e:
            results[display_name] = "failed"
            errors[display_name] = str(e)
            logger.exception("Ingestion failed: %s", display_name)

    # Summary
    succeeded = [n for n, s in results.items() if s == "success"]
    failed = [n for n, s in results.items() if s == "failed"]
    logger.info("--- Summary ---")
    logger.info("Succeeded: %s", succeeded if succeeded else "(none)")
    if failed:
        logger.warning("Failed: %s", failed)
        for name in failed:
            logger.warning("  %s: %s", name, errors.get(name, "unknown error"))
    else:
        logger.info("All ingestions completed successfully.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
