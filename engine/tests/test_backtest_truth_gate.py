from argparse import Namespace

import pytest

from nova import cli


def test_backtest_must_require_quote_history_and_never_claim_score_proxy_as_real(
    monkeypatch,
):
    def forbidden(*args, **kwargs):
        raise AssertionError(
            "backtest_opened_mutable_store_before_validating_truth_gate"
        )

    monkeypatch.setattr(cli, "_components", forbidden)
    with pytest.raises(SystemExit, match="historical.*quotes"):
        cli.cmd_backtest(Namespace(diagnostic_score_proxy=False))


def test_backtest_cli_declares_explicit_diagnostic_mode():
    import subprocess
    import sys
    from pathlib import Path

    p = subprocess.run(
        [sys.executable, "-m", "nova.cli", "backtest", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert p.returncode == 0
    assert "--diagnostic-score-proxy" in p.stdout


def test_training_cannot_fit_synthetic_proxy_trades(monkeypatch, capsys):
    import pandas as pd

    class FakeStore:
        def completed_trades(self):
            return pd.DataFrame(
                [{"exit_reason": "time_exit_proxy", "gross_return": 0.05}]
            )

    monkeypatch.setattr(
        cli, "_components", lambda _: (None, FakeStore(), None, None, None, None, None)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("learner_trained_on_score_fabricated_returns")

    monkeypatch.setattr(cli.Learner, "train_from_trades", forbidden)
    cli.cmd_train(Namespace())
    assert "blocked" in capsys.readouterr().out.lower()
