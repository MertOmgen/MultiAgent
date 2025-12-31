"""
MultiAgent Orchestrator - Main Entry Point

This is the main orchestrator for the 4-agent software development workflow:
Designer → Backend → Frontend → QA

Supports two modes:
1. Standalone: Creates isolated output folders per run
2. Project: Continuous development on a named project across multiple runs
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.llm_config import AGENT_MODELS
from app.orchestration.groupchat import SequentialWorkflow
from app.orchestration.iterative_workflow import IterativeWorkflow
from app.orchestration.project_manager import ProjectManager

# Load environment variables
load_dotenv()


def main():
    """Main orchestration entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="MultiAgent Software Development Workflow")
    parser.add_argument("--project", type=str, help="Project name for continuous development")
    parser.add_argument("--task", type=str, help="Task description for this iteration")
    parser.add_argument("--list-projects", action="store_true", help="List existing projects")
    parser.add_argument("--max-iterations", type=int, default=3, help="Maximum QA feedback iterations")
    parser.add_argument("requirement", nargs="?", help="Development requirement (or use --task with --project)")
    
    args = parser.parse_args()
    
    # List projects if requested
    if args.list_projects:
        pm = ProjectManager()
        projects = pm.list_projects()
        
        if projects:
            print("📁 Existing Projects:")
            for project_name in projects:
                project = pm.get_or_create_project(project_name)
                print(f"\n  • {project_name}")
                if 'created_at' in project.metadata:
                    print(f"    Created: {project.metadata['created_at']}")
                if 'iterations' in project.metadata:
                    print(f"    Iterations: {project.metadata['iterations']}")
        else:
            print("📁 No existing projects found.")
        
        return
    
    print("=" * 60)
    print("MultiAgent Software Development Workflow")
    print("=" * 60)
    print("\nInitializing local LLM-based multi-agent system...")
    print(f"Base URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    
    print("\n📋 Agent Model Assignments:")
    for agent_role, model in AGENT_MODELS.items():
        print(f"  • {agent_role.capitalize():10s} → {model}")
    
    print("\n🔄 Workflow Mode: ITERATIVE (with QA feedback loops)")
    print(f"   Max Iterations: {args.max_iterations}")
    
    # Determine mode and requirement
    project_name = args.project
    task_description = args.task
    
    if project_name:
        print(f"\n📁 Project Mode: {project_name}")
        if task_description:
            requirement = task_description
            print(f"   Task: {task_description}")
        else:
            requirement = args.requirement
            if not requirement:
                print("\n❌ Error: When using --project, provide either --task or a requirement")
                return
    else:
        print("\n📄 Standalone Mode")
        requirement = args.requirement
        if not requirement:
            # Use default example
            requirement = """
Create a simple User Registration API with the following features:

1. User can register with email and password
2. Email must be unique
3. Password must be at least 8 characters
4. Return a success message with user ID upon registration
5. Return appropriate error messages for validation failures

Keep it minimal - just the core registration flow.
"""
            print("\n   Using default example requirement (User Registration API)")
    
    print("=" * 60)
    
    try:
        # Initialize iterative workflow (with QA feedback loops)
        workflow = IterativeWorkflow(max_iterations=args.max_iterations)
        
        # Run the multi-agent workflow
        result = workflow.run(
            requirement=requirement,
            max_rounds=12,
            project_name=project_name,
            task_description=task_description
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("Workflow Summary")
        print("=" * 60)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Run ID: {result.get('run_id', 'N/A')}")
        print(f"Iterations: {result.get('iterations', 'N/A')}")
        if result.get('project_name'):
            print(f"Project: {result['project_name']}")
        if 'chat_file' in result:
            print(f"Chat History: {result['chat_file']}")
        
        if project_name:
            print(f"\n📁 Project files saved to: outputs/projects/{project_name}/")
        else:
            print("\n📁 Check outputs/ folder for generated artifacts")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
