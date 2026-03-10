"""Halulu AI Reliability Index — Dashboard

Sections:
1. AI Reliability Leaderboard
2. Hallucination of the Week
3. Model Trend Chart
4. Reality Stress Tests (sample questions)
5. Benchmark Dataset Transparency
6. Hallucination Hall of Fame
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grading.metrics import compute_metrics, compute_reliability_score
from runner.model_adapters import get_cost_per_100
from storage.db import ResultsDB

# ── Config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Halulu - AI Reliability Index",
    page_icon="😵‍💫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PLAUSIBLE_ENABLED = os.environ.get("PLAUSIBLE_ENABLED", "false").lower() == "true"
PLAUSIBLE_DOMAIN = os.environ.get("PLAUSIBLE_DOMAIN", "halulu.ai")

# ── Analytics & Meta ──────────────────────────────────────────────────

if PLAUSIBLE_ENABLED:
    components.html(
        f'<script defer data-domain="{PLAUSIBLE_DOMAIN}" '
        f'src="https://plausible.io/js/script.js"></script>',
        height=0,
    )

components.html(
    """<head>
    <meta property="og:title" content="Halulu - AI Reliability Index" />
    <meta property="og:description" content="Benchmarking hallucination rates across AI models. How delusional is your AI?" />
    <meta property="og:type" content="website" />
    </head>""",
    height=0,
)

# ── Theme Toggle ─────────────────────────────────────────────────────

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

dark = st.session_state.dark_mode

# ── Brand Palette ────────────────────────────────────────────────────
# Unified color system — accent + semantic colors stay constant across
# both modes so the brand reads identically light or dark.

_accent = "#6C5CE7"        # halulu purple
_accent_soft = "#8B7CF6"   # lighter purple for hover / subtle
_correct = "#2DD4BF"       # teal-green (semantic: correct)
_hallucinated = "#EF4444"  # red (semantic: hallucinated)
_warning = "#F59E0B"       # amber (semantic: citation trap)
_info = "#3B82F6"          # blue (semantic: numerical)
_organic = "#10B981"       # green (semantic: document grounded)
_teal = "#14B8A6"          # teal (semantic: summarization)

if dark:
    _bg = "#0D1117"
    _bg_secondary = "#161B22"
    _text = "#E6EDF3"
    _text_secondary = "#8B949E"
    _text_muted = "#6E7681"
    _border = "#30363D"
    _card_bg = "#161B22"
    _card_border = "#30363D"
    _table_header_bg = "#1C2128"
    _link = "#8B7CF6"
else:
    _bg = "#FFFFFF"
    _bg_secondary = "#F6F8FA"
    _text = "#1F2328"
    _text_secondary = "#59636E"
    _text_muted = "#8B949E"
    _border = "#D1D9E0"
    _card_bg = "#F6F8FA"
    _card_border = "#D1D9E0"
    _table_header_bg = "#F0F2F5"
    _link = "#6C5CE7"

# ── Custom CSS ────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    /* ── Reset & Base ───────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background-color: {_bg};
        color: {_text};
    }}

    /* Tighten Streamlit's default block spacing */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1100px;
    }}

    /* ── Hero ───────────────────────────────────────────────────── */
    .hero {{
        text-align: center;
        padding: 1.25rem 0 0.5rem;
    }}
    .hero h1 {{
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: {_text};
        letter-spacing: -0.02em;
    }}
    .hero .tagline {{
        font-size: 1rem;
        color: {_text_secondary};
        margin: 0.25rem 0 1rem;
        font-weight: 400;
    }}

    /* ── Stat Cards ────────────────────────────────────────────── */
    .stat-row {{
        display: flex;
        gap: 0.75rem;
        justify-content: center;
        flex-wrap: wrap;
        margin: 0.75rem 0 1.25rem;
    }}
    .stat-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        text-align: center;
        min-width: 140px;
        flex: 1;
        max-width: 200px;
    }}
    .stat-card .value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {_text};
        line-height: 1.2;
    }}
    .stat-card .label {{
        font-size: 0.75rem;
        color: {_text_muted};
        margin-top: 2px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 500;
    }}

    /* ── Section Headers ───────────────────────────────────────── */
    .section-header {{
        font-size: 1.15rem;
        font-weight: 600;
        margin: 1.75rem 0 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid {_border};
        color: {_text};
        letter-spacing: -0.01em;
    }}

    /* ── Leaderboard Table ─────────────────────────────────────── */
    .stDataFrame {{
        font-size: 0.875rem;
    }}
    .stDataFrame [data-testid="stDataFrameResizable"] {{
        border: 1px solid {_card_border};
        border-radius: 8px;
        overflow: hidden;
    }}

    /* ── Hall of Fame Cards ────────────────────────────────────── */
    .hof-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }}
    .hof-card .model-tag {{
        display: inline-block;
        background: {_hallucinated};
        color: white;
        padding: 1px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .hof-card .subtype-tag {{
        color: {_text_muted};
        font-size: 0.75rem;
        margin-left: 6px;
    }}
    .hof-card .prompt-text {{
        color: {_text_secondary};
        margin: 0.5rem 0;
        font-size: 0.875rem;
        line-height: 1.5;
    }}
    .hof-card .response-text {{
        color: {_hallucinated};
        margin: 0.5rem 0;
        font-size: 0.875rem;
        line-height: 1.5;
    }}
    .hof-card .correct-text {{
        color: {_correct};
        font-size: 0.875rem;
    }}

    /* ── Stress Test Cards ─────────────────────────────────────── */
    .stress-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 8px;
        padding: 0.875rem 1rem;
        margin-bottom: 0.5rem;
    }}
    .stress-card .cat-tag {{
        display: inline-block;
        padding: 1px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .cat-false_premise {{ background: {_hallucinated}; color: white; }}
    .cat-citation_trap {{ background: {_warning}; color: white; }}
    .cat-numerical {{ background: {_info}; color: white; }}
    .cat-closed_factual {{ background: {_correct}; color: white; }}
    .cat-document_grounded {{ background: {_organic}; color: white; }}
    .cat-summarization {{ background: {_teal}; color: white; }}

    /* ── Methodology Table ─────────────────────────────────────── */
    .stMarkdown table {{
        font-size: 0.825rem;
        border-collapse: collapse;
        width: 100%;
    }}
    .stMarkdown th {{
        background: {_table_header_bg};
        color: {_text};
        font-weight: 600;
        text-align: left;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid {_border};
    }}
    .stMarkdown td {{
        padding: 0.4rem 0.75rem;
        border-bottom: 1px solid {_card_border};
        color: {_text_secondary};
    }}

    /* ── Footer ────────────────────────────────────────────────── */
    .site-footer {{
        text-align: center;
        padding: 1.5rem 0 1rem;
        color: {_text_muted};
        font-size: 0.8rem;
        border-top: 1px solid {_border};
        margin-top: 2rem;
    }}
    .site-footer a {{
        color: {_link};
        text-decoration: none;
    }}
    .site-footer a:hover {{
        text-decoration: underline;
    }}

    /* ── Dark Mode Toggle ──────────────────────────────────────── */
    .mode-toggle {{
        position: fixed;
        top: 12px;
        right: 16px;
        z-index: 999;
        font-size: 0.8rem;
        color: {_text_muted};
    }}

    /* ── Streamlit widget overrides ────────────────────────────── */
    .stMarkdown p {{
        color: {_text_secondary};
        font-size: 0.875rem;
        line-height: 1.6;
    }}
    .stMarkdown strong {{
        color: {_text};
    }}
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: {_text};
    }}

    /* Info boxes */
    [data-testid="stNotification"] {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        color: {_text_secondary};
        border-radius: 8px;
    }}

    /* Chart area */
    .stPlotlyChart, [data-testid="stArrowVegaLiteChart"] {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 8px;
        padding: 0.5rem;
    }}
</style>
""", unsafe_allow_html=True)

