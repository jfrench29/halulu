"""Validate that every benchmark model ID actually exists on its provider.

A hallucination benchmark must not itself ship hallucinated model IDs. This
script makes a tiny live call to each model in the active lineup and reports
whether the provider recognizes it. Run before every eval and in CI.

Usage:
    python -m scripts.validate_models          # validate the cron lineup
    python -m scripts.validate_models --quiet  # only print failures + exit code

Exit code 0 if all models resolve, 1 if any are missing/unreachable.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from runner.cron_evaluate import MODELS
from runner.model_adapters import get_adapter, resolve_provider

# Substrings that indicate the model ID itself is not recognized (a phantom),
# as opposed to a transient error (rate limit, network, billing).
_NOT_FOUND_MARKERS = (
    "model_not_found",
    "does not exist",
    "not found",
    "unknown model",
    "is not a valid model",
    "no such model",
    "could not be found",
    "invalid model",
)


def classify(model: str) -> tuple[str, str]:
    """Return (status, detail). status in {OK, PHANTOM, ERROR, SKIP}."""
    provider = resolve_provider(model)
    if provider is None:
        return "ERROR", "no provider mapping"
    try:
        adapter = get_adapter(provider, model=model)
    except ValueError as e:
        # Missing API key — can't validate here (e.g. running without that key set)
        return "SKIP", str(e)
    try:
        resp = adapter.call("Reply with the single word: ok")
    except Exception as e:  # noqa: BLE001 — we classify the message
        msg = str(e).lower()
        if any(m in msg for m in _NOT_FOUND_MARKERS):
            return "PHANTOM", str(e)[:160]
        return "ERROR", str(e)[:160]
    if getattr(resp, "error", False):
        return "ERROR", "adapter returned error flag"
    return "OK", f"{resp.latency_ms:.0f}ms"


def main() -> None:
    quiet = "--quiet" in sys.argv
    failures = 0
    if not quiet:
        print(f"Validating {len(MODELS)} models\n{'-' * 60}")
    for model in MODELS:
        status, detail = classify(model)
        if status in ("PHANTOM", "ERROR"):
            failures += 1
            print(f"  [{status}] {model}  ::  {detail}")
        elif not quiet:
            print(f"  [{status}] {model}  {detail if status == 'OK' else ''}")
    if failures:
        print(f"\n{failures} model(s) failed validation.")
        sys.exit(1)
    if not quiet:
        print("\nAll models validated.")
    sys.exit(0)


if __name__ == "__main__":
    main()
