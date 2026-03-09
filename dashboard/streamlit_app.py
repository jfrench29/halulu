"""Halulu — AI Reliability Index dashboard.

Clean, developer-focused UI. Think HuggingFace leaderboard meets Google simplicity.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grading.metrics import compute_metrics, compute_reliability_score
from storage.db import ResultsDB

# ── Page config ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="Halulu — AI Reliability Index",
    page_icon="https://halulu.ai/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Analytics (privacy-friendly, no cookies) ──────────────────────────

PLAUSIBLE_DOMAIN = os.environ.get("PLAUSIBLE_DOMAIN", "halulu.ai")
PLAUSIBLE_ENABLED = os.environ.get("PLAUSIBLE_ENABLED", "false").lower() == "true"

if PLAUSIBLE_ENABLED:
    components.html(
        f"""<script defer data-domain="{PLAUSIBLE_DOMAIN}"
        src="https://plausible.io/js/script.js"></script>""",
        height=0,
    )

# ── Open Graph / SEO meta tags ────────────────────────────────────────

OG_TAGS = """
<style>
    /* Hide the Streamlit-injected meta tags div */
    .og-meta { display: none; }
</style>
<div class="og-meta">
    <meta property="og:title" content="Halulu — AI Reliability Index" />
    <meta property="og:description" content="Are AI models delulu? Live hallucination benchmarks for GPT, Claude, Gemini and more." />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://halulu.ai" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Halulu — AI Reliability Index" />
    <meta name="twitter:description" content="Live hallucination benchmarks for popular AI models." />
