"""FastAPI application for RAG Pipeline service."""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from qdrant_client import QdrantClient
import tempfile
import os
import logging
from datetime import datetime

from app.rag.ingestion import DocumentIngester
from app.rag.search import SearchService
from app.rag.models import (
    RegulationDocument,
    DocumentType,
    Classification,
    ApprovalStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Pipeline Service",
    version="0.1.0",
    description="Document ingestion and semantic search for BAPENDA regulations.",
)

# Initialize clients
qdrant_client = QdrantClient(host="qdrant", port=6333)
ingester = DocumentIngester(qdrant_client)
search_service = SearchService(qdrant_client)


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    document_types: Optional[List[str]] = None
    classification: Optional[str] = None
    effective_date_from: Optional[str] = None
    effective_date_to: Optional[str] = None
    top_k: int = 5
    rerank: bool = True


class IngestRequest(BaseModel):
    """Document ingestion request."""
    document_id: str
    title: str
    document_type: str
    document_number: str
    issuing_authority: str
    effective_date: str
    classification: str = "INTERNAL"
    version: str = "v1.0"
    tax_types: List[str] = []
    regions: List[str] = []
    keywords: List[str] = []


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        info = ingester.get_collection_info()
        return {
            "status": "healthy",
            "service": "rag-pipeline",
            "collection": info,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/search")
async def search(request: SearchRequest):
    """Search regulation documents."""
    try:
        results = await search_service.search(
            query=request.query,
            document_types=request.document_types,
            classification=request.classification,
            effective_date_from=request.effective_date_from,
            effective_date_to=request.effective_date_to,
            top_k=request.top_k,
            rerank=request.rerank,
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_document(
    metadata: str = Form(...),
    file: UploadFile = File(...),
):
    """Ingest a regulation document.
    
    Args:
        metadata: JSON string with document metadata
        file: Document file (PDF, DOCX, MD, TXT)
    """
    import json
    import hashlib
    
    try:
        # Parse metadata
        meta_dict = json.loads(metadata)
        content_hash_provided = meta_dict.pop("content_hash", None)
        meta_dict.pop("approval_status", None)
        
        # Read file content
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
        
        # Compute content hash
        computed_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        if content_hash_provided and content_hash_provided != computed_hash:
            raise HTTPException(
                status_code=400,
                detail="Content hash mismatch"
            )
        
        # Create document
        document = RegulationDocument(
            document_id=meta_dict["document_id"],
            title=meta_dict["title"],
            document_type=DocumentType(meta_dict["document_type"]),
            document_number=meta_dict["document_number"],
            issuing_authority=meta_dict["issuing_authority"],
            effective_date=datetime.fromisoformat(meta_dict["effective_date"]),
            classification=Classification(meta_dict.get("classification", "INTERNAL")),
            approval_status=ApprovalStatus.APPROVED,
            version=meta_dict.get("version", "v1.0"),
            tax_types=meta_dict.get("tax_types", []),
            regions=meta_dict.get("regions", []),
            keywords=meta_dict.get("keywords", []),
            content_hash=computed_hash,
            source_url=meta_dict.get("source_url"),
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
        )
        
        # Ingest
        chunk_ids = await ingester.ingest_document(document, content)
        
        return {
            "status": "success",
            "document_id": document.document_id,
            "chunks_indexed": len(chunk_ids),
            "content_hash": computed_hash,
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from the index."""
    try:
        chunks_deleted = await ingester.delete_document(document_id)
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_deleted": chunks_deleted,
        }
    except Exception as e:
        logger.error(f"Deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_id}/status")
async def get_document_status(document_id: str):
    """Get document indexing status."""
    status = await ingester.get_document_status(document_id)
    if not status:
        raise HTTPException(status_code=404, detail="Document not found")
    return status


@app.get("/collection/info")
async def get_collection_info():
    """Get collection statistics."""
    return ingester.get_collection_info()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)