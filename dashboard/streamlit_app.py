"""Halulu AI Reliability Index — Dashboard

Sections:
1. AI Reliability Leaderboard
2. Category Heatmap (model x category accuracy)
3. Model Spotlight (radar chart per model)
4. Reality Stress Tests (sample questions)
5. Benchmark Methodology
"""

from __future__ import annotations

import json
import math
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
# Primary analytics: Cloudflare Zaraz injects Plausible script at the CDN
# layer (no iframe issues). This fallback covers direct-to-Railway access.

if PLAUSIBLE_ENABLED:
    components.html(
        f"""<script>
        var s = document.createElement('script');
        s.defer = true;
        s.setAttribute('data-domain', '{PLAUSIBLE_DOMAIN}');
        s.setAttribute('data-api', 'https://plausible.io/api/event');
        s.src = 'https://plausible.io/js/script.manual.js';
        document.head.appendChild(s);
        s.onload = function() {{
            try {{ var u = window.parent.location.href; }} catch(e) {{ var u = 'https://{PLAUSIBLE_DOMAIN}'; }}
            window.plausible('pageview', {{u: u}});
        }};
        </script>""",
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

_accent = "#6C5CE7"
_accent_soft = "#8B7CF6"
_correct = "#2DD4BF"
_hallucinated = "#EF4444"
_warning = "#F59E0B"
_info = "#3B82F6"
_organic = "#10B981"
_teal = "#14B8A6"

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background-color: {_bg};
        color: {_text};
    }}

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
        min-width: 120px;
        flex: 1;
        max-width: 180px;
    }}
    .stat-card .value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {_text};
        line-height: 1.2;
    }}
    .stat-card .label {{
        font-size: 0.7rem;
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

    /* ── Heatmap ──────────────────────────────────────────────── */
    .heatmap-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
    }}
    .heatmap-table th {{
        background: {_table_header_bg};
        color: {_text};
        font-weight: 600;
        text-align: center;
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid {_border};
        font-size: 0.75rem;
    }}
    .heatmap-table td {{
        text-align: center;
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid {_card_border};
        font-weight: 500;
        font-size: 0.8rem;
    }}
    .heatmap-table td.model-name {{
        text-align: left;
        color: {_text};
        font-weight: 600;
        font-size: 0.8rem;
    }}

    /* ── Radar Chart ──────────────────────────────────────────── */
    .radar-svg {{
        display: block;
        margin: 0 auto;
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

    [data-testid="stNotification"] {{
        background: {_card_bg};
        border: 1px solid {_card_border};
        color: {_text_secondary};
        border-radius: 8px;
    }}

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
            "WRS": score,
            "Accuracy": metrics.accuracy_rate,
            "Halulu Rate": metrics.hallucination_rate,
            "TDR": metrics.trap_detection_rate,
            "Avg Severity": metrics.avg_severity,
            "Refusal Rate": metrics.refusal_rate,
            "Uncertain Rate": metrics.uncertain_rate,
            "Avg Latency": f"{metrics.avg_latency_ms:.0f}ms",
            "Cost/100q": f"${cost:.2f}" if cost else "N/A",
            "Total": metrics.total,
            "_category_breakdown": metrics.category_breakdown,
            "_cost": cost,
            "_wrs": score,
        })
    return sorted(rows, key=lambda r: r["WRS"], reverse=True)


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
    avg_halulu = sum(r["Halulu Rate"] for r in leaderboard) / total_models if total_models else 0
    avg_tdr = sum(r["TDR"] for r in leaderboard) / total_models if total_models else 0
    top_wrs = leaderboard[0]["WRS"] if leaderboard else 0
    # Cost efficiency: best WRS/cost ratio
    cost_eff = []
    for r in leaderboard:
        if r["_cost"] and r["_cost"] > 0:
            cost_eff.append({"model": r["Model"], "ratio": r["_wrs"] / r["_cost"]})
    best_value = max(cost_eff, key=lambda x: x["ratio"])["model"].split("-")[0].title() if cost_eff else "N/A"

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card"><div class="value">{total_models}</div><div class="label">Models Tested</div></div>
        <div class="stat-card"><div class="value">{top_wrs:.0f}</div><div class="label">Top WRS</div></div>
        <div class="stat-card"><div class="value">{avg_halulu:.1%}</div><div class="label">Avg Halulu Rate</div></div>
        <div class="stat-card"><div class="value">{avg_tdr:.0%}</div><div class="label">Avg Trap Detection</div></div>
        <div class="stat-card"><div class="value">{best_value}</div><div class="label">Best Value</div></div>
    </div>
    """, unsafe_allow_html=True)

# ── 1. AI Reliability Leaderboard ─────────────────────────────────────

st.markdown('<div class="section-header">AI Reliability Leaderboard</div>', unsafe_allow_html=True)

if leaderboard:
    df = pd.DataFrame(leaderboard)

    display_df = pd.DataFrame({
        "Rank": range(1, len(df) + 1),
        "Model": df["Model"],
        "WRS": df["WRS"].apply(lambda x: f"{x:.1f}"),
        "Accuracy": df["Accuracy"].apply(lambda x: f"{x:.1%}"),
        "Halulu Rate 😵‍💫": df["Halulu Rate"].apply(lambda x: f"{x:.1%}"),
        "Trap Detection": df["TDR"].apply(lambda x: f"{x:.0%}"),
        "Avg Severity": df["Avg Severity"].apply(lambda x: f"{x:.1f}" if x > 0 else "—"),
        "Latency": df["Avg Latency"],
        "Cost/100q": df["Cost/100q"],
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No evaluation data yet. Run the benchmark to populate the leaderboard.")

# ── 2. Category Accuracy Heatmap ──────────────────────────────────────

st.markdown('<div class="section-header">Category Accuracy Heatmap</div>', unsafe_allow_html=True)
st.markdown("How each model performs across different hallucination categories. Green = high accuracy, red = low.")

if leaderboard:
    categories = ["closed_factual", "false_premise", "citation_trap", "document_grounded", "summarization", "numerical"]
    cat_labels = {
        "closed_factual": "Factual",
        "false_premise": "False Premise",
        "citation_trap": "Citation Trap",
        "document_grounded": "Doc Grounded",
        "summarization": "Summary",
        "numerical": "Numerical",
    }

    def _heatmap_color(rate: float) -> str:
        """Green for high accuracy, red for low."""
        if rate >= 0.9:
            return "#2DD4BF"  # teal-green
        elif rate >= 0.7:
            return "#A7F3D0"  # light green
        elif rate >= 0.5:
            return "#FDE68A"  # yellow
        elif rate >= 0.3:
            return "#FCA5A5"  # light red
        else:
            return "#EF4444"  # red

    def _text_color_for_bg(bg: str) -> str:
        """Dark text for light backgrounds, light for dark."""
        if bg in ("#2DD4BF", "#A7F3D0", "#FDE68A", "#FCA5A5"):
            return "#1F2328"
        return "#FFFFFF"

    header_row = "<tr><th style='text-align:left;'>Model</th>"
    for cat in categories:
        header_row += f"<th>{cat_labels[cat]}</th>"
    header_row += "</tr>"

    body_rows = ""
    for row in leaderboard:
        breakdown = row.get("_category_breakdown", {})
        body_rows += f"<tr><td class='model-name'>{row['Model']}</td>"
        for cat in categories:
            cat_data = breakdown.get(cat, {})
            rate = cat_data.get("accuracy_rate", 0)
            bg = _heatmap_color(rate)
            tc = _text_color_for_bg(bg)
            body_rows += f"<td style='background:{bg}; color:{tc};'>{rate:.0%}</td>"
        body_rows += "</tr>"

    st.markdown(f"""
    <table class="heatmap-table">
        {header_row}
        {body_rows}
    </table>
    """, unsafe_allow_html=True)

# ── 3. Model Spotlight ────────────────────────────────────────────────

st.markdown('<div class="section-header">Model Spotlight</div>', unsafe_allow_html=True)
st.markdown("Select a model to see its strengths and weaknesses across categories.")

if leaderboard:
    model_names = [r["Model"] for r in leaderboard]
    selected_model = st.selectbox("Choose model", model_names, label_visibility="collapsed")

    selected_row = next((r for r in leaderboard if r["Model"] == selected_model), None)
    if selected_row:
        breakdown = selected_row.get("_category_breakdown", {})
        categories_for_radar = ["closed_factual", "false_premise", "citation_trap", "document_grounded", "summarization", "numerical"]
        radar_labels = ["Factual", "False\nPremise", "Citation\nTrap", "Doc\nGrounded", "Summary", "Numerical"]

        values = []
        for cat in categories_for_radar:
            cat_data = breakdown.get(cat, {})
            values.append(cat_data.get("accuracy_rate", 0))

        # Build SVG radar chart
        n = len(values)
        cx, cy, r = 160, 160, 120
        angles = [2 * math.pi * i / n - math.pi / 2 for i in range(n)]

        # Grid circles
        grid_svg = ""
        for level in [0.25, 0.5, 0.75, 1.0]:
            grid_r = r * level
            grid_svg += f'<circle cx="{cx}" cy="{cy}" r="{grid_r}" fill="none" stroke="{_border}" stroke-width="0.5" stroke-dasharray="3,3"/>'

        # Grid labels (25%, 50%, etc.)
        for level in [0.5, 1.0]:
            label_y = cy - r * level - 4
            grid_svg += f'<text x="{cx + 3}" y="{label_y}" font-size="9" fill="{_text_muted}" font-family="Inter, sans-serif">{int(level*100)}%</text>'

        # Axis lines and labels
        axis_svg = ""
        for i, angle in enumerate(angles):
            x_end = cx + r * math.cos(angle)
            y_end = cy + r * math.sin(angle)
            axis_svg += f'<line x1="{cx}" y1="{cy}" x2="{x_end}" y2="{y_end}" stroke="{_border}" stroke-width="0.5"/>'
            # Label
            lx = cx + (r + 24) * math.cos(angle)
            ly = cy + (r + 24) * math.sin(angle)
            label = radar_labels[i].replace("\n", "")
            axis_svg += f'<text x="{lx}" y="{ly}" font-size="10" fill="{_text_secondary}" text-anchor="middle" dominant-baseline="middle" font-family="Inter, sans-serif">{label}</text>'

        # Data polygon
        points = []
        for i, v in enumerate(values):
            px = cx + r * v * math.cos(angles[i])
            py = cy + r * v * math.sin(angles[i])
            points.append(f"{px},{py}")
        points_str = " ".join(points)

        # Data dots
        dots_svg = ""
        for i, v in enumerate(values):
            px = cx + r * v * math.cos(angles[i])
            py = cy + r * v * math.sin(angles[i])
            dots_svg += f'<circle cx="{px}" cy="{py}" r="4" fill="{_accent}" stroke="white" stroke-width="1.5"/>'

        radar_svg = f"""
        <svg class="radar-svg" width="320" height="320" viewBox="0 0 320 320">
            {grid_svg}
            {axis_svg}
            <polygon points="{points_str}" fill="{_accent}" fill-opacity="0.15" stroke="{_accent}" stroke-width="2"/>
            {dots_svg}
        </svg>
        """

        # Show radar + key stats side by side
        col_radar, col_stats = st.columns([1, 1])
        with col_radar:
            st.markdown(radar_svg, unsafe_allow_html=True)
        with col_stats:
            wrs = selected_row["WRS"]
            acc = selected_row["Accuracy"]
            hr = selected_row["Halulu Rate"]
            tdr = selected_row["TDR"]
            sev = selected_row["Avg Severity"]
            cost = selected_row["Cost/100q"]

            st.markdown(f"""
