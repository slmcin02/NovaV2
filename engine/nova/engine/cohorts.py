from __future__ import annotations

from datetime import datetime

import pandas as pd


def cohort_summary(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame(columns=["cohort_key", "cohort_value", "trade_count", "win_rate", "avg_return", "median_return", "avg_score", "created_ts"])
    df = trades_df.copy()
    if "win" not in df.columns:
        df["win"] = (df["gross_return"] > 0).astype(int)
    out = []
    now = datetime.utcnow()

    if "entry_ts" in df.columns:
        ts = pd.to_datetime(df["entry_ts"])
        df["entry_week"] = ts.dt.strftime("%Y-W%U")
        df["entry_month"] = ts.dt.strftime("%Y-%m")
        for key in ["entry_week", "entry_month"]:
            grouped = df.groupby(key)
            for value, grp in grouped:
                out.append({
                    "cohort_key": key,
                    "cohort_value": str(value),
                    "trade_count": int(len(grp)),
                    "win_rate": float(grp["win"].mean()),
                    "avg_return": float(grp["gross_return"].mean()),
                    "median_return": float(grp["gross_return"].median()),
                    "avg_score": float(grp.get("score_at_entry", pd.Series(dtype=float)).mean()) if "score_at_entry" in grp.columns else None,
                    "created_ts": now,
                })
    if "exit_reason" in df.columns:
        grouped = df.groupby("exit_reason")
        for value, grp in grouped:
            out.append({
                "cohort_key": "exit_reason",
                "cohort_value": str(value),
                "trade_count": int(len(grp)),
                "win_rate": float(grp["win"].mean()),
                "avg_return": float(grp["gross_return"].mean()),
                "median_return": float(grp["gross_return"].median()),
                "avg_score": float(grp.get("score_at_entry", pd.Series(dtype=float)).mean()) if "score_at_entry" in grp.columns else None,
                "created_ts": now,
            })
    return pd.DataFrame(out)
