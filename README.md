# Policy Analysis & Extraction Tool (RAG + GraphRAG)

A local-first platform for **deep policy intelligence**, **retrieval-augmented analysis**,
**graph reasoning**, and **theme classification & qualitative coding** of Medicaid SED /
1915(c) waiver documents.

This tool provides an end-to-end system for extracting, organizing, analyzing, comparing, and
coding complex policy documents. It combines LLMs, vector search, graph reasoning, and both
local and hosted classifiers to uncover relationships across large document corpora—all running
locally on macOS, Linux, or Windows.

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
Query both text and visual information at once, using local multimodal LLMs/VLMs to produce
**grounded answers with traceable sources**.

### 4. Agentic Theme Analysis
Autonomous agents detect patterns across documents—funding, eligibility, compliance—and
synthesize multi-document insights.

### 5. Document Comparison 
Compare two waiver records section-by-section with sentence- and word-level highlighting, and
export a shareable HTML diff report.

### 6. Theme Classification 
Tag waiver text against **20 predefined themes** using either a **local model** (TextCNN / BERT)
or the **Claude API** (zero-shot, prompt-cached), and compare the approaches on the same data.

### 7. Retrieval-Augmented Coding
Reproduce MAXQDA-style qualitative coding: retrieve human-coded examples from a knowledge base
and have Claude predict codes for new text, with confidence and rationale.

## 🧱 Architecture Overview (Local-First Multimodal RAG)

| Layer                      | Technology                                              |
|----------------------------|---------------------------------------------------------|
| LLM Inference              | Ollama or OpenAI or **Anthropic Claude**                |
| Embeddings & Vector Search | LanceDB                                                 |
| Knowledge Graph            | Neo4j                                                   |
| Local classifiers  | PyTorch (TextCNN from scratch; BERT via `transformers`) |
| App UI                     | Streamlit (Python)                                      |

## 📦 Prerequisites

- **Python 3.11+**
- **Neo4j** (Desktop, package manager, or Docker) — for the Graph RAG pages
- **Anthropic API key** — for the Claude Classification and RAG Coder pages
- **An embedding provider for retrieval** — Ollama (`bge-m3`) or OpenAI
  (`text-embedding-3-small`)

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

Create `.env` (optional for Neo4j; **required keys for the LLM pages are set as environment
variables**):

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpass

# LLM / embedding configuration (see core/config.py for all defaults)
AI_PROVIDER=OLLAMA
OLLAMA_EMBEDDING_MODEL=bge-m3
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
ANTHROPIC_LLM_MODEL=claude-sonnet-4-6
```

Set the Anthropic key in your shell (the Claude pages also accept it typed into the sidebar):

```
export ANTHROPIC_API_KEY=sk-ant-...      # macOS/Linux
setx  ANTHROPIC_API_KEY sk-ant-...       # Windows (open a new shell after)
```

> ⚠️ **Security:** do not commit real secrets. Add `.env` to `.gitignore`, ship a
> `.env.example` with placeholders, and rotate any key/password that was ever committed.

## 🛠️ App Setup
```
pip install -U pip
pip install uv
uv venv .venv
source .venv/bin/activate
uv sync
streamlit run treatment_planning.py
```

Open: http://localhost:8501

## 🐳 Docker Setup
### Install Docker
- macOS: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/engine/install/

### Run with Neo4j
```
docker compose up --build
```

Open:
- App: http://localhost:8501
- Neo4j: http://localhost:7474

### Optional Ollama Service
```
docker compose --profile ollama up --build
```

If you run Ollama on the host instead, set `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

## 📄 Pages

The app is a Streamlit multipage app. `treatment_planning.py` is the landing page; each
workflow is a file in `pages/`, auto-discovered into the sidebar. Pages 4–7 are self-contained
and do not require the ingestion/graph pages to run first.

| Page | Title | Purpose | Needs |
|------|-------|---------|-------|
| `1_Document_Upload_and_Ingest.py` | Document Upload & Ingest | Load and index the corpus. | — |
| `2_Text_RAG.py` | Text RAG | Retrieval-augmented Q&A over text. | Embeddings / LLM |
| `3_Graph_RAG.py` | Graph RAG | Graph-based reasoning over entities. | Neo4j |
| `4_Difference_Checker.py` | Waiver DiffChecker | Section-by-section diff of two records; HTML export. | Excel file |
| `5_Text_Classification.py`  | Text Classification | Train/run a local TextCNN or BERT multi-label classifier. | PyTorch; labelled CSV |
| `6_Claude_Classification.py`  | Claude Classification | Zero-shot multi-label classification via Claude. | `ANTHROPIC_API_KEY`; Excel file |
| `7_RAG_Coder.py`  | RAG Coder | Retrieval-augmented qualitative coding. | `ANTHROPIC_API_KEY`; embeddings; LanceDB |

