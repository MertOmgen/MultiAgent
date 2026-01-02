"""
Iterative Workflow v2 - Clean implementation with QA feedback loops.

Workflow: Designer → Backend → Frontend → QA → (fix loop if needed)

Key improvements:
- Cleaner agent execution flow
- Better separation of concerns
- Improved error handling
- Clear iteration tracking
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.agents.designer import create_designer_agent
from app.agents.backend import create_backend_agent
from app.agents.frontend import create_frontend_agent
from app.agents.qa import create_qa_agent
from app.orchestration.artifact_saver import ArtifactSaver
from app.orchestration.npm_installer import NpmInstaller
from app.orchestration.project_manager import ProjectManager
from app.orchestration.git_manager import GitManager



@dataclass
class WorkflowResult:
    """Result of a workflow run."""
    run_id: str
    status: str  # 'completed', 'failed', 'max_iterations'
    iterations: int = 0
    messages: List[Any] = field(default_factory=list)
    chat_file: Optional[str] = None
    project_name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class QAFeedback:
    """Parsed QA feedback."""
    needs_iteration: bool = False
    all_passed: bool = False
    fix_backend: bool = False
    fix_frontend: bool = False
    raw_message: str = ""


class IterativeWorkflow:
    """
    Iterative multi-agent workflow with QA feedback loops.
    
    Flow:
    1. Designer creates specs
    2. Backend implements API (sees Designer output)
    3. Frontend implements UI (sees Designer output, NOT Backend code)
    4. QA reviews all outputs
    5. If issues: targeted agent fixes → QA re-test
    6. Repeat until pass or max iterations
    """
    
    def __init__(self, outputs_dir: str = "./outputs", max_iterations: int = 3):
        self.outputs_dir = Path(outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.max_iterations = max_iterations
        
        # Initialize components
        self.artifact_saver = ArtifactSaver(outputs_dir)
        self.npm_installer = NpmInstaller(str(self.outputs_dir / "frontend"))
        self.project_manager = ProjectManager(outputs_dir)
        
        # Create agents (lazy - only when needed)
        self._agents = {}
    
    def _get_agent(self, name: str):
        """Lazy-load agents."""
        if name not in self._agents:
            creators = {
                'designer': create_designer_agent,
                'backend': create_backend_agent,
                'frontend': create_frontend_agent,
                'qa': create_qa_agent,
            }
            if name in creators:
                print(f"  🤖 Initializing {name} agent...")
                self._agents[name] = creators[name]()
        return self._agents.get(name)
    
    def _parse_qa_feedback(self, message: str) -> QAFeedback:
        """Parse QA agent's feedback message."""
        feedback = QAFeedback(raw_message=message)
        
        # Check for clear signals
        feedback.all_passed = "ALL TESTS PASSED" in message
        feedback.needs_iteration = "ITERATION REQUIRED" in message or "CLARIFICATION NEEDED" in message
        
        # Check for agent mentions (strict format: @Agent Agent:)
        feedback.fix_backend = "@Backend Agent:" in message
        feedback.fix_frontend = "@Frontend Agent:" in message
        
        return feedback
    
    async def _run_agent(self, agent_name: str, task: str) -> Dict[str, Any]:
        """Run a single agent and return its output."""
        agent = self._get_agent(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not found"}
        
        print(f"\n🎯 Running {agent_name.title()} Agent...")
        result = await agent.run(task=task)
        
        # Extract content from result
        # NOTE: Some models (including GLM-* via OpenAI-compatible APIs) may emit
        # an initial planning/thinking message and then the final deliverable.
        # We want the *final* message for artifact extraction.
        content = ""
        for msg in result.messages:
            if hasattr(msg, 'source') and hasattr(msg, 'content'):
                if agent_name in str(msg.source).lower() and msg.content:
                    content = msg.content
        
        return {
            "messages": result.messages,
            "content": content,
        }
    
    def _save_artifacts(
        self, 
        agent_name: str, 
        content: str, 
        output_dir: Path,
        run_id: str
    ) -> List[Path]:
        """Save agent artifacts and handle npm install for frontend."""
        saved = self.artifact_saver.save_agent_artifacts(
            agent_name, 
            content, 
            run_id,
            base_dir=str(output_dir) if output_dir != self.outputs_dir else None
        )
        
        # Auto-install npm for frontend
        if agent_name.lower() == "frontend":
            self._try_npm_install(output_dir / "frontend")
        
        return saved
    
    def _try_npm_install(self, frontend_dir: Path):
        """Try to run npm install if package.json exists."""
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            print(f"\n📦 Installing npm dependencies...")
            if self.npm_installer.check_npm_available():
                self.npm_installer.install_dependencies_sync(frontend_dir)
            else:
                print("  ⚠️  npm not found. Run 'npm install' manually.")
    
    def _save_chat_history(
        self, 
        messages: List[Any], 
        output_dir: Path, 
        run_id: str
    ) -> Path:
        """Save chat history as markdown."""
        chat_dir = output_dir / "chat_history"
        chat_dir.mkdir(exist_ok=True)
        
        chat_file = chat_dir / f"{run_id}.md"
        
        content = "# Chat History\n\n"
        content += f"Run ID: {run_id}\n"
        content += f"Generated: {datetime.now().isoformat()}\n\n"
        content += "---\n\n"
        
        for msg in messages:
            if hasattr(msg, 'source') and hasattr(msg, 'content'):
                content += f"## {msg.source}\n\n"
                content += f"{msg.content}\n\n"
                content += "---\n\n"
        
        chat_file.write_text(content, encoding='utf-8')
        return chat_file
    
    async def run_async(
        self, 
        requirement: str,
        project_name: Optional[str] = None,
        task_description: Optional[str] = None,
        **kwargs  # Accept but ignore extra args for compatibility
    ) -> WorkflowResult:
        """
        Run the iterative workflow.
        
        Args:
            requirement: User's requirement/request
            project_name: Optional project name for persistent development
            task_description: Description of this task
            
        Returns:
            WorkflowResult with status and artifacts
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_messages = []
        
        # Determine output location
        project = None
        git_manager = None
        
        if project_name:
            project = self.project_manager.get_or_create_project(project_name)
            output_dir = project.project_dir
            
            # Initialize Git
            git_manager = GitManager(output_dir)
            if git_manager.check_available():
                git_manager.init_repo()
            else:
                git_manager = None
            
            # Load existing context
            if project.important_files:
                context = self.project_manager.load_project_context(project_name)
                requirement = f"{requirement}\n\n{context}\n\nBuild upon existing code."
        else:
            output_dir = self.outputs_dir
        
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting Iterative Workflow")
        print(f"   Run ID: {run_id}")
        print(f"   Max Iterations: {self.max_iterations}")
        if project_name:
            print(f"   Project: {project_name}")
        print(f"{'=' * 60}\n")
        
        try:
            iteration = 0
            
            while iteration < self.max_iterations:
                iteration += 1
                iter_id = f"{run_id}_iter{iteration}"
                
                print(f"\n{'🔄' * 20}")
                print(f"ITERATION {iteration}/{self.max_iterations}")
                print(f"{'🔄' * 20}")
                
                if iteration == 1:
                    # First iteration: Full pipeline
                    # Designer → Backend → Frontend → QA
                    
                    # 1. Designer
                    designer_result = await self._run_agent('designer', requirement)
                    all_messages.extend(designer_result['messages'])
                    designer_output = designer_result['content']
                    
                    print(f"\n💾 Saving Designer artifacts...")
                    self._save_artifacts('Designer', designer_output, output_dir, iter_id)
                    
                    # 2. Backend (sees Designer specs)
                    backend_task = f"{requirement}\n\n=== Designer Specifications ===\n{designer_output}"
                    backend_result = await self._run_agent('backend', backend_task)
                    all_messages.extend(backend_result['messages'])
                    backend_output = backend_result['content']
                    
                    print(f"\n💾 Saving Backend artifacts...")
                    self._save_artifacts('Backend', backend_output, output_dir, iter_id)
                    
                    # 3. Frontend (sees Designer specs, NOT Backend code to prevent confusion)
                    frontend_task = f"{requirement}\n\n=== Designer Specifications ===\n{designer_output}\n\nImplement the Vue 3 frontend. Backend API is being implemented separately."
                    frontend_result = await self._run_agent('frontend', frontend_task)
                    all_messages.extend(frontend_result['messages'])
                    frontend_output = frontend_result['content']
                    
                    print(f"\n💾 Saving Frontend artifacts...")
                    self._save_artifacts('Frontend', frontend_output, output_dir, iter_id)
                    
                    # 4. QA (reviews everything)
                    qa_task = f"""Review all outputs and create test plans:

=== REQUIREMENT ===
{requirement}

=== DESIGNER OUTPUT ===
{designer_output}

=== BACKEND OUTPUT ===
{backend_output}

=== FRONTEND OUTPUT ===
{frontend_output}

Create comprehensive test files using FILE: format."""
                    
                    qa_result = await self._run_agent('qa', qa_task)
                    all_messages.extend(qa_result['messages'])
                    qa_output = qa_result['content']
                    
                    print(f"\n💾 Saving QA artifacts...")
                    self._save_artifacts('QA', qa_output, output_dir, iter_id)
                    
                else:
                    # Subsequent iterations: Fix based on QA feedback
                    feedback = self._parse_qa_feedback(qa_output)
                    
                    if feedback.all_passed:
                        print("\n✅ All tests passed!")
                        break
                    
                    if not feedback.needs_iteration:
                        print("\n⚠️  No clear iteration signal. Ending workflow.")
                        break
                    
                    if not feedback.fix_backend and not feedback.fix_frontend:
                        print("\n⚠️  No specific agents mentioned. Ending workflow.")
                        break
                    
                    # Run fixes
                    if feedback.fix_backend:
                        print(f"\n🔧 Backend fixing issues...")
                        fix_result = await self._run_agent('backend', f"Fix these issues:\n\n{qa_output}")
                        all_messages.extend(fix_result['messages'])
                        backend_output = fix_result['content']
                        self._save_artifacts('Backend', backend_output, output_dir, iter_id)
                    
                    if feedback.fix_frontend:
                        print(f"\n🔧 Frontend fixing issues...")
                        fix_result = await self._run_agent('frontend', f"Fix these issues:\n\n{qa_output}")
                        all_messages.extend(fix_result['messages'])
                        frontend_output = fix_result['content']
                        self._save_artifacts('Frontend', frontend_output, output_dir, iter_id)
                    
                    # QA re-test
                    print(f"\n🔍 QA re-testing...")
                    qa_result = await self._run_agent('qa', "Re-test the fixes. Use FILE: format for test files.")
                    all_messages.extend(qa_result['messages'])
                    qa_output = qa_result['content']
                    self._save_artifacts('QA', qa_output, output_dir, iter_id)
                
                # Git commit after each iteration
                if git_manager:
                    commit_msg = task_description or f"Iteration {iteration}"
                    git_manager.commit(commit_msg)
            
            # Save chat history
            chat_file = self._save_chat_history(all_messages, output_dir, run_id)
            
            # Update project metadata
            if project:
                self.project_manager.refresh_project(project_name)
                if task_description:
                    self.project_manager.add_task_to_history(project_name, task_description, run_id)
            
            print(f"\n{'=' * 60}")
            print(f"✅ Workflow completed!")
            print(f"   Iterations: {iteration}")
            print(f"   Chat history: {chat_file}")
            print(f"{'=' * 60}")
            
            return WorkflowResult(
                run_id=run_id,
                status="completed",
                iterations=iteration,
                messages=all_messages,
                chat_file=str(chat_file),
                project_name=project_name,
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            return WorkflowResult(
                run_id=run_id,
                status="failed",
                iterations=iteration if 'iteration' in locals() else 0,
                error=str(e),
            )
    
    def run(
        self, 
        requirement: str,
        project_name: Optional[str] = None,
        task_description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous wrapper for run_async."""
        result = asyncio.run(self.run_async(
            requirement=requirement,
            project_name=project_name,
            task_description=task_description,
            **kwargs
        ))
        
        # Convert to dict for backward compatibility
        return {
            "run_id": result.run_id,
            "status": result.status,
            "iterations": result.iterations,
            "messages": result.messages,
            "chat_file": result.chat_file,
            "project_name": result.project_name,
            "error": result.error,
        }
