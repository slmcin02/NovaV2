from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd

from nova.models import FeatureRow


def _apply_slippage(price: float, bps: float, side: str) -> float:
    mult = 1.0 + (bps / 10000.0) if side.lower() == "buy" else 1.0 - (bps / 10000.0)
    return round(price * mult, 4)


@dataclass(slots=True)
class PaperDecision:
    action: str
    reason: str
    fill_price: float | None = None


class PaperBroker:
    def __init__(self, store, entry_slippage_bps: float = 15, exit_slippage_bps: float = 20):
        self.store = store
        self.entry_slippage_bps = entry_slippage_bps
        self.exit_slippage_bps = exit_slippage_bps

    def open_position(self, row: FeatureRow, ts: datetime | None = None) -> str:
        ts = ts or datetime.now(UTC).replace(tzinfo=None)
        position_id = str(uuid4())
        order_id = str(uuid4())
        fill_id = str(uuid4())
        fill_price = _apply_slippage(float(row.ask), self.entry_slippage_bps, "buy")
        order = pd.DataFrame([{
            "order_id": order_id,
            "created_ts": ts,
            "status": "filled",
            "symbol": row.symbol,
            "contract_symbol": row.contract_symbol,
            "side": "buy",
            "qty": int(row.suggested_contracts),
            "limit_price": float(row.ask),
            "fill_price": fill_price,
            "notes": f"score={row.score} tags={row.strategy_tags}",
        }])
        position = pd.DataFrame([{
            "position_id": position_id,
            "opened_ts": ts,
            "closed_ts": None,
            "status": "open",
            "symbol": row.symbol,
            "contract_symbol": row.contract_symbol,
            "expiration": row.expiration,
            "strike": row.strike,
            "right": row.right,
            "qty": int(row.suggested_contracts),
            "market_cap": row.market_cap,
            "sector": row.sector,
            "entry_price": fill_price,
            "current_price": fill_price,
            "exit_price": None,
            "score_at_entry": row.score,
            "tags": row.strategy_tags,
            "unrealized_return": 0.0,
            "realized_return": None,
            "exit_reason": None,
        }])
        fill = pd.DataFrame([{
            "fill_id": fill_id,
            "fill_ts": ts,
            "order_id": order_id,
            "position_id": position_id,
            "side": "buy",
            "qty": int(row.suggested_contracts),
            "fill_price": fill_price,
            "notes": "paper entry",
        }])
        self.store.insert_dataframe("paper_orders", order)
        self.store.insert_dataframe("paper_positions", position)
        self.store.insert_dataframe("paper_fills", fill)
        return position_id

    def mark_to_market(self, quotes_df: pd.DataFrame) -> int:
        if quotes_df.empty:
            return 0
        positions = self.store.conn.execute("SELECT * FROM paper_positions WHERE status = 'open'").df()
        if positions.empty:
            return 0
        updated = 0
        quotes = quotes_df.set_index("contract_symbol")
        for _, pos in positions.iterrows():
            contract = pos["contract_symbol"]
            if contract not in quotes.index:
                continue
            q = quotes.loc[contract]
            current = float(q.get("mid", q.get("ask", pos["current_price"])))
            ret = (current - float(pos["entry_price"])) / max(float(pos["entry_price"]), 0.01)
            self.store.conn.execute(
                "UPDATE paper_positions SET current_price = ?, unrealized_return = ? WHERE position_id = ?",
                [current, ret, pos["position_id"]],
            )
            updated += 1
        return updated

    def close_position(self, position_id: str, reason: str, quote_price: float, ts: datetime | None = None) -> PaperDecision:
        ts = ts or datetime.now(UTC).replace(tzinfo=None)
        df = self.store.conn.execute("SELECT * FROM paper_positions WHERE position_id = ?", [position_id]).df()
        if df.empty:
            return PaperDecision(action="ignore", reason="missing_position")
        pos = df.iloc[0]
        if pos["status"] != "open":
            return PaperDecision(action="ignore", reason="already_closed")
        order_id = str(uuid4())
        fill_id = str(uuid4())
        fill_price = _apply_slippage(float(quote_price), self.exit_slippage_bps, "sell")
        realized = (fill_price - float(pos["entry_price"])) / max(float(pos["entry_price"]), 0.01)
        self.store.insert_dataframe("paper_orders", pd.DataFrame([{
            "order_id": order_id,
            "created_ts": ts,
            "status": "filled",
            "symbol": pos["symbol"],
            "contract_symbol": pos["contract_symbol"],
            "side": "sell",
            "qty": int(pos["qty"]),
            "limit_price": float(quote_price),
            "fill_price": fill_price,
            "notes": reason,
        }]))
        self.store.insert_dataframe("paper_fills", pd.DataFrame([{
            "fill_id": fill_id,
            "fill_ts": ts,
            "order_id": order_id,
            "position_id": position_id,
            "side": "sell",
            "qty": int(pos["qty"]),
            "fill_price": fill_price,
            "notes": reason,
        }]))
        self.store.conn.execute(
            "UPDATE paper_positions SET status = 'closed', closed_ts = ?, exit_price = ?, current_price = ?, realized_return = ?, exit_reason = ? WHERE position_id = ?",
            [ts, fill_price, fill_price, realized, reason, position_id],
        )
        return PaperDecision(action="close", reason=reason, fill_price=fill_price)


class PaperRiskEngine:
    def __init__(self, stop_loss_pct: float, take_profit_pct: float, thesis_break_score: float):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.thesis_break_score = thesis_break_score

    def evaluate(self, entry_price: float, current_price: float, current_score: float) -> PaperDecision:
        ret = (current_price - entry_price) / max(entry_price, 0.01)
        if ret <= -self.stop_loss_pct:
            return PaperDecision(action="close", reason="stop_loss")
        if ret >= self.take_profit_pct:
            return PaperDecision(action="close", reason="take_profit")
        if current_score < self.thesis_break_score:
            return PaperDecision(action="close", reason="thesis_break")
        return PaperDecision(action="hold", reason="hold")
