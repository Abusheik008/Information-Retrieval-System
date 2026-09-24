from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .models import Evidence


STOPWORDS = {"the", "a", "an", "of", "to", "in", "and", "is", "was", "what", "were", "for", "on"}


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9$%]+", value.lower()) if token not in STOPWORDS]


class Retriever:
    def __init__(self, index_path: Path):
        self.records = [Evidence(**item) for item in json.loads(index_path.read_text(encoding="utf-8"))]
        self.document_frequency = Counter()
        for record in self.records:
            self.document_frequency.update(set(_tokens(record.text)))

    def search(self, question: str, limit: int = 6) -> list[Evidence]:
        lowered = question.lower()
        if (
            re.search(r"\b(current|today|now|latest|weather|forecast)\b", lowered)
            and not re.search(r"\b(filing|document|pdf|report|quarter|ended|as of|2022|2021)\b", lowered)
        ):
            return []
        requested_years = {int(year) for year in re.findall(r"\b(20\d{2})\b", lowered)}
        if requested_years and requested_years - {2021, 2022}:
            return []
        query = set(_tokens(question))
        if not query:
            return []
        total = max(len(self.records), 1)
        ranked: list[Evidence] = []
        candidates: list[tuple[Evidence, int]] = []
        for record in self.records:
            terms = _tokens(record.text)
            counts = Counter(terms)
            score = 0.0
            matched_terms = 0
            for token in query:
                if token in counts:
                    matched_terms += 1
                    idf = math.log((total + 1) / (self.document_frequency[token] + 1)) + 1
                    score += (1 + math.log(counts[token])) * idf
            if record.modality == "table" and any(word in question.lower() for word in ("table", "revenue", "income", "assets", "cash", "sales")):
                score *= 1.15
            if record.modality == "figure" and any(word in question.lower() for word in ("figure", "chart", "image", "graph", "shown", "pictured")):
                score *= 2.5
            record.score = score
            if score > 0:
                candidates.append((record, matched_terms))
        # Require more than a generic word overlap. This prevents questions
        # such as current stock-price or weather requests from retrieving
        # loosely related filing paragraphs.
        for record, matched_terms in candidates:
            if matched_terms >= 2:
                ranked.append(record)
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:limit]
