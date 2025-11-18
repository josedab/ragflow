# RAGFlow Repository Structure

**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## Directory Overview

```
ragflow/
├── agent/                    # Agent workflow system
│   ├── component/           # 17 workflow components (LLM, Retrieval, etc.)
│   ├── templates/           # Pre-built agent workflows
│   ├── tools/               # 22 external tool integrations
│   └── test/                # Agent unit tests
│
├── agentic_reasoning/        # Advanced reasoning capabilities
│
├── api/                      # Flask backend application
│   ├── apps/                # Flask blueprints (kb, dialog, document, etc.)
│   │   ├── __init__.py      # App initialization, blueprint registration
│   │   ├── kb_app.py        # Knowledge base endpoints
│   │   ├── dialog_app.py    # Chat/conversation endpoints
│   │   ├── document_app.py  # Document processing endpoints
│   │   ├── canvas_app.py    # Agent workflow canvas endpoints
│   │   └── file_app.py      # File management endpoints
│   ├── common/              # Shared utilities
│   ├── db/                  # Database layer
│   │   ├── db_models.py     # 28 Peewee ORM models
│   │   ├── services/        # 20+ service classes
│   │   └── init_data.py     # Initial data seeding
│   ├── utils/               # API utilities
│   └── ragflow_server.py    # Main server entry point
│
├── common/                   # Shared utilities across modules
│   ├── data_source/         # External data source connectors
│   ├── log_utils.py         # Logging configuration
│   ├── settings.py          # Global settings management
│   └── config_utils.py      # Configuration utilities
│
├── conf/                     # Configuration files
│   ├── mapping.json         # Elasticsearch index mappings
│   └── *.json               # Various config files
│
├── deepdoc/                  # Document processing engine
│   ├── parser/              # Document parsers
│   │   ├── pdf_parser.py    # PDF parser (1,400+ lines)
│   │   ├── docx_parser.py   # Word document parser
│   │   ├── excel_parser.py  # Excel/CSV parser
│   │   ├── html_parser.py   # HTML parser
│   │   ├── json_parser.py   # JSON parser
│   │   └── ...              # Other format parsers
│   └── vision/              # Computer vision components
│       ├── ocr.py           # OCR with ONNX models
│       ├── layout_recognizer.py  # Layout detection
│       ├── table_structure_recognizer.py  # Table parsing
│       └── recognizer.py    # Base recognizer class
│
├── docker/                   # Docker deployment
│   ├── docker-compose.yml   # Full stack deployment
│   ├── docker-compose-base.yml  # Base services only
│   ├── .env                 # Environment variables
│   ├── service_conf.yaml.template  # Service configuration
│   ├── nginx/               # Nginx reverse proxy config
│   ├── entrypoint.sh        # Container entry point
│   └── Dockerfile           # Multi-stage build
│
├── docs/                     # Documentation (48 markdown files)
│   ├── guides/              # User guides
│   ├── develop/             # Developer documentation
│   ├── references/          # API references
│   └── contribution/        # Contribution guidelines
│
├── graphrag/                 # Knowledge graph RAG
│   ├── general/             # Full-featured GraphRAG
│   └── light/               # Lightweight GraphRAG
│
├── helm/                     # Kubernetes Helm charts
│   ├── Chart.yaml           # Chart metadata
│   ├── values.yaml          # Default values
│   └── templates/           # 14 K8s resource templates
│
├── intergrations/            # Third-party integrations
│   ├── chatgpt-on-wechat/   # WeChat plugin
│   ├── extension_chrome/    # Chrome extension
│   └── firecrawl/           # Web crawler
│
├── mcp/                      # Model Context Protocol
│   ├── server/              # MCP server implementation
│   │   └── server.py        # SSE + Streamable HTTP (715 lines)
│   └── client/              # MCP client example
│
├── plugin/                   # Plugin system
│   └── embedded_plugins/    # Built-in plugins
│
├── rag/                      # Core RAG pipeline
│   ├── app/                 # 14 document processing strategies
│   │   ├── naive.py         # General parsing (33KB)
│   │   ├── qa.py            # Q&A pair extraction
│   │   ├── table.py         # Table understanding
│   │   ├── laws.py          # Legal documents
│   │   ├── paper.py         # Academic papers
│   │   └── ...              # More strategies
│   ├── flow/                # Processing pipeline
│   │   ├── parser/          # Document parsing stage
│   │   ├── splitter/        # Chunking stage
│   │   ├── tokenizer/       # Embedding stage
│   │   └── extractor/       # LLM extraction stage
│   ├── llm/                 # LLM provider abstractions
│   │   ├── chat_model.py    # Chat model base (50+ providers)
│   │   ├── embedding_model.py  # Embedding models (30+)
│   │   ├── rerank_model.py  # Reranking models (6+)
│   │   ├── cv_model.py      # Vision models
│   │   └── tts_model.py     # Text-to-speech
│   ├── nlp/                 # NLP utilities
│   │   ├── __init__.py      # Chunking algorithms
│   │   ├── rag_tokenizer.py # Tokenization engine
│   │   ├── query.py         # Query processing
│   │   └── search.py        # Search implementation
│   ├── utils/               # RAG utilities
│   │   ├── es_conn.py       # Elasticsearch connection
│   │   ├── infinity_conn.py # Infinity connection
│   │   └── redis_conn.py    # Redis utilities
│   └── prompts/             # LLM prompt templates
│
├── sandbox/                  # Code execution sandbox
│   ├── executor_manager/    # Sandbox execution
│   ├── sandbox_base_image/  # Docker base image
│   └── scripts/             # Utility scripts
│
├── sdk/                      # Software Development Kit
│   └── python/              # Python SDK
│       ├── ragflow_sdk/     # SDK implementation
│       └── test/            # SDK tests
│
├── test/                     # Test suite
│   ├── testcases/           # API test cases
│   └── unit_test/           # Unit tests
│
├── web/                      # Frontend application
│   ├── src/                 # Source code
│   │   ├── components/      # UI components (90+)
│   │   │   └── ui/          # 57 shadcn/ui components
│   │   ├── pages/           # Route pages (206 components)
│   │   ├── hooks/           # Custom React hooks (40+)
│   │   ├── services/        # API service layer
│   │   ├── locales/         # i18n (11 languages)
│   │   ├── utils/           # Utility functions
│   │   └── layouts/         # Page layouts
│   ├── public/              # Static assets
│   ├── .umirc.ts            # UmiJS configuration
│   ├── tailwind.config.js   # Tailwind CSS config
│   └── package.json         # NPM dependencies
│
├── .github/                  # GitHub configuration
│   └── workflows/           # CI/CD pipelines
│
├── pyproject.toml           # Python project config (140+ deps)
├── CLAUDE.md                # Claude Code instructions
├── README.md                # Project readme
└── LICENSE                  # Apache 2.0 license
```

