import os

import streamlit as st

from core import config


def render_sidebar_settings():
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

        # st.divider()
        # st.subheader("Diff Checker")
        # st.markdown("[Open Diff Checker](https://waiverdifferencecheck.streamlit.app/)")

    configure_provider(
        provider_choice,
        openai_key,
        ollama_llm,
        ollama_embed,
        openai_llm,
        openai_embed,
    )

    return provider_choice, openai_key


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
