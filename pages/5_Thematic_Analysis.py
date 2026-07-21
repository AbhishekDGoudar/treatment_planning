import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from core.thematic.coder import code_dataframe
from core.thematic.report import (
    build_labeled_dataset,
    build_section_theme_matrix,
    build_waiver_theme_matrix,
    get_evidence,
)
from core.thematic.themes import PREDEFINED_THEMES, THEME_NAMES
from core.rag.generator import GeneratorFactory
from core.ui.sidebar import render_sidebar_settings

st.set_page_config(page_title="Thematic Analysis", layout="wide")
st.title("Thematic Analysis — Automated MAXQDA-style Coding")
st.write(
    "Upload the waiver dataset, select sections and themes, then run automated coding. "
    "Each section of each waiver is coded against all themes using the LLM, "
    "producing evidence quotes and confidence scores — mirroring MAXQDA manual coding."
)

provider_choice, openai_key = render_sidebar_settings()

# ── THEME MANAGEMENT ──────────────────────────────────────────────────────────
with st.expander("Predefined Themes (click to edit)", expanded=False):
    st.caption(
        "One theme per line. Names must be consistent — changes here affect the coding run."
    )
    theme_text = st.text_area(
        "Active themes:",
        value="\n".join(THEME_NAMES),
        height=220,
        label_visibility="collapsed",
    )
    active_theme_names = [t.strip() for t in theme_text.split("\n") if t.strip()]
    active_themes = [t for t in PREDEFINED_THEMES if t.name in active_theme_names]
    # Preserve any custom names not in PREDEFINED_THEMES with a minimal Theme object
    from core.thematic.themes import Theme as _Theme
    predefined_set = {t.name for t in PREDEFINED_THEMES}
    for name in active_theme_names:
        if name not in predefined_set:
            active_themes.append(_Theme(name=name, description=name))
    st.caption(f"{len(active_themes)} themes active")

# ── FILE UPLOAD ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload Waiver Dataset (.xlsx)", type=["xlsx"])

if not uploaded_file:
    st.info("Upload your Excel waiver dataset to begin.")
    st.stop()

df = pd.read_excel(uploaded_file, sheet_name="Data Master")

text_cols = [
    c for c in df.columns
    if df[c].dtype == "object" and df[c].astype(str).str.len().mean() > 40
]
st.success(f"Loaded {len(df)} records — {len(text_cols)} text sections available for coding.")

# ── SELECTION ─────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    selected_sections = st.multiselect(
        "Sections to code:",
        text_cols,
        default=text_cols,
    )

with col_right:
    app_numbers = sorted(df["Application Number"].dropna().unique().tolist())
    selected_waivers = st.multiselect(
        "Waivers to analyze (empty = all):",
        app_numbers,
        default=[],
    )

analysis_df = (
    df[df["Application Number"].isin(selected_waivers)]
    if selected_waivers
    else df
)

st.caption(
    f"Scope: {len(analysis_df)} waivers × {len(selected_sections)} sections × "
    f"{len(active_themes)} themes = {len(analysis_df) * len(selected_sections)} LLM calls"
)

# ── RUN CODING ────────────────────────────────────────────────────────────────
if st.button("Run Thematic Coding", type="primary", disabled=not selected_sections):
    if provider_choice == "OPENAI" and not openai_key:
        st.warning("OpenAI selected but no API key provided.")
        st.stop()
    if provider_choice == "ANTHROPIC" and not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("Anthropic selected but no API key provided.")
        st.stop()

    generator = GeneratorFactory()
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def _update(p: float) -> None:
        progress_bar.progress(p)
        status_text.text(f"Coding… {p:.0%} complete")

    results = code_dataframe(
        analysis_df,
        selected_sections,
        active_themes,
        generator,
        progress_callback=_update,
    )

    st.session_state["ta_results"] = results
    st.session_state["ta_themes"] = [t.name for t in active_themes]
    st.session_state["ta_sections"] = selected_sections
    st.session_state["ta_df"] = analysis_df.copy()

    progress_bar.empty()
    status_text.success(f"Coding complete — {len(results)} waivers coded.")

# ── RESULTS ───────────────────────────────────────────────────────────────────
if "ta_results" not in st.session_state:
    st.stop()

results = st.session_state["ta_results"]
themes = st.session_state["ta_themes"]
sections = st.session_state["ta_sections"]
stored_df = st.session_state["ta_df"]

tab_heat, tab_drill, tab_export = st.tabs(
    ["Heatmap", "Section Drill-Down", "Export"]
)

