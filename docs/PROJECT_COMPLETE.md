# BAPENDA Local AI Data Intelligence Platform - Project Status

**Phase 11: Full Architecture (LLM + MCP + RAG)** — ✅ COMPLETE

---

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **Frontend** | ✅ | Next.js 14 dashboard at http://localhost:3000 |
| **Backend** | ✅ | FastAPI at http://localhost:8000 |
| **LLM (Ollama)** | ✅ | `bapenda-ai:latest` (custom, qwen2.5:3b-instruct base) |
| **MCP Router** | ✅ | 6 DB tools wired, mock data |
| **RAG (Qdrant)** | ⏸️ | Code ready, needs Qdrant server |
| **Auth** | ✅ | JWT, RBAC, 4 roles |
| **CORS** | ✅ | Frontend connects |

---

## What Works End-to-End

```
User → Frontend → Backend (auth) → /api/v1/query
        ↓
   Intent Detection (keyword-based)
        ↓
   ┌────────┴────────┐
   │                 │
MCP/DB         RAG/Qdrant
(mock data)   (disabled)
   │                 │
   └────────┬────────┘
            ↓
   LLM (Ollama) → Answer
```

**Verified**:
- ✅ Auth: admin/admin123 → JWT
- ✅ MCP tools: get_tax_revenue, get_growth_statistics, etc.
- ✅ Query intent detection
- ✅ LLM synthesis
- ✅ Mock data flow

**Pending**:
- ⏸️ Qdrant server (for regulation search)
- ⏸️ Real DB connection strings
- ⏸️ bapenda-ai:latest model (rebuild when fixed)
- ⏸️ Document ingestion pipeline

---

## Quick Start

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Open http://localhost:3000
# Login: admin / admin123
# Ask: "Berapa pertumbuhan pajak hotel 2025?"
```

---

## Documentation

- `docs/PHASE11_FULL_ARCHITECTURE.md` - Complete architecture details
- `docs/01_ARCHITECTURE.md` - System design
- `docs/02_THREAT_MODEL.md` - STRIDE analysis
- `docs/04_RBAC_MATRIX.md` - Role/permission matrix
- `docs/05_MCP_CONTRACT.md` - MCP tool specifications

---

## Environment Setup for Production

```bash
# Real databases
export ORACLE_USER=...
export ORACLE_PASS=...
export ORACLE_DSN=host:1521/SID

export POSTGRES_USER=...
export POSTGRES_PASS=...
export POSTGRES_HOST=...

export MYSQL_USER=...
export MYSQL_PASS=...
export MYSQL_HOST=...

# RAG
export QDRANT_URL=http://qdrant:6333
export EMBEDDING_MODEL=BAAI/bge-m3

# LLM
export LLM_PROVIDER=vllm
export VLLM_URL=http://vllm:8000
```
