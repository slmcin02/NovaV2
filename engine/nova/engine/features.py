from __future__ import annotations

from nova.config import AppConfig
from nova.models import ContractSnapshot, FeatureRow
from nova.utils.market import sigma_moneyness
from nova.engine.market_ops import assignment_risk_label
from nova.engine.signal_quality import estimate_float_turnover, hidden_liquidity_score, synth_flow_score, expected_slippage_bps


def build_feature_row(
    snap: ContractSnapshot,
    config: AppConfig,
    momentum_20d: float,
    finra_short_ratio: float,
    insider_buy_flag: bool,
    edgar_dilution_flag: bool,
    vix_value: float | None,
    sector_etf: str | None = None,
    sector_momentum_20d: float = 0.0,
    occ_open_interest: int = 0,
    sec_ftd_qty: int = 0,
    macro_regime_score: float = 0.5,
) -> FeatureRow:
    m_sigma = sigma_moneyness(
        snap.underlying_price,
        snap.strike,
        max(snap.implied_vol, 1e-6),
        max(snap.dte, 1) / 365.0,
    )
    technical_score = max(min((momentum_20d * 8.0) + 0.5, 1.0), 0.0)
    float_turnover = estimate_float_turnover(snap.underlying_price, snap.market_cap, snap.volume)
    hidden_liq = hidden_liquidity_score(snap.oi, snap.volume, snap.spread_pct, snap.delta)
    synth_score = synth_flow_score(finra_short_ratio, float_turnover, hidden_liq, technical_score)
    return FeatureRow(
        symbol=snap.symbol,
        contract_symbol=snap.contract_symbol,
        expiration=snap.expiration,
        strike=snap.strike,
        right=snap.right,
        bid=snap.bid,
        ask=snap.ask,
        mid=snap.mid,
        spread_pct=snap.spread_pct,
        implied_vol=snap.implied_vol,
        underlying_price=snap.underlying_price,
        dte=snap.dte,
        delta=snap.delta,
        volume=snap.volume,
        oi=snap.oi,
        market_cap=snap.market_cap,
        sector=snap.sector,
        finra_short_ratio=finra_short_ratio,
        occ_open_interest=occ_open_interest,
        sec_ftd_qty=sec_ftd_qty,
        macro_regime_score=macro_regime_score,
        insider_buy_flag=insider_buy_flag,
        edgar_dilution_flag=edgar_dilution_flag,
        momentum_20d=momentum_20d,
        vix_value=vix_value,
        m_sigma=m_sigma,
        technical_score=technical_score,
        sector_etf=sector_etf,
        sector_momentum_20d=sector_momentum_20d,
        float_turnover=float_turnover,
        hidden_liquidity_score=hidden_liq,
        synth_flow_score=synth_score,
        assignment_risk=assignment_risk_label(snap.delta, snap.dte, m_sigma),
        expected_slippage_bps=expected_slippage_bps(snap.spread_pct, hidden_liq, synth_score),
    )
