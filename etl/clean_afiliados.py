"""
clean_afiliados.py — extract current affiliates per AFP from SP historical series.

Input:  data/raw/afiliados/afiliados.xls  (downloaded by download.py)
        Single sheet "Afiliados": wide format, one column per AFP,
        one row per month (1981→present). Values are integer affiliate counts.
        "-" means the AFP didn't exist that period.
        PlanVital appears as three variants: "PLANVITAL", "PLANVITAL.1", "PLANVITAL "
        (pandas auto-renames the 2nd duplicate column to "PLANVITAL.1")

Output: data/processed/afiliados.parquet
        Columns: afp | afiliados | market_share_pct | fecha
        One row per active AFP + one "Sistema" row for the authoritative total.

Run standalone:
    python -m etl.clean_afiliados
"""

import logging

import pandas as pd

from etl.config import AFP_LIST, DATA_PROCESSED, RAW_AFILIADOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT  = RAW_AFILIADOS / "afiliados.xls"
OUTPUT = DATA_PROCESSED / "afiliados.parquet"

# Map from XLS column name to canonical AFP name.
# "SISTEMA" is the authoritative total published by the SP.
# PlanVital variants: pandas renames the 2nd occurrence of a duplicate column to "PLANVITAL.1"
COLUMN_MAP: dict[str, str] = {
    "SISTEMA":      "Sistema",
    "CAPITAL":      "Capital",
    "CUPRUM":       "Cuprum",
    "HABITAT":      "Habitat",
    "MODELO":       "Modelo",
    "PLANVITAL":    "PlanVital",
    "PLANVITAL.1":  "PlanVital",
    "PLANVITAL ":   "PlanVital",
    "PROVIDA":      "Provida",
    "UNO":          "Uno",
}


def clean() -> pd.DataFrame:
    if not INPUT.exists():
        log.warning("Raw file not found: %s", INPUT)
        log.warning("Run: python -m etl.download")
        return pd.DataFrame()

    log.info("Reading: %s", INPUT)
    df = pd.read_excel(INPUT, sheet_name=0, header=1, engine="xlrd")
    df = df.rename(columns={df.columns[0]: "fecha"})

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()
    log.info("Date range: %s to %s (%d rows)", df["fecha"].min().date(), df["fecha"].max().date(), len(df))

    records = []
    seen: set[str] = set()

    for col, afp_name in COLUMN_MAP.items():
        if col not in df.columns:
            continue
        if afp_name in seen:
            continue

        # Coalesce all variants of the same AFP into one series
        variants = [c for c, name in COLUMN_MAP.items() if name == afp_name and c in df.columns]
        series = (
            df[variants]
            .apply(pd.to_numeric, errors="coerce")   # "-" strings become NaN
            .bfill(axis=1)
            .iloc[:, 0]
        )

        valid = series.dropna()
        if valid.empty:
            log.warning("No data found for %s", afp_name)
            continue

        latest_value = int(valid.iloc[-1])
        latest_fecha = df.loc[valid.index[-1], "fecha"].date()

        records.append({
            "afp":    afp_name,
            "afiliados": latest_value,
            "fecha":  str(latest_fecha),
        })
        seen.add(afp_name)
        log.info("  %-12s %10d  (%s)", afp_name, latest_value, latest_fecha)

    result = pd.DataFrame(records)

    # Compute market share using the authoritative SISTEMA total
    sistema_row = result[result["afp"] == "Sistema"]
    if not sistema_row.empty:
        total = int(sistema_row["afiliados"].iloc[0])
        # Only compute share for AFP rows (not Sistema itself)
        result["market_share_pct"] = result["afiliados"].apply(
            lambda v: round(v / total * 100, 2) if total > 0 else None
        )
        result.loc[result["afp"] == "Sistema", "market_share_pct"] = None
        log.info("Total sistema: %d", total)
    else:
        result["market_share_pct"] = None

    # Put Sistema first, then AFPs in canonical order
    order = ["Sistema"] + AFP_LIST
    result["afp"] = pd.Categorical(result["afp"], categories=order, ordered=True)
    result = result.sort_values("afp").reset_index(drop=True)

    log.info("Final shape: %s", result.shape)
    return result


def run() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df = clean()
    if df.empty:
        log.warning("Nothing to save.")
        return
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved -> %s", OUTPUT)
    log.info("Sample:\n%s", df.to_string())


if __name__ == "__main__":
    run()
