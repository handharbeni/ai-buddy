# Deployment Guide: AlmaLinux

Panduan ini berisi langkah-langkah untuk deploy *Local AI Data Intelligence Platform* di server AlmaLinux, menggunakan Docker Compose dan LLM lokal (Ollama).

## 0. Persyaratan Minimum

-   **OS**: AlmaLinux 9+
-   **Hardware**: RAM ≥ 8 GB (untuk model 3B + RAG embedding), disk ≥ 30 GB
-   **Koneksi**: Internet (sekadar untuk pull image/model; inferensi 100% lokal)

## 1. Instal Docker & Docker Compose

```bash
sudo dnf install -y yum-utils git curl
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Logout dan login kembali agar perubahan grup $USER aktif
```
Verifikasi instalasi:
```bash
docker compose version
```

## 2. Clone Repository & Konfigurasi Awal

```bash
git clone <URL_REPO> /opt/DBI-DB && cd /opt/DBI-DB
cp .env.example .env
```

Edit file `.env` dengan kredensial dan konfigurasi server Anda. Pastikan untuk mengubah nilai-nilai berikut:

```bash
# --- Branding (opsional, sesuaikan dengan nama proyek Anda) ---
APP_NAME="Nama Proyek Anda"
APP_SHORT_NAME="Singkatan"
APP_TAGLINE="Platform AI Lokal untuk Intelijen Data"
APP_INSTITUTION="Nama Institusi Anda"
APP_DOMAIN="domain_data"

# --- LLM Lokal ---
LLM_BACKEND=ollama
LLM_BASE_URL=http://ollama:11434        # Gunakan hostname "ollama" dalam jaringan Docker Compose
LLM_MODEL=bapenda-ai:latest             # atau nama model Ollama yang sudah ditarik (misal: qwen2.5:3b-instruct)
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=120

# --- Otentikasi ---
JWT_SECRET=$(openssl rand -hex 32)      # Ganti dengan string acak yang kuat
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MIN=15

# --- RAG / Qdrant ---
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=regulations
EMBEDDING_MODEL=BAAI/bge-m3

# --- Server & Jaringan ---
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://<IP_SERVER_ALMALINUX>:3000","http://127.0.0.1:3000"] # Sesuaikan dengan IP server
FRONTEND_PORT=3000
QDRANT_PORT=6333
OLLAMA_PORT=11434
NEXT_PUBLIC_API_URL=http://<IP_SERVER_ALMALINUX>:8000 # Sesuaikan dengan IP server

# --- Database Mock (0 = pakai DB nyata, 1 = pakai Mock DB) ---
USE_MOCK_DB=0
```

## 3. Konfigurasi Database Nyata (Opsional)

Jika menggunakan database nyata (Oracle, PostgreSQL, MySQL), tambahkan konfigurasi ke `.env` sesuai dengan `SETUP_INSTRUCTIONS.md`.

### Contoh Oracle
```bash
# .env
ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PORT=1521
ORACLE_BATAMAI_SERVICE=simpbb
ORACLE_BATAMAI_USER=ai_readonly
ORACLE_BATAMAI_PASSWORD=your_r...word
ORACLE_BATAMAI_READONLY=true
```
**Perhatian**: Pastikan user database hanya memiliki hak akses `READ ONLY`.

## 4. Konfigurasi VPN (Opsional, untuk DB di jaringan terpisah)

Jika database Anda berada di jaringan privat dan perlu diakses melalui VPN, ikuti langkah-langkah berikut. Backend akan terhubung ke VPN container untuk merutekan lalu lintas DB.

### 4.1. Siapkan File VPN

Tempatkan file `.ovpn` dan kredensial di direktori `docker/vpn/`:

-   **File Konfigurasi OpenVPN**:
    -   Untuk **Single VPN**: `docker/vpn/config.ovpn`
    -   Untuk **Multi-VPN**: `docker/vpn/<nama_db>.ovpn` (misal: `oracle.ovpn`, `mysql.ovpn`)
