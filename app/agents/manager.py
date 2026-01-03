"""Manager Agent - Project coordination and strategic oversight."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_manager_agent(work_dir: str = "./outputs/manager") -> AssistantAgent:
    """
    Create the Manager agent.
    
    Args:
        work_dir: Working directory for management artifacts
        
    Returns:
        Configured AssistantAgent for project management
    """
    # Work directory will be created on-demand when saving artifacts
    
    # Load system prompt
    system_message = load_prompt("manager")
    
    # Get model client for this agent
    model_client = create_model_client("manager")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="Manager",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
