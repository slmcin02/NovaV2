from __future__ import annotations

from datetime import UTC, datetime, date, timedelta
import pandas as pd

from nova.config import load_config
from nova.storage.duckdb_store import DuckDBStore
from nova.engine.score_optimizer import recommend_scoring_weights


def test_recommend_scoring_weights_has_robust_fields(tmp_path):
    cfg = load_config()
    cfg.raw['storage']['duckdb_path'] = str(tmp_path / 'opt.duckdb')
    store = DuckDBStore(cfg.storage['duckdb_path'])
    now = datetime.now(UTC).replace(tzinfo=None)
    signal_rows = []
    trade_rows = []
    for i in range(30):
        cs = f'PLTR260619C{10000+i:08d}'
        score = 55 + i * 0.8
        signal_rows.append({
            'signal_ts': now + timedelta(minutes=i), 'symbol': 'PLTR', 'contract_symbol': cs, 'expiration': date(2026,6,19), 'strike': 10.0+i*0.1,
            'right': 'call', 'bid': 1.0, 'ask': 1.1, 'mid': 1.05, 'spread_pct': 0.05, 'implied_vol': 0.45, 'underlying_price': 10.0,
            'dte': 45, 'delta': 0.4, 'volume': 500+i, 'oi': 1000+i*10, 'market_cap': 5000000000, 'sector': 'Technology',
            'finra_short_ratio': 0.4 + (i/100), 'occ_open_interest': 2000+i*20, 'sec_ftd_qty': i*1000, 'macro_regime_score': 0.5,
            'insider_buy_flag': False, 'edgar_dilution_flag': False, 'momentum_20d': 0.05 + i/500, 'vix_value': 20.0, 'm_sigma': 0.1,
            'technical_score': 0.6, 'sector_etf': 'XLK', 'sector_momentum_20d': 0.03, 'sector_coherence': 0.7, 'reflexivity_multiplier': 1.0,
            'spin_coherence': 0.8, 'spin_lock': False, 'float_turnover': 0.02, 'hidden_liquidity_score': 0.6, 'synth_flow_score': 0.5,
            'sci_velocity': 1.0, 'sci_acceleration': 0.2, 'failure_tag': 'stable', 'calibrated_win_prob': 0.6, 'score_lcb': 0.55,
            'event_risk': 'normal', 'assignment_risk': 'low', 'blocked_market_ops': False, 'expected_slippage_bps': 4.0,
            'score': score, 'elite': score >= 82, 'strategy_tags': 'trend', 'suggested_contracts': 1, 'payload_json': '{}',
        })
        trade_rows.append({
            'trade_id': f't{i}', 'entry_ts': now + timedelta(minutes=i), 'exit_ts': now + timedelta(minutes=i+10), 'symbol': 'PLTR', 'contract_symbol': cs,
            'expiration': date(2026,6,19), 'strike': 10.0+i*0.1, 'right': 'call', 'qty': 1, 'market_cap': 5000000000, 'sector': 'Technology',
            'entry_price': 1.05, 'exit_price': 1.15 if i > 5 else 0.95, 'gross_return': 0.09 if i > 5 else -0.09, 'exit_reason': 'tp', 'score_at_entry': score,
        })
    store.insert_dataframe('signals', pd.DataFrame(signal_rows))
    store.insert_dataframe('trades', pd.DataFrame(trade_rows))
    report = recommend_scoring_weights(store, cfg)
    assert report['status'] == 'ok'
    assert 'multicollinearity_penalty' in report
    assert 'rank_stability' in report
