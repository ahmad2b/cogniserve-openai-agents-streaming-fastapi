import json
import logging
from typing import Any, AsyncGenerator, Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import from OpenAI Agents SDK
from agents import Agent, Runner, TResponseInputItem
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
from .session_utils import create_session_if_enabled, clear_session, get_session_info, get_session_messages


class AgentRequest(BaseModel):
    """Standard request model for agent interactions."""
    input: str | list[TResponseInputItem]
    context: Optional[dict[str, Any]] = None
    session_id: Optional[str] = None 


class AgentResponse(BaseModel):
    """Standard response model for agent interactions."""
    final_output: Any
    success: bool = True
    error: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    response_id: Optional[str] = None
    session_id: Optional[str] = None


class SessionMessagesResponse(BaseModel):
    """Response model for session messages."""
    session_id: str
    messages: List[dict[str, Any]]
    message_count: int
    success: bool = True
    error: Optional[str] = None


class AgentInfo(BaseModel):
    """Agent information response model."""
    name: str
    agent_name: str
    instructions: Optional[str] = None
    model: Optional[str] = None
    tools_count: int = 0
    handoffs_count: int = 0
    endpoints: dict[str, str]
    session_config: dict[str, Any]  # Session configuration info


def create_agent_router(agent: Agent, prefix: str, agent_name: str) -> APIRouter:
    """
    Create a standardized router for an agent with run, run_streamed endpoints and automatic session support.
    
    Sessions are automatically enabled based on environment variables:
    - ENABLE_SESSIONS=true (enables session memory)
    - SESSION_DB_PATH=./conversations.db (optional, sets database path)
    
    When sessions are enabled and session_id is provided in requests,
    conversation history is automatically preserved across interactions.
    
    Args:
        agent: The OpenAI Agent instance
        prefix: URL prefix for the router (e.g., "/chat")
        agent_name: Human-readable name for the agent
    
    Returns:
        APIRouter with standardized endpoints
    """
    # Create agent-specific logger for better log context
    logger = get_logger(agent_name)
    
    router = APIRouter(prefix=prefix, tags=[agent_name])
    
    @router.post("/run", response_model=AgentResponse)
    async def run_agent(request: AgentRequest):
        """
        Run the agent and return the final result.
        
        Automatically uses session memory if:
        - ENABLE_SESSIONS=true in environment
        - session_id is provided in request
        """
        try:
            logger.info(f"Running {agent_name} with input: {request.input}")

            # Automatically create session if enabled and session_id provided
            session = create_session_if_enabled(request.session_id)
            if session:
                logger.info(f"Using session memory: {request.session_id}")
            
            # Run the agent synchronously
            result = await Runner.run(
                starting_agent=agent,
                input=request.input,
                context=request.context,
                session=session
            )
            
            logger.info(f"{agent_name} completed successfully")
            
            return AgentResponse(
                final_output=result.final_output,
                success=True,
                usage=_extract_usage_info(result),
                response_id=_extract_response_id(result),
                session_id=request.session_id
            )
            
        except Exception as e:
            logger.error(f"Error running {agent_name}: {e}")
            return AgentResponse(
                final_output=None,
                success=False,
                error=str(e),
                session_id=request.session_id
            )

    @router.post("/stream")
    async def stream_agent(request: AgentRequest):
        """
        Stream agent responses with events and automatic session support.
        
        Automatically uses session memory if:
        - ENABLE_SESSIONS=true in environment  
        - session_id is provided in request
        """
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                # Automatically create session if enabled and session_id provided
                session = create_session_if_enabled(request.session_id)
                if session:
                    logger.info(f"Using session memory for streaming: {request.session_id}")
                
                stream_result = Runner.run_streamed(
                    starting_agent=agent,
                    input=request.input,
                    context=request.context,
                    session=session
                )
                
                async for event in stream_result.stream_events():
                    # Process each event type with proper serialization
                    formatted_event = _format_stream_event(event, logger)
                    if formatted_event:
                        yield f"data: {json.dumps(formatted_event)}\n\n"
                
                # Send completion event
                completion_event = {
                    "type": "stream_complete",
                    "final_output": stream_result.final_output,
                    "current_turn": stream_result.current_turn,
                    "usage": _extract_usage_info(stream_result) if hasattr(stream_result, 'usage') else None,
                    "session_id": request.session_id
                }
                yield f"data: {json.dumps(completion_event)}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                error_event = {
                    "type": "error", 
                    "message": str(e),
                    "timestamp": str(logger.info.__self__.makeRecord("", 0, "", 0, "", (), None).created),
                    "session_id": request.session_id if hasattr(request, 'session_id') else None
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

    @router.get("/session/{session_id}", response_model=SessionMessagesResponse)
    async def get_agent_session_messages(session_id: str, limit: Optional[int] = None):
        """Retrieve all messages for a specific session."""
        try:
            messages = await get_session_messages(session_id, limit=limit)
            if messages is not None:
                # Convert messages to serializable format
                serialized_messages = []
                for message in messages:
                    if isinstance(message, dict):
                        serialized_messages.append(message)
                    else:
                        # Handle case where message might be a complex object
                        try:
                            # Try to convert to dict if it has __dict__ attribute
                            if hasattr(message, '__dict__'):
                                serialized_messages.append(message.__dict__)
                            else:
                                # Fallback to string representation
                                serialized_messages.append({"content": str(message)})
                        except Exception:
                            serialized_messages.append({"content": str(message)})
                
                return SessionMessagesResponse(
                    session_id=session_id,
                    messages=serialized_messages,
                    message_count=len(serialized_messages),
                    success=True
                )
            else:
                return SessionMessagesResponse(
                    session_id=session_id,
                    messages=[],
                    message_count=0,
                    success=False,
                    error="Session not found or sessions disabled"
                )
        except Exception as e:
            logger.error(f"Error retrieving session messages: {e}")
            return SessionMessagesResponse(
                session_id=session_id,
                messages=[],
                message_count=0,
                success=False,
                error=str(e)
            )

    @router.delete("/session/{session_id}")
    async def clear_agent_session(session_id: str):
        """Clear conversation history for a specific session."""
        try:
            success = clear_session(session_id)
            if success:
                return {"message": f"Session {session_id} cleared successfully", "success": True}
            else:
                return {"message": f"Failed to clear session {session_id}", "success": False}
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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
            
            # Build endpoints dict
            endpoints = {
                "run": f"{prefix}/run",
                "stream": f"{prefix}/stream",
                "get_session": f"{prefix}/session/{{session_id}}",
                "clear_session": f"{prefix}/session/{{session_id}}",
                "info": f"{prefix}/info"
            }
            
            # Get session configuration
            session_config = get_session_info()
            
            return AgentInfo(
                name=agent_name,
                agent_name=agent.name,
                instructions=instructions,
                model=model_info,
                tools_count=tools_count,
                handoffs_count=handoffs_count,
                endpoints=endpoints,
                session_config=session_config
            )
        except Exception as e:
            logger.error(f"Error getting {agent_name} info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


def _format_stream_event(event: StreamEvent, logger: logging.Logger) -> Optional[dict[str, Any]]:
    """
    Format stream events into a consistent, frontend-friendly structure.
    
    This avoids double JSON encoding and provides clean event structures.
    """
    try:
        formatted_event = None
        if isinstance(event, RawResponsesStreamEvent):
            formatted_event = _format_raw_response_event(event)
        elif isinstance(event, RunItemStreamEvent):
            formatted_event = _format_run_item_event(event)
        elif isinstance(event, AgentUpdatedStreamEvent):
            formatted_event = _format_agent_updated_event(event)
        else:
            # Fallback for unknown event types
            logger.warning(f"Unknown event type: {type(event)}")
            formatted_event = {
                "type": "unknown_event",
                "event_class": str(type(event).__name__),
                "data": str(event) if event else None
            }
        
        if formatted_event:
            logger.info(f"{formatted_event}")
        return formatted_event
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
            
        # Capture tool name when tool call starts 
        elif event_type == "response.output_item.added":  
            item_obj = getattr(event.data, 'item', None)  
            base_event.update({  
                "output_index": getattr(event.data, 'output_index', 0),  
                "item_type": getattr(item_obj, 'type', None) if item_obj else None  
            })  
              
            # Extract tool name if this is a function tool call  
            if item_obj and hasattr(item_obj, 'name'):  
                base_event.update({  
                    "tool_name": item_obj.name,  # Tool name available here!  
                    "call_id": getattr(item_obj, 'call_id', None)  
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
            response_obj = getattr(event.data, 'response', None)
            base_event.update({
                "response_id": getattr(response_obj, 'id', None) if response_obj else None,
                "status": getattr(response_obj, 'status', None) if response_obj else None
            })
        
        # Content lifecycle events
        elif event_type in ["response.content_part.added", "response.content_part.done"]:
            base_event.update({
                "content_index": getattr(event.data, 'content_index', 0),
                "item_id": getattr(event.data, 'item_id', None)
            })
        
        # Output item events
        elif event_type in ["response.output_item.added", "response.output_item.done"]:
            item_obj = getattr(event.data, 'item', None)
            base_event.update({
                "output_index": getattr(event.data, 'output_index', 0),
                "item_type": getattr(item_obj, 'type', None) if item_obj else None
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
            "tool_name": getattr(event.item.raw_item, 'name', None),
            "tool_arguments": getattr(event.item.raw_item, 'arguments', None),
            "call_id": getattr(event.item.raw_item, 'id', None)
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
        # Create a utility logger for these helper functions
        util_logger = get_logger("agent.utils")
        util_logger.error(f"Error extracting usage info: {e}")
    return None


def _extract_response_id(result) -> Optional[str]:
    """Extract response ID from result."""
    try:
        if result.raw_responses and result.raw_responses[-1].response_id:
            return result.raw_responses[-1].response_id
    except Exception as e:
        # Create a utility logger for these helper functions  
        util_logger = get_logger("agent.utils")
        util_logger.error(f"Error extracting response ID: {e}")
    return None