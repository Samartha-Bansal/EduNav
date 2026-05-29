"""Answer post-processing — only reject empty or clearly invalid responses."""

import re

NOT_FOUND_PHRASES = (
    "i could not find that information",
    "i couldn't find that information",
    "not in the program documents",
    "not found in the program documents",
)


def is_refusal(answer: str) -> bool:
    if not answer or not answer.strip():
        return True
    lower = answer.lower().strip()
    return any(phrase in lower for phrase in NOT_FOUND_PHRASES)


def has_substantive_content(answer: str, min_words: int = 12) -> bool:
    words = re.findall(r"\w+", answer)
    return len(words) >= min_words


class AnswerValidator:
    """Legacy wrapper — no longer blocks answers based on token overlap."""

    def validate(self, question: str, answer: str, context: str) -> bool:
        return bool(answer and answer.strip()) and not is_refusal(answer)

    def get_final_answer(self, question: str, answer: str, context: str) -> str:
        if answer and answer.strip() and not is_refusal(answer):
            return answer.strip()
        return answer.strip() if answer else ""
