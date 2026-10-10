#!/usr/bin/env bash
set -Eeuo pipefail

# Evil VPS V1 bot installer (safe to rerun; does not delete existing containers)
if [[ $EUID -ne 0 ]]; then
  echo "Run as root: bash install.sh"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BOT_SOURCE="$SCRIPT_DIR/bot.py"
[[ -f "$BOT_SOURCE" ]] || { echo "ERROR: bot.py must be in the same folder as install.sh"; exit 1; }

echo "=== Evil VPS V1 Bot Installer ==="
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) echo "Supported OS: Ubuntu or Debian"; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip ca-certificates curl snapd

# Install LXD only if the LXD CLI is not already available.
if ! command -v lxc >/dev/null 2>&1; then
  echo "Installing LXD via snap..."
  snap install lxd
fi

# Wait briefly for snap-installed LXD CLI to become available.
for _ in $(seq 1 20); do
  command -v lxc >/dev/null 2>&1 && break
  sleep 2
done
command -v lxc >/dev/null 2>&1 || { echo "ERROR: lxc command not found after installation"; exit 1; }

# Initialize only if LXD is not already responding; never reset/reconfigure an existing instance.
if ! lxc info >/dev/null 2>&1; then
  echo "LXD is not initialized/responding. Running 'lxd init --auto'..."
  if command -v lxd >/dev/null 2>&1; then
    lxd init --auto
  else
    echo "ERROR: lxd command not found. Check the snap installation."
    exit 1
  fi
else
  echo "Existing LXD detected; keeping current configuration."
fi

if ! lxc storage list --format csv 2>/dev/null | grep -q .; then
  echo "ERROR: LXD has no storage pool. Run 'lxd init' and create a storage pool, then rerun installer."
  exit 1
fi

# Keep the existing configured pool name when possible; bot detects it automatically.
install -d -m 0755 /opt/evil-vps-bot
install -m 0644 "$BOT_SOURCE" /opt/evil-vps-bot/bot.py
python3 -m venv /opt/evil-vps-bot/venv
/opt/evil-vps-bot/venv/bin/python -m pip install --upgrade pip
/opt/evil-vps-bot/venv/bin/python -m pip install --upgrade discord.py requests

read -r -s -p "Discord bot token: " DISCORD_TOKEN
echo
read -r -p "Main admin Discord ID: " MAIN_ADMIN_ID
if [[ -z "$DISCORD_TOKEN" || -z "$MAIN_ADMIN_ID" ]]; then
  echo "ERROR: token and admin ID cannot be empty"
  exit 1
fi
if ! [[ "$MAIN_ADMIN_ID" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
  echo "ERROR: Admin ID must be numeric (multiple IDs may be comma-separated)"
  exit 1
fi

# Store credentials in a root-readable environment file rather than in the unit.
install -d -m 0750 /etc/evil-vps-bot
umask 077
cat > /etc/evil-vps-bot/bot.env <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN
MAIN_ADMIN_ID=$MAIN_ADMIN_ID
BOT_NAME=Svm-v9
PREFIX=.
PYTHONUNBUFFERED=1
EOF
chmod 0600 /etc/evil-vps-bot/bot.env
unset DISCORD_TOKEN

cat > /etc/systemd/system/bot.service <<'EOF'
[Unit]
Description=Evil VPS Discord Bot
Wants=network-online.target
After=network-online.target snapd.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/evil-vps-bot
EnvironmentFile=/etc/evil-vps-bot/bot.env
ExecStart=/opt/evil-vps-bot/venv/bin/python /opt/evil-vps-bot/bot.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now bot.service
sleep 2
echo
systemctl --no-pager --full status bot.service || true
echo
echo "Install complete."
echo "Logs:   journalctl -u bot -n 100 --no-pager"
echo "Follow: journalctl -u bot -f"
echo "Restart: systemctl restart bot"
echo "LXC list: lxc list"
