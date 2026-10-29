# NOVA Calls-Only Phase 1
Module Spec and Formula Implementation Sheet

## Exact Fields, Datatypes, Normalization Rules, and Pseudocode

## 1. Scope and Design Goals

This document turns the phase-1 scoring blueprint into a build-facing specification.
It is the implementation layer for a laptop-only, calls-only, paper-trading and alerting system.

Locked scope:
- Calls only
- Laptop only
- Paper / alerts / logs / replay only
- No autonomous live trading
- Contract-level premium focus
- Premium over $2.50 is outside standard phase-1 behavior unless manually overridden

Design goals:
- Separate thesis quality from contract quality
- Use hard gates before blended ranking
- Make outputs auditable and replayable
- Keep score paths deterministic and explainable
- Support later calibration without rewriting feature contracts

## 2. Global Conventions

Naming conventions:
- snake_case for all fields
- *_raw = unnormalized value
- *_norm = normalized value on [0, 1]
- *_score = blended score on [0, 100]
- *_flag = boolean condition
- *_reason_codes = list[str] of top drivers

Datatype conventions:
- str for categorical/string identifiers
- int for counts
- float for continuous numeric values
- bool for flags
- datetime for timestamps
- date for trading date partitions
- Optional[T] where a value may be missing
- list[str] for reason code bundles

Normalization conventions:
- Prefer monotonic bounded transforms
- Clamp all normalized values to [0.0, 1.0]
- Missing values default to neutral or thesis-inapplicable, not silently bullish
- Hard veto conditions override blended score

## 3. Normalization Rules

Core helper functions:

1. clamp01(x):
   return min(1.0, max(0.0, x))

2. linear_band(value, low, high):
   maps low -> 0.0, high -> 1.0, linearly
   clamp outside range

3. reverse_band(value, low, high):
   maps low -> 1.0, high -> 0.0, linearly
   useful for spread, distortion, friction, event risk

4. center_peak(value, low, mid, high):
   triangular score where mid is best and low/high are worst
   used for premium sweet spots or DTE sweet spots

5. logistic_like(value, mid, scale):
   soft saturation around mid
   useful where extreme raw values should not dominate

6. capped_ratio(numerator, denominator, max_ratio):
   returns clamp01((numerator / max(denominator, eps)) / max_ratio)

7. safe_pct_change(curr, prev):
   if prev <= 0: return 0.0
   else return (curr - prev) / prev

8. missing_to_neutral(x, neutral=0.5):
   return neutral if x is None else x

Normalization policy by feature family:
- Flow urgency / scale: saturating positive transform
- Spread / distortion / event risk: reverse transform
- OI and option volume: positive saturating transform
- Premium sweet spot: center-peak transform
- DTE fit: center-peak per thesis
- Theta friction: reverse transform
- Gamma relevance: positive saturating transform
- Corporate-action risk: veto or reverse transform, depending on severity

## 4. Exact Field Schemas

underlying_snapshot
- as_of_ts: datetime - Snapshot timestamp
- trade_date: date - Trading date partition
- symbol: str - Underlying ticker
- spot_price: float - Underlying last/mark price
- day_volume_shares: int - Underlying day share volume
- avg_volume_20d_shares: int - 20-day avg share volume
- atr_14: float - ATR for structural stop/target logic
- rv_20: float - 20-day realized volatility
- iv_regime_raw: float - Underlying/implied vol regime proxy
- sector_etf: str - Mapped sector benchmark
- sector_return_1d: float - Sector 1-day return
- sector_return_5d: float - Sector 5-day return
- earnings_date: Optional[date] - Upcoming earnings date if known
- event_risk_flag: bool - True if earnings or comparable catalyst window
- dilution_risk_flag: bool - Offering/shelf/ATM risk present
- buyback_signal_flag: bool - Buyback/repurchase supportive flag
- insider_buy_signal_flag: bool - Form 3/4/5 buy support flag
- short_interest_pct_float: Optional[float] - Short interest as pct float
- borrow_rate_ctb: Optional[float] - Cost to borrow estimate
- utilization_pct: Optional[float] - Utilization percent
- ftd_signal_flag: bool - Failure-to-deliver stress/support flag
- threshold_list_flag: bool - Reg SHO threshold list flag
- dark_pool_accumulation_raw: Optional[float] - Dark pool accumulation signal
- hidden_liquidity_raw: Optional[float] - Hidden liquidity heuristic
- float_turnover_raw: Optional[float] - Float turnover heuristic

