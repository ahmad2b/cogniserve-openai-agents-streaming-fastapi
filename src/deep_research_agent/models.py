"""
Deep Research Agent Data Models

Comprehensive Pydantic models for all agent inputs and outputs,
based on the Deep Research Agent Implementation Guide.
"""

from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass

if TYPE_CHECKING:
    from .config import DeepResearchConfig


# ============================================================================
# Enums and Status Models
# ============================================================================

class ResearchStatus(str, Enum):
    """Status of research process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchAPI(str, Enum):
    """Available search API options"""
    TAVILY_MCP = "tavily_mcp"
    NONE = "none"


class MCPServerConfig(BaseModel):
    """Configuration for Tavily MCP server connection via SSE"""
    name: str = Field(default="tavily-search", description="Name of the MCP server")
    url: str = Field(description="URL for SSE transport")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    sse_read_timeout: float = Field(default=300.0, description="SSE read timeout in seconds")
    cache_tools_list: bool = Field(default=True, description="Whether to cache the tools list")
    convert_schemas_to_strict: bool = Field(default=True, description="Convert schemas to strict mode")

# ============================================================================
# Context Models (Local State - Not Sent to LLM)
# ============================================================================

@dataclass
class ResearchContext:
    """
    Typed context for dependency injection in Deep Research Agent.
    
    Contains local state and dependencies that are NOT sent to the LLM.
    Used for dependency injection, API keys, database connections, user info, etc.
    """
    
    # Configuration and Settings
    config: 'DeepResearchConfig'  # Forward reference since config imports models
    session_id: str
    user_id: Optional[str] = None
    
    # Session metadata (not conversation history - that's in SQLiteSession)
    status: ResearchStatus = ResearchStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    error_message: Optional[str] = None
    
    # Research State (local to current execution)
    research_brief: Optional[str] = None
    current_stage: str = "clarification"
    research_findings: list[str] = None
    compressed_research: Optional[str] = None
    final_report: Optional[str] = None
    
    # Quality tracking
    research_quality_score: float = 0.0
    confidence_level: float = 0.0
    
    # Iteration tracking
    current_iteration: int = 0
    supervisor_decisions: list[dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.research_findings is None:
            self.research_findings = []
        if self.supervisor_decisions is None:
            self.supervisor_decisions = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()



# ============================================================================
# Clarification Agent Models
# ============================================================================

class ClarificationResponse(BaseModel):
    """Response from clarification agent"""
    needs_clarification: bool = Field(description="Whether clarification is needed")
    question: Optional[str] = Field(None, description="Clarifying question if needed")
    verification: Optional[str] = Field(None, description="Confirmation message if ready to proceed")
    reasoning: str = Field(description="Reasoning for the decision")


# ============================================================================
# Research Brief Generator Models
# ============================================================================

class ResearchBriefResponse(BaseModel):
    """Response from research brief generator"""
    research_brief: str = Field(description="Detailed, actionable research question")
    key_aspects: list[str] = Field(description="Key aspects to focus on during research")
    scope: str = Field(description="Scope and boundaries of the research")
    success_criteria: str = Field(description="What constitutes successful research completion")


# ============================================================================
# Research Planning Models
# ============================================================================

class ResearchTask(BaseModel):
    """Individual research task"""
    task_id: str = Field(description="Unique identifier for the task")
    topic: str = Field(description="Specific topic to research")
    context: str = Field(description="Context and reasoning for this research")
    priority: int = Field(description="Priority level (1-10, 10 being highest)")
    estimated_depth: int = Field(description="Estimated research depth (1-5)")


class SupervisorDecision(BaseModel):
    """Decision from research supervisor"""
    action: str = Field(description="Action to take: 'conduct_research' or 'complete_research'")
    research_tasks: list[ResearchTask] = Field(default=[], description="Tasks to execute if conducting research")
    completion_reason: Optional[str] = Field(None, description="Reason for completion if ending research")
    gaps_identified: list[str] = Field(default=[], description="Knowledge gaps still present")


# ============================================================================
# Research Compression Models
# ============================================================================

class CompressedResearch(BaseModel):
    """Compressed research findings"""
    queries_made: list[str] = Field(description="List of all queries and tool calls made")
    comprehensive_findings: str = Field(description="All relevant information with inline citations")
    key_excerpts: list[str] = Field(description="Important quotes and excerpts")
    sources: list[dict[str, str]] = Field(description="List of all relevant sources with titles and URLs")
    research_quality: str = Field(description="Assessment of research quality and completeness")


# ============================================================================
# Final Report Models
# ============================================================================

class FinalReport(BaseModel):
    """Final comprehensive research report"""
    title: str = Field(description="Title of the research report")
    executive_summary: str = Field(description="Executive summary of findings")
    full_report: str = Field(description="Complete markdown-formatted report")
    key_findings: list[str] = Field(description="List of key findings")
    recommendations: list[str] = Field(description="Recommendations based on research")
    sources_cited: list[dict[str, str]] = Field(description="All sources cited in the report")
    confidence_assessment: str = Field(description="Assessment of confidence in findings")
    follow_up_research: list[str] = Field(description="Suggested areas for follow-up research")
    methodology: str = Field(description="Description of research methodology used")
    limitations: str = Field(description="Acknowledged limitations of the research")