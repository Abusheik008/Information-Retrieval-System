from __future__ import annotations

import os
from typing import Iterable

import httpx

from .models import Evidence


OUT_OF_SCOPE_MESSAGE = (
    "This question is beyond my scope. I can only answer questions supported by "
    "the supplied Apple Q3 2022 10-Q PDF, including its text, tables, and figures."
)


def _context(evidence: Iterable[Evidence]) -> str:
    return "\n\n".join(
        f"[Page {item.page} | {item.modality} | score {item.score:.2f}]\n{item.text}"
        for item in evidence
    )


def _extractive_answer(question: str, evidence: list[Evidence]) -> str:
    if not evidence:
        return "I could not find supporting evidence in the supplied PDF."
    sentences = []
    question_terms = set(question.lower().split())
    for item in evidence:
        for sentence in item.text.replace(";", ".").split("."):
            if len(sentence.strip()) > 30:
                overlap = sum(term in sentence.lower() for term in question_terms)
                sentences.append((overlap, sentence.strip(), item.page))
    selected = sorted(sentences, reverse=True)[:3]
    if not selected:
        return evidence[0].text[:900]
    return " ".join(f"{sentence} (page {page})" for _, sentence, page in selected)


class Generator:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def answer(self, question: str, evidence: list[Evidence]) -> str:
        if not evidence:
            return OUT_OF_SCOPE_MESSAGE
        if not self.api_key:
            return _extractive_answer(question, evidence)
        prompt = (
            "Answer only from the supplied evidence. Be concise, preserve units and dates, "
            "and cite every factual claim using [p. N]. If evidence is insufficient, say so. "
            "For figures, describe only what the evidence supports.\n\n"
            f"Question: {question}\n\nEvidence:\n{_context(evidence)}"
        )
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": "You are a precise PDF research assistant."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
