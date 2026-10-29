from __future__ import annotations

import json
from math import sqrt
from pathlib import Path
from typing import Any

from nova.models import FeatureRow


def load_calibration_report(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _bucket(score: float) -> str:
    floor = int(score // 5 * 5)
    return f"{floor:02d}-{floor+4:02d}"


def _wilson_lower_bound(p: float, n: int, z: float = 1.28) -> float:
    if n <= 0:
        return max(0.0, p - 0.12)
    denom = 1 + z*z/n
    centre = p + z*z/(2*n)
    spread = z * sqrt((p*(1-p) + z*z/(4*n)) / n)
    return max(0.0, (centre - spread) / denom)


def apply_probability_overlay(row: FeatureRow, report: dict[str, Any], prior_prob: float = 0.50) -> FeatureRow:
    buckets = report.get('score_buckets') or []
    if not buckets:
        row.calibrated_win_prob = round(max(0.05, min(0.95, row.score / 100.0)), 4)
        row.score_lcb = round(max(0.01, row.calibrated_win_prob - 0.08), 4)
        return row
    key = _bucket(row.score)
    match = next((b for b in buckets if b.get('score_bucket') == key), None)
    if not match:
        row.calibrated_win_prob = round(max(0.05, min(0.95, row.score / 100.0)), 4)
        row.score_lcb = round(max(0.01, row.calibrated_win_prob - 0.10), 4)
        return row
    n = int(match.get('trade_count') or 0)
    empirical = float(match.get('win_rate') or prior_prob)
    shrunk = ((n * empirical) + (12 * prior_prob)) / max(1, n + 12)
    row.calibrated_win_prob = round(max(0.05, min(0.95, shrunk)), 4)
    row.score_lcb = round(_wilson_lower_bound(row.calibrated_win_prob, max(1, n + 12)), 4)
    return row
