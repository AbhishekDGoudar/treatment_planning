import os

import lancedb
import streamlit as st

from core import config
from core.ingestion.pdf_ingest import ingest_pdf_folder
from core.ingestion.graph_ingest import ingest_statewise_kg
from core.rag.generator import GeneratorFactory, PromptPiece
from core.rag.pipeline import GraphRAGPipeline
from core.rag.text_retriever import TextRetriever
from core.storage import list_recent_documents


st.set_page_config(page_title="Policy Analysis (Local)", layout="wide")


def configure_provider(
    provider: str,
    openai_key: str,
    ollama_llm_model: str,
    ollama_embedding_model: str,
    openai_llm_model: str,
    openai_embedding_model: str,
) -> None:
    config.update_config(
        AI_PROVIDER=provider,
        OLLAMA_LLM_MODEL=ollama_llm_model,
        OLLAMA_EMBEDDING_MODEL=ollama_embedding_model,
        OPENAI_LLM_MODEL=openai_llm_model,
        OPENAI_EMBEDDING_MODEL=openai_embedding_model,
    )

    if provider.upper() == "OPENAI":
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
    else:
        os.environ.pop("OPENAI_API_KEY", None)


def build_text_rag_answer(query: str, provider: str, k: int):
    db = lancedb.connect(str(config.LANCE_DB_PATH))
    if "policy_docs" not in db.table_names():
        raise RuntimeError("LanceDB table 'policy_docs' not found. Run PDF ingestion first.")

    retriever = TextRetriever(provider)
    results = retriever.search(query, k=k)

    if not results:
        return "No relevant chunks found.", []

    context_blocks = []
    for idx, item in enumerate(results, start=1):
        context_blocks.append(f"[{idx}] {item['text']}")

    prompt = [
        PromptPiece(
            role="system",
            content="Answer using ONLY the provided context. Cite sources as [1], [2], etc.",
        ),
        PromptPiece(
            role="user",
            content=f"Question: {query}\n\nContext:\n" + "\n\n".join(context_blocks),
        ),
    ]
    generator = GeneratorFactory()
    answer = generator.generate(prompt)
    return answer, results


st.title("Policy Analysis & Extraction (Local)")
st.caption("Local-only Streamlit UI with RAG and GraphRAG. Choose Ollama or provide an API key.")

with st.sidebar:
    st.header("LLM Settings")
    provider_choice = st.selectbox("Provider", ["OLLAMA", "OPENAI"])
    openai_key = st.text_input("OpenAI API Key (optional)", type="password")
    st.divider()
    ollama_llm = st.text_input("Ollama LLM model", value=config.OLLAMA_LLM_MODEL)
    ollama_embed = st.text_input("Ollama embedding model", value=config.OLLAMA_EMBEDDING_MODEL)
    openai_llm = st.text_input("OpenAI LLM model", value=config.OPENAI_LLM_MODEL)
    openai_embed = st.text_input("OpenAI embedding model", value=config.OPENAI_EMBEDDING_MODEL)

    if st.button("Apply LLM Settings"):
        configure_provider(
            provider_choice,
            openai_key,
            ollama_llm,
            ollama_embed,
            openai_llm,
            openai_embed,
        )
        st.success("Settings applied.")

configure_provider(
    provider_choice,
    openai_key,
    ollama_llm,
    ollama_embed,
    openai_llm,
    openai_embed,
)

tab_ingest, tab_graph, tab_query = st.tabs(["Ingest PDFs", "Ingest Graph", "Query"])

with tab_ingest:
    st.subheader("PDF Ingestion")
    data_folder = st.text_input("PDF folder path", value=str(config.DATA_DIR))
    clear_existing = st.checkbox("Clear existing records", value=True)
    persist_tracking = st.checkbox("Persist file tracking", value=True)
    timeout_seconds = st.number_input("Per-file timeout (seconds)", min_value=10, max_value=600, value=60)

    if st.button("Run PDF Ingestion"):
        progress = st.progress(0)
        status = st.empty()
        data_path = Path(data_folder)
        total_files = len(list(data_path.rglob("*.pdf"))) if data_path.exists() else 0
        counts = {"seen": 0}

        def on_progress(event):
            counts["seen"] += 1
            if total_files:
                progress.progress(min(counts["seen"] / total_files, 1.0))
            status.write(f"{event.get('event')}: {event.get('path')}")

        with st.spinner("Ingesting PDFs..."):
            try:
                summary = ingest_pdf_folder(
                    data_folder=data_folder,
                    provider=provider_choice,
                    timeout_seconds=int(timeout_seconds),
                    persist_tracking=persist_tracking,
                    clear_existing=clear_existing,
                    on_progress=on_progress,
                )
                st.success("Ingestion complete.")
                st.json(summary)
            except Exception as exc:
                st.error(f"Ingestion failed: {exc}")

    st.markdown("### Recent Documents")
    recent_docs = list_recent_documents()
    if recent_docs:
        st.json(recent_docs)
    else:
        st.info("No documents found yet.")

with tab_graph:
    st.subheader("Graph Ingestion")
    graph_file_path = st.text_input(
        "Excel file path",
        value=str(config.DATA_DIR / "SED Waiver Data - Treatment Planning.xlsx"),
    )

    if st.button("Run Graph Ingestion"):
        with st.spinner("Ingesting graph data..."):
            try:
                summary = ingest_statewise_kg(graph_file_path, provider=provider_choice)
                st.success("Graph ingestion complete.")
                st.json(summary)
            except Exception as exc:
                st.error(f"Graph ingestion failed: {exc}")

with tab_query:
    st.subheader("Ask a Question")
    query = st.text_area("Question", height=100)
    mode = st.radio("Mode", ["Text RAG", "GraphRAG", "Hybrid"], horizontal=True)
    top_k = st.slider("Top-K (Text RAG)", min_value=2, max_value=10, value=5)

    if st.button("Run Query"):
        if not query.strip():
            st.warning("Enter a question to continue.")
        else:
            if provider_choice == "OPENAI" and not openai_key:
                st.warning("OpenAI selected but no API key provided.")
                st.stop()
            if mode in ("Text RAG", "Hybrid"):
                with st.spinner("Running Text RAG..."):
                    try:
                        answer, sources = build_text_rag_answer(query, provider_choice, top_k)
                        st.markdown("### Text RAG Answer")
                        st.write(answer)
                        st.markdown("### Sources")
                        st.json(sources)
                    except Exception as exc:
                        st.error(f"Text RAG failed: {exc}")

            if mode in ("GraphRAG", "Hybrid"):
                with st.spinner("Running GraphRAG..."):
                    try:
                        pipe = GraphRAGPipeline()
                        plan = pipe.plan(query)
                        if not plan.get("is_safe", True):
                            st.error(f"Graph plan rejected: {plan.get('error')}")
                        else:
                            result = pipe.execute(plan.get("cypher_query", ""), query)
                            st.markdown("### GraphRAG Answer")
                            st.write(result.get("answer"))
                            st.markdown("### Graph Data")
                            st.json(result.get("graph_data"))
                    except Exception as exc:
                        st.error(f"GraphRAG failed: {exc}")
