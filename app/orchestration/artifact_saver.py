"""Utility for saving agent artifacts to appropriate output directories."""

import re
from pathlib import Path
from typing import Dict, List, Any


class ArtifactSaver:
    """Handles parsing and saving agent outputs to appropriate directories."""
    
    # Agent-specific output directories
    AGENT_DIRS = {
        "Designer": "design",
        "Backend": "backend",
        "Frontend": "frontend",
        "QA": "qa",
    }
    
    def __init__(self, base_outputs_dir: str = "./outputs"):
        """
        Initialize artifact saver.
        
        Args:
            base_outputs_dir: Base directory for all outputs
        """
        self.base_dir = Path(base_outputs_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create agent-specific directories
        for agent_dir in self.AGENT_DIRS.values():
            (self.base_dir / agent_dir).mkdir(parents=True, exist_ok=True)
    
    def save_agent_artifacts(self, agent_name: str, content: str, run_id: str) -> List[Path]:
        """
        Parse agent output and save artifacts to appropriate directory.
        
        Args:
            agent_name: Name of the agent (Designer, Backend, Frontend, QA)
            content: Agent's output content
            run_id: Run identifier for organizing outputs
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        # Get agent-specific directory
        agent_dir = self.AGENT_DIRS.get(agent_name)
        if not agent_dir:
            print(f"⚠️  Unknown agent: {agent_name}, skipping artifact save")
            return saved_files
        
        output_dir = self.base_dir / agent_dir / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # For QA agent, try to auto-convert code blocks to FILE: format
        if agent_name == "QA":
            content = self._auto_convert_qa_files(content)
        
        # For Backend agent, try to auto-convert code blocks to FILE: format
        if agent_name == "Backend":
            content = self._auto_convert_backend_files(content)
        
        # First try structured file pattern: FILE: path
        structured_files = self._extract_structured_files(content, output_dir)
        if structured_files:
            saved_files.extend(structured_files)
        
        # Also save raw output as markdown for reference
        default_filename = f"{agent_name.lower()}_output.md"
        default_path = output_dir / default_filename
        
        # Determine if this is an iteration (check if run_id contains '_iter')
        is_iteration = '_iter' in run_id
        
        if is_iteration and default_path.exists():
            # Append to existing file with iteration marker
            iteration_num = run_id.split('_iter')[-1] if '_iter' in run_id else 'unknown'
            with default_path.open('a', encoding='utf-8') as f:
                f.write(f"\n\n{'=' * 80}\n")
                f.write(f"# ITERATION {iteration_num}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(content)
            print(f"  ➕ Appended to: {default_path.relative_to(self.base_dir)} (iteration {iteration_num})")
        else:
            # First iteration or new run - create/overwrite file
            default_path.write_text(content, encoding='utf-8')
            print(f"  💾 Saved: {default_path.relative_to(self.base_dir)}")
        
        if default_path not in saved_files:
            saved_files.append(default_path)
        
        return saved_files
    
    def _extract_structured_files(self, content: str, output_dir: Path) -> List[Path]:
        """
        Extract files using the FILE: path pattern or markdown headers with backticks.
        
        Looks for:
        FILE: path/to/file.ext
        ```language
        content
        ```
        
        OR
        
        ##### `path/to/file.ext`
        ```language
        content
        ```
        
        Args:
            content: Agent's output content
            output_dir: Directory to save files to
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        # Pattern: FILE: path followed by code block
        # Match FILE: followed by path, then optional ```language markers
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            filepath_str = None
            
            # Look for FILE: marker (can be in markdown headers like #### FILE: path)
            if 'FILE:' in line or 'file:' in line or 'File:' in line:
                # Extract filepath after FILE:
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1 and ('FILE' in parts[0].upper()):
                        filepath_str = parts[1].strip()
                        filepath_str = filepath_str.replace('`', '').replace('*', '').strip()
            # Also look for markdown headers with backticks: ##### `filename.ext`
            elif line.startswith('#') and '`' in line:
                # Extract filename from backticks
                import re
                match = re.search(r'`([^`]+\.[a-zA-Z0-9]+)`', line)
                if match:
                    filepath_str = match.group(1).strip()
            
            if filepath_str:
                # Look for code block start (skip blank lines)
                i += 1
                while i < len(lines):
                    stripped = lines[i].strip()
                    if stripped.startswith('```'):
                        break
                    elif stripped == '':
                        # Skip blank lines
                        i += 1
                    else:
                        # Non-blank, non-code-block line - no code block found
                        filepath_str = None
                        break
                
                if i >= len(lines) or not filepath_str:
                    i += 1
                    continue
                
                # Skip the ``` line
                i += 1
                
                # Collect code content until closing ```
                code_lines = []
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                if filepath_str and code_lines:
                    file_content = '\n'.join(code_lines)
                    
                    # Create the file
                    file_path = output_dir / filepath_str
                    
                    # Check for duplicate files (same filename in different paths)
                    file_name = file_path.name
                    for existing in saved_files:
                        if existing.name == file_name and existing != file_path:
                            print(f"  ⚠️  WARNING: Duplicate filename '{file_name}' detected!")
                            print(f"      Already saved: {existing.relative_to(output_dir)}")
                            print(f"      Trying to save: {file_path.relative_to(output_dir)}")
                            print(f"      Skipping duplicate to prevent overwrite.")
                            filepath_str = None
                            break
                    
                    if filepath_str:  # Not a duplicate
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.write_text(file_content, encoding='utf-8')
                        saved_files.append(file_path)
                        print(f"  💾 Saved: {file_path.relative_to(self.base_dir.parent)}")
            
            i += 1
        
        return saved_files
    
    def extract_and_save_structured_files(self, agent_name: str, content: str, run_id: str) -> List[Path]:
        """
        Alternative extraction method for structured file outputs.
        Looks for patterns like:
        
        FILE: path/to/file.ext
        ```language
        content
        ```
        
        Args:
            agent_name: Name of the agent
            content: Agent's output content
            run_id: Run identifier
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        agent_dir = self.AGENT_DIRS.get(agent_name)
        if not agent_dir:
            return saved_files
        
        output_dir = self.base_dir / agent_dir / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pattern: FILE: path/to/file.ext followed by code block
        file_pattern = r'(?:FILE|File|file):\s*([^\n]+)\s*```(?:[\w]+)?\n(.*?)```'
        
        matches = re.finditer(file_pattern, content, re.DOTALL)
        
        for match in matches:
            filepath = match.group(1).strip()
            file_content = match.group(2)
            
            file_path = output_dir / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(file_content, encoding='utf-8')
            saved_files.append(file_path)
    
    def _auto_convert_qa_files(self, content: str) -> str:
        """
        Auto-convert QA's markdown code blocks to FILE: format.
        
        Looks for patterns like:
        1. **filename.ext**
        ```language
        code
        ```
        
        And converts to:
        FILE: tests/filename.ext
        ```language
        code
        ```
        
        Args:
            content: QA agent's raw output
            
        Returns:
            Content with FILE: markers added
        """
        import re
        
        # Pattern to match: optional numbering, **filename.ext**, followed by code block
        # Examples:
        # 1. **RegistrationForm.spec.ts**
        # ```typescript
        # ...
        # ```
        pattern = r'(?:^|\n)\d*\.?\s*\*\*([a-zA-Z0-9_\-\.]+\.(ts|js|cs|spec\.ts|test\.ts|test\.cs|spec\.js))\*\*\s*\n```'
        
        def replacer(match):
            filename = match.group(1)
            # Determine path based on file extension
            if filename.endswith(('.spec.ts', '.spec.js', '.test.ts', '.test.js')):
                filepath = f"tests/{filename}"
            elif filename.endswith('.test.cs'):
                filepath = f"tests/{filename}"
            else:
                filepath = f"tests/{filename}"
            
            return f"\n\nFILE: {filepath}\n```"
        
        converted = re.sub(pattern, replacer, content)
        return converted
    
    def _auto_convert_backend_files(self, content: str) -> str:
        """
        Auto-convert Backend's markdown code blocks to FILE: format.
        
        Looks for patterns in "Code Artifacts" or "Saved Files" sections:
        - `Controllers/UserController.cs`
        - **Controllers/UserController.cs**
        
        Followed by:
        ```csharp
        code
        ```
        
        Args:
            content: Backend agent's raw output
            
        Returns:
            Content with FILE: markers added
        """
        import re
        
        # Pattern 1: Files mentioned in backticks or bold followed by code blocks
        # Examples:
        # - `Controllers/UserController.cs`
        # - **Models/User.cs**
        # ```csharp
        # ...
        # ```
        pattern1 = r'(?:^|\n)[-\*]\s*(?:`|\*\*)([A-Za-z0-9_/]+/[A-Za-z0-9_]+\.cs)(?:`|\*\*)\s*\n```'
        
        def replacer1(match):
            filepath = match.group(1)
            return f"\n\nFILE: {filepath}\n```"
        
        # Pattern 2: Section headers with file paths
        # Example:
        # #### Controllers/UserController.cs
        # ```csharp
        pattern2 = r'(?:^|\n)#{2,5}\s+([A-Za-z0-9_/]+/[A-Za-z0-9_]+\.cs)\s*\n```'
        
        def replacer2(match):
            filepath = match.group(1)
            return f"\n\nFILE: {filepath}\n```"
        
        converted = re.sub(pattern1, replacer1, content)
        converted = re.sub(pattern2, replacer2, converted)
        return converted
