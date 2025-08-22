"""
Database module for conversation persistence.
Uses PostgreSQL for storing conversation threads and messages.
"""

import os
import json
import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database connection URL from environment."""
    return os.getenv(
        "DATABASE_URI", 
        "postgresql://langgraph:langgraph_password@postgres:5432/langgraph"
    )


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def init_db():
    """Initialize database tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Create threads table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_threads (
                        id SERIAL PRIMARY KEY,
                        thread_id VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        id SERIAL PRIMARY KEY,
                        thread_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        message_order INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (thread_id) REFERENCES conversation_threads(thread_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_thread_id 
                    ON conversation_messages(thread_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_order 
                    ON conversation_messages(thread_id, message_order)
                """)
                
                conn.commit()
                logger.info("✅ Database tables initialized successfully")
                
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        # Don't raise here - allow service to start without DB
        pass


def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a conversation thread.
    
    Args:
        thread_id: The thread identifier
        
    Returns:
        List of message dictionaries with role and content
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT role, content, message_order
                    FROM conversation_messages 
                    WHERE thread_id = %s 
                    ORDER BY message_order ASC
                """, (thread_id,))
                
                rows = cursor.fetchall()
                return [{"role": row["role"], "content": row["content"]} for row in rows]
                
    except Exception as e:
        logger.error(f"❌ Failed to get thread messages: {e}")
        return []  # Return empty list on error


def save_thread_messages(thread_id: str, messages: List[Dict[str, Any]]):
    """
    Save conversation messages for a thread.
    
    Args:
        thread_id: The thread identifier
        messages: List of message dictionaries with role and content
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Insert thread if it doesn't exist
                cursor.execute("""
                    INSERT INTO conversation_threads (thread_id) 
                    VALUES (%s) 
                    ON CONFLICT (thread_id) DO UPDATE SET 
                    updated_at = CURRENT_TIMESTAMP
                """, (thread_id,))
                
                # Clear existing messages for this thread
                cursor.execute("""
                    DELETE FROM conversation_messages WHERE thread_id = %s
                """, (thread_id,))
                
                # Insert all messages
                for order, message in enumerate(messages):
                    cursor.execute("""
                        INSERT INTO conversation_messages 
                        (thread_id, role, content, message_order)
                        VALUES (%s, %s, %s, %s)
                    """, (thread_id, message["role"], message["content"], order))
                
                conn.commit()
                logger.info(f"✅ Saved {len(messages)} messages for thread {thread_id}")
                
    except Exception as e:
        logger.error(f"❌ Failed to save thread messages: {e}")
        # Don't raise - allow conversation to continue without persistence


def delete_thread(thread_id: str):
    """
    Delete a conversation thread and all its messages.
    
    Args:
        thread_id: The thread identifier
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM conversation_threads WHERE thread_id = %s
                """, (thread_id,))
                
                conn.commit()
                logger.info(f"✅ Deleted thread {thread_id}")
                
    except Exception as e:
        logger.error(f"❌ Failed to delete thread: {e}")
        raise


def get_all_threads() -> List[Dict[str, Any]]:
    """
    Get all conversation threads.
    
    Returns:
        List of thread information
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT thread_id, created_at, updated_at,
                           (SELECT COUNT(*) FROM conversation_messages 
                            WHERE conversation_messages.thread_id = conversation_threads.thread_id) as message_count
                    FROM conversation_threads 
                    ORDER BY updated_at DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
    except Exception as e:
        logger.error(f"❌ Failed to get threads: {e}")
        return []


# Health check function
def check_db_health() -> bool:
    """Check if database is accessible."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False