// ecosystem.backend.linux.config.js
module.exports = {
  apps: [{
    name: 'bapenda-backend',
    script: 'start-backend.sh', // Skrip bash
    args: '', // Tidak ada argumen tambahan diperlukan untuk skrip bash
    cwd: 'C:/Users/Administrator/Documents/DBI-DB/', // Root direktori
    interpreter: 'bash', // Gunakan bash interpreter
    exec_mode: 'fork', // mode fork untuk aplikasi non-Node.js
    max_memory_restart: '4G', // Setel ke nilai yang lebih tinggi jika perlu
    // Path log yang disesuaikan untuk Linux/macOS
    error_file: '/app/logs/backend-err.log', // PM2 default path, bisa disesuaikan
    out_file: '/app/logs/backend-out.log',
    log_file: '/app/logs/backend-combined.log',
    log_date_format: 'YYYY-MM-DD HH:mm Z',
    pid_file: '/app/logs/backend.pid'
  }]
};
