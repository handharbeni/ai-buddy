# Documentation Index

**Project**: BAPENDA Local AI Data Intelligence Platform
**Version**: 1.0
**Status**: Phase 0 - Architecture Review

## Documents

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

## Quick Reference

### Stack
- **Frontend**: Next.js 14 (App Router, TypeScript)
- **Backend**: FastAPI (Python 3.12+)
- **LLM**: Qwen2.5 (Ollama dev, vLLM prod)
- **MCP**: Custom router (6 tools)
- **DBs**: Oracle 19c, PostgreSQL 15, MySQL 8.0 (read-only)
- **Vector**: Qdrant 1.8
- **Cache**: Redis 7

### Roles
- **ADMIN** - Full system access
- **SUPERVISOR** - Regional oversight
- **ANALYST** - Cross-region analysis
- **STAFF** - Operational queries

### MCP Tools
1. `get_tax_revenue` - Oracle
2. `get_tax_arrears` - Oracle
3. `get_growth_statistics` - PostgreSQL
4. `get_region` - MySQL
5. `get_taxpayer_summary` - Oracle
6. `search_regulation` - Qdrant RAG

### Security Principles
- Zero Trust
- Database = Source of Truth
- Read-only access
- RBAC + Data Scope
- No unrestricted SQL
- Prompt Injection Protection
- Grounding mandate
- Append-only audit logs

## Next Step

**Awaiting your approval of the architecture before any application code is generated.**

Once approved, Phase 1 (Repository Skeleton) will begin with no business logic - just project structure, Dockerfiles, and CI scaffolding.