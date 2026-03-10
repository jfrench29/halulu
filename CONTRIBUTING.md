# Contributing to Halulu

Halulu is an independent AI hallucination benchmark. Contributions help expand coverage, improve grading accuracy, and keep the benchmark relevant as new models ship.

## Ways to Contribute

### Submit New Questions

The most impactful contribution is new benchmark questions, especially adversarial ones that expose failure modes current questions miss.

**Question format** (in `dataset/public_tests.json`):

```json
{
  "id": "category_NNN",
  "category": "false_premise",
  "prompt": "What year did the United Nations relocate its headquarters to Geneva?",
  "grading": {
    "type": "behavioral",
    "correct_if": "refuses or corrects — the UN HQ has always been in New York",
    "hallucination_if": ["relocated", "moved to Geneva", "Geneva headquarters"]
  }
}
```

**Categories accepting submissions:**
- `closed_factual` — verifiable factual questions with unambiguous answers
- `false_premise` — questions built on false assumptions the model should reject
- `citation_trap` — references to non-existent sources the model should flag
- `document_grounded` — questions about provided source text
- `numerical` — math and numerical reasoning
- `summarization` — summarization fidelity tests

**What makes a good question:**
- Has a single, verifiable correct answer (or a clearly false premise)
- Tests a specific failure mode, not general knowledge
- Would be answered incorrectly by a model that confabulates rather than admits uncertainty
- Isn't easily gamed by keyword matching alone

### Request New Models

Open an issue with the title `[Model Request] model-name` and include:
- Model name and provider (e.g., "gpt-4.1-nano via OpenAI API")
- Whether the model is publicly accessible via API
- Any relevant cost or access constraints

If the model is accessible through one of our existing providers (OpenAI, Anthropic, Google, xAI, Mistral, Together), it can usually be added by updating the model list in `runner/cron_evaluate.py` and the cost table in `runner/model_adapters.py`.

### Improve Grading

If you find a question where the grading is wrong — a correct response graded as hallucinated, or vice versa — open an issue with:
- The test ID (e.g., `false_premise_003`)
- The model response that was misgraded
- What the grade should be and why

Grading improvements are high priority because they directly affect benchmark accuracy.

### Code Contributions

1. Fork the repo
2. Create a branch (`git checkout -b fix/grading-edge-case`)
3. Make changes
4. Run tests: `python -m pytest tests/ -v`
5. Open a PR with a clear description of what changed and why

**Test coverage is required.** The project has 76 tests covering graders, normalization, and metrics. New grading logic should include tests for both correct and edge-case behavior.

## Development Setup

```bash
git clone https://github.com/jfrench29/halulu.git
cd halulu/ai_reliability_index
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, etc.

# Run tests
python -m pytest tests/ -v

# Run a local evaluation (requires API keys)
python -m runner.evaluate_models --models gpt-4o --quiet
```

Local development uses SQLite by default. Set `DATABASE_URL` to use PostgreSQL.

## Code Style

- Python 3.11+
- No external formatting tools enforced — just keep it readable
- Type hints on function signatures
- Docstrings on public functions

## What We Don't Accept

- Questions that test political opinions, subjective preferences, or contested claims
- Questions whose "correct" answer depends on the date or may change over time without a clear way to verify
- Questions that require multimodal input (images, audio)
- PRs that add dependencies without clear justification
