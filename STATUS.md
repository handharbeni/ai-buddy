# BAPENDA Platform Status

## ✅ VERIFIED WORKING
- **Ollama LLM**: Running with custom model `bapenda-ai:latest` 
  - URL: http://localhost:11434
  - Models: `bapenda-ai:latest`, `qwen3:14b`

## 📁 CODE READY
- **Backend API** (FastAPI): Complete
  - File: `backend/app/main.py`
  - Health: `http://localhost:8000/health`
  - Docs: `http://localhost:8000/docs`
- **Frontend** (Next.js 14): Complete
  - File: `frontend/`
  - Requires: `npm install` then `npm run dev`
- **Database Auth**: Multi-DB/multi-type configured
  - File: `backend/app/config.py`
  - Supports: Oracle, PostgreSQL, MySQL
  - Multiple connections per type (e.g., 3 Oracle DBs)

## 🚀 TO START SERVICES

### Option 1: Batch Files (Recommended)
1. **Backend**: Run `start_backend.bat`
   - Starts on: http://localhost:8000
2. **Frontend**: Run `start_frontend.bat`  
   - Starts on: http://localhost:3000

### Option 2: Manual
```cmd
# Backend
cd /d "C:\Users\Administrator\Documents\DBI-DB\backend"
"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (in separate cmd)
cd /d "C:\Users\Administrator\Documents\DBI-DB\frontend"
npm run dev
```

## 🔑 DATABASE AUTHENTICATION (MULTI-DB SUPPORT)

Your `config.py` supports **multiple authentications per database type**:

```python
# Example: 3 Oracle databases
DATABASES = {
    "oracle": {
        "primary_prod": {
            "host": "oracle-prod-1.bapenda.go.id",
            "service_name": "BAPROD", 
            "user": "AI_READONLY_PRIMARY",
            "password_env": "ORACLE_PRIMARY_PASSWORD"
        },
        "dr_site": {
            "host": "oracle-dr.bapenda.go.id",
            "service_name": "BADRP",
            "user": "AI_READONLY_DR", 
            "password_env": "ORACLE_DR_PASSWORD"
        },
        "staging": {
            "host": "oracle-stg.bapenda.go.id",
            "service_name": "BASTG",
            "user": "AI_READONLY_STG",
            "password_env": "ORACLE_STG_PASSWORD"
        }
    }
    # Similar for postgresql/mysql
}
```

Set passwords via environment variables or `.env` file:
```
ORACLE_PRIMARY_PASSWORD=xxx
ORACLE_DR_PASSWORD=xxx  
ORACLE_STG_PASSWORD=xxx
PG_PASSWORD=xxx
MYSQL_PASSWORD=xxx
JWT_SECRET_KEY=your_32+char_secret_here
```

## 📋 EXPECTED URLS WHEN RUNNING

| Service | URL | Notes |
|---------|-----|-------|
| **Backend API** | http://localhost:8000 | FastAPI application |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Alt Docs** | http://localhost:8000/redoc | ReDoc |
| **Frontend** | http://localhost:3000 | Next.js chat interface |
| **Ollama** | http://localhost:11434 | Your custom LLM (running) |
| **Health** | http://localhost:8000/health | Backend health check |

## 🧪 QUICK TEST

Once both services are running:
```bash
# Check backend
curl http://localhost:8000/health

# Check frontend (should return HTML)
curl -s http://localhost:3000 | head -5

# Check Ollama (already working)
curl http://localhost:11434/api/tags
```

**Ready to start services? Let me know which method you prefer!**