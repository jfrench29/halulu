"""Shared data classes for the grading system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResultType(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    HALLUCINATED = "hallucinated"
    REFUSED = "refused"


class HallucinationSubtype(str, Enum):
    FABRICATED_FACT = "fabricated_fact"
    FABRICATED_ENTITY = "fabricated_entity"
    FABRICATED_CITATION = "fabricated_citation"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    NUMERICAL_ERROR = "numerical_error"


@dataclass
class GradeResult:
    """Output of every grading function.

    Maps to the JSON output format:
    {
        "result": "correct",
        "reason": "Recognized false premise",
        "hallucination_subtype": null,
        "details": {...}
    }
    """

    result: str  # ResultType value
    reason: str = ""
    hallucination_subtype: str | None = None
    confidence: float = 1.0
    details: dict = field(default_factory=dict)

    # Backward-compat aliases so evaluate_models.py can still read .grade / .explanation
    @property
    def grade(self) -> str:
        return self.result

    @property
    def explanation(self) -> str:
        return self.reason
