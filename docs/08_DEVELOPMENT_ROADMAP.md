# Development Roadmap

## Overview

Phased delivery plan for the BAPENDA Local AI Data Intelligence Platform. Each phase requires explicit approval before proceeding. Documentation must be updated alongside code.

## Phase Status Legend

| Status | Description |
|--------|-------------|
| 🔴 | Pending (not started) |
| 🟡 | In Progress |
| 🟢 | Complete |
| ⏸️ | Blocked (awaiting approval/input) |

---

## Phase 0: Project Initialization (Current)

**Status**: 🟡 In Progress

**Objective**: Establish project structure, documentation baseline, and approval gates.

**Deliverables**:
- [x] `docs/01_ARCHITECTURE.md` - System architecture
- [x] `docs/02_THREAT_MODEL.md` - Security threat analysis
- [x] `docs/03_TRUST_BOUNDARY.md` - Trust domain boundaries
- [x] `docs/04_RBAC_MATRIX.md` - Role-based access control
- [x] `docs/05_MCP_CONTRACT.md` - MCP tool specifications
- [x] `docs/06_SEMANTIC_DOMAIN_MODEL.md` - Data model
- [x] `docs/07_DOCKER_TOPOLOGY.md` - Container architecture
- [x] `docs/08_DEVELOPMENT_ROADMAP.md` - This document

**Approval Gate**: User must approve architecture before Phase 1.

---

## Phase 1: Repository Skeleton & Foundations

**Status**: 🔴 Pending Approval

**Objective**: Create monorepo structure, CI/CD scaffolding, and base configurations.

**Duration**: 3-5 days

**Tasks**:
1. Initialize git repository with `.gitignore`, `README.md`
2. Create monorepo structure:
   - `frontend/` - Next.js app
   - `backend/` - FastAPI app
   - `mcp/` - MCP router service
   - `rag/` - Document ingestion pipeline
   - `docs/` - Documentation
   - `docker/` - Dockerfiles, compose files
   - `tests/` - E2E and integration tests
3. Set up Python virtual environment (uv, poetry)
4. Configure TypeScript + Next.js 14
5. Create base Dockerfiles (multi-stage: dev, build, prod)
6. Set up `docker-compose.dev.yml` for local development
7. Configure linting: ruff (Python), eslint+prettier (TS)
8. Configure pre-commit hooks (secrets scan, lint, format)
9. Create Makefile / justfile for common commands
10. Set up CI pipeline (GitHub Actions or GitLab CI)

**Files Created**:
```
.gitignore
README.md
docker-compose.dev.yml
docker-compose.prod.yml
Makefile
pyproject.toml
frontend/package.json
frontend/tsconfig.json
frontend/Dockerfile
backend/pyproject.toml
backend/Dockerfile
mcp/pyproject.toml
mcp/Dockerfile
.github/workflows/ci.yml
```

**Testing**:
- [ ] `docker compose -f docker-compose.dev.yml up` succeeds
- [ ] Lint passes
- [ ] CI pipeline green

**Approval Gate**: Skeleton builds and runs locally.

---

## Phase 2: Database Adapters & Mock Layer

**Status**: 🔴 Pending

**Objective**: Implement read-only database connectors with mock layer for dev/test.

**Duration**: 5-7 days

**Tasks**:
1. Define connection interfaces (`DBAdapter` protocol)
2. Implement Oracle adapter (python-oracledb with TCPS)
3. Implement PostgreSQL adapter (asyncpg with SSL)
4. Implement MySQL adapter (aiomysql with SSL)
5. Create mock adapters with deterministic sample data
6. Implement connection pooling
7. Add query timeout enforcement
8. Add row limit enforcement
9. Create migration script for database views (`V_TAX_REVENUE_SCOPE`, etc.)
10. Document database setup procedure

**Files Created**:
```
backend/app/db/base.py
backend/app/db/oracle.py
backend/app/db/postgresql.py
backend/app/db/mysql.py
backend/app/db/mocks/
backend/app/db/connection_pool.py
backend/app/db/queries/
backend/tests/db/
```

