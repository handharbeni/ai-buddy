# Local AI Data Intelligence Platform

**A universal, deployment-ready platform for building internal AI assistants on top of enterprise databases.**

Customize for any project by setting environment variables — no code changes required.

---

## Quick Start

```bash
# Clone
git clone <repo>
cd DBI-DB

# Configure
cp .env.example .env
# Edit .env with your database credentials and project name

# Run
docker compose up

# Open
open http://localhost:3000
```

Default dev users: `admin/admin123`, `supervisor/super123`, `analyst/analyst123`, `staff/staff123`.

---

## What's Included

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 14 + TypeScript + Linear-style UI | Modern chat interface with multi-conversation support |
| **Backend** | FastAPI + Python 3.11 | REST API with auth, RBAC, audit, rate limiting |
| **LLM** | Ollama (dev) / vLLM (prod) | Local inference with custom models |
| **RAG** | Qdrant + BAAI/bge-m3 | Vector search over regulations & documents |
| **MCP** | Custom Python router | 6+ business tools with RBAC & audit |
| **Databases** | Oracle, PostgreSQL, MySQL | Read-only data access |

---

## Use Cases

This platform is **database-agnostic** and works for any project:

- **Tax authority** (BAPENDA) — revenue analysis, arrears, taxpayer queries
- **Healthcare** — patient records, hospital KPIs
- **Logistics** — shipment tracking, warehouse analytics
- **Finance** — transaction monitoring, audit
- **Government** — public service data, citizen queries

See [docs/MULTI_INDUSTRY_ARCHITECTURE.md](docs/MULTI_INDUSTRY_ARCHITECTURE.md) for adaptation examples.

---

## Documentation

- 📘 [**Deployment Guide**](docs/DEPLOYMENT.md) — Full deployment instructions (local, Docker, production)
- 📐 [Architecture](docs/01_ARCHITECTURE.md)
- 🔐 [Security Model](docs/STRIDE_THREAT_MODEL.md)
- 🏭 [Multi-Industry Adaptation](docs/MULTI_INDUSTRY_ARCHITECTURE.md)
- 📊 [Phase Completion Docs](docs/PHASE11_FULL_ARCHITECTURE.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser → Next.js (3000) → FastAPI (8000) → DBs + LLM      │
│                                                              │
│  Orchestrator: Intent → MCP → RAG → LLM → Natural Language  │
│  Security:    Auth → RBAC → Scope → Audit → Rate Limit      │
└─────────────────────────────────────────────────────────────┘
```

Read-only data access enforced at every layer.

---

## Key Features

- ✅ **Multi-database** — Oracle, PostgreSQL, MySQL with read-only adapters
- ✅ **Multi-DB-per-type** — Configure multiple Oracle/Postgres/MySQL databases
- ✅ **Dynamic branding** — Set `APP_NAME`, `APP_TAGLINE`, `APP_INSTITUTION` to rebrand
- ✅ **RAG pipeline** — Vector search over regulations, SOPs, manuals
- ✅ **MCP tools** — Business tools with RBAC, scope, audit
- ✅ **Local LLM** — Ollama/vLLM, no external API calls
- ✅ **Zero Trust** — RBAC + scope + audit + prompt injection detection
- ✅ **Multi-format output** — JSON, CSV, XLSX, DOCX, PDF, Markdown, HTML
- ✅ **Docker-ready** — One-command deploy with compose
- ✅ **Production-ready** — TLS, secrets, health checks, monitoring hooks

---

## Project Structure

```
.
├── backend/          FastAPI backend (Python)
├── frontend/         Next.js frontend (TypeScript)
├── rag/              RAG ingestion + search
├── docs/             Documentation
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
└── README.md
```

---

## License

Internal / proprietary.
