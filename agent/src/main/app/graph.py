"""
LangGraph OSS agent implementation with multi-model support and PostgreSQL memory.
This is a pure open-source solution without licensing requirements.
"""

import os
import logging
from typing import Annotated, Dict, Any, List
from typing_extensions import TypedDict

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from .models import model_manager

logger = logging.getLogger(__name__)


class State(TypedDict):
    """State definition for the conversation graph."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    thread_id: str


def chatbot_node(state: State) -> Dict[str, Any]:
    """
    Main chatbot node that processes messages using available AI models.
    
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
    
    # Get response from the configured model provider
    assistant_response = model_manager.call_model(conversation_context, thread_id)
    
    # Ensure we return a clean string response
    if isinstance(assistant_response, dict):
        # If the response is a dict, extract the content
        assistant_response = assistant_response.get("content", str(assistant_response))
    elif not isinstance(assistant_response, str):
        # Convert any non-string response to string
        assistant_response = str(assistant_response)
    
    # Clean the response - this will be handled in main.py during normalization
    return {
        "messages": [{"role": "assistant", "content": assistant_response.strip()}]
    }


def build_conversation_context(messages: List[Dict[str, Any]], current_message: str) -> str:
    """
    Build conversation context for AI models with natural response instructions.
    
    Args:
        messages: List of previous messages
        current_message: Current user message
        
    Returns:
        Formatted conversation context with natural response guidelines
    """
    # Start with system instructions for natural conversation
    context = """You are a helpful AI assistant engaged in a natural conversation. Follow these guidelines:

RESPONSE STYLE:
- Respond directly and naturally, as if speaking to a friend
- Do NOT start responses with "Assistant:", "AI:", "Response:", or similar prefixes
- Do NOT mention that you are an AI, assistant, or language model unless directly asked
- Be conversational, helpful, and engaging
- Start your response immediately with the actual content

"""
    
    # Add conversation history if available
    if len(messages) > 1:
        context += "CONVERSATION HISTORY:\n"
        for msg in messages[:-1]:  # All except the latest
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                role_label = "Human" if role == "user" else "You"
                context += f"{role_label}: {content}\n"
        context += "\n"
    
    # Add current message and final instruction
    context += f"CURRENT MESSAGE: {current_message}\n\n"
    context += "Respond naturally and directly to the human's message above:"
    
    return context




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
