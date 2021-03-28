import json
import pathlib
from datetime import datetime
import numpy as np
import cv2

folder_name = str(datetime.now())
for o in ['.', ':', " "]:
    folder_name = folder_name.replace(o, "_")
save_path = pathlib.Path(__file__).parent.parent / "saved_data" / folder_name
log_file = save_path / "log.txt"
save_log = False


def log(*args, **kwargs):
    if save_log:
        with log_file.open('a' if log_file.exists() else 'w') as fh:
            print(*args, **kwargs, file=fh)
    print(*args, **kwargs)


def save_img(p, i):
    if not str(p).lower().endswith(('.png', '.jpg', '.jpeg')):
        p = str(p) + '.png'
    cv2.imwrite(str(p), i)


def save_dict(p, d):
    if not str(p).lower().endswith('.json'):
        p = str(p) + '.json'
    with open(str(p), 'w') as f:
        json.dump(d, f, default=lambda obj: str(obj), indent=4)


def save(p, d, job_meta=None):
    if isinstance(d, dict):
        save_dict(p, d)
    elif isinstance(d, np.ndarray):
        save_img(p, d)
    else:
        raise TypeError
