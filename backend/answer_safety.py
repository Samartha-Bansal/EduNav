"""Detect answers that leak outside knowledge or dodge scope refusal."""

import re

from topic_guard import REFUSAL_MESSAGE

# Facts the model must not invent when absent from retrieved context
OUTSIDE_KNOWLEDGE_RE = [
    re.compile(r"\b\d{1,4}\s*(?:bce|b\.c\.e?|ce|a\.d\.|ad)\b", re.I),
    re.compile(r"\bancient civilization\b", re.I),
    re.compile(r"\bconquered by (?:the )?romans?\b", re.I),
    re.compile(r"\begyptian empire\b", re.I),
    re.compile(r"\b3100\b|\b30\s+bce\b", re.I),
    re.compile(r"\ba\^2\s*\+\s*b\^2\s*=\s*c\^2\b", re.I),
    re.compile(r"\bhypotenuse\b", re.I),
    re.compile(r"\bpythagoras(?:'s)?\s+theorem\b", re.I),
    re.compile(r"\bright\s+triangle\b", re.I),
]

META_DODGE_RE = [
    re.compile(r"\bthe (?:provided )?excerpts\b", re.I),
    re.compile(r"\b(?:do not|does not|don't) mention\b", re.I),
    re.compile(r"\bnot (?:possible|able) to determine\b", re.I),
    re.compile(r"\b(?:might be a )?distraction\b", re.I),
    re.compile(r"\bhowever,?\s+if we consider\b", re.I),
    re.compile(r"\bgiven the information provided\b", re.I),
    re.compile(r"\binstead of\b", re.I),
    re.compile(r"\bnational eligibility\b", re.I),
]


def _context_text(context: str) -> str:
    return (context or "").lower()


def answer_contains_outside_knowledge(answer: str, context: str) -> bool:
    """Answer cites world facts not present in retrieved excerpts."""
    if not answer:
        return False
    ctx = _context_text(context)
    lower = answer.lower()
    for pattern in OUTSIDE_KNOWLEDGE_RE:
        match = pattern.search(lower)
        if match:
            snippet = match.group(0).lower()
            if snippet not in ctx and not _fact_in_context(snippet, ctx):
                return True
    return False


def _fact_in_context(snippet: str, ctx: str) -> bool:
    words = re.findall(r"[a-z0-9]+", snippet)
    if not words:
        return False
    return sum(1 for w in words if len(w) > 2 and w in ctx) >= max(1, len(words) // 2)


def answer_dodges_instead_of_refusing(answer: str) -> bool:
    """Model explains it can't find info but still riffing — treat as bad."""
    if not answer:
        return False
    hits = sum(1 for p in META_DODGE_RE if p.search(answer))
    return hits >= 2 or (
        hits >= 1 and len(answer) > 180
    )


def sanitize_or_refuse(answer: str, context: str, force_refusal: bool = False) -> str:
    if force_refusal:
        return REFUSAL_MESSAGE
    if answer_contains_outside_knowledge(answer, context):
        return REFUSAL_MESSAGE
    if answer_dodges_instead_of_refusing(answer):
        return REFUSAL_MESSAGE
    return answer
