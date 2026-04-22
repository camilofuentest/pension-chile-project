# CLAUDE.md — Tu Pensión en Datos

Full context for any new conversation. Read this before touching any file.

---

## Who I'm working with

Chilean Industrial Civil Engineer, 8+ years in AFP/AGF financial operations
(AFP Capital, AGF SURA). Deep domain knowledge: custody operations, regulatory
reporting to Superintendencia de Pensiones (SP), multifondos A-E, comisiones,
rentabilidad real, estados financieros AFP.

**Learning path:** actively building Python/pandas skills via Google Advanced
Data Analytics Certificate. Intermediate level — understands logic, needs
explanation of Python-specific syntax and best practices.

**Teaching style to use:**
- Explain non-obvious Python syntax inline with comments (e.g. what `:02d` does)
- When writing new patterns for the first time, add a short "why" comment
- Don't explain things they already clearly know (AFP domain, financial concepts)
- Point out best practices as you apply them, briefly
- Code comments in English, all user-facing text in Spanish

---

## Project summary

Public dashboard about the Chilean AFP pension system for ANY Chilean user
(not just finance people). Data from estadisticas.spensiones.cl, cleaned with
Python/pandas, displayed in React.

**Portfolio goal:** demonstrate data engineering + React frontend skills.
**Author:** Camilo Fuentes Toro — LinkedIn: https://www.linkedin.com/in/camilo-fuentes-toro/

**Live stack:**
- Python 3.11, pandas, requests, pyarrow, openpyxl, xlrd, lxml, html5lib
- React 18, Vite, Recharts, Tailwind CSS v4 (`@tailwindcss/vite` plugin)
- GitHub Actions (monthly auto-update)
- Vercel (free hosting)

---

## Folder structure

