# Deployment Guide: AlmaLinux (PM2)

Panduan ini berisi langkah-langkah untuk deploy *Local AI Data Intelligence Platform* di server AlmaLinux menggunakan Node.js Process Manager (PM2), tanpa Docker Compose untuk aplikasi utama.

## 0. Persyaratan Minimum

-   **OS**: AlmaLinux 9+
-   **Hardware**: RAM ≥ 8 GB (untuk model 3B + RAG embedding), disk ≥ 30 GB
-   **Perangkat Lunak**:
    -   Node.js (versi LTS direkomendasikan)
    -   Python 3.11+ (untuk backend)
    -   PM2 (global)
    -   Git
    -   Ollama (untuk LLM lokal)
    -   Qdrant (untuk RAG, bisa dijalankan via Docker atau instalasi native)
    -   Database nyata (Oracle, PostgreSQL, MySQL)

## 1. Instalasi Prasyarat

### 1.1. Node.js & npm/yarn

```bash
# Instal Node.js LTS (contoh menggunakan NodeSource)
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo dnf install -y nodejs

# Verifikasi
node -v
npm -v
# Atau yarn (jika terbiasa)
# npm install -g yarn
# yarn -v
```

### 1.2. Python 3 & Pip

AlmaLinux biasanya sudah menyertakan Python 3. Pastikan pip juga terinstal.

```bash
sudo dnf install -y python3 python3-pip
python3 --version
pip3 --version
```

### 1.3. PM2

Instal PM2 secara global:

```bash
sudo npm install pm2 -g
pm2 --version
```

### 1.4. Git

```bash
sudo dnf install -y git
git --version
```

### 1.5. Ollama (LLM Lokal)

Instalasi Ollama di AlmaLinux:

```bash
curl -fsSL https://ollama.com/install.sh | sh
# Verifikasi
ollama --version
```

### 1.6. Qdrant (Opsional, untuk RAG)

Anda bisa menginstal Qdrant secara native atau menggunakan Docker. Untuk kesederhanaan panduan ini, jika tidak menggunakan Docker Compose, kita akan asumsikan Qdrant diinstal secara terpisah (misal: native binary atau container). Jika Anda memilih Docker, jalankan Qdrant sebagai container terpisah.

```bash
# Contoh jika instalasi native (sesuaikan dengan instruksi Qdrant)
# curl -OL https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-linux-amd64-v1.7.4.tar.br
# tar -xvf qdrant-linux-amd64-v1.7.4.tar.br
# sudo mv qdrant /usr/local/bin/
# sudo systemctl enable qdrant --now # (jika ada service file)

# Atau jika menggunakan Docker (pastikan port 6333 terbuka)
# docker run -d \
#   --name localai-qdrant \
#   -p 6333:6333 \
#   -v $(pwd)/qdrant_data:/qdrant/storage \
#   qdrant/qdrant:v1.7.4
```
Pastikan Qdrant berjalan dan dapat diakses di `http://localhost:6333`.

## 2. Clone Repository & Konfigurasi

```bash
git clone <URL_REPO> /opt/DBI-DB
cd /opt/DBI-DB
cp .env.example .env
```

Edit file `.env` dengan kredensial dan konfigurasi server Anda. **Penting**:

```bash
# --- Branding ---
APP_NAME="Nama Proyek Anda"
APP_SHORT_NAME="Singkatan"
APP_TAGLINE="Platform AI Lokal untuk Intelijen Data"
APP_INSTITUTION="Nama Institusi Anda"
APP_DOMAIN="domain_data"

# --- LLM Lokal ---
LLM_BACKEND=ollama
LLM_BASE_URL=http://localhost:11434      # Akses Ollama lokal langsung
LLM_MODEL=bapenda-ai:latest             # atau nama model Ollama yang sudah ditarik
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=120

# --- Otentikasi ---
JWT_SECRET=$(openssl rand -hex 32)      # Ganti dengan string acak yang kuat
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MIN=15

# --- RAG / Qdrant ---
QDRANT_URL=http://localhost:6333        # Jika Qdrant berjalan di host yang sama
QDRANT_COLLECTION=regulations
EMBEDDING_MODEL=BAAI/bge-m3

# --- Server & Jaringan ---
API_HOST=127.0.0.1                      # Bind ke localhost untuk keamanan
API_PORT=8000
CORS_ORIGINS=["http://<IP_SERVER_ALMALINUX>:3000"] # Sesuaikan dengan IP server
FRONTEND_PORT=3000
# QDRANT_PORT, OLLAMA_PORT hanya relevan jika diakses dari host, bukan dari aplikasi backend
NEXT_PUBLIC_API_URL=http://<IP_SERVER_ALMALINUX>:8000 # Sesuaikan dengan IP server

# --- Database Mock (0 = pakai DB nyata, 1 = pakai Mock DB) ---
USE_MOCK_DB=0
```

