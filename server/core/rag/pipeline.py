from dataclasses import dataclass
from typing import Optional
import numpy as np
from core.ingestion.embeddings import embed_text_batch
from core.rag.retrieval import search_text
from core.rag.generator import LLM, PromptPiece, SYSTEM
from core.ingestion.graph import Graph

@dataclass
class RAGResult:
    answer: str
    sources: list[dict]
    graph: list[dict]

class Pipeline:
    def __init__(self, text_model_id: str):
        self.llm = LLM(text_model_id)
        self.graph = Graph()

    def ask(self, query: str, filters: Optional[dict] = None) -> RAGResult:
        qvec = embed_text_batch([query])
        hits = search_text(qvec, k=6)
        if filters:
            y = filters.get("year"); s = filters.get("state"); g = filters.get("group")
            hits = [h for h in hits if (y is None or h["document"].year == y)
                                 and (s is None or h["document"].state == s)
                                 and (g is None or h["document"].group == g)]
        ctx_lines, src_meta = [], []
        for i, h in enumerate(hits[:5], 1):
            c = h["chunk"]
            ctx_lines.append(f"[#{i}] {c.text[:1200]}")
            src_meta.append({
                "rank": i,
                "path": h["document"].path,
                "page": c.page,
                "score": round(h["score"], 4)
            })
        context = "\n\n".join(ctx_lines) or "(no context)"
        pieces = [
            PromptPiece("system", SYSTEM),
            PromptPiece("user", f"Question: {query}\n\nContext:\n{context}\n\nAnswer:")
        ]
        answer = self.llm.answer(pieces)
        sub = self.graph.subgraph_for_docs(paths=[m["path"] for m in src_meta])
        return RAGResult(answer=answer, sources=src_meta, graph=sub)
