#!/bin/sh
# Install only the separate plumbing-only producer/consumer units.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root required'; exit 1; }
[ "$#" = 1 ] || { echo 'usage: install.sh /path/to/dedicated-alpaca.env'; exit 1; }
stage=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
credential_source=$1
PYTHONDONTWRITEBYTECODE=1 python3 "$stage/verify_release.py"
PYTHONPATH="$stage/src:$stage" PYTHONDONTWRITEBYTECODE=1 python3 "$stage/validate_credentials.py" "$credential_source"
revision=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$stage/RELEASE.json")
release="/opt/trading-shadow-indicative-v1-$revision"
for unit in trading-shadow-indicative-producer.service trading-shadow-indicative-smoke.service trading-shadow-indicative-producer.timer trading-shadow-indicative-consumer.service trading-shadow-indicative.path; do
    [ ! -e "/etc/systemd/system/$unit" ] || { echo "Unit already exists: $unit"; exit 1; }
done
[ ! -e "$release" ] || { echo 'Release already exists; refusing overwrite'; exit 1; }
[ ! -e /etc/trading-shadow-indicative ] || { echo 'Credential directory already exists; refusing overwrite'; exit 1; }
getent group shadow-indicative >/dev/null 2>&1 || groupadd --system shadow-indicative
if id shadow-indicative-producer >/dev/null 2>&1; then
    [ "$(id -gn shadow-indicative-producer)" = shadow-indicative ] || { echo 'Producer user has unexpected group'; exit 1; }
else
    useradd --system --no-create-home --shell /usr/sbin/nologin --gid shadow-indicative shadow-indicative-producer
fi
install -d -o shadow-indicative-producer -g shadow-indicative -m 0750 /var/lib/trading-shadow-indicative-inbox
install -d -o shadow-indicative-producer -g shadow-indicative -m 0750 /var/lib/trading-shadow-indicative-archive
install -d -o root -g root -m 0700 /etc/trading-shadow-indicative
install -o root -g root -m 0600 "$credential_source" /etc/trading-shadow-indicative/alpaca.env
cp -R "$stage" "$release"
chmod -R a+rX,a-w "$release"
for unit in trading-shadow-indicative-producer.service trading-shadow-indicative-smoke.service trading-shadow-indicative-consumer.service; do
    sed -e "s|@RELEASE@|$release|g" -e "s|@STATE@|$revision|g" -e "s|@REVISION@|$revision|g" \
        "$release/$unit" > "/etc/systemd/system/$unit"
done
cp "$release/trading-shadow-indicative-producer.timer" /etc/systemd/system/trading-shadow-indicative-producer.timer
cp "$release/trading-shadow-indicative.path" /etc/systemd/system/trading-shadow-indicative.path
systemd-analyze verify /etc/systemd/system/trading-shadow-indicative-producer.service /etc/systemd/system/trading-shadow-indicative-smoke.service /etc/systemd/system/trading-shadow-indicative-producer.timer /etc/systemd/system/trading-shadow-indicative-consumer.service /etc/systemd/system/trading-shadow-indicative.path
systemctl daemon-reload
systemctl enable --now trading-shadow-indicative.path trading-shadow-indicative-producer.timer
printf 'Installed plumbing-only indicative release %s with revision-bound consumer state. Run the smoke unit, then verify both services and the path trigger.\n' "$revision"
