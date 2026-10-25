"""
scrape_uf.py — download daily UF values, used to turn nominal returns into real ones.

Source: mindicador.cl JSON API (one request per year). It republishes the
Banco Central series; month-end values were checked to match the Banco Central
exactly for 2016–2026.

Output: data/raw/uf/uf_raw.parquet
        Columns: fecha | uf   (one row per calendar day)

Run standalone:
    python -m etl.scrape_uf
"""

import logging
import time
from datetime import date

import pandas as pd
import requests

from etl.config import RAW_UF, UF_API_URL, VALOR_CUOTA_YEARS_BACK

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT  = RAW_UF / "uf_raw.parquet"
SLEEP   = 0.3
RETRIES = 3


def _fetch_year(year: int) -> list[dict]:
    """Return [{"fecha": ..., "valor": ...}, ...] for one year. Raises after RETRIES."""
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(UF_API_URL.format(year=year), timeout=30)
            r.raise_for_status()
            return r.json()["serie"]
        except (requests.RequestException, KeyError, ValueError) as exc:
            log.warning("  UF %d attempt %d/%d failed: %s", year, attempt, RETRIES, exc)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Could not download UF for {year}")


def scrape() -> pd.DataFrame:
    today = date.today()
    rows  = []
    # One extra year back so the first valor cuota month always has its UF
    for year in range(today.year - VALOR_CUOTA_YEARS_BACK - 1, today.year + 1):
        serie = _fetch_year(year)
        log.info("  UF %d: %d days", year, len(serie))
        rows.extend(serie)
        time.sleep(SLEEP)

    df = pd.DataFrame(rows)
    # The API gives "2026-09-30T03:00:00.000Z" (Chile midnight written in UTC).
    # The first 10 characters are the Chilean calendar date.
    df["fecha"] = pd.to_datetime(df["fecha"].str[:10])
    df = (
        df.rename(columns={"valor": "uf"})[["fecha", "uf"]]
        .drop_duplicates(subset="fecha")
        .sort_values("fecha")
        .reset_index(drop=True)
    )
    return df


def run() -> None:
    RAW_UF.mkdir(parents=True, exist_ok=True)
    df = scrape()
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved %d rows -> %s (%s to %s)", len(df), OUTPUT,
             df["fecha"].min().date(), df["fecha"].max().date())


if __name__ == "__main__":
    run()