</div>
"""
components.html(OG_TAGS, height=0)


# ── Database connection ───────────────────────────────────────────────

@st.cache_resource
def get_db():
    return ResultsDB()


# ── Custom CSS for developer-focused clean UI ─────────────────────────

st.markdown("""
<style>
    /* Clean, minimal typography */
    .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    /* Hero section */
    .hero { text-align: center; padding: 1rem 0 2rem 0; }
    .hero h1 { font-size: 2.8rem; font-weight: 700; margin-bottom: 0.25rem; }
    .hero .tagline { font-size: 1.1rem; color: #888; margin-bottom: 0; }
    .hero .subtext { font-size: 0.85rem; color: #555; }

    /* Stat cards */
    .stat-row { display: flex; gap: 1rem; justify-content: center; margin: 1.5rem 0; }
    .stat-card {
        background: #1A1D23; border: 1px solid #2A2D33; border-radius: 8px;
        padding: 1rem 1.5rem; text-align: center; min-width: 140px;
    }
    .stat-card .num { font-size: 1.6rem; font-weight: 700; color: #6C5CE7; }
    .stat-card .label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Leaderboard table polish */
    .stDataFrame { border-radius: 8px; }

    /* Section headers */
    .section-header {
        font-size: 1.3rem; font-weight: 600; margin-top: 2.5rem;
        padding-bottom: 0.5rem; border-bottom: 1px solid #2A2D33;
    }

    /* Footer */
    .footer {
        text-align: center; padding: 2rem 0 1rem 0;
        color: #555; font-size: 0.8rem; border-top: 1px solid #1A1D23;
        margin-top: 3rem;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Tighten padding */
    .block-container { padding-top: 2rem; max-width: 1100px; }
</style>
""", unsafe_allow_html=True)


# ── Main app ──────────────────────────────────────────────────────────

def main():
    db = get_db()
    models = db.get_model_names()

    # ── Hero ──
    st.markdown("""
    <div class="hero">
        <h1>halulu</h1>
        <p class="tagline">AI Reliability Index</p>
        <p class="subtext">Measuring hallucination rates across popular AI models. Updated weekly.</p>
    </div>
    """, unsafe_allow_html=True)

    if not models:
        st.info("No evaluation data yet. First benchmark run coming soon.")
        return

    # ── Summary stats ──
    latest = db.get_latest_results_per_model()
    total_evals = db.get_result_count()

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="num">{len(models)}</div>
            <div class="label">Models Tested</div>
        </div>
        <div class="stat-card">
            <div class="num">{total_evals:,}</div>
            <div class="label">Total Evaluations</div>
        </div>
        <div class="stat-card">
            <div class="num">30+</div>
            <div class="label">Benchmark Questions</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Leaderboard ──
    st.markdown('<div class="section-header">Leaderboard</div>', unsafe_allow_html=True)

    leaderboard_data = []
    for model in models:
        results = latest.get(model, [])
        if not results:
            continue
        metrics = compute_metrics(model, results)
        score = compute_reliability_score(metrics)
        leaderboard_data.append({
            "model": model,
            "score": score,
            "accuracy": metrics.accuracy_rate,
            "hallucination": metrics.hallucination_rate,
            "refusal": metrics.refusal_rate,
            "latency": metrics.avg_latency_ms,
            "tests": metrics.total,
        })

    if leaderboard_data:
        df = pd.DataFrame(leaderboard_data).sort_values("score", ascending=False).reset_index(drop=True)
        df.index = df.index + 1  # 1-based ranking

        display_df = pd.DataFrame({
            "Rank": df.index,
            "Model": df["model"],
            "Reliability": df["score"].apply(lambda x: f"{x:.1f}"),
            "Accuracy": df["accuracy"].apply(lambda x: f"{x:.1%}"),
            "Hallucination": df["hallucination"].apply(lambda x: f"{x:.1%}"),
            "Refusal": df["refusal"].apply(lambda x: f"{x:.1%}"),
            "Latency": df["latency"].apply(lambda x: f"{x:.0f}ms"),
            "Tests": df["tests"],
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=min(400, 35 * len(df) + 38))

    # ── Charts ──
    st.markdown('<div class="section-header">Performance Comparison</div>', unsafe_allow_html=True)

    if leaderboard_data:
        df_chart = pd.DataFrame(leaderboard_data)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("ACCURACY (higher is better)")
            chart = df_chart.set_index("model")[["accuracy"]].sort_values("accuracy", ascending=False)
            st.bar_chart(chart)
        with col2:
            st.caption("HALLUCINATION RATE (lower is better)")
            chart = df_chart.set_index("model")[["hallucination"]].sort_values("hallucination", ascending=True)
            st.bar_chart(chart)
        with col3:
            st.caption("REFUSAL RATE")
            chart = df_chart.set_index("model")[["refusal"]].sort_values("refusal", ascending=True)
            st.bar_chart(chart)

    # ── Trends ──
    st.markdown('<div class="section-header">Trends Over Time</div>', unsafe_allow_html=True)

    trend_data = db.get_trend_data(models=models)
    if trend_data:
        df_trend = pd.DataFrame(trend_data)
        df_trend["accuracy"] = df_trend["correct"] / df_trend["total"]
        df_trend["hallucination_rate"] = df_trend["hallucinated"] / df_trend["total"]

        metric = st.radio("Metric", ["accuracy", "hallucination_rate"], horizontal=True, label_visibility="collapsed")
        pivot = df_trend.pivot(index="eval_date", columns="model", values=metric)
        if not pivot.empty:
            st.line_chart(pivot)
        else:
            st.caption("Not enough data points for trends yet.")
    else:
        st.caption("Run multiple evaluations over time to see trends.")

    # ── Category breakdown ──
    with st.expander("Performance by Category", expanded=False):
        for model in models:
            results = latest.get(model, [])
            if not results:
                continue
            metrics = compute_metrics(model, results)
            if metrics.category_breakdown:
                st.caption(model)
                cat_rows = []
                for cat, stats in metrics.category_breakdown.items():
                    cat_rows.append({
                        "Category": cat,
                        "Total": int(stats["total"]),
                        "Accuracy": f"{stats['accuracy_rate']:.1%}",
                        "Hallucination": f"{stats['hallucination_rate']:.1%}",
                        "Refusal": f"{stats['refusal_rate']:.1%}",
                    })
                st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

    # ── Hall of Fame ──
    st.markdown('<div class="section-header">Hallucination Hall of Fame</div>', unsafe_allow_html=True)
    st.caption("The most interesting hallucinated answers from AI models.")

    hof = db.get_hall_of_fame(limit=20)
    if hof:
        for entry in hof:
            label = f"{entry['model']} \u2014 Test #{entry['test_id']} ({entry.get('hallucination_subtype', 'unknown')})"
            with st.expander(label):
                # XSS-safe: use st.code/st.text for untrusted content, never st.markdown
                st.text(f"PROMPT:\n{entry['prompt']}")
                st.text(f"\nRESPONSE:\n{entry['response'][:2000]}")
    else:
        st.caption("No hallucinations recorded yet.")

    # ── Methodology ──
    with st.expander("Methodology", expanded=False):
        st.markdown("""
**Benchmark Design:** Four-layer strategy — public questions for transparency,
hidden questions for scoring, weekly rotating questions to prevent overfitting,
and community adversarial prompts (coming soon).

**Question Types:** `closed_book`, `document_grounded`, `summarization`, `adversarial_trap`

**Grading:** Responses are classified as `correct`, `wrong`, `hallucinated`, or `refused`.
Hallucination subtypes: `fabricated_fact`, `fabricated_entity`, `fabricated_citation`,
`unsupported_claim`, `numerical_error`.

**Reliability Score:** `accuracy * 100 - hallucination_rate * 200 - refusal_rate * 50` (clamped 0-100).
Hallucinations are penalized 2x because confident wrong answers are worse than admitting uncertainty.
        """)

    # ── Footer ──
    st.markdown("""
    <div class="footer">
        <p><strong>halulu.ai</strong> &mdash; Open AI reliability benchmarks</p>
        <p>Built by <a href="https://github.com/jfrench29" target="_blank" style="color: #6C5CE7;">@jfrench29</a>
        &nbsp;&middot;&nbsp; <a href="https://github.com/jfrench29/halulu" target="_blank" style="color: #6C5CE7;">GitHub</a></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
