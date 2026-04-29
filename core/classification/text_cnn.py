"""
TextCNN for multi-label classification of waiver section text.

Architecture (Kim 2014):
  Embedding → parallel conv filters (kernel sizes 2,3,4) →
  max-over-time pooling → concat → dropout → FC → sigmoid
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TextCNN(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        num_labels: int,
        embed_dim: int = 128,
        num_filters: int = 128,
        kernel_sizes: tuple = (2, 3, 4),
        dropout: float = 0.5,
        pad_idx: int = 0,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_idx)
        self.convs = nn.ModuleList(
            [nn.Conv1d(embed_dim, num_filters, k) for k in kernel_sizes]
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(kernel_sizes), num_labels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len)
        emb = self.embedding(x).permute(0, 2, 1)  # (batch, embed_dim, seq_len)
        pooled = [F.max_pool1d(F.relu(conv(emb)), conv(emb).size(2)).squeeze(2) for conv in self.convs]
        cat = torch.cat(pooled, dim=1)             # (batch, num_filters * len(kernels))
        out = self.fc(self.dropout(cat))            # (batch, num_labels)
        return out                                  # raw logits — apply sigmoid at inference
