import time
from copy import deepcopy
from io import StringIO

import pyrealsense2 as rs
import numpy as np
import cv2

import pathlib
from datetime import datetime
import json
import argparse
from timeit import default_timer as timer

import threading
import queue

from raytils.display import OpenCVDisplay
from raytils.system import LoadBalancer
from tqdm import tqdm

from rs_store.camera import RealsenseD400Camera
from rs_store.save import save_dict, save_img, save

folder_name = str(datetime.now())
for o in ['.', ':', " "]:
    folder_name = folder_name.replace(o, "_")
save_path = pathlib.Path(__file__).parent / "saved_data" / folder_name
log_file = save_path / "log.txt"
save_log = False


def log(*args, **kwargs):
    if save_log:
        with log_file.open('a' if log_file.exists() else 'w') as fh:
            print(*args, **kwargs, file=fh)
    print(*args, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--visualise", action='store_true', default=False, help="Show the current frames")
    parser.add_argument("--save", action='store_true', default=False, help="Save the current frames")
    parser.add_argument("--interval", default=1/30, help="Number of seconds to wait between captures")
    parser.add_argument("--config", default=None, help="Config json file saved from realsense-viewer")
    parser.add_argument("--threads", default=8, help="Number of threads to use for writing to disk")
    args = parser.parse_args()

    # TODO: ADD FILTERS

    if args.config is None:
        args.config = pathlib.Path(__file__).parent / "configs/default.yaml"
    if args.save:
        global save_log
        save_log = True
        if not save_path.exists():
            save_path.mkdir(parents=True)
        idx = 0
        log("Saving images to {}".format(save_path.resolve()))
        load_balancer = LoadBalancer(maxsize=80, threads=1, auto=False)
    args.interval = float(args.interval)

    camera = RealsenseD400Camera(config_path=args.config, visualise=args.visualise)
    last_capture = timer()

    try:
        shutdown = False
        while not shutdown:
            time_since_last_capture = timer() - last_capture

            frames = camera.get_frames()

            if args.save and time_since_last_capture > args.interval:
                last_capture = timer()
                time_str = str(datetime.time(datetime.now())).replace(".", "_").replace(":", "_")

                for k in ["colour", "depth", "aligned_depth", "aligned_depth_cm", "ir_left", "ir_right", "meta"]:
                    data = getattr(frames, k)
                    if data is None:
                        continue
                    load_balancer.add_task(save, (save_path / f"{idx:07d}_{time_str}_{k}", data), {})

                log(f"Saving queue_size={load_balancer.qsize()}, iter={idx:07d} "
                    f"tps={load_balancer.tasks_per_second.get_fps()}")
                idx += 1
    finally:
        camera.pipeline.stop()
        if args.save:
            load_balancer.join()


if __name__ == '__main__':
    main()
