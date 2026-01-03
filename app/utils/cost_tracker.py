"""
Cost Tracking Utility for LLM API Usage

Tracks token usage and estimated costs for each agent during workflow execution.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


# Pricing per 1M tokens (as of 2026-01-02)
# Update these values based on your provider's pricing
PRICING = {
    "openai": {
        "gpt-4.1": {"input": 10.00, "output": 30.00},  # Example pricing
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
    "zai": {
        "glm-4.7": {"input": 1.00, "output": 1.00},  # Adjust based on z.ai pricing
        "glm-4": {"input": 1.00, "output": 1.00},
    },
    "ollama": {
        "default": {"input": 0.00, "output": 0.00},  # Local models are free
    }
}


@dataclass
class AgentUsage:
    """Tracks usage for a single agent call."""
    agent_name: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: str
    iteration: int = 1
    attempt: int = 1  # For build fix retries
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CostTracker:
    """Tracks costs across all agent calls in a workflow."""
    
    def __init__(self, project_dir: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            project_dir: Project directory to save cost reports
        """
        self.project_dir = project_dir
        self.usage_records: List[AgentUsage] = []
        self.start_time = datetime.now()
        
    def record_usage(
        self,
        agent_name: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        iteration: int = 1,
        attempt: int = 1
    ) -> AgentUsage:
        """
        Record usage for an agent call.
        
        Args:
            agent_name: Name of the agent (designer, backend, frontend, qa)
            model: Model name used
            provider: Provider name (openai, zai, ollama)
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            iteration: QA iteration number
            attempt: Build fix attempt number
            
        Returns:
            AgentUsage record with calculated cost
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        usage = AgentUsage(
            agent_name=agent_name,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            timestamp=datetime.now().isoformat(),
            iteration=iteration,
            attempt=attempt
        )
        
        self.usage_records.append(usage)
        return usage
    
    def _calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost in USD based on token usage."""
        provider = provider.lower()
        
        # Get pricing for provider and model
        if provider in PRICING:
            if model in PRICING[provider]:
                pricing = PRICING[provider][model]
            else:
                # Use default for provider if available
                pricing = PRICING[provider].get("default", {"input": 0.0, "output": 0.0})
        else:
            # Unknown provider, assume free
            pricing = {"input": 0.0, "output": 0.0}
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_summary(self) -> Dict:
        """Get cost summary across all agents."""
        if not self.usage_records:
            return {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "total_calls": 0,
                "by_agent": {},
                "by_iteration": {}
            }
        
        total_cost = sum(r.cost_usd for r in self.usage_records)
        total_tokens = sum(r.total_tokens for r in self.usage_records)
        
        # Group by agent
        by_agent = {}
        for record in self.usage_records:
            if record.agent_name not in by_agent:
                by_agent[record.agent_name] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }
            by_agent[record.agent_name]["calls"] += 1
            by_agent[record.agent_name]["tokens"] += record.total_tokens
            by_agent[record.agent_name]["cost_usd"] += record.cost_usd
            by_agent[record.agent_name]["prompt_tokens"] += record.prompt_tokens
            by_agent[record.agent_name]["completion_tokens"] += record.completion_tokens
        
        # Group by iteration
        by_iteration = {}
        for record in self.usage_records:
            iter_key = f"iteration_{record.iteration}"
            if iter_key not in by_iteration:
                by_iteration[iter_key] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost_usd": 0.0
                }
            by_iteration[iter_key]["calls"] += 1
            by_iteration[iter_key]["tokens"] += record.total_tokens
            by_iteration[iter_key]["cost_usd"] += record.cost_usd
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_prompt_tokens": sum(r.prompt_tokens for r in self.usage_records),
            "total_completion_tokens": sum(r.completion_tokens for r in self.usage_records),
            "total_calls": len(self.usage_records),
            "duration_seconds": round(duration, 2),
            "by_agent": by_agent,
            "by_iteration": by_iteration,
            "provider": self.usage_records[0].provider if self.usage_records else "unknown",
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print formatted cost summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("💰 Cost Summary")
        print("=" * 60)
        
        print(f"\n📊 Overall:")
        print(f"   Provider: {summary['provider']}")
        print(f"   Total Cost: ${summary['total_cost_usd']:.4f} USD")
        print(f"   Total Tokens: {summary['total_tokens']:,}")
        print(f"     ↳ Prompt: {summary['total_prompt_tokens']:,}")
        print(f"     ↳ Completion: {summary['total_completion_tokens']:,}")
        print(f"   Total API Calls: {summary['total_calls']}")
        print(f"   Duration: {summary['duration_seconds']:.2f}s")
        
        print(f"\n🤖 By Agent:")
        for agent, data in sorted(summary['by_agent'].items()):
            print(f"   {agent.title():10s}: ${data['cost_usd']:.4f} | "
                  f"{data['tokens']:,} tokens | {data['calls']} calls")
        
        if len(summary['by_iteration']) > 1:
            print(f"\n🔄 By Iteration:")
            for iter_key, data in sorted(summary['by_iteration'].items()):
                iter_num = iter_key.split('_')[1]
                print(f"   Iteration {iter_num}: ${data['cost_usd']:.4f} | "
                      f"{data['tokens']:,} tokens | {data['calls']} calls")
        
        print("=" * 60)
    
    def save_report(self, filename: str = "cost_report.json"):
        """Save detailed cost report to JSON file."""
        if not self.project_dir:
            return
        
        report_path = self.project_dir / filename
        
        report = {
            "summary": self.get_summary(),
            "detailed_records": [r.to_dict() for r in self.usage_records]
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Cost report saved: {report_path}")
        
    def get_records(self) -> List[AgentUsage]:
        """Get all usage records."""
        return self.usage_records.copy()
