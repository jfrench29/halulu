"""Shared data classes for the grading system."""

from __future__ import annotations

from dataclasses import dataclass, field


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
