// ecosystem.frontend.config.js
module.exports = {
  apps: [{
    name: 'bapenda-frontend',
    script: 'C:/Users/Administrator/Documents/DBI-DB/start-frontend.bat',
    args: '',
    cwd: 'C:/Users/Administrator/Documents/DBI-DB', // Root direktori untuk Windows
    interpreter: 'cmd',
    exec_mode: 'fork',
    max_memory_restart: '4G',
    error_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/frontend-err.log',
    out_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/frontend-out.log',
    log_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/frontend-combined.log',
    log_date_format: 'YYYY-MM-DD HH:mm Z',
    pid_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/frontend.pid',
    env: {
      NODE_ENV: 'production',
      PORT: 3000, // Next.js default port
      NEXT_PUBLIC_BACKEND_API_URL: 'http://localhost:8000', // Contoh frontend specific env vars
      NEXT_PUBLIC_LLM_API_URL: 'http://localhost:11434' // Contoh jika frontend perlu akses LLM (jarang)
    }
  }]
};
