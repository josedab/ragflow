# RFC-0004: Agent Component Standardization

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 2-3 weeks
**Priority:** P2 (Strategic)

## Summary

Standardize the agent component interface, improve documentation, and create a plugin system to enable easier community contributions and third-party extensions.

## Motivation

Current issues with the agent system:

1. **Inconsistent interfaces**: Components have varying input/output patterns
2. **Limited documentation**: Hard to understand how to create new components
3. **No plugin system**: Third-party components require forking
4. **Validation gaps**: Input validation varies by component
5. **Testing challenges**: Components are hard to test in isolation

## Detailed Design

### Standardized Component Interface

```python
# agent/component/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ComponentInput(BaseModel):
    """Base class for component inputs"""
    pass

class ComponentOutput(BaseModel):
    """Base class for component outputs"""
    pass

class ComponentConfig(BaseModel):
    """Component configuration schema"""
    pass

class ComponentBase(ABC):
    """Standardized component base class"""

    # Component metadata
    component_name: str = "base"
    component_version: str = "1.0.0"
    component_description: str = ""

    # Type definitions
    input_schema: type[ComponentInput] = ComponentInput
    output_schema: type[ComponentOutput] = ComponentOutput
    config_schema: type[ComponentConfig] = ComponentConfig

    def __init__(self, canvas, component_id: str, params: dict):
        self.canvas = canvas
        self.component_id = component_id
        self.config = self.config_schema(**params)
        self._output: Optional[ComponentOutput] = None

    @abstractmethod
    def run(self, inputs: ComponentInput) -> ComponentOutput:
        """Execute the component with typed inputs/outputs"""
        pass

    def validate_inputs(self, inputs: dict) -> ComponentInput:
        """Validate and convert inputs"""
        return self.input_schema(**inputs)

    def get_output(self) -> Optional[ComponentOutput]:
        """Get component output"""
        return self._output

    @classmethod
    def get_schema(cls) -> dict:
        """Get component JSON schema for UI"""
        return {
            "name": cls.component_name,
            "version": cls.component_version,
            "description": cls.component_description,
            "inputs": cls.input_schema.model_json_schema(),
            "outputs": cls.output_schema.model_json_schema(),
            "config": cls.config_schema.model_json_schema(),
        }
```

### Example Component Implementation

```python
# agent/component/retrieval.py
from pydantic import BaseModel, Field
from typing import List

class RetrievalInput(ComponentInput):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results")

class RetrievalOutput(ComponentOutput):
    chunks: List[dict] = Field(default_factory=list)
    total: int = 0
    references: List[str] = Field(default_factory=list)

class RetrievalConfig(ComponentConfig):
    kb_ids: List[str] = Field(..., description="Knowledge base IDs")
    similarity_threshold: float = Field(default=0.5)
    rerank: bool = Field(default=False)

class RetrievalComponent(ComponentBase):
    component_name = "Retrieval"
    component_version = "1.0.0"
    component_description = "Search knowledge bases for relevant content"

    input_schema = RetrievalInput
    output_schema = RetrievalOutput
    config_schema = RetrievalConfig

    def run(self, inputs: RetrievalInput) -> RetrievalOutput:
        # Perform search
        results = self._search(
            query=inputs.query,
            kb_ids=self.config.kb_ids,
            top_k=inputs.top_k,
            threshold=self.config.similarity_threshold
        )

        # Optional reranking
        if self.config.rerank:
            results = self._rerank(results, inputs.query)

        self._output = RetrievalOutput(
            chunks=results,
            total=len(results),
            references=[r['doc_name'] for r in results]
        )
        return self._output
```

### Plugin System

