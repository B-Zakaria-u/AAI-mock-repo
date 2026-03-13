"""LLM factory — returns a ChatGoogleGenerativeAI client (Gemini 2.5 Flash)."""
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Return a Gemini 2.5 Flash chat model via the Google Generative AI API.

    Requires the ``GOOGLE_API_KEY`` environment variable to be set.
    Temperature is kept low (0.1) for deterministic, code-focused outputs.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.1,
    )
