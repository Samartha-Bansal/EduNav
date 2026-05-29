"""Strict answer synthesis — prose summaries; bullets only as fallback."""

import re

STRICT_SYSTEM = """You are the Masters' Union Program Help assistant (a RAG chatbot). Users are already on the Masters' Union site — treat every question as about Masters' Union unless excerpts are clearly unrelated.

Answer ONLY using the document excerpts below. Use partial or related excerpts when they help (e.g. leadership, reports, brochures). If excerpts truly do not mention the topic at all, say you could not find that in Masters' Union program documents — do NOT guess or use outside knowledge.

FORBIDDEN:
- "Unfortunately", "I recommend", "visit the website", "contact admissions"
- "likely", "might", "generally", "typically", "I can suggest"
- Claiming information is missing when facts appear in the excerpts
- Generic guesses
- Jamming list items into one long run-on paragraph

REQUIRED:
- Prefer a clear SUMMARY in 2–4 short paragraphs of flowing prose with complete sentences
- Weave facts naturally; be specific and readable
- Use bullet points ONLY if the facts are many parallel items and proper sentences would be unclear
- If you use bullets, each line must be a complete, meaningful sentence or phrase from the excerpts"""

STRICT_PROMPT = """{system}

DOCUMENT EXCERPTS:
{context}

QUESTION: {question}

Write a concise summary (paragraphs preferred):"""

SUMMARY_RETRY_PROMPT = """Using ONLY the excerpts below, answer the question as 2–4 short paragraphs of complete sentences.
Prefer connected prose over lists.

Question: {question}

Excerpts:
{context}

Answer:"""

PROSE_FROM_DRAFT_PROMPT = """Rewrite the draft below into clear paragraphs with proper complete sentences.
Use ONLY facts from the draft. Do not add information.

Rules:
- Turn list items into natural prose where they fit together logically
- Do NOT glue unrelated points into one long run-on sentence
- If several items are truly parallel and cannot read well as prose, keep them as a short bullet list (one fact per line)
- Otherwise use paragraphs only

Question: {question}

Draft:
{draft}

Rewritten answer:"""

GENERIC_PATTERNS = [
    r"\bunfortunately\b",
    r"\bi recommend\b",
    r"\bvisit (?:the |their )?(?:official )?website\b",
    r"\bcontact (?:the )?admissions\b",
    r"\blikely has\b",
    r"\bmight include\b",
    r"\bi can suggest\b",
    r"\bgeneral information\b",
    r"\bno information (?:is )?available\b",
    r"\bdoes not contain any information\b",
    r"\bnot (?:in|within) the provided context\b",
    r"\blimited information available\b",
]

PEOPLE_SIGNALS = re.compile(
    r"\b(?:Director|Founder|Faculty|Professor|Dean|Board Member|Head of)\b",
    re.IGNORECASE,
)


def format_context(nodes: list, max_chars_per_node: int = 1500) -> str:
    parts = []
    for i, node in enumerate(nodes[:8], 1):
        source = node.metadata.get("file_name") or node.metadata.get("source") or f"source-{i}"
        text = (node.text or "").strip()
        if text:
            parts.append(f"--- [{source}] ---\n{text[:max_chars_per_node]}")
    return "\n\n".join(parts)


def is_generic_answer(answer: str) -> bool:
    lower = answer.lower()
    return any(re.search(p, lower) for p in GENERIC_PATTERNS)


def context_has_relevant_facts(context: str, question: str) -> bool:
    if not context.strip():
        return False
    q = question.lower()
    if re.search(r"\b(faculty|staff|director|professor|teacher|roster)\b", q):
        return bool(PEOPLE_SIGNALS.search(context))
    return len(context) > 200


def is_bullet_heavy(text: str) -> bool:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) < 2:
        return False
    bullet_lines = sum(
        1 for ln in lines if re.match(r"^[-*•]\s+", ln) or re.match(r"^\d+\.\s+", ln)
    )
    return bullet_lines >= max(2, len(lines) // 2)


def is_run_on_mash(text: str) -> bool:
    """Heuristic: text looks like bullet lines joined into one awkward paragraph."""
    if is_bullet_heavy(text):
        return False
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) != 1:
        return False
    block = paragraphs[0]
    sentences = re.split(r"(?<=[.?!])\s+", block)
    if len(sentences) <= 1 and (len(block) > 350 or block.count(",") > 10):
        return True
    return False


def prose_quality_ok(text: str) -> bool:
    if not text or len(text.strip()) < 40:
        return False
    if is_generic_answer(text):
        return False
    if is_run_on_mash(text):
        return False
    return True


def normalize_bullet_list(text: str) -> str:
    """Clean bullet formatting when keeping a list."""
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        stripped = re.sub(r"^[-*•]\s+", "", stripped)
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        if stripped:
            out.append(f"- {stripped}")
    return "\n".join(out).strip()


def sanitize_answer(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\\n", "\n").strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    kept = []
    for p in paragraphs:
        lower = p.lower()
        if any(
            x in lower
            for x in (
                "visit their official website",
                "contact their admissions",
                "i recommend visiting",
                "i can suggest some general",
            )
        ):
            continue
        kept.append(p)
    return "\n\n".join(kept) if kept else text.strip()


def try_rewrite_bullets_as_prose(draft: str, question: str, llm) -> str:
    prompt = PROSE_FROM_DRAFT_PROMPT.format(question=question, draft=draft)
    return sanitize_answer(llm.complete(prompt).text)


def finalize_format(answer: str, question: str, llm) -> str:
    """
    Prefer paragraphs. If the model returned bullets, try a proper prose rewrite.
    Keep bullets only when prose rewrite fails or would read worse.
    """
    if not is_bullet_heavy(answer):
        return answer

    prose_attempt = try_rewrite_bullets_as_prose(answer, question, llm)
    if prose_attempt and prose_quality_ok(prose_attempt) and not is_bullet_heavy(prose_attempt):
        return prose_attempt

    # Prose rewrite still lists or reads poorly — keep bullets, don't mash into one paragraph
    return normalize_bullet_list(answer)


def generate_answer(question: str, nodes: list, llm) -> str:
    context = format_context(nodes)
    if not context:
        return ""

    prompt = STRICT_PROMPT.format(system=STRICT_SYSTEM, context=context, question=question)
    answer = sanitize_answer(llm.complete(prompt).text)

    needs_retry = (
        not answer
        or is_generic_answer(answer)
        or (context_has_relevant_facts(context, question) and len(answer) < 80)
    )

    if needs_retry:
        retry_prompt = SUMMARY_RETRY_PROMPT.format(question=question, context=context)
        retried = sanitize_answer(llm.complete(retry_prompt).text)
        if retried and len(retried) > 50 and not is_generic_answer(retried):
            answer = retried

    return finalize_format(answer, question, llm)
