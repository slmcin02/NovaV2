from datetime import date
import pandas as pd

from nova.storage.duckdb_store import DuckDBStore
from nova.engine.execution_quality import execution_quality_summary


def test_execution_quality_summary(tmp_path):
    db = DuckDBStore(tmp_path / 'test.duckdb', schema_path='sql/schema.sql')
    db.insert_dataframe('paper_orders', pd.DataFrame([
        {'order_id':'1','created_ts':'2026-01-01','status':'filled','symbol':'PLTR','contract_symbol':'A','side':'buy','qty':1,'limit_price':1.00,'fill_price':1.02,'notes':''},
        {'order_id':'2','created_ts':'2026-01-01','status':'filled','symbol':'PLTR','contract_symbol':'A','side':'sell','qty':1,'limit_price':1.40,'fill_price':1.39,'notes':''},
    ]))
    out = execution_quality_summary(db)
    assert len(out) == 2
    assert 'mean_slippage_bps' in out.columns