-   **File Kredensial VPN**:
    -   Untuk **Single VPN**: Buat `docker/vpn/auth.txt` berisi 2 baris (`username_vpn` ENTER `password_vpn`). Beri hak akses `chmod 600 docker/vpn/auth.txt`.
    -   Untuk **Multi-VPN**: Buat `docker/vpn/auth_<nama_db>.txt` (misal: `auth_oracle.txt`, `auth_mysql.txt`). Jika `auth_<nama_db>.txt` tidak ditemukan, akan fallback ke `auth.txt`.

### 4.2. Konfigurasi `.env` untuk VPN

#### Opsi A: Single VPN (satu file `.ovpn` untuk semua DB di jaringan terpisah)

```bash
# .env
SINGLE_VPN_SUBNETS=10.11.0.0/16,192.168.1.0/24 # CIDR jaringan DB, pisahkan koma
# Atau kosongkan untuk merutekan semua traffic keluar container vpn
# SINGLE_VPN_SUBNETS=
```

#### Opsi B: Multi-VPN (setiap DB dengan VPN tunnel terpisah)

```bash
# .env
ORACLE_SUBNETS=10.11.0.0/16       # Subnet yang dirutekan via docker/vpn/oracle.ovpn
MYSQL_SUBNETS=192.168.50.0/24     # Subnet yang dirutekan via docker/vpn/mysql.ovpn
POSTGRES_SUBNETS=172.16.0.0/12    # Subnet yang dirutekan via docker/vpn/postgres.ovpn
```
Setiap entri `*_SUBNETS` harus sesuai dengan nama file `.ovpn` di `docker/vpn/` (misal: `ORACLE_SUBNETS` untuk `oracle.ovpn`).

## 5. Build & Start Service

Masuk ke direktori `/opt/DBI-DB`.

#### Tanpa VPN (akses DB langsung)
```bash
docker compose up -d --build
```

#### Dengan Single VPN
```bash
docker compose --profile vpn up -d --build
```
Backend akan menggunakan `network_mode: "service:vpn"` untuk merutekan lalu lintas DB melalui container VPN.

#### Dengan Multi-VPN
```bash
docker compose --profile vpn-multi up -d --build
```
Backend akan menggunakan `network_mode: "service:vpn-multi"` untuk merutekan lalu lintas DB melalui container Multi-VPN.

## 6. Setup Model LLM Lokal (Ollama)

Sistem menggunakan model kustom `bapenda-ai:latest` yang berbasis `qwen2.5:3b-instruct`.
Jalankan perintah berikut di server AlmaLinux:

```bash
# Tarik base model
docker exec localai-ollama ollama pull qwen2.5:3b-instruct

# Buat model kustom dari Modelfile.bapenda
docker exec -i localai-ollama ollama create bapenda-ai -f - < Modelfile.bapenda

# Verifikasi model sudah ada
docker exec localai-ollama ollama list
curl -s localhost:11434/api/tags
```
Jika Anda tidak ingin menggunakan model kustom, ganti `LLM_MODEL` di `.env` menjadi `qwen2.5:3b-instruct`.

## 7. Verifikasi

### 7.1. Cek Kesehatan Service
```bash
curl http://localhost:8000/health              # Output: {"status":"healthy", "service":"LocalAI"}
curl http://localhost:8000/                    # Output: Branding info
```

### 7.2. Cek Log Backend (DB dan LLM)
```bash
docker compose logs backend | grep -i "adapter\|mock\|LLM:"
```
Jika konfigurasi DB nyata berhasil, Anda akan melihat pesan seperti `Oracle adapter: batamai (10.11.0.252)`. Jika gagal, akan muncul `using mock`.

### 7.3. Akses Frontend
Buka browser dan navigasi ke `http://<IP_SERVER_ALMALINUX>:3000`.
Login dengan user default (jika `DEV_MODE=true` di `.env`):
-   `admin/admin123`
-   `supervisor/super123`
-   `analyst/analyst123`
-   `staff/staff123`

### 7.4. Verifikasi Koneksi Database (via API)
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

### 7.5. Verifikasi VPN Aktif (jika menggunakan VPN)
```bash
# Untuk Single VPN
docker compose exec vpn ip link show | grep tun

# Untuk Multi-VPN
docker compose exec vpn-multi ip link show tun10 2>/dev/null || exit 0 # Cek tun10, tun11, dst.
```
Untuk menguji jangkauan ke host DB di jaringan VPN:
```bash
docker compose exec backend-vpn sh -c "cat < /dev/tcp/10.11.0.252/1521" # Ganti IP/Port DB Anda
```
Jika tidak ada error, koneksi berhasil.

