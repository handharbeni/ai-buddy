"""Document ingestion pipeline for RAG."""

import hashlib
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from app.rag.models import (
    RegulationDocument,
    DocumentType,
    Classification,
    ApprovalStatus,
)

logger = logging.getLogger(__name__)


class DocumentIngester:
    """Handles document parsing, chunking, embedding, and indexing."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        collection_name: str = "regulation_documents",
    ):
        self.client = qdrant_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection_name = collection_name
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.collection_name}")

    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of document content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            if end == len(text):
                break
            start = end - self.chunk_overlap
        return chunks

    async def ingest_document(
        self,
        document: RegulationDocument,
        content: str,
    ) -> List[str]:
        """Ingest a regulation document into the vector store.
        
        Args:
            document: RegulationDocument metadata
            content: Full text content of the document
            
        Returns:
            List of chunk IDs that were indexed
        """
        # Verify document is approved
        if document.approval_status != ApprovalStatus.APPROVED:
            raise ValueError(
                f"Document {document.document_id} is not APPROVED "
                f"(status: {document.approval_status})"
            )
        
        # Verify content hash
        content_hash = self.compute_hash(content)
        if content_hash != document.content_hash:
            raise ValueError(
                f"Content hash mismatch for {document.document_id}"
            )
        
        # Chunk the content
        chunks = self.chunk_text(content)
        chunk_ids = []
        
        # Generate embeddings for all chunks
        embeddings = self.embedding_model.encode(
            chunks,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        
        # Create points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = f"{document.document_id}_chunk_{i}"
            chunk_ids.append(point_id)
            
            payload = {
                "document_id": document.document_id,
                "title": document.title,
                "document_type": document.document_type.value,
                "document_number": document.document_number,
                "issuing_authority": document.issuing_authority,
                "effective_date": document.effective_date.isoformat(),
                "classification": document.classification.value,
                "approval_status": document.approval_status.value,
                "version": document.version,
                "tax_types": document.tax_types,
                "regions": document.regions,
                "keywords": document.keywords,
                "content_hash": content_hash,
                "chunk_index": i,
                "chunk_count": len(chunks),
                "excerpt": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                "source_url": document.source_url,
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload,
            ))
        
        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        
        logger.info(
            f"Ingested document {document.document_id}: "
            f"{len(chunks)} chunks, hash={content_hash[:8]}..."
        )
        
        return chunk_ids

    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        # Find all chunks for this document
        result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=10000,
        )
        
        chunk_ids = [point.id for point in result[0]]
        
        if chunk_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids,
            )
            logger.info(f"Deleted document {document_id}: {len(chunk_ids)} chunks")
        
        return len(chunk_ids)

    async def update_document(
        self,
        document: RegulationDocument,
        content: str,
    ) -> List[str]:
        """Update an existing document (re-ingest)."""
        # Delete old version
        await self.delete_document(document.document_id)
        
        # Ingest new version
        return await self.ingest_document(document, content)

    async def get_document_status(self, document_id: str) -> Optional[dict]:
        """Get status of an indexed document."""
        result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=1,
        )
        
        if not result[0]:
            return None
        
        point = result[0][0]
        return {
            "document_id": document_id,
            "chunk_count": point.payload.get("chunk_count"),
            "approval_status": point.payload.get("approval_status"),
            "version": point.payload.get("version"),
            "content_hash": point.payload.get("content_hash"),
        }

    def get_collection_info(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "collection_name": self.collection_name,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "embedding_dim": self.embedding_dim,
        }