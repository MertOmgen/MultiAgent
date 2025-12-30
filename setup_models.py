"""
Ollama Model Setup Script

This script helps verify and pull the required Ollama models for each agent.
"""

import os
import subprocess
import sys


REQUIRED_MODELS = {
    "designer": "llama3.1:8b",
    "backend": "qwen2.5-coder:7b",
    "frontend": "qwen2.5-coder:7b",
    "qa": "deepseek-coder:6.7b",
}


def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        # Try common Ollama executable locations on Windows
        ollama_paths = [
            "ollama",  # In PATH
            r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.environ.get("USERNAME", "")),
            r"C:\Program Files\Ollama\ollama.exe",
        ]
        
        for ollama_cmd in ollama_paths:
            try:
                result = subprocess.run(
                    [ollama_cmd, "list"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True, ollama_cmd
            except (FileNotFoundError, OSError):
                continue
        
        return False, None
    except subprocess.TimeoutExpired:
        return False, None


def get_installed_models(ollama_cmd="ollama"):
    """Get list of installed Ollama models."""
    try:
        result = subprocess.run(
            [ollama_cmd, "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Parse output to extract model names
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = [line.split()[0] for line in lines if line.strip()]
            return models
        return []
    except Exception as e:
        print(f"Error getting installed models: {e}")
        return []


def pull_model(model_name, ollama_cmd="ollama"):
    """Pull a specific Ollama model."""
    print(f"  Pulling {model_name}...")
    try:
        result = subprocess.run(
            [ollama_cmd, "pull", model_name],
            capture_output=False,
            timeout=600  # 10 minutes timeout for large models
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timeout pulling {model_name}")
        return False
    except Exception as e:
        print(f"  ❌ Error pulling {model_name}: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Ollama Model Setup for MultiAgent")
    print("=" * 60)
    
    # Check if Ollama is running
    print("\n1. Checking Ollama service...")
    is_running, ollama_cmd = check_ollama_running()
    
    if not is_running:
        print("  ❌ Ollama is not running or not installed")
        print("\n  Installation steps:")
        print("  1. Download from: https://ollama.com/")
        print("  2. Install Ollama")
        print("  3. Ollama should auto-start as a service")
        print("  4. Or manually run: ollama serve")
        print("\n  💡 On Windows, check if Ollama is in system tray")
        sys.exit(1)
    
    print(f"  ✅ Ollama is running (found at: {ollama_cmd})")
    
    # Get installed models
    print("\n2. Checking installed models...")
    installed = get_installed_models(ollama_cmd)
    print(f"  Found {len(installed)} installed models")
    if installed:
        for model in installed:
            print(f"    - {model}")
    
    # Check and pull required models
    print("\n3. Verifying required models...")
    unique_models = set(REQUIRED_MODELS.values())
    
    for agent_role, model_name in REQUIRED_MODELS.items():
        status = "✅" if model_name in installed else "❌"
        print(f"  {status} {agent_role:10s} -> {model_name}")
    
    # Pull missing models
    missing = [m for m in unique_models if m not in installed]
    
    if missing:
        print(f"\n4. Pulling {len(missing)} missing model(s)...")
        print("  ⚠️  This may take several minutes (models are 4-8GB each)")
        for model in missing:
            if not pull_model(model, ollama_cmd):
                print(f"  ❌ Failed to pull {model}")
                sys.exit(1)
        print("  ✅ All models pulled successfully")
    else:
        print("\n✅ All required models are already installed")
    
    # Final summary
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nAgent Model Assignments:")
    for agent_role, model_name in REQUIRED_MODELS.items():
        print(f"  • {agent_role:10s} : {model_name}")
    print("\nYou can now run: python app/main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
