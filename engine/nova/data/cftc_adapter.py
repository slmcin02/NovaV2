from __future__ import annotations

from pathlib import Path
import requests
import pandas as pd


class CFTCAdapter:
    def __init__(self, cache_dir: str | Path = 'data/raw/cftc'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def latest_financial_futures(self) -> pd.DataFrame:
        url = 'https://www.cftc.gov/dea/newcot/FinFutWk.txt'
        out = self.cache_dir / 'FinFutWk.txt'
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            out.write_text(r.text, encoding='utf-8')
        except Exception:
            if not out.exists():
                return pd.DataFrame()
        try:
            return pd.read_csv(out)
        except Exception:
            return pd.DataFrame()
