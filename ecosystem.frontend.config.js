// PM2 Ecosystem Config - Frontend (Next.js)
// Node.js process managed by PM2
//
// Usage:
//   pm2 start ecosystem.frontend.config.js
//   pm2 monit
//   pm2 save

module.exports = {
  apps: [
    {
      name: 'bapenda-frontend',
      script: 'npm',
      args: 'run start --prefix /app/frontend',
      cwd: '/app/frontend',
      exec_mode: 'cluster',
      instances: 'max',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        NEXT_PUBLIC_API_URL: 'http://localhost:8000',
        NEXT_PUBLIC_APP_NAME: 'Local AI Platform',
        NEXT_PUBLIC_APP_TAGLINE: 'Internal AI for Data Intelligence',
        PORT: 3000
      },
      error_file: '/app/logs/frontend-err.log',
      out_file: '/app/logs/frontend-out.log',
      log_file: '/app/logs/frontend-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      pid_file: '/app/logs/frontend.pid'
    }
  ]
};