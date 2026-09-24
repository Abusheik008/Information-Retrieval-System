from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .rag.generator import Generator
from .rag.ingest import ingest
from .rag.retriever import Retriever


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "aapl_2022_q3_10q.pdf"
ARTIFACT_DIR = ROOT / "artifacts"
INDEX_PATH = ARTIFACT_DIR / "index.json"

app = FastAPI(title="SmartDataSolutions Multimodal RAG")
retriever: Retriever | None = None
generator = Generator()


class Query(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    limit: int = Field(default=6, ge=1, le=12)


@app.on_event("startup")
def load_index() -> None:
    global retriever
    if not INDEX_PATH.exists():
        ingest(PDF_PATH, ARTIFACT_DIR)
    retriever = Retriever(INDEX_PATH)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "indexed": retriever is not None, "document": PDF_PATH.name}


@app.post("/api/query")
def query(request: Query) -> dict:
    if retriever is None:
        raise HTTPException(503, "The document index is not loaded.")
    evidence = retriever.search(request.question, request.limit)
    return {
        "answer": generator.answer(request.question, evidence),
        "evidence": [item.to_dict() for item in evidence],
        "modalities": sorted({item.modality for item in evidence}),
    }


@app.get("/api/figure/{path:path}")
def figure(path: str):
    target = (ARTIFACT_DIR / path).resolve()
    if ARTIFACT_DIR.resolve() not in target.parents or not target.is_file():
        raise HTTPException(404, "Figure not found")
    return FileResponse(target)
