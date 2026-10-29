from __future__ import annotations

from datetime import date
from pathlib import Path
import io
import zipfile
import pandas as pd
import requests

HEADERS = {"User-Agent": "Stephen personal research stephen@example.com"}


class SECFTDAdapter:
    def __init__(self, cache_dir: str | Path = "data/raw/sec_ftd"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _candidate_names(self, day: date) -> list[str]:
        ym = day.strftime("%Y%m")
        prev_month = (date(day.year - (1 if day.month == 1 else 0), 12 if day.month == 1 else day.month - 1, 1)).strftime("%Y%m")
        return [f"cnsfails{ym}a.zip", f"cnsfails{ym}b.zip", f"cnsfails{prev_month}a.zip", f"cnsfails{prev_month}b.zip"]

    def download_latest(self, day: date) -> Path | None:
        base = "https://www.sec.gov/files/data/fails-deliver-data"
        for name in self._candidate_names(day):
            out = self.cache_dir / name
            if out.exists():
                return out
            try:
                r = requests.get(f"{base}/{name}", headers=HEADERS, timeout=30)
                if r.status_code == 200 and r.content:
                    out.write_bytes(r.content)
                    return out
            except Exception:
                continue
        return None

    def parse_zip(self, path: str | Path) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        try:
            with zipfile.ZipFile(p) as zf:
                names = zf.namelist()
                if not names:
                    return pd.DataFrame()
                raw = zf.read(names[0])
        except Exception:
            return pd.DataFrame()
        for sep in ['|', ',']:
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep)
                if len(df.columns) >= 3:
                    return df
            except Exception:
                continue
        return pd.DataFrame()

    def ftd_quantity_for_symbol(self, symbol: str, day: date | None = None) -> int:
        day = day or date.today()
        path = self.download_latest(day)
        if path is None:
            return 0
        df = self.parse_zip(path)
        if df.empty:
            return 0
        cols = {str(c).strip().lower(): c for c in df.columns}
        sym_col = cols.get('symbol') or cols.get('sym') or cols.get('ticker')
        qty_col = cols.get('quantity (fails)') or cols.get('quantity_fails') or cols.get('fail quantity') or cols.get('quantity')
        if sym_col is None or qty_col is None:
            return 0
        try:
            hit = df[df[sym_col].astype(str).str.upper() == symbol.upper()]
            if hit.empty:
                return 0
            return int(pd.to_numeric(hit[qty_col], errors='coerce').fillna(0).max())
        except Exception:
            return 0
