#!/bin/sh
# Multi-VPN container — one OpenVPN instance per database.
# Reads /vpn/*.ovpn and /vpn/auth_*.txt; routes per-DB subnets through the right tunnel.
# Backend connects via network_mode: "service:backend-vpn" and shares this network stack.
set -e

echo "[vpn-multi] Starting multi-VPN gateway..."

mkdir -p /dev/net
[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200
chmod 600 /dev/net/tun

# Wait for tun
for i in 1 2 3 4 5; do
  [ -c /dev/net/tun ] && break
  sleep 1
done

# Ensure we have iproute2 + iptables
which ip iptables || apk add --no-cache iproute2 iptables

# Discover all .ovpn files in /vpn
OVPN_DIR="/vpn"
TUN_INDEX=10  # tun10, tun11, tun12, ...
declare -A TUN_TO_CONF
declare -A CONF_TO_SUBNETS

if [ -d "$OVPN_DIR" ]; then
  for OVPN in "$OVPN_DIR"/*.ovpn; do
    [ -f "$OVPN" ] || continue
    BASENAME=$(basename "$OVPN" .ovpn)
    TUN="tun${TUN_INDEX}"
    TUN_INDEX=$((TUN_INDEX + 1))
    TUN_TO_CONF["$TUN"]="$BASENAME"
    echo "[vpn-multi] Found: $OVPN → will use $TUN"
  done
else
  echo "[vpn-multi] ERROR: /vpn directory missing"
  exit 1
fi

if [ ${#TUN_TO_CONF[@]} -eq 0 ]; then
  echo "[vpn-multi] No .ovpn files found in $OVPN_DIR"
  echo "[vpn-multi] Drop your .ovpn files in /vpn to enable per-database VPNs"
  echo "[vpn-multi] Container will stay alive but no tunnels will be established."
  exec tail -f /dev/null
fi

# Per-VPN routing table numbering
RT_TABLE_BASE=100
declare -A TUN_TO_TABLE

# Start each OpenVPN instance
i=0
for TUN in "${!TUN_TO_CONF[@]}"; do
  BASENAME="${TUN_TO_CONF[$TUN]}"
  OVPN="$OVPN_DIR/$BASENAME.ovpn"
  AUTH="$OVPN_DIR/auth_$BASENAME.txt"
  FALLBACK_AUTH="$OVPN_DIR/auth.txt"
  TABLE=$((RT_TABLE_BASE + i * 100))
  TUN_TO_TABLE["$TUN"]=$TABLE
  i=$((i + 1))

  # Determine auth file
  if [ -f "$AUTH" ]; then
    AUTH_FILE="$AUTH"
  elif [ -f "$FALLBACK_AUTH" ]; then
    echo "[vpn-multi] WARN: $AUTH not found, using fallback $FALLBACK_AUTH for $BASENAME"
    AUTH_FILE="$FALLBACK_AUTH"
  else
    echo "[vpn-multi] ERROR: no auth file for $BASENAME (expected auth_$BASENAME.txt or auth.txt)"
    continue
  fi

  echo "[vpn-multi] Starting $BASENAME on $TUN (table $TABLE)..."

  # Determine subnet from env: DB_<NAME>_SUBNETS (comma-separated CIDRs)
  # BASENAME=oracle → ORACLE_SUBNETS
  # BASENAME=mysql  → MYSQL_SUBNETS
  # etc.
  DB_NAME=$(echo "$BASENAME" | tr '[:lower:]-' '[:upper:]_')
  SUBNET_VAR="${DB_NAME}_SUBNETS"
  eval "SUBNETS=\${$SUBNET_VAR:-}"

  if [ -n "$SUBNETS" ]; then
    CONF_TO_SUBNETS["$TUN"]="$SUBNETS"
    echo "[vpn-multi]   $BASENAME → $SUBNETS"
  else
    echo "[vpn-multi]   $BASENAME → (no subnets set; tunnel active but unused)"
  fi

  # Launch OpenVPN on specific TUN device
  nohup openvpn \
    --config "$OVPN" \
    --auth-user-pass "$AUTH_FILE" \
    --dev "$TUN" \
    --dev-type tun \
    --auth-nocache \
    --route-up "/etc/openvpn/route-up.sh $TUN $TABLE" \
    --daemon \
    --log-append "/var/log/openvpn-$BASENAME.log" \
    --writepid "/var/run/openvpn-$BASENAME.pid" \
    > /dev/null 2>&1
done

# Write the route-up helper script
cat > /etc/openvpn/route-up.sh <<'ROUTE_EOF'
#!/bin/sh
# Called by OpenVPN when tunnel comes up.
# $1 = tun name, $2 = routing table number
TUN="$1"
TABLE="$2"
GW=$(ip route | grep "dev $TUN" | grep -oE 'via [0-9.]+' | awk '{print $2}' | head -1)
LOCAL=$(ip -4 addr show "$TUN" | grep inet | awk '{print $2}' | head -1)
if [ -n "$LOCAL" ]; then
  ip route add "$LOCAL" dev "$TUN" table "$TABLE" 2>/dev/null || true
  echo "[vpn-multi] $TUN → table $TABLE, route $LOCAL, gateway ${GW:-direct}"
else
  echo "[vpn-multi] WARN: $TUN came up without an IP"
fi
ROUTE_EOF
chmod +x /etc/openvpn/route-up.sh

# Wait for tunnels
echo "[vpn-multi] Waiting for tunnels..."
for i in $(seq 1 30); do
  ACTIVE=0
  for TUN in "${!TUN_TO_CONF[@]}"; do
    if ip -4 addr show "$TUN" 2>/dev/null | grep -q inet; then
      ACTIVE=$((ACTIVE + 1))
    fi
  done
  if [ "$ACTIVE" -eq "${#TUN_TO_CONF[@]}" ]; then
    echo "[vpn-multi] All $ACTIVE tunnels are up"
    break
  fi
  sleep 1
done

# Build iptables + ip rules for per-subnet routing
echo "[vpn-multi] Setting up policy routing..."

# Enable IP forwarding + route-aware packets
echo 1 > /proc/sys/net/ipv4/ip_forward
echo 1 > /proc/sys/net/ipv4/conf/all/route_localnet 2>/dev/null || true

# Clear any existing rules
for TBL in $(seq 100 100 900); do
  ip rule del table $TBL 2>/dev/null || true
done
iptables -t mangle -F 2>/dev/null || true
iptables -t nat    -F 2>/dev/null || true

# Mark packets per destination subnet
MARK_BASE=10
TUN_INDEX=0
for TUN in "${!TUN_TO_CONF[@]}"; do
  BASENAME="${TUN_TO_CONF[$TUN]}"
  TABLE="${TUN_TO_TABLE[$TUN]}"
  MARK=$((MARK_BASE + TUN_INDEX))
  TUN_INDEX=$((TUN_INDEX + 1))

  SUBNETS="${CONF_TO_SUBNETS[$TUN]}"
  if [ -z "$SUBNETS" ]; then
    continue
  fi

  for SUBNET in $(echo "$SUBNETS" | tr ',' ' '); do
    # Mark packets going to this subnet
    iptables -t mangle -A OUTPUT -d "$SUBNET" -j MARK --set-mark "$MARK" 2>/dev/null || true
    # Route marked packets via custom table
    ip rule add fwmark "$MARK" table "$TABLE" priority 100 2>/dev/null || true
    echo "[vpn-multi] $BASENAME ($TUN, mark=$MARK, table=$TABLE) ← $SUBNET"
  done
done

# Default: bypass VPN (go through eth0 normally)
ip rule add priority 1000 table main 2>/dev/null || true

# Sanity check
echo "[vpn-multi] Active routes:"
ip rule show
echo "[vpn-multi] Per-table routes:"
for TBL in $(seq 100 100 900); do
  ROUTES=$(ip route show table $TBL 2>/dev/null)
  if [ -n "$ROUTES" ]; then
    echo "  table $TBL:"
    echo "$ROUTES" | sed 's/^/    /'
  fi
done

# Stay alive
echo "[vpn-multi] Gateway is up. Container staying alive."
exec tail -f /dev/null
