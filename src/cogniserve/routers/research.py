from fastapi import APIRouter
from ..research_bot.manager import ResearchManager
from ..research_bot.agents.writer_agent import ReportData
from ..utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/research", response_model=ReportData)
async def research(query: str):
    logger.info(f"Received research request for query: '{query}'")
    manager = ResearchManager()
    report = await manager.run(query)
    logger.info(f"Research complete for query: '{query}'")
    return report
