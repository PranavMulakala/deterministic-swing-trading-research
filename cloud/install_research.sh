#!/bin/sh
set -eu
test "$(id -u)" = 0
test -f /opt/trading-research-v2-20260909/PINS.json
cd /opt/trading-research-v2-20260909
python3 -c 'from pathlib import Path; from cloud.research_runner import verify_pins; print("Verified research pins:",verify_pins(Path.cwd()))'
for unit in trading-references.service trading-references.timer trading-research.service trading-research.timer; do
    systemd-analyze verify "/opt/trading-collector/$unit"
    install -o root -g root -m 0644 "/opt/trading-collector/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl start trading-references.service
systemctl enable --now trading-references.timer trading-research.timer
systemctl start trading-research.service
systemctl restart trading-collector.service
systemctl show trading-research.service -p Result -p ExecMainStatus
