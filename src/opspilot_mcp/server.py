"""MCP Server implementation for OpsPilot."""

import argparse
import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .tools.log_search import log_search
from .tools.metric_query import metric_query
from .tools.runbook_lookup import runbook_lookup
from .tools.change_history import change_history
from .tools.ticket_create import ticket_create
from .resources.runbooks import get_runbook_index, get_runbook_content


# Create MCP server instance
server = Server("opspilot-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="log_search",
            description="Search logs for a service. Returns matching log entries with timestamps and levels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name to search logs for"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range (e.g., '30m', '1h', '24h')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of hits to return",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["service", "query", "time_range"]
            }
        ),
        Tool(
            name="metric_query",
            description="Query metrics for a service. Returns time series data with statistics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name to query metrics for"
                    },
                    "metric": {
                        "type": "string",
                        "description": "Metric name (e.g., 'latency', 'error_rate', 'cpu')"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range (e.g., '30m', '1h', '24h')"
                    }
                },
                "required": ["service", "metric", "time_range"]
            }
        ),
        Tool(
            name="runbook_lookup",
            description="Lookup runbooks matching a symptom. Returns relevant runbook excerpts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name"
                    },
                    "symptom": {
                        "type": "string",
                        "description": "Symptom or issue description to search for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of matches to return",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["service", "symptom"]
            }
        ),
        Tool(
            name="change_history",
            description="Get recent change/deployment history for a service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range (e.g., '30m', '1h', '24h')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of changes to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["service", "time_range"]
            }
        ),
        Tool(
            name="ticket_create",
            description="Create an incident ticket with summary, evidence, and recommended steps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Ticket summary/title"
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Evidence collected during investigation"
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommended action steps"
                    }
                },
                "required": ["service", "summary", "evidence", "steps"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "log_search":
            result = log_search(
                service=arguments["service"],
                query=arguments["query"],
                time_range=arguments["time_range"],
                limit=arguments.get("limit", 20)
            )
        elif name == "metric_query":
            result = metric_query(
                service=arguments["service"],
                metric=arguments["metric"],
                time_range=arguments["time_range"]
            )
        elif name == "runbook_lookup":
            result = runbook_lookup(
                service=arguments["service"],
                symptom=arguments["symptom"],
                limit=arguments.get("limit", 3)
            )
        elif name == "change_history":
            result = change_history(
                service=arguments["service"],
                time_range=arguments["time_range"],
                limit=arguments.get("limit", 10)
            )
        elif name == "ticket_create":
            result = ticket_create(
                service=arguments["service"],
                summary=arguments["summary"],
                evidence=arguments["evidence"],
                steps=arguments["steps"]
            )
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="runbooks://index",
            name="Runbook Index",
            description="List of all available runbooks",
            mimeType="application/json"
        )
    ]


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List available resource templates."""
    return [
        ResourceTemplate(
            uriTemplate="runbooks://{name}",
            name="Runbook Content",
            description="Get content of a specific runbook by name"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri == "runbooks://index":
        result = get_runbook_index()
        return json.dumps(result, indent=2)
    elif uri.startswith("runbooks://"):
        name = uri.replace("runbooks://", "")
        result = get_runbook_content(name)
        if result is None:
            return json.dumps({"error": f"Runbook '{name}' not found"})
        return json.dumps(result, indent=2)
    else:
        return json.dumps({"error": f"Unknown resource: {uri}"})


async def main():
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description="OpsPilot MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Use stdio transport")
    parser.add_argument("--host", default="localhost", help="Host for SSE transport")
    parser.add_argument("--port", type=int, default=8080, help="Port for SSE transport")
    
    args = parser.parse_args()
    
    if args.stdio:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    else:
        # SSE mode would go here, but stdio is primary
        print("SSE mode not implemented. Use --stdio", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
