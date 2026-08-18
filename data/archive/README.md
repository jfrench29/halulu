# Halulu benchmark dataset — final archive

Complete export of the Halulu production database, taken at retirement on
**17 August 2026**. This is the full record of every evaluation the benchmark
ever ran.

These measurements are not reproducible. Several of the models here have already
been superseded or withdrawn by their providers, and a model ID does not
guarantee identical weights over time. This export is the only remaining record.

## Coverage

| | |
|---|---|
| First run | 2026-03-10 |
| Last run | 2026-08-16 |
| Evaluation runs | 36 |
| Graded responses | 22,946 |
| Distinct models | 25 |
| Providers | 6 (OpenAI, Anthropic, Google, xAI, Mistral, DeepSeek) |

Weekly automated runs cover 2026-06-07 → 2026-08-16 (11 consecutive Sundays,
10 models × 79 questions). Earlier runs are ad-hoc and cover a changing lineup
of up to 25 models — column meanings are stable, but the model set is not.
Use `eval_runs.csv` to see exactly which models were in each run.

## Files

| File | Rows | Contents |
|---|---:|---|
| `eval_results.csv.gz` | 22,946 | Every graded response. One row per model × question × run. |
| `eval_runs.csv` | 36 | Run manifest: `run_id`, timestamp, dataset path, model list. |
| `weekly_summary.csv` | 342 | Derived per-model-per-run grade counts, hallucination and accuracy rates. Start here. |
| `hall_of_fame.csv` | 50 | Notable individual hallucinations flagged during grading. |
| `MANIFEST.json` | — | Row counts, column lists and SHA-256 checksums for each file. |

`eval_results.csv.gz` is gzipped (9 MB compressed, 27 MB raw). Read it directly:

```python
import gzip, csv, sys
csv.field_size_limit(sys.maxsize)   # some responses exceed the default limit
with gzip.open("eval_results.csv.gz", "rt") as f:
    for row in csv.DictReader(f):
        ...
```

## Columns in `eval_results.csv.gz`

| Column | Meaning |
|---|---|
| `id` | Row primary key |
| `run_id` | Joins to `eval_runs.run_id` |
| `model` | Model ID **as requested from the provider** (see the alias caveat below) |
| `test_id` | Stable question identifier |
| `category` | One of: closed factual, false premise, citation trap, document grounded, summarization, numerical |
| `prompt` | Question text sent to the model |
| `response` | Raw model output, untruncated (longest is 11,409 characters) |
| `grade` | `correct`, `incorrect`, `hallucinated`, `uncertain`, or `refused` |
| `hallucination_subtype` | `fabricated_citation`, `fabricated_fact`, `fabricated_entity`, `numerical_error`, or empty |
| `confidence` | Grader confidence |
| `explanation` | Grader rationale |
| `latency_ms` | Response latency |
| `severity` | 0–5; 5 = fabricated citation |
| `timestamp` | Response time (UTC, ISO 8601) |

Grade distribution across the full archive: 20,277 correct · 1,548 hallucinated ·
1,014 incorrect · 80 refused · 27 uncertain. 289 rows have an empty `response`,
from provider failures in early ad-hoc runs.

## Caveats

- **`model` records what was requested, not what was served.** The benchmark did
  not log the provider's returned model identifier. `deepseek-chat` and
  `mistral-large-latest` are moving aliases: by the final run, `deepseek-chat`
  resolved to `deepseek-v4-flash`. Any series using an alias may span more than
  one underlying model. This was the project's main methodological flaw — pin
  explicit versioned IDs if you build on this.
- **Costs are provider list prices** at time of run, not measured spend, and are
  not in this export. See the dashboard figures in the root `README.md`.
- **91 questions total** (79 public + 12 held back). Only the 79 public questions
  appear here. Differences of a point or two in derived scores are noise.
- **One answer per model per question per run.** No repeat sampling, default
  provider settings throughout.

## Licence

Released as-is under the repository's MIT licence. Attribution welcome, not required.
