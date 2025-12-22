"""Data access layer for mock data sources."""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def get_data_dir() -> Path:
    """Get the data directory path."""
    # Try to find data directory relative to package
    current = Path(__file__).parent.parent.parent.parent.parent
    data_dir = current / "data"
    if data_dir.exists():
        return data_dir
    # Fallback to current working directory
    return Path.cwd() / "data"


def get_runbooks_dir() -> Path:
    """Get the runbooks directory path."""
    current = Path(__file__).parent.parent.parent.parent.parent
    runbooks_dir = current / "runbooks"
    if runbooks_dir.exists():
        return runbooks_dir
    return Path.cwd() / "runbooks"


def get_artifacts_dir() -> Path:
    """Get the artifacts directory path."""
    current = Path(__file__).parent.parent.parent.parent.parent
    artifacts_dir = current / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    return artifacts_dir


def parse_time_range(time_range: str) -> timedelta:
    """Parse time range string to timedelta."""
    match = re.match(r"(\d+)([mhd])", time_range.lower())
    if not match:
        return timedelta(hours=1)  # Default
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return timedelta(hours=1)


class LogDataAccess:
    """Access layer for log data."""

    def __init__(self):
        self.logs_dir = get_data_dir() / "logs"

    def search(
        self, service: str, query: str, time_range: str, limit: int = 20
    ) -> Dict[str, Any]:
        """Search logs for a service."""
        log_file = self.logs_dir / f"{service}.log"
        if not log_file.exists():
            return {"hits": [], "summary": f"No logs found for service {service}", "total_matched": 0}

        hits = []
        query_lower = query.lower()
        
        with open(log_file, "r") as f:
            for i, line in enumerate(f, 1):
                if query_lower in line.lower():
                    # Parse log line (format: TIMESTAMP LEVEL MESSAGE)
                    parts = line.strip().split(" ", 2)
                    if len(parts) >= 3:
                        hits.append({
                            "timestamp": parts[0],
                            "level": parts[1],
                            "message": parts[2] if len(parts) > 2 else "",
                            "line_number": i
                        })
                    if len(hits) >= limit:
                        break

        total = len(hits)
        summary = f"Found {total} log entries matching '{query}' for service {service}"
        if total > 0:
            error_count = sum(1 for h in hits if h.get("level", "").upper() == "ERROR")
            warn_count = sum(1 for h in hits if h.get("level", "").upper() == "WARN")
            summary += f" ({error_count} errors, {warn_count} warnings)"

        return {"hits": hits, "summary": summary, "total_matched": total}


class MetricDataAccess:
    """Access layer for metric data."""

    def __init__(self):
        self.metrics_dir = get_data_dir() / "metrics"

    def query(self, service: str, metric: str, time_range: str) -> Dict[str, Any]:
        """Query metrics for a service."""
        metric_file = self.metrics_dir / f"{service}.json"
        if not metric_file.exists():
            return {
                "series": [],
                "stats": {"min": 0, "max": 0, "avg": 0, "latest": 0},
                "summary": f"No metrics found for service {service}"
            }

        with open(metric_file, "r") as f:
            data = json.load(f)

        if metric not in data:
            available = list(data.keys())
            return {
                "series": [],
                "stats": {"min": 0, "max": 0, "avg": 0, "latest": 0},
                "summary": f"Metric '{metric}' not found. Available: {available}"
            }

        series = data[metric]
        values = [p["value"] for p in series]
        
        stats = {
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "avg": sum(values) / len(values) if values else 0,
            "latest": values[-1] if values else 0
        }

        # Generate summary based on metric type
        if metric == "error_rate":
            if stats["latest"] > 5:
                summary = f"High error rate detected: {stats['latest']:.2f}% (avg: {stats['avg']:.2f}%)"
            else:
                summary = f"Error rate normal: {stats['latest']:.2f}% (avg: {stats['avg']:.2f}%)"
        elif metric == "latency":
            if stats["latest"] > 500:
                summary = f"High latency: {stats['latest']:.0f}ms (avg: {stats['avg']:.0f}ms)"
            else:
                summary = f"Latency normal: {stats['latest']:.0f}ms (avg: {stats['avg']:.0f}ms)"
        elif metric == "cpu":
            if stats["latest"] > 80:
                summary = f"High CPU usage: {stats['latest']:.1f}% (avg: {stats['avg']:.1f}%)"
            else:
                summary = f"CPU usage normal: {stats['latest']:.1f}% (avg: {stats['avg']:.1f}%)"
        else:
            summary = f"Metric {metric}: latest={stats['latest']}, avg={stats['avg']:.2f}"

        return {"series": series, "stats": stats, "summary": summary}


