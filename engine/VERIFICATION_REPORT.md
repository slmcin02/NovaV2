# Verification Report

Build checked: `nova_laptop_py314_scoring_hardened_v6.zip`

## What was verified

- Python compilation of the full `nova/` package
- Full pytest suite
- Clean-boot replay path from an empty local database
- Scan → signal storage → backtest → calibration → scoring optimization → paper-step smoke flow
- Audit command
- Database table creation and row persistence
- Preflight scoring/risk/provider checks

## Results

- `27/27` tests passed
- `compileall` passed
- Clean replay generated signals successfully
- Backtest completed successfully on generated signals
- Calibration and scoring optimization completed successfully
- Paper-step executed successfully
- Audit completed successfully

## Scope limits

This verifies the packaged code, local storage/parsing, and replay/offline workflows.
It does **not** prove live-provider credentials, live market data quality, or live execution behavior.
