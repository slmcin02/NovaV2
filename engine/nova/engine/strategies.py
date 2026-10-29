from __future__ import annotations

from nova.models import FeatureRow


def strategy_tags(row: FeatureRow) -> list[str]:
    tags: list[str] = []
    if row.momentum_20d > 0.08:
        tags.append("momentum_breakout")
    if row.finra_short_ratio > 0.55:
        tags.append("short_pressure")
    if row.delta >= 0.55 and row.spread_pct <= 0.05:
        tags.append("liquid_delta")
    if -0.1 <= row.m_sigma <= 0.5:
        tags.append("near_atm")
    if row.implied_vol <= 0.55:
        tags.append("cheap_vol")
    if row.oi >= 2000:
        tags.append("positioning")
    if row.vix_value is not None and row.vix_value < 25:
        tags.append("risk_on")
    if row.technical_score > 0.7:
        tags.append("trend_confirmed")
    if row.edgar_dilution_flag:
        tags.append("dilution_risk")
    if row.insider_buy_flag:
        tags.append("insider_tailwind")
    return tags
