"""Decide if a question belongs to Masters' Union — retrieval fit + topic analysis."""

import re
from typing import List

from topic_guard import (
    REFUSAL_MESSAGE,
    is_clearly_off_topic,
    is_gibberish_or_spam,
    is_implicit_mu_question,
    is_program_related,
    mentions_masters_union,
)

# Exams / tests outside Masters' Union
EXTERNAL_EXAM_RE = re.compile(
    r"\b("
    r"neet|jee|iit[\s-]?jee|upsc|csat|gate\s+exam|clat|aiims|aipmt|"
    r"cbse|icse|ncert|board\s+exam|sat\s+exam|gmat|gre\s+exam|"
    r"cat\s+exam|xat|snap|nmat|cuet|ielts|toefl"
    r")\b",
    re.IGNORECASE,
)

SCIENCE_TOPIC_RE = re.compile(
    r"\b("
    r"quantum(?:\s+theory|\s+mechanics)?|relativity|string\s+theory|"
    r"thermodynamics|photosynthesis|evolution|periodic\s+table|"
    r"law\s+of\s+gravity|big\s+bang|black\s+hole|dna\s+replication|"
    r"pythagoras|pythagorean|theorem|hypotenuse|quadratic\s+formula"
    r")\b",
    re.IGNORECASE,
)

HISTORY_TOPIC_RE = re.compile(
    r"\b("
    r"egyptian|pharaoh|roman empire|ottoman|byzantine|mughal|mongol|"
    r"ancient\s+(?:egypt|greece|rome|china|india)|world\s+war|"
    r"cold\s+war|french\s+revolution|colonial|empire|dynasty|"
    r"mesopotamia|aztec|mayan|inca|crusades|renaissance"
    r")\b",
    re.IGNORECASE,
)

MATH_ACADEMIC_RE = re.compile(
    r"\b("
    r"theorem|proof|equation|integral|derivative|algebra|geometry|"
    r"trigonometry|calculus|polynomial|logarithm|matrix|vector"
    r")\b",
    re.IGNORECASE,
)

EXAM_PREP_RE = re.compile(
    r"\b("
    r"timetable|study\s+plan|study\s+schedule|prep(?:aration)?|"
    r"how\s+to\s+prepare|exam\s+strategy|mock\s+test"
    r")\b",
    re.IGNORECASE,
)

STOP_TERMS = frozenset(
    """
    the a an is are was were be been being have has had do does did will would
    could should may might must shall can need about tell give show what who
    when where why how which that this those these with from for and or but
    not your you me my our their them they it its of in on at to by as if so
    than then also just very really please something anything someone
    masters union master end start begin did was were
    provided excerpts documents information find
    """.split()
)

# User is talking to the MU assistant about "your" offerings — always in scope
ASSISTANT_SCOPE_RE = re.compile(
    r"(?:"
    r"\b(?:tell|explain|describe)\s+(?:me\s+)?about\s+(?:your|the|mu)\b"
    r"|\bwhat\s+(?:are\s+)?(?:your|the)\s+"
    r"|\bwhat\s+(?:is|are)\s+mu\b"
    r"|\bwhat\s+(?:do\s+)?you\s+(?:offer|teach|have|provide)\b"
    r"|\b(?:your|the)\s+(?:courses?|programs?|programmes?|fees?|admissions?|"
    r"placements?|facult(?:y|ies)|campus|curriculum|offerings?|companies?|recruiters?)\b"
    r"|\bmu\s+(?:fees?|courses?|programs?|programmes?|admissions?|placements?|"
    r"facult(?:y|ies)|campus|curriculum|founder|founders?|location|address)\b"
    r"|\b(?:where|located|situated|address)\b.+\b(?:here|campus|mu|masters)\b"
    r"|\b(?:companies?|recruiters?)\b.+\b(?:visit|recruit|hire|come)\b"
    r")",
    re.IGNORECASE,
)

TERM_ALIASES = {
    "courses": ("course", "curriculum", "elective", "module", "programme", "program", "syllabus"),
    "programs": ("program", "programme", "pgp", "tbm", "degree"),
    "programmes": ("program", "programme", "pgp", "tbm"),
    "fees": ("fee", "tuition", "cost", "scholarship"),
    "admissions": ("admission", "apply", "eligibility", "deadline"),
    "placements": ("placement", "salary", "career", "internship", "recruiter", "company"),
    "companies": ("company", "recruiter", "employer", "firm", "visit", "hiring"),
    "faculty": ("professor", "director", "dean", "staff", "roster", "faculties", "instructor"),
    "faculties": ("faculty", "professor", "director", "dean", "staff", "roster", "instructor"),
    "located": ("location", "address", "situated", "campus", "gurugram", "delhi"),
    "situated": ("location", "address", "located", "campus", "gurugram", "delhi"),
}


def _has_mu_context(text: str) -> bool:
    return mentions_masters_union(text) or is_program_related(text)


def is_assistant_scoped_question(question: str) -> bool:
    """Questions directed at this bot about its offerings (e.g. 'your courses')."""
    return bool(ASSISTANT_SCOPE_RE.search(question))


