from fastapi import APIRouter
from ..chat_agent.main import chat_agent
from ..utils.agent_router import create_agent_router
from ..utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

router = create_agent_router(
    agent=chat_agent,
    prefix="/chat",
    agent_name="Chat Agent"
)