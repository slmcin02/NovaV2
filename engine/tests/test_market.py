from nova.utils.market import spread_pct, black_scholes_call_delta, expected_move, sigma_moneyness

def test_spread_pct():
    assert round(spread_pct(1.0, 1.2), 4) == round((1.2-1.0)/1.2, 4)

def test_delta_bounds():
    d = black_scholes_call_delta(100, 100, 30/365, 0.04, 0.40)
    assert 0.0 < d < 1.0

def test_expected_move_positive():
    assert expected_move(100, 0.5, 30/365) > 0

def test_sigma_moneyness_zeroish_atm():
    s = sigma_moneyness(100, 100, 0.5, 30/365)
    assert abs(s) < 0.2
