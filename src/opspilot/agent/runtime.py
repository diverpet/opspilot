"""Agent runtime - coordinates FSM, MCP client, and LLM."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .fsm import AgentFSM
from .schemas import ReportOutput
from ..llm.base import BaseLLM
from ..llm.dummy_llm import DummyLLM
from ..llm.openai_llm import OpenAILLM
from ..mcp_client.client import MCPClientContext
from ..observability.tracer import Tracer
from ..utils import get_artifacts_dir


def get_llm() -> BaseLLM:
    """Get the appropriate LLM based on environment."""
    provider = os.environ.get("LLM_PROVIDER", "dummy").lower()
    
    if provider == "openai":
        if os.environ.get("OPENAI_API_KEY"):
            return OpenAILLM()
        else:
            print("Warning: LLM_PROVIDER=openai but OPENAI_API_KEY not set, falling back to dummy")
            return DummyLLM()
    else:
        return DummyLLM()


class AgentRuntime:
    """Runtime environment for the OpsPilot agent."""
    
    def __init__(self, mcp_command: str, output_dir: Optional[Path] = None):
        """Initialize the agent runtime.
        
        Args:
            mcp_command: Command to start the MCP server
            output_dir: Optional output directory for artifacts
        """
        self.mcp_command = mcp_command
        
        if output_dir is None:
            output_dir = get_artifacts_dir()
        
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        self.tracer = Tracer(output_dir)
        self.llm = get_llm()
    
    async def run(self, service: str, alert: str, time_range: str) -> tuple[ReportOutput, Path, Path]:
        """Run the agent.
        
        Args:
            service: Service name
            alert: Alert text
            time_range: Time range for investigation
            
        Returns:
            Tuple of (report, report_path, trace_path)
        """
        # Use context manager for proper MCP client lifecycle
        async with MCPClientContext(self.mcp_command, self.tracer) as mcp_client:
            # Create and run FSM
            fsm = AgentFSM(self.llm, mcp_client, self.tracer)
            report = await fsm.run(service, alert, time_range)
            
            # Save report
            report_path = self._save_report(report)
            trace_path = self.tracer.get_trace_file()
            
            return report, report_path, trace_path
    
    def _save_report(self, report: ReportOutput) -> Path:
        """Save report to markdown file."""
        session_id = self.tracer.get_session_id()
        report_path = self.output_dir / f"report_{session_id}.md"
        
        content = self._format_report_md(report)
        report_path.write_text(content)
        
        return report_path
    
    def _format_report_md(self, report: ReportOutput) -> str:
        """Format report as markdown."""
        lines = [
            f"# {report.title}",
            "",
            f"**Service:** {report.service}",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Confidence:** {report.confidence:.0%}",
            "",
            "## Alert Summary",
            "",
            report.alert_summary,
            "",
            "## Root Cause Analysis",
            "",
            report.root_cause,
            "",
            "## Evidence Chain",
            ""
        ]
        
        for i, evidence in enumerate(report.evidence_chain, 1):
            lines.append(f"{i}. **{evidence.source}**: {evidence.finding}")
        
        lines.extend([
            "",
            "## Immediate Actions",
            ""
        ])
        
        for action in report.immediate_actions:
            lines.append(f"- [ ] {action}")
        
        if report.follow_up_actions:
            lines.extend([
                "",
                "## Follow-up Actions",
                ""
            ])
            for action in report.follow_up_actions:
                lines.append(f"- [ ] {action}")
        
        lines.extend([
            "",
            "## Investigation Metadata",
            "",
            f"- **Duration:** {report.investigation_duration_ms}ms",
            f"- **Tools Used:** {', '.join(report.tools_used)}",
        ])
        
        if report.missing_info:
            lines.append(f"- **Missing Information:** {', '.join(report.missing_info)}")
        
        lines.append("")
        
        return "\n".join(lines)
