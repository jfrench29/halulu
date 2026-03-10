"""Grader for closed_factual questions.

Uses exact or semantic match with normalization.
"""

from __future__ import annotations

import re

from grading.normalization import normalize_text, detect_refusal
from grading.schemas import GradeResult


def grade_closed_factual(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    answer = test_case.get("correct_answer", "")
    reference_facts = test_case.get("reference_facts", [answer] if answer else [])

    norm_resp = normalize_text(response)

    # Check reference_facts first
    for fact in reference_facts:
        norm_fact = normalize_text(fact)
        if norm_fact and norm_fact in norm_resp:
            return GradeResult(
                result="correct",
                reason=f"Answer '{fact}' found in response",
                details={"matched_behavior": "exact_match"},
            )

    # Fallback: check correct_answer directly
    norm_ans = normalize_text(answer)
    if norm_ans and norm_ans in norm_resp:
        return GradeResult(
            result="correct",
            reason=f"Answer '{answer}' found in response",
            details={"matched_behavior": "exact_match"},
        )

    # Regex fallback for partial matches
    if norm_ans:
        pattern = re.compile(re.escape(norm_ans), re.IGNORECASE)
        if pattern.search(response):
            return GradeResult(
                result="correct",
                reason=f"Answer '{answer}' found in response (pattern match)",
                details={"matched_behavior": "exact_match"},
            )

    return GradeResult(
        result="incorrect",
        reason=f"Expected '{answer}', not found in response",
    )
