from argparse import Namespace
from types import SimpleNamespace

from nova import cli


def test_replay_edge_ingest_skips_unknown_historical_augmentation(monkeypatch, capsys):
    calls = []

    class FakeStore:
        def upsert_edge_daily(self, rows):
            raise AssertionError("offline_ingest_fabricated_current_market_evidence")

    class FakeLake:
        def write_batch(self, *args, **kwargs):
            raise AssertionError("offline_ingest_wrote_live_evidence")

    cfg = SimpleNamespace(
        edges={
            "finra_short_volume_enabled": True,
            "occ_open_interest_enabled": True,
            "ftd_enabled": True,
            "fred_macro_enabled": True,
            "sec_dilution_lookback_days": 30,
        },
        raw={"env": {"fred_api_key": ""}},
    )

    def components(provider):
        calls.append(provider)
        return (
            cfg,
            FakeStore(),
            FakeLake(),
            SimpleNamespace(name="replay"),
            object(),
            object(),
            object(),
        )

    monkeypatch.setattr(cli, "_components", components)
    cli.cmd_ingest_edges(Namespace(provider="replay"))
    assert calls == ["replay"]
    assert "offline" in capsys.readouterr().out.lower()


def test_edge_ingest_cli_exposes_explicit_provider_choice():
    import subprocess
    import sys
    from pathlib import Path

    p = subprocess.run(
        [sys.executable, "-m", "nova.cli", "ingest-edges", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert p.returncode == 0
    assert "--provider" in p.stdout
