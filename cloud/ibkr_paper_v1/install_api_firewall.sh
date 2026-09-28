#!/bin/bash
set -euo pipefail
# Only the new Gateway paper socket is restricted. Preserve all other rules.
install -d -m 0755 /etc/ibkr-paper-firewall
cat > /etc/ibkr-paper-firewall/api.nft <<'EOF'
add table inet ibkr_paper_api_private
add chain inet ibkr_paper_api_private input { type filter hook input priority -10; policy accept; }
add rule inet ibkr_paper_api_private input iifname != "lo" tcp dport 4002 drop
EOF
cat > /etc/systemd/system/ibkr-paper-api-firewall.service <<'EOF'
[Unit]
Description=Restrict the paper Gateway API to this server
Before=ibkr-paper-gateway.service
[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/sbin/nft list table inet ibkr_paper_api_private >/dev/null 2>&1 || /usr/sbin/nft -f /etc/ibkr-paper-firewall/api.nft'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
install -d -m 0755 /etc/systemd/system/ibkr-paper-gateway.service.d
cat > /etc/systemd/system/ibkr-paper-gateway.service.d/api-firewall.conf <<'EOF'
[Unit]
Requires=ibkr-paper-api-firewall.service
After=ibkr-paper-api-firewall.service
EOF
systemctl daemon-reload
systemctl enable --now ibkr-paper-api-firewall.service
nft list table inet ibkr_paper_api_private
