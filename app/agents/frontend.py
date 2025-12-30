"""Frontend Engineer Agent."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_frontend_agent(work_dir: str = "./outputs/frontend") -> AssistantAgent:
    """
    Create the Frontend agent.
    
    Args:
        work_dir: Working directory for frontend artifacts
        
    Returns:
        Configured AssistantAgent for frontend implementation
    """
    # Ensure work directory exists
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    
    # Load system prompt
    system_message = load_prompt("frontend")
    
    # Get model client for this agent
    model_client = create_model_client("frontend")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="Frontend",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
