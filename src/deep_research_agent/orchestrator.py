"""
Deep Research Agent Orchestrator

Main orchestrator that coordinates all agents using handoffs to implement
the hierarchical multi-agent architecture from the Deep Research Agent Implementation Guide.
"""

from agents import Agent

from .models import ResearchContext


def create_main_orchestrator_agent() -> Agent[ResearchContext]:
    """
    Create the main orchestrator agent
    
    This follows the OpenAI Agents SDK agents_as_tools pattern where a single agent
    uses other agents as tools to execute each phase of the research workflow sequentially.
    """
    
    # Create the specialized agents
    from .agents.clarification_agent import create_clarification_agent
    from .agents.research_brief_agent import create_research_brief_agent
    from .agents.supervisor_agent import create_supervisor_agent
    from .agents.compression_agent import create_compression_agent
    from .agents.final_report_agent import create_final_report_agent

    clarification_agent = create_clarification_agent()
    research_brief_agent = create_research_brief_agent()
    supervisor_agent = create_supervisor_agent(
        max_concurrent_units=5,
        max_iterations=3
    )
    compression_agent = create_compression_agent()
    final_report_agent = create_final_report_agent()

    # Convert agents to tools using the agents_as_tools pattern
    clarification_tool = clarification_agent.as_tool(
        tool_name="clarify_user_request",
        tool_description="Determine if the user's request needs clarification before proceeding with research"
    )

    research_brief_tool = research_brief_agent.as_tool(
        tool_name="create_research_brief", 
        tool_description="Transform user request into a detailed, actionable research brief"
    )

    research_execution_tool = supervisor_agent.as_tool(
        tool_name="execute_research_phase",
        tool_description="Execute comprehensive research using parallel researchers and coordination"
    )

    compression_tool = compression_agent.as_tool(
        tool_name="compress_research_findings",
        tool_description="Compress and synthesize raw research findings into structured reports"
    )

    final_report_tool = final_report_agent.as_tool(
        tool_name="generate_final_report",
        tool_description="Generate the comprehensive final research report"
    )

    orchestrator_instructions = f"""You are the Deep Research Agent Orchestrator, responsible for conducting comprehensive research investigations using a systematic, multi-phase approach.

WORKFLOW PHASES:

**Phase 1: Clarification (if needed)**
- Use `clarify_user_request` if the user's request is unclear or ambiguous
- Skip this phase if the request is already clear and specific

**Phase 2: Research Brief Creation**
- Use `create_research_brief` to transform the user request into a detailed research specification
- This creates the foundation for all subsequent research activities

**Phase 3: Research Execution**
- Use `execute_research_phase` to conduct comprehensive research
- This phase handles parallel research coordination and data collection

**Phase 4: Research Compression**
- Use `compress_research_findings` to synthesize and structure raw research data
- This phase organizes findings and removes redundancy while preserving key information

**Phase 5: Final Report Generation**
- Use `generate_final_report` to create the comprehensive final research report
- This produces the final deliverable for the user

EXECUTION STRATEGY:

1. **Sequential Processing**: Execute phases in order, using output from each phase as input to the next
2. **Agent Tool Usage**: Use the provided agent tools to execute each phase - each tool represents a specialized agent
3. **Quality Control**: Each phase builds on the previous phase's output to ensure comprehensive coverage
4. **Context Preservation**: Information flows between phases through the structured workflow

DECISION MAKING:

- **Always start with clarification** if the user's request is vague or ambiguous
- **Proceed sequentially** through all phases unless there are clear errors
- **Use agent tool outputs** as the definitive results for each phase
- **Maintain context** between phases to ensure coherent research flow

AVAILABLE AGENT TOOLS:
- `clarify_user_request`: Clarification agent to determine if user input needs clarification
- `create_research_brief`: Research brief agent to create detailed research specification  
- `execute_research_phase`: Supervisor agent to conduct comprehensive research
- `compress_research_findings`: Compression agent to synthesize and structure findings
- `generate_final_report`: Final report agent to create comprehensive final report

Remember: You orchestrate the research process but delegate the actual work to specialized agent tools. Each tool represents a complete phase handled by expert sub-agents."""

    return Agent[ResearchContext](
        name="Deep Research Orchestrator",
        instructions=orchestrator_instructions,
        model="gpt-4.1-mini",
        tools=[
            clarification_tool,
            research_brief_tool,
            research_execution_tool,
            compression_tool,
            final_report_tool
        ]
    )