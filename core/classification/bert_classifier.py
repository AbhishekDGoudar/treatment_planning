"""
BERT-based multi-label classifier for waiver section text.
Uses bert-base-uncased with a linear classification head.
"""
import torch
import torch.nn as nn
from transformers import AutoModel


class BERTClassifier(nn.Module):
    def __init__(
        self,
        num_labels: int,
        model_name: str = "bert-base-uncased",
        dropout: float = 0.3,
    ):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, num_labels)

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        # Use [CLS] token representation
        cls_output = outputs.last_hidden_state[:, 0, :]
        return self.classifier(self.dropout(cls_output))  # raw logits
