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
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.agents.designer import create_designer_agent
from app.agents.backend import create_backend_agent
from app.agents.frontend import create_frontend_agent
from app.agents.qa import create_qa_agent
from app.agents.manager import create_manager_agent
from app.agents.error_agent import create_error_agent
from app.agents.devops import create_devops_agent
from app.orchestration.artifact_saver import ArtifactSaver
from app.orchestration.npm_installer import NpmInstaller
from app.orchestration.project_manager import ProjectManager
from app.orchestration.git_manager import GitManager
from app.orchestration.error_knowledge_base import ErrorKnowledgeBase
from app.utils.cost_tracker import CostTracker
from app.config.llm_config import get_agent_models, get_provider_settings



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
        self.error_kb = ErrorKnowledgeBase()  # Error knowledge base
        self.cost_tracker = None  # Initialized per run
        
        # Get provider and model info for cost tracking
        self.provider_info = get_provider_settings()
        self.agent_models = get_agent_models()
        
        # Create agents (lazy - only when needed)
        self._agents = {}
    
    def _get_agent(self, name: str):
        """Lazy-load agents."""
        if name not in self._agents:
            creators = {
                'manager': create_manager_agent,
                'error_agent': create_error_agent,
                'devops': create_devops_agent,
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
    
    async def _run_agent(self, agent_name: str, task: str, iteration: int = 1, attempt: int = 1) -> Dict[str, Any]:
        """Run a single agent and return its output."""
        agent = self._get_agent(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not found", "content": "", "messages": []}
        
        print(f"\n🎯 Running {agent_name.title()} Agent...")
        result = await agent.run(task=task)
        
        # Extract content from result
        # NOTE: Some models (including GLM-* via OpenAI-compatible APIs) may emit
        # an initial planning/thinking message and then the final deliverable.
        # We want the *final* message for artifact extraction.
        content = ""
        
        # Try multiple extraction strategies
        for msg in result.messages:
            if hasattr(msg, 'source') and hasattr(msg, 'content'):
                source_str = str(msg.source).lower()
                # Check if source matches agent name (flexible matching)
                if (agent_name.lower().replace('_', '') in source_str or 
                    agent_name.lower() in source_str or
                    source_str in agent_name.lower()):
                    if msg.content:
                        content = msg.content  # Keep last matching message
        
        # Fallback: if no content found, try to get the last message with content
        if not content:
            for msg in reversed(result.messages):
                if hasattr(msg, 'content') and msg.content:
                    content = msg.content
                    print(f"  ⚠️  Using fallback content extraction for {agent_name}")
                    break
        
        if not content:
            print(f"  ⚠️  WARNING: No content extracted from {agent_name} agent!")
            print(f"  Messages count: {len(result.messages)}")
            for i, msg in enumerate(result.messages):
                if hasattr(msg, 'source'):
                    print(f"  Message {i}: source={msg.source}, has_content={hasattr(msg, 'content')}")
        
        # Extract token usage if available and record cost
        if self.cost_tracker:
            prompt_tokens = 0
            completion_tokens = 0
            
            # Try to extract usage from response
            # AutoGen may provide usage in different places depending on the model client
            if hasattr(result, 'usage'):
                prompt_tokens = getattr(result.usage, 'prompt_tokens', 0)
                completion_tokens = getattr(result.usage, 'completion_tokens', 0)
            elif result.messages and hasattr(result.messages[-1], 'usage'):
                usage = result.messages[-1].usage
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)
            
            # Record usage
            model = self.agent_models.get(agent_name, "unknown")
            provider = self.provider_info['provider']
            self.cost_tracker.record_usage(
                agent_name=agent_name,
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                iteration=iteration,
                attempt=attempt
            )
        
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
    
    def _extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract a section from manager's analysis."""
        import re
        
        # Try different patterns for section headers
        patterns = [
            rf"###?\s*{section_name}[:\s]*(.+?)(?=###|$)",
            rf"\*\*{section_name}\*\*[:\s]*(.+?)(?=\*\*|$)",
            rf"{section_name}[:\s]*(.+?)(?=\n\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _validate_builds(self, output_dir: Path) -> bool:
        """Validate backend and frontend builds before committing."""
        all_valid = True
        is_windows = platform.system() == "Windows"
        
        # Validate backend build
        backend_dir = output_dir / "backend"
        if backend_dir.exists():
            sln_files = list(backend_dir.glob("*.sln"))
            csproj_files = list(backend_dir.glob("**/*.csproj"))
            
            if sln_files:
                print("\n🔨 Validating backend build...")
                try:
                    result = subprocess.run(
                        ["dotnet", "build", sln_files[0].name, "--nologo"],
                        cwd=str(backend_dir),
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=60,
                        shell=is_windows  # Use shell on Windows to find dotnet
                    )
                    if result.returncode == 0:
                        print("  ✅ Backend build succeeded")
                    else:
                        error_output = result.stderr or result.stdout
                        print(f"  ❌ Backend build failed:")
                        print(error_output[:500] if error_output else "No error details available")
                        all_valid = False
                except FileNotFoundError:
                    print("  ⚠️  dotnet CLI not found, skipping backend validation")
                except subprocess.TimeoutExpired:
                    print("  ⚠️  Backend build timeout, skipping validation")
                except Exception as e:
                    print(f"  ⚠️  Backend validation error: {e}")
            elif csproj_files:
                print("  ℹ️  Backend .csproj found but no .sln, skipping validation")
        
        # Validate frontend build
        frontend_dir = output_dir / "frontend"
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            print("\n🔨 Validating frontend build...")
            try:
                # Check if node_modules exists first
                node_modules = frontend_dir / "node_modules"
                if not node_modules.exists():
                    print("  ⚠️  node_modules not found, skipping frontend validation")
                else:
                    # Use npm.cmd on Windows
                    npm_cmd = "npm.cmd" if is_windows else "npm"
                    result = subprocess.run(
                        [npm_cmd, "run", "build"],
                        cwd=str(frontend_dir),
                        capture_output=True,
                        text=True,                        
                        encoding='utf-8',
                        errors='replace',                        
                        timeout=120,
                        shell=is_windows  # Use shell on Windows
                    )
                    if result.returncode == 0:
                        print("  ✅ Frontend build succeeded")
                    else:
                        error_output = result.stderr or result.stdout
                        print(f"  ❌ Frontend build failed:")
                        print(error_output[:500] if error_output else "No error details available")
                        all_valid = False
            except FileNotFoundError:
                print("  ⚠️  npm not found, skipping frontend validation")
            except subprocess.TimeoutExpired:
                print("  ⚠️  Frontend build timeout, skipping validation")
            except Exception as e:
                print(f"  ⚠️  Frontend validation error: {e}")
        
        return all_valid
    
    async def _validate_and_fix_backend(self, output_dir: Path, backend_output: str, original_task: str, iter_id: str, max_retries: int = 3, iteration: int = 1) -> tuple[str, bool]:
        """
        Validate backend build and give agent chance to fix errors.
        Flow: Backend Agent (3 attempts) → Error Agent (2 attempts) → Manager → Continue until resolved
        
        Returns:
            tuple: (final_backend_output, build_success)
        """
        is_windows = platform.system() == "Windows"
        backend_dir = output_dir / "backend"
        error_history = []  # Track all errors for escalation
        
        agent_attempt = 0
        error_agent_attempt = 0
        manager_involved = False
        
        while True:  # Continue until resolved
            agent_attempt += 1
            sln_files = list(backend_dir.glob("*.sln"))
            if not sln_files:
                print("  ℹ️  No .sln file found, skipping backend build validation")
                return backend_output, True
            
            print(f"\n🔨 Validating backend build (overall attempt {agent_attempt})...")
            try:
                result = subprocess.run(
                    ["dotnet", "build", sln_files[0].name, "--nologo"],
                    cwd=str(backend_dir),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=60,
                    shell=is_windows
                )
                
                if result.returncode == 0:
                    print("  ✅ Backend build succeeded")
                    
                    # If Error Agent was involved and build succeeded, save their solution to KB
                    if error_agent_attempt > 0 and 'error_agent_solution' in locals():
                        print("  💾 Saving Error Agent's successful solution to knowledge base...")
                        try:
                            self.error_kb.add_solution(
                                agent="backend",
                                error_type="build",
                                error_message=error_history[-1]['error_output'] if error_history else "Build error",
                                root_cause=f"Resolved by Error Agent after {error_agent_attempt} attempts",
                                solution=error_agent_solution[:1000],
                                code_examples="See Error Agent analysis artifact",
                                prevention="Follow Error Agent's recommendations",
                                project=output_dir.name if output_dir else "unknown"
                            )
                        except Exception as e:
                            print(f"  ⚠️  Error saving to KB: {e}")
                    
                    return backend_output, True
                
                # Build failed - collect error data
                error_output = result.stderr or result.stdout
                error_data = {
                    "attempt": agent_attempt,
                    "error_output": error_output,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "sln_file": sln_files[0].name
                }
                error_history.append(error_data)
                
                print(f"  ❌ Backend build failed:")
                print(error_output[:500] if error_output else "No error details available")
                
                # Check knowledge base for similar errors
                print("\n  🔍 Checking error knowledge base...")
                similar_solutions = self.error_kb.find_similar_errors(
                    agent="backend",
                    error_message=error_output,
                    error_type="build"
                )
                
                kb_context = ""
                if similar_solutions:
                    print(f"  📚 Found {len(similar_solutions)} similar error(s) in knowledge base!")
                    kb_context = "\n\n" + self.error_kb.format_similar_solutions(similar_solutions)
                    # Mark solution as potentially useful
                    if similar_solutions:
                        self.error_kb.mark_solution_successful(similar_solutions[0].error_id)
                else:
                    print("  ℹ️  No similar errors found in knowledge base")
                
                # PHASE 1: Backend Agent attempts (max 3)
                if agent_attempt <= max_retries and not manager_involved:
                    print(f"\n🔧 Backend agent fixing build errors (attempt {agent_attempt}/{max_retries})...")
                    fix_task = f"""The backend build failed with these errors:

```
{error_output[:1500]}
```

{kb_context}

CRITICAL FIXES NEEDED:
1. Check all using directives (e.g., add 'using System.Net.Sockets;' if using SocketException)
2. Verify all NuGet packages are in the .csproj file
3. Ensure method signatures match (e.g., pass CancellationToken through the call chain)
4. Use correct extension method names (e.g., AddValidatorsFromAssembly(typeof(Program).Assembly))
5. Add 'using HealthChecks.UI.Client;' NOT 'using AspNetCore.HealthChecks.UI.Client;'
6. Include AspNetCore.HealthChecks.Npgsql package for PostgreSQL health checks

Original task: {original_task}

Fix the errors and regenerate ALL files using FILE: format."""
                    
                    fix_result = await self._run_agent('backend', fix_task, iteration=iteration, attempt=agent_attempt)
                    backend_output = fix_result['content']
                    
                    # Save the fixed version
                    self._save_artifacts('Backend', backend_output, output_dir, f"{iter_id}_fix{agent_attempt}")
                
                # PHASE 2: Error Agent attempts (max 2)
                elif error_agent_attempt < 2 and not manager_involved:
                    error_agent_attempt += 1
                    print(f"\n🔍 ERROR AGENT analyzing build errors (attempt {error_agent_attempt}/2)...")
                    
                    # Prepare error report for Error Agent
                    error_agent_task = f"""BACKEND BUILD ERROR REPORT

Project: {output_dir.name}
Solution File: {sln_files[0].name}
Build Attempts: {agent_attempt} (Backend Agent failed {max_retries} times)

=== BUILD ERROR ===
```
{error_output[:2000]}
```

=== KNOWLEDGE BASE CONTEXT ===
{kb_context if kb_context else "No similar errors found in knowledge base"}

=== RECENT ERROR HISTORY ===
"""
                    for err in error_history[-3:]:  # Last 3 attempts
                        error_agent_task += f"\nAttempt {err['attempt']}: Return Code {err['returncode']}\n"
                    
                    error_agent_task += f"""

=== ORIGINAL TASK ===
{original_task}

=== YOUR TASK ===
Analyze this backend build error and provide a precise solution.
- Identify the EXACT root cause
- Provide SPECIFIC fixes with code examples
- Include complete file paths and line-level changes
- If you need architectural changes or this requires Manager, say "ESCALATE TO MANAGER"

Provide the solution for the Backend agent to implement."""
                    
                    error_agent_result = await self._run_agent('error_agent', error_agent_task, iteration=iteration, attempt=error_agent_attempt)
                    error_agent_solution = error_agent_result['content']
                    
                    # Save Error Agent's analysis
                    self._save_artifacts('ErrorAgent', error_agent_solution, output_dir, f"{iter_id}_error_agent_analysis{error_agent_attempt}")
                    
                    # Check if Error Agent wants to escalate
                    if "ESCALATE TO MANAGER" in error_agent_solution or "escalate to manager" in error_agent_solution.lower():
                        print("\n⬆️  Error Agent requesting Manager escalation")
                        manager_involved = True
                        # Continue to manager phase on next iteration
                    else:
                        # Have backend agent implement Error Agent's solution
                        print("\n🔧 Backend agent implementing Error Agent's solution...")
                        solution_task = f"""The Error Agent has analyzed the build errors:

=== ERROR AGENT'S SOLUTION ===
{error_agent_solution}

=== YOUR TASK ===
Implement the Error Agent's solution EXACTLY as specified.
Regenerate ALL files using FILE: format."""
                        
                        fix_result = await self._run_agent('backend', solution_task, iteration=iteration, attempt=agent_attempt + 1)
                        backend_output = fix_result['content']
                        
                        # Save the error-agent-guided fix
                        self._save_artifacts('Backend', backend_output, output_dir, f"{iter_id}_error_agent_fix{error_agent_attempt}")
                
                # PHASE 3: Manager escalation (after Error Agent tried)
                else:
                    manager_involved = True
                    # Escalate to manager after Error Agent attempts
                    print(f"\n🚨 ESCALATING TO MANAGER: Error Agent couldn't resolve after {error_agent_attempt} attempts")
                    print("\n📊 Preparing comprehensive error report for Manager...")
                    
                    # Compile comprehensive error report
                    error_report = f"""BACKEND BUILD ERROR - MANAGER ESCALATION

Agent Flow: Backend ({max_retries} attempts) → Error Agent ({error_agent_attempt} attempts) → Manager
Project: {output_dir.name}
Solution File: {sln_files[0].name}
Total Attempts: {agent_attempt}

=== ERROR HISTORY ===
"""
                    for i, err in enumerate(error_history[-5:], 1):  # Last 5 attempts
                        error_report += f"\n--- Attempt {err['attempt']} ---\n"
                        error_report += f"Return Code: {err['returncode']}\n"
                        error_report += f"Error Output:\n{err['error_output'][:1000]}\n"
                    
                    error_report += f"\n\n=== ORIGINAL TASK ===\n{original_task}\n"
                    error_report += f"\n\n=== LATEST BACKEND OUTPUT ===\n{backend_output[:2000]}\n"
                    error_report += f"\n\n=== KNOWLEDGE BASE CONTEXT ===\n{kb_context if kb_context else 'No similar errors found'}\n"
                    
                    # Ask manager to analyze and provide architectural solution
                    manager_task = f"""{error_report}

=== YOUR TASK ===

This error has persisted through Backend Agent and Error Agent attempts.

Provide:
1. **Root Cause Analysis**: What is the fundamental issue?
2. **Architectural Assessment**: Does this require design changes?
3. **Detailed Solution**: Specific fixes with complete code examples
4. **Step-by-Step Instructions**: Clear directives for implementation
5. **Prevention Strategy**: How to avoid this in the future
6. **Decision**: Is this solvable? If not, explain why.

Be extremely specific with using directives, package names, and code patterns."""
                    
                    print("\n🛠️  Manager analyzing error data...")
                    manager_result = await self._run_agent('manager', manager_task, iteration=iteration, attempt=agent_attempt)
                    manager_analysis = manager_result['content']
                    
                    # Save manager's analysis
                    self._save_artifacts('Manager', manager_analysis, output_dir, f"{iter_id}_manager_backend_analysis")
                    
                    print("\n📝 Manager's analysis complete")
                    
                    # Check if manager determined it's solvable
                    if "not solvable" in manager_analysis.lower() or "cannot be fixed" in manager_analysis.lower():
                        print("\n⚠️  Manager determined error cannot be resolved automatically")
                        return backend_output, False
                    
                    # Extract solution components and save to knowledge base
                    print("\n💾 Saving Manager's solution to error knowledge base...")
                    try:
                        # Extract sections from manager's analysis
                        root_cause = self._extract_section(manager_analysis, "root cause")
                        solution = self._extract_section(manager_analysis, "solution")
                        code_examples = self._extract_section(manager_analysis, "code")
                        prevention = self._extract_section(manager_analysis, "prevention")
                        
                        self.error_kb.add_solution(
                            agent="backend",
                            error_type="build",
                            error_message=error_output,
                            root_cause=root_cause or "See manager analysis",
                            solution=solution or manager_analysis[:1000],
                            code_examples=code_examples or "",
                            prevention=prevention or "",
                            project=output_dir.name if output_dir else "unknown"
                        )
                    except Exception as e:
                        print(f"  ⚠️  Error saving to knowledge base: {e}")
                    
                    # Have backend agent try again with manager's solution
                    print("\n🔧 Backend agent implementing Manager's solution...")
                    solution_task = f"""The Manager has analyzed the build errors and provided this solution:

=== MANAGER'S ANALYSIS & SOLUTION ===
{manager_analysis}

=== YOUR TASK ===
Implement the Manager's solution EXACTLY as specified.
Regenerate ALL files using FILE: format.
Follow the step-by-step instructions provided."""
                    
                    fix_result = await self._run_agent('backend', solution_task, iteration=iteration, attempt=agent_attempt + 1)
                    backend_output = fix_result['content']
                    
                    # Save the manager-guided fix
                    self._save_artifacts('Backend', backend_output, output_dir, f"{iter_id}_manager_fix{agent_attempt}")
                    
            except FileNotFoundError:
                print("  ⚠️  dotnet CLI not found, skipping validation")
                return backend_output, True
            except subprocess.TimeoutExpired:
                print("  ⚠️  Backend build timeout")
                error_history.append({"attempt": agent_attempt, "error": "Build timeout"})
                if agent_attempt > max_retries:
                    return backend_output, False
            except Exception as e:
                print(f"  ⚠️  Build validation error: {e}")
                error_history.append({"attempt": agent_attempt, "error": str(e)})
                if agent_attempt > max_retries:
                    return backend_output, False
    
    async def _validate_and_fix_frontend(self, output_dir: Path, frontend_output: str, original_task: str, iter_id: str, max_retries: int = 3, iteration: int = 1) -> tuple[str, bool]:
        """
        Validate frontend build and give agent chance to fix errors.
        Flow: Frontend Agent (3 attempts) → Error Agent (2 attempts) → Manager → Continue until resolved
        
        Returns:
            tuple: (final_frontend_output, build_success)
        """
        is_windows = platform.system() == "Windows"
        frontend_dir = output_dir / "frontend"
        package_json = frontend_dir / "package.json"
        error_history = []  # Track all errors for escalation
        
        if not package_json.exists():
            print("  ℹ️  No package.json found, skipping frontend build validation")
            return frontend_output, True
        
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("  ⚠️  node_modules not found, skipping frontend validation")
            return frontend_output, True
        
        agent_attempt = 0
        error_agent_attempt = 0
        manager_involved = False
        
        while True:  # Continue until resolved
            agent_attempt += 1
            print(f"\n🔨 Validating frontend build (overall attempt {agent_attempt})...")
            try:
                npm_cmd = "npm.cmd" if is_windows else "npm"
                result = subprocess.run(
                    [npm_cmd, "run", "build"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    shell=is_windows
                )
                
                if result.returncode == 0:
                    print("  ✅ Frontend build succeeded")
                    
                    # If Error Agent was involved and build succeeded, save their solution to KB
                    if error_agent_attempt > 0 and 'error_agent_solution' in locals():
                        print("  💾 Saving Error Agent's successful solution to knowledge base...")
                        try:
                            self.error_kb.add_solution(
                                agent="frontend",
                                error_type="build",
                                error_message=error_history[-1]['error_output'] if error_history else "Build error",
                                root_cause=f"Resolved by Error Agent after {error_agent_attempt} attempts",
                                solution=error_agent_solution[:1000],
                                code_examples="See Error Agent analysis artifact",
                                prevention="Follow Error Agent's recommendations",
                                project=output_dir.name if output_dir else "unknown"
                            )
                        except Exception as e:
                            print(f"  ⚠️  Error saving to KB: {e}")
                    
                    return frontend_output, True
                
                # Build failed - collect error data
                error_output = result.stderr or result.stdout
                error_data = {
                    "attempt": agent_attempt,
                    "error_output": error_output,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                error_history.append(error_data)
                
                print(f"  ❌ Frontend build failed:")
                print(error_output[:500] if error_output else "No error details available")
                
                # Check knowledge base for similar errors
                print("\n  🔍 Checking error knowledge base...")
                similar_solutions = self.error_kb.find_similar_errors(
                    agent="frontend",
                    error_message=error_output,
                    error_type="build"
                )
                
                kb_context = ""
                if similar_solutions:
                    print(f"  📚 Found {len(similar_solutions)} similar error(s) in knowledge base!")
                    kb_context = "\n\n" + self.error_kb.format_similar_solutions(similar_solutions)
                    # Mark solution as potentially useful
                    if similar_solutions:
                        self.error_kb.mark_solution_successful(similar_solutions[0].error_id)
                else:
                    print("  ℹ️  No similar errors found in knowledge base")
                
                # PHASE 1: Frontend Agent attempts (max 3)
                if agent_attempt <= max_retries and not manager_involved:
                    print(f"\n🔧 Frontend agent fixing build errors (attempt {agent_attempt}/{max_retries})...")
                    fix_task = f"""The frontend build failed with these errors:

```
{error_output[:1500]}
```

{kb_context}

CRITICAL FIXES NEEDED:
1. Prefix unused parameters with _ (e.g., '_from' instead of 'from' in router guards)
2. Ensure tsconfig.json includes "types": ["vite/client"]
3. Check all imports and type definitions
4. Fix any TypeScript errors
5. Ensure all Vue components are properly typed
6. Check for missing dependencies in package.json

Original task: {original_task}

Fix the errors and regenerate ALL files using FILE: format."""
                    
                    fix_result = await self._run_agent('frontend', fix_task, iteration=iteration, attempt=agent_attempt)
                    frontend_output = fix_result['content']
                    
                    # Save the fixed version
                    self._save_artifacts('Frontend', frontend_output, output_dir, f"{iter_id}_fix{agent_attempt}")
                
                # PHASE 2: Error Agent attempts (max 2)
                elif error_agent_attempt < 2 and not manager_involved:
                    error_agent_attempt += 1
                    print(f"\n🔍 ERROR AGENT analyzing build errors (attempt {error_agent_attempt}/2)...")
                    
                    # Prepare error report for Error Agent
                    error_agent_task = f"""FRONTEND BUILD ERROR REPORT

Project: {output_dir.name}
Build Command: npm run build
Build Attempts: {agent_attempt} (Frontend Agent failed {max_retries} times)

=== BUILD ERROR ===
```
{error_output[:2000]}
```

=== KNOWLEDGE BASE CONTEXT ===
{kb_context if kb_context else "No similar errors found in knowledge base"}

=== RECENT ERROR HISTORY ===
"""
                    for err in error_history[-3:]:  # Last 3 attempts
                        error_agent_task += f"\nAttempt {err['attempt']}: Return Code {err['returncode']}\n"
                    
                    error_agent_task += f"""

=== ORIGINAL TASK ===
{original_task}

=== YOUR TASK ===
Analyze this frontend build error and provide a precise solution.
- Identify the EXACT root cause
- Provide SPECIFIC fixes with code examples
- Include complete file paths and line-level changes
- If you need architectural changes or this requires Manager, say "ESCALATE TO MANAGER"

Provide the solution for the Frontend agent to implement."""
                    
                    error_agent_result = await self._run_agent('error_agent', error_agent_task, iteration=iteration, attempt=error_agent_attempt)
                    error_agent_solution = error_agent_result['content']
                    
                    # Save Error Agent's analysis
                    self._save_artifacts('ErrorAgent', error_agent_solution, output_dir, f"{iter_id}_error_agent_frontend_analysis{error_agent_attempt}")
                    
                    # Check if Error Agent wants to escalate
                    if "ESCALATE TO MANAGER" in error_agent_solution or "escalate to manager" in error_agent_solution.lower():
                        print("\n⬆️  Error Agent requesting Manager escalation")
                        manager_involved = True
                        # Continue to manager phase on next iteration
                    else:
                        # Have frontend agent implement Error Agent's solution
                        print("\n🔧 Frontend agent implementing Error Agent's solution...")
                        solution_task = f"""The Error Agent has analyzed the build errors:

=== ERROR AGENT'S SOLUTION ===
{error_agent_solution}

=== YOUR TASK ===
Implement the Error Agent's solution EXACTLY as specified.
Regenerate ALL files using FILE: format."""
                        
                        fix_result = await self._run_agent('frontend', solution_task, iteration=iteration, attempt=agent_attempt + 1)
                        frontend_output = fix_result['content']
                        
                        # Save the error-agent-guided fix
                        self._save_artifacts('Frontend', frontend_output, output_dir, f"{iter_id}_error_agent_fix{error_agent_attempt}")
                
                # PHASE 3: Manager escalation (after Error Agent tried)
                else:
                    manager_involved = True
                    # Escalate to manager after Error Agent attempts
                    print(f"\n🚨 ESCALATING TO MANAGER: Error Agent couldn't resolve after {error_agent_attempt} attempts")
                    print("\n📊 Preparing comprehensive error report for Manager...")
                    
                    # Compile comprehensive error report
                    error_report = f"""FRONTEND BUILD ERROR - MANAGER ESCALATION

Agent Flow: Frontend ({max_retries} attempts) → Error Agent ({error_agent_attempt} attempts) → Manager
Project: {output_dir.name}
Build Command: npm run build
Total Attempts: {agent_attempt}

=== ERROR HISTORY ===
"""
                    for i, err in enumerate(error_history, 1):
                        error_report += f"\n--- Attempt {err['attempt']} ---\n"
                        error_report += f"Return Code: {err['returncode']}\n"
                        error_report += f"Error Output:\n{err['error_output'][:1000]}\n"
                    
                    error_report += f"\n\n=== ORIGINAL TASK ===\n{original_task}\n"
                    error_report += f"\n\n=== LATEST FRONTEND OUTPUT ===\n{frontend_output[:2000]}\n"
                    
                    # Ask manager to analyze and provide solution
                    manager_task = f"""{error_report}

=== YOUR TASK ===

Analyze this persistent frontend build error that has failed {agent_attempt} times.

Provide:
1. **Root Cause Analysis**: What is the core issue causing these build errors?
2. **Detailed Solution**: Specific fixes needed with code examples
3. **Step-by-Step Instructions**: Clear directives for the Frontend agent
4. **Prevention Strategy**: How to avoid this error in the future
5. **Decision**: Is this error solvable? If yes, provide the complete fix. If no, explain why.

Be extremely specific with TypeScript types, Vue 3 patterns, and Vite configuration."""
                    
                    print("\n🛠️ Manager analyzing error data...")
                    manager_result = await self._run_agent('manager', manager_task, iteration=iteration, attempt=agent_attempt)
                    manager_analysis = manager_result['content']
                    
                    # Save manager's analysis
                    self._save_artifacts('Manager', manager_analysis, output_dir, f"{iter_id}_frontend_error_analysis")
                    
                    print("\n📝 Manager's analysis complete")
                    
                    # Check if manager determined it's solvable
                    if "not solvable" in manager_analysis.lower() or "cannot be fixed" in manager_analysis.lower():
                        print("\n⚠️  Manager determined error cannot be resolved automatically")
                        return frontend_output, False
                    
                    # Extract solution components and save to knowledge base
                    print("\n💾 Saving solution to error knowledge base...")
                    try:
                        # Extract sections from manager's analysis
                        root_cause = self._extract_section(manager_analysis, "root cause")
                        solution = self._extract_section(manager_analysis, "solution")
                        code_examples = self._extract_section(manager_analysis, "code")
                        prevention = self._extract_section(manager_analysis, "prevention")
                        
                        self.error_kb.add_solution(
                            agent="frontend",
                            error_type="build",
                            error_message=error_output,
                            root_cause=root_cause or "See manager analysis",
                            solution=solution or manager_analysis[:1000],
                            code_examples=code_examples or "",
                            prevention=prevention or "",
                            project=output_dir.name if output_dir else "unknown"
                        )
                    except Exception as e:
                        print(f"  ⚠️  Error saving to knowledge base: {e}")
                    
                    # Have frontend agent try again with manager's solution
                    print("\n🔧 Frontend agent implementing Manager's solution...")
                    solution_task = f"""The Manager has analyzed the build errors and provided this solution:

=== MANAGER'S ANALYSIS & SOLUTION ===
{manager_analysis}

=== YOUR TASK ===
Implement the Manager's solution EXACTLY as specified.
Regenerate ALL files using FILE: format.
Follow the step-by-step instructions provided."""
                    
                    fix_result = await self._run_agent('frontend', solution_task, iteration=iteration, attempt=agent_attempt + 1)
                    frontend_output = fix_result['content']
                    
                    # Save the manager-guided fix
                    self._save_artifacts('Frontend', frontend_output, output_dir, f"{iter_id}_manager_fix{agent_attempt}")
                    
            except FileNotFoundError:
                print("  ⚠️  npm not found, skipping validation")
                return frontend_output, True
            except subprocess.TimeoutExpired:
                print("  ⚠️  Frontend build timeout")
                error_history.append({"attempt": agent_attempt, "error": "Build timeout"})
                if agent_attempt > max_retries * 2:  # Allow more attempts for timeout
                    return frontend_output, False
            except Exception as e:
                print(f"  ⚠️  Build validation error: {e}")
                error_history.append({"attempt": agent_attempt, "error": str(e)})
                if agent_attempt > max_retries * 2:
                    return frontend_output, False
    
    async def _validate_and_fix_devops(self, output_dir: Path, devops_output: str, original_task: str, iter_id: str, max_retries: int = 3, iteration: int = 1) -> tuple[str, bool]:
        """
        Validate DevOps configuration and give agent chance to fix errors.
        Flow: DevOps Agent (3 attempts) → Error Agent (2 attempts) → Manager → Continue until resolved
        
        Returns:
            tuple: (final_devops_output, validation_success)
        """
        is_windows = platform.system() == "Windows"
        error_history = []
        
        agent_attempt = 0
        error_agent_attempt = 0
        manager_involved = False
        
        while True:  # Continue until resolved
            agent_attempt += 1
            docker_compose_file = output_dir / "docker-compose.yml"
            
            if not docker_compose_file.exists():
                print("  ℹ️  No docker-compose.yml found, skipping DevOps validation")
                return devops_output, True
            
            print(f"\n🔨 Validating Docker configuration (overall attempt {agent_attempt})...")
            try:
                # Validate docker-compose.yml syntax
                result = subprocess.run(
                    ["docker-compose", "config", "--quiet"],
                    cwd=str(output_dir),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    shell=is_windows
                )
                
                if result.returncode == 0:
                    print("  ✅ Docker configuration is valid")
                    
                    # If Error Agent was involved and validation succeeded, save to KB
                    if error_agent_attempt > 0 and 'error_agent_solution' in locals():
                        print("  💾 Saving Error Agent's successful solution to knowledge base...")
                        try:
                            self.error_kb.add_solution(
                                agent="devops",
                                error_type="docker_config",
                                error_message=error_history[-1]['error_output'] if error_history else "Docker config error",
                                root_cause=f"Resolved by Error Agent after {error_agent_attempt} attempts",
                                solution=error_agent_solution,
                                category="infrastructure"
                            )
                        except Exception as e:
                            print(f"  ⚠️  Failed to save to knowledge base: {e}")
                    
                    # If Manager was involved and validation succeeded, save to KB
                    if manager_involved and 'manager_solution' in locals():
                        print("  💾 Saving Manager's successful solution to knowledge base...")
                        try:
                            self.error_kb.add_solution(
                                agent="devops",
                                error_type="docker_config",
                                error_message=error_history[-1]['error_output'] if error_history else "Docker config error",
                                root_cause=f"Resolved by Manager after {agent_attempt} total attempts",
                                solution=manager_solution,
                                category="architecture"
                            )
                        except Exception as e:
                            print(f"  ⚠️  Failed to save to knowledge base: {e}")
                    
                    return devops_output, True
                else:
                    error_output = result.stderr or result.stdout
                    print(f"  ❌ Docker configuration validation failed:")
                    print(f"  {error_output[:300]}")
                    
                    error_history.append({
                        "attempt": agent_attempt,
                        "error_output": error_output,
                        "phase": "devops_agent" if agent_attempt <= max_retries else ("error_agent" if error_agent_attempt < 2 else "manager")
                    })
                    
                    # PHASE 1: DevOps Agent attempts (3 attempts)
                    if agent_attempt <= max_retries:
                        print(f"\n🔄 PHASE 1: Asking DevOps Agent to fix (attempt {agent_attempt}/{max_retries})...")
                        
                        fix_task = f"""The Docker configuration has validation errors. Please fix them.

=== ORIGINAL TASK ===
{original_task}

=== YOUR PREVIOUS OUTPUT ===
{devops_output}

=== VALIDATION ERROR ===
{error_output}

Analyze the error and provide corrected Docker configuration files using FILE: format.
Focus ONLY on fixing the syntax/configuration errors."""
                        
                        fix_result = await self._run_agent('devops', fix_task, iteration=iteration, attempt=agent_attempt)
                        devops_output = fix_result['content']
                        
                        print(f"\n💾 Saving DevOps fix attempt {agent_attempt}...")
                        self._save_artifacts('DevOps', devops_output, output_dir, f"{iter_id}_fix{agent_attempt}")
                        continue  # Retry validation
                    
                    # PHASE 2: Error Agent attempts (2 attempts after DevOps fails 3 times)
                    elif error_agent_attempt < 2:
                        error_agent_attempt += 1
                        print(f"\n🔄 PHASE 2: Escalating to Error Agent (attempt {error_agent_attempt}/2)...")
                        
                        # Check KB first
                        kb_solution = self.error_kb.search_solution(
                            agent="devops",
                            error_message=error_output
                        )
                        
                        kb_context = ""
                        if kb_solution:
                            print("  📚 Found similar solution in knowledge base")
                            kb_context = f"\n=== KNOWLEDGE BASE SOLUTION ===\n{kb_solution}\n"
                        
                        error_agent_task = f"""A Docker configuration error needs debugging expertise.

{kb_context}
=== ORIGINAL TASK ===
{original_task}

=== DEVOPS AGENT'S OUTPUT ===
{devops_output}

=== VALIDATION ERROR (after {agent_attempt} attempts) ===
{error_output}

=== ERROR HISTORY ===
{chr(10).join([f"Attempt {h['attempt']}: {h['error_output'][:200]}" for h in error_history[-3:]])}

Analyze and provide:
1. Root cause of the Docker configuration error
2. EXACT fix with corrected docker-compose.yml content
3. Explanation of what was wrong

Use FILE: format for corrected files."""
                        
                        error_fix_result = await self._run_agent('error_agent', error_agent_task, iteration=iteration, attempt=error_agent_attempt)
                        devops_output = error_fix_result['content']
                        error_agent_solution = devops_output
                        
                        print(f"\n💾 Saving Error Agent fix attempt {error_agent_attempt}...")
                        self._save_artifacts('ErrorAgent', devops_output, output_dir, f"{iter_id}_devops_error_fix{error_agent_attempt}")
                        continue  # Retry validation
                    
                    # PHASE 3: Manager strategic intervention
                    else:
                        if not manager_involved:
                            manager_involved = True
                            print(f"\n🔄 PHASE 3: Escalating to Manager for architectural guidance...")
                            
                            manager_task = f"""The DevOps Agent and Error Agent both failed to create valid Docker configuration.

=== ORIGINAL REQUIREMENT ===
{original_task}

=== DEVOPS OUTPUT (after {agent_attempt} attempts) ===
{devops_output}

=== LATEST VALIDATION ERROR ===
{error_output}

=== COMPLETE ERROR HISTORY ===
{chr(10).join([f"Attempt {h['attempt']} ({h['phase']}): {h['error_output'][:200]}" for h in error_history])}

This requires strategic analysis:
1. Is the Docker configuration architecturally sound?
2. Are there better approaches to the infrastructure setup?
3. What are the root architectural issues?

Provide detailed solution with corrected docker-compose.yml using FILE: format."""
                            
                            manager_fix_result = await self._run_agent('manager', manager_task, iteration=iteration, attempt=agent_attempt)
                            devops_output = manager_fix_result['content']
                            manager_solution = devops_output
                            
                            print(f"\n💾 Saving Manager's DevOps fix...")
                            self._save_artifacts('Manager', devops_output, output_dir, f"{iter_id}_devops_manager_fix")
                            continue  # Retry validation
                        else:
                            # Manager already involved, continue with infinite loop until resolved
                            print(f"\n🔄 Continuing with Manager guidance (attempt {agent_attempt})...")
                            continue  # Keep trying
                
            except FileNotFoundError:
                print("  ⚠️  docker-compose not found, skipping DevOps validation")
                return devops_output, True
            except subprocess.TimeoutExpired:
                print("  ⚠️  Docker validation timeout")
                error_history.append({"attempt": agent_attempt, "error": "Validation timeout", "error_output": "Timeout"})
                if agent_attempt > max_retries:
                    return devops_output, False
            except Exception as e:
                print(f"  ⚠️  Validation error: {e}")
                error_history.append({"attempt": agent_attempt, "error": str(e), "error_output": str(e)})
                if agent_attempt > max_retries:
                    return devops_output, False
    
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
        
        # Initialize cost tracker for this run
        self.cost_tracker = CostTracker(project_dir=output_dir if project_name else None)
        
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
                    # First iteration: Full pipeline with Manager coordination
                    # Manager → Designer → Backend → Frontend → QA
                    
                    # 0. Manager (Strategic planning and direction)
                    print(f"\n📋 Manager Agent: Analyzing requirements and creating strategy...")
                    manager_task = f"""Analyze this project requirement and create a comprehensive project plan:

{requirement}

Provide:
1. Project overview and architecture strategy
2. Development roadmap and phases
3. Quality standards and best practices to follow
4. Specific directives for Designer, Backend, Frontend, and QA agents
5. Risk assessment and mitigation strategies

Be specific and actionable in your directives."""
                    
                    manager_result = await self._run_agent('manager', manager_task, iteration=iteration)
                    all_messages.extend(manager_result['messages'])
                    manager_output = manager_result['content']
                    
                    print(f"\n💾 Saving Manager plan...")
                    self._save_artifacts('Manager', manager_output, output_dir, iter_id)
                    
                    # 1. Designer (uses Manager's directives)
                    designer_task = f"""{requirement}

=== MANAGER'S STRATEGIC PLAN ===
{manager_output}

Follow the Manager's directives and create detailed technical specifications."""
                    
                    designer_result = await self._run_agent('designer', designer_task, iteration=iteration)
                    all_messages.extend(designer_result['messages'])
                    designer_output = designer_result['content']
                    
                    print(f"\n💾 Saving Designer artifacts...")
                    self._save_artifacts('Designer', designer_output, output_dir, iter_id)
                    
                    # 2. Backend (sees Manager plan and Designer specs)
                    backend_task = f"""{requirement}

=== MANAGER'S STRATEGIC PLAN ===
{manager_output}

=== Designer Specifications ===
{designer_output}

Follow the Manager's best practices and implement the backend according to Designer's specs."""
                    
                    backend_result = await self._run_agent('backend', backend_task, iteration=iteration)
                    all_messages.extend(backend_result['messages'])
                    backend_output = backend_result['content']
                    
                    print(f"\n💾 Saving Backend artifacts...")
                    self._save_artifacts('Backend', backend_output, output_dir, iter_id)
                    
                    # Validate backend build and let agent fix if needed
                    backend_output, backend_build_ok = await self._validate_and_fix_backend(
                        output_dir, backend_output, backend_task, iter_id, iteration=iteration
                    )
                    
                    # 3. Frontend (sees Manager plan and Designer specs, NOT Backend code to prevent confusion)
                    frontend_task = f"""{requirement}

=== MANAGER'S STRATEGIC PLAN ===
{manager_output}

=== Designer Specifications ===
{designer_output}

Follow the Manager's best practices and implement the Vue 3 frontend. Backend API is being implemented separately."""
                    
                    frontend_result = await self._run_agent('frontend', frontend_task, iteration=iteration)
                    all_messages.extend(frontend_result['messages'])
                    frontend_output = frontend_result['content']
                    
                    print(f"\n💾 Saving Frontend artifacts...")
                    self._save_artifacts('Frontend', frontend_output, output_dir, iter_id)
                    
                    # Validate frontend build and let agent fix if needed
                    frontend_output, frontend_build_ok = await self._validate_and_fix_frontend(
                        output_dir, frontend_output, frontend_task, iter_id, iteration=iteration
                    )
                    
                    # 3.5 DevOps (creates Docker configs after Backend and Frontend are ready)
                    devops_task = f"""Create Docker and infrastructure configuration for this project:

=== REQUIREMENT ===
{requirement}

=== MANAGER'S STRATEGIC PLAN ===
{manager_output}

=== DESIGNER SPECIFICATIONS ===
{designer_output}

=== BACKEND IMPLEMENTATION ===
{backend_output}

=== FRONTEND IMPLEMENTATION ===
{frontend_output}

Create comprehensive Docker configuration including:
- docker-compose.yml for the entire stack
- Dockerfiles (if missing or need optimization)
- .env.example with all required variables
- Database initialization scripts
- Complete setup documentation with service URLs

The backend is .NET 8 and frontend is Vue 3. Include PostgreSQL and Redis containers."""
                    
                    devops_result = await self._run_agent('devops', devops_task, iteration=iteration)
                    all_messages.extend(devops_result['messages'])
                    devops_output = devops_result['content']
                    
                    print(f"\n💾 Saving DevOps artifacts...")
                    self._save_artifacts('DevOps', devops_output, output_dir, iter_id)
                    
                    # Validate DevOps configuration and let agent fix if needed
                    devops_output, devops_valid = await self._validate_and_fix_devops(
                        output_dir, devops_output, devops_task, iter_id, iteration=iteration
                    )
                    
                    # 4. QA (reviews everything including DevOps setup)
                    qa_task = f"""Review all outputs and create test plans:

=== REQUIREMENT ===
{requirement}

=== DESIGNER OUTPUT ===
{designer_output}

=== BACKEND OUTPUT ===
{backend_output}

=== FRONTEND OUTPUT ===
{frontend_output}

=== DEVOPS CONFIGURATION ===
{devops_output}

Create comprehensive test files using FILE: format. Verify Docker setup is correct."""
                    
                    qa_result = await self._run_agent('qa', qa_task, iteration=iteration)
                    all_messages.extend(qa_result['messages'])
                    qa_output = qa_result['content']
                    
                    print(f"\n💾 Saving QA artifacts...")
                    self._save_artifacts('QA', qa_output, output_dir, iter_id)
                    
                else:
                    # Subsequent iterations: Manager analyzes QA feedback and directs fixes
                    feedback = self._parse_qa_feedback(qa_output)
                    
                    if feedback.all_passed:
                        print("\n✅ All tests passed!")
                        break
                    
                    if not feedback.needs_iteration:
                        print("\n⚠️  No clear iteration signal. Ending workflow.")
                        break
                    
                    if not feedback.fix_backend and not feedback.fix_frontend:
                        print("\n⚠️  No specific agents mentioned. Asking Manager to analyze...")
                        
                        # Let Manager analyze the QA feedback and provide direction
                        manager_analysis_task = f"""The QA agent found issues that need to be addressed:

=== QA FEEDBACK ===
{qa_output}

=== ORIGINAL REQUIREMENT ===
{requirement}

Analyze these issues and provide:
1. Root cause analysis
2. Specific fix strategies for Backend and/or Frontend agents
3. Clear directives on what needs to be changed
4. Best practices to prevent similar issues"""
                        
                        manager_fix_result = await self._run_agent('manager', manager_analysis_task, iteration=iteration)
                        all_messages.extend(manager_fix_result['messages'])
                        manager_fix_output = manager_fix_result['content']
                        
                        print(f"\n💾 Saving Manager analysis...")
                        self._save_artifacts('Manager', manager_fix_output, output_dir, f"{iter_id}_analysis")
                        
                        # Use manager's analysis to determine which agents need fixes
                        if "Backend" in manager_fix_output or "backend" in manager_fix_output:
                            feedback.fix_backend = True
                        if "Frontend" in manager_fix_output or "frontend" in manager_fix_output:
                            feedback.fix_frontend = True
                        
                        if not feedback.fix_backend and not feedback.fix_frontend:
                            print("\n⚠️  Manager couldn't identify specific fixes. Ending workflow.")
                            break
                    
                    # Run fixes with Manager's guidance
                    if feedback.fix_backend:
                        print(f"\n🔧 Backend fixing issues based on Manager's direction...")
                        fix_task = f"""Fix these issues:

=== QA FEEDBACK ===
{qa_output}

=== MANAGER'S ANALYSIS (if available) ===
{manager_fix_output if 'manager_fix_output' in locals() else 'Follow best practices from initial plan.'}

Regenerate ALL files with fixes using FILE: format."""
                        
                        fix_result = await self._run_agent('backend', fix_task, iteration=iteration)
                        all_messages.extend(fix_result['messages'])
                        backend_output = fix_result['content']
                        self._save_artifacts('Backend', backend_output, output_dir, iter_id)
                        
                        # Validate backend build after QA fixes
                        backend_output, _ = await self._validate_and_fix_backend(
                            output_dir, backend_output, f"Fix QA issues:\n{qa_output}", iter_id, iteration=iteration
                        )
                    
                    if feedback.fix_frontend:
                        print(f"\n🔧 Frontend fixing issues based on Manager's direction...")
                        fix_task = f"""Fix these issues:

=== QA FEEDBACK ===
{qa_output}

=== MANAGER'S ANALYSIS (if available) ===
{manager_fix_output if 'manager_fix_output' in locals() else 'Follow best practices from initial plan.'}

Regenerate ALL files with fixes using FILE: format."""
                        
                        fix_result = await self._run_agent('frontend', fix_task, iteration=iteration)
                        all_messages.extend(fix_result['messages'])
                        frontend_output = fix_result['content']
                        self._save_artifacts('Frontend', frontend_output, output_dir, iter_id)
                        
                        # Validate frontend build after QA fixes
                        frontend_output, _ = await self._validate_and_fix_frontend(
                            output_dir, frontend_output, f"Fix QA issues:\n{qa_output}", iter_id, iteration=iteration
                        )
                    
                    # QA re-test
                    print(f"\n🔍 QA re-testing...")
                    qa_result = await self._run_agent('qa', "Re-test the fixes. Use FILE: format for test files.", iteration=iteration)
                    all_messages.extend(qa_result['messages'])
                    qa_output = qa_result['content']
                    self._save_artifacts('QA', qa_output, output_dir, iter_id)
                
                # Validate builds before committing
                build_valid = self._validate_builds(output_dir)
                
                # Git commit after each iteration (only if builds pass)
                if git_manager:
                    if build_valid:
                        commit_msg = task_description or f"Iteration {iteration}"
                        git_manager.commit(commit_msg)
                        # Tag the iteration for rollback
                        tag_desc = "Initial implementation" if iteration == 1 else "With fixes applied"
                        git_manager.tag_iteration(iteration, run_id, tag_desc)
                        print("  ✅ Changes committed to Git")
                        print(f"  🏷️  Tagged as: iter{iteration}_{run_id}")
                    else:
                        print("  ⚠️  Skipping Git commit due to build failures")
            
            # Save chat history
            chat_file = self._save_chat_history(all_messages, output_dir, run_id)
            
            # Update project metadata
            if project:
                self.project_manager.refresh_project(project_name)
                if task_description:
                    self.project_manager.add_task_to_history(project_name, task_description, run_id)
            
            # Generate README.md for the project
            if project_name:
                from app.utils.readme_generator import ReadmeGenerator
                print(f"\n📝 Generating README.md...")
                readme_gen = ReadmeGenerator(output_dir, project_name)
                readme_path = readme_gen.save(requirement)
                print(f"   ✅ README.md created: {readme_path.name}")
            
            # Print and save cost summary
            if self.cost_tracker:
                self.cost_tracker.print_summary()
                if project_name:
                    self.cost_tracker.save_report(f"cost_report_{run_id}.json")
            
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
