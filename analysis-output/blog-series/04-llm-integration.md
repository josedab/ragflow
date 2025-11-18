# LLM Integration: A Universal Abstraction Layer

**Reading time:** 10 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- How RAGFlow supports 50+ LLM providers through one interface
- The abstraction layer design and registration system
- Error handling, retry logic, and streaming
- Adding a new provider step-by-step

---

## Introduction

One of RAGFlow's strengths is its broad LLM support—over 50 providers work out of the box. This isn't just a list of API clients; it's a carefully designed abstraction that normalizes different APIs into a consistent interface.

This post explores how this abstraction works, the patterns that make it extensible, and the error handling that makes it production-ready.

---

## Architecture Overview

```
Application Code
    │
    ▼
┌─────────────────────────┐
│  get_model() Factory    │
│  - Routes by factory_name│
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
┌────────┐    ┌──────────┐
│ Direct │    │ LiteLLM  │
│ Impls  │    │  Proxy   │
└────┬───┘    └────┬─────┘
     │             │
     ▼             ▼
┌─────────┐  ┌──────────────┐
│ OpenAI  │  │ 26 providers │
│ Anthropic│ │ via LiteLLM  │
│ Zhipu   │  └──────────────┘
│ etc.    │
└─────────┘
```

---

## The Factory System

### Model Registration

Each provider class registers itself with a `_FACTORY_NAME`:

```python
# rag/llm/chat_model.py
class OpenAIChat(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        self.client = OpenAI(
            api_key=key,
            base_url=base_url or "https://api.openai.com/v1",
            timeout=600
        )
        self.model_name = model_name

class AnthropicChat(Base):
    _FACTORY_NAME = "Anthropic"

    def __init__(self, key, model_name, **kwargs):
        self.client = Anthropic(api_key=key)
        self.model_name = model_name
```

### Factory Function

```python
# rag/llm/__init__.py
def ChatModel(factory_name, **kwargs):
    """Instantiate a chat model by factory name"""
    # Direct implementations
    direct_models = {
        "OpenAI": OpenAIChat,
        "Anthropic": AnthropicChat,
        "ZHIPU-AI": ZhipuChat,
        "Azure-OpenAI": AzureChat,
        # ... 20+ direct implementations
    }

    if factory_name in direct_models:
        return direct_models[factory_name](**kwargs)

    # LiteLLM fallback for 26+ additional providers
    return LiteLLMChat(factory_name, **kwargs)
```

**Code reference:** [rag/llm/__init__.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/__init__.py)

---

## Base Chat Model

All chat models inherit from a base class that defines the interface:

```python
# rag/llm/chat_model.py
from abc import ABC, abstractmethod

class Base(ABC):
    def __init__(self):
        self.max_retries = 5
        self.base_delay = 2.0

    @abstractmethod
    def chat(self, messages, gen_conf, stream=False):
        """
        Send chat completion request.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            gen_conf: Generation config (temperature, max_tokens, etc.)
            stream: Whether to stream response

        Returns:
            If stream=False: (response_text, token_count)
            If stream=True: Generator yielding (chunk, is_done)
        """
        pass

    def _chat(self, messages, gen_conf):
        """Common implementation with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if gen_conf.get('stream', False):
                    return self._stream_chat(messages, gen_conf)
                else:
                    return self._batch_chat(messages, gen_conf)
            except Exception as e:
                if not self._should_retry(e, attempt):
                    raise
                self._wait_for_retry(attempt)
```

---

## Error Handling and Retry

### Error Classification

```python
# rag/llm/chat_model.py
class LLMErrorCode(StrEnum):
    ERROR_RATE_LIMIT = "RATE_LIMIT_EXCEEDED"
    ERROR_QUOTA = "QUOTA_EXCEEDED"
    ERROR_AUTHENTICATION = "AUTH_ERROR"
    ERROR_TIMEOUT = "TIMEOUT"
    ERROR_CONTENT_FILTER = "CONTENT_FILTERED"
    ERROR_INVALID_REQUEST = "INVALID_REQUEST"
    ERROR_MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    ERROR_SERVER = "SERVER_ERROR"
    ERROR_NETWORK = "NETWORK_ERROR"
    ERROR_CONTEXT_LENGTH = "CONTEXT_LENGTH_EXCEEDED"
    ERROR_JSON_DECODE = "JSON_DECODE_ERROR"
    ERROR_RESPONSE_FORMAT = "RESPONSE_FORMAT_ERROR"

def classify_error(e):
    """Map exception to error code"""
    msg = str(e).lower()

    if "rate limit" in msg or "rate_limit" in msg:
        return LLMErrorCode.ERROR_RATE_LIMIT
    if "quota" in msg or "insufficient" in msg or "billing" in msg:
        return LLMErrorCode.ERROR_QUOTA
    if "authentication" in msg or "api key" in msg or "unauthorized" in msg:
        return LLMErrorCode.ERROR_AUTHENTICATION
    if "timeout" in msg or "timed out" in msg:
        return LLMErrorCode.ERROR_TIMEOUT
    if "content filter" in msg or "content_filter" in msg:
        return LLMErrorCode.ERROR_CONTENT_FILTER
    if "context length" in msg or "maximum context" in msg:
        return LLMErrorCode.ERROR_CONTEXT_LENGTH

    return LLMErrorCode.ERROR_SERVER
```

