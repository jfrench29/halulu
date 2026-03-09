"""Evaluation runner — orchestrates benchmark execution across models."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grading.grader import grade
from grading.metrics import compute_metrics, compute_reliability_score
from runner.model_adapters import call_model
from storage.db import ResultsDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_dataset(path: str | Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def run_evaluation(
    models: list[str],
    dataset_path: str | Path,
    db: ResultsDB | None = None,
    verbose: bool = True,
) -> dict[str, list[dict]]:
    """Run evaluation for given models on a dataset."""
    dataset = load_dataset(dataset_path)
    run_id = str(uuid.uuid4())  # full UUID — no truncation

    if db is None:
        db = ResultsDB()

    db.save_run(run_id, str(dataset_path), models)
    all_results: dict[str, list[dict]] = {}
    adapter_cache: dict = {}  # reuse HTTP clients across calls

    for model_name in models:
        if verbose:
            print(f"\n{'='*60}")
            print(f"Evaluating: {model_name}")
            print(f"{'='*60}")

        model_results = []
        errors = 0

        for i, test in enumerate(dataset):
            test_id = test["id"]
            prompt = test["prompt"]
            category = test.get("category", "unknown")

            if verbose:
                print(f"  [{i+1}/{len(dataset)}] Test {test_id} ({category}): ", end="", flush=True)

            resp = call_model(model_name, prompt, _adapter_cache=adapter_cache)

            if resp.error:
                errors += 1
                if verbose:
                    print("ERROR (skipped)")
                # Do NOT grade errors — they are not real model responses
                continue

            grade_result = grade(test, resp.text)

            result = {
                "run_id": run_id,
                "model": model_name,
                "test_id": test_id,
                "category": category,
                "prompt": prompt,
                "response": resp.text,
                "grade": grade_result.grade,
                "hallucination_subtype": grade_result.hallucination_subtype,
                "confidence": grade_result.confidence,
                "explanation": grade_result.explanation,
                "latency_ms": resp.latency_ms,
            }
            model_results.append(result)

            if verbose:
                icon = {"correct": "\u2713", "wrong": "\u2717", "hallucinated": "\u26a0", "refused": "\u2298"}.get(grade_result.grade, "?")
                print(f"{icon} {grade_result.grade.upper()} ({resp.latency_ms:.0f}ms)")

        # Batch write all results for this model in one transaction
        db.save_results_batch(model_results)

        # Add hallucinations to Hall of Fame
        for r in model_results:
            if r["grade"] == "hallucinated":
                db.add_to_hall_of_fame(
                    model=model_name,
                    test_id=r["test_id"],
                    prompt=r["prompt"],
                    response=r["response"],
                    hallucination_subtype=r.get("hallucination_subtype"),
                )

        all_results[model_name] = model_results

        if verbose:
            metrics = compute_metrics(model_name, model_results)
            score = compute_reliability_score(metrics)
            print(f"\n  --- {model_name} Summary ---")
            print(f"  Accuracy:          {metrics.accuracy_rate:.1%}")
            print(f"  Hallucination:     {metrics.hallucination_rate:.1%}")
            print(f"  Refusal:           {metrics.refusal_rate:.1%}")
            print(f"  Avg Latency:       {metrics.avg_latency_ms:.0f}ms")
            print(f"  Reliability Score: {score:.1f}/100")
            if errors:
                print(f"  Errors (skipped):  {errors}")
            if metrics.hallucination_subtypes:
                print(f"  Hallucination types: {metrics.hallucination_subtypes}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="AI Reliability Index \u2014 Evaluation Runner")
    parser.add_argument(
        "--models", nargs="+", required=True,
        help="Model names (e.g., gpt-4o claude-sonnet-4-20250514 gemini-2.0-flash)",
    )
    parser.add_argument(
        "--dataset", default=str(PROJECT_ROOT / "dataset" / "public_tests.json"),
        help="Path to dataset JSON file",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    db = ResultsDB()
    try:
        run_evaluation(models=args.models, dataset_path=args.dataset, db=db, verbose=not args.quiet)
    finally:
        db.close()


if __name__ == "__main__":
    main()
