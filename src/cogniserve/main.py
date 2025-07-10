import os
from fastapi import FastAPI
from dotenv import load_dotenv
from agents import set_default_openai_api

from .routers import research
from .utils.logging import get_logger

logger = get_logger(__name__)



# Load .env and configure OpenAI API key for agents
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not set; please define it in your .env file or environment")
else:
    set_default_openai_api(api_key)

app = FastAPI()

app.include_router(research.router)

@app.get("/health")
def health_check():
    """
    Health check endpoint to verify that the service is running.
    """
    logger.info("Health check endpoint was called.")
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"Cogniserve": "Template"}
