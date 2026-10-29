from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score

FEATURE_COLUMNS = [
    "bid", "ask", "mid", "spread_pct", "implied_vol", "underlying_price", "dte",
    "delta", "volume", "oi", "finra_short_ratio", "momentum_20d", "m_sigma", "score_at_entry"
]


@dataclass(slots=True)
class EnsemblePack:
    lr: LogisticRegression
    rf: RandomForestClassifier
    gb: GradientBoostingClassifier

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        probs = np.vstack([
            self.lr.predict_proba(X)[:, 1],
            self.rf.predict_proba(X)[:, 1],
            self.gb.predict_proba(X)[:, 1],
        ])
        return probs.mean(axis=0)


class Learner:
    def __init__(self, model_dir: str | Path = "data/models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def train_from_trades(self, trades_df: pd.DataFrame) -> tuple[EnsemblePack | None, dict]:
        if trades_df.empty or len(trades_df) < 30:
            return None, {"train_rows": len(trades_df), "accuracy": None, "auc": None}
        df = trades_df.copy()
        if "win" not in df.columns:
            df["win"] = (df["gross_return"] > 0).astype(int)
        cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        if len(cols) < 4:
            return None, {"train_rows": len(df), "accuracy": None, "auc": None}

        X = df[cols].fillna(0.0)
        y = df["win"].astype(int)

        lr = LogisticRegression(max_iter=200)
        rf = RandomForestClassifier(n_estimators=200, random_state=42)
        gb = GradientBoostingClassifier(random_state=42)

        lr.fit(X, y)
        rf.fit(X, y)
        gb.fit(X, y)

        pack = EnsemblePack(lr=lr, rf=rf, gb=gb)
        probs = pack.predict_proba(X)
        preds = (probs >= 0.5).astype(int)
        metrics = {
            "train_rows": int(len(df)),
            "accuracy": float(accuracy_score(y, preds)),
            "auc": float(roc_auc_score(y, probs)) if y.nunique() > 1 else None,
        }
        return pack, metrics

    def save(self, pack: EnsemblePack, name: str = "signal_ensemble.pkl") -> Path:
        out = self.model_dir / name
        with out.open("wb") as f:
            pickle.dump(pack, f)
        return out

    def compute_psi(self, base: pd.Series, recent: pd.Series, buckets: int = 10) -> float:
        base = base.fillna(0.0).astype(float)
        recent = recent.fillna(0.0).astype(float)
        if base.empty or recent.empty:
            return 0.0
        quantiles = np.linspace(0, 1, buckets + 1)
        cuts = np.unique(np.quantile(base, quantiles))
        if len(cuts) < 3:
            return 0.0
        base_bins = pd.cut(base, bins=cuts, include_lowest=True)
        recent_bins = pd.cut(recent, bins=cuts, include_lowest=True)
        base_dist = base_bins.value_counts(normalize=True).sort_index()
        recent_dist = recent_bins.value_counts(normalize=True).sort_index()
        eps = 1e-6
        psi = float((((recent_dist + eps) - (base_dist + eps)) * np.log((recent_dist + eps) / (base_dist + eps))).sum())
        return psi
