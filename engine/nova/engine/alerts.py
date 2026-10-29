from __future__ import annotations

import hashlib
import requests

from nova.models import FeatureRow


def make_dedupe_key(row: FeatureRow) -> str:
    raw = f"{row.symbol}|{row.contract_symbol}|{row.expiration}|{row.strike}|{row.score:.2f}|{row.elite}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def send_discord(webhook_url: str, row: FeatureRow) -> bool:
    if not webhook_url:
        return False
    content = (
        f"**{row.symbol} {row.contract_symbol or ''}**\n"
        f"score={row.score:.2f} elite={row.elite} ask={row.ask:.2f} dte={row.dte} "
        f"delta={row.delta:.2f} oi={row.oi} spread={row.spread_pct:.2%}\n"
        f"tags={row.strategy_tags}"
    )
    try:
        resp = requests.post(webhook_url, json={"content": content}, timeout=10)
        return resp.status_code < 300
    except Exception:
        return False
