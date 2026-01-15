import lancedb
import streamlit as st

from core import config
from core.rag.generator import GeneratorFactory, PromptPiece
from core.rag.text_retriever import TextRetriever
from core.ui.sidebar import render_sidebar_settings


def build_text_rag_answer(query: str, provider: str, k: int):
    db = lancedb.connect(str(config.LANCE_DB_PATH))
    if "policy_docs" not in db.table_names():
        raise RuntimeError("LanceDB table 'policy_docs' not found. Run ingestion first.")

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


st.set_page_config(page_title="Text RAG", layout="wide")
st.title("Text RAG")

provider_choice, openai_key = render_sidebar_settings()

st.subheader("Ask a Question")
query = st.text_area("Question", height=120)
top_k = st.slider("Top-K", min_value=2, max_value=10, value=5)

if st.button("Run Text RAG"):
    if not query.strip():
        st.warning("Enter a question to continue.")
    else:
        if provider_choice == "OPENAI" and not openai_key:
            st.warning("OpenAI selected but no API key provided.")
            st.stop()
        with st.spinner("Running Text RAG..."):
            try:
                answer, sources = build_text_rag_answer(query, provider_choice, top_k)
                st.markdown("### Answer")
                st.write(answer)
                st.markdown("### Sources")
                st.json(sources)
            except Exception as exc:
                st.error(f"Text RAG failed: {exc}")
