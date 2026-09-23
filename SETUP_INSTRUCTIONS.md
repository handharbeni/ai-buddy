# Setup Instructions — Connecting to Real Database

Step-by-step guide to connect the platform to real databases (with or without VPN).

For full deployment options, see [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Database credentials** — host, port, service/SID, username, password (read-only user)
- [ ] **VPN files** (if DB is on private network) — `.ovpn` config + auth credentials
- [ ] **Network access** — either direct or via VPN tunnel
- [ ] `.env` file created (see step 1)

---

## Step 1: Create `.env`

```bash
cp .env.example .env
```

---

## Step 2: Configure Database

### Option A: Oracle

```bash
# .env
USE_MOCK_DB=0
ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PORT=1521
ORACLE_BATAMAI_SERVICE=simpbb
ORACLE_BATAMAI_USER=ai_readonly
ORACLE_BATAMAI_PASSWORD=your_real_password
ORACLE_BATAMAI_READONLY=true
```

**Database-side grants (DBA must run):**
```sql
CREATE USER ai_readonly IDENTIFIED BY "your_real_password";
GRANT CONNECT TO ai_readonly;
GRANT SELECT ANY DICTIONARY TO ai_readonly;
GRANT SELECT ON schema.view_name TO ai_readonly;
```

### Option B: PostgreSQL

```bash
# .env
USE_MOCK_DB=0
POSTGRES_PRIMARY_HOST=pg.internal.example.com
POSTGRES_PRIMARY_PORT=5432
POSTGRES_PRIMARY_DB=production_db
POSTGRES_PRIMARY_USER=ai_readonly
POSTGRES_PRIMARY_PASSWORD=your_real_password
```

**Database-side grants:**
```sql
CREATE USER ai_readonly WITH PASSWORD 'your_real_password';
GRANT CONNECT ON DATABASE production_db TO ai_readonly;
GRANT USAGE ON SCHEMA public TO ai_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ai_readonly;
```

### Option C: MySQL

```bash
# .env
USE_MOCK_DB=0
MYSQL_PRIMARY_HOST=mysql.internal.example.com
MYSQL_PRIMARY_PORT=3306
MYSQL_PRIMARY_DB=analytics_db
MYSQL_PRIMARY_USER=ai_readonly
MYSQL_PRIMARY_PASSWORD=your_real_password
```

**Database-side grants:**
```sql
CREATE USER 'ai_readonly'@'%' IDENTIFIED BY 'your_real_password';
GRANT SELECT ON analytics_db.* TO 'ai_readonly'@'%';
FLUSH PRIVILEGES;
```

### Multiple Databases

Add more by changing `<NAME>`:
```bash
ORACLE_SECONDARY_HOST=10.11.1.100
ORACLE_SECONDARY_PORT=1521
ORACLE_SECONDARY_SERVICE=orcl
ORACLE_SECONDARY_USER=ai_readonly
ORACLE_SECONDARY_PASSWORD=pass2

POSTGRES_ANALYTICS_HOST=pg-analytics.internal.com
POSTGRES_ANALYTICS_PORT=5432
POSTGRES_ANALYTICS_DB=analytics
POSTGRES_ANALYTICS_USER=reader
POSTGRES_ANALYTICS_PASSWORD=pass3
```

---

## Step 3: Configure VPN (if needed)

Skip if DB is directly reachable from your network.

### Single VPN (one database behind VPN)

```bash
# 1. Place files
cp /path/to/your-config.ovpn docker/vpn/config.ovpn
printf 'vpn_username\nvpn_password' > docker/vpn/auth.txt
chmod 600 docker/vpn/auth.txt

# 2. .env
SINGLE_VPN_SUBNETS=10.11.0.0/16
```

### Multi-VPN (multiple databases, different networks)

```bash
# 1. Place files — one .ovpn per database network
cp /path/to/oracle.ovpn docker/vpn/oracle.ovpn
printf 'oracle_user\noracle_pass' > docker/vpn/auth_oracle.txt

cp /path/to/mysql.ovpn docker/vpn/mysql.ovpn
printf 'mysql_user\nmysql_pass' > docker/vpn/auth_mysql.txt

# 2. .env — map subnets to tunnels
ORACLE_SUBNETS=10.11.0.0/16
MYSQL_SUBNETS=192.168.50.0/24
```

File naming: `<basename>.ovpn` → `auth_<basename>.txt` (fallback: `auth.txt`)

---

## Step 4: Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"

# Paste into .env
JWT_SECRET=<your_generated_secret>
```

---

## Step 5: Start Services

### Without VPN (direct DB access)
```bash
docker compose up -d
```

### With VPN
```bash
# Single VPN
docker compose --profile vpn up -d

# Multi-VPN
docker compose --profile vpn-multi up -d
```

---

## Step 6: Verify Connection

### 6.1 Check backend starts without errors
```bash
docker compose logs backend | grep -i "oracle\|postgresql\|mysql\|mock"
```

Expected (real DB):
```
Oracle adapter: batamai (10.11.0.252)
```

If you see `using mock` — credentials missing or connection failed.

### 6.2 Test health endpoint
```bash
curl http://localhost:8000/health
```

### 6.3 Test database connectivity
```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Query (will use real DB if configured)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 FROM dual"}'
```

### 6.4 Check adapter logs
```bash
docker compose logs backend | grep -E "(adapter|connected|pool|error)"
```

---

## Step 7: VPN Verification (if applicable)

```bash
# Check tunnel is up
docker compose exec backend-vpn ip link show | grep tun

# Test reachability to DB host
docker compose exec backend-vpn sh -c "cat < /dev/tcp/10.11.0.252/1521"
```

---

## Troubleshooting

### Backend shows "mock" for all databases
- Check `USE_MOCK_DB=0` in `.env`
- Check DB credentials are filled (not empty)
- Check logs for adapter errors

### Connection timeout
- VPN tunnel not up — check `docker compose logs vpn`
- Wrong subnet — verify `*_SUBNETS` matches DB host range
- Firewall blocking — verify port is open

### Password with special characters
URL-encode special characters in `.env`:
```bash
POSTGRES_PRIMARY_PASSWORD=p%40ssw0rd%21
```

---

## Full `.env` Example (Oracle + VPN)

```bash
# Branding
APP_NAME=BAPENDA AI Platform
APP_INSTITUTION=BAPENDA Batam
APP_DOMAIN=tax

# LLM
LLM_BACKEND=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=bapenda-ai:latest

# Database
USE_MOCK_DB=0
ORACLE_BATAMAI_HOST=10.11.0.252
ORACLE_BATAMAI_PORT=1521
ORACLE_BATAMAI_SERVICE=simpbb
ORACLE_BATAMAI_USER=ai_readonly
ORACLE_BATAMAI_PASSWORD=your_real_password
ORACLE_BATAMAI_READONLY=true

# Security
JWT_SECRET=<64-char-random-string>

# VPN
SINGLE_VPN_SUBNETS=10.11.0.0/16
```