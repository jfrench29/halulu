"""Grader for closed_factual questions.

Uses word-boundary matching with normalization to avoid false positives
from substring collisions (e.g., "Au" matching inside "automatic").
"""

from __future__ import annotations

import re

from grading.normalization import normalize_text, detect_refusal
from grading.schemas import GradeResult

_BOUNDARY_THRESHOLD = 5


def _fact_in_response(norm_fact: str, norm_resp: str) -> bool:
    if not norm_fact:
        return False
    if len(norm_fact) < _BOUNDARY_THRESHOLD:
        return bool(re.search(r"\b" + re.escape(norm_fact) + r"\b", norm_resp))
    return norm_fact in norm_resp


def grade_closed_factual(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    answer = test_case.get("correct_answer", "")
    reference_facts = test_case.get("reference_facts", [answer] if answer else [])

    norm_resp = normalize_text(response)

    for fact in reference_facts:
        norm_fact = normalize_text(fact)
        if _fact_in_response(norm_fact, norm_resp):
            return GradeResult(
                result="correct",
                reason=f"Answer '{fact}' found in response",
                details={"matched_behavior": "exact_match"},
            )

    norm_ans = normalize_text(answer)
    if _fact_in_response(norm_ans, norm_resp):
        return GradeResult(
            result="correct",
            reason=f"Answer '{answer}' found in response",
            details={"matched_behavior": "exact_match"},
        )

    return GradeResult(
        result="incorrect",
        severity=2,
        reason=f"Expected '{answer}', not found in response",
    )
