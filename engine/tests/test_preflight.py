from nova.config import load_config
from nova.engine.preflight import run_preflight


def test_preflight_has_expected_keys():
    cfg = load_config()
    out = run_preflight(cfg)
    assert "duckdb_parent_exists" in out
    assert "session_phase" in out
    assert out["max_ask_ok"] is True
