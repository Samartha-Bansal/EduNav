"""Deployment/runtime settings — tuned for Render free tier (512MB RAM)."""

import os

# Limit PyTorch/thread memory before heavy imports on small instances
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("PYTORCH_NUM_THREADS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

# Render sets RENDER=true; also allow explicit LOW_MEMORY_MODE
_on_render = bool(os.getenv("RENDER"))
_low_memory_flag = os.getenv("LOW_MEMORY_MODE", "").lower() in ("1", "true", "yes")

LOW_MEMORY_MODE = _on_render or _low_memory_flag

# Second cross-encoder model ~150MB+ — disable on small instances
_default_rerank = "false" if LOW_MEMORY_MODE else "true"
ENABLE_RERANK = os.getenv("ENABLE_RERANK", _default_rerank).lower() in ("1", "true", "yes")

# Preload models in lifespan (local dev). On Render, bind port first, load on first /ask.
_default_eager = "false" if LOW_MEMORY_MODE else "true"
EAGER_LOAD_ENGINE = os.getenv("EAGER_LOAD_ENGINE", _default_eager).lower() in ("1", "true", "yes")

EMBED_MODEL_NAME = os.getenv(
    "EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)
RERANK_MODEL_NAME = os.getenv(
    "RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

DEFAULT_TOP_K = "8" if LOW_MEMORY_MODE else "12"
DEFAULT_RERANK_TOP_N = "4" if LOW_MEMORY_MODE else "6"
