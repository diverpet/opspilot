"""Pydantic schemas for MCP Server tools and resources."""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


# ============ Tool Input Schemas ============

class LogSearchInput(BaseModel):
    """Input schema for log_search tool."""
    service: str = Field(..., description="Service name to search logs for")
    query: str = Field(..., description="Search query string")
    time_range: str = Field(..., description="Time range (e.g., '30m', '1h', '24h')")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of hits to return")


class MetricQueryInput(BaseModel):
    """Input schema for metric_query tool."""
    service: str = Field(..., description="Service name to query metrics for")
    metric: str = Field(..., description="Metric name (e.g., 'latency', 'error_rate', 'cpu')")
    time_range: str = Field(..., description="Time range (e.g., '30m', '1h', '24h')")


class RunbookLookupInput(BaseModel):
    """Input schema for runbook_lookup tool."""
    service: str = Field(..., description="Service name")
    symptom: str = Field(..., description="Symptom or issue description to search for")
    limit: int = Field(default=3, ge=1, le=10, description="Maximum number of matches to return")


class ChangeHistoryInput(BaseModel):
    """Input schema for change_history tool."""
    service: str = Field(..., description="Service name")
    time_range: str = Field(..., description="Time range (e.g., '30m', '1h', '24h')")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of changes to return")


class TicketCreateInput(BaseModel):
    """Input schema for ticket_create tool."""
    service: str = Field(..., description="Service name")
    summary: str = Field(..., description="Ticket summary/title")
    evidence: str = Field(..., description="Evidence collected during investigation")
    steps: List[str] = Field(..., description="Recommended action steps")


# ============ Tool Output Schemas ============

class LogHit(BaseModel):
    """A single log entry hit."""
    timestamp: str
    level: str
    message: str
    line_number: int


class LogSearchOutput(BaseModel):
    """Output schema for log_search tool."""
    hits: List[LogHit]
    summary: str
    total_matched: int


class MetricDataPoint(BaseModel):
    """A single metric data point."""
    timestamp: str
    value: float


class MetricStats(BaseModel):
    """Statistics for a metric series."""
    min: float
    max: float
    avg: float
    latest: float


class MetricQueryOutput(BaseModel):
    """Output schema for metric_query tool."""
    series: List[MetricDataPoint]
    stats: MetricStats
    summary: str


class RunbookMatch(BaseModel):
    """A matching runbook entry."""
    title: str
    excerpt: str
    path: str
    relevance_score: float


class RunbookLookupOutput(BaseModel):
    """Output schema for runbook_lookup tool."""
    matches: List[RunbookMatch]
    summary: str


class ChangeRecord(BaseModel):
    """A single change record."""
    deploy_id: str
    timestamp: str
    version: str
    summary: str
    author: str


class ChangeHistoryOutput(BaseModel):
    """Output schema for change_history tool."""
    changes: List[ChangeRecord]
    summary: str


class TicketCreateOutput(BaseModel):
    """Output schema for ticket_create tool."""
    ticket_path: str
    id: str
    created_at: str


# ============ Resource Schemas ============

class RunbookIndexEntry(BaseModel):
    """An entry in the runbook index."""
    name: str
    title: str
    path: str
    tags: List[str]


class RunbookIndex(BaseModel):
    """Runbook index resource output."""
    runbooks: List[RunbookIndexEntry]
    total: int


class RunbookContent(BaseModel):
    """Runbook content resource output."""
    name: str
    title: str
    content: str
    path: str
