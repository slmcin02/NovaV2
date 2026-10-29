from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any


@dataclass(slots=True)
class ContractSnapshot:
    symbol: str
    contract_symbol: str
    expiration: date
    strike: float
    right: str
    bid: float
    ask: float
    mid: float
    spread_pct: float
    implied_vol: float
    underlying_price: float
    dte: int
    delta: float
    volume: int
    oi: int
    market_cap: int | None = None
    sector: str | None = None
    provider: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FeatureRow:
    symbol: str
    contract_symbol: str
    expiration: date
    strike: float
    right: str
    bid: float
    ask: float
    mid: float
    spread_pct: float
    implied_vol: float
    underlying_price: float
    dte: int
    delta: float
    volume: int
    oi: int
    market_cap: int | None
    sector: str | None
    finra_short_ratio: float
    insider_buy_flag: bool
    edgar_dilution_flag: bool
    momentum_20d: float
    vix_value: float | None
    m_sigma: float
    technical_score: float
    occ_open_interest: int = 0
    sec_ftd_qty: int = 0
    macro_regime_score: float = 0.5
    score: float = 0.0
    elite: bool = False
    strategy_tags: str = ""
    suggested_contracts: int = 1
    sector_etf: str | None = None
    sector_momentum_20d: float = 0.0
    sector_coherence: float = 0.5
    reflexivity_multiplier: float = 1.0
    spin_coherence: float = 0.5
    spin_lock: bool = False
    float_turnover: float = 0.0
    hidden_liquidity_score: float = 0.0
    synth_flow_score: float = 0.0
    sci_velocity: float = 0.0
    sci_acceleration: float = 0.0
    failure_tag: str = ""
    calibrated_win_prob: float = 0.5
    score_lcb: float = 0.5
    event_risk: str = "normal"
    assignment_risk: str = "low"
    blocked_market_ops: bool = False
    expected_slippage_bps: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
