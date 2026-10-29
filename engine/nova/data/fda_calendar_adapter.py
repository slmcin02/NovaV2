from __future__ import annotations

from pathlib import Path
import re
import requests


class FDACalendarAdapter:
    def __init__(self, cache_dir: str | Path = 'data/raw/fda'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def advisory_events(self) -> list[dict]:
        url = 'https://www.fda.gov/advisory-committees/advisory-committee-calendar'
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            html = r.text
        except Exception:
            return []
        titles = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
        out = []
        for href, title in titles[:25]:
            clean = re.sub(r'<[^>]+>', ' ', title)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if clean:
                out.append({'title': clean, 'href': href})
        return out
