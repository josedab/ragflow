# RAGFlow Terminology Glossary

**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## Core Concepts

### RAG (Retrieval-Augmented Generation)
A technique that enhances LLM responses by first retrieving relevant information from a knowledge base, then providing it as context to the LLM for answer generation. RAGFlow implements this with hybrid search (semantic + keyword) and deep document understanding.

### Knowledge Base (KB)
A collection of documents that have been parsed, chunked, and indexed for retrieval. In RAGFlow, each KB has:
- A unique ID and configuration
- Associated documents
- Embedding model settings
- Search parameters

### Chunk
A segment of a document after parsing and splitting. Chunks are:
- Stored with embeddings for semantic search
- Indexed for full-text search
- Associated with metadata (page number, position, etc.)

### Dialog / Chat Application
A conversational interface configured with:
- One or more knowledge bases
- LLM model selection
- Prompt templates
- Retrieval parameters

### Canvas / Agent Workflow
A visual workflow editor for building AI agents. Composed of:
- **Nodes**: Processing components (LLM, Retrieval, etc.)
- **Edges**: Data flow connections between nodes
- **Variables**: Data passed between components

## Document Processing

### Parser
Component that extracts content from documents. RAGFlow parsers:
- **Naive**: General-purpose multi-format parser
- **DeepDoc**: PDF parser with layout recognition
- **MinerU**: External service parser
- **VLM**: Vision-language model parser

### Layout Recognition
Detection of document structure elements:
- Text blocks, titles, headers/footers
- Tables, figures, captions
- Equations, references
- Page numbers, watermarks

### OCR (Optical Character Recognition)
Extraction of text from images within documents. RAGFlow uses:
- ONNX-based models for detection
- Multi-language support
- Batch processing with GPU acceleration

### Chunking Strategy
Method for splitting documents into retrievable segments:
- **Naive merge**: Token-count based with overlap
- **Hierarchical merge**: Preserves document structure
- **Tree merge**: Maintains outline hierarchy
- **Q&A**: Question-answer pair extraction

## Search & Retrieval

### Hybrid Search
Combination of multiple search methods:
- **Full-text (BM25)**: Keyword matching with TF-IDF scoring
- **Semantic (Vector)**: Embedding similarity search
- **Fusion**: Weighted combination of results

### Embedding
Dense vector representation of text for semantic search. RAGFlow supports:
- OpenAI embeddings
- Built-in models (BGE, Qwen)
- 30+ provider options

### Reranking
Second-stage ranking of retrieved results using:
- Cross-encoder models
- Contextual relevance scoring
- Score normalization

### DOC_ENGINE
Configuration that determines the vector database:
- `elasticsearch` (default)
- `opensearch`
- `infinity`

## LLM Integration

### Chat Model
LLM for conversational interactions. RAGFlow supports 50+ providers through:
- Direct API integration
- LiteLLM proxy layer

### Factory Pattern
Dynamic instantiation of LLM providers based on:
- `_FACTORY_NAME` class attribute
- Configuration-driven selection

### Streaming
Token-by-token response delivery for:
- Real-time user feedback
- Early termination capability
- Progress indication

### Function Calling / Tools
LLM capability to invoke external functions:
- Tool definition schemas
- Structured output parsing
- Multi-turn tool use

## Agent System

### Component
Building block for agent workflows:
- **Begin**: Entry point
- **LLM**: Model invocation
- **Retrieval**: Knowledge search
- **Categorize**: Classification
- **Switch**: Conditional branching
- **Iterator**: Loop processing

### Tool
External service integration:
- **Tavily**: Web search
- **Wikipedia**: Encyclopedia
- **ExecSQL**: Database queries
- **CodeExec**: Code execution sandbox

### Variable Binding
Pattern-based data reference: `{{component_id@variable_name}}`
- Late binding at execution time
- Regex-based replacement
- Nested object access

### GraphRAG
Knowledge graph-enhanced RAG:
- Entity extraction
- Relation mapping
- Community detection (Leiden algorithm)
- Multi-hop reasoning

## Frontend

### UmiJS
React application framework providing:
- File-based routing
- Plugin system
- Build optimization

### Zustand Store
Client-side state management for:
- Canvas/workflow state
- Node/edge management
- Form data

### React Query
Server state management for:
- Data fetching with caching
- Mutations with invalidation
- Optimistic updates

### shadcn/ui
Component library built on Radix UI primitives:
- Accessible components
- Tailwind CSS styling
- Customizable themes

## Infrastructure

### Docker Compose
Container orchestration for:
- Multi-service deployment
- Network configuration
- Volume management

### Helm Chart
Kubernetes deployment package with:
- StatefulSets for databases
- ConfigMaps for configuration
- Secrets for credentials

### MCP (Model Context Protocol)
Standard for AI model integrations:
- Tool discovery
- Context sharing
- Streaming responses

## Database Models

### Tenant
Multi-tenancy unit representing:
- User account
- Usage quotas
- LLM configurations

### Document
File uploaded to a knowledge base:
- Status tracking (pending, running, done)
- Parser configuration
- Chunk count

### Task
Background job for:
- Document parsing
- Embedding generation
- Index updates

## Configuration

### service_conf.yaml
Backend service configuration:
- Database connections
- Storage settings
- LLM defaults

### .env
Environment variables for:
- Service ports
- Engine selection
- Credentials

### Runtime Config
Dynamic configuration loaded at startup:
- Job server settings
- HTTP configuration
- Debug mode

## API Concepts

### Blueprint
Flask route organization:
- Modular endpoint grouping
- URL prefix configuration
- Shared decorators

### Token Authentication
API access method using:
- Bearer tokens in headers
- Format validation
- Permission checking

### SSE (Server-Sent Events)
Real-time streaming protocol for:
- Chat responses
- Workflow execution events
- Progress updates

## Common Abbreviations

| Abbreviation | Full Term |
|--------------|-----------|
| KB | Knowledge Base |
| LLM | Large Language Model |
| NLP | Natural Language Processing |
| OCR | Optical Character Recognition |
| ORM | Object-Relational Mapping |
| RAG | Retrieval-Augmented Generation |
| SSE | Server-Sent Events |
| TTS | Text-to-Speech |
| VLM | Vision-Language Model |

## Status Codes

### Document Status
- `0`: Pending
- `1`: Processing
- `2`: Completed
- `3`: Failed
- `4`: Cancelled

### Task Status
- `pending`: Queued
- `running`: In progress
- `done`: Completed
- `fail`: Failed
- `cancel`: Cancelled

### Error Codes
- `0`: Success
- `100`: Authentication error
- `101`: Data not found
- `102`: Invalid parameter
- `500`: Server error

## File Conventions

### Python
- `snake_case.py` for modules
- `CamelCase` for classes
- `snake_case` for functions/variables

### TypeScript
- `kebab-case.tsx` for components
- `camelCase` for variables/functions
- `PascalCase` for types/interfaces

### API Endpoints
- `/api/v1/{resource}` base pattern
- `POST` for create/search
- `GET` for read
- `PUT/DELETE` for update/delete