option_snapshot
- as_of_ts: datetime - Snapshot timestamp
- symbol: str - Underlying ticker
- option_symbol: str - Canonical option identifier
- expiry: date - Expiration date
- dte: int - Days to expiration
- strike: float - Strike price
- right: str - Always 'C' in phase 1
- bid: float - Best bid
- ask: float - Best ask
- mid: float - Midpoint
- last: Optional[float] - Last trade price
- premium: float - Contract premium; primary price field
- spread_abs: float - ask - bid
- spread_pct_mid: float - Spread divided by mid
- oi: int - Open interest
- option_volume: int - Day option volume
- iv: float - Implied volatility
- delta: float - Option delta
- gamma: float - Option gamma
- theta: float - Option theta
- vega: float - Option vega
- gex_relevance_raw: Optional[float] - Gamma/GEX relevance for this strike
- gamma_wall_distance_pct: Optional[float] - Pct distance to nearest gamma wall
- gamma_flip_distance_pct: Optional[float] - Pct distance to flip level
- premium_distortion_raw: Optional[float] - Premium distortion metric
- quote_quality_flag: bool - False if quote stale/suspect

signal_features
- symbol: str - Underlying ticker
- as_of_ts: datetime - Feature timestamp
- flow_raw: Optional[float] - Base unusual options flow metric
- flow_urgency_raw: Optional[float] - Urgency-weighted flow metric
- call_sweep_count: Optional[int] - Call sweeps count
- dark_pool_raw: Optional[float] - Dark pool accumulation metric
- gamma_structure_raw: Optional[float] - Gamma structure summary
- gamma_slope_raw: Optional[float] - GEX slope/dealer positioning metric
- iv_trap_risk_raw: Optional[float] - IV trap severity
- theta_sink_risk_raw: Optional[float] - Theta sink severity
- divergence_raw: Optional[float] - Price/flow/sector divergence metric
- sector_coherence_raw: Optional[float] - Sector confirmation metric
- momentum_structure_raw: Optional[float] - Breakout/continuation structure metric
- distortion_risk_raw: Optional[float] - Reflexivity/distortion severity
- anomaly_risk_raw: Optional[float] - Anomaly/spoof severity
- short_squeeze_raw: Optional[float] - Squeeze-pressure composite
- accumulation_raw: Optional[float] - Accumulation composite
- vol_expansion_raw: Optional[float] - Volatility expansion composite

position_state
- position_id: str - Paper position identifier
- option_symbol: str - Tracked option
- entry_ts: datetime - Paper entry time
- entry_premium: float - Entry premium
- max_premium_seen: float - Best premium after entry
- min_premium_seen: float - Worst premium after entry
- bars_held: int - Bars since entry
- sci_at_entry: float - SCI at entry
- sci_current: float - Current SCI
- theta_fade_flag: bool - Post-entry theta fade condition
- vol_crush_flag: bool - Post-entry vol crush condition
- flow_reversal_flag: bool - Post-entry flow reversal condition
- retail_flow_trap_flag: bool - Trap condition
- energy_score_decay_raw: Optional[float] - Energy/phase decay metric
- trailing_gamma_pivot_flag: bool - Gamma pivot support lost

## 5. Universal Base Score Formula

Universal Base Score buckets (before thesis-specific routing):
- flow_quality_bucket: 24%
- gamma_structure_bucket: 18%
- volatility_regime_bucket: 12%
- technical_structure_bucket: 14%
- sector_macro_bucket: 10%
- accumulation_intel_bucket: 8%
- squeeze_intel_bucket: 8%
- distortion_risk_bucket: 6% negative bucket

