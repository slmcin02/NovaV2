from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}")


def tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in TOKEN_RE.findall(text or "")]


class VectorMemory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, record_id: str, text: str, metadata: dict | None = None) -> None:
        row = {"id": record_id, "text": text, "metadata": metadata or {}}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        q = Counter(tokenize(text))
        if not q:
            return []
        q_norm = math.sqrt(sum(v * v for v in q.values()))
        scored = []
        for row in self._load():
            d = Counter(tokenize(row.get("text", "")))
            if not d:
                continue
            dot = sum(q[t] * d.get(t, 0) for t in q)
            d_norm = math.sqrt(sum(v * v for v in d.values()))
            sim = dot / max(q_norm * d_norm, 1e-9)
            if sim > 0:
                scored.append({**row, "score": sim})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
