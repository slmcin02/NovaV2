$python = ".\.venv\Scripts\python.exe"
& $python -m nova.cli audit
& $python -m nova.cli preflight
& $python -m nova.cli replay --fixture sample_option_scan_expanded.csv
& $python -m nova.cli paper-step
& $python -m nova.cli backtest
& $python -m nova.cli cohorts
& $python -m nova.cli calibrate
