from __future__ import annotations

from math import sqrt
from statistics import mean


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def estimate_float_turnover(underlying_price: float, market_cap: int | None, option_volume: int) -> float:
    if not market_cap or not underlying_price or underlying_price <= 0:
        return 0.0
    estimated_float_shares = (float(market_cap) / float(underlying_price)) * 0.65
    if estimated_float_shares <= 0:
        return 0.0
    underlying_equiv = max(option_volume, 0) * 100.0
    return round(underlying_equiv / estimated_float_shares, 6)


def hidden_liquidity_score(oi: int, volume: int, spread_pct: float, delta: float) -> float:
    oi_component = _clip01((oi / max(volume, 1)) / 18.0)
    spread_component = _clip01(1.0 - (spread_pct / 0.10))
    delta_component = 1.0 - min(1.0, abs(delta - 0.40) / 0.45)
    return round(_clip01(0.45 * oi_component + 0.35 * spread_component + 0.20 * delta_component), 4)


def synth_flow_score(finra_short_ratio: float, float_turnover: float, hidden_liq: float, technical_score: float) -> float:
    short_component = _clip01(finra_short_ratio / 0.65)
    turnover_component = _clip01(float_turnover / 0.05)
    return round(_clip01(0.35 * short_component + 0.30 * turnover_component + 0.20 * hidden_liq + 0.15 * technical_score), 4)


def spin_coherence(momentum_20d: float, technical_score: float, sector_coherence: float, vix_value: float | None) -> tuple[float, bool]:
    momentum_component = _clip01((momentum_20d + 0.08) / 0.20)
    vol_regime = 1.0
    if vix_value is not None:
        vol_regime = _clip01(1.0 - ((float(vix_value) - 18.0) / 20.0))
    score = _clip01(0.40 * momentum_component + 0.30 * technical_score + 0.20 * sector_coherence + 0.10 * vol_regime)
    return round(score, 4), bool(score < 0.30)


def score_dynamics(prior_scores: list[float], current_score: float) -> tuple[float, float, str]:
    if not prior_scores:
        return 0.0, 0.0, "new_signal"
    velocity = current_score - prior_scores[-1]
    acceleration = 0.0
    if len(prior_scores) >= 2:
        acceleration = velocity - (prior_scores[-1] - prior_scores[-2])
    tag = "stable"
    if velocity >= 8:
        tag = "ignition"
    elif velocity <= -8:
        tag = "fast_decay"
    elif velocity < 0 and mean(prior_scores[-min(len(prior_scores),3):]) > current_score:
        tag = "fading"
    elif velocity > 0 and acceleration < -2:
        tag = "late_accel"
    return round(velocity, 2), round(acceleration, 2), tag


def expected_slippage_bps(spread_pct: float, hidden_liq: float, synth_score: float) -> float:
    bps = 4.0 + max(0.0, spread_pct * 120.0)
    bps += max(0.0, (0.5 - hidden_liq) * 10.0)
    bps -= min(4.0, synth_score * 2.5)
    return round(max(2.0, bps), 2)
