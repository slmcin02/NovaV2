from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from nova.models import ContractSnapshot
from nova.utils.market import black_scholes_call_delta, dte_from_expiration, spread_pct


class ReplayOptionsProvider:
    name = "replay"

    def __init__(self, fixtures_root: str | Path = "data/fixtures", default_fixture_name: str = "sample_option_scan.csv"):
        self.fixtures_root = Path(fixtures_root)
        self.fixtures_root.mkdir(parents=True, exist_ok=True)
        self.default_fixture_name = default_fixture_name

    def fixture_path(self, name: str) -> Path:
        return self.fixtures_root / name

    def load_fixture(self, name: str | None = None) -> pd.DataFrame:
        path = self.fixture_path(name or self.default_fixture_name)
        if not path.exists():
            return pd.DataFrame()
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)
        if path.suffix.lower() in {".parquet", ".pq"}:
            return pd.read_parquet(path)
        raise ValueError(f"unsupported fixture format: {path.suffix}")

    def get_profile(self, symbol: str) -> dict[str, Any]:
        df = self.load_fixture()
        if df.empty:
            return {"market_cap": None, "sector": None, "last_price": None}
        row = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
        if row.empty:
            return {"market_cap": None, "sector": None, "last_price": None}
        r = row.iloc[0]
        return {
            "market_cap": int(r.get("market_cap", 0) or 0) or None,
            "sector": r.get("sector") or None,
            "last_price": float(r.get("underlying_price", 0.0) or 0.0) or None,
        }

    def momentum_20d(self, symbol: str) -> float:
        df = self.load_fixture()
        if df.empty:
            return 0.0
        row = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
        if row.empty:
            return 0.0
        return float(row.iloc[0].get("momentum_20d", 0.0) or 0.0)

    def vix_value(self) -> float | None:
        df = self.load_fixture()
        if df.empty:
            return None
        return float(df["vix_value"].dropna().iloc[0]) if "vix_value" in df.columns and df["vix_value"].notna().any() else None

    def scan_calls(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7) -> list[ContractSnapshot]:
        df = self.load_fixture()
        if df.empty:
            return []
        rows = df[df["symbol"].astype(str).str.upper() == symbol.upper()].copy()
        rows = rows[(rows["ask"] > 0) & (rows["ask"] <= max_ask) & (rows["dte"] >= min_dte) & (rows["dte"] <= max_dte)]
        out: list[ContractSnapshot] = []
        for _, row in rows.iterrows():
            exp = row.get("expiration")
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp).date()
            bid = float(row.get("bid", 0.0) or 0.0)
            ask = float(row.get("ask", 0.0) or 0.0)
            spot = float(row.get("underlying_price", 0.0) or 0.0)
            strike = float(row.get("strike", 0.0) or 0.0)
            iv = float(row.get("implied_vol", 0.0) or 0.0)
            dte = int(row.get("dte", dte_from_expiration(exp)))
            delta = float(row.get("delta", black_scholes_call_delta(spot, strike, max(dte, 1)/365.0, 0.04, max(iv, 1e-6))) or 0.0)
            out.append(ContractSnapshot(
                symbol=symbol,
                contract_symbol=str(row.get("contract_symbol", "")),
                expiration=exp,
                strike=strike,
                right="call",
                bid=bid,
                ask=ask,
                mid=float(row.get("mid", (bid + ask) / 2.0) or 0.0),
                spread_pct=float(row.get("spread_pct", spread_pct(bid, ask)) or 0.0),
                implied_vol=iv,
                underlying_price=spot,
                dte=dte,
                delta=delta,
                volume=int(row.get("volume", 0) or 0),
                oi=int(row.get("oi", 0) or 0),
                market_cap=int(row.get("market_cap", 0) or 0) or None,
                sector=row.get("sector") or None,
                provider=self.name,
            ))
        return out
