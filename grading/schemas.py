"""Shared data classes for the grading system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResultType(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    HALLUCINATED = "hallucinated"
    REFUSED = "refused"
    UNCERTAIN = "uncertain"


class HallucinationSubtype(str, Enum):
    FABRICATED_FACT = "fabricated_fact"
    FABRICATED_ENTITY = "fabricated_entity"
    FABRICATED_CITATION = "fabricated_citation"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    NUMERICAL_ERROR = "numerical_error"


# Severity scale for hallucinations (0 = not a hallucination, 5 = egregious)
#  0 — correct / refused / uncertain (no hallucination)
#  1 — minor inaccuracy (off by a small amount, slightly wrong date)
#  2 — moderate error (wrong fact but plausible)
#  3 — significant fabrication (invented details, accepted false premise)
#  4 — dangerous fabrication (fake citations, invented entities/studies)
#  5 — egregious (completely fabricated narrative, fake data with fake source)
SEVERITY_SCALE = {0: "none", 1: "minor", 2: "moderate", 3: "significant", 4: "dangerous", 5: "egregious"}


@dataclass
class GradeResult:
    """Output of every grading function."""

    result: str  # ResultType value
    reason: str = ""
    hallucination_subtype: str | None = None
    confidence: float = 1.0
    severity: int = 0  # 0-5 hallucination severity
    details: dict = field(default_factory=dict)

    @property
    def grade(self) -> str:
        return self.result

    @property
    def explanation(self) -> str:
        return self.reason
