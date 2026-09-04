# BAPENDA Local AI Data Intelligence Platform - Complete Index

**Project**: BAPENDA Local AI Data Intelligence Platform
**Version**: 1.0
**Status**: Phase 1 Complete - Ready for Phase 2

## Overview

Internal AI platform for Bapenda using:
- Local LLM (Qwen2.5 via Ollama/vLLM)
- MCP (Model Context Protocol)
- RAG (Retrieval-Augmented Generation)
- Oracle, PostgreSQL, MySQL (read-only)
- Qdrant (vector database)
- Next.js (frontend)
- FastAPI (backend)

## Documentation

| # | Document | Purpose | Status |
|---|----------|---------|--------|
| 01 | [Architecture](./01_ARCHITECTURE.md) | System architecture, components, data flow | ✅ |
| 02 | [Threat Model](./02_THREAT_MODEL.md) | STRIDE analysis, risks, mitigations | ✅ |
| 03 | [Trust Boundary](./03_TRUST_BOUNDARY.md) | Trust domains, boundary rules, enforcement | ✅ |
| 04 | [RBAC Matrix](./04_RBAC_MATRIX.md) | Role permissions, scope rules, API access | ✅ |
| 05 | [MCP Contract](./05_MCP_CONTRACT.md) | 6 MCP tool specs, schemas, constraints | ✅ |
| 06 | [Semantic Domain Model](./06_SEMANTIC_DOMAIN_MODEL.md) | Entities, fields, relationships, enums | ✅ |
| 07 | [Docker Topology](./07_DOCKER_TOPOLOGY.md) | Container architecture, networks, secrets | ✅ |
| 08 | [Development Roadmap](./08_DEVELOPMENT_ROADMAP.md) | 13-phase delivery plan, approval gates | ✅ |
| 09 | [Phase 1 Complete](./09_PHASE1_COMPLETE.md) | Repository skeleton summary | ✅ |

## Repository Structure

```
bapenda-ai/
├── frontend/          # Next.js 14 (TypeScript)
├── backend/           # FastAPI (Python 3.12+)
├── mcp/               # MCP Router service
├── rag/               # RAG document ingestion
├── docs/              # Architecture & documentation
├── docker/            # Docker configs
├── tests/             # E2E tests
└── .github/           # CI/CD workflows
```

## Quick Start

### Development
```bash
cp .env.example .env
make dev
```

### Production
```bash
docker compose -f docker-compose.prod.yml up -d
```

## Commands

```bash
make help       # Show all commands
make dev        # Start dev environment
make stop       # Stop services
make logs       # View logs
make test       # Run tests
make lint       # Lint code
make format     # Format code
make build      # Build images
make clean      # Clean up
```

## Security

- **Classification**: Internal - Confidential
- **Access**: Zero Trust network
- **Authentication**: OIDC/LDAP
- **Authorization**: RBAC + Data Scope
- **Data**: Read-only database access
- **Audit**: Append-only logs (7 year retention)

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Architecture Documentation | ✅ Complete |
| 1 | Repository Skeleton | ✅ Complete |
| 2 | Database Adapters | ⏳ Pending |
| 3 | Auth/RBAC | ⏳ Pending |
| 4 | MCP Router | ⏳ Pending |
| 5 | RAG Pipeline | ⏳ Pending |
| 6 | Local LLM | ⏳ Pending |
| 7 | Orchestrator | ⏳ Pending |
| 8 | Security | ⏳ Pending |
| 9 | Frontend | ⏳ Pending |
| 10 | Observability | ⏳ Pending |
| 11 | Testing | ⏳ Pending |
| 12 | Production | ⏳ Pending |

## Roles

| Role | Access |
|------|--------|
| ADMIN | Full system access |
| SUPERVISOR | Regional oversight |
| ANALYST | Cross-region analysis |
| STAFF | Operational queries |

## MCP Tools

1. `get_tax_revenue` - Tax revenue data (Oracle)
2. `get_tax_arrears` - Tax arrears data (Oracle)
3. `get_growth_statistics` - Growth metrics (PostgreSQL)
4. `get_region` - Region master data (MySQL)
5. `get_taxpayer_summary` - Taxpayer profile (Oracle)
6. `search_regulation` - Regulation search (Qdrant RAG)

## Next Step

**Phase 2: Database Adapters** - Awaiting approval to proceed.

Phase 2 includes:
- Database connection adapters (Oracle, PostgreSQL, MySQL)
- Mock layer for development
- Connection pooling
- Query timeout enforcement
- Row limit enforcement

## Contact

- **Project Lead**: [Name]
- **Technical Lead**: [Name]
- **Security**: security@bapenda.go.id
- **Support**: support@bapenda.go.id

## License

Proprietary - BAPENDA Internal Use Only