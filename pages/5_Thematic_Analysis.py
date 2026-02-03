import streamlit as st

from core.rag.generator import GeneratorFactory, PromptPiece
from core.ui.sidebar import render_sidebar_settings


st.set_page_config(page_title="Thematic Analysis", layout="wide")
st.title("Thematic Analysis")

provider_choice, openai_key = render_sidebar_settings()

st.subheader("Analyze Themes")
input_text = st.text_area("Paste content for analysis", height=200)
analysis_goal = st.text_input("Goal (optional)", value="Identify major themes and policy implications")

if st.button("Run Thematic Analysis"):
    if not input_text.strip():
        st.warning("Enter content to analyze.")
    else:
        if provider_choice == "OPENAI" and not openai_key:
            st.warning("OpenAI selected but no API key provided.")
            st.stop()
        prompt = [
            PromptPiece(
                role="system",
                content="Extract key themes and summarize them clearly.",
            ),
            PromptPiece(
                role="user",
                content=f"Goal: {analysis_goal}\n\nContent:\n{input_text}",
            ),
        ]
        generator = GeneratorFactory()
        with st.spinner("Analyzing..."):
            try:
                analysis = generator.generate(prompt)
                st.markdown("### Thematic Analysis")
                st.write(analysis)
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
