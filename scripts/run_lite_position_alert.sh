#!/bin/zsh
# Price-only email alerts for the real LITE position. Cannot trade.
set -eu
script_directory=${0:A:h}
repository_root=${script_directory:h}
cd "${repository_root}"
exec /usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${repository_root}/src:${repository_root}" \
  "${repository_root}/.venv/bin/python" -m research.real_position_alert_v1.monitor
