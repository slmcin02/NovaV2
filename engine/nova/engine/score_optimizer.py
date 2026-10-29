from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from nova.config import AppConfig
from nova.engine.scoring import REQUIRED_WEIGHT_KEYS, normalize_weight_map


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def build_component_frame(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["momentum"] = ((df["momentum_20d"].astype(float) + 0.05) / 0.20).clip(0.0, 1.0)
    out["volatility_value"] = (1.0 - (df["implied_vol"].astype(float) - 0.45).abs() / 0.45).clip(0.0, 1.0)
    spread_quality = (1.0 - (df["spread_pct"].astype(float) / 0.10)).clip(0.0, 1.0)
    oi_quality = (df["oi"].astype(float) / 1500.0).clip(0.0, 1.0)
    vol_quality = (df["volume"].astype(float) / 800.0).clip(0.0, 1.0)
    out["liquidity"] = (0.50 * spread_quality + 0.30 * oi_quality + 0.20 * vol_quality).clip(0.0, 1.0)
    delta_quality = (1.0 - (df["delta"].astype(float) - 0.42).abs() / 0.28).clip(0.0, 1.0)
    out["positioning"] = (0.60 * delta_quality + 0.40 * (df["oi"].astype(float) / 2500.0).clip(0.0, 1.0)).clip(0.0, 1.0)
    finra_component = (df["finra_short_ratio"].astype(float) / 0.60).clip(0.0, 1.0)
    occ_component = (df.get("occ_open_interest", 0).astype(float) / 8000.0).clip(0.0, 1.0)
    ftd_component = (df.get("sec_ftd_qty", 0).astype(float) / 1_000_000.0).clip(0.0, 1.0)
    out["short_pressure"] = (0.55 * finra_component + 0.25 * occ_component + 0.20 * ftd_component).clip(0.0, 1.0)
    insider_enabled = bool(config.edges.get("insider_enabled", False))
    insider_false = 0.50 if not insider_enabled else 0.35
    out["insider"] = df["insider_buy_flag"].fillna(False).map(lambda x: 1.0 if bool(x) else insider_false)
    out["technical"] = df["technical_score"].astype(float).clip(0.0, 1.0)
    out["dilution"] = 1.0 - df["edgar_dilution_flag"].fillna(False).astype(int)
    out["sector"] = df["sector_coherence"].astype(float).clip(0.0, 1.0)
    out["hidden_liquidity"] = df["hidden_liquidity_score"].astype(float).clip(0.0, 1.0)
    out["synth_flow"] = df["synth_flow_score"].astype(float).clip(0.0, 1.0)
    out["spin"] = df["spin_coherence"].astype(float).clip(0.0, 1.0)
    return out[list(REQUIRED_WEIGHT_KEYS)].fillna(0.0)


def recommend_scoring_weights(store, config: AppConfig, min_rows: int = 25) -> dict[str, Any]:
    signals = store.signal_rows(days=730)
    trades = store.completed_trades()
    current = normalize_weight_map(config.scoring.get("weights", {}))
    if signals.empty or trades.empty:
        return {
            "status": "insufficient_data",
            "rows_used": 0,
            "current_weights": current,
            "recommended_weights": current,
            "feature_strength": {},
            "multicollinearity_penalty": {},
            "rank_stability": 0.0,
        }

    s = signals.copy()
    t = trades.copy()
    s["signal_ts"] = pd.to_datetime(s["signal_ts"], errors="coerce")
    t["entry_ts"] = pd.to_datetime(t["entry_ts"], errors="coerce")
    t["win"] = (t["gross_return"].astype(float) > 0).astype(int)
    joined = s.merge(t[["contract_symbol", "entry_ts", "win", "gross_return"]], left_on=["contract_symbol", "signal_ts"], right_on=["contract_symbol", "entry_ts"], how="inner")
    if len(joined) < min_rows:
        return {
            "status": "insufficient_data",
            "rows_used": int(len(joined)),
            "current_weights": current,
            "recommended_weights": current,
            "feature_strength": {},
            "multicollinearity_penalty": {},
            "rank_stability": 0.0,
        }

    components = build_component_frame(joined, config)
    y_win = joined["win"].astype(float)
    y_ret = joined["gross_return"].astype(float).fillna(0.0)
    corr_matrix = components.corr().abs().fillna(0.0)
    strengths: dict[str, float] = {}
    penalties: dict[str, float] = {}
    for key in REQUIRED_WEIGHT_KEYS:
        series = components[key]
        win_corr = abs(float(series.corr(y_win))) if series.nunique(dropna=True) > 1 and y_win.nunique(dropna=True) > 1 else 0.0
        ret_corr = abs(float(series.corr(y_ret))) if series.nunique(dropna=True) > 1 and y_ret.nunique(dropna=True) > 1 else 0.0
        if pd.isna(win_corr):
            win_corr = 0.0
        if pd.isna(ret_corr):
            ret_corr = 0.0
        avg_corr = float(corr_matrix[key].drop(labels=[key], errors="ignore").mean()) if key in corr_matrix else 0.0
        penalty = max(0.40, 1.0 - max(0.0, avg_corr - 0.35))
        penalties[key] = round(penalty, 6)
        strengths[key] = round(max(0.01, ((0.60 * win_corr) + (0.40 * ret_corr)) * penalty), 6)

    empirical = normalize_weight_map(strengths)
    recommended = {k: round((0.65 * current[k]) + (0.35 * empirical[k]), 6) for k in REQUIRED_WEIGHT_KEYS}
    recommended = normalize_weight_map(recommended)

    ranked = joined.assign(current_score=s.get("score", pd.Series(index=joined.index, dtype=float)).fillna(0.0).astype(float))
    rank_stability = 0.0
    if len(ranked) >= 10:
        top = ranked.sort_values("current_score", ascending=False).head(max(5, len(ranked) // 5))["contract_symbol"]
        re_scored = (components[list(REQUIRED_WEIGHT_KEYS)] * pd.Series(recommended)).sum(axis=1)
        re_top = ranked.assign(rescore=re_scored).sort_values("rescore", ascending=False).head(max(5, len(ranked) // 5))["contract_symbol"]
        overlap = len(set(top).intersection(set(re_top)))
        rank_stability = round(overlap / max(1, len(set(top))), 4)

    return {
        "status": "ok",
        "rows_used": int(len(joined)),
        "current_weights": current,
        "recommended_weights": recommended,
        "empirical_weights": empirical,
        "feature_strength": strengths,
        "multicollinearity_penalty": penalties,
        "rank_stability": rank_stability,
        "win_rate": round(float(y_win.mean()), 4),
        "avg_return": round(float(y_ret.mean()), 6),
    }


def write_scoring_optimization_report(report: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
