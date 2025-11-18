#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
Unit tests for the standardized component system (RFC-0004).

Tests cover:
- Base class functionality
- Pydantic schema validation
- Plugin manager
- Component registration
- Schema generation
"""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import Field, ValidationError

from agent.component.base import (
    ComponentInput,
    ComponentOutput,
    ComponentConfig,
    StandardizedComponentBase,
)
from agent.plugins import (
    PluginManager,
    plugin_manager,
    register_component,
    get_component,
    list_components,
)


# =============================================================================
# Test Fixtures and Helper Classes
# =============================================================================

class MockCanvas:
    """Mock canvas/graph for testing components."""

    def __init__(self):
        self.task_id = "test-task-123"
        self._canceled = False
        self._variables = {}
        self._tenant_id = "test-tenant"

    def is_canceled(self):
        return self._canceled

    def get_variable_value(self, expression):
        return self._variables.get(expression)

    def set_variable(self, key, value):
        self._variables[key] = value

    def get_tenant_id(self):
        return self._tenant_id


# Example component for testing
class TestInput(ComponentInput):
    """Test input schema."""
    text: str = Field(..., description="Input text", min_length=1)
    count: int = Field(default=1, ge=0, description="Count value")


class TestOutput(ComponentOutput):
    """Test output schema."""
    result: str = Field(default="", description="Result text")
    processed_count: int = Field(default=0, description="Processed count")


class TestConfig(ComponentConfig):
    """Test configuration schema."""
    prefix: str = Field(default="", description="Prefix to add")
    uppercase: bool = Field(default=False, description="Convert to uppercase")


class ExampleComponent(StandardizedComponentBase):
    """Example component for testing."""

    component_name = "ExampleComponent"
    component_version = "1.0.0"
    component_description = "An example test component"

    input_schema = TestInput
    output_schema = TestOutput
    config_schema = TestConfig

    def run(self, inputs: TestInput) -> TestOutput:
        result = inputs.text
        if self.config.prefix:
            result = self.config.prefix + result
        if self.config.uppercase:
            result = result.upper()

        return TestOutput(
            result=result,
            processed_count=inputs.count
        )


# =============================================================================
# Tests for Pydantic Schemas
# =============================================================================

class TestComponentSchemas:
    """Tests for Pydantic-based component schemas."""

    def test_component_input_valid(self):
        """Test valid component input."""
        input_data = TestInput(text="hello", count=5)
        assert input_data.text == "hello"
        assert input_data.count == 5

    def test_component_input_defaults(self):
        """Test component input with defaults."""
        input_data = TestInput(text="hello")
        assert input_data.count == 1

    def test_component_input_validation_error(self):
        """Test component input validation."""
        with pytest.raises(ValidationError):
            TestInput(text="")  # min_length=1 violated

    def test_component_output_defaults(self):
        """Test component output with defaults."""
        output = TestOutput()
        assert output.result == ""
        assert output.processed_count == 0

    def test_component_config_validation(self):
        """Test component config validation."""
        config = TestConfig(prefix=">>", uppercase=True)
        assert config.prefix == ">>"
        assert config.uppercase is True

    def test_component_config_extra_fields(self):
        """Test that extra fields are allowed."""
        config = TestConfig(prefix="test", extra_field="allowed")
        assert config.prefix == "test"
        assert config.extra_field == "allowed"


# =============================================================================
# Tests for StandardizedComponentBase
# =============================================================================

class TestStandardizedComponentBase:
    """Tests for the standardized component base class."""

    @pytest.fixture
    def mock_canvas(self):
        """Create a mock canvas."""
        return MockCanvas()

    @pytest.fixture
    def component(self, mock_canvas):
        """Create a test component instance."""
        with patch('agent.component.base.Graph', MockCanvas):
            return ExampleComponent(
                mock_canvas,
                "test-component-id",
                {"prefix": ">>", "uppercase": False}
            )

    def test_component_initialization(self, component):
        """Test component initialization."""
        assert component.component_name == "ExampleComponent"
        assert component.config.prefix == ">>"
        assert component.config.uppercase is False

    def test_component_run(self, component):
        """Test component run method."""
        inputs = TestInput(text="hello", count=3)
        output = component.run(inputs)

        assert output.result == ">>hello"
        assert output.processed_count == 3

    def test_component_invoke(self, component):
        """Test component invoke method."""
        result = component.invoke(text="world", count=5)

        assert result["result"] == ">>world"
        assert result["processed_count"] == 5
        assert "_elapsed_time" in result
        assert "_created_time" in result

    def test_component_validate_inputs(self, component):
        """Test input validation."""
        inputs = component.validate_inputs({"text": "test", "count": 10})
        assert isinstance(inputs, TestInput)
        assert inputs.text == "test"
        assert inputs.count == 10

    def test_component_invoke_validation_error(self, component):
        """Test invoke with invalid inputs."""
        result = component.invoke(text="", count=1)

        assert "_ERROR" in result
        assert "at least 1" in result["_ERROR"] or "min_length" in result["_ERROR"]

    def test_component_get_schema(self):
        """Test schema generation."""
        schema = ExampleComponent.get_schema()

        assert schema["name"] == "ExampleComponent"
        assert schema["version"] == "1.0.0"
        assert schema["description"] == "An example test component"
        assert "inputs" in schema
        assert "outputs" in schema
        assert "config" in schema

        # Check input schema
        assert "properties" in schema["inputs"]
        assert "text" in schema["inputs"]["properties"]

    def test_component_cancellation(self, mock_canvas, component):
        """Test component cancellation."""
        mock_canvas._canceled = True

        assert component.check_if_canceled("test") is True
        assert component._error == "Task has been canceled"

    def test_component_get_output_dict(self, component):
        """Test get_output_dict method."""
        inputs = TestInput(text="test", count=1)
        component._output = component.run(inputs)
        component._error = None
        component._created_time = 1000.0
        component._elapsed_time = 0.5

        result = component.get_output_dict()

        assert result["result"] == ">>test"
        assert result["processed_count"] == 1
        assert result["_created_time"] == 1000.0
        assert result["_elapsed_time"] == 0.5

    def test_component_retry_logic(self, mock_canvas):
        """Test retry logic on failure."""

        class FailingComponent(StandardizedComponentBase):
            component_name = "FailingComponent"
            attempt_count = 0

            input_schema = TestInput
            output_schema = TestOutput
            config_schema = TestConfig

            def run(self, inputs):
                FailingComponent.attempt_count += 1
                if FailingComponent.attempt_count < 3:
                    raise Exception("Temporary failure")
                return TestOutput(result="success")

        with patch('agent.component.base.Graph', MockCanvas):
            component = FailingComponent(
                mock_canvas,
                "test-id",
                {"max_retries": 2, "delay_after_error": 0.01}
            )

        FailingComponent.attempt_count = 0
        result = component.invoke(text="test")

        assert result["result"] == "success"
        assert FailingComponent.attempt_count == 3


# =============================================================================
# Tests for PluginManager
# =============================================================================

class TestPluginManager:
    """Tests for the plugin manager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh plugin manager."""
        return PluginManager()

    def test_register_component(self, manager):
        """Test component registration."""
        manager.register(ExampleComponent)

        assert manager.has("ExampleComponent")
        assert manager.get("ExampleComponent") == ExampleComponent

    def test_register_invalid_component(self, manager):
        """Test registration of invalid component."""
        class NotAComponent:
            pass

        with pytest.raises(ValueError):
            manager.register(NotAComponent)

    def test_register_non_class(self, manager):
        """Test registration of non-class."""
        with pytest.raises(TypeError):
            manager.register("not a class")

    def test_unregister_component(self, manager):
        """Test component unregistration."""
        manager.register(ExampleComponent)
        assert manager.unregister("ExampleComponent") is True
        assert manager.has("ExampleComponent") is False

    def test_unregister_nonexistent(self, manager):
        """Test unregistering nonexistent component."""
        assert manager.unregister("NonExistent") is False

    def test_get_unknown_component(self, manager):
        """Test getting unknown component."""
        with pytest.raises(KeyError):
            manager.get("Unknown")

    def test_get_or_none(self, manager):
        """Test get_or_none method."""
        manager.register(ExampleComponent)

        assert manager.get_or_none("ExampleComponent") == ExampleComponent
        assert manager.get_or_none("Unknown") is None

    def test_list_components(self, manager):
        """Test listing components."""
        manager.register(ExampleComponent)

        schemas = manager.list_components()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "ExampleComponent"

    def test_list_names(self, manager):
        """Test listing component names."""
        manager.register(ExampleComponent)

        names = manager.list_names()
        assert "ExampleComponent" in names

    def test_get_all(self, manager):
        """Test getting all components."""
        manager.register(ExampleComponent)

        all_components = manager.get_all()
        assert "ExampleComponent" in all_components

    def test_clear(self, manager):
        """Test clearing all components."""
        manager.register(ExampleComponent)
        manager.clear()

        assert len(manager.list_names()) == 0

    def test_overwrite_warning(self, manager, caplog):
        """Test warning when overwriting component."""
        import logging
        caplog.set_level(logging.WARNING)

        manager.register(ExampleComponent)
        manager.register(ExampleComponent)

        assert "Overwriting component" in caplog.text


# =============================================================================
# Tests for Global Plugin Manager Functions
# =============================================================================

class TestGlobalPluginFunctions:
    """Tests for global plugin manager convenience functions."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up global manager before and after each test."""
        plugin_manager.clear()
        yield
        plugin_manager.clear()

    def test_register_component_function(self):
        """Test global register_component function."""
        register_component(ExampleComponent)
        assert plugin_manager.has("ExampleComponent")

    def test_get_component_function(self):
        """Test global get_component function."""
        register_component(ExampleComponent)
        component = get_component("ExampleComponent")
        assert component == ExampleComponent

    def test_list_components_function(self):
        """Test global list_components function."""
        register_component(ExampleComponent)
        schemas = list_components()
        assert len(schemas) == 1


