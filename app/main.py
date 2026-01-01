"""
MultiAgent Orchestrator - Main Entry Point

This is the main orchestrator for the 4-agent software development workflow:
Designer → Backend → Frontend → QA
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.llm_config import AGENT_MODELS, get_agent_models, get_provider_settings
from app.orchestration.iterative_workflow import IterativeWorkflow

# Load environment variables
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-agent orchestrator")
    parser.add_argument("--task", required=False, default=None, help="User task/requirement for agents")
    parser.add_argument("--project", required=False, default="default_project", help="Project name for outputs")
    parser.add_argument("--max-iterations", type=int, default=3, help="Maximum QA feedback iterations")
    return parser.parse_args()


def main():
    """Main orchestration entry point."""
    args = parse_args()
    requirement = args.task or "Create a simple User Registration API with email/password validation."
    project_name = args.project.strip() or "default_project"
    max_iterations = args.max_iterations

    provider = get_provider_settings()
    agent_models = get_agent_models()

    print("=" * 60)
    print("MultiAgent Software Development Workflow")
    print("=" * 60)
    print("\nInitializing local LLM-based multi-agent system...")
    print(f"Provider: {provider['provider']}")
    print(f"Base URL: {provider['base_url']}")
    
    print("\n📋 Agent Model Assignments:")
    for agent_role, model in agent_models.items():
        print(f"  • {agent_role.capitalize():10s} → {model}")
    
    print("\n🔄 Workflow Mode: ITERATIVE (with QA feedback loops)")
    print(f"   Max Iterations: {max_iterations}")
    print(f"   Project: {project_name}")
    print("=" * 60)
    
    try:
        workflow = IterativeWorkflow(outputs_dir=f"./outputs/{project_name}", max_iterations=max_iterations, project_name=project_name)
        result = workflow.run(requirement, max_rounds=12)
        
        print("\n" + "=" * 60)
        print("Workflow Summary")
        print("=" * 60)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Run ID: {result.get('run_id', 'N/A')}")
        print(f"Iterations: {result.get('iterations', 'N/A')}")
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
