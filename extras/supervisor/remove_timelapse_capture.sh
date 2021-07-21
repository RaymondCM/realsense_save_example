#!/usr/bin/env bash
set -e
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit

# Delete config file
sudo rm /etc/supervisor/conf.d/timelapse_capture.conf || true
[ -f tmp_tl.conf ] && sudo rm tmp_tl.conf

sudo rm /usr/local/bin/timelapse_capture.sh || true
[ -f tmp_tl.sh ] && sudo rm tmp_tl.sh

sudo supervisorctl reread
sudo supervisorctl update
