"""
scrape_financiero.py — scrape AFP financial results from spensiones.cl.

Fetches Q4 (December) of each year per AFP — full-year cumulative figures.

Tables scraped:
  C10_RNRE  → P&L: net investment return (ganancia/pérdida)
  C02_BGPP  → Balance: total patrimonio neto + total activos

Codes extracted:
  C10_RNRE  82.10.010 → ganancia_miles      (net income incl. encaje)
  C10_RNRE  82.10.000 → sin_encaje_miles    (net income excl. encaje)
  C02_BGPP  25.11.000 → patrimonio_miles    (total equity)
  C02_BGPP  20.11.000 → total_activos_miles (total assets = pasivos + patrimonio)

Values in the HTML are "miles de pesos" with dots as thousands separators: "126.980.727"
Negatives appear as "(5.000)" — Chilean accounting notation.

Output: data/raw/estados_financieros/financiero_raw.parquet
        Columns: afp | year | ganancia_miles | sin_encaje_miles |
                 patrimonio_miles | total_activos_miles

Run standalone:
    python -m etl.scrape_financiero
"""

import io
import logging
import time
from datetime import date

import pandas as pd
import requests

from etl.config import (
    AFP_IDU_MAP,
    FINANCIERO_START_YEAR,
    FINANCIERO_URL,
    RAW_ESTADOS_FIN,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT = RAW_ESTADOS_FIN / "financiero_raw.parquet"
SLEEP  = 0.3   # seconds between requests

# Table IDs and the codes we extract from each
CUADRO_PL      = "C10_RNRE"
CUADRO_BALANCE = "C02_BGPP"

PL_CODES = {
    "ganancia_miles":   "82.10.010",   # GANANCIA (PÉRDIDA) total incl. encaje
    "sin_encaje_miles": "82.10.000",   # net income excl. encaje — pure ops
}
BALANCE_CODES = {
    "patrimonio_miles":    "25.11.000",   # TOTAL PATRIMONIO NETO
    "total_activos_miles": "20.11.000",   # TOTAL PASIVOS Y PATRIMONIO (= total assets)
}


def _parse_miles(value) -> int | None:
    """
    Convert SP's thousands-separated string to integer.
    "126.980.727" → 126980727
    "(5.000)"     → -5000   (Chilean accounting: negatives in parentheses)
    """
    s = str(value).strip()
    if s in ("", "nan", "-", "NaN"):
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace(".", "").replace(",", "")
    try:
        result = int(s)
        return -result if negative else result
    except ValueError:
        return None


def _fetch_table(cuadro: str, idu: int, year: int) -> pd.DataFrame | None:
    """
    Fetch one cuadro for one AFP × Q4 period.
    Returns the data table (tables[1]) or None if period not available.
    """
    params = {
        "menu":     "sci",
        "menuN1":   "estfinafp",
        "menuN2":   "NOID",
        "cuadroid": cuadro,
        "idu":      idu,
        "periodo":  f"{year}12",
        "tipo":     "html",
    }
    try:
        r = requests.get(FINANCIERO_URL, params=params, timeout=20)
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        return tables[1] if len(tables) >= 2 else None
    except Exception as exc:
        log.warning("  %s %d12/%d: %s", cuadro, year, idu, exc)
        return None


def _extract_codes(table: pd.DataFrame, codes: dict[str, str]) -> dict:
    """
    Extract multiple account codes from a table.
    codes = {field_name: account_code}
    Returns {field_name: value_or_None}
    """
    result = {}
    for field, code in codes.items():
        mask    = table.iloc[:, 0].astype(str).str.strip() == code
        matches = table[mask]
        result[field] = _parse_miles(matches.iloc[0, 3]) if not matches.empty else None
    return result


def scrape() -> pd.DataFrame:
    current_year = date.today().year
    years        = list(range(FINANCIERO_START_YEAR, current_year + 1))
    records      = []

    for afp, idu in AFP_IDU_MAP.items():
        log.info("Scraping %s (idu=%d)", afp, idu)

        for year in years:
            row = {"afp": afp, "year": year}

            # --- P&L table ---
            pl_table = _fetch_table(CUADRO_PL, idu, year)
            if pl_table is None:
                log.info("  %d P&L: no data", year)
                continue
            row.update(_extract_codes(pl_table, PL_CODES))
            time.sleep(SLEEP)

            # --- Balance sheet table ---
            bal_table = _fetch_table(CUADRO_BALANCE, idu, year)
            if bal_table is not None:
                row.update(_extract_codes(bal_table, BALANCE_CODES))
            time.sleep(SLEEP)

            log.info(
                "  %d: ganancia=%-12s  patrimonio=%-12s  activos=%s",
                year,
                row.get("ganancia_miles"),
                row.get("patrimonio_miles"),
                row.get("total_activos_miles"),
            )
            records.append(row)

    return pd.DataFrame(records)


def run() -> None:
    RAW_ESTADOS_FIN.mkdir(parents=True, exist_ok=True)
    df = scrape()
    if df.empty:
        log.warning("Nothing to save.")
        return
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved %d rows -> %s", len(df), OUTPUT)
    log.info("Columns: %s", df.columns.tolist())
    log.info("Sample:\n%s", df.head(8).to_string())


if __name__ == "__main__":
    run()
