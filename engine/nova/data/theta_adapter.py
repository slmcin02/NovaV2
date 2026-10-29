from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any

import httpx

from nova.models import ContractSnapshot
from nova.utils.market import dte_from_expiration, spread_pct


class ThetaDataOptionsProvider:
    name = "thetadata"

    def __init__(self, base_url: str, max_outstanding: int = 4, strike_range: int = 12):
        self.base_url = base_url.rstrip("/")
        self.max_outstanding = max_outstanding
        self.strike_range = strike_range

    async def _request_json(self, path: str, params: dict[str, Any]) -> Any:
        sem = asyncio.Semaphore(self.max_outstanding)
        timeout = httpx.Timeout(45.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with sem:
                url = f"{self.base_url}{path}"
                for attempt in range(1, 8):
                    try:
                        resp = await client.get(url, params=params)
                    except Exception:
                        await asyncio.sleep(0.25 * attempt)
                        continue
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code == 429:
                        await asyncio.sleep(min(5.0, 0.2 * (2 ** attempt)) + random.random() * 0.25)
                        continue
                    if 500 <= resp.status_code < 600:
                        await asyncio.sleep(0.25 * attempt)
                        continue
                    resp.raise_for_status()
                raise RuntimeError(f"ThetaData request failed after retries: {path}")

    async def iv_snapshot_calls(self, symbol: str, max_dte: int = 90, strike_range: int | None = None) -> list[dict]:
        return await self._request_json(
            "/option/snapshot/greeks/implied_volatility",
            {"symbol": symbol, "expiration": "*", "right": "call", "max_dte": max_dte, "strike_range": strike_range or self.strike_range, "format": "json"},
        )

    async def scan_calls_async(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7) -> list[ContractSnapshot]:
        raw = await self.iv_snapshot_calls(symbol, max_dte=max_dte)
        rows = raw if isinstance(raw, list) else raw.get("response", []) if isinstance(raw, dict) else []
        out: list[ContractSnapshot] = []
        for row in rows:
            expiration_raw = str(row.get("expiration") or "")
            if not (len(expiration_raw) == 8 and expiration_raw.isdigit()):
                continue
            exp = datetime.strptime(expiration_raw, "%Y%m%d").date()
            ask = float(row.get("ask") or 0.0)
            if ask <= 0 or ask > max_ask:
                continue
            bid = float(row.get("bid") or 0.0)
            out.append(
                ContractSnapshot(
                    symbol=symbol,
                    contract_symbol=str(row.get("contract_symbol") or ""),
                    expiration=exp,
                    strike=float(row.get("strike") or 0.0),
                    right="call",
                    bid=bid,
                    ask=ask,
                    mid=float(row.get("mid") or ((bid + ask) / 2.0)),
                    spread_pct=spread_pct(bid, ask),
                    implied_vol=float(row.get("implied_volatility") or row.get("iv") or 0.0),
                    underlying_price=float(row.get("underlying_price") or 0.0),
                    dte=dte_from_expiration(exp),
                    delta=float(row.get("delta") or 0.0),
                    volume=int(row.get("volume") or 0),
                    oi=int(row.get("open_interest") or row.get("oi") or 0),
                    provider=self.name,
                )
            )
        return [x for x in out if x.dte >= min_dte]

    def scan_calls(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7) -> list[ContractSnapshot]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.scan_calls_async(symbol, max_dte=max_dte, max_ask=max_ask, min_dte=min_dte))
        raise RuntimeError("ThetaData sync scan_calls cannot run inside an active event loop")

    def get_profile(self, symbol: str) -> dict[str, Any]:
        return {"market_cap": None, "sector": None, "last_price": None}

    def momentum_20d(self, symbol: str) -> float:
        return 0.0

    def vix_value(self) -> float | None:
        return None
