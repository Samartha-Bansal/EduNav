"""Detect off-topic questions — Masters' Union scope only.

Users are on the Masters' Union help assistant; assume questions are in-scope
unless they are clearly unrelated (weather, generic coding help, etc.).
Avoid false refusals on vague or follow-up questions.
"""

import re

REFUSAL_MESSAGE = (
    "I'm the **Masters' Union Program Help** assistant. I can only answer questions about "
    "Masters' Union — programs (PGP TBM, UG TBM), admissions, courses, fees, faculty, "
    "placements, and campus life.\n\n"
    "Please ask something related to Masters' Union."
)

LOW_RELEVANCE_MESSAGE = (
    "I couldn't find clear information about that in the Masters' Union program documents I have. "
    "You can try rephrasing, or ask about programs, admissions, courses, fees, faculty, or placements."
)

# Clearly unrelated to a university program assistant
OFF_TOPIC_PATTERNS = [
    r"\b(weather|forecast)\b",
    r"\b(recipe|cook|ingredient)\b",
    r"\b(write|debug|fix)\s+(?:me\s+)?(?:a\s+)?(?:python|javascript|java|c\+\+|code)\b",
    r"\bwho\s+(?:is|was)\s+(?:the\s+)?president\s+of\s+(?:the\s+)?(?:united states|usa|india|france|china)\b",
    r"\bcapital\s+of\b",
    r"\b(tell|write)\s+(?:me\s+)?(?:a\s+)?(?:joke|poem|story|song)\b",
    r"\b(movie|netflix|cricket\s+score|football\s+score|ipl\s+score)\b",
    r"\b(bitcoin|crypto|stock\s+market|forex)\b",
    r"\btranslate\b.+\bto\s+(?:spanish|french|hindi|german|chinese)\b",
    r"\bcompare\b.+\b(harvard|stanford|mit)\b(?!.*masters)",
]

MU_MARKERS = re.compile(
    r"masters['\u2019\s]*union|mastersunion|master['\u2019]s\s+union|"
    r"\bpgp[\s-]*tbm\b|\bug[\s-]*tbm\b|\bug[\s-]*psm\b|\btbm\b|\bmubf\b",
    re.IGNORECASE,
)

PROGRAM_TOPIC_KEYWORDS = re.compile(
    r"\b(admission|admit|apply|application|eligib|requirement|deadline|"
    r"course|curriculum|programme|program|syllabus|module|elective|degree|"
    r"fees?|tuition|cost|scholarship|financial|"
    r"faculty|professor|director|staff|roster|dean|"
    r"placement|salary|career|internship|recruit|"
    r"campus|hostel|immersion|cohort|class\s+of|"
    r"founder|board|mba|undergraduate|postgraduate|"
    r"student|learn|skill|technology|business|fellowship|incubat|startup|"
    r"challenge|report|brochure|cohort|batch|year)\b",
    re.IGNORECASE,
)

GREETING_RE = re.compile(
    r"^(?:\s*(?:hello|hi|hey|thanks|thank you|ok|okay|bye|goodbye|good morning|good evening)[\s!.,?]*\s*)+$",
    re.IGNORECASE,
)


def mentions_masters_union(text: str) -> bool:
    return bool(MU_MARKERS.search(text))


def is_program_related(text: str) -> bool:
    return bool(PROGRAM_TOPIC_KEYWORDS.search(text))


def is_clearly_off_topic(question: str, conversation_context: str = "") -> bool:
    """
    Only block obvious non-MU requests. Vague questions default to in-scope.
    conversation_context: recent Q&A — used so follow-ups inherit topic.
    """
    combined = f"{question}\n{conversation_context}".lower().strip()
    q = question.lower().strip()

    if len(q) < 2:
        return True

    if GREETING_RE.match(q):
        return False

    # Explicit MU or program vocabulary anywhere in thread → in scope
    if mentions_masters_union(combined) or is_program_related(combined):
        for pattern in OFF_TOPIC_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return True
        return False

    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return True

    # On the MU assistant: do NOT treat generic "who is X" as off-topic
    return False


def is_low_relevance(nodes: list, threshold: float = 0.45) -> bool:
    """Weak retrieval signal — used only for retry decisions, not hard refusal."""
    if not nodes:
        return True
    top = nodes[0]
    score = getattr(top, "score", None)
    if score is None:
        return False
    score = float(score)
    if score < 0:
        return score < -2.5
    if score <= 1.0:
        return score < threshold
    return False


def should_refuse(
    question: str,
    nodes: list,
    conversation_context: str = "",
    *,
    after_generation: bool = False,
) -> tuple[bool, str]:
    """
    Hard refusal only for clearly off-topic questions.
    Low retrieval quality is handled by retries + LLM, not pre-emptive refusal.
    """
    if is_clearly_off_topic(question, conversation_context):
        return True, REFUSAL_MESSAGE

    if after_generation:
        # Only suggest not-found when we truly have no chunks to work with
        if not nodes:
            return True, LOW_RELEVANCE_MESSAGE

    return False, ""
