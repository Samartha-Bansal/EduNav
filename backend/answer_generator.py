"""Strict answer synthesis — single LLM call; no outside knowledge."""

import re

from topic_guard import REFUSAL_MESSAGE

STRICT_SYSTEM = """You are the Masters' Union Program Help assistant.

Answer using ONLY the document excerpts below.

WHEN TO ANSWER (write 2–4 short paragraphs):
- Questions about Masters' Union courses, programs, curriculum, electives, modules, fees, admissions, faculty, placements, or campus life.
- Phrases like "your courses" or "what you offer" mean Masters' Union — summarize program/course facts from the excerpts even if they use different wording (e.g. electives, curriculum, PGP TBM, UG TBM).

WHEN TO REFUSE:
- Only if the question is clearly NOT about Masters' Union (history, science, other exams, general trivia) AND excerpts have nothing relevant.
- In that case say in one sentence: "I could not find that in Masters' Union program documents."

FORBIDDEN:
- Outside knowledge (dates, history, science, math not in excerpts)
- "The excerpts do not mention…", "however they discuss…", "might be a distraction"
- Refusing a Masters' Union program question when excerpts describe courses or curriculum
- "visit the website", "contact admissions", "unfortunately"
"""

MU_SUMMARY_PROMPT = """Summarize Masters' Union course and program information from the excerpts below to answer the question.
Use 2–4 short paragraphs. Only use facts from the excerpts.

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


def _looks_like_scope_refusal(text: str) -> bool:
    lower = (text or "").lower()
    return "i can only answer questions about masters" in lower or "program help** assistant" in lower


def generate_answer(question: str, nodes: list, llm, *, mu_program_question: bool = False) -> str:
    context = format_context(nodes)
    if not context:
        return ""

    prompt = STRICT_PROMPT.format(system=STRICT_SYSTEM, context=context, question=question)
    answer = sanitize_answer(llm.complete(prompt).text)

    if mu_program_question and (
        _looks_like_scope_refusal(answer) or is_not_answered_response(answer) or not answer
    ):
        retry = sanitize_answer(
            llm.complete(
                MU_SUMMARY_PROMPT.format(context=context, question=question)
            ).text
        )
        if retry and not _looks_like_scope_refusal(retry):
            answer = retry

    return finalize_format(answer)
