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

# ── Custom CSS ────────────────────────────────────────────────────────

if dark:
    _bg = "#0E1117"
    _bg2 = "#1a1a2e"
    _text = "#FAFAFA"
    _text_muted = "#888"
    _border = "#333"
    _card_bg = "#1a1a2e"
    _card_border = "#444"
    _prompt_text = "#ccc"
    _footer_color = "#666"
    _link_color = "#888"
    _stress_q_color = "#ccc"
else:
    _bg = "#FFFFFF"
    _bg2 = "#F0F2F6"
    _text = "#1A1A2E"
    _text_muted = "#666"
    _border = "#E0E0E0"
    _card_bg = "#F8F9FA"
    _card_border = "#DEE2E6"
    _prompt_text = "#444"
    _footer_color = "#999"
    _link_color = "#666"
    _stress_q_color = "#333"

st.markdown(f"""
<style>
    /* Hide Streamlit chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Base */
    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: {_bg};
        color: {_text};
    }}

    /* Hero */
    .hero {{ text-align: center; padding: 2rem 0 1rem; }}
    .hero h1 {{ font-size: 3rem; margin-bottom: 0.25rem; color: {_text}; }}
    .hero .tagline {{ font-size: 1.2rem; color: {_text_muted}; margin-bottom: 2rem; }}

    /* Stat cards */
    .stat-row {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; margin: 1.5rem 0; }}
    .stat-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 12px;
        padding: 1.25rem 2rem;
        text-align: center;
        min-width: 160px;
    }}
    .stat-card .value {{ font-size: 2rem; font-weight: 700; color: {_text}; }}
    .stat-card .label {{ font-size: 0.85rem; color: {_text_muted}; margin-top: 4px; }}

    /* Section headers */
    .section-header {{
        font-size: 1.5rem;
        font-weight: 700;
        margin: 2.5rem 0 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {_border};
        color: {_text};
    }}

    /* Hall of fame cards */
    .hof-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }}
    .hof-card .model-tag {{
        display: inline-block;
        background: #e74c3c;
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }}
    .hof-card .prompt-text {{ color: {_prompt_text}; margin-bottom: 0.75rem; font-style: italic; }}
    .hof-card .response-text {{ color: #e74c3c; margin-bottom: 0.75rem; }}
    .hof-card .correct-text {{ color: #2ecc71; }}

    /* Stress test cards */
    .stress-card {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }}
    .stress-card .cat-tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }}
    .cat-false_premise {{ background: #e74c3c; color: white; }}
    .cat-citation_trap {{ background: #e67e22; color: white; }}
    .cat-numerical {{ background: #3498db; color: white; }}
    .cat-closed_factual {{ background: #2ecc71; color: white; }}
    .cat-document_grounded {{ background: #9b59b6; color: white; }}
    .cat-summarization {{ background: #1abc9c; color: white; }}

    /* Footer */
    .footer {{
        text-align: center;
        padding: 3rem 0 2rem;
        color: {_footer_color};
        font-size: 0.85rem;
        border-top: 1px solid {_border};
        margin-top: 3rem;
    }}
    .footer a {{ color: {_link_color}; }}
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


# ── Hero Section ──────────────────────────────────────────────────────

_toggle_col1, _toggle_col2 = st.columns([9, 1])
with _toggle_col2:
    if st.toggle("Dark", value=st.session_state.dark_mode, key="dark_toggle"):
        if not st.session_state.dark_mode:
            st.session_state.dark_mode = True
            st.rerun()
    else:
        if st.session_state.dark_mode:
            st.session_state.dark_mode = False
            st.rerun()

st.markdown("""
<div class="hero">
    <h1>Halulu</h1>
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

st.markdown('<div class="section-header">Hallucination of the Week 😵‍💫</div>', unsafe_allow_html=True)

hof = load_hall_of_fame()
if hof:
    featured = hof[0]
    prompt_safe = featured["prompt"][:500].replace("<", "&lt;").replace(">", "&gt;")
    response_safe = featured["response"][:500].replace("<", "&lt;").replace(">", "&gt;")
    subtype = featured.get("hallucination_subtype", "unknown")

    st.markdown(f"""
    <div class="hof-card">
        <div class="model-tag">{featured["model"]}</div>
        <span style="color: {_text_muted}; font-size: 0.8rem; margin-left: 8px;">({subtype})</span>
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
st.markdown("Sample questions from our benchmark designed to catch AI hallucinations:")

questions = load_sample_questions()
stress_categories = ["false_premise", "citation_trap"]
stress_qs = [q for q in questions if q.get("category") in stress_categories][:6]

for q in stress_qs:
    cat = q.get("category", "unknown")
    prompt_safe = q["prompt"][:300].replace("<", "&lt;").replace(">", "&gt;")
    answer_safe = q["correct_answer"][:200].replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(f"""
    <div class="stress-card">
        <div class="cat-tag cat-{cat}">{cat.replace("_", " ").title()}</div>
        <div style="color: {_stress_q_color}; margin-top: 0.5rem;"><strong>Q:</strong> {prompt_safe}</div>
        <div style="color: #2ecc71; margin-top: 0.5rem;"><strong>Correct:</strong> {answer_safe}</div>
    </div>
    """, unsafe_allow_html=True)

# ── 5. Benchmark Dataset Transparency ─────────────────────────────────

st.markdown('<div class="section-header">Benchmark Dataset Transparency</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    **Methodology**

    Halulu tests AI models across six hallucination categories:

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
    st.markdown("""
    **Scoring**

    - **Reliability Score** = `accuracy * 100 - halulu_rate * 200 - refusal_rate * 50`
    - Clamped to 0-100. Higher is better.

    **Grade Definitions**
    - ✅ **Correct** — factually accurate response
    - ❌ **Incorrect** — wrong but not fabricated
    - 😵‍💫 **Hallucinated** — confidently fabricated
    - 🤷 **Refused** — declined to answer

    **Dataset**: 30 public questions + 10 hidden scoring questions.
    All questions have verifiable correct answers.
    """)

if questions:
    cats = {}
    for q in questions:
        c = q.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    cat_df = pd.DataFrame([{"Category": k.replace("_", " ").title(), "Questions": v} for k, v in cats.items()])
    st.bar_chart(cat_df.set_index("Category"))

# ── 6. Hallucination Hall of Fame ─────────────────────────────────────

st.markdown('<div class="section-header">Hallucination Hall of Fame 😵‍💫</div>', unsafe_allow_html=True)
st.markdown("The most egregious AI hallucinations caught by our benchmark. Easy to screenshot and share!")

if hof and len(hof) > 1:
    for entry in hof[1:10]:
        prompt_safe = entry["prompt"][:400].replace("<", "&lt;").replace(">", "&gt;")
        response_safe = entry["response"][:400].replace("<", "&lt;").replace(">", "&gt;")
        subtype = entry.get("hallucination_subtype", "unknown")

        st.markdown(f"""
        <div class="hof-card">
            <div class="model-tag">{entry["model"]}</div>
            <span style="color: {_text_muted}; font-size: 0.8rem; margin-left: 8px;">({subtype})</span>
            <div class="prompt-text"><strong>Prompt:</strong> {prompt_safe}</div>
            <div class="response-text"><strong>Model said:</strong> {response_safe}</div>
        </div>
        """, unsafe_allow_html=True)
elif not hof:
    st.info("Hall of Fame will populate after running benchmarks.")

# ── Footer ────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
    <strong>Halulu</strong> — AI Reliability Index<br>
    Benchmarking hallucination rates so you don't have to trust blindly.<br>
    <a href="https://github.com/jfrench29/halulu" target="_blank" style="color: {_link_color};">GitHub</a>
</div>
""", unsafe_allow_html=True)
