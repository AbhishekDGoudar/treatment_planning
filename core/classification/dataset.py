"""
Data loading and preprocessing for multi-label waiver section classification.

Expects a CSV with columns:
  - text       : raw section text
  - waiver_id  : identifier
  - section    : section name
  - <theme_1>  : 0/1 binary label
  - <theme_2>  : 0/1 binary label
  - ...
"""
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


# ── Vocabulary (for TextCNN) ──────────────────────────────────────────────────

PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
PAD_IDX = 0
UNK_IDX = 1


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def build_vocab(texts: List[str], min_freq: int = 1) -> Dict[str, int]:
    counter: Counter = Counter()
    for t in texts:
        counter.update(tokenize(t))
    vocab = {PAD_TOKEN: PAD_IDX, UNK_TOKEN: UNK_IDX}
    for word, freq in counter.items():
        if freq >= min_freq:
            vocab[word] = len(vocab)
    return vocab


def encode_text(text: str, vocab: Dict[str, int], max_len: int) -> List[int]:
    tokens = tokenize(text)[:max_len]
    ids = [vocab.get(t, UNK_IDX) for t in tokens]
    # Pad to max_len
    ids += [PAD_IDX] * (max_len - len(ids))
    return ids


# ── PyTorch Datasets ──────────────────────────────────────────────────────────

class WaiverTextCNNDataset(Dataset):
    def __init__(
        self,
        texts: List[str],
        labels: np.ndarray,
        vocab: Dict[str, int],
        max_len: int = 256,
    ):
        self.encodings = [encode_text(t, vocab, max_len) for t in texts]
        self.labels = labels.astype(np.float32)

    def __len__(self) -> int:
        return len(self.encodings)

    def __getitem__(self, idx: int):
        return (
            torch.tensor(self.encodings[idx], dtype=torch.long),
            torch.tensor(self.labels[idx], dtype=torch.float),
        )


class WaiverBERTDataset(Dataset):
    def __init__(
        self,
        texts: List[str],
        labels: np.ndarray,
        tokenizer,
        max_len: int = 256,
    ):
        self.encodings = tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=max_len,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.float)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        return (
            {k: v[idx] for k, v in self.encodings.items()},
            self.labels[idx],
        )


# ── Loader ────────────────────────────────────────────────────────────────────

def load_labeled_csv(
    path_or_df,
    theme_names: List[str],
    test_size: float = 0.15,
    val_size: float = 0.10,
    min_vocab_freq: int = 1,
    text_col: str = "text",
    random_state: int = 42,
) -> dict:
    """
    Returns a dict with keys:
      texts_train, texts_val, texts_test,
      labels_train, labels_val, labels_test,
      vocab, theme_names, class_weights
    """
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(path_or_df) if isinstance(path_or_df, str) else path_or_df.copy()

    # Drop rows without text
    df = df[df[text_col].notna() & (df[text_col].str.strip() != "")]

    # Keep only theme columns that actually exist in the CSV
    available_themes = [t for t in theme_names if t in df.columns]
    texts = df[text_col].tolist()
    labels = df[available_themes].fillna(0).values.astype(np.float32)

    # Train / val / test split (stratify on first theme with variance if possible)
    texts_train, texts_test, labels_train, labels_test = train_test_split(
        texts, labels, test_size=test_size, random_state=random_state
    )
    val_relative = val_size / (1 - test_size)
    texts_train, texts_val, labels_train, labels_val = train_test_split(
        texts_train, labels_train, test_size=val_relative, random_state=random_state
    )

    vocab = build_vocab(texts_train, min_freq=min_vocab_freq)

    # Positive class weight per label (for BCEWithLogitsLoss pos_weight)
    pos_counts = labels_train.sum(axis=0) + 1e-6
    neg_counts = len(labels_train) - pos_counts + 1e-6
    class_weights = torch.tensor(neg_counts / pos_counts, dtype=torch.float)

    return {
        "texts_train": texts_train,
        "texts_val": texts_val,
        "texts_test": texts_test,
        "labels_train": labels_train,
        "labels_val": labels_val,
        "labels_test": labels_test,
        "vocab": vocab,
        "theme_names": available_themes,
        "class_weights": class_weights,
        "num_labels": len(available_themes),
    }
