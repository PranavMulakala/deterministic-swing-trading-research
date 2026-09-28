#!/bin/zsh
# SPY bull put spread paper bot v1 (paper trading only). Rules: research/spy_put_spread_v1/PROTOCOL.md
set -eu
script_directory=${0:A:h}
repository_root=${script_directory:h}
cd "${repository_root}"
exec /usr/bin/caffeinate -i /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${repository_root}/src:${repository_root}" \
  "${repository_root}/.venv/bin/python" -u -m research.spy_put_spread_v1.bot
