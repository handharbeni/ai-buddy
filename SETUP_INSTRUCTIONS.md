# BAPENDA Platform - Setup Instructions

## ✅ Current Status Verified

1. **Ollama LLM**: Running with custom model `bapenda-ai:latest` (Qwen3 14.8B) ✅
   - URL: http://localhost:11434
   - Available models: `bapenda-ai:latest`, `qwen3:14b`

2. **Database Authentication**: Configured for multi-database, multi-type support ✅
   - File: `backend/app/config.py`
   - Supports: Oracle, PostgreSQL, MySQL
   - Each type can have multiple named connections (e.g., 3 Oracle DBs)
   - Auth via environment variables (secrets management ready)

3. **Backend API**: Ready to start (FastAPI) ✅
   - File: `backend/app/main.py`
   - Health endpoint: `/health`
   - API docs: `/docs`

4. **Frontend**: Code ready (Next.js 14) ✅
   - File: `frontend/`
   - Requires: `npm install` then `npm run dev`

## 🔧 Database Authentication Setup

**Multiple authentications per database type: YES**

Example configuration in `config.py`:

```python
# Oracle - 3 different databases
ORACLE_CONNECTIONS = {
    "primary": {
        "host": "oracle-prod-1.bapenda.go.id",
        "service_name": "BAPROD",
        "user": "AI_READONLY_PRIMARY",
        "password_env": "ORACLE_PRIMARY_PASSWORD",  # Set in .env or system
    },
    "dr_site": {
        "host": "oracle-dr.bapenda.go.id",
        "service_name": "BADRP",
        "user": "AI_READONLY_DR",
        "password_env": "ORACLE_DR_PASSWORD",
    },
    "staging": {
        "host": "oracle-stg.bapenda.go.id",
        "service_name": "BASTG",
        "user": "AI_READONLY_STG",
        "password_env": "ORACLE_STG_PASSWORD",
    },
}

# PostgreSQL - Primary and replica
POSTGRESQL_CONNECTIONS = {
    "primary": { ... },
    "replica": { ... },
}

# MySQL - Single or multiple
MYSQL_CONNECTIONS = {
    "region_master": { ... },
    "warehouse": { ... },
}
```

**To use:**
1. Set environment variables for each `*_password_env`
2. The `DatabaseRouter` in MCP tools will select the appropriate connection based on:
   - Tool configuration (each tool specifies which connection to use)
   - User scope/role (RBAC filtering applied at query level)

## 🚀 Starting the Services

### Option 1: Using Batch Files (Windows)
1. **Backend**: Double-click `start_backend.bat` or run:
   ```cmd
   C:\Users\Administrator\Documents\DBI-DB\start_backend.bat
   ```
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

2. **Frontend**: Double-click `start_frontend.bat` or run:
   ```cmd
   C:\Users\Administrator\Documents\DBI-DB\start_frontend.bat
   ```
   - Frontend UI: http://localhost:3000

### Option 2: Manual Start
```cmd
# Backend (from backend\ directory)
C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (from frontend\ directory)
npm run dev
```

## 📋 Expected URLs Once Running

| Service | URL | Description |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | FastAPI application |
| **API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| **Alternative Docs** | http://localhost:8000/redoc | ReDoc documentation |
| **Frontend Dashboard** | http://localhost:3000 | Next.js chat interface |
| **Ollama LLM** | http://localhost:11434 | LLM service (already running) |
| **Health Check** | http://localhost:8000/health | Backend health endpoint |

## 🔑 Environment Variables Needed

Create a `.env` file in the project root (`C:\Users\Administrator\Documents\DBI-DB\.env`):

```env
# Database Passwords (example)
ORACLE_PRIMARY_PASSWORD=your_oracle_primary_password
ORACLE_DR_PASSWORD=your_oracle_dr_password
ORACLE_STG_PASSWORD=your_oracle_stg_password
PG_PASSWORD
PG_PASSWORD=your_postgresql_password
MYSQL_PASSWORD=your_mysql_password

# JWT Secret (generate a strong secret)
JWT_SECRET_KEY=your_jwt_secret_key_here_min_32_chars

# Optional: OIDC
# OIDC_ISSUER=https://your-oidc-provider.com
# OIDC_CLIENT_ID=your-client-id
# OIDC_CLIENT_SECRET_ENV=OIDC_CLIENT_SECRET
```

## 🧪 Testing After Startup

Once both services are running:

```bash
# Test backend health
curl http://localhost:8000/health

# Test API docs
curl http://localhost:8000/docs

# Test a sample query (requires auth token)
# First login to get token, then:
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Berapa realizasi pajak PBB bulan ini?"}'

# Test Ollama directly
curl http://localhost:11434/api/tags
```

## 📝 Notes

- **Security**: All database connections are READ-ONLY (`AI_READONLY` user)
- **Scope**: Queries automatically filtered by user's NPWP, KPP, Kanwil via RBAC
- **LLM**: Uses your custom `bapenda-ai:latest` model via Ollama
- **Frontend**: Will auto-connect to backend at `http://localhost:8000`

**Please confirm:**
1. Do you want me to help you start the services now?
2. Or would you prefer to run the batch files yourself?

Once services are running, I'll provide the exact URLs to access the dashboard.