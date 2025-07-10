import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agents import set_default_openai_api

from .routers.research import router as research_router
from .routers.assistant import router as assistant_router
from .routers.coder import router as coder_router
from .utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting CogniServe application...")
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set; please define it in your .env file")
    else:
        set_default_openai_api(api_key)
        logger.info("OpenAI API key configured")
    
    logger.info("CogniServe startup complete")
    
    yield
    
    logger.info("CogniServe shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="CogniServe",
    description="AI Agent API with dedicated endpoints per agent",
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
app.include_router(coder_router)         # /coder/* endpoints


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to CogniServe - AI Agent API",
        "version": "1.0.0",
        "architecture": "Dedicated routers per agent",
        "features": [
            "Per-agent dedicated endpoints",
            "Synchronous and streaming execution",
            "Standardized API patterns",
            "Real-time Server-Sent Events",
            "Simple and scalable"
        ],
        "agents": {
            "research": {
                "description": "Multi-agent research system",
                "endpoints": ["/research/*"]
            },
            "assistant": {
                "description": "General purpose AI assistant", 
                "endpoints": ["/assistant/run", "/assistant/stream", "/assistant/info"]
            },
            "coder": {
                "description": "Programming and coding assistant",
                "endpoints": ["/coder/run", "/coder/stream", "/coder/info"]
            }
        },
        "api_docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agents": ["research", "assistant", "coder"],
        "total_agents": 3
    }


@app.get("/agents")
async def list_agents():
    """List all available agents and their endpoints."""
    return {
        "agents": [
            {
                "name": "Research Assistant",
                "prefix": "/research",
                "description": "Multi-agent research system with web search",
                "endpoints": {
                    "legacy": "/research/generate"
                }
            },
            {
                "name": "General Assistant", 
                "prefix": "/assistant",
                "description": "General purpose helpful AI assistant",
                "endpoints": {
                    "run": "/assistant/run",
                    "stream": "/assistant/stream", 
                    "info": "/assistant/info"
                }
            },
            {
                "name": "Coding Assistant",
                "prefix": "/coder", 
                "description": "Programming and software development helper",
                "endpoints": {
                    "run": "/coder/run",
                    "stream": "/coder/stream",
                    "info": "/coder/info"
                }
            }
        ],
        "standard_endpoints": {
            "run": "Synchronous execution - returns final result",
            "stream": "Real-time streaming via Server-Sent Events", 
            "info": "Agent information and capabilities"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting CogniServe with uvicorn...")
    uvicorn.run(
        "cogniserve.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
