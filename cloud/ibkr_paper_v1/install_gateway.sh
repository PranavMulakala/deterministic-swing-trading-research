#!/bin/bash
set -euo pipefail
bash /opt/ibkr-paper-v1/cloud/ibkr_paper_v1/install_api_firewall.sh
# Run as root on the existing personal trading server. No passwords are supplied.
getent passwd ibkr-paper >/dev/null || useradd --system --home-dir /var/lib/ibkr-paper --shell /usr/sbin/nologin ibkr-paper
install -d -o ibkr-paper -g ibkr-paper -m 0700 /var/lib/ibkr-paper
install -d -o ibkr-paper -g ibkr-paper -m 0750 /opt/ibkr-paper-v1/gateway
if [ ! -x /opt/ibkr-paper-v1/gateway/ibgateway ]; then
    runuser -u ibkr-paper -- sh /opt/ibkr-paper-v1/ibgateway-installer.sh -q -dir /opt/ibkr-paper-v1/gateway
fi
python3 - <<'PY'
from pathlib import Path
p=Path('/opt/ibkr-paper-v1/gateway/ibgateway.vmoptions')
if p.exists():
    lines=[x for x in p.read_text().splitlines() if not x.startswith('-Xmx')]
    p.write_text('\n'.join(lines+['-Xmx512m'])+'\n')
PY
if [ ! -f /var/lib/ibkr-paper/.Xauthority ]; then
    touch /var/lib/ibkr-paper/.Xauthority
    xauth -f /var/lib/ibkr-paper/.Xauthority add :91 . "$(mcookie)"
    chown ibkr-paper:ibkr-paper /var/lib/ibkr-paper/.Xauthority
    chmod 0600 /var/lib/ibkr-paper/.Xauthority
fi
cat > /etc/systemd/system/ibkr-paper-display.service <<'EOF'
[Unit]
Description=Private display for paper IB Gateway
[Service]
User=ibkr-paper
Group=ibkr-paper
ExecStart=/usr/bin/Xvfb :91 -screen 0 1280x800x24 -nolisten tcp -auth /var/lib/ibkr-paper/.Xauthority
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/ibkr-paper /tmp
ProtectHome=true
MemoryMax=128M
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/ibkr-paper-gateway.service <<'EOF'
[Unit]
Description=Official IB Gateway (paper login required)
Requires=ibkr-paper-display.service ibkr-paper-window-manager.service
After=ibkr-paper-display.service ibkr-paper-window-manager.service network-online.target
Wants=network-online.target
[Service]
User=ibkr-paper
Group=ibkr-paper
Environment=DISPLAY=:91
Environment=XAUTHORITY=/var/lib/ibkr-paper/.Xauthority
Environment=HOME=/var/lib/ibkr-paper
WorkingDirectory=/var/lib/ibkr-paper
# The Gateway's daily auto-restart starts a fresh copy and then exits. Keep the unit alive while any Gateway
# java process runs, so systemd does not kill that fresh copy along with the old main process.
ExecStart=/bin/sh -c '/opt/ibkr-paper-v1/gateway/ibgateway; sleep 15; while pgrep -u ibkr-paper -x java >/dev/null; do sleep 10; done'
Restart=always
RestartSec=30
TimeoutStopSec=30
KillMode=control-group
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/ibkr-paper /opt/ibkr-paper-v1/gateway /tmp
ProtectHome=true
MemoryMax=850M
CPUQuota=100%
TasksMax=256
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/ibkr-paper-window-manager.service <<'EOF'
[Unit]
Description=Window manager for private Gateway console
Requires=ibkr-paper-display.service
After=ibkr-paper-display.service
[Service]
User=ibkr-paper
Group=ibkr-paper
Environment=DISPLAY=:91
Environment=XAUTHORITY=/var/lib/ibkr-paper/.Xauthority
Environment=HOME=/var/lib/ibkr-paper
ExecStart=/usr/bin/openbox
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/ibkr-paper /tmp
ProtectHome=true
MemoryMax=128M
EOF
cat > /etc/systemd/system/ibkr-paper-console.service <<'EOF'
[Unit]
Description=Loopback-only console for paper Gateway login through SSH
Requires=ibkr-paper-display.service
After=ibkr-paper-display.service
[Service]
User=ibkr-paper
Group=ibkr-paper
ExecStart=/usr/bin/x11vnc -display :91 -auth /var/lib/ibkr-paper/.Xauthority -localhost -rfbport 5901 -forever -shared -nopw -noxdamage
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
MemoryMax=128M
EOF
cat > /etc/systemd/system/ibkr-paper-console-web.service <<'EOF'
[Unit]
Description=Loopback-only web console, accessed only through owner SSH tunnel
Requires=ibkr-paper-console.service
After=ibkr-paper-console.service
[Service]
User=ibkr-paper
Group=ibkr-paper
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 127.0.0.1:6081 127.0.0.1:5901
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
MemoryMax=128M
EOF
systemctl daemon-reload
systemctl enable --now ibkr-paper-display.service ibkr-paper-gateway.service
systemctl start ibkr-paper-console-web.service
systemctl is-active ibkr-paper-display.service ibkr-paper-gateway.service ibkr-paper-console-web.service
echo 'Gateway installed; user must select Paper Trading and authenticate. No orders configured.'
