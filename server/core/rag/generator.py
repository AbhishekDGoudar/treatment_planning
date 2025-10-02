from typing import List
from dataclasses import dataclass
from mlx_lm import load as mlx_load, generate as mlx_generate

@dataclass
class PromptPiece:
    role: str
    content: str

SYSTEM = (
    "You answer using only the given context. "
    "Return a concise rationale (2-3 bullets) and numbered sources with file paths and page numbers."
)

class LLM:
    def __init__(self, model_id: str):
        self.model, self.tokenizer = mlx_load(model_id)

    def answer(self, pieces: List[PromptPiece], max_tokens: int = 512) -> str:
        prompt = "\n\n".join([f"{p.role.upper()}: {p.content}" for p in pieces])
        return mlx_generate(self.model, self.tokenizer, prompt=prompt, max_tokens=max_tokens)
