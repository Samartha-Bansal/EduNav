"""RAG query engine: retrieve chunks and synthesize grounded answers."""

import json
import os
import re
import time
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import QueryBundle
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from answer_generator import (
    format_context,
    generate_answer,
    is_generic_answer,
    is_not_answered_response,
)
from answer_validator import has_substantive_content, is_refusal
from build_index import load_persisted_index
from conversation_context import (
    combined_scope_text,
    extract_topic_hints,
    get_history,
    memory_key,
    resolve_question,
)
from llm_factory import create_llm
from query_classifier import QueryClassifier
from query_expansion import build_retrieval_query
from answer_safety import (
    answer_contains_outside_knowledge,
    answer_dodges_instead_of_refusing,
    sanitize_or_refuse,
)
from scope_classifier import (
    evaluate_scope,
    is_assistant_scoped_question,
    is_world_knowledge_question,
)
from topic_guard import is_program_related, mentions_masters_union
from topic_guard import (
    REFUSAL_MESSAGE,
    is_clearly_off_topic,
    is_general_knowledge_question,
    is_gibberish_or_spam,
)

load_dotenv()
load_dotenv(".env.local", override=True)

Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "12"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "6"))
MAX_SOURCES = int(os.getenv("MAX_SOURCES", "5"))
MAX_HIGHLIGHTED_CHUNKS = int(os.getenv("MAX_HIGHLIGHTED_CHUNKS", "4"))

conversation_memory: Dict[str, List[Dict]] = {}


def _remember_turn(
    question: str,
    answer: str,
    conversation_id: str | None,
    client_id: str | None,
) -> None:
    key = memory_key(client_id, conversation_id)
    if not key:
        return
    conversation_memory.setdefault(key, []).append(
        {"question": question, "answer": answer, "timestamp": time.time()}
    )
    conversation_memory[key] = conversation_memory[key][-10:]


def _refusal_response(
    question: str,
    conversation_id: str | None,
    query_type: str,
    start_time: float,
    message: str | None = None,
    nodes: list | None = None,
    client_id: str | None = None,
):
    from topic_guard import REFUSAL_MESSAGE

    answer = message or REFUSAL_MESSAGE
    sources = []
    highlighted = []

    _remember_turn(question, answer, conversation_id, client_id)

    log_query(
        {
            "timestamp": time.time(),
            "conversation_id": conversation_id,
            "question": question,
            "query_type": query_type,
            "refused": True,
            "response_time": time.time() - start_time,
        }
    )

    return answer, sources, query_type, 0, highlighted, {}


def clean_answer_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\\r", "").replace("\\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def retrieve_nodes(retriever, reranker, query: str) -> list:
    bundle = QueryBundle(query_str=query)
    nodes = retriever.retrieve(bundle)
    if reranker:
        nodes = reranker.postprocess_nodes(nodes, bundle)
    return list(nodes)


def retrieve_with_retry(
    retriever,
    reranker,
    question: str,
    query_type: str,
    history: List[dict],
) -> Tuple[list, str]:
    """Retrieve; on weak results, retry with stronger MU anchoring and history hints."""
    from topic_guard import is_low_relevance

    resolved = resolve_question(question, history)
    hints = []
    for turn in history[-2:]:
        hints.extend(extract_topic_hints(turn.get("question") or ""))
        hints.extend(extract_topic_hints((turn.get("answer") or "")[:500]))

    search_query = build_retrieval_query(resolved, query_type, hints or None)
    nodes = retrieve_nodes(retriever, reranker, search_query)

    if not is_low_relevance(nodes):
        return nodes, search_query

    # Second pass: broader MU anchor + prior question verbatim
    retry_parts = [resolved, "Masters Union", "PGP TBM", "UG TBM"]
    if history:
        retry_parts.append(history[-1].get("question") or "")
    retry_parts.extend(hints[:10])
    retry_query = " ".join(dict.fromkeys(p for p in retry_parts if p and p.strip()))
    retry_nodes = retrieve_nodes(retriever, reranker, retry_query)

    if retry_nodes and (
        not is_low_relevance(retry_nodes)
        or (nodes and getattr(retry_nodes[0], "score", -999) > getattr(nodes[0], "score", -999))
    ):
        return retry_nodes, retry_query

    return nodes if nodes else retry_nodes, search_query


def log_query(log_data: dict) -> None:
    log_file = os.path.join("logs", "query_logs.json")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        json.dump(log_data, f)
        f.write("\n")


