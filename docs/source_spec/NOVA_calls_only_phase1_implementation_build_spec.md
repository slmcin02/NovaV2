# NOVA Calls-Only Phase 1 - Implementation Build Spec

## Locked phase-1 target
- Calls only until mastered
- Stocks/options only
- Laptop only
- Paper / alerts / logs / replay only
- No autonomous live trading
- Manual-override veto above $2.50 premium
- Contract-centric selector; no stock-price gate

## Build objective
Build a single laptop-native system that can ingest inputs, score setups, route thesis, select contracts, attach exits, emit alerts, paper trade, log every decision, and replay historical sessions.

## Canonical architecture
1. Ingestion and canonical normalization
2. Feature build
3. SCI and guardrail evaluation
4. Thesis routing
5. Smart contract selection
6. Exit plan attachment
7. Alerts and paper-trade proposal
8. Replay and review

## Core modules
- provider_interfaces
- ingest_scheduler
- feature_builder
- sci_engine
- guardrail_engine
- thesis_router
- contract_selector
- exit_engine
- alert_engine
- paper_trade_engine
- storage_layer
- replay_engine
- dashboard
- calibration_tools

## SCI category structure
- Flow & dark pool: 30
- Volatility & gamma: 20
- Momentum: 20
- Liquidity & microstructure: 15
- Theta & survival: 15

## Signal tiers
- Watch: SCI 75-84
- Execute: SCI 85-94
- Lock: SCI 95+

## Contract hard floors
- DTE > 7
- OI ≥ 500
- Option volume ≥ 100
- Spread ≤ 20%
- Reject obvious IV trap / severe premium distortion

## Preferred quality tier
- OI ≥ 1,000, ideally 2,000+
- Option volume ≥ 300, ideally 500+
- Spread ≤ 10-12%

## Contract selection defaults
- Premium band: $1.10-$2.50 primary
- $0.80-$0.99: stricter-entry bucket
- < $0.80: exceptional only
- Near-ATM to slightly OTM unless thesis-specific gamma map strongly favors another strike
- Watch tier uses longer runway; Execute/Lock can move nearer only if survivability remains strong
- Final rank balances survivability, liquidity, theta friction, premium distortion, gamma/flow alignment, and exitability

## Thesis families
- Momentum continuation
- Gamma squeeze
- Short squeeze
- Stealth accumulation breakout
- Insider-backed accumulation
- Volatility expansion continuation

## Guardrails
- ThetaFade / theta sink
- IV trap / VolCrush
- Spoof / anomaly / distortion
- Dilution / offering / shelf / ATM / convertibles

## Recommended layout
```text
nova_calls_phase1/
  app/
    providers/
    ingest/
    features/
    scoring/
    routing/
    selector/
    exits/
    alerts/
    paper/
    replay/
    dashboard/
    utils/
  config/
    defaults.yaml
    providers.yaml
    thresholds.yaml
  data/
    raw/
    normalized/
    marts/
    logs/
    replay/
  db/
    nova_calls.duckdb
  tests/
    unit/
    integration/
    replay/
  docs/
    implementation_spec/
```

## Build order
1. Schemas + storage
2. SCI + guardrails
3. Thesis router
4. Contract selector
5. Exit engine
6. Alerts + paper workflow
7. Replay + QA

## Acceptance criteria
- Raw/normalized/mart rows land deterministically
- Signals emit valid tiers and tags
- Known examples route into intended thesis families
- Selector returns chosen contract and ranked alternatives
- Exit engine transitions paper trades correctly under replay
- Alerts create paper rows and log packets
- Replay reproduces prior-session behavior with auditable traces

## Deferred
- Puts and spreads
- Autonomous execution
- VPS/server deployment
- Crypto
- Short-premium logic
- Broader portfolio optimization
