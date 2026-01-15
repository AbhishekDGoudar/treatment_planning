import streamlit as st

from core.rag.pipeline import GraphRAGPipeline
from core.ui.sidebar import render_sidebar_settings


st.set_page_config(page_title="Graph RAG", layout="wide")
st.title("Graph RAG")

provider_choice, openai_key = render_sidebar_settings()

st.subheader("Ask a Question")
query = st.text_area("Question", height=120)

if st.button("Run Graph RAG"):
    if not query.strip():
        st.warning("Enter a question to continue.")
    else:
        if provider_choice == "OPENAI" and not openai_key:
            st.warning("OpenAI selected but no API key provided.")
            st.stop()
        with st.spinner("Running Graph RAG..."):
            try:
                pipe = GraphRAGPipeline()
                plan = pipe.plan(query)
                if not plan.get("is_safe", True):
                    st.error(f"Graph plan rejected: {plan.get('error')}")
                else:
                    result = pipe.execute(plan.get("cypher_query", ""), query)
                    st.markdown("### Answer")
                    st.write(result.get("answer"))
                    st.markdown("### Graph Data")
                    st.json(result.get("graph_data"))
            except Exception as exc:
                st.error(f"Graph RAG failed: {exc}")
