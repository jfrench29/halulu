"""Metrics engine — accuracy, hallucination rate, TDR, WRS, and per-category breakdowns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


# Categories that are "traps" — model should refuse or correct, not answer
_TRAP_CATEGORIES = {"false_premise", "citation_trap"}


@dataclass
class ModelMetrics:
    model: str
    total: int
    correct: int
    incorrect: int
    hallucinated: int
    refused: int
    uncertain: int
    accuracy_rate: float
    hallucination_rate: float
    refusal_rate: float
    uncertain_rate: float
    avg_latency_ms: float
    hallucination_subtypes: dict[str, int]
    category_breakdown: dict[str, dict[str, float]]
    # New metrics
    trap_detection_rate: float  # TDR: % of trap questions correctly identified
    avg_severity: float         # Average severity of hallucinations (0-5)
    wrs: float                  # Weighted Reliability Score


def compute_metrics(
    model: str,
    results: list[dict],
) -> ModelMetrics:
    """Compute metrics from a list of evaluation results."""
    total = len(results)
    if total == 0:
        return ModelMetrics(
            model=model, total=0, correct=0, incorrect=0, hallucinated=0,
            refused=0, uncertain=0,
            accuracy_rate=0.0, hallucination_rate=0.0, refusal_rate=0.0,
            uncertain_rate=0.0, avg_latency_ms=0.0,
            hallucination_subtypes={}, category_breakdown={},
            trap_detection_rate=0.0, avg_severity=0.0, wrs=0.0,
        )

    grade_counts = Counter(r["grade"] for r in results)
    correct = grade_counts.get("correct", 0)
    incorrect = grade_counts.get("incorrect", 0) + grade_counts.get("wrong", 0)
    hallucinated = grade_counts.get("hallucinated", 0)
    refused = grade_counts.get("refused", 0)
    uncertain = grade_counts.get("uncertain", 0)

    accuracy_rate = correct / total
    hallucination_rate = hallucinated / total
    refusal_rate = refused / total
    uncertain_rate = uncertain / total

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    subtype_counts = Counter(
        r["hallucination_subtype"]
        for r in results
        if r.get("hallucination_subtype")
    )

    category_breakdown = _compute_category_breakdown(results)

    # TDR: Trap Detection Rate — % of false_premise + citation_trap correctly handled
    trap_results = [r for r in results if r.get("category") in _TRAP_CATEGORIES]
    trap_correct = sum(1 for r in trap_results if r["grade"] == "correct")
    trap_detection_rate = trap_correct / len(trap_results) if trap_results else 0.0

    # Average severity of hallucinations
    severities = [r.get("severity", 0) for r in results if r["grade"] == "hallucinated"]
    avg_severity = sum(severities) / len(severities) if severities else 0.0

    # WRS: Weighted Reliability Score
    wrs = compute_wrs(accuracy_rate, hallucination_rate, refusal_rate, avg_severity)

    return ModelMetrics(
        model=model,
        total=total,
        correct=correct,
        incorrect=incorrect,
        hallucinated=hallucinated,
        refused=refused,
        uncertain=uncertain,
        accuracy_rate=accuracy_rate,
        hallucination_rate=hallucination_rate,
        refusal_rate=refusal_rate,
        uncertain_rate=uncertain_rate,
        avg_latency_ms=avg_latency,
        hallucination_subtypes=dict(subtype_counts),
        category_breakdown=category_breakdown,
        trap_detection_rate=trap_detection_rate,
        avg_severity=avg_severity,
        wrs=wrs,
    )


def _compute_category_breakdown(results: list[dict]) -> dict[str, dict[str, float]]:
    """Break down metrics by question category."""
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        cat = r.get("category", "unknown")
        by_cat.setdefault(cat, []).append(r)

    breakdown = {}
    for cat, cat_results in by_cat.items():
        n = len(cat_results)
        grades = Counter(r["grade"] for r in cat_results)
        breakdown[cat] = {
            "total": n,
            "accuracy_rate": grades.get("correct", 0) / n,
            "hallucination_rate": grades.get("hallucinated", 0) / n,
            "refusal_rate": grades.get("refused", 0) / n,
            "uncertain_rate": grades.get("uncertain", 0) / n,
        }
    return breakdown


def compute_wrs(
    accuracy_rate: float,
    hallucination_rate: float,
    refusal_rate: float,
    avg_severity: float,
) -> float:
    """Weighted Reliability Score (0-100).

    WRS = accuracy * 100 - hallucination_rate * severity_weight - refusal_rate * 25

    The severity_weight scales the hallucination penalty from ×50 (severity 1)
    to ×100 (severity 5). This replaces the old flat ×200 penalty.
    A model with minor hallucinations (severity 1) is penalized much less than
    one with egregious fabrications (severity 5).
    """
    if avg_severity > 0:
        severity_weight = 50 + (avg_severity / 5) * 50  # 50-100 range
    else:
        severity_weight = 100  # default penalty if no hallucinations (doesn't matter, rate=0)

    score = accuracy_rate * 100 - hallucination_rate * severity_weight - refusal_rate * 25
    return max(0.0, min(100.0, score))


