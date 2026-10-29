from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None

from nova.models import ContractSnapshot
from nova.utils.market import black_scholes_call_delta, dte_from_expiration, spread_pct


class YFinanceOptionsProvider:
    name = "yfinance"

    @property
    def enabled(self) -> bool:
        return yf is not None

    def get_profile(self, symbol: str) -> dict[str, Any]:
        if yf is None:
            return {"market_cap": None, "sector": None, "last_price": None}
        t = yf.Ticker(symbol)
        try:
            rich = t.info or {}
        except Exception:
            rich = {}
        out = {
            "market_cap": rich.get("marketCap"),
            "sector": rich.get("sector"),
            "last_price": None,
        }
        hist = t.history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
            out["last_price"] = float(hist["Close"].dropna().iloc[-1])
        return out

    def momentum_20d(self, symbol: str) -> float:
        if yf is None:
            return 0.0
        try:
            df = yf.Ticker(symbol).history(period="60d", interval="1d")
            if df is None or df.empty or len(df) < 21:
                return 0.0
            close = df["Close"].dropna()
            return float((close.iloc[-1] / close.iloc[-21]) - 1.0)
        except Exception:
            return 0.0

    def vix_value(self) -> float | None:
        if yf is None:
            return None
        try:
            df = yf.Ticker("^VIX").history(period="10d", interval="1d")
            if df is None or df.empty:
                return None
            return float(df["Close"].dropna().iloc[-1])
        except Exception:
            return None

    def scan_calls(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7) -> list[ContractSnapshot]:
        if yf is None:
            return []
        t = yf.Ticker(symbol)
        profile = self.get_profile(symbol)
        spot = profile["last_price"]
        if not spot or spot <= 0:
            return []
        snapshots: list[ContractSnapshot] = []
        try:
            expirations = t.options or []
        except Exception:
            expirations = []
        for exp_str in expirations:
            try:
                exp = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except Exception:
                continue
            dte = dte_from_expiration(exp)
            if dte < min_dte or dte > max_dte:
                continue
            try:
                calls = t.option_chain(exp_str).calls
            except Exception:
                continue
            if calls is None or calls.empty:
                continue
            df = calls.copy()
            df = df[(df["ask"] > 0) & (df["ask"] <= max_ask)]
            for _, row in df.iterrows():
                bid = float(row.get("bid", 0.0) or 0.0)
                ask = float(row.get("ask", 0.0) or 0.0)
                iv = float(row.get("impliedVolatility", 0.0) or 0.0)
                strike = float(row.get("strike", 0.0) or 0.0)
                delta = black_scholes_call_delta(spot, strike, max(dte, 1)/365.0, 0.04, max(iv, 1e-6))
                snapshots.append(
                    ContractSnapshot(
                        symbol=symbol,
                        contract_symbol=str(row.get("contractSymbol", "")),
                        expiration=exp,
                        strike=strike,
                        right="call",
                        bid=bid,
                        ask=ask,
                        mid=round((bid + ask) / 2.0, 4),
                        spread_pct=spread_pct(bid, ask),
                        implied_vol=iv,
                        underlying_price=float(spot),
                        dte=dte,
                        delta=float(delta) if pd.notna(delta) else 0.0,
                        volume=int(row.get("volume", 0) or 0),
                        oi=int(row.get("openInterest", 0) or 0),
                        market_cap=profile["market_cap"],
                        sector=profile["sector"],
                        provider=self.name,
                    )
                )
        return snapshots
