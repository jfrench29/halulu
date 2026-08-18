# Halulu — AI Reliability Index

> ## ⚠️ Retired — 17 August 2026
>
> **This benchmark no longer runs.** It evaluated AI hallucination rates weekly from
> March to August 2026, then was retired deliberately rather than left to publish
> stale numbers behind a live-looking front page.
>
> **The full dataset is preserved here:** [`data/archive/`](data/archive/) —
> 22,946 graded responses across 25 models, 36 evaluation runs, 6 providers.
> Several of the models measured have since been superseded; the lineup is frozen
> as of August 2026 and will not be updated.
>
> **Findings and final leaderboard:** [halulu.ai](https://halulu.ai)
>
> The code below is left intact and MIT licensed. It is documented in the present
> tense as it was written; read it as a description of how the benchmark *worked*.

---

## Final results (16 August 2026)

| # | Model | WRS | Hallucination | Cost/100q | WRS per $1 |
|---|-------|----:|----:|----:|----:|
| 1 | gemini-2.5-pro | 92.5 | 2.5% | $0.25 | 370 |
| 2 | claude-haiku-4-5 | 91.1 | **1.3%** | $0.05 | 1,822 |
| 3 | grok-4.3 | 90.6 | 3.8% | $0.36 | 252 |
| 4 | claude-opus-4-8 | 90.5 | 3.8% | $1.80 | 50 |
| 5 | deepseek-chat | 86.8 | 5.1% | $0.01 | **8,677** |
| 6 | claude-sonnet-4-6 | 85.1 | 6.3% | $0.36 | 236 |
| 7 | gemini-2.5-flash | 78.4 | 8.9% | $0.02 | 3,921 |
| 8 | mistral-large | 71.6 | 11.4% | $0.16 | 448 |
| 9 | gpt-5.1 | 71.4 | 12.7% | $1.50 | 48 |
| 10 | gpt-4.1-mini | 61.1 | 16.5% | $0.03 | 2,036 |

**Headline: price does not predict honesty.** The cheapest Anthropic model had the
lowest fabrication rate of anything tested (1.3%) and outranked a model costing 36×
more. The two most expensive models had the two worst reliability-per-dollar ratios.
This held across eleven consecutive weekly runs.

**Known limitation:** `deepseek-chat` is a provider alias that resolved to different
underlying models over the project's life (it served `deepseek-v4-flash` by the final
run). Aliases should have been pinned to explicit versions. Treat that series as
indicative, not like-for-like.

---


**How reliable is your AI? Not how smart. How honest.**

Halulu is an independent, open-source benchmark that measures AI hallucination rates across production models. It uses adversarial trap questions designed to catch fabrication, not just test knowledge.

**Archived results:** [halulu.ai](https://halulu.ai) · **Dataset:** [`data/archive/`](data/archive/)

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

79 adversarial questions across 6 categories:

| Category | Questions | What It Tests |
|----------|-----------|---------------|
| Closed Factual | 16 | Factual accuracy on verifiable claims |
| False Premise | 20 | Ability to reject questions built on false assumptions |
| Citation Trap | 16 | Resistance to fabricating details about non-existent sources |
| Document Grounded | 11 | Faithfulness to provided source material |
| Numerical | 10 | Numerical reasoning accuracy |
| Summarization | 6 | Content fidelity in summaries |

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
| OpenAI | gpt-5.1, gpt-4.1-mini | `openai` |
| Anthropic | claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5 | `anthropic` |
| Google | gemini-2.5-pro, gemini-2.5-flash | `google` |
| xAI | grok-4.3 | `xai` |
| Mistral | mistral-large-latest | `mistral` |
| DeepSeek | deepseek-chat (V4) | `deepseek` |

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
