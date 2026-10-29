from __future__ import annotations

from datetime import UTC, datetime
import pandas as pd


def execution_quality_summary(store) -> pd.DataFrame:
    df = store.conn.execute("SELECT symbol, side, limit_price, fill_price, created_ts FROM paper_orders WHERE fill_price IS NOT NULL AND limit_price IS NOT NULL").df()
    if df.empty:
        return pd.DataFrame(columns=['symbol','side','order_count','mean_slippage_bps','median_slippage_bps'])
    work = df.copy()
    work['slippage_bps'] = work.apply(
        lambda r: ((float(r['fill_price']) - float(r['limit_price'])) / max(float(r['limit_price']), 0.0001) * 10000.0) if str(r['side']).lower() == 'buy'
        else ((float(r['limit_price']) - float(r['fill_price'])) / max(float(r['limit_price']), 0.0001) * 10000.0),
        axis=1,
    )
    return work.groupby(['symbol','side'], as_index=False).agg(
        order_count=('slippage_bps', 'count'),
        mean_slippage_bps=('slippage_bps', 'mean'),
        median_slippage_bps=('slippage_bps', 'median'),
    )


def persist_execution_quality(store) -> pd.DataFrame:
    summary = execution_quality_summary(store)
    if summary.empty:
        return summary
    if store.backend == 'duckdb':
        try:
            store.conn.execute("CREATE TABLE IF NOT EXISTS execution_quality (run_ts TIMESTAMP, symbol TEXT, side TEXT, order_count BIGINT, mean_slippage_bps DOUBLE, median_slippage_bps DOUBLE)")
        except Exception:
            pass
    else:
        store.conn.execute("CREATE TABLE IF NOT EXISTS execution_quality (run_ts TEXT, symbol TEXT, side TEXT, order_count INTEGER, mean_slippage_bps REAL, median_slippage_bps REAL)")
    out = summary.copy()
    out['run_ts'] = datetime.now(UTC).replace(tzinfo=None)
    store.insert_dataframe('execution_quality', out[['run_ts','symbol','side','order_count','mean_slippage_bps','median_slippage_bps']])
    return out
