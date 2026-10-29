from pathlib import Path

from nova.cli import _scan_core
from nova.config import load_config
from nova.data.finra_adapter import FINRAAdapter
from nova.data.provider_router import get_provider
from nova.data.sec_adapter import SECAdapter
from nova.storage.duckdb_store import DuckDBStore
from nova.storage.parquet_lake import ParquetLake


def test_replay_does_not_call_live_sec(monkeypatch, tmp_path: Path) -> None:
    """Replay must work without network or a real SEC account, even with nonempty universe."""
    cfg = load_config()
    cfg.raw["storage"]["duckdb_path"] = str(tmp_path / "replay.duckdb")
    cfg.raw["storage"]["lake_root"] = str(tmp_path / "lake")
    cfg.raw["runtime"]["provider"] = "replay"
    cfg.raw["alerts"]["discord_enabled"] = False

    def forbidden_sec(*args, **kwargs):
        raise AssertionError("replay_mode_contacted_live_SEC")

    monkeypatch.setattr(SECAdapter, "has_recent_dilution_risk", forbidden_sec)
    store = DuckDBStore(cfg.storage["duckdb_path"])
    try:
        universe, raw, _signals = _scan_core(
            cfg,
            store,
            ParquetLake(cfg.storage["lake_root"]),
            get_provider(cfg, "replay"),
            SECAdapter("offline-test"),
            FINRAAdapter(),
            fixture_name="sample_option_scan_expanded.csv",
        )
        assert universe
        assert raw
    finally:
        store.conn.close()


def test_replay_never_dispatches_live_alerts(monkeypatch, tmp_path: Path) -> None:
    """Even if alerts are enabled, fixture replay cannot ping Discord."""
    cfg = load_config()
    cfg.raw["storage"]["duckdb_path"] = str(tmp_path / "notifications.duckdb")
    cfg.raw["storage"]["lake_root"] = str(tmp_path / "lake")
    cfg.raw["runtime"]["provider"] = "replay"
    cfg.raw["alerts"]["discord_enabled"] = True
    cfg.raw["env"]["discord_webhook_url"] = "https://example.invalid/webhook"

    def forbidden(*args, **kwargs):
        raise AssertionError("replay_attempted_live_notification")

    monkeypatch.setattr(SECAdapter, "has_recent_dilution_risk", forbidden)
    monkeypatch.setattr("nova.cli.send_discord", forbidden)
    store = DuckDBStore(cfg.storage["duckdb_path"])
    try:
        _universe, raw, signals = _scan_core(
            cfg,
            store,
            ParquetLake(cfg.storage["lake_root"]),
            get_provider(cfg, "replay"),
            SECAdapter("offline-test"),
            FINRAAdapter(),
            fixture_name="sample_option_scan_expanded.csv",
        )
        assert raw and signals
    finally:
        store.conn.close()
