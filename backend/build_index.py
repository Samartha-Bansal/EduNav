"""Build and load the FAISS vector index for RAG."""

import os
import shutil

import faiss
from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from ingestion import load_all_documents

Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

EMBED_DIM = 384


def build_and_persist_index(
    jsonl_file: str = "final_rag_input.jsonl",
    storage_dir: str = "storage",
    data_dir: str = "data",
):
    documents = load_all_documents(jsonl_file=jsonl_file, data_dir=data_dir)
    print(f"Indexing {len(documents)} documents (corpus + uploads)")

    if not documents:
        raise ValueError("No documents found. Add files to data/ or provide final_rag_input.jsonl")

    text_splitter = SentenceSplitter(chunk_size=400, chunk_overlap=80)
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    vector_store = FaissVectorStore(faiss_index=faiss.IndexFlatIP(EMBED_DIM))
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=[text_splitter],
    )

    index.storage_context.persist(persist_dir=storage_dir)
    print(f"Index built and persisted to {storage_dir}")
    return index


def load_persisted_index(storage_dir: str = "storage"):
    if not os.path.isdir(storage_dir):
        print(f"No index at {storage_dir}, building...")
        build_and_persist_index(storage_dir=storage_dir)
        return load_persisted_index(storage_dir)

    try:
        vector_store = FaissVectorStore.from_persist_dir(persist_dir=storage_dir)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=storage_dir,
        )
        index = load_index_from_storage(storage_context)
        print(f"Index loaded from {storage_dir}")
        return index
    except Exception as exc:
        print(f"Failed to load index: {exc}. Rebuilding...")
        if os.path.exists(storage_dir):
            shutil.rmtree(storage_dir)
        build_and_persist_index(storage_dir=storage_dir)
        return load_persisted_index(storage_dir)


if __name__ == "__main__":
    os.makedirs("storage", exist_ok=True)
    build_and_persist_index()
