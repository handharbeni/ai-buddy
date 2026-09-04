# Phase 12: Observability & Operations

## Overview

This document defines the observability strategy for the BAPENDA Local AI Platform. It covers monitoring, logging, tracing, and alerting to ensure system health and performance in production.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Application Services                                │
│  (FastAPI, MCP Router, RAG Service)                 │
└──────────────┬───────────────────────────────────────┘
               │ (exposed /metrics, /health, /ready)
               ▼
┌──────────────────────────────────────────────────────┐
│  Prometheus (Metrics Collection)                    │
└──────────────┬───────────────────────────────────────┘
               │ (scrapes metrics)
               ▼
┌──────────────────────────────────────────────────────┐
│  Grafana (Visualization)                            │
│  (Dashboards, Alerts)                               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Application Services                                │
│  (JSON structured logs)                            │
└──────────────┬───────────────────────────────────────┘
               │ (logs sent to)
               ▼
┌──────────────────────────────────────────────────────┐
│  Loki (Log Aggregation)                            │
└──────────────┬───────────────────────────────────────┘
               │ (logs available)
               ▼
┌──────────────────────────────────────────────────────┐
│  Grafana (Log Visualization)                        │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Application Services                                │
│  (OTel distributed tracing)                        │
└──────────────┬───────────────────────────────────────┘
               │ (traces sent to)
               ▼
┌──────────────────────────────────────────────────────┐
│  Tempo (Trace Storage)                              │
└──────────────┬───────────────────────────────────────┘
               │ (traces available)
               ▼
