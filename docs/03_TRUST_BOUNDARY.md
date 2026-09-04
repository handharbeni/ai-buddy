# Trust Boundary Document

## Trust Boundary Definition

A trust boundary is a logical separation where data or control crosses from one trust domain to another. Each boundary requires explicit validation, authorization, and audit.

## Trust Boundaries in This System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRUST DOMAIN 0: USER DEVICE (Untrusted)                                     │
│ - Staff workstation, browser                                                │
│ - No trust: input validation, auth required                                 │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTPS + mTLS
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRUST DOMAIN 1: EDGE / DMZ (Semi-Trusted)                                   │
│ - Next.js static assets (CDN)                                               │
│ - FastAPI public endpoints (auth, health)                                   │
│ - OIDC/LDAP identity provider                                               │
│ - WAF, rate limiting, DDoS protection                                       │
│ - TLS termination                                                           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ mTLS + JWT
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRUST DOMAIN 2: APPLICATION CORE (Trusted - Internal Services)              │
│ - FastAPI internal endpoints (authenticated)                                │
│ - Auth/RBAC Service                                                         │
│ - MCP Router                                                                │
│ - Local LLM (Ollama/vLLM)                                                  │
│ - All inter-service communication: mTLS                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ mTLS + DB credentials
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRUST DOMAIN 3: DATA LAYER (Highly Trusted - Read Only)                     │
│ - Oracle (AI_READONLY user)                                                 │
│ - PostgreSQL (AI_READONLY user)                                             │
│ - MySQL (AI_READONLY user)                                                  │
│ - Qdrant (RAG vector store)                                                 │
│ - Redis (cache/queue)                                                       │
│ - No write access from application                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Boundary Crossing Rules

### Boundary 0 → 1: User to Edge

| Crossing | Validation | Authorization | Audit |
|----------|------------|---------------|-------|
| HTTPS Request | TLS 1.3, cert validation | None (public) | Access log |
| Login POST | Rate limit, CAPTCHA | Credentials vs IdP | Auth log (success/fail) |
| Static Assets | CSP, SRI | None | CDN log |

### Boundary 1 → 2: Edge to Application Core

| Crossing | Validation | Authorization | Audit |
|----------|------------|---------------|-------|
| API Request | JWT signature, expiry, issuer | RBAC middleware | Request log |
| WebSocket Upgrade | JWT + origin check | Role + scope | Connection log |
| Internal Service Call | mTLS cert, SPIFFE ID | Service identity | Service mesh log |

### Boundary 2 → 3: Application Core to Data Layer

| Crossing | Validation | Authorization | Audit |
|----------|------------|---------------|-------|
| DB Query | Parameterized query, allowlist view | AI_READONLY user + row-level security | Query log (no params) |
| MCP Tool Call | Input schema, permission check | Role + scope per tool | Tool execution log |
| RAG Search | Vector query, approval filter | Scope filter on metadata | Search log |
| LLM Inference | Prompt template, token budget | None (local) | Inference log (no prompt) |

## Data Classification at Boundaries

| Data Type | Domain 0 | Domain 1 | Domain 2 | Domain 3 |
|-----------|----------|----------|----------|----------|
| User Credentials | Input only | Verified | Token only | Never |
| JWT Token | Stored | Validated | Decoded | Never |
| Tax Revenue Data | Never | Never | Response | Source |
| Tax Arrears Data | Never | Never | Response | Source |
| Growth Statistics | Never | Never | Response | Source |
| Region Master | Never | Never | Response | Source |
| Regulations (RAG) | Never | Never | Retrieved | Indexed |
| Audit Logs | Never | Written | Written | Stored |
| LLM Prompts | Input | Sanitized | Processed | Never |
| LLM Responses | Output | Generated | Formatted | Never |

## Trust Assumptions

### Trusted Components (Within Boundary)

1. **Auth/RBAC Service** - Single source of truth for permissions
2. **MCP Router** - Enforces tool-level permissions and scope
3. **Database Views** - Row-level security enforces data scope
4. **Audit Logger** - Append-only, tamper-evident
5. **Local LLM** - Runs on controlled hardware, no external calls
6. **Container Runtime** - Hardened, non-root, read-only rootfs

### Untrusted Components (Outside Boundary)

1. **User Browser** - Full control by user, XSS possible
2. **Network** - MITM, sniffing, injection (mitigated by mTLS)
3. **LLM Output** - Hallucination, prompt injection (validated downstream)
4. **RAG Retrieved Text** - Document content untrusted (citation only)
5. **External IdP** - Trusted for auth, not for authorization decisions

### Partially Trusted

1. **Document Approval Workflow** - Human process, enforced by metadata
2. **Database Administrators** - Trusted for ops, audited for data access
3. **Infrastructure (K8s/Docker)** - Trusted for isolation, not for data

## Boundary Enforcement Mechanisms

### Network Level
- **mTLS everywhere**: All service-to-service communication
- **Network Policies**: K8s NetworkPolicy / Docker network segmentation
- **Egress Control**: No outbound internet from Domain 2/3
- **Ingress Control**: Only Domain 1 accepts external traffic

### Application Level
- **Input Validation**: Pydantic schemas on every endpoint
- **Output Encoding**: JSON responses, no HTML injection
- **Schema Validation**: MCP tool input/output schemas
- **Scope Injection**: Automatic scope filters on DB queries

### Data Level
- **Row-Level Security**: PostgreSQL/Oracle policies by user_id/region
- **Column Masking**: PII columns masked for non-privileged roles
- **View-Based Access**: No direct table access, only approved views
- **Immutable Documents**: RAG documents versioned, hash-verified

### Cryptographic
- **JWT**: RS256, 15min access, 24h refresh, key rotation
- **mTLS**: SPIFFE/SPIRE or manual cert rotation (90 days)
- **Audit Hash Chain**: Each log entry includes hash of previous
- **Document Hash**: SHA-256 stored at ingestion, verified at retrieval

## Violation Handling

| Violation Type | Detection | Response |
|----------------|-----------|----------|
| Invalid JWT | Middleware | 401, audit, rate limit IP |
| Scope Mismatch | MCP Router | 403, audit, alert SIEM |
| SQL Injection Attempt | DB Driver | 400, audit, block IP |
| Prompt Injection | Pattern + LLM | Sanitize, audit, degrade response |
| mTLS Failure | Transport | Connection refused, alert |
| Audit Gap | Scheduled Job | Alert, investigate |
| Document Hash Mismatch | Retrieval | Reject document, alert |

## Boundary Testing Requirements

1. **Penetration Test**: Annual, focus on boundary crossings
2. **Chaos Engineering**: Network partition, cert expiry, DB failover
3. **Contract Tests**: MCP tool schemas, API contracts
4. **Load Test**: Boundary latency under 50 concurrent users
5. **Audit Log Integrity**: Verify hash chain quarterly