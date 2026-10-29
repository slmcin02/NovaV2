from __future__ import annotations

from collections import Counter

from nova.config import AppConfig
from nova.models import FeatureRow


def quarter_kelly(prob_win: float, payoff_multiple: float) -> float:
    if payoff_multiple <= 0:
        return 0.0
    return max(0.0, (((prob_win * (payoff_multiple + 1.0)) - 1.0) / payoff_multiple) * 0.25)


def dynamic_contracts(row: FeatureRow, config: AppConfig) -> int:
    prob = max(0.05, min(0.95, row.score_lcb if row.score_lcb else row.calibrated_win_prob))
    edge = quarter_kelly(prob_win=prob, payoff_multiple=float(config.risk.get('assumed_payoff_multiple', 1.5)))
    base = 2 if row.elite else 1
    if row.spin_lock or row.event_risk in {'critical', 'high'}:
        return 1
    if edge >= 0.08 and row.ask * 100.0 * base * 2 <= float(config.risk['max_position_risk_usd']):
        return min(3, base + 1)
    return base


def position_risk_ok(row: FeatureRow, config: AppConfig) -> bool:
    max_risk = float(config.risk["max_position_risk_usd"])
    return (row.ask * 100.0 * row.suggested_contracts) <= max_risk


def sector_exposure_ok(new_row: FeatureRow, open_rows: list[FeatureRow], config: AppConfig) -> bool:
    max_sector = float(config.risk["max_sector_exposure"])
    if not new_row.sector:
        return True
    sectors = [r.sector for r in open_rows if r.sector] + [new_row.sector]
    counts = Counter(sectors)
    total = sum(counts.values())
    return total == 0 or (counts[new_row.sector] / total) <= max_sector
