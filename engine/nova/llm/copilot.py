from __future__ import annotations

from pathlib import Path
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimpleMemoryIndex:
    def __init__(self, store_dir: str | Path = "data/memory"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "tfidf.pkl"

    def build(self, docs: list[dict]) -> None:
        texts = [d["text"] for d in docs]
        vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        matrix = vec.fit_transform(texts)
        with self.index_path.open("wb") as f:
            pickle.dump({"docs": docs, "vectorizer": vec, "matrix": matrix}, f)

    def query(self, text: str, k: int = 5) -> list[dict]:
        if not self.index_path.exists():
            return []
        with self.index_path.open("rb") as f:
            payload = pickle.load(f)
        query_vec = payload["vectorizer"].transform([text])
        sims = cosine_similarity(query_vec, payload["matrix"]).ravel()
        order = sims.argsort()[::-1][:k]
        return [{**payload["docs"][i], "similarity": float(sims[i])} for i in order]
