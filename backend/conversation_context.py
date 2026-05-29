"""Resolve vague and follow-up questions using chat history (Masters' Union scope)."""

import re
from typing import List, Optional

MU_SCOPE = "Masters Union"

# Follow-up / deictic cues — need prior turn to resolve
FOLLOW_UP_RE = re.compile(
    r"\b("
    r"it|its|they|them|their|this|that|these|those|"
    r"he|she|him|her|his|hers|"
    r"there|here|"
    r"more|else|also|another|other|"
    r"same|such|"
    r"above|mentioned|earlier|previous|last"
    r")\b",
    re.IGNORECASE,
)

SHORT_QUERY_RE = re.compile(
    r"^(?:"
    r"(?:tell|say|give|show)\s+me\s+)?"
    r"(?:something\s+about\s+)?"
    r"(?:the\s+)?[\w\s'-]{1,40}"
    r"[?.!]?$",
    re.IGNORECASE,
)

VAGUE_STARTERS = re.compile(
    r"^(?:what|who|when|where|why|how|tell|explain|describe|any|is|are|can|does|do)\b",
    re.IGNORECASE,
)


def get_history(conversation_memory: dict, conversation_id: Optional[str], limit: int = 3) -> List[dict]:
    if not conversation_id or conversation_id not in conversation_memory:
        return []
    return conversation_memory[conversation_id][-limit:]


def extract_topic_hints(text: str, max_terms: int = 12) -> List[str]:
    """Pull salient tokens from prior Q&A for retrieval expansion."""
    if not text:
        return []
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "about",
        "that", "this", "these", "those", "it", "its", "they", "them", "their",
        "what", "which", "who", "whom", "when", "where", "why", "how", "tell",
        "me", "you", "your", "i", "we", "our", "please", "something", "more",
        "also", "just", "like", "from", "with", "for", "and", "or", "but", "not",
        "in", "on", "at", "to", "of", "as", "by", "if", "so", "than", "then",
        "there", "here", "any", "some", "couldn", "find", "information",
        "masters", "union", "program", "documents", "assistant", "help",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", text.lower())
    seen = set()
    hints = []
    for w in words:
        if w in stop or w in seen:
            continue
        seen.add(w)
        hints.append(w)
        if len(hints) >= max_terms:
            break
    return hints


def looks_like_follow_up(question: str, history: List[dict]) -> bool:
    if not history:
        return False
    q = question.strip()
    if len(q.split()) <= 8 and FOLLOW_UP_RE.search(q):
        return True
    if len(q.split()) <= 5:
        return True
    if re.search(r"\b(?:more|else|again|continue|elaborate|expand)\b", q, re.I):
        return True
    if re.search(r"^(?:and|but|so|ok|okay)[,.\s]", q, re.I):
        return True
    return False


def resolve_question(question: str, history: List[dict]) -> str:
    """
    Turn a vague or follow-up utterance into a standalone question using recent turns.
    """
    q = question.strip()
    if not history:
        return q

    last = history[-1]
    prior_q = (last.get("question") or "").strip()
    prior_a = (last.get("answer") or "").strip()

    if not looks_like_follow_up(q, history):
        # Still enrich very short vague questions with the last user topic
        if len(q.split()) <= 6 and VAGUE_STARTERS.search(q) and prior_q:
            return f"{q} (regarding Masters Union: {prior_q})"
        return q

    # Explicit resolution for common patterns
    combined_prior = f"{prior_q}\n{prior_a[:800]}"
    hints = extract_topic_hints(combined_prior)

    if re.search(r"\b(?:founder|co-?founder)\b", q, re.I) or (
        re.search(r"\b(?:he|she|him|her|they)\b", q, re.I)
        and re.search(r"\b(?:founder|pratham\s+mittal)\b", combined_prior, re.I)
    ):
        return (
            f"{q} — about Pratham Mittal, founder of Masters Union; "
            f"following up on: {prior_q}"
        )

    if re.search(r"\b(?:he|she|him|her|they)\b", q, re.I):
        if re.search(r"\bpratham\b", combined_prior, re.I):
            return f"{q} — about Pratham Mittal at Masters Union; context: {prior_q}"
        if re.search(r"\bmahak\b", combined_prior, re.I):
            return f"{q} — about Mahak Garg / faculty at Masters Union; context: {prior_q}"

    if re.search(r"\b(?:fee|fees|cost|tuition|price)\b", q, re.I) or (
        FOLLOW_UP_RE.search(q) and re.search(r"\bfee", combined_prior, re.I)
    ):
        return f"{q} — Masters Union fees and tuition, context: {prior_q}"

    if re.search(r"\b(?:faculty|professor|director|teacher|staff)\b", q, re.I):
        return f"{q} — Masters Union faculty and leadership, context: {prior_q}"

    if re.search(r"\b(?:placement|salary|internship|career)\b", q, re.I):
        return f"{q} — Masters Union placements and careers, context: {prior_q}"

    if re.search(r"\b(?:admission|apply|eligib|deadline)\b", q, re.I):
        return f"{q} — Masters Union admissions, context: {prior_q}"

    topic_tail = " ".join(hints[:8])
    if topic_tail:
        return f"{q} (Masters Union — continuing: {prior_q}; related terms: {topic_tail})"
    return f"{q} (Masters Union — continuing our discussion about: {prior_q})"


def combined_scope_text(question: str, history: List[dict]) -> str:
    """Text used for off-topic checks — includes recent conversation."""
    parts = [question]
    for turn in history[-2:]:
        parts.append(turn.get("question") or "")
        parts.append((turn.get("answer") or "")[:400])
    return "\n".join(p for p in parts if p.strip())
