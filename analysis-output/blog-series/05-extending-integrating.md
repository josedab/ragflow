# Extending RAGFlow: Agents and Integrations

**Reading time:** 9 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- The agent workflow system architecture
- How to create custom components
- Tool integration patterns
- GraphRAG capabilities for knowledge graphs

---

## Introduction

RAGFlow's agent system lets you build sophisticated AI workflows visually. Instead of writing code for each automation, you connect components in a canvas—LLM nodes, retrieval nodes, conditional logic, external tools.

This post explores how the agent system works under the hood and how to extend it with custom components and tools.

---

## Agent System Architecture

```
Canvas (Visual Editor)
    │
    ▼
┌─────────────────┐
│  DSL (JSON)     │
│  - nodes        │
│  - edges        │
│  - variables    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execution Engine│
│ - Path resolver │
│ - Dependency DAG│
│ - Thread pool   │
└────────┬────────┘
         │
    ┌────┴────┬────────┬─────────┐
    ▼         ▼        ▼         ▼
┌──────┐ ┌───────┐ ┌──────┐ ┌──────┐
│ LLM  │ │Retriev│ │Switch│ │ Tool │
│ Node │ │  Node │ │ Node │ │ Node │
└──────┘ └───────┘ └──────┘ └──────┘
```

---

## Component Model

### Base Component

All workflow components inherit from a base class:

```python
# agent/component/base.py
class ComponentBase:
    component_name = "base"

    def __init__(self, canvas, component_id, params):
        self.canvas = canvas
        self.component_id = component_id
        self.params = params
        self._output = {}

    def _run(self, history, **kwargs):
        """Execute this component - subclasses implement"""
        raise NotImplementedError

    def output(self, key=None):
        """Get component outputs"""
        if key:
            return self._output.get(key)
        return self._output

    def get_input(self, key):
        """Get input from upstream component"""
        # Variables use pattern: {{component_id@variable_name}}
        value = self.params.get(key, "")
        return self._resolve_variables(value)

    def _resolve_variables(self, text):
        """Replace variable patterns with actual values"""
        pattern = r'\{\{(\w+)@(\w+)\}\}'

        def replace(match):
            cpn_id, var_name = match.groups()
            upstream = self.canvas.get_component(cpn_id)
            return str(upstream.output(var_name))

        return re.sub(pattern, replace, text)
```

**Code reference:** [agent/component/base.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/agent/component/base.py)

### Available Components

RAGFlow includes 17 built-in components:

| Component | Purpose | Key Outputs |
|-----------|---------|-------------|
| Begin | Workflow entry point | User input |
| LLM | Model invocation | Response text |
| Retrieval | Knowledge search | Chunks, references |
| Categorize | Text classification | Category |
| Switch | Conditional branching | Selected branch |
| Message | Static message | Text |
| Agent | Nested agent call | Agent output |
| Invoke | HTTP API call | Response |
| DataOperations | Data transformation | Transformed data |
| Iteration | Loop over items | Current item |
| IterationItem | Process loop item | Item result |
| StringTransform | Text manipulation | Transformed text |
| ListOperations | List handling | List result |
| FillUp | Template filling | Filled text |
| VariableAggregator | Combine variables | Aggregated value |
| Webhook | External webhook | Response |

---

## Creating a Custom Component

### Step 1: Define the Component

```python
# agent/component/my_component.py
from agent.component.base import ComponentBase

class MyCustomComponent(ComponentBase):
    component_name = "MyCustom"

    def _run(self, history, **kwargs):
        """Execute custom logic"""
        # Get input from upstream
        input_text = self.get_input("input_text")

        # Get parameters from configuration
        option = self.params.get("option", "default")

        # Perform your custom logic
        result = self._process(input_text, option)

        # Set outputs for downstream components
        self._output = {
            "result": result,
            "metadata": {"processed_by": "MyCustom"}
        }

        # Return text for streaming (optional)
        return result

    def _process(self, text, option):
        """Your custom processing logic"""
        if option == "uppercase":
            return text.upper()
        elif option == "reverse":
            return text[::-1]
        return text
```

