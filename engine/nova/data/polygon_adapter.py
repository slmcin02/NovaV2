from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from nova.models import ContractSnapshot
from nova.utils.market import black_scholes_call_delta, dte_from_expiration, spread_pct


class PolygonOptionsProvider:
    name = "polygon"

    def __init__(self, api_key: str, base_url: str = "https://api.polygon.io"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("polygon api key missing")
        query = dict(params or {})
        query["apiKey"] = self.api_key
        r = self.session.get(f"{self.base_url}{path}", params=query, timeout=20)
        r.raise_for_status()
        return r.json()

    def get_profile(self, symbol: str) -> dict[str, Any]:
        last_price = None
        market_cap = None
        sector = None
        try:
            prev = self._get(f"/v2/aggs/ticker/{symbol}/prev", {"adjusted": "true"})
            results = prev.get("results") or []
            if results:
                last_price = float(results[0].get("c") or 0.0) or None
        except Exception:
            pass
        try:
            details = self._get(f"/v3/reference/tickers/{symbol}")
            result = details.get("results") or {}
            market_cap = result.get("market_cap")
            sector = result.get("sic_description") or result.get("market")
        except Exception:
            pass
        return {"market_cap": market_cap, "sector": sector, "last_price": last_price}

    def momentum_20d(self, symbol: str) -> float:
        try:
            end = datetime.now(UTC).date()
            start = end.replace(day=max(1, end.day - 40))
            data = self._get(
                f"/v2/aggs/ticker/{symbol}/range/1/day/{start.isoformat()}/{end.isoformat()}",
                {"adjusted": "true", "sort": "asc", "limit": 60},
            )
            rows = data.get("results") or []
            if len(rows) < 21:
                return 0.0
            closes = [float(x.get("c") or 0.0) for x in rows if x.get("c") is not None]
            if len(closes) < 21 or closes[-21] <= 0:
                return 0.0
            return float((closes[-1] / closes[-21]) - 1.0)
        except Exception:
            return 0.0

    def vix_value(self) -> float | None:
        try:
            data = self._get("/v2/aggs/ticker/I:VIX1D/prev", {"adjusted": "true"})
            rows = data.get("results") or []
            if rows:
                return float(rows[0].get("c") or 0.0) or None
        except Exception:
            return None
        return None

    def scan_calls(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7) -> list[ContractSnapshot]:
        profile = self.get_profile(symbol)
        spot = profile.get("last_price")
        if not spot or spot <= 0:
            return []
        try:
            raw = self._get(
                "/v3/snapshot/options",
                {"underlying_ticker": symbol, "limit": 250, "contract_type": "call"},
            )
        except Exception:
            return []
        rows = raw.get("results") or []
        out: list[ContractSnapshot] = []
        for row in rows:
            details = row.get("details") or {}
            day = row.get("day") or {}
            greeks = row.get("greeks") or {}
            quote = row.get("last_quote") or {}
            exp_raw = details.get("expiration_date")
            if not exp_raw:
                continue
            try:
                exp = datetime.strptime(exp_raw, "%Y-%m-%d").date()
            except Exception:
                continue
            dte = dte_from_expiration(exp)
            if dte < min_dte or dte > max_dte:
                continue
            ask = float(quote.get("ask") or row.get("ask") or 0.0)
            if ask <= 0 or ask > max_ask:
                continue
            bid = float(quote.get("bid") or row.get("bid") or 0.0)
            strike = float(details.get("strike_price") or 0.0)
            iv = float(row.get("implied_volatility") or 0.0)
            delta = float(greeks.get("delta") or black_scholes_call_delta(float(spot), strike, max(dte,1)/365.0, 0.04, max(iv, 1e-6)) or 0.0)
            out.append(ContractSnapshot(
                symbol=symbol,
                contract_symbol=str(details.get("ticker") or row.get("ticker") or ""),
                expiration=exp,
                strike=strike,
                right="call",
                bid=bid,
                ask=ask,
                mid=float((bid + ask) / 2.0),
                spread_pct=spread_pct(bid, ask),
                implied_vol=iv,
                underlying_price=float(spot),
                dte=dte,
                delta=delta,
                volume=int(day.get("volume") or 0),
                oi=int(row.get("open_interest") or 0),
                market_cap=profile.get("market_cap"),
                sector=profile.get("sector"),
                provider=self.name,
            ))
        return out
