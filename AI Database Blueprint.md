# BLUEPRINT PRD — BAPENDA LOCAL AI DATA INTELLIGENCE PLATFORM

## Tujuan
Platform AI internal Bapenda berbasis Local LLM + MCP + RAG + Oracle/PostgreSQL/MySQL.

## Arsitektur
Staff → FastAPI → Auth/RBAC → Qwen Local LLM → MCP Router → Database & RAG.

## Prinsip
- Database adalah Source of Truth
- Read Only
- RBAC + Data Scope
- No unrestricted SQL
- Prompt Injection Protection

## MCP Tools
- Oracle: get_tax_revenue, get_tax_arrears
- PostgreSQL: get_growth_statistics
- MySQL: get_region
- RAG: search_regulation

## Roadmap
1. Architecture
2. Skeleton
3. Local LLM
4. RBAC
5. DB Adapter
6. MCP
7. RAG
8. Security
9. Orchestrator
10. Frontend
11. Testing
12. Production Integration
