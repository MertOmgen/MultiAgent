"""
MultiAgent Orchestrator - Main Entry Point

This is the main orchestrator for the 4-agent software development workflow:
Designer → Backend → Frontend → QA
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.llm_config import AGENT_MODELS
from app.orchestration.groupchat import SequentialWorkflow

# Load environment variables
load_dotenv()


def main():
    """Main orchestration entry point."""
    print("=" * 60)
    print("MultiAgent Software Development Workflow")
    print("=" * 60)
    print("\nInitializing local LLM-based multi-agent system...")
    print(f"Base URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    
    print("\n📋 Agent Model Assignments:")
    for agent_role, model in AGENT_MODELS.items():
        print(f"  • {agent_role.capitalize():10s} → {model}")
    
    print("\n🔄 Workflow: Designer → Backend → Frontend → QA")
    print("=" * 60)
    
    # Example requirement
    requirement = """
    Create a simple User Registration API with the following features:
    
    1. User can register with email and password
    2. Email must be unique
    3. Password must be at least 8 characters
    4. Return a success message with user ID upon registration
    5. Return appropriate error messages for validation failures
    
    Keep it minimal - just the core registration flow.
    """
    
    try:
        # Initialize workflow
        workflow = SequentialWorkflow()
        
        # Run the multi-agent workflow
        result = workflow.run(requirement, max_rounds=12)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Workflow Summary")
        print("=" * 60)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Run ID: {result.get('run_id', 'N/A')}")
        if 'chat_file' in result:
            print(f"Chat History: {result['chat_file']}")
        print("\n📁 Check outputs/ folder for generated artifacts")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
