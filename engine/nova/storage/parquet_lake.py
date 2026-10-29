from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

try:
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore
except Exception:
    pa = None
    pq = None


class ParquetLake:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.format = "parquet" if pa is not None and pq is not None else "csv"

    def write_batch(self, name: str, rows: list[dict], ts: datetime | None = None, symbol: str | None = None) -> Path | None:
        if not rows:
            return None
        ts = ts or datetime.utcnow()
        date_part = ts.strftime("%Y-%m-%d")
        target = self.root / name / f"date={date_part}"
        if symbol:
            target = target / f"symbol={symbol}"
        target.mkdir(parents=True, exist_ok=True)
        suffix = "parquet" if self.format == "parquet" else "csv"
        out = target / f"{name}_{ts.strftime('%Y%m%dT%H%M%S%f')}.{suffix}"
        df = pd.DataFrame(rows)
        # Keep a stable column order for better compression and easier diffs.
        df = df.reindex(sorted(df.columns), axis=1)
        if self.format == "parquet":
            table = pa.Table.from_pandas(df, preserve_index=False)
            pq.write_table(
                table,
                out,
                compression="zstd",
                use_dictionary=True,
                row_group_size=min(max(len(df), 2048), 100000),
                write_statistics=True,
            )
        else:
            df.to_csv(out, index=False)
        return out

    def collapse_symbol_summary(self, snapshot_name: str) -> int:
        source_root = self.root / snapshot_name
        if not source_root.exists():
            return 0
        written = 0
        pattern = "*.parquet" if self.format == "parquet" else "*.csv"
        for day_dir in source_root.glob("date=*"):
            rows = []
            for src_file in day_dir.rglob(pattern):
                if src_file.name.startswith("_daily_summary"):
                    continue
                df = pd.read_parquet(src_file) if src_file.suffix == ".parquet" else pd.read_csv(src_file)
                if df.empty:
                    continue
                if "symbol" in df.columns:
                    top = df.sort_values(["score"], ascending=False).head(1) if "score" in df.columns else df.head(1)
                    rows.extend(top.to_dict(orient="records"))
            if rows:
                summary_df = pd.DataFrame(rows).reindex(sorted(pd.DataFrame(rows).columns), axis=1)
                if self.format == "parquet":
                    out = day_dir / "_daily_summary.parquet"
                    pq.write_table(
                        pa.Table.from_pandas(summary_df, preserve_index=False),
                        out,
                        compression="zstd",
                        use_dictionary=True,
                        row_group_size=min(max(len(summary_df), 2048), 100000),
                        write_statistics=True,
                    )
                else:
                    out = day_dir / "_daily_summary.csv"
                    summary_df.to_csv(out, index=False)
                written += 1
        return written