def _term_in_context(term: str, context: str) -> bool:
    if term in context:
        return True
    if term.endswith("s") and term[:-1] in context:
        return True
    if f"{term}s" in context:
        return True
    for alias in TERM_ALIASES.get(term, ()):
        if alias in context:
            return True
    return False


def extract_focus_terms(question: str, max_terms: int = 12) -> List[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", question.lower())
    seen = set()
    terms = []
    for w in words:
        if w in STOP_TERMS or w in seen:
            continue
        seen.add(w)
        terms.append(w)
        if len(terms) >= max_terms:
            break
    return terms


def _node_text(nodes: list, limit: int = 6) -> str:
    parts = []
    for node in nodes[:limit]:
        text = (getattr(node, "text", None) or getattr(node.node, "text", "") or "").strip()
        if text:
            parts.append(text.lower())
    return "\n".join(parts)


def _top_retrieval_score(nodes: list) -> float | None:
    if not nodes:
        return None
    score = getattr(nodes[0], "score", None)
    return float(score) if score is not None else None


def is_weak_retrieval(nodes: list) -> bool:
    score = _top_retrieval_score(nodes)
    if score is None:
        return True
    if score < 0:
        return score < -1.5
    return score < 0.35


def is_world_knowledge_question(question: str, conversation_context: str = "") -> bool:
    """
    General knowledge, other exams, history, math — not Masters' Union.
    Fast check; runs before LLM.
    """
    combined = f"{question}\n{conversation_context}"
    if mentions_masters_union(combined):
        return False

    if is_assistant_scoped_question(question) or is_program_related(question):
        return False

    if is_implicit_mu_question(question, conversation_context):
        return False

    q = question.lower().strip()

    if EXTERNAL_EXAM_RE.search(q):
        return True

    if EXAM_PREP_RE.search(q) and (
        EXTERNAL_EXAM_RE.search(q) or not _has_mu_context(combined)
    ):
        return True

    if HISTORY_TOPIC_RE.search(q):
        return True

    if SCIENCE_TOPIC_RE.search(q):
        return True

    if MATH_ACADEMIC_RE.search(q) and not _has_mu_context(combined):
        return True

    if re.search(r"\bwhen\s+(?:did|was|were)\b", q) and not _has_mu_context(combined):
        return True

    if re.search(r"\bwhat\s+is\s+the\b", q) and re.search(
        r"\b(theorem|law|formula|equation)\b", q
    ):
        return True

    if re.search(r"\b(who|whom)\s+(?:discovered|invented|founded|created)\b", q):
        if HISTORY_TOPIC_RE.search(q) or SCIENCE_TOPIC_RE.search(q):
            return True
        if not _has_mu_context(combined):
            return True

    return False


def is_external_education_question(question: str, conversation_context: str = "") -> bool:
    return bool(EXTERNAL_EXAM_RE.search(question)) and not mentions_masters_union(
        f"{question}\n{conversation_context}"
    )


def is_science_general_question(question: str, conversation_context: str = "") -> bool:
    combined = f"{question}\n{conversation_context}"
    if mentions_masters_union(combined):
        return False
    return bool(SCIENCE_TOPIC_RE.search(question))


def retrieval_supports_question(
    question: str,
    nodes: list,
    conversation_context: str = "",
) -> bool:
    combined = f"{question}\n{conversation_context}"

    if mentions_masters_union(combined):
        return True

    if is_world_knowledge_question(question, conversation_context):
        return False

    if not nodes:
        return False

    context = _node_text(nodes)
    if not context:
        return False

    if not (mentions_masters_union(context) or is_program_related(context)):
        return False

    mu_question = (
        is_assistant_scoped_question(question)
        or is_program_related(question)
        or is_implicit_mu_question(question, conversation_context)
        or is_program_related(combined)
    )

    # Strong MU retrieval — answer program-related / implicit MU questions
    if mu_question and not is_weak_retrieval(nodes):
        return True

    # Good MU chunks retrieved on the dedicated MU bot — don't hard-refuse
    if not is_weak_retrieval(nodes):
        return True

    if mu_question:
        return True

    focus = extract_focus_terms(question)
    if not focus:
        return not is_weak_retrieval(nodes)

    matched = sum(1 for term in focus if _term_in_context(term, context))
    overlap_ratio = matched / len(focus)

    if overlap_ratio < 0.15:
        return False
    if overlap_ratio < 0.3 and is_weak_retrieval(nodes):
        return False

    return True


def evaluate_scope(
    question: str,
    nodes: list,
    conversation_context: str = "",
) -> tuple[bool, str]:
    if is_clearly_off_topic(question, conversation_context):
        return False, REFUSAL_MESSAGE

    if is_gibberish_or_spam(question):
        return False, REFUSAL_MESSAGE

    if is_world_knowledge_question(question, conversation_context):
        return False, REFUSAL_MESSAGE

    if not retrieval_supports_question(question, nodes, conversation_context):
        return False, REFUSAL_MESSAGE

    return True, ""
