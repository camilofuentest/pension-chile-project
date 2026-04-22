"""
clean_financiero.py — normalize raw financiero parquet and compute profitability ratios.

Input:  data/raw/estados_financieros/financiero_raw.parquet
Output: data/processed/financiero.parquet
        Columns: afp | year | ganancia_miles | sin_encaje_miles |
                 patrimonio_miles | total_activos_miles | roe_pct | roa_pct

ROE = ganancia_miles / patrimonio_miles * 100
      → "por cada $100 de capital propio, cuánto ganó la AFP para sus dueños"

ROA = ganancia_miles / total_activos_miles * 100
      → profitability relative to total asset base (less intuitive, kept for reference)

Run standalone:
    python -m etl.clean_financiero
"""

import logging

import pandas as pd

from etl.config import AFP_LIST, DATA_PROCESSED, RAW_ESTADOS_FIN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT  = RAW_ESTADOS_FIN / "financiero_raw.parquet"
OUTPUT = DATA_PROCESSED  / "financiero.parquet"


def clean() -> pd.DataFrame:
    if not INPUT.exists():
        log.warning("Raw parquet not found: %s", INPUT)
        log.warning("Run: python -m etl.scrape_financiero")
        return pd.DataFrame()

    log.info("Reading: %s", INPUT)
    df = pd.read_parquet(INPUT)
    log.info("Raw shape: %s", df.shape)

    # Drop rows where the main metric is missing
    df = df.dropna(subset=["ganancia_miles"]).copy()

    # Keep only AFPs in the canonical list
    df = df[df["afp"].isin(AFP_LIST)].copy()

    # Enforce canonical AFP ordering for consistent JSON output
    df["afp"] = pd.Categorical(df["afp"], categories=AFP_LIST, ordered=True)
    df = df.sort_values(["afp", "year"]).reset_index(drop=True)

    # --- ROE and ROA ---
    # ROE: return on equity — how much the AFP earned per $100 of owner capital
    # Only defined when patrimonio > 0 (avoids division by zero / nonsense negatives)
    valid_pat = df["patrimonio_miles"] > 0
    df["roe_pct"] = None
    df.loc[valid_pat, "roe_pct"] = (
        df.loc[valid_pat, "ganancia_miles"] / df.loc[valid_pat, "patrimonio_miles"] * 100
    ).round(2)

    # ROA: return on assets — thinner margin, included for completeness
    valid_act = df["total_activos_miles"] > 0
    df["roa_pct"] = None
    df.loc[valid_act, "roa_pct"] = (
        df.loc[valid_act, "ganancia_miles"] / df.loc[valid_act, "total_activos_miles"] * 100
    ).round(2)

    log.info("Final shape: %s", df.shape)
    log.info("AFPs: %s", sorted(df["afp"].unique().tolist()))
    log.info("Years: %d - %d", df["year"].min(), df["year"].max())
    log.info("ROE range: %.1f%% to %.1f%%", df["roe_pct"].min(), df["roe_pct"].max())

    return df


def run() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df = clean()
    if df.empty:
        log.warning("Nothing to save.")
        return
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved -> %s", OUTPUT)


if __name__ == "__main__":
    run()
