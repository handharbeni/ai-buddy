# Docker Topology

## Overview

Container architecture for development, staging, and production environments. All services run in isolated containers with defined networks, volumes, and security policies.

## Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER NETWORKS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  frontend    │    │   backend    │    │   data       │                   │
│  │  _net        │    │   _net       │    │   _net       │                   │
│  │  (bridge)    │    │  (bridge)    │    │  (bridge)    │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         ▼                   ▼                   ▼                            │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │                    TRAEFIK / NGINX PROXY                      │           │
│  │  (Edge router, TLS termination, rate limiting, WAF)         │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Network Definitions

| Network | Driver | Purpose | Services |
|---------|--------|---------|----------|
| `frontend_net` | bridge | Frontend ↔ Proxy | nextjs, traefik |
| `backend_net` | bridge | API ↔ Internal Services | fastapi, ollama, mcp-router, redis, qdrant |
| `data_net` | bridge | Internal ↔ Databases | fastapi, mcp-router, oracle, postgresql, mysql |
| `monitoring_net` | bridge | Observability | prometheus, grafana, loki, tempo |

## Service Definitions

### 1. Traefik (Edge Router)

```yaml
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.dashboard=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--certificatesresolvers.le.acme.email=admin@bapenda.go.id"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.le.acme.tlschallenge=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=frontend_net"
      - "--log.level=INFO"
      - "--accesslog=true"
      - "--accesslog.format=json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard (internal only)
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "letsencrypt:/letsencrypt"
      - "./traefik/traefik.yml:/etc/traefik/traefik.yml:ro"
      - "./traefik/dynamic:/etc/traefik/dynamic:ro"
    networks:
      - frontend_net
      - backend_net
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(`traefik.bapenda.local`)"
      - "traefik.http.routers.traefik.entrypoints=websecure"
      - "traefik.http.routers.traefik.tls.certresolver=le"
      - "traefik.http.routers.traefik.middlewares=auth@file"
      - "traefik.http.services.traefik.loadbalancer.server.port=8080"
```

### 2. Next.js Frontend

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    image: bapenda/frontend:${VERSION:-latest}
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.bapenda.local
      - NEXT_PUBLIC_WS_URL=wss://api.bapenda.local
      - NEXT_TELEMETRY_DISABLED=1
    networks:
      - frontend_net
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`app.bapenda.local`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=le"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 3. FastAPI Backend

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    image: bapenda/backend:${VERSION:-latest}
    environment:
      - ENVIRONMENT=production
      - DATABASE_ORACLE_DSN=${ORACLE_DSN}
      - DATABASE_ORACLE_USER=AI_READONLY
      - DATABASE_ORACLE_PASSWORD_FILE=/run/secrets/oracle_password
      - DATABASE_POSTGRESQL_DSN=${POSTGRESQL_DSN}
      - DATABASE_POSTGRESQL_USER=AI_READONLY
      - DATABASE_POSTGRESQL_PASSWORD_FILE=/run/secrets/postgresql_password
      - DATABASE_MYSQL_DSN=${MYSQL_DSN}
      - DATABASE_MYSQL_USER=AI_READONLY
      - DATABASE_MYSQL_PASSWORD_FILE=/run/secrets/mysql_password
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - MCP_ROUTER_URL=http://mcp-router:8001
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - JWT_ALGORITHM=RS256
      - JWT_PUBLIC_KEY_FILE=/run/secrets/jwt_public_key
      - OIDC_ISSUER=https://idp.bapenda.go.id
      - OIDC_CLIENT_ID=bapenda-ai
      - OIDC_CLIENT_SECRET_FILE=/run/secrets/oidc_client_secret
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - RATE_LIMIT_REQUESTS=60
      - RATE_LIMIT_WINDOW=60
    networks:
      - backend_net
      - data_net
      - monitoring_net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
    secrets:
      - oracle_password
      - postgresql_password
      - mysql_password
      - jwt_secret
      - jwt_public_key
      - oidc_client_secret
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.bapenda.local`) && PathPrefix(`/api`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=le"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### 4. MCP Router

```yaml
services:
  mcp-router:
    build:
      context: ./mcp
      dockerfile: Dockerfile
      target: production
    image: bapenda/mcp-router:${VERSION:-latest}
    environment:
      - ENVIRONMENT=production
      - DATABASE_ORACLE_DSN=${ORACLE_DSN}
      - DATABASE_ORACLE_USER=AI_READONLY
      - DATABASE_ORACLE_PASSWORD_FILE=/run/secrets/oracle_password
      - DATABASE_POSTGRESQL_DSN=${POSTGRESQL_DSN}
      - DATABASE_POSTGRESQL_USER=AI_READONLY
      - DATABASE_POSTGRESQL_PASSWORD_FILE=/run/secrets/postgresql_password
      - DATABASE_MYSQL_DSN=${MYSQL_DSN}
      - DATABASE_MYSQL_USER=AI_READONLY
      - DATABASE_MYSQL_PASSWORD_FILE=/run/secrets/mysql_password
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - TOOL_TIMEOUT=30000
      - MAX_ROWS=1000
    networks:
      - backend_net
      - data_net
      - monitoring_net
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    secrets:
      - oracle_password
      - postgresql_password
      - mysql_password
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