Konfigurasi database nyata Anda (Oracle, PostgreSQL, MySQL) seperti dijelaskan di `SETUP_INSTRUCTIONS.md`.

## 3. Instal Dependensi

### 3.1. Dependensi Backend (Python)

```bash
cd /opt/DBI-DB/backend
pip3 install -r requirements.txt # Jika ada requirements.txt
# atau jika menggunakan pyproject.toml dengan Poetry/PDM/etc.
# poetry install # atau pdm install
```
Anda mungkin perlu membuat virtual environment.

### 3.2. Dependensi Frontend (Node.js)

```bash
cd /opt/DBI-DB/frontend
npm install # atau yarn install
```

## 4. Setup Model LLM Lokal (Ollama)

Model `bapenda-ai:latest` yang berbasis `qwen2.5:3b-instruct`.

```bash
ollama pull qwen2.5:3b-instruct
ollama create bapenda-ai -f ../Modelfile.bapenda
ollama list
```
Pastikan Ollama berjalan dan model siap digunakan.

## 5. Konfigurasi VPN (Opsional)

Jika database berada di jaringan privat:

1.  **Siapkan File VPN**: Tempatkan file `.ovpn` dan `auth.txt` di `docker/vpn/` (atau `auth_<nama_db>.txt` untuk multi-VPN).
2.  **Konfigurasi `.env`**: Sesuaikan `SINGLE_VPN_SUBNETS` atau `ORACLE_SUBNETS`, `MYSQL_SUBNETS`, dll., sesuai dengan rentang IP jaringan database Anda.

## 6. Jalankan Aplikasi dengan PM2

Buat file konfigurasi PM2. Asumsikan ada file `ecosystem.config.js` di root direktori proyek (atau buat satu jika belum ada).

**Contoh `ecosystem.config.js`**:

```javascript
// ecosystem.config.js
module.exports = {
  apps : [
    // Backend service (FastAPI)
    {
      name: 'backend-api',
      script: 'backend/main.py', // Path ke entry point backend
      interpreter: 'python3',    // Interpreter Python
      args: '--reload',          // Opsional: untuk auto-reload saat kode berubah (dev)
      instances: 1,
      autorestart: true,
      watch: ['./backend'],      // Watch files di direktori backend
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PORT: 8000,
        // Muat semua variabel dari .env
        // PM2 tidak otomatis membaca .env, jadi perlu di-load manual jika perlu
        // Contoh: LOAD_DOTENV_FROM: './.env'
        // Atau, jika Anda menggunakan library seperti dotenv-python di main.py
      },
      env_production: {
        NODE_ENV: 'production',
      }
    },
    // Frontend service (Next.js)
    {
      name: 'frontend-nextjs',
      script: 'frontend/node_modules/.bin/next', // Path ke executable Next.js
      args: 'start -p 3000', // Start Next.js di port 3000
      instances: 1,
      autorestart: true,
      watch: ['./frontend'], // Watch files di direktori frontend
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
        // Variabel NEXT_PUBLIC_* harus di-build saat deploy frontend
        // atau di-set di env PM2 jika Next.js dikonfigurasi untuk membaca dari env
      },
      env_production: {
        NODE_ENV: 'production',
      }
    },
    // Ollama service (jika dijalankan sebagai service terpisah)
    // Jika Ollama dijalankan via Docker, bagian ini tidak perlu.
    // Jika instalasi native:
    /*
    {
      name: 'ollama-service',
      script: '/usr/local/bin/ollama', // Sesuaikan path executable Ollama
      args: 'serve',
      instances: 1,
      autorestart: true,
      max_memory_restart: '4G',
      env: {
        OLLAMA_HOST: '127.0.0.1:11434', // Bind ke localhost
      }
    }
    */
  ]
};
```

