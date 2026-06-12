"""Masters' Union name variants, abbreviations (MU), and spelling normalization."""

import re

MU_CANONICAL = "Masters Union"

# Full name, abbreviations, program codes, common typos
MU_MARKERS = re.compile(
    r"masters?\s+union|mastersunion|master['\u2019\s]*union|"
    r"maters\s+union|mastrs\s+union|master\s+unoin|masters\s+unoin|"
    r"\bmu\b|m\.u\.|"
    r"\bpgp[\s-]*tbm\b|\bug[\s-]*tbm\b|\bug[\s-]*psm\b|\btbm\b|\bmubf\b",
    re.IGNORECASE,
)

# Phrase-level fixes (order matters — full names before bare "MU")
_PHRASE_REPLACEMENTS = [
    (re.compile(r"\bm\.u\.", re.I), MU_CANONICAL),
    (re.compile(r"\bmaters\s+union\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmastrs\s+union\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmaster\s+unoin\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmasters\s+unoin\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmastersunion\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmasters?['\u2019\s]*union\b", re.I), MU_CANONICAL),
    (re.compile(r"\bmaster\s+union\b", re.I), MU_CANONICAL),
]

# Standalone MU (on this assistant, MU = Masters' Union)
_MU_ABBREV_RE = re.compile(r"\bmu\b", re.I)


def normalize_mu_aliases(text: str) -> str:
    """
    Expand MU / M.U. and fix common Masters' Union spelling variants.
    Used before classification, retrieval, and LLM calls.
    """
    if not text or not text.strip():
        return text

    result = text.strip()
    for pattern, replacement in _PHRASE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    result = _MU_ABBREV_RE.sub(MU_CANONICAL, result)
    return result


def mentions_masters_union(text: str) -> bool:
    if not text:
        return False
    normalized = normalize_mu_aliases(text)
    return bool(MU_MARKERS.search(normalized))


def has_mu_reference(text: str) -> bool:
    return mentions_masters_union(text)
