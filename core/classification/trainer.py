"""
Shared training loop for TextCNN and BERT multi-label classifiers.
Returns epoch-level history dicts for loss and val-F1.
"""
from typing import Callable, Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_epochs: int = 10,
    lr: float = 2e-4,
    class_weights: Optional[torch.Tensor] = None,
    device: Optional[torch.device] = None,
    epoch_callback: Optional[Callable[[int, float, float], None]] = None,
    model_type: str = "textcnn",  # "textcnn" or "bert"
) -> Dict[str, List[float]]:
    """
    Train model and return history: {train_loss, val_loss, val_f1}.
    epoch_callback(epoch, train_loss, val_f1) is called after each epoch.
    """
    from sklearn.metrics import f1_score
    import numpy as np

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = model.to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=class_weights.to(device) if class_weights is not None else None)

    # Lower LR for BERT to avoid catastrophic forgetting
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)

    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": [], "val_f1": []}

    for epoch in range(num_epochs):
        # ── Training ──────────────────────────────────────────────────────────
        model.train()
        train_losses = []
        for batch in train_loader:
            optimizer.zero_grad()
            if model_type == "bert":
                inputs, labels = batch
                inputs = {k: v.to(device) for k, v in inputs.items()}
                labels = labels.to(device)
                logits = model(**inputs)
            else:
                inputs, labels = batch
                inputs = inputs.to(device)
                labels = labels.to(device)
                logits = model(inputs)

            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())

        # ── Validation ────────────────────────────────────────────────────────
        model.eval()
        val_losses, all_preds, all_labels = [], [], []
        with torch.no_grad():
            for batch in val_loader:
                if model_type == "bert":
                    inputs, labels = batch
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    labels = labels.to(device)
                    logits = model(**inputs)
                else:
                    inputs, labels = batch
                    inputs = inputs.to(device)
                    labels = labels.to(device)
                    logits = model(inputs)

                val_losses.append(criterion(logits, labels).item())
                preds = (torch.sigmoid(logits) >= 0.5).cpu().numpy()
                all_preds.append(preds)
                all_labels.append(labels.cpu().numpy())

        all_preds = np.vstack(all_preds)
        all_labels = np.vstack(all_labels)
        val_f1 = f1_score(all_labels, all_preds, average="micro", zero_division=0)

        t_loss = float(np.mean(train_losses))
        v_loss = float(np.mean(val_losses))

        history["train_loss"].append(t_loss)
        history["val_loss"].append(v_loss)
        history["val_f1"].append(val_f1)

        if epoch_callback:
            epoch_callback(epoch + 1, t_loss, val_f1)

    return history


def save_checkpoint(model: nn.Module, path: str, meta: dict) -> None:
    torch.save({"model_state": model.state_dict(), "meta": meta}, path)


def load_checkpoint(model: nn.Module, path: str) -> dict:
    ckpt = torch.load(path, map_location="cpu")
    model.load_state_dict(ckpt["model_state"])
    return ckpt["meta"]
