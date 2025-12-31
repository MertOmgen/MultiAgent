"""Project state management for continuous development across multiple runs."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class Project:
    """Represents a persistent project that can be developed over multiple runs."""
    
    def __init__(self, name: str, directory: Path, metadata: Dict[str, Any] = None):
        self.name = name
        self.project_dir = directory  # Use project_dir to match workflow usage
        self.directory = directory    # Keep for backward compatibility
        self.metadata = metadata or {}
        self.metadata_file = directory / ".project.json"
        
        # Cached data
        self.file_tree = None
        self.important_files = []
    
    def save_metadata(self):
        """Save project metadata."""
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')
    
    def load_metadata(self):
        """Load project metadata."""
        if self.metadata_file.exists():
            self.metadata = json.loads(self.metadata_file.read_text(encoding='utf-8'))
    
    def refresh_cache(self):
        """Refresh cached file tree and important files."""
        self.file_tree = self.get_file_tree()
        self.important_files = self.get_important_files()
    
    def get_important_files(self, max_files: int = 20) -> List[Dict[str, str]]:
        """
        Get list of important files to include in context.
        
        Returns:
            List of dicts with 'path' and 'content' keys
        """
        important_patterns = [
            # Backend
            "**/Program.cs",
            "**/appsettings.json",
            "**/*.csproj",
            "**/Controllers/**/*.cs",
            "**/Models/**/*.cs",
            "**/Services/**/*.cs",
            
            # Frontend
            "**/package.json",
            "**/vite.config.ts",
            "**/tsconfig.json",
            "**/src/main.ts",
            "**/src/App.vue",
            "**/src/router/**/*.ts",
            "**/src/stores/**/*.ts",
        ]
        
        files = []
        for pattern in important_patterns:
            for file in self.directory.glob(pattern):
                if file.is_file() and len(files) < max_files:
                    try:
                        content = file.read_text(encoding='utf-8')
                        files.append({
                            'path': str(file.relative_to(self.directory)),
                            'content': content
                        })
                    except Exception:
                        continue  # Skip files that can't be read
        
        return files
    
    def get_file_tree(self, max_depth: int = 3) -> str:
        """
        Get project file tree structure.
        
        Args:
            max_depth: Maximum directory depth to display
            
        Returns:
            Formatted tree string
        """
        def build_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
            if depth > max_depth:
                return []
            
            lines = []
            # Exclude common ignored directories
            ignore = {'.git', 'node_modules', 'bin', 'obj', '.vs', 'dist', '__pycache__', '.venv'}
            
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                for i, entry in enumerate(entries):
                    if entry.name in ignore or entry.name.startswith('.'):
                        continue
                    
                    is_last = i == len(entries) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "
                    
                    lines.append(f"{prefix}{current_prefix}{entry.name}")
                    
                    if entry.is_dir():
                        lines.extend(build_tree(entry, prefix + next_prefix, depth + 1))
            except PermissionError:
                pass
            
            return lines
        
        lines = [self.directory.name + "/"]
        lines.extend(build_tree(self.directory))
        return "\n".join(lines)


class ProjectManager:
    """Manages persistent projects for continuous development."""
    
    def __init__(self, base_dir: str = "./outputs/projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_or_create_project(self, project_name: str) -> Project:
        """
        Get existing project or create new one.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Project instance
        """
        project_dir = self.base_dir / project_name
        
        if project_dir.exists():
            return self._load_existing(project_dir, project_name)
        else:
            return self._create_new(project_dir, project_name)
    
    def _load_existing(self, project_dir: Path, project_name: str) -> Project:
        """Load existing project."""
        project = Project(project_name, project_dir)
        project.load_metadata()
        project.refresh_cache()  # Load file tree and important files
        
        print(f"📂 Loaded existing project: {project_name}")
        if 'created_at' in project.metadata:
            print(f"   Created: {project.metadata['created_at']}")
        if 'last_updated' in project.metadata:
            print(f"   Last updated: {project.metadata['last_updated']}")
        if 'iterations' in project.metadata:
            print(f"   Iterations: {project.metadata['iterations']}")
        
        return project
    
    def _create_new(self, project_dir: Path, project_name: str) -> Project:
        """Create new project."""
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create project structure
        (project_dir / "backend").mkdir(exist_ok=True)
        (project_dir / "frontend").mkdir(exist_ok=True)
        (project_dir / "qa").mkdir(exist_ok=True)
        (project_dir / "design").mkdir(exist_ok=True)
        
        metadata = {
            "name": project_name,
            "created_at": datetime.now().isoformat(),
            "iterations": 0,
            "tasks": []
        }
        
        project = Project(project_name, project_dir, metadata)
        project.save_metadata()
        
        print(f"✨ Created new project: {project_name}")
        print(f"   Location: {project_dir}")
        
        return project
    
    def list_projects(self) -> List[str]:
        """List all existing projects."""
        if not self.base_dir.exists():
            return []
        
        projects = []
        for path in self.base_dir.iterdir():
            if path.is_dir() and (path / ".project.json").exists():
                projects.append(path.name)
        
        return sorted(projects)
    
    def load_project_context(self, project_name: str, include_files: bool = True) -> str:
        """
        Load project context for agents.
        
        Args:
            project_name: Name of project to load
            include_files: Whether to include file contents
            
        Returns:
            Formatted context string
        """
        project = self.get_or_create_project(project_name)
        
        context_parts = []
        
        # Project info
        context_parts.append("=" * 80)
        context_parts.append(f"EXISTING PROJECT: {project.name}")
        context_parts.append("=" * 80)
        
        # File tree
        if project.file_tree:
            context_parts.append("\n📁 PROJECT STRUCTURE:")
            context_parts.append(project.file_tree)
        
        # Important files
        if include_files and project.important_files:
            context_parts.append("\n" + "=" * 80)
            context_parts.append("📄 KEY EXISTING FILES:")
            context_parts.append("=" * 80)
            
            for file_info in project.important_files:
                context_parts.append(f"\nFILE: {file_info['path']}")
                context_parts.append("-" * 80)
                context_parts.append(file_info['content'])
                context_parts.append("-" * 80)
        
        # Previous tasks
        if project.metadata.get('tasks'):
            context_parts.append("\n" + "=" * 80)
            context_parts.append("📋 PREVIOUS TASKS:")
            context_parts.append("=" * 80)
            for i, task in enumerate(project.metadata['tasks'][-5:], 1):  # Last 5 tasks
                context_parts.append(f"{i}. {task.get('description', 'Unknown')}")
                context_parts.append(f"   Completed: {task.get('completed_at', 'Unknown')}")
        
        context_parts.append("\n" + "=" * 80)
        
        return "\n".join(context_parts)
    
    def refresh_project(self, project_name: str):
        """
        Refresh project cache after new files are added.
        
        Args:
            project_name: Name of project to refresh
        """
        project = self.get_or_create_project(project_name)
        project.refresh_cache()
        print(f"   ✅ Refreshed project context")
    
    def add_task_to_history(self, project_name: str, task_description: str, run_id: str = None):
        """
        Add completed task to project history.
        
        Args:
            project_name: Name of project
            task_description: Description of the completed task
            run_id: Optional run ID for reference
        """
        project = self.get_or_create_project(project_name)
        
        if 'tasks' not in project.metadata:
            project.metadata['tasks'] = []
        
        task_entry = {
            'description': task_description,
            'completed_at': datetime.now().isoformat()
        }
        if run_id:
            task_entry['run_id'] = run_id
        
        project.metadata['tasks'].append(task_entry)
        project.metadata['iterations'] = len(project.metadata['tasks'])
        project.save_metadata()