def create_query_engine(storage_dir: str = "storage", top_k: int = TOP_K):
    index = load_persisted_index(storage_dir)
    llm = create_llm()
    Settings.llm = llm

    retriever = VectorIndexRetriever(index=index, similarity_top_k=top_k)
    reranker = SentenceTransformerRerank(
        model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_n=RERANK_TOP_N,
    )

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[reranker],
    )
    query_engine._retriever = retriever
    query_engine._node_postprocessors = [reranker]
    return query_engine, llm


def query_with_sources(
    question: str,
    query_engine,
    llm,
    filters: dict = None,
    conversation_id: str = None,
    client_id: str = None,
    history: list = None,
):
    start_time = time.time()
    chat_history = get_history(
        conversation_memory,
        conversation_id,
        client_id=client_id,
        request_history=history,
    )
    scope_text = combined_scope_text(question, chat_history)

    if is_clearly_off_topic(question, scope_text) or is_world_knowledge_question(
        question, scope_text
    ):
        return _refusal_response(
            question, conversation_id, "out_of_scope", start_time, client_id=client_id
        )

    classifier = QueryClassifier()
    query_type = classifier.classify(question)
    resolved_question = resolve_question(question, chat_history)

    retriever = query_engine._retriever
    reranker = query_engine._node_postprocessors[0] if query_engine._node_postprocessors else None
    nodes, search_query = retrieve_with_retry(
        retriever, reranker, question, query_type, chat_history
    )

    should_answer, refusal_msg = evaluate_scope(question, nodes, scope_text)
    if not should_answer:
        return _refusal_response(
            question,
            conversation_id,
            "out_of_scope",
            start_time,
            refusal_msg,
            nodes,
            client_id=client_id,
        )

    # LLM uses resolved question + optional short context note for pronouns
    llm_question = resolved_question
    if chat_history and resolved_question != question:
        llm_question = f"{question}\n\n(Context: {resolved_question})"

    context_str = format_context(nodes)
    mu_program_question = (
        is_assistant_scoped_question(question)
        or is_program_related(question)
        or mentions_masters_union(scope_text)
    )
    answer = clean_answer_text(
        generate_answer(llm_question, nodes, llm, mu_program_question=mu_program_question)
    )
    off_topic = is_world_knowledge_question(question, scope_text) or is_general_knowledge_question(
        question, scope_text
    )
    answer = sanitize_or_refuse(answer, context_str, force_refusal=off_topic)

    not_found_msg = (
        "I couldn't find that in Masters' Union program documents. "
        "Try asking about programs, admissions, courses, fees, faculty, or placements."
    )

    if off_topic or answer_contains_outside_knowledge(answer, context_str) or (
        answer_dodges_instead_of_refusing(answer) and not mu_program_question
    ):
        return _refusal_response(
            question,
            conversation_id,
            "out_of_scope",
            start_time,
            REFUSAL_MESSAGE,
            nodes,
            client_id=client_id,
        )

    if mu_program_question:
        if not answer or not has_substantive_content(answer) or is_generic_answer(answer):
            return _refusal_response(
                question,
                conversation_id,
                "not_found",
                start_time,
                not_found_msg,
                nodes,
                client_id=client_id,
            )
    elif (
        is_refusal(answer)
        or is_not_answered_response(answer)
        or is_generic_answer(answer)
        or not answer
        or not has_substantive_content(answer)
    ):
        return _refusal_response(
            question,
            conversation_id,
            "out_of_scope",
            start_time,
            REFUSAL_MESSAGE,
            nodes,
            client_id=client_id,
        )

    sources = list(
        dict.fromkeys(
            node.metadata.get("file_name") or node.metadata.get("source", "Unknown")
            for node in nodes
        )
    )

    highlighted_chunks = []
    for node in nodes[:MAX_HIGHLIGHTED_CHUNKS]:
        chunk = (node.text or "").strip()
        if len(chunk) > 50:
            highlighted_chunks.append(chunk[:500] + ("..." if len(chunk) > 500 else ""))

    limited_sources = sources[:MAX_SOURCES]

    _remember_turn(question, answer, conversation_id, client_id)

    log_query(
        {
            "timestamp": time.time(),
            "conversation_id": conversation_id,
            "question": question,
            "resolved_question": resolved_question,
            "search_query": search_query,
            "query_type": query_type,
            "retrieved_sources": limited_sources,
            "final_answer": answer[:600],
            "response_time": time.time() - start_time,
        }
    )

    return (
        answer,
        limited_sources,
        query_type,
        len(highlighted_chunks),
        highlighted_chunks,
        {},
    )
