from __future__ import annotations

import uuid
import pandas as pd


def simple_exit_backtest(signals_df: pd.DataFrame, stop_loss_pct: float, take_profit_pct: float) -> list[dict]:
    out: list[dict] = []
    if signals_df.empty:
        return out
    df = signals_df.sort_values("signal_ts").copy()
    for _, row in df.iterrows():
        entry = float(row["ask"])
        score = float(row["score"])
        expected_move = min(0.75, max(-0.40, ((score - 60.0) / 100.0)))
        if expected_move >= take_profit_pct:
            ret = take_profit_pct
            reason = "take_profit_proxy"
        elif expected_move <= -stop_loss_pct:
            ret = -stop_loss_pct
            reason = "stop_loss_proxy"
        else:
            ret = expected_move
            reason = "time_exit_proxy"
        exit_price = round(entry * (1.0 + ret), 4)
        out.append({
            "trade_id": str(uuid.uuid4()),
            "entry_ts": row["signal_ts"],
            "exit_ts": pd.Timestamp(row["signal_ts"]) + pd.Timedelta(days=5),
            "symbol": row["symbol"],
            "contract_symbol": row["contract_symbol"],
            "expiration": row["expiration"],
            "strike": row["strike"],
            "right": row["right"],
            "qty": int(row["suggested_contracts"]),
            "entry_price": entry,
            "exit_price": exit_price,
            "gross_return": round((exit_price - entry) / max(entry, 0.01), 6),
            "exit_reason": reason,
            "score_at_entry": score,
            "bid": row.get("bid"),
            "ask": row.get("ask"),
            "mid": row.get("mid"),
            "spread_pct": row.get("spread_pct"),
            "implied_vol": row.get("implied_vol"),
            "underlying_price": row.get("underlying_price"),
            "dte": row.get("dte"),
            "delta": row.get("delta"),
            "volume": row.get("volume"),
            "oi": row.get("oi"),
            "finra_short_ratio": row.get("finra_short_ratio"),
            "momentum_20d": row.get("momentum_20d"),
            "m_sigma": row.get("m_sigma"),
        })
    return out
