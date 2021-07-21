#!/usr/bin/env bash
set -e
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit

# Write config file
sudo rm /etc/supervisor/conf.d/timelapse_capture.conf || true
[ -f tmp_tl.conf ] && sudo rm tmp_tl.conf
cat << EOF > tmp_tl.conf
[program:timelapse_capture]
command=/usr/local/bin/timelapse_capture.sh
autostart=true
autorestart=true
stderr_logfile=/var/log/timelapse_capture.err.log
stdout_logfile=/var/log/timelapse_capture.out.log
EOF
sudo cp tmp_tl.conf /etc/supervisor/conf.d/timelapse_capture.conf
sudo rm tmp_tl.conf

# Get parameters from .env
source .env
INTERVAL=${INTERVAL:-600}
THREADS=${THREADS:-1}
WEBHOOK_URL=${WEBHOOK_URL:-""}
HEALTHCHECK_URL=${HEALTHCHECK_URL:-""}
SOURCE_DIRECTORY=$(pwd)

sudo rm /usr/local/bin/timelapse_capture.sh || true
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
echo "-> python main.py --save --interval ${INTERVAL} --threads ${THREADS} --visualise --webhook ${WEBHOOK_URL} --health ${HEALTHCHECK_URL}"

python main.py --save --interval "${INTERVAL}" --threads "${THREADS}" --webhook "${WEBHOOK_URL}" --health "${HEALTHCHECK_URL}"
EOF
sudo cp tmp_tl.sh /usr/local/bin/timelapse_capture.sh
sudo chmod +x /usr/local/bin/timelapse_capture.sh
sudo rm tmp_tl.sh

sudo supervisorctl reread
sudo supervisorctl update
