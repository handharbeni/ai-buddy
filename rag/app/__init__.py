"""RAG Pipeline package for BAPENDA Local AI Platform.

Provides document ingestion, embedding generation, and semantic retrieval
for regulations (Perda, Pergub, SOP, Surat Edaran).
"""

from app.rag.ingestion import DocumentIngester
from app.rag.retrieval import SearchService
from app.rag.models import RegulationDocument

__all__ = ["DocumentIngester", "SearchService", "RegulationDocument"]
