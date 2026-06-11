"""Shared embedding model — single instance to avoid loading twice."""

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from runtime_config import EMBED_MODEL_NAME

_embed_model = None


def get_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
        Settings.embed_model = _embed_model
    return _embed_model
