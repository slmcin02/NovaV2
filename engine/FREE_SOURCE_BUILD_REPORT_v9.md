# NOVA Laptop Py3.14 — Free-Source Build Report v9

## What was added

- SEC FTD adapter (`nova/data/sec_ftd_adapter.py`)
- Nasdaq halts adapter (`nova/data/nasdaq_halts_adapter.py`)
- FRED macro adapter (`nova/data/fred_adapter.py`)
- ClinicalTrials adapter (`nova/data/clinicaltrials_adapter.py`)
- FDA calendar adapter (`nova/data/fda_calendar_adapter.py`)
- CFTC COT adapter (`nova/data/cftc_adapter.py`)
- `free_source_events` storage table
- `ingest-free-sources` CLI command

## What was integrated into scoring / scan

- OCC open interest now contributes to short-pressure modeling when available
- SEC FTD quantity now contributes to short-pressure modeling when available
- FRED macro regime score now applies a regime multiplier to scores when enabled
- Nasdaq halt status now blocks new signals for halted symbols in non-replay mode

## Scoring optimizer upgrades

- Empirical weights still derived from completed trade history
- Added multicollinearity penalty based on average pairwise absolute component correlation
- Added shrinkage toward current production weights to reduce overfitting
- Added rank-stability metric to measure top-of-book consistency after recommended reweighting

## Validation run

- `python -m compileall -q nova tests`
- `pytest -q` → 31 passed
- `python -m nova.cli preflight`
- `python -m nova.cli replay --fixture sample_option_scan_expanded.csv`
- `python -m nova.cli optimize-scoring`
- `python -m nova.cli ingest-free-sources --symbol PLTR`
- `python -m nova.cli audit`
- packaging sanity via `pip install . --ignore-requires-python --no-deps --target ...`

## Notes

- Replay mode stays offline-safe and does not depend on live free-source downloads.
- Live free-source fetches fail gracefully to cached / empty results.
- ClinicalTrials and FDA are ingested as stored overlays; they are not yet directly mapped into scoring because symbol-to-trial / symbol-to-advisory linkage is not reliable enough to hard-wire without a dedicated mapping layer.
