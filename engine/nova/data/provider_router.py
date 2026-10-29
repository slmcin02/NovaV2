from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nova.config import AppConfig


@dataclass(slots=True)
class FallbackOptionsProvider:
    providers: list[Any]
    name: str = "fallback"

    def get_profile(self, symbol: str) -> dict[str, Any]:
        for provider in self.providers:
            try:
                profile = provider.get_profile(symbol)
            except Exception:
                continue
            if profile and any(profile.get(k) not in (None, 0, 0.0, "") for k in ("market_cap", "sector", "last_price")):
                return profile
        return {"market_cap": None, "sector": None, "last_price": None}

    def momentum_20d(self, symbol: str) -> float:
        for provider in self.providers:
            try:
                value = provider.momentum_20d(symbol)
            except Exception:
                continue
            if value is not None:
                return float(value)
        return 0.0

    def vix_value(self) -> float | None:
        for provider in self.providers:
            try:
                value = provider.vix_value()
            except Exception:
                continue
            if value is not None:
                return float(value)
        return None

    def scan_calls(self, symbol: str, max_dte: int, max_ask: float, min_dte: int = 7):
        for provider in self.providers:
            try:
                rows = provider.scan_calls(symbol=symbol, max_dte=max_dte, max_ask=max_ask, min_dte=min_dte)
            except Exception:
                continue
            if rows:
                return rows
        return []


def build_provider(config: AppConfig, name: str):
    n = name.lower().strip()
    if n == "yfinance":
        from nova.data.yfinance_adapter import YFinanceOptionsProvider
        return YFinanceOptionsProvider()
    if n == "replay":
        from nova.data.replay_adapter import ReplayOptionsProvider
        return ReplayOptionsProvider(config.replay.get("fixtures_root", "data/fixtures"))
    if n == "thetadata":
        from nova.data.theta_adapter import ThetaDataOptionsProvider
        td_cfg = config.providers.get("thetadata", {})
        return ThetaDataOptionsProvider(
            config.raw["env"]["thetadata_base_url"],
            strike_range=int(td_cfg.get("strike_range", 12)),
        )
    if n == "polygon":
        from nova.data.polygon_adapter import PolygonOptionsProvider
        return PolygonOptionsProvider(
            config.raw["env"]["polygon_api_key"],
            config.raw["env"]["polygon_base_url"],
        )
    raise ValueError(f"unknown provider: {name}")


def get_provider(config: AppConfig, provider_name: str | None = None):
    name = (provider_name or config.runtime.get("provider") or "yfinance").lower().strip()
    if name in {"auto", "fallback"}:
        order = [str(x) for x in config.runtime.get("provider_fallback_order", ["polygon", "thetadata", "yfinance", "replay"])]
        providers = [build_provider(config, x) for x in order]
        return FallbackOptionsProvider(providers=providers)
    if "," in name:
        providers = [build_provider(config, x.strip()) for x in name.split(",") if x.strip()]
        return FallbackOptionsProvider(providers=providers)
    return build_provider(config, name)
