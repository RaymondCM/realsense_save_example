#!/usr/bin/env bash
set -e
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit

config_name=${1:-"timelapse-capture"}

# Delete config file
sudo rm /etc/supervisor/conf.d/${config_name}.conf || true
[ -f tmp_tl.conf ] && sudo rm tmp_tl.conf

sudo rm /usr/local/bin/${config_name}.sh || true
[ -f tmp_tl.sh ] && sudo rm tmp_tl.sh

sudo supervisorctl reread
sudo supervisorctl update
