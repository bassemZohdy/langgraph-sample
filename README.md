# LangGraph Multi-Model Agent

A comprehensive LangGraph application that serves a chat agent via FastAPI with support for multiple AI providers (Ollama, OpenAI, Anthropic, Groq, Together AI), and persists conversation state and LangGraph checkpoints in PostgreSQL. This repo is fully open source and does not require any commercial licenses.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup
1. Clone and enter the project
   ```bash
   git clone <repository-url>
   cd langgraph
   ```
2. Create environment file
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```
3. Start services
   ```bash
   docker-compose up -d
   ```
4. Verify
   ```bash
   docker-compose ps
   curl http://localhost:8000/health
   ```

## 🏗️ Architecture

### Services
- PostgreSQL: Persistent storage for conversation messages and LangGraph checkpoints.
- Ollama: Local LLM server; pulls and runs the model set in `OLLAMA_MODEL` (default `phi3:mini`).
- LangGraph Agent: FastAPI app with multi-model support exposing chat/graph endpoints.
- UI: React + Vite static app served by Nginx, calls the agent API.

Note: Redis was removed; the current stack does not depend on Redis.

### Ports
- `8000`: LangGraph API (`LANGGRAPH_EXTERNAL_PORT`)
- `5432`: PostgreSQL (`POSTGRES_EXTERNAL_PORT`)
- `11434`: Ollama (`OLLAMA_EXTERNAL_PORT`)
- `3000`: UI (`UI_EXTERNAL_PORT`)

## ⚙️ Configuration

All configuration is managed through environment variables in `.env`.

### 🤖 Multi-Model AI Provider Support

The agent now supports multiple AI providers based on available API keys. Configure your preferred providers by uncommenting and setting the appropriate environment variables:

#### Model Provider Priority
```bash
# Set priority order (first available provider will be used)
MODEL_PROVIDER_PRIORITY=ollama,openai,anthropic,groq,together

# Global model parameters (applied to all providers)
MODEL_TEMPERATURE=0.7
MODEL_TOP_P=0.9
MODEL_MAX_TOKENS=500
```

#### Ollama (Local/Self-hosted)
```bash
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=phi3:mini  # Default model
# No API key required
```

**Popular Ollama Models by Size:**
- `gemma2:2b` - Minimal (2B params, ~1.4GB) - Lowest resource usage
- `phi3:mini` - Small (3.8B params, ~2.3GB) - **Default - Good balance of size/performance**
- `llama3.2:3b` - Medium (3B params, ~2GB) - Better reasoning
- `llama3.2:8b` - Large (8B params, ~4.7GB) - High performance
- `llama3.1:70b` - Very Large (70B params, ~40GB) - Maximum capability

#### OpenAI
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1
```

#### Anthropic (Claude)
```bash
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-haiku-20240307
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

#### Groq
```bash
GROQ_API_KEY=gsk_your-groq-api-key-here
GROQ_MODEL=llama3-8b-8192
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

#### Together AI
```bash
TOGETHER_API_KEY=your-together-api-key-here
TOGETHER_MODEL=meta-llama/Llama-2-7b-chat-hf
TOGETHER_BASE_URL=https://api.together.xyz/v1
```

### Database
```bash
POSTGRES_DB=langgraph
POSTGRES_USER=langgraph
POSTGRES_PASSWORD=langgraph_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URI=postgresql://langgraph:langgraph_password@postgres:5432/langgraph
```

### Ports (host)
```bash
LANGGRAPH_EXTERNAL_PORT=8000
POSTGRES_EXTERNAL_PORT=5432
OLLAMA_EXTERNAL_PORT=11434
UI_EXTERNAL_PORT=3000
```

## 🧠 Features
- **Multi-Model Support**: Supports 5 AI providers (Ollama, OpenAI, Anthropic, Groq, Together AI) with automatic failover
- **Smart Provider Selection**: Configurable priority order with automatic selection based on available API keys
- **Memory persistence**: PostgreSQL-backed LangGraph checkpointer; falls back to in-memory if DB unavailable
- **Threaded conversations**: Multiple threads keyed by `thread_id` with message history stored in DB
- **Local-first option**: Uses Ollama for completely local/offline AI inference
- **Health checks**: Container and app health endpoints
- **Centralized config**: Single `.env` for all services and AI providers
- **Runtime UI config**: UI reads `UI_API_BASE_URL` via `/config.js` generated at container startup

## 📝 API Usage

Base URL: `http://localhost:8000`

- GET `/` — Service info
- GET `/health` — Health check
- GET `/models` — Available AI providers and current configuration

- POST `/chat`
  - Body:
    ```json
    { "message": "Hello", "thread_id": "thread_123" }
    ```
    `thread_id` optional; a new one is generated if absent.
  - Response (shape):
    ```json
    { "response": "...", "thread_id": "...", "messages": [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}] }
    ```

