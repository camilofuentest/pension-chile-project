"""
clean_rentabilidades.py — rolling 12-month windows + period returns, from valor cuota.

Input:  data/raw/valor_cuota/valor_cuota_raw.parquet  (from scrape_valor_cuota.py)
        data/raw/uf/uf_raw.parquet                    (from scrape_uf.py)

Output: data/processed/rentabilidades.parquet
        Columns: afp | fondo | window | rent_real | end_year | end_month |
                 start_year | start_month | label | ref_year | ref_month |
                 2y | 5y | 10y | 15y
        data/processed/rentabilidades_mensual.parquet
        Columns: afp | fondo | year | month | rent_real
        (monthly real return, unrounded — used by validate.py to cross-check
         against the SP's own published monthly figures)

Method — point to point, same as the SP and the presentacion_sistema_afp report:

    real return = (VC_end / VC_start) / (UF_end / UF_start) - 1

  VC = valor cuota on the last calendar day of the month (the SP publishes every
  day, weekends included, so it lines up exactly with the month-end UF).
  This avoids chaining SP's monthly returns, which are rounded to 2 decimals.

  Periods (2y, 5y, 10y, 15y) are annualized: (1 + real) ** (1 / years) - 1

  "Sistema" has no valor cuota of its own: it is built as an index whose monthly
  return is the patrimonio-weighted average of the AFPs (weights = patrimonio at
  the start of each month), then the same formula is applied.

Each row = one 12-month rolling window per AFP/fondo.
  window=0  → most recent 12 months ending at ref_month
  window=14 → oldest window (15 years back)

Run standalone:
    python -m etl.clean_rentabilidades
"""

import logging

import pandas as pd