### 5. Ollama (Local LLM - Development)

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_MODELS=/models
      - OLLAMA_KEEP_ALIVE=24h
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_LOADED_MODELS=2
    volumes:
      - ollama_models:/models
    networks:
      - backend_net
    deploy:
      resources:
        limits:
          cpus: '8.0'
          memory: 32G
        reservations:
          cpus: '4.0'
          memory: 16G
    security_opt:
      - no-new-privileges:true
    # GPU support for production
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### 6. vLLM (Local LLM - Production)

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    command:
      - "--model=Qwen/Qwen2.5-14B-Instruct"
      - "--tensor-parallel-size=1"
      - "--gpu-memory-utilization=0.9"
      - "--max-model-len=32768"
      - "--max-num-seqs=256"
      - "--enforce-eager"
      - "--disable-log-requests"
      - "--served-model-name=qwen2.5"
    environment:
      - HF_HOME=/models
      - VLLM_WORKER_MULTIPROC_METHOD=spawn
    volumes:
      - vllm_models:/models
    networks:
      - backend_net
    deploy:
      resources:
        limits:
          cpus: '16.0'
          memory: 64G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/models"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
```

### 7. Qdrant (Vector Database)

```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.8
    command:
      - "--config-path=/qdrant/config/production.yaml"
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__STORAGE__OPTIMIZERS__DELETED_THRESHOLD=0.2
      - QDRANT__STORAGE__OPTIMIZERS__VACUUM_MIN_VECTOR_NUMBER=1000
      - QDRANT__STORAGE__WAL__WAL_CAPACITY_MB=32
      - QDRANT__STORAGE__WAL__WAL_CHECKPOINT_INTERVAL_MB=8
    volumes:
      - qdrant_data:/qdrant/storage
      - ./qdrant/config/production.yaml:/qdrant/config/production.yaml:ro
    networks:
      - backend_net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

### 8. Redis (Cache & Queue)

```yaml
services:
  redis:
    image: redis:7-alpine
    command:
      - redis-server
      - --appendonly=yes
      - --maxmemory=2gb
      - --maxmemory-policy=allkeys-lru
      - --save=900 1
      - --save=300 10
      - --save=60 10000
    volumes:
      - redis_data:/data
    networks:
      - backend_net
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

### 9. Oracle Database (External - Connection Only)

```yaml
# Oracle runs externally. Only connection configuration here.
# Use Oracle Instant Client in backend/mcp-router containers.
# 
# Environment variables for connection:
# ORACLE_DSN: "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=oracle.bapenda.internal)(PORT=1522))(CONNECT_DATA=(SERVICE_NAME=BAPENDA)))"
# 
# Wallet location: /opt/oracle/wallet (mounted as secret)
# 
# Network: Oracle must be reachable from data_net
# Firewall: Allow 1522/TCPS from backend_net, data_net
```

### 10. PostgreSQL (External - Connection Only)

```yaml
# PostgreSQL runs externally (managed service or separate VM)
# 
# Environment variables:
# POSTGRESQL_DSN: "postgresql://AI_READONLY@postgresql.bapenda.internal:5432/bapenda_analytics?sslmode=verify-full"
# 
# SSL certificates: /etc/ssl/postgresql/ (mounted as secret)
# 
# Network: Allow 5432 from data_net
```

### 11. MySQL (External - Connection Only)

```yaml
# MySQL runs externally
# 
# Environment variables:
# MYSQL_DSN: "mysql://AI_READONLY@mysql.bapenda.internal:3306/bapenda_master?sslmode=VERIFY_IDENTITY"
# 
# SSL certificates: /etc/ssl/mysql/ (mounted as secret)
# 
# Network: Allow 3306 from data_net
```

## Volumes

| Volume | Driver | Purpose | Backup |
|--------|--------|---------|--------|
| `ollama_models` | local | LLM model weights | No (reproducible) |
| `vllm_models` | local | vLLM model cache | No (reproducible) |
| `qdrant_data` | local | Vector embeddings | Yes (daily) |
| `redis_data` | local | Cache persistence | No (ephemeral) |
| `letsencrypt` | local | TLS certificates | Yes (weekly) |

## Secrets (Docker Secrets / External Vault)

| Secret | Description | Rotation |
|--------|-------------|----------|
| `oracle_password` | AI_READONLY Oracle password | 90 days |
| `postgresql_password` | AI_READONLY PostgreSQL password | 90 days |
| `mysql_password` | AI_READONLY MySQL password | 90 days |
| `jwt_secret` | RS256 private key (PEM) | 365 days |
| `jwt_public_key` | RS256 public key (PEM) | 365 days |
| `oidc_client_secret` | OIDC client secret | 180 days |
| `oracle_wallet` | Oracle Wallet (cwallet.sso, ewallet.p12) | 365 days |
| `postgresql_ssl` | PostgreSQL client cert/key | 365 days |
| `mysql_ssl` | MySQL client cert/key | 365 days |

## Docker Compose Files

### Development (docker-compose.dev.yml)

```yaml
version: '3.8'

