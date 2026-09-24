# Multimodal RAG Information Retrieval System

## 1. Executive summary

This repository contains a Retrieval-Augmented Generation (RAG) system built for
question answering over the supplied Apple Inc. Q3 2022 Form 10-Q PDF.

The application is designed to answer questions about:

- Narrative text in the filing.
- Financial tables and numeric disclosures.
- Figures, charts, embedded images, and rendered visual page evidence.

The system is intentionally evidence-first. Every answer is produced from
retrieved document evidence, and the API returns the supporting records with page
numbers, modality labels, and relevance scores. Questions that are unrelated to
the supplied filing are rejected with a clear out-of-scope response rather than
being answered from general model knowledge.

The project includes:

- A PyMuPDF-based PDF ingestion pipeline.
- A transparent JSON evidence index.
- Lexical TF-IDF-style retrieval with modality-aware ranking.
- An extractive answer fallback that works without an LLM API key.
- Optional OpenAI-compatible generation.
- A FastAPI backend.
- A presentation-ready browser UI.
- Figure/page-image previews.
- Automated retrieval and scope tests.

## Demo video

The project includes a recorded walkthrough of the application:

[Watch the demo video](videos/demo.mp4)

The video demonstrates the browser interface, document-grounded question
answering, retrieved evidence, table/figure support, and out-of-scope handling.
The MP4 uses H.264 encoding and is optimized for browser compatibility.

---

## 2. Repository structure

```text
SmartDataSolutions/
├── artifacts/
│   ├── index.json                 Generated evidence index
│   └── images/                    Rendered pages and extracted PDF images
├── data/
│   └── aapl_2022_q3_10q.pdf      Supplied source document
├── videos/
│   └── demo.mp4                  Browser-compatible application walkthrough
├── scripts/
│   └── ingest.py                  Rebuild the document index
├── src/
│   ├── __init__.py
│   ├── app.py                     FastAPI application and routes
│   └── rag/
│       ├── __init__.py
│       ├── generator.py           Extractive/LLM answer generation
│       ├── ingest.py              PDF parsing and multimodal indexing
│       ├── models.py              Evidence data model
│       └── retriever.py           Query filtering and ranking
├── templates/
│   └── index.html                 Browser application UI
├── tests/
│   ├── test_retriever.py          Retrieval ranking test
│   └── test_scope.py              Out-of-scope behavior test
├── .gitignore
├── requirements.txt
└── README.md
```

`artifacts/` is generated data. The source PDF is kept in `data/` so that the
project can be reproduced from a clean checkout.

---

## 3. End-to-end architecture

```text
                    ┌─────────────────────────────┐
                    │ Apple Q3 2022 Form 10-Q PDF │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │       Ingestion pipeline     │
                    │  PyMuPDF text/image parsing  │
                    │  table and visual detection  │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │      Evidence index         │
                    │ JSON records with page,     │
                    │ modality, text and image    │
                    └──────────────┬──────────────┘
                                   │
                  user question   │
                         ┌─────────▼──────────┐
                         │ FastAPI /api/query │
                         └─────────┬──────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ Scope checks and retrieval  │
                    │ token overlap + IDF scoring │
                    │ table/figure ranking boosts │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ Answer generation           │
                    │ extractive fallback or      │
                    │ OpenAI-compatible LLM        │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ Answer + evidence + pages   │
                    │ Browser presentation UI      │
                    └─────────────────────────────┘
```

The implementation separates ingestion, retrieval, and generation. This keeps
the system easy to inspect and allows the answer model to be replaced without
rewriting the document pipeline.

---

## 4. Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Language | Python 3.13 recommended | Application and data pipeline |
| PDF processing | PyMuPDF / `fitz` | Text extraction, embedded image extraction, page rendering |
| API | FastAPI | HTTP routes, validation, lifecycle management |
| ASGI server | Uvicorn | Local application server |
| Validation | Pydantic | Request schema and limits |
| HTTP client | HTTPX | OpenAI-compatible model calls |
| Document index | JSON | Transparent, portable evidence storage |
| UI | HTML/CSS/JavaScript | Search workspace, answer display, evidence drawer |
| Submission PDF | ReportLab | Methodology document generation |
| Testing | Pytest | Retrieval and scope regression tests |

The default implementation does not require a vector database, GPU, hosted
model, or external service. This makes the submission deterministic and easy to
run during evaluation.

---

## 5. Installation and setup

### 5.1 Create the virtual environment

```bash
cd /Users/abusheik/Documents/SmartDataSolutions
python3 -m venv .venv
source .venv/bin/activate
```

Python 3.13 is recommended for broad compatibility with the pinned packages.

### 5.2 Install dependencies

```bash
pip install -r requirements.txt
```

### 5.3 Build or rebuild the index

```bash
python scripts/ingest.py
```

This command reads `data/aapl_2022_q3_10q.pdf` and regenerates:

```text
artifacts/index.json
artifacts/images/
```

Re-run ingestion whenever the source PDF changes.

### 5.4 Start the application

