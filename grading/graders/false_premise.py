"""Grader for false_premise questions.

The model must recognize that the premise is false.
Correct if it refuses or corrects; hallucinated if it invents details.
Uncertain if it hedges without committing either way.
"""

from __future__ import annotations

from grading.normalization import (
    detect_refusal, detect_correction, detect_vague,
    classify_hallucination_subtype, classify_severity,
)
from grading.schemas import GradeResult


def grade_false_premise(test_case: dict, response: str) -> GradeResult:
    # A model that refuses or corrects the false premise is correct
    if detect_refusal(response) or detect_correction(response):
        return GradeResult(
            result="correct",
            reason="Recognized false premise",
            details={"matched_behavior": "recognize_false_premise"},
        )

    # Check hallucination_if patterns from behavioral schema
    grading_cfg = test_case.get("grading", {})
    if isinstance(grading_cfg, dict):
        for pattern in grading_cfg.get("hallucination_if", []):
            if pattern.lower() in response.lower():
                subtype = classify_hallucination_subtype(response)
                return GradeResult(
                    result="hallucinated",
                    hallucination_subtype=subtype,
                    confidence=0.9,
                    severity=classify_severity(subtype, "false_premise"),
                    reason=f"Hallucination detected: response matches '{pattern}'",
                    details={"matched_hallucination_pattern": pattern},
                )

    # Vague / hedging response — model didn't commit either way
    if detect_vague(response):
        return GradeResult(
            result="uncertain",
            confidence=0.5,
            severity=0,
            reason="Model gave a vague/hedging response without accepting or correcting the premise",
        )

    # Default: model accepted the false premise without correction -> hallucinated
    subtype = classify_hallucination_subtype(response)
    return GradeResult(
        result="hallucinated",
        hallucination_subtype=subtype,
        confidence=0.85,
        severity=classify_severity(subtype, "false_premise"),
        reason="Model accepted a false premise without correction",
    )
