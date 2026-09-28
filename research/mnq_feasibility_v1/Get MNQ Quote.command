#!/bin/zsh
set -u
script_dir="${0:A:h}"
"$script_dir/../../.venv/bin/python" "$script_dir/quote_only.py"
printf '\nPress Return to close this window. '
read -r reply
