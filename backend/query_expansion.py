"""Build retrieval queries — always anchored to Masters' Union."""

import re

from mu_text import MU_CANONICAL, has_mu_reference, normalize_mu_aliases

MU_ANCHOR = MU_CANONICAL

TOPIC_EXPANSIONS = [
    (
        re.compile(r"\b(founder|co-?founder|founders|founding)\b", re.I),
        ["Pratham Mittal", "Masters Union founder", "founding team", "leadership"],
    ),
    (
        re.compile(
            r"\b(facult(?:y|ies)|staff|director|professor|instructor|teacher|roster|mahak|dean|names?)\b",
            re.I,
        ),
        ["faculty", "director", "roster", "Mahak Garg", "Masters Union leadership"],
    ),
    (
        re.compile(r"\b(fee|fees|tuition|cost|price|scholarship|financial)\b", re.I),
        ["fees", "tuition", "scholarship", "PGP TBM", "UG TBM"],
    ),
    (
        re.compile(
            r"\b(placement|salary|career|internship|recruit|package|compan(?:y|ies)|recruiter|visit(?:ing|s)?|hiring)\b",
            re.I,
        ),
        ["placement", "salary", "career outcomes", "recruiters", "companies visited", "cohort"],
    ),
    (
        re.compile(r"\b(admission|admit|apply|application|eligib|deadline|requirement)\b", re.I),
        ["admissions", "eligibility", "application", "deadline"],
    ),
    (
        re.compile(
            r"\b(course|curriculum|programme|program|syllabus|module|elective|degree|ug|pgp|tbm|psm)\b",
            re.I,
        ),
        ["curriculum", "courses", "programme structure", "PGP TBM", "UG TBM"],
    ),
    (
        re.compile(
            r"\b(campus|hostel|immersion|bharat|fellowship|cohort|located|situated|location|address|where)\b",
            re.I,
        ),
        ["campus", "location", "Gurugram", "address", "immersion", "student life", "Masters Union"],
    ),
    (
        re.compile(r"\b(board|trustee|govern|chair)\b", re.I),
        ["board", "leadership", "Masters Union governance"],
    ),
]


def build_retrieval_query(
    question: str,
    query_type: str,
    history_hints: list[str] | None = None,
) -> str:
    """
    Expand question for vector search. Implicitly scoped to Masters' Union
    (users are on the MU help site — they should not need to repeat the name).
    """
    q = normalize_mu_aliases(question.strip())
    ql = q.lower()
    extras: list[str] = []

    if query_type == "curriculum":
        extras.extend(["curriculum", "courses", "programme structure"])

    for pattern, terms in TOPIC_EXPANSIONS:
        if pattern.search(q):
            extras.extend(terms)

    if history_hints:
        extras.extend(history_hints[:6])

    # Always anchor retrieval to Masters' Union unless already explicit (incl. MU shorthand)
    if not has_mu_reference(q):
        extras.insert(0, MU_ANCHOR)

    if re.search(r"\b(?:he|she|him|her|they|it|that|this|here|there)\b", q, re.I) and history_hints:
        extras.extend(history_hints[:8])

    if not extras:
        return f"{q} {MU_ANCHOR}"

    unique = list(dict.fromkeys(extras))
    return f"{q} {' '.join(unique)}"
