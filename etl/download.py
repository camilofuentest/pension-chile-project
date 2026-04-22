"""
download.py — fetch raw files from www.spensiones.cl into data/raw/.

Run standalone:
    python -m etl.download

Rules:
- Never overwrite an existing file (pass force=True to re-download).
- Save files exactly as received — no modification.
- Log every action so failures are easy to diagnose.
"""

import logging
import sys
from pathlib import Path

import requests

from etl.config import SOURCES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TIMEOUT = 30  # seconds


def download_file(url: str, dest: Path, force: bool = False) -> bool:
    """
    Download a single file from *url* and save it to *dest*.

    Returns True if the file was downloaded, False if it was skipped.
    Raises requests.HTTPError on bad status codes.
    """
    if not url:
        log.warning("No URL configured for %s — skipping", dest.name)
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        log.info("Already exists, skipping: %s", dest)
        return False

    log.info("Downloading: %s", url)
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    dest.write_bytes(response.content)
    log.info("Saved %d KB → %s", len(response.content) // 1024, dest)
    return True


def download_all(force: bool = False) -> None:
    """Download every source defined in config.SOURCES."""
    if not SOURCES:
        log.warning("SOURCES dict is empty — nothing to download.")
        log.warning("Fill in the URLs in etl/config.py after inspecting spensiones.cl.")
        return

    results = {"ok": 0, "skipped": 0, "failed": 0}

    for key, source in SOURCES.items():
        dest = source["raw_dir"] / source["filename"]
        try:
            downloaded = download_file(source["url"], dest, force=force)
            results["ok" if downloaded else "skipped"] += 1
        except Exception as exc:
            log.error("FAILED %s: %s", key, exc)
            results["failed"] += 1

    log.info(
        "Done — downloaded: %d | skipped: %d | failed: %d",
        results["ok"], results["skipped"], results["failed"],
    )

    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    force = "--force" in sys.argv
    download_all(force=force)
