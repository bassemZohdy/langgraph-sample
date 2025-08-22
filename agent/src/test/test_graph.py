#!/usr/bin/env python3
"""
Test suite for the LangGraph agent.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the main source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main'))

from app.graph import chatbot_node, build_conversation_context, call_ollama


class TestGraphFunctions:
    """Test cases for graph functions."""

    def test_build_conversation_context_single_message(self):
        """Test context building with a single message."""
        messages = [{"role": "user", "content": "Hello"}]
        current_message = "Hello"
        
        result = build_conversation_context(messages, current_message)
        assert result == "Hello"

    def test_build_conversation_context_multiple_messages(self):
        """Test context building with multiple messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        current_message = "How are you?"
        
        result = build_conversation_context(messages, current_message)
        assert "Previous conversation:" in result
        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result
        assert "Current user message: How are you?" in result

    @patch('app.graph.requests.post')
    def test_call_ollama_success(self, mock_post):
        """Test successful Ollama API call."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": "Hello! I'm doing great."}
        mock_post.return_value = mock_response
        
        result = call_ollama("Hello, how are you?", "test_thread")
        
        assert result == "Hello! I'm doing great."
        mock_post.assert_called_once()

    @patch('app.graph.requests.post')
    def test_call_ollama_connection_error(self, mock_post):
        """Test Ollama API connection error handling."""
        # Mock connection error
        mock_post.side_effect = Exception("Connection error")
        
        result = call_ollama("Hello", "test_thread")
        
        assert "unexpected error" in result.lower()

    def test_chatbot_node_with_messages(self):
        """Test chatbot node with message history."""
        state = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "How are you?"}
            ],
            "thread_id": "test_thread"
        }
        
        with patch('app.graph.call_ollama') as mock_ollama:
            mock_ollama.return_value = "I'm doing great, thanks!"
            
            result = chatbot_node(state)
            
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0]["role"] == "assistant"
            assert result["messages"][0]["content"] == "I'm doing great, thanks!"

    def test_chatbot_node_empty_messages(self):
        """Test chatbot node with no message history."""
        state = {"messages": [], "thread_id": "test_thread"}
        
        with patch('app.graph.call_ollama') as mock_ollama:
            mock_ollama.return_value = "Hello! How can I help you?"
            
            result = chatbot_node(state)
            
            assert "messages" in result
            assert result["messages"][0]["content"] == "Hello! How can I help you?"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])