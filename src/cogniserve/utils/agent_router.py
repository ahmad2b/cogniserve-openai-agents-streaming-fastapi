import json
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import from OpenAI Agents SDK
from agents import Agent, Runner
from agents.stream_events import (
    AgentUpdatedStreamEvent, 
    RawResponsesStreamEvent, 
    RunItemStreamEvent,
    StreamEvent
)
from agents.items import ItemHelpers
from agents.run_context import RunContextWrapper
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent

from .logging import get_logger

logger = get_logger(__name__)


class AgentRequest(BaseModel):
    """Standard request model for agent interactions."""
    message: str
    max_turns: int = 10
    context: Optional[dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Standard response model for agent interactions."""
    final_output: Any
    success: bool = True
    error: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    response_id: Optional[str] = None


class AgentInfo(BaseModel):
    """Agent information response model."""
    name: str
    agent_name: str
    instructions: Optional[str] = None
    model: Optional[str] = None
    tools_count: int = 0
    handoffs_count: int = 0
    endpoints: dict[str, str]


def create_agent_router(agent: Agent, prefix: str, agent_name: str) -> APIRouter:
    """
    Create a standardized router for an agent with run and run_streamed endpoints.
    
    Args:
        agent: The OpenAI Agent instance
        prefix: URL prefix for the router (e.g., "/research")
        agent_name: Human-readable name for the agent
    
    Returns:
        APIRouter with standardized endpoints
    """
    router = APIRouter(prefix=prefix, tags=[agent_name])
    
    @router.post("/run", response_model=AgentResponse)
    async def run_agent(request: AgentRequest):
        """
        Run the agent and return the final result.
        
        This is a standard synchronous endpoint that returns the complete response.
        """
        try:
            logger.info(f"Running {agent_name} with message: {request.message[:100]}...")
            
            # Create context wrapper if context is provided
            context_wrapper = None
            if request.context:
                context_wrapper = RunContextWrapper(context=request.context)
            
            # Run the agent synchronously
            result = await Runner.run(
                starting_agent=agent,
                input=request.message,
                max_turns=request.max_turns,
                context=request.context
            )
            
            logger.info(f"{agent_name} completed successfully")
            
            # Extract usage information
            usage_info = _extract_usage_info(result)
            
            # Get response ID from the last response if available
            response_id = _extract_response_id(result)
            
            return AgentResponse(
                final_output=result.final_output,
                success=True,
                usage=usage_info,
                response_id=response_id
            )
            
        except Exception as e:
            logger.error(f"Error running {agent_name}: {e}")
            return AgentResponse(
                final_output=None,
                success=False,
                error=str(e)
            )

    @router.post("/stream")
    async def stream_agent(request: AgentRequest):
        """
        Stream agent responses with properly formatted events for frontend consumption.
        
        Events are formatted consistently and avoid double JSON encoding.
        """
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                stream_result = Runner.run_streamed(
                    starting_agent=agent,
                    input=request.message,
                    max_turns=request.max_turns,
                    context=request.context,
                )
                
                async for event in stream_result.stream_events():
                    # Process each event type with proper serialization
                    formatted_event = _format_stream_event(event)
                    if formatted_event:
                        yield f"data: {json.dumps(formatted_event)}\n\n"
                
                # Send completion event
                completion_event = {
                    "type": "stream_complete",
                    "final_output": stream_result.final_output,
                    "current_turn": stream_result.current_turn,
                    "usage": _extract_usage_info(stream_result) if hasattr(stream_result, 'usage') else None
                }
                yield f"data: {json.dumps(completion_event)}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                error_event = {
                    "type": "error", 
                    "message": str(e),
                    "timestamp": str(logger.info.__self__.makeRecord("", 0, "", 0, "", (), None).created)
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )

    @router.get("/info", response_model=AgentInfo)
    async def get_agent_info():
        """Get comprehensive information about this agent."""
        try:
            # Get system prompt if it's a string
            instructions = None
            if isinstance(agent.instructions, str):
                instructions = agent.instructions
            elif agent.instructions is None:
                instructions = None
            else:
                instructions = "Dynamic instructions (function-based)"
            
            # Get model information
            model_info = None
            if agent.model:
                if isinstance(agent.model, str):
                    model_info = agent.model
                else:
                    model_info = str(agent.model)
            
            # Count tools and handoffs
            tools_count = len(agent.tools)
            handoffs_count = len(agent.handoffs)
            
            return AgentInfo(
                name=agent_name,
                agent_name=agent.name,
                instructions=instructions,
                model=model_info,
                tools_count=tools_count,
                handoffs_count=handoffs_count,
                endpoints={
                    "run": f"{prefix}/run",
                    "stream": f"{prefix}/stream",
                    "info": f"{prefix}/info"
                }
            )
        except Exception as e:
            logger.error(f"Error getting {agent_name} info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


def _format_stream_event(event: StreamEvent) -> Optional[dict[str, Any]]:
    """
    Format stream events into a consistent, frontend-friendly structure.
    
    This avoids double JSON encoding and provides clean event structures.
    """
    try:
        if isinstance(event, RawResponsesStreamEvent):
            return _format_raw_response_event(event)
        elif isinstance(event, RunItemStreamEvent):
            return _format_run_item_event(event)
        elif isinstance(event, AgentUpdatedStreamEvent):
            return _format_agent_updated_event(event)
        else:
            # Fallback for unknown event types
            logger.warning(f"Unknown event type: {type(event)}")
            return {
                "type": "unknown_event",
                "event_class": str(type(event).__name__),
                "data": str(event) if event else None
            }
    except Exception as e:
        logger.error(f"Error formatting event {type(event)}: {e}")
        return None


def _format_raw_response_event(event: RawResponsesStreamEvent) -> dict[str, Any]:
    """Format raw response events with proper JSON structure."""
    base_event = {
        "type": "raw_response",
        "event_type": event.data.type if hasattr(event.data, 'type') else 'unknown',
        "sequence_number": getattr(event.data, 'sequence_number', None),
    }
    
    # Handle specific raw event types
    if hasattr(event.data, 'type'):
        event_type = event.data.type
        
        # Text streaming events
        if event_type == "response.output_text.delta":
            base_event.update({
                "delta": getattr(event.data, 'delta', ''),
                "content_index": getattr(event.data, 'content_index', 0),
                "item_id": getattr(event.data, 'item_id', None),
                "output_index": getattr(event.data, 'output_index', 0)
            })
        
        # Reasoning events (for models like deepseek-reasoner)
        elif event_type == "response.reasoning_summary_text.delta":
            base_event.update({
                "delta": getattr(event.data, 'delta', ''),
                "reasoning": True
            })
        
        # Refusal events
        elif event_type == "response.refusal.delta":
            base_event.update({
                "delta": getattr(event.data, 'delta', ''),
                "refusal": True
            })
        
        # Function call arguments
        elif event_type == "response.function_call_arguments.delta":
            base_event.update({
                "delta": getattr(event.data, 'delta', ''),
                "function_call": True,
                "call_id": getattr(event.data, 'call_id', None)
            })
        
        # Response lifecycle events
        elif event_type in ["response.created", "response.completed"]:
            base_event.update({
                "response_id": getattr(event.data, 'response', {}).get('id') if hasattr(event.data, 'response') else None,
                "status": getattr(event.data, 'response', {}).get('status') if hasattr(event.data, 'response') else None
            })
        
        # Content lifecycle events
        elif event_type in ["response.content_part.added", "response.content_part.done"]:
            base_event.update({
                "content_index": getattr(event.data, 'content_index', 0),
                "item_id": getattr(event.data, 'item_id', None)
            })
        
        # Output item events
        elif event_type in ["response.output_item.added", "response.output_item.done"]:
            base_event.update({
                "output_index": getattr(event.data, 'output_index', 0),
                "item_type": getattr(event.data, 'item', {}).get('type') if hasattr(event.data, 'item') else None
            })
        
        # Text completion events
        elif event_type == "response.output_text.done":
            base_event.update({
                "text": getattr(event.data, 'text', ''),
                "content_index": getattr(event.data, 'content_index', 0),
                "item_id": getattr(event.data, 'item_id', None)
            })
    
    return base_event


def _format_run_item_event(event: RunItemStreamEvent) -> dict[str, Any]:
    """Format run item events (semantic agent events)."""
    base_event = {
        "type": "run_item",
        "name": event.name,
        "item_type": getattr(event.item, 'type', None) if event.item else None,
    }
    
    # Handle specific run item types
    if event.name == "message_output_created":
        base_event.update({
            "role": getattr(event.item, 'role', None),
            "status": getattr(event.item, 'status', None),
            "message_id": getattr(event.item, 'id', None)
        })
    
    elif event.name == "tool_called":
        base_event.update({
            "tool_name": getattr(event.item, 'name', None),
            "tool_arguments": getattr(event.item, 'arguments', None),
            "call_id": getattr(event.item, 'id', None)
        })
    
    elif event.name == "tool_output":
        base_event.update({
            "tool_name": getattr(event.item, 'name', None),
            "output": getattr(event.item, 'output', None),
            "call_id": getattr(event.item, 'id', None)
        })
    
    elif event.name == "handoff_requested":
        base_event.update({
            "target_agent": getattr(event.item, 'target_agent_name', None),
            "reason": getattr(event.item, 'reason', None)
        })
    
    elif event.name == "handoff_occured":
        base_event.update({
            "target_agent": getattr(event.item, 'target_agent_name', None),
            "previous_agent": getattr(event.item, 'previous_agent_name', None)
        })
    
    elif event.name == "reasoning_item_created":
        base_event.update({
            "reasoning_content": getattr(event.item, 'content', None)
        })
    
    # MCP-related events
    elif event.name == "mcp_approval_requested":
        base_event.update({
            "tool_name": getattr(event.item, 'tool_name', None),
            "server_name": getattr(event.item, 'server_name', None)
        })
    
    elif event.name == "mcp_list_tools":
        base_event.update({
            "server_name": getattr(event.item, 'server_name', None),
            "tools": getattr(event.item, 'tools', [])
        })
    
    return base_event


def _format_agent_updated_event(event: AgentUpdatedStreamEvent) -> dict[str, Any]:
    """Format agent updated events (handoffs)."""
    new_agent = event.new_agent
    return {
        "type": "agent_updated",
        "agent_name": new_agent.name,
        "agent_instructions": new_agent.instructions if isinstance(new_agent.instructions, str) else "Dynamic instructions",
        "model": str(new_agent.model) if new_agent.model else None,
        "tools_count": len(new_agent.tools),
        "handoffs_count": len(new_agent.handoffs)
    }


def _extract_usage_info(result) -> Optional[dict[str, Any]]:
    """Extract usage information from result."""
    try:
        if hasattr(result, 'context_wrapper') and result.context_wrapper.usage:
            usage = result.context_wrapper.usage
            return {
                "requests": usage.requests,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens
            }
    except Exception as e:
        logger.error(f"Error extracting usage info: {e}")
    return None


def _extract_response_id(result) -> Optional[str]:
    """Extract response ID from result."""
    try:
        if result.raw_responses and result.raw_responses[-1].response_id:
            return result.raw_responses[-1].response_id
    except Exception as e:
        logger.error(f"Error extracting response ID: {e}")
    return None