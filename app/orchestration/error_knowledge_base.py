"""
Error Knowledge Base - Stores and retrieves error solutions.

Manager stores solved errors and their fixes here.
Agents consult this knowledge base before escalating to Manager.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ErrorSolution:
    """Represents a stored error and its solution."""
    error_id: str
    agent: str  # backend, frontend, devops
    error_type: str  # build, runtime, test, docker_config
    error_signature: str  # Key patterns from error message
    error_message: str  # Full error message (first occurrence)
    root_cause: str  # Manager's root cause analysis
    solution: str  # Manager's solution
    code_examples: str  # Code fixes
    prevention: str  # How to prevent
    solved_date: str
    project: str
    success_count: int = 0  # How many times this solution worked
    category: str = "general"  # infrastructure, architecture, general
    severity: str = "medium"  # low, medium, high, critical
    auto_fix: str = ""  # Automated fix instructions if available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorSolution':
        """Create from dictionary, ignoring unknown fields."""
        # Filter to only known fields to handle legacy data
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


class ErrorKnowledgeBase:
    """Manages the error knowledge base."""
    
    def __init__(self, kb_dir: str = "./outputs/.error_kb"):
        """
        Initialize knowledge base.
        
        Args:
            kb_dir: Directory to store knowledge base files
        """
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.kb_file = self.kb_dir / "error_solutions.json"
        self.solutions: Dict[str, ErrorSolution] = {}
        self._load()
    
    def _load(self):
        """Load existing solutions from disk."""
        if self.kb_file.exists():
            try:
                with open(self.kb_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.solutions = {
                        k: ErrorSolution.from_dict(v) 
                        for k, v in data.items()
                    }
                print(f"  📚 Loaded {len(self.solutions)} error solutions from knowledge base")
            except Exception as e:
                print(f"  ⚠️  Error loading knowledge base: {e}")
                self.solutions = {}
    
    def _save(self):
        """Save solutions to disk."""
        try:
            data = {k: v.to_dict() for k, v in self.solutions.items()}
            with open(self.kb_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠️  Error saving knowledge base: {e}")
    
    def _extract_error_signature(self, error_message: str) -> str:
        """
        Extract key patterns from error message for matching.
        
        Focuses on error types, missing symbols, package names, etc.
        """
        signatures = []
        
        # Common error patterns
        patterns = [
            # C# errors
            "error CS",
            "türü veya ad alanı adı bulunamadı",
            "type or namespace name could not be found",
            "using yönergeniz",
            "using directive",
            "derleme başvurunuz",
            "assembly reference",
            
            # Missing symbols
            "bulunamadı", "could not be found", "not found",
            "undefined", "tanımsız",
            
            # Package/namespace issues  
            "PackageReference",
            "NuGet",
            
            # TypeScript/Vue errors
            "TS",
            "Type",
            "Cannot find",
            "Module",
            "Import",
            
            # Build errors
            "build failed",
            "compilation failed",
        ]
        
        error_lower = error_message.lower()
        
        # Extract error codes (e.g., CS0246, TS2307)
        import re
        error_codes = re.findall(r'\b(CS\d+|TS\d+)\b', error_message, re.IGNORECASE)
        signatures.extend(error_codes)
        
        # Extract missing type/namespace names
        # Pattern: 'SomeType' türü veya ad alanı adı bulunamadı
        missing_types = re.findall(r"'(\w+)'.*(?:türü|type|namespace)", error_message, re.IGNORECASE)
        signatures.extend(missing_types)
        
        # Extract package names
        packages = re.findall(r'(?:PackageReference|package|using)\s+["\']?(\S+?)["\']?', error_message, re.IGNORECASE)
        signatures.extend(packages[:3])  # Limit to 3
        
        # Add matched patterns
        for pattern in patterns:
            if pattern.lower() in error_lower:
                signatures.append(pattern.lower())
        
        return " | ".join(signatures[:10])  # Limit signature size
    
    def find_similar_errors(
        self, 
        agent: str, 
        error_message: str, 
        error_type: str = "build",
        threshold: float = 0.3
    ) -> List[ErrorSolution]:
        """
        Find similar errors in knowledge base.
        
        Args:
            agent: Agent name (backend, frontend)
            error_message: Current error message
            error_type: Type of error (build, runtime, test)
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar error solutions, sorted by relevance
        """
        if not self.solutions:
            return []
        
        signature = self._extract_error_signature(error_message)
        error_lower = error_message.lower()
        
        matches = []
        
        for error_id, solution in self.solutions.items():
            # Must match agent and error type
            if solution.agent != agent or solution.error_type != error_type:
                continue
            
            # Calculate similarity score
            score = 0.0
            
            # Signature overlap
            sig_parts = set(signature.split(" | "))
            solution_sig_parts = set(solution.error_signature.split(" | "))
            if sig_parts and solution_sig_parts:
                overlap = len(sig_parts & solution_sig_parts)
                sig_score = overlap / max(len(sig_parts), len(solution_sig_parts))
                score += sig_score * 0.7  # 70% weight
            
            # Text similarity (simple word overlap)
            error_words = set(error_lower.split())
            solution_words = set(solution.error_message.lower().split())
            if error_words and solution_words:
                word_overlap = len(error_words & solution_words)
                word_score = word_overlap / max(len(error_words), len(solution_words))
                score += word_score * 0.3  # 30% weight
            
            if score >= threshold:
                matches.append((score, solution))
        
        # Sort by score descending, then by success count
        matches.sort(key=lambda x: (x[0], x[1].success_count), reverse=True)
        
        return [solution for score, solution in matches]
    
    def add_solution(
        self,
        agent: str,
        error_type: str,
        error_message: str,
        root_cause: str,
        solution: str,
        code_examples: str = "",
        prevention: str = "",
        project: str = "unknown"
    ) -> str:
        """
        Add a new error solution to the knowledge base.
        
        Args:
            agent: Agent name (backend, frontend)
            error_type: Type of error (build, runtime, test)
            error_message: Full error message
            root_cause: Manager's root cause analysis
            solution: Manager's solution
            code_examples: Code fixes
            prevention: Prevention strategy
            project: Project name
            
        Returns:
            error_id: Unique ID for this error
        """
        signature = self._extract_error_signature(error_message)
        error_id = f"{agent}_{error_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        solution_obj = ErrorSolution(
            error_id=error_id,
            agent=agent,
            error_type=error_type,
            error_signature=signature,
            error_message=error_message[:1000],  # Limit size
            root_cause=root_cause,
            solution=solution,
            code_examples=code_examples,
            prevention=prevention,
            solved_date=datetime.now().isoformat(),
            project=project,
            success_count=1
        )
        
        self.solutions[error_id] = solution_obj
        self._save()
        
        print(f"  💾 Saved error solution to knowledge base: {error_id}")
        print(f"     Signature: {signature[:100]}")
        
        return error_id
    
    def mark_solution_successful(self, error_id: str):
        """Mark a solution as successful (used again)."""
        if error_id in self.solutions:
            self.solutions[error_id].success_count += 1
            self._save()
            print(f"  ✅ Marked solution {error_id} as successful (count: {self.solutions[error_id].success_count})")
    
    def get_knowledge_base_summary(self) -> str:
        """Get a summary of the knowledge base for agents."""
        if not self.solutions:
            return "No error solutions in knowledge base yet."
        
        summary = f"📚 **Error Knowledge Base Summary**\n\n"
        summary += f"Total Solutions: {len(self.solutions)}\n\n"
        
        # Group by agent
        by_agent = {}
        for solution in self.solutions.values():
            if solution.agent not in by_agent:
                by_agent[solution.agent] = []
            by_agent[solution.agent].append(solution)
        
        for agent, solutions in by_agent.items():
            summary += f"**{agent.upper()}:** {len(solutions)} solutions\n"
            for sol in sorted(solutions, key=lambda x: x.success_count, reverse=True)[:5]:
                summary += f"  - {sol.error_signature[:80]}... (used {sol.success_count} times)\n"
        
        return summary
    
    def format_similar_solutions(self, solutions: List[ErrorSolution]) -> str:
        """Format similar solutions for agent consumption."""
        if not solutions:
            return "No similar errors found in knowledge base."
        
        result = f"📚 **Found {len(solutions)} Similar Error(s) in Knowledge Base:**\n\n"
        
        for i, sol in enumerate(solutions[:3], 1):  # Show top 3
            result += f"### Similar Error #{i} (Success Rate: {sol.success_count} times)\n\n"
            result += f"**Original Error:** {sol.error_signature}\n\n"
            result += f"**Root Cause:** {sol.root_cause}\n\n"
            result += f"**Solution:**\n{sol.solution}\n\n"
            if sol.code_examples:
                result += f"**Code Examples:**\n{sol.code_examples}\n\n"
            if sol.prevention:
                result += f"**Prevention:** {sol.prevention}\n\n"
            result += "---\n\n"
        
        return result
