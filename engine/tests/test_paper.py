from __future__ import annotations

from datetime import date
import pandas as pd

from nova.storage.duckdb_store import DuckDBStore
from nova.engine.paper import PaperBroker, PaperRiskEngine
from nova.models import FeatureRow


def sample_row() -> FeatureRow:
    return FeatureRow(
        symbol="PLTR",
        contract_symbol="PLTR260619C00045000",
        expiration=date(2026, 6, 19),
        strike=45.0,
        right="call",
        bid=1.18,
        ask=1.24,
        mid=1.21,
        spread_pct=0.048,
        implied_vol=0.42,
        underlying_price=41.0,
        dte=88,
        delta=0.46,
        volume=420,
        oi=2200,
        market_cap=9500000000,
        sector="Technology",
        finra_short_ratio=0.43,
        insider_buy_flag=False,
        edgar_dilution_flag=False,
        momentum_20d=0.11,
        vix_value=21.5,
        m_sigma=0.35,
        technical_score=0.8,
        score=84.0,
        elite=True,
        strategy_tags="momentum_breakout,cheap_vol",
        suggested_contracts=2,
    )


def test_open_and_close_paper_position(tmp_path):
    db = DuckDBStore(tmp_path / "test.duckdb", schema_path="sql/schema.sql")
    broker = PaperBroker(db)
    pid = broker.open_position(sample_row())
    open_df = db.open_paper_positions()
    assert len(open_df) == 1
    quotes = pd.DataFrame([{"contract_symbol": "PLTR260619C00045000", "mid": 1.85, "ask": 1.90}])
    assert broker.mark_to_market(quotes) == 1
    decision = broker.close_position(pid, "take_profit", 1.90)
    assert decision.action == "close"
    closed = db.conn.execute("SELECT status FROM paper_positions WHERE position_id = ?", [pid]).fetchone()[0]
    assert closed == "closed"


def test_risk_engine_triggers():
    eng = PaperRiskEngine(stop_loss_pct=0.18, take_profit_pct=0.45, thesis_break_score=50)
    assert eng.evaluate(1.0, 0.75, 80).reason == "stop_loss"
    assert eng.evaluate(1.0, 1.55, 80).reason == "take_profit"
    assert eng.evaluate(1.0, 1.05, 40).reason == "thesis_break"
