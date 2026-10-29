from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
ET = ZoneInfo("America/New_York")


@dataclass(slots=True)
class SessionState:
    is_open: bool
    phase: str
    now_et: datetime


def get_session_state(now: datetime | None = None) -> SessionState:
    now = now or datetime.now(ET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET)
    t = now.timetz().replace(tzinfo=None)
    if t < time(8, 30):
        return SessionState(False, "premarket", now)
    if t < time(15, 0):
        return SessionState(True, "regular", now)
    if t < time(19, 0):
        return SessionState(False, "afterhours", now)
    return SessionState(False, "closed", now)


def hard_circuit_breaker_drop(pct_move: float) -> str | None:
    if pct_move <= -0.20:
        return "L3"
    if pct_move <= -0.13:
        return "L2"
    if pct_move <= -0.07:
        return "L1"
    return None
