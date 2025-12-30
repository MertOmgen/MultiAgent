"""Orchestration logic for multi-agent workflows using new AutoGen API."""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.ui import Console

from app.agents.designer import create_designer_agent
from app.agents.backend import create_backend_agent
from app.agents.frontend import create_frontend_agent
from app.agents.qa import create_qa_agent


def save_chat_history(messages: List[Any], run_id: str = None) -> Path:
    """
    Save chat history to outputs/chat_history/.
    
    Args:
        messages: List of chat messages
        run_id: Optional run identifier
        
    Returns:
        Path to saved file
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_dir = Path("./outputs/chat_history")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"chat_{run_id}.json"
    
    # Convert messages to serializable format
    serializable_messages = []
    for msg in messages:
        if hasattr(msg, 'model_dump'):
            try:
                # Try to serialize with model_dump
                msg_dict = msg.model_dump()
                # Convert datetime objects recursively
                serializable_messages.append(_convert_datetime_recursive(msg_dict))
            except Exception as e:
                # Fallback to string representation
                serializable_messages.append({"error": str(e), "message": str(msg)})
        else:
            serializable_messages.append(str(msg))
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "messages": serializable_messages
        }, f, indent=2, cls=DateTimeEncoder)
    
    return output_file


def _convert_datetime_recursive(obj):
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetime_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_recursive(item) for item in obj]
    else:
        return obj


class SequentialWorkflow:
    """
    Sequential workflow using RoundRobinGroupChat:
    Designer → Backend → Frontend → QA
    """
    
    def __init__(self, outputs_dir: str = "./outputs"):
        """
        Initialize the sequential workflow.
        
        Args:
            outputs_dir: Base directory for outputs
        """
        self.outputs_dir = Path(outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create agents
        print("Initializing agents...")
        self.designer = create_designer_agent()
        self.backend = create_backend_agent()
        self.frontend = create_frontend_agent()
        self.qa = create_qa_agent()
        
        print("✅ All agents initialized")
    
    async def run_async(self, requirement: str, max_rounds: int = 12) -> Dict[str, Any]:
        """
        Run the sequential workflow asynchronously.
        
        Args:
            requirement: User requirement/request
            max_rounds: Maximum conversation rounds
            
        Returns:
            Dictionary with results and metadata
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n{'=' * 60}")
        print(f"Starting workflow run: {run_id}")
        print(f"{'=' * 60}")
        print(f"\n📋 Requirement:\n{requirement}\n")
        
        # Create round-robin group chat
        participants = [self.designer, self.backend, self.frontend, self.qa]
        
        # Create termination condition
        termination = MaxMessageTermination(max_messages=max_rounds) | TextMentionTermination("TERMINATE")
        
        team = RoundRobinGroupChat(
            participants=participants,
            termination_condition=termination,
        )
        
        print("🚀 Starting multi-agent conversation...\n")
        
        try:
            # Run the team and stream to console
            result = await Console(
                team.run_stream(task=requirement)
            )
            
            # Get messages from result
            messages = result.messages if hasattr(result, 'messages') else []
            
            # Save chat history
            chat_file = save_chat_history(messages, run_id)
            
            print(f"\n{'=' * 60}")
            print(f"✅ Workflow completed: {run_id}")
            print(f"💾 Chat history saved to: {chat_file}")
            print(f"{'=' * 60}")
            
            return {
                "run_id": run_id,
                "status": "completed",
                "messages": messages,
                "chat_file": str(chat_file),
            }
            
        except Exception as e:
            print(f"\n❌ Error during workflow: {e}")
            import traceback
            traceback.print_exc()
            return {
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
            }
    
    def run(self, requirement: str, max_rounds: int = 12) -> Dict[str, Any]:
        """
        Run the sequential workflow (synchronous wrapper).
        
        Args:
            requirement: User requirement/request
            max_rounds: Maximum conversation rounds
            
        Returns:
            Dictionary with results and metadata
        """
        return asyncio.run(self.run_async(requirement, max_rounds))
