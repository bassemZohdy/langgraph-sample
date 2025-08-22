"""
FastAPI application for LangGraph agent service.
Completely open-source solution without licensing requirements.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graph import graph
from app.database import (
    init_db,
    get_thread_messages,
    save_thread_messages,
    delete_thread as db_delete_thread,
    get_all_threads,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    messages: List[ChatMessage]


class InvokeRequest(BaseModel):
    input: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None


class InvokeResponse(BaseModel):
    output: Dict[str, Any]


class StreamRequest(BaseModel):
    input: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None
    stream_mode: Optional[str] = "values"


def _normalize_role(role: str) -> str:
    mapping = {"ai": "assistant", "human": "user"}
    return mapping.get(role, role or "assistant")


def _stringify_content(content: Any) -> str:
    """Best-effort convert message content to a string.
    - If a dict contains a 'text' field, prefer it.
    - Otherwise JSON-encode dict/list, fallback to str().
    """
    try:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content["text"]
            import json as _json
            return _json.dumps(content, ensure_ascii=False)
        if isinstance(content, (list, tuple)):
            import json as _json
            return _json.dumps(content, ensure_ascii=False)
        return str(content)
    except Exception:
        try:
            return str(content)
        except Exception:
            return ""


def _normalize_message(msg: Any) -> Dict[str, str]:
    # dict-style {role, content}
    if isinstance(msg, dict):
        role = _normalize_role(msg.get("role", "assistant"))
        content = _stringify_content(msg.get("content", ""))
        return {"role": role, "content": content}
    # LangChain BaseMessage style
    role = _normalize_role(getattr(msg, "type", "assistant"))
    content = _stringify_content(getattr(msg, "content", str(msg)))
    return {"role": role, "content": content}


def _normalize_messages(messages: List[Any]) -> List[Dict[str, str]]:
    return [_normalize_message(m) for m in messages]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("🚀 Starting LangGraph FastAPI service...")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Startup complete
    logger.info("✅ Service startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down LangGraph FastAPI service...")


# Create FastAPI app
app = FastAPI(
    title="LangGraph Agent API",
    description="Open-source LangGraph agent with Ollama integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LangGraph Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "langgraph-agent",
        "version": "1.0.0"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the agent.
    
    Args:
        request: Chat request with message and optional thread_id
        
    Returns:
        Chat response with agent reply and conversation context
    """
    try:
        # Generate thread ID if not provided
        thread_id = request.thread_id or f"thread_{os.urandom(8).hex()}"
        
        # Load conversation history from database
        conversation_history = get_thread_messages(thread_id)
        
        # Add new user message
        user_message = {"role": "user", "content": request.message}
        conversation_history.append(user_message)
        
        # Prepare graph input and config for checkpointer
        graph_input = {
            "messages": conversation_history,
            "thread_id": thread_id
        }
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Processing chat request for thread: {thread_id}")
        
        # Invoke the graph
        result = graph.invoke(graph_input, config=config)
        
        # Extract response and normalized messages
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"] or []
            normalized = _normalize_messages(messages)
            conversation_history = normalized
            if normalized:
                response_content = normalized[-1].get("content", "Sorry, no response generated.")
            else:
                response_content = "Sorry, no response generated."
        else:
            response_content = "Sorry, unexpected response format."
        
        # Save updated conversation to database
        save_thread_messages(thread_id, conversation_history)
        
        # Format response
        formatted_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in conversation_history]
        
        return ChatResponse(
            response=response_content,
            thread_id=thread_id,
            messages=formatted_messages
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/threads/{thread_id}/messages")
async def get_thread_messages_endpoint(thread_id: str):
    """Get conversation history for a thread."""
    try:
        messages = get_thread_messages(thread_id)
        formatted_messages = [
            ChatMessage(role=msg["role"], content=msg["content"]) 
            for msg in messages
        ]
        return {"thread_id": thread_id, "messages": formatted_messages}
    except Exception as e:
        logger.error(f"Error getting thread messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a conversation thread and its messages from the database."""
    try:
        db_delete_thread(thread_id)
        return {"message": f"Thread {thread_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}")


@app.get("/threads")
async def list_threads():
    """List all conversation threads with basic metadata."""
    try:
        threads = get_all_threads()
        return {"threads": threads}
    except Exception as e:
        logger.error(f"Error listing threads: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}")


@app.post("/invoke", response_model=InvokeResponse)
async def invoke_graph(request: InvokeRequest):
    """
    Invoke the graph with the provided input.
    
    Args:
        request: Invoke request with input and optional config
        
    Returns:
        Graph output
    """
    try:
        logger.info(f"Invoking graph with input: {request.input}")
        
        # Prepare config; ensure checkpointer gets a thread_id if present in input
        config = request.config or {}
        if "configurable" not in config:
            config["configurable"] = {}
        if "thread_id" in request.input and not config["configurable"].get("thread_id"):
            config["configurable"]["thread_id"] = request.input.get("thread_id")
        
        # Invoke the graph
        result = graph.invoke(request.input, config=config)
        
        return InvokeResponse(output=result)
        
    except Exception as e:
        logger.error(f"Error in invoke endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Graph invocation failed: {str(e)}")


@app.post("/stream")
async def stream_graph(request: StreamRequest):
    """
    Stream the graph execution with the provided input.
    
    Args:
        request: Stream request with input, config, and stream mode
        
    Returns:
        Streaming response with graph outputs
    """
    try:
        logger.info(f"Streaming graph with input: {request.input}")
        
        def generate_stream():
            try:
                # Prepare config; ensure checkpointer gets a thread_id if present in input
                config = request.config or {}
                if "configurable" not in config:
                    config["configurable"] = {}
                if "thread_id" in request.input and not config["configurable"].get("thread_id"):
                    config["configurable"]["thread_id"] = request.input.get("thread_id")
                
                # Stream the graph execution
                stream = graph.stream(request.input, config=config, stream_mode=request.stream_mode)
                
                for chunk in stream:
                    # Format as JSON lines for streaming
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
            except Exception as e:
                logger.error(f"Error in stream generation: {str(e)}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Graph streaming failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
