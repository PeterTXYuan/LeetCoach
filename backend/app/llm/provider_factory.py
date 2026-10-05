"""Environment-only LLM provider configuration."""
import os

from dotenv import load_dotenv

from app.database import BACKEND_DIR
from app.llm.base import LLMProvider, ProviderConfigurationError
from app.llm.groq_provider import GroqLLMProvider
from app.llm.mock_provider import MockLLMProvider


def get_llm_provider() -> LLMProvider:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    provider = os.environ.get("LEETCOACH_LLM_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return MockLLMProvider()
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        model = os.environ.get("LEETCOACH_LLM_MODEL", "").strip()
        if not api_key:
            raise ProviderConfigurationError("GROQ_API_KEY is required for the Groq provider")
        if not model:
            raise ProviderConfigurationError("LEETCOACH_LLM_MODEL is required for the Groq provider")
        return GroqLLMProvider(api_key=api_key, model=model)
    raise ProviderConfigurationError("Unknown LEETCOACH_LLM_PROVIDER")
