from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _round_bps(x: float) -> float:
    return round(float(x), 2)


def _score_bucket(score: float) -> str:
    floor = int(score // 5 * 5)
    return f"{floor:02d}-{floor+4:02d}"


def calibrate_from_store(store, output_path: str | Path, min_trades: int = 20) -> dict[str, Any]:
    trades = store.completed_trades()
    buy_orders = store.conn.execute("SELECT limit_price, fill_price FROM paper_orders WHERE side = 'buy' AND fill_price IS NOT NULL").df()
    sell_orders = store.conn.execute("SELECT limit_price, fill_price FROM paper_orders WHERE side = 'sell' AND fill_price IS NOT NULL").df()

    entry_slippage_bps = 15.0
    exit_slippage_bps = 20.0
    if not buy_orders.empty:
        series = ((buy_orders['fill_price'] - buy_orders['limit_price']) / buy_orders['limit_price']).replace([np.inf, -np.inf], np.nan).dropna() * 10000.0
        if not series.empty:
            entry_slippage_bps = _round_bps(series.median())
    if not sell_orders.empty:
        series = ((sell_orders['limit_price'] - sell_orders['fill_price']) / sell_orders['limit_price']).replace([np.inf, -np.inf], np.nan).dropna() * 10000.0
        if not series.empty:
            exit_slippage_bps = _round_bps(series.median())

    recommended = {
        'entry_slippage_bps': entry_slippage_bps,
        'exit_slippage_bps': exit_slippage_bps,
        'recommended_thesis_break_score': 50.0,
        'recommended_take_profit_pct': 0.45,
        'recommended_stop_loss_pct': 0.18,
        'trades_used': int(len(trades)),
        'score_buckets': [],
        'confidence': 'low' if len(trades) < min_trades else 'medium',
    }

    if not trades.empty and 'score_at_entry' in trades.columns:
        work = trades.copy()
        work['win'] = work['gross_return'] > 0
        work['score_bucket'] = work['score_at_entry'].astype(float).map(_score_bucket)
        bucket = work.groupby('score_bucket', as_index=False).agg(
            trade_count=('trade_id', 'count'),
            win_rate=('win', 'mean'),
            avg_return=('gross_return', 'mean'),
            median_return=('gross_return', 'median'),
            avg_score=('score_at_entry', 'mean'),
        )
        recommended['score_buckets'] = bucket.to_dict(orient='records')
        strong = bucket[(bucket['trade_count'] >= 1) & (bucket['avg_return'] > 0)]
        if not strong.empty:
            best = strong.sort_values(['avg_return', 'win_rate', 'avg_score'], ascending=False).iloc[0]
            recommended['recommended_thesis_break_score'] = round(max(45.0, float(best['avg_score']) - 12.0), 2)
            expected = float(work['gross_return'].clip(lower=-0.25, upper=1.0).mean())
            recommended['recommended_take_profit_pct'] = round(min(0.60, max(0.25, expected * 1.9)), 4)
            losers = work.loc[work['gross_return'] < 0, 'gross_return']
            loss_med = abs(float(losers.median())) if not losers.empty else 0.14
            recommended['recommended_stop_loss_pct'] = round(min(0.22, max(0.10, loss_med)), 4)
            recommended['confidence'] = 'high' if len(trades) >= min_trades else 'medium'

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(recommended, indent=2), encoding='utf-8')
    return recommended