# =============================================================================
# Tests for Component Schema Generation
# =============================================================================

class TestSchemaGeneration:
    """Tests for JSON schema generation."""

    def test_input_schema_properties(self):
        """Test input schema has correct properties."""
        schema = TestInput.model_json_schema()

        assert "properties" in schema
        assert "text" in schema["properties"]
        assert "count" in schema["properties"]

        # Check text field
        text_field = schema["properties"]["text"]
        assert text_field["type"] == "string"
        assert text_field["minLength"] == 1

        # Check count field
        count_field = schema["properties"]["count"]
        assert count_field["type"] == "integer"
        assert count_field["default"] == 1

    def test_output_schema_properties(self):
        """Test output schema has correct properties."""
        schema = TestOutput.model_json_schema()

        assert "properties" in schema
        assert "result" in schema["properties"]
        assert "processed_count" in schema["properties"]

    def test_config_schema_properties(self):
        """Test config schema has correct properties."""
        schema = TestConfig.model_json_schema()

        assert "properties" in schema
        assert "prefix" in schema["properties"]
        assert "uppercase" in schema["properties"]

    def test_full_component_schema(self):
        """Test full component schema generation."""
        schema = ExampleComponent.get_schema()

        # Metadata
        assert schema["name"] == "ExampleComponent"
        assert schema["version"] == "1.0.0"

        # Schemas are complete
        assert "title" in schema["inputs"]
        assert "title" in schema["outputs"]
        assert "title" in schema["config"]


