"""
validate.py — regression guard: block the export if fresh data looks worse than what's published.

Compares the freshly processed parquets (data/processed/) against the currently
committed JSONs (data/output/ — the "baseline"). If anything regressed, raises
ValueError listing every problem, so export_json never runs and the GitHub
Action fails without committing anything.

Checks:
  rentabilidades  ref month not older than baseline · no AFP/fondo missing ·
                  latest window not null where baseline had a value
  afiliados       latest fecha not older than baseline · no AFP missing ·
                  Sistema total within ±10% of baseline
  comisiones      no AFP missing · every comision_pct between 0 and 5
  financiero      no AFP missing · latest year not lower than baseline
  rent vs SP      monthly real returns computed from valor cuota + UF match the
                  SP's own published monthly figures (last 24 months, ±0.03 pp)

A missing processed parquet is an error. A missing baseline JSON (first run)
only skips the comparison, with a warning.

Run standalone:
    python -m etl.validate
"""

import json
import logging

import pandas as pd

from etl.config import DATA_OUTPUT, DATA_PROCESSED, RAW_RENTABILIDADES
from etl.export_json import MESES_ES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Reverse of MESES_ES: "agosto" → 8. A dict comprehension swaps keys and values.
MES_TO_NUM = {nombre: num for num, nombre in MESES_ES.items()}

SISTEMA_MAX_CHANGE = 0.10   # afiliados Sistema total may move at most ±10% per run
COMISION_MAX_PCT   = 5.0    # sanity ceiling — real commissions are ~0.5–1.5%
SP_CHECK_MONTHS    = 24     # months compared against the SP's published returns
SP_MAX_DIFF_PP     = 0.03   # SP rounds to 2 decimals → normal diff is <= 0.005 pp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_parquet(name: str, problems: list[str]) -> pd.DataFrame | None:
    path = DATA_PROCESSED / f"{name}.parquet"
    if not path.exists():
        problems.append(f"{name}: processed parquet missing ({path})")
        return None
    return pd.read_parquet(path)


def _load_baseline(name: str):
    path = DATA_OUTPUT / f"{name}.json"
    if not path.exists():
        log.warning("%s: no baseline JSON (%s) - skipping comparison", name, path)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_month_label(label: str) -> tuple[int, int]:
    """'agosto de 2026' → (2026, 8)"""
    mes, _, year = label.split()
    return int(year), MES_TO_NUM[mes]


# ---------------------------------------------------------------------------
# Per-dataset checks — each appends human-readable strings to `problems`
# ---------------------------------------------------------------------------

def check_rentabilidades(problems: list[str]) -> None:
    df = _load_parquet("rentabilidades", problems)
    if df is None:
        return
    ref = (int(df["ref_year"].iloc[0]), int(df["ref_month"].iloc[0]))

    baseline = _load_baseline("rentabilidades")
    if baseline is None:
        log.info("rentabilidades OK: ref %d/%02d (no baseline)", *ref)
        return

    first = next(iter(baseline.values()))
    base_ref = _parse_month_label(first["last_month_label"])
    n_before = len(problems)

    # Tuples compare element by element: (2026, 7) < (2026, 8) is True
    if ref < base_ref:
        problems.append(
            f"rentabilidades: ref month {ref[0]}/{ref[1]:02d} is older than "
            f"baseline {base_ref[0]}/{base_ref[1]:02d}"
        )

    # Same key format as export_json: "Capital__A"
    fresh_keys = set(df["afp"].astype(str) + "__" + df["fondo"].astype(str))
    missing = sorted(set(baseline) - fresh_keys)
    if missing:
        problems.append(f"rentabilidades: missing AFP/fondo {missing}")

    # window=0 is the most recent 12 months. The baseline's last value is its latest window.
    latest = df[df["window"] == 0]
    latest_by_key = dict(zip(latest["afp"].astype(str) + "__" + latest["fondo"].astype(str),
                             latest["rent_real"]))
    newly_null = sorted(
        key for key, entry in baseline.items()
        if not key.startswith("Sistema__")
        and entry["values"] and entry["values"][-1] is not None
        and key in latest_by_key and pd.isna(latest_by_key[key])
    )
    if newly_null:
        problems.append(f"rentabilidades: latest window became null for {newly_null}")

    if len(problems) == n_before:
        log.info("rentabilidades OK: ref %d/%02d (baseline %d/%02d)", *ref, *base_ref)


