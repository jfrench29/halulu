# Halulu AI Reliability Index — Work Log

## 2026-03-09: Evaluation Architecture v2 — Severity, WRS, and Dashboard Redesign

### What Changed

**New Metrics & Scoring:**
- **WRS (Weighted Reliability Score):** Replaces flat `accuracy*100 - hallu*200 - refusal*50` formula. New: `accuracy*100 - hallu_rate*severity_weight - refusal_rate*25` where severity_weight scales 50-100 based on avg hallucination severity. Fabricated citations penalized harder than minor numerical errors.
- **TDR (Trap Detection Rate):** % of false_premise + citation_trap questions correctly identified. Measures a distinct capability from general accuracy.
- **Hallucination Severity (0-5):** 0=none, 1=minor, 2=moderate, 3=significant, 4=dangerous, 5=egregious. Assigned by category and hallucination subtype.
- **Uncertain classification:** New result type for vague/hedging responses. Prevents "I'm not sure" from being graded as hallucinated.

**Grading Changes:**
- `false_premise.py` and `citation_trap.py`: Vague responses now return "uncertain" (was "hallucinated")
- All graders assign severity scores on incorrect/hallucinated results
- `classify_severity()` in normalization.py routes by category + subtype

**Dataset Expansion:** 40 → 49 public questions
- +4 summarization (Kubernetes, JWST, zero-knowledge proofs)
- +3 document_grounded (Project Meridian, Solaris X1 EV, NovaBio trial)
- +2 citation_trap (fake IEEE paper, fake JAMA study)
- +1 numerical (Tokyo metro population)

**Dashboard Redesign:**
- REMOVED: Hallucination of the Week, Hall of Fame, Questions per Category bar chart
- ADDED: Category Accuracy Heatmap (model × category grid), Model Spotlight (SVG radar chart), Cost Efficiency table (WRS per $1)
- UPDATED: Leaderboard shows WRS, TDR, Avg Severity; methodology section updated

**DB Schema:**
- Added `severity INTEGER DEFAULT 0` column to eval_results (auto-migrated)

**Tests:** 50 → 76 (added severity scoring, uncertain classification, WRS/TDR metric tests)

### Files Modified
- `grading/schemas.py` — UNCERTAIN enum, severity field, SEVERITY_SCALE
- `grading/normalization.py` — detect_vague(), classify_severity(), VAGUE_PHRASES
- `grading/graders/{false_premise,citation_trap}.py` — uncertain + severity
- `grading/graders/{closed_factual,document_grounded,summarization,numerical}.py` — severity
- `grading/metrics.py` — WRS, TDR, uncertain rate, avg_severity
- `storage/db.py` — severity column + migration
- `runner/evaluate_models.py` — severity passthrough, uncertain icon
- `dataset/public_tests.json` — 40 → 49 questions
- `tests/test_graders.py` — 50 → 76 tests
- `dashboard/streamlit_app.py` — full redesign

### Rationale for Removing Dashboard Sections
- **Hall of Fame / Hallucination of the Week:** Risk of reducing trust if grading has any false positives. Removed until confidence is higher.
- **Bar chart (Questions per Category):** Internal QA metric, not useful for end users. Replaced with Category Accuracy Heatmap.

---

## 2026-03-09: Grading System Audit

### Overall Assessment
The behavioral grading refactor successfully fixed the core false-positive bug and the system is functional. However, the current dataset lacks difficulty — **5 of 8 models score a perfect 100.0**, which means the benchmark isn't differentiating top-tier models effectively.

### Findings

**1. Dataset Difficulty (High Priority)**
- All 10 closed_factual questions are tagged "easy" — trivial for modern LLMs
- Only false_premise and citation_trap categories produce failures
- Result: leaderboard is a flat tie at the top, reducing the benchmark's value

**2. Scoring Formula Imbalance (Medium Priority)**
- Current: `accuracy * 100 - hallucination_rate * 200 - refusal_rate * 50`
- The 200x hallucination penalty is disproportionate — a model with 90% accuracy but 50% hallucination rate scores 0
- Consider: `accuracy * 100 - hallucination_rate * 100 - refusal_rate * 25`

