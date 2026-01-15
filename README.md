# Policy Analysis & Extraction Tool (RAG + GraphRAG)

A local-first platform for **deep policy intelligence**, **retrieval-augmented analysis**, and **graph reasoning**.

This tool provides an end-to-end system for extracting, organizing, and analyzing complex policy documents. It combines LLMs, vector search, and graph reasoning to uncover relationships across large document corpora—all running locally on macOS, Linux, or Windows.

## 🚀 Core Capabilities

### 1. Information Extraction
Automatically parse dense policy text (PDFs, scans, tables, charts) into:
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
| LLM Inference             | Ollama or OpenAI                             |
| Embeddings & Vector Search| LanceDB                                      |
| Knowledge Graph           | Neo4j                                        |
| App UI                    | Streamlit (Python)                           |

## 📦 Prerequisites

- **Python 3.11+**
- **Neo4j** (Desktop, package manager, or Docker)

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

Create `.env` (optional):
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpass
```

## 🛠️ App Setup
```
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
streamlit run streamlit_app.py
```

Open: http://localhost:8501

## 📥 Ingest Documents
Use the **Ingest PDFs** tab inside Streamlit to load and index your corpus.

## 🔎 Querying
- Grounded answers  
- Numbered citations  
- GraphRAG over Neo4j  

## 🧩 Extensions
- SigLIP image embeddings  
- mlx-embeddings for text  
- Rerankers  
- Graph-first retrieval  
- Agent-based thematic clustering  

## 📄 License
MIT
