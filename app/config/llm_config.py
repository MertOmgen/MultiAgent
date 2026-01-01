"""LLM configuration with provider switching (OpenAI or Ollama)."""

import os
from typing import Dict, Any

from dotenv import load_dotenv
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient


# Ensure .env is loaded before reading env vars for model selection
load_dotenv()


# Agent-specific temperature settings
AGENT_TEMPERATURES = {
    "designer": 0.7,  # More creative for architecture decisions
    "backend": 0.5,   # Balanced for code implementation
    "frontend": 0.5,  # Balanced for code implementation
    "qa": 0.3,        # More deterministic for testing
}


def _is_openai() -> bool:
    return os.getenv("LLM_PROVIDER", "ollama").lower() == "openai"


def get_provider_settings() -> Dict[str, str]:
    """Return provider name and base URL resolved from env."""
    if _is_openai():
        return {
            "provider": "openai",
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        }
    return {
        "provider": "ollama",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


def _agent_model(role: str) -> str:
    if _is_openai():
        return os.getenv(f"OPENAI_MODEL_{role.upper()}", "gpt-4.1")
    return os.getenv(f"OLLAMA_MODEL_{role.upper()}", "qwen2.5-coder:7b")


def get_agent_models() -> Dict[str, str]:
    """Return mapping of agent role to configured model."""
    return {role: _agent_model(role) for role in AGENT_TEMPERATURES.keys()}


# Snapshot at import for quick access (used by main entrypoints)
AGENT_MODELS = get_agent_models()


def create_model_client(role: str):
    """Create model client for a specific agent role based on provider."""
    model = _agent_model(role)
    if _is_openai():
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIChatCompletionClient(model=model, base_url=base_url, api_key=api_key)

    # Ollama fallback
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaChatCompletionClient(model=model, base_url=base_url)


def get_model_params(role: str) -> Dict[str, Any]:
    """Get generation parameters for a specific role."""
    return {
        "temperature": AGENT_TEMPERATURES.get(role, 0.5),
        "max_tokens": 4096,
    }