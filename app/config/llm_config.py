"""LLM Configuration for Ollama."""

import os
from typing import Dict, Any


def get_llm_config() -> Dict[str, Any]:
    """
    Get LLM configuration for Ollama.
    
    Returns:
        Dictionary with Ollama configuration for AutoGen.
    """
    return {
        "config_list": [
            {
                "model": os.getenv("OLLAMA_MODEL", "llama3.1"),
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "api_key": "ollama",  # Ollama doesn't require a real key
            }
        ],
        "timeout": int(os.getenv("TIMEOUT", "300")),
        "cache_seed": None,  # Disable caching for reproducibility
    }


def get_agent_config(role: str) -> Dict[str, Any]:
    """
    Get agent-specific configuration.
    
    Args:
        role: Agent role (designer, backend, frontend, qa)
        
    Returns:
        Agent configuration dictionary.
    """
    base_config = get_llm_config()
    
    # Role-specific settings can be added here
    role_configs = {
        "designer": {"temperature": 0.7},
        "backend": {"temperature": 0.5},
        "frontend": {"temperature": 0.5},
        "qa": {"temperature": 0.3},
    }
    
    config = base_config.copy()
    if role in role_configs:
        config.update(role_configs[role])

    return config