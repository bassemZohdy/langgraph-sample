#!/usr/bin/env python3
"""
Test suite for the FastAPI application.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Add the main source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main'))

from main import app

# Create test client
client = TestClient(app)


class TestAPI:
    """Test cases for the FastAPI endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "LangGraph Agent API"
        assert response.json()["status"] == "running"

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "langgraph-agent"

    @patch('main.get_thread_messages')
    @patch('main.save_thread_messages')
    @patch('main.graph.invoke')
    def test_chat_endpoint_success(self, mock_invoke, mock_save, mock_get):
        """Test successful chat endpoint."""
        # Mock database functions
        mock_get.return_value = []
        mock_save.return_value = None
        
        # Mock graph response
        mock_invoke.return_value = {
            "messages": [{"role": "assistant", "content": "Hello! How can I help you?"}]
        }
        
        response = client.post("/chat", json={
            "message": "Hello",
            "thread_id": "test_thread"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello! How can I help you?"
        assert data["thread_id"] == "test_thread"
        assert len(data["messages"]) >= 1

    def test_chat_endpoint_missing_message(self):
        """Test chat endpoint with missing message."""
        response = client.post("/chat", json={})
        assert response.status_code == 422  # Validation error

    @patch('main.get_thread_messages')
    def test_get_thread_messages_endpoint(self, mock_get):
        """Test get thread messages endpoint."""
        # Mock database response
        mock_get.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        response = client.get("/threads/test_thread/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test_thread"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_delete_thread_endpoint(self):
        """Test delete thread endpoint."""
        response = client.delete("/threads/test_thread")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])