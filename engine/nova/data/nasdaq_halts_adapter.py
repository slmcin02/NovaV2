from __future__ import annotations

from pathlib import Path
import io
import pandas as pd
import requests

URL = "https://www.nasdaqtrader.com/dynamic/symdir/tradinghalts.txt"


class NasdaqHaltsAdapter:
    def __init__(self, cache_dir: str | Path = "data/raw/nasdaq"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_current(self) -> Path | None:
        out = self.cache_dir / "tradinghalts.txt"
        try:
            r = requests.get(URL, timeout=20)
            if r.status_code == 200 and r.text.strip():
                out.write_text(r.text, encoding="utf-8")
                return out
        except Exception:
            pass
        return out if out.exists() else None

    def parse_file(self, path: str | Path) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = [ln for ln in text.splitlines() if ln and not ln.startswith("File Creation Time")]
        if not lines:
            return pd.DataFrame()
        try:
            return pd.read_csv(io.StringIO("\n".join(lines)), sep="|")
        except Exception:
            return pd.DataFrame()

    def current_halts(self) -> pd.DataFrame:
        path = self.download_current()
        if path is None:
            return pd.DataFrame()
        df = self.parse_file(path)
        if df.empty:
            return df
        if "Issue Symbol" in df.columns:
            df["Issue Symbol"] = df["Issue Symbol"].astype(str).str.upper()
        return df

    def is_symbol_halted(self, symbol: str) -> bool:
        df = self.current_halts()
        if df.empty or "Issue Symbol" not in df.columns:
            return False
        return bool((df["Issue Symbol"] == symbol.upper()).any())
