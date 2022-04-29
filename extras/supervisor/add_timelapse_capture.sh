#!/usr/bin/env bash
set -e
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit

config_name=${1:-"timelapse-capture"}

# Write config file
sudo rm /etc/supervisor/conf.d/${config_name}.conf || true
[ -f tmp_tl.conf ] && sudo rm tmp_tl.conf
cat << EOF > tmp_tl.conf
[program:${config_name}]
command=/usr/local/bin/${config_name}.sh
autostart=true
autorestart=true
stderr_logfile=/var/log/${config_name}.err.log
stdout_logfile=/var/log/${config_name}.out.log
EOF
sudo cp tmp_tl.conf /etc/supervisor/conf.d/${config_name}.conf
sudo rm tmp_tl.conf

# Get parameters from .env
source .env
INTERVAL=${INTERVAL:-600}
THREADS=${THREADS:-1}
WEBHOOK_URL=${WEBHOOK_URL:-""}
HEALTHCHECK_URL=${HEALTHCHECK_URL:-""}
CONFIG_PATH=${CONFIG_PATH:-""}
SOURCE_DIRECTORY=$(pwd)

sudo rm /usr/local/bin/${config_name}.sh || true
[ -f tmp_tl.sh ] && sudo rm tmp_tl.sh
cat << EOF > tmp_tl.sh
#!/usr/bin/env bash
set -e
cd "$SOURCE_DIRECTORY"
cd ../..

source venv/bin/activate
sleep 2


echo "Starting with parameters:"
echo -e "\tINTERVAL: ${INTERVAL}"
echo -e "\tTHREADS: ${THREADS}"
echo -e "\tWEBHOOK_URL: ${WEBHOOK_URL}"
echo -e "\tHEALTHCHECK_URL: ${HEALTHCHECK_URL}"
echo "-> python main.py --save --interval ${INTERVAL} --threads ${THREADS} --webhook ${WEBHOOK_URL} --health ${HEALTHCHECK_URL} --config ${CONFIG_PATH}"

python main.py --save --interval "${INTERVAL}" --threads "${THREADS}" --webhook "${WEBHOOK_URL}" --health "${HEALTHCHECK_URL} --config ${CONFIG_PATH}"
EOF
sudo cp tmp_tl.sh /usr/local/bin/${config_name}.sh
sudo chmod +x /usr/local/bin/${config_name}.sh
sudo rm tmp_tl.sh

sudo supervisorctl reread
sudo supervisorctl update
