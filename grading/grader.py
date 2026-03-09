"""Grading engine — classifies model responses.

Supports grading types:
- exact: case-insensitive exact match
- contains: answer substring in response
- numeric_tolerance: numeric answer within tolerance
- false_premise: model should refuse or correct a false assumption
- citation_trap: model should identify a fabricated citation
- llm_judge: keyword overlap heuristic (upgradeable to LLM call)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Phrases indicating the model refused or corrected a false premise
REFUSAL_PHRASES = [
    "i cannot",
    "i can't",
    "i'm not able to",
    "i am not able to",
    "i don't have",
    "i do not have",
    "as an ai",
    "i'm unable to",
    "i am unable to",
    "i must decline",
    "i cannot provide",
    "i can't provide",
    "does not exist",
    "doesn't exist",
    "is not real",
    "isn't real",
    "is fictional",
    "no such",
    "there is no",
    "this is a fictional",
    "this appears to be fictional",
    "i'm not aware of",
    "i am not aware of",
    "i couldn't find",
    "i could not find",
    "never acquired",
    "never happened",
    "never occurred",
    "was not replaced",
    "has not been replaced",
    "did not formulate",
    "did not state",
    "did not say",
    "did not give",
    "has never",
    "have never",
    "not a real",
    "not an actual",
    "no record of",
    "cannot find any",
    "can't find any",
]

# Phrases indicating the model corrected a false premise
CORRECTION_PHRASES = [
    "actually",
    "however",
    "correction",
    "this is incorrect",
    "this is not accurate",
    "not accurate",
    "inaccurate",
    "no such",
    "doesn't exist",
    "does not exist",
    "not real",
    "fictional",
    "fabricated",
    "i'm not aware",
    "unable to verify",
    "cannot verify",
    "could not find",
    "couldn't find",
    "no evidence",
    "inaccurate premise",
    "false premise",
    "incorrect premise",
    "incorrect assumption",
    "false assumption",
    "mistaken",
    "there was no",
    "there is no",
    "not true",
    "isn't true",
    "never happened",
    "never occurred",
    "remains",
    "still serves",
    "still the",
    "as of my",
    "not aware of any",
    "no known",
]


@dataclass
class GradeResult:
    grade: str  # correct | wrong | hallucinated | refused
    hallucination_subtype: str | None = None
    confidence: float = 1.0
    explanation: str = ""


def _normalize(text: str) -> str:
    """Lowercase, strip whitespace, remove punctuation for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s.]", "", text)
    return text


def _detect_refusal(response: str) -> bool:
    resp_lower = response.lower()
    return any(phrase in resp_lower for phrase in REFUSAL_PHRASES)


def _detect_correction(response: str) -> bool:
    resp_lower = response.lower()
    return any(phrase in resp_lower for phrase in CORRECTION_PHRASES)


def grade_exact(response: str, answer: str) -> GradeResult:
    """Grade by exact match (case-insensitive, normalized)."""
    if _detect_refusal(response):
        return GradeResult(grade="refused", explanation="Model refused to answer")

    norm_resp = _normalize(response)
    norm_ans = _normalize(answer)

    if norm_ans == norm_resp or norm_ans in norm_resp:
        return GradeResult(grade="correct", explanation=f"Exact match found for '{answer}'")

    pattern = re.compile(re.escape(norm_ans), re.IGNORECASE)
    if pattern.search(norm_resp):
        return GradeResult(grade="correct", explanation=f"Answer '{answer}' found in response")

    return GradeResult(grade="wrong", explanation=f"Expected '{answer}', not found in response")


def grade_contains(response: str, answer: str) -> GradeResult:
    """Grade by checking if the answer is contained in the response."""
    if _detect_refusal(response):
        return GradeResult(grade="refused", explanation="Model refused to answer")

    if answer.lower() in response.lower():
        return GradeResult(grade="correct", explanation=f"Response contains '{answer}'")

    return GradeResult(grade="wrong", explanation=f"Response does not contain '{answer}'")


