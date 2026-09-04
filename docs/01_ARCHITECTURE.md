# Architecture Document

## System Overview

**Project:** BAPENDA Local AI Data Intelligence Platform
**Version:** 1.0
**Classification:** Internal - Confidential

## High-Level Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Staff     │────▶│  Next.js    │────▶│  FastAPI    │
│  (Client)   │     │  Frontend   │     │  Gateway    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
           ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
           │   Auth/RBAC     │         │  Qwen Local     │         │   MCP Router    │
           │   Service       │         │  LLM (Ollama)   │         │                 │
           └────────┬────────┘         └────────┬────────┘         └────────┬────────┘
                    │                           │                           │
                    │                    ┌──────┴──────┐                    │
                    │                    │             │                    │
                    ▼                    ▼             ▼                    ▼
           ┌─────────────────┐  ┌───────────────┐ ┌───────────┐  ┌─────────────────┐
           │   Oracle DB     │  │ PostgreSQL DB │ │ MySQL DB  │  │     Qdrant      │
           │  (Tax Revenue,  │  │  (Growth      │ │ (Region   │  │  (RAG Vector    │
           │   Arrears)      │  │   Statistics) │ │  Master)  │  │   Store)        │
           └─────────────────┘  └───────────────┘ └───────────┘  └─────────────────┘
```

## Component Responsibilities

### Frontend (Next.js)
- Authentication UI (Login, SSO integration)
- Chat interface for natural language queries
- Role-based dashboard
- Audit log viewer (Admin/Supervisor)
- Settings & profile management

### API Gateway (FastAPI)
- Request routing & validation
- Authentication middleware (JWT verification)
- RBAC enforcement per endpoint
- Rate limiting
- Request/response logging for audit
- MCP tool orchestration
- LLM prompt assembly

### Auth/RBAC Service
- User authentication (LDAP/OIDC)
- Role assignment (ADMIN, SUPERVISOR, ANALYST, STAFF)
- Data scope enforcement (region, department, tax_type)
- Permission matrix evaluation
- Session management
- Token issuance & validation

### Local LLM (Qwen via Ollama/vLLM)
- Intent classification
- Tool planning & selection
- Natural language generation
- Result explanation & citation
- **Never**: Execute SQL, determine permissions, access credentials

### MCP Router
- Tool registry & discovery
- Input/output schema validation
- Permission checking per tool
- Scope filtering on results
- Timeout & result limit enforcement
- Tool execution coordination

### Database Layer (Read-Only)
- **Oracle**: Tax revenue, arrears, collections
- **PostgreSQL**: Growth statistics, analytics
- **MySQL**: Region master, taxpayer registry
- All connections via `AI_READONLY` user
- Parameterized queries only
- Approved views preferred over raw tables

### RAG System (Qdrant)
- Document ingestion pipeline (Perda, Pergub, SOP, Surat Edaran)
- Metadata: title, version, effective_date, classification, approval_status
- Only APPROVED documents indexed
- Semantic search with reranking
- Retrieved text treated as untrusted

## Data Flow

```
User Query
    │
    ▼
┌─────────────────────┐
│  Auth Middleware    │──▶ Verify JWT, extract user_id, role, scope
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Intent Detection   │──▶ LLM classifies: revenue, arrears, regulation, etc.
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Tool Planning      │──▶ LLM selects MCP tools based on intent + permissions
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  MCP Execution      │──▶ Router validates permission, executes tools
│  (Parallel)         │     Applies scope filters, enforces limits
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  RAG Retrieval      │──▶ If regulation query: search Qdrant
│  (Conditional)      │     Filter by approval_status=APPROVED
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Response Synthesis │──▶ LLM generates answer with citations
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Audit Logging      │──▶ Record: request_id, user, role, scope, intent,
└─────────────────────┘     tools, latency, status
```

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Next.js | 14+ (App Router) |
| Frontend Language | TypeScript | 5+ |
| Backend | FastAPI | 0.110+ |
| Backend Language | Python | 3.12+ |
| LLM Runtime (Dev) | Ollama | Latest |
| LLM Runtime (Prod) | vLLM | Latest |
| LLM Model | Qwen2.5 | 14B/32B |
| Vector DB | Qdrant | 1.8+ |
| Oracle | Oracle DB | 19c+ |
| PostgreSQL | PostgreSQL | 15+ |
| MySQL | MySQL | 8.0+ |
| Message Queue | Redis | 7+ |
| Container | Docker | 24+ |
| Orchestration | Docker Compose | 2.24+ |

## Non-Functional Requirements

- **Availability**: 99.5% (internal business hours)
- **Latency**: P95 < 3s for simple queries, < 10s for complex multi-tool
- **Throughput**: 50 concurrent users
- **Data Freshness**: RAG sync daily, DB real-time
- **Audit Retention**: 7 years