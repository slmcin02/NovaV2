# 05_ACCEPTANCE_TEST_MATRIX.md

## Build acceptance gates

### A. Repository health
- project installs cleanly in a fresh environment
- lint config exists and runs
- type-check config exists and runs
- tests discover successfully
- README explains bootstrap and run flow

### B. Data contracts
- all core input/output models are typed
- invalid payloads fail predictably
- fixture provider can drive the full pipeline without live APIs

### C. Universal scoring
- universal base score computes deterministically
- normalization helpers clamp/scale correctly
- reason codes emit for positive and negative drivers

### D. Thesis router
- router returns one primary thesis
- optional secondary thesis allowed
- router rejects unsupported thesis families cleanly

### E. Contract selector
- hard veto gates work
- sub-$1 stricter logic is enforced
- >$2.50 manual-override path is separate from normal behavior
- ranking is stable on identical inputs
- ranking output includes reason codes and component scores

### F. Exit engine
- exit triggers fire correctly for:
  - SCI decay
  - ThetaFade
  - VolCrush
  - flow reversal
  - premium distortion worsening
  - thesis-broken condition

### G. Alerts + paper workflow
- action policy maps to:
  - ignore
  - monitor
  - alert
  - paper-enter
- paper plan includes thesis, contract, stop/target/time horizon, reason codes
- outputs persist to local storage

### H. Replay / diagnostics
- replay can rerun stored sessions
- diagnostics summarize score components and reason codes
- a failed gate is visible in outputs, not silently swallowed

## Minimum CI-style commands
- `python -m pytest -q`
- `python -m ruff check .`
- `python -m mypy nova_phase1`

## Minimum fixture tests
- one clean momentum continuation fixture
- one gamma squeeze fixture
- one short squeeze fixture
- one stealth accumulation fixture
- one sub-$1 restricted contract fixture
- one >$2.50 veto fixture
- one dilution-risk veto fixture
- one event-risk conflict fixture
