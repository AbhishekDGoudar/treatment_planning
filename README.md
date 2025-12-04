# Policy Analysis & Extraction Tool (Multimodal RAG)

A local-first platform for **deep policy intelligence**, **multimodal retrieval**, and **autonomous thematic analysis**.

This tool provides an end-to-end system for extracting, organizing, and analyzing complex policy documents. It combines multimodal LLM/VLM models, vector search, and graph reasoning to uncover relationships across large document corpora—all running locally on macOS, Linux, or Windows.

## 🚀 Core Capabilities

### 1. Information Extraction
Automatically parse dense policy text and images (PDFs, scans, tables, charts) into:
- entities  
- claims   
- themes  

### 2. Policy Theme Mapping
Generate an interactive knowledge graph showing connections between:
- policies  
- entities  
- topics  
- metadata (year, state, group)  

### 3. Multimodal Chatbot
Query both text and visual information at once, using local multimodal LLMs/VLMs to produce **grounded answers with traceable sources**.

### 4. Agentic Theme Analysis
Autonomous agents detect patterns across documents—funding, eligibility, compliance—and synthesize multi-document insights.

## 🧱 Architecture Overview (Local-First Multimodal RAG)

| Layer                     | Technology                                   |
|---------------------------|-----------------------------------------------|
| LLM / VLM Inference       | MLX (Llama 3, Qwen2-VL, etc.)                |
| Embeddings & Vector Search| FAISS                                        |
| Knowledge Graph           | Neo4j                                        |
| Backend                   | Django (Python)                              |
| Frontend                  | React (Node.js)                              |

## 📦 Prerequisites

- **Python 3.10+**
- **Node 18+**
- **Neo4j** (Desktop, package manager, or Docker)
- **Build tools**  
  - macOS: Xcode Command Line Tools  
  - Linux: build-essential  
  - Windows: MSVC Build Tools or WSL2  

## 🗄️ Install Neo4j

### macOS
```
brew install neo4j
brew services start neo4j
```

### Linux
```
sudo apt install neo4j
sudo systemctl start neo4j
```

### Windows
Install via Neo4j Desktop.

Open Neo4j browser at: http://localhost:7474

## 🔐 Environment Configuration

Create `server/.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=yourpass

MLX_TEXT_MODEL=mlx-community/Meta-Llama-3-8B-Instruct-4bit
MLX_VLM_MODEL=mlx-community/Qwen2-VL-2B-4bit
```

## 🛠️ Backend Setup
```
cd server
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## 💻 Frontend Setup
```
cd ../web
npm install
npm run dev
```

Open: http://localhost:5173

## 📥 Ingest Documents
```
cd ../server
python manage.py shell
```

```python
from core.ingestion.loaders import load_path
from core.ingestion.embeddings import index_corpus
from core.ingestion.graph import Graph
from core.models import WaiverDocument

load_path("/path/to/your/corpus")
index_corpus()

G = Graph()
for d in WaiverDocument.objects.all():
    G.upsert_doc(d.path, d.year, d.group, d.state)
```

## 🔎 Querying
- Grounded answers  
- Numbered citations  
- Interactive knowledge graph  

## 🧩 Extensions
- SigLIP image embeddings  
- mlx-embeddings for text  
- Rerankers  
- Graph-first retrieval  
- Agent-based thematic clustering  

## 📄 License
MIT
