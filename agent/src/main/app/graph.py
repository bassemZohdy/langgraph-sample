"""
LangGraph OSS agent implementation with Ollama integration and PostgreSQL memory.
This is a pure open-source solution without licensing requirements.
"""

import os
import logging
from typing import Annotated, Dict, Any, List
from typing_extensions import TypedDict

import requests
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)


class State(TypedDict):
    """State definition for the conversation graph."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    thread_id: str


def chatbot_node(state: State) -> Dict[str, Any]:
    """
    Main chatbot node that processes messages using Ollama.
    
    Args:
        state: Current graph state with messages and thread_id
        
    Returns:
        Updated state with assistant response
    """
    messages = state.get("messages", [])
    thread_id = state.get("thread_id", "default")
    
    # Extract the latest user message
    if not messages:
        user_message = "Hello! How can I help you today?"
        logger.warning("No messages found, using default greeting")
    else:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            user_message = last_message.get("content", "Hello!")
        else:
            user_message = str(last_message)
    
    # Build conversation context from recent messages (last 10)
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    conversation_context = build_conversation_context(recent_messages, user_message)
    
    logger.info(f"Processing message for thread {thread_id}: {user_message[:100]}...")
    
    # Get response from Ollama
    assistant_response = call_ollama(conversation_context, thread_id)
    
    return {
        "messages": [{"role": "assistant", "content": assistant_response}]
    }


def build_conversation_context(messages: List[Dict[str, Any]], current_message: str) -> str:
    """
    Build conversation context for Ollama from message history.
    
    Args:
        messages: List of previous messages
        current_message: Current user message
        
    Returns:
        Formatted conversation context
    """
    if len(messages) <= 1:
        return current_message
    
    context = "Previous conversation:\n"
    for msg in messages[:-1]:  # All except the latest
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context += f"{role.capitalize()}: {content}\n"
    
    context += f"\nCurrent user message: {current_message}"
    context += "\n\nPlease respond naturally considering the conversation history:"
    
    return context


def call_ollama(prompt: str, thread_id: str) -> str:
    """
    Make API call to Ollama service.
    
    Args:
        prompt: The input prompt/context
        thread_id: Thread identifier for logging
        
    Returns:
        Assistant response text
    """
    # Get Ollama configuration
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "phi3:mini")
    # Timeouts and retry behavior (configurable)
    try:
        connect_timeout = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))
    except ValueError:
        connect_timeout = 10.0
    try:
        request_timeout = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "180"))
    except ValueError:
        request_timeout = 180.0
    try:
        retry_attempts = int(os.getenv("OLLAMA_RETRY_ATTEMPTS", "1"))
    except ValueError:
        retry_attempts = 1
    try:
        retry_backoff = float(os.getenv("OLLAMA_RETRY_BACKOFF", "3"))
    except ValueError:
        retry_backoff = 3.0
    
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }
        
        logger.info(
            f"Calling Ollama API for thread {thread_id} (model={model}, base={ollama_base_url}, timeout={request_timeout}s)"
        )

        last_error: Exception | None = None
        attempts = max(1, 1 + max(0, retry_attempts))
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    f"{ollama_base_url}/api/generate",
                    json=payload,
                    timeout=(connect_timeout, request_timeout),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                result = response.json()
                assistant_message = result.get(
                    "response", "I apologize, but I couldn't generate a proper response."
                )

                logger.info(f"✅ Ollama response received for thread {thread_id}")
                return assistant_message.strip()
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < attempts:
                    logger.warning(
                        f"⏳ Ollama request timed out (attempt {attempt}/{attempts}) for thread {thread_id}; retrying in {retry_backoff}s"
                    )
                    import time
                    time.sleep(retry_backoff)
                else:
                    raise

    except requests.exceptions.Timeout:
        logger.error(f"❌ Ollama request timeout for thread {thread_id}")
        return "I apologize, but my response is taking too long. Please try again."
        
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to Ollama service for thread {thread_id}")
        return "I'm currently unable to connect to the AI service. Please check if Ollama is running and try again."
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Ollama HTTP error for thread {thread_id}: {e}")
        if e.response.status_code == 404:
            return f"The AI model '{model}' is not available. Please check if the model is downloaded in Ollama."
        return f"AI service error (HTTP {e.response.status_code}). Please try again later."
        
    except Exception as e:
        logger.error(f"❌ Unexpected Ollama error for thread {thread_id}: {str(e)}")
        return f"I encountered an unexpected error. Please try again. (Error: {str(e)[:100]})"


def create_postgres_checkpointer():
    """
    Create PostgreSQL checkpointer for conversation memory.
    
    Returns:
        PostgresSaver instance or None if setup fails
    """
    try:
        # Import lazily so missing package doesn't crash service startup
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            logger.warning("LangGraph Postgres checkpointer not installed; using in-memory checkpointer.")
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver()

        database_url = os.getenv(
            "DATABASE_URI",
            "postgresql://langgraph:langgraph_password@postgres:5432/langgraph",
        )

        logger.info("🔧 Setting up PostgreSQL checkpointer...")

        # Create connection pool
        pool = SimpleConnectionPool(1, 10, database_url)

        # Initialize PostgreSQL checkpointer
        checkpointer = PostgresSaver(pool)

        # Setup database tables if they don't exist
        checkpointer.setup()

        logger.info("✅ PostgreSQL checkpointer initialized successfully")
        return checkpointer

    except Exception as e:
        logger.error(f"❌ Failed to create PostgreSQL checkpointer: {e}")
        logger.info("🔄 Falling back to in-memory checkpointer")

        # Fallback to memory saver
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


# Build the LangGraph
def create_graph() -> StateGraph:
    """
    Create and compile the conversation graph with PostgreSQL memory.
    
    Returns:
        Compiled LangGraph instance
    """
    logger.info("🔧 Building LangGraph with PostgreSQL memory...")
    
    # Create PostgreSQL checkpointer
    checkpointer = create_postgres_checkpointer()
    
    # Create graph builder
    builder = StateGraph(State)
    
    # Add nodes
    builder.add_node("chatbot", chatbot_node)
    
    # Add edges
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    
    # Compile graph with checkpointer for persistent memory
    compiled_graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("✅ LangGraph compiled successfully with memory persistence")
    return compiled_graph


# Create the global graph instance
graph = create_graph()
