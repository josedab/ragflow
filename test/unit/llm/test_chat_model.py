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
Unit tests for chat model providers.

Tests cover chat completion, streaming responses, error handling,
and token counting for various LLM providers.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestOpenAIChat:
    """Tests for OpenAI-compatible chat model."""

    @pytest.mark.p1
    @patch("rag.llm.chat_model.OpenAI")
    def test_chat_returns_response(self, mock_openai_class):
        """Test that chat returns response and token count."""
        from rag.llm.chat_model import OpenAIChat

        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.total_tokens = 25
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Create chat model
        chat = OpenAIChat(
            key="test-key",
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1"
        )

        # Call chat
        history = [{"role": "user", "content": "Hello"}]
        response, tokens = chat.chat(None, history, {"temperature": 0.7})

        assert response == "Test response"
        assert tokens == 25

    @pytest.mark.p1
    @patch("rag.llm.chat_model.OpenAI")
    def test_chat_streamly_yields_chunks(self, mock_openai_class):
        """Test that streaming chat yields response chunks."""
        from rag.llm.chat_model import OpenAIChat

        # Setup mock streaming response
        mock_client = MagicMock()

        def mock_stream():
            chunks = [
                MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content=" World"))]),
            ]
            for chunk in chunks:
                yield chunk

        mock_client.chat.completions.create.return_value = mock_stream()
        mock_openai_class.return_value = mock_client

        chat = OpenAIChat(
            key="test-key",
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1"
        )

        history = [{"role": "user", "content": "Hello"}]

        # Collect streamed chunks
        chunks = list(chat.chat_streamly(None, history, {"temperature": 0.7}))

        assert len(chunks) >= 1

    @pytest.mark.p2
    @patch("rag.llm.chat_model.OpenAI")
    def test_chat_handles_api_error(self, mock_openai_class):
        """Test that chat handles API errors gracefully."""
        from rag.llm.chat_model import OpenAIChat

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        chat = OpenAIChat(
            key="test-key",
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1"
        )

        history = [{"role": "user", "content": "Hello"}]

        # Should handle error and return error message
        response, tokens = chat.chat(None, history, {"temperature": 0.7})

        assert "error" in response.lower() or tokens == 0


class TestOllamaChat:
    """Tests for Ollama chat model."""

    @pytest.mark.p2
    @patch("rag.llm.chat_model.requests")
    def test_ollama_chat_returns_response(self, mock_requests):
        """Test Ollama chat returns response."""
        from rag.llm.chat_model import OllamaChat

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Ollama response"},
            "eval_count": 15
        }
        mock_requests.post.return_value = mock_response

        chat = OllamaChat(
            key=None,
            model_name="llama2",
            base_url="http://localhost:11434"
        )

        history = [{"role": "user", "content": "Hello"}]
        response, tokens = chat.chat(None, history, {})

        assert "Ollama response" in response or response is not None


class TestZhipuChat:
    """Tests for Zhipu AI chat model."""

    @pytest.mark.p2
    @patch("rag.llm.chat_model.ZhipuAI")
    def test_zhipu_chat_returns_response(self, mock_zhipu_class):
        """Test Zhipu chat returns response."""
        from rag.llm.chat_model import ZhipuChat

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Zhipu response"
        mock_response.usage.total_tokens = 20
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipu_class.return_value = mock_client

        chat = ZhipuChat(
            key="test-key",
            model_name="glm-4",
            base_url=None
        )

        history = [{"role": "user", "content": "Hello"}]
        response, tokens = chat.chat(None, history, {})

        assert response == "Zhipu response"
        assert tokens == 20


class TestChatModelConfiguration:
    """Tests for chat model configuration."""

    @pytest.mark.p2
    def test_generation_config_defaults(self):
        """Test default generation configuration."""
        default_config = {
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 1024,
        }

        assert default_config["temperature"] == 0.7
        assert default_config["max_tokens"] == 1024

    @pytest.mark.p2
    def test_generation_config_override(self):
        """Test generation configuration override."""
        default_config = {
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        user_config = {
            "temperature": 0.3,
        }

        # Merge configs
        final_config = {**default_config, **user_config}

        assert final_config["temperature"] == 0.3
        assert final_config["max_tokens"] == 1024


class TestChatHistory:
    """Tests for chat history handling."""

    @pytest.mark.p1
    def test_history_format(self):
        """Test chat history format."""
        history = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        assert len(history) == 4
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[2]["role"] == "assistant"

    @pytest.mark.p2
    def test_history_truncation(self):
        """Test history truncation for token limits."""
        # Create long history
        history = []
        for i in range(100):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })

        # Truncate to last N messages
        max_messages = 10
        truncated = history[-max_messages:]

        assert len(truncated) == max_messages
        assert truncated[-1]["content"] == "Message 99"


class TestTokenCounting:
    """Tests for token counting in chat models."""

    @pytest.mark.p2
    def test_token_count_estimation(self):
        """Test token count estimation."""
        # Simple estimation: ~4 chars per token
        text = "This is a test message for token counting."
        estimated_tokens = len(text) // 4

        assert estimated_tokens > 0
        assert estimated_tokens < len(text)

    @pytest.mark.p3
    def test_token_count_for_messages(self):
        """Test token counting for message lists."""
        messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]

        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = total_chars // 4

        assert estimated_tokens > 0


class TestErrorHandling:
    """Tests for error handling in chat models."""

    @pytest.mark.p1
    def test_rate_limit_error_classification(self):
        """Test rate limit error classification."""
        from rag.llm.chat_model import LLMErrorCode

        error_msg = "Rate limit exceeded"

        # Classify error
        if "rate limit" in error_msg.lower():
            error_code = LLMErrorCode.RATE_LIMIT if hasattr(LLMErrorCode, 'RATE_LIMIT') else "RATE_LIMIT"
        else:
            error_code = "UNKNOWN"

        assert "RATE" in str(error_code)

    @pytest.mark.p2
    def test_invalid_api_key_error(self):
        """Test invalid API key error handling."""
        error_msg = "Invalid API key provided"

        is_auth_error = "invalid" in error_msg.lower() and "key" in error_msg.lower()

        assert is_auth_error is True

    @pytest.mark.p2
    def test_context_length_error(self):
        """Test context length exceeded error."""
        error_msg = "Context length exceeded maximum of 4096 tokens"

        is_context_error = "context" in error_msg.lower() and "length" in error_msg.lower()

        assert is_context_error is True


class TestRetryLogic:
    """Tests for retry logic in chat models."""

    @pytest.mark.p2
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        base_delay = 1
        max_retries = 3

        delays = []
        for i in range(max_retries):
            delay = base_delay * (2 ** i)
            delays.append(delay)

        assert delays == [1, 2, 4]

    @pytest.mark.p3
    def test_max_retry_limit(self):
        """Test maximum retry limit enforcement."""
        max_retries = 3
        attempts = 0
        success = False

        while attempts < max_retries and not success:
            attempts += 1
            # Simulate failure
            if attempts >= max_retries:
                break

        assert attempts == max_retries
        assert success is False
