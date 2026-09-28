#!/bin/sh
# Replace only this experiment's immutable release and unit definitions.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root required'; exit 1; }
stage=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 "$stage/verify_release.py"
revision=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$stage/RELEASE.json")
release="/opt/trading-shadow-indicative-v1-$revision"
[ -r /etc/trading-shadow-indicative/alpaca.env ] || { echo 'Installed credential missing'; exit 1; }
for unit in trading-shadow-indicative-producer.service trading-shadow-indicative-smoke.service trading-shadow-indicative-producer.timer trading-shadow-indicative-consumer.service trading-shadow-indicative.path; do
    [ -e "/etc/systemd/system/$unit" ] || { echo "Installed unit missing: $unit"; exit 1; }
done
[ ! -e "$release" ] || { echo 'Release already exists; refusing overwrite'; exit 1; }
PYTHONPATH="$stage/src:$stage" PYTHONDONTWRITEBYTECODE=1 python3 "$stage/validate_credentials.py" /etc/trading-shadow-indicative/alpaca.env
cp -R "$stage" "$release"
chmod -R a+rX,a-w "$release"
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
printf 'Upgraded plumbing-only indicative release to %s with new revision-bound consumer state. Previous release and state preserved.\n' "$revision"
