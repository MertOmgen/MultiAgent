"""LLM configuration with provider switching (OpenAI, Ollama, or z.ai)."""

import os
from typing import Dict, Any

from dotenv import load_dotenv
from autogen_core.models import ModelFamily
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient


# Ensure .env is loaded before reading env vars for model selection
load_dotenv()


# Agent-specific temperature settings
AGENT_TEMPERATURES = {
    "manager": 0.8,      # More creative for strategic planning and architecture
    "error_agent": 0.3,  # Precise and methodical for debugging
    "devops_agent": 0.3, # Precise for infrastructure and container configuration
    "designer": 0.7,     # More creative for architecture decisions
    "backend": 0.5,      # Balanced for code implementation
    "frontend": 0.5,     # Balanced for code implementation
    "qa": 0.3,           # More deterministic for testing
}


def _get_provider() -> str:
    """Get the current provider from environment."""
    return os.getenv("LLM_PROVIDER", "ollama").lower()


def _is_openai() -> bool:
    return _get_provider() == "openai"


def _is_zai() -> bool:
    return _get_provider() == "zai"


def _zai_base_url() -> str:
    """Resolve z.ai base URL.

    Z.ai is OpenAI-SDK compatible but uses a different base path.
    Docs: https://docs.z.ai/guides/develop/openai/python

    - General endpoint: https://api.z.ai/api/paas/v4/
    - Coding endpoint (GLM Coding Plan): https://api.z.ai/api/coding/paas/v4/

    You can override with ZAI_BASE_URL directly.
    """
    explicit = os.getenv("ZAI_BASE_URL")
    if explicit:
        return explicit

    endpoint = os.getenv("ZAI_ENDPOINT", "general").lower().strip()
    if endpoint == "coding":
        return "https://api.z.ai/api/coding/paas/v4/"
    return "https://api.z.ai/api/paas/v4/"


def _zai_model_info(model: str) -> Dict[str, Any]:
    """Return ModelInfo for z.ai models.

    autogen-ext requires explicit model_info when the model name isn't a known OpenAI model
    (e.g. glm-4.7). We provide a safe default here.

    You can override by setting ZAI_MODEL_INFO_JSON to a JSON object.
    Required fields: vision, function_calling, json_output, family.
    """

    # Allow full override via env var (useful if you need to toggle capabilities).
    raw = os.getenv("ZAI_MODEL_INFO_JSON")
    if raw:
        import json

        return json.loads(raw)

    # Conservative defaults for GLM chat models.
    return {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "structured_output": False,
        "family": ModelFamily.UNKNOWN,
    }


def get_provider_settings() -> Dict[str, str]:
    """Return provider name and base URL resolved from env."""
    provider = _get_provider()
    
    if provider == "openai":
        return {
            "provider": "openai",
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        }
    elif provider == "zai":
        return {
            "provider": "zai",
            "base_url": _zai_base_url(),
        }
    
    # Default to ollama
    return {
        "provider": "ollama",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


def _agent_model(role: str) -> str:
    provider = _get_provider()
    
    if provider == "openai":
        return os.getenv(f"OPENAI_MODEL_{role.upper()}", "gpt-4.1")
    elif provider == "zai":
        return os.getenv(f"ZAI_MODEL_{role.upper()}", "glm-4.7")
    
    # Default to ollama
    return os.getenv(f"OLLAMA_MODEL_{role.upper()}", "qwen2.5-coder:7b")


def get_agent_models() -> Dict[str, str]:
    """Return mapping of agent role to configured model."""
    return {role: _agent_model(role) for role in AGENT_TEMPERATURES.keys()}


# Snapshot at import for quick access (used by main entrypoints)
AGENT_MODELS = get_agent_models()


def create_model_client(role: str):
    """Create model client for a specific agent role based on provider."""
    model = _agent_model(role)
    provider = _get_provider()
    
    if provider == "openai":
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIChatCompletionClient(model=model, base_url=base_url, api_key=api_key)
    elif provider == "zai":
        base_url = _zai_base_url()
        api_key = os.getenv("ZAI_API_KEY")
        return OpenAIChatCompletionClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            model_info=_zai_model_info(model),
        )

    # Ollama fallback
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaChatCompletionClient(model=model, base_url=base_url)


def get_model_params(role: str) -> Dict[str, Any]:
    """Get generation parameters for a specific role."""
    return {
        "temperature": AGENT_TEMPERATURES.get(role, 0.5),
        "max_tokens": 4096,
    }