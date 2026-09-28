#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -c 'from pathlib import Path; from dashboard.server import verify_host; verify_host(Path("dashboard/state/known_hosts"))'
print 'Open http://127.0.0.1:8766 in your browser. Leave this terminal open.'
exec ssh -F /dev/null -i "$HOME/.ssh/personal_trading_cloud" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=dashboard/state/known_hosts -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 127.0.0.1:8766:127.0.0.1:8766 root@198.211.113.234
