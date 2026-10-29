from datetime import datetime
from zoneinfo import ZoneInfo

from nova.engine.market_ops import sector_etf_for, compute_sector_coherence, get_market_ops_state


def test_sector_map_returns_etf():
    assert sector_etf_for('Technology') == 'XLK'


def test_sector_coherence_bounds():
    c, m = compute_sector_coherence(0.10, 0.08, 18.0)
    assert 0 <= c <= 1
    assert m > 0


def test_market_ops_weekend_blocked():
    dt = datetime(2026, 3, 28, 14, 0, tzinfo=ZoneInfo('UTC'))
    state = get_market_ops_state(dt)
    assert state.is_trading_day is False
    assert state.can_open_new is False
