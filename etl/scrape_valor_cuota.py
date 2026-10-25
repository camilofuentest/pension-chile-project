"""
scrape_valor_cuota.py — download daily valor cuota + patrimonio per AFP and fondo.

Source: spensiones.cl/apps/valoresCuotaFondo (one CSV-like file per fondo × year).
The valor cuota is the price of one unit of the fund. Comparing it between two
dates gives the exact nominal return of that period, with no rounding.

Output: data/raw/valor_cuota/valor_cuota_raw.parquet
        Columns: afp | fondo | fecha | valor_cuota | valor_patrimonio
        One row per AFP/fondo/day (the SP publishes every calendar day,
        weekends included).

Run standalone:
    python -m etl.scrape_valor_cuota
"""

import io
import logging
import time
from datetime import date

import pandas as pd
import requests

from etl.config import (
    AFP_NAME_MAP,
    FONDOS,
    RAW_VALOR_CUOTA,
    VALOR_CUOTA_URL,
    VALOR_CUOTA_YEARS_BACK,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT  = RAW_VALOR_CUOTA / "valor_cuota_raw.parquet"
SLEEP   = 0.5   # seconds between requests
RETRIES = 3


def _fetch(fondo: str, year: int) -> str:
    """
    Download one fondo × year. Retries a few times, then raises.

    A missing year would silently leave holes in the 12-month windows,
    so here a failure stops the pipeline instead of being skipped.
    """
    params = {
        "aaaaini": year,
        "aaaafin": year,
        "tf":      fondo,
        "fecconf": date.today().strftime("%Y%m%d"),
    }
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(VALOR_CUOTA_URL, params=params, timeout=60)
            r.raise_for_status()
            r.encoding = "iso-8859-1"   # the SP file is Latin-1, not UTF-8
            return r.text
        except requests.RequestException as exc:
            log.warning("  fondo %s %d attempt %d/%d failed: %s", fondo, year, attempt, RETRIES, exc)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Could not download valor cuota fondo {fondo} {year}")


def _parse_section(lines: list[str], fondo: str) -> pd.DataFrame:
    """
    One "Valores Confirmados" section of the file:
      line 0: "Valores Confirmados"   line 1: empty
      line 2: "Fecha;CAPITAL;;CUPRUM;;..."            ← AFP names (each spans 2 cells)
      line 3: ";Valor Cuota;Valor Patrimonio;..."     ← column names
      line 4+: "2026-01-01;84.438,32;7425745000772;..."
    """
    if len(lines) < 5:
        return pd.DataFrame()

    afp_cells = [c.strip() for c in lines[2].split(";")[1:]]
    col_cells = [c.strip() for c in lines[3].split(";")[1:]]

    # Each AFP name appears once and covers the next 2 cells (cuota, patrimonio).
    # Walk the column row and carry the last AFP name seen forward.
    columns, current_afp = ["fecha"], None
    for i, col in enumerate(col_cells):
        if i < len(afp_cells) and afp_cells[i]:
            current_afp = afp_cells[i]
        campo = "valor_cuota" if "cuota" in col.lower() else "valor_patrimonio"
        columns.append(f"{current_afp}__{campo}")

    df = pd.read_csv(
        io.StringIO("\n".join(lines[4:])),
        sep=";", header=None, names=columns, dtype=str, on_bad_lines="skip",
    )
    df["fecha"] = pd.to_datetime(df["fecha"].str.strip(), format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["fecha"])

    # Wide → long: one row per (fecha, column). melt() is the opposite of pivot.
    long = df.melt(id_vars="fecha", var_name="col", value_name="valor")
    long[["afp_raw", "campo"]] = long["col"].str.split("__", n=1, expand=True)

    # Chilean number format: "84.438,32" → 84438.32
    long["valor"] = pd.to_numeric(
        long["valor"].str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

    tidy = long.pivot_table(index=["fecha", "afp_raw"], columns="campo",
                            values="valor", aggfunc="first").reset_index()
    tidy.columns.name = None
    tidy["fondo"] = fondo
    return tidy.dropna(subset=["valor_cuota"])


def _parse(text: str, fondo: str) -> pd.DataFrame:
    """When an AFP starts or merges mid-year, the file has several sections."""
    lines  = text.strip().split("\n")
    starts = [i for i, line in enumerate(lines) if "Valores Confirmados" in line]
    ends   = starts[1:] + [len(lines)]
    parts  = [_parse_section(lines[s:e], fondo) for s, e in zip(starts, ends)]
    parts  = [p for p in parts if not p.empty]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def scrape() -> pd.DataFrame:
    today  = date.today()
    years  = range(today.year - VALOR_CUOTA_YEARS_BACK, today.year + 1)
    frames = []

    for fondo in FONDOS:
        for year in years:
            df = _parse(_fetch(fondo, year), fondo)
            log.info("  fondo %s %d: %d rows", fondo, year, len(df))
            frames.append(df)
            time.sleep(SLEEP)

    df = pd.concat(frames, ignore_index=True)

    # Normalize names with the shared map ("CAPITAL" → "Capital").
    # Names not in the map (e.g. old AFPs like MAGISTER) keep their raw spelling;
    # clean_rentabilidades only keeps the AFPs in AFP_LIST.
    df["afp"] = df["afp_raw"].str.strip().map(AFP_NAME_MAP).fillna(df["afp_raw"].str.strip())

    df = (
        df[["afp", "fondo", "fecha", "valor_cuota", "valor_patrimonio"]]
        .drop_duplicates(subset=["afp", "fondo", "fecha"], keep="last")
        .sort_values(["afp", "fondo", "fecha"])
        .reset_index(drop=True)
    )
    return df


def run() -> None:
    RAW_VALOR_CUOTA.mkdir(parents=True, exist_ok=True)
    df = scrape()
    df.to_parquet(OUTPUT, index=False)
    log.info("Saved %d rows -> %s", len(df), OUTPUT)
    log.info("Range: %s to %s", df["fecha"].min().date(), df["fecha"].max().date())
    log.info("AFPs: %s", sorted(df["afp"].unique().tolist()))


if __name__ == "__main__":
    run()