```python
# agent/plugins/__init__.py
import importlib
import pkg_resources

class PluginManager:
    """Manage third-party component plugins"""

    def __init__(self):
        self.components = {}

    def discover_plugins(self):
        """Discover installed plugins via entry points"""
        for entry_point in pkg_resources.iter_entry_points('ragflow.components'):
            try:
                component_cls = entry_point.load()
                self.register(component_cls)
            except Exception as e:
                logging.warning(f"Failed to load plugin {entry_point.name}: {e}")

    def register(self, component_cls):
        """Register a component class"""
        if not issubclass(component_cls, ComponentBase):
            raise ValueError("Component must inherit from ComponentBase")

        name = component_cls.component_name
        if name in self.components:
            logging.warning(f"Overwriting component: {name}")

        self.components[name] = component_cls

    def get(self, name: str) -> type[ComponentBase]:
        """Get component class by name"""
        if name not in self.components:
            raise KeyError(f"Unknown component: {name}")
        return self.components[name]

    def list_components(self) -> List[dict]:
        """List all available components with schemas"""
        return [cls.get_schema() for cls in self.components.values()]
```

### Plugin Package Structure

```python
# setup.py for a third-party plugin
setup(
    name="ragflow-component-slack",
    entry_points={
        'ragflow.components': [
            'slack = ragflow_slack:SlackComponent',
        ],
    },
)
```

### Auto-generated UI

```typescript
// Frontend auto-generates forms from component schemas
interface ComponentSchema {
  name: string;
  version: string;
  description: string;
  inputs: JSONSchema;
  outputs: JSONSchema;
  config: JSONSchema;
}

function ComponentForm({ schema }: { schema: ComponentSchema }) {
  // Auto-generate form from JSON Schema
  return (
    <Form schema={schema.config}>
      {/* Rendered from schema */}
    </Form>
  );
}
```

## Implementation Plan

### Phase 1: Core Interface (Week 1)
1. Create Pydantic-based input/output schemas
2. Update `ComponentBase` with new interface
3. Add schema generation methods
4. Update execution engine

### Phase 2: Migrate Components (Week 2)
1. Migrate built-in components to new interface
2. Add input validation
3. Update tests
4. Ensure backwards compatibility

### Phase 3: Plugin System (Week 3)
1. Implement `PluginManager`
2. Add entry point discovery
3. Create plugin documentation
4. Example plugin package

## Example Usage

### Before

```python
# Inconsistent, untyped
class MyComponent(ComponentBase):
    def _run(self, history, **kwargs):
        text = self.get_input("text")  # String, no validation
        result = process(text)
        self._output = {"result": result}  # Dict, no schema
        return result
```

### After

```python
# Typed, validated, documented
class MyInput(ComponentInput):
    text: str = Field(..., min_length=1)

class MyOutput(ComponentOutput):
    result: str
    confidence: float

class MyComponent(ComponentBase):
    input_schema = MyInput
    output_schema = MyOutput

    def run(self, inputs: MyInput) -> MyOutput:
        result, conf = process(inputs.text)
        return MyOutput(result=result, confidence=conf)
```

## Backwards Compatibility

**Breaking changes:**
- Component interface changes from `_run()` to `run()`
- Input/output now use Pydantic models

**Migration strategy:**
1. Support both old and new interfaces during transition
2. Provide migration script for custom components
3. Deprecation warnings for old interface
4. Full removal in next major version

## Alternatives Considered

### 1. Keep Current Interface
- **Pros:** No migration
- **Cons:** Continued inconsistency, hard to extend

### 2. Use Protocol Buffers
- **Pros:** Language-agnostic
- **Cons:** Overkill, added complexity

### 3. GraphQL for Component API
- **Pros:** Strong typing
- **Cons:** Different paradigm, major rewrite

## Success Criteria

- [ ] All built-in components use new interface
- [ ] JSON schemas generated for all components
- [ ] Plugin system working with example plugin
- [ ] Documentation for creating custom components
- [ ] Migration guide for existing components
- [ ] 80%+ test coverage for component base

## Open Questions

1. Should we support async components?
2. How to handle component versioning and upgrades?
3. Should the plugin system support hot-reloading?

## Stakeholder Approvals

- [ ] Agent System Lead
- [ ] Frontend Lead (for UI generation)
- [ ] Documentation Team
- [ ] Community feedback
