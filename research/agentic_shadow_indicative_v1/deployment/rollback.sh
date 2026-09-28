#!/bin/sh
# Activate this immutable release and its matching preserved consumer state.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root required'; exit 1; }
release=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 "$release/verify_release.py"
revision=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$release/RELEASE.json")
[ -r /etc/trading-shadow-indicative/alpaca.env ] || { echo 'Installed credential missing'; exit 1; }
PYTHONPATH="$release/src:$release" PYTHONDONTWRITEBYTECODE=1 python3 "$release/validate_credentials.py" /etc/trading-shadow-indicative/alpaca.env
systemctl stop trading-shadow-indicative-producer.timer trading-shadow-indicative.path
for unit in trading-shadow-indicative-producer.service trading-shadow-indicative-smoke.service trading-shadow-indicative-consumer.service; do
    sed -e "s|@RELEASE@|$release|g" -e "s|@STATE@|$revision|g" -e "s|@REVISION@|$revision|g" \
        "$release/$unit" > "/etc/systemd/system/$unit"
done
cp "$release/trading-shadow-indicative-producer.timer" /etc/systemd/system/trading-shadow-indicative-producer.timer
cp "$release/trading-shadow-indicative.path" /etc/systemd/system/trading-shadow-indicative.path
systemd-analyze verify /etc/systemd/system/trading-shadow-indicative-producer.service /etc/systemd/system/trading-shadow-indicative-smoke.service /etc/systemd/system/trading-shadow-indicative-producer.timer /etc/systemd/system/trading-shadow-indicative-consumer.service /etc/systemd/system/trading-shadow-indicative.path
systemctl daemon-reload
systemctl enable --now trading-shadow-indicative.path trading-shadow-indicative-producer.timer
printf 'Activated indicative release %s and its preserved revision-bound consumer state.\n' "$revision"
