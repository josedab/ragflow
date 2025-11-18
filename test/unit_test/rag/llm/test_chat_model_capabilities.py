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

import pytest
from unittest.mock import MagicMock, patch

from rag.llm.chat_model import (
    Base,
    GptTurbo,
    AzureChat,
    ZhipuChat,
    MistralChat,
    GoogleChat,
    VolcEngineChat,
    OpenAI_APIChat,
    LiteLLMBase,
    CapabilityError,
    ERROR_PREFIX,
)


class TestCapabilityFlags:
    """Test cases for provider capability flags"""

    def test_gpt_turbo_capabilities(self):
        """Test that GptTurbo has all capabilities enabled"""
        assert GptTurbo.supports_json_mode is True
        assert GptTurbo.supports_vision is True
        assert GptTurbo.supports_function_calling is True
        assert GptTurbo.supports_streaming is True

    def test_azure_chat_capabilities(self):
        """Test that AzureChat has all capabilities enabled"""
        assert AzureChat.supports_json_mode is True
        assert AzureChat.supports_vision is True
        assert AzureChat.supports_function_calling is True
        assert AzureChat.supports_streaming is True

    def test_zhipu_chat_capabilities(self):
        """Test ZhipuChat capabilities (no JSON mode)"""
        assert ZhipuChat.supports_json_mode is False
        assert ZhipuChat.supports_vision is True
        assert ZhipuChat.supports_function_calling is True
        assert ZhipuChat.supports_streaming is True

    def test_mistral_chat_capabilities(self):
        """Test MistralChat capabilities"""
        assert MistralChat.supports_json_mode is True
        assert MistralChat.supports_vision is True
        assert MistralChat.supports_function_calling is True
        assert MistralChat.supports_streaming is True

    def test_google_chat_capabilities(self):
        """Test GoogleChat capabilities"""
        assert GoogleChat.supports_json_mode is True
        assert GoogleChat.supports_vision is True
        assert GoogleChat.supports_function_calling is True
        assert GoogleChat.supports_streaming is True

    def test_volcengine_chat_capabilities(self):
        """Test VolcEngineChat capabilities"""
        assert VolcEngineChat.supports_json_mode is True
        assert VolcEngineChat.supports_vision is True
        assert VolcEngineChat.supports_function_calling is True
        assert VolcEngineChat.supports_streaming is True

    def test_openai_api_chat_capabilities(self):
        """Test OpenAI_APIChat capabilities"""
        assert OpenAI_APIChat.supports_json_mode is True
        assert OpenAI_APIChat.supports_vision is True
        assert OpenAI_APIChat.supports_function_calling is True
        assert OpenAI_APIChat.supports_streaming is True

    def test_litellm_base_capabilities(self):
        """Test LiteLLMBase default capabilities"""
        assert LiteLLMBase.supports_json_mode is True
        assert LiteLLMBase.supports_vision is True
        assert LiteLLMBase.supports_function_calling is True
        assert LiteLLMBase.supports_streaming is True

    def test_base_default_capabilities(self):
        """Test Base class default capabilities (most disabled)"""
        assert Base.supports_json_mode is False
        assert Base.supports_vision is False
        assert Base.supports_function_calling is False
        assert Base.supports_streaming is True


