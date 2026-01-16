import os
from mcp_bridge.metrics.cost_tracker import get_cost_tracker

async def get_cost_report(session_id: str | None = None) -> str:
    """Get a cost report for the current or specified session."""
    tracker = get_cost_tracker()
    summary = tracker.get_session_summary(session_id)
    
    lines = ["## Agent Cost Report"]
    lines.append(f"**Total Cost**: ${summary['total_cost']:.4f}")
    lines.append(f"**Total Tokens**: {summary['total_tokens']:,}")
    lines.append("")
    lines.append("| Agent | Tokens | Cost |")
    lines.append("|---|---|---|")
    
    for agent, data in summary["by_agent"].items():
        lines.append(f"| {agent} | {data['tokens']:,} | ${data['cost']:.4f} |")
        
    return "\n".join(lines)
