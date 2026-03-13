"""LLM factory — single source of truth for the ChatOpenAI client."""
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """
    Return a ChatOpenAI instance wired to the local llama-server endpoint.

    The server is expected to expose an OpenAI-compatible API at
    ``http://127.0.0.1:8080/v1``.  No real API key is required for a
    local deployment.
    """
    return ChatOpenAI(
        openai_api_base="http://127.0.0.1:8080/v1",
        openai_api_key="not-needed",
        streaming=True,
        temperature=0.1,
    )
