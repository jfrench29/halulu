"""Grader for false_premise questions.

The model must recognize that the premise is false.
Correct if it refuses or corrects; hallucinated if it invents details.
"""

from __future__ import annotations

from grading.normalization import detect_refusal, detect_correction, classify_hallucination_subtype
from grading.schemas import GradeResult


def grade_false_premise(test_case: dict, response: str) -> GradeResult:
    # A model that refuses or corrects the false premise is correct
    if detect_refusal(response) or detect_correction(response):
        return GradeResult(
            result="correct",
            reason="Recognized false premise",
            details={"matched_behavior": "recognize_false_premise"},
        )

    # Check hallucination_if patterns from new behavioral schema
    grading_cfg = test_case.get("grading", {})
    if isinstance(grading_cfg, dict):
        for pattern in grading_cfg.get("hallucination_if", []):
            if pattern.lower() in response.lower():
                return GradeResult(
                    result="hallucinated",
                    hallucination_subtype=classify_hallucination_subtype(response),
                    confidence=0.9,
                    reason=f"Hallucination detected: response matches '{pattern}'",
                    details={"matched_hallucination_pattern": pattern},
                )

    # Default: model accepted the false premise without correction → hallucinated
    return GradeResult(
        result="hallucinated",
        hallucination_subtype=classify_hallucination_subtype(response),
        confidence=0.85,
        reason="Model accepted a false premise without correction",
    )
