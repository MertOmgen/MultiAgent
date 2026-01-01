"""
File Extractor - Robust extraction of files from LLM output.

Handles:
- FILE: path/to/file.ext markers
- Invisible Unicode characters (zero-width joiners, etc.)
- Various code block formats
"""

import re
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExtractedFile:
    """Represents an extracted file."""
    path: str
    content: str
    language: Optional[str] = None


def clean_unicode(text: str) -> str:
    """Remove invisible Unicode format characters (zero-width joiner, etc.)."""
    return ''.join(c for c in text if unicodedata.category(c) != 'Cf')


def extract_files_from_content(content: str) -> List[ExtractedFile]:
    """
    Extract all files from LLM output content.
    
    Looks for patterns:
    - FILE: path/to/file.ext
      ```language
      content
      ```
    
    Args:
        content: Raw LLM output
        
    Returns:
        List of ExtractedFile objects
    """
    files = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        cleaned = clean_unicode(stripped)
        
        filepath = None
        
        # Pattern 1: FILE: path/to/file.ext (various formats)
        file_markers = ['FILE:', 'File:', 'file:']
        for marker in file_markers:
            if marker in cleaned:
                parts = cleaned.split(':', 1)
                if len(parts) > 1:
                    filepath = parts[1].strip()
                    # Remove markdown formatting
                    filepath = filepath.replace('`', '').replace('*', '').strip()
                    break
        
        # Pattern 2: Markdown header with backticks: ##### `filename.ext`
        if not filepath and cleaned.startswith('#') and '`' in cleaned:
            match = re.search(r'`([^`]+\.[a-zA-Z0-9]+)`', cleaned)
            if match:
                filepath = match.group(1).strip()
        
        if filepath:
            # Look for code block start
            i += 1
            language = None
            
            while i < len(lines):
                check_line = clean_unicode(lines[i].strip())
                
                if check_line.startswith('```'):
                    # Extract language hint
                    lang_match = re.match(r'```(\w+)?', check_line)
                    if lang_match:
                        language = lang_match.group(1)
                    break
                elif check_line == '':
                    i += 1  # Skip blank lines
                else:
                    filepath = None  # No code block found
                    break
            
            if i >= len(lines) or not filepath:
                i += 1
                continue
            
            # Skip the opening ``` line
            i += 1
            
            # Collect content until closing ```
            code_lines = []
            while i < len(lines):
                check_line = clean_unicode(lines[i].strip())
                if check_line.startswith('```'):
                    break
                code_lines.append(lines[i])
                i += 1
            
            # Skip the closing ``` line
            if i < len(lines):
                i += 1
            
            if filepath and code_lines:
                files.append(ExtractedFile(
                    path=filepath,
                    content='\n'.join(code_lines),
                    language=language
                ))
        
        i += 1
    
    return files


def save_extracted_files(files: List[ExtractedFile], output_dir: Path) -> List[Path]:
    """
    Save extracted files to output directory.
    
    Args:
        files: List of ExtractedFile objects
        output_dir: Directory to save files to
        
    Returns:
        List of saved file paths
    """
    saved = []
    seen_names = set()
    
    for file in files:
        # Check for duplicates
        filename = Path(file.path).name
        if filename in seen_names:
            print(f"  ⚠️  Skipping duplicate: {file.path}")
            continue
        seen_names.add(filename)
        
        # Create file
        file_path = output_dir / file.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file.content, encoding='utf-8')
        saved.append(file_path)
        print(f"  💾 {file.path}")
    
    return saved


# Auto-conversion patterns for agents that don't use FILE: format

def auto_convert_to_file_format(content: str, agent_type: str) -> str:
    """
    Auto-convert agent output to FILE: format if needed.
    
    Args:
        content: Agent's raw output
        agent_type: Type of agent (Backend, Frontend, QA)
        
    Returns:
        Content with FILE: markers added where possible
    """
    if agent_type == "Backend":
        return _convert_backend_output(content)
    elif agent_type == "Frontend":
        return _convert_frontend_output(content)
    elif agent_type == "QA":
        return _convert_qa_output(content)
    return content


