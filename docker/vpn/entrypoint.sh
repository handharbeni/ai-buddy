#!/bin/sh
# VPN container entrypoint — OpenVPN client.
# Expects:
#   /vpn/config.ovpn    — OpenVPN config file
#   /vpn/auth.txt       — credentials (username on line 1, password on line 2)
#   VPN_SUBNETS         — env var, comma-separated CIDRs to route through VPN
#                          (e.g. "10.11.0.0/16,192.168.100.0/24")
#                          Empty = route ALL traffic through VPN.
set -e

echo "[vpn] Starting OpenVPN client..."

# Defaults
# Defaults — supports both VPN_SUBNETS (single) and SINGLE_VPN_SUBNETS (compose)
VPN_SUBNETS="${VPN_SUBNETS:-${SINGLE_VPN_SUBNETS:-10.11.0.0/16}}"

# Required for /dev/net/tun
mkdir -p /dev/net
[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200
chmod 600 /dev/net/tun

# Validate config
if [ ! -f /vpn/config.ovpn ]; then
  echo "[vpn] ERROR: /vpn/config.ovpn not found"
  echo "[vpn] Mount your .ovpn file at /vpn/config.ovpn"
  exit 1
fi
if [ ! -f /vpn/auth.txt ]; then
  echo "[vpn] ERROR: /vpn/auth.txt not found"
  echo "[vpn] Create with: echo 'username\npassword' > auth.txt"
  exit 1
fi

# Wait for tun device
for i in 1 2 3 4 5; do
  if [ -c /dev/net/tun ]; then break; fi
  sleep 1
done

# Start OpenVPN in background
openvpn \
  --config /vpn/config.ovpn \
  --auth-user-pass /vpn/auth.txt \
  --dev tun \
  --auth-nocache \
  --pull-filter ignore "route-ipv6" 2>/dev/null || true \
  --daemon \
  --log-append /var/log/openvpn.log \
  --writepid /var/run/openvpn.pid

# Wait for tunnel to come up
echo "[vpn] Waiting for tunnel..."
for i in $(seq 1 30); do
  if ip route | grep -q "^10\." 2>/dev/null; then
    echo "[vpn] Tunnel is up"
    break
  fi
  if [ -f /var/run/openvpn.pid ] && kill -0 $(cat /var/run/openvpn.pid) 2>/dev/null; then
    :
  else
    echo "[vpn] ERROR: openvpn process died"
    cat /var/log/openvpn.log
    exit 1
  fi
  sleep 1
done

# Add routes for required subnets (only if not already default route)
DEFAULT_VIA=$(ip route | grep default | awk '{print $3}' | head -1)
TUN_IF=$(ip route | grep "^10\." | head -1 | grep -oE 'dev \S+' | awk '{print $2}')
if [ -z "$TUN_IF" ]; then
  echo "[vpn] WARNING: No tunnel interface detected. Traffic will NOT route through VPN."
  echo "[vpn] Check /var/log/openvpn.log"
else
  echo "[vpn] Tunnel interface: $TUN_IF"
  # Add routes for each subnet
  for SUBNET in $(echo "$VPN_SUBNETS" | tr ',' ' '); do
    ip route add "$SUBNET" dev "$TUN_IF" 2>/dev/null || \
      echo "[vpn] route $SUBNET already exists or failed"
  done
  echo "[vpn] Active routes through tunnel:"
  ip route | grep "$TUN_IF" || true
fi

# Sanity: try to ping Oracle
echo "[vpn] Testing connectivity to Oracle 10.11.0.252:1521..."
timeout 5 bash -c "cat < /dev/tcp/10.11.0.252/1521" 2>&1 | head -1 || true

# Stay alive — if openvpn dies, the container dies
echo "[vpn] VPN tunnel is running. Container will stay alive."
wait
