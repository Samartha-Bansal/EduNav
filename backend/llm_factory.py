"""Create the configured LLM for RAG (Groq preferred, Gemini optional)."""

import os
from dotenv import load_dotenv
from llama_index.core.llms import LLM

load_dotenv()
load_dotenv(".env.local", override=True)


def create_llm() -> LLM:
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    if groq_key:
        from groq_llm import GroqLLM

        return GroqLLM(
            model_name=model if not model.startswith("gemini") else "llama-3.1-8b-instant",
            api_key=groq_key,
        )

    if gemini_key:
        from gemini_llm import GeminiLLM

        return GeminiLLM(model_name=model if model.startswith("gemini") else "gemini-2.0-flash")

    raise ValueError(
        "No LLM configured. Set GROQ_API_KEY or GEMINI_API_KEY in backend/.env"
    )
