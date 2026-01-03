"""DevOps Agent - Handles Docker, container orchestration, and infrastructure setup."""

from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from app.config.llm_config import create_model_client
from app.agents.utils import load_prompt


def create_devops_agent(work_dir: str = "./outputs/devops") -> AssistantAgent:
    """
    Create DevOps Agent for infrastructure and container management.
    
    Responsibilities:
    - Create Docker configurations (Dockerfile, docker-compose.yml)
    - Set up development environments (PostgreSQL, Redis, etc.)
    - Build and run containers
    - Configure networking and ports
    - Provide service URLs
    - Health checks and monitoring setup
    
    Temperature: 0.3 (precise, deterministic operations)
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    
    system_message = load_prompt("devops")
    model_client = create_model_client("devops_agent")
    
    return AssistantAgent(
        name="DevOps",
        model_client=model_client,
        system_message=system_message,
    )
