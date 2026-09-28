#!/bin/bash
set -euo pipefail
install -d -m 0700 -o ibkr-paper -g ibkr-paper /var/lib/ibkr-paper/analysis
cat > /etc/systemd/system/ibkr-paper-analysis.service <<'EOF'
[Unit]
Description=Read-only completed-session MNQ research analysis (no orders)
After=ibkr-paper-calendar.service
[Service]
Type=oneshot
User=ibkr-paper
Group=ibkr-paper
WorkingDirectory=/opt/ibkr-paper-v1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/ibkr-paper-v1/venv/bin/python -m cloud.ibkr_paper_v1.session_analysis
UMask=0077
NoNewPrivileges=true
PrivateNetwork=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ibkr-paper/analysis
InaccessiblePaths=/etc/trading-collector /etc/ibkr-paper
MemoryMax=256M
CPUQuota=35%
TimeoutStartSec=10min
EOF
cat > /etc/systemd/system/ibkr-paper-analysis.timer <<'EOF'
[Unit]
Description=Check for completed MNQ sessions every five minutes
[Timer]
OnBootSec=90
OnUnitActiveSec=5min
AccuracySec=1
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now ibkr-paper-analysis.timer
systemctl start ibkr-paper-analysis.service
systemctl is-active ibkr-paper-analysis.timer
