"""MCP Client wrapper for connecting to MCP servers."""

import asyncio
import json
import subprocess
import time
from typing import Dict, Any, List, Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from ..observability.tracer import Tracer


class MCPClientContext:
    """Context manager wrapper for MCP client connections."""
    
    def __init__(self, command: str, tracer: Optional[Tracer] = None):
        self.command = command
        self.tracer = tracer
        self.session: Optional[ClientSession] = None
        self._stack = None
    
    async def __aenter__(self):
        """Enter the async context."""
        from contextlib import AsyncExitStack
        
        parts = self.command.split()
        server_params = StdioServerParameters(
            command=parts[0],
            args=parts[1:] if len(parts) > 1 else []
        )
        
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        
        read_stream, write_stream = await self._stack.enter_async_context(
            stdio_client(server_params)
        )
        
        self.session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        
        await self.session.initialize()
        return MCPClient(self.session, self.tracer)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context."""
        if self._stack:
            await self._stack.__aexit__(exc_type, exc_val, exc_tb)
        return False


class MCPClient:
    """Client for interacting with MCP servers."""
    
    def __init__(self, session: ClientSession, tracer: Optional[Tracer] = None):
        """Initialize MCP client with an existing session.
        
        Args:
            session: Active MCP client session
            tracer: Optional tracer for observability
        """
        self.session = session
        self.tracer = tracer
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._resources_cache: Optional[List[Dict[str, Any]]] = None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server."""
        if self._tools_cache is not None:
            return self._tools_cache
        
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.session.list_tools()
        self._tools_cache = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in result.tools
        ]
        return self._tools_cache
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server with retry support.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            max_retries: Maximum retry attempts on failure
            
        Returns:
            Tool result as dictionary
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            start_time = time.time()
            try:
                result = await self.session.call_tool(tool_name, arguments)
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Extract text content
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        parsed_result = json.loads(content.text)
                        
                        if self.tracer:
                            self.tracer.trace_mcp_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                result=parsed_result,
                                success=True,
                                latency_ms=latency_ms
                            )
                        
                        return parsed_result
                
                # Empty result
                if self.tracer:
                    self.tracer.trace_mcp_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                        result={},
                        success=True,
                        latency_ms=latency_ms
                    )
                return {}
                
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                last_error = str(e)
                
                if self.tracer:
                    self.tracer.trace_mcp_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=None,
                        success=False,
                        latency_ms=latency_ms,
                        error=last_error
                    )
                
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        # All retries failed - return degraded response
        return {
            "error": last_error,
            "degraded": True,
            "summary": f"Tool {tool_name} failed after {max_retries + 1} attempts"
        }
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from the MCP server."""
        if self._resources_cache is not None:
            return self._resources_cache
        
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.session.list_resources()
        self._resources_cache = [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description
            }
            for resource in result.resources
        ]
        return self._resources_cache
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server.
        
        Args:
            uri: Resource URI (e.g., "runbooks://index")
            
        Returns:
            Resource content as dictionary
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        start_time = time.time()
        try:
            result = await self.session.read_resource(uri)
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result.contents and len(result.contents) > 0:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    parsed = json.loads(content.text)
                    
                    if self.tracer:
                        self.tracer.trace_mcp_tool_call(
                            tool_name=f"resource:{uri}",
                            arguments={"uri": uri},
                            result=parsed,
                            success=True,
                            latency_ms=latency_ms
                        )
                    
                    return parsed
            
            return {}
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            if self.tracer:
                self.tracer.trace_mcp_tool_call(
                    tool_name=f"resource:{uri}",
                    arguments={"uri": uri},
                    result=None,
                    success=False,
                    latency_ms=latency_ms,
                    error=str(e)
                )
            
            return {"error": str(e)}
