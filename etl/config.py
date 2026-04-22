"""
Central configuration for the pension-chile ETL pipeline.
All paths, constants, and mappings live here — never hardcode them in other scripts.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Root paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

DATA_RAW       = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_OUTPUT    = ROOT / "data" / "output"
FRONTEND_DATA  = ROOT / "frontend" / "public" / "data"

# Sub-folders inside data/raw/
RAW_RENTABILIDADES    = DATA_RAW / "rentabilidades"
RAW_COMISIONES        = DATA_RAW / "comisiones"
RAW_AFILIADOS         = DATA_RAW / "afiliados"
RAW_ESTADOS_FIN       = DATA_RAW / "estados_financieros"

# ---------------------------------------------------------------------------
# AFP name normalization
# Apply this map to any AFP name column before any analysis.
# Handles mergers, accent inconsistencies, and prefix variations.
# ---------------------------------------------------------------------------
AFP_NAME_MAP: dict[str, str] = {
    # --- Bansander → Capital (merged ~2010) ---
    "BANSANDER":         "Bansander",   # uppercase as it appears in SP HTML
    "Bansander":         "Bansander",
    "AFP Bansander":     "Bansander",
    # --- Capital ---
    "CAPITAL":           "Capital",
    "AFP Capital":       "Capital",
    # --- Cuprum ---
    "CUPRUM":            "Cuprum",
    "AFP Cuprum":        "Cuprum",
    # --- Habitat (Santa María merged into Habitat ~2000) ---
    "HABITAT":           "Habitat",   # uppercase, no accent, as in SP HTML
    "AFP Hábitat":       "Habitat",
    "AFP Habitat":       "Habitat",
    "SANTA MARIA":       "Santa Maria",   # old AFP, absorbed by Habitat
    "Santa Maria":       "Santa Maria",
    # --- Modelo (started 2010) ---
    "MODELO":            "Modelo",
    "AFP Modelo":        "Modelo",
    # --- PlanVital ---
    "PLANVITAL":         "PlanVital",
    "AFP PlanVital":     "PlanVital",
    "AFP Plan Vital":    "PlanVital",
    "Planvital":         "PlanVital",
    # --- Provida ---
    "PROVIDA":           "Provida",
    "AFP Provida":       "Provida",
    # --- Uno (started 2019) ---
    "UNO":               "Uno",
    "AFP Uno":           "Uno",
    # --- Sistema (SP system-wide average — kept for reference line in charts) ---
    "SISTEMA":           "Sistema",
    "Sistema":           "Sistema",
}

# Canonical AFP list (used for validation and ordering in outputs)
AFP_LIST = ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno"]

# AFPs with limited history — never interpolate, show null
AFP_LIMITED_HISTORY: dict[str, int] = {
    "Modelo": 2010,   # year founded
    "Uno":    2019,
}

# ---------------------------------------------------------------------------
# Fund types
# ---------------------------------------------------------------------------
FONDOS = ["A", "B", "C", "D", "E"]


# ---------------------------------------------------------------------------
# Estados financieros AFP
# ---------------------------------------------------------------------------
FINANCIERO_URL = (
    "https://www.spensiones.cl/apps/loadEstadisticas/"
    "loadCuadroFecuAFP.php"
)

# Internal SP identifier per AFP — used as ?idu= query param
AFP_IDU_MAP: dict[str, int] = {
    "Capital":   42,
    "Cuprum":    35,
    "Habitat":   27,
    "Modelo":    50,
    "PlanVital": 37,
    "Provida":   29,
    "Uno":       51,
}

FINANCIERO_START_YEAR = 2010   # earliest year with data on the SP site

# ---------------------------------------------------------------------------
# Rentabilidades parámetros
RENT_URL = "https://www.spensiones.cl/apps/rentabilidad/getRentabilidad.php"

RENT_FORM_BASE = {
      "btn": "Buscar",
  }

RENT_START_YEAR = 2006

# ---------------------------------------------------------------------------
# SP data sources
# Fill in the real URLs after inspecting www.spensiones.cl manually.
# Format: { key: { "url": "...", "filename": "...", "raw_dir": Path } }
# ---------------------------------------------------------------------------
SOURCES: dict[str, dict] = {
    # Example structure — replace with real URLs:
    # "rentabilidades_A": {
    #     "url": "https://www.spensiones.cl/...",
    #     "filename": "rentabilidades_fondo_A.xls",
    #     "raw_dir": RAW_RENTABILIDADES,
    # },
    "comisiones": {
        "url": "https://www.spensiones.cl/inf_estadistica/series_afp/comisiones/estructura_comisiones.xls",
        "filename": "estructura_comisiones.xls",
        "raw_dir": RAW_COMISIONES,
    },
    "afiliados": {
        "url": "https://www.spensiones.cl/inf_estadistica/series_afp/afiliados/afiliados.xls",
        "filename": "afiliados.xls",
        "raw_dir": RAW_AFILIADOS,
    },
}

# ---------------------------------------------------------------------------
# Output JSON filenames
# ---------------------------------------------------------------------------
OUTPUT_FILES = {
    "rentabilidades": DATA_OUTPUT / "rentabilidades.json",
    "comisiones":     DATA_OUTPUT / "comisiones.json",
    "afiliados":      DATA_OUTPUT / "afiliados.json",
    "financiero":     DATA_OUTPUT / "financiero.json",
}
