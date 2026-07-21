"""
Page 8 — MAXQDA RAG Coder

Retrieval-augmented coding pipeline:
  1. Knowledge Base tab — embed coded_segments.jsonl into LanceDB
  2. Code Text tab — retrieve k-nearest examples → Claude predicts codes
"""
import os
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from core.rag.kb_indexer import (
    build_index,
    drop_index,
    get_store,
    index_status,
    load_segments,
    retrieve_examples,
)
from core.rag.rag_coder import load_codebook, predict_codes, predict_codes_dataframe, theme_codes

st.set_page_config(page_title="MAXQDA RAG Coder", layout="wide")
st.title("MAXQDA RAG Coder")
st.write(
    "Retrieval-augmented qualitative coding: retrieve human-coded examples from "
    "the knowledge base, then use Claude to predict which codes apply to new text."
)

KB_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"
DEFAULT_SEGMENTS_PATH = KB_DIR / "coded_segments.jsonl"
DEFAULT_CODEBOOK_PATH = KB_DIR / "codebook.csv"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Set ANTHROPIC_API_KEY in your environment or enter it here.",
    )

    embedding_provider = st.selectbox(
        "Embedding provider",
        ["OLLAMA", "OPENAI"],
        help="Must match the provider used when the index was built.",
    )

    k_examples = st.slider(
        "Retrieved examples (k)",
        min_value=1, max_value=10, value=5,
        help="Number of similar coded segments to inject as few-shot context.",
    )

    threshold = st.slider(
        "Confidence threshold",
        min_value=0.1, max_value=0.9, value=0.5, step=0.05,
        help="Predictions below this confidence are filtered out.",
    )

    st.divider()
    st.caption("Model: claude-sonnet-4-6")
    st.caption("Input: $3.00/MTok · Output: $15.00/MTok")
    st.caption("Cache read: $0.30/MTok")


def get_client() -> anthropic.Anthropic | None:
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
        return None
    return anthropic.Anthropic(api_key=api_key)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_kb, tab_code, tab_batch = st.tabs(["Knowledge Base", "Code Text", "Batch — Excel"])


# ── Tab 1: Knowledge Base ─────────────────────────────────────────────────────
with tab_kb:
    st.subheader("Coded Segments Index")
    st.write(
        "The knowledge base embeds 1,386 human-coded segments from the 14-document "
        "MAXQDA Round-2 export into a LanceDB vector table. "
        "Build the index once; it persists between sessions."
    )

    status = index_status()

    if status["exists"]:
        st.success(
            f"Index is ready — **{status['row_count']:,} segments** indexed in LanceDB "
            f"(`coded_segments` table)."
        )
    else:
        st.warning("Index not built yet. Upload a JSONL file or use the repo default and click **Build Index**.")

    st.divider()

    # Source selection
    source_choice = st.radio(
        "Segments source",
        ["Use repo default (knowledge_base/coded_segments.jsonl)", "Upload JSONL"],
        horizontal=True,
    )

    segments_path = None
    uploaded_jsonl = None

    if source_choice.startswith("Use repo"):
        if DEFAULT_SEGMENTS_PATH.exists():
            st.info(f"Default file: `{DEFAULT_SEGMENTS_PATH}` — {DEFAULT_SEGMENTS_PATH.stat().st_size // 1024} KB")
            segments_path = DEFAULT_SEGMENTS_PATH
        else:
            st.error(f"Default JSONL not found at `{DEFAULT_SEGMENTS_PATH}`")
    else:
        uploaded_jsonl = st.file_uploader(
            "Upload coded_segments.jsonl",
            type=["jsonl", "json"],
            help="Regenerate from a new .qdpx export using knowledge_base/qdpx_extract.py",
        )

    col_build, col_rebuild = st.columns(2)

    with col_build:
        build_disabled = status["exists"] or (
            segments_path is None and uploaded_jsonl is None
        )
        if st.button("Build Index", type="primary", disabled=build_disabled):
            if uploaded_jsonl:
                import tempfile, json as _json
                with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
                    tmp.write(uploaded_jsonl.read())
                    segments_path = Path(tmp.name)

            with st.spinner("Loading segments…"):
                segs = load_segments(segments_path)
            st.write(f"Loaded **{len(segs)}** segments. Embedding now (this may take a few minutes)…")

            progress_bar = st.progress(0)

            def _cb(done, total):
                progress_bar.progress(done / total)

            with st.spinner("Embedding and indexing…"):
                n = build_index(segs, provider=embedding_provider, progress_callback=_cb)

            progress_bar.progress(1.0)
            st.success(f"Indexed **{n}** segments. Reload the page to confirm.")
            st.rerun()

    with col_rebuild:
        if st.button(
            "Rebuild Index",
            disabled=(segments_path is None and uploaded_jsonl is None),
            help="Drop the existing table and rebuild from scratch.",
        ):
            drop_index()
            st.info("Existing index dropped. Click **Build Index** to rebuild.")
            st.rerun()

    # Codebook preview
    st.divider()
    st.subheader("Codebook preview")
    if DEFAULT_CODEBOOK_PATH.exists():
        df_cb = load_codebook(str(DEFAULT_CODEBOOK_PATH))
        themes = theme_codes(df_cb)
        st.write(
            f"**{len(themes)} interpretive theme codes** (section-label codes excluded)."
        )
        st.dataframe(
            pd.DataFrame(themes)[["name", "path"]].rename(
                columns={"name": "Code", "path": "Hierarchy"}
            ),
            use_container_width=True,
            height=300,
        )
    else:
        st.warning(f"Codebook not found at `{DEFAULT_CODEBOOK_PATH}`")