## Key Entry Points

### Backend
- **Server Start**: `api/ragflow_server.py:76` - Main entry point
- **App Creation**: `api/apps/__init__.py` - Flask app factory
- **Routes**: Individual blueprint files in `api/apps/`

### Frontend
- **App Entry**: `web/src/app.tsx` - Root React component
- **Routes**: `web/src/routes.ts` - Route definitions
- **Store**: `web/src/pages/agent/store.ts` - Main Zustand store

### RAG Pipeline
- **Document Parsing**: `rag/app/naive.py` - General parser entry
- **PDF Processing**: `deepdoc/parser/pdf_parser.py` - PDF parser
- **LLM Interface**: `rag/llm/chat_model.py` - Chat model base

### Agent System
- **Components**: `agent/component/` - Workflow components
- **Tools**: `agent/tools/` - External integrations
- **Canvas API**: `api/apps/canvas_app.py` - Workflow endpoints

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python dependencies, build config |
| `web/package.json` | Frontend dependencies |
| `docker/.env` | Environment variables |
| `docker/service_conf.yaml.template` | Service configuration |
| `conf/mapping.json` | Elasticsearch mappings |
| `helm/values.yaml` | Kubernetes defaults |

## File Naming Conventions

- **Python**: `snake_case.py`
- **TypeScript/React**: `kebab-case.tsx`
- **Components**: `ComponentName/index.tsx`
- **Hooks**: `use-[name].ts` or `[feature]-hooks.ts`
- **Services**: `[feature]-service.ts`

## Important URLs (Code References)

All URLs use format: `https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/[path]`

- [Server Entry](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/ragflow_server.py#L76)
- [PDF Parser](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/deepdoc/parser/pdf_parser.py)
- [Chat Model Base](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/chat_model.py)
- [Agent Components](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/agent/component/)
- [Frontend Store](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/web/src/pages/agent/store.ts)
