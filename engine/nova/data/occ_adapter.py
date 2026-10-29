from __future__ import annotations

from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://marketdata.theocc.com/daily-open-interest"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/csv,*/*",
}


class OCCAdapter:
    def __init__(self, cache_dir: str | Path = "data/raw/occ"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_day(self, day: date) -> Path | None:
        out = self.cache_dir / f"{day.strftime('%Y%m%d')}.csv"
        if out.exists():
            return out
        params = {"reportDate": day.strftime("%m/%d/%Y"), "action": "download", "format": "csv"}
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=40)
            if resp.status_code != 200 or not resp.text.strip():
                return None
            out.write_bytes(resp.content)
            return out
        except Exception:
            return None


    def open_interest_for_symbol(self, symbol: str, day: date) -> int:
        path = self.download_day(day)
        if path is None or not path.exists():
            return 0
        try:
            import pandas as pd
            df = pd.read_csv(path)
        except Exception:
            return 0
        if df.empty:
            return 0
        cols = {str(c).strip().lower(): c for c in df.columns}
        symbol_col = cols.get('underlying_symbol') or cols.get('symbol') or cols.get('underlyingsymbol') or cols.get('root')
        oi_col = cols.get('open_interest') or cols.get('openinterest') or cols.get('oi')
        if symbol_col is None or oi_col is None:
            return 0
        try:
            hit = df[df[symbol_col].astype(str).str.upper() == symbol.upper()]
            if hit.empty:
                return 0
            return int(pd.to_numeric(hit[oi_col], errors='coerce').fillna(0).sum())
        except Exception:
            return 0
