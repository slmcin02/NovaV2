from datetime import date
from nova.config import load_config
from nova.models import FeatureRow
from nova.engine.risk import quarter_kelly, position_risk_ok

def _row():
    return FeatureRow(
        symbol="SOFI",
        contract_symbol="X",
        expiration=date(2026, 6, 19),
        strike=10.0,
        right="call",
        bid=0.9,
        ask=1.0,
        mid=0.95,
        spread_pct=0.05,
        implied_vol=0.40,
        underlying_price=9.8,
        dte=45,
        delta=0.55,
        volume=1000,
        oi=3000,
        market_cap=6_000_000_000,
        sector="Financial Services",
        finra_short_ratio=0.50,
        insider_buy_flag=False,
        edgar_dilution_flag=False,
        momentum_20d=0.10,
        vix_value=18.0,
        m_sigma=0.1,
        technical_score=0.8,
        suggested_contracts=2,
    )

def test_quarter_kelly_non_negative():
    assert quarter_kelly(0.55, 1.5) >= 0

def test_position_risk_ok():
    cfg = load_config()
    assert position_risk_ok(_row(), cfg) is True
