# RAGFlow Agent System - Quick Reference Guide

## Component Architecture at a Glance

### 17 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│ FLOW CONTROL        │ Begin, Switch, Webhook               │
├─────────────────────────────────────────────────────────────┤
│ LLM/AI              │ LLM, Agent, Categorize               │
├─────────────────────────────────────────────────────────────┤
│ DATA HANDLING       │ Message, Iteration, IterationItem    │
├─────────────────────────────────────────────────────────────┤
│ LOGIC/TRANSFORM     │ Invoke, DataOperations               │
├─────────────────────────────────────────────────────────────┤
│ TEXT/LIST           │ StringTransform, ListOperations      │
├─────────────────────────────────────────────────────────────┤
│ UTILITIES           │ FillUp, VariableAggregator           │
└─────────────────────────────────────────────────────────────┘
```

## Variable Reference Pattern

```
{{cpn_id@output_name}}          - Component output
{{sys.query}}                   - Global variable
{{cpn_0@output.nested.field}}   - Nested access
```

## Component Execution Lifecycle

```
1. INVOKE
   ├─ Record start time
   └─ Call _invoke(**kwargs)

2. PROCESS (Component-specific)
   ├─ Get inputs via get_input()
   ├─ Access canvas variables
   ├─ Execute business logic
   └─ Set outputs via set_output()

3. OUTPUT & ROUTING
   ├─ set_output("result", value)        - Main output
   ├─ set_output("_next", [cpn_ids])     - Route to next
   └─ set_output("_ERROR", msg)          - Error handling

4. CLEANUP
   ├─ Record end time
   └─ Return output dict
```

## Canvas Workflow Execution Model

```
┌─────────────────────────────────────────────────────────────┐
│ WORKFLOW EXECUTION FLOW                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. Initialize                                              │
│    ├─ Reset outputs                                        │
│    ├─ Parse inputs → set globals                           │
│    └─ Increment conversation turn                          │
│                                                             │
│ 2. Build Execution Path                                    │
│    ├─ Start: path = ["begin"]                              │
│    ├─ Components update path via _next output              │
│    ├─ Categorize/Switch modify path for routing            │
│    └─ Iteration creates child paths                        │
│                                                             │
│ 3. Batch Execute Components                                │
│    ├─ ThreadPoolExecutor (max 5 workers)                   │
│    ├─ Validate upstream dependencies                       │
│    ├─ Execute in parallel where possible                   │
│    └─ Sync results                                         │
│                                                             │
│ 4. Stream Events                                           │
│    ├─ workflow_started                                     │
│    ├─ node_started → node_finished                         │
│    ├─ message (for streaming output)                       │
│    └─ workflow_finished                                    │
│                                                             │
│ 5. Handle Errors                                           │
│    ├─ Catch exceptions                                     │
│    ├─ Check exception_handler()                            │
│    ├─ Set _ERROR output                                    │
│    └─ Continue or halt                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Tool System Architecture

### 22 Tools Available

| Category | Tools |
|----------|-------|
| **Web Search** | Tavily, GoogleSearch, DuckDuckGo, SearXNG |
| **Knowledge** | Retrieval, Wikipedia |
| **Finance** | YahooFinance, AKShare, Wencai, JIN10, TuShare |
| **Academic** | arXiv, PubMed, GoogleScholar |
| **Database** | ExecSQL, CodeExec |
| **Utility** | Crawler, Email, GitHub, DeepL, QWeather |

### Tool Execution Pattern

```python
class Tool(ToolBase):
    def get_meta(self) -> dict:
        # OpenAI function schema for LLM
        return {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
    
    def _invoke(self, **kwargs):
        # Execute: kwargs already resolved from LLM
        result = api_call(kwargs)
        self._retrieve_chunks(result, ...)  # Format for KB
        return result
```

## GraphRAG at a Glance

### Two Implementations

| Feature | General | Light |
|---------|---------|-------|
| **Extraction** | Full NLP | Basic |
| **Community Detection** | Yes (Leiden) | No |
| **Community Reports** | Yes | No |
| **Entity Resolution** | Yes | Limited |
| **N-hop Search** | Multi-hop | Single-hop |
| **Complexity** | High | Low |

### Graph Processing Pipeline

```
Document
  ↓
Chunk
  ↓
Extract Entities & Relations
  ↓
Build Graph (NetworkX)
  ↓
Merge with KB Graph (dedup, update)
  ↓
Community Detection (General only)
  ↓
Generate Reports (General only)
  ↓
Index for Search
  ↓
Query Support
```

### Search Modes

