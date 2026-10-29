from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, UTC
import sqlite3
import pandas as pd

try:
    import duckdb as _duckdb  # type: ignore
except Exception:
    _duckdb = None


def _qident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


class _CursorResult:
    def __init__(self, cursor, columns=None):
        self._cursor = cursor
        self._columns = columns or [d[0] for d in (cursor.description or [])]

    def df(self) -> pd.DataFrame:
        rows = self._cursor.fetchall()
        return pd.DataFrame(rows, columns=self._columns)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _SQLiteConn:
    def __init__(self, path: str):
        self._raw = sqlite3.connect(path)
        self._raw.execute("PRAGMA foreign_keys = ON")
        self._raw.row_factory = None

    def execute(self, sql: str, params=None):
        cur = self._raw.execute(sql, params or [])
        self._raw.commit()
        return _CursorResult(cur)

    def close(self):
        self._raw.close()


class DuckDBStore:
    def __init__(self, db_path: str | Path, schema_path: str | Path = "sql/schema.sql"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.backend = "duckdb" if _duckdb is not None else "sqlite"
        if _duckdb is not None:
            self.conn = _duckdb.connect(self.db_path)
            schema = Path(schema_path).read_text(encoding="utf-8")
            self.conn.execute(schema)
            self._run_migrations()
        else:
            sqlite_path = self.db_path if self.db_path.endswith(".sqlite") else self.db_path + ".sqlite"
            self.conn = _SQLiteConn(sqlite_path)
            schema = Path(schema_path).read_text(encoding="utf-8")
            # simple compatibility cleanup for sqlite fallback
            schema = schema.replace("DOUBLE", "REAL").replace("BIGINT", "INTEGER").replace("BOOLEAN", "INTEGER")
            for stmt in [x.strip() for x in schema.split(";") if x.strip()]:
                self.conn.execute(stmt)
            self._run_migrations()



    def _ensure_column(self, table: str, column: str, col_type: str) -> None:
        if self.backend == "duckdb":
            cols = self.conn.execute(f"PRAGMA table_info('{table}')").df()["name"].tolist()
            if column not in cols:
                self.conn.execute(f"ALTER TABLE {_qident(table)} ADD COLUMN {_qident(column)} {col_type}")
            return
        cols = [r[1] for r in self.conn._raw.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            self.conn._raw.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            self.conn._raw.commit()

    def _run_migrations(self) -> None:
        # additive migrations for older local DB files
        signal_cols = {
            "market_cap": "BIGINT" if self.backend == "duckdb" else "INTEGER",
            "sector": "TEXT",
            "occ_open_interest": "BIGINT" if self.backend == "duckdb" else "INTEGER",
            "sec_ftd_qty": "BIGINT" if self.backend == "duckdb" else "INTEGER",
            "macro_regime_score": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "technical_score": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "sector_etf": "TEXT",
            "sector_momentum_20d": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "sector_coherence": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "reflexivity_multiplier": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "spin_coherence": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "spin_lock": "BOOLEAN" if self.backend == "duckdb" else "INTEGER",
            "float_turnover": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "hidden_liquidity_score": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "synth_flow_score": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "sci_velocity": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "sci_acceleration": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "failure_tag": "TEXT",
            "calibrated_win_prob": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "score_lcb": "DOUBLE" if self.backend == "duckdb" else "REAL",
            "event_risk": "TEXT",
            "assignment_risk": "TEXT",
            "blocked_market_ops": "BOOLEAN" if self.backend == "duckdb" else "INTEGER",
            "expected_slippage_bps": "DOUBLE" if self.backend == "duckdb" else "REAL",
        }
        for col, col_type in signal_cols.items():
            self._ensure_column("signals", col, col_type)
        self._ensure_column("paper_positions", "market_cap", "BIGINT" if self.backend == "duckdb" else "INTEGER")
        self._ensure_column("paper_positions", "sector", "TEXT")
        self._create_indexes()

    def _create_indexes(self) -> None:
        statements = [
            "CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(signal_ts)",
            "CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts ON signals(symbol, signal_ts)",
            "CREATE INDEX IF NOT EXISTS idx_signals_contract ON signals(contract_symbol)",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol_entry ON trades(symbol, entry_ts)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(alert_ts)",
            "CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status)",
            "CREATE INDEX IF NOT EXISTS idx_provider_health_ts ON provider_health(check_ts)",
            "CREATE INDEX IF NOT EXISTS idx_free_source_events_ts ON free_source_events(event_ts)",
            "CREATE INDEX IF NOT EXISTS idx_free_source_events_source ON free_source_events(source)",
        ]
        if self.backend == "duckdb":
            for stmt in statements:
                self.conn.execute(stmt)
            return
        for stmt in statements:
            self.conn._raw.execute(stmt)
        self.conn._raw.commit()

    def insert_dataframe(self, table: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        if self.backend == "duckdb":
            self.conn.register("tmp_df", df)
            cols = ", ".join(_qident(c) for c in df.columns)
            self.conn.execute(f"INSERT INTO {_qident(table)} ({cols}) SELECT {cols} FROM tmp_df")
            self.conn.unregister("tmp_df")
            return
        df.to_sql(table, self.conn._raw, if_exists="append", index=False)
        self.conn._raw.commit()

    def upsert_universe(self, rows: list[dict]) -> None:
        if not rows:
            return
        if self.backend == "duckdb":
            df = pd.DataFrame(rows)
            self.conn.register("u_df", df)
            self.conn.execute("""
                INSERT OR REPLACE INTO universe
                SELECT symbol, source, sector, market_cap, bucket, active, updated_ts
                FROM u_df
            """)
            self.conn.unregister("u_df")
            return
        for row in rows:
            self.conn.execute(
                "INSERT OR REPLACE INTO universe (symbol, source, sector, market_cap, bucket, active, updated_ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [row.get("symbol"), row.get("source"), row.get("sector"), row.get("market_cap"), row.get("bucket"), int(bool(row.get("active"))), str(row.get("updated_ts"))],
            )

    def signal_rows(self, days: int = 365) -> pd.DataFrame:
        if self.backend == "duckdb":
            return self.conn.execute(
                "SELECT * FROM signals WHERE signal_ts >= now() - (? || ' days')::INTERVAL",
                [days],
            ).df()
        cutoff = (datetime.now(UTC) - timedelta(days=days)).replace(tzinfo=None).isoformat(sep=" ")
        return self.conn.execute("SELECT * FROM signals WHERE signal_ts >= ?", [cutoff]).df()

    def completed_trades(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM trades").df()

    def recent_alert_keys(self, hours: int) -> set[str]:
        if self.backend == "duckdb":
            df = self.conn.execute(
                "SELECT dedupe_key FROM alerts WHERE alert_ts >= now() - (? || ' hours')::INTERVAL",
                [hours],
            ).df()
        else:
            cutoff = (datetime.now(UTC) - timedelta(hours=hours)).replace(tzinfo=None).isoformat(sep=" ")
            df = self.conn.execute("SELECT dedupe_key FROM alerts WHERE alert_ts >= ?", [cutoff]).df()
        return set(df["dedupe_key"].tolist()) if not df.empty else set()

    def open_paper_positions(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM paper_positions WHERE status = 'open'").df()

    def health_event(self, severity: str, component: str, message: str, payload_json: str = "{}") -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
        self.conn.execute(
            "INSERT INTO health_events VALUES (?, ?, ?, ?, ?)",
            [now, severity, component, message, payload_json],
        )

    def provider_health(self, provider: str, status: str, detail: str) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
        self.conn.execute(
            "INSERT INTO provider_health VALUES (?, ?, ?, ?)",
            [now, provider, status, detail],
        )

    def upsert_edge_daily(self, rows: list[dict] | pd.DataFrame) -> None:
        if isinstance(rows, pd.DataFrame):
            df = rows
        else:
            if not rows:
                return
            df = pd.DataFrame(rows)
        if df.empty:
            return
        if self.backend == "duckdb":
            self.conn.register("e_df", df)
            self.conn.execute("""
                INSERT OR REPLACE INTO edge_daily
                SELECT asof_date, symbol, finra_short_ratio, occ_open_interest, edgar_dilution_flag
                FROM e_df
            """)
            self.conn.unregister("e_df")
            return
        for _, row in df.iterrows():
            self.conn.execute(
                "INSERT OR REPLACE INTO edge_daily (asof_date, symbol, finra_short_ratio, occ_open_interest, edgar_dilution_flag) VALUES (?, ?, ?, ?, ?)",
                [str(row["asof_date"]), row["symbol"], float(row["finra_short_ratio"]), int(row["occ_open_interest"]), int(bool(row["edgar_dilution_flag"]))],
            )
