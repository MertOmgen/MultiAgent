"""Git integration for version control and change tracking."""

import subprocess
from pathlib import Path
from typing import Optional, List


class GitManager:
    """Manages Git operations for project version control."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
    
    def init_repo(self) -> bool:
        """
        Initialize Git repository if not already initialized.
        
        Returns:
            True if successful, False otherwise
        """
        git_dir = self.project_dir / ".git"
        if git_dir.exists():
            return True
        
        try:
            result = subprocess.run(
                ["git", "init"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0:
                # Create .gitignore
                gitignore_content = """
# Dependencies
node_modules/
venv/
.venv/

# Build outputs
dist/
build/
bin/
obj/

# IDE
.vs/
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local

# Logs
*.log
npm-debug.log*

# Test results
*.trx
coverage/

# Agent outputs
*_output.md
"""
                gitignore_path = self.project_dir / ".gitignore"
                gitignore_path.write_text(gitignore_content.strip(), encoding='utf-8')
                
                print(f"   ✅ Git repository initialized")
                return True
            else:
                print(f"   ⚠️  Failed to initialize Git: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ⚠️  Git init error: {e}")
            return False
    
    def commit(self, message: str, add_all: bool = True) -> bool:
        """
        Create a Git commit.
        
        Args:
            message: Commit message
            add_all: Whether to add all files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if add_all:
                # Stage all changes
                add_result = subprocess.run(
                    ["git", "add", "."],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    shell=True
                )
                
                if add_result.returncode != 0:
                    print(f"   ⚠️  Git add failed: {add_result.stderr}")
                    return False
            
            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                shell=True
            )
            
            if commit_result.returncode == 0:
                print(f"   ✅ Git commit: {message}")
                return True
            elif "nothing to commit" in commit_result.stdout:
                print(f"   ℹ️  No changes to commit")
                return True
            else:
                print(f"   ⚠️  Git commit failed: {commit_result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ⚠️  Git commit error: {e}")
            return False
    
    def tag_iteration(self, iteration: int, run_id: str, description: str = "") -> bool:
        """
        Create a Git tag for an iteration.
        
        Args:
            iteration: Iteration number
            run_id: Workflow run ID
            description: Optional description
            
        Returns:
            True if successful
        """
        try:
            tag_name = f"iter{iteration}_{run_id}"
            tag_message = f"Iteration {iteration}"
            if description:
                tag_message += f": {description}"
            
            result = subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception:
            return False
    
    def get_status(self) -> str:
        """Get git status output."""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            return result.stdout
        except Exception:
            return ""
    
    def get_log(self, max_commits: int = 5) -> List[str]:
        """
        Get recent commit history.
        
        Args:
            max_commits: Maximum number of commits to return
            
        Returns:
            List of commit messages
        """
        try:
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--oneline"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
            return []
        except Exception:
            return []
    
    def rollback(self, commits: int = 1) -> bool:
        """
        Rollback to previous commit(s).
        
        Args:
            commits: Number of commits to rollback
            
        Returns:
            True if successful
        """
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", f"HEAD~{commits}"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ Rolled back {commits} commit(s)")
                return True
            else:
                print(f"   ⚠️  Rollback failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ⚠️  Rollback error: {e}")
            return False
    
    def get_tags(self) -> List[tuple]:
        """
        Get all iteration tags.
        
        Returns:
            List of (tag_name, message) tuples
        """
        try:
            # Get tags with messages
            result = subprocess.run(
                ["git", "tag", "-n"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                tags = []
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        tags.append((parts[0], parts[1]))
                    elif len(parts) == 1:
                        tags.append((parts[0], ""))
                return tags
            return []
        except Exception:
            return []
    
    def rollback_to_tag(self, tag_name: str) -> bool:
        """
        Rollback to a specific Git tag.
        
        Args:
            tag_name: Name of the tag to rollback to
            
        Returns:
            True if successful
        """
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", tag_name],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                shell=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ Rolled back to tag: {tag_name}")
                return True
            else:
                print(f"   ⚠️  Rollback failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ⚠️  Rollback error: {e}")
            return False
    
    def rollback_to_iteration(self, iteration: int) -> bool:
        """
        Rollback to a specific iteration number.
        
        Args:
            iteration: Iteration number to rollback to
            
        Returns:
            True if successful
        """
        tags = self.get_tags()
        # Find the most recent tag for this iteration
        matching_tags = [tag for tag, _ in tags if tag.startswith(f"iter{iteration}_")]
        
        if not matching_tags:
            print(f"   ⚠️  No tag found for iteration {iteration}")
            return False
        
        # Use the last matching tag (most recent for that iteration)
        tag_name = matching_tags[-1]
        return self.rollback_to_tag(tag_name)
    
    def check_available(self) -> bool:
        """Check if Git is available on the system."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                shell=True
            )
            return result.returncode == 0
        except Exception:
            return False
