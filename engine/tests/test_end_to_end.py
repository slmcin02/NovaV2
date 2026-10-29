from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime

import pandas as pd

from nova.config import load_config
from nova.cli import _scan_core
from nova.data.provider_router import get_provider
from nova.data.sec_adapter import SECAdapter
from nova.data.finra_adapter import FINRAAdapter
from nova.storage.duckdb_store import DuckDBStore
from nova.storage.parquet_lake import ParquetLake
from nova.engine.backtest import simple_exit_backtest
from nova.engine.execution_quality import persist_execution_quality


def test_replay_scan_backtest_pipeline(tmp_path: Path):
    cfg = load_config()
    cfg.raw['storage']['duckdb_path'] = str(tmp_path / 'nova_test.duckdb')
    cfg.raw['storage']['lake_root'] = str(tmp_path / 'lake')
    cfg.raw['alerts']['discord_enabled'] = False
    cfg.raw['runtime']['provider'] = 'replay'
    store = DuckDBStore(cfg.storage['duckdb_path'])
    lake = ParquetLake(cfg.storage['lake_root'])
    provider = get_provider(cfg, 'replay')
    sec = SECAdapter(cfg.raw['env']['sec_user_agent'])
    finra = FINRAAdapter()
    universe_rows, raw_rows, signal_rows = _scan_core(cfg, store, lake, provider, sec, finra, fixture_name='sample_option_scan_expanded.csv')
    assert len(universe_rows) > 0
    assert len(raw_rows) > 0
    assert len(signal_rows) > 0

    signals_df = store.signal_rows(days=30)
    trades = simple_exit_backtest(
        signals_df,
        stop_loss_pct=float(cfg.risk['stop_loss_pct']),
        take_profit_pct=float(cfg.risk['take_profit_pct']),
    )
    assert len(trades) > 0
    trade_cols = store.conn.execute("PRAGMA table_info('trades')").df()['name'].tolist()
    trades_df = pd.DataFrame(trades)
    store.insert_dataframe('trades', trades_df[[c for c in trades_df.columns if c in trade_cols]])
    assert not store.completed_trades().empty
    assert persist_execution_quality(store).empty or isinstance(persist_execution_quality(store), pd.DataFrame)