**Testing**:
- [ ] Unit tests for each adapter
- [ ] Mock data matches schema
- [ ] Connection pool handles failures
- [ ] Timeouts enforced
- [ ] SQL injection attempts blocked

**Approval Gate**: Adapters pass tests with mock + live DB.

---

## Phase 3: Auth/RBAC Service

**Status**: 🔴 Pending

**Objective**: Implement authentication, authorization, and data scope enforcement.

**Duration**: 7-10 days

**Tasks**:
1. JWT token issuance and validation (RS256)
2. OIDC integration (auth code flow + PKCE)
3. LDAP fallback (if OIDC unavailable)
4. Role assignment service
5. Scope resolution engine
6. Permission matrix evaluator
7. Token refresh mechanism
8. Session management
9. Audit log writer (auth events)
10. Rate limiting middleware
11. Admin endpoints for user management
12. Frontend login flow

**Files Created**:
```
backend/app/auth/
backend/app/rbac/
backend/app/middleware/
backend/app/api/v1/auth.py
backend/app/api/v1/admin/
frontend/app/login/
frontend/app/(authenticated)/
frontend/lib/auth/
frontend/lib/api/
```

**Testing**:
- [ ] JWT validation works
- [ ] RBAC matrix enforced
- [ ] Scope filtering prevents cross-region access
- [ ] Rate limiting triggers
- [ ] Admin endpoints restricted
- [ ] Prompt injection cannot escalate privileges

**Approval Gate**: Auth flow complete, RBAC tests pass.

---

## Phase 4: MCP Router & Tool Registry

**Status**: 🔴 Pending

**Objective**: Build MCP router with all 6 tools, schema validation, and scope enforcement.

**Duration**: 10-14 days

**Tasks**:
1. MCP router base service
2. Tool registry with schema validation (JSON Schema)
3. Implement `get_tax_revenue` tool
4. Implement `get_tax_arrears` tool
5. Implement `get_growth_statistics` tool
6. Implement `get_region` tool
7. Implement `get_taxpayer_summary` tool
8. Implement `search_regulation` tool (Qdrant integration)
9. Tool permission decorator
10. Scope filter injection
11. Tool timeout & row limit enforcement
12. MCP contract compliance tests
13. Error handling (all error codes)
14. Rate limiting per tool

**Files Created**:
```
mcp/app/router.py
mcp/app/registry.py
mcp/app/permissions.py
mcp/app/scope.py
mcp/app/tools/
  revenue.py
  arrears.py
  growth.py
  region.py
  taxpayer.py
  regulation.py
mcp/app/validators/
mcp/tests/
```

**Testing**:
- [ ] All 6 tools pass contract tests
- [ ] Permission denied for unauthorized
- [ ] Scope violation blocked
- [ ] Timeouts enforced
- [ ] Row limits enforced
- [ ] Error codes correct
- [ ] Rate limits work

**Approval Gate**: All MCP tools functional with full test coverage.

---

## Phase 5: RAG Pipeline

**Status**: 🔴 Pending

**Objective**: Document ingestion, embedding, and retrieval for regulations.

**Duration**: 7-10 days

**Tasks**:
1. Qdrant collection setup with proper schema
2. Document parser (PDF, DOCX, MD)
3. Text chunking strategy (semantic chunking)
4. Embedding generation (bge-m3 via Ollama/vLLM)
5. Document ingestion pipeline
6. Metadata extraction (title, version, date, classification, approval)
7. Approval workflow integration
8. Document hash verification
9. Search service (vector + reranker)
10. Document versioning & supersession
11. Daily sync job
12. Document deletion/archival

**Files Created**:
```
rag/app/ingestion/
  parser.py
  chunker.py
  embedder.py
rag/app/retrieval/
  search.py
  reranker.py
rag/app/approval/
rag/app/scheduler.py
rag/jobs/sync_daily.py
rag/tests/
```

