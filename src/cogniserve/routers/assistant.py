"""
General Assistant Agent Router

This demonstrates how to create a dedicated router for a specific agent
using the standardized agent router pattern.
"""

from agents import Agent

from ..utils.agent_router import create_agent_router

# Create the agent
assistant_agent = Agent(
    name="General Assistant",
    instructions="""You are a helpful AI assistant. 
    
    Your role is to:
    - Answer questions clearly and concisely
    - Provide helpful information on a wide range of topics
    - Be friendly and professional
    - If you're unsure about something, say so honestly
    
    Keep your responses focused and useful."""
)

# Create the router with standardized endpoints
router = create_agent_router(
    agent=assistant_agent,
    prefix="/assistant",
    agent_name="General Assistant"
)

# The router now automatically has these endpoints:
# POST /assistant/run - Synchronous execution
# POST /assistant/stream - Real-time streaming
# GET /assistant/info - Agent information 