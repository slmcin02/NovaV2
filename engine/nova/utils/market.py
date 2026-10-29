from __future__ import annotations

import math
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_ct() -> datetime:
    return utc_now().astimezone(CT)


def spread_pct(bid: float, ask: float) -> float:
    if ask <= 0:
        return 999.0
    return max(0.0, (ask - bid) / max(ask, 0.01))


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_call_delta(spot: float, strike: float, t_years: float, rate: float, sigma: float) -> float:
    if spot <= 0 or strike <= 0 or t_years <= 0 or sigma <= 0:
        return float("nan")
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * t_years) / (sigma * math.sqrt(t_years))
    return norm_cdf(d1)


def expected_move(spot: float, iv: float, t_years: float) -> float:
    if spot <= 0 or iv <= 0 or t_years <= 0:
        return 0.0
    return spot * iv * math.sqrt(t_years)


def sigma_moneyness(spot: float, strike: float, iv: float, t_years: float) -> float:
    em = expected_move(spot, iv, t_years)
    if em <= 0:
        return 999.0
    return (strike - spot) / em


def dte_from_expiration(expiration: date, today: date | None = None) -> int:
    today = today or now_ct().date()
    return (expiration - today).days


def market_cap_bucket(market_cap: int | None) -> str:
    if market_cap is None or market_cap <= 0:
        return "unknown"
    if market_cap < 2_000_000_000:
        return "small"
    if market_cap < 10_000_000_000:
        return "mid"
    return "large"