# ── Tab 2: Code Text ──────────────────────────────────────────────────────────
with tab_code:
    st.subheader("Code a text span")

    status = index_status()
    if not status["exists"]:
        st.error("The knowledge base index is not built yet. Go to the **Knowledge Base** tab first.")
        st.stop()

    if not DEFAULT_CODEBOOK_PATH.exists():
        st.error(f"Codebook not found at `{DEFAULT_CODEBOOK_PATH}`")
        st.stop()

    sample_text = (
        "The wraparound facilitator coordinates with the family and the "
        "interdisciplinary team to develop an individualized plan of care that "
        "reflects the youth's strengths, cultural background, and long-term goals. "
        "Natural supports and community-based providers collaborate throughout."
    )
    input_text = st.text_area(
        "Text span to code",
        value=sample_text,
        height=160,
        help="Paste any text segment from a waiver document here.",
    )

    if st.button("Retrieve Examples & Predict Codes", type="primary"):
        if not input_text.strip():
            st.warning("Enter a text span to code.")
            st.stop()

        client = get_client()
        if not client:
            st.stop()

        # Step 1: retrieve
        with st.spinner(f"Retrieving {k_examples} nearest coded examples…"):
            try:
                store = get_store(provider=embedding_provider)
                examples = retrieve_examples(input_text, store, k=k_examples)
            except Exception as e:
                st.error(f"Retrieval error: {e}")
                st.stop()

        # Step 2: predict
        with st.spinner("Calling Claude to predict codes…"):
            try:
                predictions, usage = predict_codes(
                    text=input_text,
                    examples=examples,
                    client=client,
                    codebook_path=str(DEFAULT_CODEBOOK_PATH),
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

        # ── Raw response debug ─────────────────────────────────────────────
        with st.expander("Raw API response (debug)", expanded=not predictions):
            st.text(usage.get("raw_response", "—"))

        # ── Results layout ─────────────────────────────────────────────────
        col_ex, col_pred = st.columns([1, 1])

        with col_ex:
            st.subheader(f"Retrieved Examples (k={k_examples})")
            if examples:
                rows = []
                for ex in examples:
                    rows.append({
                        "Sim": round(ex["score"], 3),
                        "Code": ex["code"],
                        "Document": ex["document"],
                        "Coder": ex["coder"],
                        "Text snippet": ex["text"][:120] + ("…" if len(ex["text"]) > 120 else ""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, height=320)
            else:
                st.info("No examples retrieved.")

        with col_pred:
            st.subheader("Predicted Codes")
            if predictions:
                pred_df = pd.DataFrame(predictions)[["code", "confidence", "rationale"]]
                pred_df.columns = ["Code", "Confidence", "Rationale"]
                pred_df = pred_df.sort_values("Confidence", ascending=False)
                st.dataframe(
                    pred_df.style.applymap(
                        lambda v: (
                            "background-color: #d4edda" if v >= 0.7
                            else "background-color: #fff3cd" if v >= 0.5
                            else "background-color: #f8d7da"
                        ),
                        subset=["Confidence"],
                    ),
                    use_container_width=True,
                    height=320,
                )
                st.success(
                    f"**{len(predictions)} code(s) predicted** above threshold {threshold}: "
                    + ", ".join(f'*{p["code"]}*' for p in predictions)
                )
            else:
                st.info(f"No codes predicted above confidence threshold {threshold}.")

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


# ── Tab 3: Batch from Excel ───────────────────────────────────────────────────
with tab_batch:
    st.subheader("Batch code from the SED Waiver Excel file")

    status = index_status()
    if not status["exists"]:
        st.error("Build the knowledge base index first (Knowledge Base tab).")
        st.stop()

    uploaded_file = st.file_uploader("Upload Waiver Dataset (.xlsx)", type=["xlsx"])
    if not uploaded_file:
        st.info("Please upload your Excel file to begin.")
        st.stop()

    df_excel = pd.read_excel(uploaded_file, sheet_name="Data Master")
    st.info(f"Dataset loaded: **{len(df_excel)} rows**, {len(df_excel.columns)} columns")

    # Text column selector — same filter as page 7
    text_columns = [
        c for c in df_excel.columns
        if df_excel[c].dtype == object and df_excel[c].str.len().mean() > 200
    ]

    DEFAULT_COLS = [
        "Service Plan Development Process (D1d)",
        "Service Plan Implementation and Monitoring. (D2a)",
    ]
    default_sel = [c for c in DEFAULT_COLS if c in text_columns]

    selected_col = st.selectbox(
        "Select column to code",
        options=text_columns,
        index=text_columns.index(default_sel[0]) if default_sel else 0,
        help="One column per run. D1d and D2a carry the most codeable content.",
    )

    # Row range
    n_rows = len(df_excel)
    row_start, row_end = st.slider(
        "Row range (0-indexed)",
        0, n_rows - 1, (0, min(9, n_rows - 1)),
        help="Test on a small subset before running all 139 rows.",
    )
    n_selected = row_end - row_start + 1
    subset = df_excel.iloc[row_start : row_end + 1].copy()

    # Cost estimate
    avg_chars = int(subset[selected_col].dropna().astype(str).str.len().mean()) if n_selected > 0 else 500
    avg_tokens = avg_chars // 4
    system_tokens = 2010
    example_tokens = k_examples * 50
    output_tokens = 2500
    cost_per_call = (
        system_tokens * 0.30 / 1_000_000          # cache read
        + (avg_tokens + example_tokens) * 3.00 / 1_000_000
        + output_tokens * 15.00 / 1_000_000
    )
    est_total = cost_per_call * n_selected
    est_secs = n_selected * 5

    with st.expander("Cost & time estimate", expanded=True):
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("Estimated cost", f"${est_total:.4f}")
        ec2.metric("Calls", n_selected)
        ec3.metric("~Time (sequential)", f"{est_secs}s")
        st.caption(
            f"Avg {avg_chars} chars/text (~{avg_tokens} tokens) · "
            f"k={k_examples} examples · threshold={threshold}"
        )

    if st.button("Run Batch Coding", type="primary", key="btn_batch"):
        client = get_client()
        if not client:
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(done: int, total: int):
            progress_bar.progress(done / total)
            status_text.text(f"Processing row {done} / {total}…")

        with st.spinner("Retrieving examples and coding…"):
            try:
                store = get_store(provider=embedding_provider)
                results_df, total_usage = predict_codes_dataframe(
                    df=subset,
                    text_column=selected_col,
                    client=client,
                    codebook_path=str(DEFAULT_CODEBOOK_PATH),
                    store=store,
                    id_column="Application Number",
                    k=k_examples,
                    threshold=threshold,
                    progress_callback=update_progress,
                )
            except anthropic.AuthenticationError:
                st.error("Invalid API key.")
                st.stop()
            except anthropic.RateLimitError:
                st.error("Rate limit hit — try a smaller row range.")
                st.stop()
            except Exception as e:
                st.error(f"Error during batch: {e}")
                st.stop()

        progress_bar.progress(1.0)
        status_text.text("Done!")

        st.subheader("Results")
        if results_df.empty:
            st.warning("No predictions returned. Check the raw API response below to diagnose.")
            with st.expander("Raw API response (last call)", expanded=True):
                st.text(total_usage.get("last_raw_response", "—"))
        else:
            st.dataframe(results_df, use_container_width=True, height=400)

        csv_bytes = results_df.to_csv(index=False).encode()
        st.download_button(
            "Download results CSV",
            data=csv_bytes,
            file_name=f"rag_coded_{selected_col[:20].strip()}.csv",
            mime="text/csv",
        )

        # Code frequency chart
        if len(results_df) > 0 and "Code" in results_df.columns:
            import plotly.graph_objects as go
            freq = (
                results_df.groupby("Code")
                .size()
                .sort_values(ascending=False)
                .reset_index(name="Count")
            )
            st.subheader("Code frequency")
            fig = go.Figure(go.Bar(
                x=freq["Count"], y=freq["Code"],
                orientation="h", marker_color="#5c85d6",
            ))
            fig.update_layout(
                height=max(400, len(freq) * 22),
                yaxis={"autorange": "reversed"},
                xaxis_title="Waivers coded",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Token usage summary
        st.divider()
        u1, u2, u3, u4, u5 = st.columns(5)
        u1.metric("Input tokens", f"{total_usage['input_tokens']:,}")
        u2.metric("Output tokens", f"{total_usage['output_tokens']:,}")
        u3.metric("Cache writes", f"{total_usage['cache_creation_input_tokens']:,}")
        u4.metric("Cache reads", f"{total_usage['cache_read_input_tokens']:,}")
        u5.metric("API calls", total_usage["calls"])

        actual_cost = (
            total_usage["input_tokens"] * 3.00 / 1_000_000
            + total_usage["output_tokens"] * 15.00 / 1_000_000
            + total_usage["cache_creation_input_tokens"] * 3.75 / 1_000_000
            + total_usage["cache_read_input_tokens"] * 0.30 / 1_000_000
        )
        st.metric("Actual cost", f"${actual_cost:.5f}")
