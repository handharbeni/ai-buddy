// PM2 Ecosystem Config - Backend (FastAPI + Uvicorn)
// Python process managed by PM2
//
// Usage:
//   pm2 start ecosystem.backend.config.js
//   pm2 monit
//   pm2 save
//   pm2 startup

module.exports = {
  apps: [
    {
      name: 'bapenda-backend',
      script: '/opt/venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000 --workers 2',
      cwd: '/app/backend',
      exec_mode: 'cluster',
      instances: 'max',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        LLM_BACKEND: 'ollama',
        LLM_BASE_URL: 'http://127.0.0.1:11434',
        LLM_MODEL: 'bapenda-ai:latest',
        QDRANT_URL: 'http://127.0.0.1:6333',
        JWT_SECRET: 'change-me-in-production-please',
        JWT_ALGORITHM: 'HS256',
        JWT_ACCESS_EXPIRE_MIN: '15',
        STORAGE_DB_PATH: '/app/data/app.db',
        USE_MOCK_DB: '1',
        APP_NAME: 'Local AI Platform',
        APP_TAGLINE: 'Internal AI for Data Intelligence'
      },
      error_file: '/app/logs/backend-err.log',
      out_file: '/app/logs/backend-out.log',
      log_file: '/app/logs/backend-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      pid_file: '/app/logs/backend.pid'
    }
  ]
};