// ecosystem.backend.config.js
module.exports = {
  apps: [{
    name: 'bapenda-backend',
    script: 'C:/Users/Administrator/Documents/DBI-DB/start-backend.bat',
    args: '',
    cwd: 'C:/Users/Administrator/Documents/DBI-DB', // Root direktori untuk Windows
    interpreter: 'cmd',
    exec_mode: 'fork',
    max_memory_restart: '4G',
    error_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/backend-err.log',
    out_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/backend-out.log',
    log_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/backend-combined.log',
    log_date_format: 'YYYY-MM-DD HH:mm Z',
    pid_file: 'C:/Users/Administrator/Documents/DBI-DB/logs/backend.pid',
    env: {
      NODE_ENV: 'production', // Contoh: untuk backend jika perlu
      PORT: 8000, // Port backend FastAPI
      LLM_SERVER_URL: 'http://localhost:11434', // Contoh: URL LLM Server
      LLM_MODEL_NAME: 'your-llm-model', // Contoh: Nama model LLM
      // Tambahkan variabel lingkungan backend lainnya di sini
    }
  }]
};
