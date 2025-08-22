# TODO / Roadmap

Focused tasks to align code, docs, and ops. Ordered roughly by priority.

## API + Backend
- Wire DELETE `/threads/{thread_id}` to DB: call `delete_thread()` from `database.py` in the route.
- Add GET `/threads` endpoint to list threads using `get_all_threads()`.
- Add pagination/limits for thread messages (e.g., `?limit=&offset=`) to avoid large payloads.
- Improve SSE streaming headers: use `text/event-stream` and proper `retry`/heartbeat support.
- Expose model params per request on `/chat` (temperature, top_p, max_tokens) with validation.
- Add request validation and size limits to protect the service.
- Return consistent error objects across endpoints.

## Persistence
- Add DB migrations (Alembic) for schema evolution and dev/prod parity.
- Add indices for frequent lookups beyond the current ones if needed (e.g., created_at ordering).
- Make message storage incremental (append-only) instead of full-thread rewrite in `save_thread_messages`.

## Configuration
- Switch to Pydantic Settings for typed env parsing and defaults.
- Validate required env vars at startup with clear logs.
- Document connection pooling and tuneable limits.

## Reliability & Observability
- Structured JSON logging with request IDs and `thread_id` context.
- Health/Ready endpoints: add DB and Ollama dependency checks (readiness) separate from liveness.
- Add retries/backoff around Ollama calls; circuit breaker for repeated failures.

## Security
- Optional API key or token-based auth; disable on local/dev by default.
- Rate limiting (IP or token-based) on `POST` endpoints.

## Testing & CI
- Expand tests for `/chat`, `/invoke`, `/stream`, and new `/threads` endpoints.
- Add integration tests using Docker Compose in CI.
- Pin dependency versions and set up Dependabot/Renovate.

## Developer Experience
- Make a simple CLI client for local testing (Python or Node).
- Pre-commit hooks: format, lint, basic security checks.

## UI (Optional)
- Build a minimal web UI in `ui/` for chatting, viewing threads, and deleting threads.
- Add streaming UI using EventSource or Fetch Streams.

## Future Enhancements
- Multi-model routing and per-thread model selection.
- Tool use / function calling within LangGraph nodes.
- Caching of Ollama responses for repeated prompts (if beneficial).