```bash
uvicorn src.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The application starts by loading the existing index. If the index does not
exist, the FastAPI startup hook creates it automatically.

---

## 6. Optional LLM configuration

The application works without an API key. In that mode it uses the extractive
fallback in `src/rag/generator.py`.

For model-generated answers, configure an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"
uvicorn src.app:app --reload
```

`OPENAI_BASE_URL` can point to another compatible service, such as a local
gateway or Ollama-compatible endpoint. The generator sends only the user
question and retrieved evidence to the configured model.

The prompt instructs the model to:

- Answer only from supplied evidence.
- Preserve dates, units, and numbers.
- Cite factual claims with page references.
- Say when evidence is insufficient.
- Avoid inventing visual facts.

No API key or secret is stored in the repository.

---

## 7. Ingestion and multimodal indexing

The ingestion implementation is in `src/rag/ingest.py`.

### 7.1 Text extraction

For every PDF page, PyMuPDF extracts the page text. Whitespace is normalized and
the resulting content is stored as an `Evidence` record containing:

- Stable chunk ID.
- One-based PDF page number.
- Modality label.
- Normalized text.
- Optional image path.
- Retrieval score, populated later.

Large page records are capped to keep the index manageable.

### 7.2 Table detection

The source document contains financial statements and numeric disclosures. The
current implementation uses conservative heuristics to label a text record as a
table candidate when:

- Multiple lines contain numeric values.
- Multiple lines appear to have column separation.
- Financial table terms such as `net sales`, `assets`, `liabilities`,
  `operating income`, or `cash flows` appear.

This is intentionally a candidate detector rather than a claim that every
detected page is a perfectly reconstructed table. The original page text is
preserved for citation and auditing.

### 7.3 Visual page indexing

Every page is rendered to a PNG image and stored under:

```text
artifacts/images/page-N.png
```

Rendered page evidence provides a reliable visual fallback for charts, diagrams,
figures, and layout-dependent content that may not be represented as an
extractable image object.

### 7.4 Embedded image extraction

PDF image objects are also extracted individually when possible. They are stored
with names such as:

```text
artifacts/images/page-1-image-1.jpeg
```

Each extracted image is indexed as a `figure` record with its page number and
nearby page text.

### 7.5 Evidence record format

An index entry has the following conceptual structure:

```json
{
  "chunk_id": "p19-text",
  "page": 19,
  "modality": "table",
  "text": "Services net sales increased ...",
  "score": 0.0,
  "image_path": null,
  "metadata": {}
}
```

The JSON format was selected because it is inspectable during an interview or
technical review and can later be migrated to a vector store without changing
the application contract.

---

## 8. Retrieval mechanism

Retrieval is implemented in `src/rag/retriever.py`.

### 8.1 Query tokenization

Questions are lowercased and tokenized with a regular expression. Common
stopwords are removed to reduce noise from words such as `the`, `of`, `and`, and
`what`.

### 8.2 IDF-style lexical scoring

For each query token found in an evidence record, the retriever calculates a
term-frequency and inverse-document-frequency contribution:

```text
score += (1 + log(term_frequency)) * IDF(token)
```

This gives more weight to terms that are both relevant to the question and
relatively discriminative across the document.

### 8.3 Modality-aware boosts

The retriever applies small ranking boosts when the query indicates a specific
content type:

- Table-related terms such as `revenue`, `income`, `assets`, `cash`, or `sales`
  boost table candidates.
- Figure-related terms such as `figure`, `chart`, `image`, `graph`, `shown`, or
  `pictured` boost visual evidence.

This helps the system return the right kind of evidence for a question rather
than only the highest lexical overlap.

### 8.4 Evidence threshold

At least two meaningful query terms must match an evidence record. This avoids
retrieving unrelated paragraphs because of a single generic word.

### 8.5 Out-of-scope protection

The retriever rejects questions that clearly request information outside the
provided filing, including:

- Current, latest, today, weather, or forecast questions without document
  context.
- Years other than 2021 and 2022.
- Questions with no meaningful document-term overlap.

When no evidence is returned, the generator displays:

> This question is beyond my scope. I can only answer questions supported by the
> supplied Apple Q3 2022 10-Q PDF, including its text, tables, and figures.

This is a deliberate groundedness and user-expectation safeguard.

---

## 9. Answer generation

Answer generation is implemented in `src/rag/generator.py`.

### 9.1 Extractive fallback

When no model API key is configured, the system:

1. Splits retrieved evidence into candidate sentences.
2. Measures overlap between question terms and each sentence.
3. Selects the highest-overlap sentences.
4. Adds the source page number to each selected sentence.

This mode is useful for:

- Offline demonstrations.
- Reproducible evaluation.
- Environments without model credentials.
- Inspecting whether retrieval is working independently of generation.

### 9.2 Optional LLM generation

When `OPENAI_API_KEY` is configured, the system sends the question and retrieved
evidence to `/chat/completions` on the configured OpenAI-compatible endpoint.

The model is not allowed to search the internet or access the entire PDF
implicitly. It receives only the evidence selected by the retriever. This is the
central RAG mechanism: retrieval supplies the grounded context, and generation
turns that context into a concise answer.

### 9.3 Evidence and UI separation

