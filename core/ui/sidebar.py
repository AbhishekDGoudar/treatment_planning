import os

import streamlit as st

from core import config


def render_sidebar_settings():
    with st.sidebar:
        st.header("LLM Settings")
        provider_choice = st.selectbox("Provider", ["OLLAMA", "OPENAI", "ANTHROPIC"])

        openai_key = ""
        anthropic_key = ""

        if provider_choice == "OPENAI":
            openai_key = st.text_input("OpenAI API Key", type="password")
        elif provider_choice == "ANTHROPIC":
            anthropic_key = st.text_input("Anthropic API Key", type="password")

        st.divider()
        ollama_llm   = st.text_input("Ollama LLM model",       value=config.OLLAMA_LLM_MODEL)
        ollama_embed = st.text_input("Ollama embedding model",  value=config.OLLAMA_EMBEDDING_MODEL)
        openai_llm   = st.text_input("OpenAI LLM model",       value=config.OPENAI_LLM_MODEL)
        openai_embed = st.text_input("OpenAI embedding model",  value=config.OPENAI_EMBEDDING_MODEL)
        anthropic_llm = st.text_input("Claude model",          value=config.ANTHROPIC_LLM_MODEL)

        if st.button("Apply LLM Settings"):
            configure_provider(
                provider_choice,
                openai_key,
                anthropic_key,
                ollama_llm,
                ollama_embed,
                openai_llm,
                openai_embed,
                anthropic_llm,
            )
            st.success("Settings applied.")

    configure_provider(
        provider_choice,
        openai_key,
        anthropic_key,
        ollama_llm,
        ollama_embed,
        openai_llm,
        openai_embed,
        anthropic_llm,
    )

    return provider_choice, openai_key


def configure_provider(
    provider: str,
    openai_key: str,
    anthropic_key: str,
    ollama_llm_model: str,
    ollama_embedding_model: str,
    openai_llm_model: str,
    openai_embedding_model: str,
    anthropic_llm_model: str,
) -> None:
    config.update_config(
        AI_PROVIDER=provider,
        OLLAMA_LLM_MODEL=ollama_llm_model,
        OLLAMA_EMBEDDING_MODEL=ollama_embedding_model,
        OPENAI_LLM_MODEL=openai_llm_model,
        OPENAI_EMBEDDING_MODEL=openai_embedding_model,
        ANTHROPIC_LLM_MODEL=anthropic_llm_model,
    )

    if provider.upper() == "OPENAI":
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
        os.environ.pop("ANTHROPIC_API_KEY", None)
    elif provider.upper() == "ANTHROPIC":
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
        os.environ.pop("OPENAI_API_KEY", None)
    else:
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
