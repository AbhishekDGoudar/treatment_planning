"""
Page 7 — Claude Sonnet 4.6 Multi-label Classification

Classifies waiver text against the 20 predefined themes using the Claude API
with prompt caching on the static theme definitions.
"""
import anthropic
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os

from core.classification.claude_classifier import (
    classify_dataframe,
    classify_text,
    estimate_cost,
)
from core.thematic.themes import PREDEFINED_THEMES

st.set_page_config(page_title="Claude Classification", layout="wide")
st.title("Claude Sonnet 4.6 — Theme Classification")
st.write(
    "Classify waiver text against all 20 themes using the Claude API. "
    "The theme definitions are prompt-cached, so only the waiver text is billed at full rate after the first call."
)

# ── Sidebar: API key & settings ───────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Set ANTHROPIC_API_KEY in your environment or enter it here.",
    )
    threshold = st.slider("Prediction threshold", 0.1, 0.9, 0.5, 0.05)

    st.divider()
    st.caption("Model: claude-sonnet-4-6")
    st.caption("Input: $3.00 / MTok · Output: $15.00 / MTok")
    st.caption("Cache read: $0.30 / MTok")


def get_client() -> anthropic.Anthropic | None:
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
        return None
    return anthropic.Anthropic(api_key=api_key)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_single, tab_batch = st.tabs(["Classify Text", "Batch — Excel File"])


