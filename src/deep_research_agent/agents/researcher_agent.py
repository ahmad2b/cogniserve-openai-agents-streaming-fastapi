"""
Individual Researcher Agent

Conducts focused research on specific topics using ReAct pattern with Tavily MCP server.
Implements the researcher logic from the Deep Research Agent Implementation Guide.
"""

from agents import Agent

from ..models import ResearchContext
from ..tools import assess_research_completeness, synthesize_findings
from ..config import DeepResearchConfig
from ..mcp import get_tavily_mcp_server


def get_researcher_system_prompt(research_topic: str, available_tools: list) -> str:
    """Get system prompt for individual researcher agent following the implementation guide."""
    tool_names = [getattr(tool, 'name', str(tool)) for tool in available_tools]
    
    return f"""
        You are a research assistant conducting deep research on: {research_topic}
        
        Guidelines:
        1. Use available tools to find comprehensive information
        2. Start with broad searches, then narrow down
        3. Call tools iteratively until satisfied with findings
        4. Different topics require different research depth
        5. Stop when additional searches yield diminishing returns
        
        Available tools: {tool_names}
        
        CRITICAL: You must conduct research using tools before completing.
        Call tools until you have comprehensive findings, then stop.
        """


def create_researcher_agent(research_topic: str, max_tool_calls: int = 5) -> Agent[ResearchContext]:
    """Create an individual researcher agent with Tavily MCP server."""
    
    config = DeepResearchConfig.from_environment()

    try:
        tavily_server = get_tavily_mcp_server(config.tavily_api_key)
        mcp_servers = [tavily_server]
    except ValueError:
        # If Tavily API key is not available, continue without MCP server
        mcp_servers = []
    
    # Available tools for the prompt
    available_tools = [assess_research_completeness, synthesize_findings]
    if mcp_servers:
        available_tools.append("tavily_search")  # MCP tools will be auto-discovered
    
    return Agent[ResearchContext](
        name="Individual Researcher",
        instructions=get_researcher_system_prompt(research_topic, available_tools),
        model=config.researcher_model_name,
        tools=[assess_research_completeness, synthesize_findings],
        mcp_servers=mcp_servers,
        mcp_config={"convert_schemas_to_strict": True}
    )


# Default researcher agent instance (will be replaced by topic-specific ones)
researcher_agent = None 