from pathlib import Path
import numpy as np
import faiss
from PIL import Image

from transformers import CLIPProcessor, CLIPModel
import torch

from core.models import Chunk, ImageAsset, Embedding

# Text embeddings: try MLX-LM embed API; fallback to HF CPU
try:
    from mlx_lm import embed as mlx_embed
    _HAS_MLX = True
except Exception:
    _HAS_MLX = False

CLIP_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(CLIP_NAME)
clip_proc = CLIPProcessor.from_pretrained(CLIP_NAME)

TEXT_FAISS = Path("faiss_text.index")
IMG_FAISS = Path("faiss_image.index")

text_index = faiss.IndexFlatIP(768)  # adjust to embedding size if your text model differs
img_index = faiss.IndexFlatIP(512)

def embed_text_batch(texts: list[str]) -> np.ndarray:
    if _HAS_MLX:
        try:
            vectors = mlx_embed(texts)
            return np.array(vectors, dtype="float32")
        except Exception:
            pass
    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained("intfloat/e5-small")
    mdl = AutoModel.from_pretrained("intfloat/e5-small")
    with torch.no_grad():
        embs = mdl(**tok(texts, return_tensors="pt", padding=True, truncation=True))
        vecs = embs.last_hidden_state.mean(dim=1).cpu().numpy().astype("float32")
    return vecs

def embed_image_batch(paths: list[str]) -> np.ndarray:
    imgs = [Image.open(p).convert("RGB") for p in paths]
    inputs = clip_proc(images=imgs, return_tensors="pt")
    with torch.no_grad():
        vecs = clip_model.get_image_features(**inputs).cpu().numpy().astype("float32")
    faiss.normalize_L2(vecs)
    return vecs

def index_corpus():
    # text
    chunks = list(Chunk.objects.all().order_by("id"))
    texts = [c.text for c in chunks]
    if texts:
        tvecs = embed_text_batch(texts)
        faiss.normalize_L2(tvecs)
        text_index.add(tvecs)
        for i, c in enumerate(chunks):
            Embedding.objects.create(kind="text", vector_id=i, chunk=c, document=c.document)
        faiss.write_index(text_index, str(TEXT_FAISS))
    # images
    imgs = list(ImageAsset.objects.all().order_by("id"))
    paths = [im.path for im in imgs]
    if paths:
        ivecs = embed_image_batch(paths)
        img_index.add(ivecs)
        for i, im in enumerate(imgs):
            Embedding.objects.create(kind="image", vector_id=i, document=im.document)
        faiss.write_index(img_index, str(IMG_FAISS))
