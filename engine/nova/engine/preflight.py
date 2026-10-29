from __future__ import annotations

from pathlib import Path
from typing import Any

from nova.config import AppConfig
from nova.engine.session import get_session_state
from nova.engine.market_ops import get_market_ops_state
from nova.engine.scoring import scoring_weight_sum
from nova.data.provider_router import get_provider


def run_preflight(config: AppConfig) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["duckdb_parent_exists"] = Path(config.storage["duckdb_path"]).parent.exists()
    checks["lake_root_exists"] = Path(config.storage["lake_root"]).exists()
    checks["seed_file_exists"] = Path(config.universe["seed_file"]).exists()
    checks["max_ask_ok"] = float(config.contracts["max_ask"]) <= 2.5
    checks["dte_ok"] = int(config.contracts["max_dte"]) <= 90
    checks["paper_enabled"] = bool(config.paper.get("enabled", True))
    checks["provider_auto_default"] = str(config.runtime.get("provider", "")) in {"auto", "fallback"}
    checks["calibration_enabled"] = bool(config.calibration.get("enabled", True))
    checks["free_sources_enabled"] = bool(config.edges.get("ftd_enabled", False) or config.edges.get("fred_macro_enabled", False))
    checks["score_lcb_gate_present"] = float(config.scoring.get('min_score_lcb', 0.40)) >= 0.30
    checks["sector_gate_present"] = float(config.scoring.get('min_sector_coherence', 0.20)) >= 0.15
    weight_sum = scoring_weight_sum(config.scoring.get('weights', {}))
    checks['scoring_weight_sum'] = weight_sum
    checks['scoring_weights_ok'] = abs(weight_sum - 1.0) <= 0.05
    checks['score_thresholds_ok'] = float(config.scoring.get('min_score', 0.0)) < float(config.scoring.get('elite_score', 100.0))
    checks['risk_budget_ok'] = float(config.risk.get('max_position_risk_usd', 0.0)) >= float(config.contracts.get('max_ask', 0.0)) * 100.0
    state = get_session_state()
    checks["session_phase"] = state.phase
    checks["session_open"] = state.is_open
    ops = get_market_ops_state()
    checks['market_ops_note'] = ops.note
    checks['market_ops_can_open_new'] = ops.can_open_new
    checks['market_ops_event_risk'] = ops.event_risk
    try:
        provider = get_provider(config, config.runtime.get("provider", "yfinance"))
        checks["provider_name"] = getattr(provider, 'name', type(provider).__name__)
    except Exception as exc:
        checks["provider_name"] = f"error:{exc}"
    required = [
        checks["duckdb_parent_exists"],
        checks["lake_root_exists"],
        checks["seed_file_exists"],
        checks["max_ask_ok"],
        checks["dte_ok"],
        checks["paper_enabled"],
        checks["calibration_enabled"],
        checks["provider_auto_default"],
        checks['score_lcb_gate_present'],
        checks['sector_gate_present'],
        checks['scoring_weights_ok'],
        checks['score_thresholds_ok'],
        checks['risk_budget_ok'],
    ]
    checks["ok"] = all(required)
    return checks