**3. Grading Logic Edge Cases (Low Priority)**
- Substring matching in closed_factual/document_grounded can be too lenient (e.g., "Au" matches inside "automatic")
- False premise and citation trap graders default to "hallucinated" when no correction is detected — correct design intent, but aggressive if a model gives a vague non-answer

**4. Test Coverage Gaps (Low Priority)**
- Missing edge cases: numerical grading with scientific notation scale words, summarization threshold boundaries, empty reference_facts handling
- No integration tests (grade dispatcher -> DB -> metrics pipeline)

**5. Latent UI Bug**
- Footer in streamlit_app.py uses `"""` (not f-string) with `{_link_color}` — variable won't interpolate

### Evaluation Results (Post-Refactor)

| Model | Score | Accuracy | Halulu Rate | Cost/100q |
|-------|-------|----------|-------------|-----------|
| Claude Opus 4.6 | 100.0 | 100.0% | 0.0% | $1.80 |
| Claude Haiku 4.5 | 100.0 | 100.0% | 0.0% | $0.05 |
| GPT-4o | 100.0 | 100.0% | 0.0% | $0.25 |
| Gemini 2.5 Pro | 100.0 | 100.0% | 0.0% | $0.25 |
| Llama 3.3 70B | 100.0 | 100.0% | 0.0% | $0.04 |
| GPT-4o-mini | 93.3 | 96.7% | 0.0% | $0.01 |
| Claude Sonnet 4.6 | 86.7 | 93.3% | 3.3% | $0.36 |
| Mistral Large | 86.7 | 93.3% | 3.3% | $0.16 |

### Recommendation
Highest-impact improvement: add harder questions (obscure facts, recent events, complex numerical) to break the 5-way tie at 100.0.

---

## 2026-03-09: Dashboard Brand Refresh

### Design Philosophy
Simplistic, developer-oriented (Google.com / HuggingFace style). Tightened margins, reduced whitespace, consistent typography across light and dark modes.

### Brand Palette
- **Primary accent:** `#6C5CE7` (Halulu purple — retained for brand continuity)
- **Light mode:** `#FFFFFF` bg, `#F6F8FA` cards, `#1F2328` text, `#D1D9E0` borders
- **Dark mode:** `#0D1117` bg (GitHub-dark), `#161B22` cards, `#E6EDF3` text, `#30363D` borders
- **Semantic colors (shared both modes):** correct `#2DD4BF`, hallucinated `#EF4444`, warning `#F59E0B`, info `#3B82F6`

### Changes Made
1. **Typography:** Inter font via Google Fonts import, tightened letter-spacing, smaller section headers (1.15rem vs 1.5rem)
2. **Spacing:** Hero padding 1.25rem (was 2rem), stat card padding 0.75rem (was 1.25rem), section margins 1.75rem (was 2.5rem), card margins 0.5-0.75rem (was 1rem)
3. **Layout:** Stress tests in 2-column grid instead of single column; max-width 1100px container
4. **Theme toggle:** Replaced st.toggle with a sun/moon button (less visual noise)
5. **Color consistency:** All text, card, border, and link colors defined in unified palette dict — no hardcoded colors in HTML templates
6. **Dizzy face emoji:** Incorporated in hero title, section headers (Hallucination of the Week, Hall of Fame), footer branding, and Halulu Rate column header
7. **Footer fix:** Converted to f-string so link color variable properly interpolates
8. **Card styling:** Reduced border-radius from 12px to 8px (developer aesthetic), model tags use 4px radius pills
9. **Table styling:** Added theme-aware header background and border colors for methodology table
10. **Streamlit overrides:** Notification boxes, chart containers, and markdown elements all inherit theme colors

### Bugs Fixed
- Footer `{_link_color}` was inside a non-f-string (`"""`), rendering as literal text — now uses f-string
- Dark mode text colors were not applied to markdown `<p>`, `<strong>`, `<h1-h3>` elements — added CSS overrides
