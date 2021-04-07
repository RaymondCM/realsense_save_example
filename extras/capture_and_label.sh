#!/usr/bin/env bash
# Utility script to allow easy annotation of files as they are captured
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" ||
cd ..

source venv/bin/activate
[ -f labelme ] || wget https://github.com/wkentaro/labelme/releases/download/v4.5.6/labelme-Linux -O labelme
chmod +x labelme capture_and_label.desktop

save_path=$(python -c "from rs_store.utils import get_new_save_path;print(get_new_save_path())")
echo "Saving in $save_path"
mkdir -p "$save_path"
./labelme "$save_path" --autosave &
python ../main.py --save --threads 1 --visualise --out "$save_path"