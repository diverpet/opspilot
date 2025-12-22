"""Prompt templates for the agent."""

from typing import Dict, Any


SYSTEM_PROMPT = """You are OpsPilot, an expert production incident troubleshooting agent.
You analyze alerts, investigate using available tools, and produce structured diagnostic reports.

You MUST output valid JSON that matches the expected schema for each step.
Be precise, evidence-based, and actionable in your analysis."""


def get_intake_prompt(service: str, alert: str, time_range: str) -> str:
    """Generate prompt for intake state."""
    return f"""Analyze this production alert and provide initial assessment.

Service: {service}
Alert: {alert}
Time Range: {time_range}

Respond with a JSON object containing:
- service: the service name
- alert: the alert text
- time_range: the time range
- initial_assessment: your initial assessment (2-3 sentences)
- needs_clarification: boolean, true if you need more information
- severity_estimate: "low", "medium", "high", or "critical"

Example:
{{"service": "api-gateway", "alert": "High latency detected", "time_range": "30m", "initial_assessment": "Service experiencing latency issues that may indicate downstream problems or resource constraints.", "needs_clarification": false, "severity_estimate": "high"}}"""


def get_clarify_prompt(context: Dict[str, Any]) -> str:
    """Generate prompt for clarify state."""
    return f"""Based on the initial assessment, generate clarification questions if needed.

Context:
- Service: {context.get('service', 'unknown')}
- Alert: {context.get('alert', 'unknown')}
- Initial Assessment: {context.get('initial_assessment', '')}

Generate 2-5 clarification questions to better understand the incident.

Respond with a JSON object containing:
- questions: array of 2-5 question strings
- context_gathered: any additional context you've gathered (string)
- ready_to_investigate: boolean, whether you have enough info to proceed

Example:
{{"questions": ["When did users first report this issue?", "Were there any recent deployments?"], "context_gathered": "", "ready_to_investigate": true}}"""


def get_investigate_prompt(context: Dict[str, Any], tool_results: list) -> str:
    """Generate prompt for investigate state."""
    results_text = "\n".join([
        f"Tool: {r.get('tool_name', 'unknown')}\nResult: {r.get('summary', r.get('result', 'No result'))}"
        for r in tool_results
    ])
    
    return f"""Analyze the investigation results and summarize findings.

Context:
- Service: {context.get('service', 'unknown')}
- Alert: {context.get('alert', 'unknown')}

Tool Results:
{results_text}

Respond with a JSON object containing:
- tool_calls_made: array of tool results (already provided)
- log_findings: string summarizing key findings from logs
- metric_findings: string summarizing key findings from metrics
- change_findings: string summarizing key findings from changes
- evidence_summary: comprehensive summary of all evidence

Example:
{{"tool_calls_made": [], "log_findings": "Found 15 ERROR entries related to database timeouts", "metric_findings": "Latency spiked to 2000ms, error rate at 8%", "change_findings": "Deployment v2.3.1 occurred 45 minutes ago", "evidence_summary": "Evidence suggests database connection issues following recent deployment"}}"""


def get_hypothesis_prompt(context: Dict[str, Any]) -> str:
    """Generate prompt for hypothesis state."""
    return f"""Based on the evidence, form a hypothesis about the root cause.

Evidence Summary: {context.get('evidence_summary', '')}
Log Findings: {context.get('log_findings', '')}
Metric Findings: {context.get('metric_findings', '')}
Change Findings: {context.get('change_findings', '')}

Respond with a JSON object containing:
- primary_hypothesis: your main hypothesis for root cause
- confidence: number 0-1 indicating confidence level
- supporting_evidence: array of evidence points supporting hypothesis
- alternative_hypotheses: array of alternative possible causes
- requires_verification: boolean

Example:
{{"primary_hypothesis": "Database connection pool exhaustion due to increased load after deployment", "confidence": 0.75, "supporting_evidence": ["Connection timeout errors in logs", "Latency spike correlates with deployment"], "alternative_hypotheses": ["Database server resource exhaustion"], "requires_verification": true}}"""


def get_verify_prompt(context: Dict[str, Any]) -> str:
    """Generate prompt for verify state."""
    return f"""Verify the hypothesis against available evidence.

Primary Hypothesis: {context.get('primary_hypothesis', '')}
Supporting Evidence: {context.get('supporting_evidence', [])}
Evidence Summary: {context.get('evidence_summary', '')}

Respond with a JSON object containing:
- hypothesis_verified: boolean
- verification_method: how you verified (string)
- additional_findings: any additional findings (string)
- final_root_cause: the determined root cause
- confidence: final confidence level 0-1

Example:
{{"hypothesis_verified": true, "verification_method": "Cross-referenced logs with metrics timeline", "additional_findings": "Connection pool size unchanged despite 2x traffic increase", "final_root_cause": "Database connection pool exhaustion due to traffic surge post-deployment", "confidence": 0.85}}"""


def get_recommend_prompt(context: Dict[str, Any]) -> str:
    """Generate prompt for recommend state."""
    return f"""Generate action recommendations based on the diagnosis.

Root Cause: {context.get('final_root_cause', '')}
Service: {context.get('service', '')}

Respond with a JSON object containing:
- immediate_actions: array of {{step, priority, owner}} objects for immediate actions
- follow_up_actions: array of {{step, priority, owner}} objects for follow-up
- preventive_measures: array of strings for prevention
- runbook_references: array of relevant runbook names

Example:
{{"immediate_actions": [{{"step": "Increase connection pool size", "priority": "high", "owner": "oncall"}}], "follow_up_actions": [{{"step": "Review auto-scaling configuration", "priority": "medium", "owner": "platform-team"}}], "preventive_measures": ["Add connection pool monitoring alerts"], "runbook_references": ["database-connection-issues"]}}"""


def get_report_prompt(context: Dict[str, Any]) -> str:
    """Generate prompt for report state."""
    return f"""Generate a final diagnostic report.

Service: {context.get('service', '')}
Alert: {context.get('alert', '')}
Root Cause: {context.get('final_root_cause', '')}
Confidence: {context.get('confidence', 0)}
Evidence Summary: {context.get('evidence_summary', '')}
Immediate Actions: {context.get('immediate_actions', [])}
Tools Used: {context.get('tools_used', [])}

Respond with a JSON object containing:
- title: report title
- service: service name
- alert_summary: summary of the alert
- root_cause: determined root cause
- confidence: confidence level 0-1
- evidence_chain: array of {{source, finding}} objects
- immediate_actions: array of action strings
- follow_up_actions: array of follow-up strings
- investigation_duration_ms: duration in milliseconds
- tools_used: array of tool names used
- missing_info: array of missing information

Example:
{{"title": "Incident Report: API Gateway High Latency", "service": "api-gateway", "alert_summary": "High latency affecting user requests", "root_cause": "Database connection pool exhaustion", "confidence": 0.85, "evidence_chain": [{{"source": "log_search", "finding": "Connection timeout errors"}}], "immediate_actions": ["Increase pool size"], "follow_up_actions": ["Review scaling"], "investigation_duration_ms": 5000, "tools_used": ["log_search", "metric_query"], "missing_info": []}}"""