```
pension-chile-project/
├── data/
│   ├── raw/rentabilidades/        ← rentabilidades_raw.parquet ✓
│   ├── raw/comisiones/            ← estructura_comisiones.xls ✓
│   ├── raw/afiliados/             ← afiliados.xls ✓
│   ├── raw/estados_financieros/   ← financiero_raw.parquet ✓
│   ├── processed/                 ← cleaned parquets (gitignored)
│   └── output/                    ← final JSONs (committed to git)
│       ├── rentabilidades.json
│       ├── comisiones.json
│       ├── afiliados.json
│       └── financiero.json
├── etl/
│   ├── config.py                  ← ALL constants: paths, URLs, AFP maps
│   ├── download.py                ← direct file downloads (comisiones, afiliados)
│   ├── scrape_rentabilidades.py   ← POST scraper → rentabilidades_raw.parquet ✓
│   ├── scrape_financiero.py       ← HTML scraper C10_RNRE + C02_BGPP ✓
│   ├── clean_rentabilidades.py    ← monthly→annual aggregation + periods ✓
│   ├── clean_comisiones.py        ← XLS → comisiones.parquet ✓
│   ├── clean_afiliados.py         ← XLS → afiliados.parquet ✓
│   ├── clean_financiero.py        ← raw → financiero.parquet + ROE/ROA ✓
│   ├── export_json.py             ← parquets → JSONs → data/output/ + frontend/public/data/
│   └── run_pipeline.py            ← orchestrates all steps
├── frontend/
│   ├── public/
│   │   ├── data/                  ← real JSONs served by Vite (all 4 present ✓)
│   │   │   └── sample/            ← sample JSONs for dev without ETL
│   │   └── logos/                 ← AFP logo files (SVG/PNG, downloaded from official sites)
│   │       ├── capital.svg, cuprum.png, habitat.svg
│   │       ├── modelo.png, planvital.png, provida.png, uno.svg
│   └── src/
│       ├── hooks/useAfpData.js    ← fetches all 4 JSONs, returns {data,loading,error}
│       ├── utils/format.js        ← formatPesos(), formatPct(), costoPorMes()
│       ├── utils/afpLogos.jsx     ← AFP_LOGOS map + AfpLogo component (shared)
│       ├── components/
│       │   ├── KpiCards.jsx       ✓ afiliados total, largest AFP, commission gap
│       │   ├── FondosExplainer.jsx✓ static explainer for fondos A-E
│       │   ├── RentabilidadChart.jsx ✓ rolling 12-month windows, YTD-aware
│       │   ├── RankingTable.jsx   ✓ 2y/5y/10y/15y periods, medals, gap calculator
│       │   ├── ComisionesChart.jsx✓ bar chart + detail table, salary calculator
│       │   └── SaludFinanciera.jsx✓ ROE ranking cards + historical bar chart
│       ├── App.jsx                ← layout, section cards, hero, footer with author
│       ├── main.jsx
│       └── index.css              ← @import "tailwindcss" only
├── notebooks/
│   ├── 01_eda_rentabilidades.ipynb
│   ├── 02_eda_comisiones.ipynb
│   └── 03_eda_financiero.ipynb
├── .github/workflows/update_data.yml
├── vercel.json
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Architecture rules (enforce strictly)

1. `etl/config.py` is the single source of truth — paths, URLs, AFP maps, constants
2. Python writes JSON. React reads JSON. Never mix.
3. `data/raw/` and `data/processed/` are gitignored. `data/output/*.json` are committed.
4. `export_json.py` writes to BOTH `data/output/` AND `frontend/public/data/`
5. No component calls `fetch()` — only `useAfpData.js` does
6. Every ETL script is independently runnable: `python -m etl.clean_rentabilidades`
7. All user-facing text in Spanish. Code, variables, comments in English.
8. `src/utils/afpLogos.jsx` is the single source of AFP logos — never duplicate the map.

---

## Data source: rentabilidades ✓ COMPLETE

**URL:** `https://www.spensiones.cl/apps/rentabilidad/getRentabilidad.php`
**Method:** POST — `aaaa=YYYY&mm=MM&btn=Buscar`
**Data available from:** 2006 (`RENT_START_YEAR = 2006` in config.py)

**Page returns 7+ HTML tables per request:**
- `tables[0]`, `tables[1]` → navigation/garbage, skip
- `tables[2..6]` → Fondos A–E respectively

**Each fondo table columns (by position):**
- `iloc[:, 0]` → AFP name (ALL CAPS)
- `iloc[:, 1]` → monthly return string ("7,35%")

**String cleaning:** comma→dot, strip %, `pd.to_numeric(errors="coerce")`
**Row 0** always NaN → dropped via `dropna(subset=["afp"])`
**SISTEMA row** → dropped via `~str.contains("SISTEMA")`

**Scrape output:** `data/raw/rentabilidades/rentabilidades_raw.parquet`
Columns: `afp | rent_real | fondo | year | month`

---

## ETL pipeline: rentabilidades ✓ COMPLETE

### clean_rentabilidades.py — 3 steps
1. **build_windows()** — rolling 12-month windows using `seq = year*12 + (month-1)`
   - `ref_seq` = latest month WITH actual data (not just latest in file — avoids NaN current month)
   - `months_ago >= 0` filter drops future/NaN rows before windowing
   - `window = months_ago // 12`
2. **enforce_history_limits()** — null out Modelo before 2010, Uno before 2019
3. **_period_annualized()** — annualized 2y/5y/10y/15y using `window_series[index < n_years]`
   - NOT `nsmallest()` (that selects lowest VALUES, not lowest index)

### export_json.py — rentabilidades.json schema
```json
{
  "Capital__C": {
    "afp": "Capital",
    "fondo": "C",
    "last_month_label": "marzo de 2026",
    "window_end_years": [2007, ..., 2026],
    "window_labels":    ["abr 2006–mar 2007", ...],
    "values":           [5.2, ..., 1.8],
    "periodos":         { "2y": 3.1, "5y": 4.1, "10y": 3.8, "15y": null }
  }
}
```

---

## Data source: comisiones ✓ COMPLETE

**URL:** `https://www.spensiones.cl/inf_estadistica/series_afp/comisiones/estructura_comisiones.xls`
**Method:** Direct download via `download.py`

**XLS quirks:**
- PlanVital appears as 3 column variants: `'PLANVITAL'`, `'PLANVITAL '`, `' PLANVITAL'`
- Coalesced with `df[variants].apply(pd.to_numeric, errors="coerce").bfill(axis=1).iloc[:, 0]`
- Values in the XLS are decimals (0.0057) → multiply by 100 for percentage

**Output:** `data/processed/comisiones.parquet`
Columns: `afp | comision_pct | sis_pct | total_pct | tipo`

### comisiones.json schema
```json
[
  { "afp": "Modelo", "comision_pct": 0.58, "sis_pct": 1.49, "total_pct": 2.07, "tipo": "dependiente" }
]
```

---

## Data source: afiliados ✓ COMPLETE

**URL:** `https://www.spensiones.cl/inf_estadistica/series_afp/afiliados/afiliados.xls`
**Method:** Direct download

**XLS quirks:**
- PlanVital variants: `'PLANVITAL'`, `'PLANVITAL.1'` (pandas auto-renames duplicate), `'PLANVITAL '`
- Includes `'SISTEMA'` → `'Sistema'` row as authoritative total for market share calculation

**Output:** `data/processed/afiliados.parquet`
Columns: `afp | afiliados | fecha | market_share_pct`
8 rows: Sistema + 7 AFPs

### afiliados.json schema
```json
[
  { "afp": "Sistema", "afiliados": 12500000, "fecha": "2024-12", "market_share_pct": 100.0 },
  { "afp": "Provida", "afiliados": 3200000,  "fecha": "2024-12", "market_share_pct": 25.6 }
]
```

---

## Data source: estados financieros ✓ COMPLETE

**URL:** `https://www.spensiones.cl/apps/loadEstadisticas/loadCuadroFecuAFP.php`
**Method:** GET with params `?menu=sci&menuN1=estfinafp&menuN2=NOID&cuadroid=X&idu=Y&periodo=YYYYMM&tipo=html`
**Scrapes Q4 (December) of each year — full-year cumulative figures**

**Tables scraped:**
- `C10_RNRE` → P&L (resultado neto)
- `C02_BGPP` → Balance sheet (patrimonio + activos)

**Account codes extracted:**
- `82.10.010` → `ganancia_miles` (net income incl. encaje)
- `82.10.000` → `sin_encaje_miles` (net income excl. encaje — pure ops)
- `25.11.000` → `patrimonio_miles` (total equity)
- `20.11.000` → `total_activos_miles` (total assets)

**Value format:** "miles de pesos" with dots as thousands separators.
Negatives in Chilean accounting notation: `(5.000)` = -5000.
`_parse_miles()` handles both conventions.

**AFP IDU map** (internal SP identifier, never changes):
```python
AFP_IDU_MAP = {
    "Capital": 42, "Cuprum": 35, "Habitat": 27,
    "Modelo": 50, "PlanVital": 37, "Provida": 29, "Uno": 51,
}
```
**Start year:** 2010 (`FINANCIERO_START_YEAR`)

**Output:** `data/raw/estados_financieros/financiero_raw.parquet`
103 rows — 7 AFPs × ~15 years

### clean_financiero.py — computes ROE and ROA
- `roe_pct = ganancia_miles / patrimonio_miles * 100` (only where patrimonio > 0)
- `roa_pct = ganancia_miles / total_activos_miles * 100`
- ROE uses `ganancia_miles` (WITH encaje) — correct for standard ROE: both numerator and denominator include the encaje effect

### financiero.json schema
```json
{
  "Capital": {
    "year":                [2010, 2011, ..., 2025],
    "ganancia_miles":      [39836568, ...],
    "sin_encaje_miles":    [20985923, ...],
    "patrimonio_miles":    [426820132, ...],
    "total_activos_miles": [488818904, ...],
    "roe_pct":             [9.33, ...],
    "roa_pct":             [8.15, ...]
  }
}
```

---

## AFP name decisions (user chose deliberately — do not change without asking)

Historical AFPs kept as **separate entities** — not merged into current AFP names.

`AFP_NAME_MAP` normalizes case/prefixes only:
- `BANSANDER` → `"Bansander"` (historical, until ~2010)
- `SANTA MARIA` → `"Santa Maria"` (historical, absorbed by Habitat ~2000)
- `HABITAT` → `"Habitat"` (no accent — matches SP HTML exactly)
- `CAPITAL` → `"Capital"`, `CUPRUM` → `"Cuprum"`
- `MODELO` → `"Modelo"` (started 2010)
- `PLANVITAL` → `"PlanVital"`, `PROVIDA` → `"Provida"`
- `UNO` → `"Uno"` (started 2019)

**AFP_LIST** (canonical, used for ordering): `["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno"]`
No accent on Habitat — consistent throughout config.py and all components.

**AFPs with limited history** (null, never interpolate):
- `Modelo`: founded 2010
- `Uno`: founded 2019

---

## Frontend: current state ✓ COMPLETE & RUNNING

All 4 datasets live. All 6 components data-complete. `npm run dev` → `http://localhost:5173`

### UI design system
- **Brand color:** `blue-600` (#2563eb) — selected buttons, h2 accent borders, header icon
- **Positive data:** `green-500` (#22c55e) / `green-600` — chart bars, table values
- **Negative data:** `red-500` (#ef4444) — chart bars, table values
- **Neutral chart bars:** `blue-400` (#60a5fa)
- **Section layout:** each section wrapped in `bg-white rounded-2xl shadow-sm` card in App.jsx
- **Section headings:** `border-l-4 border-blue-600 pl-3` accent on all h2
- **Hero:** `bg-blue-50` with border, rounded card
- **Top accent:** 1px gradient bar `blue-700 → blue-400 → blue-600`

### AFP logos
- Stored in `frontend/public/logos/` — SVG preferred, PNG where SVG unavailable
- Shared via `src/utils/afpLogos.jsx` — `AFP_LOGOS` map + `AfpLogo` component
- Used in: ROE ranking cards (SaludFinanciera), RankingTable rows, ComisionesChart table
- `onError` fallback: hides image silently, AFP name text stays visible
- Modelo uses PWA app icon (512×512) — official horizontal logo unavailable on their CDN

### Key UI decisions per component

**RentabilidadChart.jsx**
- Rolling 12-month windows (not calendar years) on X-axis
- Green/red bars for positive/negative real return
- Custom tooltip in plain Spanish explaining what the % means
- "Lo que va del año" language — never "YTD"

**RankingTable.jsx**
- 2y/5y/10y/15y period selector
- Medals 🥇🥈🥉 for top 3, "menor rentabilidad" gray pill for worst
- Gap calculator: editable CLP input (formatted with `Intl.NumberFormat('es-CL')`)
- AFP logos `h-5 w-10` inline with name

**ComisionesChart.jsx**
- Horizontal bar chart sorted cheapest→most expensive
- "más barata" green tag, "más cara" red tag
- Salary calculator: CLP formatted text input with dot separators
- Detail table with logo + name + monthly cost + annual overpayment vs cheapest

**SaludFinanciera.jsx**
- ROE ranking: responsive card grid (2→3→4 cols), year selector, medals
- Historical ROE bar chart: AFP selector, blue/red bars, ROE tooltip
- Callout connects high ROE + high commissions as user-relevant insight
- ROE calculated WITH encaje (standard financial definition)

**KpiCards.jsx**
- 3 cards: total afiliados / largest AFP / commission gap
- Each card: `border-t-4` colored accent + inline SVG icon + value + note

### Footer
- Two-column: data source (left) + author credit (right)
- Author: Camilo Fuentes Toro, LinkedIn linked with official SVG icon
- Title: Ingeniero Civil Industrial | Operaciones Financieras · Análisis de Datos · Control de Procesos

---

## Target audience rules (every UI decision follows these)

Users are ordinary Chileans with zero financial knowledge, likely on mobile.

- Never use jargon without plain-Spanish explanation inline
- Every chart has a "¿Qué significa esto para mí?" callout
- Callout always ends with one concrete action or insight
- Show peso examples alongside percentages
- Chilean number format: `$1.200.000` not `$1,200,000`
- Modelo/Uno with no data → friendly note, never blank/error
- Tone: neutral, honest, empowering — not promotional for any AFP
- Partial year → different color bar, never shown as a complete year

---

## Current status

- [x] Full folder structure
- [x] `etl/config.py` — paths, AFP map, SP URLs, IDU map
- [x] `etl/scrape_rentabilidades.py` — working, data 2006→today
- [x] `etl/scrape_financiero.py` — C10_RNRE + C02_BGPP, 103 rows
- [x] `etl/clean_rentabilidades.py` — rolling windows, ytd, period returns
- [x] `etl/clean_comisiones.py` — XLS download + PlanVital variant coalescing
- [x] `etl/clean_afiliados.py` — XLS download + market share
- [x] `etl/clean_financiero.py` — ROE + ROA computation
- [x] `etl/export_json.py` — all 4 datasets exported
- [x] `etl/run_pipeline.py` — full pipeline wired
- [x] `frontend/` — Vite + React + Recharts + Tailwind v4
- [x] All 6 components data-complete and styled
- [x] AFP logos downloaded and integrated (7 AFPs)
- [x] UI design system: section cards, h2 accents, brand blue, hero, footer
- [x] `frontend/public/data/` — all 4 JSONs present
- [x] GitHub Actions workflow
- [x] `vercel.json`

---

## Open questions / decisions pending

1. **Bansander / Santa Maria in frontend:** show as separate historical series in charts,
   or hide and only show current AFPs? Not decided yet.
2. **Modelo logo:** currently using PWA app icon (square). Official horizontal wordmark
   unavailable on their CDN. Worth checking afpmodelo.cl periodically.
3. **run_pipeline.py:** verify scrape_financiero is wired into the full pipeline run.
