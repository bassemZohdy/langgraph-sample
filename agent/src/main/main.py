"""
FastAPI application for LangGraph agent service.
Completely open-source solution without licensing requirements.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graph import graph, initialize_react_state
from app.database import (
    init_db,
    get_thread_messages,
    save_thread_messages,
    delete_thread as db_delete_thread,
    get_all_threads,
    save_document_embedding,
    search_similar_documents,
    get_document_by_id,
    delete_document_embedding,
    list_documents,
)
from app.models import model_manager
from app.embeddings import embedding_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    react_settings: Optional[Dict[str, Any]] = None


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


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str
    chunks_created: int
    message: str


class DocumentSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.7


class DocumentSearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    count: int


def _normalize_role(role: str) -> str:
    mapping = {"ai": "assistant", "human": "user"}
    return mapping.get(role, role or "assistant")


def _clean_assistant_response(content: str) -> str:
    """Lightweight fallback cleanup for responses that still have robotic prefixes."""
    if not content or not isinstance(content, str):
        return content
    
    # Minimal cleanup - only remove the most common prefixes as fallback
    prefixes_to_remove = [
        "assistant:",
        "ai:",
        "response:",
        "assistant response:",
    ]
    
    cleaned = content.strip()
    
    # Remove prefixes (case insensitive) - only as fallback
    for prefix in prefixes_to_remove:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
            break  # Only remove one prefix
    
    # Ensure proper capitalization
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    return cleaned


def _stringify_content(content: Any) -> str:
    """Best-effort convert message content to a string.
    - Extract actual text content from complex objects.
    - Handle LangChain message objects properly.
    """
    try:
        if isinstance(content, str):
            return content
        
        if isinstance(content, dict):
            # Check for common content fields in order of preference
            for field in ["content", "text", "message"]:
                if field in content and isinstance(content[field], str):
                    return content[field]
            
            # If it looks like a LangChain message with metadata, extract just the content
            if "content" in content and isinstance(content["content"], str):
                return content["content"]
            
            # Fallback: if content has any string value, use it
            for value in content.values():
                if isinstance(value, str) and len(value.strip()) > 0:
                    return value
                    
        # Handle list of content blocks (some APIs return this)
        if isinstance(content, (list, tuple)) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict) and "text" in first_item:
                return first_item["text"]
            elif isinstance(first_item, str):
                return first_item
        
        # Last resort: convert to string, but avoid showing metadata
        content_str = str(content)
        # If it looks like a JSON object, don't return it
        if content_str.startswith("{") and "additional_kwargs" in content_str:
            return "Error: Could not extract message content"
        
        return content_str
    except Exception:
        return "Error: Could not parse message content"


def _normalize_message(msg: Any) -> Dict[str, str]:
    # dict-style {role, content}
    if isinstance(msg, dict):
        role = _normalize_role(msg.get("role", "assistant"))
        content = _stringify_content(msg.get("content", ""))
        return {"role": role, "content": content}
    
    # LangChain BaseMessage style - check for both 'type' and 'role' attributes
    if hasattr(msg, 'type'):
        role = _normalize_role(getattr(msg, "type", "assistant"))
    elif hasattr(msg, 'role'):
        role = _normalize_role(getattr(msg, "role", "assistant"))
    else:
        role = "assistant"
    
    # Extract content from LangChain message object
    if hasattr(msg, 'content'):
        content = _stringify_content(getattr(msg, "content", ""))
    else:
        content = _stringify_content(str(msg))
    
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


@app.get("/models")
async def get_available_models():
    """Get information about available model providers."""
    try:
        providers = model_manager.get_available_providers()
        primary_provider = model_manager.get_primary_provider()
        
        return {
            "providers": providers,
            "primary_provider": primary_provider.value if primary_provider else None,
            "total_providers": len(providers)
        }
    except Exception as e:
        logger.error(f"Error getting model information: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get model information: {str(e)}")


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
        prior_history = get_thread_messages(thread_id)

        # Add new user message
        user_message = {"role": "user", "content": request.message}
        working_history = [*prior_history, user_message]

        # Initialize ReAct state with user settings
        react_state = initialize_react_state(working_history, thread_id, request.react_settings)
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"Processing ReAct chat request for thread: {thread_id}")

        # Invoke the ReAct graph with higher recursion limit
        config["recursion_limit"] = 50  # Increase from default 25 to 50
        result = graph.invoke(react_state, config=config)

        # Extract assistant response from ReAct result
        response_content = "Sorry, unexpected response format."
        
        # Check if this is a ReAct result with reasoning steps
        if isinstance(result, dict):
            if "final_answer" in result:
                # ReAct agent result with reasoning steps
                react_response = {
                    "final_answer": result.get("final_answer", "No response generated"),
                    "reasoning_steps": result.get("reasoning_steps", []),
                    "tool_results": result.get("tool_results", []),
                    "current_step": result.get("current_step", 0)
                }
                # Return structured ReAct data as JSON for UI to parse
                response_content = json.dumps(react_response)
            elif "messages" in result:
                # Fallback to regular message format
                normalized = _normalize_messages(result["messages"] or [])
                if normalized:
                    raw_content = normalized[-1].get("content", response_content)
                    response_content = _clean_assistant_response(raw_content)
            else:
                # Direct content
                response_content = str(result.get("content", result))

        # Build final updated history explicitly to ensure DB count is correct
        updated_history = [*working_history, {"role": "assistant", "content": response_content}]

        # Save updated conversation to database
        save_thread_messages(thread_id, updated_history)

        # Format response
        formatted_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in updated_history]

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
        
        # Initialize ReAct state if needed
        if "messages" in request.input and "thread_id" in request.input:
            react_state = initialize_react_state(request.input["messages"], request.input["thread_id"])
        else:
            react_state = request.input
        
        # Invoke the graph with higher recursion limit
        config["recursion_limit"] = 50  # Increase from default 25 to 50
        result = graph.invoke(react_state, config=config)
        
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
                
                # Initialize ReAct state if needed for streaming
                if "messages" in request.input and "thread_id" in request.input:
                    react_state = initialize_react_state(request.input["messages"], request.input["thread_id"])
                else:
                    react_state = request.input
                
                # Stream the graph execution
                stream = graph.stream(react_state, config=config, stream_mode=request.stream_mode)
                
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


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document and create embeddings for vector similarity search.
    
    Args:
        file: The uploaded file
        
    Returns:
        Upload response with processing details
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        file_content = await file.read()
        content_type = file.content_type or 'application/octet-stream'
        
        # Generate document ID
        import hashlib
        content_hash = hashlib.md5(file_content).hexdigest()
        document_id = f"doc_{content_hash}_{int(os.urandom(4).hex(), 16)}"
        
        logger.info(f"Processing document upload: {file.filename} ({content_type})")
        
        # Process document and create embeddings
        processed_chunks = embedding_service.process_document(
            document_id=document_id,
            filename=file.filename,
            file_content=file_content,
            content_type=content_type,
            metadata={
                'upload_timestamp': 'now()',
                'file_hash': content_hash
            }
        )
        
        if not processed_chunks:
            raise HTTPException(status_code=500, detail="Failed to process document")
        
        # Save chunks to database
        saved_count = 0
        for chunk_data in processed_chunks:
            try:
                save_document_embedding(
                    document_id=chunk_data['document_id'],
                    filename=chunk_data['filename'],
                    content_type=chunk_data['content_type'],
                    content=chunk_data['content'],
                    embedding=chunk_data['embedding'],
                    metadata=chunk_data['metadata']
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save chunk {chunk_data['document_id']}: {e}")
                continue
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            content_type=content_type,
            chunks_created=saved_count,
            message=f"Successfully processed {file.filename} into {saved_count} searchable chunks"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@app.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    """
    Search documents using vector similarity.
    
    Args:
        request: Search request with query and parameters
        
    Returns:
        Search results with similarity scores
    """
    try:
        logger.info(f"Searching documents for query: {request.query[:100]}...")
        
        # Perform similarity search
        results = embedding_service.search_similar_content(
            query=request.query,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        return DocumentSearchResponse(
            query=request.query,
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")


@app.get("/documents")
async def list_all_documents(limit: int = 100, offset: int = 0):
    """
    List all uploaded documents with pagination.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        List of document information
    """
    try:
        documents = list_documents(limit=limit, offset=offset)
        return {"documents": documents, "count": len(documents)}
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """
    Get a specific document by ID.
    
    Args:
        document_id: The document identifier
        
    Returns:
        Document data
    """
    try:
        document = get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its embeddings.
    
    Args:
        document_id: The document identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        success = delete_document_embedding(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


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