Bucket formulas:
1. flow_quality_bucket =
   0.55 * flow_norm +
   0.25 * flow_urgency_norm +
   0.20 * dark_pool_norm

2. gamma_structure_bucket =
   0.45 * gamma_structure_norm +
   0.30 * gamma_slope_norm +
   0.25 * gamma_proximity_norm

3. volatility_regime_bucket =
   0.45 * vol_expansion_norm +
   0.35 * (1 - iv_trap_risk_norm) +
   0.20 * regime_support_norm

4. technical_structure_bucket =
   0.60 * momentum_structure_norm +
   0.20 * divergence_support_norm +
   0.20 * pattern_confirmation_norm

5. sector_macro_bucket =
   0.70 * sector_coherence_norm +
   0.30 * macro_regime_norm

6. accumulation_intel_bucket =
   0.35 * dark_pool_norm +
   0.25 * hidden_liquidity_norm +
   0.20 * float_turnover_norm +
   0.20 * insider_buy_norm

7. squeeze_intel_bucket =
   0.30 * short_interest_norm +
   0.20 * borrow_rate_norm +
   0.15 * utilization_norm +
   0.20 * ftd_threshold_norm +
   0.15 * squeeze_flow_norm

8. distortion_risk_bucket =
   0.45 * distortion_risk_norm +
   0.35 * anomaly_risk_norm +
   0.20 * premium_distortion_norm

Universal Base Score =
  100 * (
      0.24*flow_quality_bucket +
      0.18*gamma_structure_bucket +
      0.12*volatility_regime_bucket +
      0.14*technical_structure_bucket +
      0.10*sector_macro_bucket +
      0.08*accumulation_intel_bucket +
      0.08*squeeze_intel_bucket +
      0.06*(1 - distortion_risk_bucket)
  )

## 6. Thesis Router Formula Sheet

Primary thesis classes:
- momentum_continuation
- gamma_squeeze
- short_squeeze
- stealth_accumulation_breakout
- insider_backed_accumulation
- volatility_expansion_continuation

Router output fields:
- primary_thesis: str
- secondary_thesis: Optional[str]
- primary_thesis_confidence: float [0,100]
- thesis_reason_codes: list[str]

Recommended router method for phase 1:
- deterministic weighted routing first
- optional calibrated classifier later

Deterministic thesis scores:

momentum_continuation_score =
  100 * (
    0.32*momentum_structure_norm +
    0.22*flow_norm +
    0.18*sector_coherence_norm +
    0.16*(1 - iv_trap_risk_norm) +
    0.12*gamma_structure_norm
  )

gamma_squeeze_score =
  100 * (
    0.28*gamma_proximity_norm +
    0.24*gamma_slope_norm +
    0.18*call_flow_squeeze_norm +
    0.14*float_turnover_norm +
    0.08*short_interest_norm +
    0.08*(1 - dilution_risk_norm)
  )

short_squeeze_score =
  100 * (
    0.20*short_interest_norm +
    0.18*borrow_rate_norm +
    0.14*utilization_norm +
    0.14*ftd_threshold_norm +
    0.12*float_turnover_norm +
    0.12*call_flow_squeeze_norm +
    0.10*(1 - dilution_risk_norm)
  )

stealth_accumulation_breakout_score =
  100 * (
    0.24*dark_pool_norm +
    0.22*hidden_liquidity_norm +
    0.16*float_turnover_norm +
    0.14*sector_coherence_norm +
    0.14*flow_norm +
    0.10*momentum_structure_norm
  )

insider_backed_accumulation_score =
  100 * (
    0.30*insider_buy_norm +
    0.22*dark_pool_norm +
    0.18*hidden_liquidity_norm +
    0.12*float_turnover_norm +
    0.10*sector_coherence_norm +
    0.08*(1 - dilution_risk_norm)
  )

volatility_expansion_continuation_score =
  100 * (
    0.30*vol_expansion_norm +
    0.24*(1 - iv_trap_risk_norm) +
    0.18*momentum_structure_norm +
    0.14*flow_norm +
    0.14*gamma_structure_norm
  )

