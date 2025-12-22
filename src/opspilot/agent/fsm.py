"""Finite State Machine for agent workflow."""

import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from .schemas import (
    AgentState,
    IntakeOutput, ClarifyOutput, InvestigateOutput,
    HypothesisOutput, VerifyOutput, RecommendOutput, ReportOutput,
    ToolResult,
    get_fallback_intake, get_fallback_clarify, get_fallback_investigate,
    get_fallback_hypothesis, get_fallback_verify, get_fallback_recommend,
    get_fallback_report
)
from .prompts import (
    get_intake_prompt, get_clarify_prompt, get_investigate_prompt,
    get_hypothesis_prompt, get_verify_prompt, get_recommend_prompt,
    get_report_prompt
)
from ..llm.base import BaseLLM
from ..mcp_client.client import MCPClient
from ..observability.tracer import Tracer


class AgentFSM:
    """Finite State Machine for the OpsPilot agent."""
    
    def __init__(
        self,
        llm: BaseLLM,
        mcp_client: MCPClient,
        tracer: Tracer
    ):
        self.llm = llm
        self.mcp_client = mcp_client
        self.tracer = tracer
        
        self.current_state = AgentState.INTAKE
        self.context: Dict[str, Any] = {}
        self.tool_results: List[ToolResult] = []
        self.start_time = time.time()
    
    async def run(self, service: str, alert: str, time_range: str) -> ReportOutput:
        """Run the FSM workflow.
        
        Args:
            service: Service name
            alert: Alert text
            time_range: Time range for investigation
            
        Returns:
            Final report output
        """
        self.context = {
            "service": service,
            "alert": alert,
            "time_range": time_range
        }
        
        while self.current_state not in (AgentState.COMPLETE, AgentState.ERROR):
            old_state = self.current_state
            await self._execute_state()
            
            self.tracer.trace_state_transition(
                from_state=old_state.value,
                to_state=self.current_state.value,
                context=self.context
            )
        
        return self.context.get("report", get_fallback_report(service, alert))
    
    async def _execute_state(self):
        """Execute the current state."""
        if self.current_state == AgentState.INTAKE:
            await self._execute_intake()
        elif self.current_state == AgentState.CLARIFY:
            await self._execute_clarify()
        elif self.current_state == AgentState.INVESTIGATE:
            await self._execute_investigate()
        elif self.current_state == AgentState.HYPOTHESIS:
            await self._execute_hypothesis()
        elif self.current_state == AgentState.VERIFY:
            await self._execute_verify()
        elif self.current_state == AgentState.RECOMMEND:
            await self._execute_recommend()
        elif self.current_state == AgentState.REPORT:
            await self._execute_report()
    
    async def _execute_intake(self):
        """Execute intake state."""
        prompt = get_intake_prompt(
            self.context["service"],
            self.context["alert"],
            self.context["time_range"]
        )
        
        start_time = time.time()
        result, success, error = await self.llm.call("intake", prompt, IntakeOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("intake", prompt, result.model_dump(), True, latency_ms)
            self.context.update(result.model_dump())
            
            if result.needs_clarification:
                self.current_state = AgentState.CLARIFY
            else:
                self.current_state = AgentState.INVESTIGATE
        else:
            self.tracer.trace_llm_call("intake", prompt, None, False, latency_ms, error)
            fallback = get_fallback_intake(
                self.context["service"],
                self.context["alert"],
                self.context["time_range"]
            )
            self.context.update(fallback.model_dump())
            self.current_state = AgentState.INVESTIGATE
    
    async def _execute_clarify(self):
        """Execute clarify state."""
        prompt = get_clarify_prompt(self.context)
        
        start_time = time.time()
        result, success, error = await self.llm.call("clarify", prompt, ClarifyOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("clarify", prompt, result.model_dump(), True, latency_ms)
            self.context["clarify_output"] = result.model_dump()
        else:
            self.tracer.trace_llm_call("clarify", prompt, None, False, latency_ms, error)
            fallback = get_fallback_clarify()
            self.context["clarify_output"] = fallback.model_dump()
        
        # Always proceed to investigate
        self.current_state = AgentState.INVESTIGATE
    
    async def _execute_investigate(self):
        """Execute investigate state - call MCP tools."""
        service = self.context["service"]
        time_range = self.context["time_range"]
        alert = self.context.get("alert", "")
        
        # Required: log_search
        log_result = await self.mcp_client.call_tool(
            "log_search",
            {
                "service": service,
                "query": "error OR timeout OR exception",
                "time_range": time_range,
                "limit": 20
            }
        )
        self.tool_results.append(ToolResult(
            tool_name="log_search",
            success="error" not in log_result,
            result=log_result,
            summary=log_result.get("summary", "")
        ))
        
        # Required: metric_query
        metric_result = await self.mcp_client.call_tool(
            "metric_query",
            {
                "service": service,
                "metric": "error_rate",
                "time_range": time_range
            }
        )
        self.tool_results.append(ToolResult(
            tool_name="metric_query",
            success="error" not in metric_result,
            result=metric_result,
            summary=metric_result.get("summary", "")
        ))
        
        # Also query latency
        latency_result = await self.mcp_client.call_tool(
            "metric_query",
            {
                "service": service,
                "metric": "latency",
                "time_range": time_range
            }
        )
        self.tool_results.append(ToolResult(
            tool_name="metric_query",
            success="error" not in latency_result,
            result=latency_result,
            summary=latency_result.get("summary", "")
        ))
        
        # Optional: change_history (if deployment/change related keywords)
        if any(kw in alert.lower() for kw in ["deploy", "change", "update", "release", "version"]):
            change_result = await self.mcp_client.call_tool(
                "change_history",
                {
                    "service": service,
                    "time_range": time_range,
                    "limit": 5
                }
            )
            self.tool_results.append(ToolResult(
                tool_name="change_history",
                success="error" not in change_result,
                result=change_result,
                summary=change_result.get("summary", "")
            ))
        else:
            # Always check for changes anyway
            change_result = await self.mcp_client.call_tool(
                "change_history",
                {
                    "service": service,
                    "time_range": time_range,
                    "limit": 5
                }
            )
            self.tool_results.append(ToolResult(
                tool_name="change_history",
                success="error" not in change_result,
                result=change_result,
                summary=change_result.get("summary", "")
            ))
        
        # Optional: runbook_lookup
        runbook_result = await self.mcp_client.call_tool(
            "runbook_lookup",
            {
                "service": service,
                "symptom": alert[:200],
                "limit": 3
            }
        )
        self.tool_results.append(ToolResult(
            tool_name="runbook_lookup",
            success="error" not in runbook_result,
            result=runbook_result,
            summary=runbook_result.get("summary", "")
        ))
        
        # Generate investigation summary with LLM
        prompt = get_investigate_prompt(self.context, [r.model_dump() for r in self.tool_results])
        
        start_time = time.time()
        result, success, error = await self.llm.call("investigate", prompt, InvestigateOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("investigate", prompt, result.model_dump(), True, latency_ms)
            # Merge tool results
            result.tool_calls_made = self.tool_results
            self.context.update(result.model_dump())
        else:
            self.tracer.trace_llm_call("investigate", prompt, None, False, latency_ms, error)
            fallback = get_fallback_investigate()
            fallback.tool_calls_made = self.tool_results
            self.context.update(fallback.model_dump())
        
        self.current_state = AgentState.HYPOTHESIS
    
    async def _execute_hypothesis(self):
        """Execute hypothesis state."""
        prompt = get_hypothesis_prompt(self.context)
        
        start_time = time.time()
        result, success, error = await self.llm.call("hypothesis", prompt, HypothesisOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("hypothesis", prompt, result.model_dump(), True, latency_ms)
            self.context.update(result.model_dump())
        else:
            self.tracer.trace_llm_call("hypothesis", prompt, None, False, latency_ms, error)
            fallback = get_fallback_hypothesis()
            self.context.update(fallback.model_dump())
        
        self.current_state = AgentState.VERIFY
    
    async def _execute_verify(self):
        """Execute verify state."""
        prompt = get_verify_prompt(self.context)
        
        start_time = time.time()
        result, success, error = await self.llm.call("verify", prompt, VerifyOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("verify", prompt, result.model_dump(), True, latency_ms)
            self.context.update(result.model_dump())
        else:
            self.tracer.trace_llm_call("verify", prompt, None, False, latency_ms, error)
            fallback = get_fallback_verify()
            self.context.update(fallback.model_dump())
        
        self.current_state = AgentState.RECOMMEND
    
    async def _execute_recommend(self):
        """Execute recommend state."""
        prompt = get_recommend_prompt(self.context)
        
        start_time = time.time()
        result, success, error = await self.llm.call("recommend", prompt, RecommendOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("recommend", prompt, result.model_dump(), True, latency_ms)
            self.context.update(result.model_dump())
        else:
            self.tracer.trace_llm_call("recommend", prompt, None, False, latency_ms, error)
            fallback = get_fallback_recommend()
            self.context.update(fallback.model_dump())
        
        self.current_state = AgentState.REPORT
    
    async def _execute_report(self):
        """Execute report state - generate final report."""
        # Add metadata
        self.context["tools_used"] = list(set(r.tool_name for r in self.tool_results))
        self.context["investigation_duration_ms"] = int((time.time() - self.start_time) * 1000)
        
        prompt = get_report_prompt(self.context)
        
        start_time = time.time()
        result, success, error = await self.llm.call("report", prompt, ReportOutput)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if success and result:
            self.tracer.trace_llm_call("report", prompt, result.model_dump(), True, latency_ms)
            self.context["report"] = result
        else:
            self.tracer.trace_llm_call("report", prompt, None, False, latency_ms, error)
            fallback = get_fallback_report(
                self.context["service"],
                self.context["alert"]
            )
            fallback.tools_used = self.context.get("tools_used", [])
            fallback.investigation_duration_ms = self.context.get("investigation_duration_ms", 0)
            self.context["report"] = fallback
        
        self.current_state = AgentState.COMPLETE