class TestHasImages:
    """Test cases for _has_images helper method"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create a minimal mock for Base class testing
        with patch.object(Base, '__init__', lambda x, *args, **kwargs: None):
            self.base = Base.__new__(Base)

    def test_no_images_text_only(self):
        """Test messages with only text content"""
        messages = [
            {"role": "user", "content": "Hello, world!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert self.base._has_images(messages) is False

    def test_has_images_single_image(self):
        """Test messages with a single image"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                ],
            }
        ]
        assert self.base._has_images(messages) is True

    def test_has_images_multiple_images(self):
        """Test messages with multiple images"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Compare these images"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image1.png"}},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image2.png"}},
                ],
            }
        ]
        assert self.base._has_images(messages) is True

    def test_has_images_mixed_messages(self):
        """Test mixed messages where only some have images"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                ],
            },
            {"role": "assistant", "content": "This is an image."},
        ]
        assert self.base._has_images(messages) is True

    def test_no_images_list_content_no_image_type(self):
        """Test list content without image_url type"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ],
            }
        ]
        assert self.base._has_images(messages) is False

    def test_empty_messages(self):
        """Test empty messages list"""
        messages = []
        assert self.base._has_images(messages) is False


class TestValidateCapabilities:
    """Test cases for capability validation"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create a minimal mock for Base class testing
        with patch.object(Base, '__init__', lambda x, *args, **kwargs: None):
            self.base = Base.__new__(Base)
            self.base.supports_json_mode = False
            self.base.supports_vision = False

    def test_json_mode_not_supported(self):
        """Test that CapabilityError is raised when JSON mode is not supported"""
        messages = [{"role": "user", "content": "Hello"}]
        gen_conf = {"response_format": {"type": "json_object"}}

        with pytest.raises(CapabilityError) as excinfo:
            self.base._validate_capabilities(messages, gen_conf)

        assert "doesn't support JSON mode" in str(excinfo.value)

    def test_json_mode_supported(self):
        """Test that no error is raised when JSON mode is supported"""
        self.base.supports_json_mode = True
        messages = [{"role": "user", "content": "Hello"}]
        gen_conf = {"response_format": {"type": "json_object"}}

        # Should not raise
        self.base._validate_capabilities(messages, gen_conf)

    def test_vision_not_supported(self):
        """Test that CapabilityError is raised when vision is not supported"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                ],
            }
        ]
        gen_conf = {}

        with pytest.raises(CapabilityError) as excinfo:
            self.base._validate_capabilities(messages, gen_conf)

        assert "doesn't support vision" in str(excinfo.value)

    def test_vision_supported(self):
        """Test that no error is raised when vision is supported"""
        self.base.supports_vision = True
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                ],
            }
        ]
        gen_conf = {}

        # Should not raise
        self.base._validate_capabilities(messages, gen_conf)

    def test_no_special_capabilities_needed(self):
        """Test that no error is raised for standard text messages"""
        messages = [{"role": "user", "content": "Hello"}]
        gen_conf = {"temperature": 0.7}

        # Should not raise
        self.base._validate_capabilities(messages, gen_conf)


class TestChatMethodCapabilityValidation:
    """Test capability validation in the chat method"""

    def test_chat_returns_error_for_unsupported_json_mode(self):
        """Test that chat method returns error for unsupported JSON mode"""
        with patch.object(Base, '__init__', lambda x, *args, **kwargs: None):
            base = Base.__new__(Base)
            base.supports_json_mode = False
            base.supports_vision = False
            base.max_retries = 3

            messages = [{"role": "user", "content": "Hello"}]
            gen_conf = {"response_format": {"type": "json_object"}}

            result, token_count = base.chat(None, messages, gen_conf)

            assert ERROR_PREFIX in result
            assert "doesn't support JSON mode" in result
            assert token_count == 0

    def test_chat_returns_error_for_unsupported_vision(self):
        """Test that chat method returns error for unsupported vision"""
        with patch.object(Base, '__init__', lambda x, *args, **kwargs: None):
            base = Base.__new__(Base)
            base.supports_json_mode = False
            base.supports_vision = False
            base.max_retries = 3

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this?"},
                        {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                    ],
                }
            ]
            gen_conf = {}

            result, token_count = base.chat(None, messages, gen_conf)

            assert ERROR_PREFIX in result
            assert "doesn't support vision" in result
            assert token_count == 0


class TestCapabilityError:
    """Test cases for CapabilityError exception"""

    def test_capability_error_message(self):
        """Test CapabilityError exception message"""
        error = CapabilityError("Test error message")
        assert str(error) == "Test error message"

    def test_capability_error_inheritance(self):
        """Test CapabilityError inherits from Exception"""
        error = CapabilityError("Test")
        assert isinstance(error, Exception)
