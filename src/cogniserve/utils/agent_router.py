import json
from typing import Any, Optional

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
            usage_info = None
            if hasattr(result, 'context_wrapper') and result.context_wrapper.usage:
                usage = result.context_wrapper.usage
                usage_info = {
                    "requests": usage.requests,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens
                }
            
            # Get response ID from the last response if available
            response_id = None
            if result.raw_responses and result.raw_responses[-1].response_id:
                response_id = result.raw_responses[-1].response_id
            
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
        Stream agent responses in real-time using Server-Sent Events.
        
        This endpoint provides real-time streaming of the agent's thinking process
        and responses as they are generated.
        """
        try:
            logger.info(f"Starting stream for {agent_name} with message: {request.message[:100]}...")
            
            async def event_stream():
                """Generate streaming events from the agent."""
                try:
                    # Use the OpenAI Agents SDK streaming
                    result = Runner.run_streamed(
                        starting_agent=agent,
                        input=request.message,
                        max_turns=request.max_turns,
                        context=request.context
                    )
                    
                    # Stream events as they come from the SDK
                    async for event in result.stream_events():
                        event_data = await _process_stream_event(event, agent_name)
                        if event_data:
                            yield f"data: {json.dumps(event_data)}\n\n"
                    
                    # After streaming completes, access the final result directly
                    
                    # Extract usage information
                    usage_info = None
                    if hasattr(result, 'context_wrapper') and result.context_wrapper.usage:
                        usage = result.context_wrapper.usage
                        usage_info = {
                            "requests": usage.requests,
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens
                        }
                    
                    # Get response ID from the last response if available
                    response_id = None
                    if result.raw_responses and result.raw_responses[-1].response_id:
                        response_id = result.raw_responses[-1].response_id
                    
                    completion_event = {
                        "type": "completion",
                        "data": {
                            "final_output": result.final_output,
                            "success": True,
                            "usage": usage_info,
                            "response_id": response_id
                        },
                        "agent": agent_name
                    }
                    yield f"data: {json.dumps(completion_event)}\n\n"
                    
                    logger.info(f"{agent_name} streaming completed successfully")
                    
                except Exception as e:
                    logger.error(f"Error in {agent_name} streaming: {e}")
                    error_event = {
                        "type": "error",
                        "data": {
                            "error": str(e),
                            "success": False
                        },
                        "agent": agent_name
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to start streaming for {agent_name}: {e}")
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


async def _process_stream_event(event: StreamEvent, agent_name: str) -> Optional[dict[str, Any]]:
    """
    Process a stream event from the OpenAI Agents SDK into a standardized format.
    
    This function handles the different event types and extracts relevant information
    in a structured way for the client.
    """
    try:
        base_event = {
            "type": event.type,
            "agent": agent_name,
            "timestamp": None  # Could add timestamp if needed
        }
        
        if isinstance(event, RawResponsesStreamEvent):
            # Handle raw LLM response events
            base_event["event_name"] = "raw_response"
            
            # Check if it's a text delta event for real-time text streaming
            if isinstance(event.data, ResponseTextDeltaEvent):
                base_event["data"] = {
                    "delta": event.data.delta,
                    "type": "text_delta"
                }
            else:
                # Handle other raw response types
                if hasattr(event.data, 'model_dump'):
                    base_event["data"] = event.data.model_dump()
                else:
                    base_event["data"] = {"raw": str(event.data)}
                    
        elif isinstance(event, AgentUpdatedStreamEvent):
            # Handle agent handoff events
            base_event["event_name"] = "agent_updated"
            base_event["data"] = {
                "new_agent_name": event.new_agent.name,
                "agent_instructions": event.new_agent.instructions if isinstance(event.new_agent.instructions, str) else None
            }
            
        elif isinstance(event, RunItemStreamEvent):
            # Handle run item events (tool calls, messages, etc.)
            base_event["event_name"] = "run_item"
            base_event["data"] = {
                "item_name": event.name,
                "item_type": event.item.type,
                "item_summary": _summarize_run_item(event.item)
            }
            
        else:
            # Fallback for unknown event types
            base_event["event_name"] = "unknown"
            base_event["data"] = {"raw_event": str(event)}
            
        return base_event
        
    except Exception as e:
        logger.error(f"Error processing stream event: {e}")
        return {
            "type": "error",
            "event_name": "processing_error",
            "agent": agent_name,
            "data": {"error": str(e)}
        }


def _summarize_run_item(item) -> dict[str, Any]:
    """Summarize a run item for the client."""
    try:
        summary = {"type": item.type}
        
        # Add type-specific information
        if item.type == "message_output_item":
            # Extract text content from message
            text_content = ItemHelpers.text_message_output(item)
            summary["content"] = text_content[:200] + "..." if len(text_content) > 200 else text_content
            
        elif item.type == "tool_call_item":
            # Summarize tool call
            if hasattr(item.raw_item, 'function'):
                summary["tool_name"] = item.raw_item.function.name
                summary["tool_args"] = item.raw_item.function.arguments[:100] + "..." if len(item.raw_item.function.arguments) > 100 else item.raw_item.function.arguments
            else:
                summary["tool_info"] = str(item.raw_item)[:100]
                
        elif item.type == "tool_call_output_item":
            # Summarize tool output
            output_str = str(item.output)
            summary["output"] = output_str[:200] + "..." if len(output_str) > 200 else output_str
            
        elif item.type == "handoff_call_item":
            # Summarize handoff
            if hasattr(item.raw_item, 'function'):
                summary["handoff_target"] = item.raw_item.function.name
                
        elif item.type == "reasoning_item":
            # Summarize reasoning
            if hasattr(item.raw_item, 'content'):
                content = str(item.raw_item.content)
                summary["reasoning"] = content[:200] + "..." if len(content) > 200 else content
                
        return summary
        
    except Exception as e:
        return {"type": item.type, "error": str(e)} 