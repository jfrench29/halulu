#!/bin/bash
set -euo pipefail

# ============================================================
# Halulu — Run First Evaluation
# Run this after deploy.sh has completed successfully
# ============================================================

cd "$(dirname "$0")/.."
echo "==> Loading Railway environment variables..."
eval $(railway variables --format shell)

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set. Is PostgreSQL linked in Railway?"
    exit 1
fi

echo "==> DATABASE_URL is set"

# Build the model list based on which API keys are available
MODELS=""
if [ -n "${OPENAI_API_KEY:-}" ]; then
    MODELS="$MODELS gpt-4o"
    echo "    OpenAI API key found → will test gpt-4o"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    MODELS="$MODELS claude-sonnet-4-20250514"
    echo "    Anthropic API key found → will test claude-sonnet-4-20250514"
fi
if [ -n "${GOOGLE_API_KEY:-}" ]; then
    MODELS="$MODELS gemini-2.0-flash"
    echo "    Google API key found → will test gemini-2.0-flash"
fi

if [ -z "$MODELS" ]; then
    echo "ERROR: No API keys found. Set at least one in Railway."
    exit 1
fi

echo ""
echo "==> Running evaluation against public test set..."
echo "    Models:$MODELS"
echo ""

python -m runner.evaluate_models --models $MODELS

echo ""
echo "============================================================"
echo "  EVALUATION COMPLETE"
echo "============================================================"
echo ""
echo "  Refresh your Halulu dashboard to see the leaderboard."
echo ""
echo "  To run against the hidden test set:"
echo "    python -m runner.evaluate_models --models$MODELS --dataset dataset/hidden_tests.json"
echo ""
