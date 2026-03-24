"""LLM factory — returns a ChatGoogleGenerativeAI, ChatGroq, or Local LLM client (LM Studio)."""
from langchain_google_genai import ChatGoogleGenerativeAI
import os

def get_llm():
    """
    Return a chat model based on the LLM_PROVIDER environment variable.
    Supported providers: 'google' (default), 'groq', 'lmstudio'.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                api_key=os.getenv("GROQ_API_KEY"),
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                temperature=0.1,
            )
        except ImportError:
            raise ImportError(
                "Could not import langchain_groq. Please install it with: "
                "pip install langchain-groq"
            )

    if provider == "lmstudio":
        try:
            from langchain_openai import ChatOpenAI
            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            model_name = os.getenv("LMSTUDIO_MODEL", "local-model")
            return ChatOpenAI(
                base_url=base_url,
                model=model_name,
                api_key="not-needed",  # LM Studio doesn't require a real key
                temperature=0.1,
            )
        except ImportError:
            raise ImportError(
                "Could not import langchain_openai. Please install it with: "
                "pip install langchain-openai"
            )

    # Default to Google Gemini
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-1.5-flash"),
        temperature=0.1,
    )