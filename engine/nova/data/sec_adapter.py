from __future__ import annotations

from datetime import timedelta
from typing import Any

import requests

from nova.utils.market import now_ct

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
DILUTION_FORMS = {"S-3", "S-1", "424B5", "424B3", "424B2", "424B4", "424B7", "POS AM", "FWP"}


class SECAdapter:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._ticker_map: dict[str, str] | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _get_json(self, url: str) -> dict[str, Any] | None:
        try:
            resp = requests.get(url, headers=self.headers, timeout=20)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def load_ticker_map(self) -> dict[str, str]:
        if self._ticker_map is not None:
            return self._ticker_map
        data = self._get_json(SEC_TICKERS_URL) or {}
        out: dict[str, str] = {}
        for _, row in data.items():
            try:
                out[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
            except Exception:
                continue
        self._ticker_map = out
        return out

    def has_recent_dilution_risk(self, symbol: str, lookback_days: int = 30) -> tuple[bool, str]:
        cik = self.load_ticker_map().get(symbol.upper())
        if not cik:
            return False, "no_cik"
        sub = self._get_json(SUBMISSIONS_URL.format(cik=cik))
        if not sub:
            return False, "no_submissions"
        recent = ((sub.get("filings") or {}).get("recent")) or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        cutoff = now_ct().date() - timedelta(days=lookback_days)
        for form, filing_date in zip(forms, dates):
            try:
                day = now_ct().date().fromisoformat(filing_date)
            except Exception:
                continue
            if day >= cutoff and str(form).upper() in DILUTION_FORMS:
                return True, str(form)
        return False, "ok"
