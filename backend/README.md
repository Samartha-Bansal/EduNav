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

## Deploy on Render (free tier / 512MB RAM)

The default stack loads two transformer models at startup and exceeds 512MB. Use:

| Env var | Render value | Why |
|---------|--------------|-----|
| `LOW_MEMORY_MODE` | `true` | Auto-set when `RENDER=true` |
| `ENABLE_RERANK` | `false` | Skips cross-encoder (~150MB+) |
| `EAGER_LOAD_ENGINE` | `false` | Binds `$PORT` before loading models |
| `GROQ_API_KEY` | (secret) | Required |
| `ALLOW_ORIGINS` | your frontend URL | CORS |

Use the repo root `render.yaml` or set **Root Directory** to `backend` and **Start Command**:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

`requirements.txt` installs **CPU-only PyTorch** (smaller than CUDA builds).

First deploy: `/health` returns `starting` while models load in the background. First `/ask` may take 30–60s.

**Commit `backend/storage/`** to git (pre-built index). Render cannot rebuild the index on 512MB RAM.

For local full quality, leave `ENABLE_RERANK=true` (default when not on Render).

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
