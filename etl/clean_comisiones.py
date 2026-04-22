"""
clean_comisiones.py — extract current commission % per AFP from SP historical series.

Input:  data/raw/comisiones/estructura_comisiones.xls  (downloaded by download.py)
        Sheet "Com. Porcentual desde 1988": wide format, one column per AFP,
        one row per month (1988→present). Values are decimals (0.0144 = 1.44%).
        "-" means the AFP didn't exist that period.
        PlanVital appears as three whitespace-variant columns — coalesced here.

Output: data/processed/comisiones.parquet
        Columns: afp | comision_pct
        One row per active AFP, current (latest non-null) commission %.

Run standalone:
    python -m etl.clean_comisiones
"""

import logging

import pandas as pd

from etl.config import AFP_LIST, AFP_NAME_MAP, DATA_PROCESSED, RAW_COMISIONES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT  = RAW_COMISIONES / "estructura_comisiones.xls"
OUTPUT = DATA_PROCESSED / "comisiones.parquet"

# Map from SP column names (as they appear in the XLS) to canonical AFP names.
# PlanVital has three whitespace variants — all map to the same name.
COLUMN_MAP: dict[str, str] = {
    "CAPITAL":          "Capital",
    "CUPRUM":           "Cuprum",
    "HABITAT":          "Habitat",
    "MODELO":           "Modelo",
    "PLANVITAL":        "PlanVital",   # original (no spaces)
    "PLANVITAL ":       "PlanVital",   # trailing space variant
    " PLANVITAL":       "PlanVital",   # leading space variant
    "PROVIDA":          "Provida",
    "UNO":              "Uno",
}


def clean() -> pd.DataFrame:
    if not INPUT.exists():
        log.warning("Raw file not found: %s", INPUT)
        log.warning("Run: python -m etl.download")
        return pd.DataFrame()

    log.info("Reading: %s", INPUT)
    df = pd.read_excel(INPUT, sheet_name=0, header=1, engine="xlrd")
    df = df.rename(columns={df.columns[0]: "fecha"})

    # Parse dates, drop non-date rows (title rows, footers)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()
    log.info("Date range: %s to %s (%d rows)", df["fecha"].min().date(), df["fecha"].max().date(), len(df))

    # Replace "-" strings with NaN so they don't interfere with numeric operations
    df = df.replace("-", pd.NA)

    records = []
    seen: set[str] = set()   # deduplicate after coalescing PlanVital variants

    for col, afp_name in COLUMN_MAP.items():
        if col not in df.columns:
            log.warning("Column %r not found in file — skipping %s", col, afp_name)
            continue
        if afp_name in seen:
            continue   # already processed this AFP from another whitespace variant

        # Coalesce all whitespace variants of the same AFP into one series
        variants = [c for c, name in COLUMN_MAP.items() if name == afp_name and c in df.columns]
        series = df[variants].apply(pd.to_numeric, errors="coerce").bfill(axis=1).iloc[:, 0]

        # Latest non-null value = current commission
        latest = series.dropna().iloc[-1] if series.dropna().shape[0] > 0 else None
        if latest is None:
            log.warning("No data found for %s", afp_name)
            continue

        comision_pct = round(float(latest) * 100, 4)   # decimal → percentage
        records.append({"afp": afp_name, "comision_pct": comision_pct})
        seen.add(afp_name)
        log.info("  %s: %.4f%%", afp_name, comision_pct)

    result = pd.DataFrame(records)

    # Keep only AFPs in the canonical list, in canonical order
    result = result[result["afp"].isin(AFP_LIST)].copy()
    result["afp"] = pd.Categorical(result["afp"], categories=AFP_LIST, ordered=True)
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
