"""Error Agent - Specialized debugging and error resolution."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_error_agent(work_dir: str = "./outputs/error_agent") -> AssistantAgent:
    """
    Create the Error Agent for specialized debugging and error resolution.
    
    Args:
        work_dir: Working directory for error analysis artifacts
        
    Returns:
        Configured AssistantAgent for error debugging
    """
    # Work directory will be created on-demand when saving artifacts
    
    # Load system prompt
    system_message = load_prompt("error_agent")
    
    # Get model client for this agent (uses temperature 0.3 for precise debugging)
    model_client = create_model_client("error_agent")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="ErrorAgent",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