from etl.config import (
    AFP_LIMITED_HISTORY,
    AFP_LIST,
    DATA_PROCESSED,
    FONDOS,
    RAW_UF,
    RAW_VALOR_CUOTA,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_VC       = RAW_VALOR_CUOTA / "valor_cuota_raw.parquet"
INPUT_UF       = RAW_UF / "uf_raw.parquet"
OUTPUT         = DATA_PROCESSED / "rentabilidades.parquet"
OUTPUT_MENSUAL = DATA_PROCESSED / "rentabilidades_mensual.parquet"

MAX_YEARS = 15  # number of 12-month windows to produce

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
# STEP 1 — month-end panels
# ---------------------------------------------------------------------------

def load_month_end() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Returns three tables indexed by month (seq):
      vc  — valor cuota, one column per (afp, fondo)
      pat — valor patrimonio, same shape (weights for Sistema)
      uf  — UF value on the month's last day
    """
    vc_raw = pd.read_parquet(INPUT_VC)
    uf_raw = pd.read_parquet(INPUT_UF)

    # Keep only the last calendar day of each month and only current AFPs.
    # .dt.is_month_end is True for 31-ene, 28/29-feb, 31-mar, ...
    vc_raw = vc_raw[vc_raw["fecha"].dt.is_month_end & vc_raw["afp"].isin(AFP_LIST)].copy()
    uf_raw = uf_raw[uf_raw["fecha"].dt.is_month_end].copy()

    vc_raw["seq"] = vc_raw["fecha"].dt.year * 12 + vc_raw["fecha"].dt.month - 1
    uf_raw["seq"] = uf_raw["fecha"].dt.year * 12 + uf_raw["fecha"].dt.month - 1

    # pivot_table turns rows into a grid: one row per month, one column per AFP/fondo
    vc  = vc_raw.pivot_table(index="seq", columns=["afp", "fondo"], values="valor_cuota")
    pat = vc_raw.pivot_table(index="seq", columns=["afp", "fondo"], values="valor_patrimonio")

    # Reindex to every month in the range, so a missing month shows up as NaN
    # instead of silently making shift(1) jump two months.
    months = range(int(vc.index.min()), int(vc.index.max()) + 1)
    vc, pat = vc.reindex(months), pat.reindex(months)

    uf = uf_raw.set_index("seq")["uf"]
    log.info("Valor cuota month-ends: %d months x %d AFP/fondo", len(vc), vc.shape[1])
    return vc, pat, uf


def add_sistema(vc: pd.DataFrame, pat: pd.DataFrame) -> pd.DataFrame:
    """
    Add a synthetic ("Sistema", fondo) valor cuota column per fondo.

    Monthly Sistema return = sum(return_afp * patrimonio_afp_prev) / sum(patrimonio_prev)
    Then index = cumulative product of (1 + return), starting at 1.0.
    """
    ret     = vc / vc.shift(1) - 1   # monthly nominal return per AFP/fondo
    weights = pat.shift(1)           # patrimonio at the start of the month

    for fondo in FONDOS:
        cols = [c for c in vc.columns if c[1] == fondo]
        r, w = ret[cols], weights[cols].where(ret[cols].notna())   # weight only AFPs with a return
        sis_ret = (r * w).sum(axis=1, min_count=1) / w.sum(axis=1, min_count=1)

        # The first month has no previous value → return 0 (index base = 1.0).
        # A gap after that would silently skip a month in the index, so fail loudly.
        if sis_ret.iloc[1:].isna().any():
            gaps = sis_ret.iloc[1:][sis_ret.iloc[1:].isna()].index.tolist()
            raise ValueError(f"Sistema fondo {fondo}: no AFP data for months {gaps}")
        vc[("Sistema", fondo)] = (1 + sis_ret.fillna(0)).cumprod()

    return vc


# ---------------------------------------------------------------------------
# STEP 2 — reference month
# ---------------------------------------------------------------------------

def find_ref_seq(vc: pd.DataFrame, uf: pd.Series) -> int:
    """Latest month where EVERY AFP/fondo has a month-end valor cuota AND the UF exists."""
    afp_cols = [c for c in vc.columns if c[0] != "Sistema"]
    complete = vc[afp_cols].notna().all(axis=1)
    complete = complete[complete & complete.index.isin(uf.index)]
    if complete.empty:
        raise ValueError("No month has complete valor cuota + UF data")
    ref_seq = int(complete.index.max())
    log.info("Reference month: %d/%02d (seq=%d)", *seq_to_ym(ref_seq), ref_seq)
    return ref_seq


# ---------------------------------------------------------------------------
# STEP 3 — returns
# ---------------------------------------------------------------------------

def real_return(vc: pd.DataFrame, uf: pd.Series, start: int, end: int) -> pd.Series:
    """
    Real return (as a fraction, e.g. 0.0877) between two month-ends, for every column.
    NaN where the valor cuota is missing at either end (AFP didn't exist yet).
    """
    if start not in vc.index or start not in uf.index:
        return pd.Series(float("nan"), index=vc.columns)
    return (vc.loc[end] / vc.loc[start]) / (uf.loc[end] / uf.loc[start]) - 1


def build_windows(vc: pd.DataFrame, uf: pd.Series, ref_seq: int) -> pd.DataFrame:
    ref_year, ref_month = seq_to_ym(ref_seq)
    records = []

    for w in range(MAX_YEARS):
        end_seq   = ref_seq - w * 12
        start_seq = end_seq - 12          # month-end BEFORE the window's first month
        ey, em = seq_to_ym(end_seq)
        sy, sm = seq_to_ym(end_seq - 11)  # first month inside the window (for the label)
        real   = real_return(vc, uf, start_seq, end_seq)

        for (afp, fondo), value in real.items():
            # Skip windows that end before the AFP existed (e.g. Uno before 2019),
            # so the chart only shows bars from the AFP's first year onward
            if pd.isna(vc.at[end_seq, (afp, fondo)]):
                continue
            records.append({
                "afp": afp, "fondo": fondo, "window": w,
                "rent_real": round(value * 100, 2) if pd.notna(value) else None,
                "end_year": ey, "end_month": em,
                "start_year": sy, "start_month": sm,
                "label": window_label(sy, sm, ey, em),
                "ref_year": ref_year, "ref_month": ref_month,
            })

    df = pd.DataFrame(records)
    log.info("Windows built: %d rows", len(df))
    return df


def enforce_history_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Null rent_real for windows whose start_year predates when the AFP existed."""
    for afp, founded_year in AFP_LIMITED_HISTORY.items():
        mask = (df["afp"] == afp) & (df["start_year"] < founded_year)
        df.loc[mask, "rent_real"] = None
        if mask.sum() > 0:
            log.info("Nulled %d windows for %s (started %d)", mask.sum(), afp, founded_year)
    return df


def compute_periods(df: pd.DataFrame, vc: pd.DataFrame, uf: pd.Series, ref_seq: int) -> pd.DataFrame:
    """
    Annualized real return over 2, 5, 10 and 15 years, point to point from valor cuota.
    None if any 12-month window inside the period is null (AFP too young).
    """
    period_map = {"2y": 2, "5y": 5, "10y": 10, "15y": 15}
    records = []

    for (afp, fondo), group in df.groupby(["afp", "fondo"]):
        row = {"afp": afp, "fondo": fondo}
        windows = group.set_index("window")["rent_real"]
        for label, n_years in period_map.items():
            recent = windows[windows.index < n_years]
            if len(recent) < n_years or recent.isna().any():
                row[label] = None
                continue
            total = real_return(vc, uf, ref_seq - n_years * 12, ref_seq)[(afp, fondo)]
            row[label] = round(((1 + total) ** (1 / n_years) - 1) * 100, 2)
        records.append(row)

    return df.merge(pd.DataFrame(records), on=["afp", "fondo"], how="left")


def monthly_returns(vc: pd.DataFrame, uf: pd.Series) -> pd.DataFrame:
    """Monthly real return per AFP/fondo (%), unrounded — for the cross-check in validate.py."""
    uf_m = uf.reindex(vc.index)
    real = (vc / vc.shift(1)).div(uf_m / uf_m.shift(1), axis=0) - 1
    long = real.stack(["afp", "fondo"], future_stack=True).rename("rent_real").reset_index().dropna()
    long["year"], long["month"] = zip(*long["seq"].map(seq_to_ym))
    long["rent_real"] = long["rent_real"] * 100
    return long[["afp", "fondo", "year", "month", "rent_real"]]


# ---------------------------------------------------------------------------
# STEP 4 — orchestrate
# ---------------------------------------------------------------------------

def clean() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in (INPUT_VC, INPUT_UF):
        if not path.exists():
            log.warning("Raw parquet not found: %s", path)
            log.warning("Run python -m etl.scrape_valor_cuota and python -m etl.scrape_uf first.")
            return pd.DataFrame(), pd.DataFrame()

    vc, pat, uf = load_month_end()
    vc      = add_sistema(vc, pat)
    ref_seq = find_ref_seq(vc, uf)

    df = build_windows(vc, uf, ref_seq)
    df = enforce_history_limits(df)
    df = compute_periods(df, vc, uf, ref_seq)
    df = df.sort_values(["afp", "fondo", "window"]).reset_index(drop=True)

    log.info("Final shape: %s", df.shape)
    log.info("AFPs: %s", sorted(df["afp"].unique().tolist()))
    log.info("Sample:\n%s", df.head(10).to_string())

    return df, monthly_returns(vc, uf)


def run() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df, mensual = clean()
    if df.empty:
        log.warning("Nothing to save.")
        return
    df.to_parquet(OUTPUT, index=False)
    mensual.to_parquet(OUTPUT_MENSUAL, index=False)
    log.info("Saved -> %s and %s", OUTPUT, OUTPUT_MENSUAL)


if __name__ == "__main__":
    run()
