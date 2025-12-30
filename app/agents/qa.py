"""QA Engineer Agent."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_qa_agent(work_dir: str = "./outputs/qa") -> AssistantAgent:
    """
    Create the QA agent.
    
    Args:
        work_dir: Working directory for QA artifacts
        
    Returns:
        Configured AssistantAgent for QA tasks
    """
    # Ensure work directory exists
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    
    # Load system prompt
    system_message = load_prompt("qa")
    
    # Get model client for this agent
    model_client = create_model_client("qa")
    
    # Create agent with new API
    agent = AssistantAgent(
        name="QA",
        model_client=model_client,
        system_message=system_message,
    )
    
    return agent
