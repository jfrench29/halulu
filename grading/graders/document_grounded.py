"""Grader for document_grounded questions.

Claims must be supported by the source document embedded in the prompt.
"""

from __future__ import annotations

from grading.normalization import normalize_text, detect_refusal
from grading.schemas import GradeResult


def grade_document_grounded(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    answer = test_case.get("correct_answer", "")
    reference_facts = test_case.get("reference_facts", [answer] if answer else [])

    norm_resp = normalize_text(response)

    for fact in reference_facts:
        norm_fact = normalize_text(fact)
        if norm_fact and norm_fact in norm_resp:
            return GradeResult(
                result="correct",
                reason=f"Response contains grounded fact: '{fact}'",
                details={"matched_behavior": "answer_from_document"},
            )

    # Fallback to correct_answer
    norm_ans = normalize_text(answer)
    if norm_ans and norm_ans in norm_resp:
        return GradeResult(
            result="correct",
            reason=f"Response contains '{answer}'",
            details={"matched_behavior": "answer_from_document"},
        )

    return GradeResult(
        result="incorrect",
        reason=f"Expected grounded answer '{answer}', not found in response",
    )
