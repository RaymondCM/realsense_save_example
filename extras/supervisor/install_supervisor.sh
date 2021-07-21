#!/usr/bin/env bash
set -e
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit

sudo apt install supervisor -y
sudo service supervisor restart