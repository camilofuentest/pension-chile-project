"""
run_pipeline.py — orchestrate the full ETL in sequence.

Steps:
  1. download          — fetch raw files from spensiones.cl
  2. clean_*           — normalize each dataset into parquet
  3. export_json       — write JSONs for the frontend

Run:
    python -m etl.run_pipeline
    python -m etl.run_pipeline --skip-download   (use existing raw files)
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _run_step(name: str, fn) -> None:
    log.info("=" * 50)
    log.info("STEP: %s", name)
    t0 = time.time()
    try:
        fn()
        log.info("DONE: %s (%.1fs)", name, time.time() - t0)
    except Exception as exc:
        log.error("FAILED: %s — %s", name, exc)
        raise


def main(skip_download: bool = False) -> None:
    from etl import (
        clean_rentabilidades,
        clean_comisiones,
        clean_financiero,
        clean_afiliados,
        export_json,
    )

    t_start = time.time()
    log.info("pension-chile ETL pipeline starting")

    if not skip_download:
        from etl import download
        _run_step("download", download.download_all)

    from etl import scrape_rentabilidades
    _run_step("scrape_rentabilidades", scrape_rentabilidades.run)

    _run_step("clean_rentabilidades", clean_rentabilidades.run)
    _run_step("clean_comisiones",     clean_comisiones.run)
    _run_step("clean_financiero",     clean_financiero.run)
    _run_step("clean_afiliados",      clean_afiliados.run)
    _run_step("export_json",          export_json.run)

    log.info("=" * 50)
    log.info("Pipeline complete in %.1fs", time.time() - t_start)


if __name__ == "__main__":
    skip = "--skip-download" in sys.argv
    main(skip_download=skip)
