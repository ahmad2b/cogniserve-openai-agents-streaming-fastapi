"""
Simple chat agent with automatic session memory support.

Session memory is automatically enabled when:
- ENABLE_SESSIONS=true in environment variables
- session_id is provided in API requests

No additional configuration or code changes needed!
"""

from pydantic import BaseModel

import uuid

from agents import Agent, ItemHelpers, MessageOutputItem, RunContextWrapper, ToolCallItem, ToolCallOutputItem, TResponseInputItem, function_tool, handoff, trace, SQLiteSession
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


chat_agent = Agent(
    name="chat_agent",
    # handoff_description="A agent that can delegate the user request to appropriate agents",
    instructions=(
        # f"{RECOMMENDED_PROMPT_PREFIX}"
        "An agent that can chat with the user and answer questions. You maintain conversation context when session memory is enabled."
    ),
    tools=[],
    handoffs=[],
    model="gpt-4.1-mini"
)