import regex as re
from typing import Iterable

def semantic_chunks(text: str, max_tokens: int = 350) -> Iterable[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    buf, out = [], []
    for s in parts:
        buf.append(s)
        if sum(len(x.split()) for x in buf) > max_tokens:
            out.append(" ".join(buf)); buf = []
    if buf: out.append(" ".join(buf))
    return out
