"""Software Designer Agent."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_designer_agent(work_dir: str = "./outputs/design") -> AssistantAgent:
    """
    Create the Designer agent.
    
    Args:
        work_dir: Working directory for design artifacts
        
    Returns:
        Configured AssistantAgent for design tasks
    """
    # Ensure work directory exists
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    
    # Load system prompt
    system_message = load_prompt("designer")
    
    # Get model client for this agent
    model_client = create_model_client("designer")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="Designer",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
