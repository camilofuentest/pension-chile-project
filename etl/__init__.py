"""
etl — pension-chile data pipeline.

Execution order:
  1. download.py            → fetch raw files from spensiones.cl → data/raw/
  2. clean_rentabilidades.py → normalize + melt → data/processed/rentabilidades.parquet
  3. clean_comisiones.py    → normalize       → data/processed/comisiones.parquet
  4. clean_financiero.py    → normalize + ROE → data/processed/financiero.parquet
  5. clean_afiliados.py     → normalize       → data/processed/afiliados.parquet
  6. export_json.py         → parquets → data/output/*.json + frontend/public/data/

Run everything at once:
  python -m etl.run_pipeline
"""
