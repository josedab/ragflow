# RFC-0006: Test Coverage Improvement

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 2-3 weeks
**Priority:** P3 (Strategic)

## Summary

Systematically improve test coverage for backend services, document parsers, and critical paths to prevent regressions and enable confident refactoring.

## Motivation

Current test coverage is insufficient:
1. **Limited unit tests**: Many services lack tests
2. **No parser tests**: Document parsers untested
3. **Frontend nearly untested**: Only 1 test file
4. **No integration tests**: API flows untested end-to-end

## Detailed Design

### Coverage Targets

| Component | Current | Target |
|-----------|---------|--------|
| Backend Services | ~30% | 70% |
| Document Parsers | ~10% | 60% |
| LLM Providers | ~20% | 50% |
| API Endpoints | ~40% | 80% |
| Frontend | ~1% | 40% |

### Test Structure

```
test/
├── unit/
│   ├── services/
│   │   ├── test_document_service.py
│   │   ├── test_kb_service.py
│   │   └── ...
│   ├── parsers/
│   │   ├── test_pdf_parser.py
│   │   ├── test_chunking.py
│   │   └── ...
│   └── llm/
│       ├── test_chat_model.py
│       └── test_embedding.py
├── integration/
│   ├── test_document_flow.py
│   ├── test_search_flow.py
│   └── test_agent_flow.py
└── fixtures/
    ├── documents/
    │   ├── sample.pdf
    │   └── sample.docx
    └── responses/
        └── llm_responses.json
```

### Example Tests

```python
# test/unit/services/test_document_service.py
import pytest
from api.db.services.document_service import DocumentService

class TestDocumentService:
    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        # Setup test DB
        yield session
        # Cleanup

    def test_create_document(self, db_session):
        doc = DocumentService.create(
            name="test.pdf",
            kb_id="kb-123",
            user_id="user-456"
        )
        assert doc.id is not None
        assert doc.name == "test.pdf"
        assert doc.status == "pending"

    def test_get_by_id_not_found(self, db_session):
        with pytest.raises(DocumentService.NotFoundError):
            DocumentService.get_by_id("nonexistent")

    @pytest.mark.p1
    def test_delete_soft_deletes(self, db_session):
        doc = DocumentService.create(name="test.pdf", kb_id="kb-123")
        DocumentService.delete(doc.id)

        # Should not find in normal queries
        docs, _ = DocumentService.list(kb_id="kb-123")
        assert doc.id not in [d.id for d in docs]

        # But record still exists
        raw = Document.get_by_id(doc.id)
        assert raw.status == StatusEnum.DELETED


# test/unit/parsers/test_pdf_parser.py
class TestPDFParser:
    @pytest.fixture
    def sample_pdf(self):
        with open("test/fixtures/documents/sample.pdf", "rb") as f:
            return f.read()

    @pytest.mark.p1
    def test_parse_extracts_text(self, sample_pdf):
        parser = RAGFlowPdfParser()
        sections = parser("sample.pdf", sample_pdf)

        assert len(sections) > 0
        assert any("expected text" in s['text'] for s in sections)

    def test_parse_detects_tables(self, sample_pdf):
        parser = RAGFlowPdfParser()
        sections = parser("sample.pdf", sample_pdf)

        tables = [s for s in sections if s.get('type') == 'table']
        assert len(tables) > 0


# test/integration/test_document_flow.py
class TestDocumentFlow:
    @pytest.mark.p1
    def test_upload_to_search(self, client, auth_headers):
        # Upload document
        response = client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", pdf_binary)}
        )
        assert response.json()["code"] == 0
        doc_id = response.json()["data"]["id"]

        # Wait for processing
        wait_for_document_ready(doc_id)

        # Search should find content
        response = client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={"kb_id": kb_id, "query": "test content"}
        )
        assert response.json()["code"] == 0
        assert len(response.json()["data"]["chunks"]) > 0
```

## Implementation Plan

### Week 1: Foundation
1. Set up test database and fixtures
2. Create test utilities and helpers
3. Add service unit tests (high priority services first)

### Week 2: Parsers and LLM
1. Create parser test fixtures (sample documents)
2. Add parser unit tests
3. Add LLM provider tests with mocks

### Week 3: Integration
1. Add integration tests for key flows
2. Set up CI coverage reporting
3. Add coverage gates to CI

## Success Criteria

- [ ] Backend coverage >= 70%
- [ ] All p1 tests passing in CI
- [ ] Coverage report in CI pipeline
- [ ] Test documentation

## Stakeholder Approvals

- [ ] QA Lead
- [ ] Backend Lead
