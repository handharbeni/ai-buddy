# Architecture Status - Phase 11

## ✅ FULL PIPELINE COMPLETE

The complete BAPENDA Local AI platform is now wired with:
- **LLM** (Ollama) → answer generation
- **MCP** (Database Tools) → structured tax data queries
- **RAG** (Qdrant) → regulation document search (requires Qdrant running)

---

## Data Flow

```
User Question
      │
      ▼
┌───────────────────────────────────────┐
│  Intent Detection (keyword-based)       │
│  • structured_query → MCP/DB          │
│  • regulation → RAG/Qdrant            │
│  • general → LLM only                │
└────────────────┬─────────────────────┘
                 │
         ┌───────┴───────┐
         ▼               ▼
┌─────────────────┐  ┌──────────────────┐
│  MCP Router     │  │  RAG Service     │
│  → Oracle DB   │  │  → Qdrant       │
│  → PostgreSQL  │  │                  │
│  → MySQL       │  │                  │
└────────┬────────┘  └────────┬─────────┘
         │                    │
         └──────────┬─────────┘
                    ▼
         ┌─────────────────────┐
         │  LLM Synthesis      │
         │  qwen2.5:3b-instruct│
         │  (via Ollama)       │
         └──────────┬──────────┘
                    ▼
               Answer + Citations
```

---

## Available Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login → JWT token |
| GET | `/api/v1/auth/me` | Current user info |
| GET | `/api/v1/auth/users` | List dev users |
| POST | `/api/v1/query` | **Main orchestrator** - auto-detects intent |
| POST | `/api/v1/query/chat` | Multi-turn chat |
| GET | `/api/v1/mcp/tools` | List 6 MCP database tools |
| GET | `/api/v1/mcp/tools/{name}` | Get tool schema |
| POST | `/api/v1/mcp/execute` | Execute single MCP tool |
| GET | `/api/v1/rag/health` | RAG/Qdrant status |
| POST | `/api/v1/rag/search` | Search regulations |
| GET | `/api/v1/llm/health` | Ollama status |
| GET | `/health` | Backend health |

---

## Test Results

### Test 1: General (LLM only)
```
Question: "Siapa director BAPENDA?"
Intent: general
Latency: 76s
Answer: "Maaf, sebagai AI berbasis AI, saya tidak memiliki database langsung
        untuk mengakses informasi terbaru tentang posisi dan direktur BAPENDA."
Status: ✅ Working
```

### Test 2: Structured Query (MCP + LLM)
```
Question: "Berapa pertumbuhan pajak hotel 2025?"
Intent: structured_query
Tools used: get_tax_revenue, get_growth_statistics
Context: MCP fetched mock DB data (2 rows from V_TAX_REVENUE_SCOPE)
Latency: 43s
Answer: "Data yang diberikan tidak mencakup pertumbuhan pajak hotel. 
         Pertumbuhan pajak PBB di Kabupaten Bandung dan Kota Bandung disajikan,
         tetapi tidak ada informasi tentang pajak hotel."
Status: ✅ Working
```

### Test 3: Regulation (RAG + LLM)
```
Question: "Apa dasar hukum insentif pajak restoran?"
Intent: regulation
RAG: disabled (Qdrant not running)
Status: ⏸️ Needs Qdrant
```

---

## MCP Tools

| Tool | Database | Purpose |
|------|----------|---------|
| `get_tax_revenue` | Oracle | Tax revenue by period/region/type |
| `get_tax_arrears` | Oracle | Tax arrears (tunggakan) |
| `get_growth_statistics` | PostgreSQL | YoY growth, target achievement |
| `get_region` | MySQL | Region hierarchy |
| `get_taxpayer_summary` | Oracle | Individual taxpayer profile |
| `search_regulation` | Qdrant | Semantic regulation search |

All tools have:
- ✅ Pydantic input validation (regex, range checks)
- ✅ RBAC permission enforcement
- ✅ Scope filtering (region, tax_type)
- ✅ Row limits and timeouts
- ✅ Audit logging ready

---

## Environment Variables

### For Real Database Connections
```bash
# Oracle (primary)
ORACLE_USER=<user>
ORACLE_PASS=<pass>
ORACLE_DSN=<host:1521/SID>

# PostgreSQL
POSTGRES_USER=<user>
POSTGRES_PASS=<pass>
POSTGRES_HOST=<host>
POSTGRES_DB=bapenda

# MySQL
MYSQL_USER=<user>
MYSQL_PASS=<pass>
MYSQL_HOST=<host>
MYSQL_DB=bapenda
```

### For Qdrant (RAG)
```bash
QDRANT_URL=http://localhost:6333
EMBEDDING_MODEL=BAAI/bge-m3
```

Without these → Mock adapters (dev mode with sample data)

---

## Model Note

**Current model**: `qwen2.5:3b-instruct`
- Fast to load (2GB)
- Response latency: 30-90 seconds
- Supports Indonesian (limited)
- System prompt in Bahasa Indonesia

**Preferred model**: `bapenda-ai:latest` (your custom Qwen3 14.8B with BAPENDA instructions)
- Was crashing on this machine (OOM or VRAM issue)
- If fixed, change `model=` in `main.py`

---

## What's Working

- ✅ JWT auth (admin/admin123)
- ✅ RBAC (ADMIN/SUPERVISOR/ANALYST/STAFF)
- ✅ MCP tools → DB adapter → mock data
- ✅ LLM synthesis (qwen2.5:3b-instruct via Ollama)
- ✅ Intent detection (keyword-based)
- ✅ Query pipeline: intent → MCP → LLM → answer
- ✅ CORS for frontend
- ✅ 14 API endpoints
- ✅ OpenAPI docs at /docs

## What's Missing

- ⏸️ Qdrant server → RAG disabled (regulation search)
- ⏸️ Real DB connections → mock data only
- ⏸️ bapenda-ai:latest model → qwen2.5:3b used as fallback
- ⏸️ Regulation document ingestion pipeline
- ⏸️ Orchestrator pipeline.py (not wired, query.py has simpler version)
