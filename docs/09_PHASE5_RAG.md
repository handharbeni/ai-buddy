# Phase 5: RAG Pipeline - BAPENDA Local AI Data Intelligence Platform

## Overview

This document defines the RAG (Retrieval-Augmented Generation) pipeline for the BAPENDA Local AI Platform. The system enables natural language queries about tax regulations, tax data, and growth statistics by retrieving and synthesizing information from approved documents and official databases.

## Key Components

| Component | Technology | Description |
|-----------|------------|-------------|
| Document Ingestion | PDF, DOCX, MD parsers | Converts official documents into structured data |
| Embedding Model | bge-m3 (768-dim) | Semantic vector generation for documents |
| Vector Database | Qdrant 1.8 | Stores document embeddings with metadata filtering |
| Query Processing | FastAPI + LLM | Natural language understanding and tool orchestration |
| Document Approval | Metadata-driven workflow | Only APPROVED documents are searchable |

## Core Components

### 1. Document Ingestion Pipeline

- **Supported Formats**: PDF, DOCX, Markdown, TXT
- **Metadata Extraction**: 
  - Title, version, effective_date, classification, approval_status
  - tax_types, regions, keywords
- **Chunking Strategy**: Semantic chunking with 512-token windows and 50% overlap
- **Metadata Embedding**: Each chunk gets embedded with bge-m3 model

### 2. Vector Database (Qdrant)

- **Collection**: `regulation_documents`
- **Primary Key**: document_id (REG_YYYYMMDD_####)
- **Metadata Fields**:
  - title, document_number, effective_date
  - classification (PUBLIC/INTERNAL/RESTRICTED)
  - approval_status (APPROVED/REJECTED/etc.)
  - tax_types, regions (for filtering)
  - content_hash (SHA-256 verification)
  - embedding_vector (1024-dim bge-m3)
- **Indexing**: IVF-PQ quantization for efficient similarity search

### 3. Document Lifecycle

| Stage | Process | Validation |
|---------|---------|------------|
| Ingestion | Parse → Chunk → Embed | Document hash verification |
| Approval | Human review workflow | Approval_status = APPROVED |
| Indexing | Vector embedding + metadata | Only APPROVED documents indexed |
| Retrieval | Semantic search + filtering | Only APPROVED documents returned |
| Archival | Move to cold storage | Hash verification maintained |

## Data Flow

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  Intent Classification      │
│  (LLM determines intent)    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Tool Planning              │
│  - Determine required tools│
│  - Check user permissions  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  RAG Retrieval              │
│  - Query Qdrant for regulation docs │
│  - Apply approval_status filter │
│  - Retrieve relevant documents │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Response Synthesis         │
│  - LLM generates answer with citations │
│  - Cite approved documents only │
└─────────────────────────────┘
```

## Security Requirements

| Requirement | Implementation |
|-------------|--------------|
| REQ-SEC-006 | Only APPROVED documents searchable |
| REQ-SEC-006 | Content hash verification at retrieval |
| REQ-SEC-006 | Versioned documents (immutable once APPROVED) |
| REQ-SEC-007 | Audit trail for document approvals |
| REQ-SEC-007 | Document classification enforced at retrieval |

## Technical Requirements

| Component | Specification |
|-----------|---------------|
| **Document Format** | PDF, DOCX, Markdown, TXT |
| **Embedding Model** | BAAI/bge-m3 (768-dim) |
| **Vector DB** | Qdrant 1.8+ |
| **Chunking** | Semantic chunking (512 tokens, 50% overlap) |
| **Search** | Vector similarity + reranking |
| **Document Lifecycle** | Draft → Review → Approved → Archived |

## Security Requirements

| Threat | Mitigation |
|----------|------------|
| Document poisoning | Immutable document versions, hash verification |
| Unauthorized access | Role-based access control on document metadata |
| PII leakage | Local LLM only, PII redaction pre-ingestion |
| RAG poisoning | Approval workflow, immutable versions |
| Data leakage | Scope enforcement in RAG retrieval |

## Implementation Roadmap

| Task | Description | Priority |
|--------|-----------|----------|
| Document Parser | Parse PDF/DOCX/MD files | High |
| Embedding Pipeline | Generate embeddings for chunks | High |
| Qdrant Setup | Configure vector database | High |
| Approval Workflow | Document approval process | High |
| Search Service | Implement query API with filtering | High |
| Testing | Unit tests for ingestion and retrieval | Medium |

## Files Created

- `docs/09_PHASE5_RAG.md` - This document
- `backend/app/rag/` directory structure
- `rag/tests/` directory with test cases

## Next Steps

1. **Review** the RAG documentation
2. **Approve** the architecture before proceeding to implementation
3. **Phase 5** will begin with database adapter implementation for RAG data sources

**Next Action**: Please review the RAG documentation and approve the architecture before I begin implementation.