"""Lightweight keyword-based query classification (no heavy ML models)."""

import re


class QueryClassifier:
    CATEGORIES = {
        "admission": [
            r"\badmission\b",
            r"\bapply\b",
            r"\beligib",
            r"\brequirement",
            r"\bdeadline\b",
        ],
        "curriculum": [
            r"\bcourse\b",
            r"\bcurriculum\b",
            r"\blearn\b",
            r"\bskill",
            r"\bsyllabus\b",
            r"\bmodule\b",
        ],
        "fees": [r"\bfee\b", r"\btuition\b", r"\bcost\b", r"\bprice\b", r"\bscholarship\b"],
        "placement": [r"\bplacement\b", r"\bsalary\b", r"\bcareer\b", r"\binternship\b"],
        "faculty": [
            r"\bfaculty\b",
            r"\bstaff\b",
            r"\bdirector\b",
            r"\bprofessor\b",
            r"\bteacher\b",
            r"\broster\b",
        ],
        "comparison": [r"\bcompare\b", r"\bdifference\b", r"\bvs\b", r"\bbetter\b"],
        "temporal": [r"\bwhen\b", r"\bduration\b", r"\bhow long\b", r"\bdeadline\b"],
    }

    def classify(self, query: str) -> str:
        query_lower = query.lower()
        for category, patterns in self.CATEGORIES.items():
            if any(re.search(pattern, query_lower) for pattern in patterns):
                return category
        return "informational"

    def get_filters(self, query_type: str) -> dict:
        mapping = {
            "admission": {"document_type": "admission"},
            "curriculum": {"document_type": "curriculum"},
            "fees": {"document_type": "fees"},
        }
        return mapping.get(query_type, {})
