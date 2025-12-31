"""LLM Configuration for Ollama with new AutoGen API."""

import os
from typing import Dict, Any
from autogen_ext.models.ollama import OllamaChatCompletionClient


# Agent-specific model mapping
AGENT_MODELS = {
    "designer": os.getenv("OLLAMA_MODEL_DESIGNER", "llama3.1:8b"),
    "backend": os.getenv("OLLAMA_MODEL_BACKEND", "qwen2.5-coder:7b"),
    "frontend": os.getenv("OLLAMA_MODEL_FRONTEND", "qwen2.5-coder:7b"),
    "qa": os.getenv("OLLAMA_MODEL_QA", "qwen2.5-coder:7b"),  # Changed from deepseek-coder:6.7b for better FILE: format following
}

# Agent-specific temperature settings
AGENT_TEMPERATURES = {
    "designer": 0.7,  # More creative for architecture decisions
    "backend": 0.5,   # Balanced for code implementation
    "frontend": 0.5,  # Balanced for code implementation
    "qa": 0.3,        # More deterministic for testing
}


def create_model_client(role: str) -> OllamaChatCompletionClient:
    """
    Create Ollama model client for a specific agent role.
    
    Args:
        role: Agent role (designer, backend, frontend, qa)
        
    Returns:
        Configured OllamaChatCompletionClient
    """
    model = AGENT_MODELS.get(role, "llama3.1:8b")
    temperature = AGENT_TEMPERATURES.get(role, 0.5)
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Create Ollama client with the new API
    client = OllamaChatCompletionClient(
        model=model,
        base_url=base_url,
        # Note: Temperature and other parameters are set during inference in new API
    )
    
    return client


def get_model_params(role: str) -> Dict[str, Any]:
    """
    Get model generation parameters for a specific role.
    
    Args:
        role: Agent role (designer, backend, frontend, qa)
        
    Returns:
        Dictionary with generation parameters
    """
    return {
        "temperature": AGENT_TEMPERATURES.get(role, 0.5),
        "max_tokens": 4096,
    }