class ChangeDataAccess:
    """Access layer for change history data."""

    def __init__(self):
        self.changes_dir = get_data_dir() / "changes"

    def get_history(self, service: str, time_range: str, limit: int = 10) -> Dict[str, Any]:
        """Get change history for a service."""
        change_file = self.changes_dir / f"{service}.json"
        if not change_file.exists():
            return {"changes": [], "summary": f"No change history found for service {service}"}

        with open(change_file, "r") as f:
            data = json.load(f)

        changes = data.get("changes", [])[:limit]
        
        if not changes:
            summary = f"No recent changes for service {service}"
        else:
            summary = f"Found {len(changes)} recent changes for {service}. "
            summary += f"Latest: {changes[0].get('summary', 'Unknown')} at {changes[0].get('timestamp', 'Unknown')}"

        return {"changes": changes, "summary": summary}


class RunbookDataAccess:
    """Access layer for runbook data."""

    def __init__(self):
        self.runbooks_dir = get_runbooks_dir()

    def get_index(self) -> Dict[str, Any]:
        """Get index of all runbooks."""
        runbooks = []
        if not self.runbooks_dir.exists():
            return {"runbooks": [], "total": 0}

        for md_file in self.runbooks_dir.glob("*.md"):
            content = md_file.read_text()
            # Extract title from first heading
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else md_file.stem
            
            # Extract tags from content (look for keywords)
            tags = []
            for tag in ["database", "api", "latency", "error", "memory", "cpu", "timeout", "connection"]:
                if tag in content.lower():
                    tags.append(tag)

            runbooks.append({
                "name": md_file.stem,
                "title": title,
                "path": str(md_file),
                "tags": tags
            })

        return {"runbooks": runbooks, "total": len(runbooks)}

    def get_content(self, name: str) -> Optional[Dict[str, Any]]:
        """Get content of a specific runbook."""
        runbook_file = self.runbooks_dir / f"{name}.md"
        if not runbook_file.exists():
            # Try without .md extension
            runbook_file = self.runbooks_dir / name
            if not runbook_file.exists():
                return None

        content = runbook_file.read_text()
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else name

        return {
            "name": name,
            "title": title,
            "content": content,
            "path": str(runbook_file)
        }

    def lookup(self, service: str, symptom: str, limit: int = 3) -> Dict[str, Any]:
        """Lookup runbooks matching a symptom."""
        matches = []
        symptom_lower = symptom.lower()
        service_lower = service.lower()

        if not self.runbooks_dir.exists():
            return {"matches": [], "summary": "No runbooks available"}

        for md_file in self.runbooks_dir.glob("*.md"):
            content = md_file.read_text()
            content_lower = content.lower()
            
            # Calculate relevance score
            score = 0
            if symptom_lower in content_lower:
                score += 5
            if service_lower in content_lower:
                score += 3
            
            # Check for keyword matches
            symptom_words = symptom_lower.split()
            for word in symptom_words:
                if len(word) > 3 and word in content_lower:
                    score += 1

            if score > 0:
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                title = title_match.group(1) if title_match else md_file.stem
                
                # Extract excerpt
                excerpt_start = content_lower.find(symptom_words[0]) if symptom_words else 0
                excerpt_start = max(0, excerpt_start - 50)
                excerpt = content[excerpt_start:excerpt_start + 200].strip()
                if excerpt_start > 0:
                    excerpt = "..." + excerpt
                if len(content) > excerpt_start + 200:
                    excerpt = excerpt + "..."

                matches.append({
                    "title": title,
                    "excerpt": excerpt,
                    "path": str(md_file),
                    "relevance_score": score
                })

        # Sort by relevance and limit
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        matches = matches[:limit]

        if matches:
            summary = f"Found {len(matches)} relevant runbooks for '{symptom}'"
        else:
            summary = f"No runbooks found matching '{symptom}'"

        return {"matches": matches, "summary": summary}


class TicketDataAccess:
    """Access layer for ticket creation."""

    def __init__(self):
        self.artifacts_dir = get_artifacts_dir()

    def create(
        self, service: str, summary: str, evidence: str, steps: List[str]
    ) -> Dict[str, Any]:
        """Create a new ticket."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ticket_id = f"TKT-{timestamp}"
        ticket_path = self.artifacts_dir / f"ticket_{ticket_id}.md"

        content = f"""# Incident Ticket: {ticket_id}

## Service
{service}

## Summary
{summary}

## Evidence
{evidence}

## Recommended Actions
"""
        for i, step in enumerate(steps, 1):
            content += f"{i}. {step}\n"

        content += f"\n---\nCreated: {datetime.now().isoformat()}\n"

        ticket_path.write_text(content)

        return {
            "ticket_path": str(ticket_path),
            "id": ticket_id,
            "created_at": datetime.now().isoformat()
        }
