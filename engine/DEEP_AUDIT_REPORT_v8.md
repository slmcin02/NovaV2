# NOVA Laptop Py3.14 Deep Audit v8

## What was checked

- full `pytest` suite
- full package compile check
- end-to-end CLI flow:
  - `validate`
  - `preflight`
  - `replay --fixture sample_option_scan_expanded.csv`
  - `backtest`
  - `calibrate`
  - `optimize-scoring`
  - `paper-step --provider replay`
  - `execution-quality`
  - `market-ops`
  - `audit`
- import inventory review across package modules
- packaging metadata review (`pyproject.toml` vs `requirements-py314.txt`)
- storage layer review (DuckDB/SQLite fallback + Parquet/CSV fallback)

## What was fixed in v8

1. **Packaging metadata bug fixed**
   - `pyproject.toml` previously had an empty `project.dependencies` list.
   - This meant `pip install .` would install the package entrypoint without installing runtime dependencies.
   - `project.dependencies` is now populated and synchronized with `requirements-py314.txt`.

2. **Dependency floors refreshed**
   - Requirements were updated to current Python 3.14-capable releases verified from current PyPI package pages during audit.
   - This reduces the chance of landing on stale versions when the package is installed on the laptop.

## Local verification results

- `27/27` tests passed
- full compile check passed
- replay pipeline generated signals correctly
- signal storage and backtest persistence worked
- calibration and scoring optimization produced outputs
- execution-quality and market-ops commands executed correctly
- audit command passed

## Honest limits

- Runtime verification in the container was performed on Python 3.13.5.
- Python 3.14 compatibility was strengthened by refreshing dependency floors against current package release data and wheel availability, but this is not the same thing as a full live run on the target laptop.
- Live provider credentials, live data quality, and live broker behavior remain external validation tasks.

## Packaging check

- `pip install . --ignore-requires-python --no-deps --target /tmp/nova_pkg_test` succeeded in the audit container.
- `import nova` and `import nova.cli` succeeded from the installed target.
- A normal `pip install .` was correctly blocked in the container because the container is running Python 3.13.5 while the package explicitly requires Python 3.14+.
