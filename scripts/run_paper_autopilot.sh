#!/bin/zsh
set -eu

script_directory=${0:A:h}
repository_root=${script_directory:h}

exec /usr/bin/caffeinate -i \
  /usr/bin/env PYTHONPATH="${repository_root}/src" \
  "${repository_root}/.venv/bin/python" -u -m swingbot.cli \
  paper --root "${repository_root}" autopilot \
  --authorization I_AUTHORIZE_UNATTENDED_PAPER_ONLY \
  --interval 15 \
  --closed-interval 60