def _convert_backend_output(content: str) -> str:
    """Convert Backend agent output to FILE: format."""
    
    # Pattern 1: Bullet points with file paths
    # - `Controllers/UserController.cs`
    # - **Models/User.cs**
    pattern1 = r'(?:^|\n)[-\*]\s*(?:`|\*\*)([A-Za-z0-9_/]+/[A-Za-z0-9_\.]+\.(?:cs|csproj|json|sln))(?:`|\*\*)\s*\n```'
    content = re.sub(pattern1, r'\n\nFILE: \1\n```', content)
    
    # Pattern 2: ### Headers with file names
    # ### Controllers/UserController.cs
    pattern2 = r'(?:^|\n)###\s+([A-Za-z0-9_/]+\.cs)\s*\n```'
    content = re.sub(pattern2, r'\n\nFILE: \1\n```', content)

    # Pattern 2b: Narrative instructions followed by a code fence
    # e.g., "Create a new file `Models/User.cs`:" on the line before ```
    pattern2b = r'(?:^|\n)(?:Create|Add|Implement)[^\n]*`([^`]+\.(?:cs|json|csproj|sln))`[^\n]*\n```'
    content = re.sub(pattern2b, r'\n\nFILE: \1\n```', content)
    
    # Pattern 3: appsettings.json / Program.cs sections
    config_pattern = r'(?:^|\n)(?:Example\s+)?(?:appsettings\.json|Program\.cs)\s*(?:configuration)?\s*\n+```'
    
    def config_replacer(match):
        text = match.group(0)
        if 'appsettings.json' in text.lower():
            return '\n\nFILE: appsettings.json\n```'
        elif 'program.cs' in text.lower():
            return '\n\nFILE: Program.cs\n```'
        return match.group(0)
    
    content = re.sub(config_pattern, config_replacer, content, flags=re.IGNORECASE)
    
    return content


def _convert_frontend_output(content: str) -> str:
    """Convert Frontend agent output to FILE: format."""
    
    # Pattern 1: npm Packages section -> package.json
    pattern1 = r'(?:###?\s*npm Packages[^\n]*|\*\*npm Packages[^\n]*\*\*:?)\s*\n```json\s*\n(\{[\s\S]*?"dependencies"[\s\S]*?\})\s*\n```'
    
    def package_replacer(match):
        return f'\n\nFILE: package.json\n```json\n{match.group(1)}\n```'
    
    content = re.sub(pattern1, package_replacer, content)
    
    # Pattern 2: **FILE: src/...** or `FILE: src/...`
    pattern2 = r'(?:^|\n)(?:\*\*|`)FILE:\s*([^\n*`]+?)(?:\*\*|`)\s*\n```'
    content = re.sub(pattern2, r'\n\nFILE: \1\n```', content)
    
    # Pattern 3: ### src/views/MyView.vue
    pattern3 = r'(?:^|\n)###\s+(src/[^\n]+\.(?:vue|ts|js))\s*\n```'
    content = re.sub(pattern3, r'\n\nFILE: \1\n```', content)

    # Pattern 3b: Narrative instructions referencing a filename and directory before a code fence
    pattern3b = r'(?:^|\n)(?:Create|Add|Implement)[^\n]*`([^`/]+\.(?:vue|ts|js|css|json))`[^\n]*`(src/[^`\n]+)`[^\n]*\n```'

    def narrative_replacer(match):
        filename = match.group(1)
        directory = match.group(2).rstrip('/')
        return f"\n\nFILE: {directory}/{filename}\n```"

    content = re.sub(pattern3b, narrative_replacer, content)
    
    return content


def _convert_qa_output(content: str) -> str:
    """Convert QA agent output to FILE: format."""
    
    # Pattern 1: **filename.spec.ts** or **filename.test.cs**
    pattern1 = r'(?:^|\n)\d*\.?\s*\*\*([a-zA-Z0-9_\-\.]+\.(?:spec\.ts|test\.ts|test\.cs|spec\.js))\*\*\s*\n```'
    
    def test_replacer(match):
        filename = match.group(1)
        return f'\n\nFILE: tests/{filename}\n```'
    
    content = re.sub(pattern1, test_replacer, content)
    
    # Pattern 2: Test plan markdown
    pattern2 = r'(?:^|\n)(?:###?\s*)?(?:Test Plan|test_plan\.md)\s*\n```(?:markdown)?'
    content = re.sub(pattern2, '\n\nFILE: test_plan.md\n```markdown', content, flags=re.IGNORECASE)
    
    return content
