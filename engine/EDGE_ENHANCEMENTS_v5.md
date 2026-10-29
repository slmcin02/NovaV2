# NOVA Laptop Edge Enhancements v5

Integrated into this package:

- Sector coherence and reflexivity filter
- Spin-lock coherence gate
- Hidden-liquidity and float-turnover estimation
- Synth-flow distortion score
- SCI velocity / acceleration / failure tagging
- Probability calibration with lower-confidence-bound ranking
- Market-ops layer for holidays / early close / OPEX risk
- Execution-quality monitor and persistence
- Strengthened preflight checks

New modules:
- nova/engine/market_ops.py
- nova/engine/signal_quality.py
- nova/engine/probability.py
- nova/engine/execution_quality.py

New CLI commands:
- market-ops
- execution-quality

Notes:
- This package stays laptop-first and provider-agnostic.
- Live hookup remains a later credentials/runtime step.
- Core tests pass locally.