┌──────────────────────────────────────────────────────┐
│  Grafana (Trace Visualization)                      │
└──────────────────────────────────────────────────────┘
```

## Metrics Collection

### Application Metrics

The following metrics are exposed at `/metrics` by each service:

#### 1. Request Metrics
- `bapenda_http_requests_total{method, endpoint, status}` - Total HTTP requests
- `bapenda_http_request_duration_seconds{method, endpoint, status}` - Request latency histogram
- `bapenda_http_requests_in_flight` - Currently in-flight requests

#### 2. Database Metrics
- `bapenda_db_query_duration_seconds{adapter, operation}` - Query duration
- `bapenda_db_connection_pool_size{adapter}` - Pool size
- `bapenda_db_connection_pool_used{adapter}` - Used connections
- `bapenda_db_query_errors_total{adapter, error_type}` - Query errors

#### 3. MCP Tool Metrics
- `bapenda_mcp_tool_executions_total{tool, status}` - Tool execution count
- `bapenda_mcp_tool_duration_seconds{tool}` - Tool execution time
- `bapenda_mcp_tool_errors_total{tool, error_code}` - Tool errors

#### 4. LLM Metrics
- `bapenda_llm_requests_total{model, status}` - LLM request count
- `bapenda_llm_token_usage_total{model, type}` - Token usage
- `bapenda_llm_request_duration_seconds{model}` - LLM request latency
- `bapenda_llm_streaming_duration_seconds` - Streaming latency

#### 5. RAG Metrics
- `bapenda_rag_ingestions_total{document_type, status}` - Document ingestion
- `bapenda_rag_searches_total{status}` - Search count
- `bapenda_rag_search_duration_seconds` - Search latency
- `bapenda_rag_documents_indexed` - Total documents in index

#### 6. Auth/RBAC Metrics
- `bapenda_auth_attempts_total{status}` - Authentication attempts
- `bapenda_auth_token_validations_total{status}` - Token validations
- `bapenda_rbac_permission_checks_total{result}` - Permission check results
- `bapenda_rbac_scope_violations_total{role}` - Scope violations

### System Metrics

System-level metrics are collected by `node_exporter`:

- CPU usage (per core, per service)
- Memory usage (RSS, virtual memory)
- Disk I/O (read/write bytes, operations)
- Network I/O (bytes in/out, packets)
- Container resource usage

### Database Metrics

Database-specific metrics:

#### Oracle
- Active sessions
- Lock waits
- Tablespace usage
- Buffer cache hit ratio

#### PostgreSQL
- Active connections
- Query duration (pg_stat_statements)
- Replication lag
- Index usage

#### MySQL
- Active connections
- Query throughput
- Slow queries
- InnoDB buffer pool hit ratio

## Logging

### Log Format

All logs are JSON structured with the following fields:

```json
{
  "timestamp": "2026-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "bapenda-backend",
  "logger": "app.mcp.router",
  "request_id": "uuid",
  "user_id": "STAFF_001",
  "role": "STAFF",
  "message": "Tool executed successfully",
  "metadata": {
    "tool": "get_tax_revenue",
    "duration_ms": 123,
    "row_count": 42
  }
}
```

### Log Levels

| Level | Use Case | Retention |
|-------|----------|-----------|
| DEBUG | Detailed debugging | 1 day |
| INFO | General information | 30 days |
| WARNING | Warning conditions | 90 days |
| ERROR | Error conditions | 1 year |
| CRITICAL | Critical failures | 7 years |

### Sensitive Data Handling

The following are NEVER logged:

- Passwords or credentials
- JWT tokens
- Personal Identifiable Information (PII)
- Database connection strings
- API keys
- Secret keys

PII redaction is applied automatically before logging.

## Distributed Tracing

### Trace Context

W3C Trace Context is used for distributed tracing:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

### Spans

Each operation creates a span with:

- Operation name (e.g., `mcp.execute`, `db.query`, `llm.generate`)
- Start time and duration
- Attributes (service, tool, parameters, etc.)
- Events (exceptions, retries, etc.)
- Links to related spans (for async operations)

### Service Map

The trace data creates a service map showing:

- Service dependencies
- Request flow
- Bottlenecks
- Error hotspots

## Alerting

### Alert Rules

The following alerts are configured in Grafana:

#### Critical Alerts (Immediate Response)

| Alert | Condition | Response |
|-------|-----------|----------|
| Service Down | `up{job="..."} == 0` for 1 minute | Page on-call |
| Database Unreachable | `bapenda_db_connection_pool_used / bapenda_db_connection_pool_size > 0.9` for 5 minutes | Page on-call |
| Audit Log Failure | `bapenda_audit_log_writes_total{status="error"} > 0` | Page security |

#### Warning Alerts (Next Business Day)

| Alert | Condition | Response |
|-------|-----------|----------|
| High Latency | P95 latency > 5s for 5 minutes | Investigate |
| High Error Rate | Error rate > 1% for 5 minutes | Investigate |
| Token Usage Spike | Token usage 2x normal | Investigate |
| Disk Space Low | Disk usage > 80% | Clean up |

#### Info Alerts (Weekly Review)

| Alert | Condition | Response |
|-------|-----------|----------|
| New Document Ingested | `bapenda_rag_ingestions_total` increase | Review |
| User Activity Anomaly | User count > 3x normal | Review |

### Alert Routing

| Severity | Channel | Escalation |
|----------|---------|------------|
| Critical | PagerDuty + Slack | Immediate |
| Warning | Slack | Within 4 hours |
| Info | Email | Within 24 hours |

## Dashboards

### Service Overview Dashboard

- Service health status
- Request rate per service
- Error rate per service
- Latency (P50, P95, P99) per service
- Active users

### Database Dashboard

- Query throughput per database
- Query latency per database
- Active connections per database
- Slow queries
- Lock waits

### LLM Dashboard

- Request rate per model
- Token usage per model
- Latency per model
- Error rate per model
- Cost tracking (if applicable)

### RAG Dashboard

- Document count by type
- Search rate
- Search latency
- Index size
- Reranking performance

### Auth/RBAC Dashboard

- Authentication attempts
- Token validations
- Permission denials
- Active sessions
- Token refresh rate

## Health Checks

### Liveness Probe

Simple check that the service is running:

```bash
GET /health
```

Returns:
- 200 OK if service is alive
- 503 Service Unavailable if not

### Readiness Probe

Check that the service is ready to accept requests:

```bash
GET /ready
```

Returns:
- 200 OK if all dependencies are connected
- 503 Service Unavailable if any dependency is unreachable

### Deep Health Check

Detailed health status of all components:

```bash
GET /health/deep
```

Returns detailed status of:
- Database connections
- LLM service
- Vector database
- Cache
- External services

## Backup & Recovery

### Database Backups

- Full backup: Daily at 02:00
- Incremental backup: Every 6 hours
- Retention: 30 days

### Configuration Backups

- Git version control
- Daily snapshot of production config
- Retention: 90 days

### Disaster Recovery

- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 1 hour
- DR site: Secondary data center
- Failover: Automated with manual confirmation

## Operational Procedures

### Deployment

1. Deploy to staging environment
2. Run integration tests
3. Deploy to production (blue-green)
4. Verify health checks
5. Monitor metrics for 1 hour
6. Decommission old version

### Incident Response

1. Alert fires
2. On-call engineer acknowledges
3. Investigate using dashboards and logs
4. Apply fix or rollback
5. Document incident
6. Conduct post-mortem

### Capacity Planning

- Review metrics weekly
- Identify trends
- Plan capacity 3 months ahead
- Procure resources as needed

## Implementation Status

| Component | Status |
|-----------|--------|
| Prometheus | ⏳ Pending |
| Grafana | ⏳ Pending |
| Loki | ⏳ Pending |
| Tempo | ⏳ Pending |
| Alert rules | ⏳ Pending |
| Dashboards | ⏳ Pending |
| Backup automation | ⏳ Pending |
| DR runbook | ⏳ Pending |