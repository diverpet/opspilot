"""Tracer for observability - records all LLM and MCP tool calls."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict


@dataclass
class TraceEvent:
    """A single trace event."""
    ts: str
    event_type: str  # "llm" | "mcp_tool" | "state"
    name: str  # step name or tool name
    input: str  # input summary
    output_summary: str
    ok: bool
    latency_ms: int
    error: Optional[str] = None


class Tracer:
    """Tracer for recording agent events."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.events: List[TraceEvent] = []
        self.start_time = time.time()
        
        if output_dir is None:
            # Default to artifacts directory
            current = Path(__file__).parent.parent.parent.parent
            output_dir = current / "artifacts"
        
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trace_file = self.output_dir / f"trace_{self.session_id}.jsonl"
    
    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now().isoformat()
    
    def _summarize(self, data: Any, max_length: int = 200) -> str:
        """Create a summary of data for logging."""
        if data is None:
            return ""
        if isinstance(data, str):
            text = data
        elif hasattr(data, 'model_dump'):
            # Handle Pydantic models
            text = json.dumps(data.model_dump())
        elif isinstance(data, dict):
            # Convert any pydantic models in the dict
            serializable = self._make_serializable(data)
            text = json.dumps(serializable)
        elif isinstance(data, list):
            serializable = self._make_serializable(data)
            text = json.dumps(serializable)
        else:
            text = str(data)
        
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def _make_serializable(self, obj: Any) -> Any:
        """Recursively convert objects to JSON-serializable form."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        # Fallback to string representation
        return str(obj)
    
    def trace_llm_call(
        self,
        step_name: str,
        prompt: str,
        response: Any,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None
    ):
        """Record an LLM call event."""
        event = TraceEvent(
            ts=self._get_timestamp(),
            event_type="llm",
            name=step_name,
            input=self._summarize(prompt),
            output_summary=self._summarize(response),
            ok=success,
            latency_ms=latency_ms,
            error=error
        )
        self.events.append(event)
        self._write_event(event)
    
    def trace_mcp_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None
    ):
        """Record an MCP tool call event."""
        event = TraceEvent(
            ts=self._get_timestamp(),
            event_type="mcp_tool",
            name=tool_name,
            input=self._summarize(arguments),
            output_summary=self._summarize(result),
            ok=success,
            latency_ms=latency_ms,
            error=error
        )
        self.events.append(event)
        self._write_event(event)
    
    def trace_state_transition(
        self,
        from_state: str,
        to_state: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record a state transition event."""
        event = TraceEvent(
            ts=self._get_timestamp(),
            event_type="state",
            name=f"{from_state} -> {to_state}",
            input=self._summarize(context),
            output_summary="",
            ok=True,
            latency_ms=0
        )
        self.events.append(event)
        self._write_event(event)
    
    def _write_event(self, event: TraceEvent):
        """Write event to trace file."""
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the trace."""
        llm_calls = [e for e in self.events if e.event_type == "llm"]
        tool_calls = [e for e in self.events if e.event_type == "mcp_tool"]
        state_transitions = [e for e in self.events if e.event_type == "state"]
        
        return {
            "total_events": len(self.events),
            "llm_calls": len(llm_calls),
            "llm_success_rate": sum(1 for e in llm_calls if e.ok) / len(llm_calls) if llm_calls else 0,
            "tool_calls": len(tool_calls),
            "tool_success_rate": sum(1 for e in tool_calls if e.ok) / len(tool_calls) if tool_calls else 0,
            "state_transitions": len(state_transitions),
            "total_llm_latency_ms": sum(e.latency_ms for e in llm_calls),
            "total_tool_latency_ms": sum(e.latency_ms for e in tool_calls),
            "trace_file": str(self.trace_file)
        }
    
    def get_trace_file(self) -> Path:
        """Get the trace file path."""
        return self.trace_file
    
    def get_session_id(self) -> str:
        """Get the session ID."""
        return self.session_id
