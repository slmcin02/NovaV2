from __future__ import annotations

from pathlib import Path

from nova.config import AppConfig
from nova.utils.market import market_cap_bucket


class UniverseBuilder:
    def __init__(self, config: AppConfig, provider):
        self.config = config
        self.provider = provider

    def seed_symbols(self) -> list[str]:
        seed_file = Path(self.config.universe["seed_file"])
        if not seed_file.exists():
            return []
        return [line.strip().upper() for line in seed_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    def filtered_symbols(self) -> list[dict]:
        out: list[dict] = []
        min_cap = int(self.config.universe["min_market_cap"])
        max_cap = int(self.config.universe["max_market_cap"])
        allowed = set(self.config.universe["allowed_buckets"])
        limit = int(self.config.universe["max_symbols_per_scan"])
        for symbol in self.seed_symbols()[:limit]:
            profile = self.provider.get_profile(symbol)
            mcap = profile.get("market_cap")
            bucket = market_cap_bucket(mcap)
            if mcap is None:
                continue
            if mcap < min_cap or mcap > max_cap:
                continue
            if bucket not in allowed:
                continue
            out.append({
                "symbol": symbol,
                "source": self.provider.name,
                "sector": profile.get("sector"),
                "market_cap": int(mcap),
                "bucket": bucket,
                "active": True,
                "updated_ts": __import__("datetime").datetime.now(__import__("datetime").UTC).replace(tzinfo=None),
            })
        return out
