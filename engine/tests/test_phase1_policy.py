import pytest

from nova.phase1.policy import (
    decide_action,
    evaluate_contract,
    evaluate_setup,
    route_thesis,
    score_post_entry,
    score_universal,
)

GOOD_OPTION = {
    "option_symbol": "EXAMPLE260320C00025000",
    "right": "C",
    "premium": 1.45,
    "quote_quality_flag": True,
    "severe_dilution_event_flag": False,
    "severe_iv_trap_flag": False,
    "spread_pct_mid": 0.04,
    "oi": 2300,
    "option_volume": 850,
    "dte": 18,
    "delta": 0.45,
    "strike": 25.0,
}

# A fixture is not evidence of a successful real trade.
GOOD_FEATURES = {
    "flow_norm": 1,
    "flow_urgency_norm": 1,
    "dark_pool_norm": 1,
    "gamma_structure_norm": 1,
    "gamma_slope_norm": 1,
    "gamma_proximity_norm": 1,
    "vol_expansion_norm": 1,
    "iv_trap_risk_norm": 0,
    "regime_support_norm": 1,
    "momentum_structure_norm": 1,
    "divergence_support_norm": 1,
    "pattern_confirmation_norm": 1,
    "sector_coherence_norm": 1,
    "macro_regime_norm": 1,
    "hidden_liquidity_norm": 1,
    "float_turnover_norm": 1,
    "insider_buy_norm": 1,
    "short_interest_norm": 1,
    "borrow_rate_norm": 1,
    "utilization_norm": 1,
    "ftd_threshold_norm": 1,
    "squeeze_flow_norm": 1,
    "distortion_risk_norm": 0,
    "anomaly_risk_norm": 0,
    "premium_distortion_norm": 0,
    "call_flow_squeeze_norm": 1,
    "dilution_risk_norm": 0,
    "theta_friction_norm": 0,
    "quote_stability_norm": 1,
    "gamma_relevance_norm": 1,
    "flow_contract_alignment_norm": 1,
    "dte_runway_norm": 1,
}


def test_formula_universal_and_router_stay_bounded():
    s = score_universal(GOOD_FEATURES)
    assert s["score"] == pytest.approx(100)
    r = route_thesis(GOOD_FEATURES)
    assert r["primary_thesis"] in r["scores"]
    assert 55 <= r["confidence"] <= 100
    assert 0 <= min(r["scores"].values()) <= max(r["scores"].values()) <= 100


@pytest.mark.parametrize("override,expected", [(False, "veto"), (True, "ok")])
def test_premium_over_250_requires_manual_override(override, expected):
    item = dict(GOOD_OPTION, premium=2.51)
    assert (
        evaluate_contract(
            item, GOOD_FEATURES, "momentum_continuation", manual_override_flag=override
        )["status"]
        == expected
    )


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"right": "P"}, "not_call"),
        ({"quote_quality_flag": False}, "bad_quote"),
        ({"spread_pct_mid": 0.21}, "wide_spread"),
        ({"oi": 499}, "thin_oi"),
        ({"option_volume": 99}, "thin_option_volume"),
        ({"dte": 7}, "too_low_dte"),
        ({"severe_iv_trap_flag": True}, "severe_iv_trap"),
        ({"severe_dilution_event_flag": True}, "severe_dilution_event"),
    ],
)
def test_hard_veto_reasons(changes, reason):
    option = dict(GOOD_OPTION, **changes)
    result = evaluate_contract(option, GOOD_FEATURES, "momentum_continuation")
    assert result["status"] == "veto"
    assert reason in result["reason_codes"]


def test_soft_liquidity_monitor_cannot_paper_enter():
    option = dict(GOOD_OPTION, oi=550, option_volume=170, spread_pct_mid=0.13)
    result = evaluate_setup(
        GOOD_FEATURES, [option], regime_fit_norm=1, event_alignment_norm=1
    )
    assert result["action"] in ("ignore", "monitor", "alert_only")
    assert result["action"] != "paper_enter"


def test_under_one_dollar_needs_strict_policy():
    option = dict(GOOD_OPTION, premium=0.90)
    res = evaluate_contract(option, GOOD_FEATURES, "momentum_continuation")
    assert "sub_1_bucket" in res["reason_codes"]
    action = decide_action(100, 100, res, 1, 1)
    assert action["action"] != "paper_enter"


def test_missing_quote_data_fails_closed():
    option = dict(GOOD_OPTION)
    option.pop("quote_quality_flag")
    assert evaluate_contract(option, GOOD_FEATURES, "gamma_squeeze")["status"] == "veto"


