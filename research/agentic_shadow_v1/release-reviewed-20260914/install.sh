#!/bin/sh
# Run only after verifying the personal server's identity and release tests.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root required for new isolated systemd unit installation'; exit 1; }
stage=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$stage/verify_release.py"
revision=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$stage/RELEASE.json")
release="/opt/trading-shadow-7500-v1-$revision"
[ ! -e "$release" ] || { echo 'Release already exists; inspect it instead of overwriting'; exit 1; }
[ ! -e /etc/systemd/system/trading-shadow-7500.service ] || { echo 'Shadow service already exists; no overwrite'; exit 1; }
[ ! -e /etc/systemd/system/trading-shadow-7500.timer ] || { echo 'Shadow timer already exists; no overwrite'; exit 1; }
# No collector configuration, identity, archive, credentials, or service is changed.
cp -R "$stage" "$release"
chmod -R a+rX,a-w "$release"
mkdir -p /var/lib/trading-shadow-7500-inbox
chmod 755 /var/lib/trading-shadow-7500-inbox
sed "s|@RELEASE@|$release|g" "$release/trading-shadow-7500.service" > /etc/systemd/system/trading-shadow-7500.service
cp "$release/trading-shadow-7500.timer" /etc/systemd/system/trading-shadow-7500.timer
systemd-analyze verify /etc/systemd/system/trading-shadow-7500.service /etc/systemd/system/trading-shadow-7500.timer
systemctl daemon-reload
systemctl enable --now trading-shadow-7500.timer
printf 'Installed shadow release %s. Verify an actual timer-triggered run before claiming scheduling readiness.\n' "$revision"