The answer is shown first. Supporting evidence is hidden behind a collapsible
**Supporting evidence** control so the interface remains concise while still
allowing reviewers to inspect the source passages and visual evidence.

---

## 10. API reference

### `GET /`

Returns the browser application.

### `GET /health`

Returns service status and the indexed document:

```json
{
  "status": "ok",
  "indexed": true,
  "document": "aapl_2022_q3_10q.pdf"
}
```

### `POST /api/query`

Request:

```json
{
  "question": "What were Apple’s total net sales for the third quarter of 2022?",
  "limit": 6
}
```

Validation rules:

- `question` must contain 3–2000 characters.
- `limit` must be between 1 and 12.

Response:

```json
{
  "answer": "Grounded answer with page references.",
  "evidence": [
    {
      "chunk_id": "p19-text",
      "page": 19,
      "modality": "table",
      "text": "Retrieved source passage...",
      "score": 12.34,
      "image_path": null,
      "metadata": {}
    }
  ],
  "modalities": ["table"]
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H 'content-type: application/json' \
  -d '{"question":"What were Apple’s net sales by product category?"}'
```

### `GET /api/figure/{path}`

Serves an extracted or rendered image from the `artifacts/` directory. The route
resolves and validates the path to prevent access outside the artifact directory.

---

## 11. User interface

The UI is implemented as a single server-rendered HTML file at
`templates/index.html`.

The presentation layer includes:

- Branded document intelligence header.
- Active source document card.
- Research workspace.
- Example question chips.
- Search button and `Ctrl/Cmd + Enter` shortcut.
- Loading state while retrieval runs.
- Answer card with modality badges.
- Grounded-response metadata.
- Collapsible supporting evidence.
- Page numbers and relevance scores.
- Inline figure and page-image previews.
- Responsive layout for smaller screens.

Example question chips are provided for:

- Net sales.
- Product tables.
- Figures and visual evidence.

The UI does not perform retrieval itself. It sends JSON to `/api/query` and
renders the returned response. This keeps the browser layer thin and makes the
API independently testable.

---

## 12. Testing and validation

Run the tests with:

```bash
source .venv/bin/activate
python -m pytest -q
```

The current tests cover:

### Retrieval ranking

`tests/test_retriever.py` verifies that a record containing the relevant terms
is ranked above an unrelated record.

### Scope protection

`tests/test_scope.py` verifies that an unrelated weather question returns no
evidence and produces the expected out-of-scope message.

Additional manual validation:

```bash
python -m compileall -q src scripts
python scripts/ingest.py
uvicorn src.app:app --reload
```

---

## 13. Assumptions

The implementation makes the following assumptions:

1. The supplied PDF is digitally generated and contains extractable text.
2. The filing date context is limited to the 2021 and 2022 periods represented in
   the document.
3. A page containing numeric, column-like financial text is a useful table
   candidate even when the PDF does not expose semantic table structure.
4. A rendered page is a valid visual evidence fallback for figures and charts.
5. Users prefer a grounded limitation message to an unsupported answer.

---

## 14. Known limitations

### Table reconstruction

The current implementation identifies table candidates but does not rebuild every
table into a fully structured row/column representation. PDF layout extraction
varies significantly across documents.

### Figure understanding

Figures and page images are indexed and displayed, but the default extractive
mode does not perform detailed visual reasoning over image pixels. A multimodal
vision-language model should be added for questions that require interpreting
chart trends or diagram relationships.

### Retrieval quality

The baseline retriever is sparse lexical retrieval. It does not yet use dense
embeddings, semantic reranking, query expansion, or a vector database.

### Numeric reasoning

The system retrieves numeric evidence but does not have a dedicated financial
calculation layer. Arithmetic questions should be handled by adding a verified
calculation tool that cites the source values before computing.

### Production security

The local demo has no authentication, rate limiting, user accounts, or persistent
query history. These should be added before public deployment.

---

## 15. Recommended future improvements

1. Replace heuristic table detection with layout-aware table extraction.
2. Add OCR for scanned pages and image-only PDFs.
3. Add dense embeddings and hybrid sparse/dense retrieval.
4. Add a cross-encoder reranker for the top retrieved candidates.
5. Store embeddings and metadata in a vector database.
6. Add image embeddings and vision-language evidence analysis.
7. Add a calculation tool for percentages, comparisons, and financial totals.
8. Add answer faithfulness and citation-completeness evaluation.
9. Add caching for repeated questions.
10. Add authentication, rate limiting, logging, and monitoring.
11. Add a document-upload workflow for multiple PDFs.
12. Add configurable chunking instead of one main text record per page.

---

## 16. Quick demonstration script

```bash
cd /Users/abusheik/Documents/SmartDataSolutions
source .venv/bin/activate
python scripts/ingest.py
python -m pytest -q
uvicorn src.app:app --reload
```

Then open `http://127.0.0.1:8000` and try:

```text
What were Apple’s total net sales for the third quarter of 2022?
```

```text
What were Apple’s net sales by product category?
```

```text
Which pages contain figures or visual evidence?
```

Negative-scope test:

```text
What is Apple’s current stock price?
```

The final question should return the documented out-of-scope message.
