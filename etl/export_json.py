"""
export_json.py — read processed parquets, write JSON files for the frontend.

Writes to BOTH:
  - data/output/*.json          (committed to git)
  - frontend/public/data/*.json (served by Vite dev server)

Run standalone:
    python -m etl.export_json
"""

import json
import logging
import shutil
from pathlib import Path

import pandas as pd

from etl.config import DATA_OUTPUT, DATA_PROCESSED, FRONTEND_DATA

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Wrote %s", path)


MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def export_rentabilidades() -> None:
    src = DATA_PROCESSED / "rentabilidades.parquet"
    if not src.exists():
        log.warning("Missing %s — skipping rentabilidades export", src)
        return

    df = pd.read_parquet(src)

    # Reference month is stored in the parquet (same for every row)
    ref_year  = int(df["ref_year"].iloc[0])
    ref_month = int(df["ref_month"].iloc[0])
    last_month_label = f"{MESES_ES[ref_month]} de {ref_year}"

    output = {}

    for (afp, fondo), group in df.groupby(["afp", "fondo"]):
        # Sort window descending → oldest window first (left side of bar chart)
        group = group.sort_values("window", ascending=False)
        key   = f"{afp}__{fondo}"

        # Period returns — same value for all rows of this AFP/fondo, take first
        periodos = {}
        for p in ["2y", "5y", "10y", "15y"]:
            if p in group.columns:
                val = group[p].iloc[0]
                periodos[p] = round(float(val), 2) if pd.notna(val) else None
            else:
                periodos[p] = None

        output[key] = {
            "afp":              afp,
            "fondo":            fondo,
            "last_month_label": last_month_label,
            # End year of each window → used as X-axis label in the bar chart
            "window_end_years": group["end_year"].tolist(),
            # Full range label → shown in tooltip: "abr 2025–mar 2026"
            "window_labels":    group["label"].tolist(),
            "values": [
                round(float(v), 2) if pd.notna(v) else None
                for v in group["rent_real"]
            ],
            "periodos": periodos,
        }

    _write(DATA_OUTPUT / "rentabilidades.json", output)


def export_comisiones() -> None:
    src = DATA_PROCESSED / "comisiones.parquet"
    if not src.exists():
        log.warning("Missing %s — skipping comisiones export", src)
        return

    df = pd.read_parquet(src)
    cols = [c for c in ["afp", "comision_pct", "sis_pct", "total_pct", "tipo"] if c in df.columns]
    records = df[cols].to_dict(orient="records")
    # Round floats
    for r in records:
        for k, v in r.items():
            if isinstance(v, float):
                r[k] = round(v, 4)

    _write(DATA_OUTPUT / "comisiones.json", records)


def export_financiero() -> None:
    src = DATA_PROCESSED / "financiero.parquet"
    if not src.exists():
        log.warning("Missing %s — skipping financiero export", src)
        return

    df = pd.read_parquet(src)
    output = {}

    for afp, group in df.groupby("afp", observed=True):
        group = group.sort_values("year")
        record = {}
        numeric_cols = [c for c in group.columns if c not in ("afp",)]
        for col in numeric_cols:
            vals = group[col].tolist()
            record[col] = [round(v, 2) if isinstance(v, float) and pd.notna(v) else (None if pd.isna(v) else v) for v in vals]
        output[afp] = record

    _write(DATA_OUTPUT / "financiero.json", output)


def export_afiliados() -> None:
    src = DATA_PROCESSED / "afiliados.parquet"
    if not src.exists():
        log.warning("Missing %s — skipping afiliados export", src)
        return

    df = pd.read_parquet(src)
    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if pd.isna(v) if not isinstance(v, (list, dict)) else False:
                r[k] = None

    _write(DATA_OUTPUT / "afiliados.json", records)


def copy_to_frontend() -> None:
    """Mirror data/output/ → frontend/public/data/ so Vite dev server can serve them."""
    for json_file in DATA_OUTPUT.glob("*.json"):
        dest = FRONTEND_DATA / json_file.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_file, dest)
        log.info("Copied → %s", dest)


def run() -> None:
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    export_rentabilidades()
    export_comisiones()
    export_financiero()
    export_afiliados()
    copy_to_frontend()
    log.info("All JSON exports complete.")


if __name__ == "__main__":
    run()
