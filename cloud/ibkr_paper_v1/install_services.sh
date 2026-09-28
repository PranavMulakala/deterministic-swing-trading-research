#!/bin/bash
set -euo pipefail
cd /opt/ibkr-paper-v1
python3 -m venv venv
venv/bin/pip install --disable-pip-version-check --quiet protobuf==5.29.5 ./vendor/pythonclient
venv/bin/python -m unittest discover -s tests/ibkr_paper_v1 -v
install -d -m 0750 -o root -g ibkr-paper /etc/ibkr-paper
cat > /etc/systemd/system/ibkr-paper-calendar.service <<'EOF'
[Unit]
Description=Mirror verified public calendar for isolated paper research
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/ibkr-paper-v1/cloud/ibkr_paper_v1/mirror_calendar.py
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ibkr-paper/references
InaccessiblePaths=/etc/trading-collector
PrivateNetwork=true
EOF
cat > /etc/systemd/system/ibkr-paper-calendar.timer <<'EOF'
[Unit]
Description=Refresh paper calendar mirror
[Timer]
OnBootSec=30
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/ibkr-paper-collector.service <<'EOF'
[Unit]
Description=MNQ paper-only continuous data collection (orders denied)
After=ibkr-paper-gateway.service ibkr-paper-calendar.service
Wants=ibkr-paper-calendar.service
[Service]
User=ibkr-paper
Group=ibkr-paper
WorkingDirectory=/opt/ibkr-paper-v1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/ibkr-paper-v1/venv/bin/python -m cloud.ibkr_paper_v1.collector --account DUT109401 --references /var/lib/ibkr-paper/references
Restart=on-failure
RestartSec=30
TimeoutStopSec=30
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ibkr-paper
InaccessiblePaths=/etc/trading-collector /etc/ibkr-paper
IPAddressDeny=any
IPAddressAllow=localhost
MemoryMax=256M
CPUQuota=50%
TasksMax=32
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/ibkr-paper-reports.service <<'EOF'
[Unit]
Description=Pre/post session email and missing-feed alerts
After=network-online.target
[Service]
Type=oneshot
User=ibkr-paper
Group=ibkr-paper
WorkingDirectory=/opt/ibkr-paper-v1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/ibkr-paper-v1/venv/bin/python -m cloud.ibkr_paper_v1.operations --references /var/lib/ibkr-paper/references
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ibkr-paper
ReadOnlyPaths=/etc/ibkr-paper
InaccessiblePaths=/etc/trading-collector
MemoryMax=128M
TimeoutStartSec=90
EOF
cat > /etc/systemd/system/ibkr-paper-reports.timer <<'EOF'
[Unit]
Description=Check session-aware email schedule every minute
[Timer]
OnBootSec=45
OnUnitActiveSec=60
AccuracySec=1
[Install]
WantedBy=timers.target
EOF
install -d -m 0755 /var/lib/ibkr-paper/references
systemctl daemon-reload
systemctl start ibkr-paper-calendar.service
systemctl enable --now ibkr-paper-calendar.timer ibkr-paper-collector.service ibkr-paper-reports.timer
systemctl start ibkr-paper-reports.service
bash /opt/ibkr-paper-v1/cloud/ibkr_paper_v1/install_analysis_service.sh
systemctl is-active ibkr-paper-collector.service ibkr-paper-reports.timer
echo 'Paper observation services installed. Strategy/orders remain gated; SMTP delivery awaits credentials.'