## 8. RAG (Opsional, untuk ingest dan pencarian regulasi/dokumen)

Untuk mengaktifkan RAG service (Qdrant + embedding model):

```bash
docker compose --profile rag up -d --build
```
**Catatan**: Embedding model `BAAI/bge-m3` (~2 GB) akan di-download secara otomatis ke volume `rag_models` saat pertama kali service RAG dijalankan. Proses ini bisa memakan waktu, terutama di CPU-only.
Setelah RAG service aktif, Anda perlu meng-ingest dokumen melalui `backend/app/rag/ingest_cli.py`.

## 9. Firewall & Produksi Hardening (Wajib)

### 9.1. Konfigurasi Firewall
Buka port 3000 (frontend) dan 8000 (backend API) di firewall AlmaLinux. Port lainnya (Qdrant, Ollama) sebaiknya tidak di-expose ke publik.

```bash
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 9.2. Hardening Produksi
1.  **Nonaktifkan `DEV_MODE`**: Di `.env`, set `DEV_MODE=false`. Ini menonaktifkan user development hardcoded.
2.  **Ganti Kredensial Default**: Pastikan `JWT_SECRET` adalah string acak yang kuat (sudah di Langkah 2).
3.  **Manajemen User**: Buat user nyata melalui API `/api/v1/users`.
4.  **Keamanan Jaringan**: Idealnya, expose hanya port 3000 melalui reverse proxy (Nginx/Caddy) dengan TLS/SSL. Port 8000 (backend) dan lainnya dapat dibatasi aksesnya hanya dari localhost atau jaringan internal.
5.  **Akses Database**: Selalu gunakan akun database dengan hak akses `READ ONLY` untuk platform ini.

## 10. Opsi GPU (Jika Server Memiliki NVIDIA GPU)

Untuk memanfaatkan GPU NVIDIA di Ollama dan vLLM (jika digunakan), pastikan driver NVIDIA dan `nvidia-container-toolkit` sudah terinstal di AlmaLinux. Kemudian, tambahkan konfigurasi `deploy` ke service `ollama` (dan `backend` jika menggunakan vLLM) di `docker-compose.yml`:

```yaml
services:
  ollama:
    # ... konfigurasi lainnya
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```
Tanpa GPU, model 3B masih berjalan di CPU dengan kecepatan sekitar 5-10 token/detik.

---

## Troubleshooting Cepat

-   **Backend shows "mock" for all databases**:
    -   Pastikan `USE_MOCK_DB=0` di `.env`.
    -   Periksa kredensial DB (host, port, user, password) di `.env` sudah terisi dengan benar.
    -   Cek log `docker compose logs backend` untuk error koneksi DB spesifik.
-   **Connection timeout ke Database**:
    -   Jika pakai VPN, pastikan container VPN aktif dan tunnel terbentuk (`docker compose logs vpn` atau `vpn-multi`).
    -   Verifikasi `*_SUBNETS` di `.env` sesuai dengan rentang IP host DB.
    -   Periksa firewall server DB atau jaringan intermediate.
-   **Frontend kosong / CORS error**:
    -   Pastikan `NEXT_PUBLIC_API_URL` di `.env` menggunakan IP atau hostname server yang benar (bukan `localhost`).
    -   Tambahkan `http://<IP_SERVER_ALMALINUX>:3000` ke `CORS_ORIGINS` di `.env`.
-   **LLM request timeout**:
    -   Tingkatkan nilai `LLM_TIMEOUT` di `.env` (misal: 180 atau 300 detik), terutama jika berjalan di CPU.
    -   Pastikan Ollama service sehat (`docker compose logs ollama`).
-   **Password dengan karakter spesial di `.env`**:
    -   URL-encode karakter spesial seperti `@`, `#`, `!` jika password DB mengandung karakter tersebut. Contoh: `p%40ssw0rd%21` untuk `p@ssword!`.
