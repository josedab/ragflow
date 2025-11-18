# RFC-0003: LLM Provider SDK Updates

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 2-3 weeks
**Priority:** P2 (Strategic)

## Summary

Update and standardize LLM provider SDKs to latest versions, improve error handling, and add support for new model capabilities.

## Motivation

Current issues:
1. **Outdated SDKs**: Some providers pinned to old versions
2. **Missing features**: No support for JSON mode, vision in chat, etc.
3. **Inconsistent error handling**: Different providers handle errors differently
4. **Security concerns**: Old versions may have vulnerabilities

## Detailed Design

### Updated Dependencies

```toml
# pyproject.toml updates
dependencies = [
    "openai>=1.50.0",        # Was >=1.45.0
    "anthropic>=0.40.0",     # Was 0.34.1
    "litellm>=1.80.0",       # Was >=1.74.15
    "groq>=0.12.0",          # Was 0.9.0
    "mistralai>=1.0.0",      # Was 0.4.2
    "cohere>=5.10.0",        # Was 5.6.2
]
```

### Enhanced Base Class

```python
# rag/llm/chat_model.py
class Base(ABC):
    # New capabilities
    supports_json_mode: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True

    def chat(self, messages, gen_conf, stream=False):
        """Enhanced chat with new features"""
        # Validate capabilities
        if gen_conf.get('response_format') == 'json' and not self.supports_json_mode:
            raise CapabilityError(f"{self.__class__.__name__} doesn't support JSON mode")

        # Handle vision messages
        if self._has_images(messages) and not self.supports_vision:
            raise CapabilityError(f"{self.__class__.__name__} doesn't support vision")

        return self._chat(messages, gen_conf, stream)

    def _has_images(self, messages):
        """Check if messages contain images"""
        for msg in messages:
            if isinstance(msg.get('content'), list):
                for item in msg['content']:
                    if item.get('type') == 'image_url':
                        return True
        return False
```

### Provider Updates

```python
# OpenAI with JSON mode and vision
class OpenAIChat(Base):
    supports_json_mode = True
    supports_vision = True
    supports_function_calling = True

    def _chat(self, messages, gen_conf, stream):
        kwargs = {
            'model': self.model_name,
            'messages': messages,
            'stream': stream,
        }

        # JSON mode
        if gen_conf.get('response_format') == 'json':
            kwargs['response_format'] = {'type': 'json_object'}

        # Temperature, etc.
        if 'temperature' in gen_conf:
            kwargs['temperature'] = gen_conf['temperature']

        return self.client.chat.completions.create(**kwargs)


# Anthropic with vision
class AnthropicChat(Base):
    supports_vision = True
    supports_json_mode = False  # Anthropic handles differently
    supports_function_calling = True

    def _chat(self, messages, gen_conf, stream):
        # Convert to Anthropic format
        system = None
        anthropic_messages = []

        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                anthropic_messages.append(self._convert_message(msg))

        return self.client.messages.create(
            model=self.model_name,
            system=system,
            messages=anthropic_messages,
            stream=stream,
            **gen_conf
        )
```

## Implementation Plan

### Phase 1: SDK Updates (Week 1)
1. Update all provider SDKs in pyproject.toml
2. Run existing tests to identify breaks
3. Fix compatibility issues

### Phase 2: Feature Enhancement (Week 2)
1. Add capability flags to all providers
2. Implement JSON mode support
3. Implement vision support
4. Update error handling

### Phase 3: Testing (Week 3)
1. Integration tests for each provider
2. Feature capability tests
3. Error handling tests
4. Performance benchmarks

## Success Criteria

- [ ] All SDKs updated to latest stable versions
- [ ] No security vulnerabilities (pip-audit clean)
- [ ] JSON mode working for supported providers
- [ ] Vision working for supported providers
- [ ] All existing tests passing

## Stakeholder Approvals

- [ ] Backend Lead
- [ ] Security Review
- [ ] QA Sign-off
