"""Dummy LLM provider for offline testing."""

import json
import re
from typing import Type, Optional, Dict, Any

from pydantic import BaseModel

from .base import BaseLLM


class DummyLLM(BaseLLM):
    """Dummy LLM provider that generates rule-based responses for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    async def raw_call(self, prompt: str, system_prompt: str = "") -> str:
        """Raw LLM call - returns a generic response."""
        return '{"message": "Dummy LLM response"}'
    
    def _generate_intake_response(self, prompt: str) -> dict:
        """Generate intake state response."""
        # Extract service and alert from prompt
        service_match = re.search(r'Service:\s*(.+)', prompt)
        alert_match = re.search(r'Alert:\s*(.+)', prompt)
        time_match = re.search(r'Time Range:\s*(.+)', prompt)
        
        service = service_match.group(1).strip() if service_match else "unknown-service"
        alert = alert_match.group(1).strip() if alert_match else "unknown alert"
        time_range = time_match.group(1).strip() if time_match else "30m"
        
        # Determine severity based on keywords
        severity = "medium"
        if any(kw in alert.lower() for kw in ["critical", "down", "outage", "crash"]):
            severity = "critical"
        elif any(kw in alert.lower() for kw in ["high", "spike", "elevated"]):
            severity = "high"
        elif any(kw in alert.lower() for kw in ["low", "minor", "warning"]):
            severity = "low"
        
        return {
            "service": service,
            "alert": alert,
            "time_range": time_range,
            "initial_assessment": f"Alert received for {service}. Initial analysis indicates potential issues requiring investigation. The alert mentions: {alert[:100]}",
            "needs_clarification": False,
            "severity_estimate": severity
        }
    
    def _generate_clarify_response(self, prompt: str) -> dict:
        """Generate clarify state response."""
        return {
            "questions": [
                "When did users first start reporting this issue?",
                "Were there any recent deployments or configuration changes?",
                "Is this affecting all users or a specific subset?"
            ],
            "context_gathered": "Based on alert context, investigating potential service degradation",
            "ready_to_investigate": True
        }
    
    def _generate_investigate_response(self, prompt: str) -> dict:
        """Generate investigate state response."""
        return {
            "tool_calls_made": [],
            "log_findings": "Found multiple ERROR level log entries indicating connection timeouts and failed requests. Errors started approximately 30 minutes ago.",
            "metric_findings": "Latency metrics show significant increase from baseline 100ms to 500ms+. Error rate elevated to 5% from normal 0.1%.",
            "change_findings": "Recent deployment detected within the investigation time window. Version change may correlate with observed issues.",
            "evidence_summary": "Investigation reveals correlated issues: elevated error rates, increased latency, and recent deployment activity. Log errors indicate connection-related failures that began around the deployment time."
        }
    
    def _generate_hypothesis_response(self, prompt: str) -> dict:
        """Generate hypothesis state response."""
        return {
            "primary_hypothesis": "Service degradation likely caused by recent deployment introducing a regression or misconfiguration affecting downstream connections",
            "confidence": 0.75,
            "supporting_evidence": [
                "Error logs show connection timeout patterns",
                "Latency spike correlates with deployment timestamp",
                "Error rate increase matches deployment window"
            ],
            "alternative_hypotheses": [
                "Downstream dependency experiencing issues",
                "Resource exhaustion under normal load"
            ],
            "requires_verification": True
        }
    
    def _generate_verify_response(self, prompt: str) -> dict:
        """Generate verify state response."""
        return {
            "hypothesis_verified": True,
            "verification_method": "Cross-referenced deployment timeline with error onset, verified configuration changes in deployment",
            "additional_findings": "Deployment included changes to connection pool settings that may have reduced available connections",
            "final_root_cause": "Recent deployment introduced a configuration change that reduced connection pool capacity, causing connection exhaustion under normal load",
            "confidence": 0.85
        }
    
    def _generate_recommend_response(self, prompt: str) -> dict:
        """Generate recommend state response."""
        return {
            "immediate_actions": [
                {"step": "Rollback to previous stable version", "priority": "high", "owner": "oncall"},
                {"step": "Increase connection pool size as temporary mitigation", "priority": "high", "owner": "oncall"},
                {"step": "Monitor error rates after changes", "priority": "medium", "owner": "oncall"}
            ],
            "follow_up_actions": [
                {"step": "Review deployment changes for configuration issues", "priority": "medium", "owner": "dev-team"},
                {"step": "Add connection pool monitoring alerts", "priority": "medium", "owner": "platform-team"}
            ],
            "preventive_measures": [
                "Add connection pool metrics to deployment validation",
                "Implement canary deployment for configuration changes",
                "Add automated rollback triggers for error rate spikes"
            ],
            "runbook_references": [
                "database-connection-issues",
                "deployment-rollback-procedure"
            ]
        }
    
    def _generate_report_response(self, prompt: str) -> dict:
        """Generate report state response."""
        # Extract context from prompt
        service_match = re.search(r'Service:\s*(.+)', prompt)
        alert_match = re.search(r'Alert:\s*(.+)', prompt)
        
        service = service_match.group(1).strip() if service_match else "unknown-service"
        alert = alert_match.group(1).strip()[:200] if alert_match else "Unknown alert"
        
        return {
            "title": f"Incident Report: {service} Service Degradation",
            "service": service,
            "alert_summary": alert,
            "root_cause": "Recent deployment introduced configuration change reducing connection pool capacity, causing connection exhaustion",
            "confidence": 0.85,
            "evidence_chain": [
                {"source": "log_search", "finding": "Connection timeout errors detected starting 30 minutes ago"},
                {"source": "metric_query", "finding": "Latency increased 5x, error rate elevated to 5%"},
                {"source": "change_history", "finding": "Deployment with connection pool configuration change"}
            ],
            "immediate_actions": [
                "Rollback to previous stable version",
                "Increase connection pool size",
                "Monitor error rates"
            ],
            "follow_up_actions": [
                "Review deployment changes",
                "Add connection pool monitoring"
            ],
            "investigation_duration_ms": 5000,
            "tools_used": ["log_search", "metric_query", "change_history"],
            "missing_info": []
        }
    
    def _detect_schema_type(self, prompt: str) -> str:
        """Detect which schema type is expected based on prompt content."""
        prompt_lower = prompt.lower()
        
        if "analyze this production alert" in prompt_lower or "initial assessment" in prompt_lower:
            return "intake"
        elif "clarification questions" in prompt_lower:
            return "clarify"
        elif "analyze the investigation results" in prompt_lower or "tool results:" in prompt_lower:
            return "investigate"
        elif "form a hypothesis" in prompt_lower:
            return "hypothesis"
        elif "verify the hypothesis" in prompt_lower:
            return "verify"
        elif "generate action recommendations" in prompt_lower:
            return "recommend"
        elif "generate a final diagnostic report" in prompt_lower:
            return "report"
        else:
            return "unknown"
    
    async def call(
        self,
        step_name: str,
        prompt: str,
        schema: Type[BaseModel],
        max_retries: int = 2
    ) -> tuple[Optional[BaseModel], bool, str]:
        """Call the dummy LLM and generate appropriate response."""
        self.call_count += 1
        
        try:
            # Detect schema type from step_name or prompt
            schema_type = step_name.lower().replace("_", "")
            
            if "intake" in schema_type:
                response_dict = self._generate_intake_response(prompt)
            elif "clarify" in schema_type:
                response_dict = self._generate_clarify_response(prompt)
            elif "investigate" in schema_type:
                response_dict = self._generate_investigate_response(prompt)
            elif "hypothesis" in schema_type:
                response_dict = self._generate_hypothesis_response(prompt)
            elif "verify" in schema_type:
                response_dict = self._generate_verify_response(prompt)
            elif "recommend" in schema_type:
                response_dict = self._generate_recommend_response(prompt)
            elif "report" in schema_type:
                response_dict = self._generate_report_response(prompt)
            else:
                # Try to detect from prompt content
                detected = self._detect_schema_type(prompt)
                generators = {
                    "intake": self._generate_intake_response,
                    "clarify": self._generate_clarify_response,
                    "investigate": self._generate_investigate_response,
                    "hypothesis": self._generate_hypothesis_response,
                    "verify": self._generate_verify_response,
                    "recommend": self._generate_recommend_response,
                    "report": self._generate_report_response
                }
                generator = generators.get(detected)
                if generator:
                    response_dict = generator(prompt)
                else:
                    return None, False, f"Unknown step type: {step_name}"
            
            # Validate with schema
            result = schema.model_validate(response_dict)
            return result, True, ""
            
        except Exception as e:
            return None, False, f"Dummy LLM error: {str(e)}"
