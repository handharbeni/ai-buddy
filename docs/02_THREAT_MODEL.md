# Threat Model

## Methodology: STRIDE

## Assets

| Asset | Classification | Description |
|-------|----------------|-------------|
| Tax Revenue Data | Confidential | Oracle: revenue, collections, targets |
| Tax Arrears Data | Confidential | Oracle: outstanding debts, taxpayer details |
| Growth Statistics | Internal | PostgreSQL: regional growth metrics |
| Region Master Data | Internal | MySQL: administrative boundaries |
| Regulations (RAG) | Public/Internal | Perda, Pergub, SOP, Surat Edaran |
| User Credentials | Secret | JWT tokens, LDAP bind credentials |
| Audit Logs | Confidential | 7-year retention, tamper-evident |
| LLM Prompts/Context | Internal | May contain PII from queries |

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET / EXTERNAL                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DMZ / EDGE (WAF, TLS Termination)            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Next.js   │  │   FastAPI   │  │   Auth      │             │
│  │  (Static)   │  │  (Public)   │  │  (OIDC)     │             │
│  └─────────────┘  └──────┬──────┘  └─────────────┘             │
└──────────────────────────│──────────────────────────────────────┘
                           │ HTTPS + mTLS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTERNAL NETWORK (Zero Trust)                │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   FastAPI   │  │  Ollama/    │  │   MCP       │             │
│  │  (Internal) │  │  vLLM       │  │  Router     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Oracle    │  │ PostgreSQL  │  │   MySQL     │             │
│  │  (ReadOnly) │  │ (ReadOnly)  │  │ (ReadOnly)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   Qdrant    │  │   Redis     │                              │
│  │  (RAG)      │  │  (Cache/    │                              │
│  │             │  │   Queue)    │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## STRIDE Analysis

### Spoofing

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Impersonate user via stolen JWT | High | Medium | Short JWT expiry (15m), refresh token rotation, device fingerprinting |
| Impersonate service (MCP→DB) | Critical | Low | mTLS between all services, certificate pinning |
| Spoof LLM responses | High | Medium | Response validation, deterministic tool outputs |
| DNS spoofing internal services | Critical | Low | Internal DNSSEC, service mesh (future) |

### Tampering

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Modify query parameters | High | Medium | Input validation, Pydantic schemas, parameterized queries |
| Inject SQL via tool params | Critical | Low | No raw SQL tools, allowlist-only MCP tools, parameterized queries |
| Poison RAG documents | High | Medium | Approval workflow, immutable document versions, hash verification |
| Modify audit logs | Critical | Low | Append-only storage, WORM, cryptographic chaining |
| Tamper LLM system prompt | High | Low | System prompt baked into container, integrity check at startup |

### Repudiation

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| User denies query | Medium | Medium | Audit log with user_id, timestamp, request_hash |
| Admin denies config change | High | Low | Config changes via GitOps, signed commits |
| Service denies action | Medium | Medium | Distributed tracing (OpenTelemetry), correlation IDs |

### Information Disclosure

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Cross-user data leak (scope bypass) | Critical | Medium | Row-level security in DB views, scope enforced in MCP router |
| PII in LLM context | High | Medium | PII redaction pre-LLM, local LLM only, no external API |
| Credentials in logs | Critical | Low | Structured logging with field filtering, secret scanning |
| RAG document classification leak | Medium | Low | Classification metadata enforced at retrieval |
| Error messages leak schema | Medium | Medium | Generic error responses, debug mode disabled in prod |

### Denial of Service

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| LLM prompt flooding | High | Medium | Rate limiting per user, token budget per request |
| Complex query exhaustion | Medium | Medium | Tool timeouts (30s), result limits (1000 rows), query complexity scoring |
| RAG retrieval flood | Low | Low | Vector search limits, caching frequent queries |
| DB connection exhaustion | High | Low | Connection pooling, max connections per service |

### Elevation of Privilege

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Role escalation via prompt injection | Critical | Medium | Deterministic RBAC in backend, LLM never decides permissions |
| Scope expansion via tool chaining | High | Medium | Scope validated per tool, not transitive |
| Admin API access | Critical | Low | Admin endpoints on separate network segment, MFA required |
| Container escape | Critical | Low | Non-root containers, read-only rootfs, seccomp, drop capabilities |

## Attack Trees

### Goal: Access Taxpayer PII Without Authorization

```
Access Taxpayer PII
├── Steal valid JWT
│   ├── XSS in frontend
│   ├── MITM (prevented by HSTS, mTLS)
│   └── Token replay (prevented by short expiry, rotation)
├── Bypass RBAC in API
│   ├── IDOR via manipulated request
│   ├── Privilege escalation via prompt injection
│   └── Admin endpoint exposure
├── Direct DB access
│   ├── Credential theft from config
│   ├── SQL injection via MCP tool
│   └── ReadOnly user privilege escalation
└── RAG document extraction
    ├── Classification bypass
    └── Vector store direct query
```

### Goal: Modify Tax Data

```
Modify Tax Data
├── SQL injection via MCP
│   └── Blocked: no write tools, parameterized queries
├── Compromise AI_READONLY user
│   └── Blocked: DB-level read-only enforcement
├── Supply chain attack (container image)
│   └── Mitigated: signed images, SBOM, vulnerability scanning
└── Insider threat (DBA)
    └── Mitigated: Audit logs, separation of duties
```

## Risk Matrix

| Threat | Severity | Current Controls | Residual Risk |
|--------|----------|------------------|---------------|
| Prompt injection → privilege escalation | Critical | Deterministic RBAC, no LLM auth decisions | Medium |
| SQL injection via MCP tools | Critical | No raw SQL, allowlist tools, param queries | Low |
| Cross-scope data access | Critical | Scope in MCP router, DB row-level security | Low |
| PII leakage to LLM | High | Local LLM only, PII redaction | Medium |
| RAG document poisoning | High | Approval workflow, immutable versions | Medium |
| Audit log tampering | Critical | Append-only, WORM, hash chaining | Low |
| Credential leakage | Critical | Vault, no secrets in code, log filtering | Low |
| DoS via LLM flooding | High | Rate limits, token budgets, timeouts | Medium |

## Security Requirements Traceability

| Requirement | Threat Mitigated | Implementation |
|-------------|------------------|----------------|
| REQ-SEC-001 | All spoofing | mTLS everywhere |
| REQ-SEC-002 | Tampering, Info disclosure | Parameterized queries, no raw SQL |
| REQ-SEC-003 | Privilege escalation | Deterministic RBAC in backend |
| REQ-SEC-004 | Info disclosure | Scope enforcement at MCP + DB |
| REQ-SEC-005 | PII leakage | Local LLM, PII redaction |
| REQ-SEC-006 | RAG poisoning | Approval workflow, immutable docs |
| REQ-SEC-007 | Repudiation | Append-only audit, correlation IDs |
| REQ-SEC-008 | DoS | Rate limits, timeouts, quotas |
| REQ-SEC-009 | Container escape | Hardened containers, non-root |
| REQ-SEC-010 | Supply chain | Signed images, SBOM, scanning |

## Assumptions

1. Internal network is not trusted (Zero Trust)
2. All external access via VPN/Zero Trust Network Access
3. LDAP/OIDC identity provider is trusted
4. Database administrators are trusted but audited
5. Local LLM hardware is physically secured
6. Document approval process is governed by policy
7. Audit log storage is WORM-compliant