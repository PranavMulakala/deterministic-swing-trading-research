#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
exec env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m dashboard.server
