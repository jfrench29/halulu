"""Grader for numerical questions.

Normalizes numeric formats and supports tolerance matching.
Handles: "$27B", "27 billion", "about 27 billion dollars", "299,792,458".
"""

from __future__ import annotations

from grading.normalization import extract_numbers, detect_refusal
from grading.schemas import GradeResult


def grade_numerical(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    answer_str = test_case.get("correct_answer", "")

    grading_cfg = test_case.get("grading", {})
    if isinstance(grading_cfg, dict):
        tolerance = grading_cfg.get("tolerance", 0)
    else:
        tolerance = test_case.get("tolerance", 0)

    expected_nums = extract_numbers(answer_str)
    if not expected_nums:
        try:
            expected_nums = [float(answer_str)]
        except ValueError:
            return GradeResult(
                result="incorrect",
                reason="Could not parse expected answer as number",
            )

    expected = expected_nums[0]

    actual_nums = extract_numbers(response)
    if not actual_nums:
        return GradeResult(
            result="incorrect",
            severity=2,
            reason=f"No numeric value found in response (expected {expected})",
        )

    for actual in actual_nums:
        if abs(actual - expected) <= tolerance:
            return GradeResult(
                result="correct",
                reason=f"Numeric match: {actual} ≈ {expected}",
                details={"matched_behavior": "numeric_match", "extracted_value": actual},
            )

    return GradeResult(
        result="incorrect",
        severity=2,
        reason=f"No numeric value close to {expected} found (got: {actual_nums[:5]})",
    )
