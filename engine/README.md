# NOVA Laptop PY314 Full Build

Laptop-first, calls-only options research and alert stack for **small- and mid-cap stocks**
with **call ask <= $2.50** and **DTE <= 90**.

This package upgrades the current free bundle into a **DuckDB + Parquet + feature store + scoring +
backtest + learner** architecture while staying practical for your **2016 MSI Titan / Windows 10 / Python 3.14**.

## Included

- Calls-only scanning
- Small/mid-cap universe filtering
- Premium cap, DTE cap, spread gate, OI gate
- DuckDB catalog + Parquet lake
- Free edge ingestion:
  - SEC dilution shield
  - FINRA CNMS short volume
  - OCC daily open interest
- Provider abstraction:
  - `yfinance` fallback provider
  - `ThetaData` adapter (ready when you enable it)
- SCI-style weighted scoring
- Strategy tags / style overlays
- Risk vetoes + contract suggestion sizing
- Backtest engine + completed trade table
- Local ensemble learner + drift check
- Discord/webhook alerts
- Local memory / retrieval layer
- Retention + compaction scripts
- Google Drive backup via `rclone`

## Honest status

This is a **real upgraded build**, not just a plan, but it is still **not magic**:
- no guaranteed edge
- no paid feed credentials included
- no claim of full institutional completeness on a laptop
- still needs real-world validation, walk-forward testing, and paper-trade hardening

## Quick start

```powershell
cd nova_laptop_py314_full_build
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements-py314.txt

copy .env.example .env
# edit .env if needed

.\.venv\Scripts\python -m nova.cli validate
.\.venv\Scripts\python -m nova.cli scan --provider yfinance
.\.venv\Scripts\python -m nova.cli ingest-edges
.\.venv\Scripts\python -m nova.cli backtest
.\.venv\Scripts\python -m nova.cli train
```

## Reviewed sources used to shape this build

See `REVIEWED_SOURCES.md`.


## Core build additions in this revision

- offline **replay provider** with fixture support
- **provider router** so the only remaining live-step is feed swap / credential wiring
- **paper broker** with order / fill / position ledger tables
- **paper risk engine** for stop / target / thesis-break exits
- **preflight checks** for config, storage, and session state
- **cohort analytics** for week / month / exit-reason summaries
- lightweight **vector memory** for local retrieval over recent signals
- expanded CLI commands:
  - `preflight`
  - `replay`
  - `paper-step`
  - `cohorts`
  - `memory-build`
  - `memory-query`

## Updated quick start

```powershell
.\.venv\Scripts\python -m nova.cli preflight
.\.venv\Scripts\python -m nova.cli replay
.\.venv\Scripts\python -m nova.cli paper-step
.\.venv\Scripts\python -m nova.cli backtest
.\.venv\Scripts\python -m nova.cli cohorts
.\.venv\Scripts\python -m nova.cli memory-build
```


## Final build additions in this revision

- **Polygon provider** added for live-feed swap readiness
- **fallback provider router** added (`auto`, comma chains, replay expansion)
- **ThetaData sync wrapper** added so the CLI can switch providers cleanly later
- **expanded replay fixture** added for deeper offline scans and paper-state testing
- **calibration engine** added to estimate slippage + score / stop / target recommendations from stored paper + backtest results
- new CLI commands:
  - `provider-check`
  - `calibrate`
  - `audit`


## Hardening added in v4

- default provider switched to `auto` so feed fallback is the normal path
- signals now persist `market_cap` and `sector` for better downstream replay/paper decisions
- paper positions now persist `market_cap` and `sector`
- `paper-step` now blocks entries that would break configured sector exposure
- scan path now enforces `scoring.min_score` in addition to contract/risk gates
- added `audit` command for compile/preflight/schema/lake sanity
- added GitHub Actions CI and `scripts/run_all.ps1`


## Added edge layers

- Sector coherence and reflexivity down-weighting
- Spin-lock avoidance
- Hidden-liquidity and float-turnover estimation
- Synth-flow distortion score
- Calibration-aware lower-confidence-bound ranking
- Market-ops awareness for holidays / OPEX / early close
- Execution-quality reporting
