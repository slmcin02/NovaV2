# Reviewed Sources

## Local uploaded bundles reviewed
- `nova_stock_free_bundle.zip`
  - `calls_lite_plus.py`
  - `build_universe_from_cboe.py`
  - `alpaca_backfill_options_daily.py`
  - `occ_download_daily_open_interest.py`
  - `finra_download_cnms_short_volume.py`
  - `duckdb_build_from_philipp.sql`
- `nova_lite_free_edges_pack.zip`
  - `calls_lite_plus.py`
  - `build_universe_from_cboe.py`
- `Laptop.zip`
  - `Laptop.md`
  - supporting PDFs present in bundle

## Accessible Google Drive materials reviewed
- `Laptop-Based Calls-Only Options Alert + Continuous Backtest System Under $80/Month`
- `Project Nova: v37 "Singularity" Ultimate Build`
- `Project Nova: Master Codebase Audit & Logic Specification (v5.0)`

## How those sources were used
- Moved storage from SQLite-only toward DuckDB + Parquet.
- Kept calls-only / small-midcap / <= $2.50 premium / <= 90 DTE target.
- Added SCI-style scoring, risk vetoes, edge ingestion, alerts, learner, and backtest loop.
- Deliberately adapted away from VPS-only assumptions into a laptop-safe local build.