def test_ranked_contracts_are_deterministic_and_explainable():
    better = dict(GOOD_OPTION, option_symbol="AAA", oi=2500)
    worse = dict(GOOD_OPTION, option_symbol="BBB", oi=1100)
    a = evaluate_setup(GOOD_FEATURES, [worse, better], regime_fit_norm=1)
    b = evaluate_setup(GOOD_FEATURES, [better, worse], regime_fit_norm=1)
    assert a["selected"]["option_symbol"] == b["selected"]["option_symbol"]
    assert len(a["alternatives"]) == 1
    assert a["primary_thesis"] in a["thesis_scores"]
    assert a["reason_codes"]


def test_hard_veto_always_prevents_action():
    result = evaluate_setup(GOOD_FEATURES, [dict(GOOD_OPTION, right="P")])
    assert result["action"] == "ignore"
    assert result["selected"] is None


def test_post_entry_emergency_exit_is_paper_only():
    p = score_post_entry(
        {
            "sci_at_entry": 90,
            "sci_current": 85,
            "flow_reversal_flag": True,
            "vol_crush_flag": True,
        }
    )
    assert p["state"] == "thesis_broken"
    assert p["action"] == "paper_exit_recommendation"
    assert "flow_reversal_plus_vol_crush" in p["reason_codes"]


@pytest.mark.parametrize("malformed", ["true", 1, {"approved": True}])
def test_manual_override_rejects_nonboolean_authorization(malformed):
    option = dict(GOOD_OPTION, premium=2.75)
    evaluation = evaluate_contract(
        option, GOOD_FEATURES, "momentum_continuation", manual_override_flag=malformed
    )
    assert evaluation["status"] == "veto"
    assert "premium_over_cap" in evaluation["reason_codes"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("premium", float("nan")),
        ("premium", float("inf")),
        ("spread_pct_mid", -0.01),
        ("option_volume", "not-a-number"),
        ("dte", 91),
        ("premium", -0.1),
    ],
)
def test_malformed_or_out_of_scope_quotes_fail_closed(key, value):
    evaluation = evaluate_contract(
        dict(GOOD_OPTION, **{key: value}), GOOD_FEATURES, "gamma_squeeze"
    )
    assert evaluation["status"] == "veto"


def test_missing_signals_cannot_produce_an_actionable_thesis():
    result = evaluate_setup(
        {}, [GOOD_OPTION], regime_fit_norm=1, event_alignment_norm=1
    )
    assert result["primary_thesis"] == "weak_undefined"
    assert result["action"] == "ignore"


def test_immediate_exit_triggers_override_good_health():
    for risk in ("severe_dilution_event_flag", "quote_collapse_flag"):
        result = score_post_entry(
            {
                "sci_at_entry": 90,
                "sci_current": 100,
                "current_contract_health_norm": 1,
                risk: True,
            }
        )
        assert result["state"] == "thesis_broken"
        assert result["action"] == "paper_exit_recommendation"


def test_sub_one_exceptional_quality_may_paper_enter_by_locked_formula():
    from nova.phase1.policy import decide_action

    contract = {
        "status": "ok",
        "contract_quality_score": 96,
        "survival_composite_norm": 0.91,
        "sub_1_bucket_flag": True,
        "monitor_only": True,
        "reason_codes": ["sub_1_bucket"],
    }
    result = decide_action(
        100,
        100,
        contract,
        regime_fit_norm=1,
        event_alignment_norm=1,
        veto_penalty_norm=0,
    )
    assert result["action"] == "paper_enter"


def test_sub_one_high_score_remains_monitor_if_liquidity_is_weak():
    from nova.phase1.policy import decide_action

    contract = {
        "status": "ok",
        "contract_quality_score": 96,
        "survival_composite_norm": 0.91,
        "sub_1_bucket_flag": True,
        "monitor_only": True,
        "reason_codes": ["sub_1_bucket", "monitor_low_oi"],
    }
    result = decide_action(
        100,
        100,
        contract,
        regime_fit_norm=1,
        event_alignment_norm=1,
        veto_penalty_norm=0,
    )
    assert result["action"] == "monitor"


@pytest.mark.parametrize("field", ["severe_dilution_event_flag", "severe_iv_trap_flag"])
@pytest.mark.parametrize("invalid", [None, 0, "false", []])
def test_missing_critical_event_evidence_fails_closed(field, invalid):
    option = dict(GOOD_OPTION)
    option[field] = invalid
    evaluation = evaluate_contract(option, GOOD_FEATURES, "gamma_squeeze")
    assert evaluation["status"] == "veto"
    assert f"{field}_unverified" in evaluation["reason_codes"]


@pytest.mark.parametrize("field", ["severe_dilution_event_flag", "severe_iv_trap_flag"])
def test_missing_critical_event_field_fails_closed(field):
    option = dict(GOOD_OPTION)
    del option[field]
    evaluation = evaluate_contract(option, GOOD_FEATURES, "gamma_squeeze")
    assert evaluation["status"] == "veto"
    assert f"{field}_unverified" in evaluation["reason_codes"]