**Testing**:
- [ ] PDF/DOCX parsing correct
- [ ] Embeddings generated
- [ ] Search returns relevant results
- [ ] Only APPROVED documents indexed
- [ ] Hash verification works
- [ ] Versioning handles supersession

**Approval Gate**: RAG returns relevant, approved documents.

---

## Phase 6: Local LLM Integration

**Status**: 🔴 Pending

**Objective**: Connect to local LLM (Ollama for dev, vLLM for prod) with prompt engineering.

**Duration**: 7-10 days

**Tasks**:
1. Ollama client (development)
2. vLLM client (production, OpenAI-compatible API)
3. System prompt engineering (intent detection, tool planning)
4. Tool calling format (JSON mode or function calling)
5. Prompt template management
6. Token budget enforcement
7. Response parsing & validation
8. Fallback handling
9. Context window management
10. Prompt injection detection layer
11. Model evaluation harness

**Files Created**:
```
backend/app/llm/
  client.py
  ollama.py
  vllm.py
  prompts/
  template_manager.py
  token_budget.py
  injection_detector.py
backend/tests/llm/
```

**Testing**:
- [ ] LLM generates valid tool calls
- [ ] Token limits enforced
- [ ] Prompt injection detected/blocked
- [ ] Fallback works
- [ ] Response validation catches hallucinations

**Approval Gate**: LLM correctly plans and calls tools for test queries.

---

## Phase 7: Orchestrator & Query Processing

**Status**: 🔴 Pending

**Objective**: End-to-end query orchestration: user query → LLM → MCP tools → response.

**Duration**: 10-14 days

**Tasks**:
1. Query intake endpoint (`/api/v1/query`)
2. Intent detection
3. Tool planning (LLM-based)
4. Parallel tool execution
5. Result aggregation
6. RAG integration (regulation queries)
7. Response synthesis (LLM)
8. Citation enforcement
9. Streaming response support
10. Conversation context management
11. Error handling & user feedback
12. Audit log writer (all requests)

**Files Created**:
```
backend/app/orchestrator/
  pipeline.py
  intent.py
  planner.py
  executor.py
  synthesizer.py
  context.py
backend/app/api/v1/query.py
backend/app/api/v1/chat.py
backend/tests/orchestrator/
```

**Testing**:
- [ ] End-to-end query works
- [ ] Multi-tool queries succeed
- [ ] Citations present
- [ ] Hallucination prevented
- [ ] Audit log complete
- [ ] Streaming works
- [ ] Latency < 10s for complex queries

**Approval Gate**: Full query flow works with real data.

---

## Phase 8: Security Hardening

**Status**: 🔴 Pending

**Objective**: Implement and validate all security controls from Threat Model.

**Duration**: 7-10 days

**Tasks**:
1. Input validation on all endpoints
2. Output encoding
3. mTLS between services
4. Secrets management (Docker secrets → external vault)
5. PII redaction in LLM context
6. SQL injection prevention review
7. Prompt injection prevention review
8. Rate limiting (per user, per tool, per IP)
9. Audit log integrity (hash chain)
10. Security headers (CSP, HSTS, X-Frame-Options)
11. Dependency vulnerability scanning
12. Container image scanning (Trivy, Snyk)
13. Penetration testing prep
14. Security documentation

**Files Created**:
```
backend/app/security/
  input_validator.py
  output_encoder.py
  pii_redactor.py
  audit_chain.py
docs/security/
.github/workflows/security.yml
```

**Testing**:
- [ ] OWASP Top 10 coverage
- [ ] Penetration test report
- [ ] Vulnerability scan clean
- [ ] Audit chain verification
- [ ] Prompt injection tests pass
- [ ] SQL injection tests pass

**Approval Gate**: Security review sign-off.

---

## Phase 9: Frontend Implementation

**Status**: 🔴 Pending

**Objective**: Build Next.js chat interface, dashboards, and admin panels.

**Duration**: 10-14 days