Selection rule:
- primary_thesis = argmax(thesis_scores)
- secondary_thesis = 2nd highest only if within 8 points of primary
- if primary score < 55, do not route to actionable thesis; mark setup as weak/undefined

## 7. Contract Selector Formula Sheet

Stage 0: hard veto / monitor-only checks
Veto if any:
- right != "C"
- premium > 2.50 and not manual_override_flag
- quote_quality_flag == False
- spread_pct_mid > 0.20
- oi < 500
- option_volume < 100
- dte < 8
- severe_dilution_event_flag == True
- severe_iv_trap_flag == True

Monitor-only candidate if:
- 0.80 <= premium < 1.00
- oi between 500 and 999
- option_volume between 100 and 299
- spread_pct_mid between 0.12 and 0.20

Stage 1: thesis-fit transforms

premium_fit_norm:
- Use center_peak
- standard phase-1 center band:
  low=0.80, mid=1.45, high=2.50
- for sub_1_bucket, require stricter action threshold later

dte_fit_norm:
- momentum_continuation: center_peak(dte, 8, 15, 28)
- gamma_squeeze: center_peak(dte, 8, 12, 21)
- short_squeeze: center_peak(dte, 10, 18, 35)
- stealth_accumulation_breakout: center_peak(dte, 14, 28, 42)
- insider_backed_accumulation: center_peak(dte, 14, 28, 49)
- volatility_expansion_continuation: center_peak(dte, 8, 15, 28)

strike_posture_fit_norm:
- gamma / short squeeze: prefer slightly OTM to ATM
- accumulation / continuation: prefer slightly OTM if gamma support good
- compute from delta and gamma proximity:
    if delta in [0.35, 0.60] and gamma proximity strong -> high
    if delta too low or too deep ITM -> penalize

survival_composite_norm =
  0.22*dte_runway_norm +
  0.18*oi_norm +
  0.16*option_volume_norm +
  0.16*(1 - spread_pct_norm) +
  0.14*(1 - theta_friction_norm) +
  0.08*(1 - premium_distortion_norm) +
  0.06*exitability_norm

contract_quality_score =
  100 * (
    0.22*survival_composite_norm +
    0.18*premium_fit_norm +
    0.16*dte_fit_norm +
    0.14*strike_posture_fit_norm +
    0.12*gamma_relevance_norm +
    0.10*flow_contract_alignment_norm +
    0.08*exitability_norm
  )

exitability_norm =
  0.35*oi_norm +
  0.30*option_volume_norm +
  0.20*(1 - spread_pct_norm) +
  0.15*quote_stability_norm

## 8. Action Policy Formula Sheet

Action score purpose:
- separate "good setup" from "take action now"

Inputs:
- universal_base_score
- primary_thesis_confidence
- contract_quality_score
- regime_fit_norm
- veto_penalty_norm
- event_alignment_norm

Formula:
action_score =
  (
    0.30*universal_base_score +
    0.25*primary_thesis_confidence +
    0.30*contract_quality_score +
    0.10*(100*regime_fit_norm) +
    0.05*(100*event_alignment_norm)
  ) * (1 - 0.35*veto_penalty_norm)

Phase-1 action policy:
- action_score < 60 -> ignore
- 60 to <75 -> monitor
- 75 to <85 -> alert only
- >=85 -> paper-enter candidate
- if premium < 1.00:
    require action_score >= 90
    require contract_quality_score >= 85
    require survival_composite_norm >= 0.72

Urgent alert policy:
- action_score >= 90
- primary_thesis_confidence >= 80
- contract_quality_score >= 80
- no hard or soft veto triggered

## 9. Post-Entry Health and Exit Rules

Post-entry health score purpose:
- hold / caution / reduce / thesis broken state machine

Inputs:
- current_thesis_health_norm
- current_contract_health_norm
- flow_reversal_risk_norm
- vol_crush_risk_norm
- theta_fade_risk_norm
- gamma_support_loss_norm
- energy_score_decay_norm
- retail_flow_trap_norm

