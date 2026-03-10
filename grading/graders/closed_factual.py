"""Grader for closed_factual questions.

Uses word-boundary matching with normalization to avoid false positives
from substring collisions (e.g., "Au" matching inside "automatic").
"""

from __future__ import annotations

from grading.normalization import normalize_text, detect_refusal, fact_in_response
from grading.schemas import GradeResult


def grade_closed_factual(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    answer = test_case.get("correct_answer", "")
    reference_facts = test_case.get("reference_facts", [answer] if answer else [])

    norm_resp = normalize_text(response)

    for fact in reference_facts:
        norm_fact = normalize_text(fact)
        if fact_in_response(norm_fact, norm_resp):
            return GradeResult(
                result="correct",
                reason=f"Answer '{fact}' found in response",
                details={"matched_behavior": "exact_match"},
            )

    norm_ans = normalize_text(answer)
    if fact_in_response(norm_ans, norm_resp):
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
