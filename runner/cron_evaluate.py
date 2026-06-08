"""Daily cron evaluation — runs all benchmark models and exits.

Designed for Railway's native cron scheduler (schedule: ``0 6 * * *``,
06:00 UTC daily). The process must terminate cleanly after completion;
Railway skips the next scheduled run if the previous one is still alive.

A preflight check validates the environment (database + API keys) before
any work starts, so a misconfigured deploy fails loudly and early instead
of silently producing no — or partial — results.

Usage:
    python -m runner.cron_evaluate                 # run all models
    python -m runner.cron_evaluate --dry           # print model list and exit
    python -m runner.cron_evaluate --allow-sqlite  # permit SQLite fallback (local testing)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from runner.evaluate_models import run_evaluation
from runner.model_adapters import required_env_vars
from storage.db import ResultsDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Models to evaluate each day ──────────────────────────────────────
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


def preflight(models: list[str], allow_sqlite: bool = False) -> list[str]:
    """Return a list of fatal misconfiguration problems (empty == all good).

    Catches the silent-failure modes that otherwise leave the dashboard
    stale with no obvious cause: a missing database (writes vanish into an
    ephemeral SQLite file the web service never reads) and missing API keys
    (that provider's models all error out, yielding a half-empty leaderboard).
    """
    problems: list[str] = []

    if not os.environ.get("DATABASE_URL"):
        if allow_sqlite:
            logger.warning(
                "DATABASE_URL not set — using local SQLite fallback. "
                "Results will NOT reach the cloud dashboard."
            )
        else:
            problems.append(
                "DATABASE_URL is not set. In the cloud this means results are "
                "written to an ephemeral SQLite file the dashboard never reads. "
                "Set DATABASE_URL, or pass --allow-sqlite for local testing."
            )

    for var, dependents in sorted(required_env_vars(models).items()):
        if var == "<no provider mapping>":
            problems.append(
                f"No provider mapping for model(s): {', '.join(dependents)}. "
                "Check the model ID or runner/model_adapters.py:_PROVIDER_MAP."
            )
        elif not os.environ.get(var):
            problems.append(
                f"{var} is not set — required by: {', '.join(dependents)}."
            )

    return problems


def main() -> None:
    if "--dry" in sys.argv:
        print(f"Cron evaluate: {len(MODELS)} models, dataset: {DATASET}")
        for m in MODELS:
            print(f"  - {m}")
        sys.exit(0)

    allow_sqlite = "--allow-sqlite" in sys.argv

    problems = preflight(MODELS, allow_sqlite=allow_sqlite)
    if problems:
        logger.error("Preflight failed — aborting before any model calls:")
        for p in problems:
            logger.error("  - %s", p)
        sys.exit(2)

    logger.info("Preflight OK. Cron evaluation starting: %d models, %s", len(MODELS), DATASET)

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
