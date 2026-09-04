# Phase 8: Security Hardening

**Status**: 🔴 Pending

**Objective**: Implement comprehensive security controls as defined in the Threat Model.

**Duration**: 7-10 days

## Security Requirements Traceability

| Requirement | Implementation |
|-----------|--------------|
| REQ-SEC-001 | mTLS between services (in progress) |
| REQ-SEC-002 | Parameterized queries (already implemented) |
| REQ-SEC-003 | Deterministic RBAC in backend (backend) | ✅ |
| REQ-SEC-004 | Scope enforcement at all layers (MCP + DB) | ✅ |
| REQ-SEC-005 | Local LLM only (no external API calls) | ✅ |
| REQ-SEC-006 | Document approval workflow (metadata validation) | ✅ |
| REQ-SEC-007 | Append-only audit logs (in progress) | ⏳ |
| REQ-SEC-007 | PII redaction in LLM context | ⏳ |
| REQ-SEC-008 | Rate limiting (per user, tool, IP) | ⏳ |
| REQ-SEC-009 | Container hardening (no-root, read-only) | ⏳ |
| REQ-SEC-009 | Container escape prevention | ⏳ |
| REQ-SEC-010 | Supply chain security (signed images) | ⏳ |

## Security Implementation Plan

### 1. Network Security (mTLS)

**Current State**: No mTLS between services (only application-level auth)

**Implementation Plan**:
1. Generate SPIFFE/SPIRE certificates for all services
2. Configure mTLS between all internal services
3. Update FastAPI to use mTLS (via Uvicorn + TLS)
4. Implement SPIFFE/SPIRE service identity management

### 2. Secrets Management

**Current State**: Docker secrets (limited)

**Enhancement Plan**:
1. Integrate with HashiCorp Vault or AWS Secrets Manager
2. Rotate secrets automatically (90-day rotation)
3. Audit secret access
4. Move from Docker secrets to external secret management

### 3. Input/Output Validation

**Current State**: Basic Pydantic validation

**Enhancement Plan**:
1. Add Pydantic model validation for all API endpoints
2. Implement PII redaction in LLM context
3. Add input sanitization for all user inputs
4. Implement content security policy (CSP) headers

### 4. Audit Logging Enhancement

**Current State**: Basic audit logging

**Enhancement Plan**:
1. Implement cryptographic hash chaining for audit logs
2. Add correlation IDs to all requests
3. Integrate with SIEM systems
4. Enable tamper-evident storage

### 5. Container Security

**Current State**: Basic containerization

**Enhancement Plan**:
1. Non-root user in containers
2. Read-only root filesystem
3. Drop unnecessary capabilities
4. Seccomp profile enforcement
5. Resource limits (CPU/memory/cpu)

### 6. Security Testing

**Required Tests**:
- OWASP Top 10 coverage
- Penetration testing
- Vulnerability scanning (Trivy, Snyk)
- Container escape attempts
- API penetration testing

## Implementation Plan

### 1. mTLS Implementation (Critical)

**Tasks**:
1. Generate SPIFFE/SPIRE certificates for all services (frontend, backend, mcp, rag)
2. Configure mTLS between all services (frontend↔backend, backend↔db, etc.)
3. Update FastAPI to use mTLS (via Uvicorn + TLS)
4. Implement SPIFFE/SPIRE service identity management
5. Add mTLS health checks

### 2. Secrets Management Upgrade

**Tasks**:
1. Integrate with HashiCorp Vault or AWS Secrets Manager
2. Replace Docker secrets with external secret management
3. Implement secret rotation (90-day cycle)
4. Audit secret access logs

### 3. Input/Output Validation Enhancements

**Tasks**:
1. Implement Pydantic model validation on all endpoints
2. Add PII redaction in LLM context (before sending to LLM)
3. Implement content security policy (CSP) headers
4. Add input validation for all tool parameters

### 5. Audit Log Enhancement

**Tasks**:
1. Implement hash chain for audit logs (each entry hashes previous entry)
2. Add correlation IDs to all requests
3. Implement tamper-evident storage (WORM)
4. Add audit log integrity verification

### 6. Container Security Hardening

**Tasks**:
1. Run containers as non-root user (UID 1000)
2. Set read-only root filesystem (tmpfs for /tmp)
3. Drop all Linux capabilities except necessary ones
4. Apply seccomp profile
5. Add resource limits (CPU/memory)
6. Implement health checks with proper readiness/liveness probes

## Implementation Plan

### 1. mTLS Setup (Critical Path)

1. **Generate SPIFFE/SPIRE Certificates**:
   ```bash
   # Generate SPIFFE IDs
   spiffeid --spiffe-id=spiffe:///spiffe:///bapenda-frontend/0.1
   spiffeid --spiffe-id=spiffe:///spiffe:///bapenda-backend/0.1
   # ... for all services

   # Generate certificates
   spire-server -certs-dir=/etc/spire/certs -config=/etc/spire/config.yaml
   ```

2. **Configure mTLS in Traefik**:
   ```yaml
   # traefik.yml
   http:
     routers:
       backend:
         entrypoints: websecure
         service: backend-service
         middlewares:
           - mTLS-middleware
   providers:
     docker:
       exposedbydefault: false
   providers:
     docker:
       exposedbydefault: false
   providers:
     docker:
       networks:
         - backend_net
   providers:
     docker:
       exposedbydefault: false
   providers:
     docker:
       networks:
         - backend_net
   providers:
     docker:
       containers:
         - name: backend
           labels:
             - "traefik.enable=true"
             - "traefik.http.routers.backend.rule=Host(`api.bapenda.local`)"
             - "traefik.http.routers.backend.entrypoints=websecure"
             - "traefik.http.routers.backend.tls.certresolver=le"
             - "traefik.http.routers.backend.middlewares=mtls-auth"
   ```

### 2. Secrets Management Upgrade

**Tasks**:
1. Integrate HashiCorp Vault or AWS Secrets Manager
2. Create secret access policies
3. Implement secret rotation automation
4. Update all services to use external secrets

### 6. Security Testing

**Tasks**:
1. Implement security scanning in CI/CD
2. Conduct penetration testing
3. Validate all security requirements
4. Document security controls

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|---------|--------|------------|------------|
| Container escape | Critical | Low | Hardened containers, seccomp, read-only rootfs |
| Credential leakage | Critical | Low | Vault, no secrets in code, audit logs |
| mTLS misconfiguration | High | Medium | Automated testing, documentation |
| PII leakage to LLM | High | Medium | Local LLM only, PII redaction |
| Audit log tampering | Critical | Low | Append-only, hash chaining |
| Supply chain attack | Critical | Low | Signed images, SBOM, scanning |

## Testing Requirements

1. **Security Testing**:
   - Penetration testing (annual)
   - Vulnerability scanning (weekly)
   - Container escape tests
   - API penetration testing
   - Audit log integrity verification

**Next Action**: Implement mTLS configuration for all internal services and update the Docker Compose files with mTLS configuration.