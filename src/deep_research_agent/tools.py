"""
Deep Research Agent Function Tools

Comprehensive function tools for research operations using
the OpenAI Agents SDK function_tool decorator.
"""

from typing import List
from agents import function_tool, RunContextWrapper, Runner
from ..api.utils.logging import get_logger
from .models import ResearchContext

logger = get_logger(__name__)


# ============================================================================
# Research Orchestration Tools
# ============================================================================

@function_tool
async def conduct_research(
    ctx: RunContextWrapper[ResearchContext],
    research_topic: str
) -> str:
    """
    Conduct focused research on a specific topic using individual researcher agents.
    
    This tool spawns an individual researcher agent that will use available tools
    (like Tavily MCP server) to conduct comprehensive research on the specified topic.
    Following the guide's specification for parallel research execution.
    
    Args:
        ctx: Runtime context wrapper with ResearchContext
        research_topic: Specific topic to research in detail
        
    Returns:
        Instruction for conducting research
    """
    context = ctx.context
    logger.info(f"Conducting research on topic: {research_topic}")
    
    try:
        # Create a researcher agent for this specific topic
        from .agents.researcher_agent import create_researcher_agent
        
        researcher = create_researcher_agent(
            research_topic=research_topic,
            max_tool_calls=5
        )
        
        # Run the researcher agent with comprehensive research prompt
        research_prompt = f"""Conduct comprehensive research on: {research_topic}

Use all available search tools to thoroughly investigate this topic:

1. **Search Phase**: Use available search tools to find relevant information
   - Search with different query variations
   - Look for recent developments and historical context
   - Find authoritative sources and expert perspectives

2. **Deep Analysis Phase**: Analyze the search results
   - Extract detailed information from key sources
   - Focus on factual data, statistics, and expert opinions
   - Identify key trends and insights

3. **Comprehensive Coverage**: Ensure you cover all aspects
   - Technical details and practical implications
   - Current state and future projections
   - Different viewpoints and perspectives

4. **Quality Assurance**: Verify information quality
   - Cross-reference facts across multiple sources
   - Prioritize authoritative and recent sources
   - Note any contradictions or uncertainties

Provide a comprehensive research summary with:
- Key findings and insights
- Supporting evidence and statistics
- Source attribution for all claims
- Assessment of information quality and reliability"""
        
        result = await Runner.run(
            starting_agent=researcher,
            input=research_prompt,
            context=context
        )
        
        research_findings = str(result.final_output)
        
        # Store findings in context
        context.research_findings.append(research_findings)
        context.current_iteration += 1
        
        logger.info(f"Research completed for topic: {research_topic}")
        logger.info(f"Session {context.session_id}: Research iteration {context.current_iteration} completed")
        
        return research_findings
        
    except Exception as e:
        error_msg = f"Research failed for topic '{research_topic}': {str(e)}"
        logger.error(error_msg)
        context.error_message = error_msg
        return f"ERROR: {error_msg}"


@function_tool
async def research_complete(
    ctx: RunContextWrapper[ResearchContext],
    reason: str,
    confidence_level: float = 0.8
) -> str:
    """
    Signal that research is complete.
    
    Args:
        ctx: Runtime context wrapper with ResearchContext
        reason: Reason for completing research
        confidence_level: Confidence in research completeness (0-1)
        
    Returns:
        Completion confirmation message
    """
    logger.info(f"Research completion signaled: {reason} (confidence: {confidence_level})")
    
    # Update context with completion info
    context = ctx.context
    context.confidence_level = confidence_level
    context.current_stage = "completed"
    
    logger.info(f"Session {context.session_id}: Research completed at iteration {context.current_iteration}")
    
    return f"""
RESEARCH COMPLETED

Reason: {reason}
Confidence Level: {confidence_level:.2f}

The research phase has been completed. All identified research tasks have been 
addressed with the specified confidence level. The findings should now be 
processed for final report generation.
"""


# ============================================================================
# Research Quality and Analysis Tools
# ============================================================================

