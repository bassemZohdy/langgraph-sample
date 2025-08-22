# LangGraph Agent (FastAPI + Ollama + Postgres)

A compact LangGraph application that serves a chat agent via FastAPI, uses Ollama for local LLM inference, and persists conversation state and LangGraph checkpoints in PostgreSQL. This repo is fully open source and does not require any commercial licenses.

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
- Ollama: Local LLM server; pulls and runs the model set in `LLM_MODEL` (default `phi3:mini`).
- LangGraph Agent: FastAPI app exposing chat/graph endpoints.
- UI: React + Vite static app served by Nginx, calls the agent API.

Note: Redis was removed; the current stack does not depend on Redis.

### Ports
- `8000`: LangGraph API (`LANGGRAPH_EXTERNAL_PORT`)
- `5432`: PostgreSQL (`POSTGRES_EXTERNAL_PORT`)
- `11434`: Ollama (`OLLAMA_EXTERNAL_PORT`)
- `3000`: UI (`UI_EXTERNAL_PORT`)

## ⚙️ Configuration

All configuration is managed through environment variables in `.env`.

### Core
```bash
NODE_ENV=development
LLM_MODEL=phi3:mini
OLLAMA_BASE_URL=http://ollama:11434
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
- Memory persistence: PostgreSQL-backed LangGraph checkpointer; falls back to in-memory if DB unavailable.
- Threaded conversations: Multiple threads keyed by `thread_id` with message history stored in DB.
- Local-first LLM: Uses Ollama with `LLM_MODEL` you choose.
- Health checks: Container and app health endpoints.
- Centralized config: Single `.env` for all services.
- Runtime UI config: UI reads `UI_API_BASE_URL` via `/config.js` generated at container startup.

## 📝 API Usage

Base URL: `http://localhost:8000`

- GET `/` — Service info
- GET `/health` — Health check

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
- `agent/src/main/app/graph.py` builds a `StateGraph` with a `chatbot` node that calls Ollama.
- `agent/src/main/app/database.py` stores and retrieves conversation threads and messages in PostgreSQL.
- `agent/src/main/main.py` exposes FastAPI routes for chat, invoke, and streaming.
- Docker Compose brings up Postgres, Ollama, and the agent in one network.

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
