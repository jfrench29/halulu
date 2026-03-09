# AI Reliability Index

Measure hallucination rates of popular AI models and publish a public leaderboard.

## Setup

```bash
cd ai_reliability_index
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure API Keys

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

## Run Evaluation

```bash
# Evaluate one or more models against the public test set
python -m runner.evaluate_models --models gpt-4o claude-sonnet-4-20250514

# Use the hidden test set
python -m runner.evaluate_models --models gpt-4o --dataset dataset/hidden_tests.json

# Quiet mode
python -m runner.evaluate_models --models gpt-4o --quiet
```

## Launch Dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

## Project Structure

```
ai_reliability_index/
├── dataset/
│   ├── public_tests.json     # 30 visible benchmark questions
│   └── hidden_tests.json     # 10 hidden scoring questions
├── runner/
│   ├── model_adapters.py     # Unified model calling interface
│   └── evaluate_models.py    # Evaluation orchestrator
├── grading/
│   ├── grader.py             # Response classification engine
│   └── metrics.py            # Accuracy/hallucination/refusal metrics
├── storage/
│   └── db.py                 # SQLite persistence layer
├── dashboard/
│   └── streamlit_app.py      # Leaderboard & trend charts
├── requirements.txt
└── README.md
```

## Benchmark Layers

| Layer | Purpose | Count |
|-------|---------|-------|
| Public | Transparency & reproducibility | 30 questions |
| Hidden | Leaderboard scoring | 10 questions |
| Weekly (planned) | Prevent overfitting | 10-20/week |
| Community (planned) | Adversarial prompts | User-submitted |

## Grading Taxonomy

Responses are classified as: **correct**, **wrong**, **hallucinated**, or **refused**.

Hallucination subtypes:
- `fabricated_fact` — invented factual claims
- `fabricated_entity` — invented people, organizations, places
- `fabricated_citation` — invented papers, books, URLs
- `unsupported_claim` — claims without basis
- `numerical_error` — wrong numbers stated with confidence
