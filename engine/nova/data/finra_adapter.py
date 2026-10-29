from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://cdn.finra.org/equity/regsho/daily"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.finra.org/",
    "Accept": "text/plain,*/*",
}


class FINRAAdapter:
    def __init__(self, cache_dir: str | Path = "data/raw/finra"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_day(self, day: date) -> Path | None:
        ymd = day.strftime("%Y%m%d")
        name = f"CNMSshvol{ymd}.txt"
        out = self.cache_dir / name
        if out.exists():
            return out
        try:
            resp = requests.get(f"{BASE}/{name}", headers=HEADERS, timeout=30)
            if resp.status_code != 200 or not resp.text.strip():
                return None
            out.write_bytes(resp.content)
            return out
        except Exception:
            return None

    def short_ratio_for_symbol(self, symbol: str, day: date) -> float:
        path = self.download_day(day)
        if path is None:
            return 0.0
        try:
            df = pd.read_csv(path, sep="|")
            row = df[df["Symbol"].astype(str).str.upper() == symbol.upper()]
            if row.empty:
                return 0.0
            short_vol = float(row.iloc[0]["ShortVolume"])
            total_vol = float(row.iloc[0]["TotalVolume"])
            return round(short_vol / total_vol, 6) if total_vol > 0 else 0.0
        except Exception:
            return 0.0
