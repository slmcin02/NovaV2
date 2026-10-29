# NovaV2 offline calls-only Phase 1 - development build verification

October 28, 2026. MSI GT73VR laptop; Python 3.14.7.

## Proven working
- Original sources from nova_laptop_py314_fullybuilt_v9.zip and NOVA_Codex_Intake_Pack_v5.zip.
- Hash-verified source copy under engine/ and manifest at docs/NOVA_PHASE1_SOURCE_MANIFEST.json.
- Isolated Python 3.14.7 venv with complete installed dependencies.
- Full suite: 70 tests passed; Ruff lint and format of new modules and tests; undefined-identifier scan across Nova; Python compileall and pip dependency check.
- Deterministic six-thesis Phase1 policy and audited phase1-eval command for offline JSON fixtures; two hard vetoes and post-entry exit recommendation verified.
- Original V9 staged replay/paper diagnostic ran; it is not a real price-history trading backtest.

## Usage
From engine/:
1. Install Python 3.14.7 isolated environment with python -m pip install -e . pytest ruff.
2. Run python -m pytest -q tests.
3. Run python -m nova.cli phase1-eval --input data/fixtures/phase1_demo_offline.json --output <new unused receipt path>.
4. For nonfinancial diagnostics only, run python -m nova.cli backtest --diagnostic-score-proxy.

## Fixes verified with reproducing tests
- Offline replay does not reach live SEC or send real Discord alerts.
- ingest-edges --provider replay skips unknown historical free-source augmentation rather than fabricating present-day evidence.
- Score-derived proxy returns are not presented as market P&L or written by the CLI to canonical trades.
- train cannot consume synthetic score-derived labels; it requires verified paper fills and provenance, currently not implemented in the trade schema.
- Contract caps, malformed quotes and non-Boolean manual overrides fail closed.
- Sub-$1 exceptional eligibility follows the strict locked Phase1 thresholds, without overriding separate monitor-only liquidity flags.

## Remaining acceptance and deployment gaps
- Historical option bid/ask feed, T-1 data, 60-second execution lag, partial fills, full spread/commission assumptions, validated paper fill provenance and actual live provider health.
- Full Phase1 schema and production scanner adapter wiring; the new policy runs only via phase1-eval.
- True out-of-sample performance, final live alert safety, full corporate/Greeks provenance, hosted CI, reboot/restore and signed release gates.
- Production main and Stephen OS live system were not modified.
- Synthetic replay win rates cannot establish financial edge.

Status: tested developer build, paper-safe and offline; not production qualified.
