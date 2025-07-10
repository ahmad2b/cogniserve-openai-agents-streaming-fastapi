from __future__ import annotations

import asyncio

from agents import Runner, custom_span, gen_trace_id, trace

from .agents.planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from .agents.search_agent import search_agent
from .agents.writer_agent import ReportData, writer_agent
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ResearchManager:
  def __init__(self):
    pass

  async def run(self, query: str) -> ReportData:
    trace_id = gen_trace_id()
    logger.info(f"Starting research for query: '{query}'. Trace ID: {trace_id}")
    with trace("Research Trace", trace_id=trace_id):
      search_plan = await self._plan_searches(query=query)
      search_results = await self._perform_searches(search_plan=search_plan)
      report = await self._write_report(query=query, search_results=search_results)
      
    logger.info(f"Research finished for query: '{query}'.")
    return report
      
  async def _plan_searches(self, query: str) -> WebSearchPlan:
    logger.info("Planning searches...")
    result = await Runner.run(
        planner_agent,
        f"Query: {query}",
    )
    logger.info(f"Search planning complete. Found {len(result.final_output.searches)} searches.")
    return result.final_output_as(WebSearchPlan)
  
  async def _perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
    logger.info(f"Performing {len(search_plan.searches)} searches...")
    with custom_span("Search the web"):
      num_completed = 0
      tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches]
      results = []
      for task in asyncio.as_completed(tasks):
        result = await task
        if result is not None:
            results.append(result)
        num_completed += 1
        logger.debug(f"Search {num_completed}/{len(tasks)} completed.")
    logger.info("All searches performed.")
    return results

  async def _search(self, item: WebSearchItem) -> str | None:
    logger.debug(f"Searching for: '{item.query}'")
    input = f"Search term: {item.query}\nReason for searching: {item.reason}"
    try:
      result = await Runner.run(
          search_agent,
          input,
      )
      return str(result.final_output)
    except Exception as e:
      logger.error(f"Search failed for query '{item.query}': {e}")
      return None

  async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
    logger.info("Writing report...")
    input = f"Original query: {query}\nSummarized search results: {search_results}"
    result = await Runner.run(
        writer_agent,
        input,
    )
    logger.info("Report writing complete.")
    return result.final_output_as(ReportData)