#!/bin/sh
set -eu
test "$(id -u)" = 0
cd /opt/trading-collector
python3 -m unittest test_collector -v
if ! id trading-collector >/dev/null 2>&1; then
    useradd --system --home-dir /var/lib/trading-collector --shell /usr/sbin/nologin trading-collector
fi
install -d -o root -g trading-collector -m 0750 /etc/trading-collector
install -d -o trading-collector -g trading-collector -m 0700 /var/lib/trading-collector
chown root:root collector.py set_credentials.py trading-collector.service test_collector.py
chmod 0644 collector.py set_credentials.py trading-collector.service test_collector.py
systemd-analyze verify /opt/trading-collector/trading-collector.service
install -o root -g root -m 0644 trading-collector.service /etc/systemd/system/trading-collector.service
systemctl daemon-reload
systemctl enable trading-collector.service
printf '%s\n' 'Installed and boot-enabled; credentials and activation remain separate.'
