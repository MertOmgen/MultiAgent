"""Backend Engineer Agent."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_backend_agent(work_dir: str = "./outputs/backend") -> AssistantAgent:
    """
    Create the Backend agent.
    
    Args:
        work_dir: Working directory for backend artifacts
        
    Returns:
        Configured AssistantAgent for backend implementation
    """
    # Ensure work directory exists
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    
    # Load system prompt
    system_message = load_prompt("backend")
    
    # Get model client for this agent
    model_client = create_model_client("backend")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="Backend",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
