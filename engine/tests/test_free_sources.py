from __future__ import annotations

from pathlib import Path
import zipfile

from nova.data.nasdaq_halts_adapter import NasdaqHaltsAdapter
from nova.data.sec_ftd_adapter import SECFTDAdapter
from nova.data.fred_adapter import FREDMacroAdapter


def test_nasdaq_halts_parser(tmp_path: Path):
    text = """Issue Symbol|Issue Name|Market|Reason Code|Pause Threshold Price|Halt Time|Resume Date|Resume Time
AAPL|Apple|NASDAQ|T1||10:00:00|2026-03-24|10:05:00
"""
    p = tmp_path / "tradinghalts.txt"
    p.write_text(text, encoding="utf-8")
    df = NasdaqHaltsAdapter(tmp_path).parse_file(p)
    assert not df.empty
    assert df.iloc[0]["Issue Symbol"] == "AAPL"


def test_sec_ftd_parser(tmp_path: Path):
    p = tmp_path / "cnsfails202603a.zip"
    raw = """SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)
20260314|000000|PLTR|123456
"""
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("ftd.txt", raw)
    df = SECFTDAdapter(tmp_path).parse_zip(p)
    assert not df.empty
    assert "SYMBOL" in df.columns


def test_fred_regime_score_range(monkeypatch):
    adapter = FREDMacroAdapter("")
    vals = {"VIXCLS": 18.0, "DGS10": 4.0}
    monkeypatch.setattr(adapter, "latest_value", lambda s: vals.get(s))
    score = adapter.risk_regime_score()
    assert 0.0 <= score <= 1.0