**Tasks**:
1. Login page with OIDC redirect
2. Chat interface (streaming responses)
3. Message history
4. Tool result visualization (charts, tables)
5. Citation display
6. Role-based dashboard
7. User management UI (Admin)
8. Audit log viewer (Admin/Supervisor)
9. Settings & profile page
10. Error handling & notifications
11. Responsive design (mobile + desktop)
12. Accessibility (WCAG 2.1 AA)
13. Performance optimization

**Files Created**:
```
frontend/app/
  login/
  chat/
  dashboard/
  admin/
  audit/
  settings/
frontend/components/
  ChatMessage.tsx
  ToolResult.tsx
  DataTable.tsx
  Chart.tsx
  Citation.tsx
frontend/lib/
  api.ts
  auth.ts
  hooks/
frontend/tests/
```

**Testing**:
- [ ] E2E tests (Playwright)
- [ ] Accessibility audit
- [ ] Performance budget met
- [ ] Cross-browser tested
- [ ] Mobile responsive

**Approval Gate**: UI complete, accessible, performant.

---

## Phase 10: Observability & Operations

**Status**: 🔴 Pending

**Objective**: Add monitoring, logging, and alerting for production readiness.

**Duration**: 5-7 days

**Tasks**:
1. Prometheus metrics on all services
2. Grafana dashboards
3. Loki log aggregation
4. Tempo distributed tracing
5. Alert rules (latency, error rate, resource usage)
6. Health check endpoints
7. Readiness/liveness probes
8. Backup automation (Qdrant, Redis)
9. Disaster recovery runbook
10. Operational documentation

**Files Created**:
```
docker/prometheus/
docker/grafana/
docker/loki/
docker/tempo/
docs/operations/
  runbook.md
  disaster_recovery.md
  monitoring.md
```

**Testing**:
- [ ] Metrics scrape
- [ ] Dashboards render
- [ ] Alerts fire on test conditions
- [ ] Backup/restore works
- [ ] DR procedure tested

**Approval Gate**: Operations team accepts documentation.

---

## Phase 11: Testing & Quality Assurance

**Status**: 🔴 Pending

**Objective**: Comprehensive testing across all layers.

**Duration**: 7-10 days

**Tasks**:
1. Unit test coverage > 80%
2. Integration test suite
3. E2E test suite (Playwright)
4. Security test suite
   - Prompt injection tests
   - SQL injection tests
   - RBAC tests
   - Scope tests
   - RAG injection tests
5. Performance test suite (k6, Locust)
6. Load test (50 concurrent users)
7. Chaos engineering tests
8. Contract tests (MCP, API)
9. Accessibility tests
10. UAT with stakeholders

**Files Created**:
```
tests/
  unit/
  integration/
  e2e/
  security/
  performance/
  contract/
  chaos/
```

**Testing**:
- [ ] Coverage > 80%
- [ ] All security tests pass
- [ ] Load test: 50 concurrent, P95 < 10s
- [ ] Chaos test: services recover
- [ ] UAT sign-off

**Approval Gate**: All test suites pass, UAT complete.

---

## Phase 12: Production Integration

**Status**: 🔴 Pending

**Objective**: Deploy to production environment with full operational support.

**Duration**: 7-10 days