# =============================================================================
# Tests for Backwards Compatibility
# =============================================================================

class TestBackwardsCompatibility:
    """Tests to ensure backwards compatibility with legacy components."""

    def test_legacy_component_base_exists(self):
        """Test that legacy ComponentBase still exists."""
        from agent.component.base import ComponentBase, ComponentParamBase

        assert ComponentBase is not None
        assert ComponentParamBase is not None

    def test_legacy_imports(self):
        """Test that legacy imports still work."""
        from agent.component.base import ComponentBase, ComponentParamBase

        # Should not raise any errors
        assert hasattr(ComponentBase, 'component_name')
        assert hasattr(ComponentBase, 'invoke')
        assert hasattr(ComponentParamBase, 'check')


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the standardized component system."""

    @pytest.fixture
    def mock_canvas(self):
        """Create a mock canvas."""
        return MockCanvas()

    def test_component_with_variable_resolution(self, mock_canvas):
        """Test component with variable resolution."""
        mock_canvas.set_variable("upstream@result", "variable_value")

        class VariableComponent(StandardizedComponentBase):
            component_name = "VariableComponent"

            input_schema = TestInput
            output_schema = TestOutput
            config_schema = TestConfig

            def run(self, inputs):
                # Access variable from canvas
                var_value = self.get_variable_value("upstream@result")
                return TestOutput(result=var_value or inputs.text)

        with patch('agent.component.base.Graph', MockCanvas):
            component = VariableComponent(mock_canvas, "test-id", {})

        result = component.invoke(text="fallback")
        assert result["result"] == "variable_value"

    def test_error_handling_with_default_value(self, mock_canvas):
        """Test error handling with exception default value."""

        class ErrorComponent(StandardizedComponentBase):
            component_name = "ErrorComponent"

            input_schema = TestInput
            output_schema = TestOutput
            config_schema = TestConfig

            def run(self, inputs):
                raise Exception("Intentional error")

        with patch('agent.component.base.Graph', MockCanvas):
            component = ErrorComponent(
                mock_canvas,
                "test-id",
                {"exception_method": "comment", "exception_default_value": "default"}
            )

        result = component.invoke(text="test")

        # Should not have error since default value is set
        assert "_ERROR" not in result or result.get("_ERROR") is None

    def test_multiple_components_registration(self):
        """Test registering multiple components."""
        manager = PluginManager()

        class ComponentA(StandardizedComponentBase):
            component_name = "ComponentA"
            def run(self, inputs): pass

        class ComponentB(StandardizedComponentBase):
            component_name = "ComponentB"
            def run(self, inputs): pass

        manager.register(ComponentA)
        manager.register(ComponentB)

        assert len(manager.list_names()) == 2
        assert manager.has("ComponentA")
        assert manager.has("ComponentB")
