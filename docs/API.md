# API Reference — BAPENDA Local AI Data Intelligence Platform

Dokumentasi endpoint API untuk platform AI lokal BAPENDA.

---

## Table of Contents

1. [Auth](#1-auth)
2. [Query](#2-query)
3. [Conversations](#3-conversations)
4. [Users](#4-users)
5. [RAG Documents](#5-rag-documents)
6. [Download](#6-download)
7. [LLM Health](#7-llm-health)
8. [Config](#8-config)
9. [WebSocket](#9-websocket)
10. [Metrics](#10-metrics)
11. [Health Check](#11-health-check)

---

## Base URL

```
http://localhost:8000
```

All endpoints return JSON unless otherwise noted.

---

## Authentication

All endpoints (except `/health`, `/docs`, `/openapi.json`, `/api/v1/config`, `/api/v1/llm/health`, `/metrics`) require a JWT token.

Include token in header:

```
Authorization: Bearer <token>
```

---

## 1. Auth

### 1.1 Login

```
POST /api/v1/auth/login
```

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | yes | Username |
| `password` | string | yes | Password |

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiAiSFMyNTYi...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error (401):**

```json
{
  "detail": "Invalid credentials"
}
```

### 1.2 Current User

```
GET /api/v1/auth/me
```

**Response (200):**

```json
{
  "username": "admin",
  "role": "ADMIN",
  "scope": {"databases": ["oracle", "mysql", "postgresql"]}
}
```

### 1.3 List Users

```
GET /api/v1/users
```

**Permission:** ADMIN only

**Response (200):**

```json
[
  {
    "username": "admin",
    "user_id": "uuid",
    "role": "ADMIN",
    "display_name": "Admin",
    "scope": {},
    "is_active": true,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  }
]
```

### 1.4 Create User

```
POST /api/v1/users
```

**Permission:** ADMIN only

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | yes | 2-64 chars, alphanumeric |
| `password` | string | yes | 4-128 chars |
| `role` | string | yes | `ADMIN` \| `SUPERVISOR` \| `ANALYST` \| `STAFF` |
| `display_name` | string | no | Display name |
| `scope` | object | no | Database scope filter |

### 1.5 Update User

```
PATCH /api/v1/users/{username}
```

**Permission:** ADMIN only. Cannot modify/delete self (400).

### 1.6 Delete User

```
DELETE /api/v1/users/{username}
```

**Permission:** ADMIN only. Cannot delete self (400).

### 1.7 Reset Password

```
POST /api/v1/users/{username}/reset-password
```

**Permission:** ADMIN only.

---

## 2. Query (Main AI Endpoint)

### 2.1 Query AI

```
POST /api/v1/query
```

**Request:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | string | yes | — | Question (3-2000 chars) |
| `history` | array | no | `[]` | Message history |
| `top_k` | int | no | `5` | MCP result limit (1-20) |

**Message object:**

```json
{
  "role": "user" | "assistant",
  "content": "string"
}
```

**Response (200):**

```json
{
  "answer": "Berdasarkan Perda No. 3/2024...",
  "citations": [
    {
      "document_id": "REG_20250101_0001",
      "title": "Perda No. 3/2024",
      "chunk_index": 0,
      "text": "Pasal 3...",
      "score": 0.85
    }
  ],
  "tools_used": ["get_tax_revenue", "get_taxpayer_summary"],
  "intent": "regulation",
  "conversation_id": "uuid",
  "metadata": {
    "db_sources": ["oracle", "mysql"],
    "rag_chunks": 3,
    "processing_time_ms": 2450
  },
  "data": [],
  "suggested_format": "xlsx"
}
```

**Intent values:**

| Intent | Description |
|--------|-------------|
| `structured_query` | Numeric data question (revenue, arrears, targets) |
| `regulation` | Regulation-related (Perda, Pergub, SOP) |
| `general` | General knowledge question |

### 2.2 Stream Query (WebSocket)

```
WS /api/v1/ws/query
```

**Query param:** `token` (JWT token)

**Message sent by client:**

```json
{
  "question": "Berapa pendapatan daerah tahun ini?",
  "top_k": 5
}
```

**Server sends:**

```json
{"chunk": "Berdasarkan...", "type": "answer"}
{"chunk": "...", "type": "answer"}
{"type": "done", "answer": "...", "citations": [...], "tools_used": [...], "data": [...]}
{"error": "message"}  // on error
```

---

## 3. Conversations

All endpoints require authentication.

### 3.1 List Conversations

```
GET /api/v1/conversations
```

Returns conversations belonging to the current user (scope-scoped).

**Response (200):**

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "title": "Pendapatan Daerah",
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00",
    "message_count": 5
  }
]
```

### 3.2 Create Conversation

```
POST /api/v1/conversations
```

**Request:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | no | auto-generated | Conversation title |

**Response (201):**

```json
{
  "id": "uuid",
  "title": "New Conversation",
  "created_at": "..."
}
```

### 3.3 Get Conversation

```
GET /api/v1/conversations/{id}
```

Returns conversation with full message history.

### 3.4 Update Conversation

```
PATCH /api/v1/conversations/{id}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | New title |

### 3.5 Delete Conversation

```
DELETE /api/v1/conversations/{id}
```

Cascades: deletes all messages in the conversation.

### 3.6 Add Message

```
POST /api/v1/conversations/{id}/messages
```

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | `user` \| `assistant` | Message role |
| `content` | string | yes | Message content |

### 3.7 Clear Messages

```
DELETE /api/v1/conversations/{id}/messages
```

Removes all messages but keeps the conversation entry.

---

## 4. Users

**Permission:** ADMIN only (all endpoints).

### 4.1 List All Users

```
GET /api/v1/users
```

### 4.2 Get User

```
GET /api/v1/users/{username}
```

### 4.3 Create User

```
POST /api/v1/users
```

### 4.4 Update User

```
PATCH /api/v1/users/{username}
```

Cannot update self → returns `400`.

### 4.5 Delete User

```
DELETE /api/v1/users/{username}
```

Cannot delete self → returns `400`.

### 4.6 Reset Password

```
POST /api/v1/users/{username}/reset-password
```

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_password` | string | yes | 4-128 chars |

---

## 5. RAG Documents

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/v1/rag/health` | Any user | RAG service health |
| `GET /api/v1/rag/documents` | Any user | List documents in collection |
| `POST /api/v1/rag/search` | Any user | Search documents |
| `POST /api/v1/rag/ingest` | Admin/Supervisor | Ingest document |
| `DELETE /api/v1/rag/documents/{id}` | Admin/Supervisor | Delete document |

### 5.1 Search Documents

```
POST /api/v1/rag/search
```

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | yes | Search query |
| `top_k` | int | no | Result limit (default 5) |

### 5.2 Ingest Document

```
POST /api/v1/rag/ingest
```

**Form data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | PDF/DOCX/MD/TXT |
| `title` | string | no | Override title |
| `type` | string | no | PERDA/PERGUB/SOP/etc |
| `document_number` | string | no | Document number |
| `authority` | string | no | Issuing authority |
| `effective_date` | string | no | Effective date |
| `version` | string | no | Version |
| `tags` | string | no | Comma-separated tags |

**Response (200):**

```json
{
  "status": "ingested",
  "document_id": "REG_20250101_0001",
  "title": "Perda No. 3/2024",
  "chunks": 42,
  "content_hash": "sha256:..."
}
```

### 5.3 List Documents

```
GET /api/v1/rag/documents
```

**Response:**

```json
{
  "count": 5,
  "documents": [
    {
      "id": "REG_20250101_0001",
      "title": "Perda No. 3/2024",
      "type": "PERDA",
      "document_number": "3/2024",
      "authority": "DPRD Kabupaten X",
      "version": "1.0",
      "effective_date": "2024-01-01",
      "chunk_count": 42,
      "content_hash": "sha256:...",
      "uploaded_at": "2025-01-01T00:00:00",
      "status": "active"
    }
  ]
}
```

### 5.4 Delete Document

```
DELETE /api/v1/rag/documents/{document_id}
```

---

## 6. Download

### 6.1 List Formats

```
GET /api/v1/download/formats
```

**Response:**

```json
{
  "formats": ["xlsx", "csv", "json", "html", "markdown", "docx", "pdf"]
}
```

### 6.2 Download

```
POST /api/v1/download
```

**Request:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `data` | array | yes | — | Data rows |
| `format` | string | no | `xlsx` | Output format |
| `question` | string | no | `""` | Original question |
| `answer` | string | no | `""` | LLM answer |

**Response:** Binary file download with appropriate Content-Type.

| Format | Content-Type | Extension |
|--------|-------------|-----------|
| `xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` |
| `csv` | `text/csv` | `.csv` |
| `json` | `application/json` | `.json` |
| `html` | `text/html` | `.html` |
| `markdown` | `text/markdown` | `.md` |
| `docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |
| `pdf` | `application/pdf` | `.pdf` |

---

## 7. LLM Health

```
GET /api/v1/llm/health
```

No auth required.

**Response (200):**

```json
{
  "status": "healthy",
  "model": "bapenda-ai:latest",
  "backend": "ollama",
  "uptime_seconds": 3600
}
```

**Error (503):** Ollama not reachable.

---

## 8. Config

```
GET /api/v1/config
```

No auth required. Returns branding configuration.

**Response:**

```json
{
  "app_name": "BAPENDA Local AI Platform",
  "app_short_name": "BAPENDA AI",
  "tagline": "Intelligent Tax & Compliance Intelligence",
  "institution": "BAPENDA Regional Tax Authority",
  "domain": "data.bapenda.go.id",
  "version": "1.0.0"
}
```

Override via env vars: `APP_NAME`, `APP_TAGLINE`, `APP_INSTITUTION`, `APP_DOMAIN`, `APP_VERSION`.

---

## 9. WebSocket

```
WS /api/v1/ws/query?token=<jwt>
```

**Connection:** Upgrade to WebSocket.

**Client → Server:**

```json
{"question": "...", "top_k": 5}
```

**Server → Client:**

```json
{"chunk": "partial answer...", "type": "answer"}
```

```json
{"type": "done", "answer": "full answer", "citations": [...], "tools_used": [...], "data": [...]}
```

```json
{"error": "error message"}
```

---

## 10. Metrics (Prometheus)

```
GET /metrics
```

No auth required.

Returns Prometheus format metrics:

- `http_requests_total` — Request count by endpoint, method, status
- `http_request_duration_seconds` — Request latency histogram
- `llm_requests_total` — LLM API call counter
- `llm_tokens_total` — Token usage counter
- `db_queries_total` — Database query counter
- `rag_documents_total` — RAG document count
- `rag_queries_total` — RAG search counter
- `active_users` — Currently active users (gauge)

Example:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/v1/query",method="POST",status="200"} 142
```

---

## 11. Health Check

```
GET /health
```

No auth required.

**Response (200):**

```json
{
  "status": "healthy",
  "service": "bapenda-backend",
  "version": "1.0.0"
}
```

---

## Error Format

All errors return:

```json
{
  "detail": "Error message"
}
```

| Status Code | When |
|-------------|------|
| `400` | Bad request, cannot modify/delete self |
| `401` | Unauthorized (missing/invalid token) |
| `403` | Forbidden (insufficient role) |
| `404` | Not found |
| `422` | Validation error |
| `500` | Internal server error |
| `503` | Service unavailable (Ollama down, etc.) |

---

## Rate Limiting

| Scope | Limit | Window |
|-------|-------|--------|
| Per user (API key) | 60 req/min | 1 minute sliding |
| Per IP | 120 req/min | 1 minute sliding |

Response header on rate-limited requests:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1700000000
```

Returns `429 Too Many Requests` when exceeded.

---

## OpenAPI Schema

Full OpenAPI 3.0 schema available at:

```
http://localhost:8000/docs
```

Swagger UI: interactive API explorer with try-it-out functionality.

ReDoc alternative:

```
http://localhost:8000/redoc
```
