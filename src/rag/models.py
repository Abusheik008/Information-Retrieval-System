from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


Modality = Literal["text", "table", "figure", "mixed"]


@dataclass
class Evidence:
    chunk_id: str
    page: int
    modality: Modality
    text: str
    score: float = 0.0
    image_path: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
