from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
import math

CT = ZoneInfo("America/Chicago")

SECTOR_ETF_MAP = {
    "technology": "XLK",
    "software": "XLK",
    "semiconductor": "SMH",
    "communication": "XLC",
    "consumer discretionary": "XLY",
    "consumer cyclical": "XLY",
    "consumer defensive": "XLP",
    "financial": "XLF",
    "health": "XLV",
    "energy": "XLE",
    "industrial": "XLI",
    "materials": "XLB",
    "utilities": "XLU",
    "real estate": "XLRE",
}


def _easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    shift = (weekday - first.weekday()) % 7
    return first + timedelta(days=shift + (n - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    return {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),  # MLK
        _nth_weekday(year, 2, 0, 3),  # Presidents
        easter - timedelta(days=2),   # Good Friday
        _last_weekday(year, 5, 0),    # Memorial
        _observed(date(year, 6, 19)),
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),  # Labor
        _nth_weekday(year, 11, 3, 4), # Thanksgiving
        _observed(date(year, 12, 25)),
    }


def nyse_early_closes(year: int) -> set[date]:
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    out = {thanksgiving + timedelta(days=1)}
    july4 = date(year, 7, 4)
    if july4.weekday() in {5, 6}:
        # if holiday observed away from 7/3, then 7/3 often early close when weekday
        july3 = date(year, 7, 3)
        if july3.weekday() < 5:
            out.add(july3)
    elif date(year, 7, 3).weekday() < 5:
        out.add(date(year, 7, 3))
    christmas_eve = date(year, 12, 24)
    if christmas_eve.weekday() < 5:
        out.add(christmas_eve)
    return out


def third_friday(year: int, month: int) -> date:
    return _nth_weekday(year, month, 4, 3)


@dataclass(slots=True)
class MarketOpsState:
    now_ct: datetime
    is_trading_day: bool
    is_early_close: bool
    is_open: bool
    can_open_new: bool
    close_time_ct: datetime
    event_risk: str
    note: str


def get_market_ops_state(now: datetime | None = None) -> MarketOpsState:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    now_ct = now.astimezone(CT)
    holidays = nyse_holidays(now_ct.year)
    early = nyse_early_closes(now_ct.year)
    is_trading_day = now_ct.weekday() < 5 and now_ct.date() not in holidays
    close_hour, close_minute = (12, 0) if now_ct.date() in early else (15, 0)
    close_time = now_ct.replace(hour=close_hour, minute=close_minute, second=0, microsecond=0)
    open_time = now_ct.replace(hour=8, minute=30, second=0, microsecond=0)
    is_open = is_trading_day and open_time <= now_ct <= close_time
    can_open_new = is_open and now_ct <= (close_time - timedelta(minutes=5))
    event_risk = "normal"
    note = "regular"
    tf = third_friday(now_ct.year, now_ct.month)
    if now_ct.date() == tf:
        event_risk = "critical"
        note = "monthly_opex"
    elif abs((tf - now_ct.date()).days) <= 2:
        event_risk = "high"
        note = "opex_window"
    elif now_ct.date() in early:
        event_risk = "high"
        note = "early_close"
    elif not is_trading_day:
        event_risk = "blocked"
        note = "holiday_or_weekend"
    return MarketOpsState(
        now_ct=now_ct,
        is_trading_day=is_trading_day,
        is_early_close=now_ct.date() in early,
        is_open=is_open,
        can_open_new=can_open_new,
        close_time_ct=close_time,
        event_risk=event_risk,
        note=note,
    )


def sector_etf_for(sector: str | None) -> str | None:
    if not sector:
        return None
    text = sector.lower()
    for key, etf in SECTOR_ETF_MAP.items():
        if key in text:
            return etf
    return "SPY"


def compute_sector_coherence(stock_momentum: float, sector_momentum: float, vix_value: float | None) -> tuple[float, float]:
    same_sign = 1.0 if stock_momentum == 0 or sector_momentum == 0 or (stock_momentum > 0) == (sector_momentum > 0) else 0.0
    magnitude_gap = min(1.0, abs(stock_momentum - sector_momentum) / 0.20)
    raw = max(0.0, min(1.0, 0.65 * same_sign + 0.35 * (1.0 - magnitude_gap)))
    vol_penalty = 0.0
    if vix_value is not None and vix_value >= 28:
        vol_penalty = min(0.20, (float(vix_value) - 28.0) / 50.0)
    coherence = max(0.0, min(1.0, raw - vol_penalty))
    if coherence >= 0.65:
        mult = 1.0 + (coherence - 0.65) * 0.35
    else:
        mult = 0.70 + coherence * 0.35
    return round(coherence, 4), round(mult, 4)


def assignment_risk_label(delta: float, dte: int, m_sigma: float) -> str:
    # for long calls this is really early-exercise sensitivity, not assignment.
    if dte <= 3 and delta >= 0.80 and abs(m_sigma) <= 0.20:
        return "high"
    if dte <= 7 and delta >= 0.70:
        return "moderate"
    return "low"
