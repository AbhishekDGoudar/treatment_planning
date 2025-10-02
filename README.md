# Multimodal RAG (Neo4j + MLX) — Django + React

Local-first **multimodal RAG** on macOS using **MLX** for LLM/VLM, **FAISS** for vectors, and **Neo4j** for a knowledge graph.

## Prereqs
- macOS with Apple Silicon
- Python 3.10+
- Node 18+
- Homebrew
- Neo4j (via Homebrew service or Neo4j Desktop)
- Xcode CLT

## Install Neo4j
```bash
brew install neo4j
brew services start neo4j
# open http://localhost:7474 first time to set password
```
Create `server/.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=yourpass
MLX_TEXT_MODEL=mlx-community/Meta-Llama-3-8B-Instruct-4bit
MLX_VLM_MODEL=mlx-community/Qwen2-VL-2B-4bit
```

## Backend setup
```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Frontend setup
```bash
cd ../web
npm i
npm run dev # http://localhost:5173
```

## Ingest a folder of docs/images
```bash
cd ../server
python manage.py shell
```
```python
from core.ingestion.loaders import load_path
from core.ingestion.embeddings import index_corpus
from core.ingestion.graph import Graph
from core.models import Document

load_path("/path/to/your/corpus")

# Optionally tag metadata
# Document.objects.filter(path__endswith="report2022.pdf").update(year=2022, group="A", state="TX")

index_corpus()

G = Graph()
for d in Document.objects.all():
    G.upsert_doc(d.path, d.year, d.group, d.state)
```

## Ask questions
Open the web app, ask a question, optionally filter by year/group/state. You’ll get:
- concise answer + numbered sources (file path, page, score)
- a force-directed **graph** of the cited sources and attributes

## Notes
- You can swap CLIP with SigLIP, or use mlx-embeddings for text.
- Add reranking, image captioning on ingest, and graph-first filtering as upgrades.