Formula:
post_entry_health_score =
  100 * (
    0.24*current_thesis_health_norm +
    0.20*current_contract_health_norm +
    0.12*(1 - flow_reversal_risk_norm) +
    0.10*(1 - vol_crush_risk_norm) +
    0.10*(1 - theta_fade_risk_norm) +
    0.08*(1 - gamma_support_loss_norm) +
    0.08*(1 - energy_score_decay_norm) +
    0.08*(1 - retail_flow_trap_norm)
  )

State map:
- >=75: healthy
- 60 to <75: caution
- 45 to <60: reduce / tighten paper management
- <45: thesis broken

Immediate thesis-break triggers:
- hard dilution/offering surprise
- quote collapse / exitability failure
- flow_reversal_flag + vol_crush_flag together
- post_entry_health_score < 35

## 10. Pseudocode by Score Path

Pseudocode A: build feature packet

function build_feature_packet(underlying_snapshot, option_snapshot, signal_features):
    feats = {}
    feats.flow_norm = clamp01(logistic_like(signal_features.flow_raw, mid=1.0, scale=0.6))
    feats.flow_urgency_norm = clamp01(logistic_like(signal_features.flow_urgency_raw, mid=1.0, scale=0.5))
    feats.dark_pool_norm = clamp01(linear_band(underlying_snapshot.dark_pool_accumulation_raw, 0.0, 1.0))
    feats.hidden_liquidity_norm = clamp01(linear_band(underlying_snapshot.hidden_liquidity_raw, 0.0, 1.0))
    feats.float_turnover_norm = clamp01(linear_band(underlying_snapshot.float_turnover_raw, 0.0, 1.0))
    feats.short_interest_norm = clamp01(linear_band(underlying_snapshot.short_interest_pct_float, 5.0, 30.0))
    feats.borrow_rate_norm = clamp01(logistic_like(underlying_snapshot.borrow_rate_ctb, mid=20.0, scale=10.0))
    feats.utilization_norm = clamp01(linear_band(underlying_snapshot.utilization_pct, 70.0, 100.0))
    feats.ftd_threshold_norm = 1.0 if underlying_snapshot.threshold_list_flag or underlying_snapshot.ftd_signal_flag else 0.0
    feats.dilution_risk_norm = 1.0 if underlying_snapshot.dilution_risk_flag else 0.0
    feats.gamma_proximity_norm = 1.0 - clamp01(linear_band(abs(option_snapshot.gamma_wall_distance_pct), 0.0, 0.10))
    feats.spread_pct_norm = clamp01(linear_band(option_snapshot.spread_pct_mid, 0.00, 0.20))
    feats.oi_norm = clamp01(logistic_like(option_snapshot.oi, mid=1500.0, scale=700.0))
    feats.option_volume_norm = clamp01(logistic_like(option_snapshot.option_volume, mid=500.0, scale=250.0))
    feats.theta_friction_norm = clamp01(linear_band(abs(option_snapshot.theta), 0.02, 0.20))
    feats.premium_distortion_norm = clamp01(linear_band(option_snapshot.premium_distortion_raw, 0.0, 1.0))
    return feats

Pseudocode B: universal scoring

function score_universal(feats):
    compute each bucket
    universal_base_score = weighted sum from Section 5
    return universal_base_score, reason_codes

Pseudocode C: thesis routing

function route_thesis(feats):
    compute all thesis scores from Section 6
    primary = argmax(scores)
    secondary = second best if close enough
    if scores[primary] < 55:
        primary = "weak_undefined"
    return primary, secondary, scores, reason_codes

Pseudocode D: contract hard-floor and ranking

