import json
import os
import subprocess
import sys
from pathlib import Path

from test_phase1_policy import GOOD_FEATURES, GOOD_OPTION


def _run(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, DISCORD_WEBHOOK_URL="", POLYGON_API_KEY="", FRED_API_KEY="")
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    return subprocess.run(
        [sys.executable, "-m", "nova.cli", "phase1-eval", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )


def test_phase1_cli_is_offline_auditable_and_does_not_overwrite(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    receipt = tmp_path / "receipt.json"
    fixture.write_text(
        json.dumps(
            {
                "data_mode": "offline_fixture",
                "features": GOOD_FEATURES,
                "contracts": [GOOD_OPTION],
                "regime_fit_norm": 1,
                "event_alignment_norm": 1,
            }
        ),
        encoding="utf-8",
    )
    result = _run("--input", str(fixture), "--output", str(receipt))
    assert result.returncode == 0, result.stderr
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    assert evidence["data_mode"] == "offline_fixture"
    assert evidence["policy"]["mode"] == "offline_phase1_paper_policy"
    assert evidence["policy"]["has_live_order_authority"] is False
    assert evidence["input_sha256"]
    assert json.loads(result.stdout)["input_sha256"] == evidence["input_sha256"]
    second = _run("--input", str(fixture), "--output", str(receipt))
    assert second.returncode != 0
    assert (
        receipt.read_text(encoding="utf-8")
        == json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )


def test_phase1_cli_rejects_live_data_mode(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"data_mode": "live", "features": {}, "contracts": []}))
    result = _run("--input", str(p))
    assert result.returncode != 0
