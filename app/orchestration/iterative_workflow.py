"""Iterative workflow with QA feedback loops."""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination

from app.agents.designer import create_designer_agent
from app.agents.backend import create_backend_agent
from app.agents.frontend import create_frontend_agent
from app.agents.qa import create_qa_agent
from app.orchestration.artifact_saver import ArtifactSaver
from app.orchestration.npm_installer import NpmInstaller
from app.orchestration.groupchat import save_chat_history
from app.orchestration.project_manager import ProjectManager, Project
from app.orchestration.git_manager import GitManager


class IterativeWorkflow:
    """
    Iterative workflow with QA feedback loops:
    Designer → Backend → Frontend → QA → (if issues) → Backend/Frontend → QA → ...
    
    Supports both project-based (continuous development) and standalone modes.
    """
    
    def __init__(self, outputs_dir: str = "./outputs", max_iterations: int = 3):
        """
        Initialize the iterative workflow.
        
        Args:
            outputs_dir: Base directory for outputs
            max_iterations: Maximum number of QA feedback iterations
        """
        self.outputs_dir = Path(outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.max_iterations = max_iterations
        
        # Initialize utilities
        self.artifact_saver = ArtifactSaver(outputs_dir)
        self.npm_installer = NpmInstaller(str(self.outputs_dir / "frontend"))
        
        # Initialize project manager
        self.project_manager = ProjectManager(outputs_dir)
        
        # Create agents
        print("Initializing agents...")
        self.designer = create_designer_agent()
        self.backend = create_backend_agent()
        self.frontend = create_frontend_agent()
        self.qa = create_qa_agent()
        
        print("✅ All agents initialized")
    
    def _check_qa_feedback(self, qa_message: str) -> Dict[str, Any]:
        """
        Parse QA feedback to determine if iteration is needed.
        
        Args:
            qa_message: QA agent's message content
            
        Returns:
            Dictionary with iteration info
        """
        # Check for iteration signals
        needs_iteration = "ITERATION REQUIRED" in qa_message or "CLARIFICATION NEEDED" in qa_message
        all_tests_passed = "ALL TESTS PASSED" in qa_message
        
        # Extract agent mentions - STRICT format: must have @ symbol and "Agent:" suffix
        # This prevents false matches like "Backend Agent: Please review..."
        backend_fixes = "@Backend Agent:" in qa_message
        frontend_fixes = "@Frontend Agent:" in qa_message
        
        # Log what we found for debugging
        if needs_iteration:
            print(f"🔍 QA Feedback Analysis:")
            print(f"   - Needs iteration: {needs_iteration}")
            print(f"   - Backend fixes needed: {backend_fixes}")
            print(f"   - Frontend fixes needed: {frontend_fixes}")
            if not backend_fixes and not frontend_fixes:
                print("   ⚠️  WARNING: ITERATION REQUIRED but no agents mentioned with @AgentName: format")
        
        return {
            "needs_iteration": needs_iteration,
            "all_tests_passed": all_tests_passed,
            "needs_backend_fix": backend_fixes,
            "needs_frontend_fix": frontend_fixes,
        }
    
    async def run_async(
        self, 
        requirement: str, 
        max_rounds: int = 20,
        project_name: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the iterative workflow asynchronously.
        
        Args:
            requirement: User requirement/request
            max_rounds: Maximum conversation rounds per iteration
            project_name: Optional project name for continuous development
            task_description: Description of this specific task/iteration
            
        Returns:
            Dictionary with results and metadata
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Project-based or standalone mode
        project = None
        git_manager = None
        
        if project_name:
            # Project mode: Load existing context
            print(f"\n{'=' * 60}")
            print(f"📁 Project Mode: {project_name}")
            print(f"{'=' * 60}")
            
            project = self.project_manager.get_or_create_project(project_name)
            git_manager = GitManager(project.project_dir)
            
            # Initialize Git if needed
            if git_manager.check_available():
                git_manager.init_repo()
            else:
                print("   ⚠️  Git not available. Skipping version control.")
                git_manager = None
            
            # Load existing project context
            if project.file_tree or project.important_files:
                print(f"\n📚 Loading existing project context...")
                existing_context = self.project_manager.load_project_context(project_name)
                print(f"   ✅ Loaded {len(project.important_files)} files")
                
                # Add context to requirement
                requirement = f"""{requirement}

=== EXISTING PROJECT CONTEXT ===

{existing_context}

=== END EXISTING CONTEXT ===

Build upon the existing code above. Update or extend existing files as needed."""
            else:
                print(f"   ℹ️  New project - no existing context")
        
        print(f"\n{'=' * 60}")
        print(f"Starting iterative workflow: {run_id}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"{'=' * 60}")
        print(f"\n📋 Requirement:\n{requirement}\n")
        
        iteration = 0
        all_messages = []
        
        try:
            while iteration < self.max_iterations:
                iteration += 1
                print(f"\n{'🔄' * 30}")
                print(f"ITERATION {iteration}/{self.max_iterations}")
                print(f"{'🔄' * 30}\n")
                
                # Determine which agents to include in this iteration
                if iteration == 1:
                    # First iteration: Run agents SEQUENTIALLY to prevent context pollution
                    # Designer -> Backend -> Frontend -> QA
                    # Each agent only sees previous agents, not peers
                    
                    print("🎯 Round 1: Designer")
                    designer_result = await self.designer.run(task=requirement)
                    all_messages.extend(designer_result.messages)
                    
                    print("\n🎯 Round 2: Backend (sees Designer only)")
                    backend_result = await self.backend.run(task=f"{requirement}\n\nDesigner has provided the specifications above.")
                    all_messages.extend(backend_result.messages)
                    
                    print("\n🎯 Round 3: Frontend (sees Designer only, NOT Backend)")
                    # Frontend should NOT see Backend's C# code!
                    frontend_task = f"{requirement}\n\nDesigner has provided specifications. Backend is implementing the API separately. Build the Vue 3 frontend that calls the backend API."
                    frontend_result = await self.frontend.run(task=frontend_task)
                    all_messages.extend(frontend_result.messages)
                    
                    print("\n🎯 Round 4: QA (reviews all)")
                    # QA needs to see all previous outputs - include them in the task
                    designer_output = next((msg.content for msg in designer_result.messages if hasattr(msg, 'source') and msg.source == 'Designer'), "")
                    backend_output = next((msg.content for msg in backend_result.messages if hasattr(msg, 'source') and msg.source == 'Backend'), "")
                    frontend_output = next((msg.content for msg in frontend_result.messages if hasattr(msg, 'source') and msg.source == 'Frontend'), "")
                    
                    qa_task = f"""Review the following outputs and create comprehensive test plans with test files:

=== DESIGNER OUTPUT ===
{designer_output}

=== BACKEND OUTPUT ===
{backend_output}

=== FRONTEND OUTPUT ===
{frontend_output}

===

Create test plans and test code files for this implementation."""
                    
                    qa_result = await self.qa.run(task=qa_task)
                    all_messages.extend(qa_result.messages)
                    
                else:
                    # Subsequent iterations: only agents that need to fix issues + QA
                    # Check previous QA feedback
                    last_qa_msg = next((msg.content for msg in reversed(all_messages) 
                                       if hasattr(msg, 'source') and 'qa' in msg.source.lower()), "")
                    
                    feedback = self._check_qa_feedback(last_qa_msg)
                    
                    if feedback["all_tests_passed"]:
                        print("✅ All tests passed! Workflow complete.")
                        break
                    
                    if not feedback["needs_iteration"]:
                        print("⚠️  No clear iteration signal from QA. Ending workflow.")
                        break
                    
                    # Run fixes SEPARATELY for Backend and Frontend
                    if feedback["needs_backend_fix"]:
                        print(f"\n🎯 Iteration {iteration}: Backend Fixes")
                        backend_result = await self.backend.run(task=f"Address QA feedback:\n\n{last_qa_msg}")
                        all_messages.extend(backend_result.messages)
                    
                    if feedback["needs_frontend_fix"]:
                        print(f"\n🎯 Iteration {iteration}: Frontend Fixes")
                        frontend_result = await self.frontend.run(task=f"Address QA feedback:\n\n{last_qa_msg}")
                        all_messages.extend(frontend_result.messages)
                    
                    if not feedback["needs_backend_fix"] and not feedback["needs_frontend_fix"]:
                        print("⚠️  No agents to fix issues. Ending workflow.")
                        break
                    
                    print(f"\n🎯 Iteration {iteration}: QA Re-test")
                    qa_result = await self.qa.run(task="Re-test the fixes and create updated test results.")
                    all_messages.extend(qa_result.messages)
                
                # Save artifacts from this iteration
                print(f"\n{'=' * 60}")
                print(f"💾 Saving artifacts (iteration {iteration})...")
                
                # Get messages from this iteration only (not all_messages)
                iteration_messages = []
                if iteration == 1:
                    # First iteration - get messages from all 4 rounds
                    start_idx = 0
                else:
                    # Subsequent iterations - get messages added in this iteration
                    # This is a bit tricky - we need to track where this iteration started
                    start_idx = len(all_messages) - 10  # Approximate, get last ~10 messages
                
                iteration_messages = all_messages[start_idx:]
                
                # Determine output directory based on mode
                if project:
                    # Project mode: Save to project directory
                    output_base = project.project_dir
                    iteration_dir = None  # Don't use iteration subdirectory for projects
                else:
                    # Standalone mode: Use run_id based directory
                    output_base = self.artifact_saver.base_dir
                    iteration_dir = f"{run_id}_iter{iteration}"
                
                for msg in iteration_messages:
                    if hasattr(msg, 'source') and hasattr(msg, 'content'):
                        agent_name = msg.source
                        content = msg.content
                        
                        agent_map = {
                            "designer_agent": "Designer",
                            "backend_agent": "Backend",
                            "frontend_agent": "Frontend",
                            "qa_agent": "QA",
                            "designer": "Designer",
                            "backend": "Backend",
                            "frontend": "Frontend",
                            "qa": "QA"
                        }
                        
                        standardized_name = agent_map.get(agent_name.lower(), agent_name.title())
                        
                        if standardized_name in self.artifact_saver.AGENT_DIRS:
                            print(f"\n📂 Processing {standardized_name} output...")
                            
                            # Validate agent output against role boundaries
                            if standardized_name == "Backend":
                                # Backend should only output C#/.NET files
                                if any(ext in content for ext in ['.vue', '.js', '.ts', '.jsx', '.tsx']) and 'FILE:' in content:
                                    print("  ⚠️  WARNING: Backend agent appears to be generating frontend files!")
                                    print("  This violates role boundaries. Check prompts and iteration routing.")
                            elif standardized_name == "Frontend":
                                # Frontend should only output Vue/TypeScript/JavaScript files
                                if any(ext in content for ext in ['.cs', '.csproj', '.sln']) and 'FILE:' in content:
                                    print("  ⚠️  WARNING: Frontend agent appears to be generating backend files!")
                                    print("  This violates role boundaries. Check prompts and iteration routing.")
                            
                            if project:
                                # Project mode: Save directly to project folders (backend/, frontend/, tests/)
                                self.artifact_saver.save_agent_artifacts(standardized_name, content, iteration_dir, base_dir=str(project.project_dir))
                            else:
                                # Standalone mode: Save to outputs/{agent}/{run_id}/
                                self.artifact_saver.save_agent_artifacts(standardized_name, content, iteration_dir)
                            
                            # Auto-install npm dependencies if Frontend generated package.json
                            if standardized_name == "Frontend":
                                if project:
                                    frontend_dir = project.project_dir / "frontend"
                                else:
                                    # artifact_saver saves to outputs/frontend/{iteration_dir}
                                    frontend_dir = self.artifact_saver.base_dir / "frontend" / iteration_dir
                                
                                package_json = frontend_dir / "package.json"
                                
                                # Check if package.json exists (might be in outputs/frontend/ or just frontend/)
                                if not package_json.exists() and not project:
                                    # Try without outputs prefix
                                    alt_frontend_dir = self.outputs_dir / "frontend" / iteration_dir
                                    alt_package_json = alt_frontend_dir / "package.json"
                                    if alt_package_json.exists():
                                        frontend_dir = alt_frontend_dir
                                        package_json = alt_package_json
                                
                                if package_json.exists():
                                    print(f"\n{'=' * 60}")
                                    print("🔧 Frontend Setup")
                                    print(f"{'=' * 60}")
                                    
                                    if self.npm_installer.check_npm_available():
                                        self.npm_installer.install_dependencies_sync(frontend_dir)
                                    else:
                                        print("  ⚠️  npm not found. Skipping dependency installation.")
                
                # Update project metadata if in project mode
                if project and git_manager:
                    # Refresh file tree and important files
                    self.project_manager.refresh_project(project_name)
                    
                    # Add task to history
                    if task_description:
                        self.project_manager.add_task_to_history(project_name, task_description, run_id)
                    
                    # Git commit
                    commit_msg = task_description or f"Iteration {iteration}: {requirement[:50]}"
                    git_manager.commit(commit_msg)
            
            # Save complete chat history
            if project:
                chat_file = project.project_dir / "chat_history" / f"{run_id}.md"
                chat_file.parent.mkdir(exist_ok=True)
                # Manual save since we have custom path
                import json
                chat_content = "# Chat History\n\n"
                for msg in all_messages:
                    if hasattr(msg, 'source') and hasattr(msg, 'content'):
                        chat_content += f"## {msg.source}\n\n{msg.content}\n\n"
                chat_file.write_text(chat_content, encoding='utf-8')
            else:
                chat_file = save_chat_history(all_messages, f"{run_id}_complete")
            
            print(f"\n{'=' * 60}")
            print(f"✅ Iterative workflow completed: {run_id}")
            print(f"   Total iterations: {iteration}")
            if project:
                print(f"📁 Project: {project.name}")
                print(f"   Location: {project.project_dir}")
            print(f"💾 Complete chat history: {chat_file}")
            print(f"{'=' * 60}")
            
            return {
                "run_id": run_id,
                "status": "completed",
                "iterations": iteration,
                "messages": all_messages,
                "chat_file": str(chat_file),
                "project_name": project_name if project else None,
            }
            
        except Exception as e:
            print(f"\n❌ Error during workflow: {e}")
            import traceback
            traceback.print_exc()
            return {
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
                "iterations": iteration,
            }
    
    def run(
        self, 
        requirement: str, 
        max_rounds: int = 20,
        project_name: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the iterative workflow (synchronous wrapper).
        
        Args:
            requirement: User requirement/request
            max_rounds: Maximum conversation rounds per iteration
            project_name: Optional project name for continuous development
            task_description: Description of this specific task/iteration
            
        Returns:
            Dictionary with results and metadata
        """
        return asyncio.run(self.run_async(requirement, max_rounds, project_name, task_description))
