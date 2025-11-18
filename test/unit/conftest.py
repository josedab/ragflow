#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
Pytest configuration and fixtures for unit tests.

This module provides fixtures for database sessions, mock data,
and test utilities used across unit tests.
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure test environment before importing project modules
os.environ.setdefault("REDIS_CONN", "redis://localhost:6379/0")
os.environ.setdefault("DOC_ENGINE", "elasticsearch")


# Test markers configuration
MARKER_EXPRESSIONS = {
    "p1": "p1",
    "p2": "p1 or p2",
    "p3": "p1 or p2 or p3",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom pytest options."""
    parser.addoption(
        "--level",
        action="store",
        default="p2",
        choices=list(MARKER_EXPRESSIONS.keys()),
        help=f"Test level ({'/'.join(MARKER_EXPRESSIONS)}): p1=smoke, p2=core, p3=full",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest based on command line options."""
    level = config.getoption("--level")
    config.option.markexpr = MARKER_EXPRESSIONS[level]

    # Register custom markers
    config.addinivalue_line("markers", "p1: Priority 1 (smoke) tests")
    config.addinivalue_line("markers", "p2: Priority 2 (core) tests")
    config.addinivalue_line("markers", "p3: Priority 3 (full) tests")


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database connection context."""
    mock_conn = MagicMock()
    with patch("api.db.db_models.DB.connection_context") as mock_context:
        mock_context.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_conn


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    with patch("rag.utils.redis_conn.REDIS_CONN") as mock_redis:
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.xadd.return_value = "1-0"
        yield mock_redis


# ==============================================================================
# Test Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_user_id():
    """Return a sample user ID."""
    return "test-user-001"


@pytest.fixture
def sample_tenant_id():
    """Return a sample tenant ID."""
    return "test-tenant-001"


@pytest.fixture
def sample_kb_id():
    """Return a sample knowledge base ID."""
    return "test-kb-001"


@pytest.fixture
def sample_doc_id():
    """Return a sample document ID."""
    return "test-doc-001"


@pytest.fixture
def sample_document_data(sample_kb_id, sample_user_id):
    """Return sample document data for testing."""
    return {
        "id": "test-doc-001",
        "name": "test_document.pdf",
        "kb_id": sample_kb_id,
        "created_by": sample_user_id,
        "location": "/tmp/test_document.pdf",
        "size": 1024,
        "type": "pdf",
        "suffix": "pdf",
        "status": "1",  # Valid
        "run": "0",  # Pending
        "progress": 0.0,
        "progress_msg": "",
        "token_num": 0,
        "chunk_num": 0,
        "parser_id": "naive",
        "parser_config": {"chunk_token_num": 128},
        "create_time": int(datetime.now().timestamp() * 1000),
        "update_time": int(datetime.now().timestamp() * 1000),
    }


@pytest.fixture
def sample_kb_data(sample_tenant_id, sample_user_id):
    """Return sample knowledge base data for testing."""
    return {
        "id": "test-kb-001",
        "name": "Test Knowledge Base",
        "tenant_id": sample_tenant_id,
        "created_by": sample_user_id,
        "description": "A test knowledge base",
        "language": "English",
        "embd_id": "BAAI/bge-small-en-v1.5@Builtin",
        "permission": "me",
        "doc_num": 0,
        "token_num": 0,
        "chunk_num": 0,
        "status": "1",
        "parser_id": "naive",
        "parser_config": {"chunk_token_num": 128},
        "create_time": int(datetime.now().timestamp() * 1000),
        "update_time": int(datetime.now().timestamp() * 1000),
    }


@pytest.fixture
def sample_chunk_data(sample_doc_id, sample_kb_id):
    """Return sample chunk data for testing."""
    return {
        "id": "test-chunk-001",
        "content_with_weight": "This is test content for the chunk.",
        "content_ltks": "test content chunk",
        "content_sm_ltks": "test content",
        "doc_id": sample_doc_id,
        "kb_id": sample_kb_id,
        "important_kwd": ["test", "content"],
        "positions": [[0, 100]],
        "available_int": 1,
    }


# ==============================================================================
# File Fixtures
# ==============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_pdf_path():
    """Return the path to a sample PDF fixture."""
    return os.path.join(
        os.path.dirname(__file__),
        "../fixtures/documents/sample.pdf"
    )


@pytest.fixture
def sample_pdf_binary(sample_pdf_path):
    """Return binary content of the sample PDF."""
    if os.path.exists(sample_pdf_path):
        with open(sample_pdf_path, "rb") as f:
            return f.read()
    # Return minimal PDF if fixture doesn't exist
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n299\n%%EOF"


@pytest.fixture
def sample_text_content():
    """Return sample text content for testing chunking."""
    return """
    This is a sample document for testing purposes.

    Section 1: Introduction

    This section contains introductory text that will be used to test
    the document parsing and chunking functionality. It includes multiple
    paragraphs and sections to ensure proper handling.

    Section 2: Main Content

    The main content section provides more detailed information that
    can be used to test search and retrieval functions. This text should
    be long enough to create multiple chunks.

    Section 3: Conclusion

    The conclusion wraps up the document with summary information.
    """


# ==============================================================================
# Mock Model Fixtures
# ==============================================================================

@pytest.fixture
def mock_llm_response():
    """Return a mock LLM response."""
    return {
        "text": "This is a mock LLM response for testing.",
        "token_count": 10,
    }


@pytest.fixture
def mock_embedding_response():
    """Return a mock embedding response."""
    import numpy as np
    return {
        "vectors": np.random.rand(3, 384).astype(np.float32),
        "token_count": 15,
    }


@pytest.fixture
def mock_chat_model():
    """Create a mock chat model."""
    mock = MagicMock()
    mock.chat.return_value = ("Mock response", 10)
    mock.chat_streamly.return_value = iter([("Mock ", 2), ("response", 3)])
    return mock


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    import numpy as np
    mock = MagicMock()
    mock.encode.return_value = (np.random.rand(1, 384).astype(np.float32), 5)
    mock.encode_queries.return_value = (np.random.rand(384).astype(np.float32), 3)
    return mock


# ==============================================================================
# Service Mock Fixtures
# ==============================================================================

@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    with patch("api.utils.file_utils.STORAGE_IMPL") as mock:
        mock.put.return_value = True
        mock.get.return_value = b"test content"
        mock.rm.return_value = True
        mock.obj_exist.return_value = True
        yield mock


@pytest.fixture
def mock_doc_store():
    """Create a mock document store."""
    with patch("rag.utils.doc_store_conn.DOC_STORE") as mock:
        mock.search.return_value = ([], 0)
        mock.insert.return_value = True
        mock.delete.return_value = True
        yield mock


# ==============================================================================
# Utility Functions
# ==============================================================================

def create_mock_document(**kwargs):
    """Create a mock Document object with default values."""
    defaults = {
        "id": "mock-doc-001",
        "name": "mock_document.pdf",
        "kb_id": "mock-kb-001",
        "created_by": "mock-user-001",
        "location": "/tmp/mock_document.pdf",
        "size": 1024,
        "type": "pdf",
        "suffix": "pdf",
        "status": "1",
        "run": "0",
        "progress": 0.0,
        "progress_msg": "",
        "token_num": 0,
        "chunk_num": 0,
        "parser_id": "naive",
        "parser_config": {},
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def create_mock_kb(**kwargs):
    """Create a mock Knowledgebase object with default values."""
    defaults = {
        "id": "mock-kb-001",
        "name": "Mock Knowledge Base",
        "tenant_id": "mock-tenant-001",
        "created_by": "mock-user-001",
        "description": "Mock KB",
        "language": "English",
        "embd_id": "BAAI/bge-small-en-v1.5@Builtin",
        "permission": "me",
        "doc_num": 0,
        "token_num": 0,
        "chunk_num": 0,
        "status": "1",
        "parser_id": "naive",
        "parser_config": {},
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock
