# ENTERPRISE PRD — BAPENDA LOCAL AI DATA INTELLIGENCE PLATFORM

## Executive Summary
Platform AI internal berbasis Local LLM + MCP + RAG.

## Architecture
Staff → Next.js → FastAPI → Auth/RBAC → Qwen → MCP → Oracle/PostgreSQL/MySQL/RAG.

## Security
- Zero Trust
- RBAC
- Data Scope
- Prompt Injection Protection
- Read-only Database
- Grounding

## MCP Tools
- Oracle: get_tax_revenue, get_tax_arrears
- PostgreSQL: get_growth_statistics
- MySQL: get_region
- RAG: search_regulation

## Roadmap
1. Architecture
2. Skeleton
3. LLM
4. RBAC
5. MCP
6. RAG
7. Security
8. Frontend
9. Testing
10. Production