from __future__ import annotations

from pathlib import Path
import json
import requests


class FREDMacroAdapter:
    def __init__(self, api_key: str = '', cache_dir: str | Path = 'data/raw/fred'):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _series_obs(self, series_id: str) -> list[dict]:
        params = {'series_id': series_id, 'file_type': 'json'}
        if self.api_key:
            params['api_key'] = self.api_key
        try:
            r = requests.get('https://api.stlouisfed.org/fred/series/observations', params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            return data.get('observations') or []
        except Exception:
            return []

    def latest_value(self, series_id: str) -> float | None:
        obs = self._series_obs(series_id)
        for row in reversed(obs):
            val = row.get('value')
            if val not in (None, '.', ''):
                try:
                    return float(val)
                except Exception:
                    return None
        return None

    def risk_regime_score(self) -> float:
        vix = self.latest_value('VIXCLS')
        dgs10 = self.latest_value('DGS10')
        score = 0.5
        if vix is not None:
            score += max(-0.25, min(0.25, (20.0 - vix) / 40.0))
        if dgs10 is not None:
            score += max(-0.10, min(0.10, (4.0 - dgs10) / 20.0))
        return round(max(0.0, min(1.0, score)), 4)