## 🗂️ Shared Data Assets 

### The SED Waiver Excel workbook (Pages 4, 6, 7)
Read with `pd.read_excel(file, sheet_name="Data Master")`. The workbook **must** have a sheet
named exactly `Data Master` and a column `Application Number` (one row = one waiver). Narrative
text columns such as `Service Plan Development Process (D1d)` and
`Service Plan Implementation and Monitoring. (D2a)` are auto-selected as defaults. **Not committed
to the repo — supply your own.**

### The 20 predefined themes (Pages 5, 6)
Defined in `core/thematic/themes.py` as `PREDEFINED_THEMES` and `THEME_NAMES`. The local and
Claude classifiers tag against the same 20 themes, so their outputs are directly comparable.

### The MAXQDA coding knowledge base (Page 7)
Under `knowledge_base/`:
- `coded_segments.jsonl` — 1,386 human-coded spans (`document, code, code_path, coder, start,
  end, length, text`).
- `codebook.csv` — code hierarchy (`guid, name, path, color`).
- `qdpx_extract.py` — regenerates the JSONL from a REFI-QDA `.qdpx` export.

A prebuilt LanceDB index ships at `lancedb/coded_segments.lance`.

## 📥 Ingest Documents
Use the **Document Upload and Ingest** page inside Streamlit to load and index your corpus.

## 🔎 Querying & Analysis
- Text RAG
- Graph RAG
- Thematic analysis
- **Difference Checker** *(new)*
- **Text Classification** — local TextCNN / BERT *(new)*
- **Claude Classification** — hosted, prompt-cached *(new)*
- **RAG Coder** — retrieval-augmented coding *(new)*

## ⚠️ Gotchas 

- **Hard-coded schema.** The sheet `Data Master` and the `Application Number` column are required
  by name on Pages 4, 6, 7.
- **Session-state models.** On Text Classification, the Classify/Compare tabs read the model from
  `st.session_state`; the saved `.pt` checkpoint is not auto-reloaded, so train within the session.
- **BERT download.** `bert-base-uncased` is fetched from Hugging Face on first run.
- **Embedding-provider mismatch.** A LanceDB index built with Ollama `bge-m3` cannot be queried
  with OpenAI embeddings. Rebuild with the provider you intend to query with.
- **LLM reproducibility.** Claude results depend on the live model and threshold; record both
  alongside exported CSVs.

## 🗂️ Project Layout
```
treatment_planning.py
pages/
  1_Document_Upload_and_Ingest.py
  2_Text_RAG.py
  3_Graph_RAG.py
  4_Difference_Checker.py        
  5_Text_Classification.py       
  6_Claude_Classification.py     
  7_RAG_Coder.py                 
core/
  config.py
  classification/                #  local + Claude classifiers
    bert_classifier.py
    claude_classifier.py
    dataset.py
    evaluator.py
    text_cnn.py
    trainer.py
  extraction/
    extraction_utils.py
  ingestion/
    pdf_ingest.py
    graph_ingest.py
  rag/
    generator.py
    pipeline.py
    retriever.py
    text_retriever.py
    kb_indexer.py                #  LanceDB knowledge-base indexing
    rag_coder.py                 #  retrieval-augmented coding
  storage/
    graph_storage.py
    sqlite_storage.py
  thematic/                      #  themes + thematic analysis
    themes.py                    #  PREDEFINED_THEMES / THEME_NAMES (20 themes)
    coder.py
    report.py
  ui/
    sidebar.py
knowledge_base/                  #  MAXQDA coding KB
  coded_segments.jsonl           #  Load the file using same nomenclature before executing
lancedb/                         #  prebuilt vector index
```

## 🧩 Extensions
- SigLIP image embeddings
- mlx-embeddings for text
- Rerankers
- Graph-first retrieval
- Agent-based thematic clustering

## 🔭 Future Work
- Difference Checker: configurable schema; PDF/Word export; cross-file comparison.
- Text Classification: auto-reload checkpoints; cross-validation; early stopping.
- Claude Classification: concurrency; DB persistence; eval against the labelled CSV.
- RAG Coder: store embedding provider in the index; human-in-the-loop write-back; reranking.
- Cross-cutting: unified comparison dashboard; sample dataset for smoke tests; `.env.example`.

## 📄 License
MIT
