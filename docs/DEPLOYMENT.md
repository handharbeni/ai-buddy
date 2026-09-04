# Deployment Guide — Local AI Data Intelligence Platform

Dokumen ini mencakup SEMUA aspek deployment: prerequisites, arsitektur, setup local, Docker, VPN, environment config, database setup, monitoring, backup, dan production checklist.

Untuk dokumentasi API (endpoint, schema, authentication), lihat [`docs/API.md`](./API.md).

---

## Table of Contents

1. [Ringkasan Arsitektur](#1-arsitektur)
2. [Prerequisites](#2-prerequisites)
3. [Quick Start](#3-quick-start)
4. [Project Setup](#4-project-setup)
5. [Environment Variables](#5-environment-variables)
6. [Database Configuration](#6-database-configuration)
7. [LLM / Ollama Setup](#7-llm--ollama-setup)
8. [VPN Setup (Single & Multi)](#8-vpn-setup)
9. [RAG (Document Search)](#9-rag--document-search)
10. [Docker Deployment](#10-docker-deployment)
11. [Production Deployment](#11-production-deployment)
12. [Monitoring & Logging](#12-monitoring--logging)
13. [Backup & Restore](#13-backup--restore)
14. [Troubleshooting](#14-troubleshooting)
15. [Production Checklist](#15-production-checklist)

---

## 1. Arsitektur

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser / Client                                                     │
│  http://localhost:3000  (frontend)                                  │
└────────────────────────┬──────────────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼──────────────────────────────────────────────┐
│  Reverse Proxy (nginx) — port 443 / 80                              │
│  - SSL termination                                                  │
│  - Rate limiting                                                     │
│  - Serve static /api/* → backend :8000                             │
└──────────┬──────────────────────────────────────┬───────────────────┘
           │                                      │
┌──────────▼──────────┐           ┌───────────────▼─────────────────┐
│  Frontend            │           │  Backend (FastAPI)               │
│  Next.js :3000       │           │  :8000                           │
│  (standalone image)  │           │                                  │
└─────────────────────┘           │  ┌─ Auth (JWT, RBAC)            │
                                   │  ├─ Audit (append-only)         │
                                   │  ├─ Rate Limiting               │
                                   │  ├─ Prompt Injection Guard       │
                                   │  ├─ MCP Router (6 tools)        │
                                   │  ├─ RAG Pipeline                │
                                   │  ├─ LLM Orchestrator            │
                                   │  ├─ Output Formatter (7 fmt)    │
                                   │  └─ Conversation Storage (SQLite)│
                                   └──────────────┬──────────────────┘
                                                  │
                         ┌────────────────────────┼────────────────────┐
                         │                        │                    │
               ┌─────────▼───────┐    ┌──────────▼──────┐   ┌────────▼──────┐
               │  VPN Container   │    │  Qdrant         │   │  Ollama       │
               │  (single/multi)  │    │  Vector Store   │   │  Local LLM    │
               │  tun0, tun10...  │    │  :6333          │   │  :11434       │
               └─────────┬─────────┘    └─────────────────┘   └───────────────┘
                         │ (optional — hanya jika DB di private network)
               ┌─────────▼───────────────────────────────────────────┐
               │  Remote Databases (Oracle / PostgreSQL / MySQL)    │
               │  READ-ONLY access. No INSERT, UPDATE, DELETE.       │
               └─────────────────────────────────────────────────────┘
```

### Container Images

| Service | Image | Default Port |
|---------|-------|-------------|
| `backend` / `backend-vpn` | `localai/backend:latest` | 8000 |
| `frontend` | `localai/frontend:latest` | 3000 → 8080 |
| `qdrant` | `qdrant/qdrant:v1.7.4` | 6333 |
| `ollama` | `ollama/ollama:latest` | 11434 |
| `vpn` / `vpn-multi` | `localai/vpn:latest` | — |

---

## 2. Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16+ GB |
| CPU | 4 cores | 8+ cores |
| Storage | 20 GB | 50+ GB SSD |
| GPU (for LLM) | None (CPU inference) | NVIDIA GPU with CUDA 12+ |

### Software

| Software | Version | Required For |
|----------|---------|-------------|
| Docker | 24+ | Container deployment |
| Docker Compose | 2.20+ | Multi-service orchestration |
| Python | 3.11+ | Local development |
| Node.js | 20+ | Frontend development |
| Ollama | latest | Local LLM inference |
| Git | any | Source code |

### Docker Desktop vs. Native Docker

| OS | Recommended | Note |
|----|-------------|------|
| Windows | Docker Desktop | WSL2 backend |
| macOS | Docker Desktop | |
| Linux | Native Docker + Docker Compose | |

> **Windows**: Pastikan WSL2 diaktifkan dan Docker Desktop menggunakan WSL2 backend untuk performa terbaik.

---

## 3. Quick Start

### 3.1 Clone / Copy Project

```bash
git clone <repository-url>
cd DBI-DB
```

### 3.2 Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env — minimal config untuk development:
# APP_NAME=My Organization AI
# USE_MOCK_DB=1          # 1 = mock DB, 0 = real DB
# LLM_BASE_URL=http://localhost:11434
```

### 3.3 Start (Development — Mock DB, No VPN)

```bash
# Start semua service
docker compose up -d

# Atau untuk development dengan hot-reload
docker compose up
```

**Akses:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard
- Ollama: http://localhost:11434

### 3.4 Login (Development)

```
Username: admin
Password: admin123

Roles: ADMIN, SUPERVISOR, ANALYST, STAFF
```

---

## 4. Project Setup

### 4.1 Directory Structure

```
DBI-DB/
├── backend/                  # FastAPI backend
│   └── app/
│       ├── api/v1/         # REST endpoints
│       ├── auth/           # JWT authentication
│       ├── config.py       # Settings (env-driven)
│       ├── db/             # DB adapters (Oracle, PG, MySQL)
│       ├── llm/            # LLM client + orchestrator
│       ├── mcp/            # MCP tool router
│       ├── middleware/     # CORS, RBAC, audit
│       ├── orchestrator/   # Intent → tool → synthesis pipeline
│       ├── output/         # Multi-format output
│       ├── rag/            # RAG pipeline
│       ├── rbac/           # Role-based access control
│       ├── security/       # Prompt injection detection
│       └── storage/        # SQLite (conversations, users)
├── frontend/                 # Next.js frontend
│   └── app/
│       ├── page.tsx       # Main app (chat + users + settings)
│       └── globals.css     # Linear dark theme
├── docker/                  # Docker-specific files
│   └── vpn/                # VPN container (OpenVPN)
├── docs/                    # Documentation
│   ├── DEPLOYMENT.md       # This file
│   └── API.md              # API reference
├── docker-compose.yml       # Multi-service orchestration
├── Dockerfile.backend       # Backend image
├── Dockerfile.frontend      # Frontend image
├── .env.example            # Environment template
├── .env                     # Your secrets (never commit)
├── .dockerignore
└── README.md
```

### 4.2 Environment File

```bash
# Wajib: copy dari .env.example
cp .env.example .env

# Edit minimal:
nano .env
```

**Minimal development `.env`:**
```bash
APP_NAME=My Organization AI
APP_TAGLINE=Internal AI Assistant
USE_MOCK_DB=1
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=local-ai:latest
JWT_SECRET=change-me-in-production-please
```

---

## 5. Environment Variables

### 5.1 Project Branding

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Local AI Platform` | Nama aplikasi (terlihat di login page) |
| `APP_SHORT_NAME` | `LocalAI` | Nama pendek |
| `APP_TAGLINE` | `Internal AI for Data Intelligence` | Tagline |
| `APP_INSTITUTION` | — | Nama organisasi/institusi |
| `APP_DOMAIN` | `data` | Domain/subject area |
| `APP_VERSION` | `1.0.0` | Version string |

### 5.2 LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `ollama` | Backend: `ollama` atau `vllm` |
| `LLM_BASE_URL` | `http://localhost:11434` | LLM server URL |
| `LLM_MODEL` | `local-ai:latest` | Model name |
| `LLM_TIMEOUT` | `120` | Timeout dalam detik |

### 5.3 Database Configuration

 Setiap database mengikuti pola `DB_<NAME>_*`:

| Variable | Deskripsi |
|----------|-----------|
| `ORACLE_<NAME>_HOST` | Oracle host |
| `ORACLE_<NAME>_PORT` | Oracle port (default 1521) |
| `ORACLE_<NAME>_SERVICE` | Oracle service name / SID |
| `ORACLE_<NAME>_USER` | Username |
| `ORACLE_<NAME>_PASSWORD` | Password (via .env, bukan hardcode) |
| `POSTGRES_<NAME>_HOST` | PostgreSQL host |
| `POSTGRES_<NAME>_PORT` | PostgreSQL port (default 5432) |
| `POSTGRES_<NAME>_DB` | Database name |
| `POSTGRES_<NAME>_USER` | Username |
| `POSTGRES_<NAME>_PASSWORD` | Password |
| `MYSQL_<NAME>_HOST` | MySQL host |
| `MYSQL_<NAME>_PORT` | MySQL port (default 3306) |
| `MYSQL_<NAME>_DB` | Database name |
| `MYSQL_<NAME>_USER` | Username |
| `MYSQL_<NAME>_PASSWORD` | Password |

**Contoh (BAPENDA):**
```bash
ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PORT=1521
ORACLE_BATAMAI_SERVICE=simpbb
ORACLE_BATAMAI_USER=batamai
ORACLE_BATAMAI_PASSWORD=batamai2026
```

### 5.4 VPN Configuration

| Variable | Description |
|----------|-------------|
| `VPN_SUBNETS` | Subnet untuk single-VPN mode (contoh: `10.11.0.0/16`) |
| `SINGLE_VPN_SUBNETS` | Alias untuk `VPN_SUBNETS` |
| `ORACLE_SUBNETS` | Subnet via `oracle.ovpn` tunnel |
| `MYSQL_SUBNETS` | Subnet via `mysql.ovpn` tunnel |
| `POSTGRES_SUBNETS` | Subnet via `postgres.ovpn` tunnel |

Generic pattern: `DB_<UPPERCASE_BASENAME>_SUBNETS`

### 5.5 Auth & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `change-me-in-production-please` | Secret key untuk JWT signing |
| `JWT_ALGORITHM` | `HS256` | Algorithm |
| `JWT_ACCESS_EXPIRE_MIN` | `15` | Token expiry dalam menit |
| `USE_MOCK_DB` | `1` | 1=mock (dev), 0=real DB |
| `CORS_ORIGINS` | `["http://localhost:3000", ...]` | Allowed origins |

### 5.6 Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_DB_PATH` | `./data/app.db` | SQLite DB untuk conversations + users |

---

## 6. Database Configuration

### 6.1 Read-Only Policy

**SELURUH koneksi database adalah READ-ONLY.** Tidak ada INSERT, UPDATE, DELETE, DROP, ALTER, atau TRUNCATE yang pernah dieksekusi. Defense in depth:

1. **DB Adapter layer** — hanya `execute_query()` yang SELECT
2. **RBAC layer** — tools hanya expose read operations
3. **Audit layer** — semua query logged
4. **SQLAlchemy model** — read-only ORM patterns

### 6.2 Oracle

#### Development (Mock)
```bash
USE_MOCK_DB=1
```

#### Production

```bash
USE_MOCK_DB=0

ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PORT=1521
ORACLE_BATAMAI_SERVICE=simpbb
ORACLE_BATAMAI_USER=batamai
ORACLE_BATAMAI_PASSWORD=batamai2026
```

**Oracle connection string format:**
```
(host)/(service_name)  atau  (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=<host>)(PORT=<port>))(CONNECT_DATA=(SERVICE_NAME=<service>)))
```

**Oracle SQL grants (minimum untuk platform):**
```sql
-- Buat user dedicated untuk platform
CREATE USER batamai IDENTIFIED BY "batamai2026";
GRANT CONNECT, RESOURCE TO batamai;

-- Grant untuk query saja (read-only)
GRANT SELECT ANY DICTIONARY TO batamai;
GRANT SELECT ON <schema>.<table> TO batamai;

-- Contoh grants untuk BAPENDA tables:
GRANT SELECT ON batamai.vw_tax_revenue TO batamai;
GRANT SELECT ON batamai.vw_tax_arrears TO batamai;
GRANT SELECT ON batamai.vw_taxpayer_summary TO batamai;
```

### 6.3 PostgreSQL

```bash
USE_MOCK_DB=0

POSTGRES_PRIMARY_HOST=pg.internal.example.com
POSTGRES_PRIMARY_PORT=5432
POSTGRES_PRIMARY_DB=production_db
POSTGRES_PRIMARY_USER=localai_reader
POSTGRES_PRIMARY_PASSWORD=SecurePassword123
```

**PostgreSQL grants:**
```sql
-- Buat user read-only
CREATE USER localai_reader WITH PASSWORD 'SecurePassword123';
GRANT CONNECT ON DATABASE production_db TO localai_reader;
GRANT USAGE ON SCHEMA public TO localai_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO localai_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO localai_reader;
```

### 6.4 MySQL

```bash
USE_MOCK_DB=0

MYSQL_PRIMARY_HOST=mysql.internal.example.com
MYSQL_PRIMARY_PORT=3306
MYSQL_PRIMARY_DB=analytics_db
MYSQL_PRIMARY_USER=localai_reader
MYSQL_PRIMARY_PASSWORD=SecurePassword123
```

**MySQL grants:**
```sql
-- Buat user read-only
CREATE USER 'localai_reader'@'%' IDENTIFIED BY 'SecurePassword123';
GRANT SELECT ON analytics_db.* TO 'localai_reader'@'%';
FLUSH PRIVILEGES;
```

### 6.5 Multiple Databases

Platform mendukung banyak database sekaligus. Setiap database punya konfigurasi sendiri:

```bash
# Database A (Oracle)
ORACLE_A_HOST=10.11.0.252
ORACLE_A_PORT=1521
ORACLE_A_SERVICE=simpbb
ORACLE_A_USER=reader_a
ORACLE_A_PASSWORD=xxx

# Database B (PostgreSQL)
POSTGRES_B_HOST=pg2.internal.example.com
POSTGRES_B_PORT=5432
POSTGRES_B_DB=db_b
POSTGRES_B_USER=reader_b
POSTGRES_B_PASSWORD=xxx
```

---

## 7. LLM / Ollama Setup

### 7.1 Ollama (Recommended for Development)

```bash
# Install Ollama
# https://ollama.ai/download

# Pull model
ollama pull bapenda-ai:latest

# Atau build dari base
ollama pull qwen2.5:3b-instruct
ollama run qwen2.5:3b-instruct "print('hello')"

# Verify
curl http://localhost:11434/api/tags
```

**Docker compose sudah includes Ollama container** — tidak perlu install separately jika pakai `docker compose up`.

### 7.2 Custom Model (Production)

```bash
# Build custom model dari base
ollama create bapenda-ai:latest \
  --from qwen2.5:3b-instruct \
  --system /path/to/system-prompt.txt

# Set model di .env
LLM_MODEL=bapenda-ai:latest
```

### 7.3 vLLM (GPU Production)

```bash
# vLLM server (standalone)
vllm serve \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.9

# .env
LLM_BACKEND=vllm
LLM_BASE_URL=http://vllm-host:8000
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### 7.4 System Prompt (Domain Knowledge)

Customize `backend/app/llm/prompts.py` untuk menambahkan domain knowledge spesifik organisasi. Ini penting untuk akurasi respons, terutama untuk:
- Istilah domain-specific
- Format output yang diharapkan
- Role/behavior AI assistant
- Constraint dan guardrails

---

## 8. VPN Setup

### 8.1 Overview: 3 Deployment Modes

| Mode | Command | Database access |
|------|---------|----------------|
| **Development** | `docker compose up` | Mock DB atau DB reachable langsung |
| **Single VPN** | `docker compose --profile vpn up` | 1 database di private network |
| **Multi-VPN** | `docker compose --profile vpn-multi up` | Banyak DB di banyak private network |

### 8.2 Single VPN Mode

Gunakan ketika hanya SATU database yang perlu VPN.

**Files:**
```
docker/vpn/
├── config.ovpn      # OpenVPN profile
└── auth.txt         # Username (line 1), Password (line 2)
```

**Setup:**
```bash
# 1. Buat credentials
mkdir -p docker/vpn
cp /path/to/batamai.ovpn docker/vpn/config.ovpn
printf 'vpn_user\nvpn_pass' > docker/vpn/auth.txt
chmod 600 docker/vpn/auth.txt

# 2. Set .env
SINGLE_VPN_SUBNETS=10.11.0.0/16
USE_MOCK_DB=0
ORACLE_BATAMAI_HOST=10.11.0.252

# 3. Start
docker compose --profile vpn up -d
```

### 8.3 Multi-VPN Mode (Per-Database Tunnels)

Gunakan ketika BANYAK database masing-masing di private network berbeda.

**Files:**
```
docker/vpn/
├── oracle-a.ovpn          # VPN untuk Oracle A
├── auth_oracle-a.txt
├── oracle-b.ovpn          # VPN untuk Oracle B
├── auth_oracle-b.txt
├── vpn-d.ovpn             # VPN D (shared untuk MySQL B + PostgreSQL B)
├── auth_vpn-d.txt
├── mysql-a.ovpn           # VPN untuk MySQL A
├── auth_mysql-a.txt
├── postgres-a.ovpn        # VPN untuk PostgreSQL A
└── auth_postgres-a.txt
```

**Routing rules di `.env`:**
```bash
# Oracle A via VPN A
ORACLE_A_SUBNETS=10.11.0.0/16

# Oracle B via VPN B
ORACLE_B_SUBNETS=10.12.0.0/16

# MySQL A via VPN C
MYSQL_A_SUBNETS=192.168.10.0/24

# VPN D (shared tunnel): MySQL B + PostgreSQL B
VPN_D_SUBNETS=192.168.20.0/24,172.16.10.0/24

# PostgreSQL A via VPN E
POSTGRES_A_SUBNETS=172.17.0.0/16

# Production DB config
USE_MOCK_DB=0
ORACLE_A_HOST=10.11.0.252
ORACLE_B_HOST=10.12.0.100
MYSQL_A_HOST=192.168.10.50
MYSQL_B_HOST=192.168.20.50
POSTGRES_A_HOST=172.17.0.10
```

**Start:**
```bash
docker compose --profile vpn-multi up -d
```

**Verify:**
```bash
# Cek tunnel
docker compose exec vpn-multi ip link show | grep tun

# Cek routing
docker compose exec vpn-multi ip rule show

# Test per-database
docker compose exec vpn-multi sh -c "cat < /dev/tcp/10.11.0.252/1521"
docker compose exec vpn-multi sh -c "cat < /dev/tcp/192.168.10.50/3306"
```

### 8.4 VPN Subnet Convention

Routing key diambil dari basename file `.ovpn`:
- `oracle-a.ovpn` → env var `ORACLE_A_SUBNETS`
- `mysql-prod.ovpn` → env var `MYSQL_PROD_SUBNETS`
- `legacy.ovpn` → env var `LEGACY_SUBNETS`

---

## 9. RAG (Document Search)

The **RAG service** allows the AI to answer questions from **regulation documents** (Perda, Pergub, SOP, Surat Edaran) — not just database numbers.

### How It Works

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│ Admin/      │───▶│ RAG service      │───▶│  Qdrant      │
│ Operator    │    │ (port 8002)      │    │  collection: │
│ uploads PDF │    │ - chunk text     │    │  regulations │
│             │    │ - embed (BGE-M3) │    └──────────────┘
└─────────────┘    │ - store vectors  │
                   └──────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │  Backend        │ ◀── User asks question
                   │  (port 8000)    │     via /api/v1/query
                   │  - proxy to RAG │
                   │  - LLM synthesis│
                   └─────────────────┘
```

### Activate RAG Profile

```bash
# Start with RAG service
docker compose --profile rag up -d

# Or with VPN
docker compose --profile vpn --profile rag up -d
```

This starts an extra container `localai-rag` on port 8002. Pre-downloads the `BAAI/bge-m3` embedding model on first build (saves time later).

### Two Ways to Ingest Documents

#### Option A: Admin UI (drag-drop)

1. Login as `admin`
2. Click `📚 Knowledge` in sidebar
3. Drag-drop PDF/DOCX/MD/TXT files
4. Fill metadata (title, type, document number, etc.)
5. Click Upload

#### Option B: CLI (batch)

```bash
# From host (against running RAG service)
python rag/ingest_cli.py ./regulations/

# From inside container
docker compose exec backend python /path/to/ingest_cli.py ./regulations/

# With custom URL (RAG service running on different host)
python rag/ingest_cli.py ./regulations/ --url http://rag:8002

# Dry-run (preview metadata without upload)
python rag/ingest_cli.py ./regulations/ --dry-run
```

### Auto-Detection

The CLI auto-detects from filename + content:

| Filename pattern | Detected as | Number |
|---|---|---|
| `perda_3_2024.pdf` | `PERDA` | `3/2024` |
| `pergub_15_2025.docx` | `PERGUB` | `15/2025` |
| `sop_penagihan.md` | `SOP` | auto |
| `se_dispen_2024.txt` | `SURAT_EDARAN` | auto |
| `manual_layanan.pdf` | `GENERAL` | auto |

YAML frontmatter in `.md` files overrides auto-detection:
```markdown
---
title: PERDA No 3/2024 tentang Pajak Hotel
type: PERDA
number: 3
year: 2024
authority: DPRD Kota Batam
effective_date: 2024-03-15
---
```

### RAG API Endpoints (proxied via backend)

| Backend endpoint | Forwarded to | Auth |
|---|---|---|
| `GET /api/v1/rag/health` | `GET /health` | any user |
| `POST /api/v1/rag/search` | `POST /search` | any user |
| `GET /api/v1/rag/documents` | `GET /collection/info` | any user |
| `POST /api/v1/rag/ingest` | `POST /ingest` | admin/supervisor |
| `DELETE /api/v1/rag/documents/{id}` | `DELETE /documents/{id}` | admin/supervisor |

### Environment Variables

```bash
# In .env
EMBEDDING_MODEL=BAAI/bge-m3      # sentence-transformer model
RAG_BASE_URL=http://rag:8002      # internal Docker URL
# Or if RAG runs on different host:
# RAG_BASE_URL=http://10.0.0.5:8002
```

### Storage

Documents are stored in:
- **Qdrant collection** `regulations` (vectors + metadata) — backed by `qdrant_data` volume
- **Embedding model cache** at `/app/.cache/hf` inside RAG container — backed by `rag_models` volume

### Verifying

```bash
# Check RAG health
curl http://localhost:8002/health

# Check via backend proxy
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/rag/health

# Search (returns top-5 matching chunks)
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "tarif pajak hotel", "top_k": 3}'
```

### How AI Uses RAG in Chat

When user asks a question, the orchestrator may:
1. Detect intent → "regulation_query" or "hybrid_query"
2. Call `/api/v1/rag/search` with the question
3. Get top-5 chunks from Perda/Pergub
4. Feed chunks + question to LLM
5. LLM synthesizes answer with citations: "Berdasarkan Perda No. 3/2024..."

---

## 10. Docker Deployment

### 9.1 Build Images

```bash
# Build semua image
docker compose build

# Build spesifik
docker compose build backend
docker compose build frontend
docker compose build vpn
```

### 9.2 Start Services

```bash
# Development mode (mock DB, hot-reload friendly)
docker compose up

# Background
docker compose up -d

# Dengan VPN
docker compose --profile vpn up -d

# Dengan multi-VPN
docker compose --profile vpn-multi up -d

# Checklist layanan
docker compose ps
```

### 9.3 Build + Push to Registry

```bash
# Login ke registry
docker login registry.example.com

# Tag images
docker tag localai/backend:latest registry.example.com/localai/backend:latest
docker tag localai/frontend:latest registry.example.com/localai/frontend:latest

# Push
docker push registry.example.com/localai/backend:latest
docker push registry.example.com/localai/frontend:latest
```

### 9.4 Access Logs

```bash
# Semua service
docker compose logs -f

# Backend saja
docker compose logs -f backend
docker compose logs -f backend-vpn

# Filter by time
docker compose logs --since 30m

# Follow specific container
docker compose logs -f vpn-multi
```

### 9.5 Restart / Reload

```bash
# Restart semua
docker compose restart

# Restart satu service
docker compose restart backend

# Rebuild + restart
docker compose up -d --build

# Reload config tanpa restart
docker compose up -d
```

### 9.6 Environment File untuk Docker

```bash
# .env untuk Docker deployment
docker compose --env-file .env up -d
```

**Critical production variables:**
```bash
# WAJIB dirubah
JWT_SECRET=<64-char-random-string>

# DB
USE_MOCK_DB=0
ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PASSWORD=<from-secrets-manager>

# Branding
APP_NAME=Organization Name
APP_INSTITUTION=Institution Name

# VPN (jika perlu)
SINGLE_VPN_SUBNETS=10.11.0.0/16
```

---

## 10. Production Deployment

### 10.1 Recommended Architecture

```
                    ┌──────────────┐
        Users ────► │  Cloudflare  │ (CDN + DDoS protection)
                    │  / DNS       │
                    └──────┬───────┘
                           │ HTTPS (443)
                    ┌──────▼───────┐
                    │  nginx       │ (reverse proxy)
                    │  :443        │
                    └──────┬───────┘
                           │ Proxy pass
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼──────┐ ┌────▼─────┐ ┌─────▼─────┐
    │  Backend     │ │  Frontend │ │  Ollama   │
    │  :8000       │ │  :3000    │ │  :11434   │
    └───────┬──────┘ └──────────┘ └───────────┘
            │              │
    ┌───────▼──────────────▼──────────────┐
    │        VPN Container(s)              │
    │  (tun0 / tun10, tun11, ...)        │
    └───────┬──────────────────────────────┘
            │ (routed via VPN)
    ┌───────▼──────────────┐
    │  Oracle / PG / MySQL │
    │  (Private network)   │
    └──────────────────────┘
```

### 10.2 nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/localai
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name ai.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.example.com;

    ssl_certificate     /etc/letsencrypt/live/ai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend
    location / {
        proxy_pass         http://frontend;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering    off;
    }

    # Backend API
    location /api/ {
        proxy_pass         http://backend;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        client_max_body_size 10M;
    }

    # Rate limiting per IP (nginx level)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
    location /api/ {
        limit_req zone=api_limit burst=50 nodelay;
    }
}
```

```bash
# Aktifkan
sudo ln -s /etc/nginx/sites-available/localai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10.3 SSL / TLS

**Option A: Let's Encrypt (Gratis)**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ai.example.com
# Auto-renewal sudah di-setup otomatis
```

**Option B: Commercial Certificate**

Mount certificate di `docker-compose.yml`:
```yaml
backend:
  volumes:
    - /path/to/cert.pem:/app/cert.pem:ro
    - /path/to/key.pem:/app/key.pem:ro
```

### 10.4 Systemd Service (Docker Compose Auto-start)

```bash
# /etc/systemd/system/localai.service
[Unit]
Description=Local AI Data Intelligence Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/localai
ExecStart=/usr/local/bin/docker compose --env-file /opt/localai/.env up -d
ExecStop=/usr/local/bin/docker compose down
Restart=on-failure
RestartSec=10s
User=<deployment-user>

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable localai
sudo systemctl start localai
sudo systemctl status localai
```

### 10.5 Deployment User

```bash
# Buat dedicated user (bukan root)
sudo useradd -r -s /bin/false localai
sudo chown -R localai:localai /opt/localai

# User harus punya akses Docker
sudo usermod -aG docker localai
```

### 10.6 Firewall

```bash
# UFW example
sudo ufw default deny incoming
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS (nginx)
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw enable
```

---

## 11. Monitoring & Logging

### 11.1 Health Checks

```bash
# Cek semua service
curl http://localhost:8000/health

# Cek individual
curl http://localhost:6333/healthz
curl http://localhost:11434/api/tags

# Docker health
docker compose ps
docker compose exec backend curl -f http://localhost:8000/health
```

### 11.2 Application Logs

Backend logs semua request + audit trail:
```bash
# Follow backend logs
docker compose logs -f backend

# Filter by level
docker compose logs backend | grep ERROR
docker compose logs backend | grep AUDIT

# Export logs
docker compose logs backend > logs/backend-$(date +%Y%m%d).log
```

### 11.3 Structured Logging

Backend menggunakan structured logging (JSON). Fields:

| Field | Description |
|-------|-------------|
| `request_id` | Unique UUID per request |
| `user` | Username |
| `role` | User role |
| `intent` | Detected intent |
| `tools_used` | Tools called |
| `latency_ms` | Total latency |
| `status` | success/error |
| `prompt_injection` | true/false (if detected) |

### 11.4 Prometheus Metrics (TODO)

Endpoint `/metrics` akan menampilkan:
- `localai_requests_total` — total requests by endpoint + status
- `localai_request_duration_seconds` — histogram
- `localai_db_connection_status` — 1=up, 0=down
- `localai_llm_latency_seconds` — LLM inference time

---

## 12. Backup & Restore

### 12.1 SQLite (Conversations + Users)

**Location:** `backend/data/app.db` (mapped to Docker volume `app_data`)

```bash
# Backup (hot — SQLite supports concurrent reads)
docker compose exec backend sh -c 'cp /app/data/app.db /app/data/app.db.bak'
docker cp localai-backend:/app/data/app.db.bak ./backups/

# Backup with timestamp
docker compose exec backend sh -c \
  'cp /app/data/app.db /app/data/app-$(date +%Y%m%d-%H%M%S).db'
```

**Restore:**
```bash
docker compose exec -T backend sh -c 'cat > /app/data/app.db' < ./backups/app.db.bak
docker compose exec backend chmod 644 /app/data/app.db
docker compose restart backend
```

**Automated backup (crontab):**
```bash
# /etc/cron.d/localai-backup
0 2 * * * root docker compose exec backend sh -c 'cp /app/data/app.db /app/data/app.db.bak' && \
  docker cp localai-backend:/app/data/app.db.bak /opt/backups/localai-$(date +\%Y\%m\%d).db
```

### 12.2 Volumes

```bash
# List volumes
docker volume ls | grep localai

# Backup volume
docker run --rm \
  -v localai_app_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/app_data-$(date +%Y%m%d).tar.gz -C /data .

# Restore volume
docker run --rm \
  -v localai_app_data:/data \
  -v $(pwd)/backups:/backup \
  alpine sh -c 'tar xzf /backup/app_data-YYYYMMDD.tar.gz -C /data'
```

### 12.3 Docker Images

```bash
# Backup image to tar
docker save -o backups/localai-backend.tar localai/backend:latest
docker save -o backups/localai-frontend.tar localai/frontend:latest

# Restore
docker load -i backups/localai-backend.tar
```

---

## 13. Troubleshooting

### Backend tidak start

```bash
# Cek logs
docker compose logs backend

# Cek config
docker compose config

# Cek port conflict
netstat -ano | findstr :8000
# Atau di Linux: ss -tlnp | grep 8000
```

### Oracle connection gagal

```bash
# Test network (dari host)
ping 10.11.0.252
nc -zv 10.11.0.252 1521

# Test dari dalam container (dengan VPN)
docker compose --profile vpn exec backend sh -c \
  'python -c "import oracledb; print(oracledb.connect(user=...)"'

# Cek Oracle driver installed
docker compose exec backend python -c "import oracledb; print(oracledb.__version__)"
```

### VPN tidak connect

```bash
# Cek logs
docker compose logs vpn
docker compose logs vpn-multi

# Cek TUN device
docker compose exec vpn ip link show tun0

# Cek credentials
docker compose exec vpn cat /vpn/auth.txt

# Cek .ovpn config
docker compose exec vpn cat /vpn/config.ovpn | head -20
```

### Qdrant tidak available

```bash
# Cek Qdrant container
docker compose logs qdrant
docker compose exec qdrant ls /qdrant/storage

# Reset Qdrant volume
docker compose down qdrant
docker volume rm localai_qdrant_data
docker compose up -d qdrant
```

### LLM timeout / tidak respond

```bash
# Cek Ollama
curl http://localhost:11434/api/tags

# Test model
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"bapenda-ai:latest","prompt":"hello","stream":false}'

# Rebuild model
docker compose exec ollama ollama pull bapenda-ai:latest
docker compose restart ollama
```

### Frontend tidak bisa connect ke Backend

```bash
# Cek CORS config
docker compose logs backend | grep CORS

# Test langsung
curl -H "Authorization: Bearer <token>" \
     -H "Origin: http://localhost:3000" \
     http://localhost:8000/api/v1/auth/me

# Cek NEXT_PUBLIC_API_URL
docker compose exec frontend env | grep NEXT_PUBLIC
```

### Konfigurasi .env tidak terbaca

```bash
# Docker compose wajib pakai .env di working directory
# Atau gunakan --env-file flag
docker compose --env-file /path/to/.env up -d

# Verify loaded env
docker compose exec backend env | grep APP_
docker compose exec backend env | grep ORACLE_
```

---

## 14. Production Checklist

### Security

- [ ] `JWT_SECRET` diganti dengan random 64-char string
- [ ] `APP_NAME` / branding diset ke nama organisasi
- [ ] `USE_MOCK_DB=0` untuk production
- [ ] Credentials di `.env` (tidak di hardcode)
- [ ] SSL/TLS enabled (HTTPS only)
- [ ] CORS `CORS_ORIGINS` diset ke domain production
- [ ] Rate limiting nginx diaktifkan
- [ ] Firewall configured (port 443 only, SSH jika perlu)
- [ ] Docker tidak running sebagai root
- [ ] `.env` tidak di-commit ke git

### Database

- [ ] Oracle/PostgreSQL/MySQL credentials di `.env`
- [ ] User database adalah read-only (hanya SELECT)
- [ ] VPN config benar jika DB di private network
- [ ] `ORACLE_SUBNETS` / `MYSQL_SUBNETS` / `POSTGRES_SUBNETS` diset
- [ ] DB grants diverifikasi dengan `SHOW GRANTS`

### Infrastructure

- [ ] Docker images di-push ke private registry
- [ ] Volumes (app_data, qdrant_data, ollama_data) di-backup
- [ ] nginx reverse proxy configured
- [ ] SSL certificate valid dan auto-renewal aktif
- [ ] Systemd service untuk auto-start
- [ ] Monitoring / alerting setup
- [ ] Backup schedule aktif (SQLite + volumes)

### LLM

- [ ] Model downloaded di Ollama container
- [ ] `LLM_MODEL` diset ke model yang tepat
- [ ] System prompt sudah dikustomisasi untuk domain
- [ ] GPU memory cukup untuk model size

### Operational

- [ ] Log rotation configured
- [ ] `docker-compose.yml` ada di version control
- [ ] `docs/DEPLOYMENT.md` dan `docs/API.md` up-to-date
- [ ] Team memahami VPN routing setup
- [ ] Runbook untuk restore dari backup tersedia
- [ ] Rollback plan ada (previous image tag)

---

## Quick Reference

```bash
# Development
docker compose up

# Production
docker compose --env-file .env up -d --build

# VPN (single)
docker compose --profile vpn --env-file .env up -d

# VPN (multi-database)
docker compose --profile vpn-multi --env-file .env up -d

# Logs
docker compose logs -f backend

# Restart
docker compose restart backend

# Update image
docker compose pull
docker compose up -d

# Full rebuild
docker compose down
docker compose build --no-cache
docker compose up -d

# Backup SQLite
docker cp localai-backend:/app/data/app.db ./backups/

# CLI exec
docker compose exec backend python -c "from app.config import get_settings; print(get_settings().app_name)"

# Cek semua env vars
docker compose exec backend env | grep -E '^(APP_|ORACLE_|POSTGRES_|MYSQL_|LLM_|JWT_)' | sort

# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```
