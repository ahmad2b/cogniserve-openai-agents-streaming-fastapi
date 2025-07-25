"""
Deep Research Agent MCP Server

MCP Server for the Deep Research Agent.
"""

import os
from agents.mcp import MCPServerSse
from typing import Optional

# ============================================================================
# Tavily MCP Server
# ============================================================================

def get_tavily_mcp_server(tavily_api_key: Optional[str] = None):
    """
    Returns a configured MCPServerSse instance for Tavily.
    
    Args:
        tavily_api_key: The Tavily API key. If None, it will attempt to read from environment variable.
    """
    if not tavily_api_key:
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable or argument is required")
            
    return MCPServerSse(
        params={
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}",
            "timeout": 30.0,
            "sse_read_timeout": 300.0
        },
        cache_tools_list=True,
        name="tavily-search"
    )