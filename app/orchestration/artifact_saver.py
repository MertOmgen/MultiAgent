"""
Artifact Saver - Saves agent outputs to appropriate directories.

Refactored to use:
- file_extractor.py for FILE: pattern extraction
- agent_utils.py for agent name standardization
"""

from pathlib import Path
from typing import List, Optional

from .file_extractor import (
    extract_files_from_content,
    save_extracted_files,
    auto_convert_to_file_format,
)
from .agent_utils import (
    AGENT_DIRS,
    standardize_agent_name,
    get_agent_dir,
    validate_agent_output,
    check_file_format_usage,
)


class ArtifactSaver:
    """Handles parsing and saving agent outputs to appropriate directories."""
    
    # Expose AGENT_DIRS for backward compatibility
    AGENT_DIRS = AGENT_DIRS
    
    def __init__(self, base_outputs_dir: str = "./outputs"):
        """
        Initialize artifact saver.
        
        Args:
            base_outputs_dir: Base directory for all outputs
        """
        self.base_dir = Path(base_outputs_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Note: Agent-specific directories are created on-demand in save_agent_artifacts
        # to avoid creating empty folders directly under outputs/
    
    def save_agent_artifacts(
        self, 
        agent_name: str, 
        content: str, 
        run_id: str = None,
        base_dir: str = None
    ) -> List[Path]:
        """
        Parse agent output and save artifacts to appropriate directory.
        
        Args:
            agent_name: Name of the agent (Designer, Backend, Frontend, QA)
            content: Agent's output content
            run_id: Run identifier for organizing outputs (optional for project mode)
            base_dir: Custom base directory (for project mode)
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        # Standardize agent name
        standard_name = standardize_agent_name(agent_name)
        if not standard_name:
            print(f"⚠️  Unknown agent: {agent_name}, skipping artifact save")
            return saved_files
        
        agent_dir = get_agent_dir(standard_name)
        
        # Validate output doesn't violate role boundaries
        is_valid, warning = validate_agent_output(standard_name, content)
        if not is_valid:
            print(f"  ⚠️  WARNING: {warning}")
        
        # Determine output directory
        if base_dir:
            output_dir = Path(base_dir) / agent_dir
        elif run_id:
            output_dir = self.base_dir / agent_dir / run_id
        else:
            output_dir = self.base_dir / agent_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-convert to FILE: format if needed
        converted_content = auto_convert_to_file_format(content, standard_name)
        
        # Check if FILE: format is being used
        has_markers, marker_count = check_file_format_usage(converted_content)
        if has_markers:
            print(f"  📄 Found {marker_count} FILE: marker(s)")
        
        # Extract and save structured files
        extracted = extract_files_from_content(converted_content)
        if extracted:
            saved = save_extracted_files(extracted, output_dir)
            saved_files.extend(saved)
        
        # Always save raw output as markdown reference
        self._save_raw_output(
            standard_name, 
            content, 
            output_dir, 
            run_id,
            base_dir
        )
        
        return saved_files
    
    def _save_raw_output(
        self,
        agent_name: str,
        content: str,
        output_dir: Path,
        run_id: Optional[str],
        base_dir: Optional[str]
    ) -> Path:
        """Save raw agent output as markdown file."""
        filename = f"{agent_name.lower()}_output.md"
        filepath = output_dir / filename
        
        # Check if this is an iteration
        is_iteration = run_id and '_iter' in run_id
        
        if is_iteration and filepath.exists():
            # Append to existing file
            iteration_num = run_id.split('_iter')[-1] if '_iter' in run_id else '?'
            with filepath.open('a', encoding='utf-8') as f:
                f.write(f"\n\n{'=' * 80}\n")
                f.write(f"# ITERATION {iteration_num}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(content)
            print(f"  ➕ Appended to: {filename} (iteration {iteration_num})")
        else:
            filepath.write_text(content, encoding='utf-8')
            print(f"  📝 Raw output: {filename}")
        
        return filepath
