"""
scrape_rentabilidades.py
Scrapes monthly real (inflation-adjusted) returns from spensiones.cl
and saves them to data/raw/rentabilidades/rentabilidades_raw.parquet

Run standalone:
    python -m etl.scrape_rentabilidades
"""

import io
import time
import logging
from datetime import date

import requests
import pandas as pd

from etl.config import (
    RENT_URL,
    RENT_FORM_BASE,
    RENT_START_YEAR,
    RAW_RENTABILIDADES,
    AFP_NAME_MAP,
    FONDOS,
)

# ---------------------------------------------------------------------------
# Logger: prints timestamped messages so you can follow progress
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)

# Where the final file will be saved
OUTPUT = RAW_RENTABILIDADES / "rentabilidades_raw.parquet"

# The SP page returns several HTML tables per request.
# Tables 0 and 1 are navigation / header garbage we don't need.
# The actual fund data starts at index 2:
#   index 2 → Fondo A
#   index 3 → Fondo B
#   index 4 → Fondo C
#   index 5 → Fondo D
#   index 6 → Fondo E
FONDO_TABLE_OFFSET = 2


# ---------------------------------------------------------------------------
# STEP 1 — fetch_month
# Send a POST request for one specific year + month.
# Returns a Python list where each item is a pandas DataFrame
# (one DataFrame per HTML <table> found on the page).
# ---------------------------------------------------------------------------
def fetch_month(year: int, month: int) -> list[pd.DataFrame]:
    """
    POST to spensiones.cl and return all HTML tables as DataFrames.

    Parameters
    ----------
    year  : e.g. 2024
    month : 1 to 12

    Returns
    -------
    List of DataFrames — one per <table> in the HTML page.
    """
    # Build the form data dict that the SP website expects.
    # f"{month:02d}" formats the month with a leading zero: 1 → "01", 12 → "12"
    form_data = {
        **RENT_FORM_BASE,   # unpacks {"btn": "Buscar"}
        "aaaa": year,
        "mm":   f"{month:02d}",
    }

    # requests.post() sends an HTTP POST request (like clicking "Buscar" on the site).
    # data= puts the parameters in the request body (not the URL).
    response = requests.post(RENT_URL, data=form_data, timeout=30)

    # raise_for_status() throws an error if the server returned 404, 500, etc.
    response.raise_for_status()

    # pd.read_html() finds every <table> in the HTML and converts each one
    # to a DataFrame. Returns a list even if there's only one table.
    # io.StringIO() wraps the HTML text so pandas can read it like a file.
    tables = pd.read_html(io.StringIO(response.text), flavor="lxml")

    log.debug("  %d tables found for %d-%02d", len(tables), year, month)
    return tables


