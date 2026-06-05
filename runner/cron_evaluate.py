"""Weekly cron evaluation — runs all benchmark models and exits.

Designed for Railway's native cron scheduler. The process must terminate
cleanly after completion; Railway skips the next scheduled run if the
previous one is still alive.

Usage:
    python -m runner.cron_evaluate          # run all models
    python -m runner.cron_evaluate --dry    # print model list and exit
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from runner.evaluate_models import run_evaluation
from storage.db import ResultsDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Models to evaluate each week ─────────────────────────────────────
# Update this list when adding or removing models from the benchmark.

MODELS = [
    # OpenAI
    "gpt-5.1",                       # flagship reasoning
    "gpt-4.1-mini",                  # best-value standard
    # Anthropic
    "claude-opus-4-8",              # flagship
    "claude-sonnet-4-6",            # mid-tier
    "claude-haiku-4-5-20251001",    # best-value
    # Google
    "gemini-2.5-pro",               # flagship
    "gemini-2.5-flash",             # best-value
    # xAI
    "grok-4.3",                     # flagship
    # Mistral
    "mistral-large-latest",
    # DeepSeek (open-weight value)
    "deepseek-chat",                # DeepSeek V4
]

DATASET = PROJECT_ROOT / "dataset" / "public_tests.json"


def main() -> None:
    if "--dry" in sys.argv:
        print(f"Cron evaluate: {len(MODELS)} models, dataset: {DATASET}")
        for m in MODELS:
            print(f"  - {m}")
        sys.exit(0)

    logger.info("Cron evaluation starting: %d models, %s", len(MODELS), DATASET)

    db = ResultsDB()
    try:
        run_evaluation(models=MODELS, dataset_path=DATASET, db=db, verbose=False)
        logger.info("Cron evaluation complete.")
    except Exception:
        logger.exception("Cron evaluation failed.")
        sys.exit(1)
    finally:
        db.close()

    sys.exit(0)


if __name__ == "__main__":
    main()
