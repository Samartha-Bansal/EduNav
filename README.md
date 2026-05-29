# EduNavigator

AI course assistant powered by **RAG** (Retrieval-Augmented Generation). Upload program documents, build a vector index, and ask questions grounded in your content.

## Architecture

```
Documents (data/ or final_rag_input.jsonl)
        ↓
  build_index.py  →  FAISS vector store (storage/)
        ↓
  FastAPI /ask  →  retrieve chunks → Groq/Gemini LLM → answer + sources
        ↓
  Next.js chat UI
```

## Quick start

### 1. Backend (terminal 1)

```powershell
cd D:\EduNavigator
.\scripts\start-backend.ps1
```

If port 8001 is busy, the script stops the old process first. API runs at **http://127.0.0.1:8001**.

First-time setup:

```powershell
cd backend
..\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env.local
# Add GROQ_API_KEY to .env.local
..\.venv\Scripts\python build_index.py
```

### 2. Frontend (terminal 2)

```powershell
cd D:\EduNavigator
.\scripts\start-frontend.ps1
```

Open **http://localhost:3000**. The UI calls `/api/*`, which Next.js proxies to the backend (no CORS issues).

**Restart the frontend** after changing `next.config.js` or `.env.local`.

## Features

- Chat with conversation history (saved in browser)
- Document upload (.txt, .pdf, .md) from the sidebar
- Rebuild vector index after uploading new files
- Source citations and highlighted context snippets
- Query type labels (admission, curriculum, fees, etc.)

## Environment variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (recommended) |
| `GEMINI_API_KEY` | Alternative: Google Gemini |
| `LLM_MODEL` | e.g. `llama-3.1-8b-instant` or `gemini-2.0-flash` |
| `PORT` | Backend port (default `8001`) |
| `NEXT_PUBLIC_API_URL` | Frontend → backend URL |

## Project layout

```
EduNavigator/
├── backend/          # FastAPI + LlamaIndex + FAISS
├── frontend/         # Next.js 14 chat UI
└── README.md
```

## License

MIT
