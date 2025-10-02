from pathlib import Path
import numpy as np
import faiss
from core.models import Document, Chunk, Embedding

TEXT_FAISS = Path("faiss_text.index")
IMG_FAISS = Path("faiss_image.index")

text_index = faiss.read_index(str(TEXT_FAISS)) if TEXT_FAISS.exists() else None
img_index = faiss.read_index(str(IMG_FAISS)) if IMG_FAISS.exists() else None

def search_text(query_vec: np.ndarray, k: int = 8):
    if text_index is None: return []
    D, I = text_index.search(query_vec.astype("float32"), k)
    hits = []
    for dist, idx in zip(D[0], I[0]):
        if idx == -1: continue
        emb = Embedding.objects.filter(kind="text", vector_id=idx).select_related("chunk","document").first()
        if emb:
            hits.append({"score": float(dist), "chunk": emb.chunk, "document": emb.document})
    return hits

def search_image(img_vec: np.ndarray, k: int = 8):
    if img_index is None: return []
    D, I = img_index.search(img_vec.astype("float32"), k)
    hits = []
    for dist, idx in zip(D[0], I[0]):
        if idx == -1: continue
        emb = Embedding.objects.filter(kind="image", vector_id=idx).select_related("document").first()
        if emb:
            hits.append({"score": float(dist), "document": emb.document})
    return hits
