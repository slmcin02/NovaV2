from __future__ import annotations

from math import isfinite

from nova.config import AppConfig
from nova.models import FeatureRow


REQUIRED_WEIGHT_KEYS = (
    "momentum",
    "volatility_value",
    "liquidity",
    "positioning",
    "short_pressure",
    "insider",
    "technical",
    "dilution",
    "sector",
    "hidden_liquidity",
    "synth_flow",
    "spin",
)


def _clip01(x: float) -> float:
    if not isfinite(float(x)):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def normalize_weight_map(weight_map: dict[str, float]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key in REQUIRED_WEIGHT_KEYS:
        value = float(weight_map.get(key, 0.0) or 0.0)
        cleaned[key] = max(0.0, value)
    total = sum(cleaned.values())
    if total <= 0:
        base = 1.0 / len(REQUIRED_WEIGHT_KEYS)
        return {k: base for k in REQUIRED_WEIGHT_KEYS}
    return {k: v / total for k, v in cleaned.items()}


def scoring_weight_sum(weight_map: dict[str, float]) -> float:
    return round(sum(float(weight_map.get(k, 0.0) or 0.0) for k in REQUIRED_WEIGHT_KEYS), 6)


def score_components(row: FeatureRow, config: AppConfig) -> dict[str, float]:
    # Momentum: center around mild-to-strong positive trend without rewarding parabolic moves too much.
    momentum = _clip01((row.momentum_20d + 0.05) / 0.20)

    # Volatility value: prefer moderate IV for cheap long calls; too low can mean no movement, too high can mean overpaying.
    volatility_value = _clip01(1.0 - abs(row.implied_vol - 0.45) / 0.45)

    # Liquidity: combine spread, OI, and contract volume.
    spread_quality = _clip01(1.0 - (row.spread_pct / 0.10))
    oi_quality = _clip01(row.oi / 1500.0)
    volume_quality = _clip01(row.volume / 800.0)
    liquidity = _clip01(0.50 * spread_quality + 0.30 * oi_quality + 0.20 * volume_quality)

    # Positioning: prefer tradable deltas near the sweet spot instead of blindly preferring highest delta.
    delta_quality = _clip01(1.0 - abs(row.delta - 0.42) / 0.28)
    positioning = _clip01(0.60 * delta_quality + 0.40 * _clip01(row.oi / 2500.0))

    # Short pressure: combine FINRA daily short ratio, OCC open interest sponsorship, and SEC FTD stress.
    finra_component = _clip01(row.finra_short_ratio / 0.60)
    occ_component = _clip01(row.occ_open_interest / 8000.0)
    ftd_component = _clip01(row.sec_ftd_qty / 1_000_000.0)
    short_pressure = _clip01(0.55 * finra_component + 0.25 * occ_component + 0.20 * ftd_component)

    # Insider is neutral if disabled / unavailable, positive only when present.
    insider_enabled = bool(config.edges.get("insider_enabled", False))
    insider = 1.0 if row.insider_buy_flag else (0.50 if not insider_enabled else 0.35)

    technical = _clip01(row.technical_score)
    dilution = 0.0 if row.edgar_dilution_flag else 1.0
    sector = _clip01(row.sector_coherence)
    hidden = _clip01(row.hidden_liquidity_score)
    synth = _clip01(row.synth_flow_score)
    spin = _clip01(row.spin_coherence)

    return {
        "momentum": momentum,
        "volatility_value": volatility_value,
        "liquidity": liquidity,
        "positioning": positioning,
        "short_pressure": short_pressure,
        "insider": insider,
        "technical": technical,
        "dilution": dilution,
        "sector": sector,
        "hidden_liquidity": hidden,
        "synth_flow": synth,
        "spin": spin,
    }


def score_row(row: FeatureRow, config: AppConfig) -> FeatureRow:
    weights = normalize_weight_map(config.scoring["weights"])
    components = score_components(row, config)
    raw_score = 100.0 * sum(weights[k] * components[k] for k in REQUIRED_WEIGHT_KEYS)

    # Structural multipliers / penalties.
    raw_score *= row.reflexivity_multiplier
    # Macro regime can suppress otherwise decent signals during stressed conditions.
    raw_score *= (0.85 + (0.30 * _clip01(row.macro_regime_score)))
    if row.spin_lock:
        raw_score *= 0.82
    if row.failure_tag in {"fast_decay", "fading"}:
        raw_score *= 0.88
    elif row.failure_tag == "late_accel":
        raw_score *= 0.94

    if row.event_risk == "critical":
        raw_score *= 0.70
    elif row.event_risk == "high":
        raw_score *= 0.86
    elif row.event_risk == "blocked":
        raw_score *= 0.10

    if row.expected_slippage_bps >= 18:
        raw_score *= 0.90
    elif row.expected_slippage_bps >= 12:
        raw_score *= 0.95

    if row.assignment_risk == "high":
        raw_score *= 0.92
    elif row.assignment_risk == "moderate":
        raw_score *= 0.97

    row.score = round(max(0.0, min(100.0, raw_score)), 2)
    row.elite = bool(row.score >= float(config.scoring["elite_score"]))
    row.suggested_contracts = 2 if row.elite else 1
    return row


def passes_contract_gates(row: FeatureRow, config: AppConfig) -> bool:
    c = config.contracts
    if row.ask > float(c["max_ask"]) or row.ask < float(c["min_ask"]):
        return False
    if row.dte < int(c["min_dte"]) or row.dte > int(c["max_dte"]):
        return False
    if row.oi < int(c["min_oi"]):
        return False
    if row.spread_pct > float(c["max_spread_pct"]):
        return False
    if row.m_sigma < float(c["strike_sigma_min"]) or row.m_sigma > float(c["strike_sigma_max"]):
        return False
    if row.edgar_dilution_flag:
        return False
    if row.blocked_market_ops:
        return False
    if row.spin_lock and not row.elite:
        return False
    if row.score_lcb < float(config.scoring.get("min_score_lcb", 0.40)):
        return False
    if row.sector_coherence < float(config.scoring.get("min_sector_coherence", 0.20)):
        return False
    return True
