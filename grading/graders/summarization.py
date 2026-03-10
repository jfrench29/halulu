"""Grader for summarization questions.

Grades whether the summary stays faithful to the source material.
Uses keyword overlap heuristic (upgradeable to LLM judge).
"""

from __future__ import annotations

from grading.normalization import detect_refusal
from grading.schemas import GradeResult

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "to",
    "and", "that", "it", "for", "on", "with", "by", "as", "its", "from",
}


def grade_summarization(test_case: dict, response: str) -> GradeResult:
    if detect_refusal(response):
        return GradeResult(result="refused", reason="Model refused to answer")

    reference = test_case.get("correct_answer", "")
    reference_facts = test_case.get("reference_facts", [])
    ref_text = " ".join(reference_facts) if reference_facts else reference

    ref_words = set(ref_text.lower().split()) - _STOPWORDS
    resp_words = set(response.lower().split()) - _STOPWORDS

    if not ref_words:
        return GradeResult(
            result="correct",
            confidence=0.5,
            reason="No meaningful keywords to compare",
            details={"matched_behavior": "faithful_summary", "keyword_overlap": 0.0},
        )

    overlap = ref_words & resp_words
    ratio = len(overlap) / len(ref_words)

    if ratio >= 0.4:
        return GradeResult(
            result="correct",
            confidence=ratio,
            reason=f"Keyword overlap: {ratio:.0%}",
            details={"matched_behavior": "faithful_summary", "keyword_overlap": ratio},
        )

    return GradeResult(
        result="incorrect",
        confidence=1 - ratio,
        reason=f"Low keyword overlap: {ratio:.0%}",
        details={"keyword_overlap": ratio},
    )
