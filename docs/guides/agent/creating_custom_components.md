# Creating Custom Components

This guide explains how to create custom components for RAGFlow's agent system using the standardized interface (RFC-0004).

## Overview

RAGFlow's component system allows you to create reusable, typed components for agent workflows. The standardized interface provides:

- **Pydantic-validated inputs and outputs**: Type safety and automatic validation
- **JSON schema generation**: Auto-generated UI forms
- **Plugin system support**: Easy distribution as third-party packages

## Basic Structure

Every standardized component consists of four parts:

1. **Input Schema**: Defines what the component accepts
2. **Output Schema**: Defines what the component produces
3. **Config Schema**: Defines configuration parameters
4. **Component Class**: The main implementation

## Quick Start

Here's a minimal example:

```python
from pydantic import Field
from agent.component.base import (
    StandardizedComponentBase,
    ComponentInput,
    ComponentOutput,
    ComponentConfig,
)

# 1. Define input schema
class GreetingInput(ComponentInput):
    name: str = Field(..., description="Name to greet")

# 2. Define output schema
class GreetingOutput(ComponentOutput):
    message: str = Field(default="", description="Greeting message")

# 3. Define config schema
class GreetingConfig(ComponentConfig):
    greeting_style: str = Field(default="formal", description="Style of greeting")

# 4. Implement component
class GreetingComponent(StandardizedComponentBase):
    component_name = "Greeting"
    component_version = "1.0.0"
    component_description = "Generate personalized greetings"

    input_schema = GreetingInput
    output_schema = GreetingOutput
    config_schema = GreetingConfig

    def run(self, inputs: GreetingInput) -> GreetingOutput:
        if self.config.greeting_style == "formal":
            message = f"Good day, {inputs.name}."
        else:
            message = f"Hey {inputs.name}!"

        return GreetingOutput(message=message)
```

## Detailed Guide

### Defining Input Schemas

Use Pydantic models with Field descriptors:

```python
from typing import List, Optional
from pydantic import Field

class MyInput(ComponentInput):
    # Required field
    query: str = Field(..., description="Search query", min_length=1)

    # Optional field with default
    limit: int = Field(default=10, ge=1, le=100, description="Max results")

    # List field
    tags: List[str] = Field(default_factory=list, description="Filter tags")

    # Optional field
    context: Optional[str] = Field(default=None, description="Additional context")
```

### Defining Output Schemas

Similarly, define what your component produces:

```python
class MyOutput(ComponentOutput):
    results: List[dict] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, description="Total matches")
    error_message: Optional[str] = Field(default=None, description="Error if any")
```

### Defining Config Schemas

Configuration inherits from ComponentConfig which provides common options:

```python
class MyConfig(ComponentConfig):
    # Your custom config options
    api_key: str = Field(default="", description="API key for external service")
    timeout: float = Field(default=30.0, ge=0, description="Request timeout")

    # Inherited from ComponentConfig:
    # - description: str
    # - max_retries: int
    # - delay_after_error: float
    # - exception_method: Optional[str]
    # - exception_default_value: Optional[str]
    # - exception_goto: Optional[str]
```

### Implementing the Component

```python
class MyComponent(StandardizedComponentBase):
    # Required metadata
    component_name = "MyComponent"      # Unique identifier
    component_version = "1.0.0"         # Semantic version
    component_description = "What it does"  # Brief description

    # Schema definitions
    input_schema = MyInput
    output_schema = MyOutput
    config_schema = MyConfig

    def run(self, inputs: MyInput) -> MyOutput:
        # Check for cancellation (important for long operations)
        if self.check_if_canceled("processing"):
            return MyOutput()

        # Access config
        timeout = self.config.timeout
        api_key = self.config.api_key

        # Process inputs
        results = self._do_search(inputs.query, inputs.limit)

        # Return typed output
        return MyOutput(
            results=results,
            total=len(results)
        )

    def _do_search(self, query: str, limit: int) -> List[dict]:
        # Implementation details
        pass

    def thoughts(self) -> str:
        """Optional: Return status message for UI."""
        return "Searching for relevant results..."
```

## Advanced Features

### Accessing Variables from Canvas

Components can access variables from upstream components:

```python
def run(self, inputs):
    # Get variable from another component
    upstream_result = self.get_variable_value("component_id@output_name")

    # Get system variables
    query = self.get_variable_value("sys.query")

    # Get environment variables
    api_url = self.get_variable_value("env.API_URL")
```

### Error Handling with Retries

The base class handles retries automatically based on config:

```python
class ResilientConfig(ComponentConfig):
    max_retries: int = 3
    delay_after_error: float = 1.0

# In your component, just raise exceptions - retries are automatic
def run(self, inputs):
    response = external_api_call()
    if not response.ok:
        raise Exception(f"API error: {response.status}")
    return MyOutput(...)
```

### Cancellation Handling

Always check for cancellation in long-running operations:

```python
def run(self, inputs):
    results = []
    for item in inputs.items:
        if self.check_if_canceled("processing items"):
            return MyOutput(results=results)

        result = self._process_item(item)
        results.append(result)

    return MyOutput(results=results)
```

