CREATE TABLE IF NOT EXISTS universe (
    symbol TEXT PRIMARY KEY,
    source TEXT,
    sector TEXT,
    market_cap BIGINT,
    bucket TEXT,
    active BOOLEAN,
    updated_ts TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signals (
    signal_ts TIMESTAMP,
    symbol TEXT,
    contract_symbol TEXT,
    expiration DATE,
    strike DOUBLE,
    "right" TEXT,
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE,
    spread_pct DOUBLE,
    implied_vol DOUBLE,
    underlying_price DOUBLE,
    dte INTEGER,
    delta DOUBLE,
    volume BIGINT,
    oi BIGINT,
    market_cap BIGINT,
    sector TEXT,
    finra_short_ratio DOUBLE,
    occ_open_interest BIGINT,
    sec_ftd_qty BIGINT,
    macro_regime_score DOUBLE,
    insider_buy_flag BOOLEAN,
    edgar_dilution_flag BOOLEAN,
    momentum_20d DOUBLE,
    vix_value DOUBLE,
    m_sigma DOUBLE,
    technical_score DOUBLE,
    sector_etf TEXT,
    sector_momentum_20d DOUBLE,
    sector_coherence DOUBLE,
    reflexivity_multiplier DOUBLE,
    spin_coherence DOUBLE,
    spin_lock BOOLEAN,
    float_turnover DOUBLE,
    hidden_liquidity_score DOUBLE,
    synth_flow_score DOUBLE,
    sci_velocity DOUBLE,
    sci_acceleration DOUBLE,
    failure_tag TEXT,
    calibrated_win_prob DOUBLE,
    score_lcb DOUBLE,
    event_risk TEXT,
    assignment_risk TEXT,
    blocked_market_ops BOOLEAN,
    expected_slippage_bps DOUBLE,
    score DOUBLE,
    elite BOOLEAN,
    strategy_tags TEXT,
    suggested_contracts INTEGER,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_ts TIMESTAMP,
    dedupe_key TEXT PRIMARY KEY,
    channel TEXT,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    entry_ts TIMESTAMP,
    exit_ts TIMESTAMP,
    symbol TEXT,
    contract_symbol TEXT,
    expiration DATE,
    strike DOUBLE,
    "right" TEXT,
    qty INTEGER,
    market_cap BIGINT,
    sector TEXT,
    entry_price DOUBLE,
    exit_price DOUBLE,
    gross_return DOUBLE,
    exit_reason TEXT,
    score_at_entry DOUBLE
);

CREATE TABLE IF NOT EXISTS model_runs (
    run_ts TIMESTAMP,
    model_name TEXT,
    train_rows BIGINT,
    auc DOUBLE,
    accuracy DOUBLE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS drift_reports (
    report_ts TIMESTAMP,
    feature_name TEXT,
    psi DOUBLE,
    status TEXT
);

CREATE TABLE IF NOT EXISTS edge_daily (
    asof_date DATE,
    symbol TEXT,
    finra_short_ratio DOUBLE,
    occ_open_interest BIGINT,
    edgar_dilution_flag BOOLEAN,
    PRIMARY KEY(asof_date, symbol)
);

CREATE TABLE IF NOT EXISTS paper_orders (
    order_id TEXT PRIMARY KEY,
    created_ts TIMESTAMP,
    status TEXT,
    symbol TEXT,
    contract_symbol TEXT,
    side TEXT,
    qty INTEGER,
    limit_price DOUBLE,
    fill_price DOUBLE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS paper_positions (
    position_id TEXT PRIMARY KEY,
    opened_ts TIMESTAMP,
    closed_ts TIMESTAMP,
    status TEXT,
    symbol TEXT,
    contract_symbol TEXT,
    expiration DATE,
    strike DOUBLE,
    "right" TEXT,
    qty INTEGER,
    market_cap BIGINT,
    sector TEXT,
    entry_price DOUBLE,
    current_price DOUBLE,
    exit_price DOUBLE,
    score_at_entry DOUBLE,
    tags TEXT,
    unrealized_return DOUBLE,
    realized_return DOUBLE,
    exit_reason TEXT
);

CREATE TABLE IF NOT EXISTS paper_fills (
    fill_id TEXT PRIMARY KEY,
    fill_ts TIMESTAMP,
    order_id TEXT,
    position_id TEXT,
    side TEXT,
    qty INTEGER,
    fill_price DOUBLE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS replay_runs (
    run_id TEXT PRIMARY KEY,
    created_ts TIMESTAMP,
    fixture_name TEXT,
    provider TEXT,
    signal_count BIGINT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS cohort_stats (
    cohort_key TEXT,
    cohort_value TEXT,
    trade_count BIGINT,
    win_rate DOUBLE,
    avg_return DOUBLE,
    median_return DOUBLE,
    avg_score DOUBLE,
    created_ts TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_events (
    event_ts TIMESTAMP,
    severity TEXT,
    component TEXT,
    message TEXT,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS calibration_runs (
    run_ts TIMESTAMP,
    source TEXT,
    trades_used BIGINT,
    entry_slippage_bps DOUBLE,
    exit_slippage_bps DOUBLE,
    recommended_thesis_break_score DOUBLE,
    recommended_take_profit_pct DOUBLE,
    recommended_stop_loss_pct DOUBLE,
    notes TEXT,
    report_json TEXT
);

CREATE TABLE IF NOT EXISTS provider_health (
    check_ts TIMESTAMP,
    provider TEXT,
    status TEXT,
    detail TEXT
);


CREATE TABLE IF NOT EXISTS execution_quality (
    run_ts TIMESTAMP,
    symbol TEXT,
    side TEXT,
    order_count BIGINT,
    mean_slippage_bps DOUBLE,
    median_slippage_bps DOUBLE
);


CREATE TABLE IF NOT EXISTS free_source_events (
    event_ts TIMESTAMP,
    source TEXT,
    symbol TEXT,
    event_key TEXT,
    event_value TEXT,
    payload_json TEXT
);
