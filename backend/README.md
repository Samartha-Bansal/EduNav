# EduNavigator Backend

FastAPI RAG service using LlamaIndex, HuggingFace embeddings, FAISS, and Groq (or Gemini).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env.local
# Add GROQ_API_KEY to .env.local
python build_index.py
python api.py
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ask` | Ask a question |
| GET | `/health` | Service status |
| POST | `/upload_documents` | Upload files to `data/` |
| POST | `/rebuild_index` | Rebuild FAISS index |
| GET | `/documents` | List files in `data/` |
| GET | `/logs` | Recent query logs |

## Data sources

1. **`final_rag_input.jsonl`** — pre-built corpus (used if present)
2. **`data/`** — your `.txt` / `.pdf` files

Run `python build_index.py` after adding or changing documents.
