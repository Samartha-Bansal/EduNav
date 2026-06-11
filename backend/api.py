"""FastAPI server for EduNavigator RAG."""

import runtime_config  # noqa: F401 — thread/env limits before torch loads

import asyncio
import json
import logging
import os
import re
import socket
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import build_index
from query_engine import create_query_engine, query_with_sources
from runtime_config import EAGER_LOAD_ENGINE, LOW_MEMORY_MODE

load_dotenv()
load_dotenv(".env.local", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8001"))
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")

_engine_lock = threading.Lock()


class AppState:
    query_engine = None
    llm = None
    init_error: str | None = None
    engine_loading: bool = False


app_state = AppState()


def get_query_engine():
    if app_state.query_engine is not None and app_state.llm is not None:
        return app_state.query_engine, app_state.llm

    with _engine_lock:
        if app_state.query_engine is not None and app_state.llm is not None:
            return app_state.query_engine, app_state.llm
        app_state.engine_loading = True
        try:
            app_state.query_engine, app_state.llm = create_query_engine(
                storage_dir=STORAGE_DIR
            )
            app_state.init_error = None
            return app_state.query_engine, app_state.llm
        except Exception as exc:
            app_state.init_error = str(exc)
            raise
        finally:
            app_state.engine_loading = False


async def _init_engine_background():
    try:
        await asyncio.to_thread(get_query_engine)
        logger.info("Query engine ready (background init)")
    except Exception as exc:
        app_state.init_error = str(exc)
        logger.warning("Engine init failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup_task = None
    if EAGER_LOAD_ENGINE:
        try:
            await asyncio.to_thread(get_query_engine)
            logger.info("Query engine ready (eager init)")
        except Exception as exc:
            app_state.init_error = str(exc)
            logger.warning("Startup init deferred: %s", exc)
    else:
        logger.info(
            "Skipping eager engine load (%s). Models will load only on the first /ask request.",
            "LOW_MEMORY_MODE" if LOW_MEMORY_MODE else "EAGER_LOAD_ENGINE=false",
        )
        warmup_task = None
    yield
    if warmup_task and not warmup_task.done():
        warmup_task.cancel()


def _cors_origins() -> list[str]:
    raw = os.getenv("ALLOW_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app = FastAPI(title="EduNavigator Course Assistant", version="4.0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_recent_logs(limit: int = 50):
    log_file = Path("logs") / "query_logs.json"
    if not log_file.exists():
        return []
    logs = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    return logs[-limit:]


class ChatTurn(BaseModel):
    question: str
    answer: str


class QuestionRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    client_id: str | None = None
    history: list[ChatTurn] | None = None
    filters: dict | None = None


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: str
    retrieved_chunks: int
    highlighted_chunks: list[str]


COMMON_KEYWORDS = [
    "founder", "global", "immersion", "placement", "admission", "application",
    "fee", "tuition", "faculty", "entrepreneurship", "startup", "campus",
    "program", "course", "career", "salary", "location",
]

SPELLING_REPLACEMENTS = {
    "foundr": "founder",
    "entreprenuer": "entrepreneurship",
    "immerison": "immersion",
    "globel": "global",
    "placemant": "placement",
    "admisison": "admission",
    "applicaton": "application",
    "tution": "tuition",
    "fakulty": "faculty",
    "stertup": "startup",
}


def normalize_question(question: str) -> str:
    words = re.findall(r"\w+", question.lower())
    normalized = []
    for word in words:
        if word in SPELLING_REPLACEMENTS:
            normalized.append(SPELLING_REPLACEMENTS[word])
            continue
        close = get_close_matches(word, COMMON_KEYWORDS, n=1, cutoff=0.8)
        normalized.append(close[0] if close else word)
    return " ".join(normalized)


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    logger.info("Received /ask request")
    normalized_question = normalize_question(request.question)
    try:
        query_engine, llm = await asyncio.to_thread(get_query_engine)
        history = (
            [turn.model_dump() for turn in request.history] if request.history else None
        )
        answer, sources, query_type, retrieved_chunks, highlighted_chunks, _ = await asyncio.to_thread(
            query_with_sources,
            normalized_question,
            query_engine,
            llm,
            request.filters,
            request.conversation_id,
            request.client_id,
            history,
        )
        if not answer or not answer.strip():
            raise ValueError("No answer generated from indexed documents.")
        return AnswerResponse(
            answer=answer,
            sources=sources,
            query_type=query_type,
            retrieved_chunks=retrieved_chunks,
            highlighted_chunks=highlighted_chunks,
        )
    except Exception as exc:
        logger.exception("Failed to answer question")
        raise HTTPException(status_code=500, detail=f"Backend error: {exc}")


@app.post("/upload_documents")
async def upload_documents(files: list[UploadFile] = File(...)):
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    uploaded = []
    for file in files:
        if not file.filename:
            continue
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".txt", ".pdf", ".md"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
        path = data_dir / file.filename
        path.write_bytes(await file.read())
        uploaded.append(file.filename)
    return {"message": f"Uploaded {len(uploaded)} file(s)", "files": uploaded}


@app.get("/health")
async def health_check():
    index_ready = Path(STORAGE_DIR).is_dir() and any(Path(STORAGE_DIR).iterdir())
    llm_configured = bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))
    engine_ready = app_state.query_engine is not None
    # Always 200 so Render detects the open port; status reflects readiness.
    if engine_ready and index_ready and llm_configured:
        status = "healthy"
    elif app_state.engine_loading:
        status = "starting"
    elif app_state.init_error:
        status = "error"
    else:
        status = "degraded"
    return {
        "status": status,
        "index_ready": index_ready,
        "llm_configured": llm_configured,
        "engine_ready": engine_ready,
        "engine_loading": app_state.engine_loading,
        "low_memory_mode": LOW_MEMORY_MODE,
        "init_error": app_state.init_error,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/rebuild_index")
async def rebuild_index_endpoint(background_tasks: BackgroundTasks):
    def _rebuild():
        build_index.build_and_persist_index(storage_dir=STORAGE_DIR)
        app_state.query_engine = None
        app_state.llm = None
        try:
            get_query_engine()
            logger.info("Index rebuilt and query engine reloaded")
        except Exception as exc:
            app_state.init_error = str(exc)
            logger.exception("Failed to reload engine after rebuild")

    background_tasks.add_task(_rebuild)
    return {"message": "Index rebuild started. Ask questions again in a minute."}


@app.get("/documents")
async def list_documents():
    data_dir = Path("data")
    if not data_dir.exists():
        return {"documents": []}
    docs = [p.name for p in sorted(data_dir.iterdir()) if p.is_file()]
    return {"documents": docs}


@app.get("/logs")
async def get_logs():
    return {"logs": read_recent_logs()}


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


if __name__ == "__main__":
    import uvicorn

    if port_in_use(HOST, PORT):
        logger.error(
            "Port %s is already in use. Stop the other process first:\n"
            "  netstat -ano | findstr :%s\n"
            "  taskkill /PID <pid> /F\n"
            "Or use: ..\\scripts\\start-backend.ps1",
            PORT,
            PORT,
        )
        raise SystemExit(1)

    uvicorn.run(app, host=HOST, port=PORT)
