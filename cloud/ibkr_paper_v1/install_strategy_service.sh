#!/bin/bash
set -euo pipefail
test -s /etc/ibkr-paper/execution-qualification.json
cat > /etc/systemd/system/ibkr-paper-strategy.service <<'EOF'
[Unit]
Description=Guarded one-contract MNQ paper strategy supervisor
After=ibkr-paper-gateway.service ibkr-paper-collector.service
Wants=ibkr-paper-gateway.service ibkr-paper-collector.service
[Service]
Type=simple
User=ibkr-paper
Group=ibkr-paper
WorkingDirectory=/opt/ibkr-paper-v1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/ibkr-paper-v1/venv/bin/python -m cloud.ibkr_paper_v1.strategy_runtime
Restart=on-failure
RestartSec=15
TimeoutStopSec=90
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ibkr-paper
ReadOnlyPaths=/etc/ibkr-paper/execution-qualification.json
InaccessiblePaths=/etc/trading-collector /etc/ibkr-paper/smtp.json
IPAddressDeny=any
IPAddressAllow=localhost
MemoryMax=384M
CPUQuota=40%
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ibkr-paper-strategy.service
systemctl is-active ibkr-paper-strategy.service