**Tasks**:
1. Production infrastructure provisioning
2. Secrets management setup (external vault)
3. Certificate management (Let's Encrypt)
4. Database connection setup (with TLS)
5. LLM model deployment (vLLM + GPU)
6. Network configuration (firewall, VPN)
7. DNS configuration
8. Production deployment (blue-green or rolling)
9. Smoke tests in production
10. Performance baseline
11. Handover to operations team
12. Training sessions
13. Go-live announcement
14. Post-launch monitoring (1 week intensive)

**Prerequisites** (Require Human Approval):
- [ ] Production database access (AI_READONLY user)
- [ ] Production database credentials
- [ ] Production network access (VPN/firewall rules)
- [ ] OIDC IdP integration approval
- [ ] GPU server provisioning
- [ ] LLM model licensing
- [ ] DNS/SSL certificate approval
- [ ] Go-live date confirmation

**Deliverables**:
- Production URL
- Operations runbook
- Incident response plan
- Training materials
- Support escalation matrix

**Approval Gate**: Stakeholder sign-off for go-live.

---

## Phase 13: Post-Launch Support & Iteration

**Status**: 🔴 Pending

**Objective**: Stabilize, gather feedback, plan v2.

**Duration**: Ongoing

**Tasks**:
1. Bug triage and fixes
2. User feedback collection
3. Performance optimization based on real usage
4. Additional MCP tools (per stakeholder requests)
5. Additional RAG documents (per approval)
6. Dashboard improvements
7. Model fine-tuning (if data permits)
8. Security patching
9. Dependency updates
10. Capacity planning

**Success Metrics**:
- Adoption rate (% of eligible staff)
- Query success rate (> 95%)
- User satisfaction (NPS)
- P95 latency < 5s
- Availability > 99.5%
- Security incidents: 0

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 0. Init | ✅ Done | - |
| 1. Skeleton | 3-5d | Phase 0 approval |
| 2. DB Adapters | 5-7d | Phase 1 |
| 3. Auth/RBAC | 7-10d | Phase 1 |
| 4. MCP Router | 10-14d | Phase 2, 3 |
| 5. RAG | 7-10d | Phase 2 |
| 6. LLM | 7-10d | Phase 1 |
| 7. Orchestrator | 10-14d | Phase 3, 4, 5, 6 |
| 8. Security | 7-10d | Phase 3, 4, 7 |
| 9. Frontend | 10-14d | Phase 3, 7 |
| 10. Observability | 5-7d | Phase 1 |
| 11. Testing | 7-10d | All above |
| 12. Production | 7-10d | All + approval |
| 13. Support | Ongoing | - |

**Total estimated**: 85-120 days (4-6 months) for full delivery.

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM hallucination on numeric data | High | High | Grounding mandate, tool-only data, validation |
| Scope bypass via prompt injection | Critical | Medium | Deterministic RBAC, no LLM auth decisions |
| Production DB access delayed | High | Medium | Mock layer for dev, clear approval process |
| GPU availability for vLLM | High | Medium | Fallback to Ollama, cloud GPU option |
| OIDC IdP integration complexity | Medium | Medium | LDAP fallback, manual config |
| User adoption resistance | Medium | High | Training, champions program, iterative UI |
| Model performance in Bahasa | Medium | High | Qwen chosen for multilingual, testing with local queries |

## Approval Gates Summary

| Gate | Phase | Approver | Status |
|------|-------|----------|--------|
| Architecture approval | 0→1 | User (this document) | ⏳ |
| Skeleton build | 1→2 | Dev Lead | ⏳ |
| DB adapters tested | 2→3 | Dev Lead | ⏳ |
| Auth/RBAC complete | 3→4 | Security | ⏳ |
| MCP tools complete | 4→5 | Dev Lead | ⏳ |
| RAG functional | 5→6 | Dev Lead | ⏳ |
| LLM integrated | 6→7 | Dev Lead | ⏳ |
| Orchestrator working | 7→8 | Dev Lead | ⏳ |
| Security sign-off | 8→9 | Security | ⏳ |
| UI complete | 9→10 | Product Owner | ⏳ |
| Observability ready | 10→11 | Operations | ⏳ |
| All tests pass | 11→12 | QA Lead | ⏳ |
| **Production go-live** | **12→13** | **Steering Committee** | ⏳ |

## Next Action

Awaiting your approval of the architecture documentation (Phase 0) before proceeding to Phase 1 (Repository Skeleton).

**Please review**:
- `docs/01_ARCHITECTURE.md`
- `docs/02_THREAT_MODEL.md`
- `docs/03_TRUST_BOUNDARY.md`
- `docs/04_RBAC_MATRIX.md`
- `docs/05_MCP_CONTRACT.md`
- `docs/06_SEMANTIC_DOMAIN_MODEL.md`
- `docs/07_DOCKER_TOPOLOGY.md`
- `docs/08_DEVELOPMENT_ROADMAP.md` (this file)

On approval, I will create the Phase 1 repository skeleton with no application logic.