@function_tool
async def assess_research_completeness(
    ctx: RunContextWrapper[ResearchContext],
    research_findings: str,
    original_query: str,
    required_aspects: List[str] = None
) -> str:
    """
    Assess the completeness and quality of research findings.
    
    Args:
        ctx: Runtime context wrapper
        research_findings: Current research findings to assess
        original_query: Original research query for context
        required_aspects: Optional list of aspects that should be covered
        
    Returns:
        Assessment of research completeness with recommendations
    """
    logger.info(f"Assessing research completeness for query: {original_query}")
    
    try:
        aspects_instruction = ""
        if required_aspects:
            aspects_instruction = f"""
Required aspects to verify coverage:
{chr(10).join(f"- {aspect}" for aspect in required_aspects)}
"""
        
        assessment_instruction = f"""
Please assess the completeness and quality of the following research findings:

ORIGINAL QUERY: {original_query}

RESEARCH FINDINGS TO ASSESS:
{research_findings}

{aspects_instruction}

Assessment criteria:
1. **Completeness**: Are all key aspects of the query addressed?
2. **Depth**: Is the information sufficiently detailed and comprehensive?
3. **Currency**: Is the information current and up-to-date?
4. **Source Quality**: Are the sources credible and authoritative?
5. **Balance**: Are multiple perspectives represented?
6. **Factual Accuracy**: Are claims supported by evidence?

Provide your assessment in this format:

**RESEARCH QUALITY ASSESSMENT**

**Completeness Score: X/10**
- What's well covered
- What's missing or insufficient

**Quality Indicators:**
- Source credibility level
- Information currency
- Factual support level

**Gaps Identified:**
- Key information still needed
- Areas requiring deeper research
- Missing perspectives or viewpoints

**Recommendations:**
- Specific additional research needed
- Priority areas for improvement
- Suggested search strategies

**Overall Assessment:**
- Ready for final report? (Yes/No)
- Confidence level in findings
- Final recommendations
"""
        
        logger.info("Prepared research completeness assessment instruction")
        return assessment_instruction
        
    except Exception as e:
        error_msg = f"Research assessment preparation failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool
async def synthesize_findings(
    ctx: RunContextWrapper[ResearchContext],
    research_data: List[str],
    synthesis_focus: str
) -> str:
    """
    Synthesize multiple research findings into coherent insights.
    
    Args:
        ctx: Runtime context wrapper
        research_data: List of research findings to synthesize
        synthesis_focus: Focus area for synthesis
        
    Returns:
        Synthesized research insights
    """
    logger.info(f"Preparing research synthesis with focus: {synthesis_focus}")
    
    try:
        findings_text = "\n\n---\n\n".join(research_data)
        
        synthesis_instruction = f"""
Please synthesize the following research findings into coherent, actionable insights:

SYNTHESIS FOCUS: {synthesis_focus}

RESEARCH FINDINGS TO SYNTHESIZE:
{findings_text}

Synthesis Guidelines:
1. **Integration**: Combine related information from different sources
2. **Pattern Recognition**: Identify common themes and trends
3. **Contradiction Resolution**: Address any conflicting information
4. **Gap Analysis**: Note areas where information is limited
5. **Insight Generation**: Draw meaningful conclusions from the data

Provide synthesis in this format:

**RESEARCH SYNTHESIS**

**Key Themes Identified:**
- Major themes across all research
- Supporting evidence for each theme

**Cross-Source Insights:**
- Insights that emerge from combining multiple sources
- Patterns visible only when viewing all findings together

**Contradictions and Uncertainties:**
- Areas where sources disagree
- Information gaps or uncertainties
- Reliability assessment of conflicting claims

**Actionable Insights:**
- Practical implications of the findings
- Recommendations based on the research
- Future research directions

**Confidence Assessment:**
- High-confidence findings (well-supported)
- Medium-confidence findings (some support)
- Low-confidence findings (limited support)

**Sources Integration:**
- How different sources complement each other
- Source quality and reliability assessment
- Citation recommendations for final report
"""
        
        logger.info(f"Prepared synthesis instruction for {len(research_data)} findings")
        return synthesis_instruction
        
    except Exception as e:
        error_msg = f"Research synthesis preparation failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


# ============================================================================
# Tool Registry
# ============================================================================

# Orchestration tools
ORCHESTRATION_TOOLS = [
    conduct_research,
    research_complete,
]

# Quality assurance tools
QUALITY_TOOLS = [
    assess_research_completeness,
    synthesize_findings,
]

# All available research tools
ALL_RESEARCH_TOOLS = ORCHESTRATION_TOOLS + QUALITY_TOOLS

# Tools for different agent types
SUPERVISOR_TOOLS = [conduct_research, research_complete]
RESEARCHER_TOOLS = QUALITY_TOOLS  # MCP tools will be added directly to agents
COMPRESSION_TOOLS = [synthesize_findings, assess_research_completeness] 