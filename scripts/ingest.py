from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.ingest import ingest

root = Path(__file__).resolve().parents[1]
records = ingest(root / "data" / "aapl_2022_q3_10q.pdf", root / "artifacts")
print(f"Indexed {len(records)} evidence records.")
