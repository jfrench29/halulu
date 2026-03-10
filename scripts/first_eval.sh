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
    MODELS="$MODELS claude-sonnet-4-6"
    echo "    Anthropic API key found → will test claude-sonnet-4-6"
fi
if [ -n "${GOOGLE_API_KEY:-}" ]; then
    MODELS="$MODELS gemini-2.5-flash"
    echo "    Google API key found → will test gemini-2.5-flash"
fi
if [ -n "${XAI_API_KEY:-}" ]; then
    MODELS="$MODELS grok-3-mini"
    echo "    xAI API key found → will test grok-3-mini"
fi
if [ -n "${MISTRAL_API_KEY:-}" ]; then
    MODELS="$MODELS mistral-large-latest"
    echo "    Mistral API key found → will test mistral-large-latest"
fi
if [ -n "${TOGETHER_API_KEY:-}" ]; then
    MODELS="$MODELS meta-llama/Llama-3.3-70B-Instruct-Turbo"
    echo "    Together API key found → will test meta-llama/Llama-3.3-70B-Instruct-Turbo"
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
echo "    python -m runner.evaluate_models --models $MODELS --dataset dataset/hidden_tests.json"
echo ""
