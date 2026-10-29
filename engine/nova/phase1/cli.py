"""Offline-only audited Nova Phase-1 evaluation from an explicit local fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from nova.phase1.policy import evaluate_setup, score_post_entry


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"phase1_{name}_must_be_object")
    return value


def run_phase1_fixture(input_path: Path) -> dict[str, Any]:
    p = input_path.resolve(strict=True)
    if not p.is_file() or p.stat().st_size > 2_000_000:
        raise ValueError("phase1_fixture_file_size_invalid")
    raw = p.read_bytes()
    packet = _mapping(json.loads(raw.decode("utf-8")), "packet")
    mode = packet.get("data_mode")
    if mode not in ("offline_fixture", "historical_replay"):
        raise ValueError("phase1_live_data_mode_not_supported")
    features = _mapping(packet.get("features"), "features")
    options = packet.get("contracts")
    if not isinstance(options, list) or len(options) > 1000:
        raise ValueError("phase1_contract_list_invalid")
    for item in options:
        _mapping(item, "contract")
    result = evaluate_setup(
        features,
        options,
        regime_fit_norm=packet.get("regime_fit_norm", 0.5),
        event_alignment_norm=packet.get("event_alignment_norm", 0.5),
        manual_override_flag=packet.get("manual_override_flag", False),
    )
    if packet.get("position_state") is not None:
        result["post_entry"] = score_post_entry(
            _mapping(packet["position_state"], "position_state")
        )
    return {
        "schema": "nova_phase1_offline_decision_v1",
        "policy_source": "NOVA_calls_only_phase1_module_spec_formula_sheet.md",
        "data_mode": mode,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "input_filename": p.name,
        "policy": result,
        "limits": [
            "No live brokerage or order authority",
            "Fixture/historical provenance must be separately verified",
            "Unknown market, SEC, earnings or dilution inputs are NOT verified safe",
            "Synthetic replay does not estimate out-of-sample trading returns",
        ],
    }


def cmd_phase1_eval(args: Any) -> None:
    report = run_phase1_fixture(Path(args.input))
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as f:
            f.write(encoded)
    print(encoded, end="")
