"""Pydantic schemas for Agent FSM states."""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """FSM states for the agent."""
    INTAKE = "intake"
    CLARIFY = "clarify"
    INVESTIGATE = "investigate"
    HYPOTHESIS = "hypothesis"
    VERIFY = "verify"
    RECOMMEND = "recommend"
    REPORT = "report"
    COMPLETE = "complete"
    ERROR = "error"


# ============ State Output Schemas ============

class IntakeOutput(BaseModel):
    """Output from Intake state."""
    service: str = Field(..., description="Service name")
    alert: str = Field(..., description="Alert text")
    time_range: str = Field(..., description="Time range for investigation")
    initial_assessment: str = Field(..., description="Initial assessment of the alert")
    needs_clarification: bool = Field(default=False, description="Whether clarification is needed")
    severity_estimate: str = Field(default="medium", description="Estimated severity")


class ClarifyOutput(BaseModel):
    """Output from Clarify state."""
    questions: List[str] = Field(..., min_length=2, max_length=5, description="Clarification questions")
    context_gathered: str = Field(default="", description="Additional context gathered")
    ready_to_investigate: bool = Field(default=True, description="Whether ready to proceed")


class ToolCall(BaseModel):
    """A tool call to be made."""
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")


class ToolResult(BaseModel):
    """Result from a tool call."""
    tool_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    summary: str = ""


class InvestigateOutput(BaseModel):
    """Output from Investigate state."""
    tool_calls_made: List[ToolResult] = Field(default_factory=list, description="Tools called and results")
    log_findings: str = Field(default="", description="Key findings from logs")
    metric_findings: str = Field(default="", description="Key findings from metrics")
    change_findings: str = Field(default="", description="Key findings from change history")
    evidence_summary: str = Field(..., description="Summary of all evidence collected")


class HypothesisOutput(BaseModel):
    """Output from Hypothesis state."""
    primary_hypothesis: str = Field(..., description="Primary hypothesis for root cause")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level (0-1)")
    supporting_evidence: List[str] = Field(..., description="Evidence supporting hypothesis")
    alternative_hypotheses: List[str] = Field(default_factory=list, description="Alternative hypotheses")
    requires_verification: bool = Field(default=True, description="Whether verification is needed")


class VerifyOutput(BaseModel):
    """Output from Verify state."""
    hypothesis_verified: bool = Field(..., description="Whether primary hypothesis is verified")
    verification_method: str = Field(..., description="How verification was done")
    additional_findings: str = Field(default="", description="Additional findings during verification")
    final_root_cause: str = Field(..., description="Final determined root cause")
    confidence: float = Field(..., ge=0, le=1, description="Final confidence level")


class ActionStep(BaseModel):
    """A recommended action step."""
    step: str = Field(..., description="Action step description")
    priority: str = Field(default="medium", description="Priority: high/medium/low")
    owner: str = Field(default="oncall", description="Suggested owner")


class RecommendOutput(BaseModel):
    """Output from Recommend state."""
    immediate_actions: List[ActionStep] = Field(..., description="Immediate actions to take")
    follow_up_actions: List[ActionStep] = Field(default_factory=list, description="Follow-up actions")
    preventive_measures: List[str] = Field(default_factory=list, description="Preventive measures")
    runbook_references: List[str] = Field(default_factory=list, description="Relevant runbook references")


class EvidenceItem(BaseModel):
    """An evidence item in the report."""
    source: str = Field(..., description="Source of evidence (tool name)")
    finding: str = Field(..., description="The finding")
    timestamp: Optional[str] = None


class ReportOutput(BaseModel):
    """Output from Report state - final diagnostic report."""
    title: str = Field(..., description="Report title")
    service: str = Field(..., description="Service name")
    alert_summary: str = Field(..., description="Summary of the alert")
    
    # Diagnosis
    root_cause: str = Field(..., description="Determined root cause")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    
    # Evidence chain
    evidence_chain: List[EvidenceItem] = Field(..., description="Chain of evidence")
    
    # Actions
    immediate_actions: List[str] = Field(..., description="Immediate actions")
    follow_up_actions: List[str] = Field(default_factory=list, description="Follow-up actions")
    
    # Metadata
    investigation_duration_ms: int = Field(default=0, description="Investigation duration")
    tools_used: List[str] = Field(default_factory=list, description="Tools used")
    missing_info: List[str] = Field(default_factory=list, description="Missing information")


# ============ Fallback Templates ============

def get_fallback_intake(service: str, alert: str, time_range: str) -> IntakeOutput:
    """Generate fallback intake output."""
    return IntakeOutput(
        service=service,
        alert=alert,
        time_range=time_range,
        initial_assessment=f"Received alert for {service}: {alert[:100]}...",
        needs_clarification=True,
        severity_estimate="medium"
    )


def get_fallback_clarify() -> ClarifyOutput:
    """Generate fallback clarify output."""
    return ClarifyOutput(
        questions=[
            "When did this issue first occur?",
            "Are there any recent deployments or configuration changes?",
            "Is this affecting all users or a subset?"
        ],
        context_gathered="",
        ready_to_investigate=True
    )


def get_fallback_investigate() -> InvestigateOutput:
    """Generate fallback investigate output."""
    return InvestigateOutput(
        tool_calls_made=[],
        log_findings="Unable to parse log findings",
        metric_findings="Unable to parse metric findings",
        change_findings="Unable to parse change findings",
        evidence_summary="Investigation completed but output parsing failed"
    )


def get_fallback_hypothesis() -> HypothesisOutput:
    """Generate fallback hypothesis output."""
    return HypothesisOutput(
        primary_hypothesis="Unable to determine hypothesis - manual investigation required",
        confidence=0.0,
        supporting_evidence=["Fallback due to LLM parsing failure"],
        alternative_hypotheses=[],
        requires_verification=True
    )


def get_fallback_verify() -> VerifyOutput:
    """Generate fallback verify output."""
    return VerifyOutput(
        hypothesis_verified=False,
        verification_method="fallback",
        additional_findings="",
        final_root_cause="Unable to determine - manual investigation required",
        confidence=0.0
    )


def get_fallback_recommend() -> RecommendOutput:
    """Generate fallback recommend output."""
    return RecommendOutput(
        immediate_actions=[
            ActionStep(step="Escalate to on-call engineer", priority="high", owner="oncall"),
            ActionStep(step="Check service health dashboard", priority="high", owner="oncall")
        ],
        follow_up_actions=[],
        preventive_measures=[],
        runbook_references=[]
    )


def get_fallback_report(service: str, alert: str) -> ReportOutput:
    """Generate fallback report output."""
    return ReportOutput(
        title=f"Incident Report: {service}",
        service=service,
        alert_summary=alert,
        root_cause="Unable to determine automatically - manual investigation required",
        confidence=0.0,
        evidence_chain=[
            EvidenceItem(source="system", finding="Automated analysis failed - fallback report generated")
        ],
        immediate_actions=["Escalate to on-call engineer for manual investigation"],
        follow_up_actions=["Review agent logs for debugging"],
        investigation_duration_ms=0,
        tools_used=[],
        missing_info=["LLM analysis failed"]
    )
