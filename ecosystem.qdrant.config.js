// PM2 Ecosystem Config - Qdrant Vector DB
// Standalone binary managed by PM2
//
// Usage:
//   pm2 start ecosystem.qdrant.config.js
//   pm2 monit

module.exports = {
  apps: [
    {
      name: 'qdrant-vector',
      script: '/opt/qdrant/qdrant',
      args: '--storage-path /app/data/qdrant --http-port 6333',
      cwd: '/opt/qdrant',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        QDRANT_URL: 'http://127.0.0.1:6333'
      },
      error_file: '/app/logs/qdrant-err.log',
      out_file: '/app/logs/qdrant-out.log',
      log_file: '/app/logs/qdrant-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      pid_file: '/app/logs/qdrant.pid'
    }
  ]
};