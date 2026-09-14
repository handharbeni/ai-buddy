// PM2 Ecosystem Config - Ollama LLM
// LLM service managed by PM2
//
// Usage:
//   pm2 start ecosystem.ollama.config.js
//   pm2 monit

module.exports = {
  apps: [
    {
      name: 'ollama-llm',
      script: '/usr/local/bin/ollama',
      args: 'serve',
      cwd: '/root',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        OLLAMA_HOST: '127.0.0.1',
        OLLAMA_PORT: '11434',
        OLLAMA_MODELS: '/app/data/models'
      },
      error_file: '/app/logs/ollama-err.log',
      out_file: '/app/logs/ollama-out.log',
      log_file: '/app/logs/ollama-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      pid_file: '/app/logs/ollama.pid'
    }
  ]
};