# RAGFlow Test Suite

This directory contains the comprehensive test suite for RAGFlow, organized into unit tests and integration tests.

## Directory Structure

```
test/
├── unit/                    # Unit tests
│   ├── conftest.py          # Shared fixtures and configuration
│   ├── services/            # Service layer tests
│   │   ├── test_document_service.py
│   │   └── test_kb_service.py
│   ├── parsers/             # Document parser tests
│   │   ├── test_pdf_parser.py
│   │   └── test_chunking.py
│   └── llm/                 # LLM provider tests
│       ├── test_chat_model.py
│       └── test_embedding.py
├── integration/             # Integration tests
│   ├── test_document_flow.py
│   ├── test_search_flow.py
│   └── test_agent_flow.py
├── fixtures/                # Test fixtures
│   ├── documents/           # Sample documents
│   │   ├── sample.pdf
│   │   └── sample.txt
│   └── responses/           # Mock API responses
│       └── llm_responses.json
├── testcases/               # Existing API tests
│   └── ...
└── unit_test/               # Existing utility tests
    └── ...
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
uv sync --python 3.10 --group test
```

### Running All Unit Tests

```bash
uv run pytest test/unit -v
```

### Running Specific Test Levels

Tests are organized by priority levels:
- **p1**: Smoke tests (critical functionality)
- **p2**: Core tests (important features)
- **p3**: Full tests (comprehensive coverage)

```bash
# Run only p1 (smoke) tests
uv run pytest test/unit --level=p1 -v

# Run p1 and p2 tests
uv run pytest test/unit --level=p2 -v

# Run all tests
uv run pytest test/unit --level=p3 -v
```

### Running Specific Test Modules

```bash
# Run service tests
uv run pytest test/unit/services -v

# Run parser tests
uv run pytest test/unit/parsers -v

# Run LLM tests
uv run pytest test/unit/llm -v

# Run integration tests
uv run pytest test/integration -v
```

### Running with Coverage

```bash
# Run with coverage report
uv run pytest test/unit \
    --cov=api \
    --cov=rag \
    --cov=deepdoc \
    --cov=agent \
    --cov-report=term-missing \
    --cov-report=html

# View HTML coverage report
open coverage_html/index.html
```

## Test Categories

### Unit Tests

Unit tests are isolated tests that verify individual components:

- **Service Tests** (`test/unit/services/`): Test database operations, business logic, and service methods
- **Parser Tests** (`test/unit/parsers/`): Test document parsing, chunking, and text extraction
- **LLM Tests** (`test/unit/llm/`): Test LLM provider integrations, embeddings, and chat models

### Integration Tests

Integration tests verify end-to-end flows:

- **Document Flow**: Upload → Parse → Index workflow
- **Search Flow**: Query → Retrieval → Ranking
- **Agent Flow**: Agent creation → Tool execution → Response generation

## Writing Tests

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<description>`

### Using Priority Markers

Mark tests with priority levels:

```python
import pytest

@pytest.mark.p1
def test_critical_feature():
    """Critical test that must always pass."""
    pass

@pytest.mark.p2
def test_important_feature():
    """Important test for core functionality."""
    pass

@pytest.mark.p3
def test_comprehensive_scenario():
    """Comprehensive test for edge cases."""
    pass
```

### Using Fixtures

Common fixtures are defined in `test/unit/conftest.py`:

```python
def test_document_creation(sample_document_data, mock_db):
    """Test document creation with fixtures."""
    # sample_document_data provides test data
    # mock_db provides a mocked database connection
    pass
```

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

@patch("api.db.services.document_service.DocumentService.model")
def test_with_mocked_db(mock_model):
    mock_model.select.return_value.where.return_value.count.return_value = 10
    # Test logic
```

## Coverage Targets

| Component | Current | Target |
|-----------|---------|--------|
| Backend Services | ~30% | 70% |
| Document Parsers | ~10% | 60% |
| LLM Providers | ~20% | 50% |
| API Endpoints | ~40% | 80% |

## CI Integration

Unit tests run automatically on:
- Push to `main` branch
- Pull requests

Coverage reports are:
- Uploaded as artifacts
- Displayed in PR comments (when applicable)

## Troubleshooting

### Import Errors

Ensure PYTHONPATH includes the project root:

```bash
export PYTHONPATH=$(pwd)
uv run pytest test/unit -v
```

### Database Connection Errors

Unit tests use mocks and don't require a running database. If you see connection errors, ensure you're running unit tests, not integration tests.

### Missing Dependencies

Re-sync dependencies:

```bash
uv sync --python 3.10 --all-groups
```

## Contributing

When adding new tests:

1. Follow the directory structure
2. Use appropriate priority markers
3. Add fixtures to `conftest.py` if reusable
4. Update this README if adding new test categories
5. Ensure tests pass locally before submitting PR

```bash
# Verify all tests pass
uv run pytest test/unit --level=p2 -v
```
