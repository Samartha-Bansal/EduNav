"""Strict answer synthesis — grounded summaries only; never output scope boilerplate."""

import re

STRICT_SYSTEM = """You are the Masters' Union Program Help assistant.

Answer using ONLY the document excerpts below about Masters' Union (programs, people, campus, placements).

RULES:
- Write 2–4 short paragraphs of clear prose when excerpts contain relevant facts.
- Questions about founders, faculty, courses, fees, admissions, or placements ARE about Masters' Union — answer from excerpts.
- "MU", "M.U.", "Master Union", "Masters Union", or misspellings (maters union) mean this school.
- If excerpts truly lack the answer, say ONLY: "I could not find that in Masters' Union program documents."

NEVER output:
- A message saying you "can only answer questions about Masters' Union" (the user is already on the MU site).
- Outside knowledge not in excerpts.
- "The excerpts do not mention…" followed by unrelated MU marketing.
"""

FOUNDER_PROMPT = """Using ONLY the excerpts below, answer the question about Masters' Union leadership/founder.
Focus on Pratham Mittal or whoever the excerpts name as founder or founding partner.
Write 2–3 paragraphs. If founder details are missing, say you could not find that in Masters' Union program documents.

Excerpts:
{context}

Question: {question}

Answer:"""

MU_SUMMARY_PROMPT = """Summarize information from the excerpts below to answer the question about Masters' Union.
Use 2–4 short paragraphs. Only facts from excerpts.

Excerpts:
{context}

Question: {question}

Answer:"""

STRICT_PROMPT = """{system}

DOCUMENT EXCERPTS:
{context}

QUESTION: {question}

Answer:"""

GENERIC_PATTERNS = [
    r"\bunfortunately\b",
    r"\bi recommend\b",
    r"\bvisit (?:the |their )?(?:official )?website\b",
    r"\bcontact (?:the )?admissions\b",
    r"\bhowever,?\s+they do provide\b",
    r"\bthe excerpts (?:provided )?do not mention\b",
    r"\bwhile .+ is not mentioned\b",
    r"\bin summary,?\s+while\b",
    r"\bmight be a distraction\b",
    r"\bancient civilization\b",
    r"\b\d{1,4}\s*(?:bce|ce)\b",
    r"\bi can only answer questions about masters",
    r"\bprogram help\*\* assistant\b",
]

NOT_ANSWERED_PATTERNS = [
    r"could not find",
    r"couldn't find",
    r"do not mention",
    r"does not mention",
    r"not mentioned in",
    r"no information about",
    r"not possible to determine",
]

FOUNDER_RE = re.compile(r"\b(founder|co-?founder|founders|founding)\b", re.I)


def format_context(nodes: list, max_chars_per_node: int = 1500) -> str:
    parts = []
    for i, node in enumerate(nodes[:6], 1):
        source = node.metadata.get("file_name") or node.metadata.get("source") or f"source-{i}"
        text = (node.text or "").strip()
        if text:
            parts.append(f"--- [{source}] ---\n{text[:max_chars_per_node]}")
    return "\n\n".join(parts)


def is_generic_answer(answer: str) -> bool:
    lower = answer.lower()
    return any(re.search(p, lower) for p in GENERIC_PATTERNS)


def is_not_answered_response(answer: str) -> bool:
    lower = answer.lower()
    return any(re.search(p, lower) for p in NOT_ANSWERED_PATTERNS)


def is_scope_refusal_answer(answer: str) -> bool:
    from answer_validator import is_scope_refusal

    return is_scope_refusal(answer)


def is_bullet_heavy(text: str) -> bool:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) < 2:
        return False
    bullet_lines = sum(
        1 for ln in lines if re.match(r"^[-*•]\s+", ln) or re.match(r"^\d+\.\s+", ln)
    )
    return bullet_lines >= max(2, len(lines) // 2)


def normalize_bullet_list(text: str) -> str:
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
    return text.replace("\\n", "\n").strip()


def finalize_format(answer: str) -> str:
    if is_bullet_heavy(answer):
        return normalize_bullet_list(answer)
    return answer


def _bad_answer(answer: str) -> bool:
    return (
        not answer
        or is_scope_refusal_answer(answer)
        or is_not_answered_response(answer)
        or is_generic_answer(answer)
    )


def generate_answer(question: str, nodes: list, llm, *, mu_program_question: bool = False) -> str:
    context = format_context(nodes)
    if not context:
        return ""

    prompt = STRICT_PROMPT.format(system=STRICT_SYSTEM, context=context, question=question)
    answer = sanitize_answer(llm.complete(prompt).text)

    if _bad_answer(answer) and mu_program_question:
        if FOUNDER_RE.search(question):
            retry_prompt = FOUNDER_PROMPT.format(context=context, question=question)
        else:
            retry_prompt = MU_SUMMARY_PROMPT.format(context=context, question=question)
        retry = sanitize_answer(llm.complete(retry_prompt).text)
        if retry and not is_scope_refusal_answer(retry):
            answer = retry

    if _bad_answer(answer) and mu_program_question and not FOUNDER_RE.search(question):
        retry = sanitize_answer(
            llm.complete(FOUNDER_PROMPT.format(context=context, question=question)).text
        )
        if retry and not is_scope_refusal_answer(retry):
            answer = retry

    return finalize_format(answer)