- GET `/threads/{thread_id}/messages` — Returns stored messages for a thread.
- DELETE `/threads/{thread_id}` — Deletes a thread (endpoint exists; wiring to DB is pending, see TODO).
- GET `/threads` — Lists threads with metadata.

- POST `/invoke`
  - Body: Direct LangGraph input
    ```json
    {
      "input": {
        "messages": [{"role": "user", "content": "Hi"}],
        "thread_id": "thread_123"
      }
    }
    ```

- POST `/stream`
  - Body:
    ```json
    {
      "input": {"messages": [{"role":"user","content":"Hi"}], "thread_id": "thread_123"},
      "stream_mode": "values"
    }
    ```
  - Returns Server-Sent-Events style lines: `data: { ... }` per chunk.

## 🧩 How It Works
- `agent/src/main/app/models.py` manages multiple AI providers with automatic selection and failover
- `agent/src/main/app/graph.py` builds a `StateGraph` with a `chatbot` node that uses the model manager
- `agent/src/main/app/database.py` stores and retrieves conversation threads and messages in PostgreSQL
- `agent/src/main/main.py` exposes FastAPI routes for chat, invoke, streaming, and model information
- Docker Compose brings up Postgres, Ollama, and the agent in one network

## 🧪 Development

With Docker Compose:
```bash
# Logs
docker-compose logs -f

# Restart only the agent
docker-compose restart langgraph-agent

# Rebuild the agent after code changes
docker-compose up --build langgraph-agent

# Stop services
docker-compose down

# Stop and remove volumes (data loss)
docker-compose down -v
```

Run the agent locally (optional):
```bash
cd agent
pip install -r requirements.txt
python src/main/main.py  # listens on 8000 by default
```

UI (React + Vite):
```bash
# Build and run all services including the UI
docker-compose up --build -d

# UI becomes available at
open http://localhost:3000       # macOS
start http://localhost:3000      # Windows
xdg-open http://localhost:3000   # Linux
```

Local UI development (hot reload):
```bash
cd ui
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

UI runtime config:
```bash
# Default to relative path and proxy via Nginx
UI_API_BASE_URL=/api
# The UI container proxies /api -> http://langgraph-agent:8000
# To bypass proxy (not recommended), set UI_API_BASE_URL=http://localhost:8000
```

Run tests (agent module):
```bash
cd agent
pytest -q
```

## 🔍 Troubleshooting
- Service not starting: `docker-compose logs [service]`
- Ollama/model issues: `docker-compose logs ollama` (the service pulls `LLM_MODEL` on start)

### Ollama timeouts

If you see `Ollama request timeout` in the agent logs, the model may be cold (first run), large, or your machine is busy. You can increase the agent → Ollama timeouts via environment variables:

- `OLLAMA_CONNECT_TIMEOUT` (default 10s)
- `OLLAMA_REQUEST_TIMEOUT` (default 180s)
- `OLLAMA_RETRY_ATTEMPTS` (default 1)
- `OLLAMA_RETRY_BACKOFF` (default 3s)

Update these in your `.env` and restart the stack: `docker-compose up -d --build`.
- DB connectivity: `docker-compose exec postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- Port conflicts: change `*_EXTERNAL_PORT` values in `.env`
- Module error `ModuleNotFoundError: No module named 'langgraph.checkpoint.postgres'`:
  - The Postgres checkpointer is a separate package. Rebuild Docker (`docker-compose up --build langgraph-agent`) or install locally: `pip install langgraph-checkpoint-postgres`. The agent will fall back to in-memory if the package is missing.

## 📁 Project Structure

```
.
├─ docker-compose.yml
├─ .env.example
├─ agent/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ src/
│     ├─ main/
│     │  ├─ main.py             # FastAPI app (routes)
│     │  └─ app/
│     │     ├─ graph.py         # LangGraph + Ollama integration
│     │     └─ database.py      # Postgres persistence helpers
│     └─ test/                  # Basic tests
└─ ui/
   ├─ Dockerfile               # Build React app and serve via Nginx
   ├─ package.json             # Vite + React + TS project
   ├─ index.html               # Loads /config.js + app bundle
   ├─ docker/
   │  ├─ entrypoint.sh         # Generates /config.js from env
   │  └─ nginx.conf            # Static serving config
   └─ src/                     # React code
```

## 📌 Notes
- Redis references in earlier docs have been removed; the current implementation does not use Redis.
- The `/threads/{thread_id}` DELETE endpoint exists but currently returns a stub response; see TODO to wire it to the DB.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper configuration via `.env`
4. Test with `docker-compose up`
5. Submit a pull request

## 📄 License

[Your License Here]
