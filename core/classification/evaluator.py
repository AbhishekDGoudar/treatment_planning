"""
Evaluation metrics for multi-label classification.
"""
from typing import Dict, List

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    theme_names: List[str],
    threshold: float = 0.5,
    device: torch.device = None,
    model_type: str = "textcnn",
) -> Dict:
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.eval().to(device)
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in loader:
            if model_type == "bert":
                inputs, labels = batch
                inputs = {k: v.to(device) for k, v in inputs.items()}
                logits = model(**inputs)
            else:
                inputs, labels = batch
                inputs = inputs.to(device)
                logits = model(inputs)

            preds = (torch.sigmoid(logits) >= threshold).cpu().numpy()
            all_preds.append(preds)
            all_labels.append(labels.numpy())

    all_preds = np.vstack(all_preds)
    all_labels = np.vstack(all_labels)

    per_label = []
    for i, name in enumerate(theme_names):
        per_label.append({
            "Theme": name,
            "Precision": round(precision_score(all_labels[:, i], all_preds[:, i], zero_division=0), 3),
            "Recall":    round(recall_score(all_labels[:, i], all_preds[:, i], zero_division=0), 3),
            "F1":        round(f1_score(all_labels[:, i], all_preds[:, i], zero_division=0), 3),
            "Support":   int(all_labels[:, i].sum()),
        })

    metrics_df = pd.DataFrame(per_label)

    summary = {
        "micro_f1":  round(f1_score(all_labels, all_preds, average="micro",  zero_division=0), 4),
        "macro_f1":  round(f1_score(all_labels, all_preds, average="macro",  zero_division=0), 4),
        "micro_p":   round(precision_score(all_labels, all_preds, average="micro",  zero_division=0), 4),
        "micro_r":   round(recall_score(all_labels, all_preds, average="micro",  zero_division=0), 4),
    }

    return {"per_label": metrics_df, "summary": summary, "preds": all_preds, "labels": all_labels}


def predict_text(
    text: str,
    model: nn.Module,
    theme_names: List[str],
    threshold: float = 0.5,
    device: torch.device = None,
    model_type: str = "textcnn",
    vocab: dict = None,
    max_len: int = 256,
    tokenizer=None,
) -> pd.DataFrame:
    """Run inference on a single text string. Returns DataFrame of theme predictions."""
    from core.classification.dataset import encode_text

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.eval().to(device)

    with torch.no_grad():
        if model_type == "bert" and tokenizer is not None:
            enc = tokenizer([text], padding="max_length", truncation=True, max_length=max_len, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc)
        else:
            ids = encode_text(text, vocab, max_len)
            x = torch.tensor([ids], dtype=torch.long).to(device)
            logits = model(x)

        probs = torch.sigmoid(logits).squeeze().cpu().numpy()

    results = []
    for name, prob in zip(theme_names, probs):
        results.append({
            "Theme": name,
            "Confidence": round(float(prob), 3),
            "Predicted": "Yes" if prob >= threshold else "No",
        })
    return pd.DataFrame(results).sort_values("Confidence", ascending=False)