### Retry Strategy

```python
def _should_retry(self, error, attempt):
    """Determine if error is retryable"""
    error_code = classify_error(error)

    # Never retry these
    non_retryable = {
        LLMErrorCode.ERROR_AUTHENTICATION,
        LLMErrorCode.ERROR_QUOTA,
        LLMErrorCode.ERROR_CONTENT_FILTER,
        LLMErrorCode.ERROR_INVALID_REQUEST,
        LLMErrorCode.ERROR_MODEL_NOT_FOUND,
    }

    if error_code in non_retryable:
        return False

    # Retry rate limits and server errors
    return attempt < self.max_retries - 1

def _wait_for_retry(self, attempt):
    """Exponential backoff with jitter"""
    delay = self.base_delay * (2 ** attempt)
    jitter = random.uniform(0.5, 1.5)
    time.sleep(delay * jitter)
```

**Code reference:** [rag/llm/chat_model.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/chat_model.py)

---

## Streaming Implementation

Streaming allows token-by-token delivery for better UX:

```python
# rag/llm/chat_model.py
class OpenAIChat(Base):
    def _stream_chat(self, messages, gen_conf):
        """Stream response tokens"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **gen_conf
        )

        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token, False

        # Final yield with complete response
        yield "", True
```

### SSE Delivery to Frontend

```python
# api/apps/dialog_app.py
@manager.route('/completion', methods=['POST'])
def completion():
    # ... setup code

    def generate():
        for token, is_done in chat_model.chat(messages, gen_conf, stream=True):
            if is_done:
                yield f"data: [DONE]\n\n"
            else:
                yield f"data: {json.dumps({'content': token})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache'}
    )
```

---

## Token Management

### Token Counting

```python
# rag/llm/chat_model.py
import tiktoken

class Base:
    def count_tokens(self, text, model=None):
        """Count tokens using tiktoken"""
        try:
            encoding = tiktoken.encoding_for_model(model or self.model_name)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def truncate_to_tokens(self, text, max_tokens):
        """Truncate text to fit token limit"""
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        return encoding.decode(tokens[:max_tokens])
```

### Context Management

```python
def prepare_messages(self, messages, max_context):
    """Ensure messages fit in context window"""
    total_tokens = sum(self.count_tokens(m['content']) for m in messages)

    if total_tokens <= max_context:
        return messages

    # Truncate from oldest messages (keep system + recent)
    system_msg = messages[0] if messages[0]['role'] == 'system' else None
    other_msgs = messages[1:] if system_msg else messages

    # Keep most recent messages that fit
    truncated = []
    remaining = max_context - (self.count_tokens(system_msg['content']) if system_msg else 0)

    for msg in reversed(other_msgs):
        msg_tokens = self.count_tokens(msg['content'])
        if remaining >= msg_tokens:
            truncated.insert(0, msg)
            remaining -= msg_tokens
        else:
            break

    return ([system_msg] if system_msg else []) + truncated
```

---

## Function Calling Support

RAGFlow supports function calling for agent workflows:

```python
# rag/llm/chat_model.py
class Base:
    def __init__(self):
        self.tools = []

    def register_tools(self, tools):
        """Register tools for function calling"""
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in tools
        ]

    def chat_with_tools(self, messages, gen_conf):
        """Chat with function calling"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.tools if self.tools else None,
            **gen_conf
        )

        # Check for tool calls
        if response.choices[0].message.tool_calls:
            return {
                "type": "tool_call",
                "calls": [
                    {
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
            }

        return {
            "type": "message",
            "content": response.choices[0].message.content
        }
```

---

## LiteLLM Integration