### Step 2: Register the Component

```python
# agent/component/__init__.py
from agent.component.my_component import MyCustomComponent

COMPONENT_REGISTRY = {
    # ... existing components
    "MyCustom": MyCustomComponent,
}
```

### Step 3: Add UI Configuration

Create the component's form configuration for the canvas editor:

```typescript
// web/src/pages/agent/canvas/node/my-custom-node.tsx
export const MyCustomNodeConfig = {
  inputs: [
    {
      name: "input_text",
      label: "Input Text",
      type: "variable",
      required: true
    }
  ],
  parameters: [
    {
      name: "option",
      label: "Processing Option",
      type: "select",
      options: ["default", "uppercase", "reverse"]
    }
  ],
  outputs: [
    { name: "result", label: "Result" },
    { name: "metadata", label: "Metadata" }
  ]
};
```

---

## Tool Integration

Tools are external services that agents can invoke:

### Tool Base Class

```python
# agent/tools/base.py
class ToolBase:
    name = "base_tool"
    description = "Base tool description"

    # OpenAI function calling schema
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, config):
        self.config = config

    def run(self, **kwargs):
        """Execute the tool"""
        raise NotImplementedError
```

### Example: Web Search Tool

```python
# agent/tools/tavily_search.py
class TavilySearch(ToolBase):
    name = "tavily_search"
    description = "Search the web for current information"

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self, config):
        from tavily import TavilyClient
        self.client = TavilyClient(api_key=config.get('api_key'))

    def run(self, query, max_results=5):
        """Execute web search"""
        response = self.client.search(
            query=query,
            max_results=max_results
        )

        # Format results
        results = []
        for item in response.get('results', []):
            results.append({
                'title': item.get('title'),
                'url': item.get('url'),
                'content': item.get('content')
            })

        return results
```

**Code reference:** [agent/tools/](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/agent/tools/)

### Available Tools (22)

| Category | Tools |
|----------|-------|
| Web Search | Tavily, Google, DuckDuckGo, SearXNG |
| Knowledge | Retrieval, Wikipedia |
| Finance | YahooFinance, AKShare, Wencai, JIN10, TuShare |
| Academic | arXiv, PubMed, GoogleScholar |
| Database | ExecSQL, CodeExec |
| Utilities | Crawler, Email, GitHub, DeepL, QWeather |

---

## Workflow Execution

### Execution Engine

```python
# agent/canvas/canvas.py
class Canvas:
    def __init__(self, dsl):
        self.nodes = dsl['components']
        self.edges = dsl['edges']
        self.components = {}

    def run(self, input_text, history=[]):
        """Execute workflow"""
        # Initialize components
        for node in self.nodes:
            cls = COMPONENT_REGISTRY[node['type']]
            self.components[node['id']] = cls(
                self, node['id'], node['params']
            )

        # Build execution path from edges
        execution_order = self._topological_sort()

        # Execute with thread pool
        executor = ThreadPoolExecutor(max_workers=5)

        for component_id in execution_order:
            component = self.components[component_id]

            # Wait for upstream dependencies
            self._wait_for_dependencies(component_id)

            # Execute component
            future = executor.submit(
                component._run,
                history
            )

            # Stream results
            result = future.result()
            yield {
                'component_id': component_id,
                'output': result
            }

    def _topological_sort(self):
        """Sort components by dependencies"""
        # Build adjacency list from edges
        # Return execution order
        pass
```

### Variable Resolution

Variables use a pattern-based late-binding system:

```python
# Pattern: {{component_id@variable_name}}
# Supports nested access: {{retrieval_0@chunks[0].content}}

def _resolve_variables(self, text):
    """Replace variable patterns"""
    pattern = r'\{\{(\w+)@([\w\.\[\]]+)\}\}'

    def replace(match):
        cpn_id, var_path = match.groups()
        upstream = self.canvas.get_component(cpn_id)
        value = upstream.output()

        # Handle nested path (e.g., "chunks[0].content")
        for part in var_path.split('.'):
            if '[' in part:
                name, idx = part.rstrip(']').split('[')
                value = value[name][int(idx)]
            else:
                value = value[part]

        return str(value)

    return re.sub(pattern, replace, text)
```

---

## GraphRAG Integration

RAGFlow includes GraphRAG for knowledge graph-enhanced retrieval:

### Entity Extraction

```python
# graphrag/general/extractor.py
class EntityExtractor:
    def __init__(self, llm_model):
        self.llm = llm_model

    def extract(self, text):
        """Extract entities and relations from text"""
        prompt = f"""
        Extract entities and relationships from this text.

        Text: {text}

        Output format:
        Entities: [list of entities with types]
        Relations: [list of (entity1, relation, entity2)]
        """

        response = self.llm.chat([
            {"role": "user", "content": prompt}
        ])

        return self._parse_response(response)
```

### Knowledge Graph Construction

```python
# graphrag/general/builder.py
class GraphBuilder:
    def __init__(self, redis_conn):
        self.graph = redis_conn

    def build(self, documents):
        """Build knowledge graph from documents"""
        for doc in documents:
            # Extract entities and relations
            entities, relations = self.extractor.extract(doc.content)

            # Add nodes
            for entity in entities:
                self.graph.add_node(
                    entity['name'],
                    entity_type=entity['type'],
                    doc_id=doc.id
                )

            # Add edges
            for subj, rel, obj in relations:
                self.graph.add_edge(subj, obj, relation=rel)

        # Community detection
        communities = self._detect_communities()

        return communities
```

### Graph-Enhanced Search

```python
# graphrag/general/search.py
class GraphSearch:
    def search(self, query, mode="hybrid"):
        """Search with graph enhancement"""
        if mode == "entity":
            # Find entities matching query
            entities = self._entity_search(query)
            return self._expand_from_entities(entities)

        elif mode == "relation":
            # Find relations matching query
            relations = self._relation_search(query)
            return self._expand_from_relations(relations)

        elif mode == "community":
            # Find relevant communities
            communities = self._community_search(query)
            return self._aggregate_community_content(communities)

        elif mode == "hybrid":
            # Combine all modes
            results = []
            results.extend(self._entity_search(query))
            results.extend(self._community_search(query))
            return self._deduplicate_and_rank(results)
```

**Code reference:** [graphrag/](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/graphrag/)

---

## Integration Patterns

### HTTP Webhook Integration

```python
# agent/component/invoke.py
class InvokeComponent(ComponentBase):
    component_name = "Invoke"

    def _run(self, history, **kwargs):
        url = self.get_input("url")
        method = self.params.get("method", "GET")
        headers = self.params.get("headers", {})
        body = self.get_input("body")

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body if method in ["POST", "PUT"] else None,
            timeout=30
        )

        self._output = {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }

        return str(self._output['body'])
```

### Database Integration

```python
# agent/tools/exec_sql.py
class ExecSQL(ToolBase):
    name = "exec_sql"
    description = "Execute SQL query on configured database"

    def run(self, query):
        """Execute SQL and return results"""
        # Validate query (prevent dangerous operations)
        if not self._is_safe_query(query):
            raise ValueError("Query contains forbidden operations")

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        conn.commit()
        return {"affected_rows": cursor.rowcount}
```

---

## Key Takeaways

1. **Components are the building blocks** of agent workflows with standardized input/output interfaces.

2. **Variable late-binding** enables flexible data flow with `{{cpn_id@var}}` patterns.

3. **Tools follow OpenAI function schema** for compatibility with function calling.

4. **Execution uses topological sort** to respect dependencies, with thread pool concurrency.

5. **GraphRAG adds knowledge graphs** with entity extraction, community detection, and multi-modal search.

6. **Extension is straightforward**—implement base class, register, add UI config.

---

## What's Next

In [Blog 6: Performance Analysis](./06-performance-analysis.md), we'll examine RAGFlow's performance characteristics, identify bottlenecks, and explore scaling strategies.

---

## Further Reading

- [RFC-0004: Agent Component Standardization](../rfcs/RFC-0004-agent-component-standardization.md)
- [Terminology Glossary](../initial-analysis/terminology-glossary.md)