function evaluate_contract(option_snapshot, feats, primary_thesis, manual_override_flag=False):
    veto_reasons = []
    if option_snapshot.right != "C": veto_reasons.append("not_call")
    if option_snapshot.premium > 2.50 and not manual_override_flag: veto_reasons.append("premium_over_cap")
    if not option_snapshot.quote_quality_flag: veto_reasons.append("bad_quote")
    if option_snapshot.spread_pct_mid > 0.20: veto_reasons.append("wide_spread")
    if option_snapshot.oi < 500: veto_reasons.append("thin_oi")
    if option_snapshot.option_volume < 100: veto_reasons.append("thin_option_volume")
    if option_snapshot.dte < 8: veto_reasons.append("too_low_dte")
    if veto_reasons:
        return {"status":"veto","veto_reasons":veto_reasons}

    sub_1_bucket_flag = (option_snapshot.premium < 1.00)
    dte_fit_norm = thesis_specific_dte_fit(primary_thesis, option_snapshot.dte)
    premium_fit_norm = center_peak(option_snapshot.premium, 0.80, 1.45, 2.50)
    strike_posture_fit_norm = score_strike_posture(primary_thesis, option_snapshot.delta, feats.gamma_proximity_norm)
    survival_composite_norm = compute_survival_composite(feats)
    exitability_norm = compute_exitability(feats)
    contract_quality_score = weighted formula from Section 7

    return {
      "status":"ok",
      "sub_1_bucket_flag":sub_1_bucket_flag,
      "contract_quality_score":contract_quality_score,
      "survival_composite_norm":survival_composite_norm,
      "premium_fit_norm":premium_fit_norm,
      "dte_fit_norm":dte_fit_norm,
      "strike_posture_fit_norm":strike_posture_fit_norm,
      "exitability_norm":exitability_norm
    }

Pseudocode E: action decision

function decide_action(universal_base_score, primary_thesis_confidence, contract_eval, regime_fit_norm, event_alignment_norm):
    if contract_eval.status == "veto":
        return {"action":"ignore","reason_codes":contract_eval.veto_reasons}

    action_score = weighted formula from Section 8

    if contract_eval.sub_1_bucket_flag:
        if action_score >= 90 and contract_eval.contract_quality_score >= 85 and contract_eval.survival_composite_norm >= 0.72:
            return {"action":"paper_enter","urgency":"strict_sub_1"}
        elif action_score >= 75:
            return {"action":"alert_only","urgency":"strict_sub_1_monitor"}
        else:
            return {"action":"monitor"}

    if action_score >= 90:
        return {"action":"paper_enter","urgency":"urgent"}
    if action_score >= 85:
        return {"action":"paper_enter","urgency":"normal"}
    if action_score >= 75:
        return {"action":"alert_only"}
    if action_score >= 60:
        return {"action":"monitor"}
    return {"action":"ignore"}

Pseudocode F: post-entry health

function score_post_entry_health(position_state, current_feats):
    current_thesis_health_norm = clamp01(position_state.sci_current / max(position_state.sci_at_entry, 1))
    current_contract_health_norm = compute_contract_health(current_feats)
    flow_reversal_risk_norm = 1.0 if position_state.flow_reversal_flag else 0.0
    vol_crush_risk_norm = 1.0 if position_state.vol_crush_flag else 0.0
    theta_fade_risk_norm = 1.0 if position_state.theta_fade_flag else 0.0
    gamma_support_loss_norm = 1.0 if position_state.trailing_gamma_pivot_flag else 0.0
    energy_score_decay_norm = clamp01(linear_band(position_state.energy_score_decay_raw, 0.20, 1.00))
    retail_flow_trap_norm = 1.0 if position_state.retail_flow_trap_flag else 0.0

    post_entry_health_score = formula from Section 9
    map to state
    emit action recommendation + reason codes

## 11. Implementation Order and Acceptance Targets

Module build order:
1. schema.py
2. normalize.py
3. gates.py
4. universal_score.py
5. thesis_router.py
6. contract_selector.py
7. action_policy.py
8. post_entry_health.py
9. reason_codes.py
10. replay_and_audit.py

Required outputs per decision cycle:
- universal_base_score
- thesis score vector
- primary_thesis / secondary_thesis
- contract_quality_score
- survival_composite_norm
- action_score
- action_class
- reason_codes
- hard_veto_reasons
- post_entry_health_score (for open positions)

Testing requirements:
- deterministic scoring with fixed fixtures
- normalization boundary tests
- hard-gate unit tests
- thesis routing snapshot tests
- selector ranking regression tests
- action-policy threshold tests
- post-entry state transition tests
