import streamlit as st


st.set_page_config(page_title="Policy Analysis (Local)", layout="wide")

st.title("Policy Analysis & Extraction (Local)")
st.caption("Use the pages on the left to upload documents and run RAG workflows.")

st.markdown(
    """
### Pages
- Document Upload and Ingest
- Text RAG
- Graph RAG
- Thematic Analysis

### External Tools
- Diff Checker: https://waiverdifferencecheck.streamlit.app/
"""
)