For providers without direct implementation, RAGFlow uses LiteLLM:

```python
# rag/llm/chat_model.py
class LiteLLMChat(Base):
    """Universal provider via LiteLLM proxy"""

    # Supported providers
    SUPPORTED = [
        "Tongyi-Qianwen", "Moonshot", "xAI", "DeepInfra",
        "Groq", "Cohere", "Gemini", "DeepSeek", "NVIDIA",
        "TogetherAI", "Ollama", "OpenRouter", "StepFun",
        "PPIO", "Upstage", "NovitaAI", "Lingyi-AI",
        "GiteeAI", "302.AI", "Bedrock", # ... and more
    ]

    def __init__(self, factory_name, key, model_name, **kwargs):
        import litellm

        self.factory_name = factory_name
        self.model_name = self._format_model_name(factory_name, model_name)
        litellm.api_key = key

    def _format_model_name(self, provider, model):
        """Format model name for LiteLLM"""
        provider_prefixes = {
            "Bedrock": "bedrock/",
            "Groq": "groq/",
            "Ollama": "ollama/",
            # ... mappings
        }
        prefix = provider_prefixes.get(provider, "")
        return f"{prefix}{model}"

    def chat(self, messages, gen_conf, stream=False):
        import litellm

        response = litellm.completion(
            model=self.model_name,
            messages=messages,
            stream=stream,
            **gen_conf
        )

        if stream:
            return self._handle_stream(response)
        return response.choices[0].message.content, response.usage.total_tokens
```

**Code reference:** [rag/llm/chat_model.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/chat_model.py)

---

## Adding a New Provider

Here's how to add support for a new LLM provider:

### Step 1: Create the Class

```python
# rag/llm/chat_model.py

class NewProviderChat(Base):
    _FACTORY_NAME = "NewProvider"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        from newprovider import NewProviderClient

        self.client = NewProviderClient(api_key=key)
        self.model_name = model_name
        self.base_url = base_url

    def chat(self, messages, gen_conf, stream=False):
        try:
            if stream:
                return self._stream_chat(messages, gen_conf)

            response = self.client.generate(
                model=self.model_name,
                messages=self._convert_messages(messages),
                **gen_conf
            )

            return response.text, response.token_count

        except Exception as e:
            error_code = classify_error(e)
            raise LLMException(error_code, str(e))

    def _stream_chat(self, messages, gen_conf):
        response = self.client.generate(
            model=self.model_name,
            messages=self._convert_messages(messages),
            stream=True,
            **gen_conf
        )

        for chunk in response:
            yield chunk.text, chunk.is_final

    def _convert_messages(self, messages):
        """Convert to provider's message format if needed"""
        return messages  # Or transform as needed
```

### Step 2: Register in Factory

```python
# rag/llm/__init__.py

# Add to the factory mapping
direct_models = {
    # ... existing providers
    "NewProvider": NewProviderChat,
}
```

### Step 3: Add UI Configuration

Update the frontend to include the new provider in LLM selection dropdowns.

---

## Embedding Models

The same pattern applies to embedding models:

```python
# rag/llm/embedding_model.py
class OpenAIEmbed(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name, **kwargs):
        self.client = OpenAI(api_key=key)
        self.model_name = model_name

    def encode(self, texts, batch_size=16):
        """Encode texts to embeddings"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch,
                encoding_format="float"
            )
            embeddings = [e.embedding for e in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    def encode_queries(self, queries):
        """Encode queries (may use different model/settings)"""
        return self.encode(queries)
```

**Code reference:** [rag/llm/embedding_model.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/embedding_model.py)

---

## Key Takeaways

1. **Factory pattern with registration** enables 50+ providers with configuration-driven selection.

2. **Error classification** allows intelligent retry strategies—retry rate limits, fail fast on auth errors.

3. **Streaming is first-class** with SSE delivery to frontend for responsive UX.

4. **Token management** includes counting, truncation, and context window management.

5. **LiteLLM fallback** provides 26+ additional providers with minimal code.

6. **Adding new providers** is straightforward—implement the base class and register.

---

## What's Next

In [Blog 5: Extending RAGFlow](./05-extending-integrating.md), we'll explore the agent workflow system—how to create custom components, integrate external tools, and build sophisticated AI workflows.

---

## Further Reading

- [RFC-0003: LLM Provider SDK Updates](../rfcs/RFC-0003-llm-provider-updates.md)
- [Dependency Graph](../initial-analysis/dependency-graph.md)
