from pathlib import Path

from src.rag.generator import OUT_OF_SCOPE_MESSAGE, Generator
from src.rag.retriever import Retriever


def test_unrelated_question_returns_no_evidence():
    retriever = Retriever(Path("artifacts/index.json"))
    evidence = retriever.search("What is the weather in California today?")
    assert evidence == []
    assert Generator().answer("What is the weather in California today?", evidence) == OUT_OF_SCOPE_MESSAGE
