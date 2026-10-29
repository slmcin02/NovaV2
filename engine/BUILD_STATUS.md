# BUILD STATUS

Current package: NOVA laptop Py3.14 audit-hardened build v8

Integrated in this build:
- Sector coherence / reflexivity filter
- Spin lock coherence gate
- SCI velocity / acceleration / failure tagging
- Hidden liquidity + float turnover estimates
- Synth-flow distortion scoring
- Probability calibration with lower-confidence-bound ranking
- Market-ops layer (holidays, early close, OPEX risk)
- Execution-quality monitor and persistence
- Strengthened preflight around laptop-safe gates

Still external by design:
- live credentials
- actual live provider enablement
- paper/live validation after hookup


## v9 free-source build
- Added SEC FTD, Nasdaq halts, FRED macro, ClinicalTrials, FDA calendar, and CFTC adapters.
- Added free_source_events storage and ingest-free-sources CLI.
- Integrated OCC open interest, SEC FTD, FRED macro regime, and Nasdaq halt blocking into scan/scoring pipeline.
- Upgraded scoring optimization with multicollinearity penalties and rank-stability reporting.
