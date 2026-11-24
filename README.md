# SHADOW VPS Deploy Bot V2

Invite-reward VPS provisioning bot built with discord.py, SQLite and LXD.

## Reward tiers

| Invites | RAM | vCore | NVMe |
|---:|---:|---:|---:|
| 2 | 1 GB | 1 | 5 GB |
| 4 | 2 GB | 1 | 5 GB |
| 6 | 4 GB | 1 | 10 GB |
| 8 | 6 GB | 1 | 15 GB |
| 10 | 8 GB | 2 | 20 GB |
| 14 | 12 GB | 3 | 25 GB |
| 18 | 16 GB | 3 | 30 GB |
| 22 | 20 GB | 4 | 35 GB |
| 26 | 24 GB | 4 | 40 GB |
| 32 | 32 GB | 6 | 45 GB |

## Commands
- .claim — reward selector.
- .invites / .invs — active referrals, available credits and used credits.
- .myvps — your VPS instances.
- .ping and .help.
- Admins: .syncinvites and .vpslist.

## Invite tracking
Enable Server Members Intent and Message Content Intent in the Discord Developer Portal. Give the bot Manage Server permission to read invite usage. Only uniquely attributed human members count. Self-invites and bots do not count. A referred member leaving makes an unused credit unavailable. Consumed credits are not refunded. Existing members are not credited retroactively. Vanity/unknown invite joins cannot be attributed.

## Claim safety
Claims are serialized. The bot checks invite credits and host headroom, provisions the LXD container, then consumes credits only after successful deployment. Provisioning failure does not deduct credits. Capacity checks reserve RAM, disk and CPU. Each VPS receives a generated root password and an SSH proxy port.

## Requirements
- Ubuntu/Debian with root access and outbound HTTPS.
- LXD initialized with a storage pool.
- Public IPv4 and provider firewall access.
- Discord bot token and numeric admin Discord ID(s).

## Install on a clean host

\`\`\`bash
git clone -b v2-rebuild https://github.com/shadowboss092-design/vps-deploy-bot-v1.git
cd vps-deploy-bot-v1
chmod +x install.sh
./install.sh
\`\`\`

Installer asks for bot token, admin IDs, public IPv4 and LXD storage pool. Secrets are stored in /etc/evil-vps-bot/bot.env with mode 0600.

## Service

\`\`\`bash
systemctl status bot
journalctl -u bot -f
systemctl restart bot
\`\`\`

The bot runs as root to manage LXD. Restrict host access and never publish the token. Do not expose the LXD API publicly. Open TCP 22000-49999 in the provider firewall for SSH proxy connections. Installer does not delete existing containers or storage pools.
