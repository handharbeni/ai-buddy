"""Semantic search service for RAG."""

import time
import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
)
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SearchResult:
    """Single search result with metadata and score."""

    def __init__(
        self,
        document_id: str,
        title: str,
        document_type: str,
        document_number: str,
        effective_date: str,
        classification: str,
        approval_status: str,
        excerpt: str,
        relevance_score: float,
        source_url: Optional[str] = None,
    ):
        self.document_id = document_id
        self.title = title
        self.document_type = document_type
        self.document_number = document_number
        self.effective_date = effective_date
        self.classification = classification
        self.approval_status = approval_status
        self.excerpt = excerpt
        self.relevance_score = relevance_score
        self.source_url = source_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "effective_date": self.effective_date,
            "classification": self.classification,
            "approval_status": self.approval_status,
            "excerpt": self.excerpt,
            "relevance_score": self.relevance_score,
            "source_url": self.source_url,
        }


class SearchService:
    """Semantic search service for regulation documents."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model_name: str = "BAAI/bge-m3",
        collection_name: str = "regulation_documents",
    ):
        self.client = qdrant_client
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer(embedding_model_name)

    def _build_filter(
        self,
        document_types: Optional[List[str]] = None,
        classification: Optional[str] = None,
        effective_date_from: Optional[str] = None,
        effective_date_to: Optional[str] = None,
    ) -> Filter:
        """Build Qdrant filter from search parameters."""
        conditions = [
            # Always filter for APPROVED documents
            FieldCondition(
                key="approval_status",
                match=MatchValue(value="APPROVED"),
            )
        ]
        
        if document_types and "ALL" not in document_types:
            conditions.append(
                FieldCondition(
                    key="document_type",
                    match=MatchAny(any=document_types),
                )
            )
        
        if classification and classification != "ALL":
            conditions.append(
                FieldCondition(
                    key="classification",
                    match=MatchValue(value=classification),
                )
            )
        
        # Date range filtering would be added here
        # Note: requires string comparison since Qdrant stores ISO format
        
        return Filter(must=conditions)

    async def search(
        self,
        query: str,
        document_types: Optional[List[str]] = None,
        classification: Optional[str] = None,
        effective_date_from: Optional[str] = None,
        effective_date_to: Optional[str] = None,
        top_k: int = 5,
        rerank: bool = True,
    ) -> Dict[str, Any]:
        """Perform semantic search on regulation documents.
        
        Args:
            query: Natural language search query
            document_types: Filter by document types
            classification: Filter by classification level
            effective_date_from: Minimum effective date
            effective_date_to: Maximum effective date
            top_k: Number of results to return
            rerank: Whether to apply reranking
            
        Returns:
            Search results with metadata
        """
        start_time = time.time()
        query_id = str(uuid4())
        
        # Generate query embedding
        query_vector = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
        ).tolist()
        
        # Build filter
        search_filter = self._build_filter(
            document_types=document_types,
            classification=classification,
            effective_date_from=effective_date_from,
            effective_date_to=effective_date_to,
        )
        
        # Initial retrieval: get more candidates if reranking
        candidate_k = top_k * 3 if rerank else top_k
        
        # Search Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=candidate_k,
            with_payload=True,
        )
        
        # Convert to SearchResult objects
        results = []
        for hit in search_results:
            result = SearchResult(
                document_id=hit.payload.get("document_id"),
                title=hit.payload.get("title"),
                document_type=hit.payload.get("document_type"),
                document_number=hit.payload.get("document_number"),
                effective_date=hit.payload.get("effective_date"),
                classification=hit.payload.get("classification"),
                approval_status=hit.payload.get("approval_status"),
                excerpt=hit.payload.get("excerpt", ""),
                relevance_score=float(hit.score),
                source_url=hit.payload.get("source_url"),
            )
            results.append(result)
        
        # Rerank if requested
        if rerank and len(results) > top_k:
            results = self._rerank(query, results, top_k)
        
        # Limit to top_k
        results = results[:top_k]
        
        search_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query_id": query_id,
            "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "result_count": len(results),
            "search_time_ms": search_time_ms,
            "data": [r.to_dict() for r in results],
        }

    def _rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """Apply cross-encoder reranking for better relevance."""
        try:
            from sentence_transformers import CrossEncoder
            
            # Use a lightweight cross-encoder for reranking
            reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            
            # Prepare pairs for reranking
            pairs = [(query, r.excerpt) for r in results]
            
            # Score with cross-encoder
            scores = reranker.predict(pairs)
            
            # Update relevance scores and sort
            for r, score in zip(results, scores):
                r.relevance_score = float(score)
            
            results = sorted(results, key=lambda x: x.relevance_score, reverse=True)
        except Exception as e:
            logger.warning(f"Reranking failed, using original scores: {e}")
            results = sorted(results, key=lambda x: x.relevance_score, reverse=True)
        
        return results[:top_k]

    async def get_document_chunks(
        self,
        document_id: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a specific document."""
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )]
            ),
            limit=1000,
        )
        
        chunks = []
        for point in results[0]:
            chunks.append({
                "chunk_id": point.id,
                "chunk_index": point.payload.get("chunk_index"),
                "excerpt": point.payload.get("excerpt"),
                "payload": point.payload,
            })
        
        # Sort by chunk index
        chunks.sort(key=lambda x: x.get("chunk_index", 0))
        return chunks