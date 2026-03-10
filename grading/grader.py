"""Grading engine — routes to category-specific graders.

Supports both the new behavioral schema (grading is a dict with type/hallucination_if)
and the legacy schema (grading is a string like "exact", "contains", "false_premise").
"""

from __future__ import annotations

from grading.schemas import GradeResult
from grading.graders.closed_factual import grade_closed_factual
from grading.graders.false_premise import grade_false_premise
from grading.graders.citation_trap import grade_citation_trap
from grading.graders.document_grounded import grade_document_grounded
from grading.graders.summarization import grade_summarization
from grading.graders.numerical import grade_numerical

# Map category names to grader functions
_CATEGORY_GRADERS = {
    "closed_factual": grade_closed_factual,
    "false_premise": grade_false_premise,
    "citation_trap": grade_citation_trap,
    "document_grounded": grade_document_grounded,
    "summarization": grade_summarization,
    "numerical": grade_numerical,
}

# Map legacy grading type strings to category graders
_LEGACY_GRADING_MAP = {
    "exact": "closed_factual",
    "contains": "closed_factual",
    "numeric_tolerance": "numerical",
    "false_premise": "false_premise",
    "adversarial": "false_premise",
    "citation_trap": "citation_trap",
    "llm_judge": "summarization",
}


def grade(test_case: dict, response: str) -> GradeResult:
    """Main grading dispatcher.

    Routes by category first (preferred), then falls back to legacy grading type string.
    """
    # Try category-based routing first
    category = test_case.get("category", "")
    if category in _CATEGORY_GRADERS:
        return _CATEGORY_GRADERS[category](test_case, response)

    # Fallback: legacy schema where grading is a string
    grading_type = test_case.get("grading", "exact")
    if isinstance(grading_type, str):
        mapped_category = _LEGACY_GRADING_MAP.get(grading_type)
        if mapped_category:
            return _CATEGORY_GRADERS[mapped_category](test_case, response)

    raise ValueError(f"Unknown category '{category}' or grading type '{grading_type}'")