# ── Data Loading ──────────────────────────────────────────────────────


@st.cache_resource(ttl=60)
def get_db():
    return ResultsDB()


@st.cache_data(ttl=120)
def load_leaderboard():
    db = get_db()
    results_by_model = db.get_latest_results_per_model()
    rows = []
    for model, results in results_by_model.items():
        metrics = compute_metrics(model, results)
        score = compute_reliability_score(metrics)
        cost = get_cost_per_100(model)
        rows.append({
            "Model": model,
            "Score": score,
            "Accuracy": metrics.accuracy_rate,
            "Halulu Rate": metrics.hallucination_rate,
            "Refusal Rate": metrics.refusal_rate,
            "Avg Latency": f"{metrics.avg_latency_ms:.0f}ms",
            "Cost/100q": f"${cost:.2f}" if cost else "N/A",
            "Total": metrics.total,
        })
    return sorted(rows, key=lambda r: r["Score"], reverse=True)


@st.cache_data(ttl=120)
def load_hall_of_fame():
    db = get_db()
    return db.get_hall_of_fame(limit=20)


@st.cache_data(ttl=120)
def load_trend_data():
    db = get_db()
    return db.get_trend_data()


@st.cache_data(ttl=3600)
def load_sample_questions():
    path = PROJECT_ROOT / "dataset" / "public_tests.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


