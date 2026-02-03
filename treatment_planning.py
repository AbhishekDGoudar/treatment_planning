import streamlit as st


st.set_page_config(page_title="Policy Analysis", layout="wide")

st.title("Policy Analysis & Extraction")
st.caption("Use the pages on the left to upload documents and run RAG workflows.")

st.markdown(
    """
### Pages
- Document Upload and Ingest
- Text RAG
- Graph RAG
- Waiver Difference Checker
- Thematic Analysis
"""
)
