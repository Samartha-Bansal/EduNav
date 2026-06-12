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

from mu_text import MU_MARKERS, mentions_masters_union, normalize_mu_aliases

PROGRAM_TOPIC_KEYWORDS = re.compile(
    r"\b(admissions?|admit|apply|application|eligib|requirement|deadline|"
    r"courses?|curriculum|programmes?|programs?|syllabus|modules?|electives?|degrees?|"
    r"fees?|tuition|costs?|scholarships?|financial|"
    r"faculty|professors?|directors?|staff|roster|dean|"
    r"placements?|salaries?|careers?|internships?|recruits?|"
    r"campus|hostels?|immersions?|cohorts?|class\s+of|"
    r"founders?|board|mba|undergraduates?|postgraduates?|"
    r"students?|learn|skills?|technologies?|business|fellowships?|incubat|startups?|"
    r"challenges?|reports?|brochures?|batches?|years?)\b",
    re.IGNORECASE,
)

GREETING_RE = re.compile(
    r"^(?:\s*(?:hello|hi|hey|thanks|thank you|ok|okay|bye|goodbye|good morning|good evening)[\s!.,?]*\s*)+$",
    re.IGNORECASE,
)

# General knowledge / homework — not Masters' Union (stern refusal, not soft not-found)
GENERAL_KNOWLEDGE_PATTERNS = [
    r"\b(law of gravity|theory of relativity|speed of light|periodic table|big bang|black hole)\b",
    r"\b(newton|einstein|darwin|galileo|tesla|edison|shakespeare|mozart|napoleon)\b",
    r"\b(who|whom)\s+(?:wrote|discovered|invented|found|created|developed)\b",
    r"\b(what|when)\s+(?:is|was|are|were)\s+(?:the\s+)?(?:capital|population|president)\s+of\b",
    r"\bwho\s+(?:is|was)\s+(?:the\s+)?(?:president|prime minister|pm|king|queen|monarch|chancellor)\s+of\b",
    r"\b(?:president|prime minister|pm|king|queen)\s+of\s+(?:the\s+)?(?:uk|u\.k\.|united kingdom|britain|england|usa|u\.s\.a?|india|china|france|germany|canada|australia)\b",
    r"\b(homework|worksheet)\s+(?:help|problem|question)\b",
    r"\b(solve|calculate|prove)\s+(?:this|the)\s+(?:equation|integral|derivative|problem)\b",
    r"\b(physics|chemistry|mathematics|algebra|calculus|geography|astronomy)\s+(?:homework|problem|exam)\b",
    r"\b(world war|cold war|french revolution|roman empire)\b",
    r"\b(marvel|harry potter|game of thrones)\b",
    r"\b(neet|jee|iit[\s-]?jee|upsc|gate\s+exam|clat|aiims|cbse|icse)\b",
    r"\bquantum(?:\s+theory|\s+mechanics)?\b",
]


def is_program_related(text: str) -> bool:
    return bool(PROGRAM_TOPIC_KEYWORDS.search(text))


def is_general_knowledge_question(question: str, conversation_context: str = "") -> bool:
    """Science, history, homework, etc. with no Masters' Union angle."""
    from scope_classifier import is_world_knowledge_question

    if is_world_knowledge_question(question, conversation_context):
        return True
    combined = f"{question}\n{conversation_context}"
    if mentions_masters_union(combined):
        return False
    q = question.lower()
    for pattern in GENERAL_KNOWLEDGE_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return True
    return False


def is_gibberish_or_spam(question: str) -> bool:
    """Very long repetitive / meaningless input — do not run RAG."""
    q = question.strip()
    if len(q) < 80:
        return False
    if re.search(r"[a-zA-Z0-9]{100,}", q):
        return True
    words = re.findall(r"[a-zA-Z]{2,}", q)
    if len(q) > 400 and len(words) < 4:
        return True
    if len(words) >= 8:
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        if unique_ratio < 0.18:
            return True
    return False


def is_clearly_off_topic(question: str, conversation_context: str = "") -> bool:
    """
    Only block obvious non-MU requests. Vague questions default to in-scope.
    conversation_context: recent Q&A — used so follow-ups inherit topic.
    """
    combined = normalize_mu_aliases(f"{question}\n{conversation_context}").lower().strip()
    q = normalize_mu_aliases(question).lower().strip()

    if len(q) < 2:
        return True

    if GREETING_RE.match(q):
        return False

    if is_gibberish_or_spam(q):
        return True

    if is_general_knowledge_question(question, conversation_context):
        return True

    # "syllabus" alone is in-scope; "syllabus for NEET" is not — world_knowledge handles that above

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
