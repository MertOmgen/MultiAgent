"""Utilities for loading agent prompts and creating agents."""

from pathlib import Path
from typing import Dict


def load_prompt(agent_role: str) -> str:
    """
    Load system prompt for a specific agent role.
    
    Args:
        agent_role: Agent role (designer, backend, frontend, qa)
        
    Returns:
        System prompt content
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_dir = Path(__file__).parent / "prompts"
    prompt_file = prompt_dir / f"{agent_role}.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    return prompt_file.read_text(encoding="utf-8")


def get_all_prompts() -> Dict[str, str]:
    """
    Load all agent prompts.
    
    Returns:
        Dictionary mapping agent role to prompt content
    """
    roles = ["designer", "backend", "frontend", "qa"]
    return {role: load_prompt(role) for role in roles}
