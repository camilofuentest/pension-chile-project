# Tu Pensión en Datos

Dashboard público sobre el sistema AFP chileno. Datos reales de la Superintendencia de Pensiones, explicados en lenguaje simple para cualquier chileno — sin jerga financiera.

**Stack:** Python 3.13 · pandas · React 18 · Vite · Recharts · Tailwind CSS v4 · Vercel

---

## ¿Qué muestra este dashboard?

| Sección | Qué encontrarás |
|---|---|
| **KPIs** | Afiliados totales al sistema, AFP con más afiliados, brecha máxima de comisiones |
| **Los 5 fondos** | Qué es cada fondo (A–E), su nivel de riesgo y para quién es recomendado |
| **Ranking de rentabilidad** | Mejor y peor AFP en 2, 5, 10 y 15 años por fondo — con calculadora de impacto en pesos |
| **Rentabilidad histórica** | Períodos de 12 meses rolling por AFP y fondo, ya descontando inflación |
| **Comisiones** | Cuánto te cobra cada AFP en pesos concretos según tu sueldo imponible |
| **AFP como negocio** | ROE por AFP y año — quién gana más para sus dueños, y si eso te afecta a ti |

---

## Estructura del proyecto

```
pension-chile-project/
├── data/
│   ├── raw/            ← archivos originales de spensiones.cl (gitignored)
│   ├── processed/      ← parquets intermedios (gitignored)
│   └── output/         ← JSONs finales (committed — el frontend los lee)
│       ├── rentabilidades.json
│       ├── comisiones.json
│       ├── afiliados.json
│       └── financiero.json
├── etl/
│   ├── config.py                  ← constantes, rutas, mapa de nombres AFP
│   ├── scrape_rentabilidades.py   ← POST scraper → parquet
│   ├── scrape_financiero.py       ← scraper estados financieros → parquet
│   ├── clean_rentabilidades.py    ← mensual → ventanas rolling, períodos
│   ├── clean_comisiones.py        ← XLS → comisiones.parquet
│   ├── clean_afiliados.py         ← XLS → afiliados.parquet
│   ├── clean_financiero.py        ← raw → financiero.parquet + ROE/ROA
│   ├── export_json.py             ← parquets → JSONs para el frontend
│   └── run_pipeline.py            ← orquesta todo en secuencia
├── frontend/                      ← React + Vite
│   ├── public/
│   │   ├── data/                  ← JSONs servidos por Vite
│   │   └── logos/                 ← logos oficiales AFP (SVG/PNG)
│   └── src/
│       ├── hooks/useAfpData.js
│       ├── utils/format.js
│       ├── utils/afpLogos.jsx      ← mapa de logos AFP compartido
│       └── components/
│           ├── KpiCards.jsx
│           ├── FondosExplainer.jsx
│           ├── RentabilidadChart.jsx
│           ├── RankingTable.jsx
│           ├── ComisionesChart.jsx
│           └── SaludFinanciera.jsx
├── notebooks/                     ← EDA por dataset
└── .github/workflows/             ← actualización mensual automática
```

---

## Cómo correr el ETL localmente

### 1. Crear y activar el entorno virtual

```bash
# Crear el venv (una sola vez)
python -m venv .venv
```

| Terminal | Comando para activar |
|---|---|
| **Git Bash** (Windows) | `source .venv/Scripts/activate` |
| **PowerShell** | `.venv\Scripts\Activate.ps1` |
| **CMD** | `.venv\Scripts\activate.bat` |
| **Mac / Linux** | `source .venv/bin/activate` |

El prompt cambia a `(.venv)` cuando está activo. Para salir: `deactivate`.

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Correr el pipeline

```bash
# Pipeline completo (recomendado)
python -m etl.run_pipeline

# O paso a paso:
python -m etl.scrape_rentabilidades   # rentabilidades 2006→hoy
python -m etl.scrape_financiero       # estados financieros 2010→hoy
python -m etl.clean_rentabilidades
python -m etl.clean_comisiones
python -m etl.clean_afiliados
python -m etl.clean_financiero
python -m etl.export_json             # genera los 4 JSONs
```

---

## Cómo correr el frontend localmente

```bash
cd frontend
npm install
npm run dev
# Abre http://localhost:5173
```

---

## Fuente de datos

| Dataset | Fuente | Método |
|---|---|---|
| Rentabilidad real fondos A–E | spensiones.cl/apps/rentabilidad | Scraping POST mensual 2006→hoy |
| Comisiones vigentes | spensiones.cl (Excel) | Descarga directa |
| Afiliados y cuota de mercado | spensiones.cl (Excel) | Descarga directa |
| Estados financieros AFP | spensiones.cl/apps/loadEstadisticas | Scraping HTML 2010→hoy |

Datos actualizados automáticamente el primer día de cada mes via GitHub Actions.

---

## Decisiones técnicas destacadas

- **Ventanas rolling de 12 meses** en lugar de años calendario — evita que un año parcial distorsione los promedios. El mes de referencia es el último con datos reales, no el último en el archivo.
- **Compounding geométrico** para agregar retornos mensuales a anuales — matemáticamente correcto.
- **ROE con encaje** — ganancia total / patrimonio total. Ambos términos incluyen el efecto del encaje, lo que da el ROE estándar desde el punto de vista del accionista.
- **PlanVital coalescing** — el Excel de SP publica la misma AFP en hasta 3 columnas con variantes de espaciado. Se resuelve con `bfill(axis=1)`.
- **Logos AFP** descargados desde sitios oficiales y servidos localmente para evitar dependencias externas.

---

## Despliegue

Desplegado en Vercel. Cada push a `main` activa un redeploy automático.
El workflow de GitHub Actions actualiza los datos mensualmente y hace commit de los JSONs.

---

Desarrollado por **Camilo Fuentes Toro** — [LinkedIn](https://www.linkedin.com/in/camilo-fuentes-toro/)
Ingeniero Civil Industrial | Operaciones Financieras · Análisis de Datos · Control de Procesos

Este sitio no está afiliado ni patrocinado por ninguna AFP. Todos los datos son públicos y provienen de la [Superintendencia de Pensiones de Chile](https://www.spensiones.cl).
