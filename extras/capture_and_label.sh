#!/usr/bin/env bash
# Utility script to allow easy annotation of files as they are captured
set -e
cd $HOME/realsense_save_example/extras
cd ..

trap 'kill $(jobs -p)' EXIT

source venv/bin/activate
[ -f ./extras/labelme ] || wget https://github.com/wkentaro/labelme/releases/download/v4.5.6/labelme-Linux -O ./extras/labelme
chmod +x ./extras/labelme extras/capture_and_label.desktop

save_path=$(python -c "from rs_store.utils import get_new_save_path;print(get_new_save_path())")
echo "Saving in $save_path"
mkdir -p "$save_path"
./extras/labelme "$save_path" --autosave &
python main.py --save --threads 1 --visualise --out "$save_path"