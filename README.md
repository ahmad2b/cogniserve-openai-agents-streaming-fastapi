# OpenAI Agents Streaming API

A FastAPI-based backend demonstrating the OpenAI Agents SDK with streaming endpoints for multiple AI agents. This project features dedicated routers per agent with real-time streaming events including agent updates, raw responses, and run items, plus **persistent conversation memory** for multi-turn interactions.

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
- 💾 **Session Memory & Conversation History** - Persistent multi-turn conversations
- 🧩 **Modular architecture** - each agent as separate package
- 📚 **Auto-generated OpenAPI docs** at `/docs`
- 🔧 **Development-ready** with hot reload and comprehensive logging

### 🆕 Session Memory & Conversation Persistence

**Built-in conversational memory using OpenAI Agents SDK's SQLiteSession:**

- **Multi-turn conversations**: Agents remember context across requests
- **Session isolation**: Each user/conversation maintains separate history  
- **Persistent storage**: Conversation history survives server restarts
- **Environment-based config**: Enable with simple `ENABLE_SESSIONS=true`
- **Zero code changes**: Existing endpoints automatically support sessions
- **Production-ready**: SQLite-based storage with proper error handling

**Perfect for:** Chatbots, virtual assistants, customer support, educational apps, and any conversational AI that needs context awareness.

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

# Session Memory Configuration (Optional)
ENABLE_SESSIONS=true                    # Enable conversation memory
SESSION_DB_PATH=./conversations.db      # SQLite database path

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

Each agent has standardized endpoints with **automatic session support**:

#### General Assistant (`/assistant/*`)
```bash
POST /assistant/run      # Synchronous execution
POST /assistant/stream   # Real-time streaming
GET  /assistant/info     # Agent information & session config
DELETE /assistant/session/{session_id}  # Clear conversation history
```

#### Chat Agent (`/chat/*`)  
```bash
POST /chat/run          # Synchronous execution
POST /chat/stream       # Real-time streaming
GET  /chat/info         # Agent information & session config
DELETE /chat/session/{session_id}  # Clear conversation history
```

#### Research Agent (`/research/*`)
```bash
POST /research          # Full research pipeline
```

### Example Usage

#### Basic Usage (No Memory)
```bash
# Test the chat agent without session memory
curl -X POST "http://127.0.0.1:8000/chat/run" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how can you help me?"}'
```

#### With Session Memory (Multi-turn Conversations)
```bash
# First message with session_id - agent introduces context
curl -X POST "http://127.0.0.1:8000/chat/run" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hi, my name is Sarah and I work as a software engineer", "session_id": "user_sarah_123"}'

# Second message - agent remembers Sarah and her profession
curl -X POST "http://127.0.0.1:8000/chat/run" \
  -H "Content-Type: application/json" \
  -d '{"input": "What kind of work do I do?", "session_id": "user_sarah_123"}'

# Stream responses with conversation context
curl -X POST "http://127.0.0.1:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"input": "Give me some programming tips for my field", "session_id": "user_sarah_123"}' \
  --no-buffer
```

#### Session Management
```bash
# Clear conversation history for a user
curl -X DELETE "http://127.0.0.1:8000/chat/session/user_sarah_123"

# Check agent info and session configuration
curl -X GET "http://127.0.0.1:8000/chat/info"
```

## Session Memory & Conversation Persistence

### 🔧 Configuration

**Environment Variables:**
- `ENABLE_SESSIONS=true` - Enable conversation memory globally
- `SESSION_DB_PATH=./conversations.db` - SQLite database location (optional)

### 🎯 How It Works

**Automatic Session Handling:**
- **No session_id**: Traditional stateless interaction
- **With session_id**: Automatic conversation history using OpenAI Agents SDK's SQLiteSession
- **Session isolation**: Each session_id maintains separate conversation memory
- **Persistent storage**: History survives server restarts and deployments

### 💾 Technical Details

**Built on OpenAI Agents SDK patterns:**
- Uses `SQLiteSession` for reliable conversation storage
- Integrates with `Runner.run()` and `Runner.run_streamed()` seamlessly  
- Maintains conversation context across agent handoffs
- Supports both synchronous and streaming interactions with memory

### 🚀 Production Features

- **Environment-driven**: 12-factor app configuration
- **Zero code changes**: Works with existing agent implementations
- **Scalable storage**: SQLite for single instance, easily extensible to PostgreSQL
- **Error handling**: Graceful degradation when sessions unavailable
- **Security**: Session isolation prevents cross-user data leakage

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

Each agent can be imported and used independently, **with or without session memory**:

```python
# Using the chat agent directly (no session)
from src.chat_agent.main import chat_agent
from agents import Runner

result = await Runner.run(chat_agent, "Hello!")

# Using with session memory
from agents import SQLiteSession

session = SQLiteSession("user_123", db_path="conversations.db")
result = await Runner.run(chat_agent, "Hello!", session=session)

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
- **DELETE `/session/{session_id}`** - Clear conversation history for specific session
- **GET `/info`** - Agent metadata, configuration, and session status

### Event Types

The streaming endpoints emit structured events:

1. **`raw_response`** - Direct from OpenAI (text deltas, function calls, etc.)
2. **`run_item`** - Semantic agent events (tool usage, handoffs, reasoning)
3. **`agent_updated`** - Agent handoff notifications
4. **`stream_complete`** - Final results with usage statistics and session info
5. **`error`** - Error handling with details

### Extending the System

To add a new agent **with automatic session support**:

1. Create `src/your_agent/main.py` with agent definition
2. Create `src/api/routers/your_agent.py` using `create_agent_router()`
3. Include the router in `src/api/main.py`
4. **Sessions work automatically** - no additional code needed!

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root and the virtual environment is activated
2. **OpenAI API Key**: Check that `OPENAI_API_KEY` is set in your `.env` file
3. **Port Conflicts**: Change the port in the uvicorn command if 8000 is occupied
4. **Python Version**: Ensure Python 3.13+ is installed and selected
5. **Session Memory**: Set `ENABLE_SESSIONS=true` and restart server to enable conversation memory

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.api.main:app --reload

# Check agent information and session configuration
curl http://127.0.0.1:8000/chat/info

# Test session functionality
curl -X POST http://127.0.0.1:8000/chat/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Test message", "session_id": "debug_session"}'
```

### Performance Optimization

- Use `--workers N` for production deployment
- Configure appropriate `--timeout-keep-alive` for long streaming sessions
- Monitor memory usage with longer conversations
- **Session cleanup**: Implement periodic cleanup of old conversation sessions
- **Database maintenance**: Regular SQLite VACUUM for optimal performance

## Use Cases

### 🤖 Conversational AI Applications
- **Customer support chatbots** with conversation context
- **Virtual assistants** that remember user preferences
- **Educational tutors** tracking learning progress
- **Healthcare assistants** maintaining patient interaction history

### 🏢 Enterprise Applications  
- **Employee helpdesk** with persistent conversation threads
- **Sales assistants** remembering customer interactions
- **Internal knowledge bots** with user-specific context
- **Multi-turn research assistants** building on previous queries

### 🛠️ Developer Tools
- **Code assistants** with project context memory
- **Documentation bots** maintaining conversation flow
- **API testing tools** with session-based request history
- **Interactive debugging assistants** with state persistence

## Contributing

1. Follow the established package structure
2. Use the standardized agent router pattern
3. **Session memory works automatically** - no special handling needed
4. Add comprehensive logging
5. Update documentation for new agents
6. Test both sync and streaming endpoints with and without sessions

---

**Built with FastAPI, OpenAI Agents SDK (with SQLiteSession), and uv for modern Python development.**
