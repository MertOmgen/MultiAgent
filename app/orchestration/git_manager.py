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
    
    def get_status(self) -> str:
        """Get git status output."""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
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
    
    def check_available(self) -> bool:
        """Check if Git is available on the system."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return result.returncode == 0
        except Exception:
            return False
