#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Run as root: bash install.sh"; exit 1; }
APP="/opt/evil-vps-bot"; ENV_DIR="/etc/evil-vps-bot"
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
. /etc/os-release
case "$ID" in ubuntu|debian) ;; *) echo "Ubuntu/Debian required."; exit 1 ;; esac
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip snapd ca-certificates
if ! command -v lxc >/dev/null 2>&1; then snap install lxd; fi
for _ in $(seq 1 30); do command -v lxc >/dev/null 2>&1 && break; sleep 2; done
command -v lxc >/dev/null 2>&1 || { echo "LXD CLI unavailable."; exit 1; }
if ! lxc info >/dev/null 2>&1; then lxd init --auto; fi
lxc storage list --format csv | grep -q . || { echo "No LXD storage pool. Configure LXD and rerun."; exit 1; }
install -d -m 0755 "$APP"
install -m 0644 "$HERE/bot.py" "$APP/bot.py"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip
"$APP/venv/bin/pip" install -r "$HERE/requirements.txt"
echo "=== SHADOW VPS V2 setup ==="
read -r -s -p "Discord bot token: " DISCORD_TOKEN; echo
read -r -p "Main admin Discord ID(s), comma-separated: " MAIN_ADMIN_ID
read -r -p "This host's public IPv4: " PUBLIC_IP
read -r -p "LXD storage pool [default]: " DEFAULT_STORAGE_POOL
if [[ -z "$DEFAULT_STORAGE_POOL" ]]; then DEFAULT_STORAGE_POOL="default"; fi
[[ -n "$DISCORD_TOKEN" && -n "$MAIN_ADMIN_ID" && -n "$PUBLIC_IP" ]] || { echo "All three values are required."; exit 1; }
[[ "$MAIN_ADMIN_ID" =~ ^[0-9]+(,[0-9]+)*$ ]] || { echo "Admin IDs must be numeric."; exit 1; }
[[ "$PUBLIC_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || { echo "Enter a valid IPv4 address."; exit 1; }
install -d -m 0750 "$ENV_DIR"
umask 077
cat > "$ENV_DIR/bot.env" <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN
MAIN_ADMIN_ID=$MAIN_ADMIN_ID
BOT_NAME=SHADOW VPS
PREFIX=.
PUBLIC_IP=$PUBLIC_IP
DEFAULT_OS_IMAGE=ubuntu:22.04
DEFAULT_STORAGE_POOL=$DEFAULT_STORAGE_POOL
DATABASE_PATH=$APP/vps-v2.db
PYTHONUNBUFFERED=1
EOF
chmod 0600 "$ENV_DIR/bot.env"
unset DISCORD_TOKEN
cat > /etc/systemd/system/bot.service <<'EOF'
[Unit]
Description=SHADOW VPS Deploy Bot V2
Wants=network-online.target snapd.service
After=network-online.target snapd.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/evil-vps-bot
EnvironmentFile=/etc/evil-vps-bot/bot.env
ExecStart=/opt/evil-vps-bot/venv/bin/python /opt/evil-vps-bot/bot.py
Restart=on-failure
RestartSec=8
TimeoutStopSec=30
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now bot.service
systemctl --no-pager --full status bot.service || true
echo "Logs: journalctl -u bot -f"
echo "Give the bot Manage Server permission and enable Server Members + Message Content intents."
echo "Allow TCP 22000-49999 in your provider firewall for SSH access."