### Custom Validation

Add custom validation in the run method:

```python
def run(self, inputs):
    # Custom validation
    if not self.config.api_key:
        raise ValueError("API key is required")

    if inputs.limit > 1000:
        inputs.limit = 1000  # Cap the limit

    # ... rest of implementation
```

## Creating a Plugin Package

To distribute your component as a pip-installable package:

### 1. Project Structure

```
ragflow-component-mycomponent/
├── setup.py
├── ragflow_mycomponent/
│   ├── __init__.py
│   └── component.py
└── README.md
```

### 2. setup.py

```python
from setuptools import setup, find_packages

setup(
    name="ragflow-component-mycomponent",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0",
    ],
    entry_points={
        'ragflow.components': [
            'MyComponent = ragflow_mycomponent:MyComponent',
        ],
    },
)
```

### 3. Component Module

```python
# ragflow_mycomponent/__init__.py
from .component import MyComponent, MyInput, MyOutput, MyConfig

__all__ = ['MyComponent', 'MyInput', 'MyOutput', 'MyConfig']
```

### 4. Install and Use

```bash
pip install ragflow-component-mycomponent
```

The component will be automatically discovered by RAGFlow's plugin system.

## Registering Components Manually

You can also register components programmatically:

```python
from agent.plugins import register_component, plugin_manager

# Register a single component
register_component(MyComponent)

# Discover all installed plugins
plugin_manager.discover_plugins()

# List all available components
schemas = plugin_manager.list_components()
```

## Schema Generation for UI

The standardized interface automatically generates JSON schemas for UI:

```python
# Get component schema
schema = MyComponent.get_schema()
print(schema)
# {
#     "name": "MyComponent",
#     "version": "1.0.0",
#     "description": "...",
#     "inputs": { ... JSON Schema ... },
#     "outputs": { ... JSON Schema ... },
#     "config": { ... JSON Schema ... }
# }
```

## Best Practices

1. **Use descriptive field names**: Make inputs/outputs self-documenting
2. **Add Field descriptions**: They appear in auto-generated UI
3. **Set sensible defaults**: Reduce required configuration
4. **Validate early**: Catch errors before expensive operations
5. **Check cancellation**: Especially in loops and before external calls
6. **Version your components**: Follow semantic versioning
7. **Document with docstrings**: Explain what the component does

## Testing Your Component

```python
import pytest
from unittest.mock import MagicMock, patch

def test_my_component():
    # Create mock canvas
    mock_canvas = MagicMock()
    mock_canvas.is_canceled.return_value = False

    # Create component
    with patch('agent.component.base.Graph', MagicMock):
        component = MyComponent(
            mock_canvas,
            "test-id",
            {"api_key": "test-key"}
        )

    # Test invocation
    result = component.invoke(query="test", limit=5)

    assert "results" in result
    assert result["total"] >= 0
```

## Migration from Legacy Interface

If you have components using the old `_invoke()` method, here's how to migrate:

### Before (Legacy)

```python
class OldComponent(ComponentBase):
    def _invoke(self, **kwargs):
        text = self.get_input("text")
        result = process(text)
        self._output = {"result": result}
```

### After (Standardized)

```python
class NewComponent(StandardizedComponentBase):
    input_schema = MyInput
    output_schema = MyOutput
    config_schema = MyConfig

    def run(self, inputs: MyInput) -> MyOutput:
        result = process(inputs.text)
        return MyOutput(result=result)
```

## Examples

See the following files for complete examples:

- `agent/component/standardized/retrieval.py` - Knowledge base retrieval
- `test/unit_test/agent/test_standardized_components.py` - Test patterns

## API Reference

### StandardizedComponentBase

| Method | Description |
|--------|-------------|
| `run(inputs)` | Main execution method (implement this) |
| `invoke(**kwargs)` | Entry point with error handling |
| `validate_inputs(dict)` | Convert dict to typed input |
| `get_output()` | Get typed output object |
| `get_output_dict()` | Get output as dictionary |
| `check_if_canceled(msg)` | Check cancellation status |
| `get_variable_value(expr)` | Get canvas variable |
| `get_schema()` | Get JSON schema (class method) |
| `thoughts()` | Return status message |

### ComponentConfig Base Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | str | "" | Component description |
| `max_retries` | int | 0 | Retry attempts |
| `delay_after_error` | float | 2.0 | Delay between retries |
| `exception_method` | str | None | Exception handling |
| `exception_default_value` | str | None | Default on error |
| `exception_goto` | str | None | Jump to on error |

## Troubleshooting

### Component not found

Make sure the entry point is correctly defined in setup.py and the package is installed.

### Validation errors

Check that your input data matches the schema. Pydantic provides detailed error messages.

### Cancellation not working

Ensure you call `check_if_canceled()` in loops and before long operations.

## Getting Help

- GitHub Issues: https://github.com/infiniflow/ragflow/issues
- Documentation: https://ragflow.io/docs