def check_afiliados(problems: list[str]) -> None:
    df = _load_parquet("afiliados", problems)
    if df is None:
        return
    df["afp"] = df["afp"].astype(str)
    fecha = df["fecha"].max()   # ISO strings ("2026-07-01") sort correctly as text

    baseline = _load_baseline("afiliados")
    if baseline is None:
        log.info("afiliados OK: fecha %s (no baseline)", fecha)
        return

    base = pd.DataFrame(baseline)
    base_fecha = base["fecha"].max()
    n_before = len(problems)

    if fecha < base_fecha:
        problems.append(f"afiliados: fecha {fecha} is older than baseline {base_fecha}")

    missing = sorted(set(base["afp"]) - set(df["afp"]))
    if missing:
        problems.append(f"afiliados: missing AFP {missing}")

    fresh_sis = df.loc[df["afp"] == "Sistema", "afiliados"]
    base_sis  = base.loc[base["afp"] == "Sistema", "afiliados"]
    if not fresh_sis.empty and not base_sis.empty:
        change = fresh_sis.iloc[0] / base_sis.iloc[0] - 1
        if abs(change) > SISTEMA_MAX_CHANGE:
            problems.append(
                f"afiliados: Sistema total changed {change:+.1%} "
                f"({base_sis.iloc[0]:,} -> {fresh_sis.iloc[0]:,})"
            )

    if len(problems) == n_before:
        log.info("afiliados OK: fecha %s (baseline %s)", fecha, base_fecha)


def check_comisiones(problems: list[str]) -> None:
    df = _load_parquet("comisiones", problems)
    if df is None:
        return
    df["afp"] = df["afp"].astype(str)
    n_before = len(problems)

    # ~ negates a boolean mask: "rows where the value is NOT between 0 and 5"
    out_of_range = df[~df["comision_pct"].between(0, COMISION_MAX_PCT, inclusive="neither")]
    if not out_of_range.empty:
        problems.append(
            "comisiones: comision_pct out of range (0, 5): "
            + ", ".join(f"{r.afp}={r.comision_pct}" for r in out_of_range.itertuples())
        )

    baseline = _load_baseline("comisiones")
    if baseline is not None:
        missing = sorted({r["afp"] for r in baseline} - set(df["afp"]))
        if missing:
            problems.append(f"comisiones: missing AFP {missing}")

    if len(problems) == n_before:
        log.info("comisiones OK: %d AFPs", len(df))


def check_financiero(problems: list[str]) -> None:
    df = _load_parquet("financiero", problems)
    if df is None:
        return
    df["afp"] = df["afp"].astype(str)
    max_year = int(df["year"].max())

    baseline = _load_baseline("financiero")
    if baseline is None:
        log.info("financiero OK: up to %d (no baseline)", max_year)
        return

    base_max = max(max(entry["year"]) for entry in baseline.values())
    n_before = len(problems)

    missing = sorted(set(baseline) - set(df["afp"]))
    if missing:
        problems.append(f"financiero: missing AFP {missing}")

    if max_year < base_max:
        problems.append(f"financiero: latest year {max_year} is lower than baseline {base_max}")

    if len(problems) == n_before:
        log.info("financiero OK: up to %d (baseline %d)", max_year, base_max)


def check_rent_vs_sp(problems: list[str]) -> None:
    """
    Our returns come from valor cuota + UF. The SP also publishes monthly real
    returns (rounded to 2 decimals). If both disagree by more than rounding,
    something is wrong in the scrape or the formula (wrong UF date, wrong fondo...).
    """
    mensual = _load_parquet("rentabilidades_mensual", problems)
    sp_path = RAW_RENTABILIDADES / "rentabilidades_raw.parquet"
    if mensual is None:
        return
    if not sp_path.exists():
        log.warning("rent vs SP: %s not found - cross-check skipped", sp_path)
        return

    sp = pd.read_parquet(sp_path)
    # merge = SQL join on the shared keys; suffixes rename the two rent_real columns
    joined = mensual.merge(sp, on=["afp", "fondo", "year", "month"], suffixes=("_vc", "_sp"))
    joined = joined.dropna(subset=["rent_real_vc", "rent_real_sp"])
    if joined.empty:
        problems.append("rent vs SP: no overlapping months between valor cuota and SP data")
        return

    seq    = joined["year"] * 12 + joined["month"]
    recent = joined[seq > seq.max() - SP_CHECK_MONTHS].copy()
    recent["diff"] = (recent["rent_real_vc"] - recent["rent_real_sp"]).abs()
    off = recent[recent["diff"] > SP_MAX_DIFF_PP]

    if not off.empty:
        sample = off.sort_values("diff", ascending=False).head(5)
        detail = ", ".join(f"{r.afp} {r.fondo} {r.year}-{r.month:02d} ({r.diff:.3f} pp)"
                           for r in sample.itertuples())
        problems.append(f"rent vs SP: {len(off)} monthly returns differ > {SP_MAX_DIFF_PP} pp: {detail}")
    else:
        log.info("rent vs SP OK: %d AFP-months, max diff %.4f pp", len(recent), recent["diff"].max())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    problems: list[str] = []
    check_rentabilidades(problems)
    check_afiliados(problems)
    check_comisiones(problems)
    check_financiero(problems)
    check_rent_vs_sp(problems)

    if problems:
        for p in problems:
            log.error("  %s", p)
        raise ValueError(
            f"Validation failed ({len(problems)} problem(s)) - export blocked:\n  - "
            + "\n  - ".join(problems)
        )
    log.info("Validation passed - safe to export.")


if __name__ == "__main__":
    run()
