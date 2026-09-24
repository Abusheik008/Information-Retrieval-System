import json
from pathlib import Path

from src.rag.retriever import Retriever


def test_retriever_ranks_matching_record(tmp_path: Path):
    index = tmp_path / "index.json"
    index.write_text(json.dumps([
        {"chunk_id": "one", "page": 1, "modality": "text", "text": "Apple net sales increased."},
        {"chunk_id": "two", "page": 2, "modality": "text", "text": "The company reported operating income."},
    ]))
    results = Retriever(index).search("What happened to net sales?")
    assert results[0].chunk_id == "one"
