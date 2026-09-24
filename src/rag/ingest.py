from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

from .models import Evidence


TABLE_HINTS = ("revenue", "net sales", "operating income", "assets", "liabilities", "cash flows")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    numeric_lines = sum(bool(re.search(r"\$?\(?\d[\d,]*(?:\.\d+)?\)?", line)) for line in lines)
    column_lines = sum(len(re.split(r"\s{2,}|\t", line)) >= 2 for line in lines)
    hint = any(term in text.lower() for term in TABLE_HINTS)
    return (numeric_lines >= 2 and column_lines >= 2) or (hint and numeric_lines >= 2)


def ingest(pdf_path: Path, artifact_dir: Path) -> list[Evidence]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    image_dir = artifact_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    records: list[Evidence] = []

    for page_number, page in enumerate(document, start=1):
        raw_text = page.get_text("text")
        text = _clean(raw_text)
        if text:
            modality = "table" if _looks_like_table(raw_text) else "text"
            records.append(Evidence(
                chunk_id=f"p{page_number}-text",
                page=page_number,
                modality=modality,
                text=text[:12000],
            ))

        # A page render is a dependable visual fallback for charts, diagrams,
        # and figures that are not stored as extractable PDF image objects.
        page_image = image_dir / f"page-{page_number}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False).save(page_image)
        records.append(Evidence(
            chunk_id=f"p{page_number}-visual",
            page=page_number,
            modality="figure",
            text=f"Figure/chart/image visual page {page_number}. Nearby text: {text[:1800]}",
            image_path=str(page_image.relative_to(artifact_dir)),
        ))

        for image_number, image in enumerate(page.get_images(full=True), start=1):
            xref = image[0]
            try:
                extracted = document.extract_image(xref)
                extension = extracted["ext"]
                output = image_dir / f"page-{page_number}-image-{image_number}.{extension}"
                output.write_bytes(extracted["image"])
                records.append(Evidence(
                    chunk_id=f"p{page_number}-figure-{image_number}",
                    page=page_number,
                    modality="figure",
                    text=f"Figure or embedded image on page {page_number}. Surrounding page text: {text[:1200]}",
                    image_path=str(output.relative_to(artifact_dir)),
                ))
            except (KeyError, RuntimeError):
                continue

    (artifact_dir / "index.json").write_text(
        json.dumps([record.to_dict() for record in records], indent=2),
        encoding="utf-8",
    )
    return records
