"""
Agent Utilities - Common utilities for agent management.

Provides:
- Agent name mapping and standardization
- Role boundary validation
- Output format validation
"""

from typing import Dict, Optional, Tuple

# Standard agent directories
AGENT_DIRS: Dict[str, str] = {
    "Designer": "design",
    "Backend": "backend",
    "Frontend": "frontend",
    "QA": "qa",
}

# Agent name aliases to standard names
AGENT_ALIASES: Dict[str, str] = {
    "designer_agent": "Designer",
    "backend_agent": "Backend",
    "frontend_agent": "Frontend",
    "qa_agent": "QA",
    "designer": "Designer",
    "backend": "Backend",
    "frontend": "Frontend",
    "qa": "QA",
}

# File extensions each agent should produce
AGENT_FILE_EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "Designer": (".md", ".json"),
    "Backend": (".cs", ".csproj", ".sln", ".json"),
    "Frontend": (".vue", ".ts", ".js", ".tsx", ".jsx", ".json", ".css", ".scss"),
    "QA": (".cs", ".ts", ".js", ".md"),
}

# File extensions each agent should NOT produce (role violations)
AGENT_FORBIDDEN_EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "Designer": (".cs", ".vue", ".ts", ".js"),  # Designer shouldn't write code
    "Backend": (".vue", ".jsx", ".tsx"),  # Backend shouldn't write frontend
    "Frontend": (".cs", ".csproj", ".sln"),  # Frontend shouldn't write backend
    "QA": (),  # QA can write tests for any language
}


def standardize_agent_name(name: str) -> Optional[str]:
    """
    Convert agent name alias to standard name.
    
    Args:
        name: Agent name (may be alias like 'backend_agent')
        
    Returns:
        Standard name (e.g., 'Backend') or None if unknown
    """
    return AGENT_ALIASES.get(name.lower(), name.title() if name.title() in AGENT_DIRS else None)


def get_agent_dir(agent_name: str) -> Optional[str]:
    """
    Get output directory for agent.
    
    Args:
        agent_name: Standard or aliased agent name
        
    Returns:
        Directory name (e.g., 'backend') or None
    """
    standard_name = standardize_agent_name(agent_name)
    return AGENT_DIRS.get(standard_name) if standard_name else None


def validate_agent_output(agent_name: str, content: str) -> Tuple[bool, str]:
    """
    Validate agent output doesn't violate role boundaries.
    
    Args:
        agent_name: Standard agent name
        content: Agent's output content
        
    Returns:
        Tuple of (is_valid, warning_message)
    """
    standard_name = standardize_agent_name(agent_name)
    if not standard_name:
        return True, ""
    
    forbidden = AGENT_FORBIDDEN_EXTENSIONS.get(standard_name, ())
    
    # Check if FILE: markers contain forbidden extensions
    if 'FILE:' in content:
        for ext in forbidden:
            # Look for FILE: markers with forbidden extensions
            if f'{ext}\n' in content or f'{ext}`' in content or content.endswith(ext):
                return False, f"{standard_name} agent appears to be generating {ext} files (role violation)"
    
    return True, ""


def check_file_format_usage(content: str) -> Tuple[bool, int]:
    """
    Check if content properly uses FILE: format.
    
    Args:
        content: Agent's output content
        
    Returns:
        Tuple of (has_file_markers, count_of_markers)
    """
    import re
    markers = re.findall(r'(?:^|\n)\s*FILE:\s*[^\n]+', content, re.IGNORECASE)
    return len(markers) > 0, len(markers)


def check_code_blocks_without_file(content: str) -> int:
    """
    Count code blocks that don't have FILE: markers.
    
    Args:
        content: Agent's output content
        
    Returns:
        Number of orphan code blocks
    """
    import re
    
    # Find all code blocks
    code_blocks = re.findall(r'```\w*\n[\s\S]*?```', content)
    
    # Find FILE: markers followed by code blocks
    file_blocks = re.findall(r'FILE:[^\n]+\n\s*```', content, re.IGNORECASE)
    
    # Orphan = total blocks - blocks with FILE markers
    return max(0, len(code_blocks) - len(file_blocks))
