from nova.engine.signal_quality import estimate_float_turnover, hidden_liquidity_score, synth_flow_score, spin_coherence, score_dynamics


def test_float_turnover_positive():
    assert estimate_float_turnover(10.0, 1_000_000_000, 5000) > 0


def test_hidden_liquidity_bounds():
    s = hidden_liquidity_score(oi=5000, volume=200, spread_pct=0.03, delta=0.4)
    assert 0 <= s <= 1


def test_spin_lock_detects_conflict():
    score, locked = spin_coherence(-0.05, 0.2, 0.1, 35.0)
    assert 0 <= score <= 1
    assert isinstance(locked, bool)


def test_score_dynamics_tags_ignition():
    vel, acc, tag = score_dynamics([50.0, 56.0], 66.0)
    assert vel > 0
    assert tag in {"ignition", "late_accel", "stable"}