**{selected_model}**

| Metric | Value |
|--------|-------|
| WRS | **{wrs:.1f}** / 100 |
| Accuracy | {acc:.1%} |
| Halulu Rate | {hr:.1%} |
| Trap Detection | {tdr:.0%} |
| Avg Severity | {sev:.1f} / 5 |
| Cost / 100q | {cost} |
""")

# ── 4. Cost Efficiency ───────────────────────────────────────────────

st.markdown('<div class="section-header">Cost Efficiency</div>', unsafe_allow_html=True)
st.markdown("WRS score per dollar spent — which model gives the best reliability for your budget?")

if leaderboard:
    eff_rows = []
    for r in leaderboard:
        cost = r.get("_cost")
        if cost and cost > 0:
            ratio = r["_wrs"] / cost
            eff_rows.append({
                "Model": r["Model"],
                "WRS": f"{r['_wrs']:.1f}",
                "Cost/100q": r["Cost/100q"],
                "WRS per $1": f"{ratio:.0f}",
            })
    if eff_rows:
        eff_rows.sort(key=lambda x: float(x["WRS per $1"]), reverse=True)
        eff_df = pd.DataFrame(eff_rows)
        eff_df.insert(0, "Rank", range(1, len(eff_df) + 1))
        st.dataframe(eff_df, use_container_width=True, hide_index=True)

# ── 5. Reality Stress Tests ───────────────────────────────────────────

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

# ── 6. Benchmark Methodology ─────────────────────────────────────────

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
**Key Metrics**

- **WRS** (Weighted Reliability Score) — severity-weighted composite score (0-100)
- **TDR** (Trap Detection Rate) — % of false premise + citation traps caught
- **Severity** (0-5) — how dangerous a hallucination is (5 = fabricated citations)

**Grade Definitions**

- ✅ **Correct** — factually accurate
- ❌ **Incorrect** — wrong but not fabricated
- 😵‍💫 **Hallucinated** — confidently fabricated
- ❓ **Uncertain** — vague/hedging response
- 🤷 **Refused** — declined to answer

**Dataset:** {len(questions)} public + 12 hidden scoring questions.
""")

# ── Footer ────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="site-footer">
    😵‍💫 <strong>Halulu</strong> — AI Reliability Index<br>
    Benchmarking hallucination rates so you don't have to trust blindly.<br>
    <a href="https://github.com/jfrench29/halulu" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
