# Methodology

This document describes the grading rubric, metric definitions, and scoring formulas used by the Halulu AI Reliability Index.

## Grading Architecture

Each model response is graded by a **category-specific grader** selected by the question type. There is no single grading function — each category has its own behavioral logic.

### Response Classifications

Every response receives one of five grades:

| Grade | Meaning |
|-------|---------|
| **correct** | Factually accurate, or correctly identified a trap |
| **incorrect** | Wrong answer, but no fabrication |
| **hallucinated** | Contains fabricated content stated with confidence |
| **refused** | Model declined to answer |
| **uncertain** | Vague or hedging response without committing either way |

### Hallucination Subtypes

When a response is graded `hallucinated`, it is further classified:

| Subtype | Description | Example |
|---------|-------------|---------|
| `fabricated_fact` | Invented factual claims | Stating a false historical date as fact |
| `fabricated_entity` | Invented people, organizations, places | Describing a non-existent company |
| `fabricated_citation` | Invented papers, books, URLs | Citing a paper that doesn't exist |
| `unsupported_claim` | Claims without basis in the provided context | Adding facts not in the source document |
| `numerical_error` | Wrong numbers stated with confidence | Calculating 15% of 200 as 45 |

## Benchmark Categories

### Closed Factual (15 questions)

Tests factual accuracy on verifiable claims. The grader normalizes both the expected answer and the model response, then checks whether the expected fact appears in the response. Short facts (under 5 characters) use word-boundary matching to avoid substring false positives.

### False Premise (12 questions)

Questions built on false assumptions (e.g., "What year did [fictional event] happen?"). A **correct** response refuses to answer or corrects the premise. A **hallucinated** response accepts the false premise and fabricates details. The grader checks for refusal patterns, correction language, and hallucination trigger patterns defined per question.

### Citation Trap (9 questions)

References non-existent sources and asks the model to discuss them. A **correct** response identifies that the source doesn't exist. A **hallucinated** response fabricates details about the non-existent source. This is the highest-severity category — fabricating citations that look real erodes trust in verifiable claims.

### Document Grounded (9 questions)

Provides source text and asks questions about it. The grader checks whether the model's response is faithful to the provided document. Claims not supported by the source text are graded as hallucinated with subtype `unsupported_claim`.

### Numerical (9 questions)

Tests numerical reasoning with defined tolerance ranges. Responses are parsed for numeric values and compared against expected answers within a configurable tolerance (default: 1% relative or exact match). Values outside tolerance are graded as hallucinated with subtype `numerical_error`.

### Summarization (7 questions)

Provides text and asks for a summary. The grader uses keyword overlap to measure whether the summary captures key content from the source. Summaries that fall below a 40% keyword overlap threshold are flagged. This is the category most likely to benefit from future LLM-judge grading.

## Severity Scale (0-5)

Hallucination severity is assigned based on both the subtype and the question category. Higher severity means the fabrication is more dangerous in production use.

| Severity | Assignment |
|----------|-----------|
| **5** | Citation trap + fabricated citation (invented a full citation for a non-existent source) |
| **4** | Citation trap + other subtypes, or false premise + fabricated entity |
| **3** | False premise (accepted), document grounded (unsupported claim), fabricated fact |
| **2** | Numerical error, summarization distortion |
| **0** | Not a hallucination |

## Key Metrics

### WRS — Weighted Reliability Score (0-100)

The primary ranking metric. WRS rewards accuracy and penalizes hallucinations proportionally to their severity, with a smaller penalty for refusals (which are safer than hallucinations).

```
WRS = accuracy_rate * 100 - hallucination_rate * severity_weight - refusal_rate * 25
```

Where `severity_weight` scales from 50 (severity 1) to 100 (severity 5):

```
severity_weight = 50 + (avg_severity / 5) * 50
```

This means:
- A model with minor hallucinations (avg severity 1) loses 50 points per 100% hallucination rate
- A model with egregious fabrications (avg severity 5) loses 100 points per 100% hallucination rate
- Refusals are penalized at 25 per 100% refusal rate — much less than hallucinations, because refusing is safer than fabricating

WRS is clamped to [0, 100].

### TDR — Trap Detection Rate

Measures the model's ability to recognize adversarial questions. Calculated across `false_premise` and `citation_trap` categories only:

```
TDR = (correct trap responses) / (total trap questions)
```

A model that accepts all false premises and fabricates citations will have TDR = 0%. A model that correctly refuses or corrects all trap questions will have TDR = 100%.

### Hallucination Rate

Simple ratio of hallucinated responses to total responses:

```
hallucination_rate = hallucinated / total
```

### Cost Efficiency

The dashboard displays cost per 100 questions based on estimated token usage (~200 input + ~200 output tokens per question). Cost efficiency can be derived as WRS per dollar.

## Grading Approach

All grading is **deterministic and rule-based**. No LLM is used in the grading pipeline. This ensures reproducibility — the same response always gets the same grade.

The grading pipeline uses:
- **Text normalization** (lowercasing, whitespace normalization, article removal)
- **Pattern matching** for refusal detection, correction detection, and hallucination triggers
- **Keyword overlap** for summarization fidelity
- **Numeric parsing** with configurable tolerance for numerical questions
- **Behavioral patterns** defined per question in the dataset JSON

### Known Limitations

- **Summarization grading** uses keyword overlap (40% threshold) rather than semantic similarity. Edge cases exist where a semantically accurate summary uses different vocabulary.
- **False premise detection** relies on pattern matching for refusal/correction language. A model that corrects a premise using unexpected phrasing may be misclassified.
- **No partial credit** — a response is either correct, incorrect, hallucinated, refused, or uncertain. There is no scoring gradient within a grade.

These limitations are documented because transparency about methodology constraints is part of the benchmark's credibility. LLM-judge grading for subjective categories is on the roadmap.

## Reproducibility

The public question set (`dataset/public_tests.json`) is included in the repository. Anyone can run the benchmark against any supported model and verify results independently.

Evaluations are run weekly via automated cron on the production database. Historical results are preserved — the dashboard shows the most recent evaluation per model.
