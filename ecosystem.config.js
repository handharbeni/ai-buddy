// ecosystem.config.js
const path = require('path');
const os = require('os');

const isWindows = os.platform() === 'win32';

let backendConfig;
let frontendConfig;

if (isWindows) {
  // Konfigurasi Windows (sudah ada)
  backendConfig = require('./ecosystem.backend.config.js');
  frontendConfig = require('./ecosystem.frontend.config.js');
} else {
  // Konfigurasi Linux/macOS
  backendConfig = require('./ecosystem.backend.linux.config.js');
  frontendConfig = require('./ecosystem.frontend.linux.config.js');
}

// Gabungkan konfigurasi dari backend dan frontend
// PM2 dapat membaca array dari beberapa file config, tapi lebih aman menggabungkannya di sini
module.exports = {
  apps: [...backendConfig.apps, ...frontendConfig.apps]
};