# ── Theme Toggle ─────────────────────────────────────────────────────

_toggle_col1, _toggle_col2 = st.columns([9, 1])
with _toggle_col2:
    _icon = "☀️" if dark else "🌙"
    if st.button(_icon, key="theme_btn", help="Toggle dark/light mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ── Hero Section ──────────────────────────────────────────────────────

st.markdown(f"""
<div class="hero">
    <h1>😵‍💫 Halulu</h1>
    <div class="tagline">AI Reliability Index — How delusional is your AI?</div>
</div>
""", unsafe_allow_html=True)

leaderboard = load_leaderboard()

if leaderboard:
    total_models = len(leaderboard)
    total_questions = sum(r["Total"] for r in leaderboard)
    avg_halulu = sum(r["Halulu Rate"] for r in leaderboard) / total_models if total_models else 0
    top_score = leaderboard[0]["Score"] if leaderboard else 0

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card"><div class="value">{total_models}</div><div class="label">Models Tested</div></div>
        <div class="stat-card"><div class="value">{total_questions}</div><div class="label">Questions Answered</div></div>
        <div class="stat-card"><div class="value">{avg_halulu:.1%}</div><div class="label">Avg Halulu Rate</div></div>
        <div class="stat-card"><div class="value">{top_score:.0f}</div><div class="label">Top Score</div></div>
    </div>
    """, unsafe_allow_html=True)

# ── 1. AI Reliability Leaderboard ─────────────────────────────────────

st.markdown('<div class="section-header">AI Reliability Leaderboard</div>', unsafe_allow_html=True)

if leaderboard:
    df = pd.DataFrame(leaderboard)

    display_df = pd.DataFrame({
        "Rank": range(1, len(df) + 1),
        "Model": df["Model"],
        "Score": df["Score"].apply(lambda x: f"{x:.1f}"),
        "Accuracy": df["Accuracy"].apply(lambda x: f"{x:.1%}"),
        "Halulu Rate 😵‍💫": df["Halulu Rate"].apply(lambda x: f"{x:.1%}"),
        "Refusal Rate": df["Refusal Rate"].apply(lambda x: f"{x:.1%}"),
        "Avg Latency": df["Avg Latency"],
        "Cost/100q": df["Cost/100q"],
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No evaluation data yet. Run the benchmark to populate the leaderboard.")

# ── 2. Hallucination of the Week ──────────────────────────────────────

st.markdown('<div class="section-header">😵‍💫 Hallucination of the Week</div>', unsafe_allow_html=True)

hof = load_hall_of_fame()
if hof:
    featured = hof[0]
    prompt_safe = featured["prompt"][:500].replace("<", "&lt;").replace(">", "&gt;")
    response_safe = featured["response"][:500].replace("<", "&lt;").replace(">", "&gt;")
    subtype = featured.get("hallucination_subtype", "unknown")

    st.markdown(f"""
    <div class="hof-card">
        <div class="model-tag">{featured["model"]}</div>
        <span class="subtype-tag">{subtype}</span>
        <div class="prompt-text"><strong>Prompt:</strong> {prompt_safe}</div>
        <div class="response-text"><strong>Model said:</strong> {response_safe}</div>
        <div class="correct-text"><strong>Reality:</strong> This is a hallucination.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No hallucinations recorded yet. Run the benchmark to catch some!")

# ── 3. Model Trend Chart ──────────────────────────────────────────────

st.markdown('<div class="section-header">Model Trend Chart</div>', unsafe_allow_html=True)

trend_data = load_trend_data()
if trend_data:
    trend_df = pd.DataFrame(trend_data)
    if "eval_date" in trend_df.columns and "hallucinated" in trend_df.columns:
        trend_df["halulu_rate"] = trend_df["hallucinated"] / trend_df["total"]
        chart_data = trend_df.pivot_table(
            index="eval_date", columns="model", values="halulu_rate", aggfunc="mean"
        )
        st.line_chart(chart_data)
    else:
        st.info("Not enough data for trend chart yet. Run multiple evaluations over time.")
else:
    st.info("Trend data will appear after multiple evaluation runs.")

# ── 4. Reality Stress Tests ───────────────────────────────────────────

st.markdown('<div class="section-header">Reality Stress Tests</div>', unsafe_allow_html=True)
st.markdown("Sample questions from our benchmark designed to catch AI hallucinations.")

questions = load_sample_questions()
stress_categories = ["false_premise", "citation_trap"]
stress_qs = [q for q in questions if q.get("category") in stress_categories][:6]

cols = st.columns(2)
for i, q in enumerate(stress_qs):
    cat = q.get("category", "unknown")
    prompt_safe = q["prompt"][:300].replace("<", "&lt;").replace(">", "&gt;")
    answer_safe = q["correct_answer"][:200].replace("<", "&lt;").replace(">", "&gt;")
    with cols[i % 2]:
        st.markdown(f"""
        <div class="stress-card">
            <div class="cat-tag cat-{cat}">{cat.replace("_", " ")}</div>
            <div style="color: {_text}; margin-top: 0.4rem; font-size: 0.85rem;"><strong>Q:</strong> {prompt_safe}</div>
            <div style="color: {_correct}; margin-top: 0.3rem; font-size: 0.85rem;"><strong>A:</strong> {answer_safe}</div>
        </div>
        """, unsafe_allow_html=True)

# ── 5. Benchmark Dataset Transparency ─────────────────────────────────

st.markdown('<div class="section-header">Benchmark Methodology</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
**Hallucination Categories**

| Category | What it catches |
|----------|-----------------|
| Closed Factual | Basic knowledge errors |
| False Premise | Accepting false assumptions |
| Citation Trap | Fabricating sources |
| Document Grounded | Unsupported claims |
| Summarization | Content distortion |
| Numerical | Numerical hallucinations |
""")

with col2:
    st.markdown(f"""
**Scoring**

Reliability Score = `accuracy * 100 - halulu_rate * 200 - refusal_rate * 50`
(clamped 0–100, higher is better)

**Grade Definitions**

- ✅ **Correct** — factually accurate
- ❌ **Incorrect** — wrong but not fabricated
- 😵‍💫 **Hallucinated** — confidently fabricated
- 🤷 **Refused** — declined to answer

**Dataset:** 30 public + 10 hidden scoring questions.
""")

if questions:
    cats = {}
    for q in questions:
        c = q.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    cat_df = pd.DataFrame([{"Category": k.replace("_", " ").title(), "Questions": v} for k, v in cats.items()])
    st.bar_chart(cat_df.set_index("Category"))

# ── 6. Hallucination Hall of Fame ─────────────────────────────────────

st.markdown('<div class="section-header">😵‍💫 Hallucination Hall of Fame</div>', unsafe_allow_html=True)
st.markdown("The most egregious AI hallucinations caught by our benchmark.")

if hof and len(hof) > 1:
    for entry in hof[1:10]:
        prompt_safe = entry["prompt"][:400].replace("<", "&lt;").replace(">", "&gt;")
        response_safe = entry["response"][:400].replace("<", "&lt;").replace(">", "&gt;")
        subtype = entry.get("hallucination_subtype", "unknown")

        st.markdown(f"""
        <div class="hof-card">
            <div class="model-tag">{entry["model"]}</div>
            <span class="subtype-tag">{subtype}</span>
            <div class="prompt-text"><strong>Prompt:</strong> {prompt_safe}</div>
            <div class="response-text"><strong>Model said:</strong> {response_safe}</div>
        </div>
        """, unsafe_allow_html=True)
elif not hof:
    st.info("Hall of Fame will populate after running benchmarks.")

# ── Footer ────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="site-footer">
    😵‍💫 <strong>Halulu</strong> — AI Reliability Index<br>
    Benchmarking hallucination rates so you don't have to trust blindly.<br>
    <a href="https://github.com/jfrench29/halulu" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
