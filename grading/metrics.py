"""Metrics engine — calculates accuracy, hallucination rate, and refusal rate."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class ModelMetrics:
    model: str
    total: int
    correct: int
    incorrect: int
    hallucinated: int
    refused: int
    accuracy_rate: float
    hallucination_rate: float
    refusal_rate: float
    avg_latency_ms: float
    hallucination_subtypes: dict[str, int]
    category_breakdown: dict[str, dict[str, float]]


def compute_metrics(
    model: str,
    results: list[dict],
) -> ModelMetrics:
    """Compute metrics from a list of evaluation results.

    Each result dict should have keys: grade, hallucination_subtype, latency_ms, category.
    """
    total = len(results)
    if total == 0:
        return ModelMetrics(
            model=model,
            total=0,
            correct=0,
            incorrect=0,
            hallucinated=0,
            refused=0,
            accuracy_rate=0.0,
            hallucination_rate=0.0,
            refusal_rate=0.0,
            avg_latency_ms=0.0,
            hallucination_subtypes={},
            category_breakdown={},
        )

    grade_counts = Counter(r["grade"] for r in results)
    correct = grade_counts.get("correct", 0)
    incorrect = grade_counts.get("incorrect", 0) + grade_counts.get("wrong", 0)
    hallucinated = grade_counts.get("hallucinated", 0)
    refused = grade_counts.get("refused", 0)

    accuracy_rate = correct / total
    hallucination_rate = hallucinated / total
    refusal_rate = refused / total

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    subtype_counts = Counter(
        r["hallucination_subtype"]
        for r in results
        if r.get("hallucination_subtype")
    )

    category_breakdown = _compute_category_breakdown(results)

    return ModelMetrics(
        model=model,
        total=total,
        correct=correct,
        incorrect=incorrect,
        hallucinated=hallucinated,
        refused=refused,
        accuracy_rate=accuracy_rate,
        hallucination_rate=hallucination_rate,
        refusal_rate=refusal_rate,
        avg_latency_ms=avg_latency,
        hallucination_subtypes=dict(subtype_counts),
        category_breakdown=category_breakdown,
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
        }
    return breakdown


def compute_reliability_score(metrics: ModelMetrics) -> float:
    """Compute a single reliability score (0-100).

    Formula: accuracy * 100 - hallucination_rate * 200 - refusal_rate * 50
    Clamped to [0, 100].
    """
    score = metrics.accuracy_rate * 100 - metrics.hallucination_rate * 200 - metrics.refusal_rate * 50
    return max(0.0, min(100.0, score))
