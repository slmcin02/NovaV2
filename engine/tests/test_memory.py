from nova.llm.vector_memory import VectorMemory


def test_vector_memory_query(tmp_path):
    mem = VectorMemory(tmp_path / "memory.jsonl")
    mem.add("1", "PLTR score 84 momentum breakout", {"symbol": "PLTR"})
    mem.add("2", "SOFI score 78 short pressure", {"symbol": "SOFI"})
    hits = mem.query("PLTR breakout", top_k=2)
    assert hits
    assert hits[0]["metadata"]["symbol"] == "PLTR"
