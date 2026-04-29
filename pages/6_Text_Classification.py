"""
Page 6 — Multi-label Text Classification (TextCNN & BERT)

Workflow:
  1. Upload the labeled CSV exported from Page 5 (Thematic Analysis)
  2. Choose a model (TextCNN or BERT), configure hyperparameters, and train
  3. Classify new waiver section text against all themes
  4. Compare TextCNN vs BERT side-by-side on test-set metrics
"""
import io
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Text Classification", layout="wide")
st.title("Multi-label Text Classification")
st.write(
    "Train TextCNN or BERT on the labeled dataset produced by the Thematic Analysis page, "
    "then classify new waiver section text."
)

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import torch
    from torch.utils.data import DataLoader
    TORCH_OK = True
except ImportError:
    TORCH_OK = False

try:
    from transformers import AutoTokenizer
    TRANSFORMERS_OK = True
except ImportError:
    TRANSFORMERS_OK = False

if not TORCH_OK:
    st.error(
        "**PyTorch is not installed.** Run the following in your project environment, then restart Streamlit:\n\n"
        "```\nuv add torch transformers\n```"
    )
    st.stop()

from core.classification.dataset import (
    WaiverBERTDataset,
    WaiverTextCNNDataset,
    load_labeled_csv,
)
from core.classification.evaluator import evaluate, predict_text
from core.classification.text_cnn import TextCNN
from core.classification.trainer import load_checkpoint, save_checkpoint, train_model
from core.thematic.themes import THEME_NAMES

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_train, tab_classify, tab_compare = st.tabs(["Train", "Classify", "Compare Models"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TRAIN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_train:
    st.subheader("Train a Multi-label Classifier")
    st.caption(
        "Upload the **Labeled Dataset CSV** exported from the Thematic Analysis page. "
        "Each row is one waiver section; columns are 0/1 theme labels."
    )

    uploaded_csv = st.file_uploader("Upload Labeled Dataset (.csv)", type=["csv"], key="train_csv")

    if not uploaded_csv:
        st.info("Upload the labeled_dataset.csv from the Thematic Analysis export to begin.")
        st.stop()

    df_raw = pd.read_csv(uploaded_csv)
    st.success(f"Loaded {len(df_raw)} rows.")

    # Detect theme columns (binary 0/1 int columns that match known themes)
    detected_themes = [c for c in df_raw.columns if c in THEME_NAMES]
    if not detected_themes:
        st.error("No theme columns found in the CSV. Make sure you exported from the Thematic Analysis page.")
        st.stop()

    st.caption(f"Detected {len(detected_themes)} theme labels: {', '.join(detected_themes)}")

    # ── Model & hyperparameter selection ──────────────────────────────────────
    st.markdown("---")
    st.subheader("Model Configuration")

    cfg_col1, cfg_col2 = st.columns(2)
    with cfg_col1:
        model_choice = st.selectbox("Model", ["TextCNN", "BERT (bert-base-uncased)"])
        num_epochs = st.slider("Epochs", 1, 30, 10)
        batch_size = st.selectbox("Batch size", [8, 16, 32], index=1)

    with cfg_col2:
        lr = st.select_slider(
            "Learning rate",
            options=[1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3],
            value=2e-4 if "TextCNN" in model_choice else 2e-5,
            format_func=lambda x: f"{x:.0e}",
        )
        threshold = st.slider("Prediction threshold", 0.1, 0.9, 0.5, 0.05)
        use_class_weights = st.checkbox("Use class weights (handles label imbalance)", value=True)

    if "TextCNN" in model_choice:
        with st.expander("TextCNN architecture"):
            embed_dim   = st.slider("Embedding dim", 64, 256, 128, 64)
            num_filters = st.slider("Filters per kernel", 64, 256, 128, 64)
            dropout     = st.slider("Dropout", 0.1, 0.7, 0.5, 0.1)
            max_len     = st.slider("Max token length", 64, 512, 256, 64)
    else:
        embed_dim = num_filters = dropout = None
        max_len = st.slider("Max token length (BERT)", 64, 512, 256, 64)
        if not TRANSFORMERS_OK:
            st.error("`transformers` not installed. Run `uv add transformers` then restart.")
            st.stop()

    st.markdown("---")

    if st.button("Start Training", type="primary"):
        is_bert = "BERT" in model_choice
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        st.caption(f"Using device: **{device}**")

        # ── Load & split data ─────────────────────────────────────────────────
        with st.spinner("Preparing dataset…"):
            data = load_labeled_csv(df_raw, detected_themes)

        # ── Build datasets & loaders ──────────────────────────────────────────
        if is_bert:
            bert_name = "bert-base-uncased"
            tokenizer = AutoTokenizer.from_pretrained(bert_name)
            train_ds = WaiverBERTDataset(data["texts_train"], data["labels_train"], tokenizer, max_len)
            val_ds   = WaiverBERTDataset(data["texts_val"],   data["labels_val"],   tokenizer, max_len)
            test_ds  = WaiverBERTDataset(data["texts_test"],  data["labels_test"],  tokenizer, max_len)
        else:
            train_ds = WaiverTextCNNDataset(data["texts_train"], data["labels_train"], data["vocab"], max_len)
            val_ds   = WaiverTextCNNDataset(data["texts_val"],   data["labels_val"],   data["vocab"], max_len)
            test_ds  = WaiverTextCNNDataset(data["texts_test"],  data["labels_test"],  data["vocab"], max_len)
            tokenizer = None

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader   = DataLoader(val_ds,   batch_size=batch_size)
        test_loader  = DataLoader(test_ds,  batch_size=batch_size)

        # ── Build model ───────────────────────────────────────────────────────
        num_labels = data["num_labels"]
        if is_bert:
            from core.classification.bert_classifier import BERTClassifier
            model = BERTClassifier(num_labels=num_labels, model_name=bert_name, dropout=dropout or 0.3)
        else:
            model = TextCNN(
                vocab_size=len(data["vocab"]),
                num_labels=num_labels,
                embed_dim=embed_dim,
                num_filters=num_filters,
                dropout=dropout,
            )

        class_weights = data["class_weights"] if use_class_weights else None

        # ── Training loop with live chart ─────────────────────────────────────
        st.subheader("Training Progress")
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        history = {"epoch": [], "train_loss": [], "val_loss": [], "val_f1": []}

        def on_epoch(epoch, train_loss, val_f1):
            history["epoch"].append(epoch)
            history["train_loss"].append(train_loss)
            history["val_f1"].append(val_f1)
            status_placeholder.text(
                f"Epoch {epoch}/{num_epochs} — train_loss: {train_loss:.4f}  val_F1: {val_f1:.4f}"
            )
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history["epoch"], y=history["train_loss"], name="Train Loss", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=history["epoch"], y=history["val_f1"],    name="Val F1 (micro)", mode="lines+markers", yaxis="y2"))
            fig.update_layout(
                xaxis_title="Epoch",
                yaxis=dict(title="Loss"),
                yaxis2=dict(title="F1", overlaying="y", side="right", range=[0, 1]),
                legend=dict(x=0.01, y=0.99),
                height=350,
                margin=dict(t=20),
            )
            chart_placeholder.plotly_chart(fig, use_container_width=True)

        raw_history = train_model(
            model, train_loader, val_loader,
            num_epochs=num_epochs,
            lr=lr,
            class_weights=class_weights,
            device=device,
            epoch_callback=on_epoch,
            model_type="bert" if is_bert else "textcnn",
        )

        # ── Test evaluation ───────────────────────────────────────────────────
        eval_results = evaluate(
            model, test_loader, detected_themes,
            threshold=threshold, device=device,
            model_type="bert" if is_bert else "textcnn",
        )

        st.success("Training complete!")
        st.subheader("Test Set Performance")
        s = eval_results["summary"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Micro F1",    s["micro_f1"])
        m2.metric("Macro F1",    s["macro_f1"])
        m3.metric("Micro P",     s["micro_p"])
        m4.metric("Micro R",     s["micro_r"])

        st.dataframe(
            eval_results["per_label"].style.background_gradient(
                subset=["F1"], cmap="YlOrRd", vmin=0, vmax=1
            ),
            use_container_width=True,
        )

        # ── Save checkpoint ───────────────────────────────────────────────────
        model_key = "bert" if is_bert else "textcnn"
        ckpt_path = os.path.join(MODELS_DIR, f"{model_key}_classifier.pt")
        meta = {
            "theme_names": detected_themes,
            "model_type": model_key,
            "vocab": data.get("vocab"),
            "max_len": max_len,
            "threshold": threshold,
        }
        save_checkpoint(model, ckpt_path, meta)

        # Store in session state for Classify tab
        st.session_state[f"{model_key}_model"] = model
        st.session_state[f"{model_key}_meta"] = meta
        if is_bert:
            st.session_state[f"{model_key}_tokenizer"] = tokenizer

        st.session_state[f"{model_key}_eval"] = eval_results
        st.caption(f"Checkpoint saved to `{ckpt_path}`")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CLASSIFY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_classify:
    st.subheader("Classify a Waiver Section")
    st.caption("Paste any waiver section text and get theme predictions from a trained model.")

    clf_model_choice = st.radio("Model to use:", ["TextCNN", "BERT"], horizontal=True)
    mk = "bert" if clf_model_choice == "BERT" else "textcnn"

    input_text = st.text_area("Paste section text:", height=200)
    clf_threshold = st.slider("Confidence threshold", 0.1, 0.9, 0.5, 0.05, key="clf_thresh")

    if st.button("Predict Themes", type="primary"):
        if not input_text.strip():
            st.warning("Enter some text to classify.")
        elif f"{mk}_model" not in st.session_state:
            st.warning(f"No trained {clf_model_choice} model found. Train one in the Train tab first.")
        else:
            model = st.session_state[f"{mk}_model"]
            meta  = st.session_state[f"{mk}_meta"]
            tokenizer = st.session_state.get(f"{mk}_tokenizer")
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            preds_df = predict_text(
                input_text, model, meta["theme_names"],
                threshold=clf_threshold, device=device,
                model_type=mk, vocab=meta.get("vocab"),
                max_len=meta["max_len"], tokenizer=tokenizer,
            )

            positive = preds_df[preds_df["Predicted"] == "Yes"]
            st.markdown(f"**{len(positive)} theme(s) detected:**")

            styled = preds_df.style.apply(
                lambda row: ["background-color: #1b4332; color: white" if row["Predicted"] == "Yes"
                             else "" for _ in row],
                axis=1,
            ).format({"Confidence": "{:.3f}"})
            st.dataframe(styled, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE MODELS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("TextCNN vs BERT — Side-by-side Comparison")

    has_textcnn = "textcnn_eval" in st.session_state
    has_bert    = "bert_eval"    in st.session_state

    if not has_textcnn and not has_bert:
        st.info("Train at least one model in the Train tab to see comparisons here.")
    else:
        # Summary metrics
        rows = []
        if has_textcnn:
            s = st.session_state["textcnn_eval"]["summary"]
            rows.append({"Model": "TextCNN", **s})
        if has_bert:
            s = st.session_state["bert_eval"]["summary"]
            rows.append({"Model": "BERT", **s})

        summary_df = pd.DataFrame(rows).set_index("Model")
        st.dataframe(summary_df.style.highlight_max(axis=0, color="#2e7d32"), use_container_width=True)

        # Per-label F1 bar chart
        st.markdown("---")
        st.subheader("Per-theme F1 Score")

        fig = go.Figure()
        if has_textcnn:
            pl = st.session_state["textcnn_eval"]["per_label"]
            fig.add_trace(go.Bar(x=pl["Theme"], y=pl["F1"], name="TextCNN"))
        if has_bert:
            pl = st.session_state["bert_eval"]["per_label"]
            fig.add_trace(go.Bar(x=pl["Theme"], y=pl["F1"], name="BERT"))

        fig.update_layout(
            barmode="group",
            xaxis_tickangle=-45,
            yaxis=dict(title="F1 Score", range=[0, 1]),
            height=420,
            legend=dict(x=0.01, y=0.99),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed per-label tables
        if has_textcnn and has_bert:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**TextCNN per-theme metrics**")
                st.dataframe(st.session_state["textcnn_eval"]["per_label"], use_container_width=True)
            with c2:
                st.markdown("**BERT per-theme metrics**")
                st.dataframe(st.session_state["bert_eval"]["per_label"], use_container_width=True)
        elif has_textcnn:
            st.dataframe(st.session_state["textcnn_eval"]["per_label"], use_container_width=True)
        else:
            st.dataframe(st.session_state["bert_eval"]["per_label"], use_container_width=True)