services:
  traefik:
    # ... dev config with self-signed certs
  
  frontend:
    build:
      target: development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev
    environment:
      - NODE_ENV=development
  
  backend:
    build:
      target: development
    volumes:
      - ./backend:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
  
  mcp-router:
    build:
      target: development
    volumes:
      - ./mcp:/app
    command: python -m mcp_router --reload
  
  ollama:
    # ... same as production but smaller resources
  
  qdrant:
    # ... same as production
  
  redis:
    # ... same as production

networks:
  frontend_net:
  backend_net:
  data_net:
  monitoring_net:

volumes:
  ollama_models:
  qdrant_data:
  redis_data:
  letsencrypt:
```

### Production (docker-compose.prod.yml)

```yaml
version: '3.8'

services:
  traefik:
    # ... production config with Let's Encrypt
  
  frontend:
    # ... production build
  
  backend:
    # ... production build
  
  mcp-router:
    # ... production build
  
  vllm:
    # ... production GPU config
  
  qdrant:
    # ... production config
  
  redis:
    # ... production config

networks:
  frontend_net:
    external: true
  backend_net:
    external: true
  data_net:
    external: true
  monitoring_net:
    external: true

volumes:
  vllm_models:
    external: true
  qdrant_data:
    external: true
  redis_data:
    external: true
  letsencrypt:
    external: true

secrets:
  oracle_password:
    external: true
  postgresql_password:
    external: true
  mysql_password:
    external: true
  jwt_secret:
    external: true
  jwt_public_key:
    external: true
  oidc_client_secret:
    external: true
  oracle_wallet:
    external: true
  postgresql_ssl:
    external: true
  mysql_ssl:
    external: true
```

## Security Hardening

### Container Security
- All containers: `no-new-privileges:true`
- All containers: `read_only: true` (except where tmpfs needed)
- Non-root user: `user: "1000:1000"` in Dockerfiles
- Drop capabilities: `cap_drop: [ALL]`
- Seccomp profile: `security_opt: ["seccomp=default.json"]`

### Network Security
- No external egress from `backend_net`, `data_net`
- Ingress only via Traefik on `frontend_net`
- mTLS between all internal services (future: service mesh)
- Database connections: TLS only (TCPS, SSL, SSL)

### Resource Limits
- CPU/memory limits on all containers
- OOM score adjustment
- PIDs limit: `pids_limit: 1000`

## Deployment Commands

```bash
# Development
docker compose -f docker-compose.dev.yml up -d

# Production (with secrets pre-created)
docker compose -f docker-compose.prod.yml up -d

# Scale backend
docker compose -f docker-compose.prod.yml up -d --scale backend=3

# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Health check all
docker compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
```

## Backup & Restore

```bash
# Qdrant backup
docker exec qdrant qdrant-backup --uri http://localhost:6333 --output /backup/qdrant-$(date +%F).snapshot

# Redis backup (RDB)
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb ./backup/redis-$(date +%F).rdb

# Let's Encrypt
tar -czf ./backup/letsencrypt-$(date +%F).tar.gz /var/lib/docker/volumes/letsencrypt/_data
```

## Monitoring Endpoints

| Service | Metrics Port | Health Endpoint |
|---------|--------------|-----------------|
| Traefik | 8080 | /ping |
| Frontend | 3000 | /api/health |
| Backend | 8000 | /health |
| MCP Router | 8001 | /health |
| Ollama | 11434 | /api/tags |
| vLLM | 8000 | /v1/models |
| Qdrant | 6333 | /health |
| Redis | 6379 | PING |