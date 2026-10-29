from __future__ import annotations

from nova.config import load_config
from nova.data.provider_router import get_provider


def test_fallback_provider_builds():
    cfg = load_config()
    provider = get_provider(cfg, 'polygon,yfinance,replay')
    assert getattr(provider, 'name', '') == 'fallback'


def test_replay_provider_can_use_expanded_fixture():
    cfg = load_config()
    provider = get_provider(cfg, 'replay')
    provider.default_fixture_name = 'sample_option_scan_expanded.csv'
    rows = provider.scan_calls('PLTR', max_dte=90, min_dte=7, max_ask=2.5)
    assert len(rows) >= 3