# ── Tab 1: Single text ────────────────────────────────────────────────────────
with tab_single:
    st.subheader("Classify a single text passage")

    sample = (
        "The person-centered planning process is driven by the individual and their family, "
        "with support from the interdisciplinary team. The team coordinates with child-serving "
        "agencies and community-based natural supports to develop a plan that reflects the "
        "individual's strengths and goals across multiple life domains."
    )
    text_input = st.text_area("Waiver section text", value=sample, height=180)

    if st.button("Classify", type="primary", key="btn_single"):
        client = get_client()
        if client and text_input.strip():
            with st.spinner("Calling Claude API…"):
                try:
                    result_df, usage = classify_text(
                        text_input,
                        client,
                        themes=PREDEFINED_THEMES,
                        threshold=threshold,
                    )
                except anthropic.AuthenticationError:
                    st.error("Invalid API key.")
                    st.stop()
                except anthropic.RateLimitError:
                    st.error("Rate limit hit — wait a moment and retry.")
                    st.stop()
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.stop()

            col_res, col_chart = st.columns([1, 1])

            with col_res:
                st.subheader("Predictions")
                predicted_yes = result_df[result_df["Predicted"] == "Yes"]
                st.dataframe(
                    result_df.style.applymap(
                        lambda v: "background-color: #d4edda" if v == "Yes" else "",
                        subset=["Predicted"],
                    ),
                    use_container_width=True,
                    height=500,
                )

            with col_chart:
                st.subheader("Confidence scores")
                fig = go.Figure(go.Bar(
                    x=result_df["Confidence"],
                    y=result_df["Theme"],
                    orientation="h",
                    marker_color=[
                        "#28a745" if p == "Yes" else "#6c757d"
                        for p in result_df["Predicted"]
                    ],
                ))
                fig.add_vline(x=threshold, line_dash="dash", line_color="red",
                              annotation_text=f"threshold={threshold}")
                fig.update_layout(
                    height=550,
                    xaxis_range=[0, 1],
                    yaxis={"autorange": "reversed"},
                    margin=dict(l=10, r=10, t=30, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Token usage
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Input tokens", usage["input_tokens"])
            c2.metric("Output tokens", usage["output_tokens"])
            c3.metric("Cache write", usage["cache_creation_input_tokens"])
            c4.metric("Cache read", usage["cache_read_input_tokens"])

            cost = (
                usage["input_tokens"] * 3.00 / 1_000_000
                + usage["output_tokens"] * 15.00 / 1_000_000
                + usage["cache_creation_input_tokens"] * 3.75 / 1_000_000
                + usage["cache_read_input_tokens"] * 0.30 / 1_000_000
            )
            st.caption(f"Estimated cost for this call: **${cost:.5f}**")

            themes_found = ", ".join(predicted_yes["Theme"].tolist()) if len(predicted_yes) else "None"
            st.success(f"**{len(predicted_yes)} themes detected:** {themes_found}")


# ── Tab 2: Batch from Excel ───────────────────────────────────────────────────
with tab_batch:
    st.subheader("Batch classify from the SED Waiver Excel file")

    uploaded_file = st.file_uploader("Upload Waiver Dataset (.xlsx)", type=["xlsx"])
    if not uploaded_file:
        st.info("Please upload your Excel file to begin.")
        st.stop()

    df_excel = pd.read_excel(uploaded_file, sheet_name="Data Master")

    # Show dataset info
    st.info(f"Dataset loaded: **{len(df_excel)} rows**, {len(df_excel.columns)} columns")

    # Column selector — pre-select the two richest D1/D2 columns
    text_columns = [c for c in df_excel.columns if df_excel[c].dtype == object
                    and df_excel[c].str.len().mean() > 200]

    DEFAULT_COLS = [
        "Service Plan Development Process (D1d)",
        "Service Plan Implementation and Monitoring. (D2a)",
    ]
    default_sel = [c for c in DEFAULT_COLS if c in text_columns]

    selected_col = st.selectbox(
        "Select column to classify",
        options=text_columns,
        index=text_columns.index(default_sel[0]) if default_sel else 0,
        help="Choose one text column per run. D1d and D2a have the richest content.",
    )

    # Row range
    n_rows = len(df_excel)
    row_start, row_end = st.slider(
        "Row range (0-indexed)",
        0, n_rows - 1, (0, min(9, n_rows - 1)),
        help="Limit to a subset for testing before running the full dataset.",
    )
    n_selected = row_end - row_start + 1

    # Cost estimate
    subset = df_excel.iloc[row_start:row_end + 1]
    avg_chars = int(subset[selected_col].dropna().astype(str).str.len().mean()) if len(subset) > 0 else 500
    est = estimate_cost(n_selected, avg_chars, len(PREDEFINED_THEMES))

    with st.expander("Cost & time estimate", expanded=True):
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("Estimated cost", f"${est['total_usd']:.4f}")
        ec2.metric("Calls", n_selected)
        ec3.metric("~Time (sequential)", f"{est['estimated_seconds_sequential']:.0f}s")
        st.caption(
            f"Avg {avg_chars} chars/text · "
            f"~{est['avg_input_text_tokens']} input tokens + "
            f"~{est['avg_output_tokens']} output tokens per call"
        )

    if st.button("Run Classification", type="primary", key="btn_batch"):
        client = get_client()
        if not client:
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()
        usage_placeholder = st.empty()

        def update_progress(done: int, total: int):
            progress_bar.progress(done / total)
            status_text.text(f"Processing row {done} / {total}…")

        df_subset = subset.copy()

        with st.spinner("Classifying…"):
            try:
                results_df, total_usage = classify_dataframe(
                    df_subset,
                    text_column=selected_col,
                    client=client,
                    id_column="Application Number",
                    themes=PREDEFINED_THEMES,
                    threshold=threshold,
                    progress_callback=update_progress,
                )
            except anthropic.AuthenticationError:
                st.error("Invalid API key.")
                st.stop()
            except anthropic.RateLimitError:
                st.error("Rate limit hit — consider running a smaller batch.")
                st.stop()
            except Exception as e:
                st.error(f"Error during batch: {e}")
                st.stop()

        progress_bar.progress(1.0)
        status_text.text("Done!")

        # Results
        st.subheader("Results")
        st.dataframe(results_df, use_container_width=True, height=400)

        # Download
        csv_bytes = results_df.to_csv(index=False).encode()
        st.download_button(
            "Download results CSV",
            data=csv_bytes,
            file_name=f"claude_classification_{selected_col[:20].strip()}.csv",
            mime="text/csv",
        )

        # Aggregated usage
        st.divider()
        st.subheader("Token usage summary")
        u1, u2, u3, u4, u5 = st.columns(5)
        u1.metric("Total input tokens", f"{total_usage['input_tokens']:,}")
        u2.metric("Total output tokens", f"{total_usage['output_tokens']:,}")
        u3.metric("Cache writes", f"{total_usage['cache_creation_input_tokens']:,}")
        u4.metric("Cache reads", f"{total_usage['cache_read_input_tokens']:,}")
        u5.metric("API calls made", total_usage["calls"])

        actual_cost = (
            total_usage["input_tokens"] * 3.00 / 1_000_000
            + total_usage["output_tokens"] * 15.00 / 1_000_000
            + total_usage["cache_creation_input_tokens"] * 3.75 / 1_000_000
            + total_usage["cache_read_input_tokens"] * 0.30 / 1_000_000
        )
        st.metric("Actual cost", f"${actual_cost:.5f}")

        # Theme frequency chart
        if len(results_df) > 0 and "Predicted" in results_df.columns:
            freq = (
                results_df[results_df["Predicted"] == "Yes"]
                .groupby("Theme")
                .size()
                .sort_values(ascending=False)
                .reset_index(name="Count")
            )
            if len(freq) > 0:
                st.subheader("Theme frequency across classified rows")
                fig2 = go.Figure(go.Bar(
                    x=freq["Count"],
                    y=freq["Theme"],
                    orientation="h",
                    marker_color="#28a745",
                ))
                fig2.update_layout(
                    height=500,
                    yaxis={"autorange": "reversed"},
                    xaxis_title="Number of waivers",
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig2, use_container_width=True)
