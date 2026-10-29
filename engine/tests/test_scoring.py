from datetime import date
from nova.config import load_config
from nova.models import FeatureRow
from nova.engine.scoring import score_row, passes_contract_gates, normalize_weight_map, scoring_weight_sum


def _row():
    return FeatureRow(
        symbol="SOFI",
        contract_symbol="SOFI260619C00010000",
        expiration=date(2026, 6, 19),
        strike=10.0,
        right="call",
        bid=0.9,
        ask=1.0,
        mid=0.95,
        spread_pct=0.10,
        implied_vol=0.45,
        underlying_price=9.8,
        dte=45,
        delta=0.55,
        volume=1000,
        oi=3000,
        market_cap=6_000_000_000,
        sector="Financial Services",
        finra_short_ratio=0.52,
        insider_buy_flag=False,
        edgar_dilution_flag=False,
        momentum_20d=0.12,
        vix_value=20.0,
        m_sigma=0.15,
        technical_score=0.8,
    )


def test_weight_normalization_sums_to_one():
    weights = normalize_weight_map({"momentum": 2, "liquidity": 2})
    assert round(sum(weights.values()), 6) == 1.0
    assert weights["momentum"] > 0
    assert weights["liquidity"] > 0


def test_config_scoring_weight_sum_close_to_one():
    cfg = load_config()
    assert abs(scoring_weight_sum(cfg.scoring["weights"]) - 1.0) <= 0.05


def test_score_row():
    cfg = load_config()
    row = score_row(_row(), cfg)
    assert 0 <= row.score <= 100


def test_passes_contract_gates():
    cfg = load_config()
    row = score_row(_row(), cfg)
    row.score_lcb = 0.65
    row.sector_coherence = 0.75
    assert passes_contract_gates(row, cfg) is True
