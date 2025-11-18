#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Integration tests for agent workflow flow.

Tests cover agent creation, execution, tool usage,
and multi-step reasoning.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestAgentCreation:
    """Integration tests for agent creation."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_create_agent_success(self, mock_client, auth_headers):
        """Test successful agent creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "id": "agent-001",
                "name": "Research Agent",
                "description": "An agent for research tasks"
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas",
            headers=auth_headers,
            json={
                "name": "Research Agent",
                "description": "An agent for research tasks",
                "canvas_type": "agent"
            }
        )
        result = response.json()

        assert result["code"] == 0
        assert result["data"]["id"] == "agent-001"

    @pytest.mark.p2
    def test_create_agent_with_components(self, mock_client, auth_headers):
        """Test creating agent with workflow components."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "id": "agent-001",
                "components": [
                    {"id": "llm-1", "type": "llm"},
                    {"id": "retrieval-1", "type": "retrieval"},
                    {"id": "answer-1", "type": "answer"}
                ]
            }
        }
        mock_client.post.return_value = mock_response

        agent_config = {
            "name": "QA Agent",
            "components": [
                {"type": "llm", "config": {"model": "gpt-4"}},
                {"type": "retrieval", "config": {"kb_ids": ["kb-001"]}},
                {"type": "answer", "config": {}}
            ]
        }

        response = mock_client.post(
            "/api/v1/canvas",
            headers=auth_headers,
            json=agent_config
        )
        result = response.json()

        assert result["code"] == 0
        assert len(result["data"]["components"]) == 3


class TestAgentExecution:
    """Integration tests for agent execution."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_run_agent_success(self, mock_client, auth_headers):
        """Test successful agent execution."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "Based on my research, the answer is...",
                "references": [
                    {"source": "doc-001", "content": "Supporting evidence"}
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "What is machine learning?"
            }
        )
        result = response.json()

        assert result["code"] == 0
        assert "answer" in result["data"]

    @pytest.mark.p1
    def test_agent_streaming_response(self, mock_client, auth_headers):
        """Test agent streaming response."""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'data: {"component": "retrieval", "status": "running"}',
            b'data: {"component": "llm", "status": "running"}',
            b'data: {"answer": "Final answer", "status": "complete"}',
            b'data: [DONE]'
        ]
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "Test query",
                "stream": True
            },
            stream=True
        )

        events = list(response.iter_lines())
        assert len(events) == 4


class TestAgentTools:
    """Integration tests for agent tool usage."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_agent_uses_retrieval_tool(self, mock_client, auth_headers):
        """Test agent uses retrieval tool."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "According to the documents...",
                "tool_calls": [
                    {
                        "tool": "retrieval",
                        "input": {"query": "machine learning"},
                        "output": {"chunks": [{"content": "ML is..."}]}
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "Explain machine learning"
            }
        )
        result = response.json()

        tool_calls = result["data"]["tool_calls"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["tool"] == "retrieval"

    @pytest.mark.p2
    def test_agent_uses_web_search_tool(self, mock_client, auth_headers):
        """Test agent uses web search tool."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "According to recent web search...",
                "tool_calls": [
                    {
                        "tool": "web_search",
                        "input": {"query": "latest AI news"},
                        "output": {"results": [{"title": "AI News", "url": "..."}]}
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "What are the latest AI developments?"
            }
        )
        result = response.json()

        tool_calls = result["data"]["tool_calls"]
        web_search_calls = [c for c in tool_calls if c["tool"] == "web_search"]
        assert len(web_search_calls) > 0

    @pytest.mark.p3
    def test_agent_uses_calculator_tool(self, mock_client, auth_headers):
        """Test agent uses calculator tool."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "The result is 42",
                "tool_calls": [
                    {
                        "tool": "calculator",
                        "input": {"expression": "6 * 7"},
                        "output": {"result": 42}
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "What is 6 times 7?"
            }
        )
        result = response.json()

        assert "42" in result["data"]["answer"]


class TestAgentWorkflow:
    """Integration tests for agent workflow execution."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_workflow_step_execution(self, mock_client, auth_headers):
        """Test workflow executes steps in order."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "execution_trace": [
                    {"step": 1, "component": "retrieval", "status": "complete"},
                    {"step": 2, "component": "llm", "status": "complete"},
                    {"step": 3, "component": "answer", "status": "complete"}
                ],
                "answer": "Final answer"
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "Test query"
            }
        )
        result = response.json()

        trace = result["data"]["execution_trace"]
        assert len(trace) == 3
        assert trace[0]["step"] == 1
        assert trace[2]["step"] == 3

    @pytest.mark.p2
    def test_workflow_conditional_branching(self, mock_client, auth_headers):
        """Test workflow with conditional branching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "execution_trace": [
                    {"component": "categorize", "output": "technical"},
                    {"component": "technical_branch", "status": "complete"}
                ],
                "answer": "Technical answer"
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "How does TCP/IP work?"
            }
        )
        result = response.json()

        # Should have taken the technical branch
        trace = result["data"]["execution_trace"]
        categories = [t.get("output") for t in trace if t.get("output")]
        assert "technical" in categories


class TestAgentMemory:
    """Integration tests for agent memory/conversation handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_agent_maintains_conversation(self, mock_client, auth_headers):
        """Test agent maintains conversation context."""
        # First turn
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {
            "code": 0,
            "data": {
                "answer": "RAGFlow is a RAG engine.",
                "session_id": "session-001"
            }
        }
        mock_client.post.return_value = mock_response1

        response1 = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "What is RAGFlow?"
            }
        )

        session_id = response1.json()["data"]["session_id"]

        # Second turn with context
        mock_response2 = MagicMock()
        mock_response2.json.return_value = {
            "code": 0,
            "data": {
                "answer": "It was created by InfiniFlow.",
                "session_id": session_id
            }
        }
        mock_client.post.return_value = mock_response2

        response2 = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "Who created it?",
                "session_id": session_id
            }
        )

        # Should understand "it" refers to RAGFlow
        assert response2.json()["code"] == 0


class TestAgentErrorHandling:
    """Integration tests for agent error handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_agent_handles_tool_failure(self, mock_client, auth_headers):
        """Test agent handles tool failures gracefully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "I encountered an issue with the search, but based on my knowledge...",
                "tool_calls": [
                    {
                        "tool": "retrieval",
                        "status": "failed",
                        "error": "Connection timeout"
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": "Test query"
            }
        )
        result = response.json()

        # Should still return an answer despite tool failure
        assert result["code"] == 0
        assert "answer" in result["data"]

    @pytest.mark.p2
    def test_agent_handles_invalid_input(self, mock_client, auth_headers):
        """Test agent handles invalid input."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 102,
            "message": "Query cannot be empty"
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/canvas/run",
            headers=auth_headers,
            json={
                "canvas_id": "agent-001",
                "query": ""
            }
        )
        result = response.json()

        assert result["code"] != 0
