import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agents import set_default_openai_api

from .routers.research import router as research_router
from .routers.assistant import router as assistant_router
from .routers.chat import router as chat_router
from .utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting OpenAI Agents Streaming API application...")
    
    # Load environment variables
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set; please define it in your .env file")
    else:
        set_default_openai_api(api_key)
        logger.info("OpenAI API key configured")
    
    logger.info("OpenAI Agents Streaming API startup complete")
    
    yield
    
    logger.info("OpenAI Agents Streaming API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="OpenAI Agents Streaming API",
    description="This project demonstrates the OpenAI Agents SDK with streaming endpoints for each agent. Streaming events include agent updates, raw responses, and run items.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware for browser compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include agent routers - each agent gets its own dedicated endpoints
app.include_router(research_router)      # /research/* endpoints
app.include_router(assistant_router)     # /assistant/* endpoints  
app.include_router(chat_router)         # /chat/* endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the OpenAI Agents Streaming API",
        "version": "1.0.0",
        "architecture": "Dedicated routers per agent",
        "features": [
            "Per-agent dedicated endpoints",
            "Streaming events for agent updates, raw responses, and run items",
            "Simple and scalable",
            "OpenAI Agents SDK"
        ],
        "api_docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting OpenAI Agents Streaming API with uvicorn...")
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
