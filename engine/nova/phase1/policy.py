"""NOVA calls-only Phase-1: pure, deterministic, paper-only decision policies.

Formulas: NOVA_calls_only_phase1_module_spec_formula_sheet.md sections 5-9.
This is NOT a live trading engine, a source-credibility oracle, or a return forecast.
Missing soft signals contribute neutral 0.5; missing hard quote fields veto.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite


def clamp01(value: object, neutral: float = 0.5) -> float:
    try:
        value = float(value)  # type: ignore[arg-type]
        if not isfinite(value):
            return neutral
        return max(0.0, min(1.0, value))
    except TypeError, ValueError:
        return neutral


def n(data: Mapping[str, object], name: str, default: float = 0.5) -> float:
    return clamp01(data.get(name), default)


def center_peak(value: float, low: float, mid: float, high: float) -> float:
    if not low < mid < high:
        raise ValueError("invalid_center_peak_band")
    if value <= low or value >= high:
        return 0.0
    if value <= mid:
        return clamp01((value - low) / (mid - low))
    return clamp01((high - value) / (high - mid))


def _float(value: object) -> float | None:
    try:
        v = float(value)  # type: ignore[arg-type]
        return v if isfinite(v) else None
    except TypeError, ValueError:
        return None


def _weighted(*parts: tuple[float, float]) -> float:
    return sum(weight * value for weight, value in parts)


def score_universal(features: Mapping[str, object]) -> dict[str, object]:
    def f(key: str) -> float:
        return n(features, key)

    buckets = {
        "flow_quality": _weighted(
            (0.55, f("flow_norm")),
            (0.25, f("flow_urgency_norm")),
            (0.20, f("dark_pool_norm")),
        ),
        "gamma_structure": _weighted(
            (0.45, f("gamma_structure_norm")),
            (0.30, f("gamma_slope_norm")),
            (0.25, f("gamma_proximity_norm")),
        ),
        "volatility_regime": _weighted(
            (0.45, f("vol_expansion_norm")),
            (0.35, 1 - f("iv_trap_risk_norm")),
            (0.20, f("regime_support_norm")),
        ),
        "technical_structure": _weighted(
            (0.60, f("momentum_structure_norm")),
            (0.20, f("divergence_support_norm")),
            (0.20, f("pattern_confirmation_norm")),
        ),
        "sector_macro": _weighted(
            (0.70, f("sector_coherence_norm")), (0.30, f("macro_regime_norm"))
        ),
        "accumulation_intel": _weighted(
            (0.35, f("dark_pool_norm")),
            (0.25, f("hidden_liquidity_norm")),
            (0.20, f("float_turnover_norm")),
            (0.20, f("insider_buy_norm")),
        ),
        "squeeze_intel": _weighted(
            (0.30, f("short_interest_norm")),
            (0.20, f("borrow_rate_norm")),
            (0.15, f("utilization_norm")),
            (0.20, f("ftd_threshold_norm")),
            (0.15, f("squeeze_flow_norm")),
        ),
        "distortion_risk": _weighted(
            (0.45, f("distortion_risk_norm")),
            (0.35, f("anomaly_risk_norm")),
            (0.20, f("premium_distortion_norm")),
        ),
    }
    value = 100 * _weighted(
        (0.24, buckets["flow_quality"]),
        (0.18, buckets["gamma_structure"]),
        (0.12, buckets["volatility_regime"]),
        (0.14, buckets["technical_structure"]),
        (0.10, buckets["sector_macro"]),
        (0.08, buckets["accumulation_intel"]),
        (0.08, buckets["squeeze_intel"]),
        (0.06, 1 - buckets["distortion_risk"]),
    )
    reasons = [
        name + "_low"
        for name, val in buckets.items()
        if name != "distortion_risk" and val < 0.35
    ]
    if buckets["distortion_risk"] >= 0.65:
        reasons.append("high_distortion_risk")
    return {
        "score": round(value, 4),
        "buckets": {k: round(v, 4) for k, v in buckets.items()},
        "reason_codes": reasons,
    }


def route_thesis(features: Mapping[str, object]) -> dict[str, object]:
    def f(key: str) -> float:
        return n(features, key)

    scores = {
        "momentum_continuation": _weighted(
            (0.32, f("momentum_structure_norm")),
            (0.22, f("flow_norm")),
            (0.18, f("sector_coherence_norm")),
            (0.16, 1 - f("iv_trap_risk_norm")),
            (0.12, f("gamma_structure_norm")),
        ),
        "gamma_squeeze": _weighted(
            (0.28, f("gamma_proximity_norm")),
            (0.24, f("gamma_slope_norm")),
            (0.18, f("call_flow_squeeze_norm")),
            (0.14, f("float_turnover_norm")),
            (0.08, f("short_interest_norm")),
            (0.08, 1 - f("dilution_risk_norm")),
        ),
        "short_squeeze": _weighted(
            (0.20, f("short_interest_norm")),
            (0.18, f("borrow_rate_norm")),
            (0.14, f("utilization_norm")),
            (0.14, f("ftd_threshold_norm")),
            (0.12, f("float_turnover_norm")),
            (0.12, f("call_flow_squeeze_norm")),
            (0.10, 1 - f("dilution_risk_norm")),
        ),
        "stealth_accumulation_breakout": _weighted(
            (0.24, f("dark_pool_norm")),
            (0.22, f("hidden_liquidity_norm")),
            (0.16, f("float_turnover_norm")),
            (0.14, f("sector_coherence_norm")),
            (0.14, f("flow_norm")),
            (0.10, f("momentum_structure_norm")),
        ),
        "insider_backed_accumulation": _weighted(
            (0.30, f("insider_buy_norm")),
            (0.22, f("dark_pool_norm")),
            (0.18, f("hidden_liquidity_norm")),
            (0.12, f("float_turnover_norm")),
            (0.10, f("sector_coherence_norm")),
            (0.08, 1 - f("dilution_risk_norm")),
        ),
        "volatility_expansion_continuation": _weighted(
            (0.30, f("vol_expansion_norm")),
            (0.24, 1 - f("iv_trap_risk_norm")),
            (0.18, f("momentum_structure_norm")),
            (0.14, f("flow_norm")),
            (0.14, f("gamma_structure_norm")),
        ),
    }
    ordered = sorted(scores, key=lambda name: (-scores[name], name))
    confidence = round(100 * scores[ordered[0]], 4)
    primary = ordered[0] if confidence >= 55 else "weak_undefined"
    secondary = (
        ordered[1]
        if primary != "weak_undefined"
        and 100 * (scores[ordered[0]] - scores[ordered[1]]) <= 8
        else None
    )
    return {
        "primary_thesis": primary,
        "secondary_thesis": secondary,
        "confidence": confidence,
        "scores": {k: round(100 * v, 4) for k, v in scores.items()},
        "reason_codes": ["primary_" + primary]
        + (["secondary_" + secondary] if secondary else []),
    }


_DTE_BANDS = {
    "momentum_continuation": (8, 15, 28),
    "gamma_squeeze": (8, 12, 21),
    "short_squeeze": (10, 18, 35),
    "stealth_accumulation_breakout": (14, 28, 42),
    "insider_backed_accumulation": (14, 28, 49),
    "volatility_expansion_continuation": (8, 15, 28),
}


def evaluate_contract(
    option: Mapping[str, object],
    features: Mapping[str, object],
    thesis: str,
    manual_override_flag: bool = False,
) -> dict[str, object]:
    """Conservative Stage-0 veto followed by exact section-7 blended ranking."""
    if thesis not in _DTE_BANDS:
        return {
            "status": "veto",
            "option_symbol": str(option.get("option_symbol", "")),
            "reason_codes": ["unsupported_thesis"],
        }
    symbol = str(option.get("option_symbol", ""))
    premium = _float(option.get("premium"))
    spread = _float(option.get("spread_pct_mid"))
    oi = _float(option.get("oi"))
    volume = _float(option.get("option_volume"))
    dte = _float(option.get("dte"))
    delta = _float(option.get("delta"))
    reasons = []
    if option.get("right") != "C":
        reasons.append("not_call")
    if premium is None or premium <= 0:
        reasons.append("invalid_premium")
    elif premium > 2.50 and manual_override_flag is not True:
        reasons.append("premium_over_cap")
    elif premium < 0.80:
        reasons.append("sub_080_exceptional_review_required")
    if option.get("quote_quality_flag") is not True:
        reasons.append("bad_quote")
    if spread is None or spread < 0:
        reasons.append("invalid_spread")
    elif spread > 0.20:
        reasons.append("wide_spread")
    if oi is None or oi < 500:
        reasons.append("thin_oi")
    if volume is None or volume < 100:
        reasons.append("thin_option_volume")
    if dte is None or dte < 8:
        reasons.append("too_low_dte")
    elif dte > 90:
        reasons.append("too_high_dte")
    if option.get("severe_dilution_event_flag") is True:
        reasons.append("severe_dilution_event")
    if option.get("severe_iv_trap_flag") is True:
        reasons.append("severe_iv_trap")
    if reasons:
        return {"status": "veto", "option_symbol": symbol, "reason_codes": reasons}

    assert premium is not None and spread is not None
    assert oi is not None and volume is not None and dte is not None
    oi_norm = clamp01(oi / (oi + 1500))
    volume_norm = clamp01(volume / (volume + 500))
    spread_norm = clamp01(spread / 0.20)
    quote_stability = n(features, "quote_stability_norm")
    exitability = _weighted(
        (0.35, oi_norm),
        (0.30, volume_norm),
        (0.20, 1 - spread_norm),
        (0.15, quote_stability),
    )
    runway = n(features, "dte_runway_norm", center_peak(dte, 8, 21, 60))
    survival = _weighted(
        (0.22, runway),
        (0.18, oi_norm),
        (0.16, volume_norm),
        (0.16, 1 - spread_norm),
        (0.14, 1 - n(features, "theta_friction_norm")),
        (0.08, 1 - n(features, "premium_distortion_norm")),
        (0.06, exitability),
    )
    premium_fit = center_peak(premium, 0.80, 1.45, 2.50)
    dte_fit = center_peak(dte, *_DTE_BANDS[thesis])
    delta_fit = 0.5 if delta is None else clamp01(1 - abs(delta - 0.45) / 0.25)
    strike_fit = _weighted(
        (0.65, delta_fit), (0.35, n(features, "gamma_proximity_norm"))
    )
    quality = 100 * _weighted(
        (0.22, survival),
        (0.18, premium_fit),
        (0.16, dte_fit),
        (0.14, strike_fit),
        (0.12, n(features, "gamma_relevance_norm")),
        (0.10, n(features, "flow_contract_alignment_norm")),
        (0.08, exitability),
    )
    monitor = []
    if 0.80 <= premium < 1.00:
        monitor.append("sub_1_bucket")
    if 500 <= oi < 1000:
        monitor.append("monitor_low_oi")
    if 100 <= volume < 300:
        monitor.append("monitor_low_volume")
    if 0.12 <= spread <= 0.20:
        monitor.append("monitor_wide_spread")
    if premium > 2.50:
        monitor.append("premium_manual_override")
    return {
        "status": "ok",
        "option_symbol": symbol,
        "reason_codes": monitor,
        "monitor_only": bool(set(monitor) - {"premium_manual_override"}),
        "manual_override_used": bool(premium > 2.50),
        "sub_1_bucket_flag": premium < 1.0,
        "contract_quality_score": round(quality, 4),
        "survival_composite_norm": round(survival, 5),
        "premium_fit_norm": round(premium_fit, 5),
        "dte_fit_norm": round(dte_fit, 5),
        "strike_posture_fit_norm": round(strike_fit, 5),
        "exitability_norm": round(exitability, 5),
    }


def decide_action(
    universal_base_score: float,
    primary_thesis_confidence: float,
    contract_eval: Mapping[str, object],
    regime_fit_norm: float = 0.5,
    event_alignment_norm: float = 0.5,
    veto_penalty_norm: float = 0.5,
) -> dict[str, object]:
    """A paper-enter *candidate* is a proposed simulated action only."""
    reasons = list(contract_eval.get("reason_codes", []))
    if contract_eval.get("status") != "ok":
        return {"action": "ignore", "action_score": 0.0, "reason_codes": reasons}
    quality = (
        clamp01(
            _float(contract_eval.get("contract_quality_score")) / 100
            if _float(contract_eval.get("contract_quality_score")) is not None
            else None
        )
        * 100
    )
    base = clamp01(universal_base_score / 100) * 100
    confidence = clamp01(primary_thesis_confidence / 100) * 100
    action_score = _weighted(
        (0.30, base),
        (0.25, confidence),
        (0.30, quality),
        (0.10, 100 * clamp01(regime_fit_norm)),
        (0.05, 100 * clamp01(event_alignment_norm)),
    ) * (1 - 0.35 * clamp01(veto_penalty_norm))
    if action_score < 60:
        action = "ignore"
    elif action_score < 75:
        action = "monitor"
    elif action_score < 85:
        action = "alert_only"
    else:
        action = "paper_enter"
    if contract_eval.get("sub_1_bucket_flag") and not (
        action_score >= 90
        and quality >= 85
        and float(contract_eval.get("survival_composite_norm", 0)) >= 0.72
    ):
        action = "alert_only" if action_score >= 75 else "monitor"
    # The monitor-only conditions are hard caps on action escalation.
    if contract_eval.get("monitor_only") and action == "paper_enter":
        monitor_reasons = set(contract_eval.get("reason_codes", []))
        exceptional_sub_one_only = (
            contract_eval.get("sub_1_bucket_flag") is True
            and monitor_reasons == {"sub_1_bucket"}
            and action_score >= 90
            and quality >= 85
            and float(contract_eval.get("survival_composite_norm", 0)) >= 0.72
        )
        if not exceptional_sub_one_only:
            action = "monitor"
    return {
        "action": action,
        "action_score": round(action_score, 4),
        "reason_codes": reasons,
        "urgent": bool(
            action == "paper_enter"
            and action_score >= 90
            and confidence >= 80
            and quality >= 80
            and not reasons
        ),
    }


def evaluate_setup(
    features: Mapping[str, object],
    options: Sequence[Mapping[str, object]],
    *,
    regime_fit_norm: float = 0.5,
    event_alignment_norm: float = 0.5,
    manual_override_flag: bool = False,
) -> dict[str, object]:
    base = score_universal(features)
    routed = route_thesis(features)
    thesis = str(routed["primary_thesis"])
    evaluations = [
        evaluate_contract(
            option, features, thesis, manual_override_flag=manual_override_flag
        )
        for option in options
    ]
    candidates = sorted(
        (v for v in evaluations if v["status"] == "ok"),
        key=lambda v: (-float(v["contract_quality_score"]), str(v["option_symbol"])),
    )
    selected = candidates[0] if candidates else None
    if selected is None or thesis == "weak_undefined":
        action = {
            "action": "ignore",
            "action_score": 0.0,
            "reason_codes": ["weak_or_no_valid_contract"],
        }
    else:
        action = decide_action(
            float(base["score"]),
            float(routed["confidence"]),
            selected,
            regime_fit_norm,
            event_alignment_norm,
            veto_penalty_norm=n(features, "veto_penalty_norm"),
        )
    reasons = [*base["reason_codes"], *routed["reason_codes"], *action["reason_codes"]]
    if selected is None:
        for e in evaluations:
            reasons.extend(e["reason_codes"])
    return {
        "mode": "offline_phase1_paper_policy",
        "universal_base_score": base["score"],
        "score_buckets": base["buckets"],
        "primary_thesis": thesis,
        "secondary_thesis": routed["secondary_thesis"],
        "primary_thesis_confidence": routed["confidence"],
        "thesis_scores": routed["scores"],
        "selected": selected,
        "alternatives": candidates[1:],
        "rejected": [e for e in evaluations if e["status"] == "veto"],
        "action": action["action"],
        "action_score": action["action_score"],
        "reason_codes": sorted({str(r) for r in reasons}),
        "has_live_order_authority": False,
    }


def score_post_entry(state: Mapping[str, object]) -> dict[str, object]:
    entry = _float(state.get("sci_at_entry"))
    current = _float(state.get("sci_current"))
    if entry is None or entry <= 0 or current is None:
        thesis_health = 0.5
    else:
        thesis_health = clamp01(current / entry)

    def flag(key: str) -> float:
        return 1.0 if state.get(key) is True else 0.0

    health = 100 * _weighted(
        (0.24, thesis_health),
        (0.20, n(state, "current_contract_health_norm")),
        (0.12, 1 - flag("flow_reversal_flag")),
        (0.10, 1 - flag("vol_crush_flag")),
        (0.10, 1 - flag("theta_fade_flag")),
        (0.08, 1 - flag("trailing_gamma_pivot_flag")),
        (0.08, 1 - n(state, "energy_score_decay_norm")),
        (0.08, 1 - flag("retail_flow_trap_flag")),
    )
    reasons = []
    if state.get("severe_dilution_event_flag") is True:
        reasons.append("hard_dilution_surprise")
    if state.get("quote_collapse_flag") is True:
        reasons.append("quote_collapse")
    if state.get("flow_reversal_flag") is True and state.get("vol_crush_flag") is True:
        reasons.append("flow_reversal_plus_vol_crush")
    if health < 35:
        reasons.append("health_below_35")
    broken = bool(reasons)
    status = (
        "thesis_broken"
        if broken or health < 45
        else "reduce"
        if health < 60
        else "caution"
        if health < 75
        else "healthy"
    )
    action = (
        "paper_exit_recommendation"
        if status == "thesis_broken"
        else "paper_reduce_recommendation"
        if status == "reduce"
        else "monitor"
        if status == "caution"
        else "hold"
    )
    return {
        "health_score": round(health, 4),
        "state": status,
        "action": action,
        "reason_codes": reasons,
        "has_live_order_authority": False,
    }
