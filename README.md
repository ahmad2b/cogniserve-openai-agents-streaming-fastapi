# OpenAI Agents Streaming API

A FastAPI-based backend demonstrating the OpenAI Agents SDK with streaming endpoints for multiple AI agents. This project features dedicated routers per agent with real-time streaming events including agent updates, raw responses, and run items.

## Architecture

This project is structured with separate packages for each agent:

```
src/
├── api/                 # FastAPI application
│   ├── routers/        # Agent-specific endpoints  
│   └── utils/          # Shared utilities
├── chat_agent/         # General chat agent package
└── research_bot/       # Research agent package with sub-agents
    ├── agents/         # Planner, Search, and Writer agents
    └── manager.py      # Research orchestration
```

Each agent package can be imported and used independently, making the system modular and scalable.

## Features

- 🚀 **Per-agent dedicated endpoints** with standardized patterns
- 📡 **Real-time streaming** with Server-Sent Events (SSE)
- 🔄 **Event types**: Raw LLM responses, semantic agent events, handoffs
- 🧩 **Modular architecture** - each agent as separate package
- 📚 **Auto-generated OpenAPI docs** at `/docs`
- 🔧 **Development-ready** with hot reload and comprehensive logging

## Prerequisites

- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **OpenAI API Key** - Set in environment variables

## Installation & Setup

### 1. Install uv (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip
pip install uv
```

### 2. Clone and Setup Project

```bash
git clone https://github.com/ahmad2b/openai-agents-streaming-api.git
cd openai-agents-streaming-api

# Create virtual environment with correct Python version
uv venv

# Activate virtual environment
# On Unix/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install project in development mode with all dependencies
uv pip install -e .
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: Custom port (default is 8000)
PORT=8000
```

## Running the Application

### Development Mode (Recommended)

```bash
# Using uvicorn directly (with hot reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using the module directly
python -m src.api.main
```

### Production Mode

```bash
# Install production dependencies (if different)
uv pip install -e .

# Run with production settings
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using uv run (Alternative)

```bash
# Run directly with uv (manages virtual environment automatically)
uv run uvicorn src.api.main:app --reload
```

## API Endpoints

### Base URLs
- **Application**: `http://127.0.0.1:8000`
- **Interactive Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

### Agent Endpoints

Each agent has standardized endpoints:

#### General Assistant (`/assistant/*`)
```bash
POST /assistant/run      # Synchronous execution
POST /assistant/stream   # Real-time streaming
GET  /assistant/info     # Agent information
```

#### Chat Agent (`/chat/*`)  
```bash
POST /chat/run          # Synchronous execution
POST /chat/stream       # Real-time streaming
GET  /chat/info         # Agent information
```

#### Research Agent (`/research/*`)
```bash
POST /research          # Full research pipeline
```

### Example Usage

```bash
# Test the chat agent
curl -X POST "http://127.0.0.1:8000/chat/run" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how can you help me?"}'

# Stream responses from assistant
curl -X POST "http://127.0.0.1:8000/assistant/stream" \
  -H "Content-Type: application/json" \
  -d '{"input": "Explain quantum computing"}' \
  --no-buffer
```

## Development Best Practices

### Package Management with uv

```bash
# Add new dependencies
uv add package-name

# Add development dependencies  
uv add --dev pytest black isort

# Update all dependencies
uv lock --upgrade

# Install from lock file (for consistent environments)
uv pip install -r uv.lock
```

### Code Quality

```bash
# Install development tools
uv add --dev black isort flake8 pytest

# Format code
black src/
isort src/

# Run linting
flake8 src/

# Run tests
pytest
```

### Working with Individual Agents

Each agent can be imported and used independently:

```python
# Using the chat agent directly
from src.chat_agent.main import chat_agent
from agents import Runner

result = await Runner.run(chat_agent, "Hello!")

# Using the research bot
from src.research_bot.manager import ResearchManager

manager = ResearchManager()
report = await manager.run("AI trends 2024")
```

## Project Structure Details

### Agent Router Pattern

Each agent uses the standardized `create_agent_router()` utility that provides:

- **POST `/run`** - Synchronous execution with complete response
- **POST `/stream`** - Real-time streaming with formatted events  
- **GET `/info`** - Agent metadata and configuration

### Event Types

The streaming endpoints emit structured events:

1. **`raw_response`** - Direct from OpenAI (text deltas, function calls, etc.)
2. **`run_item`** - Semantic agent events (tool usage, handoffs, reasoning)
3. **`agent_updated`** - Agent handoff notifications
4. **`stream_complete`** - Final results with usage statistics
5. **`error`** - Error handling with details

### Extending the System

To add a new agent:

1. Create `src/your_agent/main.py` with agent definition
2. Create `src/api/routers/your_agent.py` using `create_agent_router()`
3. Include the router in `src/api/main.py`

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root and the virtual environment is activated
2. **OpenAI API Key**: Check that `OPENAI_API_KEY` is set in your `.env` file
3. **Port Conflicts**: Change the port in the uvicorn command if 8000 is occupied
4. **Python Version**: Ensure Python 3.13+ is installed and selected

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.api.main:app --reload

# Check agent information
curl http://127.0.0.1:8000/assistant/info
```

### Performance Optimization

- Use `--workers N` for production deployment
- Configure appropriate `--timeout-keep-alive` for long streaming sessions
- Monitor memory usage with longer conversations
- Consider implementing conversation cleanup for long-running sessions

## Contributing

1. Follow the established package structure
2. Use the standardized agent router pattern
3. Add comprehensive logging
4. Update documentation for new agents
5. Test both sync and streaming endpoints

---

**Built with FastAPI, OpenAI Agents SDK, and uv for modern Python development.**
