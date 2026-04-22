"""
clean_rentabilidades.py — rolling 12-month windows + period returns.

Input:  data/raw/rentabilidades/rentabilidades_raw.parquet  (from scrape_rentabilidades.py)
        Columns: afp | fondo | year | month | rent_real  (one row per AFP/fondo/month)

Output: data/processed/rentabilidades.parquet
        Columns: afp | fondo | window | rent_real | end_year | end_month |
                 start_year | start_month | label | ref_year | ref_month |
                 2y | 5y | 10y | 15y

Each row = one 12-month rolling window per AFP/fondo.
  window=0  → most recent 12 months ending at ref_month
  window=14 → oldest window (15 years back)

Run standalone:
    python -m etl.clean_rentabilidades
"""

import logging

import pandas as pd

from etl.config import AFP_LIMITED_HISTORY, DATA_PROCESSED, RAW_RENTABILIDADES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT  = RAW_RENTABILIDADES / "rentabilidades_raw.parquet"
OUTPUT = DATA_PROCESSED / "rentabilidades.parquet"

MAX_YEARS = 15  # discard data older than this many years from reference month

MESES_ES_ABREV = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ym_to_seq(year: int, month: int) -> int:
    """Monotone integer: year*12 + (month-1). Jan 2000 = 24000."""
    return year * 12 + (month - 1)


def seq_to_ym(seq: int) -> tuple[int, int]:
    return seq // 12, seq % 12 + 1


def window_label(sy: int, sm: int, ey: int, em: int) -> str:
    return f"{MESES_ES_ABREV[sm]} {sy}–{MESES_ES_ABREV[em]} {ey}"


# ---------------------------------------------------------------------------
# STEP 1 — assign windows
# ---------------------------------------------------------------------------

def build_windows(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """
    Compute 'window' for each monthly row relative to the latest month in data.
    window=0 → the 12 months ending at ref_month.
    Drops rows older than MAX_YEARS * 12 months.

    Reference = latest month that has at least one real (non-null) return.
    Months with all-NaN returns (e.g. current incomplete month) are excluded.
    """
    df = df.copy()
    df["seq"] = df["year"] * 12 + (df["month"] - 1)

    # Only consider months where at least some AFP has real data
    has_data = df.groupby("seq")["rent_real"].apply(lambda s: s.notna().any())
    ref_seq   = int(has_data[has_data].index.max())
    ref_year, ref_month = seq_to_ym(ref_seq)
    log.info("Reference month: %d/%02d (seq=%d)", ref_year, ref_month, ref_seq)

    df["months_ago"] = ref_seq - df["seq"]
    # Drop rows after the reference month (months_ago < 0) and beyond MAX_YEARS
    df = df[(df["months_ago"] >= 0) & (df["months_ago"] < MAX_YEARS * 12)].copy()
    df["window"] = df["months_ago"] // 12

    log.info("Monthly rows after cutoff: %d", len(df))
    return df, ref_year, ref_month


# ---------------------------------------------------------------------------
# STEP 2 — aggregate monthly returns into one return per window
# ---------------------------------------------------------------------------

def _window_return(monthly: pd.Series) -> float | None:
    """Geometric compounding of monthly returns. Returns None if < 12 real values."""
    clean = monthly.dropna()   # ignore NaN rows (incomplete months)
    if len(clean) < 12:
        return None
    cumulative = (1 + clean / 100).prod()
    return round((cumulative - 1) * 100, 2)


def aggregate_windows(df: pd.DataFrame, ref_year: int, ref_month: int) -> pd.DataFrame:
    ref_seq = ym_to_seq(ref_year, ref_month)

    result = (
        df.groupby(["afp", "fondo", "window"])["rent_real"]
        .apply(_window_return)
        .reset_index(name="rent_real")
    )

    # Attach date metadata for each window
    def _dates(w: int):
        end_seq   = ref_seq - w * 12
        start_seq = end_seq - 11
        ey, em = seq_to_ym(end_seq)
        sy, sm = seq_to_ym(start_seq)
        return pd.Series({
            "end_year":   ey,
            "end_month":  em,
            "start_year": sy,
            "start_month": sm,
            "label":      window_label(sy, sm, ey, em),
        })

    result[["end_year", "end_month", "start_year", "start_month", "label"]] = (
        result["window"].apply(_dates)
    )
    result["ref_year"]  = ref_year
    result["ref_month"] = ref_month

    log.info("Windows aggregated: %d rows", len(result))
    return result


# ---------------------------------------------------------------------------
# STEP 3 — null out windows before AFP founding year
# ---------------------------------------------------------------------------

def enforce_history_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Null rent_real for windows whose start_year predates when the AFP existed."""
    for afp, founded_year in AFP_LIMITED_HISTORY.items():
        mask = (df["afp"] == afp) & (df["start_year"] < founded_year)
        df.loc[mask, "rent_real"] = None
        if mask.sum() > 0:
            log.info("Nulled %d windows for %s (started %d)", mask.sum(), afp, founded_year)
    return df


# ---------------------------------------------------------------------------
# STEP 4 — compute period returns (2y, 5y, 10y, 15y)
# ---------------------------------------------------------------------------

def _period_annualized(window_series: pd.Series, n_years: int) -> float | None:
    """
    Annualized return using the n_years most recent windows (index 0..n-1).
    window_series must be indexed by window number (0 = most recent).
    Returns None if any required window is missing or null.
    """
    recent = window_series[window_series.index < n_years]
    if len(recent) < n_years or recent.isna().any():
        return None
    cumulative = (1 + recent / 100).prod()
    annualized = (cumulative ** (1 / n_years) - 1) * 100
    return round(annualized, 2)


def compute_periods(df: pd.DataFrame) -> pd.DataFrame:
    period_map = {"2y": 2, "5y": 5, "10y": 10, "15y": 15}
    records = []

    for (afp, fondo), group in df.groupby(["afp", "fondo"]):
        row = {"afp": afp, "fondo": fondo}
        # Series indexed by window number (0 = most recent)
        window_series = group.set_index("window")["rent_real"]
        for label, n_years in period_map.items():
            row[label] = _period_annualized(window_series, n_years)
        records.append(row)

    periods_df = pd.DataFrame(records)
    return df.merge(periods_df, on=["afp", "fondo"], how="left")


# ---------------------------------------------------------------------------
# STEP 5 — orchestrate
# ---------------------------------------------------------------------------

def clean() -> pd.DataFrame:
    if not INPUT.exists():
        log.warning("Raw parquet not found: %s", INPUT)
        log.warning("Run python -m etl.scrape_rentabilidades first.")
        return pd.DataFrame()

    log.info("Reading: %s", INPUT)
    df = pd.read_parquet(INPUT)
    log.info("Raw shape: %s  |  Columns: %s", df.shape, df.columns.tolist())

    df, ref_year, ref_month = build_windows(df)
    df = aggregate_windows(df, ref_year, ref_month)
    df = enforce_history_limits(df)
    df = compute_periods(df)

    df = df.sort_values(["afp", "fondo", "window"]).reset_index(drop=True)

    log.info("Final shape: %s", df.shape)
    log.info("AFPs: %s", sorted(df["afp"].unique().tolist()))
    log.info("Sample:\n%s", df.head(10).to_string())

    return df


def run() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df = clean()
    if df.empty:
        log.warning("Nothing to save.")
        return
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved → %s", OUTPUT)


if __name__ == "__main__":
    run()
