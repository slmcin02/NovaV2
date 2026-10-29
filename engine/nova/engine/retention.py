from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


def compact_old_snapshots(lake_root: str | Path, snapshot_name: str, retention_days: int = 60) -> int:
    root = Path(lake_root) / snapshot_name
    if not root.exists():
        return 0
    cutoff = datetime.utcnow().date() - timedelta(days=retention_days)
    removed = 0
    for day_dir in root.glob("date=*"):
        try:
            day = datetime.strptime(day_dir.name.split("=")[1], "%Y-%m-%d").date()
        except Exception:
            continue
        if day >= cutoff:
            continue
        for path in day_dir.rglob("*.parquet"):
            if path.name == "_daily_summary.parquet":
                continue
            path.unlink(missing_ok=True)
            removed += 1
        for child in sorted(day_dir.rglob("*"), reverse=True):
            if child.is_dir():
                try:
                    next(child.iterdir())
                except StopIteration:
                    child.rmdir()
    return removed
