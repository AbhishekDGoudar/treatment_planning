from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io

from core.models import Document, Chunk, ImageAsset

TEXT_EXT = {".txt", ".md"}
DOC_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

def load_path(path: str):
    p = Path(path)
    docs = []
    if p.is_file():
        d = _register_file(p); 
        if d: docs.append(d)
    else:
        for f in p.rglob("*"):
            if f.suffix.lower() in (TEXT_EXT | DOC_EXT | IMG_EXT):
                d = _register_file(f); 
                if d: docs.append(d)
    return docs

def _register_file(f: Path):
    doc_type = "text" if f.suffix.lower() in TEXT_EXT else ("pdf" if f.suffix.lower() in DOC_EXT else "image")
    d, _ = Document.objects.get_or_create(path=str(f), defaults={"doc_type": doc_type})
    if doc_type == "text":
        text = f.read_text(errors="ignore")
        Chunk.objects.create(document=d, text=text, order=0)
    elif doc_type == "pdf":
        pdf = fitz.open(str(f))
        for i, page in enumerate(pdf):
            text = page.get_text("text")
            Chunk.objects.create(document=d, text=text, page=i, order=i)
            for img in page.get_images(full=True):
                xref = img[0]
                base = pdf.extract_image(xref)
                img_bytes = base["image"]
                ext = base["ext"]
                out = f.with_suffix("")
                img_path = out.parent / f"{out.name}_p{i}_{xref}.{ext}"
                Image.open(io.BytesIO(img_bytes)).save(img_path)
                ImageAsset.objects.create(document=d, path=str(img_path), page=i)
    elif doc_type == "image":
        ImageAsset.objects.get_or_create(document=d, path=str(f))
    return d
