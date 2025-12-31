"""Utility for automatically installing npm dependencies in frontend projects."""

import subprocess
import asyncio
from pathlib import Path
from typing import Optional


class NpmInstaller:
    """Handles npm installation for frontend projects."""
    
    def __init__(self, frontend_base_dir: str = "./outputs/frontend"):
        """
        Initialize npm installer.
        
        Args:
            frontend_base_dir: Base directory for frontend outputs
        """
        self.base_dir = Path(frontend_base_dir)
    
    async def install_dependencies_async(self, project_dir: Path) -> bool:
        """
        Install npm dependencies asynchronously.
        
        Args:
            project_dir: Directory containing package.json
            
        Returns:
            True if successful, False otherwise
        """
        package_json = project_dir / "package.json"
        
        if not package_json.exists():
            print(f"  ⚠️  No package.json found in {project_dir}")
            return False
        
        print(f"  📦 Installing npm dependencies in {project_dir.name}...")
        
        try:
            # Run npm install
            process = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"  ✅ npm install completed successfully")
                return True
            else:
                print(f"  ❌ npm install failed:")
                print(f"     {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            print(f"  ❌ npm not found. Please install Node.js and npm.")
            return False
        except Exception as e:
            print(f"  ❌ Error during npm install: {e}")
            return False
    
    def install_dependencies_sync(self, project_dir: Path) -> bool:
        """
        Install npm dependencies synchronously.
        
        Args:
            project_dir: Directory containing package.json
            
        Returns:
            True if successful, False otherwise
        """
        package_json = project_dir / "package.json"
        
        if not package_json.exists():
            print(f"  ⚠️  No package.json found in {project_dir}")
            return False
        
        print(f"  📦 Installing npm dependencies in {project_dir.name}...")
        
        try:
            # Run npm install
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                shell=True  # Required on Windows
            )
            
            if result.returncode == 0:
                print(f"  ✅ npm install completed successfully")
                return True
            else:
                print(f"  ❌ npm install failed:")
                print(f"     {result.stderr}")
                return False
                
        except FileNotFoundError:
            print(f"  ❌ npm not found. Please install Node.js and npm.")
            return False
        except subprocess.TimeoutExpired:
            print(f"  ❌ npm install timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"  ❌ Error during npm install: {e}")
            return False
    
    def check_npm_available(self) -> bool:
        """
        Check if npm is available on the system.
        
        Returns:
            True if npm is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True  # Required on Windows
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