**Catatan Penting**:
-   Pastikan `script` dan `args` merujuk pada cara Anda menjalankan aplikasi. Untuk Next.js, Anda biasanya menjalankan `next start` setelah build.
-   PM2 tidak secara otomatis membaca file `.env`. Anda perlu mengintegrasikannya. Cara paling umum adalah:
    -   Menggunakan library seperti `dotenv-python` di backend (`main.py`) untuk memuat `.env`.
    -   Menyediakan variabel lingkungan secara eksplisit di bagian `env` PM2, atau menggunakan `dotenv` di Next.js build step.

**Memulai Aplikasi dengan PM2**:

```bash
cd /opt/DBI-DB
# Jika menggunakan VPN, pastikan koneksi VPN sudah aktif sebelum start PM2
# Misalnya, jalankan script VPN Anda secara manual di background

# Mulai semua service
pm2 start ecosystem.config.js

# Atau mulai service tertentu
# pm2 start ecosystem.config.js --only backend-api
# pm2 start ecosystem.config.js --only frontend-nextjs

# Cek status
pm2 list
pm2 status

# Lihat log
pm2 logs backend-api
pm2 logs frontend-nextjs

# Restart service tertentu
# pm2 restart backend-api
```

## 7. Verifikasi

### 7.1. Cek Kesehatan Service
```bash
curl http://localhost:8000/health
curl http://localhost:3000/ # Akses frontend di browser
```

### 7.2. Cek Log PM2 (untuk error backend/frontend)
```bash
pm2 logs backend-api --lines 100 # Cek 100 baris terakhir log backend
pm2 logs frontend-nextjs --lines 100
```

### 7.3. Verifikasi Koneksi Database (via API)
```bash
# Login untuk mendapatkan token akses
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password": "***"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Lakukan query API (contoh)
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 FROM dual"}'
```

### 7.4. Verifikasi VPN Aktif (jika menggunakan VPN)
Jika Anda mengonfigurasi VPN dan menjalankannya secara terpisah (misalnya, script `vpn.sh`):

```bash
# Pastikan tunnel VPN aktif
ip link show | grep tun

# Uji koneksi ke host DB di jaringan VPN (jalankan dari server host)
ping <IP_DB_HOST>
# atau gunakan netcat
nc -zv <IP_DB_HOST> <PORT_DB>
```

## 8. RAG & LLM Lokal

-   **Ollama**: Pastikan Ollama server berjalan (baik native maupun Docker). Sesuaikan `LLM_BASE_URL` di `.env` jika Ollama berjalan di port atau host yang berbeda.
-   **Qdrant**: Pastikan Qdrant server berjalan dan dapat diakses di `QDRANT_URL` yang diset di `.env`. Jika Qdrant dijalankan native, Anda mungkin perlu mengonfigurasi systemd service untuk menjadikannya `autorestart`.
-   Untuk RAG, Anda perlu meng-ingest dokumen melalui script Python yang sesuai (misal: `backend/app/rag/ingest_cli.py`).

## 9. Firewall & Produksi Hardening (Wajib)

### 9.1. Konfigurasi Firewall
Buka port 3000 (frontend) dan 8000 (backend API) di firewall AlmaLinux.

```bash
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 9.2. Hardening Produksi
1.  **Nonaktifkan `DEV_MODE`**: Set `DEV_MODE=false` di `.env`.
2.  **Ganti Kredensial Default**: Pastikan `JWT_SECRET` adalah string acak yang kuat.
3.  **Manajemen User**: Buat user nyata melalui API `/api/v1/users`.
4.  **Keamanan Jaringan**: Gunakan reverse proxy (Nginx/Caddy) untuk expose port 3000 dengan TLS/SSL. Batasi akses port 8000 ke localhost (`API_HOST=127.0.0.1`).
5.  **Akses Database**: Gunakan akun database `READ ONLY`.

---

## Troubleshooting Cepat

-   **Backend API crash / error saat startup**:
    -   Periksa log PM2 (`pm2 logs backend-api`).
    -   Pastikan semua dependensi Python terinstal (`pip install -r requirements.txt`).
    -   Cek konfigurasi `.env` (DB credentials, `JWT_SECRET`, dll.).
-   **Frontend tidak load / CORS error**:
    -   Pastikan `NEXT_PUBLIC_API_URL` dan `CORS_ORIGINS` di `.env` mengarah ke IP server yang benar.
    -   Jika menggunakan Nginx, pastikan konfigurasinya benar.
-   **LLM/Qdrant tidak merespon**:
    -   Pastikan Ollama dan Qdrant server berjalan (cek status service/container).
    -   Verifikasi `LLM_BASE_URL`, `QDRANT_URL` di `.env` sudah benar.