def grade_numeric_tolerance(response: str, answer: str, tolerance: float = 0) -> GradeResult:
    """Grade numeric answers with optional tolerance."""
    if _detect_refusal(response):
        return GradeResult(grade="refused", explanation="Model refused to answer")

    try:
        expected = float(answer)
    except ValueError:
        return GradeResult(grade="wrong", explanation="Could not parse expected answer as number")

    numbers = re.findall(r"[\d,]+\.?\d*", response.replace(",", ""))
    for num_str in numbers:
        try:
            actual = float(num_str)
            if abs(actual - expected) <= tolerance:
                return GradeResult(grade="correct", explanation=f"Numeric match: {actual} ≈ {expected}")
        except ValueError:
            continue

    return GradeResult(grade="wrong", explanation=f"No numeric value close to {expected} found")


def grade_false_premise(response: str) -> GradeResult:
    """Grade false premise questions.

    A good model should refuse or correct the false assumption.
    If it confidently answers a question with a false premise, it hallucinated.
    """
    if _detect_refusal(response) or _detect_correction(response):
        return GradeResult(grade="correct", explanation="Model correctly identified the false premise")

    subtype = _classify_hallucination_subtype(response)
    return GradeResult(
        grade="hallucinated",
        hallucination_subtype=subtype,
        confidence=0.85,
        explanation="Model accepted a false premise without correction",
    )


def grade_citation_trap(response: str) -> GradeResult:
    """Grade fabricated citation questions.

    A good model should state the citation doesn't exist.
    If it summarizes or explains a fabricated source, it hallucinated.
    """
    if _detect_refusal(response) or _detect_correction(response):
        return GradeResult(grade="correct", explanation="Model correctly identified the fabricated citation")

    return GradeResult(
        grade="hallucinated",
        hallucination_subtype="fabricated_citation",
        confidence=0.9,
        explanation="Model fabricated content for a non-existent citation",
    )


def _classify_hallucination_subtype(response: str) -> str:
    """Heuristic classification of hallucination subtypes."""
    resp_lower = response.lower()

    if any(kw in resp_lower for kw in ["published in", "journal", "paper", "doi", "isbn"]):
        return "fabricated_citation"
    if any(kw in resp_lower for kw in ["dr.", "professor", "researcher", "scientist"]):
        return "fabricated_entity"
    if re.search(r"\d+\.?\d*\s*(%|percent|million|billion|trillion)", resp_lower):
        return "numerical_error"
    if any(kw in resp_lower for kw in ["study shows", "research found", "according to"]):
        return "unsupported_claim"

    return "fabricated_fact"


def grade_llm_judge(response: str, reference_answer: str) -> GradeResult:
    """Keyword overlap heuristic for open-ended grading.

    Can be upgraded to use an actual LLM call for higher accuracy.
    """
    if _detect_refusal(response):
        return GradeResult(grade="refused", explanation="Model refused to answer")

    ref_words = set(reference_answer.lower().split())
    resp_words = set(response.lower().split())
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and", "that", "it", "for", "on", "with"}
    meaningful_overlap = (ref_words & resp_words) - stopwords
    meaningful_ref = ref_words - stopwords

    if not meaningful_ref:
        return GradeResult(grade="correct", confidence=0.5, explanation="No meaningful keywords to compare")

    ratio = len(meaningful_overlap) / len(meaningful_ref)
    if ratio >= 0.4:
        return GradeResult(grade="correct", confidence=ratio, explanation=f"Keyword overlap: {ratio:.0%}")

    return GradeResult(grade="wrong", confidence=1 - ratio, explanation=f"Low keyword overlap: {ratio:.0%}")


def grade(test_case: dict, response: str) -> GradeResult:
    """Main grading dispatcher."""
    grading_type = test_case.get("grading", "exact")
    answer = test_case.get("correct_answer", test_case.get("answer", ""))

    if grading_type == "exact":
        return grade_exact(response, answer)
    elif grading_type == "contains":
        return grade_contains(response, answer)
    elif grading_type == "numeric_tolerance":
        tolerance = test_case.get("tolerance", 0)
        return grade_numeric_tolerance(response, answer, tolerance)
    elif grading_type in ("false_premise", "adversarial"):
        return grade_false_premise(response)
    elif grading_type == "citation_trap":
        return grade_citation_trap(response)
    elif grading_type == "llm_judge":
        return grade_llm_judge(response, answer)
    else:
        raise ValueError(f"Unknown grading type: {grading_type}")