# ---------------------------------------------------------------------------
# STEP 2 — parse_month
# Extract only the data we need from the 5 fund tables:
#   - AFP name       (column 0)
#   - Monthly return (column 1) — "Del Período"
# ---------------------------------------------------------------------------
def parse_month(tables: list, year: int, month: int) -> pd.DataFrame:
    """
    From the raw list of tables for one month, extract AFP + monthly return
    for each of the 5 fondos. Returns a clean DataFrame.

    The raw tables have multi-level column headers that look messy.
    We ignore them and grab columns by position (0 and 1) instead.
    """
    frames = []

    for i, fondo in enumerate(FONDOS):      # i=0→A, i=1→B, ..., i=4→E
        table_idx = FONDO_TABLE_OFFSET + i  # 2, 3, 4, 5, 6

        # .copy() avoids a pandas warning about modifying a slice of another df
        df = tables[table_idx].copy()

        # --- Grab the two columns we care about by position ---
        # .iloc[:, 0] means "all rows, column at position 0" → AFP names
        # .iloc[:, 1] means "all rows, column at position 1" → monthly % return
        afp_names   = df.iloc[:, 0]
        rent_values = df.iloc[:, 1]

        # Build a clean DataFrame with only the columns we need
        result = pd.DataFrame({
            "afp":       afp_names,
            "rent_real": rent_values,
            "fondo":     fondo,   # same value for every row in this table
            "year":      year,
            "month":     month,
        })

        # --- Drop rows we don't want ---

        # Row 0 is always empty (NaN) — it's a ghost row from multi-level columns
        result = result.dropna(subset=["afp"])

        # --- Normalize AFP names ---
        # SISTEMA (system-wide average) is kept — it's used as a reference line in charts.
        # AFP_NAME_MAP normalizes it to "Sistema" along with all other AFP names.
        # .str.strip() removes leading/trailing whitespace (e.g. "CUPRUM " → "CUPRUM")
        # .replace(AFP_NAME_MAP) applies our dictionary:
        #   "BANSANDER" → "Capital", "HABITAT" → "Hábitat", "SANTA MARIA" → "Hábitat", etc.
        result["afp"] = result["afp"].str.strip().replace(AFP_NAME_MAP)

        # --- Convert return value from string to float ---
        # The SP page shows values like "7,35%" (Spanish: comma = decimal separator)
        # We need the number 7.35
        # Step 1: .astype(str)        — ensure it's text before string operations
        # Step 2: remove the "%" sign
        # Step 3: replace "," with "." so Python understands it as a decimal
        # Step 4: pd.to_numeric()     — convert text to float
        #         errors="coerce"     — if it can't convert, put NaN instead of crashing
        result["rent_real"] = (
            result["rent_real"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        result["rent_real"] = pd.to_numeric(result["rent_real"], errors="coerce")

        frames.append(result)

    # pd.concat() stacks all 5 fondo DataFrames vertically into one tall DataFrame
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# STEP 3 — scrape_all
# Loop over every year/month from RENT_START_YEAR to today.
# Collect every monthly result into one big DataFrame.
# ---------------------------------------------------------------------------
def scrape_all() -> pd.DataFrame:
    """
    Scrape all months from RENT_START_YEAR up to the current month.
    Returns a single combined DataFrame.
    """
    today        = date.today()
    all_rows     = []
    total_months = (today.year - RENT_START_YEAR) * 12 + today.month
    count        = 0

    for year in range(RENT_START_YEAR, today.year + 1):
        for month in range(1, 13):

            # Stop when we reach a future month
            if year == today.year and month > today.month:
                break

            count += 1
            log.info("[%d/%d] Fetching %d-%02d ...", count, total_months, year, month)

            try:
                tables = fetch_month(year, month)
                df     = parse_month(tables, year, month)
                all_rows.append(df)

            except Exception as e:
                # Don't crash the whole scrape if one month fails.
                # Just log the warning and continue with the next month.
                log.warning("  Skipped %d-%02d: %s", year, month, e)

            # Wait 0.5 s between requests — polite to the SP server.
            # Without this, rapid-fire requests may get your IP temporarily blocked.
            time.sleep(0.5)

    if not all_rows:
        log.error("No data collected. Check URL and form parameters in config.py.")
        return pd.DataFrame()

    # Stack all monthly DataFrames into one big table
    combined = pd.concat(all_rows, ignore_index=True)

    log.info(
        "Scrape complete — %d rows collected",
        len(combined),
    )
    return combined


# ---------------------------------------------------------------------------
# STEP 4 — run
# Entry point called by run_pipeline.py or directly from the command line.
# ---------------------------------------------------------------------------
def run() -> None:
    # Create the output folder if it doesn't exist yet
    RAW_RENTABILIDADES.mkdir(parents=True, exist_ok=True)

    log.info("Starting rentabilidades scrape: %d → %d", RENT_START_YEAR, date.today().year)

    df = scrape_all()

    if df.empty:
        log.warning("Nothing to save.")
        return

    # Parquet is a compressed binary format — much faster to read/write than CSV
    # for large datasets. index=False means don't save row numbers as a column.
    df.to_parquet(OUTPUT, index=False)

    log.info("Saved %d rows → %s", len(df), OUTPUT)
    log.info("Columns: %s", df.columns.tolist())
    log.info("AFP values found: %s", sorted(df["afp"].unique().tolist()))
    log.info("Sample:\n%s", df.head(15).to_string())


# ---------------------------------------------------------------------------
# This block only runs when you execute this file directly:
#   python -m etl.scrape_rentabilidades
# It does NOT run when another script imports this file (e.g. run_pipeline.py).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run()
