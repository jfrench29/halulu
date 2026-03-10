# Halulu — AI Reliability Index

**How reliable is your AI? Not how smart. How honest.**

Halulu is an independent, open-source benchmark that measures AI hallucination rates across production models. It uses adversarial trap questions designed to catch fabrication, not just test knowledge.

**Live dashboard:** [halulu.ai](https://halulu.ai)

---

## Why This Exists

Accuracy benchmarks tell you what a model knows. Halulu tells you whether you can trust what it says when it doesn't know.

Standard benchmarks (MMLU, HumanEval) test knowledge recall. Halulu tests behavioral failure modes: Does the model fabricate citations? Accept false premises? Invent details about things that don't exist? These failures matter more in production than raw accuracy.

## What We Measure

| Metric | Definition |
|--------|-----------|
| **WRS** (Weighted Reliability Score) | 0-100 composite score penalizing hallucinations by severity |
| **TDR** (Trap Detection Rate) | % of false premise + citation trap questions correctly caught |
| **Hallucination Rate** | % of responses containing fabricated content |
| **Severity** (0-5) | How dangerous the hallucination is, by category and subtype |

## Benchmark Categories

61 adversarial questions across 6 categories:

| Category | Questions | What It Tests |
|----------|-----------|---------------|
| Closed Factual | 15 | Factual accuracy on verifiable claims |
| False Premise | 12 | Ability to reject questions built on false assumptions |
| Citation Trap | 9 | Resistance to fabricating details about non-existent sources |
| Document Grounded | 9 | Faithfulness to provided source material |
| Numerical | 9 | Numerical reasoning accuracy |
| Summarization | 7 | Content fidelity in summaries |

## Running the Benchmark

```bash
# Clone and setup
git clone https://github.com/jfrench29/halulu.git
cd halulu/ai_reliability_index
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set API keys for the providers you want to test
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
export MISTRAL_API_KEY="..."
export TOGETHER_API_KEY="..."

# Run evaluation
python -m runner.evaluate_models --models gpt-4o claude-sonnet-4-6 gemini-2.5-pro

# Launch local dashboard
streamlit run dashboard/streamlit_app.py
```

## Project Structure

```
ai_reliability_index/
├── dataset/
│   └── public_tests.json          # 49 public benchmark questions
├── runner/
│   ├── model_adapters.py          # Provider adapters (OpenAI, Anthropic, Google, xAI, Mistral, Together)
│   ├── evaluate_models.py         # Evaluation orchestrator
│   └── cron_evaluate.py           # Weekly automated evaluation
├── grading/
│   ├── grader.py                  # Category-based grading dispatcher
│   ├── graders/                   # 6 category-specific graders
│   ├── normalization.py           # Shared NLP utilities
│   ├── metrics.py                 # WRS, TDR, and metric computation
│   └── schemas.py                 # GradeResult dataclass
├── storage/
│   └── db.py                      # PostgreSQL (prod) / SQLite (dev)
├── dashboard/
│   └── streamlit_app.py           # Streamlit dashboard (halulu.ai)
└── tests/                         # 76 tests covering graders, normalization, metrics
```

## Supported Models

Halulu supports any model accessible through these providers:

| Provider | Example Models | Adapter |
|----------|---------------|---------|
| OpenAI | gpt-4o, gpt-4.1, o3, o4-mini, gpt-5.4 | `openai` |
| Anthropic | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 | `anthropic` |
| Google | gemini-2.5-pro, gemini-2.5-flash | `google` |
| xAI | grok-3, grok-3-mini, grok-4 | `xai` |
| Mistral | mistral-large-latest | `mistral` |
| Together | Llama 3.3 70B, Llama 4 Maverick | `together` |

To request a new model, [open an issue](https://github.com/jfrench29/halulu/issues).

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the full grading rubric, severity scale, and WRS formula derivation.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit questions, request models, and contribute code.

## License

MIT

## Citation

If you use Halulu in research, see [CITATION.cff](CITATION.cff) or cite as:

```
French, J. (2026). Halulu: AI Reliability Index.
https://github.com/jfrench29/halulu
```
