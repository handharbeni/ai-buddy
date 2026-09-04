"""Tests for RAG search service."""

import pytest
from unittest.mock import MagicMock, patch
from app.rag.search import SearchService, SearchResult


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    model = MagicMock()
    model.encode.return_value = [0.1, 0.2, 0.3] * 128  # 384-dim
    return model


@pytest.fixture
def search_service(mock_qdrant_client, mock_embedding_model):
    """Create a SearchService instance with mocked dependencies."""
    with patch('app.rag.search.QdrantClient', return_value=mock_qdrant_client), \
         patch('app.rag.search.SentenceTransformer', return_value=mock_embedding_model):
        return SearchService(
            qdrant_client=mock_qdrant_client,
            embedding_model_name="test-model",
            collection_name="regulation_documents",
        )


@pytest.fixture
def mock_search_results():
    """Create mock search results from Qdrant."""
    class MockHit:
        def __init__(self, **kwargs):
            self.payload = kwargs
            self.score = kwargs.get("score", 0.9)
    
    return [
        MockHit(
            document_id="REG_20260101_0001",
            title="Test Regulation 1",
            document_type="PERDA",
            document_number="PERDA-1/2026",
            effective_date="2026-01-01T00:00:00",
            classification="PUBLIC",
            approval_status="APPROVED",
            excerpt="This is a test excerpt about tax regulations.",
            score=0.95,
        ),
        MockHit(
            document_id="REG_20260101_0002",
            title="Test Regulation 2",
            document_type="PERGUB",
            document_number="PERGUB-2/2026",
            effective_date="2026-02-01T00:00:00",
            classification="INTERNAL",
            approval_status="APPROVED",
            excerpt="Another test excerpt about arrears.",
            score=0.85,
        ),
    ]


class TestSearchService:
    """Tests for SearchService."""

    def test_build_filter_basic(self, search_service):
        """Test basic filter building."""
        filter_obj = search_service._build_filter()
        assert filter_obj is not None
        assert hasattr(filter_obj, 'must')

    def test_build_filter_with_document_types(self, search_service):
        """Test filter with document types."""
        filter_obj = search_service._build_filter(
            document_types=["PERDA", "PERGUB"]
        )
        assert filter_obj is not None

    def test_build_filter_with_classification(self, search_service):
        """Test filter with classification."""
        filter_obj = search_service._build_filter(classification="PUBLIC")
        assert filter_obj is not None

    def test_rerank_no_crossencoder(self, search_service):
        """Test reranking when cross-encoder is not available."""
        results = [
            SearchResult(
                document_id="REG_001",
                title="Test 1",
                document_type="PERDA",
                document_number="PERDA-1",
                effective_date="2026-01-01",
                classification="PUBLIC",
                approval_status="APPROVED",
                excerpt="Excerpt 1",
                relevance_score=0.9,
            ),
            SearchResult(
                document_id="REG_002",
                title="Test 2",
                document_type="PERGUB",
                document_number="PERGUB-2",
                effective_date="2026-02-01",
                classification="PUBLIC",
                approval_status="APPROVED",
                excerpt="Excerpt 2",
                relevance_score=0.8,
            ),
        ]
        
        # Should not fail when cross-encoder not available
        reranked = search_service._rerank("test query", results, top_k=2)
        assert len(reranked) == 2
        assert reranked[0].relevance_score >= reranked[1].relevance_score


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SearchResult(
            document_id="REG_001",
            title="Test",
            document_type="PERDA",
            document_number="PERDA-1",
            effective_date="2026-01-01",
            classification="PUBLIC",
            approval_status="APPROVED",
            excerpt="Test excerpt",
            relevance_score=0.95,
            source_url=None,
        )
        
        d = result.to_dict()
        assert d["document_id"] == "REG_001"
        assert d["title"] == "Test"
        assert d["relevance_score"] == 0.95