# ── TAB 1: HEATMAP ────────────────────────────────────────────────────────────
with tab_heat:
    st.subheader("Waiver × Theme Heatmap")
    st.caption("Cell = highest confidence score for that theme across all coded sections of that waiver.")

    matrix = build_waiver_theme_matrix(results, themes)

    view = st.radio(
        "View as:", ["Interactive heatmap", "Styled table"], horizontal=True
    )

    if view == "Interactive heatmap":
        fig = px.imshow(
            matrix,
            color_continuous_scale="YlOrRd",
            zmin=0,
            zmax=1,
            aspect="auto",
            labels={"color": "Confidence"},
        )
        fig.update_layout(
            height=max(400, len(matrix) * 30 + 150),
            xaxis_tickangle=-45,
            margin=dict(l=160, r=20, t=40, b=120),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        styled = matrix.style.background_gradient(cmap="YlOrRd", vmin=0, vmax=1).format("{:.2f}")
        st.dataframe(styled, use_container_width=True)

    # Summary: theme prevalence across waivers
    st.markdown("---")
    st.subheader("Theme Prevalence (% of waivers where theme applies)")
    threshold = st.slider("Confidence threshold:", 0.0, 1.0, 0.5, 0.05)
    prevalence = (matrix >= threshold).sum() / len(matrix) * 100
    prevalence_df = prevalence.reset_index()
    prevalence_df.columns = ["Theme", "% Waivers"]
    prevalence_df = prevalence_df.sort_values("% Waivers", ascending=False)
    fig2 = px.bar(
        prevalence_df,
        x="Theme",
        y="% Waivers",
        color="% Waivers",
        color_continuous_scale="YlOrRd",
        range_color=[0, 100],
    )
    fig2.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ── TAB 2: SECTION DRILL-DOWN ─────────────────────────────────────────────────
with tab_drill:
    st.subheader("Section-Level Drill-Down")

    waiver_ids = list(results.keys())
    d_col1, d_col2 = st.columns(2)
    selected_waiver = d_col1.selectbox("Select Waiver:", waiver_ids)
    selected_theme = d_col2.selectbox("Select Theme:", themes)

    if selected_waiver and selected_theme:
        # Section × theme matrix for this waiver (all themes)
        sec_matrix = build_section_theme_matrix(results, selected_waiver, themes)

        st.markdown(f"**Section × Theme matrix for waiver `{selected_waiver}`**")
        fig3 = px.imshow(
            sec_matrix,
            color_continuous_scale="YlOrRd",
            zmin=0,
            zmax=1,
            aspect="auto",
            labels={"color": "Confidence"},
        )
        fig3.update_layout(
            height=max(300, len(sec_matrix) * 40 + 100),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Evidence quotes for selected theme
        st.markdown(f"---")
        st.markdown(f"**Evidence quotes for theme: `{selected_theme}`**")
        evidence = get_evidence(results, selected_waiver, selected_theme)

        if evidence:
            for e in evidence:
                section_label = e["section"].replace("_", " ")
                with st.expander(
                    f"Section: {section_label}  —  confidence: {e['confidence']:.2f}",
                    expanded=True,
                ):
                    st.markdown(
                        f"""
                        <div style='background:#1e3a2f;border-left:4px solid #2e7d32;
                                    padding:10px 14px;border-radius:6px;font-family:serif;
                                    color:#e8f5e9;font-size:0.95em;line-height:1.6'>
                        {e["evidence"]}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info(f"No evidence found for **{selected_theme}** in waiver **{selected_waiver}**.")

        # Raw section texts for reference
        st.markdown("---")
        with st.expander("View raw section texts for this waiver"):
            waiver_row = stored_df[
                stored_df["Application Number"].astype(str) == selected_waiver
            ]
            if not waiver_row.empty:
                row = waiver_row.iloc[0]
                for col in sections:
                    st.markdown(f"**{col.replace('_', ' ')}**")
                    st.text(str(row.get(col, "N/A")))
                    st.divider()

# ── TAB 3: EXPORT ─────────────────────────────────────────────────────────────
with tab_export:
    st.subheader("Export Coding Results")

    col_a, col_b, col_c = st.columns(3)

    # Full coding results as JSON
    with col_a:
        st.markdown("**Full Coding (JSON)**")
        st.caption("Complete coding with evidence and confidence for every (waiver, section, theme).")
        st.download_button(
            "Download JSON",
            data=json.dumps(results, indent=2),
            file_name="thematic_coding_results.json",
            mime="application/json",
        )

    # Heatmap matrix as CSV
    with col_b:
        st.markdown("**Theme Matrix (CSV)**")
        st.caption("Waiver × theme confidence matrix — import into Excel or MAXQDA.")
        matrix_csv = build_waiver_theme_matrix(results, themes).to_csv()
        st.download_button(
            "Download CSV",
            data=matrix_csv,
            file_name="theme_matrix.csv",
            mime="text/csv",
        )

    # Labeled dataset for classification models
    with col_c:
        st.markdown("**Labeled Dataset (CSV)**")
        st.caption(
            "One row per (waiver, section) with raw text and binary theme columns. "
            "Use this as training data for TextCNN / BERT classification."
        )
        labeled_df = build_labeled_dataset(results, stored_df, sections, themes)
        st.download_button(
            "Download Labeled Dataset",
            data=labeled_df.to_csv(index=False),
            file_name="labeled_dataset.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.subheader("Preview: Labeled Dataset")
    labeled_df = build_labeled_dataset(results, stored_df, sections, themes)
    st.dataframe(labeled_df[["waiver_id", "section", "themes"]].head(20), use_container_width=True)
    st.caption(f"{len(labeled_df)} rows total — {labeled_df['themes'].str.count('|').add(1).where(labeled_df['themes'] != '').fillna(0).astype(int).sum()} theme assignments across all sections.")
