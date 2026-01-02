"""
MultiAgent Orchestrator - Main Entry Point

4-Agent Software Development Workflow:
Designer → Backend → Frontend → QA → (iterate if needed)

Usage:
    python -m app.main "Create a user login feature"
    python -m app.main --project MyApp --task "Add user registration"
    python -m app.main --list-projects
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.llm_config import get_agent_models, get_provider_settings
from app.orchestration.project_manager import ProjectManager

# Load environment variables
load_dotenv()


def print_header():
    """Print application header."""
    print("=" * 60)
    print("🤖 MultiAgent Software Development System")
    print("=" * 60)
    provider = get_provider_settings()
    print(f"\nLLM Provider: {provider['provider']}")
    print(f"LLM Base URL: {provider['base_url']}")
    print("\n📋 Agent Assignments:")
    for role, model in get_agent_models().items():
        print(f"   {role:10s} → {model}")


def list_projects():
    """List all existing projects."""
    # Keep consistent with workflow default outputs dir (projects live under outputs/<project>/)
    pm = ProjectManager("./outputs")
    projects = pm.list_projects()
    
    if projects:
        print("\n📁 Existing Projects:")
        for name in projects:
            project = pm.get_or_create_project(name)
            print(f"\n  • {name}")
            if 'created_at' in project.metadata:
                print(f"    Created: {project.metadata['created_at'][:10]}")
            if 'iterations' in project.metadata:
                print(f"    Tasks: {project.metadata['iterations']}")
    else:
        print("\n📁 No existing projects found.")
        print("   Create one with: python -m app.main --project MyProject \"requirement\"")


def get_default_requirement() -> str:
    """Get default example requirement."""
    return """
Create a simple User Registration API with:

1. User can register with email and password
2. Email must be unique
3. Password must be at least 8 characters
4. Return success message with user ID
5. Return appropriate error messages

Keep it minimal - just the core registration flow.
"""


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MultiAgent Software Development System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main "Create a todo list API"
  python -m app.main --project TodoApp "Create a todo list API"
  python -m app.main --project TodoApp --task "Add user authentication"
  python -m app.main --list-projects
  python -m app.main --max-iterations 5 "Complex feature..."
        """
    )
    
    parser.add_argument(
        "requirement", 
        nargs="?",
        help="Development requirement (use quotes for multi-word)"
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Project name for persistent development"
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Task description (used with --project)"
    )
    parser.add_argument(
        "--list-projects", "-l",
        action="store_true",
        help="List all existing projects"
    )
    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=3,
        help="Maximum QA feedback iterations (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Handle --list-projects
    if args.list_projects:
        print_header()
        list_projects()
        return 0
    
    # Determine requirement
    if args.project and args.task:
        requirement = args.task
    elif args.requirement:
        requirement = args.requirement
    else:
        requirement = get_default_requirement()
        print("\n💡 No requirement provided. Using default example.")
    
    # Print header
    print_header()
    
    print(f"\n🔄 Workflow: ITERATIVE (max {args.max_iterations} iterations)")
    if args.project:
        print(f"📁 Project: {args.project}")
    
    print("\n" + "=" * 60)
    print("📋 Requirement:")
    print("-" * 60)
    print(requirement.strip())
    print("=" * 60)
    
    try:
        from app.orchestration.iterative_workflow import IterativeWorkflow
        workflow = IterativeWorkflow(max_iterations=args.max_iterations)
        
        # Run workflow
        result = workflow.run(
            requirement=requirement,
            project_name=args.project,
            task_description=args.task,
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Workflow Summary")
        print("=" * 60)
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Run ID: {result.get('run_id', 'N/A')}")
        print(f"   Iterations: {result.get('iterations', 'N/A')}")
        
        if result.get('project_name'):
            print(f"   Project: {result['project_name']}")
        
        if result.get('chat_file'):
            print(f"   Chat Log: {result['chat_file']}")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
        
        print("=" * 60)
        
        if args.project:
            print(f"\n📁 Project files: outputs/{args.project}/")
        else:
            print("\n📁 Output files: outputs/")
        
        return 0 if result.get('status') == 'completed' else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
