"""Tests for RAG document ingestion."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.rag.ingestion import DocumentIngester
from app.rag.models import RegulationDocument, DocumentType, Classification, ApprovalStatus


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock()
    client.get_collections.return_value = MagicMock(collections=[])
    client.create_collection = MagicMock()
    client.upsert = MagicMock()
    client.scroll = MagicMock(return_value=([], None))
    client.delete = MagicMock()
    return client


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    model = MagicMock()
    model.encode.return_value = [[0.1, 0.2, 0.3] * 128]  # 384-dim embedding
    model.get_sentence_embedding_dimension.return_value = 384
    return model


@pytest.fixture
def ingester(mock_qdrant_client, mock_embedding_model):
    """Create a DocumentIngester instance with mocked dependencies."""
    with patch('app.rag.ingestion.QdrantClient', return_value=mock_qdrant_client), \
         patch('app.rag.ingestion.SentenceTransformer', return_value=mock_embedding_model):
        return DocumentIngester(qdrant_client=mock_qdrant_client, embedding_model="test-model")


@pytest.fixture
def sample_document():
    """Create a sample regulation document."""
    return RegulationDocument(
        document_id="REG_20260101_0001",
        title="Sample Regulation",
        document_type=DocumentType.PERDA,
        document_number="PERDA-1/2026",
        issuing_authority="DPRD Kabupaten Test",
        effective_date=datetime(2026, 1, 1),
        classification=Classification.PUBLIC,
        approval_status=ApprovalStatus.APPROVED,
        version="v1.0",
        tax_types=["PBB"],
        regions=["3201"],
        keywords=["sample", "test"],
        content_hash="a" * 64,  # 64 hex chars
        source_url=None,
        created_at=datetime(2026, 1, 1),
        approved_at=datetime(2026, 1, 1),
        approved_by="admin",
    )


@pytest.mark.asyncio
async def test_ingester_initialization(ingester, mock_qdrant_client, mock_embedding_model):
    """Test that the ingester initializes correctly."""
    assert ingester is not None
    assert ingester.collection_name == "regulation_documents"
    assert ingester.chunk_size == 512
    assert ingester.chunk_overlap == 50
    mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_compute_hash(ingester):
    """Test hash computation."""
    content = "Hello, World!"
    hash_result = ingester.compute_hash(content)
    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)


@pytest.mark.asyncio
async def test_chunk_text(ingester):
    """Test text chunking."""
    text = "a" * 1000  # 1000 'a' characters
    chunks = ingester.chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 512 for c in chunks)
    # Check overlap
    if len(chunks) > 1:
        assert chunks[0][-50:] == chunks[1][:50]


@pytest.mark.asyncio
async def test_ingest_document_success(ingester, sample_document, mock_qdrant_client):
    """Test successful document ingestion."""
    content = "This is a test document. " * 100  # ~2500 chars
    
    chunk_ids = await ingester.ingest_document(sample_document, content)
    
    assert isinstance(chunk_ids, list)
    assert len(chunk_ids) > 0
    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_document_not_approved(ingester, sample_document):
    """Test that non-approved documents are rejected."""
    sample_document.approval_status = ApprovalStatus.DRAFT
    content = "Test content"
    
    with pytest.raises(ValueError, match="not APPROVED"):
        await ingester.ingest_document(sample_document, content)


@pytest.mark.asyncio
async def test_ingest_document_hash_mismatch(ingester, sample_document):
    """Test that hash mismatch is detected."""
    sample_document.content_hash = "b" * 64  # Wrong hash
    content = "Test content"
    
    with pytest.raises(ValueError, match="Content hash mismatch"):
        await ingester.ingest_document(sample_document, content)


@pytest.mark.asyncio
async def test_delete_document(ingester, mock_qdrant_client):
    """Test document deletion."""
    mock_qdrant_client.scroll.return_value = ([
        MagicMock(id="chunk1"),
        MagicMock(id="chunk2"),
    ], None)
    
    deleted = await ingester.delete_document("REG_20260101_0001")
    
    assert deleted == 2
    mock_qdrant_client.delete.assert_called_once_with(
        collection_name="regulation_documents",
        points_selector=["chunk1", "chunk2"],
    )


@pytest.mark.asyncio
async def test_get_document_status(ingester, mock_qdrant_client):
    """Test getting document status."""
    mock_point = MagicMock()
    mock_point.payload = {
        "chunk_count": 3,
        "approval_status": "APPROVED",
        "version": "v1.0",
        "content_hash": "a" * 64,
    }
    mock_qdrant_client.scroll.return_value = ([mock_point], None)
    
    status = await ingester.get_document_status("REG_20260101_0001")
    
    assert status is not None
    assert status["document_id"] == "REG_20260101_0001"
    assert status["chunk_count"] == 3
    assert status["approval_status"] == "APPROVED"


@pytest.mark.asyncio
async def test_get_collection_info(ingester, mock_qdrant_client):
    """Test getting collection info."""
    mock_qdrant_client.get_collection.return_value = MagicMock(
        vectors_count=100,
        indexed_vectors_count=100,
        points_count=100,
    )
    
    info = ingester.get_collection_info()
    
    assert info["collection_name"] == "regulation_documents"
    assert info["vectors_count"] == 100
    assert info["indexed_vectors_count"] == 100
    assert info["points_count"] == 100