```
Entity Search    → Vector + PageRank + n-hop neighbors
Relation Search  → from_entity → to_entity + weight
Community Search → Top communities + summaries
Hybrid Search    → Entity + Relation + Community context
```

## Template Patterns (24 Pre-built)

```
Research/Analysis:  Deep Research, Stock Research, Market Blog
Customer Service:   Customer Service, Customer Support, User Interaction
Knowledge Work:     Technical Q&A, KB Report, SQL Assistant
Content:            SEO Blog, Image Analysis, Trip Planner
Data:               CSV Analysis, CV Analysis, Chunking
```

## Key Extension Points

### Adding a Component

```
1. Create MyComponentParam (ComponentParamBase)
2. Create MyComponent (ComponentBase)
   └─ component_name = "MyComponent"
3. Implement _invoke() method
4. Drop in agent/component/ directory
5. Auto-discovered at runtime
```

### Adding a Tool

```
1. Create MyToolParam (ToolParamBase)
   └─ Define meta: ToolMeta with parameters
2. Create MyTool (ToolBase)
   └─ Implement _invoke(**kwargs)
3. Drop in agent/tools/ directory
4. Auto-discovered at runtime
```

### Customizing GraphRAG

```
1. Extend GraphExtractor or KGSearch
2. Override extraction_prompt or search logic
3. Pass custom class to run_graphrag()
```

## Important Directories

```
/agent/
  ├─ component/        - 17 components
  ├─ tools/            - 22 tools
  ├─ templates/        - 24 pre-built workflows
  ├─ canvas.py         - Execution engine
  └─ settings.py       - Configuration

/graphrag/
  ├─ general/          - Full GraphRAG
  ├─ light/            - Lightweight version
  ├─ search.py         - Query interface
  ├─ utils.py          - Helpers
  ├─ entity_resolution.py
  └─ agentic_reasoning/ - Deep research

/api/
  └─ apps/
     ├─ canvas_app.py  - Canvas API endpoints
     └─ dialog_app.py  - Chat/dialog endpoints
```

## Data Flow Example: Deep Research

```
User Input (query)
  ↓
Begin Component
  ├─ Parse inputs
  ├─ Set sys.query
  └─ Route to Research Agent
  ↓
Agent Component
  ├─ Initialize tools: [WebSearch, Retrieval]
  ├─ Tool 1: WebSearch → find key sources
  ├─ Tool 2: Retrieval → find KB context
  ├─ Synthesize results
  ├─ Tool 3: WebSearch → drill deeper
  └─ Final response
  ↓
Message Component
  ├─ Template: format with citations
  ├─ Stream to client
  └─ Return final report
```

## Performance Tips

1. **Parallel Components**: Siblings execute in parallel (max 5 workers)
2. **LLM Caching**: Identical prompts cached in Redis
3. **Streaming**: Use Message component for long operations
4. **Graph Caching**: GraphRAG subgraphs cached, merged incrementally
5. **Timeouts**: Configurable per component (default 10 min)

## Common Patterns

### Intent-Based Routing
```
Begin → Categorize → Switch → [Agent1, Agent2, Agent3]
```

### Multi-Source Research
```
Begin → [SearchTool1, SearchTool2, KB] → Synthesize → Agent → Message
```

### Iterative Processing
```
Begin → Iteration → [ProcessItem1, ProcessItem2, ...] → Aggregate → Message
```

### Data Transformation
```
Begin → DataOperations → Filter/Transform/Combine → Message
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `COMPONENT_EXEC_TIMEOUT` | 600s | Max execution time per component |
| `MAX_CONCURRENT_CHATS` | 10 | Parallel chat sessions |
| `ENABLE_TIMEOUT_ASSERTION` | 1 | Strict timeout in GraphRAG |

## Error Handling

```
Component Error:
  ├─ Exception caught in invoke()
  ├─ Check exception_handler()
  │  ├─ "comment" → use default value
  │  └─ "goto" → route to exception component
  ├─ Set _ERROR output
  └─ Continue (if configured)

Task Cancellation:
  ├─ REDIS_CONN.set(f"{task_id}-cancel", "x")
  ├─ Canvas.is_canceled() returns True
  ├─ Component.check_if_canceled() stops execution
  └─ Set _ERROR output
```

## File Locations

```
Main Report:     /home/user/ragflow/RAGFLOW_AGENT_ANALYSIS.md
Quick Reference: /home/user/ragflow/RAGFLOW_QUICK_REFERENCE.md
Source Code:     /home/user/ragflow/agent/*
                 /home/user/ragflow/graphrag/*
```

---

Last Updated: Nov 18, 2025 | Document Size: 1,217 lines | Scope: Complete agent & GraphRAG analysis

