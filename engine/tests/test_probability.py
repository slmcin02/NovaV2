from datetime import date

from nova.engine.probability import apply_probability_overlay
from nova.models import FeatureRow


def _row():
    return FeatureRow(
        symbol='PLTR', contract_symbol='X', expiration=date(2026,6,19), strike=45.0, right='call',
        bid=1.0, ask=1.1, mid=1.05, spread_pct=0.05, implied_vol=0.45, underlying_price=40.0,
        dte=60, delta=0.4, volume=500, oi=1200, market_cap=10_000_000_000, sector='Technology',
        finra_short_ratio=0.4, insider_buy_flag=False, edgar_dilution_flag=False, momentum_20d=0.12,
        vix_value=20.0, m_sigma=0.2, technical_score=0.8, score=78.0
    )


def test_probability_overlay_uses_bucket():
    report = {'score_buckets': [{'score_bucket': '75-79', 'trade_count': 20, 'win_rate': 0.7}]}
    row = apply_probability_overlay(_row(), report)
    assert row.calibrated_win_prob >= 0.5
    assert 0 <= row.score_lcb <= row.calibrated_win_prob
