from __future__ import annotations

from pathlib import Path
from datetime import date
import pandas as pd

from nova.engine.calibration import calibrate_from_store
from nova.storage.duckdb_store import DuckDBStore


def test_calibration_generates_report(tmp_path):
    db = DuckDBStore(tmp_path / 'test.duckdb', schema_path='sql/schema.sql')
    trades = pd.DataFrame([
        {'trade_id':'t1','entry_ts':'2026-01-01','exit_ts':'2026-01-05','symbol':'PLTR','contract_symbol':'PLTR1','expiration':date(2026,6,19),'strike':45.0,'right':'call','qty':1,'entry_price':1.0,'exit_price':1.3,'gross_return':0.30,'exit_reason':'take_profit','score_at_entry':84.0},
        {'trade_id':'t2','entry_ts':'2026-01-01','exit_ts':'2026-01-05','symbol':'SOFI','contract_symbol':'SOFI1','expiration':date(2026,6,19),'strike':12.0,'right':'call','qty':1,'entry_price':1.0,'exit_price':0.9,'gross_return':-0.10,'exit_reason':'stop_loss','score_at_entry':68.0},
        {'trade_id':'t3','entry_ts':'2026-01-01','exit_ts':'2026-01-05','symbol':'HIMS','contract_symbol':'HIMS1','expiration':date(2026,6,19),'strike':40.0,'right':'call','qty':1,'entry_price':1.0,'exit_price':1.2,'gross_return':0.20,'exit_reason':'time_exit','score_at_entry':79.0},
    ])
    db.insert_dataframe('trades', trades)
    db.insert_dataframe('paper_orders', pd.DataFrame([
        {'order_id':'o1','created_ts':'2026-01-01','status':'filled','symbol':'PLTR','contract_symbol':'PLTR1','side':'buy','qty':1,'limit_price':1.00,'fill_price':1.01,'notes':''},
        {'order_id':'o2','created_ts':'2026-01-02','status':'filled','symbol':'PLTR','contract_symbol':'PLTR1','side':'sell','qty':1,'limit_price':1.30,'fill_price':1.28,'notes':''},
    ]))
    report = calibrate_from_store(db, tmp_path / 'calibration.json', min_trades=2)
    assert report['trades_used'] == 3
    assert Path(tmp_path / 'calibration.json').exists()
    assert report['entry_slippage_bps'] >= 0
